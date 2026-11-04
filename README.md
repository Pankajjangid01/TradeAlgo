# TradeIQ — Intelligent Algo Trading Platform

An automated intraday trading platform for Indian derivatives market (NIFTY 50 & SENSEX options) built with modern architecture following the BRD v1.1 specifications.

## 🚀 Features

### Core Trading Engine
- **Three Strategies**: Opening Range Breakout (ORB), VWAP Trend Pullback, Support/Resistance Breakout & Retest
- **Hierarchical Decision Architecture**: Market Regime → Price Action → Trend → Momentum → Volume → ML → Risk → Execution
- **Market Regime Detection**: Strong Bullish/Bearish, Sideways, High/Low Volatility, Breakout Transition, Uncertain
- **Technical Indicators**: EMA (9/20/50), VWAP, RSI, MACD, ADX/DI, ATR, Bollinger Bands, Relative Volume
- **Market Structure**: Swing points, Support/Resistance zones, BOS/CHoCH, Pivot levels, Opening Range

### Machine Learning
- **KNN Classifier**: Pattern matching for bullish/bearish/no-trade classification
- **Feature Engineering**: 17 technical features including EMA distances, VWAP distance, RSI, MACD histogram, ADX, volume ratios
- **Model Safety**: Chronological train/test split, walk-forward validation, probability calibration, drift detection
- **Fallback**: Rule-based prediction when model unavailable

### Risk Management
- **Pre-trade Checks**: Daily loss limit, max positions, consecutive losses, kill switch, R:R ratio, spread validation
- **Position Sizing**: Risk budget, available funds/margin, max exposure, lot size constraints
- **Stop/Target**: Structure-based, ATR-based, percentage, custom methods with 2R default target
- **Emergency Protection**: Kill switch, broker disconnect handling, data staleness detection

### Options Selection (Capital-Aware)
- **Affordability Check**: Validates premium × quantity + charges against available funds
- **Alternative Strike Search**: ATM → OTM1 → ITM1 when preferred strike unaffordable
- **Liquidity Filters**: Min OI, volume, spread, bid/ask depth requirements
- **Never Increases Risk**: Rejects trades exceeding risk budget rather than reducing size

### Order Management
- **State Machine**: CREATED → VALIDATED → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED
- **Idempotency**: Unique keys prevent duplicate orders
- **Reconciliation**: Periodic broker position sync
- **Broker Adapters**: Angel One SmartAPI (primary), Flattrade Pi API (secondary)

### Backtesting
- **Historical Replay**: 2024-2026 data with realistic costs
- **Anti-Bias**: No look-ahead, no survivorship bias, walk-forward validation
- **Cost Modeling**: Slippage, commission, STT, exchange fees, GST, SEBI, stamp duty
- **Metrics**: Win rate, profit factor, expectancy, max drawdown, Sharpe/Sortino, MAE/MFE

### Frontend Dashboard (React + TypeScript + Material UI)
- **Real-time Market Analysis**: Candlestick charts with indicators, regime display, structure levels
- **Signal Center**: Live signals with ML predictions, filtering, detail views
- **Trading Terminal**: Position monitoring, order book, new order entry
- **Backtesting UI**: Configuration, results, equity curves, trade lists
- **ML Monitoring**: Model performance, predictions, feature importance, drift detection
- **Risk Console**: Real-time risk metrics, configuration, emergency controls
- **Audit Logs**: Full audit trail with filtering and detail views

## 📁 Project Structure

```
trade-algo/
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI routes
│   │   ├── core/             # Core configuration
│   │   ├── db/               # Database models & session
│   │   ├── market_data/      # Angel One & Flattrade clients
│   │   ├── ml/               # ML inference engine
│   │   ├── oms/              # Order management system
│   │   ├── risk/             # Risk engine
│   │   ├── services/         # Indicators, structure, regime
│   │   ├── strategies/       # ORB, VWAP, S/R engines
│   │   └── main.py           # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/       # Reusable UI components
│   │   ├── pages/            # Dashboard pages
│   │   ├── hooks/            # Custom React hooks
│   │   ├── services/         # API & WebSocket clients
│   │   ├── store/            # Redux slices
│   │   ├── theme/            # Material UI theme
│   │   ├── types/            # TypeScript types
│   │   └── utils/            # Helper functions
│   ├── package.json
│   └── Dockerfile
├── deployment/
│   ├── docker-compose.yml
│   └── nginx.conf
├── .env.example
├── start.sh
└── README.md
```

## 🛠 Installation

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 20+ (for frontend development)
- PostgreSQL 15+ (if not using Docker)
- Redis 7+ (if not using Docker)

### Quick Start with Docker

```bash
# Clone and navigate
cd trade-algo

# Copy environment template
cp .env.example .env

# Edit .env with your broker credentials
nano .env

# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f
```

### Local Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
# Edit .env
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm start
```

## ⚙️ Configuration

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `ANGELONE_API_KEY` | Angel One SmartAPI key | Yes (primary) |
| `ANGELONE_CLIENT_CODE` | Angel One client code | Yes |
| `ANGELONE_PASSWORD` | Angel One password | Yes |
| `ANGELONE_TOTP_SECRET` | Angel One TOTP secret | Yes |
| `FLATTRADE_API_KEY` | Flattrade API key | Optional |
| `FLATTRADE_API_SECRET` | Flattrade API secret | Optional |
| `FLATTRADE_CLIENT_ID` | Flattrade client ID | Optional |

### Key Configuration Sections

- **Strategy Parameters**: `backend/app/config/settings.py` → `STRATEGY_CONFIG`
- **Indicator Parameters**: `INDICATOR_CONFIG`
- **Risk Limits**: `RISK_CONFIG`
- **Options Selection**: `OPTIONS_CONFIG`
- **ML Parameters**: `ML_CONFIG`

## 📊 Usage

### Starting the Platform

```bash
# Using Docker (recommended)
./start.sh

# Or manually
docker-compose up -d
```

### Accessing the Dashboard

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Trading Workflow

1. **Configure Brokers**: Settings → Brokers tab
2. **Set Risk Limits**: Risk Console → Configuration
3. **Select Strategy**: Market Analysis → Verify signals
4. **Enable Trading**: Trading Terminal → Toggle switch
5. **Monitor**: Dashboard, Signal Center, Risk Console

### Running Backtests

1. Navigate to Backtesting page
2. Configure strategy, symbol, date range
3. Adjust parameters in accordion sections
4. Click "Run Backtest"
5. View results in Results History tab

## 🔒 Security

- API credentials encrypted at rest (AES-256)
- HTTPS enforcement for all communications
- JWT-based authentication with auto-refresh
- Role-based access control (Admin/Trader)
- Audit logging for all critical actions
- Rate limiting on API endpoints

## 📈 Monitoring

- **Health Checks**: `/health` endpoint with service status
- **Latency Tracking**: P50/P95/P99 for all critical paths
- **Risk Alerts**: Daily loss, consecutive losses, position limits
- **System Metrics**: WebSocket latency, broker API latency, ML inference time

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest -v --cov=app

# Frontend tests
cd frontend
npm test
```

## 📝 License

Proprietary - TradeIQ Algorithmic Trading Platform

## ⚠️ Disclaimer

This software is for educational and research purposes. Trading derivatives involves substantial risk of loss and is not suitable for every investor. Past performance is not indicative of future results. The authors are not responsible for any financial losses incurred through the use of this platform.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

For issues and feature requests, please open a GitHub issue.