import unittest

from airalarm.ukrainealarm import alert_level

# Response shape of GET /api/v3/alerts/{regionId}, as returned on 2026-11-16.
QUIET = [{
    "regionId": "100", "regionType": "State",
    "regionName": "Example region",
    "lastUpdate": "2026-11-16T20:06:07.568108Z",
    "activeAlerts": [],
}]


def alerting(*levels):
    """A region response with one active AIR alert carrying these levels."""
    alert = {"regionId": "100", "regionType": "State", "type": "AIR",
             "lastUpdate": "2026-11-16T21:00:00Z"}
    if levels:
        alert["activeAlertLevels"] = [
            {"alertLevel": lvl, "reason": "",
             "createdAt": "2026-11-16T20:59:16.730789Z"} for lvl in levels]
    return [{"regionId": "100", "regionType": "State",
             "lastUpdate": "2026-11-16T21:00:00Z",
             "activeAlerts": [alert]}]


class AlertLevel(unittest.TestCase):
    def test_no_active_alerts_means_quiet(self):
        self.assertIsNone(alert_level(QUIET))

    def test_red_level_means_red(self):
        self.assertEqual(alert_level(alerting("Red")), "red")

    def test_yellow_level_means_yellow(self):
        self.assertEqual(alert_level(alerting("Yellow")), "yellow")

    def test_red_wins_over_yellow(self):
        self.assertEqual(alert_level(alerting("Yellow", "Red")), "red")

    def test_alert_without_or_with_unknown_level_counts_as_red(self):
        self.assertEqual(alert_level(alerting()), "red")
        self.assertEqual(alert_level(alerting("Purple")), "red")

    def test_unexpected_shape_raises(self):
        with self.assertRaises(ValueError):
            alert_level({"message": "something else"})


if __name__ == "__main__":
    unittest.main()
