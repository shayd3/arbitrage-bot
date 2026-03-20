from prometheus_client import Counter, Gauge, Histogram

scanner_cycles_total = Counter(
    "scanner_cycles_total",
    "Total number of scanner cycles completed",
)

opportunities_found_total = Counter(
    "opportunities_found_total",
    "Total arbitrage opportunities detected",
    ["sport"],
)

trades_placed_total = Counter(
    "trades_placed_total",
    "Total trades successfully placed",
)

trades_rejected_total = Counter(
    "trades_rejected_total",
    "Total trades rejected by risk checks",
    ["reason"],
)

active_positions = Gauge(
    "active_positions",
    "Number of currently open positions",
)

daily_pnl = Gauge(
    "daily_pnl",
    "Realized P&L for the current day in dollars",
)

available_balance = Gauge(
    "available_balance",
    "Available account balance in dollars",
)

espn_poll_latency_seconds = Histogram(
    "espn_poll_latency_seconds",
    "Latency of ESPN scoreboard API calls in seconds",
    ["sport"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

kalshi_api_latency_seconds = Histogram(
    "kalshi_api_latency_seconds",
    "Latency of Kalshi API calls in seconds",
    ["endpoint"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)
