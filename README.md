# PiSignageAirAlarm

Switches every [piSignage](https://github.com/colloqi/pisignage-server) player to an alarm playlist while an air-raid alert is active in a chosen Ukrainian region, and puts the previous playlists back after the all-clear. Alert data comes from the [UkraineAlarm API](https://api.ukrainealarm.com) or from [alerts.in.ua](https://devs.alerts.in.ua), chosen with `ALARM_API`.

## How it works

Every `POLL_SECONDS` the service asks the chosen API for the alert level in `REGION_ID`.

When an alert starts, it saves each piSignage group's playlists and asset list to `data/state.json`, then redeploys the group with only the alert's playlist: `ALARM_PLAYLIST` for a red alert, `YELLOW_PLAYLIST` for a yellow one. The group keeps its old assets, so players do not download them again after the alert. When the alert ends, it redeploys the saved playlists and deletes them from the state file.

The state is written before each deploy. If the service or the Pi restarts during an alert, it still restores the original playlists afterwards. A failed deploy is retried on the next poll.

The service switches groups instead of sending players a playlist directly, because piSignage server's `/api/setplaylist` command never reaches players connected over WebSocket (player 5.x). A deployed group config also reaches players that were offline when the alert started, as soon as they reconnect.

An alert shows its playlist for one pass of it: the sum of its assets' `duration` values, in seconds. For example, two images with 10 seconds each give 20 seconds. After that the normal content comes back, even if the alert is still active, and stays until the level changes or the alert ends. A playlist without durations has no limit.

The yellow playlist is optional. If `YELLOW_PLAYLIST` does not exist in piSignage, a yellow alert leaves the normal content on screen. When the level changes from yellow to red or back, the playlist changes on the next poll.

## Alert sources

`ukrainealarm` (default). Any active alert type counts (air raid, artillery, and so on). The level comes from the alert's `activeAlertLevels` field in the API response. An alert is yellow only when all its levels are `Yellow`; an alert with no level or an unknown one is treated as red. If yellow and red alerts are active at once, the red playlist wins.

`alertsinua`. The service reads `GET /v2/iot/active_air_raid_alerts/{uid}.json`, which returns one letter: `R` for a red air-raid alert, `Y` for yellow, `P` when only part of the region is alerted, `N` for none. Only air-raid alerts count; artillery and street fighting do not. A hromada or raion also shows its oblast's alert. `P` is treated as no alert, because the screens may be outside the alerted part, so set `REGION_ID` to the uid of the hromada where the screens are. The uid table is at https://devs.alerts.in.ua. The API allows about 8 to 10 requests a minute per IP and blocks tokens that keep going over.

## Requirements

- A running piSignage server reachable over HTTP.
- A UkraineAlarm API key (https://api.ukrainealarm.com) or an alerts.in.ua token (https://devs.alerts.in.ua).
- Docker with Compose, or Python 3.10+ (standard library only).

## Setup

1. In piSignage, create the playlist to show during red alerts (named `ALARM` by default) and, if you want a separate one for yellow alerts, a second playlist (named `ALARM_YELLOW` by default).
2. Copy `.env.example` to `.env` and fill it in:

   | Variable | Default | Meaning |
   |---|---|---|
   | `ALARM_API` | `ukrainealarm` | Alert source: `ukrainealarm` or `alertsinua` |
   | `UKRAINEALARM_API_KEY` | none | UkraineAlarm API key, for `ALARM_API=ukrainealarm` |
   | `ALERTSINUA_TOKEN` | none | alerts.in.ua token, for `ALARM_API=alertsinua` |
   | `REGION_ID` | none | Region to watch, as an id of the chosen API; the two number regions differently. UkraineAlarm: `GET /api/v3/regions` (send the API key in the `Authorization` header). alerts.in.ua: the uid table at https://devs.alerts.in.ua. |
   | `ALARM_PLAYLIST` | `ALARM` | piSignage playlist shown during a red alert |
   | `YELLOW_PLAYLIST` | `ALARM_YELLOW` | piSignage playlist shown during a yellow alert (optional) |
   | `POLL_SECONDS` | `30` | Poll interval. Both APIs rate-limit hard, so keep it at 30 or more. |
   | `PISIGNAGE_URL` | `http://host.docker.internal:3000` | piSignage server |
   | `PISIGNAGE_USER`, `PISIGNAGE_PASSWORD` | `pi`, `pi` | piSignage web UI login |

3. Start it:

   ```bash
   docker compose up -d
   docker logs -f pisignage-airalarm
   ```

   Inside the container, `host.docker.internal` is the machine running Docker. If piSignage runs there, in Docker or not, it must listen on port 3000 on all interfaces, as `ports: "3000:3000"` does. If piSignage runs on another machine, set `PISIGNAGE_URL` to its LAN address.

## Manual switch

To check the setup without waiting for a real alert:

```bash
docker compose run --rm airalarm python -m airalarm.main --set red
docker compose run --rm airalarm python -m airalarm.main --set yellow
docker compose run --rm airalarm python -m airalarm.main --set off
```

While the service is running, its next poll brings the groups back in line with the real alert state, so a manual switch lasts at most `POLL_SECONDS`. For a longer test, run `docker compose stop` first and `docker compose start` afterwards.

## Test it step by step

Before you test, the piSignage server needs at least one group with a player, and the `ALARM` and `ALARM_YELLOW` playlists from Setup. Each playlist needs one image.

1. Stop the service, so its polling does not interfere with your test:

   ```bash
   docker compose stop
   ```

2. Red alert. Show the red playlist on every group:

   ```bash
   docker compose run --rm airalarm python -m airalarm.main --set red
   ```

   The log says `applied red`. In the piSignage web UI each group now shows only `ALARM`, and the players show the red image.

3. Restore. Put the groups back to their old playlists:

   ```bash
   docker compose run --rm airalarm python -m airalarm.main --set off
   ```

   The log says `applied off`. Each group shows its original playlists again.

4. Yellow alert. Repeat step 2 with `--set yellow`. Players should show the yellow image and `ALARM_YELLOW` should be the only playlist in each group. Then run step 3.

5. Missing playlist. Rename `ALARM` in piSignage, run `--set red`, and check the log. It should say `playlist 'ALARM' not found on piSignage, not switching`, and the groups should stay as they were. Rename `ALARM` back afterwards.

6. Start the service again and watch the log:

   ```bash
   docker compose start
   docker logs -f pisignage-airalarm
   ```

   Expect `watching ukrainealarm region ... every 30s` (or `alertsinua`) and then `alarm OFF` or `alarm RED`, depending on the real alert state.

Always finish a manual test with `--set off`. If you stop in the middle, the groups keep the alarm playlist until the service sees the end of the alert.

Unit tests need no piSignage and no Docker:

```bash
python -m unittest discover -s tests
```

## Install on another machine

1. Install Docker with Compose. Make sure a piSignage server is running there, with at least one group and a connected player.
2. In piSignage, upload a red image and a yellow image to the media library. Create the `ALARM` playlist with the red image and `ALARM_YELLOW` with the yellow one.
3. Clone this repository, then:

   ```bash
   cp .env.example .env
   ```

   Fill in `ALARM_API`, its key (`UKRAINEALARM_API_KEY` or `ALERTSINUA_TOKEN`), `REGION_ID`, and `PISIGNAGE_PASSWORD` in `.env`.

4. Start the service and follow the steps in [Test it step by step](#test-it-step-by-step).

   ```bash
   docker compose up -d --build
   ```

The same compose file works on Linux, Windows, and macOS: `host.docker.internal` reaches the Docker host on all of them.

## Limitations

- If someone deploys a group by hand during an alert, the service switches it back to the alarm playlist, and the manual change is lost after the all-clear.
- If the machine loses internet access, it cannot see alerts.
- If the red or yellow playlist does not exist in piSignage, the service logs a warning on every poll and leaves the groups alone. While an alert is active it still asks piSignage once per poll whether that playlist exists.

## Tests

```bash
python -m unittest discover -s tests
```
