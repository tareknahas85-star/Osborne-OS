"""osb-shell: wallpaper + top bar + dock + quick settings (HeroUI 'Linux Desktop' design)."""
import os, sys, re, time, json, subprocess, threading, getpass, pwd, ctypes
import gi
gi.require_version('GdkX11','3.0')
from gi.repository import GdkX11
from .common import *
from .i18n import tr as T

def launch(cmd):
    try: subprocess.Popen(cmd, shell=isinstance(cmd, str), start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e: print('launch failed', cmd, e, file=sys.stderr)

def run_bg(cmd, cb=None, timeout=4):
    def w():
        try: out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout.strip()
        except Exception: out = ''
        if cb: GLib.idle_add(cb, out)
    threading.Thread(target=w, daemon=True).start()

def sh_out(cmd, timeout=2):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception: return ''

def user_names():
    name = display_name(); return name, name_initials(name)

# ---------------------------------------------------------------- wallpaper
class Wallpaper(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL); scr = Gdk.Screen.get_default()
        self.w, self.h = scr.get_width(), scr.get_height()
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP); self.set_decorated(False); self.set_title('osb-wallpaper')
        self.set_default_size(self.w, self.h); self.move(0, 0); self.set_skip_taskbar_hint(True)
        self.da = Gtk.DrawingArea(); self.add(self.da); self.da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK); self.da.connect('button-press-event', self._click); self.da.connect('draw', self._d); self.surf = None; self.surf_mode = None; watch_wall(lambda: self.da.queue_draw())
    def _d(self, wd, cr):
        key = (State.mode, get_wall())
        if self.surf_mode != key: self.surf = render_wall(self.w, self.h, State.mode); self.surf_mode = key
        cr.set_source_surface(self.surf, 0, 0); cr.paint(); return False
    def refresh(self): self.da.queue_draw()
    def _click(self, w, e):
        if e.button != 3: return False
        m = new_menu()
        for label, cmd in (('Change wallpaper', 'osb-settings appearance'), ('Display settings', 'osb-settings display'), ('Open Files', 'osb-files'), ('Open Terminal', 'lxterminal'), ('Settings', 'osb-settings')):
            it = Gtk.MenuItem(label=T(label)); it.connect('activate', lambda i, c=cmd: launch(c)); m.append(it)
        m.show_all(); m.popup_at_pointer(e); return True

def lclick(fn):
    """button-press handler that reacts to the left button only (so right-click can open a menu)."""
    return lambda w, e: ((fn(), True)[-1] if e.button == 1 else False)

class Stats:
    """CPU %, memory % and network speed, read from /proc (cheap)."""
    def __init__(self): self.c = None; self.n = None; self.t = 0
    def read(self):
        now = time.time(); out = {}
        try:
            v = [int(x) for x in open('/proc/stat').readline().split()[1:8]]; idle = v[3] + v[4]; tot = sum(v)
            if self.c: out['cpu'] = max(0, min(100, int(round(100.0 * (1 - (idle - self.c[0]) / float(max(1, tot - self.c[1])))))))
            self.c = (idle, tot)
        except Exception: pass
        try:
            m = {}
            for ln in open('/proc/meminfo'):
                k, v = ln.split(':', 1); m[k] = int(v.split()[0])
                if len(m) > 6: break
            out['ram'] = int(round(100.0 * (m['MemTotal'] - m['MemAvailable']) / m['MemTotal']))
        except Exception: pass
        try:
            rx = tx = 0
            for ln in list(open('/proc/net/dev'))[2:]:
                n, d = ln.split(':', 1)
                if n.strip() == 'lo' or n.strip().startswith(('docker', 'veth', 'virbr')): continue
                f = d.split(); rx += int(f[0]); tx += int(f[8])
            if self.n and now > self.t: out['down'] = max(0, (rx - self.n[0]) / (now - self.t)); out['up'] = max(0, (tx - self.n[1]) / (now - self.t))
            self.n = (rx, tx); self.t = now
        except Exception: pass
        return out

def fmt_speed(b):
    for u, d in (('G', 1 << 30), ('M', 1 << 20), ('K', 1 << 10)):
        if b >= d: return '%.1f%s' % (b / float(d), u) if b < 10 * d else '%d%s' % (b / d, u)
    return '%dB' % b

# ---------------------------------------------------------------- top bar
APPNAMES = {'osb-files': 'Files', 'Osb-files': 'Files', 'firefox': 'Firefox', 'Firefox': 'Firefox', 'google-chrome': 'Chrome', 'Google-chrome': 'Chrome', 'lxterminal': 'Terminal',
            'Lxterminal': 'Terminal', 'mousepad': 'Text Editor', 'Mousepad': 'Text Editor', 'pavucontrol': 'Sound', 'Pavucontrol': 'Sound', 'Osb-settings': 'Settings', 'Osb-calc': 'Calculator', 'Osb-wifi': 'Wi-Fi', 'Osb-monitor': 'System Monitor', 'Osb-power': 'Power', 'Osb-store': 'Software'}
class TopBar(OsbWindow):
    def __init__(self, app):
        sw = Gdk.Screen.get_default().get_width()
        super().__init__(sw, px(40), 0, Gdk.WindowTypeHint.DOCK, 'osb-topbar'); self.app = app; self.sw = sw
        self.move(0, 0)
        cfg = self.cfg = load_bar()
        if cfg.get('tint'):
            tb = Gtk.DrawingArea(); tb.set_size_request(sw, px(40))
            def _tint(w, cr):
                c = hex2rgb(pal('win')); cr.set_source_rgba(c[0], c[1], c[2], 0.82); cr.paint(); return False
            tb.connect('draw', _tint); self.put(tb, 0, 0)
        self.put(Emblem(px(26), 'bar'), px(16), px(7)); lx = 54
        if cfg['activities']:
            act = make_label('Activities', 13, 'semibold', 'text', w=px(80), h=px(20)); self.put(act, px(lx), px(10)); lx = 127
            aev = Gtk.EventBox(); aev.set_visible_window(False); aev.set_size_request(px(80), px(40)); aev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            aev.connect('button-press-event', lclick(lambda: launch('osb-switcher overview'))); self.put(aev, px(54), 0)
        self.appl = make_label('Files', 13, 'medium', 'muted', w=px(140), h=px(20))
        if cfg['appname']: self.put(self.appl, px(lx), px(10))
        self.wifi = Icon('wifi', px(17), 'text', 1.6); self.vol = Icon('volume', px(17), 'text', 1.6); self.bat = Icon('battery', px(17), 'text', 1.6)
        self.clock = make_label('00:00', 13, 'medium', 'text', xalign=0.0, w=px(62), h=px(20))
        self.chev = Icon('chev-d', px(14), 'text', 1.8); self.lay = make_label('EN', 11.5, 'semibold', 'text', xalign=0.5, w=px(30), h=px(20))
        self.bell = Icon('bell', px(17), 'text', 1.6)
        self.pw = Icon('power', px(17), 'text', 1.7); self.put(self.pw, sw - px(36), px(11))
        pev = Gtk.EventBox(); pev.set_visible_window(False); pev.set_size_request(px(32), px(40)); pev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pev.connect('button-press-event', lclick(lambda: launch('osb-power'))); self.put(pev, sw - px(42), 0)
        # right side: laid out from the power button towards the left, only the items the user kept
        cur = sw - px(56); self.put(self.chev, cur - px(14), px(13)); cur -= px(14)
        right_edge = cur + px(14)
        tray = []
        cpos = cfg.get('clock_pos', 'right')
        if cfg['clock'] and cpos == 'right': cur -= px(70); self.put(self.clock, cur, px(10)); tray.append(cur)
        for key, w_, off in (('bat', 17, 9), ('vol', 17, 9), ('wifi', 17, 9)):
            if cfg[key]: cur -= px(w_ + off); self.put(getattr(self, key), cur, px(11)); tray.append(cur)
        self.wx_on = cfg.get('weather', True); self.wx_data = None
        if self.wx_on:
            cur -= px(84); self.wxi = Icon('wx-cloud', px(16), 'text', 1.6); self.put(self.wxi, cur + px(2), px(12))
            self.wxl = make_label('…', 12, 'medium', 'text', xalign=0.0, w=px(58), h=px(20)); self.put(self.wxl, cur + px(22), px(10))
            wev = Gtk.EventBox(); wev.set_visible_window(False); wev.set_size_request(px(84), px(40)); wev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            wev.connect('button-press-event', lclick(self.wx_popup)); self.put(wev, cur, 0)
            self.wx_pop = Gtk.Popover(); self.wx_pop.set_relative_to(self.wxl); self.wx_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            self.wx_box.set_margin_start(14); self.wx_box.set_margin_end(14); self.wx_box.set_margin_top(12); self.wx_box.set_margin_bottom(12); self.wx_pop.add(self.wx_box)
            GLib.timeout_add_seconds(4, self.wx_tick); GLib.timeout_add_seconds(900, self.wx_tick)
        tray_left = cur
        ev = Gtk.EventBox(); ev.set_visible_window(False); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        ev.set_size_request(max(px(40), right_edge - tray_left + px(20)), px(40)); ev.connect('button-press-event', lclick(app.toggle_qs)); self.put(ev, tray_left - px(10), 0)
        if cfg['bell']:
            cur -= px(17 + 16); self.put(self.bell, cur, px(11))
            bev = Gtk.EventBox(); bev.set_visible_window(False); bev.set_size_request(px(32), px(40)); bev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            bev.connect('button-press-event', lclick(lambda: launch('osb-notifs'))); self.put(bev, cur - px(7), 0)
        if cfg['lang']:
            cur -= px(30 + 8); self.put(self.lay, cur, px(10))
            lev = Gtk.EventBox(); lev.set_visible_window(False); lev.set_size_request(px(34), px(40)); lev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            lev.connect('button-press-event', lclick(self.toggle_layout)); self.put(lev, cur - px(2), 0)
        # left / centre clock and the optional CPU, memory and network readouts
        lx2 = px(lx) + (px(150) if cfg['appname'] else 0)
        if cfg['clock'] and cpos in ('left', 'center'):
            self.clock.set_xalign(0.5); self.clock.set_size_request(px(80), px(20))
            cx = int((sw - px(80)) / 2) if cpos == 'center' else lx2; self.put(self.clock, cx, px(10))
            cev = Gtk.EventBox(); cev.set_visible_window(False); cev.set_size_request(px(80), px(40)); cev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            cev.connect('button-press-event', lclick(app.toggle_qs)); self.put(cev, cx, 0)
            if cpos == 'left': lx2 += px(90)
        self.stats = Stats(); self.stat_on = [k for k in ('cpu', 'ram', 'net') if cfg.get(k)]
        self.statl = make_label('', 11, 'medium', 'muted', w=px(300), h=px(20))
        if self.stat_on:
            self.put(self.statl, lx2 + px(6), px(10)); self.stats.read(); GLib.timeout_add_seconds(2, self.stat_tick)
        self.connect('button-press-event', self._rclick)
        self.connect('realize', self._strut); self.poll_layout(); GLib.timeout_add(800, self.poll_layout); self.tick(); GLib.timeout_add_seconds(15, self.tick); GLib.timeout_add(2500, self.poll_active)
    def wx_tick(self):
        if not self.wx_on: return False
        import threading
        def work():
            from . import weather as W
            try:
                lat, lon, name = W.place(); d = W.forecast(lat, lon); GLib.idle_add(self.wx_show, d, name)
            except Exception: GLib.idle_add(self.wx_show, None, '')
        threading.Thread(target=work, daemon=True).start(); return True
    def wx_show(self, d, name):
        if d is None: self.wxl.set_text('—'); self.wx_data = None; return False
        from . import weather as W
        self.wx_data = (d, name); self.wxl.set_text('%d°' % d['temp']); self.wxi.set_name_(W.icon_for(d.get('code')))
        self.wx_morning(d, name); return False
    def wx_morning(self, d, name):
        """Once a day between 07:00 and 09:00, send a short weather notification."""
        stamp = os.path.join(CONF, 'wx_morning'); today = time.strftime('%Y-%m-%d')
        if not (7 <= time.localtime().tm_hour < 9): return
        try:
            if open(stamp).read().strip() == today: return
        except Exception: pass
        os.makedirs(CONF, exist_ok=True); open(stamp, 'w').write(today)
        body = '%s  ·  %d°C  ·  %s' % (name or '', d['temp'], d['text'])
        run_bg(['notify-send', '-a', 'Weather', 'Good morning', body], None, 5)
    def wx_popup(self):
        for c in self.wx_box.get_children(): self.wx_box.remove(c)
        if not self.wx_data:
            lines = [('Weather', 'bold'), ('Could not get the weather. Check the internet connection.', 'normal')]
        else:
            d, name = self.wx_data
            lines = [(name or 'Weather', 'bold'), ('%d°C  ·  %s' % (d['temp'], d['text']), 'semibold'),
                     ('Humidity %s%%  ·  Wind %d km/h' % (d['humidity'], d['wind']), 'normal')]
            lines += [('%s   %d° / %d°   %s' % (x['day'], x['hi'], x['lo'], x['text']), 'normal') for x in d['days']]
        for t, w in lines:
            lb = make_label(t, 12 if w != 'bold' else 13, w, 'text', w=px(260), h=px(20)); lb.set_xalign(0.0); self.wx_box.pack_start(lb, False, False, 0)
        self.wx_box.show_all(); self.wx_pop.popup(); return False
    def stat_tick(self):
        if not self.stat_on: return False
        d = self.stats.read(); parts = []
        if 'cpu' in self.stat_on and 'cpu' in d: parts.append('CPU %d%%' % d['cpu'])
        if 'ram' in self.stat_on and 'ram' in d: parts.append('RAM %d%%' % d['ram'])
        if 'net' in self.stat_on and 'down' in d: parts.append('\u2193%s \u2191%s' % (fmt_speed(d['down']), fmt_speed(d['up'])))
        self.statl.set_text('   '.join(parts)); return True
    def _rclick(self, w, e):
        if e.button != 3: return False
        m = new_menu(); self.app.menu_open = True; cfg = load_bar()
        def flip(k):
            d = load_bar(); d[k] = not d.get(k); save_json(BARFILE, d)
        def setpos(v):
            d = load_bar(); d['clock_pos'] = v; save_json(BARFILE, d)
        for k, lab in (('cpu', 'Show CPU usage'), ('ram', 'Show memory usage'), ('net', 'Show network speed')):
            it = Gtk.CheckMenuItem(label=T(lab)); it.set_active(bool(cfg.get(k))); it.connect('toggled', lambda i, k=k: flip(k)); m.append(it)
        m.append(Gtk.SeparatorMenuItem())
        sub = Gtk.Menu(); grp = None
        for v, lab in (('left', 'Left'), ('center', 'Centre'), ('right', 'Right')):
            it = Gtk.RadioMenuItem.new_with_label_from_widget(grp, T(lab)); grp = grp or it; it.set_active(cfg.get('clock_pos', 'right') == v)
            it.connect('toggled', lambda i, v=v: i.get_active() and setpos(v)); sub.append(it)
        ci = Gtk.MenuItem(label=T('Clock position')); ci.set_submenu(sub); m.append(ci)
        m.append(Gtk.SeparatorMenuItem())
        it = Gtk.MenuItem(label=T('Top bar settings…')); it.connect('activate', lambda i: launch(['osb-settings', 'customize'])); m.append(it)
        m.connect('hide', lambda *a: setattr(self.app, 'menu_open', False)); m.show_all(); m.popup_at_pointer(e); return True
    def _strut(self, *_):
        try:
            xid = self.get_window().get_xid(); h = px(40)
            subprocess.Popen(['xprop', '-id', str(xid), '-f', '_NET_WM_STRUT_PARTIAL', '32c', '-set', '_NET_WM_STRUT_PARTIAL',
                              '0,0,%d,0,0,0,0,0,0,%d,0,0' % (h, self.sw)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e: print('strut', e, file=sys.stderr)
    def _query_layouts(self):
        """Synchronous read of the layout list (short, runs only on a click)."""
        try:
            q = subprocess.run(['setxkbmap', '-query'], capture_output=True, text=True, timeout=3).stdout
            m = re.search(r'layout:\s+(\S+)', q)
            return (m.group(1) if m else 'us').split(',')
        except Exception: return ['us']
    def _log_layout(self, msg):
        try:
            with open(os.path.join(CONF, 'layout.log'), 'a') as f: f.write(time.strftime('%H:%M:%S ') + msg + '\n')
        except Exception: pass
    def _set_label(self, group, layouts):
        code = layouts[min(group, len(layouts) - 1)] if len(layouts) > 1 else ('ara' if self._rtl() else layouts[0])
        self.lay.set_text({'us': 'EN', 'gb': 'EN', 'ara': 'AR', 'ar': 'AR', 'fr': 'FR', 'de': 'DE'}.get(code, code[:2].upper()))
    def toggle_layout(self):
        try:
            import ctypes
            if not hasattr(self, '_x11'): self.poll_layout()
            layouts = self._query_layouts()
            if len(layouts) < 2:
                subprocess.run(['setxkbmap', '-layout', 'us,ara', '-option', 'grp:alt_shift_toggle', '-option', 'grp:win_space_toggle'], timeout=5)
                layouts = self._query_layouts()
            self._layouts = layouts; n = max(1, len(layouts))
            st = self._XkbState(); self._x11.XkbGetState(ctypes.c_void_p(self._dpy), 0x0100, ctypes.byref(st))
            nxt = (st.group + 1) % n
            r = self._x11.XkbLockGroup(ctypes.c_void_p(self._dpy), 0x0100, nxt); self._x11.XFlush(ctypes.c_void_p(self._dpy))
            self._log_layout('click group %s -> %s layouts=%s rc=%s' % (st.group, nxt, layouts, r))
            self._set_label(nxt, layouts)
        except Exception as e:
            self._log_layout('toggle error %r' % (e,)); print('layout', e, file=sys.stderr)
    def _rtl(self):
        try: return Gdk.Keymap.get_for_display(Gdk.Display.get_default()).get_direction() == Pango.Direction.RTL
        except Exception: return False
    def poll_layout(self):
        import ctypes
        try:
            if not hasattr(self, '_x11'):
                import ctypes; self._x11 = ctypes.CDLL('libX11.so.6'); self._x11.XOpenDisplay.restype = ctypes.c_void_p; self._dpy = self._x11.XOpenDisplay(None)
                class XkbState(ctypes.Structure): _fields_ = [('group', ctypes.c_ubyte), ('locked_group', ctypes.c_ubyte), ('base_group', ctypes.c_ushort), ('latched_group', ctypes.c_ushort), ('mods', ctypes.c_ubyte), ('base_mods', ctypes.c_ubyte), ('latched_mods', ctypes.c_ubyte), ('locked_mods', ctypes.c_ubyte), ('compat_state', ctypes.c_ubyte), ('grab_mods', ctypes.c_ubyte), ('compat_grab_mods', ctypes.c_ubyte), ('lookup_mods', ctypes.c_ubyte), ('compat_lookup_mods', ctypes.c_ubyte), ('ptr_buttons', ctypes.c_ushort)]
                self._XkbState = XkbState; self._layouts = None
            self._lp = getattr(self, '_lp', 0) + 1
            if self._layouts is None: self._layouts = ['us']
            if self._lp % 40 == 1:  # refresh the layout list in the background, never block the UI
                def got(q):
                    m = re.search(r'layout:\s+(\S+)', q or ''); self._layouts = (m.group(1) if m else 'us').split(',')
                run_bg(['sh', '-c', 'setxkbmap -query'], got, 3)
            st = self._XkbState(); self._x11.XkbGetState(ctypes.c_void_p(self._dpy), 0x0100, ctypes.byref(st))
            self._set_label(st.group, self._layouts)
        except Exception as e:
            if not getattr(self, '_perr', False): self._perr = True; self._log_layout('poll error %r' % (e,))
        return True
    def tick(self):
        self.clock.set_text(time.strftime('%I:%M %p').lstrip('0') if os.path.exists(os.path.expanduser('~/.config/osborne/12h')) else time.strftime('%H:%M')); self.app.refresh_status(); return True
    def poll_active(self):
        run_bg(['sh', '-c', 'xdotool getactivewindow getwindowclassname 2>/dev/null'], self._act, 2); return True
    def _act(self, cls):
        n = APPNAMES.get(cls.strip(), '')
        self.appl.set_text(n or ('' if not cls.strip() else cls.strip().capitalize()))

# ---------------------------------------------------------------- dock
def focus_or_launch(cls, cmd):
    ids = sh_out("xdotool search --class %s 2>/dev/null | tail -1" % cls)
    if ids.strip(): subprocess.Popen(['xdotool', 'windowactivate', ids.strip()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else: launch(cmd)

DOCK_SIZES = {'small': 0.84, 'medium': 1.0, 'large': 1.22}
# id -> (icon, gradient stops, action, window class for the running dot, label)
BUILTIN = {
    'apps': ('grid', [(0, '#ffc43d'), (1, '#ff9d12')], lambda: launch('osb-apps'), None, 'Apps'),
    'files': ('folder', [(0, '#55abff'), (1, '#0a7cff')], lambda: focus_or_launch('osb-files', 'osb-files'), 'osb-files', 'Files'),
    'browser': ('globe', None, lambda: focus_or_launch('google-chrome', 'google-chrome-stable'), 'google-chrome', 'Browser'),
    'terminal': ('terminal', [(0, '#33343c'), (1, '#16171c')], lambda: focus_or_launch('lxterminal', 'lxterminal'), 'lxterminal', 'Terminal'),
    'calculator': ('calculator', [(0, '#ff8f84'), (1, '#f2616c')], lambda: focus_or_launch('osb-calc', 'osb-calc'), 'osb-calc', 'Calculator'),
    'settings': ('gear', [(0, '#a7acb8'), (1, '#7a7f8c')], lambda: focus_or_launch('osb-settings', 'osb-settings'), 'osb-settings', 'Settings'),
    'store': ('download', [(0, '#5ad2a0'), (1, '#1ea672')], lambda: focus_or_launch('osb-store', 'osb-store'), 'osb-store', 'Software'),
    'monitor': ('monitor', [(0, '#9b86ff'), (1, '#6a4de0')], lambda: focus_or_launch('osb-monitor', 'osb-monitor'), 'osb-monitor', 'System Monitor'),
    'wifi': ('wifi', [(0, '#4cc9f0'), (1, '#1d90d8')], lambda: launch('osb-wifi'), None, 'Wi-Fi'),
    'notes': ('file', [(0, '#ffd166'), (1, '#f0a020')], lambda: launch('mousepad'), None, 'Text Editor'),
}
def app_info(item):
    """item like 'app:firefox.desktop' -> Gio.DesktopAppInfo or None"""
    try: return Gio.DesktopAppInfo.new(item.split(':', 1)[1])
    except Exception: return None
def item_label(item):
    if item in BUILTIN: return BUILTIN[item][4]
    ai = app_info(item); return ai.get_name() if ai else item

# ---- running windows (for the dock)
EXTRAS = []   # [(key, ai or None, label)] running apps that are not pinned
_SKIP_CLS = ('rofi', 'dunst', 'picom', 'lxpolkit', 'polkit', 'xfce4-notifyd', 'conky', 'tint2', 'stalonetray')
_APPMAP = {}
def _build_appmap():
    if _APPMAP: return
    for ai in Gio.AppInfo.get_all():
        try:
            if not ai.should_show(): continue
            did = (ai.get_id() or '').lower()
            keys = [did[:-8] if did.endswith('.desktop') else did]
            try: keys.append((ai.get_startup_wm_class() or '').lower())
            except Exception: pass
            ex = (ai.get_executable() or '').split('/')[-1].lower(); keys.append(ex)
            keys.append((ai.get_name() or '').lower())
            for k in keys:
                if k and k not in _APPMAP: _APPMAP[k] = ai
        except Exception: pass
def match_app(cls, inst):
    _build_appmap()
    for k in (cls, inst, cls.replace('_', '-'), inst.replace('_', '-')):
        if k in _APPMAP: return _APPMAP[k]
    return None
def list_windows():
    out = sh_out("for w in $(xprop -root _NET_CLIENT_LIST 2>/dev/null | sed 's/.*# //; s/,//g'); do echo \"W $w\"; xprop -id $w WM_CLASS _NET_WM_STATE _NET_WM_WINDOW_TYPE _NET_WM_NAME 2>/dev/null; done", timeout=6)
    res = []; cur = None
    for ln in out.splitlines():
        if ln.startswith('W '):
            cur = dict(id=ln[2:].strip(), cls='', inst='', hidden=False, skip=False, title=''); res.append(cur); continue
        if cur is None: continue
        if ln.startswith('WM_CLASS'):
            q = re.findall(r'"([^"]*)"', ln)
            if len(q) >= 2: cur['inst'], cur['cls'] = q[0].lower(), q[1].lower()
        elif ln.startswith('_NET_WM_STATE'):
            cur['hidden'] = 'HIDDEN' in ln
            if 'SKIP_TASKBAR' in ln: cur['skip'] = True
        elif ln.startswith('_NET_WM_WINDOW_TYPE'):
            if re.search(r'DOCK|DESKTOP|NOTIFICATION|MENU|SPLASH|TOOLTIP|POPUP|DROPDOWN|COMBO|UTILITY|DND', ln): cur['skip'] = True
        elif ln.startswith('_NET_WM_NAME'):
            q = re.findall(r'"(.*)"', ln); cur['title'] = q[0] if q else ''
    return [w for w in res if w['cls'] and not w['skip'] and not w['cls'].startswith('osb') and w['cls'] not in _SKIP_CLS]
def win_toggle(wins):
    """Click on a running icon: restore if minimised, minimise if it is already in front, else bring to front."""
    if not wins: return
    try: act = sh_out('xdotool getactivewindow 2>/dev/null').strip()
    except Exception: act = ''
    ids = [w['id'] for w in wins]
    if all(w['hidden'] for w in wins) or act not in ids:
        for w in wins: subprocess.Popen(['xdotool', 'windowactivate', w['id']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        for w in wins: subprocess.Popen(['xdotool', 'windowminimize', w['id']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

class Dock(OsbWindow):
    def __init__(self, app):
        sw, sh = Gdk.Screen.get_default().get_width(), Gdk.Screen.get_default().get_height()
        cfg = self.cfg = load_dock(); k = DOCK_SIZES.get(cfg['size'], 1.0)
        items = [i for i in cfg['items'] if i in BUILTIN or (i.startswith('app:') and app_info(i))] or list(DOCK_DEFAULT['items'])
        T = int(round(42 * k)); G = int(round(8 * k)); self.pinned_n = len(items); self.extras = list(EXTRAS); self.extra_wins = {}; self.pin_wins = {}; self.pin_dots = {}; n = len(items) + len(self.extras); pad = 11
        self.T = T; right = (px(13 + G + 42 * k) if cfg['trash'] else 0)
        cw = px(pad * 2 + n * (T + G) - G) + (px(8 + 1 + 8) + px(42 * k) if cfg['trash'] else 0); ch = px(18 + T)
        m = px(40); super().__init__(cw, ch, m, Gdk.WindowTypeHint.DOCK, 'osb-dock'); self.app = app
        self.move(int((sw - cw) / 2) - m, sh - px(9) - ch - m)
        self.shadow = (22, 8, 26); self.put(Box('dock', cw, ch), 0, 0)
        self.dots = {}
        for i, it in enumerate(items):
            x = px(pad) + i * px(T + G)
            if it in BUILTIN:
                ic, stops, fn, cls, _lab = BUILTIN[it]; self.put(self.tile(ic, stops, fn, T, it), x, px(9))
                if cls:
                    dot = Gtk.DrawingArea(); dot.set_size_request(px(5), px(5)); dot.on = False
                    dot.connect('draw', lambda w, cr: ((cr.arc(px(2.5), px(2.5), px(2.2), 0, 6.3), cr.set_source_rgba(*hex2rgb(pal('bar'))), cr.fill()) if w.on else None, False)[-1])
                    self.put(dot, x + px(T / 2.0) - px(2), px(9 + T + 3)); self.dots[cls] = dot
            else:
                self.put(self.app_tile(app_info(it), T, it), x, px(9)); self.pin_dot(it, x, T)
        for j, (key, ai, lab) in enumerate(self.extras):
            x = px(pad) + (len(items) + j) * px(T + G)
            self.put(self.run_tile(key, ai, lab, T), x, px(9)); self.pin_dot(key, x, T, extra=True)
        if cfg['trash']:
            sx = px(pad) + n * px(T + G) - px(G) + px(8)
            self.put(Box('rowline', max(1, px(1)), px(T * 0.8)), sx, px(9 + T * 0.1))
            t = Gtk.DrawingArea(); t.set_size_request(px(T), px(T)); t.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            def dt(w, cr, T=T):
                rounded_rect(cr, 0, 0, px(T), px(T), px(14)); cr.set_source_rgba(*hex2rgb(pal('trash'))); cr.fill()
                draw_icon(cr, 'trash', px(T * 0.21), px(T * 0.21), px(T * 0.57), pal('trashicon'), 1.7); return False
            t.connect('draw', dt); t.connect('button-press-event', lambda *a: launch('osb-files --trash')); self.put(t, sx + px(9), px(9))
        self._poll_id = GLib.timeout_add(2500, self.poll); self.connect('destroy', lambda *a: (GLib.source_remove(self._poll_id) if self._poll_id else None, setattr(self, '_poll_id', 0), setattr(self, '_dead', True))); self.poll()
    def item_menu(self, item, e):
        """Right-click menu of a dock icon."""
        m = new_menu(); self.app.menu_open = True; d = load_dock(); its = d['items']; i = its.index(item) if item in its else -1
        def save(): save_json(DOCKFILE, d)
        def do_open():
            if item in BUILTIN: BUILTIN[item][2]()
            else:
                ai = app_info(item)
                if ai: ai.launch([], None)
        def move(delta):
            j = i + delta
            if 0 <= i and 0 <= j < len(its): its[i], its[j] = its[j], its[i]; save()
        def remove():
            if len(its) > 1 and i >= 0: its.pop(i); save()
        entries = [('Open', do_open, True)]
        entries += [('Move left', lambda: move(-1), i > 0), ('Move right', lambda: move(1), 0 <= i < len(its) - 1), ('Remove from dock', remove, len(its) > 1)]
        for lab, fn, ok in entries:
            it = Gtk.MenuItem(label=T(lab)); it.set_sensitive(ok); it.connect('activate', lambda w, f=fn: f()); m.append(it)
            if lab == entries[0][0]: m.append(Gtk.SeparatorMenuItem())
        m.append(Gtk.SeparatorMenuItem())
        it = Gtk.MenuItem(label=T('Dock settings…')); it.connect('activate', lambda w: launch(['osb-settings', 'customize'])); m.append(it)
        m.connect('hide', lambda *a: setattr(self.app, 'menu_open', False)); m.show_all(); m.popup_at_pointer(e)
    def run_menu(self, key, ai, label, e):
        """Right-click menu of a running (unpinned) app: pin it to the dock, or close it."""
        m = new_menu(); self.app.menu_open = True
        def pin():
            d = load_dock(); it = 'app:' + ai.get_id()
            if it not in d['items']: d['items'].append(it); save_json(DOCKFILE, d)
        def close():
            for w in self.extra_wins.get(key, []): subprocess.Popen(['xdotool', 'windowquit', w['id']], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        def show():
            win_toggle(self.extra_wins.get(key, []))
        for lab, fn, ok in [('Show', show, True), ('Pin to dock', pin, ai is not None), ('Close', close, True)]:
            it = Gtk.MenuItem(label=T(lab)); it.set_sensitive(ok); it.connect('activate', lambda w, f=fn: f()); m.append(it)
        m.connect('hide', lambda *a: setattr(self.app, 'menu_open', False)); m.show_all(); m.popup_at_pointer(e)
    def pin_dot(self, key, x, T, extra=False):
        dot = Gtk.DrawingArea(); dot.set_size_request(px(5), px(5)); dot.on = extra
        dot.connect('draw', lambda w, cr: ((cr.arc(px(2.5), px(2.5), px(2.2), 0, 6.3), cr.set_source_rgba(*hex2rgb(pal('bar'))), cr.fill()) if w.on else None, False)[-1])
        self.put(dot, x + px(T / 2.0) - px(2), px(9 + T + 3)); self.pin_dots[key] = dot
    def poll(self):
        if getattr(self, '_dead', False): return False
        def work():
            res = {cls: bool(sh_out("xdotool search --class %s 2>/dev/null | head -1" % cls)) for cls in self.dots}
            try: wins = list_windows()
            except Exception: wins = []
            GLib.idle_add(self.apply_poll, res, wins)
        threading.Thread(target=work, daemon=True).start(); return True
    def apply_poll(self, res, wins):
        if getattr(self, '_dead', False) or self.app.dock is not self: return False
        for cls, on in res.items():
            d = self.dots[cls]
            if d.on != on: d.on = on; d.queue_draw()
        pinned = set(self.cfg['items']); pw = {}; ew = {}; labs = {}; ais = {}
        for w in wins:
            ai = match_app(w['cls'], w['inst'])
            item = ('app:' + ai.get_id()) if ai else None
            if item and item in pinned: pw.setdefault(item, []).append(w); continue
            if any(BUILTIN[b][3] and BUILTIN[b][3] in (w['cls'], w['inst']) for b in BUILTIN): continue
            key = ai.get_id() if ai else 'cls:' + w['cls']
            ew.setdefault(key, []).append(w); ais[key] = ai; labs.setdefault(key, ai.get_name() if ai else (w['title'] or w['cls']))
        self.pin_wins = pw; self.extra_wins = ew
        ex = [e[0] for e in self.extras]
        for item, d in self.pin_dots.items():
            on = (item in ew) if item in ex else (item in pw)
            if d.on != on: d.on = on; d.queue_draw()
        new = [(k, ais[k], labs[k]) for k in ew]
        if [e[0] for e in new] != [e[0] for e in self.extras]:
            global EXTRAS
            EXTRAS = new; GLib.idle_add(self.app.rebuild_dock)
        return False
    def run_tile(self, key, ai, lab, T=42):
        d = self.app_tile(ai, T, None, key=key, label=lab)
        return d
    def tile(self, ic, stops, fn, T=42, item=None):
        d = Gtk.DrawingArea(); sz = px(T); d.set_size_request(sz, sz); d.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        def draw(w, cr):
            if ic == 'globe': rainbow_tile(cr, sz, sz, px(14))
            else: gradient_tile(cr, sz, sz, px(14), stops, 160)
            draw_icon(cr, ic, sz * 0.21, sz * 0.21, sz * 0.57, '#ffffff', 1.7); return False
        d.connect('draw', draw); d.connect('button-press-event', lambda w, e: (fn(), True)[-1] if e.button == 1 else (self.item_menu(item, e), True)[-1]); return d
    def app_tile(self, ai, T=42, item=None, key=None, label=''):
        d = Gtk.DrawingArea(); sz = px(T); d.set_size_request(sz, sz); d.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pb = [None]
        def load():
            try:
                ic = ai.get_icon(); info = Gtk.IconTheme.get_default().lookup_by_gicon(ic, int(sz * 0.7), Gtk.IconLookupFlags.FORCE_SIZE) if ic else None
                pb[0] = info.load_icon() if info else None
            except Exception: pb[0] = None
        load()
        def draw(w, cr):
            rounded_rect(cr, 0, 0, sz, sz, px(14)); cr.set_source_rgba(*hex2rgb(pal('trash'))); cr.fill()
            if pb[0]: Gdk.cairo_set_source_pixbuf(cr, pb[0], (sz - pb[0].get_width()) / 2.0, (sz - pb[0].get_height()) / 2.0); cr.paint()
            else:
                cr.select_font_face('Sans', 0, 1); cr.set_font_size(sz * 0.46); cr.set_source_rgba(*hex2rgb(pal('text')))
                ch = (label or '?')[:1].upper(); ext = cr.text_extents(ch); cr.move_to((sz - ext.width) / 2.0 - ext.x_bearing, (sz + ext.height) / 2.0); cr.show_text(ch)
            return False
        def click(w, e):
            if key is not None:
                if e.button == 1: win_toggle(self.extra_wins.get(key, []))
                else: self.run_menu(key, ai, label, e)
            elif e.button == 1:
                ws = self.pin_wins.get(item)
                if ws: win_toggle(ws)
                elif ai: ai.launch([], None)
            else: self.item_menu(item, e)
            return True
        d.connect('draw', draw); d.connect('button-press-event', click); return d

# ---------------------------------------------------------------- quick settings
QS_DY = 55
class QuickSettings(OsbWindow):
    def put(self, w, x, y):
        if getattr(self, '_shift', False) and y >= px(110): y += px(QS_DY)
        return super().put(w, x, y)
    def __init__(self, app):
        sw = Gdk.Screen.get_default().get_width()
        cw, ch = px(280), px(342 + QS_DY); m = px(50); self._shift = False
        super().__init__(cw, ch, m, None, 'osb-quicksettings'); self.app = app
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY); self.set_keep_above(True)
        self.move(sw - px(95) - cw - m, px(54) - m)
        self.shadow = (26, 14, 34); self.put(Box('panel', cw, ch), 0, 0)
        name, ini = user_names()
        self.av = Avatar(px(34)); self.put(self.av, px(18), px(18))
        self.nm = make_label(name, 12, 'semibold', 'text', w=px(150), h=px(18)); self.put(self.nm, px(61), px(19))
        pfev = Gtk.EventBox(); pfev.set_visible_window(False); pfev.set_size_request(px(150), px(38)); pfev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pfev.connect('button-press-event', lambda *a: (launch(['osb-settings', 'profile']), app.qs.hide(), True)[-1]); self.put(pfev, px(14), px(14))
        def _prof():
            n = display_name(); self.nm.set_text(n); self.av.name = n; self.av.refresh()
        watch_profile(_prof)
        self.put(make_label('Available', 9, 'normal', 'green', w=px(100), h=px(14)), px(61), px(35))
        gear = Icon('gear', px(19), 'muted', 1.5); self.put(gear, px(237), px(25))
        pw = Icon('power', px(19), 'muted', 1.5); self.put(pw, px(207), px(25))
        pwev = Gtk.EventBox(); pwev.set_visible_window(False); pwev.set_size_request(px(30), px(30)); pwev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pwev.connect('button-press-event', lambda *a: (launch('osb-power'), app.qs.hide(), True)[-1]); self.put(pwev, px(201), px(20))
        gev = Gtk.EventBox(); gev.set_visible_window(False); gev.set_size_request(px(30), px(30)); gev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        gev.connect('button-press-event', lambda *a: (launch('osb-settings'), app.qs.hide(), True)[-1]); self.put(gev, px(231), px(20))
        # tiles
        self.wifi_state = (True, 'Nova Home'); self.bt_state = (True, 'On')
        self.wifi_sub = make_label('', 8, 'normal', 'muted', w=px(70), h=px(12)); self.bt_sub = make_label('', 8, 'normal', 'muted', w=px(70), h=px(12))
        self.tile(18, 65, 119, 'wifi', 'Wi-Fi', self.wifi_sub, app.toggle_wifi, app.wifi_menu)
        self.tile(145, 65, 119, 'bluetooth', 'Bluetooth', self.bt_sub, app.toggle_bt, app.bt_menu)
        self.dnd_sub = make_label('Off', 8, 'normal', 'muted', w=px(70), h=px(12)); self.night_sub = make_label('Off', 8, 'normal', 'muted', w=px(70), h=px(12))
        self.tile(18, 120, 119, 'bell', 'Quiet', self.dnd_sub, app.toggle_dnd, lambda e: launch('osb-settings'))
        self.tile(145, 120, 119, 'moon', 'Night light', self.night_sub, app.toggle_night, lambda e: launch('osb-settings display'))
        self._shift = True
        # sliders
        self.row(18, 119, 40, 'sun', app.brightness, app.set_brightness, 'bright')
        self.row(18, 167, 40, 'volume', app.volume, app.set_volume, 'vol')
        # appearance
        self.put(Box('qsrow', px(246), px(41)), px(18), px(216))
        self.app_icon = Icon('sun', px(18), 'text', 1.5); self.put(self.app_icon, px(26), px(227))
        self.put(make_label('Appearance', 10, 'semibold', 'text', w=px(110), h=px(16)), px(52), px(228))
        self.put(Box('seg', px(60), px(28)), px(196), px(223))
        self.segact = Box('segact', px(29), px(26)); self.put(self.segact, px(198), px(224))
        self.sun_i = Icon('sun', px(15), 'primary', 1.7); self.moon_i = Icon('moon', px(15), 'muted', 1.7)
        self.put(self.sun_i, px(205), px(229)); self.put(self.moon_i, px(233), px(229))
        for x, mode in ((198, 'light'), (227, 'dark')):
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(29), px(26)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, m=mode: app.set_appearance(m)); self.put(ev, px(x), px(224))
        # player
        self.put(Box('player', px(248), px(61)), px(16), px(266))
        self.put(Box('art', px(40), px(40)), px(24), px(276))
        self.art_bars = Gtk.DrawingArea(); self.art_bars.set_size_request(px(40), px(40))
        def bars(w, cr):
            cr.set_source_rgba(1, 1, 1, 0.95)
            for x, y0, y1 in ((12, 11, 29), (19, 13, 31), (26, 17, 27)):
                rounded_rect(cr, px(x), px(y0), px(3), px(y1 - y0), px(1.5)); cr.fill()
            return False
        self.art_bars.connect('draw', bars); self.put(self.art_bars, px(24), px(276))
        self.title = make_label('Nothing playing', 10, 'semibold', '#ffffff', w=px(130), h=px(15)); self.put(self.title, px(76), px(284))
        self.artist = make_label('Play music in any app', 8, 'normal', '#a9afc3', w=px(130), h=px(12)); self.put(self.artist, px(76), px(299))
        self.prog = Gtk.DrawingArea(); self.prog.set_size_request(px(146), px(3)); self.prog.frac = 0.0
        def pg(w, cr):
            rounded_rect(cr, 0, 0, px(146), px(2.4), px(1.2)); cr.set_source_rgba(1, 1, 1, 0.25); cr.fill()
            rounded_rect(cr, 0, 0, px(146) * self.prog.frac, px(2.4), px(1.2)); cr.set_source_rgba(1, 1, 1, 0.95); cr.fill(); return False
        self.prog.connect('draw', pg); self.put(self.prog, px(76), px(310))
        self.pico = Icon('play', px(18), '#ffffff', 1.5); self.put(self.pico, px(235), px(287))
        pev = Gtk.EventBox(); pev.set_visible_window(False); pev.set_size_request(px(30), px(30)); pev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pev.connect('button-press-event', lambda *a: (launch('playerctl play-pause'), GLib.timeout_add(450, lambda: (self.refresh_player(), False)[-1]), True)[-1]); self.put(pev, px(229), px(281))
        GLib.timeout_add_seconds(2, lambda: (self.refresh_player() if self.get_visible() else None, True)[-1])
        self.connect('focus-out-event', self._focus_out); self.set_appearance_ui(State.mode)
    def refresh_player(self):
        run_bg(['playerctl', 'metadata', '--format', '{{status}}|{{title}}|{{artist}}|{{position}}|{{mpris:length}}'], self._player_cb, 2)
    def _player_cb(self, out):
        p = out.split('|') if out else []
        if len(p) < 5 or not p[1]:
            self.title.set_text('Nothing playing'); self.artist.set_text('Play music in any app'); self.pico.set_name_('play'); self.prog.frac = 0.0; self.prog.queue_draw(); return
        self.title.set_text(p[1][:40]); self.artist.set_text((p[2] or 'Unknown artist')[:40]); self.pico.set_name_('pause' if p[0] == 'Playing' else 'play')
        try: self.prog.frac = max(0.0, min(1.0, float(p[3]) / float(p[4])))
        except Exception: self.prog.frac = 0.0
        self.prog.queue_draw()
    def tile(self, x, y, w, ic, title, sub, on_click, on_right):
        self.put(Box('qstile', px(w), px(47)), px(x), px(y)); self.put(Box('qsicon', px(29), px(29)), px(x + 7), px(y + 9))
        self.put(Icon(ic, px(17), '#ffffff', 1.7), px(x + 13), px(y + 15))
        self.put(make_label(title, 10, 'semibold', 'text', w=px(70), h=px(15)), px(x + 44), px(y + 10))
        self.put(sub, px(x + 44), px(y + 25))
        ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(w), px(47)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        def pr(wd, e):
            if e.button == 3 or e.x > px(44): on_right(e)
            else: on_click()
            return True
        ev.connect('button-press-event', pr); self.put(ev, px(x), px(y))
    def row(self, x, y, h, ic, val, cb, key):
        self.put(Box('qsrow', px(246), px(h)), px(x), px(y))
        self.put(Icon(ic, px(17), 'iconmuted', 1.5), px(x + 9), px(y + 11))
        sl = Slider(px(162), val, cb, (lambda v: beep()) if key == 'vol' else None); self.put(sl, px(x + 36), px(y + 10))
        lab = make_label('%d%%' % round(val * 100), 8, 'normal', 'muted', xalign=1.0, w=px(34), h=px(14)); self.put(lab, px(x + 207), px(y + 13))
        setattr(self, key + '_slider', sl); setattr(self, key + '_label', lab)
    def place(self):
        sw = Gdk.Screen.get_default().get_width()
        self.move(sw - px(95) - self.cw - self.M, px(54) - self.M); return False
    def set_appearance_ui(self, mode):
        self.app_icon.set_name_('sun' if mode == 'light' else 'moon')
        self.content.move(self.segact, px(198 if mode == 'light' else 227), px(224 + QS_DY))
        self.sun_i.color = 'primary' if mode == 'light' else 'muted'; self.moon_i.color = 'primary' if mode == 'dark' else 'muted'
        self.sun_i.queue_draw(); self.moon_i.queue_draw()
    def _focus_out(self, *a):
        GLib.timeout_add(120, self._maybe_hide); return False
    def _maybe_hide(self):
        if not self.is_active() and not self.app.menu_open: self.hide()
        return False

# ---------------------------------------------------------------- app
class ShellApp:
    def __init__(self):
        init_mode(); self.menu_open = False
        self.brightness = self.read_brightness(); self.volume = self.read_volume()
        self.wall = Wallpaper(); self.bar = TopBar(self); self.dock = Dock(self); self.qs = QuickSettings(self)
        for w in (self.wall, self.bar, self.dock): w.show_all()
        self.wall.show_all(); self.refresh_status()
        watch_mode(self._mode_from_file)
        from . import sysconf
        def sysinit():
            try: sysconf.apply_touchpad(); sysconf.apply_power(); sysconf.apply_night()
            except Exception as ex: print('sysinit', ex, file=sys.stderr)
            return False
        GLib.timeout_add(1500, sysinit); GLib.timeout_add_seconds(60, lambda: (sysconf.apply_night(), True)[-1])
        watch_conf('nightlight.json', lambda: (sysconf.apply_night(), self.refresh_status()))
        watch_conf('touchpad.json', sysconf.apply_touchpad); watch_conf('power.json', sysconf.apply_power)
        watch_conf('lang', lambda: os.execv(sys.executable, [sys.executable] + sys.argv))
        watch_conf('dock.json', self.rebuild_dock); watch_conf('topbar.json', self.rebuild_bar); watch_conf('accent', self.accent_changed)
        GLib.timeout_add(2500, lambda: ([launch(['osb-clip']), launch(['osb-widgets'])], False)[-1])
        self._fs_paused = False; GLib.timeout_add_seconds(3, self.fullscreen_check)
        from . import upkeep, reopen
        self.reopen = reopen.Tracker(); GLib.timeout_add_seconds(2, lambda: (self.reopen.run_async(), True)[-1])
        GLib.timeout_add_seconds(120, lambda: (threading.Thread(target=upkeep.check_updates, daemon=True).start(), True)[-1])
        GLib.timeout_add_seconds(6 * 3600, lambda: (threading.Thread(target=upkeep.check_updates, daemon=True).start(), True)[-1])
        GLib.timeout_add_seconds(600, lambda: (threading.Thread(target=upkeep.flatpak_update_daily, daemon=True).start(), True)[-1])
        self.net_last = None; GLib.timeout_add_seconds(30, self.net_usage); GLib.timeout_add_seconds(75, lambda: (self.update_check(), False)[-1]); GLib.timeout_add_seconds(6 * 3600, lambda: (self.update_check(), True)[-1])
    def fullscreen_check(self):
        """Pause notifications while a window is full screen; resume when it leaves full screen."""
        if os.path.exists(os.path.join(CONF, 'nopresent')): return True
        def work():
            wid = sh_out('xdotool getactivewindow 2>/dev/null').strip()
            fs = bool(wid) and 'FULLSCREEN' in sh_out('xprop -id %s _NET_WM_STATE 2>/dev/null' % wid)
            GLib.idle_add(self._apply_fs, fs)
        threading.Thread(target=work, daemon=True).start(); return True
    def _apply_fs(self, fs):
        if fs and not self._fs_paused:
            self._fs_paused = True; subprocess.run(['dunstctl', 'set-paused', 'true'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif not fs and self._fs_paused:
            self._fs_paused = False; subprocess.run(['dunstctl', 'set-paused', 'false'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return False
    def net_usage(self):
        """Count the bytes used per day (shown in Settings > Network)."""
        try:
            rx = tx = 0
            for ln in list(open('/proc/net/dev'))[2:]:
                n, d = ln.split(':', 1)
                if n.strip() == 'lo' or n.strip().startswith(('docker', 'veth', 'virbr')): continue
                f = d.split(); rx += int(f[0]); tx += int(f[8])
            if self.net_last and rx >= self.net_last[0] and tx >= self.net_last[1]:
                p = os.path.join(CONF, 'netusage.json'); day = time.strftime('%Y-%m-%d')
                try: d = json.load(open(p))
                except Exception: d = {}
                a = d.get(day, [0, 0]); d[day] = [a[0] + rx - self.net_last[0], a[1] + tx - self.net_last[1]]
                for k in sorted(d)[:-70]: d.pop(k, None)
                save_json(p, d)
            self.net_last = (rx, tx)
        except Exception as ex: print('netusage', ex, file=sys.stderr)
        return True
    def update_check(self):
        """Tell the user once when a new version is on GitHub. It only looks; nothing is downloaded."""
        if os.path.exists(os.path.join(CONF, 'noupdatecheck')): return
        def work():
            import urllib.request
            try:
                with urllib.request.urlopen(urllib.request.Request('https://api.github.com/repos/tareknahas85-star/Osborne-OS/commits/main', headers={'User-Agent': 'osborne'}), timeout=15) as r: sha = json.load(r)['sha']
                cur = open('/usr/local/lib/osborne/version').read().strip() if os.path.exists('/usr/local/lib/osborne/version') else ''
                seen = os.path.join(CONF, 'update-notified'); last = open(seen).read().strip() if os.path.exists(seen) else ''
                if sha != cur and sha != last:
                    open(seen, 'w').write(sha)
                    subprocess.Popen(['notify-send', '-a', 'Osborne', T('A new Osborne update is available'), T('Open Settings > System Update to install it.')])
            except Exception: pass
        threading.Thread(target=work, daemon=True).start()
    def rebuild_dock(self):
        old = self.dock; self.dock = Dock(self); self.dock.show_all(); old.destroy()
    def rebuild_bar(self):
        old = self.bar; self.bar = TopBar(self); self.bar.show_all(); old.destroy(); self.refresh_status()
    def accent_changed(self):
        apply_accent(); apply_css(State.mode); restyle_labels(); launch(['osb-apply-theme', State.mode])
        for w in (self.wall, self.bar, self.dock, self.qs): w.queue_draw()
    def _mode_from_file(self, mode):
        # theme was changed by another process (e.g. Settings) -> repaint the whole shell exactly like the clock toggle
        for w in (self.wall, self.bar, self.dock, self.qs): w.queue_draw()
        self.wall.refresh(); self.qs.set_appearance_ui(mode)
    # -- system state
    def read_brightness(self):
        out = sh_out('osb-brightness get 2>/dev/null')
        try: return max(0.05, min(1.0, float(out) / 100.0))
        except Exception: return 1.0
    def read_volume(self):
        out = sh_out('wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null')
        try: return min(1.0, float(out.split()[1]))
        except Exception: return 0.68
    def set_brightness(self, v):
        self.brightness = v; self.qs.bright_label.set_text('%d%%' % round(v * 100))
        launch(['osb-brightness', 'set', '%d' % max(5, round(v * 100))])
    def set_volume(self, v):
        self.volume = v; self.qs.vol_label.set_text('%d%%' % round(v * 100))
        launch(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '%.2f' % v])
    def refresh_status(self):
        try:
            from . import sysconf
            self.qs.night_sub.set_text({'off': 'Off', 'on': 'On', 'auto': 'Evening'}[sysconf.get_night()['mode']])
        except Exception: pass
        run_bg(['sh', '-c', 'dunstctl is-paused 2>/dev/null'], lambda o: self.qs.dnd_sub.set_text('On' if o.strip() == 'true' else 'Off'), 3)
        def wf(out):
            on = 'enabled' in out and 'disabled' not in out
            self.qs.wifi_state = (on, self.qs.wifi_state[1])
            run_bg(['sh', '-c', "nmcli -t -f active,ssid dev wifi 2>/dev/null | grep '^yes' | head -1 | cut -d: -f2"],
                   lambda s: self.qs.wifi_sub.set_text(s if on and s else ('Off' if not on else 'Not connected')), 3)
        run_bg(['nmcli', 'radio', 'wifi'], wf, 3)
        run_bg(['sh', '-c', "bluetoothctl show 2>/dev/null | grep -i 'Powered' | awk '{print $2}'"],
               lambda s: self.qs.bt_sub.set_text('On' if s.strip() == 'yes' else ('Off' if s.strip() == 'no' else 'Unavailable')), 3)
    def toggle_qs(self):
        if self.qs.get_visible(): self.qs.hide()
        else:
            self.qs.show_all(); self.qs.present(); self.refresh_status(); self.qs.refresh_player()
            for d in (30, 150): GLib.timeout_add(d, self.qs.place)
    def toggle_dnd(self):
        run_bg(['sh', '-c', "dunstctl is-paused | grep -q true && dunstctl set-paused false || dunstctl set-paused true"], lambda o: self.refresh_status(), 4)
    def toggle_night(self):
        from . import sysconf
        d = sysconf.get_night(); d['mode'] = 'off' if d['mode'] != 'off' else 'on'; sysconf.set_night(d); sysconf.apply_night(); self.refresh_status()
    def toggle_wifi(self):
        run_bg(['sh', '-c', "nmcli radio wifi | grep -q '^enabled' && nmcli radio wifi off || nmcli radio wifi on; rfkill unblock wifi 2>/dev/null"], lambda o: self.refresh_status(), 5)
    def toggle_bt(self):
        run_bg(['sh', '-c', "rfkill unblock bluetooth 2>/dev/null; bluetoothctl show | grep -q 'Powered: yes' && bluetoothctl power off || bluetoothctl power on"], lambda o: self.refresh_status(), 6)
    def wifi_menu(self, e): launch('osb-settings wifi')
    def bt_menu(self, e): launch('osb-settings bluetooth')
    def set_appearance(self, mode):
        State.mode = mode; set_mode(mode); apply_css(mode); restyle_labels()
        for w in (self.wall, self.bar, self.dock, self.qs):
            w.queue_draw()
        self.wall.refresh(); self.qs.set_appearance_ui(mode)
        launch(['osb-apply-theme', mode])
    def show_calendar(self):
        win = Gtk.Window(title='Calendar'); win.set_default_size(300, 300); cal = Gtk.Calendar(); win.add(cal); win.show_all()
    def show_settings_menu(self):
        m = new_menu(); self.menu_open = True
        for label, cmd in (('Network', 'nm-connection-editor'), ('Wi-Fi networks', 'osb-wifi'), ('Bluetooth', 'blueman-manager'),
                           ('Sound', 'pavucontrol'), ('Appearance', 'lxappearance'), ('Terminal', 'lxterminal')):
            it = Gtk.MenuItem(label=T(label)); it.connect('activate', lambda w, c=cmd: launch(c)); m.append(it)
        m.connect('hide', lambda *a: setattr(self, 'menu_open', False)); m.show_all(); m.popup_at_pointer(None)

def main():
    app = ShellApp(); Gtk.main()
