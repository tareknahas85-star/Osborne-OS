"""osb-apps: icon-grid app drawer."""
import os, sys, subprocess
from .common import *

HIDE = {'tint2', 'tint2 settings', 'advanced network configuration', 'customize look and feel', 'desktop preferences', 'file roller', 'mousepad', 'text editor settings', 'text editor', 'file manager pcmanfm', 'file manager', 'pulseaudio volume control', 'bluetooth manager', 'bluetooth adapters', 'wi-fi', 'firefox web browser', 'firefox', 'avahi ssh server browser', 'avahi vnc server browser', 'picom', 'openbox configuration manager', 'vim', 'rofi', 'rofi theme selector', 'avahi zeroconf browser', 'bulk rename', 'lxappearance customize look and feel', 'uxterm', 'xterm'}

class AppDrawer(OsbWindow):
    def __init__(self):
        cw, ch, m = px(760), px(540), px(40)
        super().__init__(cw, ch, m, None, 'Apps'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-apps', 'Osb-apps'); self.set_type_hint(Gdk.WindowTypeHint.DIALOG); self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True); self.enable_escape()
        self.put(Box('panel', cw, ch), 0, 0)
        self.put(Box('qsrow', px(716), px(46)), px(22), px(22)); self.put(Icon('search', px(18), 'muted', 1.6), px(36), px(36))
        self.entry = Gtk.Entry(); self.entry.set_has_frame(False); self.entry.set_placeholder_text('Search apps'); self.entry.set_size_request(px(640), px(34))
        self.entry.get_style_context().add_class('osbentry'); self.put(self.entry, px(64), px(28))
        self.fb = Gtk.FlowBox(); self.fb.set_max_children_per_line(6); self.fb.set_min_children_per_line(6); self.fb.set_homogeneous(True)
        self.fb.set_selection_mode(Gtk.SelectionMode.NONE); self.fb.set_activate_on_single_click(True); self.fb.set_valign(Gtk.Align.START)
        self.fb.set_filter_func(self.flt); self.fb.set_sort_func(lambda a, b: (a.name.lower() > b.name.lower()) - (a.name.lower() < b.name.lower()))
        self.fb.connect('child-activated', lambda fb, ch: self.run(ch.info))
        sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); sc.set_size_request(px(720), px(430)); sc.add(self.fb)
        sc.get_style_context().add_class('osbscroll'); self.put(sc, px(20), px(86))
        it = Gtk.IconTheme.get_default(); seen = set()
        for ai in sorted(Gio.AppInfo.get_all(), key=lambda a: a.get_name().lower()):
            if not ai.should_show() or ai.get_name() in seen or ai.get_name().lower() in HIDE: continue
            seen.add(ai.get_name()); box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=px(6)); box.set_size_request(px(112), px(104))
            ic = ai.get_icon(); img = Gtk.Image.new_from_gicon(ic, Gtk.IconSize.DIALOG) if ic else Gtk.Image.new_from_icon_name('application-x-executable', Gtk.IconSize.DIALOG)
            img.set_pixel_size(px(48)); box.pack_start(img, False, False, px(6))
            lb = Gtk.Label(label=ai.get_name()); lb.set_line_wrap(True); lb.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR); lb.set_lines(2); lb.set_ellipsize(Pango.EllipsizeMode.END); lb.set_max_width_chars(12); lb.set_width_chars(12); lb.set_justify(Gtk.Justification.CENTER)
            box.pack_start(lb, False, False, 0); ch = Gtk.FlowBoxChild(); ch.add(box); ch.info = ai; ch.name = ai.get_name(); ch.get_style_context().add_class('appitem')
            self.fb.add(ch)
        self.entry.connect('changed', lambda e: self.fb.invalidate_filter())
        self.entry.connect('activate', lambda e: self.first())
        self.was_active = False; self.connect('notify::is-active', lambda *a: setattr(self, 'was_active', self.was_active or self.is_active()))
        self.connect('focus-out-event', lambda *a: (GLib.timeout_add(250, self.maybe_close), False)[-1])
    def flt(self, ch):
        q = self.entry.get_text().strip().lower(); return not q or q in ch.name.lower()
    def first(self):
        for ch in sorted(self.fb.get_children(), key=lambda c: c.name.lower()):
            if self.flt(ch): self.run(ch.info); return
    def run(self, ai):
        try: ai.launch([], None)
        except Exception as e: print('launch', e, file=sys.stderr)
        self.close()
    def maybe_close(self):
        if self.was_active and not self.is_active(): self.close()
        return False

def main():
    me = os.getpid(); r = subprocess.run(['pgrep', '-f', 'python.*osb-apps'], capture_output=True, text=True).stdout.split()
    others = [p for p in r if p.isdigit() and int(p) != me]
    if others:
        for p in others: subprocess.run(['kill', p])
        return
    init_mode(); c = Gtk.CssProvider()
    c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;} .osbentry{background:transparent;border:none;box-shadow:none;font-size:15px;} flowboxchild.appitem{border-radius:16px;padding:6px;} flowboxchild.appitem:hover{background-color:alpha(#0a7cff,0.12);} flowboxchild:focus{outline:none;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = AppDrawer(); w.connect('destroy', Gtk.main_quit); w.show_all(); w.entry.grab_focus(); Gtk.main()
