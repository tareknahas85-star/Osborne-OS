"""osb-welcome: first-run screen that asks who is using this computer."""
import os, sys, subprocess
from .common import *

class Welcome(OsbWindow):
    def __init__(self):
        cw, ch, m = px(520), px(440), px(40)
        super().__init__(cw, ch, m, None, 'Welcome'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-welcome', 'Osb-welcome'); self.set_type_hint(Gdk.WindowTypeHint.DIALOG); self.set_position(Gtk.WindowPosition.CENTER); self.set_keep_above(True)
        self.put(Box('panel', cw, ch), 0, 0)
        self.put(Emblem(px(44), 'text'), px(238), px(26))
        self.put(make_label('Welcome to Osborne', 22, 'bold', 'text', xalign=0.5, w=px(480), h=px(32)), px(20), px(84))
        self.put(make_label('Tell us who is using this computer.', 11, 'normal', 'muted', xalign=0.5, w=px(480), h=px(18)), px(20), px(120))
        self.put(make_label('Your name', 10, 'semibold', 'muted', w=px(200), h=px(16)), px(60), px(162))
        self.ent = Gtk.Entry(); self.ent.set_max_length(30); self.ent.set_size_request(px(400), px(38)); self.ent.set_placeholder_text('Type your name'); self.ent.connect('activate', lambda e: self.done())
        self.put(self.ent, px(60), px(184))
        self.put(make_label('Pick an avatar (you can change it later)', 10, 'semibold', 'muted', w=px(400), h=px(16)), px(60), px(240))
        self.kind = 'initials'; self.picks = []
        for i, kind in enumerate(['initials'] + ['preset:%d' % i for i in range(5)]):
            da = Gtk.DrawingArea(); da.set_size_request(px(52), px(52)); da.kind = kind; da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            def draw(w, cr):
                n = self.ent.get_text().strip() or 'Osborne'; cr.translate(px(1), px(1)); draw_avatar(cr, px(50), w.kind, name_initials(n))
                if w.kind == self.kind: cr.identity_matrix(); rounded_rect(cr, 1, 1, px(52) - 2, px(52) - 2, px(16)); cr.set_line_width(2.5); cr.set_source_rgba(*hex2rgb(pal('primary'))); cr.stroke()
                return False
            da.connect('draw', draw); da.connect('button-press-event', lambda w, e: (setattr(self, 'kind', w.kind), [x.queue_draw() for x in self.picks], True)[-1])
            self.ent.connect('changed', lambda e, d=da: d.queue_draw()); self.picks.append(da); self.put(da, px(60) + i * px(66), px(264))
        b = Gtk.Button(label='Continue'); b.get_style_context().add_class('suggested-action'); b.set_size_request(px(400), px(42)); b.connect('clicked', lambda *a: self.done()); self.put(b, px(60), px(346))
        self.put(make_label('Your name is only kept on this computer.', 9, 'normal', 'muted', xalign=0.5, w=px(480), h=px(14)), px(20), px(396))
    def done(self):
        n = self.ent.get_text().strip()
        if not n: self.ent.grab_focus(); return
        set_display_name(n); set_avatar(self.kind)
        open(os.path.join(CONF, 'welcomed'), 'w').write('1'); self.destroy(); Gtk.main_quit()

def main():
    os.makedirs(CONF, exist_ok=True)
    if os.path.exists(os.path.join(CONF, 'welcomed')) or os.path.exists(PROFILE): return
    init_mode(); w = Welcome(); w.connect('destroy', Gtk.main_quit); w.show_all(); w.ent.grab_focus(); Gtk.main()
