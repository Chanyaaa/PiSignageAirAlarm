import unittest

from airalarm.alertsinua import alert_level

# GET /v2/iot/active_air_raid_alerts/{uid}.json returns one JSON string,
# as seen on 2026-11-18: "R" red, "Y" yellow, "P" partial, "N" none.


class AlertLevel(unittest.TestCase):
    def test_none_means_quiet(self):
        self.assertIsNone(alert_level("N"))

    def test_r_means_red(self):
        self.assertEqual(alert_level("R"), "red")

    def test_y_means_yellow(self):
        self.assertEqual(alert_level("Y"), "yellow")

    def test_partial_means_quiet(self):
        # Only part of the region is alerted; the watched place may be outside it.
        self.assertIsNone(alert_level("P"))

    def test_unexpected_response_raises(self):
        for bad in ("", "X", {"message": "Unauthorized"}, None):
            with self.assertRaises(ValueError):
                alert_level(bad)


if __name__ == "__main__":
    unittest.main()
