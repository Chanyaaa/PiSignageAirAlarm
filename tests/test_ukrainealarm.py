import unittest

from airalarm.ukrainealarm import is_alert_active

# Response shape of GET /api/v3/alerts/{regionId}, as returned on 2026-11-16.
QUIET = [{
    "regionId": "100", "regionType": "State",
    "regionName": "Example region",
    "lastUpdate": "2026-11-16T20:06:07.568108Z",
    "activeAlerts": [],
}]

ALERT = [{
    "regionId": "100", "regionType": "State",
    "lastUpdate": "2026-11-16T21:00:00Z",
    "activeAlerts": [{
        "regionId": "100", "regionType": "State", "type": "AIR",
        "lastUpdate": "2026-11-16T21:00:00Z",
    }],
}]


class IsAlertActive(unittest.TestCase):
    def test_no_active_alerts_means_quiet(self):
        self.assertFalse(is_alert_active(QUIET))

    def test_any_active_alert_means_alarm(self):
        self.assertTrue(is_alert_active(ALERT))

    def test_unexpected_shape_raises(self):
        with self.assertRaises(ValueError):
            is_alert_active({"message": "something else"})


if __name__ == "__main__":
    unittest.main()
