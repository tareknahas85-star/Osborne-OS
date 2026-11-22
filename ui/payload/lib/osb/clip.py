"""osb-clip: clipboard history. 'osb-clip' runs the background watcher, 'osb-clip show' (Super+V) opens the list."""
import os, sys, signal, subprocess
from .common import *
from .i18n import tr

RT = os.environ.get('XDG_RUNTIME_DIR') or '/tmp'
PIDF = os.path.join(RT, 'osb-clip.pid')

class Popup(OsbWindow):
    def __init__(self, daemon):
        self.d = daemon; cw, ch, m = px(420), px(460), px(40)
        super().__init__(cw, ch, m, Gdk.WindowTypeHint.DIALOG, 'osb-clip'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-clip', 'Osb-clip'); self.set_position(Gtk.WindowPosition.CENTER); self.set_keep_above(True); self.dismiss_on_outside()
        self.put(Box('panel', cw, ch), 0, 0)
        self.put(make_label('Clipboard history', 14, 'bold', 'text', w=px(250), h=px(22)), px(22), px(18))
        clr = Gtk.Button(label=tr('Clear')); clr.connect('clicked', lambda *a: (self.d.items.clear(), self.fill())); clr.set_size_request(px(70), px(28)); self.put(clr, cw - px(92), px(16))
        self.sc = Gtk.ScrolledWindow(); self.sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); self.sc.set_size_request(px(386), px(380)); self.sc.get_style_context().add_class('osbscroll')
        self.put(self.sc, px(16), px(60)); self.hint = make_label('Click an item to copy it, then paste with Ctrl+V', 9.5, 'normal', 'muted', w=px(380), h=px(16)); self.put(self.hint, px(22), px(436))
        self.fill()
    def fill(self):
        old = self.sc.get_child()
        if old: self.sc.remove(old)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        if not self.d.items:
            l = Gtk.Label(label=tr('Nothing copied yet')); l.set_margin_top(30); box.pack_start(l, False, False, 0)
        for t in self.d.items:
            one = ' '.join(t.split())[:90] or '…'
            b = Gtk.Button(label=one); b.set_relief(Gtk.ReliefStyle.NONE); b.get_child().set_xalign(0); b.get_child().set_ellipsize(Pango.EllipsizeMode.END)
            b.connect('clicked', lambda w, t=t: self.pick(t)); box.pack_start(b, False, False, 0)
        self.sc.add(box); self.sc.show_all()
    def pick(self, t):
        self.d.skip = 1; self.d.cb.set_text(t, -1); self.d.cb.store()
        if t in self.d.items: self.d.items.remove(t)
        self.d.items.insert(0, t); self.close()

class Daemon:
    def __init__(self):
        self.items = []; self.skip = 0; self.pop = None
        self.cb = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD); self.cb.connect('owner-change', self.changed)
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGUSR1, self.show)
    def changed(self, cb, ev):
        if self.skip: self.skip = 0; return
        t = cb.wait_for_text()
        if not t or not t.strip() or len(t) > 20000: return
        if t in self.items: self.items.remove(t)
        self.items.insert(0, t); del self.items[30:]
    def show(self):
        if self.pop is not None:
            try: self.pop.close()
            except Exception: pass
        self.pop = Popup(self); self.pop.connect('destroy', lambda *a: setattr(self, 'pop', None)); self.pop.show_all(); return True

def main():
    if len(sys.argv) > 1 and sys.argv[1] == 'show':
        try:
            pid = int(open(PIDF).read()); os.kill(pid, signal.SIGUSR1); return
        except Exception: pass
    else:
        try:
            os.kill(int(open(PIDF).read()), 0); return          # already running
        except Exception: pass
    open(PIDF, 'w').write(str(os.getpid())); init_mode(); d = Daemon()
    c = Gtk.CssProvider(); c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;}'); Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    if len(sys.argv) > 1 and sys.argv[1] == 'show': GLib.idle_add(d.show)
    Gtk.main()
