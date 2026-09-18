#!/usr/bin/env bash
set -euo pipefail

PREFIX="${TECTONIC_PREFIX:-$HOME/tectonic}"
VENV="${TECTONIC_VENV:-$HOME/.tectonic}"
REPO_URL="https://github.com/GSI-Fing-Udelar/tectonic.git"
ADD_BASHRC="no"

usage() {
  cat <<EOF
Usage: $0 [options]

Install Docker-platform dependencies on Ubuntu and Tectonic from this
repository checkout (pip install -e). This does not install the
published tectonic-cyberrange package from PyPI.

Options:
  --prefix DIR     Clone destination if not already inside a checkout
                   (default: $HOME/tectonic). Ignored when run from
                   inside a Tectonic clone.
  --venv DIR       Python virtualenv (default: $HOME/.tectonic)
  --add-bashrc     Append a tectonic-env alias to ~/.bashrc
  -h, --help       Show this help

Environment:
  TECTONIC_PREFIX  Same as --prefix
  TECTONIC_VENV    Same as --venv
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix) PREFIX="$2"; shift 2 ;;
    --venv) VENV="$2"; shift 2 ;;
    --add-bashrc) ADD_BASHRC="yes"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
  esac
done

if [[ "$(id -u)" -eq 0 ]]; then
  echo "Do not run this script as root. Use a sudo-capable user." >&2
  exit 1
fi

if [[ ! -f /etc/os-release ]]; then
  echo "Unsupported OS: /etc/os-release is missing." >&2
  exit 1
fi
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "This installer supports Ubuntu only. Detected: ${ID:-unknown}" >&2
  exit 1
fi

USER_NAME="$(id -un)"
ARCH="$(dpkg --print-architecture)"
CODENAME="${VERSION_CODENAME:-$(lsb_release -cs)}"

log() { printf '\n\033[1;36m==>\033[0m %s\n' "$*"; }
ok()  { printf '\033[1;32mOK\033[0m %s\n' "$*"; }
warn(){ printf '\033[1;33mWARN\033[0m %s\n' "$*"; }

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root=""
candidate="$script_dir"
for _ in 1 2 3 4; do
  if [[ -f "$candidate/tectonic.ini" && -f "$candidate/pyproject.toml" && -d "$candidate/tectonic" ]]; then
    repo_root="$candidate"
    break
  fi
  candidate="$(dirname "$candidate")"
done

sudo -v

log "Installing build dependencies"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  ca-certificates curl wget gnupg lsb-release \
  git openssh-client python3 python3-pip python3-venv python3-dev \
  build-essential pkg-config libvirt-dev

PY=""
for cand in python3.13 python3.12 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    if "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)'; then
      PY="$cand"
      break
    fi
  fi
done

if [[ -z "$PY" ]]; then
  if [[ "$CODENAME" == "jammy" || "$CODENAME" == "focal" ]]; then
    log "Installing Python 3.12 from deadsnakes"
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y software-properties-common
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update -y
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
      python3.12 python3.12-venv python3.12-dev
    PY=python3.12
  else
    echo "Python >= 3.12 is required and was not found." >&2
    exit 1
  fi
fi
ok "$($PY --version)"

if command -v terraform >/dev/null 2>&1 && command -v packer >/dev/null 2>&1; then
  ok "Terraform and Packer already installed"
else
  log "Installing Terraform and Packer"
  if [[ ! -f /usr/share/keyrings/hashicorp-archive-keyring.gpg ]]; then
    wget -O- https://apt.releases.hashicorp.com/gpg \
      | gpg --dearmor \
      | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg >/dev/null
  fi
  echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com ${CODENAME} main" \
    | sudo tee /etc/apt/sources.list.d/hashicorp.list >/dev/null
  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y terraform packer
fi
ok "$(terraform version | head -1)"
ok "$(packer version | head -1)"

if command -v docker >/dev/null 2>&1; then
  ok "Docker already installed"
else
  log "Installing Docker Engine"
  sudo install -m 0755 -d /etc/apt/keyrings
  sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
  sudo chmod a+r /etc/apt/keyrings/docker.asc
  echo "deb [arch=${ARCH} signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${CODENAME} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -y
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y docker-ce docker-ce-cli
  if command -v systemctl >/dev/null && systemctl list-units >/dev/null 2>&1; then
    sudo systemctl enable --now docker
  else
    warn "systemd is not available; start Docker yourself (WSL/container)"
  fi
fi
sudo usermod -aG docker "$USER_NAME"
ok "$(docker --version)"
warn "Log out and back in before using Docker without sudo"

log "Checking SSH key pair (~/.ssh/id_rsa.pub)"
mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
if [[ ! -f "$HOME/.ssh/id_rsa" && ! -f "$HOME/.ssh/id_rsa.pub" ]]; then
  ssh-keygen -t rsa -b 4096 -f "$HOME/.ssh/id_rsa" -N "" -C "tectonic@${HOSTNAME:-lab}"
elif [[ ! -f "$HOME/.ssh/id_rsa.pub" ]]; then
  echo "Found $HOME/.ssh/id_rsa without .pub; not overwriting." >&2
  exit 1
fi
chmod 644 "$HOME/.ssh/id_rsa.pub"
ok "$HOME/.ssh/id_rsa.pub"

if [[ -n "$repo_root" ]]; then
  log "Using existing repository at $repo_root"
else
  log "Cloning Tectonic into $PREFIX"
  if [[ -f "$PREFIX/tectonic.ini" && -f "$PREFIX/pyproject.toml" ]]; then
    repo_root="$PREFIX"
    ok "Already present"
  else
    mkdir -p "$(dirname "$PREFIX")"
    git clone --depth 1 "$REPO_URL" "$PREFIX"
    repo_root="$PREFIX"
  fi
fi

if [[ ! -f "$repo_root/tectonic.ini" ]]; then
  echo "tectonic.ini not found in $repo_root" >&2
  exit 1
fi

log "Installing this checkout in editable mode into $VENV"
if [[ ! -d "$VENV" ]]; then
  "$PY" -m venv "$VENV"
fi
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel
python -m pip install -e "$repo_root"
ok "tectonic $(command -v tectonic)"
deactivate

if [[ "$ADD_BASHRC" == "yes" && -f "$HOME/.bashrc" ]] && ! grep -q 'alias tectonic-env=' "$HOME/.bashrc"; then
  {
    echo ""
    echo "alias tectonic-env='source ${VENV}/bin/activate'"
  } >> "$HOME/.bashrc"
  ok "Alias tectonic-env added to ~/.bashrc"
fi

cat <<EOF

================================================================
Tectonic is installed from this git checkout, not from the
tectonic-cyberrange package on PyPI.

  Repository:  $repo_root
  Config:      $repo_root/tectonic.ini
  Virtualenv:  $VENV
  SSH pubkey:  $HOME/.ssh/id_rsa.pub

Next steps:
  1. Log out and back in (docker group).
  2. source $VENV/bin/activate
  3. tectonic -c $repo_root/tectonic.ini <lab_edition.yml> create-images
     tectonic -c $repo_root/tectonic.ini <lab_edition.yml> deploy

Docker runs scenario containers in privileged mode. Prefer Libvirt
or AWS for class deployments.
================================================================
EOF