"""osb-setup: first-boot wizard (language, name, picture, password, Wi-Fi, time zone). Runs before the desktop."""
import os, sys, re, json, subprocess, threading, time, unicodedata
from .common import *
from .common import _texts
from . import sysconf

TR = {
 'welcome': ('Welcome to Osborne OS', 'أهلاً في Osborne OS'),
 'welcome_sub': ('Let us set up your device in a few quick steps.', 'منجهّز جهازك بكم خطوة سريعة.'),
 'lang_t': ('Choose your language', 'اختر لغتك'),
 'name_t': ('What is your name?', 'شو اسمك؟'),
 'name_sub': ('This is how your name appears on the screen.', 'هيك بيظهر اسمك على الشاشة.'),
 'name_ph': ('Your name', 'اسمك'),
 'user_l': ('Username (letters and numbers, no spaces)', 'اسم المستخدم (حروف وأرقام بدون مسافات)'),
 'pic_t': ('Choose a picture', 'اختار صورة'),
 'pic_sub': ('You can change it later in Settings.', 'بتقدر تغيّرها بعدين من الإعدادات.'),
 'pw_t': ('Create a password', 'أنشئ كلمة سر'),
 'pw_sub': ('Any password works, even a short one. It also unlocks your private files.', 'أي كلمة سر بتمشي، حتى لو كانت قصيرة. وهي كمان بتفتح ملفاتك الخاصة.'),
 'pw1': ('Password', 'كلمة السر'),
 'pw2': ('Type it again', 'اكتبها مرة تانية'),
 'show': ('Show password', 'أظهر كلمة السر'),
 'wifi_t': ('Connect to Wi-Fi', 'اربط الواي فاي'),
 'wifi_sub': ('Optional. You can skip this and do it later.', 'اختياري. بتقدر تتخطاها وتعملها بعدين.'),
 'scan': ('Scanning for networks…', 'عم بدوّر على شبكات…'),
 'none': ('No networks found.', 'ما لقيت شبكات.'),
 'connect': ('Connect', 'اربط'),
 'connected': ('Connected', 'موصول'),
 'wifi_pw': ('Wi-Fi password', 'كلمة سر الواي فاي'),
 'tz_t': ('Where are you?', 'من أي منطقة انت؟'),
 'tz_sub': ('Pick your time zone so the clock is right.', 'اختار منطقتك الزمنية حتى تضبط الساعة.'),
 'search': ('Search', 'بحث'),
 'done_t': ('Ready to finish', 'جاهزين نخلّص'),
 'done_sub': ('Check your choices, then press Finish.', 'تأكد من اختياراتك وبعدين اكبس إنهاء.'),
 'r_name': ('Name', 'الاسم'), 'r_user': ('Username', 'اسم المستخدم'), 'r_tz': ('Time zone', 'المنطقة الزمنية'), 'r_lang': ('Language', 'اللغة'),
 'next': ('Next', 'التالي'), 'back': ('Back', 'رجوع'), 'skip': ('Skip', 'تخطّى'), 'finish': ('Finish', 'إنهاء'), 'retry': ('Try again', 'حاول مرة تانية'),
 'working': ('Setting things up… please do not turn off the device.', 'عم بجهّز كل شي… لا تطفي الجهاز.'),
 'starting': ('All set! Starting your desktop…', 'تمام! عم بشغّل سطح المكتب…'),
 'err_name': ('Please type your name.', 'اكتب اسمك لو سمحت.'),
 'err_user': ('The username must start with a letter and use only letters, numbers, - or _.', 'اسم المستخدم لازم يبدأ بحرف ويكون حروف إنجليزية وأرقام و - أو _ بس.'),
 'err_pw': ('Please type a password.', 'اكتب كلمة سر لو سمحت.'),
 'err_pw2': ('The two passwords are different.', 'كلمتي السر مو متطابقتين.'),
 'err_pw3': ('Please avoid the ":" character.', 'تجنّب الحرف ":" لو سمحت.'),
 'fail': ('Something went wrong:', 'صار خلل:'),
}
RESERVED = {'root', 'daemon', 'bin', 'sys', 'sync', 'games', 'man', 'lp', 'mail', 'news', 'uucp', 'proxy', 'www-data', 'backup', 'list', 'irc', 'nobody', 'osbsetup', 'sudo', 'admin'}

def slug(name):
    n = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().lower()
    n = re.sub(r'[^a-z0-9]+', '', n)
    if not n or not n[0].isalpha(): n = 'user' + n
    return n[:24]

class Setup(Gtk.Window):
    CW, CH = 720, 520
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL); scr = Gdk.Screen.get_default(); self.w, self.h = scr.get_width(), scr.get_height()
        self.set_decorated(False); self.set_title('osb-setup'); self.fullscreen(); set_rgba_visual(self); self.get_style_context().add_class('osb')
        self.lang = 0; self.d = {'name': '', 'user': '', 'pw': '', 'tz': 'Asia/Damascus', 'avatar': 'initials'}; self.step = 0; self.busy = False; self.user_edited = False
        fx = Gtk.Fixed(); self.add(fx); self.fx = fx; da = Gtk.DrawingArea(); da.set_size_request(self.w, self.h); da.connect('draw', self._bg); fx.put(da, 0, 0); self.surf = None
        self.cx, self.cy = (self.w - px(self.CW)) // 2, (self.h - px(self.CH)) // 2
        self.card = Gtk.Fixed(); self.card.set_size_request(px(self.CW), px(self.CH)); fx.put(self.card, self.cx, self.cy)
        self.pages = [self.pg_lang, self.pg_name, self.pg_pic, self.pg_pw, self.pg_wifi, self.pg_tz, self.pg_done]
        self.render()
        self.connect('map-event', lambda *a: GLib.timeout_add(300, self._grab))
    def _grab(self):
        try: Gdk.Display.get_default().get_default_seat().grab(self.get_window(), Gdk.SeatCapabilities.KEYBOARD, True, None, None, None)
        except Exception: pass
        return False
    def _bg(self, w, cr):
        if self.surf is None: self.surf = render_wall(self.w, self.h, State.mode)
        cr.set_source_surface(self.surf, 0, 0); cr.paint(); cr.set_source_rgba(*hex2rgb(pal('win'))[:3], 0.25); cr.paint(); return False
    def t(self, k): return TR[k][self.lang]
    # ---- layout helpers
    def clear(self):
        for c in self.card.get_children(): self.card.remove(c)
        _texts[:] = [r for r in _texts if r[0].get_parent() is not None]
    def put(self, w, x, y): self.card.put(w, px(x), px(y)); return w
    def label(self, text, size, weight='normal', color='text', x=0, y=0, w=None, xalign=0.0, h=None):
        l = make_label(text, size, weight, color, xalign=xalign, w=px(w) if w else px(self.CW - 2 * x), h=px(h) if h else None); l.set_single_line_mode(False); l.set_line_wrap(True); l.set_ellipsize(Pango.EllipsizeMode.NONE)
        self.put(l, x, y); return l
    def button(self, text, cb, x, y, w=120, primary=False):
        b = Gtk.Button(label=text); b.set_size_request(px(w), px(38)); b.connect('clicked', lambda *a: cb())
        b.get_style_context().add_class('suggested-action' if primary else 'setupbtn')
        self.put(b, x, y); return b
    def entry(self, x, y, w, ph, vis=True, text=''):
        e = Gtk.Entry(); e.set_size_request(px(w), px(40)); e.set_placeholder_text(ph); e.set_visibility(vis); e.set_text(text); e.get_style_context().add_class('setupentry'); self.put(e, x, y); return e
    def render(self):
        self.clear(); self.card.put(Box('panel', px(self.CW), px(self.CH)), 0, 0)
        self.err = None; self.pages[self.step](); self.card.show_all()
        # step dots
        n = len(self.pages)
        for i in range(n):
            dot = Box('pill' if i == self.step else 'qsrow', px(18 if i == self.step else 8), px(8)); self.put(dot, self.CW // 2 - (n * 16) // 2 + i * 16 + (0 if i <= self.step else 10), self.CH - 22)
        self.card.show_all()
    def nav(self, back=True, nxt='next', skip=False):
        if back and self.step > 0: self.button(self.t('back'), self.go_back, 36, self.CH - 76, 110)
        if skip: self.button(self.t('skip'), self.go_next, self.CW - 36 - 110 - 130, self.CH - 76, 110)
        self.nb = self.button(self.t(nxt), self.on_next, self.CW - 36 - 120, self.CH - 76, 120, True)
    def title(self, k, sub=None):
        self.label(self.t(k), 22, 'bold', 'text', 36, 36, h=34)
        if sub: self.label(self.t(sub), 11.5, 'normal', 'muted', 36, 76, h=40)
    def show_err(self, key_or_text, raw=False):
        if self.err is None: self.err = self.label('', 10.5, 'normal', '#ef4444', 36, self.CH - 112, h=24)
        self.err.set_text(key_or_text if raw else self.t(key_or_text)); self.err.show()
    def go_back(self): self.step = max(0, self.step - 1); self.render()
    def go_next(self): self.step = min(len(self.pages) - 1, self.step + 1); self.render()
    def on_next(self):
        v = getattr(self, 'validate', None)
        if v and not v(): return
        self.validate = None
        if self.step == len(self.pages) - 1: self.apply(); return
        self.go_next()
    # ---- pages
    def pg_lang(self):
        self.validate = None
        self.label(TR['welcome'][0], 26, 'bold', 'text', 36, 34, h=40); self.label(TR['welcome'][1], 24, 'bold', 'text', 36, 74, h=40)
        self.label(self.t('lang_t'), 12, 'semibold', 'muted', 36, 140, h=22)
        for i, (nm, sub) in enumerate((('English', 'English'), ('العربية', 'اللهجة الشامية'))):
            x = 36 + i * 320; on = self.lang == i
            self.put(Box('pill' if on else 'qsrow', px(308), px(110)), x, 176)
            self.label(nm, 18, 'bold', 'primary' if on else 'text', x + 22, 200, w=260, h=28); self.label(sub, 11, 'normal', 'muted', x + 22, 240, w=260, h=20)
            ev = Gtk.EventBox(); ev.set_visible_window(False); ev.set_size_request(px(308), px(110)); ev.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            ev.connect('button-press-event', lambda w, e, i=i: (self.set_lang(i), True)[-1]); self.put(ev, x, 176)
        self.label(self.t('welcome_sub'), 12, 'normal', 'muted', 36, 316, h=40)
        self.nav(back=False)
    def set_lang(self, i):
        self.lang = i; self.d['lang'] = 'ar' if i else 'en'; self.render()
    def pg_name(self):
        self.title('name_t', 'name_sub')
        self.e_name = self.entry(36, 140, 648, self.t('name_ph'), True, self.d['name']); self.e_name.set_max_length(30)
        self.label(self.t('user_l'), 10.5, 'normal', 'muted', 36, 204, h=20)
        self.e_user = self.entry(36, 230, 330, 'username', True, self.d['user'] or slug(self.d['name'] or '')); self.e_user.set_max_length(30)
        def chg(e):
            if not self.user_edited and self.e_user.get_text() != slug(e.get_text()):
                self.e_user.handler_block(self.uh); self.e_user.set_text(slug(e.get_text()) if e.get_text().strip() else ''); self.e_user.handler_unblock(self.uh)
        self.uh = self.e_user.connect('changed', lambda e: setattr(self, 'user_edited', True))
        self.e_name.connect('changed', chg); self.e_name.grab_focus(); self.e_name.connect('activate', lambda *a: self.on_next())
        def val():
            n = self.e_name.get_text().strip(); u = self.e_user.get_text().strip().lower()
            if not n: self.show_err('err_name'); return False
            if not u: u = slug(n)
            if not re.match(r'^[a-z][a-z0-9_-]{0,30}$', u) or u in RESERVED: self.show_err('err_user'); return False
            self.d['name'], self.d['user'] = n, u; return True
        self.validate = val; self.nav()
    def pg_pic(self):
        self.title('pic_t', 'pic_sub'); n = self.d['name'] or '?'; self.avs = []; opts = ['initials'] + ['preset:%d' % i for i in range(len(AVATAR_PRESETS))]; per = 5
        for i, kind in enumerate(opts):
            da = Gtk.DrawingArea(); da.set_size_request(px(72), px(72)); da.kind = kind
            def draw(w, cr):
                cr.translate(px(2), px(2)); draw_avatar(cr, px(68), w.kind, name_initials(n))
                if w.kind == self.d['avatar']: cr.identity_matrix(); rounded_rect(cr, 1, 1, px(72) - 2, px(72) - 2, px(22)); cr.set_line_width(3); cr.set_source_rgba(*hex2rgb(pal('primary'))); cr.stroke()
                return False
            da.connect('draw', draw); da.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            da.connect('button-press-event', lambda w, e: (self.d.__setitem__('avatar', w.kind), [x.queue_draw() for x in self.avs], True)[-1]); self.put(da, 36 + (i % per) * 96, 150 + (i // per) * 96)
            self.avs.append(da)
        self.validate = None; self.nav()
    def pg_pw(self):
        self.title('pw_t', 'pw_sub')
        self.e_p1 = self.entry(36, 150, 648, self.t('pw1'), False, self.d['pw']); self.e_p2 = self.entry(36, 204, 648, self.t('pw2'), False, self.d['pw'])
        chk = Gtk.CheckButton(label=self.t('show')); chk.connect('toggled', lambda c: (self.e_p1.set_visibility(c.get_active()), self.e_p2.set_visibility(c.get_active()))); self.put(chk, 36, 262)
        self.e_p1.grab_focus(); self.e_p1.connect('activate', lambda *a: self.e_p2.grab_focus()); self.e_p2.connect('activate', lambda *a: self.on_next())
        def val():
            a, b = self.e_p1.get_text(), self.e_p2.get_text()
            if not a: self.show_err('err_pw'); return False
            if ':' in a or '\n' in a: self.show_err('err_pw3'); return False
            if a != b: self.show_err('err_pw2'); return False
            self.d['pw'] = a; return True
        self.validate = val; self.nav()
    def pg_wifi(self):
        self.title('wifi_t', 'wifi_sub'); self.wl = Gtk.ListBox(); self.wl.set_selection_mode(Gtk.SelectionMode.SINGLE)
        sc = Gtk.ScrolledWindow(); sc.get_style_context().add_class('setupscroll'); sc.set_size_request(px(648), px(200)); sc.add(self.wl); self.put(sc, 36, 124)
        self.wst = self.label(self.t('scan'), 11, 'normal', 'muted', 36, 334, h=20)
        self.e_wp = self.entry(36, 362, 400, self.t('wifi_pw'), False); self.cbtn = self.button(self.t('connect'), self.wifi_connect, 448, 362, 130)
        self.sel_ssid = None
        def sel(lb, row):
            if row is not None: self.sel_ssid = row.ssid; self.e_wp.set_sensitive(row.sec)
        self.wl.connect('row-selected', sel); self.validate = None; self.nav(skip=True)
        def scan():
            out = subprocess.run("nmcli dev wifi rescan >/dev/null 2>&1; nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi list", shell=True, capture_output=True, text=True).stdout
            GLib.idle_add(self.wifi_list, out)
        threading.Thread(target=scan, daemon=True).start()
    def wifi_list(self, out):
        if self.step != 4: return
        nets = {}
        for ln in out.splitlines():
            p = ln.replace('\\:', '\x00').split(':')
            if len(p) < 4 or not p[1]: continue
            ssid = p[1].replace('\x00', ':'); sig = int(p[2] or 0)
            if ssid not in nets or sig > nets[ssid][1]: nets[ssid] = (p[0] == '*', sig, p[3])
        for ssid, (act, sig, sec) in sorted(nets.items(), key=lambda kv: (not kv[1][0], -kv[1][1])):
            r = Gtk.ListBoxRow(); r.ssid = ssid; r.sec = bool(sec) and not act; lb = Gtk.Label(label='%s    %s%s' % (ssid, ('\U0001F512 ' if sec else ''), self.t('connected') if act else '%d%%' % sig)); lb.set_xalign(0); lb.set_margin_start(10); lb.set_margin_top(8); lb.set_margin_bottom(8); r.add(lb); self.wl.add(r)
        self.wst.set_text('' if nets else self.t('none')); self.wl.show_all()
    def wifi_connect(self):
        if not self.sel_ssid: return
        s = self.sel_ssid.replace("'", "'\\''"); pw = self.e_wp.get_text().replace("'", "'\\''")
        self.wst.set_text('…'); self.cbtn.set_sensitive(False)
        def w():
            out = subprocess.run("nmcli dev wifi connect '%s'%s 2>&1" % (s, (" password '%s'" % pw) if pw else ''), shell=True, capture_output=True, text=True).stdout.strip().splitlines()
            GLib.idle_add(lambda: (self.wst.set_text((out[-1] if out else '')[:90]) if self.step == 4 else None, self.cbtn.set_sensitive(True) if self.step == 4 else None))
        threading.Thread(target=w, daemon=True).start()
    def pg_tz(self):
        self.title('tz_t', 'tz_sub'); self.zones = self.zone_list()
        self.e_s = self.entry(36, 124, 648, self.t('search')); self.tzl = Gtk.ListBox(); sc = Gtk.ScrolledWindow(); sc.get_style_context().add_class('setupscroll'); sc.set_size_request(px(648), px(250)); sc.add(self.tzl); self.tzl.set_adjustment(sc.get_vadjustment()); self.put(sc, 36, 176)
        self.rows = {}
        for z in self.zones:
            r = Gtk.ListBoxRow(); r.z = z; lb = Gtk.Label(label=z.replace('_', ' ')); lb.set_xalign(0); lb.set_margin_start(10); lb.set_margin_top(6); lb.set_margin_bottom(6); r.add(lb); self.tzl.add(r); self.rows[z] = r
        def flt(row): q = self.e_s.get_text().strip().lower().replace(' ', '_'); return (not q) or q in row.z.lower()
        self.tzl.set_filter_func(flt); self.e_s.connect('changed', lambda e: self.tzl.invalidate_filter())
        self.tzl.connect('row-selected', lambda lb, r: r is not None and self.d.__setitem__('tz', r.z))
        if self.d['tz'] in self.rows:
            self.tzl.select_row(self.rows[self.d['tz']])
            GLib.timeout_add(300, lambda: (self.rows[self.d['tz']].grab_focus() if self.step == 5 else None, False)[-1])
        self.validate = None; self.nav()
    def zone_list(self):
        z = subprocess.run('timedatectl list-timezones 2>/dev/null', shell=True, capture_output=True, text=True).stdout.split()
        if not z:
            try: z = sorted(l.split('\t')[2] for l in open('/usr/share/zoneinfo/zone1970.tab') if l.strip() and not l.startswith('#'))
            except Exception: z = ['Asia/Damascus', 'Asia/Beirut', 'Asia/Amman', 'Asia/Riyadh', 'Europe/London', 'UTC']
        return z
    def pg_done(self):
        self.title('done_t', 'done_sub'); ini = name_initials(self.d['name']); av = Avatar(px(64), self.d['avatar'], self.d['name']); self.put(av, 36, 130)
        rows = [('r_name', self.d['name']), ('r_user', self.d['user']), ('r_lang', 'English' if self.lang == 0 else 'العربية'), ('r_tz', self.d['tz'])]
        for i, (k, v) in enumerate(rows):
            self.label(self.t(k), 10.5, 'normal', 'muted', 130, 126 + i * 34, w=170, h=20); self.label(v, 12, 'semibold', 'text', 300, 124 + i * 34, w=380, h=22)
        self.validate = None; self.nav(nxt='finish')
    # ---- apply
    def apply(self):
        if self.busy: return
        self.busy = True; self.clear(); self.card.put(Box('panel', px(self.CW), px(self.CH)), 0, 0)
        self.label(self.t('working'), 16, 'semibold', 'text', 36, 150, h=60); bar = PulseBar(px(648)); self.put(bar, 36, 240); bar.start(); self.status = self.label('', 10.5, 'normal', 'muted', 36, 270, h=24); self.card.show_all()
        data = {'name': self.d['name'], 'user': self.d['user'], 'password': self.d['pw'], 'tz': self.d['tz'], 'lang': 'ar' if self.lang else 'en'}
        # save profile + avatar into this session's config; the helper copies them to the new account
        set_display_name(self.d['name']); set_avatar(self.d['avatar'] if self.d['avatar'] != 'file' else 'initials')
        def w():
            try:
                p = subprocess.Popen(['sudo', '-n', '/usr/local/sbin/osb-setup-apply'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                p.stdin.write(json.dumps(data)); p.stdin.close(); err = ''
                for ln in p.stdout:
                    ln = ln.strip()
                    if ln.startswith('STEP '): GLib.idle_add(self.status.set_text, ln[5:][:90])
                    elif ln.startswith('ERROR'): err = ln[5:].strip()
                rc = p.wait()
            except Exception as ex: rc, err = 1, str(ex)
            GLib.idle_add(self.finished, rc, err)
        threading.Thread(target=w, daemon=True).start()
    def finished(self, rc, err):
        if rc == 0:
            self.status.set_text(self.t('starting')); return
        self.busy = False; self.clear(); self.card.put(Box('panel', px(self.CW), px(self.CH)), 0, 0)
        self.label(self.t('fail'), 16, 'semibold', 'text', 36, 120, h=30); self.label(err or ('code %s' % rc), 11, 'normal', '#ef4444', 36, 160, h=120)
        self.button(self.t('retry'), lambda: self.apply(), self.CW - 36 - 140, self.CH - 76, 140, True); self.button(self.t('back'), lambda: (setattr(self, 'step', 3), self.render()), 36, self.CH - 76, 110); self.card.show_all()

def main():
    State.mode = 'light'; apply_css('light')
    t, row, bd, pill = pal('text'), pal('row'), pal('border'), pal('pill')
    css = ('window.osb{background-color:#000;} entry.setupentry{font-size:14px;color:%s;background:%s;border:1px solid %s;border-radius:12px;padding:0 12px;min-height:40px;box-shadow:none;}'
           ' entry.setupentry selection{background:%s;color:%s;} checkbutton label{color:%s;} .setupscroll{background:%s;border:1px solid %s;border-radius:12px;}'
           ' button.setupbtn{background-image:none;background-color:%s;color:%s;border:1px solid %s;border-radius:12px;box-shadow:none;} check{background-image:none;background-color:%s;border:1px solid %s;border-radius:6px;color:#fff;} check:checked{background-color:%s;}'
           ' .setupscroll list, .setupscroll row{background:transparent;color:%s;} .setupscroll row label{color:%s;} .setupscroll row:selected{background:%s;} .setupscroll row:selected label{color:%s;}') % (t, row, bd, pal('primary'), '#ffffff', t, row, bd, row, t, bd, row, bd, pal('primary'), t, t, pill, pal('primary'))
    c = Gtk.CssProvider(); c.load_from_data(css.encode())
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), c, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
    w = Setup(); w.show_all(); Gtk.main()
