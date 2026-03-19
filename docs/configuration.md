# Configuration

Settings come from two sources:

1. **Environment / `.env` file** — static values set at startup via `backend/config.py`
2. **Database config overrides** — runtime values editable from the Settings page, stored in the `config_overrides` table, read dynamically on each scan loop iteration

## Environment Settings

Defined in `backend/config.py` using `pydantic-settings`. Set via `.env` or environment variables.

| Variable | Default | Description |
|----------|---------|-------------|
| `KALSHI_API_KEY_ID` | `""` | API key ID from Kalshi account settings |
| `KALSHI_PRIVATE_KEY_PATH` | `./kalshi_private_key.pem` | Path to RSA private key file |
| `KALSHI_USE_DEMO` | `true` | `true` = demo environment, `false` = live trading |
| `DATABASE_PATH` | `./arbitrage.db` | SQLite database file path |
| `ESPN_POLL_INTERVAL` | `10.0` | Scan loop sleep interval in seconds (baseline default) |
| `KALSHI_POLL_INTERVAL` | `15.0` | Kalshi API throttle interval in seconds (baseline default) |

`ESPN_POLL_INTERVAL` and `KALSHI_POLL_INTERVAL` are only used as fallback defaults. The runtime-configurable values in the DB take precedence once set.

## Runtime Settings (Settings Page)

Stored in the `config_overrides` table. Editable live from the dashboard Settings page. All changes take effect within one scan loop iteration (no restart required).

### Global Risk

Stored under config key `global_risk` as a JSON object.

| Setting | Default | Description |
|---------|---------|-------------|
| Bet % of Balance | `20%` | Maximum cost of a single trade as a % of available balance |
| Max Open Positions | `5` | Maximum number of simultaneously open (filled) trades |
| Max Daily Loss | `$100` | Daily loss limit in dollars; bot stops placing new trades when hit |

### Scanner Intervals

Stored under config key `scanner_intervals` as a JSON object.

| Setting | Default | Minimum | Description |
|---------|---------|---------|-------------|
| ESPN Poll | `10s` | `5s` | How often the main scan loop runs and ESPN scores are fetched |
| Kalshi Poll | `15s` | `10s` | How often Kalshi markets, balance, and settlements are checked |
| DB Sync | `1800s` (30 min) | `30s` | How often the local DB is reconciled against Kalshi's order history |

Minimum floors are enforced both in the backend (before writing to the DB) and in the frontend form inputs. Values below the floor are silently raised to the minimum.

### Per-Sport Thresholds

Stored under config key `sport_config_{sport}` (e.g. `sport_config_nba`) as a JSON object.

| Setting | Description |
|---------|-------------|
| End-of-Game window | Seconds remaining in the final period to start looking for trades |
| Min Lead | Minimum point/goal/run lead required to consider a trade |
| Min YES Price | Minimum price (in cents) the favoured side must be trading at |

## Config Override Precedence

```
DB override present → use DB value (with floor enforcement)
       ↓ absent
Static .env / config.py default
```

The settings page always shows the currently active value, whether it came from the DB or the default.
