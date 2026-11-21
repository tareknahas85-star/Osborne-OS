"""osb-power: shut down / restart / log out / sleep / lock."""
import sys, subprocess
from .common import *

ACTS = [('Lock', 'lock', 'osb-lock', False), ('Sleep', 'moon', 'systemctl suspend', False),
        ('Log out', 'logout', 'openbox --exit', True), ('Restart', 'restart', 'systemctl reboot', True), ('Shut down', 'power', 'systemctl poweroff', True)]

class PowerWin(OsbWindow):
    def __init__(self):
        cw, ch, m = px(300), px(60 + 52 * len(ACTS) + 18), px(40)
        super().__init__(cw, ch, m, None, 'Power'); self.shadow = (26, 14, 30); self.set_wmclass('osb-power', 'Osb-power')
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG); self.set_position(Gtk.WindowPosition.CENTER); self.set_keep_above(True); self.enable_escape()
        self.put(Box('panel', cw, ch), 0, 0); traffic_lights(self, 16, 14)
        self.put(make_label('Power', 13, 'semibold', 'text', w=px(200), h=px(20)), px(20), px(36))
        self.armed = None; self.labs = {}
        for i, (name, ic, cmd, confirm) in enumerate(ACTS):
            y = 66 + i * 52; self.put(Box('qsrow', px(268), px(44)), px(16), px(y))
            danger = name == 'Shut down'
            self.put(Icon(ic, px(18), '#ef4444' if danger else 'text', 1.6), px(30), px(y + 13))
            lab = make_label(name, 11, 'semibold', 'text', w=px(190), h=px(18)); self.put(lab, px(60), px(y + 13)); self.labs[name] = lab
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(268), px(44)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, n=name, c=cmd, cf=confirm: (self.go(n, c, cf), True)[-1]); self.put(ev, px(16), px(y))
        self.was_active = False; self.connect('notify::is-active', lambda *a: setattr(self, 'was_active', self.was_active or self.is_active()))
        self.connect('focus-out-event', lambda *a: (GLib.timeout_add(250, lambda: (self.close() if self.was_active and not self.is_active() else None, False)[-1]), False)[-1])
    def go(self, name, cmd, confirm):
        if confirm and self.armed != name:
            if self.armed: self.labs[self.armed].set_text(self.armed)
            self.armed = name; self.labs[name].set_text(name + ' — click again to confirm'); return
        subprocess.Popen(cmd, shell=True, start_new_session=True); self.close()

def main():
    init_mode(); w = PowerWin(); w.connect('destroy', Gtk.main_quit); w.show_all(); Gtk.main()
