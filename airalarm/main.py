"""Poll an alarm API and switch piSignage groups to the red/yellow alarm playlist.

ALARM_API picks the source: "ukrainealarm" (default) or "alertsinua".

    python -m airalarm.main                # run forever
    python -m airalarm.main --set red      # show the red playlist now (manual test)
    python -m airalarm.main --set yellow   # show the yellow playlist now
    python -m airalarm.main --set off      # restore now
"""
import argparse
import logging
import os
import time

from airalarm import alertsinua, ukrainealarm
from airalarm.pisignage import PiSignage
from airalarm.switcher import Switcher

log = logging.getLogger("airalarm")

# ALARM_API value -> (env var with the key, fetch(key, region), parse(response))
APIS = {
    "ukrainealarm": ("UKRAINEALARM_API_KEY", ukrainealarm.fetch_region_alerts,
                     ukrainealarm.alert_level),
    "alertsinua": ("ALERTSINUA_TOKEN", alertsinua.fetch_region_status,
                   alertsinua.alert_level),
}


def env(name, default=None):
    value = os.environ.get(name) or default
    if not value:
        raise SystemExit(f"missing environment variable {name}")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["red", "yellow", "off"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    signage = PiSignage(env("PISIGNAGE_URL", "http://127.0.0.1:3000"),
                        env("PISIGNAGE_USER", "pi"),
                        env("PISIGNAGE_PASSWORD", "pi"))
    switcher = Switcher(signage, env("STATE_FILE", "state.json"),
                        {"red": env("ALARM_PLAYLIST", "ALARM"),
                         "yellow": env("YELLOW_PLAYLIST", "ALARM_YELLOW")})

    if args.set:
        switcher.apply(None if args.set == "off" else args.set)
        log.info("applied %s", args.set)
        return

    api = env("ALARM_API", "ukrainealarm")
    if api not in APIS:
        raise SystemExit(f"ALARM_API must be one of {', '.join(APIS)}, got {api!r}")
    key_var, fetch, parse = APIS[api]
    api_key = env(key_var)
    region = env("REGION_ID")
    poll = int(env("POLL_SECONDS", "30"))
    log.info("watching %s region %s every %ss", api, region, poll)
    last = "unknown"
    while True:
        try:
            level = parse(fetch(api_key, region))
            if level != last:
                log.info("alarm %s", (level or "off").upper())
            switcher.apply(level)
            last = level
        except Exception as e:  # keep running; retry on next poll
            log.warning("poll failed: %s", e)
        time.sleep(poll)


if __name__ == "__main__":
    main()
