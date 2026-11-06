import unittest
from app import create_app
from app.cache import cache_service
from app.rate_limiter import circuit_breaker

class TestReverse(unittest.TestCase):
    """
    Hiện thực và kiểm thử 3 test cases của Task 3.3 theo đúng Bảng 10:
    R1: Tọa độ có dữ liệu (Chợ Bến Thành, TP.HCM) -> 200 OK
    R2: Tọa độ ở vùng không có dữ liệu (vịnh Guinea giữa biển 0,0) -> 404 NO_RESULT
    R3: Tọa độ bị đảo thứ tự (lat=106.6980, lon=10.7725) -> 400 INVALID_COORDINATE
    """
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        circuit_breaker.reset()
        cache_service.clear()

    def tearDown(self):
        circuit_breaker.reset()
        cache_service.clear()

    def test_case_r1_valid_coordinates(self):
        """[R1] Tọa độ có dữ liệu tại trung tâm TP.HCM -> 200 OK."""
        res = self.client.get("/api/v1/geocode/reverse?lat=10.7725&lon=106.6980&zoom=18")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("result", data)
        item = data["result"]
        self.assertEqual(item["osmType"], "way")
        self.assertIsInstance(item["lat"], float)
        self.assertIsInstance(item["lon"], float)
        self.assertIn("address", item)
        self.assertEqual(data["meta"]["provider"], "nominatim")

    def test_case_r2_no_data_ocean(self):
        """[R2] Tọa độ giữa biển (0, 0) không có đối tượng -> 404 NO_RESULT."""
        res = self.client.get("/api/v1/geocode/reverse?lat=0.0&lon=0.0")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "NO_RESULT")
        self.assertIn("Không tìm thấy", data["error"]["message"])

    def test_case_r3_inverted_coordinates(self):
        """[R3] Tọa độ bị đảo thứ tự (lat > 90) -> 400 INVALID_COORDINATE."""
        res = self.client.get("/api/v1/geocode/reverse?lat=106.6980&lon=10.7725")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "INVALID_COORDINATE")
        self.assertIn("đảo thứ tự", data["error"]["message"])

if __name__ == "__main__":
    unittest.main()
