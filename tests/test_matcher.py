"""Tests for backend/scanner/matcher.py — game-to-market matching."""
import pytest
from backend.models import Game, GameStatus, KalshiMarket, Sport, Team
from backend.scanner.matcher import (
    normalize_team_name,
    team_to_kalshi_abbrev,
    _ticker_contains_team,
    match_game_to_markets,
    GameMarketMatch,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_game(
    home_name="Los Angeles Lakers", home_abbrev="LAL",
    away_name="Boston Celtics", away_abbrev="BOS",
    sport=Sport.NBA,
) -> Game:
    return Game(
        id="g1", sport=sport,
        home_team=Team(id="h", name=home_name, abbreviation=home_abbrev, score=0),
        away_team=Team(id="a", name=away_name, abbreviation=away_abbrev, score=0),
        status=GameStatus.IN_PROGRESS,
    )


def make_market(ticker="KXNBA-LAL-BOS-20260317", status="open") -> KalshiMarket:
    return KalshiMarket(ticker=ticker, title="Lakers vs Celtics", status=status,
                        yes_ask=80, no_ask=22)


# ---------------------------------------------------------------------------
# normalize_team_name
# ---------------------------------------------------------------------------

class TestNormalizeTeamName:
    def test_lowercases(self):
        assert normalize_team_name("Boston Celtics") == "boston celtics"

    def test_strips_whitespace(self):
        assert normalize_team_name("  Lakers  ") == "lakers"

    def test_already_lower(self):
        assert normalize_team_name("heat") == "heat"


# ---------------------------------------------------------------------------
# team_to_kalshi_abbrev
# ---------------------------------------------------------------------------

class TestTeamToKalshiAbbrev:
    def test_full_name(self):
        assert team_to_kalshi_abbrev("Los Angeles Lakers") == "LAL"

    def test_nickname_only(self):
        assert team_to_kalshi_abbrev("lakers") == "LAL"

    def test_case_insensitive(self):
        assert team_to_kalshi_abbrev("BOSTON CELTICS") == "BOS"

    def test_unknown_team_returns_none(self):
        assert team_to_kalshi_abbrev("Springfield Isotopes") is None

    def test_alias_variant(self):
        assert team_to_kalshi_abbrev("cavs") == "CLE"
        assert team_to_kalshi_abbrev("sixers") == "PHI"
        assert team_to_kalshi_abbrev("twolves") == "MIN"


# ---------------------------------------------------------------------------
# _ticker_contains_team
# ---------------------------------------------------------------------------

class TestTickerContainsTeam:
    def test_match_with_dash(self):
        assert _ticker_contains_team("KXNBA-LAL-BOS", "LAL") is True

    def test_match_case_insensitive(self):
        assert _ticker_contains_team("kxnba-lal-bos", "LAL") is True

    def test_no_match(self):
        assert _ticker_contains_team("KXNBA-BOS-MIA", "LAL") is False

    def test_partial_match_not_confused(self):
        # "MIA" should not match a ticker containing "MIAMI" substring oddly placed
        assert _ticker_contains_team("KXNBA-MIADAL", "DAL") is True


# ---------------------------------------------------------------------------
# match_game_to_markets
# ---------------------------------------------------------------------------

class TestMatchGameToMarkets:
    def test_matching_by_alias(self):
        game = make_game()
        markets = [make_market("KXNBA-LAL-BOS-20260317")]
        result = match_game_to_markets(game, markets)
        assert len(result) == 1
        assert result[0].ticker == "KXNBA-LAL-BOS-20260317"

    def test_closed_market_excluded(self):
        game = make_game()
        markets = [make_market("KXNBA-LAL-BOS-20260317", status="closed")]
        result = match_game_to_markets(game, markets)
        assert result == []

    def test_wrong_sport_excluded(self):
        game = make_game(sport=Sport.NBA)
        # NFL ticker should not match an NBA game
        markets = [make_market("KXNFL-LAL-BOS-20260317")]
        result = match_game_to_markets(game, markets)
        assert result == []

    def test_match_via_espn_abbreviation(self):
        """If alias lookup fails, ESPN abbreviation is also tried."""
        game = make_game(home_name="Unknown Team", home_abbrev="UNK",
                         away_name="Boston Celtics", away_abbrev="BOS")
        markets = [make_market("KXNBA-UNK-BOS-20260317")]
        result = match_game_to_markets(game, markets)
        assert len(result) == 1

    def test_multiple_markets_returned(self):
        game = make_game()
        markets = [
            make_market("KXNBA-LAL-BOS-Q4"),
            make_market("KXNBA-LAL-BOS-TOTAL"),
            make_market("KXNBA-MIA-CHI-20260317"),  # different game
        ]
        result = match_game_to_markets(game, markets)
        assert len(result) == 2
        tickers = {m.ticker for m in result}
        assert "KXNBA-LAL-BOS-Q4" in tickers
        assert "KXNBA-LAL-BOS-TOTAL" in tickers

    def test_no_team_in_ticker_excluded(self):
        game = make_game()
        markets = [make_market("KXNBA-NOTATEAM-20260317")]
        result = match_game_to_markets(game, markets)
        assert result == []


# ---------------------------------------------------------------------------
# GameMarketMatch
# ---------------------------------------------------------------------------

class TestGameMarketMatch:
    def _make_match(self, home_score, away_score, home_team_wins, yes_ask=80, no_ask=22):
        game = Game(
            id="g", sport=Sport.NBA,
            home_team=Team(id="h", name="Lakers", abbreviation="LAL", score=home_score),
            away_team=Team(id="a", name="Celtics", abbreviation="BOS", score=away_score),
            status=GameStatus.IN_PROGRESS,
        )
        market = KalshiMarket(ticker="KXNBA-LAL", title="t", status="open",
                              yes_ask=yes_ask, no_ask=no_ask)
        return GameMarketMatch(game, market, home_team_wins)

    def test_home_leading_home_is_yes(self):
        m = self._make_match(110, 90, home_team_wins=True)
        assert m.leading_team_yes_price == 80  # YES = home = leading

    def test_home_leading_home_is_no(self):
        m = self._make_match(110, 90, home_team_wins=False)
        assert m.leading_team_yes_price == 22  # leading team is NO

    def test_away_leading_home_is_yes(self):
        m = self._make_match(80, 110, home_team_wins=True)
        assert m.leading_team_yes_price == 22  # leading = away = NO

    def test_lead_calculation(self):
        m = self._make_match(110, 95, home_team_wins=True)
        assert m.lead == 15

    def test_lead_always_positive(self):
        m = self._make_match(80, 110, home_team_wins=True)
        assert m.lead == 30
