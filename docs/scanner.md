# Scanner

The scanner is the bot's main background process. It runs continuously as an asyncio task started at app startup and drives all live trading activity.

## Scan Loop

`ScannerEngine._run_loop()` sleeps for `espn_poll_interval` seconds between iterations and calls `_scan()` on each tick. Within `_scan()`, actions are individually throttled so higher-frequency operations (ESPN score polling) run more often than lower-frequency ones (Kalshi API calls).

```
every espn_poll_interval (~10s):
  └── _scan()
        ├── _refresh_intervals()          — reload any config changes
        ├── [throttled to kalshi_sync_interval (default 30min)]
        │     └── sync_trades_from_kalshi() — reconcile DB with Kalshi orders
        ├── [throttled to kalshi_poll_interval]
        │     ├── check_settlements()       — detect settled trades, write P&L
        │     ├── sync_balance()            — snapshot current balance
        │     └── _fetch_all_markets()      — refresh open Kalshi markets
        ├── fetch_games() (ESPN)            — get live scores for all active sports
        └── _process_game_markets()         — evaluate opportunities + place orders
```

> **Note:** `kalshi_sync_interval` is the interval for the DB↔Kalshi trade reconciliation and defaults to 30 minutes. The other Kalshi calls (settlements, balance, markets) run on `kalshi_poll_interval` (default 15s).

## Settlement Detection

When a Kalshi market resolves, filled trades need to be updated with their outcome and P&L. `check_settlements()` handles this by calling `/portfolio/settlements` — Kalshi's activity feed — which returns all recent settlement events in a single response.

**Flow:**
1. Load all `status='filled'` trades from the local DB
2. Fetch recent settlements from `/portfolio/settlements`
3. Build a `ticker → result` map (`"yes"` or `"no"`)
4. For each filled trade whose ticker appears in the map:
   - **Won** (trade side matches result): `pnl = contracts × (100 − price) / 100`
   - **Lost**: `pnl = −(contracts × price) / 100`
5. Write `status='settled'`, `pnl`, and `settled_at` back to the DB

This approach requires only one API call regardless of how many filled trades are open, and relies on Kalshi's own settlement records rather than polling individual market objects.

## DB Sync

`sync_trades_from_kalshi()` reconciles the local trade DB against Kalshi's order history via `/portfolio/orders`. It runs on the `kalshi_sync_interval` (default 30 minutes).

**Why this exists:** If the bot restarts mid-session, orders placed before the restart may not be in the local DB, or may be stuck at `status='pending'`. The sync catches both cases.

**Upsert logic (`sync_trade_from_order`):**

| Scenario | Action |
|----------|--------|
| `kalshi_order_id` not in DB | Insert new trade record |
| Status has advanced (e.g. `pending` → `filled`) | Update status |
| Status already at or past new value (e.g. already `settled`) | No-op |

Status ordering: `pending (0) < filled (1) < settled (2)`. Cancelled is treated as rank 1 (terminal, same as filled). The sync will never downgrade a `settled` trade back to `filled`.

**What can't be recovered:** The `game_id` field (which ESPN game triggered the trade) is only set at order placement time and is not stored in Kalshi. Synced-in orders will have a null `game_id`.

## Trade Side Determination

When an opportunity is detected, the strategy evaluates each matched Kalshi market to decide whether to buy **YES** or **NO**.

Kalshi game-winner tickers follow this format:

```
KXNBAGAME-26MAR25SASMEM-SAS
           └───────────┘ └─┘
             game pair    outcome team (YES = this team wins)
```

The trailing suffix after the last `-` is the team whose **YES** side you are buying. The strategy parses this suffix to determine the correct side:

- If the suffix matches the **leading team** → buy **YES**
- If the suffix matches the **other team** → buy **NO**

Both markets for a game (`-SAS` and `-MEM`) will produce a valid, equivalent trade signal. They both resolve to the same economic bet.

**ESPN → Kalshi abbreviation mapping:** ESPN uses different abbreviations for some teams (e.g. `SA` for the San Antonio Spurs, but Kalshi uses `SAS`). The strategy resolves these via `espn_abbrev_to_kalshi()` in `backend/scanner/matcher.py`, which mirrors the same mapping used by the frontend.

**Fallback:** If the ticker suffix can't be parsed as a team abbreviation (e.g. it's a date like `20260317`), the strategy falls back to the legacy assumption that YES = home team wins and logs a warning.

## Interval Configuration

All scan intervals are configurable at runtime via the Settings page without restarting the app. Changes take effect within one scan loop iteration.

See [configuration.md](configuration.md) for the full list of settings and their minimum values.
