import time
from flask import Blueprint, request, jsonify, render_template_string, Response
from app.config import Config
from app.dtos import (
    SearchRequest,
    ReverseRequest,
    AppException,
    ValidationError,
    InvalidCoordinateError,
    NoResultError,
    UpstreamRateLimitedError,
    UpstreamTimeoutError,
    UpstreamError,
    UpstreamBlockedError,
    UpstreamBadResponseError,
)
from app.mapper import map_nominatim_to_geocode_item
from app.cache import cache_service
from app.rate_limiter import circuit_breaker
from app.client import nominatim_client
from app.logger import structured_logger

api_bp = Blueprint("api", __name__)

ATTRIBUTION = "© OpenStreetMap contributors"
PROVIDER = "nominatim"

@api_bp.app_errorhandler(AppException)
def handle_app_exception(err: AppException):
    req_id = getattr(request, "request_id", structured_logger.generate_request_id())
    structured_logger.log_request(
        request_id=req_id,
        endpoint=request.path,
        cache_status="none",
        outcome=err.code.lower(),
        extra={"error": err.message},
    )
    payload = {
        "error": {
            "code": err.code,
            "message": err.message,
            "requestId": req_id,
        }
    }
    response = jsonify(payload)
    response.status_code = err.status_code
    for k, v in err.headers.items():
        response.headers[k] = v
    return response


@api_bp.app_errorhandler(Exception)
def handle_generic_exception(err: Exception):
    req_id = getattr(request, "request_id", structured_logger.generate_request_id())
    structured_logger.log_request(
        request_id=req_id,
        endpoint=request.path,
        cache_status="none",
        outcome="internal_error",
        extra={"exception": str(err)},
    )
    payload = {
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "Đã xảy ra lỗi hệ thống nội bộ.",
            "requestId": req_id,
        }
    }
    response = jsonify(payload)
    response.status_code = 500
    return response


@api_bp.route("/api/v1/geocode/search", methods=["GET"])
def geocode_search():
    """
    Endpoint POC Search:
    Tìm kiếm địa danh/địa chỉ theo chuỗi văn bản và chuẩn hóa về danh sách GeocodeItem.
    Tuân thủ đúng Pipeline 10 bước (Mục 7.2).
    """
    req_id = structured_logger.generate_request_id()
    request.request_id = req_id

    # Bước 1 & 2: Nhận input & Validate
    search_req = SearchRequest.from_query_params(request.args)

    # Bước 3: Chuẩn hóa và tạo khóa cache
    cache_key = cache_service.make_search_key(
        q=search_req.q,
        limit=search_req.limit,
        lang=search_req.lang,
        country=search_req.country,
    )

    # Bước 4: Tra cache
    cached_payload, is_hit = cache_service.get(cache_key)
    if is_hit:
        # Cache hit: trả ngay, đánh dấu meta.cached = true
        cached_payload["meta"]["cached"] = True
        structured_logger.log_request(
            request_id=req_id,
            endpoint="search",
            cache_status="hit",
            outcome="ok",
        )
        return jsonify(cached_payload), 200

    # Bước 5 & 6: Điều tốc & Gọi Nominatim /search
    raw_results, upstream_status, upstream_ms = nominatim_client.search(
        q=search_req.q,
        limit=search_req.limit,
        lang=search_req.lang,
        country=search_req.country,
    )

    # Bước 7 & 8: Phân tích & Ánh xạ DTO thống nhất
    items = []
    for raw in raw_results:
        try:
            item = map_nominatim_to_geocode_item(raw)
            items.append(item.to_dict())
        except UpstreamBadResponseError:
            continue

    response_payload = {
        "query": search_req.q,
        "count": len(items),
        "results": items,
        "meta": {
            "provider": PROVIDER,
            "cached": False,
            "attribution": ATTRIBUTION,
        },
    }

    # Bước 9: Lưu cache (Positive: 1h, Negative cache nếu mảng rỗng: 60s)
    ttl = Config.CACHE_TTL_NEGATIVE_SEC if len(items) == 0 else Config.CACHE_TTL_POSITIVE_SEC
    cache_service.set(cache_key, response_payload, ttl_seconds=ttl)

    # Bước 10: Trả response & ghi log
    structured_logger.log_request(
        request_id=req_id,
        endpoint="search",
        cache_status="miss",
        outcome="ok",
        upstream_status=upstream_status,
        upstream_ms=upstream_ms,
    )
    return jsonify(response_payload), 200


@api_bp.route("/api/v1/geocode/reverse", methods=["GET"])
def geocode_reverse():
    """
    Endpoint POC Reverse:
    Tìm địa chỉ gần nhất từ cặp tọa độ (lat, lon) và chuẩn hóa về GeocodeItem.
    Xử lý rành mạch 2 nhánh: có kết quả (200) và không có kết quả (404 NO_RESULT).
    """
    req_id = structured_logger.generate_request_id()
    request.request_id = req_id

    # Bước 1 & 2: Nhận input & Validate (kiểm tra chặt chẽ lat/lon và nghi đảo thứ tự)
    reverse_req = ReverseRequest.from_query_params(request.args)

    # Bước 3: Chuẩn hóa tọa độ và tạo khóa cache
    cache_key = cache_service.make_reverse_key(
        lat=reverse_req.lat,
        lon=reverse_req.lon,
        zoom=reverse_req.zoom,
        lang=reverse_req.lang,
    )

    # Bước 4: Tra cache
    cached_payload, is_hit = cache_service.get(cache_key)
    if is_hit:
        if cached_payload.get("status") == "no_result":
            # Cache hit của trường hợp không có kết quả (negative cache)
            structured_logger.log_request(
                request_id=req_id,
                endpoint="reverse",
                cache_status="hit",
                outcome="no_result",
            )
            raise NoResultError()

        cached_payload["meta"]["cached"] = True
        structured_logger.log_request(
            request_id=req_id,
            endpoint="reverse",
            cache_status="hit",
            outcome="ok",
        )
        return jsonify(cached_payload), 200

    # Bước 5 & 6: Điều tốc & Gọi Nominatim /reverse
    raw_result, upstream_status, upstream_ms = nominatim_client.reverse(
        lat=reverse_req.lat,
        lon=reverse_req.lon,
        zoom=reverse_req.zoom,
        lang=reverse_req.lang,
    )

    # Bước 7 & 8: Phân tích & Ánh xạ DTO
    if raw_result is None:
        # Nhánh không có kết quả (tọa độ giữa biển hoặc ngoài vùng phủ OSM)
        # Lưu negative cache 60s để giảm tải
        cache_service.set(cache_key, {"status": "no_result"}, ttl_seconds=Config.CACHE_TTL_NEGATIVE_SEC)
        structured_logger.log_request(
            request_id=req_id,
            endpoint="reverse",
            cache_status="miss",
            outcome="no_result",
            upstream_status=upstream_status,
            upstream_ms=upstream_ms,
        )
        raise NoResultError()

    item = map_nominatim_to_geocode_item(raw_result)
    response_payload = {
        "result": item.to_dict(),
        "meta": {
            "provider": PROVIDER,
            "cached": False,
            "attribution": ATTRIBUTION,
        },
    }

    # Bước 9: Lưu cache (Positive: 1h)
    cache_service.set(cache_key, response_payload, ttl_seconds=Config.CACHE_TTL_POSITIVE_SEC)

    # Bước 10: Trả response & ghi log
    structured_logger.log_request(
        request_id=req_id,
        endpoint="reverse",
        cache_status="miss",
        outcome="ok",
        upstream_status=upstream_status,
        upstream_ms=upstream_ms,
    )
    return jsonify(response_payload), 200


@api_bp.route("/api/v1/geocode/stats", methods=["GET"])
def get_stats():
    """Lấy số liệu quan sát: Trạng thái Cache, Circuit Breaker và cấu hình."""
    return jsonify({
        "cache": cache_service.stats(),
        "circuitBreaker": circuit_breaker.check_state(),
        "config": {
            "nominatimBaseUrl": Config.NOMINATIM_BASE_URL,
            "userAgent": Config.USER_AGENT,
            "connectTimeout": Config.CONNECT_TIMEOUT_SEC,
            "readTimeout": Config.READ_TIMEOUT_SEC,
            "rateLimitRps": Config.RATE_LIMIT_RPS,
        }
    }), 200


@api_bp.route("/api/v1/geocode/cache/clear", methods=["POST"])
def clear_cache():
    """Xóa trắng bộ nhớ đệm (dùng khi demo so sánh cache hit/miss)."""
    cache_service.clear()
    return jsonify({"message": "Cache đã được xóa trắng thành công.", "status": "ok"}), 200


@api_bp.route("/api/v1/geocode/circuit-breaker/reset", methods=["POST"])
def reset_circuit_breaker():
    """Đặt lại trạng thái ngắt mạch (dùng khi demo mô phỏng 429)."""
    circuit_breaker.reset()
    return jsonify({"message": "Circuit breaker đã được reset về trạng thái CLOSED.", "status": "ok"}), 200


@api_bp.route("/api/v1/geocode/logs", methods=["GET"])
def get_recent_logs():
    """Xem các dòng log gần nhất có cấu trúc JSON."""
    limit = int(request.args.get("limit", 30))
    return jsonify({"logs": structured_logger.get_recent_logs(limit)}), 200

