"""osb-lock: lock screen (wallpaper, clock, password; PAM)."""
import os, sys, time, getpass, pwd, subprocess
from .common import *

def check(user, pw):
    try:
        import pam
        p = pam.pam()
        return p.authenticate(user, pw, service='common-auth') or p.authenticate(user, pw, service='login')
    except ImportError:
        r = subprocess.run(['su', '-c', 'true', user], input=pw + '\n', capture_output=True, text=True); return r.returncode == 0

class Lock(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL); scr = Gdk.Screen.get_default(); self.w, self.h = scr.get_width(), scr.get_height()
        self.set_decorated(False); self.set_title('osb-lock'); self.fullscreen(); self.set_keep_above(True); set_rgba_visual(self); self.get_style_context().add_class('osb')
        self.user = getpass.getuser()
        self.name = display_name(); self.surf = None; self.msg = ''
        fx = Gtk.Fixed(); self.add(fx); self.fx = fx
        da = Gtk.DrawingArea(); da.set_size_request(self.w, self.h); da.connect('draw', self.draw); fx.put(da, 0, 0); self.da = da
        cx = self.w // 2
        self.clock = make_label('', 72, 'bold', 'text', xalign=0.5, spacing=-2, w=px(600), h=px(96)); fx.put(self.clock, cx - px(300), int(self.h * 0.2))
        self.date = make_label('', 16, 'normal', 'muted', xalign=0.5, w=px(600), h=px(24)); fx.put(self.date, cx - px(300), int(self.h * 0.2) + px(98))
        y = int(self.h * 0.5)
        fx.put(Box('avatar', px(64), px(64)), cx - px(32), y)
        ini = ''.join(p[0] for p in self.name.split()[:2]).upper() or self.name[:1].upper()
        fx.put(make_label(ini, 22, 'bold', '#ffffff', xalign=0.5, w=px(64), h=px(64)), cx - px(32), y)
        fx.put(make_label(self.name, 14, 'semibold', 'text', xalign=0.5, w=px(300), h=px(22)), cx - px(150), y + px(74))
        fx.put(Box('qsrow', px(280), px(46)), cx - px(140), y + px(108))
        self.ent = Gtk.Entry(); self.ent.set_visibility(False); self.ent.set_placeholder_text('Password'); self.ent.set_has_frame(False); self.ent.set_size_request(px(250), px(34))
        self.ent.get_style_context().add_class('lockentry'); self.ent.connect('activate', self.go); fx.put(self.ent, cx - px(125), y + px(114))
        self.err = make_label('', 10.5, 'normal', '#ef4444', xalign=0.5, w=px(300), h=px(16)); fx.put(self.err, cx - px(150), y + px(162))
        self.tick(); GLib.timeout_add_seconds(1, self.tick); self.connect('map-event', self.grab); self.connect('key-press-event', self.on_key)
    def on_key(self, w, e):
        # keep typing in the entry; grab_focus() would select all text, so the next key replaces it
        if not self.ent.has_focus():
            self.ent.grab_focus(); self.ent.set_position(-1)
        return False
    def draw(self, w, cr):
        if self.surf is None or self.sm != State.mode: self.surf = render_wall(self.w, self.h, State.mode); self.sm = State.mode
        cr.set_source_surface(self.surf, 0, 0); cr.paint(); cr.set_source_rgba(*hex2rgb(pal('win'))[:3], 0.35); cr.paint(); return False
    def tick(self):
        self.clock.set_text(time.strftime('%H:%M')); self.date.set_text(time.strftime('%A, %d %B')); return True
    def grab(self, *a):
        def g():
            try:
                seat = Gdk.Display.get_default().get_default_seat(); seat.grab(self.get_window(), Gdk.SeatCapabilities.ALL, True, None, None, None)
            except Exception: pass
            self.ent.grab_focus(); self.ent.set_position(-1); return False
        GLib.timeout_add(300, g)
    def go(self, *a):
        pw = self.ent.get_text(); self.ent.set_sensitive(False); self.err.set_text('Checking…')
        import threading
        def w():
            ok = check(self.user, pw); GLib.idle_add(self.done, ok)
        threading.Thread(target=w, daemon=True).start()
    def done(self, ok):
        if ok:
            try: Gdk.Display.get_default().get_default_seat().ungrab()
            except Exception: pass
            Gtk.main_quit(); return
        self.ent.set_sensitive(True); self.ent.set_text(''); self.ent.grab_focus(); self.ent.set_position(-1); self.err.set_text('Wrong password, try again')

def main():
    if subprocess.run(['pgrep', '-fc', 'python.*osb-lock'], capture_output=True, text=True).stdout.strip() not in ('0', '1'): return
    init_mode(); c = Gtk.CssProvider(); c.load_from_data(b'.lockentry{background:transparent;border:none;box-shadow:none;font-size:14px;} window.osb{background-color:#000;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = Lock(); w.show_all(); Gtk.main()
