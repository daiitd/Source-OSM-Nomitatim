import time
from flask import Flask, request, jsonify, Response

mock_app = Flask(__name__)

# Trạng thái giả lập lỗi có thể bật/tắt động
simulation_mode = {
    "force_429": False,
    "force_500": False,
    "force_timeout": False,
    "retry_after_sec": 10,
}

@mock_app.route("/search", methods=["GET"])
def mock_search():
    if simulation_mode["force_429"]:
        resp = jsonify({"error": "Bandwidth limit exceeded (Simulated 429)"})
        resp.status_code = 429
        resp.headers["Retry-After"] = str(simulation_mode["retry_after_sec"])
        return resp

    if simulation_mode["force_500"]:
        return jsonify({"error": "Internal Server Error from OSM cluster (Simulated 500)"}), 500

    if simulation_mode["force_timeout"]:
        time.sleep(15)  # Gây timeout phía client
        return jsonify([]), 200

    q = request.args.get("q", "").lower()
    limit = int(request.args.get("limit", 5))

    if "bến thành" in q:
        return jsonify([
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
        ][:limit])

    if "đức bà" in q:
        return jsonify([
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
                    "country": "Việt Nam",
                    "country_code": "vn",
                },
            }
        ][:limit])

    # Kết quả rỗng
    return jsonify([])


@mock_app.route("/reverse", methods=["GET"])
def mock_reverse():
    if simulation_mode["force_429"]:
        resp = jsonify({"error": "Bandwidth limit exceeded (Simulated 429)"})
        resp.status_code = 429
        resp.headers["Retry-After"] = str(simulation_mode["retry_after_sec"])
        return resp

    if simulation_mode["force_500"]:
        return jsonify({"error": "Database temporarily unavailable (Simulated 500)"}), 500

    if simulation_mode["force_timeout"]:
        time.sleep(15)
        return jsonify({}), 200

    lat = float(request.args.get("lat", 0))
    lon = float(request.args.get("lon", 0))

    # Test Case R2: Biển / Vùng không có dữ liệu -> trả {"error": "Unable to geocode"}
    if abs(lat) < 0.1 and abs(lon) < 0.1:
        return jsonify({"error": "Unable to geocode"}), 200

    # Test Case R1: Chợ Bến Thành
    if 10.7 < lat < 10.8 and 106.6 < lon < 106.75:
        return jsonify({
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
        })

    return jsonify({"error": "Unable to geocode"}), 200


@mock_app.route("/mock/control", methods=["POST"])
def control():
    """Endpoint để script test bật/tắt nhanh các kịch bản lỗi 429, 500, timeout."""
    data = request.get_json(force=True)
    for k in simulation_mode:
        if k in data:
            simulation_mode[k] = data[k]
    return jsonify({"status": "ok", "currentMode": simulation_mode})


if __name__ == "__main__":
    print("Mock Nominatim Server listening on http://localhost:8081")
    mock_app.run(port=8081, debug=False)

