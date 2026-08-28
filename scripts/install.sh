#!/usr/bin/env bash
set -euo pipefail

APP_USER="${AXIOMVOX_USER:-${SUDO_USER:-pi}}"
APP_GROUP="${AXIOMVOX_GROUP:-$APP_USER}"
INSTALL_DIR="${AXIOMVOX_INSTALL_DIR:-/opt/axiomvox}"
REPO_URL="${AXIOMVOX_REPO_URL:-https://github.com/drgncabe/AxiomVox.git}"
SERVICE_NAME="${AXIOMVOX_SERVICE_NAME:-axiomvox.service}"
WEB_PORT="${AXIOMVOX_WEB_PORT:-8080}"
STATUS_FILE="${AXIOMVOX_STATUS_FILE:-/run/axiomvox/status.json}"
INSTALL_HARDWARE="${AXIOMVOX_INSTALL_HARDWARE:-1}"
INSTALL_WHISPLAY_DRIVER="${AXIOMVOX_INSTALL_WHISPLAY_DRIVER:-1}"
INSTALL_WHISPLAY_DAEMON="${AXIOMVOX_INSTALL_WHISPLAY_DAEMON:-0}"
INSTALL_PISUGAR="${AXIOMVOX_INSTALL_PISUGAR:-1}"
VENDOR_DIR="${AXIOMVOX_VENDOR_DIR:-/opt/axiomvox-vendor}"
WHISPLAY_REPO="${AXIOMVOX_WHISPLAY_REPO:-https://github.com/PiSugar/Whisplay.git}"
PISUGAR_INSTALLER_URL="${AXIOMVOX_PISUGAR_INSTALLER_URL:-https://cdn.pisugar.com/release/pisugar-power-manager.sh}"
PISUGAR_MODEL="${AXIOMVOX_PISUGAR_MODEL:-PiSugar 3}"
PISUGAR_AUTH_USER="${AXIOMVOX_PISUGAR_AUTH_USER:-admin}"
PISUGAR_AUTH_PASSWORD="${AXIOMVOX_PISUGAR_AUTH_PASSWORD:-admin}"
NEEDS_REBOOT=0

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this installer with sudo." >&2
    exit 1
  fi
}

detect_profile() {
  local machine
  machine="$(uname -m 2>/dev/null || echo unknown)"
  echo "Detected architecture: ${machine}"
  case "${machine}" in
    armv6l)
      echo "AxiomVox profile: Raspberry Pi Zero W with Raspberry Pi OS Lite 32-bit"
      ;;
    aarch64)
      echo "AxiomVox profile: Raspberry Pi Zero 2 W with Raspberry Pi OS Lite 64-bit"
      ;;
    armv7l)
      echo "AxiomVox profile: Raspberry Pi OS 32-bit"
      ;;
    *)
      echo "AxiomVox profile: unknown hardware; continuing with portable M0 install"
      ;;
  esac
}

install_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    debconf-utils \
    git \
    netcat-openbsd \
    python3 \
    python3-pip \
    python3-venv \
    alsa-utils \
    i2c-tools \
    raspi-config
}

enable_pi_interfaces() {
  if command -v raspi-config >/dev/null 2>&1; then
    raspi-config nonint do_i2c 0 || true
    raspi-config nonint do_spi 0 || true
  fi
}

install_whisplay_driver() {
  if [[ "${INSTALL_HARDWARE}" != "1" || "${INSTALL_WHISPLAY_DRIVER}" != "1" ]]; then
    return
  fi

  install -d -m 0755 "${VENDOR_DIR}"
  if [[ ! -d "${VENDOR_DIR}/Whisplay/.git" ]]; then
    git clone --depth 1 "${WHISPLAY_REPO}" "${VENDOR_DIR}/Whisplay"
  else
    git -C "${VENDOR_DIR}/Whisplay" pull --ff-only
  fi

  bash "${VENDOR_DIR}/Whisplay/install_driver.sh"
  NEEDS_REBOOT=1

  if [[ "${INSTALL_WHISPLAY_DAEMON}" == "1" ]]; then
    bash "${VENDOR_DIR}/Whisplay/daemon/install_whisplay_daemon_service.sh"
  fi
}

install_pisugar_power_manager() {
  if [[ "${INSTALL_HARDWARE}" != "1" || "${INSTALL_PISUGAR}" != "1" ]]; then
    return
  fi

  install -d -m 0755 "${VENDOR_DIR}"
  debconf-set-selections <<EOF
pisugar-server pisugar-server/model select ${PISUGAR_MODEL}
pisugar-server pisugar-server/auth-username string ${PISUGAR_AUTH_USER}
pisugar-server pisugar-server/auth-password password ${PISUGAR_AUTH_PASSWORD}
pisugar-poweroff pisugar-poweroff/model select ${PISUGAR_MODEL}
EOF
  curl -fsSL "${PISUGAR_INSTALLER_URL}" -o "${VENDOR_DIR}/pisugar-power-manager.sh"
  DEBIAN_FRONTEND=noninteractive bash "${VENDOR_DIR}/pisugar-power-manager.sh" -c release

  if [[ -f /etc/default/pisugar-server ]]; then
    sed -i -E "s|--model '[^']*'|--model '${PISUGAR_MODEL}'|g" /etc/default/pisugar-server || true
    systemctl restart pisugar-server || true
  fi

  if [[ -f /etc/default/pisugar-poweroff ]]; then
    sed -i -E "s|--model '[^']*'|--model '${PISUGAR_MODEL}'|g" /etc/default/pisugar-poweroff || true
    systemctl restart pisugar-poweroff || true
  fi
}

prepare_install_dir() {
  if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
    mkdir -p "${INSTALL_DIR}"
    git clone "${REPO_URL}" "${INSTALL_DIR}"
  fi

  chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}"
}

install_python_app() {
  sudo -u "${APP_USER}" python3 -m venv "${INSTALL_DIR}/.venv"
  sudo -u "${APP_USER}" "${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip
  sudo -u "${APP_USER}" "${INSTALL_DIR}/.venv/bin/python" -m pip install -e "${INSTALL_DIR}"
}

install_service() {
  cp "${INSTALL_DIR}/device/systemd/axiomvox.service" "/etc/systemd/system/${SERVICE_NAME}"
  sed -i \
    -e "s|WorkingDirectory=/opt/axiomvox|WorkingDirectory=${INSTALL_DIR}|g" \
    -e "s|ExecStart=/opt/axiomvox/.venv/bin/axiomvox-device|ExecStart=${INSTALL_DIR}/.venv/bin/axiomvox-device|g" \
    -e "s|--port 8080|--port ${WEB_PORT}|g" \
    -e "s|--status-file /run/axiomvox/status.json|--status-file ${STATUS_FILE}|g" \
    -e "s|User=pi|User=${APP_USER}|g" \
    -e "s|Group=pi|Group=${APP_GROUP}|g" \
    "/etc/systemd/system/${SERVICE_NAME}"

  install -d -m 0755 -o "${APP_USER}" -g "${APP_GROUP}" "$(dirname "${STATUS_FILE}")"
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}"
  systemctl restart "${SERVICE_NAME}"
}

print_summary() {
  local ip_address
  ip_address="$(hostname -I | awk '{print $1}')"
  cat <<EOF
AxiomVox installed.

Service: ${SERVICE_NAME}
Install directory: ${INSTALL_DIR}
Dashboard: http://${ip_address:-localhost}:${WEB_PORT}/

Useful checks:
  systemctl status ${SERVICE_NAME}
  journalctl -u ${SERVICE_NAME} -f
EOF

  if [[ "${NEEDS_REBOOT}" == "1" ]]; then
    cat <<EOF

Whisplay driver installation changed low-level hardware settings.
Reboot before final hardware validation:
  sudo reboot
EOF
  fi
}

require_root
detect_profile
install_packages
enable_pi_interfaces
prepare_install_dir
install_python_app
install_service
install_whisplay_driver
install_pisugar_power_manager
print_summary
