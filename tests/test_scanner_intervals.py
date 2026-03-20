"""Tests for dynamic scanner interval configuration in ScannerEngine._refresh_intervals."""

import json
from unittest.mock import AsyncMock, patch

from backend.config import settings
from backend.scanner.engine import ScannerEngine


class TestRefreshIntervals:
    async def test_defaults_when_no_override(self):
        engine = ScannerEngine()
        with patch("backend.scanner.engine.get_config_override", new=AsyncMock(return_value=None)):
            await engine._refresh_intervals()
        assert engine._espn_interval == settings.espn_poll_interval
        assert engine._kalshi_interval == settings.kalshi_poll_interval
        assert engine._sync_interval == 1800.0

    async def test_overrides_apply(self):
        engine = ScannerEngine()
        override = json.dumps(
            {
                "espn_poll_interval": 20.0,
                "kalshi_poll_interval": 30.0,
                "kalshi_sync_interval": 600.0,
            }
        )
        with patch(
            "backend.scanner.engine.get_config_override", new=AsyncMock(return_value=override)
        ):
            await engine._refresh_intervals()
        assert engine._espn_interval == 20.0
        assert engine._kalshi_interval == 30.0
        assert engine._sync_interval == 600.0

    async def test_partial_override_only_updates_present_keys(self):
        engine = ScannerEngine()
        override = json.dumps({"espn_poll_interval": 25.0})
        with patch(
            "backend.scanner.engine.get_config_override", new=AsyncMock(return_value=override)
        ):
            await engine._refresh_intervals()
        assert engine._espn_interval == 25.0
        assert engine._kalshi_interval == settings.kalshi_poll_interval
        assert engine._sync_interval == 1800.0

    async def test_espn_floor_enforced(self):
        engine = ScannerEngine()
        override = json.dumps({"espn_poll_interval": 2.0})  # below 5s minimum
        with patch(
            "backend.scanner.engine.get_config_override", new=AsyncMock(return_value=override)
        ):
            await engine._refresh_intervals()
        assert engine._espn_interval == 5.0

    async def test_kalshi_floor_enforced(self):
        engine = ScannerEngine()
        override = json.dumps({"kalshi_poll_interval": 3.0})  # below 10s minimum
        with patch(
            "backend.scanner.engine.get_config_override", new=AsyncMock(return_value=override)
        ):
            await engine._refresh_intervals()
        assert engine._kalshi_interval == 10.0

    async def test_sync_floor_enforced(self):
        engine = ScannerEngine()
        override = json.dumps({"kalshi_sync_interval": 10.0})  # below 30s minimum
        with patch(
            "backend.scanner.engine.get_config_override", new=AsyncMock(return_value=override)
        ):
            await engine._refresh_intervals()
        assert engine._sync_interval == 30.0

    async def test_invalid_json_leaves_current_values(self):
        engine = ScannerEngine()
        engine._espn_interval = 12.0
        engine._kalshi_interval = 25.0
        with patch(
            "backend.scanner.engine.get_config_override", new=AsyncMock(return_value="not-json")
        ):
            await engine._refresh_intervals()
        assert engine._espn_interval == 12.0
        assert engine._kalshi_interval == 25.0

    async def test_floor_at_exact_minimum(self):
        engine = ScannerEngine()
        override = json.dumps(
            {
                "espn_poll_interval": 5.0,
                "kalshi_poll_interval": 10.0,
                "kalshi_sync_interval": 30.0,
            }
        )
        with patch(
            "backend.scanner.engine.get_config_override", new=AsyncMock(return_value=override)
        ):
            await engine._refresh_intervals()
        assert engine._espn_interval == 5.0
        assert engine._kalshi_interval == 10.0
        assert engine._sync_interval == 30.0
