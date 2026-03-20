<div align="center">

# Arbitrage Bot

**A live sports prediction market scanner for [Kalshi](https://kalshi.com)**

Monitor real-time game scores · Identify mispriced markets · Execute trades with risk controls

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-TypeScript-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev)
[![SQLite](https://img.shields.io/badge/SQLite-aiosqlite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)

</div>

---

> **Disclaimer:** This software is provided for educational and informational purposes only. Use at your own risk. Prediction markets are a form of gambling and carry real financial risk — you may lose money. The author is not responsible for any financial losses, damages, or other consequences resulting from the use of this bot. Never trade with money you cannot afford to lose.

---

## How It Works

The bot polls ESPN's public API for live scores, matches active games against open Kalshi markets, and applies a **late-game value strategy** — looking for markets where implied probability hasn't caught up to the current game state. Trades are gated by pre-trade risk checks before any order is placed.

```
ESPN (live scores) ──▶ Scanner Engine ──▶ Market Matcher ──▶ Strategy Evaluator
                                                                       │
                                                               Risk Checks
                                                                       │
                                                            Kalshi Order Placement
```

---

## Supported Sports

| Sport | League |
|-------|--------|
| Football | NFL |
| Hockey | NHL |
| Baseball | MLB |
| Basketball | WNBA |
| Basketball | CBB (College) |

---

## Features

- **Real-time scanning** — polls ESPN on a configurable interval; pushes updates to the UI over WebSocket
- **Per-sport strategy** — independently tunable thresholds, max positions, and bet sizes per league
- **Risk controls** — max position size, max daily loss, and per-trade limits enforced before every order
- **Trade audit trail** — every order attempt and settlement logged to a local SQLite database
- **Balance history** — snapshots portfolio value over time for charting
- **Live dashboard** — React frontend with charts, open positions, scanner log, and strategy controls
- **Demo mode** — full workflow against Kalshi's demo environment with no real money at risk

---

## Kalshi API Setup

1. Go to [kalshi.com](https://kalshi.com) → **Account** → **API**
2. Click **Generate RSA key pair** and download the private key (`.pem`)
3. Copy the displayed **API Key ID** — you'll need it for `.env`

> For testing, use [demo.kalshi.co](https://demo.kalshi.co) and set `KALSHI_USE_DEMO=true`.

---

## Setup

### Backend

```bash
cp .env.example .env
# Edit .env — set KALSHI_API_KEY_ID, KALSHI_PRIVATE_KEY_PATH, KALSHI_USE_DEMO
uv sync
uv run python -m backend.main
# API available at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Available at http://localhost:5173
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check + demo/live mode |
| GET | `/api/games` | Live game scores (ESPN) |
| GET | `/api/markets` | Kalshi open markets |
| GET | `/api/markets/{ticker}` | Single market detail |
| GET | `/api/balance` | Current balance + portfolio value |
| GET | `/api/balance/history` | Historical balance snapshots |
| GET | `/api/trades` | Trade history |
| GET | `/api/positions` | Open Kalshi positions |
| GET | `/api/strategy` | Current strategy + interval config |
| POST | `/api/strategy/global` | Update global risk + interval settings |
| POST | `/api/strategy/sport/{sport}` | Update per-sport thresholds |
| GET | `/api/scanner/status` | Scanner running state |
| GET | `/api/scanner/log` | Recent scanner log entries |
| WS | `/ws` | Real-time game/opportunity updates |

---

## Project Structure

```
arbitrage-bot/
├── backend/
│   ├── api/
│   │   ├── routes.py           # FastAPI route handlers
│   │   └── websocket.py        # WebSocket connection manager
│   ├── clients/
│   │   ├── espn.py             # ESPN scoreboard poller
│   │   └── kalshi.py           # Kalshi API client (RSA-PSS auth)
│   ├── execution/
│   │   ├── risk.py             # Pre-trade risk checks
│   │   └── order.py            # Order placement
│   ├── scanner/
│   │   ├── engine.py           # Main scan loop, settlement detection, DB sync
│   │   ├── matcher.py          # Market↔game matching logic
│   │   └── sports.py           # Per-sport strategy configs
│   ├── strategy/
│   │   └── late_game.py        # Late-game value betting strategy
│   ├── config.py               # Settings via pydantic-settings
│   ├── db.py                   # aiosqlite database layer
│   ├── models.py               # Pydantic domain models
│   └── main.py                 # FastAPI app entrypoint
├── frontend/
│   └── src/
│       ├── api/                # Fetch functions + WebSocket hook
│       ├── components/         # Shared UI components
│       ├── hooks/              # Reusable React hooks
│       ├── pages/              # Route-level page components
│       └── types/              # TypeScript interfaces
├── tests/                      # pytest test suite
├── docs/                       # Extended documentation
├── .env.example
└── pyproject.toml
```

---

## Further Reading

- [docs/scanner.md](docs/scanner.md) — Scanner loop, settlement detection, and DB sync
- [docs/configuration.md](docs/configuration.md) — All configurable settings with defaults and minimum values
