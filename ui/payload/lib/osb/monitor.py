"""osb-monitor: system monitor (CPU / memory / disk / network graphs + process list)."""
import os, sys, time, subprocess, signal
from .common import *
from .common import _texts

W, H = 880, 600

def read_cpu():
    f = open('/proc/stat').readline().split()[1:]; v = list(map(int, f)); idle = v[3] + v[4]; return sum(v), idle
def read_mem():
    d = {}
    for ln in open('/proc/meminfo'):
        k, v = ln.split(':'); d[k] = int(v.split()[0])
    tot = d['MemTotal']; return tot, tot - d.get('MemAvailable', d['MemFree'])
def read_net():
    rx = tx = 0
    for ln in open('/proc/net/dev').readlines()[2:]:
        n, v = ln.split(':'); 
        if n.strip() == 'lo': continue
        p = v.split(); rx += int(p[0]); tx += int(p[8])
    return rx, tx
def fmt(b):
    for u in ('B', 'KB', 'MB', 'GB'):
        if b < 1024 or u == 'GB': return ('%d %s' % (b, u)) if u == 'B' else '%.1f %s' % (b, u)
        b /= 1024.0
def procs(n=14):
    out = subprocess.run(['ps', '-eo', 'pid,pcpu,rss,comm', '--sort=-pcpu'], capture_output=True, text=True).stdout.splitlines()[1:n + 1]
    r = []
    for ln in out:
        p = ln.split(None, 3)
        if len(p) == 4: r.append((int(p[0]), float(p[1]), int(p[2]) * 1024, p[3]))
    return r

class Graph(Gtk.DrawingArea):
    def __init__(self, w, h, title):
        super().__init__(); self.set_size_request(w, h); self.data = [0.0] * 60; self.title = title; self.value = ''; self.w, self.h = w, h; self.maxv = 1.0
        self.connect('draw', self.draw)
    def push(self, v, text, maxv=1.0): self.data = self.data[1:] + [v]; self.value = text; self.maxv = maxv; self.queue_draw()
    def draw(self, wd, cr):
        w, h = self.w, self.h; pr = tuple(hex2rgb(pal('primary')))[:3]; n = len(self.data)
        top = px(70); gh = h - top - px(16); step = (w - px(32)) / float(n - 1); x0 = px(16)
        cr.set_line_width(1); cr.set_source_rgba(*hex2rgb(pal('border')))
        for i in range(4): y = top + gh * i / 3.0; cr.move_to(x0, y); cr.line_to(w - px(16), y); cr.stroke()
        pts = [(x0 + i * step, top + gh * (1 - min(1.0, v / self.maxv))) for i, v in enumerate(self.data)]
        cr.move_to(pts[0][0], top + gh)
        for x, y in pts: cr.line_to(x, y)
        cr.line_to(pts[-1][0], top + gh); cr.close_path(); g = cairo.LinearGradient(0, top, 0, top + gh); g.add_color_stop_rgba(0, *pr, 0.35); g.add_color_stop_rgba(1, *pr, 0.02); cr.set_source(g); cr.fill()
        cr.set_line_width(max(1.5, pxf(2))); cr.set_line_join(cairo.LINE_JOIN_ROUND); cr.set_source_rgba(*pr, 1); cr.move_to(*pts[0])
        for x, y in pts[1:]: cr.line_to(x, y)
        cr.stroke(); return False

class Monitor(OsbWindow):
    draggable = True
    def __init__(self):
        m = px(50); super().__init__(px(W), px(H), m, None, 'System Monitor'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-monitor', 'Osb-monitor'); self.set_type_hint(Gdk.WindowTypeHint.NORMAL); self.set_position(Gtk.WindowPosition.CENTER); self.enable_escape()
        self.put(Box('win', px(W), px(H)), 0, 0); traffic_lights(self, 16, 25)
        self.put(make_label('System Monitor', 20, 'bold', 'text', spacing=-0.3, w=px(400), h=px(30)), px(24), px(54))
        cw = (W - 24 * 2 - 14 * 2) // 3; self.gr = {}; self.vl = {}
        for i, (k, t) in enumerate((('cpu', 'Processor'), ('mem', 'Memory'), ('net', 'Network'))):
            x = px(24 + i * (cw + 14)); self.put(Box('qsrow', px(cw), px(170)), x, px(100))
            self.put(make_label(t, 10.5, 'semibold', 'muted', w=px(cw - 20), h=px(16)), x + px(16), px(112))
            v = make_label('—', 15, 'bold', 'text', w=px(cw - 20), h=px(22)); self.put(v, x + px(16), px(130)); self.vl[k] = v
            g = Graph(px(cw), px(170), t); self.put(g, x, px(100)); self.gr[k] = g
        self.put(make_label('Processes', 11, 'semibold', 'muted', w=px(200), h=px(16)), px(28), px(286))
        self.put(make_label('Click a process, then End task to close it', 9, 'normal', 'muted', xalign=1.0, w=px(300), h=px(14)), px(W - 24 - 300 - 10 - 90), px(288))
        self.store = Gtk.ListStore(int, str, str, str); tv = Gtk.TreeView(model=self.store); tv.set_headers_visible(True); self.tv = tv
        for i, (t, xa) in enumerate((('Name', 0), ('CPU', 1), ('Memory', 1))):
            r = Gtk.CellRendererText(); r.set_property('xalign', xa); col = Gtk.TreeViewColumn(t, r, text=i + 1); col.set_expand(i == 0); tv.append_column(col)
        sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); sc.add(tv); sc.set_size_request(px(W - 48), px(238)); sc.get_style_context().add_class('osbscroll')
        self.put(sc, px(24), px(312))
        b = Gtk.Button(label='End task'); b.connect('clicked', lambda *a: self.kill()); b.set_size_request(px(90), px(30)); self.put(b, px(W - 24 - 90), px(280))
        self.last = (read_cpu(), read_net(), time.time()); self.tick(); GLib.timeout_add(1000, self.tick)
    def kill(self):
        sel = self.tv.get_selection().get_selected()
        if sel[1]:
            try: os.kill(self.store[sel[1]][0], signal.SIGTERM)
            except Exception: pass
    def tick(self):
        (t0, i0), (rx0, tx0), tm = self.last; t1, i1 = read_cpu(); rx1, tx1 = read_net(); now = time.time(); dt = max(0.2, now - tm)
        cpu = 1 - (i1 - i0) / float(max(1, t1 - t0)); self.gr['cpu'].push(cpu, ''); self.restyle(self.vl['cpu'], '%d%%' % round(cpu * 100))
        tot, used = read_mem(); self.gr['mem'].push(used / float(tot), ''); self.restyle(self.vl['mem'], '%s of %s' % (fmt(used * 1024), fmt(tot * 1024)))
        rate = ((rx1 - rx0) + (tx1 - tx0)) / dt; mx = max(self.gr['net'].maxv if self.gr['net'].maxv > 1 else 0, rate, 100 * 1024.0)
        self.gr['net'].push(rate, '', max(max(self.gr['net'].data), 100 * 1024.0)); self.restyle(self.vl['net'], '%s/s' % fmt(rate))
        self.last = ((t1, i1), (rx1, tx1), now)
        sel = self.tv.get_selection().get_selected(); keep = self.store[sel[1]][0] if sel[1] else None
        self.store.clear()
        for pid, c, mem, name in procs():
            it = self.store.append([pid, name, '%.1f%%' % c, fmt(mem)])
            if pid == keep: self.tv.get_selection().select_iter(it)
        return True
    def restyle(self, lab, text): lab.set_text(text)

def main():
    ids = subprocess.run(['xdotool', 'search', '--class', 'osb-monitor'], capture_output=True, text=True).stdout.split()
    if ids and subprocess.run(['pgrep', '-fc', 'osb.monitor|osb-monitor'], capture_output=True, text=True).stdout.strip() not in ('0', '1'):
        subprocess.run(['xdotool', 'windowactivate', ids[-1]]); return
    init_mode(); c = Gtk.CssProvider(); c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = Monitor(); w.connect('destroy', Gtk.main_quit); w.show_all(); watch_mode(lambda m: w.queue_draw()); Gtk.main()
