#!/bin/bash
# Osborne OS - update the desktop UI straight from GitHub.
#   curl -fsSL https://raw.githubusercontent.com/tareknahas85-star/Osborne-OS/main/ui/update.sh | sudo bash
set -e
exec > >(tee -a /var/log/osborne-update.log) 2>&1
echo "=== update $(date) ==="
[ "$(id -u)" = 0 ] || { echo "Run with sudo:  curl -fsSL <this url> | sudo bash"; exit 1; }
BRANCH="${OSB_BRANCH:-main}"
SHA="${OSB_SHA:-}"
echo "$SHA" | grep -Eq '^[0-9a-f]{40}$' || SHA=$(curl -fsSL -H "User-Agent: osborne" -H "Accept: application/vnd.github.sha" https://api.github.com/repos/tareknahas85-star/Osborne-OS/commits/main 2>/dev/null || true)
echo "$SHA" | grep -Eq '^[0-9a-f]{40}$' || SHA=$(git ls-remote https://github.com/tareknahas85-star/Osborne-OS.git refs/heads/main 2>/dev/null | cut -f1)
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
echo "Downloading Osborne UI ($BRANCH)..."
curl -fsSL "https://github.com/tareknahas85-star/Osborne-OS/archive/refs/heads/$BRANCH.tar.gz" | tar xz -C "$T" --strip-components=1
bash "$T/ui/install.sh"
[ -n "$SHA" ] && echo "$SHA" > /usr/local/lib/osborne/version
echo "Update complete."
