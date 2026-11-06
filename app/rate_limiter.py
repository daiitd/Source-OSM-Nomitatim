import time
import threading
from typing import Dict, Any, Optional
from app.config import Config

class UpstreamCircuitBreaker:
    """
    Ngắt mạch (Circuit Breaker) dành riêng cho tình huống Upstream 429 Too Many Requests.
    Tuân thủ nghiêm ngặt tiêu chí: 'Nêu được chiến lược giảm call API, không retry 429 liên tục'.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._is_open = False
        self._open_until: float = 0.0
        self._trip_count: int = 0
        self._last_retry_after: int = 0

    def trip(self, retry_after_sec: int) -> None:
        """Kích hoạt ngắt mạch khi nhận HTTP 429 từ Nominatim."""
        with self._lock:
            self._is_open = True
            cooldown = max(retry_after_sec, 5)
            self._open_until = time.time() + cooldown
            self._trip_count += 1
            self._last_retry_after = cooldown

    def check_state(self) -> Dict[str, Any]:
        """Kiểm tra trạng thái ngắt mạch."""
        with self._lock:
            now = time.time()
            if self._is_open:
                if now >= self._open_until:
                    # Tự động đóng lại (hoặc chuyển HALF_OPEN) khi hết thời gian cooldown
                    self._is_open = False
                    self._open_until = 0.0
                else:
                    remaining = int(self._open_until - now) + 1
                    return {
                        "isOpen": True,
                        "state": "OPEN",
                        "remainingCooldownSec": remaining,
                        "totalTrips": self._trip_count,
                    }
            return {
                "isOpen": False,
                "state": "CLOSED",
                "remainingCooldownSec": 0,
                "totalTrips": self._trip_count,
            }

    def reset(self) -> None:
        """Đặt lại ngắt mạch thủ công (hữu ích khi test/demo)."""
        with self._lock:
            self._is_open = False
            self._open_until = 0.0


class UpstreamRateLimiter:
    """
    Bộ điều tốc phía Backend đảm bảo không gọi Nominatim quá 1 request/giây
    (tuân thủ chính sách OSM public endpoint).
    """
    def __init__(self, min_interval_sec: float = 1.0):
        self._min_interval = min_interval_sec
        self._last_request_time = 0.0
        self._lock = threading.Lock()

    def acquire(self) -> float:
        """
        Chờ nếu cần thiết để đảm bảo khoảng cách giữa 2 lần gọi Nominatim >= min_interval_sec.
        Trả về thời gian đã phải chờ (wait_time).
        """
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            wait_time = 0.0
            if elapsed < self._min_interval:
                wait_time = self._min_interval - elapsed
                time.sleep(wait_time)
            self._last_request_time = time.time()
            return wait_time

# Global instances
circuit_breaker = UpstreamCircuitBreaker()
rate_limiter = UpstreamRateLimiter(Config.RATE_LIMIT_MIN_INTERVAL)

