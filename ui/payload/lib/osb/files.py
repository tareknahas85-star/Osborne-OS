"""osb-files: Files app in the HeroUI 'Linux Desktop' design."""
import os, sys, time, shutil, subprocess, getpass, pwd, json, threading, urllib.parse
from .common import *
from .common import _texts

HOME = os.path.expanduser('~')
KINDS = {'pdf': ('PDF', 'red', 'PDF document'), 'fig': ('FIG', 'purple', 'Figma design')}
IMG = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'}; AUD = {'mp3', 'wav', 'flac', 'ogg', 'm4a'}
CARD_TONES = ['blue', 'purple', 'red', 'green']

def first_name(): return display_name()

def initials(n):
    p = n.split(); return (p[0][0] + (p[1][0] if len(p) > 1 else (p[0][1:2] or ''))).upper()

def ago(t):
    d = time.time() - t
    if d < 90: return 'Just now'
    if d < 3600: return '%d min ago' % (d // 60)
    if d < 86400: return '%d hr ago' % (d // 3600)
    if d < 172800: return 'Yesterday'
    return time.strftime('%b %d', time.localtime(t))

def kind_of(path, isdir):
    if isdir: return ('DIR', 'blue', 'Folder')
    ext = os.path.splitext(path)[1].lstrip('.').lower()
    if ext in KINDS: return KINDS[ext]
    if ext in IMG: return (ext.upper()[:3], 'green', 'Image')
    if ext in AUD: return (ext.upper()[:3], 'purple', 'Audio')
    return ((ext or 'FILE').upper()[:4], 'blue', (ext.upper() + ' file') if ext else 'File')

SHOW_HIDDEN = False
def list_dir(path):
    out = []
    try:
        for e in os.scandir(path):
            if e.name.startswith('.') and not SHOW_HIDDEN: continue
            try: st = e.stat(); out.append((e.name, e.path, e.is_dir(), st.st_mtime, st.st_size))
            except OSError: pass
    except OSError: pass
    return out

def count_items(p):
    try: return len([n for n in os.listdir(p) if not n.startswith('.')])
    except OSError: return 0

def recent_files(n=3):
    items = []
    for root, dirs, files in os.walk(HOME):
        dirs[:] = [d for d in dirs if not d.startswith('.') and root.count(os.sep) - HOME.count(os.sep) < 2]
        for f in files:
            if f.startswith('.'): continue
            p = os.path.join(root, f)
            try: items.append((f, p, False, os.stat(p).st_mtime, 0))
            except OSError: pass
    items.sort(key=lambda x: -x[3]); return items[:n]

TRASH = os.path.expanduser('~/.local/share/Trash')
def notify(t, b): subprocess.Popen(['notify-send', '-a', 'Files', t, b], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
def uniq(dst):
    if not os.path.exists(dst): return dst
    base, ext = os.path.splitext(dst); i = 1
    while os.path.exists('%s (copy %d)%s' % (base, i, ext) if i > 1 else '%s (copy)%s' % (base, ext)): i += 1
    return '%s (copy %d)%s' % (base, i, ext) if i > 1 else '%s (copy)%s' % (base, ext)
def to_trash(p):
    os.makedirs(TRASH + '/files', exist_ok=True); os.makedirs(TRASH + '/info', exist_ok=True)
    n = os.path.basename(p.rstrip('/')); d = n; i = 1
    while os.path.exists(os.path.join(TRASH, 'files', d)): i += 1; d = '%s.%d' % (n, i)
    open(os.path.join(TRASH, 'info', d + '.trashinfo'), 'w').write('[Trash Info]\nPath=%s\nDeletionDate=%s\n' % (urllib.parse.quote(os.path.abspath(p)), time.strftime('%Y-%m-%dT%H:%M:%S')))
    shutil.move(p, os.path.join(TRASH, 'files', d))
def restore(p):
    n = os.path.basename(p); info = os.path.join(TRASH, 'info', n + '.trashinfo'); dest = os.path.join(HOME, n)
    try:
        for ln in open(info):
            if ln.startswith('Path='): dest = urllib.parse.unquote(ln[5:].strip())
    except OSError: pass
    os.makedirs(os.path.dirname(dest), exist_ok=True); shutil.move(p, uniq(dest) if os.path.exists(dest) else dest)
    try: os.remove(info)
    except OSError: pass
def rm_perm(p):
    shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
    try: os.remove(os.path.join(TRASH, 'info', os.path.basename(p) + '.trashinfo'))
    except OSError: pass
def copy_to(src, dstdir, move=False):
    dst = os.path.join(dstdir, os.path.basename(src.rstrip('/')))
    if os.path.abspath(dst) == os.path.abspath(src): dst = uniq(dst)
    elif os.path.exists(dst): dst = uniq(dst)
    if move: shutil.move(src, dst)
    elif os.path.isdir(src): shutil.copytree(src, dst, symlinks=True)
    else: shutil.copy2(src, dst)
def usb_devices():
    try: j = json.loads(subprocess.run(['lsblk', '-J', '-o', 'NAME,PATH,LABEL,MOUNTPOINT,RM,TRAN,TYPE,SIZE,FSTYPE,PKNAME'], capture_output=True, text=True, timeout=4).stdout)
    except Exception: return []
    out = []
    def walk(n, root_disk, parent):
        for c in n.get('children', []) or []:
            walk(c, root_disk, n)
    bad = set()
    def mark(n, top):
        mp = n.get('mountpoint') or ''
        if mp == '/' or mp.startswith('/boot'): bad.add(top)
        for c in n.get('children', []) or []: mark(c, top)
    for d in j.get('blockdevices', []): mark(d, d['name'])
    for d in j.get('blockdevices', []):
        if d['name'] in bad or d.get('type') != 'disk': continue
        if not (d.get('rm') in (True, '1', 1) or d.get('tran') == 'usb'): continue
        parts = [c for c in (d.get('children') or []) if c.get('type') == 'part' and c.get('fstype')] or ([d] if d.get('fstype') else [])
        for p in parts:
            out.append(dict(path=p['path'], name=p.get('label') or ('USB drive ' + (p.get('size') or '')), mp=p.get('mountpoint'), disk='/dev/' + d['name'], size=p.get('size')))
    return out

def human(n):
    for u in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or u == 'GB': return ('%d %s' % (n, u)) if u == 'B' else ('%.1f %s' % (n, u))
        n /= 1024.0

class FilesWindow(OsbWindow):
    W0, H0 = 1050, 627
    def __init__(self):
        m = px(50); self.W, self.H = self.W0, self.H0
        super().__init__(px(self.W), px(self.H), m, None, 'Files'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-files', 'Osb-files'); self.set_role('osb-files')
        self.move(px(95) - m, px(54) - m); self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.cwd = HOME; self.hist = []; self.set_icon_name('system-file-manager'); self.maxed = False; self.bottoms = []
        self.winbox = Box('win', px(self.W), px(self.H)); self.put(self.winbox, 0, 0)
        self.sidebox = Box('sidebar', px(211), px(self.H)); self.put(self.sidebox, 0, 0)
        traffic_lights(self, 16, 25, self.toggle_max)
        self.sidebar_items = {}; self.build_sidebar()
        self.page = Gtk.Fixed(); self.put(self.page, px(211), 0); self.apply_page_size()
        self.show_dir(HOME, push=False); self.connect('map', lambda *a: [GLib.timeout_add(d, self.place) for d in (40, 200)])
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK); self.connect('button-press-event', self._drag)
        watch_mode(lambda m: self.queue_draw_all()); GLib.timeout_add_seconds(30, self.update_storage); self.poll_devices(); GLib.timeout_add_seconds(4, self.poll_devices)
    @property
    def PW(self): return self.W - 211
    @property
    def CW(self): return self.PW - 56
    def apply_page_size(self): self.page.set_size_request(px(self.PW), px(self.H))
    def place(self):
        if not self.maxed: self.move(px(95) - self.M, px(54) - self.M)
        return False
    def toggle_max(self):
        scr = Gdk.Screen.get_default(); sw, sh = scr.get_width(), scr.get_height()
        if not self.maxed:
            self.saved = (self.W, self.H); self.W = int((sw - px(24)) / S); self.H = int((sh - px(40) - px(12) - px(86)) / S); self.maxed = True
            self.M = 0; nx, ny = px(12), px(48); self.shadow = None
        else:
            self.W, self.H = self.saved; self.maxed = False; self.M = px(50); self.shadow = (28, 16, 32); nx, ny = px(95) - self.M, px(54) - self.M
        self.fixed.move(self.content, self.M, self.M)
        self.winbox.set_size_request(px(self.W), px(self.H)); self.sidebox.set_size_request(px(211), px(self.H))
        for w, y0 in self.bottoms: self.content.move(w, self.content.child_get_property(w, 'x'), px(y0 + self.H - self.H0))
        self.set_content_size(px(self.W), px(self.H)); self.apply_page_size(); self.rebuild()
        GLib.timeout_add(30, lambda: (self.move(nx, ny), False)[-1])
    def _drag(self, w, e):
        if e.button == 3 and e.x > self.M + px(211) and e.y > self.M + px(60): self.bg_menu(e); return True
        if e.button == 1 and e.y < self.M + px(60) and not (e.x < self.M + px(84) and e.y < self.M + px(46)):
            if e.type == Gdk.EventType._2BUTTON_PRESS: self.toggle_max(); return True
            if e.type == Gdk.EventType.BUTTON_PRESS and not self.maxed: self.begin_move_drag(e.button, int(e.x_root), int(e.y_root), e.time)
        return False
    def queue_draw_all(self):
        def walk(w):
            w.queue_draw()
            if isinstance(w, Gtk.Container): w.foreach(walk)
        walk(self); self.rebuild()
    def bott(self, w, x, y):
        self.put(w, x, px(y)); self.bottoms.append((w, y)); return w
    def build_sidebar(self):
        name = first_name()
        self.av = Avatar(px(32), None, name); self.put(self.av, px(21), px(53))
        self.nm = make_label(name, 11.5, 'semibold', 'text', w=px(120), h=px(18)); self.put(self.nm, px(62), px(51))
        watch_profile(lambda: (self.nm.set_text(display_name()), setattr(self.av, 'name', display_name()), self.av.refresh()))
        self.put(make_label('Personal space', 10, 'normal', 'muted', w=px(120), h=px(14)), px(62), px(70))
        self.put(Icon('chev-d', px(14), 'muted', 1.6), px(176), px(62))
        items = [('Home', 'home', HOME, 101), ('Recent', 'clock', 'recent', 139), ('Starred', 'star', 'starred', 177),
                 ('Images', 'image', os.path.join(HOME, 'Pictures'), 215), ('Music', 'music', os.path.join(HOME, 'Music'), 253),
                 ('Downloads', 'download', os.path.join(HOME, 'Downloads'), 291)]
        self.pillbox = Box('pill', px(184), px(38)); self.put(self.pillbox, px(14), px(101))
        for label, ic, target, y in items + [('Trash', 'trash', 'trash', 351)]:
            if label == 'Trash':
                self.put(Box('rowline', px(170), max(1, px(1))), px(20), px(341))
            icn = Icon(ic, px(18), 'text', 1.5); lab = make_label(label, 11.5, 'medium', 'text', w=px(120), h=px(18))
            self.put(icn, px(25), px(y + 10)); self.put(lab, px(54), px(y + 10))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(184), px(38)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, t=target, l=label: (self.nav(t, l), True)[-1]); self.put(ev, px(14), px(y))
            self.sidebar_items[label] = (icn, lab, y, target)
        # storage card
        self.bott(Box('store', px(182), px(62)), px(15), 549)
        self.bott(Box('tile-sm', px(26), px(26)), px(26), 561); self.bott(Icon('grid', px(15), 'primary', 1.5), px(31), 566)
        self.bott(make_label('Storage', 10.5, 'semibold', 'text', w=px(100), h=px(14)), px(63), 560)
        self.stlab = make_label('', 7.5, 'normal', 'muted', w=px(120), h=px(12)); self.bott(self.stlab, px(63), 575)
        self.stbar = Gtk.DrawingArea(); self.stbar.set_size_request(px(159), px(4)); self.stbar.frac = 0.64
        def bar(w, cr):
            rounded_rect(cr, 0, 0, px(159), px(3), px(1.5)); cr.set_source_rgba(*hex2rgb(pal('track'))); cr.fill()
            rounded_rect(cr, 0, 0, px(159) * self.stbar.frac, px(3), px(1.5)); cr.set_source_rgba(*hex2rgb(pal('primary'))); cr.fill(); return False
        self.stbar.connect('draw', bar); self.bott(self.stbar, px(26), 597); self.update_storage()
    def update_storage(self):
        try: u = shutil.disk_usage(HOME); tot, used = u.total, u.used
        except Exception: tot, used = 100 << 30, 64 << 30
        self.stlab.set_text('%.1f GB of %.0f GB' % (used / 2**30, tot / 2**30)); self.stbar.frac = min(1.0, used / float(tot or 1)); self.stbar.queue_draw(); return True
    def highlight(self, label):
        for l, (icn, lab, y, t) in self.sidebar_items.items():
            on = (l == label); icn.color = 'primary' if on else 'text'; lab.hide() if False else None
            for rec in _texts:
                if rec[0] is lab: rec[3] = 'primary' if on else 'text'; style_label(rec)
            icn.queue_draw()
            if on: self.content.move(self.pillbox, px(14), px(y))
        self.pillbox.set_visible(label in self.sidebar_items and label != 'Trash' or label == 'Trash')
    # ---- navigation
    def nav(self, target, label=None):
        if target == 'search': self.apply_search()
        elif target == 'recent': self.show_list('Recent', recent_files(40), label='Recent')
        elif target == 'starred': self.show_list('Starred', [], label='Starred', empty='No starred items yet')
        elif target == 'trash':
            tp = os.path.expanduser('~/.local/share/Trash/files'); self.show_list('Trash', list_dir(tp), label='Trash', empty='Trash is empty')
        else:
            if not os.path.isdir(target): os.makedirs(target, exist_ok=True)
            self.show_dir(target)
    def rebuild(self):
        if os.path.isdir(self.cwd): self.show_dir(self.cwd, push=False)
        else: self.nav(self.cwd)
    def clear(self):
        for c in self.page.get_children(): c.destroy()
        _texts[:] = [r for r in _texts if not r[0].in_destruction() and r[0].get_parent() is not None]
    def back(self):
        if self.hist: self.show_dir(self.hist.pop(), push=False)
    def show_dir(self, path, push=True):
        if not self._in_search and getattr(self, 'sentry', None) is not None and self.sentry.get_visible(): self.sentry.hide(); self.sentry.set_text(''); self.query = ''
        if push and self.cwd != path: self.hist.append(self.cwd)
        self.cwd = path
        self.highlight('Home' if path == HOME else next((l for l, (i, la, y, t) in self.sidebar_items.items() if t == path), ''))
        if path == HOME: self.home_view()
        else: self.show_list(os.path.basename(path) or '/', self.sort_items(list_dir(path)), label=None, path=path)
        self.page.show_all()
    # ---- shared header
    def header(self, crumbs):
        P = self.page; Wd = px(self.PW)
        P.put(Icon('chev-l', px(16), 'muted', 1.8), px(28), px(22))
        ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(30), px(30)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        ev.connect('button-press-event', lambda *a: (self.back(), True)[-1]); P.put(ev, px(22), px(15))
        x = 61
        for i, (txt, last) in enumerate(crumbs):
            wlab = 12 + 6.2 * len(txt)
            P.put(make_label(txt, 10.5, 'semibold' if last else 'normal', 'text' if last else 'muted', w=px(wlab), h=px(16)), px(x), px(22)); x += wlab - 2
            if not last: P.put(Icon('chev-r', px(12), 'muted', 1.6), px(x + 3), px(24)); x += 22
        act = {'search': bool(getattr(self, 'sentry', None) and self.sentry.get_visible()), 'grid': getattr(self, 'vmode', 'list') == 'grid', 'dots': False}
        for ic, xx in (('search', self.PW - 121), ('grid', self.PW - 81), ('dots', self.PW - 41)):
            P.put(Icon(ic, px(18), 'primary' if act[ic] else 'muted', 1.6), px(xx), px(21))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(34), px(34)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, k=ic: (self.tool(k, e), True)[-1]); P.put(ev, px(xx - 8), px(13))
        P.put(Box('hline', Wd, max(1, px(1))), 0, px(60))
    def tabs(self):
        P = self.page
        for t, x in (('All files', 41), ('Shared', 130), ('Favorites', 204)):
            P.put(make_label(t, 10.5, 'semibold' if t == 'All files' else 'normal', 'text' if t == 'All files' else 'muted', w=px(70), h=px(16)), px(x), px(192))
        P.put(Box('hline', px(self.CW), max(1, px(1))), px(28), px(219))
        ul = Box('btnp', px(40), px(2)); ul.get_style_context().remove_class('btnp'); ul.get_style_context().add_class('ulblue'); P.put(ul, px(41), px(218))
    def section(self, title, y):
        P = self.page
        P.put(make_label(title, 12.5, 'semibold', 'text', w=px(200), h=px(20)), px(28), px(y))
        P.put(make_label('View all', 8.5, 'medium', 'primary', xalign=1.0, w=px(50), h=px(14)), px(self.CW - 52), px(y + 3))
        P.put(Icon('chev-r', px(10), 'primary', 1.8), px(self.CW), px(y + 5))
    def tilebox(self, x, y, size, kind, label, fsz):
        P = self.page; P.put(Box('tile-' + kind, px(size), px(size)), px(x), px(y))
        if label == 'DIR': P.put(Icon('folder', px(size * 0.58), px(1) and 'primary', 1.6), px(x + size * 0.21), px(y + size * 0.21))
        else:
            lb = make_label(label, fsz, 'bold', INKS[kind], xalign=0.5, w=px(size), h=px(size)); P.put(lb, px(x), px(y))
    # ---- home view
    def home_view(self):
        self.clear(); P = self.page; name = first_name().split()[0]
        self.header([('Home', False), ('Home', True)])
        P.put(make_label('PERSONAL WORKSPACE', 8.5, 'bold', 'primary', spacing=0.9, w=px(300), h=px(14)), px(28), px(84))
        hr = int(time.strftime('%H')); gr = 'Good morning' if hr < 12 else ('Good afternoon' if hr < 18 else 'Good evening')
        P.put(make_label('%s, %s' % (gr, name), 30, 'bold', 'text', spacing=-0.6, w=px(560), h=px(44)), px(28), px(99))
        P.put(make_label('Everything is right where you left it.', 10.5, 'normal', 'muted', w=px(400), h=px(16)), px(28), px(145))
        nb = Box('btnp', px(110), px(38)); P.put(nb, px(self.PW - 139), px(123))
        P.put(Icon('plus', px(16), '#ffffff', 2.0), px(self.PW - 128), px(134))
        P.put(make_label('New folder', 11, 'semibold', '#ffffff', w=px(80), h=px(18)), px(self.PW - 106), px(133))
        ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(110), px(38)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        ev.connect('button-press-event', lambda *a: (self.new_folder(), True)[-1]); P.put(ev, px(self.PW - 139), px(123))
        self.tabs(); self.section('Folders', 238)
        folders = [(n, os.path.join(HOME, n)) for n in ('Documents', 'Downloads', 'Pictures', 'Music', 'Videos', 'Desktop') if os.path.isdir(os.path.join(HOME, n))][:4]
        for i, (n, p) in enumerate(folders):
            cwd4 = (self.CW - 34) / 4.0; x = 28 + i * (cwd4 + 11.3); tone = CARD_TONES[i % 4]
            P.put(Box('card', px(cwd4), px(65)), px(x), px(268 - 0))
            self.tilebox(x + 14, 282, 34, tone, 'DIR', 8)
            ic = P.get_children()[-1]
            ic.color = INKS[tone]
            P.put(make_label(n, 10, 'semibold', 'text', w=px(110), h=px(15)), px(x + 60), px(285))
            P.put(make_label('%d items' % count_items(p), 8, 'normal', 'muted', w=px(110), h=px(12)), px(x + 60), px(302))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(cwd4), px(65)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, p=p: (self.show_dir(p), True)[-1]); P.put(ev, px(x), px(268))
        self.section('Recent files', 355)
        self.rows(recent_files(3), 386, self.CW, 28, 3)
    def rows(self, items, y0, width, x0, maxn):
        P = self.page; n = min(len(items), maxn)
        if not n:
            P.put(make_label('Nothing here yet', 10, 'normal', 'muted', w=px(300), h=px(16)), px(x0 + 14), px(y0 + 18)); return
        P.put(Box('store', px(width), px(52 * n)), px(x0), px(y0))
        for i, (nm, p, isdir, mt, sz) in enumerate(items[:n]):
            y = y0 + i * 52; lab, tone, desc = kind_of(p, isdir)
            self.tilebox(x0 + 14, y + 9, 34, tone, lab, 7.5)
            if lab == 'DIR': P.get_children()[-1].color = INKS[tone]
            P.put(make_label(nm, 9.5, 'semibold', 'text', w=px(width - 300), h=px(15)), px(x0 + 59), px(y + 11))
            P.put(make_label(desc if not isdir else 'Folder', 8, 'normal', 'muted', w=px(200), h=px(12)), px(x0 + 59), px(y + 27))
            P.put(make_label(ago(mt), 8, 'normal', 'muted', xalign=1.0, w=px(80), h=px(12)), px(x0 + width - 120), px(y + 20))
            P.put(Icon('dots', px(16), 'muted', 1.4), px(x0 + width - 38), px(y + 18))
            if i < n - 1: P.put(Box('hline', px(width - 2), max(1, px(1))), px(x0 + 1), px(y + 51))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(width), px(52)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, p=p, d=isdir: (self.row_click(e, p, d), True)[-1]); P.put(ev, px(x0), px(y))
    clip = None
    def menu(self, items, e):
        m = Gtk.Menu()
        for it in items:
            if it is None: m.append(Gtk.SeparatorMenuItem()); continue
            lab, fn = it; mi = Gtk.MenuItem(label=lab); mi.set_sensitive(fn is not None)
            if fn: mi.connect('activate', lambda w, fn=fn: fn())
            m.append(mi)
        m.show_all(); m.popup_at_pointer(e)
    def row_click(self, e, p, isdir):
        intrash = self.cwd == 'trash'
        if e.button == 3:
            if intrash: self.menu([('Restore', lambda: (restore(p), self.rebuild())), ('Delete permanently', lambda: (rm_perm(p), self.rebuild())), None, ('Empty trash', self.empty_trash)], e)
            else: self.menu([('Open', lambda: self.open(p, isdir)), None, ('Copy', lambda: self.set_clip('copy', p)), ('Cut', lambda: self.set_clip('cut', p)), ('Rename…', lambda: self.rename(p)),
                             ('Copy path', lambda: self.copy_path(p)), None, ('Move to Trash', lambda: self.trash(p))], e)
        else: self.open(p, isdir)
    def bg_menu(self, e):
        if self.cwd == 'trash': self.menu([('Empty trash', self.empty_trash)], e); return
        base = self.cwd if os.path.isdir(self.cwd) else HOME
        self.menu([('New folder', self.new_folder), ('New text file', self.new_file), None, ('Paste', self.paste if self.clip else None), None, ('Open terminal here', lambda: subprocess.Popen(['lxterminal', '--working-directory=' + base], start_new_session=True))], e)
    def set_clip(self, op, p): FilesWindow.clip = (op, p); notify('Files', ('Copied ' if op == 'copy' else 'Cut ') + os.path.basename(p))
    def copy_path(self, p):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(p, -1)
    def paste(self):
        if not self.clip: return
        op, p = self.clip; base = self.cwd if os.path.isdir(self.cwd) else HOME
        try: copy_to(p, base, move=(op == 'cut')); FilesWindow.clip = None if op == 'cut' else self.clip
        except Exception as ex: notify('Files', 'Paste failed: %s' % ex)
        self.rebuild()
    def trash(self, p):
        try: to_trash(p); notify('Files', 'Moved to Trash: ' + os.path.basename(p))
        except Exception as ex: notify('Files', 'Could not move to Trash: %s' % ex)
        self.rebuild()
    def empty_trash(self):
        for n in os.listdir(os.path.join(TRASH, 'files')) if os.path.isdir(os.path.join(TRASH, 'files')) else []:
            try: rm_perm(os.path.join(TRASH, 'files', n))
            except OSError: pass
        self.rebuild()
    def rename(self, p):
        d = Gtk.Dialog(title='Rename', transient_for=self, modal=True); b = d.get_content_area(); b.set_border_width(18); b.set_spacing(10)
        ent = Gtk.Entry(); ent.set_text(os.path.basename(p)); ent.set_size_request(300, -1); ent.set_activates_default(True); b.add(ent)
        d.add_button('Cancel', Gtk.ResponseType.CANCEL); ok = d.add_button('Rename', Gtk.ResponseType.OK); ok.get_style_context().add_class('suggested-action'); d.set_default_response(Gtk.ResponseType.OK); d.show_all()
        stem = os.path.splitext(os.path.basename(p))[0]; ent.select_region(0, len(stem))
        if d.run() == Gtk.ResponseType.OK and ent.get_text().strip():
            try: os.rename(p, os.path.join(os.path.dirname(p), ent.get_text().strip()))
            except OSError as ex: notify('Files', 'Rename failed: %s' % ex)
        d.destroy(); self.rebuild()
    def new_file(self):
        base = self.cwd if os.path.isdir(self.cwd) else HOME; n = 'New file.txt'; i = 1
        while os.path.exists(os.path.join(base, n)): i += 1; n = 'New file %d.txt' % i
        open(os.path.join(base, n), 'w').close(); self.rebuild()
    # ---- removable drives
    def poll_devices(self):
        def w():
            d = usb_devices(); GLib.idle_add(self.apply_devices, d)
        threading.Thread(target=w, daemon=True).start(); return True
    def apply_devices(self, devs):
        key = json.dumps(devs, sort_keys=True)
        if key == getattr(self, 'devkey', None): return False
        self.devkey = key
        for w in getattr(self, 'devw', []): w.destroy()
        self.devw = []; y0 = 389
        if devs:
            sep = Box('rowline', px(170), max(1, px(1))); self.put(sep, px(20), px(y0 - 6)); self.devw.append(sep)
            lab = make_label('DEVICES', 8, 'bold', 'muted', spacing=0.8, w=px(120), h=px(12)); self.put(lab, px(26), px(y0 + 2)); self.devw.append(lab)
        for i, d in enumerate(devs[:3]):
            y = y0 + 22 + i * 38; icn = Icon('disk', px(18), 'text', 1.5); nm = make_label(d['name'], 11, 'medium', 'text', w=px(110), h=px(18))
            ej = Icon('x', px(12), 'muted', 1.8); self.put(icn, px(25), px(y + 10)); self.put(nm, px(54), px(y + 10)); self.put(ej, px(176), px(y + 13))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(150), px(38)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, d=d: (self.open_dev(d), True)[-1]); self.put(ev, px(14), px(y))
            ev2 = Gtk.EventBox(); ev2.set_visible_window(False); ev2.set_size_request(px(30), px(38)); ev2.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev2.connect('button-press-event', lambda w, e, d=d: (self.eject(d), True)[-1]); self.put(ev2, px(168), px(y))
            self.devw += [icn, nm, ej, ev, ev2]
        for w in self.devw: w.show_all()
        return False
    def open_dev(self, d):
        def w():
            mp = d['mp']
            if not mp:
                out = subprocess.run(['udisksctl', 'mount', '-b', d['path']], capture_output=True, text=True).stdout
                mp = out.split(' at ')[-1].strip().rstrip('.') if ' at ' in out else None
            GLib.idle_add(lambda: (self.show_dir(mp) if mp and os.path.isdir(mp) else notify('Files', 'Could not open ' + d['name']), False)[-1])
        threading.Thread(target=w, daemon=True).start()
    def eject(self, d):
        def w():
            subprocess.run(['udisksctl', 'unmount', '-b', d['path']], capture_output=True); r = subprocess.run(['udisksctl', 'power-off', '-b', d['disk']], capture_output=True, text=True)
            notify('Files', ('Safe to remove ' if r.returncode == 0 else 'Could not eject ') + d['name']); GLib.idle_add(self.poll_devices)
        threading.Thread(target=w, daemon=True).start()
    def open(self, p, isdir):
        if isdir: self.show_dir(p)
        else: subprocess.Popen(['xdg-open', p], start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def show_list(self, title, items, label=None, path=None, empty='This folder is empty'):
        self.clear(); P = self.page; self.cwd = path or title.lower()
        if label: self.highlight(label)
        elif path is not None: self.highlight(next((l for l, (i, la, y, t) in self.sidebar_items.items() if t == path), ''))
        crumbs = [('Home', False), (title, True)] if path != HOME else [('Home', False), ('Home', True)]
        self.header(crumbs)
        P.put(make_label(title.upper(), 8.5, 'bold', 'primary', spacing=0.9, w=px(300), h=px(14)), px(28), px(80))
        P.put(make_label(title, 24, 'bold', 'text', spacing=-0.4, w=px(560), h=px(36)), px(28), px(98))
        P.put(make_label('%d items' % len(items), 10.5, 'normal', 'muted', w=px(300), h=px(16)), px(28), px(138))
        if path:
            nb = Box('btnp', px(110), px(38)); P.put(nb, px(self.PW - 139), px(96))
            P.put(Icon('plus', px(16), '#ffffff', 2.0), px(self.PW - 128), px(107)); P.put(make_label('New folder', 11, 'semibold', '#ffffff', w=px(80), h=px(18)), px(self.PW - 106), px(106))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(110), px(38)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda *a: (self.new_folder(), True)[-1]); P.put(ev, px(self.PW - 139), px(96))
        if not items:
            P.put(make_label(empty, 10.5, 'normal', 'muted', w=px(400), h=px(16)), px(28), px(190)); return
        sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); sc.set_size_request(px(self.CW + 4), px(self.H - 187))
        sc.get_style_context().add_class('osbscroll'); inner = Gtk.Fixed(); sc.add(inner)
        if self.vmode == 'grid':
            cols = max(2, self.CW // 150); gw = (self.CW - (cols - 1) * 12) / float(cols); inner.set_size_request(px(self.CW), px(((len(items) + cols - 1) // cols) * 112 + 8))
            old = self.page; self.page = inner
            for i, (nm, p, isdir, mt, sz) in enumerate(items[:400]):
                x = (i % cols) * (gw + 12); y = 4 + (i // cols) * 112; lab, tone, desc = kind_of(p, isdir)
                inner.put(Box('card', px(gw), px(100)), px(x), px(y)); self.tilebox(x + gw / 2.0 - 20, y + 12, 40, tone, lab, 8)
                if lab == 'DIR': inner.get_children()[-1].color = INKS[tone]
                inner.put(make_label(nm, 9, 'semibold', 'text', xalign=0.5, w=px(gw - 10), h=px(15)), px(x + 5), px(y + 60)); inner.put(make_label('Folder' if isdir else desc, 7.5, 'normal', 'muted', xalign=0.5, w=px(gw - 10), h=px(12)), px(x + 5), px(y + 77))
                ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(gw), px(100)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
                ev.connect('button-press-event', lambda w, e, p=p, d=isdir: (self.row_click(e, p, d), True)[-1]); inner.put(ev, px(x), px(y))
            self.page = old
        else:
            inner.set_size_request(px(self.CW), px(52 * len(items) + 8)); old = self.page; self.page = inner; self.rows(items, 4, self.CW, 0, 400); self.page = old
        P.put(sc, px(28), px(176)); P.show_all()
    vmode = 'list'; sortkey = 'name'; query = ''; _in_search = False; search_base = None
    def tool(self, k, e):
        if k == 'search': self.toggle_search()
        elif k == 'grid':
            self.vmode = 'grid' if self.vmode == 'list' else 'list'; self.rebuild_view()
        else:
            base = self.cwd if os.path.isdir(self.cwd) else HOME; ck = lambda c: ('\u2713 ' if c else '    ')
            def setsort(v): self.sortkey = v; self.rebuild_view()
            def hid(): 
                global SHOW_HIDDEN
                SHOW_HIDDEN = not SHOW_HIDDEN; self.rebuild_view()
            self.menu([('New folder', self.new_folder), ('New text file', self.new_file), ('Paste', self.paste if self.clip else None), None,
                       (ck(self.sortkey == 'name') + 'Sort by name', lambda: setsort('name')), (ck(self.sortkey == 'date') + 'Sort by date', lambda: setsort('date')), (ck(self.sortkey == 'size') + 'Sort by size', lambda: setsort('size')), None,
                       (ck(SHOW_HIDDEN) + 'Show hidden files', hid), ('Open terminal here', lambda: subprocess.Popen(['lxterminal', '--working-directory=' + base], start_new_session=True)), ('Refresh', self.rebuild_view)], e)
    def rebuild_view(self):
        if self.cwd == 'search': self.apply_search()
        else: self.rebuild()
    def sort_items(self, items):
        k = {'name': lambda x: (not x[2], x[0].lower()), 'date': lambda x: (not x[2], -x[3]), 'size': lambda x: (not x[2], -x[4])}[self.sortkey]
        return sorted(items, key=k)
    def toggle_search(self):
        if getattr(self, 'sentry', None) is None:
            self.sentry = Gtk.Entry(); self.sentry.set_placeholder_text('Search files'); self.sentry.set_size_request(px(210), px(30)); self.sentry.get_style_context().add_class('osbsearch')
            self.sentry.connect('changed', self.on_search_changed); self.sentry.connect('key-press-event', lambda w, ev: (self.close_search(), True)[-1] if ev.keyval == Gdk.KEY_Escape else False)
            self.put(self.sentry, px(211 + self.PW - 345), px(13))
        if self.sentry.get_visible(): self.close_search(); return
        if os.path.isdir(self.cwd): self.search_base = self.cwd
        elif self.search_base is None: self.search_base = HOME
        self.content.move(self.sentry, px(211 + self.PW - 345), px(13)); self.sentry.set_text(''); self.sentry.show(); self.sentry.grab_focus(); self.apply_search()
    def close_search(self):
        if getattr(self, 'sentry', None) is not None and self.sentry.get_visible():
            self.sentry.hide(); self.sentry.set_text(''); self.query = ''
            self.show_dir(self.search_base or HOME, push=False)
        self.grab_focus()
    def on_search_changed(self, ent):
        if getattr(self, '_st', None): GLib.source_remove(self._st)
        self._st = GLib.timeout_add(250, self.apply_search)
    def apply_search(self):
        self._st = None
        q = (self.sentry.get_text() if getattr(self, 'sentry', None) else '').strip().lower(); self.query = q; base = self.search_base or HOME
        if not q: self._in_search = True; self.show_dir(base, push=False); self._in_search = False; self.cwd = 'search'; return False
        res = []; seen = 0
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            if root[len(base):].count(os.sep) >= 4: dirs[:] = []
            for n in dirs + files:
                seen += 1
                if q in n.lower() and not n.startswith('.'):
                    pth = os.path.join(root, n)
                    try: st = os.stat(pth); res.append((n, pth, os.path.isdir(pth), st.st_mtime, st.st_size))
                    except OSError: pass
            if seen > 30000 or len(res) >= 300: break
        self._in_search = True; self.show_list('Search results', self.sort_items(res), label=None, empty='No matches', path=None); self._in_search = False; self.cwd = 'search'
        return False
    def new_folder(self):
        base = self.cwd if os.path.isdir(self.cwd) else HOME; n = 'New folder'; i = 1
        while os.path.exists(os.path.join(base, n)): i += 1; n = 'New folder %d' % i
        try: os.makedirs(os.path.join(base, n))
        except OSError: pass
        self.show_dir(base, push=False)

def already_running():
    me = os.getpid(); out = subprocess.run(['pgrep', '-f', 'osb-files|osb.files'], capture_output=True, text=True).stdout.split()
    others = [p for p in out if p.isdigit() and int(p) != me and 'pgrep' not in open('/proc/%s/cmdline' % p, 'rb').read().decode(errors='ignore')]
    if not others: return False
    ids = subprocess.run(['xdotool', 'search', '--class', 'osb-files'], capture_output=True, text=True).stdout.split()
    if ids: subprocess.run(['xdotool', 'windowactivate', ids[-1]])
    return bool(ids)

def main():
    if already_running(): return
    init_mode()
    c = Gtk.CssProvider(); c.load_from_data(b'.osbsearch{border-radius:15px;padding:2px 12px;font-size:12px;} .ulblue{background-color:#0a7cff;border-radius:1px;} .osbscroll,.osbscroll viewport{background:transparent;} .osbscroll undershoot,.osbscroll overshoot{background:none;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = FilesWindow(); w.connect('destroy', Gtk.main_quit); w.show_all()
    if '--trash' in sys.argv: w.nav('trash', 'Trash')
    Gtk.main()
