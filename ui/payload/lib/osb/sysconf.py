"""Small system-level settings applied from the shell and Settings: night light, touchpad, power/lock, interface scale, language."""
import os, json, re, subprocess, time
CONF = os.path.expanduser('~/.config/osborne')

def _load(name, default):
    try:
        d = json.load(open(os.path.join(CONF, name)))
        out = dict(default); out.update(d if isinstance(d, dict) else {}); return out
    except Exception: return dict(default)
def _save(name, d):
    os.makedirs(CONF, exist_ok=True); json.dump(d, open(os.path.join(CONF, name), 'w'))

def _run(cmd, **kw):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=8, **kw).stdout
    except Exception: return ''

# ---- interface scale (multiplier on top of the automatic screen scale)
SCALES = [('Small', 0.85), ('Normal', 1.0), ('Large', 1.2), ('Extra large', 1.45)]
def get_ui_scale():
    try: return max(0.6, min(2.0, float(open(os.path.join(CONF, 'scale')).read().strip())))
    except Exception: return 1.0
def set_ui_scale(v): os.makedirs(CONF, exist_ok=True); open(os.path.join(CONF, 'scale'), 'w').write('%.2f' % v)

# ---- language
LANGS = [('en', 'English'), ('ar', 'العربية (شامي)')]
def get_lang():
    try:
        v = open(os.path.join(CONF, 'lang')).read().strip(); return v if v in ('en', 'ar') else 'en'
    except Exception: return 'en'
def set_lang(v): os.makedirs(CONF, exist_ok=True); open(os.path.join(CONF, 'lang'), 'w').write(v)

# ---- night light
NIGHT_DEFAULT = {'mode': 'off', 'temp': 4000}   # off | on | auto (20:00-06:00)
def get_night(): return _load('nightlight.json', NIGHT_DEFAULT)
def set_night(d): _save('nightlight.json', d)
_night_last = [None]
def apply_night():
    """Warm the screen colours. Only talks to the display when the wanted state changed, so there is no flicker every minute."""
    d = get_night(); h = time.localtime().tm_hour
    on = d['mode'] == 'on' or (d['mode'] == 'auto' and (h >= 20 or h < 6))
    want = ('on', int(d['temp'])) if on else ('off', 0)
    if want == _night_last[0] or (want[0] == 'off' and _night_last[0] is None): _night_last[0] = want; return
    _night_last[0] = want
    if on: subprocess.Popen(['redshift', '-P', '-O', str(int(d['temp']))], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else: subprocess.Popen(['redshift', '-x'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ---- touchpad
TP_DEFAULT = {'tap': True, 'natural': False, 'speed': 0.0}
def get_tp(): return _load('touchpad.json', TP_DEFAULT)
def set_tp(d): _save('touchpad.json', d)
def apply_touchpad():
    d = get_tp()
    for ln in _run('xinput list --name-only').splitlines():
        nm = ln.strip()
        if not nm or not re.search(r'touchpad|trackpad|synaptics|clickpad', nm, re.I): continue
        q = "'" + nm.replace("'", "'\\''") + "'"
        _run('xinput set-prop %s "libinput Tapping Enabled" %d' % (q, 1 if d['tap'] else 0))
        _run('xinput set-prop %s "libinput Natural Scrolling Enabled" %d' % (q, 1 if d['natural'] else 0))
        _run('xinput set-prop %s "libinput Accel Speed" %.2f' % (q, d['speed']))

# ---- power / lock
PW_DEFAULT = {'lock': 10, 'off': 15}   # minutes, 0 = never
def get_power(): return _load('power.json', PW_DEFAULT)
def set_power(d): _save('power.json', d)
def apply_power():
    d = get_power(); lock = int(d['lock']) * 60; off = int(d['off']) * 60
    _run('xset s %d 10' % lock if lock else 'xset s off')
    _run('xset +dpms; xset dpms %d %d %d' % (off, off, off) if off else 'xset -dpms')
