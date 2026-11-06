import unittest
from app import create_app
from app.cache import cache_service
from app.rate_limiter import circuit_breaker

class TestSearch(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        circuit_breaker.reset()
        cache_service.clear()

    def tearDown(self):
        circuit_breaker.reset()
        cache_service.clear()

    def test_search_success_and_caching(self):
        """Kiểm tra tìm kiếm có kết quả và hoạt động của cache."""
        # Lần 1: Cache Miss
        res1 = self.client.get("/api/v1/geocode/search?q=Chợ Bến Thành&limit=2")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertEqual(data1["query"], "Chợ Bến Thành")
        self.assertGreaterEqual(data1["count"], 1)
        self.assertFalse(data1["meta"]["cached"])
        self.assertIn("attribution", data1["meta"])

        first_item = data1["results"][0]
        self.assertIsInstance(first_item["lat"], float)
        self.assertIsInstance(first_item["lon"], float)
        self.assertIn("boundingBox", first_item)
        self.assertIn("address", first_item)

        # Lần 2: Cache Hit (cùng query)
        res2 = self.client.get("/api/v1/geocode/search?q=Chợ Bến Thành&limit=2")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2["meta"]["cached"])

    def test_search_no_results_returns_200_empty(self):
        """
        Kiểm tra tìm kiếm không có kết quả:
        Theo thiết kế, đây KHÔNG phải là lỗi hệ thống, trả về 200 OK kèm results=[].
        """
        res = self.client.get("/api/v1/geocode/search?q=dia_danh_khong_ton_tai_xyz")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])
        self.assertFalse(data["meta"]["cached"])

if __name__ == "__main__":
    unittest.main()
