import copy
import os
import tempfile
import unittest

from airalarm.switcher import Switcher

ALARM = "ALARM"
YELLOW = "ALARM_YELLOW"


def regular(name):
    return {"name": name, "skipForSchedule": False, "plType": "regular",
            "settings": {"ads": {"adPlaylist": False}, "audio": {"enable": False}}}


class FakeSignage:
    """In-memory piSignage server: groups, playlists and a deploy log."""

    def __init__(self):
        self.groups = {
            "g1": {"_id": "g1", "name": "default",
                   "playlists": [regular("test")],
                   "assets": ["test1.png", "test2.png", "__test.json"]},
        }
        self.playlists = {
            ALARM: {"assets": [{"filename": "alarm.png", "duration": 10}],
                    "templateName": "custom_layout.html",
                    "settings": {"ads": {"adPlaylist": False},
                                 "audio": {"enable": False}}},
            YELLOW: {"assets": [{"filename": "yellow.png", "duration": 10}],
                     "settings": {}},
        }
        self.deploys = []
        self.fail_deploys = 0
        self.api_calls = []

    def list_groups(self):
        self.api_calls.append("list_groups")
        return copy.deepcopy(list(self.groups.values()))

    def get_playlist(self, name):
        self.api_calls.append("get_playlist:" + name)
        if name not in self.playlists:
            raise LookupError(name)
        return copy.deepcopy(self.playlists[name])

    def deploy_group(self, group_id, playlists, assets):
        self.api_calls.append("deploy_group")
        if self.fail_deploys:
            self.fail_deploys -= 1
            raise ConnectionError("piSignage down")
        self.groups[group_id]["playlists"] = copy.deepcopy(playlists)
        self.groups[group_id]["assets"] = list(assets)
        self.deploys.append(group_id)


class SwitcherTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.state = os.path.join(self.dir.name, "state.json")
        self.signage = FakeSignage()
        self.original = copy.deepcopy(self.signage.groups["g1"])

    def tearDown(self):
        self.dir.cleanup()

    def switcher(self):
        return Switcher(self.signage, self.state, {"red": ALARM, "yellow": YELLOW})

    def shown(self):
        return [p["name"] for p in self.signage.groups["g1"]["playlists"]]

    def test_red_deploys_only_the_red_playlist_with_its_files(self):
        self.switcher().apply("red")

        g = self.signage.groups["g1"]
        self.assertEqual(self.shown(), [ALARM])
        for f in ["alarm.png", "__ALARM.json", "custom_layout.html",
                  "test1.png", "test2.png", "__test.json"]:
            self.assertIn(f, g["assets"])
        self.assertEqual(self.signage.deploys, ["g1"])

    def test_yellow_deploys_the_yellow_playlist(self):
        self.switcher().apply("yellow")

        self.assertEqual(self.shown(), [YELLOW])
        self.assertIn("yellow.png", self.signage.groups["g1"]["assets"])

    def test_red_without_a_red_playlist_skips_the_group_calls(self):
        del self.signage.playlists[ALARM]
        self.switcher().apply("red")

        self.assertEqual(self.signage.api_calls, ["get_playlist:" + ALARM])
        self.assertEqual(self.signage.groups["g1"]["playlists"],
                         self.original["playlists"])

    def switcher_with_clock(self, now):
        return Switcher(self.signage, self.state,
                        {"red": ALARM, "yellow": YELLOW},
                        clock=lambda: now[0])

    def test_alarm_goes_back_to_normal_when_the_playlist_has_run(self):
        now = [0]
        s = self.switcher_with_clock(now)
        s.apply("red")
        now[0] = 5
        s.apply("red")
        self.assertEqual(self.shown(), [ALARM])

        now[0] = 10
        s.apply("red")
        self.assertEqual(self.signage.groups["g1"]["playlists"],
                         self.original["playlists"])

    def test_the_limit_is_the_sum_of_the_asset_durations(self):
        self.signage.playlists[ALARM]["assets"] = [
            {"filename": "a.png", "duration": 4},
            {"filename": "b.png", "duration": 6},
        ]
        now = [0]
        s = self.switcher_with_clock(now)
        s.apply("red")
        now[0] = 9
        s.apply("red")
        self.assertEqual(self.shown(), [ALARM])

        now[0] = 10
        s.apply("red")
        self.assertEqual(self.signage.groups["g1"]["playlists"],
                         self.original["playlists"])

    def test_expired_alarm_stays_off_without_api_calls(self):
        now = [0]
        s = self.switcher_with_clock(now)
        s.apply("red")
        now[0] = 10
        s.apply("red")
        self.signage.api_calls.clear()

        now[0] = 90
        s.apply("red")
        self.assertEqual(self.signage.api_calls, [])
        self.assertEqual(self.signage.groups["g1"]["playlists"],
                         self.original["playlists"])

    def test_a_new_alert_after_all_clear_shows_the_alarm_again(self):
        now = [0]
        s = self.switcher_with_clock(now)
        s.apply("red")
        now[0] = 10
        s.apply("red")
        s.apply(None)
        s.apply("red")
        self.assertEqual(self.shown(), [ALARM])

    def test_a_playlist_without_durations_has_no_limit(self):
        self.signage.playlists[ALARM]["assets"] = [{"filename": "a.png"}]
        now = [0]
        s = self.switcher_with_clock(now)
        s.apply("red")
        now[0] = 10000
        s.apply("red")
        self.assertEqual(self.shown(), [ALARM])

    def test_yellow_without_a_yellow_playlist_keeps_normal_content(self):
        del self.signage.playlists[YELLOW]
        s = self.switcher()
        s.apply("red")
        s.apply("yellow")

        self.assertEqual(self.signage.groups["g1"]["playlists"],
                         self.original["playlists"])

    def test_level_change_then_all_clear_restores_the_original(self):
        s = self.switcher()
        s.apply("yellow")
        s.apply("red")
        self.assertEqual(self.shown(), [ALARM])
        self.assertNotIn("yellow.png", self.signage.groups["g1"]["assets"])
        s.apply(None)

        g = self.signage.groups["g1"]
        self.assertEqual(g["playlists"], self.original["playlists"])
        self.assertEqual(g["assets"], self.original["assets"])

    def test_all_clear_restores_what_the_group_had_before(self):
        s = self.switcher()
        s.apply("red")
        s.apply(None)

        g = self.signage.groups["g1"]
        self.assertEqual(g["playlists"], self.original["playlists"])
        self.assertEqual(g["assets"], self.original["assets"])

    def test_repeated_polls_deploy_each_change_once(self):
        s = self.switcher()
        s.apply("red")
        s.apply("red")
        s.apply(None)
        s.apply(None)

        self.assertEqual(self.signage.deploys, ["g1", "g1"])

    def test_restart_during_alarm_still_restores_the_original(self):
        self.switcher().apply("red")
        self.switcher().apply("red")   # service restarted
        self.switcher().apply(None)

        g = self.signage.groups["g1"]
        self.assertEqual(g["playlists"], self.original["playlists"])

    def test_failed_deploys_are_retried_on_the_next_poll(self):
        s = self.switcher()
        self.signage.fail_deploys = 1
        with self.assertRaises(ConnectionError):
            s.apply("red")
        s.apply("red")
        self.assertEqual(self.shown(), [ALARM])

        self.signage.fail_deploys = 1
        with self.assertRaises(ConnectionError):
            s.apply(None)
        s.apply(None)
        self.assertEqual(self.signage.groups["g1"]["playlists"],
                         self.original["playlists"])


if __name__ == "__main__":
    unittest.main()
