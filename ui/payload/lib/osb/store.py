"""osb-store: Osborne Software - one themed store for Flathub (Flatpak) and the Snap Store."""
import os, re, sys, shutil, subprocess, threading, hashlib, pty, select, time
from .common import *

FLATHUB = 'https://dl.flathub.org/repo/flathub.flatpakrepo'
# (name, summary, flatpak id, snap name, snap classic?)
FEATURED = [
    ('Firefox', 'Fast, private web browser', 'org.mozilla.firefox', 'firefox', False),
    ('Chromium', 'Open-source web browser', 'org.chromium.Chromium', 'chromium', False),
    ('VLC', 'Plays almost any video or audio file', 'org.videolan.VLC', 'vlc', False),
    ('GIMP', 'Image editor, a free Photoshop alternative', 'org.gimp.GIMP', 'gimp', False),
    ('LibreOffice', 'Word processor, spreadsheets, presentations', 'org.libreoffice.LibreOffice', 'libreoffice', False),
    ('Visual Studio Code', 'Code editor from Microsoft', 'com.visualstudio.code', 'code', True),
    ('OBS Studio', 'Screen recording and live streaming', 'com.obsproject.Studio', 'obs-studio', False),
    ('Telegram', 'Messaging app', 'org.telegram.desktop', 'telegram-desktop', False),
    ('Discord', 'Chat for communities and friends', 'com.discordapp.Discord', 'discord', False),
    ('Spotify', 'Music streaming', 'com.spotify.Client', 'spotify', False),
    ('Thunderbird', 'Email client', 'org.mozilla.Thunderbird', 'thunderbird', False),
    ('Inkscape', 'Vector graphics editor', 'org.inkscape.Inkscape', 'inkscape', False),
    ('Blender', '3D creation suite', 'org.blender.Blender', 'blender', True),
    ('Kdenlive', 'Video editor', 'org.kde.kdenlive', 'kdenlive', False),
    ('Audacity', 'Audio recorder and editor', 'org.audacityteam.Audacity', 'audacity', False),
    ('Postman', 'API testing tool', 'com.getpostman.Postman', 'postman', False),
]
SKIP_SNAPS = {'core', 'core18', 'core20', 'core22', 'core24', 'bare', 'snapd', 'snap-store', 'gtk-common-themes'}
TILE_COLORS = ['#0a7cff', '#7a5af8', '#f2616c', '#1ea672', '#ff9d12', '#d46fb5', '#2aa5c9']

def run(cmd, timeout=40):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout); return r.returncode, (r.stdout or ''), (r.stderr or '')
    except FileNotFoundError: return 127, '', 'not installed'
    except Exception as e: return 1, '', str(e)

def have(cmd): return shutil.which(cmd) is not None

def run_stream(cmd, on_line, timeout=1800, stdin_text=None):
    """Run a command on a pseudo terminal (so flatpak prints its progress) and call on_line(text) for every line or progress update."""
    try:
        master, slave = pty.openpty()
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE if stdin_text is not None else subprocess.DEVNULL, stdout=slave, stderr=slave, close_fds=True); os.close(slave)
    except FileNotFoundError: return 127, 'not installed'
    except Exception as e: return 1, str(e)
    if stdin_text is not None:
        try: p.stdin.write(stdin_text.encode()); p.stdin.close()
        except Exception: pass
    buf = b''; t0 = time.time(); last = ''
    while True:
        if time.time() - t0 > timeout: p.kill(); return 1, 'timed out'
        r, _, _ = select.select([master], [], [], 1.0)
        if r:
            try: d = os.read(master, 2048)
            except OSError: d = b''
            if not d: break
            buf += d
            parts = re.split(rb'[\r\n]', buf); buf = parts.pop()
            for part in parts:
                t = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', part.decode('utf-8', 'replace')).strip()
                if t: last = t; on_line(t)
        elif p.poll() is not None: break
    try: os.close(master)
    except Exception: pass
    return p.wait(), last

_fh = {'ready': False, 'err': ''}
def ensure_flathub(on_line=None):
    """Add the Flathub store (once) and download its app list, so search and install work."""
    if not have('flatpak'): _fh['err'] = 'Flatpak is not installed on this system.'; return False
    rc, out, err = run(['flatpak', 'remote-add', '--user', '--if-not-exists', 'flathub', FLATHUB], 60)
    if rc != 0: _fh['err'] = (err or out).strip().splitlines()[-1][:120] if (err or out).strip() else 'Could not add Flathub.'; return False
    rc, last = run_stream(['flatpak', 'update', '--user', '--appstream', '-y', '--noninteractive', 'flathub'], on_line or (lambda t: None), 240)
    _fh['ready'] = rc == 0; _fh['err'] = '' if rc == 0 else (last or 'Could not download the app list.')
    return _fh['ready']

# --------------------------------------------------------------- backends
def flatpak_search(q):
    if not have('flatpak'): return []
    rc, out, _ = run(['flatpak', 'search', '--user', '--columns=application,name,description', q], 60)
    res = []
    for ln in out.splitlines():
        p = ln.split('\t')
        if len(p) >= 2 and '.' in p[0]: res.append(dict(src='flathub', id=p[0], name=p[1], summary=p[2] if len(p) > 2 else '', classic=False))
    return res[:25]

def snap_search(q):
    if not have('snap'): return []
    rc, out, _ = run(['snap', 'find', q], 30)
    res = []
    for ln in out.splitlines()[1:]:
        p = re.split(r'\s{2,}', ln.strip())
        if len(p) >= 4: res.append(dict(src='snap', id=p[0], name=p[0], summary=p[-1], classic='classic' in (p[3] if len(p) > 4 else '')))
    return res[:25]

def installed_list():
    res = []
    if have('flatpak'):
        rc, out, _ = run(['flatpak', 'list', '--app', '--columns=application,name,description'], 15)
        for ln in out.splitlines():
            p = ln.split('\t')
            if len(p) >= 2: res.append(dict(src='flathub', id=p[0], name=p[1], summary=p[2] if len(p) > 2 else '', classic=False, installed=True))
    if have('snap'):
        rc, out, _ = run(['snap', 'list'], 15)
        for ln in out.splitlines()[1:]:
            p = ln.split()
            if p and p[0] not in SKIP_SNAPS and not p[0].startswith(('core', 'gnome-', 'gtk-', 'mesa-', 'kf5-')):
                res.append(dict(src='snap', id=p[0], name=p[0], summary='Snap · ' + (p[1] if len(p) > 1 else ''), classic=False, installed=True))
    return res

def installed_ids():
    return {(a['src'], a['id']) for a in installed_list()}

def do_install(a, on_line, pw=None):
    if a['src'] == 'flathub':
        if not _fh['ready'] and not ensure_flathub(on_line): return 1, 'Flathub: ' + (_fh['err'] or 'not reachable')
        return run_stream(['flatpak', 'install', '--user', '-y', '--noninteractive', 'flathub', a['id']], on_line, 3600)
    cmd = ['sudo', '-S', '-k', '-p', '', 'snap', 'install', a['id']] + (['--classic'] if a.get('classic') else [])
    return run_stream(cmd, on_line, 3600, stdin_text=(pw or '') + '\n')

def do_remove(a, on_line, pw=None):
    if a['src'] == 'flathub': return run_stream(['flatpak', 'uninstall', '--user', '-y', '--noninteractive', a['id']], on_line, 900)
    return run_stream(['sudo', '-S', '-k', '-p', '', 'snap', 'remove', a['id']], on_line, 900, stdin_text=(pw or '') + '\n')

# --------------------------------------------------------------- UI
class Store(OsbWindow):
    draggable = True
    def __init__(self):
        cw, ch, m = px(800), px(560), px(40)
        super().__init__(cw, ch, m, None, 'Software'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-store', 'Osb-store'); self.set_type_hint(Gdk.WindowTypeHint.NORMAL); self.set_position(Gtk.WindowPosition.CENTER)
        self.put(Box('panel', cw, ch), 0, 0); traffic_lights(self, 16, 14); self.enable_escape()
        self.put(make_label('Software', 15, 'semibold', 'text', w=px(300), h=px(24)), px(30), px(38))
        self.put(Box('qsrow', px(470), px(42)), px(30), px(76)); self.put(Icon('search', px(18), 'muted', 1.6), px(44), px(88))
        self.entry = Gtk.Entry(); self.entry.set_has_frame(False); self.entry.set_placeholder_text('Search apps in Flathub and Snap')
        self.entry.set_size_request(px(410), px(34)); self.entry.get_style_context().add_class('osbentry'); self.put(self.entry, px(72), px(80))
        self.entry.connect('activate', lambda e: self.search()); self.deb = None
        def typed(e):
            if self.deb: GLib.source_remove(self.deb)
            self.deb = GLib.timeout_add(700, lambda: (setattr(self, 'deb', None), self.search(), False)[-1]) if e.get_text().strip() else None
            if not e.get_text().strip() and self.mode != 'installed': self.show_featured()
        self.entry.connect('changed', typed)
        self.mode = 'all'; self.pills = {}
        for i, (key, lab) in enumerate((('all', 'All'), ('flathub', 'Flathub'), ('snap', 'Snap'), ('installed', 'Installed'))):
            x = 512 + i * 66 if i < 3 else 512 + 3 * 66 + 0
            wd = 62 if key != 'installed' else 80
            pill = Box('seg', px(wd), px(30)); lb = make_label(lab, 10, 'semibold', 'text', xalign=0.5, w=px(wd), h=px(30))
            self.put(pill, px(x), px(82)); self.put(lb, px(x), px(82))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(wd), px(30)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, k=key: (self.set_mode_(k), True)[-1]); self.put(ev, px(x), px(82)); self.pills[key] = (pill, lb)
        self.status = make_label('Popular apps', 10, 'semibold', 'muted', w=px(500), h=px(16)); self.put(self.status, px(32), px(130))
        self.sc = Gtk.ScrolledWindow(); self.sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); self.sc.set_size_request(px(750), px(368))
        self.sc.get_style_context().add_class('osbscroll'); self.lst = Gtk.Fixed(); self.sc.add(self.lst); self.put(self.sc, px(20), px(154))
        self.bar = PulseBar(px(740), 6); self.put(self.bar, px(30), px(536)); self.bar.hide()
        self.busy = False; self.results = []; self.inst = set(); self.token = 0
        self.connect('destroy', lambda *a: Gtk.main_quit()); self.paint_pills(); self.show_featured()
        threading.Thread(target=self._warm, daemon=True).start()
    def _warm(self):
        ids = installed_ids(); GLib.idle_add(self._set_inst, ids)
        if have('flatpak') and not _fh['ready']:
            GLib.idle_add(self.status.set_text, 'Connecting to Flathub… (first time can take a minute)')
            ok = ensure_flathub(lambda t: GLib.idle_add(self.status.set_text, 'Connecting to Flathub… ' + t[:60]))
            GLib.idle_add(self._fh_done, ok)
    def _fh_done(self, ok):
        if self.busy: return False
        if ok: self.status.set_text('Popular apps' if not self.entry.get_text().strip() else self.status.get_text())
        else: self.status.set_text('Cannot reach Flathub: %s' % (_fh['err'] or 'check the internet connection'))
        return False
    def _set_inst(self, ids):
        self.inst = ids; self.fill(self.results); return False
    # -- pills
    def paint_pills(self):
        for k, (pill, lb) in self.pills.items():
            ctx = pill.get_style_context(); ctx.remove_class('btnp'); ctx.remove_class('seg')
            ctx.add_class('btnp' if k == self.mode else 'seg')
    def set_mode_(self, k):
        self.mode = k; self.paint_pills()
        if k == 'installed': self.show_installed()
        elif self.entry.get_text().strip(): self.search()
        else: self.show_featured()
    # -- lists
    def show_featured(self):
        self.status.set_text('Popular apps'); res = []
        for name, summ, fid, snap, classic in FEATURED:
            if self.mode in ('all', 'flathub'): res.append(dict(src='flathub', id=fid, name=name, summary=summ, classic=False))
            if self.mode == 'snap' or (self.mode == 'all' and False): res.append(dict(src='snap', id=snap, name=name, summary=summ, classic=classic))
        self.results = res; self.fill(res)
    def show_installed(self):
        self.status.set_text('Loading installed apps…')
        def w():
            res = installed_list(); GLib.idle_add(self._show_inst, res)
        threading.Thread(target=w, daemon=True).start()
    def _show_inst(self, res):
        self.inst = {(a['src'], a['id']) for a in res}; self.results = res
        self.status.set_text('%d installed apps' % len(res) if res else 'Nothing installed from these stores yet'); self.fill(res); return False
    def search(self):
        q = self.entry.get_text().strip()
        if self.mode == 'installed': self.mode = 'all'; self.paint_pills()
        if not q: self.show_featured(); return
        self.token += 1; tok = self.token; self.status.set_text('Searching for “%s”…' % q)
        def w():
            res = []
            if self.mode in ('all', 'flathub') and have('flatpak') and not _fh['ready']: ensure_flathub()
            if self.mode in ('all', 'flathub'): res += flatpak_search(q)
            if self.mode in ('all', 'snap'): res += snap_search(q)
            GLib.idle_add(self._got, tok, q, res)
        threading.Thread(target=w, daemon=True).start()
    def _got(self, tok, q, res):
        if tok != self.token: return False
        offline = not res and not (have('flatpak') or have('snap'))
        if not res and have('flatpak') and not _fh['ready'] and _fh['err']: self.results = res; self.status.set_text('Cannot reach Flathub: %s' % _fh['err'][:80]); self.fill(res); return False
        self.results = res
        self.status.set_text('%d results for “%s”' % (len(res), q) if res else ('No store is installed on this system' if offline else 'No results for “%s” (check the internet connection)' % q))
        self.fill(res); return False
    def fill(self, res):
        for c in self.lst.get_children(): c.destroy()
        y = 0
        for a in res:
            self.lst.put(Box('qsrow', px(736), px(62)), 0, px(y))
            col = TILE_COLORS[int(hashlib.md5(a['name'].encode()).hexdigest(), 16) % len(TILE_COLORS)]
            tile = Gtk.DrawingArea(); tile.set_size_request(px(40), px(40)); ini = (a['name'][:1] or '?').upper()
            def dt(w, cr, col=col, ini=ini):
                rounded_rect(cr, 0, 0, px(40), px(40), px(12)); cr.set_source_rgba(*hex2rgb(col)); cr.fill()
                cr.select_font_face('sans-serif', 0, 1); cr.set_font_size(px(18)); xb, yb, tw, th, xa, ya = cr.text_extents(ini)
                cr.set_source_rgb(1, 1, 1); cr.move_to((px(40) - tw) / 2 - xb, (px(40) - th) / 2 - yb); cr.show_text(ini); return False
            tile.connect('draw', dt); self.lst.put(tile, px(12), px(y + 11))
            self.lst.put(make_label(a['name'], 11.5, 'semibold', 'text', w=px(410), h=px(18)), px(64), px(y + 9))
            self.lst.put(make_label(a['summary'] or a['id'], 9, 'normal', 'muted', w=px(430), h=px(14)), px(64), px(y + 31))
            self.lst.put(make_label('Flathub' if a['src'] == 'flathub' else 'Snap', 9, 'semibold', 'primary', xalign=0.5, w=px(60), h=px(14)), px(500), px(y + 24))
            isin = (a['src'], a['id']) in self.inst
            b = Gtk.Button(label='Remove' if isin else 'Install'); b.set_size_request(px(110), px(34))
            if not isin: b.get_style_context().add_class('suggested-action')
            b.connect('clicked', lambda w, a=a, isin=isin: self.act(a, isin)); self.lst.put(b, px(604), px(y + 14)); y += 68
        self.lst.set_size_request(px(736), max(px(y), px(10))); self.lst.show_all(); self.sc.get_vadjustment().set_value(0)
    # -- install / remove
    def act(self, a, isin):
        if self.busy: self.status.set_text('Please wait, another job is running…'); return
        pw = None
        if a['src'] == 'snap':
            pw = ask_password(self, 'Software', 'Type your account password to %s %s.' % ('remove' if isin else 'install', a['name']), 'Continue')
            if pw is None: return
        self.busy = True; verb = 'Removing' if isin else 'Installing'; self.job = '%s %s' % (verb, a['name']); self.status.set_text(self.job + '… starting'); self.bar.show(); self.bar.set_fraction(None); self.bar.start()
        def on_line(t):
            m = re.search(r'(\d{1,3})%', t)
            def ui():
                if m: self.bar.set_fraction(min(1.0, int(m.group(1)) / 100.0)); self.status.set_text('%s… %s%%' % (self.job, m.group(1)))
                else: self.status.set_text('%s… %s' % (self.job, re.sub(r'[^\w\s\.\-/:()]+', '', t)[:70].strip()))
                return False
            GLib.idle_add(ui)
        def w():
            rc, msg = (do_remove if isin else do_install)(a, on_line, pw); GLib.idle_add(self.finished, a, isin, rc, msg)
        threading.Thread(target=w, daemon=True).start()
    def finished(self, a, isin, rc, msg):
        self.busy = False; self.bar.stop(); self.bar.hide()
        if rc == 0:
            (self.inst.discard if isin else self.inst.add)((a['src'], a['id']))
            self.status.set_text('%s %s' % (a['name'], 'removed' if isin else 'installed - find it in the apps list')); subprocess.Popen(['notify-send', 'Software', '%s %s' % (a['name'], 'removed' if isin else 'installed')], stderr=subprocess.DEVNULL)
            if self.mode == 'installed': self.show_installed()
            else: self.fill(self.results)
        else:
            m = (msg or '').strip(); hint = ' (check the internet connection)' if re.search(r'connect|resolve|network|timed out|unable to load|summary', m, re.I) else ''
            self.status.set_text('Failed: ' + (m[:80] if m else 'unknown error') + hint)
        return False

def main():
    ids = subprocess.run(['pgrep', '-f', 'python.*osb-store'], capture_output=True, text=True).stdout.split()
    others = [p for p in ids if p.isdigit() and int(p) != os.getpid()]
    if others:
        r = subprocess.run(['xdotool', 'search', '--class', 'osb-store'], capture_output=True, text=True).stdout.split()
        if r: subprocess.run(['xdotool', 'windowactivate', r[-1]]); return
    init_mode(); c = Gtk.CssProvider()
    c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;} .osbentry{background:transparent;border:none;box-shadow:none;font-size:14px;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = Store(); w.show_all(); w.bar.hide(); w.entry.grab_focus(); watch_mode(lambda m: w.queue_draw()); Gtk.main()
