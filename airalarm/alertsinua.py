"""alerts.in.ua API (https://devs.alerts.in.ua). Stdlib only.

Limits: about 8-10 requests a minute per IP; more gets HTTP 429 and, if
repeated, a blocked token.
"""
import json
import urllib.request

API = "https://api.alerts.in.ua/v2"

# Status letter of /iot/active_air_raid_alerts/{uid}.json. A place inherits
# alerts of its raion and oblast. "P" means only part of the region is
# alerted, so the watched place may be quiet: pick a hromada uid to avoid it.
LEVELS = {"R": "red", "Y": "yellow", "P": None, "N": None}


def alert_level(response):
    """Alert level the IoT status reports: None, "yellow" or "red"."""
    if not isinstance(response, str) or response not in LEVELS:
        raise ValueError(f"unexpected alerts.in.ua response: {response!r}")
    return LEVELS[response]


def fetch_region_status(token, region_uid, timeout=15):
    """Raises urllib.error.HTTPError on 401, 404 (unknown uid), 429 and others."""
    req = urllib.request.Request(
        f"{API}/iot/active_air_raid_alerts/{region_uid}.json",
        headers={"Authorization": f"Bearer {token}",
                 "Accept": "application/json",
                 "User-Agent": "pisignage-airalarm/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)
