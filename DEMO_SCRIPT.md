# KỊCH BẢN DEMO NGHIỆM THU TUẦN 3 (40 PHÚT)
**Nội dung:** Báo cáo thực hành tích hợp Nominatim vào Backend — Search, Reverse và chuẩn hóa kết quả  
**Thời gian trình bày:** Sáng thứ Bảy, 07/11/2026  
**Người trình bày:** Nguyễn Phương Đại · Dương Đức Quân  
**Đơn vị nghiệm thu:** Công ty TNHH MID Software  

---

## 1. PHÂN BỔ THỜI LƯỢNG (BẢNG 14)

| Thời lượng | Nội dung trình bày | Công cụ / Minh chứng |
| :---: | :--- | :--- |
| **0 – 3'** | Giới thiệu mục tiêu tuần 3; sơ đồ kiến trúc Client &rarr; Backend Proxy &rarr; Nominatim OSM. | Slide 1–2 + Sơ đồ kiến trúc |
| **3 – 10'** | **Hợp đồng API (Task 3.1):** Trình bày Request/Response DTO, quy tắc validate, mô hình lỗi; chạy thử lỗi đảo `lat`/`lon`. | Swagger UI (`/docs`) + `API_CONTRACT.md` |
| **10 – 18'**| **Demo Endpoint Search (Task 3.2):** Tìm kiếm có kết quả ("Chợ Bến Thành"), tìm kiếm rỗng ("xyzxyzxyz"); so sánh dữ liệu DTO với JSON gốc của Nominatim. | Dashboard (`http://localhost:8080/`) + Postman/cURL |
| **18 – 25'**| **Demo Endpoint Reverse (Task 3.3):** Trình diễn 3 test cases bắt buộc (R1: có kết quả, R2: biển 0,0 &rarr; 404, R3: đảo tọa độ &rarr; 400); giải thích lý do kết quả phụ thuộc dữ liệu cộng đồng OSM. | Postman Collection / Dashboard Test Buttons |
| **25 – 32'**| **Cache, Điều tốc & Xử lý lỗi (Task 3.4):** Chạy lại request thứ hai để thấy Cache Hit (thời gian phản hồi từ ~400ms xuống < 1ms); mô phỏng kịch bản lỗi 429 và ngắt mạch Circuit Breaker không retry dồn dập. | Script `simulate_scenarios.py` + JSON Log |
| **32 – 40'**| **Tổng kết & Reviewer thử nghiệm:** Hướng dẫn reviewer chạy lệnh `python run.py`, chạy unit tests `python -m unittest`, hỏi đáp (Q&A). | `README.md` + Live Terminal |

---

## 2. DIỄN GIẢI CHI TIẾT PIPELINE 10 BƯỚC (TỪ INPUT ĐẾN RESPONSE)

Khi nhận câu hỏi từ Reviewer: *"Mô tả pipeline xử lý một request geocoding qua backend?"*, trình bày theo 10 bước:

```
[1. Nhận Input] (Query parameters: q, lat, lon, limit, zoom, country, lang)
       │
       ▼
[2. Validate Chặt Chẽ]
   ├── Sai định dạng, q < 3 ký tự, limit > 10 ─────────► [Trả 400 VALIDATION_ERROR] (Dừng, 0 call upstream)
   └── lat/lon sai miền, nghi đảo thứ tự (lat > 90) ───► [Trả 400 INVALID_COORDINATE] (Dừng, 0 call upstream)
       │
       ▼
[3. Chuẩn Hóa & Tạo Khóa Cache]
   ├── Search: lowercase, trim, gộp khoảng trắng -> "search:chợ bến thành:5:vi:vn"
   └── Reverse: làm tròn 5 số thập phân (~1.1m) -> "reverse:10.77250:106.69800:18:vi"
       │
       ▼
[4. Tra Bộ Nhớ Đệm (Cache Lookup)]
   ├── CACHE HIT ──────────────────────────────────────► [Đánh dấu meta.cached=true -> Trả ngay 200 OK] (0ms upstream)
   └── CACHE MISS ──┐
                    ▼
[5. Điều Tốc & Kiểm Tra Ngắt Mạch (Rate Limiter & Circuit Breaker)]
   ├── Circuit Breaker đang OPEN (sau khi bị 429) ──────► [Trả ngay 429 UPSTREAM_RATE_LIMITED + Retry-After] (Không spam)
   └── Chờ đảm bảo tần suất <= 1 request/giây
                    │
                    ▼
[6. Gửi Request Tới Upstream Nominatim]
   ├── Gửi kèm User-Agent định danh: "MidSoftware-GeoPOC/0.1 (contact: contact@midsoftware.com)"
   ├── Timeouts: Connect 3s, Read 8s
   └── Gặp 429 -> BẬT NGẮT MẠCH NGAY LẬP TỨC (Không retry!)
   └── Gặp 5xx -> Retry tối đa 2 lần với Exponential Backoff + Jitter
   └── Gặp Timeout -> Retry tối đa 1 lần sau 1s
                    │
                    ▼
[7. Phân Tích Phản Hồi (Response Parsing)]
   ├── Reverse trả {"error": "Unable to geocode"} ─────► [Lưu Negative Cache 60s -> Trả 404 NO_RESULT]
   └── Search trả [] (Mảng rỗng) ──────────────────────► [Lưu Negative Cache 60s -> Trả 200 count=0, results=[]]
                    │
                    ▼
[8. Ánh Xạ DTO Thống Nhất (Data Mapping)]
   ├── Ép kiểu lat, lon từ chuỗi sang float
   ├── Chuyển boundingbox 4 chuỗi [south, north, west, east] sang Object có tên trường tường minh
   ├── Gom nhóm phân cấp địa chỉ: street, ward, district, city, province, countryCode
   └── Fallback trường name nếu rỗng
                    │
                    ▼
[9. Lưu Vào Bộ Nhớ Đệm (Cache Storage)]
   └── Lưu kết quả thành công với TTL = 3600 giây (1 giờ)
                    │
                    ▼
[10. Trả Response Về Client & Ghi Structured Log]
   └── Ghi JSON Log 1 dòng: ts, requestId, endpoint, cache, upstreamStatus, upstreamMs, outcome
```

---

## 3. CÂU HỎI THƯỜNG GẶP KHI BẢO VỆ (DEFENSE Q&A)

### Q1: Tại sao không để Client (Web/Mobile) gọi trực tiếp Nominatim mà phải dựng Backend Proxy?
> **Trả lời:**
> 1. **Chính sách máy chủ công cộng (Quota):** Nếu 1.000 thiết bị client cùng gọi trực tiếp thì không thể kiểm soát giới hạn 1 req/sec và định danh User-Agent tập trung. Hệ thống sẽ bị OpenStreetMap chặn IP ngay lập tức.
> 2. **Hợp đồng DTO ổn định:** Nominatim trả kiểu dữ liệu chuỗi cho tọa độ, mảng boundingbox dễ nhầm thứ tự, và các key địa chỉ (`quarter`, `suburb`, `residential`) thay đổi theo từng khu vực. Backend chuẩn hóa giúp client nhận dữ liệu sạch, nhất quán.
> 3. **Độc lập hạ tầng:** Khi dự án chuyển từ máy chủ công cộng sang cụm Nominatim riêng hoặc dịch vụ trả phí, frontend hoàn toàn không phải sửa một dòng mã nào.

### Q2: Vì sao khi gặp 429 Too Many Requests lại không được retry ngay?
> **Trả lời:**
> Khi máy chủ trả 429 nghĩa là họ đang trong tình trạng quá tải hoặc ứng dụng đã vi phạm quota. Nếu tiếp tục gửi request thử lại dồn dập, máy chủ sẽ đánh giá đây là hành vi tấn công từ chối dịch vụ (DoS) và chặn vĩnh viễn IP (HTTP 403 Forbidden).  
> Giải pháp chuẩn là kích hoạt **Circuit Breaker**, dừng ngay lập tức mọi lượt gọi trong thời gian `Retry-After`, phục vụ dữ liệu từ Cache nếu có và trả lỗi 429 cho client kèm thời gian chờ.

### Q3: Vì sao Reverse Geocoding tại tọa độ `(0, 0)` lại trả 404 NO_RESULT mà không phải 200 kết quả rỗng?
> **Trả lời:**
> Search là bài toán tìm kiếm tập hợp danh sách (trả về mảng, không tìm thấy thì mảng rỗng `count: 0`).  
> Reverse là bài toán tìm một thực thể địa chỉ đại diện cho một điểm cụ thể. Khi điểm đó rơi vào vùng đại dương không có dữ liệu OSM, không có tài nguyên nào được tìm thấy, do đó theo chuẩn RESTful việc trả HTTP 404 NO_RESULT là chính xác về mặt ngữ nghĩa.

