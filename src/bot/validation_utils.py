import datetime
from typing import Optional


def validate_int(value: str, min_value: Optional[int] = None, max_value: Optional[int] = None) -> int | None:
    try:
        result = int(value)
        if min_value is not None and result < min_value:
            return None
        if max_value is not None and result > max_value:
            return None
        return result
    except Exception:
        return None


def validate_float(value: str, min_value: Optional[float] = None, max_value: Optional[float] = None) -> float | None:
    try:
        result = float(value.replace(",", "."))  # Handle comma as decimal separator
        if min_value is not None and result < min_value:
            return None
        if max_value is not None and result > max_value:
            return None
        return result
    except Exception:
        return None


def validate_date(value: str) -> datetime.date | None:
    try:
        return datetime.date.fromisoformat(value)
    except Exception:
        return None


def validate_date_not_in_past(value: str) -> datetime.date | None:
    """
    Validate that the date is not in the past.
    """
    try:
        d = datetime.date.fromisoformat(value)
        if d < datetime.date.today():
            raise ValueError("Date cannot be in the past")
        return d
    except Exception:
        return None


def validate_date_difference(start: str, end: str) -> bool:
    """
    Validate that the end date is not earlier than the start date.
    """
    try:
        start_date = datetime.date.fromisoformat(start)
        end_date = datetime.date.fromisoformat(end)
        return end_date >= start_date
    except Exception:
        return False


def validate_time_range(value: str) -> str | None:
    from src.medicover.watch import WatchTimeRange

    try:
        return str(WatchTimeRange(value))
    except Exception:
        return None


def validate_bool(value: str) -> bool | None:
    if value.lower() in ("yes", "true", "1", "y"):
        return True
    if value.lower() in ("no", "false", "0", "n"):
        return False
    return None


def validate_str(value: str | None, min_length: Optional[int] = None, max_length: Optional[int] = None) -> str | None:
    if not value or not value.strip():
        return None

    value = value.strip()
    if min_length is not None and len(value) < min_length:
        return None
    if max_length is not None and len(value) > max_length:
        return None

    return value


def validate_exclusions(value: str | None) -> str | None:
    """
    Validate exclusions format, e.g. "doctor:123,345;clinic:777,888".
    Returns the value if valid, None otherwise.
    """
    if not value:
        return None
    parts = value.split(";")
    for part in parts:
        if ":" not in part or len(part.split(":")) != 2:
            return None
        key, ids = part.split(":")
        if not ids or not all(validate_int(i) for i in ids.split(",")):
            return None
    return value.strip()
