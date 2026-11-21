"""osb-shell: wallpaper + top bar + dock + quick settings (HeroUI 'Linux Desktop' design)."""
import os, sys, re, time, subprocess, threading, getpass, pwd, ctypes
import gi
gi.require_version('GdkX11','3.0')
from gi.repository import GdkX11
from .common import *

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
    try: full = pwd.getpwnam(getpass.getuser()).pw_gecos.split(',')[0] or getpass.getuser()
    except Exception: full = getpass.getuser()
    name = full.strip() or getpass.getuser()
    name = name[:1].upper() + name[1:]
    parts = name.split(); ini = (parts[0][0] + (parts[1][0] if len(parts) > 1 else parts[0][1:2] or '')).upper()
    return name, ini

# ---------------------------------------------------------------- wallpaper
class Wallpaper(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL); scr = Gdk.Screen.get_default()
        self.w, self.h = scr.get_width(), scr.get_height()
        self.set_type_hint(Gdk.WindowTypeHint.DESKTOP); self.set_decorated(False); self.set_title('osb-wallpaper')
        self.set_default_size(self.w, self.h); self.move(0, 0); self.set_skip_taskbar_hint(True)
        self.da = Gtk.DrawingArea(); self.add(self.da); self.da.connect('draw', self._d); self.surf = None; self.surf_mode = None; watch_wall(lambda: self.da.queue_draw())
    def _d(self, wd, cr):
        key = (State.mode, get_wall())
        if self.surf_mode != key: self.surf = render_wall(self.w, self.h, State.mode); self.surf_mode = key
        cr.set_source_surface(self.surf, 0, 0); cr.paint(); return False
    def refresh(self): self.da.queue_draw()

# ---------------------------------------------------------------- top bar
APPNAMES = {'osb-files': 'Files', 'Osb-files': 'Files', 'firefox': 'Firefox', 'Firefox': 'Firefox', 'lxterminal': 'Terminal',
            'Lxterminal': 'Terminal', 'mousepad': 'Text Editor', 'Mousepad': 'Text Editor', 'pavucontrol': 'Sound', 'Pavucontrol': 'Sound', 'Osb-settings': 'Settings', 'Osb-calc': 'Calculator', 'Osb-wifi': 'Wi-Fi', 'Osb-monitor': 'System Monitor', 'Osb-power': 'Power'}
class TopBar(OsbWindow):
    def __init__(self, app):
        sw = Gdk.Screen.get_default().get_width()
        super().__init__(sw, px(40), 0, Gdk.WindowTypeHint.DOCK, 'osb-topbar'); self.app = app; self.sw = sw
        self.move(0, 0)
        self.put(Icon('logo', px(26), 'bar'), px(16), px(7))
        act = make_label('Activities', 13, 'semibold', 'text', w=px(80), h=px(20)); self.put(act, px(54), px(10))
        self.appl = make_label('Files', 13, 'medium', 'muted', w=px(140), h=px(20)); self.put(self.appl, px(127), px(10))
        self.wifi = Icon('wifi', px(17), 'text', 1.6); self.vol = Icon('volume', px(17), 'text', 1.6); self.bat = Icon('battery', px(17), 'text', 1.6)
        self.clock = make_label('00:00', 13, 'medium', 'text', xalign=0.0, w=px(62), h=px(20))
        self.chev = Icon('chev-d', px(14), 'text', 1.8)
        x = sw - px(262)
        self.pw = Icon('power', px(17), 'text', 1.7); self.put(self.pw, sw - px(36), px(11))
        pev = Gtk.EventBox(); pev.set_visible_window(False); pev.set_size_request(px(32), px(40)); pev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pev.connect('button-press-event', lambda *a: (launch('osb-power'), True)[-1]); self.put(pev, sw - px(42), 0)
        self.lay = make_label('EN', 11.5, 'semibold', 'text', xalign=0.5, w=px(30), h=px(20)); self.put(self.lay, x, px(10))
        lev = Gtk.EventBox(); lev.set_visible_window(False); lev.set_size_request(px(34), px(40)); lev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        lev.connect('button-press-event', lambda *a: (launch('xdotool key ISO_Next_Group'), True)[-1]); self.put(lev, x - px(2), 0)
        self.bell = Icon('bell', px(17), 'text', 1.6); self.put(self.bell, x + px(38), px(11))
        bev = Gtk.EventBox(); bev.set_visible_window(False); bev.set_size_request(px(30), px(40)); bev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        bev.connect('button-press-event', lambda *a: (launch('osb-notifs'), True)[-1]); self.put(bev, x + px(33), 0)
        x += px(68)
        self.put(self.wifi, x, px(11)); self.put(self.vol, x + px(28), px(11)); self.put(self.bat, x + px(54), px(11))
        self.put(self.clock, x + px(75), px(10)); self.put(self.chev, x + px(133), px(13))
        # click area over the tray -> quick settings
        ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(160), px(40)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        ev.connect('button-press-event', lambda *a: app.toggle_qs()); self.put(ev, x - px(10), 0)
        aev = Gtk.EventBox(); aev.set_visible_window(False); aev.set_size_request(px(80), px(40)); aev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        aev.connect('button-press-event', lambda *a: launch('osb-apps')); self.put(aev, px(54), 0)
        self.connect('realize', self._strut); self.poll_layout(); GLib.timeout_add(600, self.poll_layout); self.tick(); GLib.timeout_add_seconds(15, self.tick); GLib.timeout_add(1500, self.poll_active)
    def _strut(self, *_):
        try:
            xid = self.get_window().get_xid(); h = px(40)
            subprocess.Popen(['xprop', '-id', str(xid), '-f', '_NET_WM_STRUT_PARTIAL', '32c', '-set', '_NET_WM_STRUT_PARTIAL',
                              '0,0,%d,0,0,0,0,0,0,%d,0,0' % (h, self.sw)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e: print('strut', e, file=sys.stderr)
    def poll_layout(self):
        try:
            if not hasattr(self, '_x11'):
                import ctypes; self._x11 = ctypes.CDLL('libX11.so.6'); self._x11.XOpenDisplay.restype = ctypes.c_void_p; self._dpy = self._x11.XOpenDisplay(None)
                class XkbState(ctypes.Structure): _fields_ = [('group', ctypes.c_ubyte), ('locked_group', ctypes.c_ubyte), ('base_group', ctypes.c_ushort), ('latched_group', ctypes.c_ushort), ('mods', ctypes.c_ubyte), ('base_mods', ctypes.c_ubyte), ('latched_mods', ctypes.c_ubyte), ('locked_mods', ctypes.c_ubyte), ('compat_state', ctypes.c_ubyte), ('grab_mods', ctypes.c_ubyte), ('compat_grab_mods', ctypes.c_ubyte), ('lookup_mods', ctypes.c_ubyte), ('compat_lookup_mods', ctypes.c_ubyte), ('ptr_buttons', ctypes.c_ushort)]
                self._XkbState = XkbState; self._layouts = None
            if self._layouts is None or int(time.time()) % 20 == 0:
                q = sh_out('setxkbmap -query'); m = re.search(r'layout:\s+(\S+)', q); self._layouts = (m.group(1) if m else 'us').split(',')
            st = self._XkbState(); self._x11.XkbGetState(ctypes.c_void_p(self._dpy), 0x0100, ctypes.byref(st))
            code = self._layouts[min(st.group, len(self._layouts) - 1)]; self.lay.set_text({'us': 'EN', 'ar': 'AR', 'gb': 'EN', 'fr': 'FR', 'de': 'DE'}.get(code, code[:2].upper()))
        except Exception as e: pass
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

class Dock(OsbWindow):
    def __init__(self, app):
        sw, sh = Gdk.Screen.get_default().get_width(), Gdk.Screen.get_default().get_height()
        cw, ch = px(376), px(60); m = px(40)
        super().__init__(cw, ch, m, Gdk.WindowTypeHint.DOCK, 'osb-dock'); self.app = app
        self.move(int((sw - cw) / 2) - m, sh - px(9) - ch - m)
        self.shadow = (22, 8, 26); self.put(Box('dock', cw, ch), 0, 0)
        specs = [('grid', [(0, '#ffc43d'), (1, '#ff9d12')], lambda: launch('osb-apps'), None),
                 ('folder', [(0, '#55abff'), (1, '#0a7cff')], lambda: focus_or_launch('osb-files', 'osb-files'), 'osb-files'),
                 ('globe', None, lambda: focus_or_launch('firefox', 'firefox'), 'firefox'),
                 ('terminal', [(0, '#33343c'), (1, '#16171c')], lambda: focus_or_launch('lxterminal', 'lxterminal'), 'lxterminal'),
                 ('calendar', [(0, '#ff8f84'), (1, '#f2616c')], lambda: focus_or_launch('osb-calc', 'osb-calc'), 'osb-calc'),
                 ('gear', [(0, '#a7acb8'), (1, '#7a7f8c')], lambda: focus_or_launch('osb-settings', 'osb-settings'), 'osb-settings')]
        self.dots = {}
        for i, (ic, stops, fn, cls) in enumerate(specs):
            self.put(self.tile(ic, stops, fn), px(11) + i * px(50), px(9))
            if cls:
                dot = Gtk.DrawingArea(); dot.set_size_request(px(5), px(5)); dot.on = False
                dot.connect('draw', lambda w, cr: ((cr.arc(px(2.5), px(2.5), px(2.2), 0, 6.3), cr.set_source_rgba(*hex2rgb(pal('bar'))), cr.fill()) if w.on else None, False)[-1])
                self.put(dot, px(11) + i * px(50) + px(21) - px(2), px(54)); self.dots[cls] = dot
        sep = Box('rowline', max(1, px(1)), px(34)); self.put(sep, px(313), px(13))
        t = Gtk.DrawingArea(); t.set_size_request(px(42), px(42)); t.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        def dt(w, cr):
            rounded_rect(cr, 0, 0, px(42), px(42), px(14)); cr.set_source_rgba(*hex2rgb(pal('trash'))); cr.fill()
            draw_icon(cr, 'trash', px(9), px(9), px(24), pal('trashicon'), 1.7); return False
        t.connect('draw', dt); t.connect('button-press-event', lambda *a: launch('osb-files --trash')); self.put(t, px(324), px(9))
        GLib.timeout_add(2000, self.poll); self.poll()
    def poll(self):
        def work():
            res = {cls: bool(sh_out("xdotool search --class %s 2>/dev/null | head -1" % cls)) for cls in self.dots}
            GLib.idle_add(self.apply_dots, res)
        threading.Thread(target=work, daemon=True).start(); return True
    def apply_dots(self, res):
        for cls, on in res.items():
            d = self.dots[cls]
            if d.on != on: d.on = on; d.queue_draw()
        return False
    def tile(self, ic, stops, fn):
        d = Gtk.DrawingArea(); sz = px(42); d.set_size_request(sz, sz); d.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        def draw(w, cr):
            if ic == 'globe': rainbow_tile(cr, sz, sz, px(14))
            else: gradient_tile(cr, sz, sz, px(14), stops, 160)
            draw_icon(cr, 'grid' if ic == 'grid' else ic, px(9), px(9), px(24), '#ffffff', 1.7); return False
        d.connect('draw', draw); d.connect('button-press-event', lambda *a: fn()); return d

# ---------------------------------------------------------------- quick settings
class QuickSettings(OsbWindow):
    def __init__(self, app):
        sw = Gdk.Screen.get_default().get_width()
        cw, ch = px(280), px(342); m = px(50)
        super().__init__(cw, ch, m, None, 'osb-quicksettings'); self.app = app
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY); self.set_keep_above(True)
        self.move(sw - px(95) - cw - m, px(54) - m)
        self.shadow = (26, 14, 34); self.put(Box('panel', cw, ch), 0, 0)
        name, ini = user_names()
        av = Box('avatar', px(34), px(34)); self.put(av, px(18), px(18))
        self.put(make_label(ini, 11, 'bold', '#ffffff', xalign=0.5, w=px(34), h=px(34)), px(18), px(18))
        self.put(make_label(name, 12, 'semibold', 'text', w=px(150), h=px(18)), px(61), px(19))
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
        self.title = make_label('Soft Focus', 10, 'semibold', '#ffffff', w=px(130), h=px(15)); self.put(self.title, px(76), px(284))
        self.artist = make_label('Spatial Sessions', 8, 'normal', '#a9afc3', w=px(130), h=px(12)); self.put(self.artist, px(76), px(299))
        self.prog = Gtk.DrawingArea(); self.prog.set_size_request(px(146), px(3)); self.prog.frac = 0.55
        def pg(w, cr):
            rounded_rect(cr, 0, 0, px(146), px(2.4), px(1.2)); cr.set_source_rgba(1, 1, 1, 0.25); cr.fill()
            rounded_rect(cr, 0, 0, px(146) * self.prog.frac, px(2.4), px(1.2)); cr.set_source_rgba(1, 1, 1, 0.95); cr.fill(); return False
        self.prog.connect('draw', pg); self.put(self.prog, px(76), px(310))
        self.put(Icon('pause', px(18), '#ffffff', 1.5), px(235), px(287))
        pev = Gtk.EventBox(); pev.set_visible_window(False); pev.set_size_request(px(30), px(30)); pev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        pev.connect('button-press-event', lambda *a: launch('playerctl play-pause')); self.put(pev, px(229), px(281))
        self.connect('focus-out-event', self._focus_out); self.set_appearance_ui(State.mode)
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
        sl = Slider(px(162), val, cb); self.put(sl, px(x + 36), px(y + 10))
        lab = make_label('%d%%' % round(val * 100), 8, 'normal', 'muted', xalign=1.0, w=px(34), h=px(14)); self.put(lab, px(x + 207), px(y + 13))
        setattr(self, key + '_slider', sl); setattr(self, key + '_label', lab)
    def place(self):
        sw = Gdk.Screen.get_default().get_width()
        self.move(sw - px(95) - self.cw - self.M, px(54) - self.M); return False
    def set_appearance_ui(self, mode):
        self.app_icon.set_name_('sun' if mode == 'light' else 'moon')
        self.content.move(self.segact, px(198 if mode == 'light' else 227), px(224))
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
    # -- system state
    def read_brightness(self):
        out = sh_out('brightnessctl -m 2>/dev/null')
        try: return float(out.split(',')[3].strip('%')) / 100.0
        except Exception: return 0.76
    def read_volume(self):
        out = sh_out('wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null')
        try: return min(1.0, float(out.split()[1]))
        except Exception: return 0.68
    def set_brightness(self, v):
        self.brightness = v; self.qs.bright_label.set_text('%d%%' % round(v * 100))
        launch(['brightnessctl', 's', '%d%%' % max(1, round(v * 100))])
    def set_volume(self, v):
        self.volume = v; self.qs.vol_label.set_text('%d%%' % round(v * 100))
        launch(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '%.2f' % v])
    def refresh_status(self):
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
            self.qs.show_all(); self.qs.present(); self.refresh_status()
            for d in (30, 150): GLib.timeout_add(d, self.qs.place)
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
        m = Gtk.Menu(); self.menu_open = True
        for label, cmd in (('Network', 'nm-connection-editor'), ('Wi-Fi networks', 'osb-wifi'), ('Bluetooth', 'blueman-manager'),
                           ('Sound', 'pavucontrol'), ('Appearance', 'lxappearance'), ('Terminal', 'lxterminal')):
            it = Gtk.MenuItem(label=label); it.connect('activate', lambda w, c=cmd: launch(c)); m.append(it)
        m.connect('hide', lambda *a: setattr(self, 'menu_open', False)); m.show_all(); m.popup_at_pointer(None)

def main():
    app = ShellApp(); Gtk.main()
