#!/bin/bash
# Osborne OS - update the desktop UI straight from GitHub.
#   curl -fsSL https://raw.githubusercontent.com/tareknahas85-star/Osborne-OS/main/ui/update.sh | sudo bash
set -e
[ "$(id -u)" = 0 ] || { echo "Run with sudo:  curl -fsSL <this url> | sudo bash"; exit 1; }
BRANCH="${OSB_BRANCH:-main}"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
echo "Downloading Osborne UI ($BRANCH)..."
curl -fsSL "https://github.com/tareknahas85-star/Osborne-OS/archive/refs/heads/$BRANCH.tar.gz" | tar xz -C "$T" --strip-components=1
bash "$T/ui/install.sh"
