import unittest
from app.mapper import map_nominatim_to_geocode_item
from app.dtos import UpstreamBadResponseError

class TestMapper(unittest.TestCase):
    def test_complete_mapping(self):
        sample_raw = {
            "place_id": 123456,
            "osm_type": "way",
            "osm_id": 987654321,
            "category": "amenity",
            "type": "marketplace",
            "name": "Chợ Bến Thành",
            "display_name": "Chợ Bến Thành, Đường Lê Lợi, Phường Bến Thành, Quận 1, TP Hồ Chí Minh, 700000, Việt Nam",
            "lat": "10.7725000",
            "lon": "106.6980000",
            "boundingbox": ["10.7718000", "10.7732000", "106.6973000", "106.6987000"],
            "importance": "0.625",
            "address": {
                "road": "Đường Lê Lợi",
                "suburb": "Phường Bến Thành",
                "city_district": "Quận 1",
                "city": "Thành phố Hồ Chí Minh",
                "state": "Thành phố Hồ Chí Minh",
                "postcode": "700000",
                "country": "Việt Nam",
                "country_code": "VN",
            }
        }

        item = map_nominatim_to_geocode_item(sample_raw)

        # 1. Kiểm tra ép kiểu tọa độ sang số thực
        self.assertIsInstance(item.lat, float)
        self.assertIsInstance(item.lon, float)
        self.assertAlmostEqual(item.lat, 10.7725)
        self.assertAlmostEqual(item.lon, 106.6980)

        # 2. Kiểm tra BoundingBox DTO dạng đối tượng south, north, west, east
        self.assertEqual(item.boundingBox.south, 10.7718)
        self.assertEqual(item.boundingBox.north, 10.7732)
        self.assertEqual(item.boundingBox.west, 106.6973)
        self.assertEqual(item.boundingBox.east, 106.6987)

        # 3. Kiểm tra address fields
        self.assertEqual(item.address.street, "Đường Lê Lợi")
        self.assertEqual(item.address.ward, "Phường Bến Thành")
        self.assertEqual(item.address.district, "Quận 1")
        self.assertEqual(item.address.city, "Thành phố Hồ Chí Minh")
        self.assertEqual(item.address.countryCode, "vn")  # Chuyển về chữ thường

        # 4. Giữ lại osmType và osmId
        self.assertEqual(item.osmType, "way")
        self.assertEqual(item.osmId, 987654321)

    def test_missing_name_fallback_to_display_name(self):
        sample_no_name = {
            "osm_type": "node",
            "osm_id": 111,
            "category": "amenity",
            "type": "cafe",
            "name": "",
            "display_name": "Cà Phê Sữa Đá, 12 Lê Lợi, TP.HCM",
            "lat": "10.77",
            "lon": "106.69",
            "boundingbox": ["10.76", "10.78", "106.68", "106.70"],
        }
        item = map_nominatim_to_geocode_item(sample_no_name)
        self.assertEqual(item.name, "Cà Phê Sữa Đá")

    def test_invalid_lat_lon_throws_exception(self):
        sample_corrupt = {
            "osm_type": "node",
            "osm_id": 111,
            "lat": "not-a-number",
            "lon": "106.69",
        }
        with self.assertRaises(UpstreamBadResponseError):
            map_nominatim_to_geocode_item(sample_corrupt)

if __name__ == "__main__":
    unittest.main()

