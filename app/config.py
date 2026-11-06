import os

class Config:
    # Server configuration
    PORT = int(os.environ.get("PORT", 8080))
    HOST = os.environ.get("HOST", "0.0.0.0")
    DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1")

    # Nominatim Upstream Configuration
    # Theo Bảng 8: Cấu hình HTTP client gọi Nominatim
    NOMINATIM_BASE_URL = os.environ.get("NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org").rstrip("/")
    USER_AGENT = os.environ.get(
        "NOMINATIM_USER_AGENT",
        "MidSoftware-GeoPOC/0.1 (contact: contact@midsoftware.com)"
    )
    
    # Timeouts
    CONNECT_TIMEOUT_SEC = float(os.environ.get("CONNECT_TIMEOUT_SEC", 3.0))
    READ_TIMEOUT_SEC = float(os.environ.get("READ_TIMEOUT_SEC", 8.0))

    # Rate Limiting & Resilience
    # Chính sách Nominatim OSM: Tối đa 1 request/giây
    RATE_LIMIT_RPS = float(os.environ.get("RATE_LIMIT_RPS", 1.0))
    RATE_LIMIT_MIN_INTERVAL = 1.0 / RATE_LIMIT_RPS  # 1.0 second between requests
    
    # Circuit Breaker for 429
    CIRCUIT_BREAKER_DEFAULT_COOLDOWN_SEC = int(os.environ.get("CIRCUIT_BREAKER_COOLDOWN_SEC", 60))
    MAX_RETRIES_5XX = 2
    MAX_RETRIES_TIMEOUT = 1
    INITIAL_BACKOFF_SEC = 1.0

    # Cache TTL (Time to Live)
    CACHE_TTL_POSITIVE_SEC = int(os.environ.get("CACHE_TTL_POSITIVE_SEC", 3600))  # 1 hour
    CACHE_TTL_NEGATIVE_SEC = int(os.environ.get("CACHE_TTL_NEGATIVE_SEC", 60))    # 60 seconds (empty search / 404 reverse)

    # Defaults & Validation limits
    SEARCH_DEFAULT_LIMIT = 5
    SEARCH_MIN_LIMIT = 1
    SEARCH_MAX_LIMIT = 10
    
    REVERSE_DEFAULT_ZOOM = 18
    REVERSE_MIN_ZOOM = 3
    REVERSE_MAX_ZOOM = 18

    DEFAULT_LANG = "vi"
    ALLOWED_LANGS = ["vi", "en", "fr", "de", "ja", "zh", "ru"]
    DEFAULT_COUNTRY = "vn"

    # Offline / Mock Fallback toggle
    ENABLE_OFFLINE_MOCK_FALLBACK = os.environ.get("ENABLE_OFFLINE_MOCK_FALLBACK", "True").lower() in ("true", "1")

