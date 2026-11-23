"""Background upkeep: pending system updates, daily Flatpak app updates, and the readings shown in Settings > System Status.
Only free, local tools (apt, flatpak, nmcli, sysfs). Nothing here needs a password."""
import os, json, time, shutil, subprocess

CONF = os.path.expanduser('~/.config/osborne')
STATE = os.path.join(CONF, 'upkeep.json')
DAY = 24 * 3600

def load():
    try: return json.load(open(STATE))
    except Exception: return {}

def save(d):
    os.makedirs(CONF, exist_ok=True); json.dump(d, open(STATE, 'w'))

def _run(cmd, timeout=120):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception: return ''

def count_updates():
    """(all pending updates, security updates) from apt."""
    lines = [l for l in _run(['apt', 'list', '--upgradable'], 60).splitlines() if '/' in l and 'Listing' not in l]
    sec = sum(1 for l in lines if '-security' in l.split('/', 1)[1])
    return len(lines), sec

def check_updates(notify=True):
    """Refresh the update counts; notify once a day when security updates are waiting."""
    total, sec = count_updates()
    st = load(); st.update(total=total, security=sec, checked=time.time()); save(st)
    if notify and sec > 0 and time.strftime('%Y-%m-%d') != st.get('notified'):
        st['notified'] = time.strftime('%Y-%m-%d'); save(st)
        subprocess.Popen(['notify-send', '-a', 'System Update', 'Security updates available',
                          '%d security update%s waiting. Open Settings > System Update.' % (sec, '' if sec == 1 else 's')])
    return total, sec

def autoupdate_on():
    return bool(load().get('autoupdate', True))

def set_autoupdate(on):
    st = load(); st['autoupdate'] = bool(on); save(st)

def flatpak_update_daily():
    """Update installed Flatpak apps once a day (when the setting is on and flatpak is installed)."""
    st = load()
    if not st.get('autoupdate', True) or not shutil.which('flatpak'): return
    if time.time() - st.get('flatpak_at', 0) < DAY: return
    st['flatpak_at'] = time.time(); save(st)
    subprocess.run(['flatpak', 'update', '-y', '--noninteractive'], capture_output=True, timeout=3600)

def cpu_temp():
    temps = []
    for z in os.listdir('/sys/class/thermal') if os.path.isdir('/sys/class/thermal') else []:
        try: temps.append(int(open('/sys/class/thermal/%s/temp' % z).read()) / 1000.0)
        except Exception: pass
    return max(temps) if temps else None

def disk_free_gb():
    try: return shutil.disk_usage('/').free / 1073741824.0
    except Exception: return None

def vpn_active():
    out = _run(['nmcli', '-t', '-f', 'TYPE', 'connection', 'show', '--active'], 5)
    return any(t.strip() in ('vpn', 'wireguard') for t in out.splitlines())
