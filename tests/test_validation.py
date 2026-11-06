import unittest
from app import create_app
from app.dtos import SearchRequest, ReverseRequest, ValidationError, InvalidCoordinateError

class TestValidation(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_search_missing_q(self):
        """Kiểm tra tìm kiếm thiếu tham số q -> 400 VALIDATION_ERROR."""
        res = self.client.get("/api/v1/geocode/search")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_search_q_too_short(self):
        """Kiểm tra từ khóa < 3 ký tự -> 400 VALIDATION_ERROR."""
        res = self.client.get("/api/v1/geocode/search?q=ab")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("quá ngắn", data["error"]["message"])

    def test_search_q_only_special_chars(self):
        """Kiểm tra từ khóa chỉ gồm ký tự đặc biệt -> 400 VALIDATION_ERROR."""
        res = self.client.get("/api/v1/geocode/search?q=---@@@###")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_search_limit_out_of_bounds(self):
        """Kiểm tra limit ngoài khoảng [1, 10] -> 400 VALIDATION_ERROR."""
        res = self.client.get("/api/v1/geocode/search?q=Hà Nội&limit=15")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertIn("limit", data["error"]["message"])

    def test_reverse_missing_lat_lon(self):
        """Kiểm tra reverse thiếu lat hoặc lon -> 400 VALIDATION_ERROR."""
        res = self.client.get("/api/v1/geocode/reverse?lat=10.7725")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

    def test_reverse_inverted_coordinates_vietnam(self):
        """
        Kiểm tra phát hiện đảo thứ tự lat/lon tại Việt Nam:
        lat=106.6980, lon=10.7725 -> 400 INVALID_COORDINATE.
        """
        res = self.client.get("/api/v1/geocode/reverse?lat=106.6980&lon=10.7725")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "INVALID_COORDINATE")
        self.assertIn("đảo thứ tự", data["error"]["message"])

    def test_reverse_lat_out_of_range(self):
        """Kiểm tra lat vượt quá 90 -> 400 INVALID_COORDINATE."""
        res = self.client.get("/api/v1/geocode/reverse?lat=95.5&lon=50.0")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "INVALID_COORDINATE")

    def test_reverse_zoom_out_of_range(self):
        """Kiểm tra zoom ngoài [3, 18] -> 400 VALIDATION_ERROR."""
        res = self.client.get("/api/v1/geocode/reverse?lat=10.7725&lon=106.6980&zoom=25")
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")

if __name__ == "__main__":
    unittest.main()

