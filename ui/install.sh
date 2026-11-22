#!/bin/bash
# Osborne OS - UI v4 installer (HeroUI "Linux Desktop" design + Wi-Fi/Bluetooth/sound fix)
# Run on the live system or inside a chroot of the card:   sudo bash install-osborne-ui.sh
set -e
[ "$(id -u)" = 0 ] || { echo "Run with sudo"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"; P="$HERE/payload"
export DEBIAN_FRONTEND=noninteractive
echo "[1/6] Packages (connectivity, sound, UI runtime)..."
apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  network-manager wpasupplicant iw rfkill wireless-regdb crda 2>/dev/null || apt-get install -y -qq --no-install-recommends network-manager wpasupplicant iw rfkill wireless-regdb
apt-get install -y -qq --no-install-recommends \
  bluez blueman libspa-0.2-bluetooth pipewire pipewire-pulse wireplumber pipewire-alsa alsa-utils pavucontrol \
  brightnessctl playerctl xdotool x11-utils picom rofi lxterminal xdg-utils \
  python3 python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 librsvg2-common fonts-inter \
  papirus-icon-theme network-manager-gnome lxpolkit dunst libnotify-bin qt5-gtk-platformtheme fonts-jetbrains-mono adwaita-icon-theme gnome-themes-extra libglib2.0-bin \
  python3-pam scrot xclip xss-lock x11-xserver-utils \
  xcape fonts-noto-core sound-theme-freedesktop pulseaudio-utils xserver-xorg-input-libinput curl ca-certificates
echo "[2/6] Installing shell + apps..."
install -d /usr/local/lib/osborne
rm -rf /usr/local/lib/osborne/osb; cp -r "$P/lib/osb" /usr/local/lib/osborne/osb
for b in osb-shell osb-files osb-wifi osb-apps osb-power osb-settings osb-calc osb-apply-theme osb-notifs osb-lock osb-monitor osb-switcher osb-brightness osb-welcome osb-store; do
  sed 's#^sys.path.insert.*#sys.path.insert(0, "/usr/local/lib/osborne")#' "$P/bin/$b" > /usr/local/bin/$b; chmod 755 /usr/local/bin/$b; done
install -m 755 "$P/bin/osb-launcher" /usr/local/bin/
install -m 755 "$P/bin/osb-shot" /usr/local/bin/
printf "QT_QPA_PLATFORMTHEME=gtk3\nGTK_THEME=\n" >/dev/null
grep -q QT_QPA_PLATFORMTHEME /etc/environment 2>/dev/null || echo "QT_QPA_PLATFORMTHEME=gtk2" >> /etc/environment
install -m 755 "$P/bin/osb-compositor" /usr/local/bin/
install -d /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/00-osborne-keyboard.conf <<'XK'
Section "InputClass"
    Identifier "osborne keyboard"
    MatchIsKeyboard "on"
    Option "XkbLayout" "us,ara"
    Option "XkbOptions" "grp:alt_shift_toggle"
EndSection
XK
cat > /etc/X11/xorg.conf.d/40-osborne-input.conf <<'XC'
Section "InputClass"
    Identifier "Osborne touchpad"
    MatchIsTouchpad "on"
    Driver "libinput"
    Option "Tapping" "on"
    Option "TappingButtonMap" "lrm"
    Option "ClickMethod" "buttonareas"
    Option "DisableWhileTyping" "on"
    Option "NaturalScrolling" "off"
EndSection
XC
echo "[2b/6] Google Chrome (replaces Firefox)..."
if ! command -v google-chrome-stable >/dev/null 2>&1; then
  if curl -fsSL -o /tmp/osb-chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb; then
    apt-get install -y -qq /tmp/osb-chrome.deb || echo "Chrome install failed (will retry on next update)"
  else echo "Could not download Chrome (no internet?)"; fi
  rm -f /tmp/osb-chrome.deb
fi
if command -v google-chrome-stable >/dev/null 2>&1; then
  update-alternatives --set x-www-browser /usr/bin/google-chrome-stable >/dev/null 2>&1 || true
  update-alternatives --set gnome-www-browser /usr/bin/google-chrome-stable >/dev/null 2>&1 || true
  apt-get purge -y -qq firefox >/dev/null 2>&1 || true
fi
echo "[3/6] Radios and audio services..."
systemctl enable NetworkManager bluetooth >/dev/null 2>&1 || true
systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service >/dev/null 2>&1 || true
rfkill unblock all 2>/dev/null || true
install -d /etc/NetworkManager/conf.d; printf '[main]\nplugins=ifupdown,keyfile\n[ifupdown]\nmanaged=true\n[device]\nwifi.scan-rand-mac-address=no\n' > /etc/NetworkManager/conf.d/10-osborne.conf
echo "[4/6] Per-user config..."
cfgset() { # $1 = home dir, $2 = user
  local H="$1" U="$2"
  install -d -o "$U" -g "$U" "$H/.config/osborne" "$H/.config/openbox"
  cp "$P/cfg/"* "$H/.config/osborne/"
  [ -f "$H/.config/openbox/autostart" ] && [ ! -f "$H/.config/openbox/autostart.pre-ui2" ] && cp "$H/.config/openbox/autostart" "$H/.config/openbox/autostart.pre-ui2"
  cat > "$H/.config/openbox/autostart" <<'AS'
# Osborne OS UI v4
rfkill unblock all &
osb-apply-theme >/dev/null 2>&1
[ -x "$HOME/.config/osborne/keyboard.sh" ] && { "$HOME/.config/osborne/keyboard.sh"; (sleep 4; "$HOME/.config/osborne/keyboard.sh") & } &
osb-compositor &
(sleep 2; osb-brightness restore) &
(sleep 4; osb-welcome) &
xcape -e 'Super_L=Super_L|space' &
(sleep 1; pgrep -x pipewire >/dev/null || { pipewire & sleep 1; pipewire-pulse & wireplumber & }) &
(sleep 6; [ -f "$HOME/.config/osborne/audio-init" ] || { wpctl set-mute @DEFAULT_AUDIO_SINK@ 0 && wpctl set-volume @DEFAULT_AUDIO_SINK@ 0.6 && touch "$HOME/.config/osborne/audio-init"; for c in Master Speaker Headphone PCM; do amixer -q sset "$c" unmute 2>/dev/null; done; }) &
lxpolkit &
blueman-applet &
dunst &
xset s 600 10 2>/dev/null
xss-lock -- osb-lock &
(sleep 0.6; osb-shell) &
(sleep 2.2; osb-files) &
AS
  [ -f "$H/.config/osborne/keyboard.sh" ] || { printf '#!/bin/sh\nsetxkbmap -layout us,ara -option grp:alt_shift_toggle\n' > "$H/.config/osborne/keyboard.sh"; chmod +x "$H/.config/osborne/keyboard.sh"; }
  sed -i -E 's/(-layout [a-z,]*[,])ar( |$)/\1ara\2/; s/-layout ar /-layout ara /' "$H/.config/osborne/keyboard.sh" 2>/dev/null || true
  # shortcuts: Super+Space = apps, volume / brightness keys
  RC="$H/.config/openbox/rc.xml"
  if [ -f "$RC" ]; then
    python3 - "$RC" <<'PY'
import sys,re
p=sys.argv[1]; x=open(p).read()
k='''
    <keybind key="W-space"><action name="Execute"><command>osb-apps</command></action></keybind>
    <keybind key="Print"><action name="Execute"><command>osb-shot</command></action></keybind>
    <keybind key="S-Print"><action name="Execute"><command>osb-shot area</command></action></keybind>
    <keybind key="A-Print"><action name="Execute"><command>osb-shot window</command></action></keybind>
    <keybind key="W-l"><action name="Execute"><command>osb-lock</command></action></keybind>
    <keybind key="A-Tab"><action name="Execute"><command>osb-switcher alttab next</command></action></keybind>
    <keybind key="A-S-Tab"><action name="Execute"><command>osb-switcher alttab prev</command></action></keybind>
    <keybind key="W-Tab"><action name="Execute"><command>osb-switcher overview</command></action></keybind>
    <keybind key="W-m"><action name="Execute"><command>osb-monitor</command></action></keybind>
    <keybind key="XF86AudioRaiseVolume"><action name="Execute"><command>wpctl set-volume -l 1.0 @DEFAULT_AUDIO_SINK@ 5%+</command></action></keybind>
    <keybind key="XF86AudioLowerVolume"><action name="Execute"><command>wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-</command></action></keybind>
    <keybind key="XF86AudioMute"><action name="Execute"><command>wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle</command></action></keybind>
    <keybind key="XF86MonBrightnessUp"><action name="Execute"><command>osb-brightness up</command></action></keybind>
    <keybind key="XF86MonBrightnessDown"><action name="Execute"><command>osb-brightness down</command></action></keybind>
'''
x=re.sub(r'\s*<keybind key="(A-Tab|A-S-Tab|W-Tab|XF86MonBrightnessUp|XF86MonBrightnessDown)">.*?</keybind>','',x,flags=re.S)
k=''.join(l+'\n' for l in k.split('\n') if l.strip() and re.search(r'key="([^"]+)"',l) and 'key="%s"'%re.search(r'key="([^"]+)"',l).group(1) not in x)
open(p,'w').write(x.replace('</keyboard>',k+'  </keyboard>',1) if (k and '</keyboard>' in x) else x)
PY
  fi
  [ -f "$H/.config/osborne/mode" ] || echo light > "$H/.config/osborne/mode"
  chown -R "$U:$U" "$H/.config/osborne" "$H/.config/openbox"
  usermod -aG audio,video,netdev,bluetooth "$U" 2>/dev/null || true
}
for d in /home/*; do u=$(basename "$d"); id "$u" >/dev/null 2>&1 && cfgset "$d" "$u"; done
install -d /etc/skel/.config/osborne /etc/skel/.config/openbox; cp "$P/cfg/"* /etc/skel/.config/osborne/
echo "[5/6] Desktop entries..."
cat > /usr/share/applications/osb-files.desktop <<'DE'
[Desktop Entry]
Type=Application
Name=Files
Exec=osb-files
Icon=system-file-manager
Categories=System;FileManager;
StartupWMClass=osb-files
DE
cat > /usr/share/applications/osb-wifi.desktop <<'DE'
[Desktop Entry]
Type=Application
Name=Wi-Fi
Exec=osb-wifi
Icon=network-wireless
Categories=Settings;Network;
DE
for n in "settings:Settings:preferences-system:osb-settings" "calc:Calculator:accessories-calculator:osb-calc" "apps:Apps:view-app-grid-symbolic:osb-apps" "monitor:System Monitor:utilities-system-monitor:osb-monitor"; do
  IFS=: read -r id nm ic ex <<<"$n"
  printf '[Desktop Entry]\nType=Application\nName=%s\nExec=%s\nIcon=%s\nCategories=Utility;\nStartupWMClass=%s\n' "$nm" "$ex" "$ic" "$ex" > /usr/share/applications/osb-$id.desktop
done
sed -i '/^NoDisplay/d' /usr/share/applications/osb-apps.desktop; echo 'NoDisplay=true' >> /usr/share/applications/osb-apps.desktop
for h in picom rofi rofi-theme-selector vim tint2 tint2conf nm-connection-editor lxappearance pcmanfm-desktop-pref pcmanfm file-roller org.gnome.FileRoller mousepad org.xfce.mousepad org.xfce.mousepad-settings pavucontrol blueman-manager blueman-adapters osb-wifi firefox htop lxrandr obconf openbox-config; do [ -f /usr/share/applications/$h.desktop ] && { install -d /usr/local/share/applications; cp /usr/share/applications/$h.desktop /usr/local/share/applications/; sed -i '/^NoDisplay/d' /usr/local/share/applications/$h.desktop; echo 'NoDisplay=true' >> /usr/local/share/applications/$h.desktop; }; done
echo "[6/6] Software stores (Snap + Flathub)..."
apt-get install -y -qq --no-install-recommends snapd flatpak >/dev/null 2>&1 || echo "  (could not install snapd/flatpak: no internet or not available)"
command -v flatpak >/dev/null 2>&1 && flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo >/dev/null 2>&1 || true
systemctl enable --now snapd.socket >/dev/null 2>&1 || true
# Proton VPN (official free app)
if ! dpkg -s proton-vpn-gtk-app >/dev/null 2>&1; then
  echo "  Proton VPN..."
  PV=$(mktemp -d); if curl -fsSL -m 120 -o "$PV/pvpn.deb" https://repo.protonvpn.com/debian/dists/stable/main/binary-all/protonvpn-stable-release_1.0.8_all.deb && dpkg -i "$PV/pvpn.deb" >/dev/null 2>&1; then
    apt-get update -qq >/dev/null 2>&1 || true
    apt-get install -y -qq --no-install-recommends proton-vpn-gtk-app gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1 >/dev/null 2>&1 || echo "  (could not install Proton VPN)"
  else echo "  (could not download Proton VPN)"; fi
  rm -rf "$PV"
fi
printf '[Desktop Entry]\nType=Application\nName=Software\nComment=Install apps from Flathub and the Snap Store\nExec=osb-store\nIcon=system-software-install\nCategories=System;\n' > /usr/share/applications/osb-store.desktop
grep -q snapd/desktop /etc/environment 2>/dev/null || echo 'XDG_DATA_DIRS=/usr/local/share:/usr/share:/var/lib/snapd/desktop:/var/lib/flatpak/exports/share' >> /etc/environment
# boot resilience: repair the file system automatically after a hard power-off
if [ -f /boot/grub/grub.cfg ] && grep -q 'root=LABEL=osb-root' /boot/grub/grub.cfg && ! grep -q 'fsck.repair=yes' /boot/grub/grub.cfg; then
  sed -i 's#root=LABEL=osb-root ro#root=LABEL=osb-root ro fsck.mode=auto fsck.repair=yes#' /boot/grub/grub.cfg || true
fi
echo "Done. Log out and back in (or reboot) to load the new desktop."
