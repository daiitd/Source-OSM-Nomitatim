@echo off
chcp 65001 > nul
set BASE_URL=http://localhost:8080

echo ==========================================================
echo  MID SOFTWARE - DEMO CURL POC NOMINATIM (TUẦN 3)
echo ==========================================================

echo.
echo --- 1. [TASK 3.2] SEARCH THÀNH CÔNG (CACHE MISS LẦN 1) ---
curl -s "%BASE_URL%/api/v1/geocode/search?q=Chợ%%20Bến%%20Thành&limit=2"

echo.
echo.
echo --- 2. [TASK 3.4] SEARCH LẦN 2 (KIỂM TRA CACHE HIT) ---
curl -s "%BASE_URL%/api/v1/geocode/search?q=Chợ%%20Bến%%20Thành&limit=2"

echo.
echo.
echo --- 3. [TASK 3.2] SEARCH KHÔNG CÓ KẾT QUẢ (200 OK + RESULTS RỖNG) ---
curl -s "%BASE_URL%/api/v1/geocode/search?q=xyzxyzxyz12345"

echo.
echo.
echo --- 4. [TASK 3.1] LỖI VALIDATE SEARCH (q ^< 3 ký tự -^> 400) ---
curl -s "%BASE_URL%/api/v1/geocode/search?q=ab"

echo.
echo.
echo --- 5. [TASK 3.3] REVERSE TEST CASE R1: TỌA ĐỘ CÓ DỮ LIỆU (BẾN THÀNH) ---
curl -s "%BASE_URL%/api/v1/geocode/reverse?lat=10.7725&lon=106.6980&zoom=18"

echo.
echo.
echo --- 6. [TASK 3.3] REVERSE TEST CASE R2: TỌA ĐỘ BIỂN (0,0) (404 NO_RESULT) ---
curl -s "%BASE_URL%/api/v1/geocode/reverse?lat=0.0&lon=0.0"

echo.
echo.
echo --- 7. [TASK 3.3] REVERSE TEST CASE R3: ĐẢO THỨ TỰ LAT/LON (400 INVALID_COORDINATE) ---
curl -s "%BASE_URL%/api/v1/geocode/reverse?lat=106.6980&lon=10.7725"

echo.
echo.
echo --- 8. [TASK 3.4] XEM THỐNG KÊ CACHE ^& CIRCUIT BREAKER ---
curl -s "%BASE_URL%/api/v1/geocode/stats"

echo.
echo Demo hoàn tất!
pause

