# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`superfan` is a small single-file Python daemon that controls a PWM fan on a Raspberry Pi
based on CPU temperature. It runs as a systemd service for continuous uptime. It is
deployed on a host called **loftpi** (`ssh pi@loftpi`).

The entire project is three files:

- `superfan.py` — the daemon (`FanController` class). Depends on `RPi.GPIO`.
- `superfan.service` — systemd unit.
- `readme.md` — one-line description.

## How it works (`superfan.py`)

- **PWM**: software PWM on GPIO `FAN_PIN = 14` (BCM) at `PWM_FREQ = 100` Hz via `RPi.GPIO`.
- **Temperature**: `vcgencmd measure_temp`, parsed from `temp=XX.X'C`. On any error it
  returns a safe default of `40.0°C`.
- **Control law**: `TEMP_THRESHOLDS` is an ordered list of `(temp, duty_cycle%, interval_s)`
  tuples, highest temp first. The loop picks the first row where `temp >= threshold`, sets
  that duty cycle, then sleeps that interval before re-checking. Hotter = faster fan and
  more frequent checks. The final `(0, …)` row is the catch-all floor.
- **Lifecycle**: `SIGTERM`/`SIGINT` set `running = False` for graceful shutdown; sleep is
  done in 1-second steps so shutdown is responsive. `cleanup()` stops PWM and calls
  `GPIO.cleanup()`.
- **Logging**: to both `/var/log/pi-fan-controller.log` and stdout (journal).

Fan behavior is tuned by editing the module-level constants (`FAN_PIN`, `PWM_FREQ`,
`TEMP_THRESHOLDS`) — there is no CLI/config-file layer.

## Running it

```sh
sudo python3 superfan.py        # direct run
sudo systemctl enable --now superfan
sudo journalctl -u superfan -f  # logs
```

There is no build step and no test suite. The only third-party dependency is `RPi.GPIO`
(present on Raspberry Pi OS).

## Known inconsistencies (verify before relying on them)

- `superfan.service` points `ExecStart` at `/usr/local/bin/pi-fan-controller.py`, not at a
  path matching this repo's `superfan.py`. Deployment must copy/symlink the script to that
  path (or the unit must be edited). Confirm the actual installed paths on loftpi.
- `ProtectHome=true` + `ProtectSystem=strict` with `ReadWritePaths=/var/log`: the script
  must be reachable under those protections and only writes under `/var/log`.
