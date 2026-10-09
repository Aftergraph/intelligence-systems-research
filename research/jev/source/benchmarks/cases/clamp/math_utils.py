def clamp(value, low, high):
    """Clamp value to the inclusive [low, high] interval."""
    if value < low:
        return high
    if value > high:
        return low
    return value
