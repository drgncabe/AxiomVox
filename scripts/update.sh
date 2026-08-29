#!/usr/bin/env bash
set -euo pipefail

APP_USER="${AXIOMVOX_USER:-${SUDO_USER:-pi}}"
APP_GROUP="${AXIOMVOX_GROUP:-$APP_USER}"
INSTALL_DIR="${AXIOMVOX_INSTALL_DIR:-/opt/axiomvox}"
SERVICE_NAME="${AXIOMVOX_SERVICE_NAME:-axiomvox.service}"
BRANCH="${AXIOMVOX_BRANCH:-main}"
UPDATE_HARDWARE="${AXIOMVOX_UPDATE_HARDWARE:-0}"
VENDOR_DIR="${AXIOMVOX_VENDOR_DIR:-/opt/axiomvox-vendor}"
PISUGAR_INSTALLER_URL="${AXIOMVOX_PISUGAR_INSTALLER_URL:-https://cdn.pisugar.com/release/pisugar-power-manager.sh}"
WEB_PORT="${AXIOMVOX_WEB_PORT:-8080}"
STATUS_FILE="${AXIOMVOX_STATUS_FILE:-/run/axiomvox/status.json}"
SESSION_DIR="${AXIOMVOX_SESSION_DIR:-/var/lib/axiomvox/sessions}"
CAPTURE_DEVICE="${AXIOMVOX_CAPTURE_DEVICE:-plughw:whisplaysound,0}"
CAPTURE_FORMAT="${AXIOMVOX_CAPTURE_FORMAT:-S32_LE}"
CAPTURE_RATE="${AXIOMVOX_CAPTURE_RATE:-16000}"
CAPTURE_CHANNELS="${AXIOMVOX_CAPTURE_CHANNELS:-2}"

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this updater with sudo." >&2
    exit 1
  fi
}

require_checkout() {
  if [[ ! -d "${INSTALL_DIR}/.git" ]]; then
    echo "No AxiomVox git checkout found at ${INSTALL_DIR}." >&2
    exit 1
  fi
}

update_checkout() {
  git -C "${INSTALL_DIR}" fetch origin
  git -C "${INSTALL_DIR}" checkout "${BRANCH}"
  git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
  chown -R "${APP_USER}:${APP_GROUP}" "${INSTALL_DIR}"
}

install_runtime_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends python3-libgpiod python3-pil python3-spidev
}

update_python_app() {
  if [[ -f "${INSTALL_DIR}/.venv/pyvenv.cfg" ]] && ! grep -q "include-system-site-packages = true" "${INSTALL_DIR}/.venv/pyvenv.cfg"; then
    rm -rf "${INSTALL_DIR}/.venv"
  fi
  sudo -u "${APP_USER}" python3 -m venv --system-site-packages "${INSTALL_DIR}/.venv"
  sudo -u "${APP_USER}" "${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip
  sudo -u "${APP_USER}" "${INSTALL_DIR}/.venv/bin/python" -m pip install -e "${INSTALL_DIR}"
}

install_cli_launcher() {
  ln -sf "${INSTALL_DIR}/.venv/bin/axiomvox-device" /usr/local/bin/axiomvox-device
}

configure_user_groups() {
  for group in audio video input i2c gpio spi; do
    if getent group "${group}" >/dev/null 2>&1; then
      usermod -aG "${group}" "${APP_USER}"
    fi
  done
}

install_service() {
  cp "${INSTALL_DIR}/device/systemd/axiomvox.service" "/etc/systemd/system/${SERVICE_NAME}"
  sed -i \
    -e "s|WorkingDirectory=/opt/axiomvox|WorkingDirectory=${INSTALL_DIR}|g" \
    -e "s|ExecStart=/opt/axiomvox/.venv/bin/axiomvox-device|ExecStart=${INSTALL_DIR}/.venv/bin/axiomvox-device|g" \
    -e "s|--port 8080|--port ${WEB_PORT}|g" \
    -e "s|--status-file /run/axiomvox/status.json|--status-file ${STATUS_FILE}|g" \
    -e "s|--session-dir /var/lib/axiomvox/sessions|--session-dir ${SESSION_DIR}|g" \
    -e "s|--capture-device plughw:whisplaysound,0|--capture-device ${CAPTURE_DEVICE}|g" \
    -e "s|--capture-format S32_LE|--capture-format ${CAPTURE_FORMAT}|g" \
    -e "s|--capture-rate 16000|--capture-rate ${CAPTURE_RATE}|g" \
    -e "s|--capture-channels 2|--capture-channels ${CAPTURE_CHANNELS}|g" \
    -e "s|User=pi|User=${APP_USER}|g" \
    -e "s|Group=pi|Group=${APP_GROUP}|g" \
    "/etc/systemd/system/${SERVICE_NAME}"

  install -d -m 0755 -o "${APP_USER}" -g "${APP_GROUP}" "$(dirname "${STATUS_FILE}")"
  install -d -m 0755 -o "${APP_USER}" -g "${APP_GROUP}" "${SESSION_DIR}"
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}"
}

update_hardware_tools() {
  if [[ "${UPDATE_HARDWARE}" != "1" ]]; then
    return
  fi

  if [[ -d "${VENDOR_DIR}/Whisplay/.git" ]]; then
    git -C "${VENDOR_DIR}/Whisplay" pull --ff-only
    bash "${VENDOR_DIR}/Whisplay/install_driver.sh"
  fi

  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "${PISUGAR_INSTALLER_URL}" -o "${VENDOR_DIR}/pisugar-power-manager.sh"
    bash "${VENDOR_DIR}/pisugar-power-manager.sh" -c release
  fi
}

restart_service() {
  systemctl daemon-reload
  systemctl restart "${SERVICE_NAME}"
}

print_summary() {
  cat <<EOF
AxiomVox updated.

Branch: ${BRANCH}
Install directory: ${INSTALL_DIR}
Service: ${SERVICE_NAME}
Command: /usr/local/bin/axiomvox-device

Useful checks:
  systemctl status ${SERVICE_NAME}
  journalctl -u ${SERVICE_NAME} -f
EOF
}

require_root
require_checkout
update_checkout
install_runtime_packages
update_hardware_tools
update_python_app
install_cli_launcher
configure_user_groups
install_service
restart_service
print_summary
