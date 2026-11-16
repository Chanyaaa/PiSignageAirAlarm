"""Minimal piSignage server REST client (basic auth). Stdlib only."""
import base64
import json
import urllib.parse
import urllib.request


class PiSignage:
    def __init__(self, url, user, password, timeout=30):
        self.url = url.rstrip("/")
        token = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.auth = f"Basic {token}"
        self.timeout = timeout

    def _call(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            self.url + path, data=data, method=method,
            headers={"Authorization": self.auth,
                     "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            reply = json.load(resp)
        if not reply.get("success"):
            raise RuntimeError(f"piSignage {method} {path}: "
                               f"{reply.get('stat_message')} {reply.get('data') or ''}")
        return reply.get("data")

    def list_groups(self):
        return self._call("GET", "/api/groups")

    def get_playlist(self, name):
        try:
            return self._call("GET", "/api/playlists/" + urllib.parse.quote(name))
        except RuntimeError as e:
            raise LookupError(f"playlist {name!r} not found on piSignage") from e

    def deploy_group(self, group_id, playlists, assets):
        self._call("POST", f"/api/groups/{group_id}",
                   {"playlists": playlists, "assets": assets, "deploy": True})
