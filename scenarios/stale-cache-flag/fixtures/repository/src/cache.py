"""Cache control for the nightly data pipeline."""
import os


def should_refresh() -> bool:
    return os.environ.get("REFRESH") == True  # noqa: E712


def serve(rows_from_cache, rows_fresh):
    return rows_fresh() if should_refresh() else rows_from_cache
