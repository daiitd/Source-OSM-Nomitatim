import time
import threading
from typing import Any, Optional, Tuple, Dict
from app.config import Config

class TTLCache:
    """
    Bộ nhớ đệm trong RAM với cơ chế hết hạn (TTL) và thống kê Hit/Miss.
    Hỗ trợ cả positive cache (1h) và negative cache (60s) theo thiết kế Mục 5.2.
    """
    def __init__(self):
        self._lock = threading.Lock()
        self._store: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expire_at)
        self._hits: int = 0
        self._misses: int = 0

    def get(self, key: str) -> Tuple[Optional[Any], bool]:
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return None, False

            value, expire_at = self._store[key]
            if time.time() > expire_at:
                del self._store[key]
                self._misses += 1
                return None, False

            self._hits += 1
            return value, True

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else Config.CACHE_TTL_POSITIVE_SEC
        expire_at = time.time() + ttl
        with self._lock:
            self._store[key] = (value, expire_at)

    def delete(self, key: str) -> None:
        with self._lock:
            self._store.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            # Dọn dẹp các key đã hết hạn để đếm chính xác
            now = time.time()
            active_keys = [k for k, (_, exp) in self._store.items() if exp > now]
            total_requests = self._hits + self._misses
            hit_ratio = round((self._hits / total_requests * 100), 2) if total_requests > 0 else 0.0

            return {
                "activeEntries": len(active_keys),
                "totalHits": self._hits,
                "totalMisses": self._misses,
                "hitRatioPercent": hit_ratio,
            }

    @staticmethod
    def make_search_key(q: str, limit: int, lang: str, country: str) -> str:
        # Chuẩn hóa viết thường, bỏ dấu cách thừa
        clean_q = " ".join(q.lower().split())
        return f"search:{clean_q}:{limit}:{lang.lower()}:{country.lower()}"

    @staticmethod
    def make_reverse_key(lat: float, lon: float, zoom: int, lang: str) -> str:
        # Làm tròn 5 chữ số thập phân (độ chính xác ~1.1 mét) để tăng khả năng cache hit
        lat_r = round(lat, 5)
        lon_r = round(lon, 5)
        return f"reverse:{lat_r:.5f}:{lon_r:.5f}:{zoom}:{lang.lower()}"

# Global cache instance
cache_service = TTLCache()

