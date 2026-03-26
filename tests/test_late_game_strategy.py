"""Tests for backend/strategy/late_game.py — LateGameStrategy."""

from unittest.mock import AsyncMock, patch

from backend.models import Game, GameClock, GameStatus, KalshiMarket, Sport, Team
from backend.scanner.sports import SPORT_CONFIGS
from backend.strategy.late_game import LateGameStrategy

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_game(
    home_score=110,
    away_score=90,
    status=GameStatus.IN_PROGRESS,
    period=4,
    seconds_remaining=120.0,
    sport=Sport.NBA,
    home_name="Los Angeles Lakers",
    home_abbrev="LAL",
    away_name="Boston Celtics",
    away_abbrev="BOS",
) -> Game:
    return Game(
        id="game-1",
        sport=sport,
        home_team=Team(id="h", name=home_name, abbreviation=home_abbrev, score=home_score),
        away_team=Team(id="a", name=away_name, abbreviation=away_abbrev, score=away_score),
        status=status,
        clock=GameClock(
            period=period,
            period_type="regular",
            display_clock="2:00",
            seconds_remaining=seconds_remaining,
        )
        if status == GameStatus.IN_PROGRESS
        else None,
    )


def make_market(yes_ask=90, no_ask=12, status="open", ticker="KXNBAGAME-26MAR25LALBOS-LAL") -> KalshiMarket:
    return KalshiMarket(
        ticker=ticker,
        title="Lakers to win",
        status=status,
        yes_ask=yes_ask,
        no_ask=no_ask,
    )


NBA_CONFIG = SPORT_CONFIGS[Sport.NBA]

strategy = LateGameStrategy()


def patch_max_dollars(dollars=200.0):
    # get_max_position_dollars is imported lazily inside evaluate(), so patch at source
    return patch(
        "backend.execution.risk.get_max_position_dollars",
        new=AsyncMock(return_value=dollars),
    )


# ---------------------------------------------------------------------------
# Rejection cases
# ---------------------------------------------------------------------------


class TestLateGameRejections:
    async def test_game_not_in_progress(self):
        game = make_game(status=GameStatus.FINAL)
        game.clock = None
        market = make_market()
        with patch(
            "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert not signal.should_trade
        assert "not in progress" in signal.reason

    async def test_no_clock_data(self):
        game = make_game()
        game.clock = None
        market = make_market()
        with patch(
            "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert not signal.should_trade
        assert "clock" in signal.reason.lower()

    async def test_lead_below_threshold(self):
        # NBA min_lead = 15; give a lead of 5
        game = make_game(home_score=100, away_score=96)
        market = make_market()
        with patch(
            "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert not signal.should_trade
        assert "Lead" in signal.reason

    async def test_no_yes_ask_price(self):
        game = make_game()
        market = make_market(yes_ask=None)
        with patch(
            "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert not signal.should_trade
        assert "YES ask" in signal.reason

    async def test_price_below_min_yes_price(self):
        # NBA min_yes_price = 88; give 80¢ YES ask
        game = make_game()
        market = make_market(yes_ask=80)
        with patch(
            "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert not signal.should_trade
        assert "min" in signal.reason

    async def test_spread_too_small(self):
        # Price 90¢ → spread = 10¢ < 12¢ minimum
        game = make_game()
        market = make_market(yes_ask=90)
        with patch(
            "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert not signal.should_trade
        assert "Spread" in signal.reason


# ---------------------------------------------------------------------------
# Trade signals
# ---------------------------------------------------------------------------


class TestLateGameTradeSignals:
    async def test_home_leading_buys_yes(self):
        # LAL (home) leading — market ticker ends in -LAL, so YES = LAL wins → buy YES
        game = make_game(home_score=110, away_score=90)
        market = make_market(yes_ask=88, ticker="KXNBAGAME-26MAR25LALBOS-LAL")
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.should_trade
        assert signal.side == "yes"
        assert signal.price == 88
        assert signal.contracts >= 1

    async def test_away_leading_buys_no(self):
        # BOS (away) leading — market ticker ends in -LAL (home), so YES = LAL wins → buy NO
        game = make_game(home_score=80, away_score=100)
        market = make_market(yes_ask=15, no_ask=88, ticker="KXNBAGAME-26MAR25LALBOS-LAL")
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.should_trade
        assert signal.side == "no"
        assert signal.price == 88

    async def test_away_leading_buys_yes_on_away_market(self):
        # BOS (away) leading — market ticker ends in -BOS, so YES = BOS wins → buy YES
        game = make_game(home_score=80, away_score=100)
        market = make_market(yes_ask=88, no_ask=15, ticker="KXNBAGAME-26MAR25LALBOS-BOS")
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.should_trade
        assert signal.side == "yes"
        assert signal.price == 88

    async def test_home_leading_buys_no_on_away_market(self):
        # LAL (home) leading — market ticker ends in -BOS (away), so YES = BOS wins → buy NO
        game = make_game(home_score=110, away_score=90)
        market = make_market(yes_ask=15, no_ask=88, ticker="KXNBAGAME-26MAR25LALBOS-BOS")
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.should_trade
        assert signal.side == "no"
        assert signal.price == 88

    async def test_espn_abbrev_mismatch_sa_vs_sas(self):
        # SA (ESPN) → SAS (Kalshi). Ticker ends in -SAS. SA is away and leading → buy YES.
        game = make_game(
            home_score=87, away_score=115,
            home_name="Memphis Grizzlies", home_abbrev="MEM",
            away_name="San Antonio Spurs", away_abbrev="SA",
        )
        market = make_market(yes_ask=88, no_ask=15, ticker="KXNBAGAME-26MAR25SASMEM-SAS")
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.should_trade
        assert signal.side == "yes"
        assert signal.price == 88

    async def test_fallback_when_ticker_unparseable(self):
        # Ticker last segment is a date — outcome_team_from_ticker returns None → fallback
        # Home (LAL) is leading, so fallback still buys YES
        game = make_game(home_score=110, away_score=90)
        market = make_market(yes_ask=88, ticker="KXNBA-LAL-20260317")
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.should_trade
        assert signal.side == "yes"

    async def test_contracts_sized_to_max_dollars(self):
        # max $200, price 88¢ → floor(200*100/88) = 227 contracts
        game = make_game()
        market = make_market(yes_ask=88)
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value=None)
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.contracts == int(200 * 100 / 88)

    async def test_min_yes_price_db_override(self):
        """A DB override for min_yes_price should be respected."""
        game = make_game()
        # YES ask 80¢ is normally below NBA's 88¢ min — but if override is 75, it should pass
        market = make_market(yes_ask=80)
        with (
            patch(
                "backend.strategy.late_game.get_config_override", new=AsyncMock(return_value="75")
            ),
            patch_max_dollars(200.0),
        ):
            signal = await strategy.evaluate(game, market, NBA_CONFIG)
        assert signal.should_trade
        assert signal.price == 80


# ---------------------------------------------------------------------------
# _size_position unit tests
# ---------------------------------------------------------------------------


class TestSizePosition:
    def test_basic_sizing(self):
        # $100 max, 50¢ price → 200 contracts
        assert strategy._size_position(50, 100.0) == 200

    def test_minimum_one_contract(self):
        # Tiny max but nonzero → at least 1
        assert strategy._size_position(99, 0.01) == 1

    def test_zero_price_returns_zero(self):
        assert strategy._size_position(0, 100.0) == 0

    def test_zero_max_dollars_returns_zero(self):
        assert strategy._size_position(80, 0.0) == 0

    def test_floor_division(self):
        # $10 max, 30¢ price → floor(1000/30) = 33 contracts
        assert strategy._size_position(30, 10.0) == 33
