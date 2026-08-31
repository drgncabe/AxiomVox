# AxiomVox

AxiomVox is an appliance-style live transcription device and companion server.

M0 is focused on the device foundation: boot reliably on the target hardware,
validate attached peripherals, present status on the Whisplay LCD and HDMI, and
expose a small local web dashboard with graceful shutdown. M1 adds the appliance
loop, M2 adds local recording-session metadata and initial WAV capture, M3 adds
WAV validation/audio confidence checks, and M4 adds settings, power, and
brightness controls. M5 adds a searchable web log viewer for system and
AxiomVox service logs. M6 adds appliance polish and PiSugar diagnostics.

## M0 Target

- Raspberry Pi Zero W with Raspberry Pi OS Lite 32-bit
- Raspberry Pi Zero 2 W with Raspberry Pi OS Lite 64-bit
- PiSugar Whisplay HAT
- PiSugar 3 UPS
- HDMI as a passive secondary status display
- Python device application managed by systemd
- Docker-first server architecture documented for future milestones

## Repository Layout

```text
device/   Raspberry Pi appliance application and systemd assets
server/   Future AxiomVox Server implementation
shared/   Protocol and state definitions shared across components
docs/     Product, architecture, and protocol documentation
docker/   Docker-first server packaging placeholders
```

## M0 Quick Start

Recommended OS for V1/M0 depends on the board:

- Raspberry Pi Zero W: **Raspberry Pi OS Lite 32-bit**
- Raspberry Pi Zero 2 W: **Raspberry Pi OS Lite 64-bit**

On the Raspberry Pi, the normal path is:

```bash
wget https://raw.githubusercontent.com/drgncabe/AxiomVox/main/install_axiomvox.sh
sudo chmod +x install_axiomvox.sh && sudo ./install_axiomvox.sh
```

To update an installed device:

```bash
cd /opt/axiomvox
sudo ./scripts/update.sh
```

For manual development:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
axiomvox-device --host 0.0.0.0 --port 8080
```

For automatic startup, install the systemd unit from
`device/systemd/axiomvox.service` and point `WorkingDirectory` at the deployed
repository path.

## Documentation

- [V1 Architecture](docs/v1-architecture.md)
- [Product Decisions](docs/product-decisions.md)
- [M0 Acceptance](docs/m0-acceptance.md)
- [M1 Appliance Loop](docs/m1-appliance-loop.md)
- [M2 Local Sessions](docs/m2-local-sessions.md)
- [M3 Audio Confidence](docs/m3-audio-confidence.md)
- [M4 Settings And Power](docs/m4-settings-power.md)
- [M5 Log Viewer](docs/m5-log-viewer.md)
- [M6 Appliance Polish](docs/m6-appliance-polish.md)
- [AVTP/1 Protocol](docs/avtp-1.md)
- [OS and Installation](docs/os-and-install.md)

## License

AxiomVox is licensed under the GNU Affero General Public License v3.0. See
[LICENSE](LICENSE).
