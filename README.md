# TradeIQ — Intelligent Algo Trading Platform

Complete algo-trading platform for the Indian derivatives market (NIFTY 50 & SENSEX options). Built with **FastAPI + Python** backend and **React + TypeScript + Material UI** frontend.

---

## 📑 Table of Contents

1. [Project Overview](#-project-overview)
2. [Features List](#-features-list)
3. [Project Structure](#-project-structure)
4. [Prerequisites](#-prerequisites)
5. [Step-by-Step Setup](#-step-by-step-setup)
   - [Option A: Docker (Recommended)](#option-a-docker-recommended)
   - [Option B: Local Development](#option-b-local-development)
6. [Configuration (.env)](#-configuration-env)
7. [Demo Account & Login Details](#-demo-account--login-details)
8. [Demo vs Real Account Flow](#-demo-vs-real-account-flow)
9. [How the Platform Works (End-to-End)](#-how-the-platform-works-end-to-end)
10. [All Screens & Functionality](#-all-screens--functionality)
11. [How to Test Everything on the UI](#-how-to-test-everything-on-the-ui)
12. [Backend API Endpoints](#-backend-api-endpoints)
13. [Running Tests](#-running-tests)
14. [Access URLs](#-access-urls)
15. [Troubleshooting](#-troubleshooting)
16. [Disclaimer](#-disclaimer)

---

## 🎯 Project Overview

TradeIQ is an automated intraday algorithmic trading platform for the **Indian derivatives market** (NIFTY 50 and SENSEX options). It follows a hierarchical decision architecture:

**Market Regime → Price Action → Trend → Momentum → Volume → ML → Risk → Execution**

It supports three strategies:
- **ORB** — Opening Range Breakout
- **VWAP Pullback** — VWAP Trend Pullback
- **S/R Breakout** — Support/Resistance Breakout & Retest

It includes ML signal prediction (KNN classifier), pre-trade risk checks, capital-aware options selection, order management with idempotency, backtesting, and a full React dashboard.

---

## 🌟 Features List

| Category | Features |
|----------|----------|
| **Strategies** | ORB, VWAP Pullback, S/R Breakout & Retest |
| **Market Regime** | Strong Bullish/Bearish, Sideways, High/Low Volatility, Breakout Transition, Uncertain |
| **Indicators** | EMA (9/20/50), VWAP, RSI, MACD, ADX/DI, ATR, Bollinger Bands, Relative Volume |
| **ML** | KNN classifier, 17 features, walk-forward validation, drift detection, rule-based fallback |
| **Risk** | Daily loss limit, max positions, consecutive losses, kill switch, R:R ratio, stop/target methods |
| **Options** | Affordability check, alternative strike search (ATM→OTM→ITM), liquidity filters (OI/volume/spread) |
| **Order Mgmt** | State machine, idempotency, reconciliation, Angel One + Flattrade adapters |
| **Backtesting** | 2024–2026 data, no look-ahead bias, cost modeling (slippage, STT, GST, SEBI, stamp duty) |
| **Frontend** | Dashboard, Market Analysis, Signal Center, Trading Terminal, Backtesting, ML Monitoring, Risk Console, Audit Logs, Settings |

---

## 📁 Project Structure

```
trade-algo/
├── backend/                  # FastAPI + Python backend
│   ├── app/
│   │   ├── api/              # API route modules
│   │   ├── brokers/          # Broker adapters (Angel One, Flattrade)
│   │   ├── config/           # settings.py (all config)
│   │   ├── core/             # Core configuration
│   │   ├── db/               # Database models & session
│   │   ├── market_data/      # Broker market-data clients
│   │   ├── ml/               # ML inference engine
│   │   ├── oms/              # Order Management System
│   │   ├── risk/             # Risk engine
│   │   ├── services/         # Indicators, structure, regime
│   │   ├── strategies/       # ORB, VWAP, S/R engines
│   │   └── main.py           # FastAPI app entrypoint
│   ├── requirements.txt
│   ├── Dockerfile
│   └── tests/
├── frontend/                 # React + TypeScript + MUI frontend
│   ├── src/
│   │   ├── components/       # Reusable UI components (Layout, etc.)
│   │   ├── pages/            # All dashboard pages
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # api.ts (axios), websocket.ts
│   │   ├── store/            # Redux slices (market, signals, trading, ui)
│   │   ├── theme/            # MUI theme
│   │   ├── types/            # TypeScript types
│   │   └── utils/            # Helper functions
│   ├── package.json
│   └── Dockerfile
├── deployment/
│   ├── docker-compose.yml
│   └── nginx.conf
├── .env.example              # Environment template (copy to .env)
├── .env                      # Your actual env (create from .env.example)
├── start.sh                  # One-script startup (backend + frontend)
└── README.md                 # This file
```

---

## 🔧 Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Docker & Docker Compose | latest | Recommended one-command setup |
| Python | 3.11+ | Backend (local dev) |
| Node.js | 20+ | Frontend (local dev) |
| PostgreSQL | 15+ | Database (if not using Docker) |
| Redis | 7+ | Cache/queue (if not using Docker) |

---

## 🚀 Step-by-Step Setup

### Option A: Docker (Recommended)

Run everything from the **project root** (`/home/codetrade/Desktop/trade-algo`):

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your broker credentials (see Configuration section below)
nano .env

# 3. Start all services (backend + frontend + postgres + redis)
docker-compose up -d

# 4. Watch logs
docker-compose logs -f
```

Or use the bundled startup script:

```bash
chmod +x start.sh
./start.sh
```

### Option B: Local Development (no Docker)

Open **two terminals** in the project root.

**Terminal 1 — Backend:**
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# edit .env with your values
alembic upgrade head
uvicorn app.main:app --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm install
npm start
```

---

## ⚙️ Configuration (.env)

Copy `.env.example` to `.env` and fill in your values. Key sections:

### Broker Credentials (required for live trading)
```env
ANGELONE_API_KEY=your_angelone_api_key
ANGELONE_CLIENT_CODE=your_client_code
ANGELONE_PASSWORD=your_password
ANGELONE_TOTP_SECRET=your_totp_secret

# Optional secondary broker
FLATTRADE_API_KEY=your_flattrade_api_key
FLATTRADE_API_SECRET=your_flattrade_api_secret
FLATTRADE_CLIENT_ID=your_client_id
```

### Market Data Provider
```env
MARKET_DATA_PROVIDER=angelone   # angelone or flattrade
```

### Risk Limits (edit in `backend/app/config/settings.py` → `RISK_CONFIG`)
| Setting | Default | Meaning |
|---------|---------|---------|
| `initial_risk_per_trade_pct` | 0.0035 | 0.35% risk per trade |
| `max_daily_loss_pct` | 0.0125 | 1.25% max daily loss |
| `max_simultaneous_positions` | 1 | Max open positions |
| `max_consecutive_losses` | 3 | Kill switch after N losses |
| `target_r_multiple` | 2.0 | Default target = 2R |

---

## 🔑 Demo Account & Login Details

**There is no real user database.** Authentication on the frontend is **mock/demo-only**:

- **Login URL:** http://localhost:3000/login
- **Demo Email:** `trader@tradeiq.com`
- **Demo Password:** `demo123`

On the Login page there is a **"Fill Demo Credentials"** button that auto-fills these values. Any non-empty email + password works (mock auth), but the demo pair is the intended one.

After login, a mock JWT is stored in `localStorage` and you're redirected to `/dashboard`.

> ⚠️ This is a demo/mock login. Do not use real broker credentials here. Real broker keys go only in `.env` (backend), not in the login form.

---

## 🔄 Demo vs Real Account Flow

TradeIQ does **not** have a separate "demo mode" toggle in the UI. Instead, the distinction is at the **broker/configuration layer**:

### Demo / Paper Trading Flow
1. Login with demo credentials (`trader@tradeiq.com` / `demo123`).
2. Go to **Settings → Brokers** — do **not** enter real Angel One/Flattrade keys (leave them empty or in paper mode).
3. Go to **Risk Console** — set your risk limits (these are virtual/demo limits).
4. Go to **Market Analysis** / **Signal Center** — view signals (ML + rule-based).
5. Go to **Trading Terminal** — toggle "Trading Enabled". Orders are simulated locally; no real broker API is called unless keys are configured.
6. Go to **Backtesting** — run historical backtests on 2024–2026 data.
7. View **Audit Logs** to see all actions.

### Real / Live Trading Flow
1. Obtain real **Angel One SmartAPI** (or Flattrade) API keys from your broker.
2. Add them to `.env`:
   ```env
   ANGELONE_API_KEY=...
   ANGELONE_CLIENT_CODE=...
   ANGELONE_PASSWORD=...
   ANGELONE_TOTP_SECRET=...
   MARKET_DATA_PROVIDER=angelone
   ```
3. Restart the backend (`docker-compose restart` or `uvicorn ... --reload`).
4. In UI: **Settings → Brokers** — enter/verify the connection.
5. **Risk Console** — set real risk limits (daily loss, max positions, etc.).
6. **Trading Terminal** — enable trading. Real orders go to the broker via the OMS.
7. Monitor positions/P&L in **Dashboard** and **Trading Terminal**.
8. All actions are recorded in **Audit Logs**.

**Rule:** Never put real broker secrets in the login form or frontend code. They belong only in `.env` read by the backend.

---

## 🧩 How the Platform Works (End-to-End)

```
┌─────────────┐      REST/WebSocket      ┌──────────────┐
│  React UI   │ ◄───────────────────────► │  FastAPI     │
│  (port 300) │                           │  (port 800)  │
└─────────────┘                           └──────┬───────┘
                                                 │
        ┌────────────────────────────────────────┼────────────────────────────────┐
        │                                        │                                │
   Market Data                              Risk Engine                        OMS
   (Angel One/Flattrade)                   (pre-trade checks)               (Order Mgmt)
        │                                        │                                │
   ML Inference                            Options Selector                   Broker API
   (KNN classifier)                        (capital-aware)                  (Angel One/Flattrade)
```

**Request lifecycle (placing a trade):**
1. User enables trading in **Trading Terminal**.
2. Frontend calls `POST /api/v1/orders/place` via the API service (`src/services/api.ts`).
3. Backend **Risk Engine** runs pre-trade checks (daily loss, position count, consecutive losses, R:R).
4. If risk passes, **Options Selector** picks an affordable strike (ATM → OTM → ITM).
5. **OMS** creates the order (state: CREATED → VALIDATED → SUBMITTED → ... → FILLED).
6. Order is sent to the broker adapter (Angel One or Flattrade).
7. WebSocket (`/ws/market`) pushes live ticks; frontend updates Dashboard/Signal Center in real time.
8. Every action is written to **Audit Logs**.

---

## 🖥️ All Screens & Functionality

| Page | Path | What it does |
|------|------|--------------|
| **Login** | `/login` | Mock login. Demo creds: `trader@tradeiq.com` / `demo123`. |
| **Dashboard** | `/dashboard` | Home. Overview of market status, signals, risk summary. |
| **Market Analysis** | `/market-analysis` | Candlestick charts, indicators, regime display, structure levels, signal analysis. |
| **Signal Center** | `/signals` | Live signals with ML predictions, filtering, detail views. |
| **Trading Terminal** | `/trading` | Position monitoring, order book, new order entry, trading on/off toggle. |
| **Backtesting** | `/backtesting` | Configure strategy/symbol/dates, run backtest, view equity curves & trade lists. |
| **ML Monitoring** | `/ml-monitoring` | Model performance, predictions, feature importance, drift detection. |
| **Risk Console** | `/risk` | Real-time risk metrics, config (risk per trade, daily loss, positions), kill switch. |
| **Audit Logs** | `/audit` | Full audit trail of all actions with filtering and detail view (old/new values). |
| **Settings** | `/settings` | Profile, broker config, trading mode (paper/live), notifications, system, security. |

---

## 🧪 How to Test Everything on the UI

### 1. Login
- Open http://localhost:3000/login
- Click **"Fill Demo Credentials"** or type `trader@tradeiq.com` / `demo123`
- Click **Sign In** → redirects to `/dashboard`

### 2. Dashboard
- Verify you land on `/dashboard`
- Check market status cards and quick stats

### 3. Market Analysis
- Go to `/market-analysis`
- Select symbol (NIFTY/SENSEX), timeframe
- Observe regime badge, indicators, structure levels
- Click **Analyze** to generate signals

### 4. Signal Center
- Go to `/signals`
- View live signal list
- Filter by action/symbol
- Click a signal for details (ML prediction, confidence)

### 5. Trading Terminal (Paper/Demo)
- Go to `/trading`
- Ensure broker keys are **not** configured (paper/demo mode)
- Toggle **Trading Enabled** switch
- Try placing a mock order → should succeed in demo mode
- Watch **Order Book** and **Positions**

### 6. Backtesting
- Go to `/backtesting`
- Choose strategy (ORB / VWAP / S/R)
- Choose symbol (NIFTY/SENSEX), date range, capital
- Click **Run Backtest**
- View **Results History** → equity curve, win rate, max drawdown, Sharpe

### 7. ML Monitoring
- Go to `/ml-monitoring`
- Check model status (loaded/not loaded)
- View predictions, feature importance bars, drift detection

### 8. Risk Console
- Go to `/risk`
- View current risk metrics (daily P&L, positions, consecutive losses)
- Edit configuration (risk per trade %, max positions, etc.)
- Test **Kill Switch** toggle

### 9. Audit Logs
- Go to `/audit`
- Perform actions above (login, settings change, order)
- Refresh logs → see entries with timestamp, action, entity, user
- Click **View Changes** to see old vs new values

### 10. Settings
- Go to `/settings`
- Tabs: Profile, Brokers, Trading, Notifications, System, Security
- In **Brokers** tab: enter demo/test keys (do not use real keys unless going live)
- In **Trading** tab: toggle Paper vs Live mode
- Click **Save Changes**

---

## 🔌 Backend API Endpoints

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/status` | System status (market data, ML, trading) |
| GET | `/api/v1/market/ltp` | Last traded price |
| GET | `/api/v1/market/quote` | Market quote |
| GET | `/api/v1/market/historical` | Historical candles |
| GET | `/api/v1/market/instruments` | Search instruments |
| GET | `/api/v1/market/option-chain` | Option chain |
| POST | `/api/v1/market/provider` | Set data provider |
| GET | `/api/v1/account/funds` | Funds |
| GET | `/api/v1/account/positions` | Positions |
| GET | `/api/v1/account/holdings` | Holdings |
| GET | `/api/v1/account/orders` | Order book |
| POST | `/api/v1/signals/analyze` | Analyze market & generate signals |
| GET | `/api/v1/signals/active` | Active signals |
| POST | `/api/v1/orders/place` | Place order |
| POST | `/api/v1/orders/{id}/modify` | Modify order |
| POST | `/api/v1/orders/{id}/cancel` | Cancel order |
| POST | `/api/v1/risk/check` | Pre-trade risk check |
| POST | `/api/v1/risk/position-size` | Calculate position size |
| POST | `/api/v1/options/select` | Select option contract |
| POST | `/api/v1/backtest/run` | Run backtest |
| GET | `/api/v1/backtest/{run_id}` | Backtest results |
| WS | `/ws/market` | Market data WebSocket |

Interactive docs: http://localhost:8000/docs (when `DEBUG=true`)

---

## 🧪 Running Tests

```bash
# Backend (from project root)
cd backend
pytest -v --cov=app

# Frontend
cd frontend
npm test
```

---

## 🌐 Access URLs

| Service | URL |
|---------|-----|
| Frontend (React) | http://localhost:3000 |
| Backend API (FastAPI) | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |
| Backend health | http://localhost:8000/health |

---

## 🛠 Troubleshooting

| Issue | Fix |
|-------|-----|
| `npm start` fails on `@mui/material/styles` | Downgrade `@mui/x-date-pickers` to v6: `npm install @mui/x-date-pickers@6 date-fns@2 --legacy-peer-deps` |
| Backend won't start | Check `.env` exists; run `alembic upgrade head` in `backend/` |
| Proxy errors to `localhost:8000` | Backend is not running — start it first |
| Build fails on `@/` imports | Use relative paths (already fixed in source) |
| Login doesn't work | Any email+password works; use demo creds `trader@tradeiq.com` / `demo123` |

---

## ⚠️ Disclaimer

This software is for **educational and research purposes**. Trading derivatives (NIFTY/SENSEX options) involves substantial risk of loss and is not suitable for every investor. Past performance is not indicative of future results. The authors are **not responsible** for any financial losses incurred through the use of this platform. Use real money only after thorough backtesting and risk understanding.

---

## 📞 Support

For issues and feature requests, open a GitHub issue.
