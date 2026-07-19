import os
from typing import Optional


def base_url() -> Optional[str]:
    """Return the fixture override used by CI, or production when unset."""
    return os.environ.get("OILPRICEAPI_BASE_URL")
