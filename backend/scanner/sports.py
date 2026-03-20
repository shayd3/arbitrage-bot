from dataclasses import dataclass

from backend.models import Sport

# Kalshi series ticker for game winner markets per sport
SPORT_SERIES_TICKER: dict[Sport, str] = {
    Sport.NBA: "KXNBAGAME",
    Sport.NFL: "KXNFLGAME",
    Sport.NHL: "KXNHLGAME",
    Sport.MLB: "KXMLBGAME",
    Sport.WNBA: "KXWNBAGAME",
    Sport.CBB: "KXCBBGAME",
}


@dataclass
class SportConfig:
    sport: Sport
    final_period: int  # Last regular period number
    final_period_window: float  # Seconds remaining threshold
    min_lead: int  # Points/goals/runs required
    min_yes_price: int  # Minimum YES price in cents
    poll_interval: float  # ESPN poll interval in seconds
    regular_periods: int = 4  # Periods before overtime
    clock_based: bool = True  # False for MLB (innings, no game clock)


SPORT_CONFIGS: dict[Sport, SportConfig] = {
    Sport.NBA: SportConfig(
        sport=Sport.NBA,
        final_period=4,
        final_period_window=300.0,  # 5 minutes
        min_lead=15,
        min_yes_price=88,
        poll_interval=10.0,
        regular_periods=4,
        clock_based=True,
    ),
    Sport.NFL: SportConfig(
        sport=Sport.NFL,
        final_period=4,
        final_period_window=300.0,  # 5 minutes
        min_lead=14,
        min_yes_price=88,
        poll_interval=30.0,
        regular_periods=4,
        clock_based=True,
    ),
    Sport.NHL: SportConfig(
        sport=Sport.NHL,
        final_period=3,
        final_period_window=300.0,  # 5 minutes
        min_lead=3,
        min_yes_price=88,
        poll_interval=15.0,
        regular_periods=3,
        clock_based=True,
    ),
    Sport.MLB: SportConfig(
        sport=Sport.MLB,
        final_period=9,
        final_period_window=0.0,  # No game clock; gate triggers at final_period (9th inning)
        min_lead=5,
        min_yes_price=88,
        poll_interval=20.0,
        regular_periods=9,
        clock_based=False,
    ),
    Sport.WNBA: SportConfig(
        sport=Sport.WNBA,
        final_period=4,
        final_period_window=300.0,  # 5 minutes
        min_lead=15,
        min_yes_price=88,
        poll_interval=10.0,
        regular_periods=4,
        clock_based=True,
    ),
    Sport.CBB: SportConfig(
        sport=Sport.CBB,
        final_period=2,
        final_period_window=300.0,  # 5 minutes
        min_lead=15,
        min_yes_price=88,
        poll_interval=10.0,
        regular_periods=2,
        clock_based=True,
    ),
}


async def get_sport_config(sport: Sport) -> SportConfig:
    """Get sport config, applying any DB overrides."""
    import json

    from backend.db import get_config_override

    config = SPORT_CONFIGS.get(sport)
    if config is None:
        raise ValueError(f"No config for sport: {sport}")

    # Check for runtime overrides
    override_key = f"sport_config_{sport.value}"
    override_json = await get_config_override(override_key)
    if override_json:
        try:
            overrides = json.loads(override_json)
            return SportConfig(
                sport=sport,
                final_period=overrides.get("final_period", config.final_period),
                final_period_window=overrides.get(
                    "final_period_window", config.final_period_window
                ),
                min_lead=overrides.get("min_lead", config.min_lead),
                min_yes_price=overrides.get("min_yes_price", config.min_yes_price),
                poll_interval=overrides.get("poll_interval", config.poll_interval),
                regular_periods=overrides.get("regular_periods", config.regular_periods),
                clock_based=overrides.get("clock_based", config.clock_based),
            )
        except (json.JSONDecodeError, KeyError):
            pass

    return config
