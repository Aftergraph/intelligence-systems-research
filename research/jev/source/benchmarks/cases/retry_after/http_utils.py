def parse_retry_after(value: str | None) -> int | None:
    """Parse delta-seconds Retry-After. Invalid or negative values return None."""
    if value is None:
        return None
    return int(value)
