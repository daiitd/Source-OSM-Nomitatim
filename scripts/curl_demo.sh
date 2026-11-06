#!/usr/bin/env bash
# Script cURL demo tất cả các kịch bản của Tuần 3
BASE_URL="http://localhost:8080"

echo "=========================================================="
echo " MID SOFTWARE - DEMO CURL POC NOMINATIM (TUẦN 3)"
echo "=========================================================="

echo -e "\n--- 1. [TASK 3.2] SEARCH THÀNH CÔNG (CACHE MISS LẦN 1) ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/search?q=Chợ%20Bến%20Thành&limit=2" | jq .

echo -e "\n--- 2. [TASK 3.4] SEARCH LẦN 2 (KIỂM TRA CACHE HIT) ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/search?q=Chợ%20Bến%20Thành&limit=2" | jq .

echo -e "\n--- 3. [TASK 3.2] SEARCH KHÔNG CÓ KẾT QUẢ (200 OK + RESULTS RỖNG) ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/search?q=xyzxyzxyz12345" | jq .

echo -e "\n--- 4. [TASK 3.1] LỖI VALIDATE SEARCH (q < 3 ký tự -> 400) ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/search?q=ab" | jq .

echo -e "\n--- 5. [TASK 3.3] REVERSE TEST CASE R1: TỌA ĐỘ CÓ DỮ LIỆU (BẾN THÀNH) ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/reverse?lat=10.7725&lon=106.6980&zoom=18" | jq .

echo -e "\n--- 6. [TASK 3.3] REVERSE TEST CASE R2: TỌA ĐỘ BIỂN (0,0) (404 NO_RESULT) ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/reverse?lat=0.0&lon=0.0" | jq .

echo -e "\n--- 7. [TASK 3.3] REVERSE TEST CASE R3: ĐẢO THỨ TỰ LAT/LON (400 INVALID_COORDINATE) ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/reverse?lat=106.6980&lon=10.7725" | jq .

echo -e "\n--- 8. [TASK 3.4] XEM THỐNG KÊ CACHE & CIRCUIT BREAKER ---"
curl -s -X GET "$BASE_URL/api/v1/geocode/stats" | jq .

