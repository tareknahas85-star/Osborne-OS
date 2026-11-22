"""osb-capture: screenshot and screen recording."""
import os, sys, time, subprocess, threading
from .common import *
from .i18n import tr

class Capture(OsbWindow):
    draggable = True
    def __init__(self):
        cw, ch, m = px(360), px(250), px(40)
        super().__init__(cw, ch, m, Gdk.WindowTypeHint.DIALOG, 'osb-capture'); self.shadow = (24, 14, 30)
        self.set_wmclass('osb-capture', 'Osb-capture'); self.set_position(Gtk.WindowPosition.CENTER); self.set_keep_above(True); self.enable_escape()
        self.put(Box('panel', cw, ch), 0, 0); self.proc = None; self.t0 = 0
        self.put(make_label('Screenshot and recording', 14, 'bold', 'text', w=px(300), h=px(22)), px(22), px(18))
        def b(txt, y, fn, prim=False, x=px(22), w=px(150)):
            bt = Gtk.Button(label=tr(txt)); bt.set_size_request(w, px(36)); bt.connect('clicked', lambda *a: fn())
            if prim: bt.get_style_context().add_class('suggested-action')
            self.put(bt, x, y); return bt
        b('Full screen', px(62), lambda: self.shot('full')); b('Select area', px(62), lambda: self.shot('area'), x=px(188))
        b('One window', px(106), lambda: self.shot('window'))
        self.rec = b('Start recording', px(150), self.toggle, True, w=px(316))
        self.msg = make_label('Pictures go to Pictures/Screenshots, videos to Videos', 9.5, 'normal', 'muted', w=px(316), h=px(16)); self.put(self.msg, px(22), px(204))
    def say(self, t): self.msg.set_text(tr(t))
    def shot(self, how):
        self.iconify(); GLib.timeout_add(600, lambda: (subprocess.Popen(['osb-shot'] + ([] if how == 'full' else [how])), GLib.timeout_add(2500, lambda: (self.deiconify(), self.say('Saved in Pictures/Screenshots'), False)[-1]), False)[-1])
    def toggle(self):
        if self.proc: return self.stop()
        d = os.path.expanduser('~/Videos'); os.makedirs(d, exist_ok=True); f = os.path.join(d, time.strftime('Recording-%Y%m%d-%H%M%S.mp4'))
        sc = Gdk.Screen.get_default(); w, h = sc.get_width() // 2 * 2, sc.get_height() // 2 * 2
        try:
            self.proc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'x11grab', '-framerate', '25', '-video_size', '%dx%d' % (w, h), '-i', os.environ.get('DISPLAY', ':0') + '.0',
                                          '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p', f], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        except Exception as e: self.say('Recording is not available (ffmpeg is missing)'); self.proc = None; return
        self.file = f; self.t0 = time.time(); self.rec.set_label(tr('Stop recording')); self.tick_id = GLib.timeout_add_seconds(1, self.tick)
    def tick(self):
        if not self.proc: return False
        s = int(time.time() - self.t0); self.say('Recording…  %d:%02d' % (s // 60, s % 60)); return True
    def stop(self):
        p = self.proc; self.proc = None; self.rec.set_label(tr('Start recording'))
        try: p.stdin.write(b'q'); p.stdin.close()
        except Exception: pass
        threading.Thread(target=lambda: (p.wait(), GLib.idle_add(self.say, 'Saved in Videos')), daemon=True).start()
    def do_delete_event(self, *a):
        if self.proc: self.stop()
        return False

def main():
    me = os.getpid(); r = subprocess.run(['pgrep', '-f', 'python.*osb-capture'], capture_output=True, text=True).stdout.split()
    if [p for p in r if p.isdigit() and int(p) != me]: return
    init_mode(); w = Capture(); w.connect('destroy', Gtk.main_quit); w.show_all(); Gtk.main()
