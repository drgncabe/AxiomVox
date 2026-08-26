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

update_python_app() {
  sudo -u "${APP_USER}" python3 -m venv "${INSTALL_DIR}/.venv"
  sudo -u "${APP_USER}" "${INSTALL_DIR}/.venv/bin/python" -m pip install --upgrade pip
  sudo -u "${APP_USER}" "${INSTALL_DIR}/.venv/bin/python" -m pip install -e "${INSTALL_DIR}"
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

Useful checks:
  systemctl status ${SERVICE_NAME}
  journalctl -u ${SERVICE_NAME} -f
EOF
}

require_root
require_checkout
update_checkout
update_hardware_tools
update_python_app
restart_service
print_summary
