"""Poll UkraineAlarm and switch piSignage groups to the red/yellow alarm playlist.

    python -m airalarm.main                # run forever
    python -m airalarm.main --set red      # show the red playlist now (manual test)
    python -m airalarm.main --set yellow   # show the yellow playlist now
    python -m airalarm.main --set off      # restore now
"""
import argparse
import logging
import os
import time

from airalarm.pisignage import PiSignage
from airalarm.switcher import Switcher
from airalarm.ukrainealarm import alert_level, fetch_region_alerts

log = logging.getLogger("airalarm")


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
                         "yellow": env("YELLOW_PLAYLIST", "ALARM_YELLOW")},
                        max_seconds=int(env("MAX_ALARM_SECONDS", "0")))

    if args.set:
        switcher.apply(None if args.set == "off" else args.set)
        log.info("applied %s", args.set)
        return

    api_key = env("UKRAINEALARM_API_KEY")
    region = env("REGION_ID")
    poll = int(env("POLL_SECONDS", "30"))
    log.info("watching region %s every %ss", region, poll)
    last = "unknown"
    while True:
        try:
            level = alert_level(fetch_region_alerts(api_key, region))
            if level != last:
                log.info("alarm %s", (level or "off").upper())
            switcher.apply(level)
            last = level
        except Exception as e:  # keep running; retry on next poll
            log.warning("poll failed: %s", e)
        time.sleep(poll)


if __name__ == "__main__":
    main()
