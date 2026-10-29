"""Date helpers for storing dates as ISO strings in MongoDB."""

from datetime import date, datetime


def to_iso_string(value):
    """Convert a date/datetime to an ISO date string; pass through others."""
    if value is None:
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    return value
