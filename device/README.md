# Device

The M0 device application validates hardware, renders status, serves the web
dashboard, handles early appliance controls, and runs under systemd.

## Run Locally

```bash
axiomvox-device --simulate-hardware --once
axiomvox-device --simulate-hardware --self-test
```

The installer also leaves the virtual-environment command available directly at
`/opt/axiomvox/.venv/bin/axiomvox-device`.

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
- Whisplay runtime/daemon availability or Linux input metadata for the Whisplay button.
- PiSugar server socket, direct PiSugar 3 I2C register reads, Linux power supply entries, or `pisugar-server` for PiSugar.
- PiSugar button API responses or direct PiSugar 3 I2C custom-button register readability for PiSugar button availability.
- DRM connector status for HDMI.

These probes are intentionally modular. Future milestones can replace them with
device-specific PiSugar and Whisplay libraries without changing the rest of the
application.
