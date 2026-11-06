import math
import re
from dataclasses import dataclass, asdict, field
from typing import Optional, List, Dict, Any
from app.config import Config

class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, headers: Optional[Dict[str, str]] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.headers = headers or {}

class ValidationError(AppException):
    def __init__(self, message: str):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=400)

class InvalidCoordinateError(AppException):
    def __init__(self, message: str):
        super().__init__(code="INVALID_COORDINATE", message=message, status_code=400)

class NoResultError(AppException):
    def __init__(self, message: str = "Không tìm thấy địa chỉ hoặc đối tượng tương ứng tại tọa độ cung cấp."):
        super().__init__(code="NO_RESULT", message=message, status_code=404)

class RateLimitedError(AppException):
    def __init__(self, retry_after: int, message: str = "Client gọi backend quá nhanh. Vui lòng thử lại sau."):
        super().__init__(code="RATE_LIMITED", message=message, status_code=429, headers={"Retry-After": str(retry_after)})

class UpstreamRateLimitedError(AppException):
    def __init__(self, retry_after: int = 60, message: str = "Nominatim đang giới hạn tốc độ (429). Hệ thống đang kích hoạt ngắt mạch tạm thời."):
        super().__init__(code="UPSTREAM_RATE_LIMITED", message=message, status_code=429, headers={"Retry-After": str(retry_after)})

class UpstreamTimeoutError(AppException):
    def __init__(self, message: str = "Nominatim không phản hồi trong thời gian cho phép (timeout)."):
        super().__init__(code="UPSTREAM_TIMEOUT", message=message, status_code=504)

class UpstreamError(AppException):
    def __init__(self, message: str = "Máy chủ Nominatim gặp lỗi nội bộ (5xx)."):
        super().__init__(code="UPSTREAM_ERROR", message=message, status_code=502)

class UpstreamBlockedError(AppException):
    def __init__(self, message: str = "Yêu cầu bị Nominatim từ chối (403 Forbidden). Cần kiểm tra User-Agent hoặc giới hạn truy cập."):
        super().__init__(code="UPSTREAM_BLOCKED", message=message, status_code=502)

class UpstreamBadResponseError(AppException):
    def __init__(self, message: str = "Phản hồi từ Nominatim không hợp lệ hoặc thiếu trường bắt buộc."):
        super().__init__(code="UPSTREAM_BAD_RESPONSE", message=message, status_code=502)


@dataclass
class AddressDTO:
    houseNumber: Optional[str] = None
    street: Optional[str] = None
    ward: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    postcode: Optional[str] = None
    country: Optional[str] = None
    countryCode: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BoundingBoxDTO:
    south: float
    north: float
    west: float
    east: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class GeocodeItem:
    osmType: str
    osmId: int
    category: str
    type: str
    name: Optional[str]
    displayName: str
    lat: float
    lon: float
    boundingBox: BoundingBoxDTO
    importance: Optional[float]
    address: AddressDTO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "osmType": self.osmType,
            "osmId": self.osmId,
            "category": self.category,
            "type": self.type,
            "name": self.name,
            "displayName": self.displayName,
            "lat": self.lat,
            "lon": self.lon,
            "boundingBox": self.boundingBox.to_dict(),
            "importance": self.importance,
            "address": self.address.to_dict(),
        }


@dataclass
class SearchRequest:
    q: str
    limit: int = Config.SEARCH_DEFAULT_LIMIT
    lang: str = Config.DEFAULT_LANG
    country: str = Config.DEFAULT_COUNTRY

    @classmethod
    def from_query_params(cls, args: Dict[str, Any]) -> "SearchRequest":
        q = args.get("q", "")
        if not q or not isinstance(q, str):
            raise ValidationError("Tham số 'q' là bắt buộc và không được để trống.")
        
        # Cắt khoảng trắng đầu/cuối, gộp khoảng trắng liên tiếp
        clean_q = re.sub(r"\s+", " ", q.strip())
        if len(clean_q) < 3:
            raise ValidationError(f"Từ khóa tìm kiếm 'q' quá ngắn ({len(clean_q)} ký tự). Độ dài tối thiểu là 3 ký tự.")
        if len(clean_q) > 200:
            raise ValidationError(f"Từ khóa tìm kiếm 'q' quá dài ({len(clean_q)} ký tự). Độ dài tối đa là 200 ký tự.")
        if not re.search(r"[\w\d\u00C0-\u1EF9]", clean_q):
            raise ValidationError("Từ khóa tìm kiếm 'q' không được chỉ chứa ký tự đặc biệt.")

        # limit validation
        raw_limit = args.get("limit")
        limit = Config.SEARCH_DEFAULT_LIMIT
        if raw_limit is not None and str(raw_limit).strip() != "":
            try:
                limit = int(raw_limit)
            except (ValueError, TypeError):
                raise ValidationError("Tham số 'limit' phải là số nguyên.")
            if limit < Config.SEARCH_MIN_LIMIT or limit > Config.SEARCH_MAX_LIMIT:
                raise ValidationError(
                    f"Tham số 'limit' ({limit}) nằm ngoài khoảng cho phép [{Config.SEARCH_MIN_LIMIT}, {Config.SEARCH_MAX_LIMIT}]."
                )

        # lang validation
        lang = str(args.get("lang", Config.DEFAULT_LANG)).strip().lower()
        if lang not in Config.ALLOWED_LANGS:
            lang = Config.DEFAULT_LANG

        # country validation
        country = str(args.get("country", Config.DEFAULT_COUNTRY)).strip().lower()
        if country and not re.match(r"^[a-z]{2}$", country):
            raise ValidationError("Tham số 'country' phải là mã ISO 3166-1 alpha-2 gồm 2 ký tự (ví dụ: 'vn', 'us').")

        return cls(q=clean_q, limit=limit, lang=lang, country=country)


@dataclass
class ReverseRequest:
    lat: float
    lon: float
    zoom: int = Config.REVERSE_DEFAULT_ZOOM
    lang: str = Config.DEFAULT_LANG

    @classmethod
    def from_query_params(cls, args: Dict[str, Any]) -> "ReverseRequest":
        raw_lat = args.get("lat")
        raw_lon = args.get("lon")

        if raw_lat is None or str(raw_lat).strip() == "":
            raise ValidationError("Tham số 'lat' là bắt buộc.")
        if raw_lon is None or str(raw_lon).strip() == "":
            raise ValidationError("Tham số 'lon' là bắt buộc.")

        try:
            lat = float(raw_lat)
        except (ValueError, TypeError):
            raise ValidationError("Tham số 'lat' phải là số thực hợp lệ.")

        try:
            lon = float(raw_lon)
        except (ValueError, TypeError):
            raise ValidationError("Tham số 'lon' phải là số thực hợp lệ.")

        if math.isnan(lat) or math.isinf(lat):
            raise ValidationError("Tham số 'lat' không được là NaN hoặc Infinity.")
        if math.isnan(lon) or math.isinf(lon):
            raise ValidationError("Tham số 'lon' không được là NaN hoặc Infinity.")

        # Phát hiện lỗi đảo tọa độ (lat/lon swap) và kiểm tra miền giá trị
        # Tọa độ Việt Nam: lat ~ [8.5, 23.5], lon ~ [102.0, 110.0]
        if abs(lat) > 90:
            if 102.0 <= lat <= 110.0 and 8.0 <= lon <= 24.0:
                raise InvalidCoordinateError(
                    f"Giá trị lat={lat} vượt quá phạm vi [-90, 90]. Phát hiện lat và lon bị đảo thứ tự (Việt Nam: lat ~ [8, 24], lon ~ [102, 110])."
                )
            raise InvalidCoordinateError(
                f"Giá trị lat={lat} phải nằm trong khoảng [-90, 90]. Có thể lat và lon bị đảo thứ tự."
            )

        if abs(lon) > 180:
            raise InvalidCoordinateError(f"Giá trị lon={lon} phải nằm trong khoảng [-180, 180].")

        # Zoom validation
        raw_zoom = args.get("zoom")
        zoom = Config.REVERSE_DEFAULT_ZOOM
        if raw_zoom is not None and str(raw_zoom).strip() != "":
            try:
                zoom = int(raw_zoom)
            except (ValueError, TypeError):
                raise ValidationError("Tham số 'zoom' phải là số nguyên.")
            if zoom < Config.REVERSE_MIN_ZOOM or zoom > Config.REVERSE_MAX_ZOOM:
                raise ValidationError(
                    f"Tham số 'zoom' ({zoom}) nằm ngoài khoảng cho phép [{Config.REVERSE_MIN_ZOOM}, {Config.REVERSE_MAX_ZOOM}]."
                )

        lang = str(args.get("lang", Config.DEFAULT_LANG)).strip().lower()
        if lang not in Config.ALLOWED_LANGS:
            lang = Config.DEFAULT_LANG

        return cls(lat=lat, lon=lon, zoom=zoom, lang=lang)

