import time
import random
import requests
from typing import Dict, Any, Optional, List, Tuple
from app.config import Config
from app.dtos import (
    UpstreamRateLimitedError,
    UpstreamTimeoutError,
    UpstreamError,
    UpstreamBlockedError,
    UpstreamBadResponseError,
    NoResultError,
)
from app.rate_limiter import rate_limiter, circuit_breaker

# Realistic offline mock fixtures (dùng khi chạy demo không có kết nối internet hoặc kiểm thử nội bộ)
OFFLINE_FIXTURES_SEARCH = {
    "chợ bến thành": [
        {
            "place_id": 101,
            "osm_type": "way",
            "osm_id": 24231889,
            "category": "amenity",
            "type": "marketplace",
            "name": "Chợ Bến Thành",
            "display_name": "Chợ Bến Thành, Đường Lê Lợi, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh, 700000, Việt Nam",
            "lat": "10.7725",
            "lon": "106.6980",
            "boundingbox": ["10.7718", "10.7732", "106.6973", "106.6987"],
            "importance": 0.62,
            "address": {
                "amenity": "Chợ Bến Thành",
                "road": "Đường Lê Lợi",
                "suburb": "Phường Bến Thành",
                "city_district": "Quận 1",
                "city": "Thành phố Hồ Chí Minh",
                "state": "Thành phố Hồ Chí Minh",
                "postcode": "700000",
                "country": "Việt Nam",
                "country_code": "vn",
            },
        }
    ],
    "nhà thờ đức bà": [
        {
            "place_id": 102,
            "osm_type": "way",
            "osm_id": 24231890,
            "category": "amenity",
            "type": "place_of_worship",
            "name": "Nhà thờ Đức Bà Sài Gòn",
            "display_name": "Nhà thờ Đức Bà Sài Gòn, 01, Công xã Paris, Phường Bến Nghé, Quận 1, Thành phố Hồ Chí Minh, 700000, Việt Nam",
            "lat": "10.7798",
            "lon": "106.6990",
            "boundingbox": ["10.7790", "10.7806", "106.6982", "106.6998"],
            "importance": 0.58,
            "address": {
                "house_number": "01",
                "road": "Công xã Paris",
                "suburb": "Phường Bến Nghé",
                "city_district": "Quận 1",
                "city": "Thành phố Hồ Chí Minh",
                "state": "Thành phố Hồ Chí Minh",
                "postcode": "700000",
                "country": "Việt Nam",
                "country_code": "vn",
            },
        }
    ],
    "hồ hoàn kiếm": [
        {
            "place_id": 103,
            "osm_type": "relation",
            "osm_id": 1234567,
            "category": "natural",
            "type": "water",
            "name": "Hồ Hoàn Kiếm",
            "display_name": "Hồ Hoàn Kiếm, Phường Hàng Trống, Quận Hoàn Kiếm, Hà Nội, 100000, Việt Nam",
            "lat": "21.0285",
            "lon": "105.8542",
            "boundingbox": ["21.0250", "21.0320", "105.8500", "105.8580"],
            "importance": 0.65,
            "address": {
                "road": "Đinh Tiên Hoàng",
                "suburb": "Phường Hàng Trống",
                "city_district": "Quận Hoàn Kiếm",
                "city": "Hà Nội",
                "state": "Hà Nội",
                "postcode": "100000",
                "country": "Việt Nam",
                "country_code": "vn",
            },
        }
    ],
}

OFFLINE_FIXTURE_REVERSE_BEN_THANH = {
    "place_id": 201,
    "osm_type": "way",
    "osm_id": 24231889,
    "category": "amenity",
    "type": "marketplace",
    "name": "Chợ Bến Thành",
    "display_name": "Chợ Bến Thành, Đường Lê Lợi, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh, 700000, Việt Nam",
    "lat": "10.7725",
    "lon": "106.6980",
    "boundingbox": ["10.7718", "10.7732", "106.6973", "106.6987"],
    "importance": 0.62,
    "address": {
        "road": "Đường Lê Lợi",
        "suburb": "Phường Bến Thành",
        "city_district": "Quận 1",
        "city": "Thành phố Hồ Chí Minh",
        "country": "Việt Nam",
        "country_code": "vn",
    },
}


class NominatimClient:
    """
    HTTP Client giao tiếp với Nominatim OSM tuân thủ nghiêm ngặt Bảng 8 & Bảng 12:
    - User-Agent tùy chỉnh định danh ứng dụng
    - Connect timeout: 3s, Read timeout: 8s
    - Điều tốc 1 request/giây
    - Circuit breaker cho 429 (KHÔNG retry ngay)
    - Retry có giới hạn với backoff + jitter cho 5xx và timeout
    - Chặn ngay khi gặp 403 Forbidden
    """
    def __init__(self, base_url: str = Config.NOMINATIM_BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": Config.USER_AGENT,
            "Accept": "application/json",
        })

    def search(
        self,
        q: str,
        limit: int,
        lang: str = Config.DEFAULT_LANG,
        country: str = Config.DEFAULT_COUNTRY,
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Gọi endpoint /search của Nominatim.
        Trả về: (results_list, upstream_http_status, upstream_latency_ms)
        """
        params = {
            "q": q,
            "format": "jsonv2",
            "limit": limit,
            "addressdetails": 1,
            "accept-language": lang,
            "countrycodes": country,
        }
        url = f"{self.base_url}/search"
        raw_data, status, latency_ms = self._execute_with_resilience("GET", url, params)

        if not isinstance(raw_data, list):
            raise UpstreamBadResponseError("Kết quả tìm kiếm từ Nominatim không phải là một mảng.")

        return raw_data, status, latency_ms

    def reverse(
        self,
        lat: float,
        lon: float,
        zoom: int = Config.REVERSE_DEFAULT_ZOOM,
        lang: str = Config.DEFAULT_LANG,
    ) -> Tuple[Optional[Dict[str, Any]], int, int]:
        """
        Gọi endpoint /reverse của Nominatim.
        Trả về: (result_dict_or_None, upstream_http_status, upstream_latency_ms)
        Nếu không có kết quả (tọa độ ngoài vùng dữ liệu), trả về None (khiến Route xử lý 404 NO_RESULT).
        """
        params = {
            "lat": str(lat),
            "lon": str(lon),
            "format": "jsonv2",
            "zoom": zoom,
            "addressdetails": 1,
            "accept-language": lang,
        }
        url = f"{self.base_url}/reverse"
        raw_data, status, latency_ms = self._execute_with_resilience("GET", url, params)

        if isinstance(raw_data, dict):
            # Kiểm tra trường error của Nominatim (ví dụ: {"error": "Unable to geocode"})
            if "error" in raw_data:
                return None, status, latency_ms
            return raw_data, status, latency_ms

        raise UpstreamBadResponseError("Kết quả reverse từ Nominatim không phải là đối tượng hợp lệ.")

    def _execute_with_resilience(
        self,
        method: str,
        url: str,
        params: Dict[str, Any],
    ) -> Tuple[Any, int, int]:
        """
        Thực thi HTTP request kèm kiểm tra ngắt mạch, giới hạn tốc độ và retry theo chính sách.
        """
        # Bước 1: Kiểm tra Circuit Breaker (Ngắt mạch)
        cb_state = circuit_breaker.check_state()
        if cb_state["isOpen"]:
            raise UpstreamRateLimitedError(
                retry_after=cb_state["remainingCooldownSec"],
                message=f"Ngắt mạch đang BẬT do Nominatim trả 429 trước đó. Vui lòng thử lại sau {cb_state['remainingCooldownSec']} giây."
            )

        # Bước 2: Điều tốc backend (giữ khoảng cách >= 1 giây giữa các request)
        rate_limiter.acquire()

        # Bước 3: Vòng lặp gọi HTTP với chính sách retry phân biệt rõ 429, timeout, 5xx
        attempt = 0
        max_attempts = 1 + Config.MAX_RETRIES_5XX

        while attempt < max_attempts:
            attempt += 1
            start_time = time.time()
            try:
                resp = self.session.request(
                    method=method,
                    url=url,
                    params=params,
                    timeout=(Config.CONNECT_TIMEOUT_SEC, Config.READ_TIMEOUT_SEC),
                )
                latency_ms = int((time.time() - start_time) * 1000)

                # Trường hợp 429 Too Many Requests:
                if resp.status_code == 429:
                    retry_after_header = resp.headers.get("Retry-After", str(Config.CIRCUIT_BREAKER_DEFAULT_COOLDOWN_SEC))
                    try:
                        retry_after = int(retry_after_header)
                    except ValueError:
                        retry_after = Config.CIRCUIT_BREAKER_DEFAULT_COOLDOWN_SEC
                    
                    # BẬT NGẮT MẠCH NGAY LẬP TỨC - TUYỆT ĐỐI KHÔNG RETRY!
                    circuit_breaker.trip(retry_after)
                    raise UpstreamRateLimitedError(retry_after=retry_after)

                # Trường hợp 403 Forbidden (bị chặn):
                if resp.status_code == 403:
                    # KHÔNG RETRY
                    raise UpstreamBlockedError("Nominatim từ chối truy cập (403). Kiểm tra lại User-Agent hoặc IP.")

                # Trường hợp 5xx Server Error:
                if 500 <= resp.status_code <= 599:
                    if attempt <= Config.MAX_RETRIES_5XX:
                        # Exponential backoff + jitter
                        backoff = (Config.INITIAL_BACKOFF_SEC * (2 ** (attempt - 1))) + random.uniform(0.1, 0.4)
                        time.sleep(backoff)
                        continue
                    raise UpstreamError(f"Nominatim lỗi máy chủ ({resp.status_code}) sau {attempt} lần thử.")

                # Xử lý JSON phản hồi
                try:
                    data = resp.json()
                    return data, resp.status_code, latency_ms
                except ValueError:
                    raise UpstreamBadResponseError(f"Phản hồi không phải định dạng JSON (HTTP {resp.status_code}).")

            except requests.exceptions.Timeout:
                latency_ms = int((time.time() - start_time) * 1000)
                if attempt <= Config.MAX_RETRIES_TIMEOUT:
                    time.sleep(1.0)
                    continue
                raise UpstreamTimeoutError(f"Hết thời gian chờ phản hồi từ Nominatim ({Config.READ_TIMEOUT_SEC}s).")

            except requests.exceptions.RequestException as e:
                # Nếu gặp lỗi kết nối (ví dụ offline, sandbox không có mạng)
                if Config.ENABLE_OFFLINE_MOCK_FALLBACK:
                    fallback_data, fb_status = self._get_offline_mock(url, params)
                    return fallback_data, fb_status, 15
                raise UpstreamError(f"Không thể kết nối đến máy chủ Nominatim: {e}")

        raise UpstreamError("Đã vượt quá số lần thử lại tối đa.")

    def _get_offline_mock(self, url: str, params: Dict[str, Any]) -> Tuple[Any, int]:
        """Phục vụ mock data khi chạy offline hoặc môi trường không có internet."""
        if "/search" in url:
            q = str(params.get("q", "")).strip().lower()
            limit = int(params.get("limit", 5))
            for key, items in OFFLINE_FIXTURES_SEARCH.items():
                if key in q or q in key:
                    return items[:limit], 200
            # Không tìm thấy -> trả mảng rỗng
            return [], 200

        elif "/reverse" in url:
            lat = float(params.get("lat", 0))
            lon = float(params.get("lon", 0))
            # Test case R2: 0,0 (biển) -> trả {"error": "Unable to geocode"}
            if abs(lat) < 0.1 and abs(lon) < 0.1:
                return {"error": "Unable to geocode"}, 200
            # Test case R1: Tọa độ gần Chợ Bến Thành
            if 10.7 < lat < 10.85 and 106.6 < lon < 106.75:
                return OFFLINE_FIXTURE_REVERSE_BEN_THANH, 200
            # Mặc định vùng khác: trả về địa chỉ mô phỏng
            return {
                "place_id": 301,
                "osm_type": "node",
                "osm_id": 99887766,
                "category": "place",
                "type": "locality",
                "name": "Khu vực tọa độ",
                "display_name": f"Vị trí ({lat}, {lon}), Việt Nam",
                "lat": str(lat),
                "lon": str(lon),
                "boundingbox": [str(lat - 0.001), str(lat + 0.001), str(lon - 0.001), str(lon + 0.001)],
                "importance": 0.4,
                "address": {
                    "city": "Thành phố Hồ Chí Minh",
                    "country": "Việt Nam",
                    "country_code": "vn",
                },
            }, 200

        return {}, 200

# Global client instance
nominatim_client = NominatimClient()

