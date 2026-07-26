import unittest

from region import UNKNOWN_REGION, extract_region


class ExtractRegionTests(unittest.TestCase):
    def test_prefers_chirpstack_region_config_id(self):
        data = {
            "regionConfigId": "EU868",
            "deviceInfo": {"tags": {"region_name": "us915_0"}},
        }

        self.assertEqual(extract_region(data), "eu868")

    def test_accepts_legacy_tag_with_whitespace(self):
        data = {
            "deviceInfo": {"tags": {"region_name\t": " EU868 "}},
        }

        self.assertEqual(extract_region(data), "eu868")

    def test_returns_unknown_region_when_no_region_is_available(self):
        self.assertEqual(extract_region({"deviceInfo": {}}), UNKNOWN_REGION)


if __name__ == "__main__":
    unittest.main()
