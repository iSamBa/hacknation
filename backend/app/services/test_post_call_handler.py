from app.services.post_call_handler import parse_slot


class TestParseSlot:
    def test_none_input(self):
        assert parse_slot(None) is None

    def test_empty_string(self):
        assert parse_slot("") is None

    def test_whitespace_only(self):
        assert parse_slot("   ") is None

    def test_iso_format(self):
        result = parse_slot("2026-02-10T14:00:00")
        assert result is not None
        assert result.month == 2
        assert result.day == 10
        assert result.hour == 14

    def test_natural_date_with_time(self):
        result = parse_slot("February 10th at 14:00")
        assert result is not None
        assert result.month == 2
        assert result.day == 10
        assert result.hour == 14

    def test_day_and_time(self):
        result = parse_slot("Tuesday 2pm")
        assert result is not None
        assert result.hour == 14

    def test_unparseable_returns_none(self):
        assert parse_slot("not a date at all xyz") is None
