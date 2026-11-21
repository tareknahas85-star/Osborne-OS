"""osb-notifs: notification centre (dunst history) + Do not disturb."""
import os, sys, json, subprocess, time
from .common import *
from .common import _texts

def dunst(args, timeout=3):
    try: return subprocess.run(['dunstctl'] + args, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception: return ''

def history():
    try: data = json.loads(dunst(['history']))['data'][0]
    except Exception: return []
    out = []
    for n in data:
        g = lambda k: (n.get(k) or {}).get('data', '') if isinstance(n.get(k), dict) else ''
        out.append(dict(id=(n.get('id') or {}).get('data'), app=g('appname'), title=g('summary'), body=g('body') or g('message')))
    return out

class Notifs(OsbWindow):
    def __init__(self):
        cw, ch, m = px(340), px(470), px(50); sw = Gdk.Screen.get_default().get_width()
        super().__init__(cw, ch, m, None, 'osb-notifs'); self.shadow = (26, 14, 34); self.set_wmclass('osb-notifs', 'Osb-notifs')
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY); self.set_keep_above(True); self.enable_escape()
        self.put(Box('panel', cw, ch), 0, 0)
        self.put(make_label('Notifications', 14, 'bold', 'text', w=px(200), h=px(22)), px(22), px(20))
        self.clear_l = make_label('Clear all', 9.5, 'semibold', 'primary', xalign=1.0, w=px(70), h=px(16)); self.put(self.clear_l, px(250), px(24))
        ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(70), px(24)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        ev.connect('button-press-event', lambda *a: (dunst(['history-clear']), self.fill(), True)[-1]); self.put(ev, px(250), px(20))
        self.put(Box('qsrow', px(300), px(46)), px(20), px(56)); self.put(Icon('moon', px(18), 'text', 1.5), px(32), px(70))
        self.put(make_label('Do not disturb', 10.5, 'semibold', 'text', w=px(180), h=px(16)), px(60), px(71))
        self.put(Switch(dunst(['is-paused']) == 'true', lambda on: dunst(['set-paused', 'true' if on else 'false'])), px(266), px(66))
        self.sc = Gtk.ScrolledWindow(); self.sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); self.sc.set_size_request(px(304), px(340)); self.sc.get_style_context().add_class('osbscroll')
        self.put(self.sc, px(18), px(116)); self.inner = None; self.fill()
        self.was_active = False; self.connect('notify::is-active', lambda *a: setattr(self, 'was_active', self.was_active or self.is_active()))
        self.connect('focus-out-event', lambda *a: (GLib.timeout_add(250, lambda: (self.close() if self.was_active and not self.is_active() else None, False)[-1]), False)[-1])
        self.connect('map', lambda *a: [GLib.timeout_add(d, self.place) for d in (30, 160)])
    def place(self):
        sw = Gdk.Screen.get_default().get_width(); self.move(sw - px(20) - self.cw - self.M, px(48) - self.M); return False
    def fill(self):
        if self.inner: self.inner.destroy()
        self.inner = Gtk.Fixed(); self.sc.add(self.inner); items = history(); y = 0
        if not items:
            self.inner.put(make_label('No notifications', 11, 'normal', 'muted', xalign=0.5, w=px(300), h=px(20)), 0, px(120))
        for it in items[:40]:
            self.inner.put(Box('qsrow', px(296), px(66)), px(2), px(y))
            self.inner.put(make_label(it['title'] or it['app'], 10.5, 'semibold', 'text', w=px(270), h=px(16)), px(16), px(y + 10))
            self.inner.put(make_label((it['body'] or '').replace('\n', ' '), 9, 'normal', 'muted', w=px(270), h=px(14)), px(16), px(y + 29))
            self.inner.put(make_label(it['app'], 8, 'normal', 'muted', w=px(200), h=px(12)), px(16), px(y + 46)); y += 74
        self.inner.set_size_request(px(300), px(max(y, 10))); self.inner.show_all()

def main():
    me = os.getpid(); r = subprocess.run(['pgrep', '-f', 'python.*osb-notifs'], capture_output=True, text=True).stdout.split()
    others = [p for p in r if p.isdigit() and int(p) != me]
    if others:
        for p in others: subprocess.run(['kill', p])
        return
    init_mode(); c = Gtk.CssProvider(); c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = Notifs(); w.connect('destroy', Gtk.main_quit); w.show_all(); Gtk.main()
