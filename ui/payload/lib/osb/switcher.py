"""osb-switcher: Alt+Tab window switcher and the Activities overview."""
import os, re, sys, subprocess
from .common import *

NAMES = {'osb-files': 'Files', 'osb-settings': 'Settings', 'osb-calc': 'Calculator', 'osb-monitor': 'System Monitor', 'lxterminal': 'Terminal', 'google-chrome': 'Chrome', 'firefox': 'Firefox'}

def xp(args, t=3):
    try: return subprocess.run(['xprop'] + args, capture_output=True, text=True, timeout=t).stdout
    except Exception: return ''

def windows():
    out = xp(['-root', '_NET_CLIENT_LIST_STACKING']); ids = re.findall(r'0x[0-9a-fA-F]+', out); res = []
    for wid in reversed(ids):
        o = xp(['-id', wid, '_NET_WM_WINDOW_TYPE', 'WM_CLASS', '_NET_WM_NAME', 'WM_NAME'])
        t = re.search(r'_NET_WM_WINDOW_TYPE.*= (.*)', o); t = t.group(1) if t else ''
        if t and 'NORMAL' not in t: continue
        c = re.search(r'WM_CLASS.*= "([^"]*)", "([^"]*)"', o); cls = (c.group(2) if c else '').lower(); inst = (c.group(1) if c else '').lower()
        if cls.startswith('osb-') and inst in ('osb-topbar', 'osb-dock', 'osb-wallpaper', 'osb-apps', 'osb-power', 'osb-notifs', 'osb-lock', 'osb-switcher'): continue
        n = re.search(r'_NET_WM_NAME.*= "(.*)"', o) or re.search(r'WM_NAME.*= "(.*)"', o); title = n.group(1) if n else ''
        res.append(dict(id=wid, cls=cls or inst, title=title, name=NAMES.get(cls) or NAMES.get(inst) or (cls or inst).replace('-', ' ').title()))
    return res

def icon_for(cls, size):
    it = Gtk.IconTheme.get_default()
    for n in (cls, cls.replace('osb-files', 'system-file-manager').replace('osb-settings', 'preferences-system').replace('osb-calc', 'accessories-calculator').replace('osb-monitor', 'utilities-system-monitor'), 'application-x-executable'):
        try:
            pb = it.load_icon(n, size, 0)
            if pb: return Gtk.Image.new_from_pixbuf(pb)
        except Exception: continue
    return Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)

class Switcher(OsbWindow):
    def __init__(self, mode, wins, direction):
        self.mode = mode; self.wins = wins; n = len(wins)
        if mode == 'alttab':
            cw = px(max(1, min(n, 6)) * 150 + 30); ch = px(150 + 40 * ((n - 1) // 6)); per = 6
        else:
            per = 4; rows = max(1, (n + per - 1) // per); cw = px(per * 170 + 40); ch = px(80 + rows * 150 + 20)
        super().__init__(cw, ch, px(40), Gdk.WindowTypeHint.DIALOG, 'osb-switcher'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-switcher', 'Osb-switcher'); self.set_position(Gtk.WindowPosition.CENTER); self.set_keep_above(True)
        self.put(Box('panel', cw, ch), 0, 0); self.sel = 0; self.cards = []
        top = 20
        if mode == 'overview':
            self.put(make_label('Open windows' if n else 'No windows open', 14, 'bold', 'text', w=px(300), h=px(22)), px(24), px(20))
            b = Gtk.Button(label='Apps'); b.set_size_request(px(90), px(32)); b.connect('clicked', lambda *a: (subprocess.Popen(['osb-apps'], start_new_session=True), self.close())); self.put(b, cw - px(114), px(16)); top = 62
        if mode == 'alttab' or n:
            self.hl = Box('pill', px(138), px(130)); self.put(self.hl, 0, 0)
        for i, w in enumerate(wins):
            cwid = 150 if mode == 'alttab' else 170; x = 15 + (i % per) * cwid if mode == 'alttab' else 20 + (i % per) * cwid; y = (top - 0 if mode == 'alttab' else top + 18) + (i // per) * 160
            if mode == 'alttab': y = 15 + (i // per) * 160
            img = icon_for(w['cls'], px(56)); self.put(img, px(x + 36), px(y + 14))
            self.put(make_label(w['name'], 10.5, 'semibold', 'text', xalign=0.5, w=px(130), h=px(16)), px(x + 4), px(y + 84))
            self.put(make_label(w['title'][:24], 8.5, 'normal', 'muted', xalign=0.5, w=px(130), h=px(14)), px(x + 4), px(y + 102))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(138), px(130)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda wd, e, i=i: (self.choose(i), True)[-1]); self.put(ev, px(x), px(y)); self.cards.append((x, y))
        if n: self.start = (1 if n > 1 else 0) if direction != 'prev' else n - 1
        else: self.start = 0
        self.sel = self.start; self.move_hl()
        self.connect('key-press-event', self.on_key); self.connect('key-release-event', self.on_release)
        self.connect('map-event', lambda *a: GLib.idle_add(self.grab)); self.alt_held = True
        if mode == 'overview': self.dismiss_on_outside()
    def move_hl(self):
        if self.wins and hasattr(self, 'hl'):
            x, y = self.cards[self.sel]; self.content.move(self.hl, px(x), px(y))
    def grab(self):
        try:
            gw = self.get_window(); seat = Gdk.Display.get_default().get_default_seat()
            seat.grab(gw, Gdk.SeatCapabilities.KEYBOARD, True, None, None, None)
            if self.mode == 'alttab':
                st = Gdk.Keymap.get_default().get_modifier_state()
                if not (st & Gdk.ModifierType.MOD1_MASK): GLib.timeout_add(80, lambda: (self.choose(self.sel), False)[-1])
        except Exception as e: print('grab', e, file=sys.stderr)
        return False
    def step(self, d):
        if self.wins: self.sel = (self.sel + d) % len(self.wins); self.move_hl()
    def on_key(self, w, e):
        k = e.keyval
        if k == Gdk.KEY_Escape: self.close(); return True
        if k == Gdk.KEY_ISO_Left_Tab: self.step(-1); return True
        if k == Gdk.KEY_Tab: self.step(-1 if e.state & Gdk.ModifierType.SHIFT_MASK else 1); return True
        if k in (Gdk.KEY_Right, Gdk.KEY_Down): self.step(1); return True
        if k in (Gdk.KEY_Left, Gdk.KEY_Up): self.step(-1); return True
        if k in (Gdk.KEY_Return, Gdk.KEY_KP_Enter): self.choose(self.sel); return True
        return False
    def on_release(self, w, e):
        if self.mode == 'alttab' and e.keyval in (Gdk.KEY_Alt_L, Gdk.KEY_Alt_R, Gdk.KEY_Meta_L, Gdk.KEY_Meta_R): self.choose(self.sel); return True
        return False
    def choose(self, i):
        if 0 <= i < len(self.wins): subprocess.Popen(['xdotool', 'windowactivate', self.wins[i]['id']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.close()

def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'alttab'; direction = sys.argv[2] if len(sys.argv) > 2 else 'next'
    me = os.getpid(); r = subprocess.run(['pgrep', '-f', 'python.*osb-switcher'], capture_output=True, text=True).stdout.split()
    others = [p for p in r if p.isdigit() and int(p) != me]
    if others:
        if mode == 'overview':
            for p in others: subprocess.run(['kill', p])
        return
    wins = windows()
    if mode == 'alttab' and not wins: return
    init_mode(); w = Switcher(mode, wins, direction)
    if mode == 'overview': w.connect('focus-out-event', lambda *a: (GLib.timeout_add(250, lambda: (w.close() if w.was_active and not w.is_active() else None, False)[-1]), False)[-1])
    w.was_active = False; w.connect('notify::is-active', lambda *a: setattr(w, 'was_active', w.was_active or w.is_active()))
    w.connect('destroy', Gtk.main_quit); w.show_all(); Gtk.main()
