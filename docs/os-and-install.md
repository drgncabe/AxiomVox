# OS and Installation

## Recommended OS

Use the Raspberry Pi OS Lite image that matches the board:

- Raspberry Pi Zero W: Raspberry Pi OS Lite 32-bit.
- Raspberry Pi Zero 2 W: Raspberry Pi OS Lite 64-bit.

Raspberry Pi OS Lite is the preferred target because AxiomVox depends on
small-board hardware behavior: GPIO, I2C, audio devices, display/framebuffer
setup, systemd startup, and HAT/UPS integration. Raspberry Pi OS is the most
direct path for that stack on Zero-class Raspberry Pi hardware.

Ubuntu Server is also a viable operating system for Raspberry Pi Zero 2 W, but
it is not the preferred M0 baseline. Raspberry Pi Zero W should use Raspberry Pi
OS Lite 32-bit.

## Install

From a fresh Raspberry Pi OS Lite install:

```bash
sudo apt-get update
wget https://raw.githubusercontent.com/drgncabe/AxiomVox/main/install_axiomvox.sh
sudo chmod +x install_axiomvox.sh && sudo ./install_axiomvox.sh
```

Choose `Raspberry Pi appliance with Whisplay + PiSugar 3`.

On Raspberry Pi Zero W, use Raspberry Pi OS Lite 32-bit and choose the same
appliance option.

For unattended setup, skip the menu:

```bash
sudo AXIOMVOX_INSTALL_MODE=appliance ./install_axiomvox.sh
```

The installer:

- Installs Git if it is not already available.
- Clones or updates AxiomVox at `/opt/axiomvox`.
- Installs required system packages.
- Enables Raspberry Pi hardware interfaces when `raspi-config` is available.
- Installs the Whisplay LCD/audio/button driver.
- Installs the PiSugar 3 power manager/server tools.
- Installs AxiomVox into `/opt/axiomvox`.
- Creates a Python virtual environment.
- Installs the device app.
- Installs and starts the systemd service.

Reboot after the first install so Whisplay overlay, audio, display, and bus
changes are active:

```bash
sudo reboot
```

After reboot, open the dashboard at:

```text
http://<pi-ip-address>:8080/
```

## Update

```bash
cd /opt/axiomvox
sudo ./scripts/update.sh
```

The updater fetches the configured branch, updates the Python environment, and
restarts the service.

By default, updates do not reinstall vendor hardware drivers. To refresh those
too:

```bash
sudo AXIOMVOX_UPDATE_HARDWARE=1 ./scripts/update.sh
```

## Configuration

The scripts can be adjusted with environment variables:

| Variable | Default |
| --- | --- |
| `AXIOMVOX_USER` | sudo user, otherwise `pi` |
| `AXIOMVOX_GROUP` | same as user |
| `AXIOMVOX_INSTALL_DIR` | `/opt/axiomvox` |
| `AXIOMVOX_REPO_URL` | `https://github.com/drgncabe/AxiomVox.git` |
| `AXIOMVOX_SERVICE_NAME` | `axiomvox.service` |
| `AXIOMVOX_WEB_PORT` | `8080` |
| `AXIOMVOX_STATUS_FILE` | `/run/axiomvox/status.json` |
| `AXIOMVOX_INSTALL_HARDWARE` | `1` |
| `AXIOMVOX_INSTALL_WHISPLAY_DRIVER` | `1` |
| `AXIOMVOX_INSTALL_WHISPLAY_DAEMON` | `0` |
| `AXIOMVOX_INSTALL_PISUGAR` | `1` |
| `AXIOMVOX_PISUGAR_MODEL` | `PiSugar 3` |
| `AXIOMVOX_PISUGAR_AUTH_USER` | `admin` |
| `AXIOMVOX_PISUGAR_AUTH_PASSWORD` | `admin` |
| `AXIOMVOX_INSTALL_MODE` | prompts when unset |

## Board Profiles

| Board | OS | AxiomVox role |
| --- | --- | --- |
| Raspberry Pi Zero W | Raspberry Pi OS Lite 32-bit | M0 appliance device |
| Raspberry Pi Zero 2 W | Raspberry Pi OS Lite 64-bit | M0 appliance device |

The Zero W is intentionally treated as an appliance device, not a local
transcription server. Docker-first AxiomVox Server work should run on stronger
hardware.

Example:

```bash
sudo AXIOMVOX_USER=axiomvox AXIOMVOX_INSTALL_DIR=/srv/axiomvox ./scripts/install.sh
```

## Hardware Notes

The Whisplay driver installer is vendor-maintained and handles the LCD, audio,
buttons, LEDs, and required buses. AxiomVox does not install the Whisplay daemon
by default because the daemon owns its own app/menu behavior; AxiomVox should
own the appliance interface directly.

The PiSugar installer is vendor-maintained and installs `pisugar-server` and
`pisugar-poweroff`. AxiomVox uses the PiSugar socket when present to read model
and battery information.
