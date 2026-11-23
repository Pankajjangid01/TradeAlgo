from SmartApi import SmartConnect
import pyotp
from getpass import getpass

api_key = getpass("API Key: ")
totp_secret = getpass("TOTP Secret: ")
client_code = input("Client Code: ")
pin = getpass("Trading PIN: ")

smart_api = SmartConnect(api_key=api_key)

totp = pyotp.TOTP(totp_secret).now()
print("TOTP generated successfully")

session = smart_api.generateSession(client_code, pin, totp)

print("Login status:", session.get("status"))

if session.get("status"):
    access_token = session["data"]["jwtToken"]
    refresh_token = session["data"]["refreshToken"]

    feed_token = smart_api.getfeedToken()

    print("Feed token:", "Received" if feed_token else "Missing")

    smart_api.setAccessToken(access_token)
    smart_api.setRefreshToken(refresh_token)
    smart_api.setFeedToken(feed_token)

    profile = smart_api.getProfile(refresh_token)
    print("Profile:", profile)

    result = smart_api.getMarketData(
        "FULL",
        {"NSE": ["99926000"]}
    )

    print("Market Data:", result)

else:
    print("Login failed:", session)
