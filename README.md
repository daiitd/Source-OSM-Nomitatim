# MID Software | OpenStreetMap × Nominatim Backend POC (Tuần 3)

Dự án mẫu thực hành tích hợp dịch vụ Geocoding OpenStreetMap Nominatim vào Backend, chuẩn hóa kết quả, quản lý bộ nhớ đệm (Cache), điều tốc và quan sát lỗi theo đúng lộ trình nghiên cứu **RESEARCH ROADMAP | TUẦN 3 (02–06/11/2026)**.

- **Đơn vị thực tập:** Công ty TNHH MID Software  
- **Nhóm thực hiện:** Nguyễn Phương Đại · Dương Đức Quân  
- **Thời gian nghiệm thu:** Sáng thứ Bảy, 07/11/2026  

---

## 1. BẢNG CHECKLIST BÀN GIAO THEO YÊU CẦU NGHIỆM THU

| Task | Tên Task & Phạm vi nghiên cứu | Sản phẩm bàn giao | Tiêu chí nghiệm thu | Trạng thái |
| :---: | :--- | :--- | :--- | :---: |
| **3.1** | **Thiết kế hợp đồng API**<br>Xác định endpoint search/reverse nội bộ, request DTO, response DTO, mô hình lỗi. | [API_CONTRACT.md](./API_CONTRACT.md)<br>OpenAPI 3.0 / Swagger UI | Thiết kế rành mạch input/output, validate chặt chẽ lat/lon, phát hiện đảo tọa độ, áp trần limit. | **ĐẠT (100%)** |
| **3.2** | **Backend POC Search**<br>Tạo endpoint proxy Search, map field OSM về DTO thống nhất. | Source code `app/`<br>cURL & Postman Collection | Có error handling, timeout (connect 3s, read 8s), User-Agent hợp lệ theo chính sách public endpoint. | **ĐẠT (100%)** |
| **3.3** | **Backend POC Reverse**<br>Tạo endpoint reverse, xử lý tình huống không có kết quả. | Source code + **3 Test Cases** (`tests/test_reverse.py`) | Bắt kết quả truy đổi theo dữ liệu OSM (không giả định tọa độ nào cũng ra địa chỉ chính xác). | **ĐẠT (100%)** |
| **3.4** | **Cache, Limit và Quan sát lỗi**<br>Đề xuất cache đơn giản; phân biệt 429 / timeout / 5xx. | [ERROR_SCENARIOS.md](./ERROR_SCENARIOS.md)<br>File log mẫu `logs/access.jsonl` | Nêu được chiến lược giảm call API, điều tốc 1 req/sec, Circuit Breaker KHÔNG retry 429 liên tục. | **ĐẠT (100%)** |
| **3.5** | **Demo Tuần 3 & Diễn giải Pipeline**<br>Demo 2 endpoint và diễn giải pipeline từ input đến response. | [DEMO_SCRIPT.md](./DEMO_SCRIPT.md)<br>Interactive Dashboard UI | Reviewer có thể cài/chạy ngay trong 1 dòng lệnh; mô tả đầy đủ pipeline 10 bước. | **ĐẠT (100%)** |

---

## 2. CẤU TRÚC THƯ MỤC DỰ ÁN

```
source/
├── app/
│   ├── __init__.py           # Khởi tạo Flask Application & CORS
│   ├── config.py             # Cấu hình tham số: Timeout, User-Agent, Cache TTL, Rate limit
│   ├── dtos.py               # Request/Response DTOs, Validation logic & Ngoại lệ nghiệp vụ
│   ├── mapper.py             # Mapper ánh xạ dữ liệu thô Nominatim -> DTO thống nhất GeocodeItem
│   ├── cache.py              # In-memory TTL Cache (hỗ trợ positive cache 1h & negative cache 60s)
│   ├── rate_limiter.py       # Rate Limiter (1 req/sec) & Circuit Breaker cho 429
│   ├── client.py             # HTTP Client gọi Nominatim OSM (có retry backoff & fallback mock)
│   ├── logger.py             # Structured JSON Logger ghi file logs/access.jsonl
│   ├── routes.py             # Pipeline 10 bước xử lý Search, Reverse, Stats, Logs
│   ├── openapi.py            # Đặc tả OpenAPI 3.0 spec JSON (/api/v1/openapi.json)
│   └── views.py              # Giao diện Web Dashboard Demo (/) và Swagger Docs (/docs)
├── mock_server/
│   └── server.py             # Máy chủ giả lập Nominatim độc lập phục vụ test offline/lỗi
├── tests/
│   ├── test_validation.py    # Kiểm thử validate input: độ dài q, limit, lat/lon swap
│   ├── test_mapper.py        # Kiểm thử ép kiểu tọa độ sang float, boundingbox, phân cấp address
│   ├── test_search.py        # Kiểm thử search thành công, cache hit, kết quả rỗng
│   ├── test_reverse.py       # Kiểm thử 3 Test Cases bắt buộc (R1, R2, R3)
│   └── test_resilience.py    # Kiểm thử ngắt mạch Circuit Breaker khi gặp 429
├── postman/
│   └── Nominatim_POC_Tuan_3.postman_collection.json  # Postman collection kèm test script tự động
├── scripts/
│   ├── simulate_scenarios.py # Script CLI mô phỏng sinh động toàn bộ kịch bản nghiệm thu
│   ├── curl_demo.sh          # Script cURL dành cho môi trường Linux/macOS
│   └── curl_demo.bat         # Script cURL dành cho môi trường Windows
├── logs/
│   └── access.jsonl          # File nhật ký có cấu trúc JSON theo thời gian thực
├── API_CONTRACT.md           # Tài liệu đặc tả Hợp đồng API chi tiết
├── ERROR_SCENARIOS.md        # Ma trận kịch bản lỗi, chiến lược retry và quan sát
├── DEMO_SCRIPT.md            # Kịch bản thuyết trình và diễn giải pipeline 40 phút
├── run.py                    # Điểm khởi chạy Backend Server chính
└── requirements.txt          # Danh sách thư viện Python
```

---

## 3. HƯỚNG DẪN CÀI ĐẶT VÀ CHẠY NHANH

### Yêu cầu môi trường
- Python 3.10 trở lên (đã kiểm thử tương thích hoàn hảo trên Python 3.13)
- Các thư viện tiêu chuẩn: `flask`, `flask-cors`, `requests`

### Khởi động Server
Chạy lệnh trực tiếp từ thư mục `source/`:
```bash
python run.py
```

Server sẽ lắng nghe tại:
- **Giao diện Demo trực quan (Dashboard):** [http://localhost:8080/](http://localhost:8080/)
- **Tài liệu Swagger / OpenAPI UI:** [http://localhost:8080/docs](http://localhost:8080/docs)
- **Endpoint Search:** `http://localhost:8080/api/v1/geocode/search`
- **Endpoint Reverse:** `http://localhost:8080/api/v1/geocode/reverse`
- **Chỉ số giám sát (Stats):** `http://localhost:8080/api/v1/geocode/stats`

---

## 4. CÁCH KIỂM THỬ VÀ TÁI HIỆN KẾT QUẢ CHO REVIEWER

### Cách 1: Chạy toàn bộ Unit Tests tự động (17/17 tests PASS)
```bash
python -m unittest discover tests
```
Tất cả 17 ca kiểm thử (Validation, DTO Mapper, Search, 3 Reverse Cases, Circuit Breaker) sẽ chạy trong ~3 giây và báo `OK`.

### Cách 2: Chạy Script mô phỏng kịch bản (Recommended for Demo)
```bash
python scripts/simulate_scenarios.py
```
Script sẽ tự động chạy qua:
1. **Search Cache Miss & Cache Hit:** Thời gian phản hồi giảm từ ~11ms xuống < 1ms.
2. **Reverse 3 Test Cases:**
   - **R1:** Chợ Bến Thành (`lat=10.7725, lon=106.6980`) &rarr; `200 OK`.
   - **R2:** Giữa biển (`lat=0.0, lon=0.0`) &rarr; `404 NO_RESULT`.
   - **R3:** Đảo thứ tự (`lat=106.6980, lon=10.7725`) &rarr; `400 INVALID_COORDINATE`.
3. **Mô phỏng 429 Too Many Requests:** Ngắt mạch BẬT (OPEN), backend từ chối nhanh không gửi request lên upstream, trả header `Retry-After: 30`.

### Cách 3: Chạy bằng cURL
- Trên Windows Command Prompt / PowerShell:
  ```cmd
  scripts\curl_demo.bat
  ```
- Hoặc trên Linux/macOS:
  ```bash
  bash scripts/curl_demo.sh
  ```

### Cách 4: Nhập Postman Collection
Nhập file `postman/Nominatim_POC_Tuan_3.postman_collection.json` vào Postman. Bộ sưu tập đã có sẵn test script tự động kiểm tra HTTP Status và Schema.

---

## 5. BA TEST CASES REVERSE (TASK 3.3 - BẢNG 10)

| Mã Case | Tọa độ đầu vào | Kết quả kỳ vọng | Ý nghĩa & Tiêu chí nghiệm thu |
| :---: | :--- | :---: | :--- |
| **R1** | `lat=10.7725, lon=106.6980, zoom=18` (Bến Thành, TP.HCM) | **200 OK** | Tọa độ có dữ liệu địa chỉ; quan sát phân cấp `address` và ép kiểu `lat/lon` thành số thực. |
| **R2** | `lat=0.0, lon=0.0` (Vịnh Guinea giữa đại dương) | **404 NO_RESULT** | Xử lý tình huống không có kết quả mà không làm sập server; không giả định tọa độ nào cũng có địa chỉ. |
| **R3** | `lat=106.6980, lon=10.7725` (Đảo thứ tự lat/lon) | **400 INVALID_COORDINATE** | Phát hiện tọa độ bị đảo; trả thông báo cảnh báo thông minh; chặn ngay tại backend, 0 request gửi lên OSM. |

---

## 6. THÔNG TIN LIÊN HỆ VÀ BẢN QUYỀN
- **Nhóm thực tập sinh:** Nguyễn Phương Đại & Dương Đức Quân
- **Đơn vị công tác:** Công ty TNHH MID Software
- **Nguồn dữ liệu địa lý:** Dữ liệu bản đồ thuộc bản quyền © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright).

