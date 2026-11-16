"""UkraineAlarm API (https://api.ukrainealarm.com). Stdlib only."""
import json
import urllib.request

API = "https://api.ukrainealarm.com/api/v3"


def alert_level(response):
    """Alert level GET /alerts/{regionId} reports: None, "yellow" or "red".

    "yellow" only when every active alert is marked Yellow; an alert with no
    level or an unknown one counts as red, so nothing is missed.
    """
    if not isinstance(response, list):
        raise ValueError(f"unexpected UkraineAlarm response: {response!r}")
    levels = set()
    for region in response:
        if not isinstance(region, dict) or "activeAlerts" not in region:
            raise ValueError(f"unexpected UkraineAlarm region: {region!r}")
        for alert in region["activeAlerts"]:
            marks = [str(m.get("alertLevel", "")).lower()
                     for m in alert.get("activeAlertLevels") or []]
            levels.add("yellow" if marks and all(m == "yellow" for m in marks)
                       else "red")
    if "red" in levels:
        return "red"
    return "yellow" if levels else None


def fetch_region_alerts(api_key, region_id, timeout=15):
    """Raises urllib.error.HTTPError on 429 (rate limit) and other errors."""
    req = urllib.request.Request(
        f"{API}/alerts/{region_id}",
        # Cloudflare in front of the API answers 403 to the default
        # "Python-urllib" User-Agent.
        headers={"Authorization": api_key, "Accept": "application/json",
                 "User-Agent": "pisignage-airalarm/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)
