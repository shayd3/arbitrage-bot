# Arbitrage Bot

A sports prediction market bot targeting Kalshi. The bot monitors live sports scores via ESPN's public API and identifies potential arbitrage and value betting opportunities on Kalshi prediction markets.

## Overview

- **Backend**: Python 3.12+ with FastAPI, asyncio, httpx, and aiosqlite
- **Frontend**: Vite + React + TypeScript with TanStack Query, Recharts, and Tailwind CSS v4
- **Database**: SQLite via aiosqlite
- **Modes**: `dry-run` (no orders), `simulation` (virtual trades), `live` (real orders)

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
   - `BOT_MODE` — `simulation` to start (no real orders placed)

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
| GET | `/api/health` | Health check |
| GET | `/api/games` | Live game scores (ESPN) |
| GET | `/api/markets` | Kalshi open markets |
| GET | `/api/markets/{ticker}` | Single market detail |
| GET | `/api/balance` | Current balance |
| GET | `/api/balance/history` | Balance history |
| GET | `/api/trades` | Trade history |
| WS | `/ws` | Real-time updates |

## Project Structure

```
arbitrage-bot/
├── backend/
│   ├── api/
│   │   ├── routes.py       # FastAPI route handlers
│   │   └── websocket.py    # WebSocket connection manager
│   ├── clients/
│   │   ├── espn.py         # ESPN scoreboard poller
│   │   └── kalshi.py       # Kalshi API client (RSA-PSS auth)
│   ├── config.py           # Settings via pydantic-settings
│   ├── db.py               # aiosqlite database layer
│   ├── models.py           # Pydantic domain models
│   └── main.py             # FastAPI app entrypoint
├── frontend/
│   └── src/
│       ├── api/            # React Query hooks + WebSocket
│       ├── components/     # Shared UI components
│       ├── pages/          # Route-level page components
│       └── types/          # TypeScript interfaces
├── .env.example
└── pyproject.toml
```
