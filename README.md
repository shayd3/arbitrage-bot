# Arbitrage Bot

A sports prediction market bot targeting Kalshi. The bot monitors live sports scores via ESPN's public API and identifies potential value betting opportunities on Kalshi prediction markets.

## Overview

- **Backend**: Python 3.12+ with FastAPI, asyncio, httpx, and aiosqlite
- **Frontend**: Vite + React + TypeScript with TanStack Query, Recharts, and Tailwind CSS v4
- **Database**: SQLite via aiosqlite (local audit trail + balance history)

## Kalshi API Key Setup

1. Go to [kalshi.com](https://kalshi.com) and log in to your account
2. Navigate to **Account** → **API**
3. Click **Generate RSA key pair**
4. Download the private key file (`.pem`) to your project directory
5. Copy the displayed API Key ID — you will need it for your `.env` file

For testing, use the [Kalshi demo environment](https://demo.kalshi.co) and set `KALSHI_USE_DEMO=true`.

## Setup

### Backend

1. Copy the example environment file and fill in your credentials:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set:
   - `KALSHI_API_KEY_ID` — your API key ID from Kalshi
   - `KALSHI_PRIVATE_KEY_PATH` — path to your downloaded `.pem` file
   - `KALSHI_USE_DEMO` — `true` for demo, `false` for live trading

2. Install dependencies with [uv](https://github.com/astral-sh/uv):
   ```bash
   uv sync
   ```

3. Run the backend:
   ```bash
   uv run python -m backend.main
   ```
   The API will be available at `http://localhost:8000`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`.

## API Endpoints

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

## Further Reading

- [docs/scanner.md](docs/scanner.md) — Scanner loop, settlement detection, and DB sync
- [docs/configuration.md](docs/configuration.md) — All configurable settings with defaults and minimum values
