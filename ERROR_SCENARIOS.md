# BẢNG KỊCH BẢN LỖI, CHIẾN LƯỢC CACHE VÀ QUAN SÁT
**Dự án:** Tích hợp Nominatim vào Backend (Tuần 3)  
**Nhóm thực hiện:** Nguyễn Phương Đại · Dương Đức Quân — Công ty TNHH MID Software  

---

## 1. CHIẾN LƯỢC GIẢM CALL API VÀ BỘ NHỚ ĐỆM (CACHE STRATEGY)

Để tuân thủ nghiêm ngặt chính sách [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/) (tối đa ~1 request/giây):
1. **Khóa Cache Search:** `search:<q_lowercase_trimmed>:<limit>:<lang>:<country>`  
   - Ví dụ: `search:chợ bến thành:5:vi:vn`
   - TTL kết quả thành công: **3600 giây (1 giờ)**.
   - Negative Cache (tìm kiếm rỗng): **60 giây** để tránh bị spam liên tục cùng một từ khóa vô nghĩa.
2. **Khóa Cache Reverse:** `reverse:<lat_5_decimals>:<lon_5_decimals>:<zoom>:<lang>`  
   - Làm tròn tọa độ đến 5 chữ số thập phân (tương đương độ chính xác ~1.1 mét) để tăng tỷ lệ Cache Hit giữa các thiết bị GPS có độ lệch nhỏ.
   - TTL kết quả thành công: **3600 giây (1 giờ)**.
   - Negative Cache (404 NO_RESULT): **60 giây**.
3. **Bộ điều tốc Backend (Rate Limiter):**  
   - Áp dụng cơ chế khóa phân luồng (Mutex lock) đo `elapsed_time = now - last_request_time`.
   - Nếu `elapsed_time < 1.0s`, luồng gọi tự động ngủ (`time.sleep(1.0 - elapsed)`) trước khi gửi request tới Nominatim, đảm bảo tần suất phát ra luôn `<= 1 req/sec`.

---

## 2. BẢNG KỊCH BẢN LỖI VÀ CHÍNH SÁCH XỬ LÝ (ERROR MATRIX)

| Kịch bản | Dấu hiệu nhận biết | Hành vi xử lý của Backend | Phản hồi trả về Client |
| :--- | :--- | :--- | :--- |
| **429 Too Many Requests** | Nominatim trả HTTP 429 | **TUYỆT ĐỐI KHÔNG RETRY!** Đọc header `Retry-After` (mặc định 60s), **BẬT NGẮT MẠCH (Circuit Breaker OPEN)**. Mọi request mới trong thời gian cooldown bị từ chối ngay lập tức tại backend. Phục vụ dữ liệu cũ từ cache nếu có. | HTTP `429 UPSTREAM_RATE_LIMITED` kèm header `Retry-After: <số giây>` |
| **Timeout** | Quá Connect Timeout (3s) hoặc Read Timeout (8s) | Cho phép **thử lại tối đa 1 lần** sau khoảng chờ 1.0 giây nếu chưa hết thời hạn request. Không retry nếu ngắt mạch đang mở. | HTTP `504 UPSTREAM_TIMEOUT` |
| **5xx Server Error** | Nominatim trả 500, 502, 503, 504 | Cho phép **thử lại tối đa 2 lần** với thuật toán **Exponential Backoff có Jitter ngẫu nhiên** (`base * 2^attempt + rand(0.1, 0.4)`). Nếu vẫn lỗi thì dừng. | HTTP `502 UPSTREAM_ERROR` |
| **403 Forbidden** | Nominatim trả HTTP 403 | **KHÔNG RETRY**. Ghi log mức ERROR cảnh báo vi phạm User-Agent hoặc bị chặn IP vĩnh viễn. | HTTP `502 UPSTREAM_BLOCKED` |
| **Phản hồi hỏng / Thiếu tọa độ** | Không phải JSON hoặc `lat`/`lon` không thể ép sang số | **KHÔNG RETRY**. Bắt ngoại lệ và ghi log phần đầu phản hồi. | HTTP `502 UPSTREAM_BAD_RESPONSE` |
| **Search rỗng** | Mảng `[]` từ Nominatim | **KHÔNG PHẢI LỖI**. Lưu negative cache 60s. | HTTP `200 OK`, `count = 0`, `results = []` |
| **Reverse ngoài vùng dữ liệu** | Phản hồi có `{"error": "Unable to geocode"}` | **KHÔNG PHẢI LỖI HỆ THỐNG**. Lưu negative cache 60s. | HTTP `404 NO_RESULT` |
| **Đầu vào không hợp lệ** | Vi phạm quy tắc validate (q quá ngắn, lat > 90, đảo tọa độ) | **CHẶN NGAY TẠI TẦNG VALIDATE**, 0 request gửi lên Nominatim. | HTTP `400 VALIDATION_ERROR` hoặc `INVALID_COORDINATE` |

---

## 3. LOG MẪU CÓ CẤU TRÚC (STRUCTURED JSON LOGS)

Mỗi request được ghi nhận dưới định dạng 1 dòng JSON trên file `logs/access.jsonl`:

```json
{"ts": "2026-11-05T09:41:12+07:00", "requestId": "a1b2c3d4", "endpoint": "search", "cache": "miss", "upstreamStatus": 200, "upstreamMs": 412, "outcome": "ok"}
{"ts": "2026-11-05T09:41:13+07:00", "requestId": "b2c3d4e5", "endpoint": "search", "cache": "hit", "upstreamStatus": null, "upstreamMs": null, "outcome": "ok"}
{"ts": "2026-11-05T10:15:22+07:00", "requestId": "c3d4e5f6", "endpoint": "reverse", "cache": "miss", "upstreamStatus": 200, "upstreamMs": 18, "outcome": "no_result"}
{"ts": "2026-11-05T15:20:01+07:00", "requestId": "d4e5f6a1", "endpoint": "search", "cache": "miss", "upstreamStatus": 429, "upstreamMs": 95, "outcome": "upstream_rate_limited", "circuitOpenSec": 60}
{"ts": "2026-11-05T15:20:02+07:00", "requestId": "e5f6a1b2", "endpoint": "search", "cache": "none", "upstreamStatus": null, "upstreamMs": null, "outcome": "upstream_rate_limited", "circuitOpenSec": 59}
{"ts": "2026-11-05T16:05:10+07:00", "requestId": "f6a1b2c3", "endpoint": "reverse", "cache": "none", "upstreamStatus": null, "upstreamMs": null, "outcome": "invalid_coordinate"}
```

---

## 4. CHỈ SỐ QUAN SÁT (OBSERVABILITY METRICS)

Được cung cấp qua API `GET /api/v1/geocode/stats`:
1. `cache.activeEntries`: Số lượng truy vấn đang được lưu trong RAM.
2. `cache.totalHits` & `cache.totalMisses`: Số lần trúng / trượt cache.
3. `cache.hitRatioPercent`: Tỷ lệ trúng cache (`Hits / (Hits + Misses) * 100%`).
4. `circuitBreaker.state`: Trạng thái ngắt mạch (`CLOSED` bình thường, `OPEN` đang làm mát sau khi bị 429).
5. `circuitBreaker.remainingCooldownSec`: Số giây còn lại trước khi Circuit Breaker phục hồi.

