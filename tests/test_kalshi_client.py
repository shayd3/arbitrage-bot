"""Tests for backend/clients/kalshi.py — price parsing and order construction."""

from backend.clients.kalshi import _dollars_to_cents, _fp_to_int, _parse_market

# ---------------------------------------------------------------------------
# _dollars_to_cents
# ---------------------------------------------------------------------------


class TestDollarsToCents:
    def test_typical_yes_ask(self):
        assert _dollars_to_cents("0.8100") == 81

    def test_typical_no_ask(self):
        assert _dollars_to_cents("0.2000") == 20

    def test_min_price(self):
        assert _dollars_to_cents("0.0100") == 1

    def test_max_price(self):
        assert _dollars_to_cents("0.9900") == 99

    def test_full_dollar(self):
        assert _dollars_to_cents("1.0000") == 100

    def test_none_returns_none(self):
        assert _dollars_to_cents(None) is None

    def test_zero_string(self):
        assert _dollars_to_cents("0.0000") == 0

    def test_rounding(self):
        # Python uses banker's rounding: round(88.5) == 88 (round half to even)
        assert _dollars_to_cents("0.8850") == 88
        # round(87.5) == 88 (rounds up to even)
        assert _dollars_to_cents("0.8750") == 88

    def test_invalid_string_returns_none(self):
        assert _dollars_to_cents("not-a-number") is None


# ---------------------------------------------------------------------------
# _fp_to_int
# ---------------------------------------------------------------------------


class TestFpToInt:
    def test_typical_volume(self):
        assert _fp_to_int("73774.00") == 73774

    def test_typical_open_interest(self):
        assert _fp_to_int("59837.00") == 59837

    def test_zero(self):
        assert _fp_to_int("0.00") == 0

    def test_none_returns_none(self):
        assert _fp_to_int(None) is None

    def test_already_int(self):
        assert _fp_to_int("12345") == 12345

    def test_truncates_fractional(self):
        # int(float("1.9")) == 1 — we truncate, not round
        assert _fp_to_int("1.9") == 1

    def test_invalid_returns_none(self):
        assert _fp_to_int("bad") is None


# ---------------------------------------------------------------------------
# _parse_market — field mapping from Kalshi API response
# ---------------------------------------------------------------------------


class TestParseMarket:
    def _raw(self, **overrides) -> dict:
        base = {
            "ticker": "KXNBAGAME-26MAR17OKCORL-OKC",
            "title": "Oklahoma City at Orlando Winner?",
            "status": "active",
            "yes_ask_dollars": "0.8100",
            "yes_bid_dollars": "0.8000",
            "no_ask_dollars": "0.2000",
            "no_bid_dollars": "0.1900",
            "volume_fp": "73774.00",
            "open_interest_fp": "59837.00",
            "close_time": "2026-03-31T23:00:00Z",
        }
        base.update(overrides)
        return base

    def test_ticker_and_title(self):
        m = _parse_market(self._raw())
        assert m.ticker == "KXNBAGAME-26MAR17OKCORL-OKC"
        assert m.title == "Oklahoma City at Orlando Winner?"

    def test_status_preserved(self):
        m = _parse_market(self._raw())
        assert m.status == "active"

    def test_yes_ask_converted_to_cents(self):
        m = _parse_market(self._raw())
        assert m.yes_ask == 81

    def test_yes_bid_converted_to_cents(self):
        m = _parse_market(self._raw())
        assert m.yes_bid == 80

    def test_no_ask_converted_to_cents(self):
        m = _parse_market(self._raw())
        assert m.no_ask == 20

    def test_no_bid_converted_to_cents(self):
        m = _parse_market(self._raw())
        assert m.no_bid == 19

    def test_volume_parsed(self):
        m = _parse_market(self._raw())
        assert m.volume == 73774

    def test_open_interest_parsed(self):
        m = _parse_market(self._raw())
        assert m.open_interest == 59837

    def test_null_prices_become_none(self):
        raw = self._raw()
        raw.pop("yes_ask_dollars")
        raw.pop("yes_bid_dollars")
        m = _parse_market(raw)
        assert m.yes_ask is None
        assert m.yes_bid is None

    def test_missing_volume_becomes_none(self):
        raw = self._raw()
        raw.pop("volume_fp")
        m = _parse_market(raw)
        assert m.volume is None

    def test_result_parsed(self):
        m = _parse_market(self._raw(result="yes"))
        assert m.result == "yes"

    def test_result_no_parsed(self):
        m = _parse_market(self._raw(result="no"))
        assert m.result == "no"

    def test_result_absent_is_none(self):
        m = _parse_market(self._raw())
        assert m.result is None
