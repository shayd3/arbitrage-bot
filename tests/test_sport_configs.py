"""Tests for backend/scanner/sports.py — sport config and DB overrides."""

import json
from unittest.mock import AsyncMock, patch

from backend.models import Sport
from backend.scanner.sports import SPORT_CONFIGS, SPORT_SERIES_TICKER, get_sport_config


class TestSportConfigDefaults:
    async def test_nba_defaults(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=None)):
            cfg = await get_sport_config(Sport.NBA)
        assert cfg.final_period == 4
        assert cfg.final_period_window == 300.0
        assert cfg.min_lead == 15
        assert cfg.min_yes_price == 88
        assert cfg.poll_interval == 10.0

    async def test_nhl_defaults(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=None)):
            cfg = await get_sport_config(Sport.NHL)
        assert cfg.final_period == 3
        assert cfg.min_lead == 3

    async def test_mlb_defaults(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=None)):
            cfg = await get_sport_config(Sport.MLB)
        assert cfg.final_period == 9
        assert cfg.final_period_window == 0.0

    async def test_nfl_defaults(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=None)):
            cfg = await get_sport_config(Sport.NFL)
        assert cfg.final_period == 4
        assert cfg.min_lead == 14

    async def test_all_sports_have_config(self):
        for sport in Sport:
            assert sport in SPORT_CONFIGS, f"Missing config for {sport}"


class TestSportConfigOverrides:
    async def test_db_override_applied(self):
        override = json.dumps({"min_lead": 7, "min_yes_price": 75})
        with patch("backend.db.get_config_override", new=AsyncMock(return_value=override)):
            cfg = await get_sport_config(Sport.NBA)
        assert cfg.min_lead == 7
        assert cfg.min_yes_price == 75
        # Non-overridden fields keep defaults
        assert cfg.final_period == 4
        assert cfg.poll_interval == 10.0

    async def test_invalid_json_falls_back_to_defaults(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value="not-json")):
            cfg = await get_sport_config(Sport.NBA)
        assert cfg.min_lead == SPORT_CONFIGS[Sport.NBA].min_lead

    async def test_empty_override_object_keeps_defaults(self):
        with patch("backend.db.get_config_override", new=AsyncMock(return_value="{}")):
            cfg = await get_sport_config(Sport.NBA)
        default = SPORT_CONFIGS[Sport.NBA]
        assert cfg.min_lead == default.min_lead
        assert cfg.min_yes_price == default.min_yes_price

    async def test_override_uses_correct_key(self):
        """Verify the DB is queried with the right key for each sport."""
        for sport in Sport:
            expected_key = f"sport_config_{sport.value}"
            mock = AsyncMock(return_value=None)
            with patch("backend.db.get_config_override", new=mock):
                await get_sport_config(sport)
            mock.assert_called_once_with(expected_key)


class TestSportSeriesTicker:
    def test_all_sports_have_series_ticker(self):
        for sport in Sport:
            assert sport in SPORT_SERIES_TICKER, f"Missing series ticker for {sport}"

    def test_nba_series_ticker(self):
        assert SPORT_SERIES_TICKER[Sport.NBA] == "KXNBAGAME"

    def test_nfl_series_ticker(self):
        assert SPORT_SERIES_TICKER[Sport.NFL] == "KXNFLGAME"

    def test_nhl_series_ticker(self):
        assert SPORT_SERIES_TICKER[Sport.NHL] == "KXNHLGAME"

    def test_mlb_series_ticker(self):
        assert SPORT_SERIES_TICKER[Sport.MLB] == "KXMLBGAME"
