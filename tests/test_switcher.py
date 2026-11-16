import copy
import os
import tempfile
import unittest

from airalarm.switcher import Switcher

ALARM = "ALARM"


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
        }
        self.deploys = []
        self.fail_deploys = 0

    def list_groups(self):
        return copy.deepcopy(list(self.groups.values()))

    def get_playlist(self, name):
        if name not in self.playlists:
            raise LookupError(name)
        return copy.deepcopy(self.playlists[name])

    def deploy_group(self, group_id, playlists, assets):
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
        return Switcher(self.signage, self.state, ALARM)

    def test_alarm_deploys_only_the_alarm_playlist_with_its_files(self):
        self.switcher().apply(alarm=True)

        g = self.signage.groups["g1"]
        self.assertEqual([p["name"] for p in g["playlists"]], [ALARM])
        for f in ["alarm.png", "__ALARM.json", "custom_layout.html",
                  "test1.png", "test2.png", "__test.json"]:
            self.assertIn(f, g["assets"])
        self.assertEqual(self.signage.deploys, ["g1"])

    def test_all_clear_restores_what_the_group_had_before(self):
        s = self.switcher()
        s.apply(alarm=True)
        s.apply(alarm=False)

        g = self.signage.groups["g1"]
        self.assertEqual(g["playlists"], self.original["playlists"])
        self.assertEqual(g["assets"], self.original["assets"])

    def test_repeated_polls_deploy_each_change_once(self):
        s = self.switcher()
        s.apply(alarm=True)
        s.apply(alarm=True)
        s.apply(alarm=False)
        s.apply(alarm=False)

        self.assertEqual(self.signage.deploys, ["g1", "g1"])

    def test_restart_during_alarm_still_restores_the_original(self):
        self.switcher().apply(alarm=True)
        self.switcher().apply(alarm=True)   # service restarted
        self.switcher().apply(alarm=False)

        g = self.signage.groups["g1"]
        self.assertEqual(g["playlists"], self.original["playlists"])

    def test_failed_deploys_are_retried_on_the_next_poll(self):
        s = self.switcher()
        self.signage.fail_deploys = 1
        with self.assertRaises(ConnectionError):
            s.apply(alarm=True)
        s.apply(alarm=True)
        self.assertEqual([p["name"] for p in self.signage.groups["g1"]["playlists"]],
                         [ALARM])

        self.signage.fail_deploys = 1
        with self.assertRaises(ConnectionError):
            s.apply(alarm=False)
        s.apply(alarm=False)
        self.assertEqual(self.signage.groups["g1"]["playlists"],
                         self.original["playlists"])


if __name__ == "__main__":
    unittest.main()
