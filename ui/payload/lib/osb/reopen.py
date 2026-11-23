"""Remember the apps whose windows were closed, so Ctrl+Shift+T can open the last one again."""
import os, json, subprocess, threading

CONF = os.path.expanduser('~/.config/osborne')
CLOSED = os.path.join(CONF, 'closed.json')
MAX = 10
SKIP = ('openbox', 'dunst', 'picom', 'xdotool', 'xprop', 'lightdm')
# the desktop's own background helpers: their windows are not user apps
BACKGROUND = ('osb-shell', 'osb-clip', 'osb-widgets', 'osb-notifs', 'osb-lock', 'osb-compositor', 'osb-switcher', 'osb-brightness', 'osb-welcome', 'osb-apply-theme')

def _sh(cmd):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=3).stdout
    except Exception: return ''

def clients():
    """Ids of the normal windows the window manager currently knows about."""
    out = _sh(['xprop', '-root', '_NET_CLIENT_LIST'])
    return [int(x, 16) for x in out.replace(',', ' ').split() if x.startswith('0x')]

def command_of(wid):
    """argv that started the app owning this window, or None."""
    out = _sh(['xprop', '-id', str(wid), '_NET_WM_PID'])
    try: pid = int(out.split('=')[-1].strip())
    except Exception: return None
    try: argv = [a.decode('utf-8', 'replace') for a in open('/proc/%d/cmdline' % pid, 'rb').read().split(b'\0') if a]
    except Exception: return None
    if not argv: return None
    names = [os.path.basename(a).lower() for a in argv[:2]]
    if any(n in BACKGROUND for n in names): return None
    if os.path.basename(argv[0]).lower().startswith(SKIP): return None
    return argv

def load():
    try: return json.load(open(CLOSED))
    except Exception: return []

def push(argv):
    lst = [a for a in load() if a != argv] + [argv]
    os.makedirs(CONF, exist_ok=True); json.dump(lst[-MAX:], open(CLOSED, 'w'))

def pop():
    lst = load()
    if not lst: return None
    argv = lst.pop(); os.makedirs(CONF, exist_ok=True); json.dump(lst, open(CLOSED, 'w')); return argv

class Tracker:
    """Polled from the shell: records each app's command when its window appears and saves it when the window goes away."""
    def __init__(self): self.seen = {}
    def tick(self):
        now = set(clients())
        for wid in now - set(self.seen):
            self.seen[wid] = command_of(wid)
        for wid in set(self.seen) - now:
            argv = self.seen.pop(wid)
            if argv: push(argv)
    def run_async(self):
        threading.Thread(target=self.tick, daemon=True).start()

def main():
    argv = pop()
    if argv: subprocess.Popen(argv, start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
