"""Shared pagination validation for public SDK helpers."""

MIN_PAGE_SIZE = 1
MAX_PAGE_SIZE = 1000


def validate_page_size(per_page: int) -> int:
    """Return a valid API page size or fail before making a request."""
    if (
        isinstance(per_page, bool)
        or not isinstance(per_page, int)
        or not MIN_PAGE_SIZE <= per_page <= MAX_PAGE_SIZE
    ):
        raise ValueError(f"per_page must be an integer between {MIN_PAGE_SIZE} and {MAX_PAGE_SIZE}")
    return per_page
