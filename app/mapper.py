from typing import Dict, Any, Optional
from app.dtos import GeocodeItem, AddressDTO, BoundingBoxDTO, UpstreamBadResponseError

def map_nominatim_to_geocode_item(data: Dict[str, Any]) -> GeocodeItem:
    """
    Ánh xạ dữ liệu JSONv2 thô từ Nominatim sang DTO thống nhất GeocodeItem.
    Tuân thủ đúng quy tắc chuẩn hóa tại Bảng 5 của tài liệu thiết kế.
    """
    if not isinstance(data, dict):
        raise UpstreamBadResponseError("Dữ liệu từ Nominatim không phải là đối tượng JSON hợp lệ.")

    # 1. Tọa độ lat, lon (ép kiểu chuỗi sang float)
    try:
        lat_raw = data.get("lat")
        lon_raw = data.get("lon")
        if lat_raw is None or lon_raw is None:
            raise ValueError("Thiếu trường lat hoặc lon")
        lat = float(lat_raw)
        lon = float(lon_raw)
    except (ValueError, TypeError) as e:
        raise UpstreamBadResponseError(f"Không thể chuyển đổi tọa độ [lat, lon] sang số thực: {e}")

    # 2. BoundingBox: Nominatim jsonv2 trả về mảng 4 chuỗi [south, north, west, east]
    bbox_raw = data.get("boundingbox")
    if bbox_raw and isinstance(bbox_raw, list) and len(bbox_raw) >= 4:
        try:
            bounding_box = BoundingBoxDTO(
                south=float(bbox_raw[0]),
                north=float(bbox_raw[1]),
                west=float(bbox_raw[2]),
                east=float(bbox_raw[3]),
            )
        except (ValueError, TypeError):
            bounding_box = BoundingBoxDTO(south=lat, north=lat, west=lon, east=lon)
    else:
        bounding_box = BoundingBoxDTO(south=lat, north=lat, west=lon, east=lon)

    # 3. Phân cấp địa chỉ (Address details)
    addr_raw = data.get("address") or {}
    if not isinstance(addr_raw, dict):
        addr_raw = {}

    # Ward: lấy giá trị đầu tiên có trong suburb, quarter, neighbourhood, ward, residential
    ward = (
        addr_raw.get("suburb")
        or addr_raw.get("quarter")
        or addr_raw.get("neighbourhood")
        or addr_raw.get("ward")
        or addr_raw.get("residential")
    )

    # District: lấy giá trị đầu tiên có trong city_district, district, county, state_district
    district = (
        addr_raw.get("city_district")
        or addr_raw.get("district")
        or addr_raw.get("county")
        or addr_raw.get("state_district")
    )

    # City: lấy giá trị đầu tiên có trong city, town, village, municipality
    city = (
        addr_raw.get("city")
        or addr_raw.get("town")
        or addr_raw.get("village")
        or addr_raw.get("municipality")
    )

    # Province / State
    province = addr_raw.get("state") or addr_raw.get("province")

    # Country code: chuyển về chữ thường
    raw_cc = addr_raw.get("country_code")
    country_code = str(raw_cc).lower() if raw_cc else None

    address_dto = AddressDTO(
        houseNumber=addr_raw.get("house_number"),
        street=addr_raw.get("road"),
        ward=ward,
        district=district,
        city=city,
        province=province,
        postcode=addr_raw.get("postcode"),
        country=addr_raw.get("country"),
        countryCode=country_code,
    )

    # 4. Tên đối tượng và fallback displayName
    display_name = data.get("display_name") or ""
    name = data.get("name")
    if not name and display_name:
        # Nếu trường name rỗng, lấy phần đầu của displayName trước dấu phẩy
        name = display_name.split(",")[0].strip()

    # 5. Importance
    importance_raw = data.get("importance")
    importance: Optional[float] = None
    if importance_raw is not None:
        try:
            importance = float(importance_raw)
        except (ValueError, TypeError):
            importance = None

    # 6. osm_type, osm_id
    osm_type = str(data.get("osm_type", "unknown"))
    try:
        osm_id = int(data.get("osm_id", 0))
    except (ValueError, TypeError):
        osm_id = 0

    return GeocodeItem(
        osmType=osm_type,
        osmId=osm_id,
        category=str(data.get("category", "")),
        type=str(data.get("type", "")),
        name=name if name else None,
        displayName=display_name,
        lat=lat,
        lon=lon,
        boundingBox=bounding_box,
        importance=importance,
        address=address_dto,
    )

