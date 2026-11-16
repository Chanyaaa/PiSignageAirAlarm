"""Poll UkraineAlarm and switch piSignage groups to the alarm playlist.

    python -m airalarm.main            # run forever
    python -m airalarm.main --set on   # switch to alarm now (manual test)
    python -m airalarm.main --set off  # restore now
"""
import argparse
import logging
import os
import time

from airalarm.pisignage import PiSignage
from airalarm.switcher import Switcher
from airalarm.ukrainealarm import fetch_region_alerts, is_alert_active

log = logging.getLogger("airalarm")


def env(name, default=None):
    value = os.environ.get(name) or default
    if not value:
        raise SystemExit(f"missing environment variable {name}")
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=["on", "off"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    signage = PiSignage(env("PISIGNAGE_URL", "http://127.0.0.1:3000"),
                        env("PISIGNAGE_USER", "pi"),
                        env("PISIGNAGE_PASSWORD", "pi"))
    switcher = Switcher(signage, env("STATE_FILE", "state.json"),
                        env("ALARM_PLAYLIST", "ALARM"))

    if args.set:
        switcher.apply(alarm=args.set == "on")
        log.info("applied alarm=%s", args.set)
        return

    api_key = env("UKRAINEALARM_API_KEY")
    region = env("REGION_ID")
    poll = int(env("POLL_SECONDS", "30"))
    log.info("watching region %s every %ss", region, poll)
    last = None
    while True:
        try:
            alarm = is_alert_active(fetch_region_alerts(api_key, region))
            if alarm != last:
                log.info("alarm %s", "ON" if alarm else "OFF")
            switcher.apply(alarm)
            last = alarm
        except Exception as e:  # keep running; retry on next poll
            log.warning("poll failed: %s", e)
        time.sleep(poll)


if __name__ == "__main__":
    main()
