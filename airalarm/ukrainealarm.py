"""UkraineAlarm API (https://api.ukrainealarm.com). Stdlib only."""
import json
import urllib.request

API = "https://api.ukrainealarm.com/api/v3"


def is_alert_active(response):
    """True if GET /alerts/{regionId} reports any active alert for the region."""
    if not isinstance(response, list):
        raise ValueError(f"unexpected UkraineAlarm response: {response!r}")
    for region in response:
        if not isinstance(region, dict) or "activeAlerts" not in region:
            raise ValueError(f"unexpected UkraineAlarm region: {region!r}")
        if region["activeAlerts"]:
            return True
    return False


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
