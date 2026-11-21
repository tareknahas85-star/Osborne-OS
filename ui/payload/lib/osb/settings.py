"""osb-settings: Settings app in the Osborne design."""
import os, sys, re, shutil, subprocess, threading, platform, socket, getpass
from .common import *
from .common import _texts

def sh(cmd, timeout=6):
    try: return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout).stdout.strip()
    except Exception: return ''

def bg(cmd, cb=None, timeout=30):
    def w():
        out = sh(cmd, timeout)
        if cb: GLib.idle_add(cb, out)
    threading.Thread(target=w, daemon=True).start()

CATS = [('Wi-Fi', 'wifi', 'wifi'), ('Bluetooth', 'bluetooth', 'bluetooth'), ('Sound', 'speaker', 'sound'), ('Display', 'monitor', 'display'),
        ('Appearance', 'palette', 'appearance'), ('Keyboard', 'keyboard', 'keyboard'), ('Date & Time', 'clock', 'time'),
        ('Storage', 'disk', 'storage'), ('About', 'info', 'about'), ('System Update', 'download', 'update')]
CONF = os.path.expanduser('~/.config/osborne')

class SettingsWin(OsbWindow):
    W, H = 960, 620
    def __init__(self, start='wifi'):
        m = px(50); super().__init__(px(self.W), px(self.H), m, None, 'Settings'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-settings', 'Osb-settings'); self.set_type_hint(Gdk.WindowTypeHint.NORMAL); self.set_position(Gtk.WindowPosition.CENTER)
        self.enable_escape(); self.put(Box('win', px(self.W), px(self.H)), 0, 0); self.put(Box('sidebar', px(220), px(self.H)), 0, 0)
        traffic_lights(self, 16, 25)
        self.put(make_label('Settings', 15, 'bold', 'text', w=px(150), h=px(22)), px(22), px(58))
        self.pill = Box('pill', px(192), px(38)); self.put(self.pill, px(14), px(100)); self.items = {}
        for i, (name, ic, key) in enumerate(CATS):
            y = 100 + i * 42; icn = Icon(ic, px(18), 'text', 1.5); lab = make_label(name, 11.5, 'medium', 'text', w=px(140), h=px(18))
            self.put(icn, px(26), px(y + 10)); self.put(lab, px(55), px(y + 10))
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(192), px(38)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
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
            rw = rw or 120; P.put(right, self.PWd - px(4) - px(rw) - px(16), px(self.y + (h - 30) / 2.0))
        if click:
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(self.PWd - px(4), px(h)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e: (click(), True)[-1]); P.put(ev, 0, px(self.y))
        self.y += h + 8
    def btn(self, text, cb, primary=False):
        b = Gtk.Button(label=text); b.connect('clicked', lambda *a: cb())
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
        sl = Slider(px(260), v, lambda x: subprocess.Popen(['wpctl', 'set-volume', '@DEFAULT_AUDIO_SINK@', '%.2f' % x])); self.row('Volume', 'Speakers / headphones', sl, rw=270)
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
        o = sh('brightnessctl -m'); 
        try: b = float(o.split(',')[3].strip('%')) / 100
        except Exception: b = 0.7
        self.row('Brightness', 'Screen backlight' if o else 'Brightness control is not available on this screen', Slider(px(260), b, lambda x: subprocess.Popen(['brightnessctl', 's', '%d%%' % max(1, round(x * 100))])), rw=270)
        xr = sh('xrandr'); out = re.search(r'^(\S+) connected', xr, re.M)
        if out:
            name = out.group(1); modes = re.findall(r'^\s+(\d+x\d+)\s+([\d.]+)', xr.split(name, 1)[1], re.M); seen = []; cur = re.search(r'(\d+x\d+)\+', xr)
            for md, hz in modes:
                if md not in seen: seen.append(md)
            cb = Gtk.ComboBoxText(); [cb.append_text(m) for m in seen]
            if cur and cur.group(1) in seen: cb.set_active(seen.index(cur.group(1)))
            cb.connect('changed', lambda c: subprocess.Popen(['xrandr', '--output', name, '--mode', c.get_active_text()]))
            self.row('Resolution', name, cb, rw=170)
        self.note('Tip: a lower resolution makes everything bigger on small screens.')
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
            da.connect('draw', draw); ev = Gtk.EventBox(); ev.set_visible_window(False); ev.add(da); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, v=val: (set_wall(v), self.show('appearance', True), True)[-1])
            self.page.put(ev, x, y); self.page.put(make_label(name, 9.5, 'normal', 'muted', w=tw, h=px(14)), x, y + th + px(4))
        rows = (len(opts) + per - 1) // per; self.y += rows * (70 + 30) + 6
        self.note('Put your own pictures in the Pictures folder and they will show up here.')
    def set_theme(self, m):
        State.mode = m; set_mode(m); apply_css(m); restyle_labels(); subprocess.Popen(['osb-apply-theme', m]); self.show('appearance', True)
        for w in Gtk.Window.list_toplevels(): w.queue_draw()
    def p_keyboard(self):
        cur = (re.search(r'layout:\s+(\S+)', sh('setxkbmap -query')) or [0, 'us'])[1]; have = set(cur.split(','))
        self.sect('Layouts', 0); self.note('Press Alt + Shift to switch between the layouts you enable.')
        def apply():
            ls = [l for l in ('us', 'ar') if l in self.have] or ['us']; self.have = set(ls)
            os.makedirs(CONF, exist_ok=True); cmd = 'setxkbmap -layout %s -option grp:alt_shift_toggle' % ','.join(ls); open(os.path.join(CONF, 'keyboard.sh'), 'w').write('#!/bin/sh\n' + cmd + '\n'); subprocess.Popen(cmd, shell=True)
        self.have = have
        for code, name, sub in (('us', 'English (US)', 'QWERTY'), ('ar', 'Arabic', 'العربية')):
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
    def p_storage(self):
        seen = set()
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
        for t, v in (('Device name', socket.gethostname()), ('Operating system', 'Osborne OS  ·  ' + os_name), ('Kernel', platform.release()), ('Processor', cpu.strip()),
                     ('Memory', '%.1f GB' % (int(mem.group(1)) / 1048576.0) if mem else '—'), ('User', getpass.getuser())):
            self.row(t, v, None, h=54)
        self.row('Password', 'Change the password for this user', self.btn('Change…', lambda: subprocess.Popen(['lxterminal', '-e', 'passwd'])), rw=100)

    # ---- system update (pulls straight from GitHub)
    UPD_URL = 'https://raw.githubusercontent.com/tareknahas85-star/Osborne-OS/main/ui/update.sh'
    API = 'https://api.github.com/repos/tareknahas85-star/Osborne-OS/commits/main'
    def p_update(self):
        try: cur = open('/usr/local/lib/osborne/version').read().strip()
        except Exception: cur = ''
        self.upd_cur = cur; self.upd_busy = False
        self.row('Installed version', cur[:7] if cur else 'Unknown (installed before updates were tracked)', None)
        self.upd_status = make_label('Checking for updates…', 11, 'semibold', 'text', w=self.PWd, h=px(20)); self.page.put(self.upd_status, px(6), px(self.y)); self.y += 30
        self.upd_log = make_label('', 9, 'normal', 'muted', w=self.PWd, h=px(16)); self.page.put(self.upd_log, px(6), px(self.y)); self.y += 30
        self.upd_btn = self.btn('Update now', self.do_update, True); self.upd_btn.set_size_request(px(140), px(36)); self.upd_btn.set_sensitive(False); self.page.put(self.upd_btn, px(4), px(self.y))
        self.chk_btn = self.btn('Check again', lambda: self.check_update()); self.chk_btn.set_size_request(px(120), px(36)); self.page.put(self.chk_btn, px(156), px(self.y)); self.y += 56
        self.out_btn = self.btn('Log out now', lambda: subprocess.Popen(['openbox', '--exit'])); self.out_btn.set_size_request(px(140), px(36)); self.out_btn.set_no_show_all(True); self.page.put(self.out_btn, px(4), px(self.y)); self.y += 50
        self.note('Needs an internet connection. Your files and settings are kept.')
        self.check_update()
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
        def work():
            try:
                p = subprocess.Popen(['pkexec', 'bash', '-c', 'curl -fsSL %s | bash' % self.UPD_URL], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                for ln in p.stdout:
                    ln = ln.strip()
                    if ln: GLib.idle_add(lambda t=ln[:90]: self.upd_log.set_text(t) if self.upd_log.get_parent() else None)
                rc = p.wait()
            except Exception: rc = 1
            GLib.idle_add(self.update_done, rc)
        threading.Thread(target=work, daemon=True).start()
    def update_done(self, rc):
        self.upd_busy = False
        if self.upd_status.get_parent() is None: return
        self.chk_btn.set_sensitive(True)
        if rc == 0:
            self.upd_status.set_text('Update finished. Log out and back in to use the new version.'); self.upd_log.set_text(''); self.out_btn.show()
            try: self.upd_cur = open('/usr/local/lib/osborne/version').read().strip()
            except Exception: pass
        else:
            self.upd_status.set_text('The update did not finish. Check the internet connection and try again.'); self.upd_btn.set_sensitive(True)

def main():
    start = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] in [k for n, i, k in CATS] else 'wifi'
    ids = subprocess.run(['xdotool', 'search', '--class', 'osb-settings'], capture_output=True, text=True).stdout.split()
    if ids and subprocess.run(['pgrep', '-fc', 'osb.settings|osb-settings'], capture_output=True, text=True).stdout.strip() not in ('0', '1'):
        subprocess.run(['xdotool', 'windowactivate', ids[-1]]); return
    init_mode(); c = Gtk.CssProvider(); c.load_from_data(b'.osbscroll,.osbscroll viewport{background:transparent;}')
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = SettingsWin(start); w.connect('destroy', Gtk.main_quit); w.show_all(); Gtk.main()
