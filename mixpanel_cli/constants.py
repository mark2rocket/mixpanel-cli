"""공통 상수 정의."""

REGION_URLS: dict[str, dict[str, str]] = {
    "us": {
        "api": "https://mixpanel.com",
        "data": "https://data.mixpanel.com",
        "ingestion": "https://api.mixpanel.com",
    },
    "eu": {
        "api": "https://eu.mixpanel.com",
        "data": "https://eu.data.mixpanel.com",
        "ingestion": "https://api-eu.mixpanel.com",
    },
    "in": {
        "api": "https://in.mixpanel.com",
        "data": "https://in.data.mixpanel.com",
        "ingestion": "https://api-in.mixpanel.com",
    },
}

DEFAULT_TIMEOUT = 30
DEFAULT_EXPORT_CHUNK_DAYS = 30
EVENTS_CACHE_TTL = 3600  # seconds

PROFILES_PATH_DEFAULT = "~/.mixpanel/profiles.json"
HISTORY_PATH_DEFAULT = "~/.mixpanel/history"
CACHE_DIR_DEFAULT = "~/.mixpanel/cache"

KEYRING_SERVICE = "mixpanel-cli"
