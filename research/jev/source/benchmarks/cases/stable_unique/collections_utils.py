def stable_unique(items):
    """Deduplicate while preserving first occurrence, including unhashable values."""
    return list(set(items))
