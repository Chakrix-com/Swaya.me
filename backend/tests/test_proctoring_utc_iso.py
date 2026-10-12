"""Event timestamps in the integrity report must carry an explicit UTC offset."""
from datetime import datetime, timezone, timedelta

from features.proctoring.proctoring_service_async import _utc_iso


def test_naive_datetime_is_marked_utc():
    assert _utc_iso(datetime(2026, 10, 12, 12, 23, 51)) == "2026-10-12T12:23:51+00:00"


def test_aware_datetime_keeps_its_offset():
    ist = timezone(timedelta(hours=5, minutes=30))
    assert _utc_iso(datetime(2026, 10, 12, 17, 53, 51, tzinfo=ist)) == "2026-10-12T17:53:51+05:30"


def test_none_passes_through():
    assert _utc_iso(None) is None
