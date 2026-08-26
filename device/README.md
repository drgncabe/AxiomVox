# Device

The M0 device application validates hardware, renders status, serves the web
dashboard, and runs under systemd.

## Run Locally

```bash
axiomvox-device --simulate-hardware --once
```

## Run On Device

```bash
axiomvox-device --host 0.0.0.0 --port 8080 --status-file /run/axiomvox/status.json
```

Add `--allow-shutdown` only on the target Raspberry Pi. Without it, web shutdown
is a dry run.

## Hardware Detection Notes

M0 uses conservative system probes:

- I2C devices for Whisplay presence.
- Framebuffer devices for LCD initialization.
- ALSA capture listing for microphones.
- Linux input metadata for Whisplay and PiSugar buttons.
- PiSugar socket, Linux power supply entries, or `pisugar-server` for PiSugar.
- DRM connector status for HDMI.

These probes are intentionally modular. Future milestones can replace them with
device-specific PiSugar and Whisplay libraries without changing the rest of the
application.
