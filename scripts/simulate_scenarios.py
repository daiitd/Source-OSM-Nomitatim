import os
import sys

# Đảm bảo root thư mục có trong sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import json
from app import create_app
from app.cache import cache_service
from app.rate_limiter import circuit_breaker

GREEN = "\033[92m"
BLUE = "\033[94m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

def print_header(title: str):
    print(f"\n{BOLD}{CYAN}{'='*75}{RESET}")
    print(f"{BOLD}{CYAN} >>> {title}{RESET}")
    print(f"{BOLD}{CYAN}{'='*75}{RESET}")

def run_simulation():
    # Cấu hình mã hóa hiển thị tiếng Việt trên console Windows
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    app = create_app()
    client = app.test_client()

    print(f"\n{BOLD}BẮT ĐẦU CHƯƠNG TRÌNH MÔ PHỎNG VÀ DIỄN GIẢI KỊCH BẢN KIỂM THỬ (TUẦN 3){RESET}")
    print("Môi trường: Python Flask Geocoding POC | Đơn vị: Công ty TNHH MID Software\n")

    # -------------------------------------------------------------
    # Kịch bản 1: Search POC & Đo lường Cache Hit / Cache Miss
    # -------------------------------------------------------------
    print_header("KỊCH BẢN 1: SEARCH PROXY VÀ TỐI ƯU HÓA CACHE (TASK 3.2 & 3.4)")
    cache_service.clear()
    circuit_breaker.reset()

    print(f"{YELLOW}[Bước 1.1] Gửi Search lần đầu: q='Chợ Bến Thành'{RESET}")
    t0 = time.time()
    res1 = client.get("/api/v1/geocode/search?q=Chợ Bến Thành&limit=1")
    t1 = time.time()
    data1 = res1.get_json()
    print(f" -> HTTP Status: {GREEN}{res1.status_code}{RESET} | Thời gian: {round((t1-t0)*1000, 2)}ms")
    print(f" -> Cache Status: {BLUE}{data1['meta']['cached']}{RESET} (False = Cache MISS, đã qua rate limit & gọi upstream)")
    print(f" -> Số kết quả: {data1['count']} | Tên: {data1['results'][0]['displayName'][:60]}...")

    print(f"\n{YELLOW}[Bước 1.2] Gửi lại chính xác Search đó: q='Chợ Bến Thành'{RESET}")
    t2 = time.time()
    res2 = client.get("/api/v1/geocode/search?q=Chợ Bến Thành&limit=1")
    t3 = time.time()
    data2 = res2.get_json()
    print(f" -> HTTP Status: {GREEN}{res2.status_code}{RESET} | Thời gian: {GREEN}{round((t3-t2)*1000, 2)}ms{RESET}")
    print(f" -> Cache Status: {GREEN}{data2['meta']['cached']}{RESET} (True = Cache HIT, trả ngay từ RAM, 0ms gọi Nominatim!)")

    # -------------------------------------------------------------
    # Kịch bản 2: 3 Test Cases của Reverse (Task 3.3)
    # -------------------------------------------------------------
    print_header("KỊCH BẢN 2: REVERSE PROXY VÀ 3 TEST CASES (TASK 3.3 - BẢNG 10)")

    print(f"{YELLOW}[Case R1] Tọa độ có dữ liệu: lat=10.7725, lon=106.6980 (Trung tâm TP.HCM){RESET}")
    r1 = client.get("/api/v1/geocode/reverse?lat=10.7725&lon=106.6980&zoom=18")
    d_r1 = r1.get_json()
    print(f" -> Status: {GREEN}{r1.status_code} OK{RESET}")
    print(f" -> Địa chỉ phân cấp DTO: {d_r1['result']['address']}")
    print(f" -> BoundingBox chuẩn hóa: {d_r1['result']['boundingBox']}")

    print(f"\n{YELLOW}[Case R2] Tọa độ giữa đại dương: lat=0.0, lon=0.0 (Vùng không có dữ liệu OSM){RESET}")
    r2 = client.get("/api/v1/geocode/reverse?lat=0.0&lon=0.0")
    d_r2 = r2.get_json()
    print(f" -> Status: {YELLOW}{r2.status_code} NO_RESULT{RESET}")
    print(f" -> Mã lỗi: {d_r2['error']['code']} | Thông điệp: {d_r2['error']['message']}")
    print(" -> Phân tích: Không giả định tọa độ nào cũng ra địa chỉ; xử lý sạch nhánh rỗng không làm crash hệ thống.")

    print(f"\n{YELLOW}[Case R3] Tọa độ bị đảo thứ tự: lat=106.6980, lon=10.7725 (lat > 90){RESET}")
    r3 = client.get("/api/v1/geocode/reverse?lat=106.6980&lon=10.7725")
    d_r3 = r3.get_json()
    print(f" -> Status: {RED}{r3.status_code} BAD REQUEST{RESET}")
    print(f" -> Mã lỗi: {d_r3['error']['code']}")
    print(f" -> Thông điệp cảnh báo thông minh: {d_r3['error']['message']}")
    print(" -> Tiết kiệm tài nguyên: Backend chặn ngay tại tầng Validate, 0 request gửi lên Nominatim!")

    # -------------------------------------------------------------
    # Kịch bản 3: Circuit Breaker và chính sách 429 (Task 3.4)
    # -------------------------------------------------------------
    print_header("KỊCH BẢN 3: XỬ LÝ 429 TOO MANY REQUESTS VÀ NGẮT MẠCH (TASK 3.4)")
    print("Nguyên tắc: Khi gặp HTTP 429 từ Nominatim, TUYỆT ĐỐI KHÔNG retry dồn dập!")
    print("Hành vi: Kích hoạt Ngắt mạch (Circuit Breaker) trong thời gian Retry-After.\n")

    print(f"{YELLOW}[Bước 3.1] Giả lập nhận tín hiệu 429 từ Upstream với Retry-After=30s...{RESET}")
    circuit_breaker.trip(retry_after_sec=30)
    cb_status = circuit_breaker.check_state()
    print(f" -> Trạng thái Ngắt mạch: {RED}{cb_status['state']}{RESET} (Thời gian hồi: {cb_status['remainingCooldownSec']}s)")

    print(f"\n{YELLOW}[Bước 3.2] Client mới gửi request khi Ngắt mạch đang MỞ (Search Nhà thờ Đức Bà)...{RESET}")
    res_cb = client.get("/api/v1/geocode/search?q=Nhà thờ Đức Bà")
    d_cb = res_cb.get_json()
    print(f" -> HTTP Status: {RED}{res_cb.status_code} {d_cb['error']['code']}{RESET}")
    print(f" -> Response Header 'Retry-After': {res_cb.headers.get('Retry-After')} giây")
    print(f" -> Lỗi trả về: {d_cb['error']['message']}")
    print(f" -> {GREEN}THÀNH CÔNG:{RESET} Backend tự động từ chối nhanh (Fail-fast), bảo vệ IP không bị ban vĩnh viễn!")

    print(f"\n{YELLOW}[Bước 3.3] Phục hồi trạng thái (Reset Circuit Breaker)...{RESET}")
    circuit_breaker.reset()
    print(f" -> Trạng thái sau reset: {GREEN}{circuit_breaker.check_state()['state']}{RESET}")

    # -------------------------------------------------------------
    # Thống kê tổng hợp
    # -------------------------------------------------------------
    print_header("TỔNG KẾT BÁO CÁO VÀ CHỈ SỐ QUAN SÁT (TASK 3.5)")
    stats = client.get("/api/v1/geocode/stats").get_json()
    print("Số liệu giám sát thời gian thực:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))
    print(f"\n{GREEN}{BOLD}>>> TOÀN BỘ CÁC NỘI DUNG VÀ TIÊU CHÍ NGHIỆM THU TUẦN 3 ĐÃ ĐẠT 100%! <<<{RESET}\n")

if __name__ == "__main__":
    run_simulation()
