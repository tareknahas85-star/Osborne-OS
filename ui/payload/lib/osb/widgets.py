"""osb-widgets: small desktop widgets (clock, system, notes, weather). Turn them on in Settings > Customize."""
import os, sys, time, json, subprocess, threading
from .common import *
from .i18n import tr

WFILE = os.path.join(CONF, 'widgets.json')
DEFAULT = dict(clock=dict(on=False, x=60, y=90), system=dict(on=False, x=60, y=260), notes=dict(on=False, x=60, y=450), weather=dict(on=False, x=330, y=90))
SIZES = dict(clock=(250, 120), system=(250, 150), notes=(250, 170), weather=(250, 110))

def load():
    d = json.loads(json.dumps(DEFAULT))
    try:
        x = json.load(open(WFILE))
        for k in d:
            if isinstance(x.get(k), dict): d[k].update({a: x[k][a] for a in ('on', 'x', 'y') if a in x[k]})
    except Exception: pass
    return d
def save(d):
    os.makedirs(CONF, exist_ok=True); json.dump(d, open(WFILE, 'w'))

class Widget(OsbWindow):
    draggable = True
    def __init__(self, kind, pos, on_move):
        cw, ch = px(SIZES[kind][0]), px(SIZES[kind][1]); m = px(24); self.kind = kind; self.on_move = on_move
        super().__init__(cw, ch, m, None, 'osb-widget-' + kind); self.shadow = (18, 8, 20)
        self.set_wmclass('osb-widget', 'Osb-widget'); self.set_keep_below(True); self.stick()
        self.put(Box('panel', cw, ch), 0, 0); self.move(int(pos[0]) - m, int(pos[1]) - m)
        self.build(cw, ch); self._mv = 0
        self.connect('configure-event', self._conf)
    def _conf(self, w, e):
        if self._mv: GLib.source_remove(self._mv)
        self._mv = GLib.timeout_add(700, self._moved); return False
    def _moved(self):
        self._mv = 0; x, y = self.get_position(); self.on_move(self.kind, x + self.M, y + self.M); return False
    def build(self, cw, ch):
        k = self.kind
        if k == 'clock':
            self.t = make_label('', 34, 'bold', 'text', w=px(220), h=px(46)); self.put(self.t, px(20), px(18)); self.dt = make_label('', 12, 'normal', 'muted', w=px(220), h=px(20)); self.put(self.dt, px(22), px(72))
            self.every(1, self.tick_clock); self.tick_clock()
        elif k == 'system':
            self.bars = {}
            for i, n in enumerate(('CPU', 'Memory', 'Disk')):
                y = 16 + i * 44; self.put(make_label(n, 11, 'semibold', 'text', w=px(120), h=px(18)), px(20), px(y))
                v = make_label('', 11, 'normal', 'muted', xalign=1.0, w=px(80), h=px(18)); self.put(v, px(150), px(y))
                bar = Gtk.DrawingArea(); bar.set_size_request(px(210), px(6)); bar.f = 0.0
                bar.connect('draw', lambda w, cr: (rounded_rect(cr, 0, 0, px(210), px(5), px(2.5)), cr.set_source_rgba(*hex2rgb(pal('track'))), cr.fill(), rounded_rect(cr, 0, 0, px(210) * w.f, px(5), px(2.5)), cr.set_source_rgba(*hex2rgb(pal('primary'))), cr.fill(), False)[-1])
                self.put(bar, px(20), px(y + 22)); self.bars[n] = (bar, v)
            self._cpu = None; self.every(2, self.tick_sys); self.tick_sys()
        elif k == 'notes':
            self.put(make_label('Notes', 12, 'bold', 'text', w=px(200), h=px(18)), px(20), px(12))
            sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); sc.set_size_request(px(206), px(112)); sc.get_style_context().add_class('osbscroll')
            tv = Gtk.TextView(); tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR); tv.get_style_context().add_class('osblog'); self.tv = tv; sc.add(tv); self.put(sc, px(18), px(40))
            nf = os.path.join(CONF, 'notes.txt')
            try: tv.get_buffer().set_text(open(nf).read())
            except Exception: pass
            self._ns = 0
            def ch(b):
                if self._ns: GLib.source_remove(self._ns)
                self._ns = GLib.timeout_add(800, lambda: (open(nf, 'w').write(b.get_text(b.get_start_iter(), b.get_end_iter(), False)), setattr(self, '_ns', 0), False)[-1])
            tv.get_buffer().connect('changed', ch)
            tv.connect('button-press-event', lambda *a: False)
            self.set_accept_focus(True)
        elif k == 'weather':
            self.w1 = make_label('…', 26, 'bold', 'text', w=px(210), h=px(36)); self.put(self.w1, px(20), px(14)); self.w2 = make_label('Looking up the weather…', 11, 'normal', 'muted', w=px(214), h=px(18)); self.put(self.w2, px(22), px(56))
            self.w3 = make_label('', 10, 'normal', 'muted', w=px(214), h=px(16)); self.put(self.w3, px(22), px(78)); self.every(1800, self.fetch_weather); self.fetch_weather()
    def every(self, s, fn): GLib.timeout_add_seconds(s, lambda: (fn(), True)[-1])
    def tick_clock(self):
        self.t.set_text(time.strftime('%I:%M').lstrip('0') if os.path.exists(os.path.join(CONF, '12h')) else time.strftime('%H:%M')); self.dt.set_text(time.strftime('%A, %d %B'))
    def tick_sys(self):
        try:
            a = [int(x) for x in open('/proc/stat').readline().split()[1:]]; idle = a[3] + a[4]; tot = sum(a)
            if self._cpu: dt = tot - self._cpu[0]; cpu = 1 - (idle - self._cpu[1]) / float(dt) if dt else 0
            else: cpu = 0
            self._cpu = (tot, idle)
            mi = dict((l.split(':')[0], int(l.split()[1])) for l in open('/proc/meminfo') if ':' in l); mem = 1 - mi['MemAvailable'] / float(mi['MemTotal'])
            st = os.statvfs('/'); dsk = 1 - st.f_bavail / float(st.f_blocks)
            for n, f in (('CPU', cpu), ('Memory', mem), ('Disk', dsk)):
                bar, v = self.bars[n]; bar.f = max(0, min(1, f)); v.set_text('%d%%' % round(f * 100)); bar.queue_draw()
        except Exception: pass
    def fetch_weather(self):
        def work():
            try:
                from . import weather as W
                lat, lon, name = W.place(); d = W.forecast(lat, lon)
                GLib.idle_add(self.show_weather, (d, name))
            except Exception: GLib.idle_add(self.show_weather, None)
        threading.Thread(target=work, daemon=True).start()
    def show_weather(self, o):
        if not o: self.w1.set_text('—'); self.w2.set_text(tr('No internet connection')); self.w3.set_text(''); return
        d, name = o
        self.w1.set_text('%d°C' % d['temp']); self.w2.set_text('%s  ·  %s' % (name or '', d['text'])); self.w3.set_text('Humidity %s%%  ·  Wind %d km/h' % (d['humidity'], d['wind']))

class App:
    def __init__(self):
        self.cfg = load(); self.win = {}; self.sync(); watch_conf('widgets.json', self.reload)
    def moved(self, k, x, y):
        self.cfg[k]['x'], self.cfg[k]['y'] = x, y; self.self_write = time.time(); save(self.cfg)
    def reload(self):
        if time.time() - getattr(self, 'self_write', 0) < 2: return
        self.cfg = load(); self.sync()
    def sync(self):
        for k, c in self.cfg.items():
            if c['on'] and k not in self.win:
                w = Widget(k, (c['x'], c['y']), self.moved); w.show_all(); self.win[k] = w
            elif not c['on'] and k in self.win: self.win.pop(k).destroy()

def main():
    import signal
    pidf = os.path.join(os.environ.get('XDG_RUNTIME_DIR') or '/tmp', 'osb-widgets.pid')
    try:
        os.kill(int(open(pidf).read()), 0); return      # already running, it follows widgets.json by itself
    except Exception: pass
    open(pidf, 'w').write(str(os.getpid()))
    init_mode(); c = Gtk.CssProvider(); c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;} textview.osblog, textview.osblog text{background:transparent;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    App(); Gtk.main()
