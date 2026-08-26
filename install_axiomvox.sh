#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${AXIOMVOX_REPO_URL:-https://github.com/drgncabe/AxiomVox.git}"
BRANCH="${AXIOMVOX_BRANCH:-main}"
INSTALL_DIR="${AXIOMVOX_INSTALL_DIR:-/opt/axiomvox}"

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this installer with sudo." >&2
    exit 1
  fi
}

print_banner() {
  local machine
  machine="$(uname -m 2>/dev/null || echo unknown)"
  cat <<'EOF'
AxiomVox Installer

Fresh Raspberry Pi OS Lite -> AxiomVox M0 appliance.
This installs system packages, Whisplay drivers, PiSugar 3 tools,
the AxiomVox device app, and the systemd autostart service.
EOF
  echo
  echo "Detected architecture: ${machine}"
  case "${machine}" in
    armv6l)
      echo "Profile: Raspberry Pi Zero W / Raspberry Pi OS Lite 32-bit"
      ;;
    aarch64)
      echo "Profile: Raspberry Pi Zero 2 W / Raspberry Pi OS Lite 64-bit"
      ;;
    armv7l)
      echo "Profile: Raspberry Pi OS 32-bit on newer Raspberry Pi hardware"
      ;;
  esac
}

install_bootstrap_packages() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update
  apt-get install -y --no-install-recommends ca-certificates git
}

prepare_repo() {
  if [[ -d "${INSTALL_DIR}/.git" ]]; then
    git -C "${INSTALL_DIR}" fetch origin
    git -C "${INSTALL_DIR}" checkout "${BRANCH}"
    git -C "${INSTALL_DIR}" pull --ff-only origin "${BRANCH}"
  else
    mkdir -p "$(dirname "${INSTALL_DIR}")"
    git clone --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
  fi
}

choose_install_type() {
  if [[ "${AXIOMVOX_INSTALL_MODE:-}" != "" ]]; then
    echo "${AXIOMVOX_INSTALL_MODE}"
    return
  fi

  cat <<'EOF'

Choose install type:
  1) Raspberry Pi appliance with Whisplay + PiSugar 3
  2) Raspberry Pi appliance without vendor hardware drivers
  3) Server/development checkout only
  4) Update existing AxiomVox install
  q) Quit
EOF

  read -r -p "Selection [1]: " selection
  echo "${selection:-1}"
}

run_choice() {
  local choice="$1"
  case "${choice}" in
    1|device|appliance)
      bash "${INSTALL_DIR}/scripts/install.sh"
      ;;
    2|device-no-hardware|no-hardware)
      AXIOMVOX_INSTALL_HARDWARE=0 bash "${INSTALL_DIR}/scripts/install.sh"
      ;;
    3|server|dev|development)
      echo "Repository installed at ${INSTALL_DIR}."
      echo "Server runtime is documented but not implemented in M0."
      ;;
    4|update)
      bash "${INSTALL_DIR}/scripts/update.sh"
      ;;
    q|Q|quit|exit)
      echo "Install cancelled."
      ;;
    *)
      echo "Unknown selection: ${choice}" >&2
      exit 1
      ;;
  esac
}

require_root
print_banner
install_bootstrap_packages
prepare_repo
run_choice "$(choose_install_type)"
