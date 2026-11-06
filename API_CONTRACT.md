# TÀI LIỆU HỢP ĐỒNG API (API CONTRACT)
**Dự án:** Nghiên cứu tích hợp OpenStreetMap × Nominatim vào Backend  
**Đơn vị:** Công ty TNHH MID Software  
**Nhóm thực hiện:** Nguyễn Phương Đại · Dương Đức Quân  
**Giai đoạn:** Tuần 3 (02–06/11/2026) | Nghiệm thu: Sáng thứ Bảy, 07/11/2026  

---

## 1. BỐI CẢNH VÀ KIẾN TRÚC TỔNG QUÁT

```
+------------------+         +----------------------------+         +-------------------------------+
|  Client Web/App  |  ---->  |    Backend Proxy (POC)     |  ---->  | Public Nominatim OSM Server   |
|                  |  <----  | (Validate, Cache, DTO Map) |  <----  | (Rate limit: max 1 req/sec)   |
+------------------+         +----------------------------+         +-------------------------------+
```

Client ứng dụng không gọi trực tiếp máy chủ OpenStreetMap công cộng nhằm đảm bảo:
1. **Tuân thủ chính sách sử dụng (OSM Usage Policy):** Quản lý tập trung User-Agent, giới hạn tốc độ 1 request/giây, và lưu cache.
2. **Hợp đồng DTO ổn định:** Chuẩn hóa dữ liệu thô của Nominatim (chuỗi lat/lon, boundingBox đảo chiều) thành một cấu trúc đồng nhất, độc lập với nhà cung cấp bản đồ.
3. **Bảo vệ và quan sát:** Ghi log tập trung, ngắt mạch (circuit breaker) khi bị 429, retry có kiểm soát với 5xx/timeout.

---

## 2. DANH SÁCH ENDPOINTS NỘI BỘ

| Phương thức | Đường dẫn | Mục đích | Nominatim Upstream Tương Ứng |
| :--- | :--- | :--- | :--- |
| **GET** | `/api/v1/geocode/search` | Tìm kiếm địa danh / địa chỉ từ chuỗi văn bản | `/search?format=jsonv2` |
| **GET** | `/api/v1/geocode/reverse` | Truy vấn địa chỉ từ tọa độ địa lý `(lat, lon)` | `/reverse?format=jsonv2` |
| **GET** | `/api/v1/geocode/stats` | Giám sát trạng thái Cache, Circuit Breaker | *Nội bộ Backend* |
| **GET** | `/api/v1/geocode/logs` | Xem nhật ký có cấu trúc JSON thời gian thực | *Nội bộ Backend* |
| **POST**| `/api/v1/geocode/cache/clear` | Xóa trắng bộ nhớ đệm phục vụ thử nghiệm | *Nội bộ Backend* |

---

## 3. REQUEST DTO VÀ QUY TẮC VALIDATE

### 3.1. Endpoint Search: `GET /api/v1/geocode/search`

| Tham số | Kiểu dữ liệu | Bắt buộc | Mặc định | Quy tắc Validate & Xử lý |
| :--- | :--- | :---: | :---: | :--- |
| `q` | String | **Có** | — | Cắt khoảng trắng thừa (`trim`), gộp khoảng trắng liên tiếp. Độ dài từ 3 đến 200 ký tự. Không được chỉ chứa ký tự đặc biệt. |
| `limit` | Integer | Không | `5` | Giới hạn từ `1` đến `10` (Nominatim cho phép tối đa 40, backend áp trần 10 để giảm tải). |
| `lang` | String | Không | `"vi"` | Chỉ chấp nhận danh sách hợp lệ: `vi`, `en`, `fr`, `de`, `ja`, `zh`, `ru`. Chuyển thành header `Accept-Language`. |
| `country`| String | Không | `"vn"` | Mã quốc gia ISO 3166-1 alpha-2 gồm 2 ký tự thường. Chuyển thành query param `countrycodes`. |

### 3.2. Endpoint Reverse: `GET /api/v1/geocode/reverse`

| Tham số | Kiểu dữ liệu | Bắt buộc | Mặc định | Quy tắc Validate & Xử lý |
| :--- | :--- | :---: | :---: | :--- |
| `lat` | Float | **Có** | — | Số thực hữu hạn (không NaN/Inf). Miền giá trị: `[-90.0, 90.0]`. |
| `lon` | Float | **Có** | — | Số thực hữu hạn (không NaN/Inf). Miền giá trị: `[-180.0, 180.0]`. |
| `zoom` | Integer | Không | `18` | Miền giá trị `[3, 18]`. Zoom 18 = tòa nhà, zoom 10 = thành phố, zoom 3 = quốc gia. |
| `lang` | String | Không | `"vi"` | Tương tự search. |

> [!IMPORTANT]
> **Quy tắc phát hiện đảo thứ tự `lat` và `lon` (Inverted Coordinates Detection):**  
> - Nếu `|lat| > 90`: Trả lỗi ngay lập tức `INVALID_COORDINATE`.  
> - Đặc biệt với dữ liệu Việt Nam (`lat` ~ 8.5 đến 23.5, `lon` ~ 102.0 đến 110.0), nếu `lat` nằm trong khoảng [102, 110] và `lon` nằm trong khoảng [8, 24], backend trả thông điệp cảnh báo: *"Phát hiện lat và lon bị đảo thứ tự (Việt Nam: lat ~ [8, 24], lon ~ [102, 110])"*.  
> - Mọi lỗi validate bị từ chối với HTTP 400 và **không gửi bất kỳ request nào lên Nominatim**, giúp tiết kiệm hoàn toàn quota.

---

## 4. RESPONSE DTO THỐNG NHẤT (`GeocodeItem`)

Cả 2 endpoint Search và Reverse đều sử dụng chung cấu trúc đối tượng `GeocodeItem`:

```json
{
  "osmType": "way",
  "osmId": 24231889,
  "category": "amenity",
  "type": "marketplace",
  "name": "Chợ Bến Thành",
  "displayName": "Chợ Bến Thành, Đường Lê Lợi, Phường Bến Thành, Quận 1, Thành phố Hồ Chí Minh, 700000, Việt Nam",
  "lat": 10.7725,
  "lon": 106.6980,
  "boundingBox": {
    "south": 10.7718,
    "north": 10.7732,
    "west": 106.6973,
    "east": 106.6987
  },
  "importance": 0.62,
  "address": {
    "houseNumber": null,
    "street": "Đường Lê Lợi",
    "ward": "Phường Bến Thành",
    "district": "Quận 1",
    "city": "Thành phố Hồ Chí Minh",
    "province": "Thành phố Hồ Chí Minh",
    "postcode": "700000",
    "country": "Việt Nam",
    "countryCode": "vn"
  }
}
```

### Bảng Ánh Xạ Field (Nominatim jsonv2 &rarr; DTO Thống Nhất)

| Field Gốc Nominatim | Field trong DTO | Quy tắc chuyển đổi |
| :--- | :--- | :--- |
| `osm_type`, `osm_id` | `osmType`, `osmId` | Giữ nguyên kiểu chuỗi (`node`, `way`, `relation`) và số nguyên ID OSM. |
| `category`, `type` | `category`, `type` | Giữ nguyên phân loại ngữ nghĩa OSM (ví dụ: `amenity`, `highway`, `shop`). |
| `name` | `name` | Nếu chuỗi rỗng, fallback lấy phần đầu tiên của `display_name` trước dấu phẩy. |
| `display_name` | `displayName` | Giữ nguyên chuỗi địa chỉ đầy đủ do Nominatim sinh ra. |
| `lat`, `lon` *(chuỗi)* | `lat`, `lon` *(số)* | **Ép kiểu sang Float**. Tránh lỗi tính toán hình học phía frontend. |
| `boundingbox` *(mảng 4 chuỗi: south, north, west, east)* | `boundingBox` *({south, north, west, east})* | **Ép kiểu sang Float và chuyển thành Object có tên trường tường minh**. Loại bỏ sự nhầm lẫn với chuẩn GeoJSON `[west, south, east, north]`. |
| `importance` | `importance` | Số thực hoặc `null`. |
| `address.road` | `address.street` | Tên đường phố. |
| `address.suburb` / `quarter` / `neighbourhood` / `ward` | `address.ward` | Lấy giá trị đầu tiên tồn tại (Phường / Xã). |
| `address.city_district` / `district` / `county` | `address.district` | Lấy giá trị đầu tiên tồn tại (Quận / Huyện). |
| `address.city` / `town` / `village` | `address.city` | Lấy giá trị đầu tiên tồn tại (Thành phố / Thị xã). |
| `address.state` | `address.province` | Tỉnh / Thành phố trực thuộc trung ương. |
| `address.country_code` | `address.countryCode` | Chuyển thành chữ thường 2 ký tự (`vn`). |

---

## 5. MÔ HÌNH LỖI THỐNG NHẤT (ERROR MODEL)

Mọi phản hồi lỗi đều tuân thủ cấu trúc chuẩn:
```json
{
  "error": {
    "code": "UPSTREAM_TIMEOUT",
    "message": "Nominatim không phản hồi trong thời gian cho phép.",
    "requestId": "a1b2c3d4"
  }
}
```

| Mã lỗi (`code`) | HTTP Status | Tình huống kích hoạt | Ghi chú |
| :--- | :---: | :--- | :--- |
| `VALIDATION_ERROR` | **400** | Tham số sai định dạng, `q` quá ngắn, `limit` ngoài khoảng | Không gọi Nominatim |
| `INVALID_COORDINATE`| **400** | `lat`/`lon` ngoài miền hoặc phát hiện đảo thứ tự | Không gọi Nominatim |
| `NO_RESULT` | **404** | Reverse không tìm thấy đối tượng tại tọa độ biển/hoang mạc | Search rỗng trả 200, reverse rỗng trả 404 |
| `RATE_LIMITED` | **429** | Client gọi backend vượt ngưỡng | Có header `Retry-After` |
| `UPSTREAM_RATE_LIMITED` | **429** | Nominatim trả 429 hoặc Circuit Breaker đang BẬT | Có header `Retry-After`, không retry ngay |
| `UPSTREAM_TIMEOUT` | **504** | Nominatim không phản hồi quá 8s (đã retry 1 lần) | Timeout kết nối/đọc |
| `UPSTREAM_ERROR` | **502** | Nominatim trả lỗi máy chủ 5xx (đã retry 2 lần backoff) | Lỗi cụm máy chủ OSM |
| `UPSTREAM_BLOCKED` | **502** | Nominatim trả 403 Forbidden | Kiểm tra User-Agent / IP bị chặn |
| `UPSTREAM_BAD_RESPONSE`| **502** | Phản hồi từ Nominatim hỏng hoặc không ép được tọa độ | Lỗi phân tích cú pháp |
| `INTERNAL_ERROR` | **500** | Lỗi ngoại lệ chưa lường trước trong backend | Không để lộ stack trace |

