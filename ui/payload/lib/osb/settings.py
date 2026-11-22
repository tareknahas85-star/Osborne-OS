"""osb-settings: Settings app in the Osborne design."""
import os, sys, re, shutil, subprocess, threading, platform, socket, getpass, time, json
from .common import *
from .common import _texts
from . import sysconf

def sh(cmd, timeout=6):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception: return ''

def bg(cmd, cb=None, timeout=30):
    def w():
        out = sh(cmd, timeout)
        if cb: GLib.idle_add(cb, out)
    threading.Thread(target=w, daemon=True).start()

CATS = [('Profile', 'user', 'profile'), ('Wi-Fi', 'wifi', 'wifi'), ('Bluetooth', 'bluetooth', 'bluetooth'), ('Sound', 'speaker', 'sound'), ('Display', 'monitor', 'display'),
        ('Appearance', 'palette', 'appearance'), ('Customize', 'grid', 'customize'), ('Keyboard', 'keyboard', 'keyboard'), ('Devices', 'gear', 'devices'), ('Power & Lock', 'battery', 'power'), ('Date & Time', 'clock', 'time'),
        ('Storage', 'disk', 'storage'), ('System Info', 'info', 'about'), ('System Update', 'download', 'update'), ('About', 'star', 'creator')]
CONF = os.path.expanduser('~/.config/osborne')

class SettingsWin(OsbWindow):
    draggable = True
    W, H = 960, 620
    def __init__(self, start='wifi'):
        m = px(50); super().__init__(px(self.W), px(self.H), m, None, 'Settings'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-settings', 'Osb-settings'); self.set_type_hint(Gdk.WindowTypeHint.NORMAL); self.set_position(Gtk.WindowPosition.CENTER)
        self.enable_escape(); self.put(Box('win', px(self.W), px(self.H)), 0, 0); self.put(Box('sidebar', px(220), px(self.H)), 0, 0)
        traffic_lights(self, 16, 25)
        self.put(make_label('Settings', 15, 'bold', 'text', w=px(150), h=px(22)), px(22), px(58))
        self.pill = Box('pill', px(192), px(32)); self.put(self.pill, px(14), px(96)); self.items = {}
        for i, (name, ic, key) in enumerate(CATS):
            y = 96 + i * 32; icn = Icon(ic, px(17), 'text', 1.5); lab = make_label(name, 11.5, 'medium', 'text', w=px(140), h=px(18))
            self.put(icn, px(26), px(y + 7)); self.put(lab, px(55), px(y + 7))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(192), px(32)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, k=key: (self.show(k), True)[-1]); self.put(ev, px(14), px(y)); self.items[key] = (icn, lab, y)
        self.sc = Gtk.ScrolledWindow(); self.sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); self.sc.get_style_context().add_class('osbscroll')
        self.sc.set_size_request(px(self.W - 220 - 20), px(self.H - 100)); self.put(self.sc, px(230), px(88))
        self.title = make_label('', 24, 'bold', 'text', spacing=-0.4, w=px(500), h=px(36)); self.put(self.title, px(236), px(36))
        self.page = None; self.timers = []; self.cur = None; self.show(start)
        watch_mode(lambda m: self.show(self.cur, force=True))
    # ---- helpers
    def clear(self):
        for t in self.timers: GLib.source_remove(t)
        self.timers = []
        for ch in self.sc.get_children(): self.sc.remove(ch)
        if self.page: self.page.destroy()
        self.page = Gtk.Fixed(); self.sc.add(self.page); self.y = 4; self.PWd = px(self.W - 220 - 60)
        _texts[:] = [r for r in _texts if r[0].get_parent() is not None]
    def finish(self): self.page.set_size_request(self.PWd, px(self.y + 20)); self.page.show_all()
    def sect(self, t, gap=14):
        self.y += gap; self.page.put(make_label(t, 11, 'semibold', 'muted', w=px(400), h=px(16)), px(4), px(self.y)); self.y += 24
    def row(self, title, sub='', right=None, h=58, rw=None, click=None):
        P = self.page; P.put(Box('qsrow', self.PWd // 1 if False else self.PWd, px(h)) if False else Box('qsrow', self.PWd - px(4), px(h)), px(0), px(self.y))
        ty = self.y + (h - (34 if sub else 18)) / 2.0
        P.put(make_label(title, 11, 'semibold', 'text', w=px(360), h=px(18)), px(18), px(ty))
        if sub: P.put(make_label(sub, 9, 'normal', 'muted', w=px(400), h=px(14)), px(18), px(ty + 18))
        if right is not None:
            rw = rw or 120
            if isinstance(right, Gtk.ComboBox):
                right.set_size_request(px(rw), px(30))
                for c in right.get_cells():
                    try: c.set_property('ellipsize', Pango.EllipsizeMode.END)
                    except Exception: pass
            P.put(right, self.PWd - px(4) - px(rw) - px(16), px(self.y + (h - 30) / 2.0))
        if click:
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(self.PWd - px(4), px(h)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e: (click(), True)[-1]); P.put(ev, 0, px(self.y))
        self.y += h + 8
    def btn(self, text, cb, primary=False):
        from .i18n import tr
        b = Gtk.Button(label=tr(text)); b.connect('clicked', lambda *a: cb())
        if primary: b.get_style_context().add_class('suggested-action')
        return b
    def note(self, t):
        self.page.put(make_label(t, 10, 'normal', 'muted', w=px(520), h=px(16)), px(6), px(self.y)); self.y += 26
    def every(self, sec, fn): self.timers.append(GLib.timeout_add_seconds(sec, fn))
    # ---- navigation
    def show(self, key, force=False):
        if key == self.cur and not force: return
        self.cur = key
        for k, (icn, lab, y) in self.items.items():
            on = k == key; icn.color = 'primary' if on else 'text'; icn.queue_draw()
            for r in _texts:
                if r[0] is lab: r[3] = 'primary' if on else 'text'; style_label(r)
            if on: self.content.move(self.pill, px(14), px(y))
        self.title.set_text(next(n for n, i, k in CATS if k == key)); self.clear(); getattr(self, 'p_' + key)(); self.finish()
    # ---- pages
    def p_wifi(self):
        self.sw = Switch(sh('nmcli radio wifi') == 'enabled', lambda on: bg('nmcli radio wifi %s; rfkill unblock wifi' % ('on' if on else 'off'), lambda o: self.show('wifi', True), 15))
        self.row('Wi-Fi', 'Turn the wireless radio on or off', self.sw, rw=42)
        self.cur_row = None; self.sect('Available networks'); self.netbox_y = self.y; self.status = make_label('Scanning…', 10, 'normal', 'muted', w=px(400), h=px(16)); self.page.put(self.status, px(6), px(self.y)); self.y += 30
        self.scan()
    def scan(self):
        def got(out):
            if self.cur != 'wifi' or self.status.get_parent() is None: return
            nets = {}
            for ln in out.splitlines():
                p = ln.replace('\\:', '\x00').split(':')
                if len(p) < 4 or not p[1]: continue
                ssid = p[1].replace('\x00', ':'); sig = int(p[2] or 0)
                if ssid not in nets or sig > nets[ssid][1]: nets[ssid] = (p[0] == '*', sig, p[3])
            self.status.set_text('' if nets else 'No networks found. Check that Wi-Fi is on.'); y0 = self.y - 30; self.y = y0
            for ssid, (act, sig, sec) in sorted(nets.items(), key=lambda kv: (not kv[1][0], -kv[1][1])):
                ic = Icon('wifi', px(18), 'primary' if act else 'text', 1.6)
                self.row(ssid, ('Connected' if act else ('Secured' if sec else 'Open')) + '  ·  signal %d%%' % sig, ic if False else None, h=58, click=(lambda s=ssid, se=sec, a=act: self.pick(s, se, a)))
            self.finish()
        bg("nmcli dev wifi rescan >/dev/null 2>&1; nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi list", got, 25)
    def pick(self, ssid, sec, act):
        d = Gtk.Dialog(title='Connect to ' + ssid, transient_for=self, modal=True); d.set_decorated(True)
        box = d.get_content_area(); box.set_spacing(10); box.set_border_width(18)
        lab = Gtk.Label(label=ssid); lab.set_xalign(0); box.add(lab); ent = Gtk.Entry(); ent.set_visibility(False); ent.set_placeholder_text('Password')
        ent.set_activates_default(True); ent.set_size_request(280, -1)
        if sec and not act: box.add(ent)
        d.add_button('Cancel', Gtk.ResponseType.CANCEL); ok = d.add_button('Disconnect' if act else 'Connect', Gtk.ResponseType.OK); ok.get_style_context().add_class('suggested-action'); d.set_default_response(Gtk.ResponseType.OK)
        d.show_all()
        if d.run() == Gtk.ResponseType.OK:
            pw = ent.get_text()
            cmd = ("nmcli connection down id '%s'" % ssid.replace("'", "'\\''")) if act else "nmcli dev wifi connect '%s'%s" % (ssid.replace("'", "'\\''"), (" password '%s'" % pw.replace("'", "'\\''")) if pw else '')
            self.status.set_text('Working…'); bg(cmd, lambda o: (self.show('wifi', True), self.notify('Wi-Fi', o.splitlines()[-1] if o else 'Done')), 50)
        d.destroy()
    def notify(self, t, b): subprocess.Popen(['notify-send', t, b], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def p_bluetooth(self):
        on = 'yes' in sh('bluetoothctl show | grep Powered')
        self.row('Bluetooth', 'Turn Bluetooth on or off' if sh('bluetoothctl show') else 'No Bluetooth adapter found', Switch(on, lambda v: bg('rfkill unblock bluetooth; bluetoothctl power %s' % ('on' if v else 'off'), lambda o: self.show('bluetooth', True), 12)), rw=42)
        self.sect('Devices'); self.row('Search for devices', 'Scan for nearby devices for 10 seconds', self.btn('Scan', lambda: (bg('bluetoothctl --timeout 10 scan on', lambda o: self.show('bluetooth', True), 20), self.notify('Bluetooth', 'Scanning…')), True), rw=80)
        devs = sh('bluetoothctl devices').splitlines()
        if not devs: self.note('No devices yet. Put your device in pairing mode and press Scan.')
        for ln in devs:
            mm = re.match(r'Device ([0-9A-F:]{17}) (.*)', ln)
            if not mm: continue
            mac, name = mm.groups(); info = sh('bluetoothctl info ' + mac); con = 'Connected: yes' in info; paired = 'Paired: yes' in info
            self.row(name, 'Connected' if con else ('Paired' if paired else 'Not paired'), self.btn('Disconnect' if con else ('Connect' if paired else 'Pair'),
                     (lambda m=mac, c=con, p=paired: (bg('bluetoothctl disconnect %s' % m if c else ('bluetoothctl connect %s' % m if p else 'bluetoothctl pair %s && bluetoothctl trust %s && bluetoothctl connect %s' % (m, m, m)), lambda o: self.show('bluetooth', True), 30), self.notify('Bluetooth', 'Working…')))), rw=110)
    def vol(self, tgt='@DEFAULT_AUDIO_SINK@'):
        o = sh('wpctl get-volume %s' % tgt)
        try: return min(1.0, float(o.split()[1])), 'MUTED' in o
        except Exception: return 0.5, False
    def p_sound(self):
        if not sh('wpctl status'): self.note('Sound service is not running yet. It starts with your session.')
        v, mu = self.vol(); self.sect('Output')
        self.vlab = None
        def setv(x):
            subprocess.Popen(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '%.2f' % x])
            if self.vlab is not None and self.vlab.get_parent() is not None: self.vlab.set_text('%d%%' % round(x * 100))
        sl = Slider(px(260), v, setv, lambda x: beep()); self.row('Volume', 'Speakers / headphones', sl, rw=270)
        self.vlab = make_label('%d%%' % round(v * 100), 10, 'semibold', 'primary', xalign=1.0, w=px(50), h=px(16)); self.page.put(self.vlab, self.PWd - px(4) - px(270) - px(16) - px(54), px(self.y - 8 - 58 + 21))
        self.row('Test sound', 'Play a short sound to check the speakers', self.btn('Play', beep), rw=80)
        self.row('Mute', 'Silence the output', Switch(mu, lambda on: subprocess.Popen(['wpctl', 'set-mute', '@DEFAULT_AUDIO_SINK@', '1' if on else '0'])), rw=42)
        st = sh('wpctl status'); sec = re.search(r'Sinks:(.*?)(?:\n\s*├─|\n\s*└─|\Z)', st, re.S)
        if sec:
            for ln in sec.group(1).splitlines():
                mm = re.search(r'(\*)?\s*(\d+)\.\s+(.+?)\s+\[vol', ln)
                if mm: star, nid, nm = mm.groups(); self.row(nm, 'Active output' if star else 'Click to use this output', None, click=(lambda i=nid: (subprocess.run(['wpctl', 'set-default', i]), self.show('sound', True))))
        self.sect('Input'); v2, mu2 = self.vol('@DEFAULT_AUDIO_SOURCE@')
        self.row('Microphone', 'Input volume', Slider(px(260), v2, lambda x: subprocess.Popen(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SOURCE@', '%.2f' % x])), rw=270)
        self.row('Sound mixer', 'Advanced per-app volume control', self.btn('Open', lambda: subprocess.Popen(['pavucontrol'])), rw=80)
    def p_display(self):
        try: b = int(sh('osb-brightness get') or 100) / 100.0
        except Exception: b = 1.0
        self.row('Brightness', 'Screen brightness', Slider(px(260), b, None, lambda x: subprocess.Popen(['osb-brightness', 'set', '%d' % max(5, round(x * 100))])), rw=270)
        xr = sh('xrandr'); out = re.search(r'^(\S+) connected', xr, re.M)
        if out:
            name = out.group(1); modes = re.findall(r'^\s+(\d+x\d+)\s+([\d.]+)', xr.split(name, 1)[1], re.M); seen = []; cur = re.search(r'(\d+x\d+)\+', xr)
            for md, hz in modes:
                if md not in seen: seen.append(md)
            cb = Gtk.ComboBoxText(); [cb.append_text(m) for m in seen]
            if cur and cur.group(1) in seen: cb.set_active(seen.index(cur.group(1)))
            cb.connect('changed', lambda c: subprocess.Popen(['xrandr', '--output', name, '--mode', c.get_active_text()]))
            self.row('Resolution', name, cb, rw=170)
        self.sect('Interface size')
        cur = sysconf.get_ui_scale(); idx = min(range(len(sysconf.SCALES)), key=lambda i: abs(sysconf.SCALES[i][1] - cur))
        cb = Gtk.ComboBoxText(); [cb.append_text(n) for n, v in sysconf.SCALES]; cb.set_active(idx)
        def setsc(c):
            sysconf.set_ui_scale(sysconf.SCALES[c.get_active()][1]); self.note_scale.set_text('Saved. Press "Restart desktop" to apply.'); self.rs_btn.show()
        cb.connect('changed', setsc); self.row('Size of text and buttons', 'Make the whole interface smaller or bigger', cb, rw=150)
        self.note_scale = make_label('', 10, 'normal', 'primary', w=px(400), h=px(16)); self.page.put(self.note_scale, px(6), px(self.y - 4))
        self.rs_btn = self.btn('Restart desktop', self.restart_desktop); self.rs_btn.set_size_request(px(150), px(32)); self.rs_btn.set_no_show_all(True); self.page.put(self.rs_btn, px(300), px(self.y - 10)); self.y += 30
        self.sect('Night light')
        nl = sysconf.get_night(); modes = [('off', 'Off'), ('auto', 'Evening to morning'), ('on', 'Always on')]
        cb2 = Gtk.ComboBoxText(); [cb2.append_text(t) for k, t in modes]; cb2.set_active([k for k, t in modes].index(nl['mode']) if nl['mode'] in [k for k, t in modes] else 0)
        def setnl(c): nl['mode'] = modes[c.get_active()][0]; sysconf.set_night(nl); sysconf.apply_night()
        cb2.connect('changed', setnl); self.row('Night light', 'Warmer colours to rest your eyes (8 pm to 6 am)', cb2, rw=170)
        def settemp(x): nl['temp'] = int(6500 - x * 3000); sysconf.set_night(nl)
        self.row('Warmth', 'Move to the right for warmer colours', Slider(px(260), (6500 - nl['temp']) / 3000.0, settemp, lambda x: sysconf.apply_night()), rw=270)
        self.note('Tip: a lower resolution makes everything bigger on small screens.')
    def restart_desktop(self):
        subprocess.Popen(['bash', '-c', 'pkill -f "python.*osb-shell"; pkill -f "python.*osb-files"; sleep 1; setsid osb-shell >/dev/null 2>&1 & sleep 2; setsid osb-files >/dev/null 2>&1 &'], start_new_session=True)
        GLib.timeout_add(600, lambda: (self.destroy(), False)[-1])
    def p_appearance(self):
        self.sect('Theme', 0)
        for i, (mode, label, sub) in enumerate((('light', 'Light', 'Bright and clean'), ('dark', 'Dark', 'Easy on the eyes'))):
            on = State.mode == mode; x = i * (self.PWd // 2 - px(2))
            card = Box('qstile' if not on else 'pill', self.PWd // 2 - px(12), px(110)); self.page.put(card, x, px(self.y))
            self.page.put(Icon('sun' if mode == 'light' else 'moon', px(28), 'primary' if on else 'text', 1.6), x + px(20), px(self.y + 18))
            self.page.put(make_label(label, 12, 'semibold', 'primary' if on else 'text', w=px(200), h=px(20)), x + px(20), px(self.y + 58)); self.page.put(make_label(sub, 9.5, 'normal', 'muted', w=px(200), h=px(14)), x + px(20), px(self.y + 80))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(self.PWd // 2 - px(12), px(110)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, m=mode: (self.set_theme(m), True)[-1]); self.page.put(ev, x, px(self.y))
        self.y += 128; self.note('The whole system follows this choice: apps, menus, window titles, terminal and notifications.')
        self.page.put(make_label('Wallpaper', 12, 'semibold', 'text', w=px(300), h=px(20)), px(2), px(self.y)); self.y += 30
        opts = [('default', 'Default')] + [('builtin:' + k, k.capitalize()) for k in WALLS]
        try:
            pics = os.path.expanduser('~/Pictures'); opts += [(os.path.join(pics, f), os.path.splitext(f)[0][:12]) for f in sorted(os.listdir(pics)) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) and os.path.isfile(os.path.join(pics, f))][:6]
        except Exception: pass
        cur = get_wall(); tw, th = px(112), px(70); gap = px(10); per = max(1, (self.PWd - px(8)) // (tw + gap))
        for i, (val, name) in enumerate(opts):
            x = px(2) + (i % per) * (tw + gap); y = px(self.y) + (i // per) * (th + px(30))
            da = Gtk.DrawingArea(); da.set_size_request(tw, th); da.val = val; da.on = (val == cur)
            def draw(w, cr, tw=tw, th=th):
                sf = render_wall(tw, th, State.mode, w.val); rounded_rect(cr, 0, 0, tw, th, px(8)); cr.save(); cr.clip(); cr.set_source_surface(sf, 0, 0); cr.paint(); cr.restore()
                rounded_rect(cr, 1, 1, tw - 2, th - 2, px(8)); cr.set_line_width(2.5 if w.on else 1); cr.set_source_rgba(*hex2rgb(pal('primary' if w.on else 'border'))); cr.stroke(); return False
            da.connect('draw', draw); da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            da.connect('button-press-event', lambda w, e, v=val: (e.type == Gdk.EventType.BUTTON_PRESS and e.button == 1 and (set_wall(v), GLib.idle_add(self.show, 'appearance', True)), True)[-1])
            self.page.put(da, x, y); self.page.put(make_label(name, 9.5, 'normal', 'muted', w=tw, h=px(14)), x, y + th + px(4))
        rows = (len(opts) + per - 1) // per; self.y += rows * (70 + 30) + 6
        self.note('Put your own pictures in the Pictures folder and they will show up here.')
    def run_theme(self, m):
        try: subprocess.Popen(['osb-apply-theme', m])
        except Exception as e: print('apply-theme', e, file=sys.stderr)
    def set_theme(self, m):
        State.mode = m; set_mode(m); apply_css(m); restyle_labels(); self.run_theme(m); self.show('appearance', True)
        for w in Gtk.Window.list_toplevels(): w.queue_draw()
    def p_customize(self):
        from .shell import BUILTIN, item_label
        self.sect('Accent colour', 0)
        cur = get_accent(); per = 7; sw_ = px(52)
        for i, (nm, hx) in enumerate(ACCENTS):
            da = Gtk.DrawingArea(); da.set_size_request(sw_, sw_); da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK); da.hx = hx
            def dr(w, cr, hx=hx, sw_=sw_):
                rounded_rect(cr, px(3), px(3), sw_ - px(6), sw_ - px(6), px(14)); cr.set_source_rgba(*hex2rgb(hx)); cr.fill()
                if hx.lower() == get_accent().lower():
                    cr.set_source_rgb(1, 1, 1); cr.set_line_width(px(2.6)); cr.move_to(px(17), px(27)); cr.line_to(px(23), px(33)); cr.line_to(px(35), px(19)); cr.stroke()
                return False
            da.connect('draw', dr); da.connect('button-press-event', lambda w, e, hx=hx: (self.pick_accent(hx), True)[-1]); self.page.put(da, px(2) + i * (sw_ + px(8)), px(self.y))
        self.y += 62; self.note('Changes buttons, highlights, switches and selections across the whole system.')
        # ---- dock
        dock = load_dock()
        self.sect('Dock')
        seg = Gtk.Box(spacing=px(6))
        for key, lab in (('small', 'Small'), ('medium', 'Medium'), ('large', 'Large')):
            b = Gtk.Button(label=lab); b.set_size_request(px(70), px(30))
            if dock['size'] == key: b.get_style_context().add_class('suggested-action')
            b.connect('clicked', lambda w, k=key: self.dock_set(size=k)); seg.pack_start(b, False, False, 0)
        self.row('Icon size', 'How big the dock icons are', seg, rw=230)
        self.row('Show Trash', 'Keep the Trash icon at the end of the dock', Switch(dock['trash'], lambda on: self.dock_set(trash=on)), rw=42)
        self.page.put(make_label('Dock apps', 11, 'semibold', 'text', w=px(300), h=px(18)), px(4), px(self.y + 2)); self.page.put(self.btn('+ Add app', self.add_dock_app, True), self.PWd - px(130), px(self.y - 4)); self.y += 36
        items = list(dock['items'])
        for idx, it in enumerate(items):
            box = Gtk.Box(spacing=px(6))
            for txt, fn, ok in (('↑', lambda i=idx: self.dock_move(i, -1), idx > 0), ('↓', lambda i=idx: self.dock_move(i, 1), idx < len(items) - 1), ('Remove', lambda i=idx: self.dock_remove(i), len(items) > 1)):
                b = Gtk.Button(label=txt); b.set_sensitive(ok); b.set_size_request(px(34 if len(txt) == 1 else 72), px(28)); b.connect('clicked', lambda w, f=fn: f()); box.pack_start(b, False, False, 0)
            self.row(item_label(it), 'Built-in' if it in BUILTIN else 'Added app', box, h=52, rw=184)
        self.page.put(self.btn('Reset dock', lambda: (save_json(DOCKFILE, DOCK_DEFAULT), self.show('customize', True))), px(2), px(self.y)); self.y += 44
        # ---- top bar
        bar = load_bar()
        self.sect('Top bar')
        for key, title, sub in (('activities', 'Activities', 'The "Activities" button on the left'), ('appname', 'App name', 'Shows which app is active'), ('lang', 'Language', 'EN / AR indicator'),
                                ('bell', 'Notifications', 'Notification centre button'), ('wifi', 'Wi-Fi icon', ''), ('vol', 'Sound icon', ''), ('bat', 'Battery icon', ''), ('clock', 'Clock', '')):
            self.row(title, sub, Switch(bar[key], lambda on, k=key: self.bar_set(k, on)), rw=42, h=52 if sub else 46)
        self.page.put(self.btn('Reset top bar', lambda: (save_json(BARFILE, BAR_DEFAULT), self.show('customize', True))), px(2), px(self.y)); self.y += 44
    def pick_accent(self, hx):
        set_accent(hx); apply_accent(hx); apply_css(State.mode); restyle_labels(); self.run_theme(State.mode)
        for w in Gtk.Window.list_toplevels(): w.queue_draw()
        self.show('customize', True)
    def dock_set(self, **kw):
        d = load_dock(); d.update(kw); save_json(DOCKFILE, d); self.show('customize', True)
    def dock_move(self, i, delta):
        d = load_dock(); it = d['items']; j = i + delta
        if 0 <= j < len(it): it[i], it[j] = it[j], it[i]; save_json(DOCKFILE, d)
        self.show('customize', True)
    def dock_remove(self, i):
        d = load_dock()
        if len(d['items']) > 1: d['items'].pop(i); save_json(DOCKFILE, d)
        self.show('customize', True)
    def bar_set(self, key, on):
        d = load_bar(); d[key] = bool(on); save_json(BARFILE, d)
    def add_dock_app(self):
        d = Gtk.Dialog(title='Add to dock', transient_for=self, modal=True); d.set_decorated(True); d.set_default_size(px(420), px(520))
        box = d.get_content_area(); box.set_spacing(8); box.set_border_width(14)
        ent = Gtk.SearchEntry(); ent.set_placeholder_text('Search apps'); box.pack_start(ent, False, False, 0)
        sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC); sc.set_vexpand(True); lb = Gtk.ListBox(); sc.add(lb); box.pack_start(sc, True, True, 0)
        cur = set(load_dock()['items']); cands = []
        from .shell import BUILTIN as _B, app_info as _ai
        for k, v in _B.items():
            if k not in cur: cands.append((v[4], k, None))
        seen = set()
        for ai in sorted(Gio.AppInfo.get_all(), key=lambda a: a.get_name().lower()):
            if not ai.should_show() or ai.get_name() in seen: continue
            did = ai.get_id()
            if not did or ('app:' + did) in cur: continue
            seen.add(ai.get_name()); cands.append((ai.get_name(), 'app:' + did, ai.get_icon()))
        for name, key, gi in cands:
            row = Gtk.ListBoxRow(); hb = Gtk.Box(spacing=10); hb.set_border_width(6)
            if gi: img = Gtk.Image.new_from_gicon(gi, Gtk.IconSize.LARGE_TOOLBAR); hb.pack_start(img, False, False, 0)
            lab = Gtk.Label(label=name); lab.set_xalign(0); hb.pack_start(lab, True, True, 0); row.add(hb); row.key = key; row.nm = name.lower(); lb.add(row)
        lb.set_filter_func(lambda r: not ent.get_text().strip() or ent.get_text().strip().lower() in r.nm); ent.connect('search-changed', lambda e: lb.invalidate_filter())
        def chosen(l, r):
            dd = load_dock(); dd['items'].append(r.key); save_json(DOCKFILE, dd); d.destroy(); self.show('customize', True)
        lb.connect('row-activated', chosen); d.add_button('Cancel', Gtk.ResponseType.CANCEL); d.show_all(); d.run(); d.destroy()
    def p_devices(self):
        tp = sysconf.get_tp(); self.sect('Touchpad', 0)
        def mk(key):
            def f(on): tp[key] = on; sysconf.set_tp(tp); threading.Thread(target=sysconf.apply_touchpad, daemon=True).start()
            return f
        self.row('Tap to click', 'Touch the pad once instead of pressing it', Switch(tp['tap'], mk('tap')), rw=42)
        self.row('Natural scrolling', 'Content follows your fingers, like on a phone', Switch(tp['natural'], mk('natural')), rw=42)
        def spd(x): tp['speed'] = round(x * 2 - 1, 2); sysconf.set_tp(tp)
        self.row('Pointer speed', 'How fast the pointer moves', Slider(px(260), (tp['speed'] + 1) / 2.0, spd, lambda x: sysconf.apply_touchpad()), rw=270)
        self.sect('Printers')
        have = bool(shutil.which('system-config-printer'))
        self.row('Printers', 'Add and manage printers' if have else 'The printer tool is installed with the next system update', self.btn('Open', lambda: subprocess.Popen(['system-config-printer'])) if have else None, rw=80)
    def p_power(self):
        pw = sysconf.get_power(); opts = [(0, 'Never'), (1, '1 minute'), (2, '2 minutes'), (5, '5 minutes'), (10, '10 minutes'), (15, '15 minutes'), (30, '30 minutes'), (60, '1 hour')]
        def combo(key):
            cb = Gtk.ComboBoxText(); [cb.append_text(t) for v, t in opts]
            vals = [v for v, t in opts]; cb.set_active(vals.index(pw[key]) if pw[key] in vals else 4)
            def ch(c): pw[key] = opts[c.get_active()][0]; sysconf.set_power(pw); threading.Thread(target=sysconf.apply_power, daemon=True).start()
            cb.connect('changed', ch); return cb
        self.sect('Screen lock', 0)
        self.row('Lock the screen after', 'Ask for the password when you are away', combo('lock'), rw=150)
        self.row('Turn the screen off after', 'Save battery when you are not using the device', combo('off'), rw=150)
        self.note('The screen is locked automatically after the first time above.')
        self.sect('Power')
        self.row('Lock now', 'Lock the screen right away (Super + L)', self.btn('Lock', lambda: subprocess.Popen(['osb-lock'])), rw=80)
        self.row('Sleep', 'Put the device to sleep', self.btn('Sleep', lambda: subprocess.Popen(['systemctl', 'suspend'])), rw=80)
    def p_keyboard(self):
        cur = (re.search(r'layout:\s+(\S+)', sh('setxkbmap -query')) or [0, 'us'])[1]
        try: cur = re.search(r'-layout (\S+)', open(os.path.join(CONF, 'keyboard.sh')).read()).group(1)
        except Exception: pass
        have = set(('ara' if c == 'ar' else c) for c in cur.split(','))
        self.sect('Language', 0)
        cbl = Gtk.ComboBoxText(); [cbl.append_text(n) for k, n in sysconf.LANGS]; cbl.set_active([k for k, n in sysconf.LANGS].index(sysconf.get_lang()))
        def setl(c): sysconf.set_lang(sysconf.LANGS[c.get_active()][0]); self.notify('Language', 'Saved. Restart the desktop to apply.')
        cbl.connect('changed', setl); self.row('Interface language', 'Language of menus, buttons and settings', cbl, rw=170)
        self.sect('Layouts'); self.note('Press Alt + Shift to switch between the layouts you enable.')
        def apply():
            ls = [l for l in ('us', 'ara') if l in self.have] or ['us']; self.have = set(ls)
            os.makedirs(CONF, exist_ok=True); cmd = 'setxkbmap -layout %s -option grp:alt_shift_toggle' % ','.join(ls); open(os.path.join(CONF, 'keyboard.sh'), 'w').write('#!/bin/sh\n' + cmd + '\n'); subprocess.Popen(cmd + '; sleep 2; ' + cmd, shell=True)
        self.have = have
        for code, name, sub in (('us', 'English (US)', 'QWERTY'), ('ara', 'Arabic', 'العربية')):
            def tog(on, c=code):
                (self.have.add if on else self.have.discard)(c); apply()
            self.row(name, sub, Switch(code in have, tog), rw=42)
    def p_time(self):
        tz = sh('timedatectl show -p Timezone --value'); ntp = sh('timedatectl show -p NTP --value') == 'yes'
        cb = Gtk.ComboBoxText(); zs = sh('timedatectl list-timezones', 10).splitlines()
        for z in zs: cb.append_text(z)
        if tz in zs: cb.set_active(zs.index(tz))
        cb.connect('changed', lambda c: bg('timedatectl set-timezone %s' % c.get_active_text(), lambda o: self.notify('Time zone', c.get_active_text()), 20))
        self.row('Time zone', sh('date "+%A %d %B, %H:%M"'), cb, rw=240)
        self.row('Set time automatically', 'Use the internet to keep the clock right', Switch(ntp, lambda on: bg('timedatectl set-ntp %s' % ('true' if on else 'false'))), rw=42)
        f24 = not os.path.exists(os.path.join(CONF, '12h'))
        def t12(on):
            p = os.path.join(CONF, '12h')
            (open(p, 'w').close() if not on else (os.path.exists(p) and os.remove(p)))
        self.row('24-hour clock', 'Show time as 14:30 instead of 2:30 PM', Switch(f24, t12), rw=42)
    def setup_private_storage(self):
        d = Gtk.Dialog(title='Private storage', transient_for=self, modal=True); box = d.get_content_area(); box.set_spacing(10); box.set_border_width(18)
        lab = Gtk.Label(label='Type your account password. It will also unlock your private files.'); lab.set_xalign(0); box.add(lab)
        e = Gtk.Entry(); e.set_visibility(False); e.set_size_request(300, -1); box.add(e); msg = Gtk.Label(label=''); msg.set_xalign(0); box.add(msg)
        d.add_button('Cancel', Gtk.ResponseType.CANCEL); ok = d.add_button('Set up', Gtk.ResponseType.OK); ok.get_style_context().add_class('suggested-action'); d.show_all()
        if d.run() == Gtk.ResponseType.OK and e.get_text():
            pw = e.get_text(); msg.set_text('Working, this takes a minute…')
            r = subprocess.run(['sudo', '-S', '-k', '-p', '', '/usr/local/sbin/osb-data-setup', getpass.getuser()], input='%s\n%s\n' % (pw, pw), capture_output=True, text=True)
            self.notify('Storage', 'Private storage is ready' if r.returncode == 0 else ((r.stdout.strip().splitlines() or ['Could not set up the storage'])[-1]))
        d.destroy(); self.show('storage', True)
    def p_storage(self):
        seen = set()
        if os.path.exists('/var/lib/osborne/setup-done') and not os.path.exists('/var/lib/osborne/auto-unlock'):
            self.row('Private storage', 'Not set up yet. Your private files get their own locked area on the card.', self.btn('Set up…', self.setup_private_storage, True), rw=100)
        for ln in sh('df -h --output=source,size,used,avail,pcent,target -x tmpfs -x devtmpfs -x squashfs -x overlay').splitlines()[1:]:
            p = ln.split()
            if len(p) < 6 or p[0] in seen or p[5].startswith('/boot') and False: continue
            seen.add(p[0]); name = {'/': 'System', '/home': 'Home'}.get(p[5], p[5]); pct = int(p[4].strip('%') or 0)
            self.row('%s  (%s)' % (name, p[0]), '%s used of %s  ·  %s free' % (p[2], p[1], p[3]), None)
            bar = Gtk.DrawingArea(); bar.set_size_request(self.PWd - px(40), px(6)); bar.frac = pct / 100.0; W = self.PWd - px(40)
            bar.connect('draw', lambda w, cr, W=W: (rounded_rect(cr, 0, 0, W, px(5), px(2.5)), cr.set_source_rgba(*hex2rgb(pal('track'))), cr.fill(), rounded_rect(cr, 0, 0, W * w.frac, px(5), px(2.5)), cr.set_source_rgba(*hex2rgb(pal('primary'))), cr.fill(), False)[-1])
            self.y -= 18; self.page.put(bar, px(18), px(self.y)); self.y += 26
    def p_about(self):
        mem = re.search(r'MemTotal:\s+(\d+)', open('/proc/meminfo').read()); cpu = (re.search(r'model name\s*:\s*(.+)', open('/proc/cpuinfo').read()) or [0, 'Unknown'])[1]
        os_name = (re.search(r'PRETTY_NAME="?([^"\n]+)', open('/etc/os-release').read()) or [0, 'Linux'])[1]
        for t, v in (('Device name', socket.gethostname()), ('Osborne OS version', 'v' + __import__('osb.version', fromlist=['VERSION']).VERSION), ('Operating system', 'Osborne OS  ·  ' + os_name), ('Kernel', platform.release()), ('Processor', cpu.strip()),
                     ('Memory', '%.1f GB' % (int(mem.group(1)) / 1048576.0) if mem else '—'), ('User', getpass.getuser())):
            self.row(t, v, None, h=54)
        self.row('Password', 'Change the password for this user', self.btn('Change…', self.change_password), rw=100)
        self.row('Reset desktop settings', 'Dock, top bar, colours and sizes go back to the defaults. Your files stay.', self.btn('Reset…', self.reset_settings), rw=100)

    def change_password(self):
        d = Gtk.Dialog(title='Change password', transient_for=self, modal=True); box = d.get_content_area(); box.set_spacing(10); box.set_border_width(18)
        ents = []
        for ph in ('Current password', 'New password', 'New password again'):
            e = Gtk.Entry(); e.set_visibility(False); e.set_placeholder_text(ph); e.set_size_request(300, -1); box.add(e); ents.append(e)
        msg = Gtk.Label(label='Any password is fine, even a short one.'); msg.set_xalign(0); box.add(msg)
        d.add_button('Cancel', Gtk.ResponseType.CANCEL); ok = d.add_button('Change', Gtk.ResponseType.OK); ok.get_style_context().add_class('suggested-action'); d.show_all()
        while d.run() == Gtk.ResponseType.OK:
            cur, new, new2 = [e.get_text() for e in ents]
            if not new: msg.set_text('Type a new password.'); continue
            if new != new2: msg.set_text('The two new passwords are different.'); continue
            if ':' in new or '\n' in new: msg.set_text('Please avoid the ":" character.'); continue
            r = subprocess.run(['sudo', '-S', '-k', '-p', '', 'chpasswd'], input='%s\n%s:%s\n' % (cur, getpass.getuser(), new), capture_output=True, text=True)
            if r.returncode == 0:
                if os.path.exists('/var/lib/osborne/auto-unlock'):
                    try:
                        import tempfile
                        with tempfile.NamedTemporaryFile('w', delete=False) as a, tempfile.NamedTemporaryFile('w', delete=False) as b: a.write(cur); b.write(new)
                        subprocess.run(['sudo', '-S', '-k', '-p', '', 'cryptsetup', 'luksChangeKey', '/dev/disk/by-partlabel/data', '--key-file', a.name, '--new-keyfile', b.name, '--batch-mode'], input=cur + '\n', capture_output=True, text=True)
                        os.remove(a.name); os.remove(b.name)
                    except Exception: pass
                self.notify('Password', 'Password changed'); break
            msg.set_text('The current password is not right.')
        d.destroy()
    def reset_settings(self):
        d = Gtk.MessageDialog(transient_for=self, modal=True, message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.NONE, text='Reset desktop settings?')
        d.format_secondary_text('The dock, top bar, colours, sizes, night light, touchpad and power settings go back to the defaults. Your files, name and picture are kept.')
        d.add_button('Cancel', Gtk.ResponseType.CANCEL); d.add_button('Reset', Gtk.ResponseType.OK)
        if d.run() == Gtk.ResponseType.OK:
            for f in ('dock.json', 'topbar.json', 'accent', 'scale', 'nightlight.json', 'touchpad.json', 'power.json'):
                try: os.remove(os.path.join(CONF, f))
                except Exception: pass
            self.notify('Settings', 'Reset. Restart the desktop to apply.')
        d.destroy()
    # ---- profile
    def p_profile(self):
        P = self.page; name = display_name(); big = Avatar(px(72)); P.put(big, px(6), px(self.y + 4))
        P.put(make_label('Display name', 10, 'semibold', 'muted', w=px(200), h=px(16)), px(100), px(self.y + 6))
        ent = Gtk.Entry(); ent.set_text(name); ent.set_max_length(30); ent.set_size_request(px(250), px(34)); P.put(ent, px(100), px(self.y + 28))
        def save(*a):
            n = ent.get_text().strip()
            if n: set_display_name(n); self.notify('Profile', 'Name saved'); big.name = n; big.refresh()
        ent.connect('activate', save); P.put(self.btn('Save', save, True), px(364), px(self.y + 28)); self.y += 96
        self.sect('Avatar', 4); cur = get_avatar(); opts = ['initials'] + ['preset:%d' % i for i in range(len(AVATAR_PRESETS))]
        if os.path.isfile(AVATARPNG): opts.append('file')
        per = max(1, (self.PWd - px(8)) // px(64))
        for i, kind in enumerate(opts):
            da = Gtk.DrawingArea(); da.set_size_request(px(54), px(54)); da.kind = kind
            def draw(w, cr):
                cr.translate(px(1), px(1)); draw_avatar(cr, px(52), w.kind, name_initials(display_name()))
                if w.kind == cur: cr.identity_matrix(); rounded_rect(cr, 1, 1, px(54) - 2, px(54) - 2, px(17)); cr.set_line_width(2.5); cr.set_source_rgba(*hex2rgb(pal('primary'))); cr.stroke()
                return False
            da.connect('draw', draw); da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            da.connect('button-press-event', lambda w, e: (e.button == 1 and (set_avatar(w.kind), GLib.idle_add(self.show, 'profile', True)), True)[-1])
            P.put(da, px(4) + (i % per) * px(64), px(self.y) + (i // per) * px(64))
        self.y += ((len(opts) + per - 1) // per) * 64 + 10
        def pick():
            d = Gtk.FileChooserDialog(title='Choose a picture', transient_for=self, action=Gtk.FileChooserAction.OPEN)
            d.add_button('Cancel', Gtk.ResponseType.CANCEL); d.add_button('Use picture', Gtk.ResponseType.OK)
            f = Gtk.FileFilter(); f.set_name('Pictures'); [f.add_pattern(x) for x in ('*.png', '*.jpg', '*.jpeg', '*.webp', '*.bmp', '*.gif')]; d.add_filter(f)
            pics = os.path.expanduser('~/Pictures'); d.set_current_folder(pics if os.path.isdir(pics) else os.path.expanduser('~'))
            if d.run() == Gtk.ResponseType.OK:
                try: import_avatar(d.get_filename())
                except Exception as ex: self.notify('Profile', 'Could not use that picture: %s' % ex)
            d.destroy(); self.show('profile', True)
        P.put(self.btn('Choose a picture…', pick, True), px(6), px(self.y))
        P.put(self.btn('Use initials', lambda: (set_avatar('initials'), self.show('profile', True))), px(170), px(self.y)); self.y += 46
        self.note('Your name and picture show in the top panel, Files and the lock screen.')

    # ---- about (creator info from GitHub)
    GH_USER = 'tareknahas85-star'; GHC = os.path.join(CONF, 'github.json'); _gh_try = 0; _gh_busy = False
    def p_creator(self):
        try: d = json.load(open(self.GHC))
        except Exception: d = None
        if (not d or time.time() - d.get('t', 0) > 600) and not self._gh_busy and time.time() - self._gh_try > 30:
            self._gh_busy = True; self._gh_try = time.time()
            def work():
                try:
                    u = json.loads(sh('curl -fsSL -m 12 -H "User-Agent: osborne" https://api.github.com/users/%s' % self.GH_USER, 15))
                    r = json.loads(sh('curl -fsSL -m 12 -H "User-Agent: osborne" "https://api.github.com/users/%s/repos?per_page=30&sort=updated"' % self.GH_USER, 15))
                    sh('curl -fsSL -m 12 -o "%s" "%s&s=200"' % (os.path.join(CONF, 'gh_avatar.png'), u.get('avatar_url', '')), 15)
                    os.makedirs(CONF, exist_ok=True); json.dump({'t': time.time(), 'u': u, 'r': [x for x in r if not x.get('fork')]}, open(self.GHC, 'w'))
                except Exception: pass
                def done(): self._gh_busy = False; (self.show('creator', True) if self.cur == 'creator' else None); return False
                GLib.idle_add(done)
            threading.Thread(target=work, daemon=True).start()
        if not d:
            self.note('Could not reach GitHub. Check the internet connection and open this page again.' if not self._gh_busy and self._gh_try and time.time() - self._gh_try > 1 else 'Loading from GitHub…'); return
        u = d['u']; P = self.page; apath = os.path.join(CONF, 'gh_avatar.png')
        if os.path.isfile(apath):
            da = Gtk.DrawingArea(); da.set_size_request(px(72), px(72))
            def dr(w, cr):
                try:
                    pb = GdkPixbuf.Pixbuf.new_from_file_at_size(apath, px(72), px(72)); cr.arc(px(36), px(36), px(36), 0, 6.2832); cr.clip(); Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0); cr.paint()
                except Exception: pass
                return False
            da.connect('draw', dr); P.put(da, px(6), px(self.y + 2))
        P.put(make_label(u.get('name') or u.get('login', ''), 18, 'bold', 'text', w=px(400), h=px(26)), px(96), px(self.y + 6))
        P.put(make_label('@' + u.get('login', ''), 10.5, 'normal', 'muted', w=px(300), h=px(16)), px(96), px(self.y + 34))
        P.put(make_label('%s public projects  \u00b7  %s followers' % (u.get('public_repos', 0), u.get('followers', 0)), 10, 'normal', 'muted', w=px(400), h=px(16)), px(96), px(self.y + 54)); self.y += 86
        for t, v in (('Bio', u.get('bio')), ('Location', u.get('location')), ('Website', u.get('blog'))):
            if v: self.row(t, v, None, h=54)
        self.row('GitHub profile', u.get('html_url', ''), self.btn('Open', lambda: subprocess.Popen(['xdg-open', u.get('html_url', '')], start_new_session=True)), rw=80)
        self.sect('Projects')
        for r in d['r'][:8]:
            self.row(r.get('name', ''), (r.get('description') or 'No description')[:90], make_label('\u2605 %s' % r.get('stargazers_count', 0), 10, 'semibold', 'muted', xalign=1.0, w=px(60), h=px(16)), h=54, rw=60,
                     click=lambda url=r.get('html_url', ''): subprocess.Popen(['xdg-open', url], start_new_session=True))
        self.sect('Osborne OS'); self.row('Made by', 'Tarek Nahas  \u00b7  AI', None, h=54)

    # ---- system update (pulls straight from GitHub)
    UPD_URL = 'https://raw.githubusercontent.com/tareknahas85-star/Osborne-OS/main/ui/update.sh'
    API = 'https://api.github.com/repos/tareknahas85-star/Osborne-OS/commits/main'
    def p_update(self):
        try: cur = open('/usr/local/lib/osborne/version').read().strip()
        except Exception: cur = ''
        self.upd_cur = cur; self.upd_busy = False
        from .version import VERSION
        self.row('Installed version', 'v%s%s' % (VERSION, ('  \u00b7  build ' + cur[:7]) if cur else ''), None)
        self.upd_status = make_label('Checking for updates…', 11, 'semibold', 'text', w=self.PWd, h=px(20)); self.page.put(self.upd_status, px(6), px(self.y)); self.y += 30
        self.upd_log = make_label('', 9, 'normal', 'muted', w=self.PWd, h=px(16)); self.page.put(self.upd_log, px(6), px(self.y)); self.y += 26
        self.upd_bar = PulseBar(self.PWd - px(60)); self.upd_bar.set_no_show_all(True); self.page.put(self.upd_bar, px(6), px(self.y))
        self.upd_arrow = Gtk.Button(label='\u25B8 Details'); self.upd_arrow.connect('clicked', lambda *a: self.toggle_details()); self.upd_arrow.set_size_request(px(86), px(26)); self.page.put(self.upd_arrow, self.PWd - px(96), px(self.y - 6)); self.y += 22
        self.upd_btn = self.btn('Update now', self.do_update, True); self.upd_btn.set_size_request(px(140), px(36)); self.upd_btn.set_sensitive(False); self.page.put(self.upd_btn, px(4), px(self.y))
        self.chk_btn = self.btn('Check again', lambda: self.check_update()); self.chk_btn.set_size_request(px(120), px(36)); self.page.put(self.chk_btn, px(156), px(self.y)); self.y += 56
        self.out_btn = self.btn('Restart desktop', lambda: self.restart_shell()); self.out_btn.set_size_request(px(160), px(36)); self.out_btn.set_no_show_all(True); self.page.put(self.out_btn, px(290), px(self.y - 56)); self.y += 0
        self.det_open = False; self.det_h = px(230)
        sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC); sc.set_size_request(self.PWd - px(12), self.det_h)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_cursor_visible(False); tv.set_monospace(True); tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR); tv.set_left_margin(10); tv.set_right_margin(10); tv.set_top_margin(8); tv.get_style_context().add_class('osblog')
        sc.add(tv); sc.set_no_show_all(True); self.det_sc = sc; self.det_tv = tv; self.page.put(sc, px(6), px(self.y)); self.y += 230 + 8
        if not hasattr(self, 'upd_lines'): self.upd_lines = []
        self.note('Needs an internet connection. Your files and settings are kept.')
        self.check_update()
    def restart_shell(self):
        subprocess.Popen(['bash', '-c', 'pkill -f "python.*osb-shell"; sleep 1; setsid osb-shell >/dev/null 2>&1 &'], start_new_session=True)
        self.out_btn.set_sensitive(False); self.upd_status.set_text('Restarting the desktop…')
    def toggle_details(self, force=None):
        self.det_open = (not self.det_open) if force is None else force
        if self.det_open:
            self.det_sc.show(); self.upd_arrow.set_label('\u25BE Details')
            if not self.upd_lines:
                try: self.upd_lines = ['(previous update log)'] + open('/var/log/osborne-update.log', errors='replace').read().splitlines()[-60:]
                except Exception: self.upd_lines = ['No update has run yet.']
            self.det_tv.get_buffer().set_text('\n'.join(self.upd_lines)); self.det_scroll()
        else: self.det_sc.hide(); self.upd_arrow.set_label('\u25B8 Details')
    def det_scroll(self):
        def go():
            adj = self.det_sc.get_vadjustment(); adj.set_value(adj.get_upper() - adj.get_page_size()); return False
        GLib.idle_add(go)
    def det_add(self, ln):
        self.upd_lines.append(ln); self.upd_lines = self.upd_lines[-400:]
        if self.det_open and self.det_sc.get_parent() is not None:
            b = self.det_tv.get_buffer(); b.insert(b.get_end_iter(), ln + '\n'); self.det_scroll()
    def check_update(self):
        if self.upd_busy: return
        self.upd_status.set_text('Checking for updates…'); self.upd_btn.set_sensitive(False)
        def work():
            import urllib.request, json
            try:
                with urllib.request.urlopen(urllib.request.Request(self.API, headers={'User-Agent': 'osborne'}), timeout=12) as r: sha = json.load(r)['sha']
            except Exception: sha = None
            GLib.idle_add(self.checked, sha)
        threading.Thread(target=work, daemon=True).start()
    def checked(self, sha):
        if self.cur != 'update' or self.upd_status.get_parent() is None: return
        self.latest = sha
        if not sha: self.upd_status.set_text('Could not reach GitHub. Check your internet connection.'); self.upd_btn.set_sensitive(False)
        elif sha == self.upd_cur: self.upd_status.set_text('Osborne is up to date.'); self.upd_btn.set_sensitive(False)
        else: self.upd_status.set_text('A new version is available.'); self.upd_btn.set_sensitive(True)
    def do_update(self):
        if self.upd_busy: return
        self.upd_busy = True; self.upd_btn.set_sensitive(False); self.chk_btn.set_sensitive(False); self.upd_status.set_text('Updating… this takes a few minutes. Please keep the device on.')
        self.upd_t0 = self.upd_last = time.time(); self.upd_step = 0; self.upd_bar.show(); self.upd_bar.set_fraction(0.03); self.upd_bar.start()
        def tick():
            if not self.upd_busy or self.upd_status.get_parent() is None: return False
            el = int(time.time() - self.upd_t0); idle = int(time.time() - self.upd_last)
            t = 'Updating…  %d:%02d' % (el // 60, el % 60) + ('  \u00b7  step %d of 6' % self.upd_step if self.upd_step else '')
            if idle > 60: t += '  \u00b7  still working, no new messages for %d min' % (idle // 60)
            self.upd_status.set_text(t); return True
        self.timers.append(GLib.timeout_add_seconds(1, tick))
        def work():
            try:
                cmd = 'set -o pipefail; T=$(mktemp); curl -fsSL --retry 3 --connect-timeout 20 "%s" -o "$T" || { echo "ERROR: could not download the update script (code $?)"; exit 20; }; grep -q "Osborne OS" "$T" || { echo "ERROR: the downloaded update script is invalid"; exit 21; }; OSB_SHA=%s bash "$T"' % (self.UPD_URL, getattr(self, 'latest', '') or '')
                p = subprocess.Popen(['pkexec', 'bash', '-c', cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                GLib.idle_add(self.det_add, '$ update started')
                for ln in p.stdout:
                    ln = ln.strip()
                    if ln:
                        self.upd_tail = ln[:90]; GLib.idle_add(self.det_add, ln)
                        m = re.match(r'\[(\d)/6\]', ln)
                        def ui(t=ln[:90], n=int(m.group(1)) if m else 0):
                            self.upd_last = time.time()
                            if n: self.upd_step = n; self.upd_bar.set_fraction(0.05 + 0.9 * (n - 1) / 6.0)
                            if self.upd_log.get_parent(): self.upd_log.set_text(t)
                        GLib.idle_add(ui)
                rc = p.wait()
            except Exception: rc = 1
            GLib.idle_add(self.update_done, rc)
        threading.Thread(target=work, daemon=True).start()
    def update_done(self, rc):
        self.upd_busy = False
        if self.upd_status.get_parent() is None: return
        self.upd_bar.stop(); self.upd_bar.set_fraction(1.0 if rc == 0 else 0.0)
        self.chk_btn.set_sensitive(True)
        if rc == 0:
            self.upd_status.set_text('Update finished. Press "Restart desktop" to load the new version.'); self.upd_log.set_text(''); self.out_btn.show()
            try: self.upd_cur = open('/usr/local/lib/osborne/version').read().strip()
            except Exception: pass
        else:
            self.det_add('$ update failed (exit code %s)' % rc); self.toggle_details(True)
            self.upd_status.set_text('The update did not finish (code %s). Last message: %s' % (rc, getattr(self, 'upd_tail', '-'))); self.upd_btn.set_sensitive(True)

def main():
    start = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in [k for n, i, k in CATS] else 'wifi'
    ids = subprocess.run(['xdotool', 'search', '--class', 'osb-settings'], capture_output=True, text=True).stdout.split()
    if ids and subprocess.run(['pgrep', '-fc', 'osb.settings|osb-settings'], capture_output=True, text=True).stdout.strip() not in ('0', '1'):
        subprocess.run(['xdotool', 'windowactivate', ids[-1]]); return
    init_mode(); c = Gtk.CssProvider(); c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = SettingsWin(start); w.connect('destroy', Gtk.main_quit); w.show_all(); Gtk.main()
