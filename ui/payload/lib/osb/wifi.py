"""osb-wifi: Wi-Fi picker (design-matched card)."""
import sys, subprocess, threading
from .common import *
from .common import _texts

def nm(args, timeout=25):
    try:
        r = subprocess.run(['nmcli'] + args, capture_output=True, text=True, timeout=timeout); return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e: return 1, str(e)

class WifiWin(OsbWindow):
    draggable = True
    def __init__(self):
        cw, ch, m = px(320), px(420), px(40)
        super().__init__(cw, ch, m, None, 'Wi-Fi'); self.shadow = (26, 14, 30); self.set_wmclass('osb-wifi', 'Osb-wifi')
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG); self.set_position(Gtk.WindowPosition.CENTER)
        self.put(Box('panel', cw, ch), 0, 0)
        traffic_lights(self, 16, 14); self.enable_escape()
        self.put(make_label('Wi-Fi networks', 13, 'semibold', 'text', w=px(200), h=px(20)), px(20), px(38))
        self.status = make_label('Scanning…', 9, 'normal', 'muted', w=px(280), h=px(14)); self.put(self.status, px(20), px(60))
        self.sc = Gtk.ScrolledWindow(); self.sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); self.sc.set_size_request(px(290), px(280))
        self.sc.get_style_context().add_class('osbscroll'); self.lst = Gtk.Fixed(); self.sc.add(self.lst); self.put(self.sc, px(16), px(86))
        self.pw = Gtk.Entry(); self.pw.set_visibility(False); self.pw.set_placeholder_text('Password'); self.pw.set_size_request(px(200), px(34))
        self.btn = Gtk.Button(label='Connect'); self.btn.set_size_request(px(80), px(34)); self.sel = None
        self.btn.connect('clicked', self.connect_sel); self.pw.connect('activate', self.connect_sel)
        self.put(self.pw, px(20), px(374)); self.put(self.btn, px(228), px(374)); self.pw.hide(); self.btn.hide()
        self.connect('destroy', lambda *a: Gtk.main_quit()); self.scan()
    def scan(self):
        def w():
            nm(['dev', 'wifi', 'rescan'], 8)
            rc, out = nm(['-t', '-f', 'IN-USE,SSID,SIGNAL,SECURITY', 'dev', 'wifi', 'list'])
            GLib.idle_add(self.fill, rc, out)
        threading.Thread(target=w, daemon=True).start()
    def fill(self, rc, out):
        for c in self.lst.get_children(): c.destroy()
        nets = {}
        for ln in out.splitlines():
            p = ln.replace('\\:', '\x00').split(':')
            if len(p) < 4 or not p[1]: continue
            ssid = p[1].replace('\x00', ':'); sig = int(p[2] or 0)
            if ssid not in nets or sig > nets[ssid][1]: nets[ssid] = (p[0] == '*', sig, p[3])
        if rc != 0 or not nets:
            self.status.set_text('No networks found' if rc == 0 else 'Wi-Fi unavailable — check that Wi-Fi is on'); return False
        self.status.set_text('%d networks' % len(nets)); y = 0
        for ssid, (act, sig, sec) in sorted(nets.items(), key=lambda kv: (not kv[1][0], -kv[1][1])):
            self.lst.put(Box('qsrow', px(286), px(44)), 0, px(y))
            self.lst.put(Icon('wifi', px(18), 'primary' if act else 'text', 1.6), px(12), px(y + 13))
            self.lst.put(make_label(ssid, 10.5, 'semibold', 'text', w=px(170), h=px(16)), px(42), px(y + 6))
            self.lst.put(make_label('Connected' if act else ('Secured' if sec else 'Open') + ' · %d%%' % sig, 8, 'normal', 'green' if act else 'muted', w=px(170), h=px(12)), px(42), px(y + 24))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(286), px(44)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, s=ssid, se=sec: (self.pick(s, se), True)[-1]); self.lst.put(ev, 0, px(y)); y += 50
        self.lst.set_size_request(px(286), px(y)); self.lst.show_all(); return False
    def pick(self, ssid, sec):
        self.sel = ssid
        if sec: self.pw.show(); self.btn.show(); self.pw.grab_focus(); self.status.set_text('Enter password for ' + ssid)
        else: self.pw.hide(); self.btn.show(); self.status.set_text('Connect to ' + ssid + '?')
    def connect_sel(self, *a):
        if not self.sel: return
        ssid, pw = self.sel, self.pw.get_text(); self.status.set_text('Connecting…')
        def w():
            args = ['dev', 'wifi', 'connect', ssid] + (['password', pw] if pw else [])
            rc, out = nm(args, 45); GLib.idle_add(self.done, rc, out)
        threading.Thread(target=w, daemon=True).start()
    def done(self, rc, out):
        self.status.set_text('Connected' if rc == 0 else 'Failed: ' + out.splitlines()[-1][:60] if out else 'Failed')
        if rc == 0: self.pw.set_text(''); GLib.timeout_add(900, lambda: (self.close(), False)[-1])
        return False

def main():
    init_mode(); c = Gtk.CssProvider(); c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = WifiWin(); w.show_all(); w.pw.hide(); w.btn.hide(); watch_mode(lambda m: w.queue_draw()); Gtk.main()
