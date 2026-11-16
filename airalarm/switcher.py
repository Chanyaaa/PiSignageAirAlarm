"""Switch piSignage groups to the alarm playlist and back.

piSignage's per-player "setplaylist" command does not reach players connected
over WebSocket (player 5.x), so we change each group's playlists and deploy it,
the same way the web UI does. Players that are offline get the deployed
config when they reconnect.
"""
import json
import logging
import os

log = logging.getLogger("airalarm")

# Zone keys a playlist asset can reference besides the main "filename"
# (public/app/js/services/pi.js, layoutOtherZones).
ZONES = ("side", "bottom", "zone4", "zone5", "zone6")


class Switcher:
    def __init__(self, signage, state_path, playlists):
        """playlists maps an alert level ("red", "yellow") to a playlist name.

        A playlist that does not exist on piSignage is skipped: the groups are
        left alone (or restored), so a missing playlist costs no deploys.
        """
        self.signage = signage
        self.state_path = state_path
        self.playlists = playlists

    def apply(self, level):
        """Show the playlist for level ("red", "yellow"), or restore on None."""
        if level is None:
            return self._restore()
        name = self.playlists[level]
        try:
            playlist = self.signage.get_playlist(name)
        except LookupError:
            log.warning("playlist %r not found on piSignage, not switching", name)
            return self._restore()
        self._switch_to(name, playlist)

    def _switch_to(self, name, playlist):
        entry, files = self._alarm_entry(name, playlist)
        saved = self._load()
        for group in self.signage.list_groups():
            gid = group["_id"]
            current = [p.get("name") for p in group.get("playlists") or []]
            if current == [name]:
                continue
            if gid not in saved:
                # Persist the original before touching the group, so a crash
                # or reboot mid-alarm can still put it back.
                saved[gid] = {"playlists": group.get("playlists") or [],
                              "assets": group.get("assets") or []}
                self._save(saved)
            assets = list(saved[gid]["assets"])
            assets += [f for f in files if f not in assets]
            self.signage.deploy_group(gid, [entry], assets)

    def _restore(self):
        saved = self._load()
        for gid in list(saved):
            self.signage.deploy_group(gid, saved[gid]["playlists"],
                                      saved[gid]["assets"])
            del saved[gid]
            self._save(saved)

    def _load(self):
        try:
            with open(self.state_path, encoding="utf-8") as f:
                return json.load(f)["groups"]
        except FileNotFoundError:
            return {}

    def _save(self, groups):
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"groups": groups}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.state_path)

    def _alarm_entry(self, name, playlist):
        files = []
        for asset in playlist.get("assets") or []:
            for f in [asset.get("filename")] + [asset.get(z) for z in ZONES]:
                if f and not f.startswith("_system") and f not in files:
                    files.append(f)
        files.append(f"__{name}.json")
        if playlist.get("templateName"):
            files.append(playlist["templateName"])
        settings = playlist.get("settings") or {}
        entry = {
            "name": name,
            "skipForSchedule": False,
            "plType": "regular",
            "settings": {k: settings.get(k) for k in ("ads", "audio")},
        }
        return entry, files
