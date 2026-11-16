# PiSignageAirAlarm

Switches every [piSignage](https://github.com/colloqi/pisignage-server) player to an alarm playlist while an air-raid alert is active in a chosen Ukrainian region, and puts the previous playlists back after the all-clear. Alert data comes from the [UkraineAlarm API](https://api.ukrainealarm.com).

## How it works

Every `POLL_SECONDS` the service asks UkraineAlarm for the alerts in `REGION_ID`.

When an alert starts, it saves each piSignage group's playlists and asset list to `data/state.json`, then redeploys the group with only the alert's playlist: `ALARM_PLAYLIST` for a red alert, `YELLOW_PLAYLIST` for a yellow one. The group keeps its old assets, so players do not download them again after the alert. When the alert ends, it redeploys the saved playlists and deletes them from the state file.

The state is written before each deploy. If the service or the Pi restarts during an alert, it still restores the original playlists afterwards. A failed deploy is retried on the next poll.

The service switches groups instead of sending players a playlist directly, because piSignage server's `/api/setplaylist` command never reaches players connected over WebSocket (player 5.x). A deployed group config also reaches players that were offline when the alert started, as soon as they reconnect.

Any active alert type counts (air raid, artillery, and so on). The level comes from the alert's `activeAlertLevels` field in the API response. An alert is yellow only when all its levels are `Yellow`; an alert with no level or an unknown one is treated as red. If yellow and red alerts are active at once, the red playlist wins.

The yellow playlist is optional. If `YELLOW_PLAYLIST` does not exist in piSignage, a yellow alert leaves the normal content on screen. When the level changes from yellow to red or back, the playlist changes on the next poll.

## Requirements

- A running piSignage server reachable over HTTP.
- A UkraineAlarm API key. Request one at https://api.ukrainealarm.com.
- Docker with Compose, or Python 3.10+ (standard library only).

## Setup

1. In piSignage, create the playlist to show during red alerts (named `ALARM` by default) and, if you want a separate one for yellow alerts, a second playlist (named `ALARM_YELLOW` by default).
2. Copy `.env.example` to `.env` and fill it in:

   | Variable | Default | Meaning |
   |---|---|---|
   | `UKRAINEALARM_API_KEY` | none | UkraineAlarm API key |
   | `REGION_ID` | none | Region to watch. Look up its id in `GET /api/v3/regions` (send the API key in the `Authorization` header). |
   | `ALARM_PLAYLIST` | `ALARM` | piSignage playlist shown during a red alert |
   | `YELLOW_PLAYLIST` | `ALARM_YELLOW` | piSignage playlist shown during a yellow alert (optional) |
   | `POLL_SECONDS` | `30` | Poll interval. UkraineAlarm rate-limits hard, so keep it at 30 or more. |
   | `PISIGNAGE_URL` | `http://127.0.0.1:3000` | piSignage server |
   | `PISIGNAGE_USER`, `PISIGNAGE_PASSWORD` | `pi`, `pi` | piSignage web UI login |

3. Start it:

   ```bash
   docker compose up -d
   docker logs -f pisignage-airalarm
   ```

   The compose file uses host networking, so `127.0.0.1:3000` is the piSignage server on the same machine.

## Manual switch

To check the setup without waiting for a real alert:

```bash
docker compose run --rm airalarm python -m airalarm.main --set red
docker compose run --rm airalarm python -m airalarm.main --set yellow
docker compose run --rm airalarm python -m airalarm.main --set off
```

While the service is running, its next poll brings the groups back in line with the real alert state, so a manual switch lasts at most `POLL_SECONDS`. For a longer test, run `docker compose stop` first and `docker compose start` afterwards.

## Limitations

- If someone deploys a group by hand during an alert, the service switches it back to the alarm playlist, and the manual change is lost after the all-clear.
- If the machine loses internet access, it cannot see alerts.
- If the red alarm playlist does not exist, the service logs an error on every poll and leaves the groups alone.

## Tests

```bash
python -m unittest discover -s tests
```
