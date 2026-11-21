#!/bin/bash
# Osborne OS - update the desktop UI straight from GitHub.
#   curl -fsSL https://raw.githubusercontent.com/tareknahas85-star/Osborne-OS/main/ui/update.sh | sudo bash
set -e
[ "$(id -u)" = 0 ] || { echo "Run with sudo:  curl -fsSL <this url> | sudo bash"; exit 1; }
BRANCH="${OSB_BRANCH:-main}"
SHA=$(curl -fsSL -H "User-Agent: osborne" https://api.github.com/repos/tareknahas85-star/Osborne-OS/commits/main | sed -n 's/^  "sha": "\([0-9a-f]*\)".*/\1/p' | head -1)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
echo "Downloading Osborne UI ($BRANCH)..."
curl -fsSL "https://github.com/tareknahas85-star/Osborne-OS/archive/refs/heads/$BRANCH.tar.gz" | tar xz -C "$T" --strip-components=1
bash "$T/ui/install.sh"
[ -n "$SHA" ] && echo "$SHA" > /usr/local/lib/osborne/version
echo "Update complete."
