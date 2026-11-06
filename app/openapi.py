from flask import Blueprint, jsonify

openapi_bp = Blueprint("openapi", __name__)

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "MID Software - Geocoding POC API Contract",
        "description": "API Contract phục vụ nghiên cứu tích hợp OpenStreetMap Nominatim vào Backend (Tuần 3: 02–06/11/2026).",
        "version": "1.0.0",
        "contact": {
            "name": "Nguyễn Phương Đại · Dương Đức Quân",
            "email": "contact@midsoftware.com"
        }
    },
    "servers": [
        {"url": "/", "description": "Local Development / Demo Server"}
    ],
    "paths": {
        "/api/v1/geocode/search": {
            "get": {
                "summary": "Tìm kiếm địa danh/địa chỉ theo chuỗi ký tự (Search Proxy)",
                "description": "Proxy chuyển tiếp request đến Nominatim /search, chuẩn hóa dữ liệu sang DTO thống nhất và quản lý cache.",
                "parameters": [
                    {
                        "name": "q",
                        "in": "query",
                        "required": True,
                        "description": "Từ khóa tìm kiếm (độ dài 3-200 ký tự, không chỉ gồm ký tự đặc biệt).",
                        "schema": {"type": "string", "example": "Chợ Bến Thành"}
                    },
                    {
                        "name": "limit",
                        "in": "query",
                        "required": False,
                        "description": "Số lượng kết quả tối đa (mặc định 5, giới hạn 1-10).",
                        "schema": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10, "example": 5}
                    },
                    {
                        "name": "lang",
                        "in": "query",
                        "required": False,
                        "description": "Ngôn ngữ kết quả (mặc định 'vi').",
                        "schema": {"type": "string", "default": "vi", "enum": ["vi", "en", "fr", "de", "ja", "zh", "ru"]}
                    },
                    {
                        "name": "country",
                        "in": "query",
                        "required": False,
                        "description": "Mã quốc gia ISO 3166-1 alpha-2 chữ thường (mặc định 'vn').",
                        "schema": {"type": "string", "default": "vn", "example": "vn"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Tìm kiếm thành công (kể cả trường hợp không tìm thấy kết quả nào thì results rỗng).",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SearchResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Tham số đầu vào không hợp lệ (q quá ngắn, limit ngoài khoảng).",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "429": {
                        "description": "Bị giới hạn tốc độ (Client hoặc Upstream Nominatim).",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "502": {
                        "description": "Lỗi từ phía máy chủ Nominatim hoặc bị chặn.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "504": {
                        "description": "Hết thời gian chờ phản hồi từ Nominatim (Timeout).",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/geocode/reverse": {
            "get": {
                "summary": "Truy vấn địa chỉ từ tọa độ địa lý (Reverse Proxy)",
                "description": "Chuyển đổi cặp tọa độ WGS84 (lat, lon) thành thông tin địa chỉ OSM.",
                "parameters": [
                    {
                        "name": "lat",
                        "in": "query",
                        "required": True,
                        "description": "Vĩ độ [-90, 90].",
                        "schema": {"type": "number", "format": "float", "example": 10.7725}
                    },
                    {
                        "name": "lon",
                        "in": "query",
                        "required": True,
                        "description": "Kinh độ [-180, 180].",
                        "schema": {"type": "number", "format": "float", "example": 106.6980}
                    },
                    {
                        "name": "zoom",
                        "in": "query",
                        "required": False,
                        "description": "Mức chi tiết (3=quốc gia, 10=thành phố, 18=tòa nhà). Mặc định 18.",
                        "schema": {"type": "integer", "default": 18, "minimum": 3, "maximum": 18, "example": 18}
                    },
                    {
                        "name": "lang",
                        "in": "query",
                        "required": False,
                        "description": "Ngôn ngữ kết quả (mặc định 'vi').",
                        "schema": {"type": "string", "default": "vi"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Tìm thấy địa chỉ phù hợp.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ReverseResponse"}
                            }
                        }
                    },
                    "400": {
                        "description": "Tọa độ không hợp lệ hoặc phát hiện đảo lat/lon.",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    },
                    "404": {
                        "description": "Không tìm thấy dữ liệu OSM tại tọa độ đã cho (NO_RESULT).",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "schemas": {
            "BoundingBox": {
                "type": "object",
                "properties": {
                    "south": {"type": "number", "example": 10.7718},
                    "north": {"type": "number", "example": 10.7732},
                    "west": {"type": "number", "example": 106.6973},
                    "east": {"type": "number", "example": 106.6987}
                },
                "required": ["south", "north", "west", "east"]
            },
            "Address": {
                "type": "object",
                "properties": {
                    "houseNumber": {"type": "string", "nullable": True, "example": "01"},
                    "street": {"type": "string", "nullable": True, "example": "Đường Lê Lợi"},
                    "ward": {"type": "string", "nullable": True, "example": "Phường Bến Thành"},
                    "district": {"type": "string", "nullable": True, "example": "Quận 1"},
                    "city": {"type": "string", "nullable": True, "example": "Thành phố Hồ Chí Minh"},
                    "province": {"type": "string", "nullable": True, "example": "Thành phố Hồ Chí Minh"},
                    "postcode": {"type": "string", "nullable": True, "example": "700000"},
                    "country": {"type": "string", "nullable": True, "example": "Việt Nam"},
                    "countryCode": {"type": "string", "nullable": True, "example": "vn"}
                }
            },
            "GeocodeItem": {
                "type": "object",
                "properties": {
                    "osmType": {"type": "string", "example": "way"},
                    "osmId": {"type": "integer", "example": 24231889},
                    "category": {"type": "string", "example": "amenity"},
                    "type": {"type": "string", "example": "marketplace"},
                    "name": {"type": "string", "nullable": True, "example": "Chợ Bến Thành"},
                    "displayName": {"type": "string", "example": "Chợ Bến Thành, Đường Lê Lợi, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh, 700000, Việt Nam"},
                    "lat": {"type": "number", "format": "float", "example": 10.7725},
                    "lon": {"type": "number", "format": "float", "example": 106.6980},
                    "boundingBox": {"$ref": "#/components/schemas/BoundingBox"},
                    "importance": {"type": "number", "format": "float", "nullable": True, "example": 0.62},
                    "address": {"$ref": "#/components/schemas/Address"}
                },
                "required": ["osmType", "osmId", "category", "type", "displayName", "lat", "lon", "boundingBox", "address"]
            },
            "SearchResponse": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "example": "Chợ Bến Thành"},
                    "count": {"type": "integer", "example": 1},
                    "results": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/GeocodeItem"}
                    },
                    "meta": {
                        "type": "object",
                        "properties": {
                            "provider": {"type": "string", "example": "nominatim"},
                            "cached": {"type": "boolean", "example": False},
                            "attribution": {"type": "string", "example": "© OpenStreetMap contributors"}
                        }
                    }
                }
            },
            "ReverseResponse": {
                "type": "object",
                "properties": {
                    "result": {"$ref": "#/components/schemas/GeocodeItem"},
                    "meta": {
                        "type": "object",
                        "properties": {
                            "provider": {"type": "string", "example": "nominatim"},
                            "cached": {"type": "boolean", "example": False},
                            "attribution": {"type": "string", "example": "© OpenStreetMap contributors"}
                        }
                    }
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "example": "INVALID_COORDINATE"},
                            "message": {"type": "string", "example": "lat phải nằm trong [-90, 90]. Có thể lat và lon bị đảo thứ tự."},
                            "requestId": {"type": "string", "example": "a1b2c3d4"}
                        },
                        "required": ["code", "message", "requestId"]
                    }
                }
            }
        }
    }
}

@openapi_bp.route("/api/v1/openapi.json", methods=["GET"])
def get_openapi_json():
    return jsonify(OPENAPI_SPEC)

