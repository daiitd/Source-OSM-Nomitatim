import unittest
from app import create_app
from app.rate_limiter import circuit_breaker
from app.cache import cache_service

class TestResilience(unittest.TestCase):
    """
    Kiểm thử cơ chế Circuit Breaker và chính sách không retry 429 liên tục (Task 3.4).
    """
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()
        circuit_breaker.reset()
        cache_service.clear()

    def tearDown(self):
        circuit_breaker.reset()
        cache_service.clear()

    def test_circuit_breaker_tripped_on_429(self):
        """Khi Circuit Breaker mở, mọi request mới phải bị từ chối ngay với 429 và Retry-After."""
        # Giả lập ngắt mạch được kích hoạt bởi phản hồi 429 từ Nominatim với Retry-After=30s
        circuit_breaker.trip(retry_after_sec=30)

        # Kiểm tra trạng thái
        state = circuit_breaker.check_state()
        self.assertTrue(state["isOpen"])
        self.assertGreaterEqual(state["remainingCooldownSec"], 25)

        # Gửi request search -> Backend phải từ chối ngay lập tức, KHÔNG gọi upstream
        res = self.client.get("/api/v1/geocode/search?q=Chợ Bến Thành")
        self.assertEqual(res.status_code, 429)
        self.assertIn("Retry-After", res.headers)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "UPSTREAM_RATE_LIMITED")
        self.assertIn("ngắt mạch đang bật", data["error"]["message"].lower())

        # Reset ngắt mạch
        circuit_breaker.reset()
        state_after = circuit_breaker.check_state()
        self.assertFalse(state_after["isOpen"])

if __name__ == "__main__":
    unittest.main()
