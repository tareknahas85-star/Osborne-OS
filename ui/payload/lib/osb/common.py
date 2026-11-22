"""Osborne shell - shared theme, icons and widgets (matches the HeroUI Linux Desktop design)."""
import os, sys, math, colorsys
import gi
gi.require_version('Gtk', '3.0'); gi.require_version('Gdk', '3.0')
gi.require_version('GdkPixbuf', '2.0'); gi.require_version('Pango', '1.0'); gi.require_version('PangoCairo', '1.0')
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio, Pango, PangoCairo
import cairo

CONF = os.path.expanduser('~/.config/osborne')
MODEFILE = os.path.join(CONF, 'mode')
FONT = 'Inter'

def get_mode():
    try:
        m = open(MODEFILE).read().strip()
        return m if m in ('light', 'dark') else 'light'
    except Exception:
        return 'light'

def set_mode(m):
    os.makedirs(CONF, exist_ok=True)
    with open(MODEFILE, 'w') as f:
        f.write(m)

def _scale():
    if os.environ.get('OSB_SCALE'):
        return float(os.environ['OSB_SCALE'])
    scr = Gdk.Screen.get_default()
    base = max(0.6, min(scr.get_width() / 1536.0, scr.get_height() / 769.0))
    try: base *= max(0.6, min(2.0, float(open(os.path.join(os.path.expanduser('~/.config/osborne'), 'scale')).read().strip())))
    except Exception: pass
    return base
S = _scale()
def px(n): return int(round(n * S))
def pxf(n): return n * S

# ------------------------------------------------------------------ palette
P = {
 'light': dict(
   win='#ffffff', sidebar='#f8f9fb', border='#e8eaee', text='#14151a', muted='#80838e',
   primary='#0a7cff', pill='#e6f2fe', card='#ffffff', row='#f6f7f9', track='#e5e6e8',
   seg='#ffffff', panel='rgba(255,255,255,0.94)', panelb='rgba(255,255,255,0.9)',
   tray='rgba(255,255,255,0.72)', trayb='rgba(255,255,255,0.9)', tile='#e6f2fe',
   trash='#ffffff', trashicon='#6b6e79', shadow='rgba(40,50,80,0.16)', bar='#14151a',
   green='#1fa971', thumb='#ffffff', storebg='#ffffff', iconmuted='#7d808b'),
 'dark': dict(
   win='#1c2029', sidebar='#232730', border='#2b2f38', text='#f2f3f6', muted='#9296a3',
   primary='#0a7cff', pill='#203552', card='#1d212a', row='#262930', track='#383c45',
   seg='#15171d', panel='rgba(34,37,44,0.96)', panelb='rgba(255,255,255,0.08)',
   tray='rgba(30,33,41,0.78)', trayb='rgba(255,255,255,0.10)', tile='#1c3150',
   trash='#1e212a', trashicon='#9a9eab', shadow='rgba(0,0,0,0.45)', bar='#f2f3f6',
   green='#1fa971', thumb='#ffffff', storebg='#1e222b', iconmuted='#9296a3'),
}
TINTS = dict(blue='#e6f2fe', purple='#eeeaff', red='#ffe8e7', green='#e6f7f1')
INKS = dict(blue='#0a7cff', purple='#7c5cf0', red='#ef7a66', green='#1fa98a')

# ------------------------------------------------------------------ accent colour (user choice)
ACCENTFILE = os.path.join(CONF, 'accent')
ACCENTS = [('Blue', '#0a7cff'), ('Purple', '#7a5af8'), ('Pink', '#e0509a'), ('Red', '#e5484d'), ('Orange', '#f08a1c'), ('Green', '#1fa971'), ('Teal', '#12a594')]
ACC = dict(base='#0a7cff', top='#2b90ff', glow='rgba(10,124,255,0.38)')
def _h2t(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
def _t2h(t): return '#%02x%02x%02x' % tuple(max(0, min(255, int(round(v)))) for v in t)
def mix_hex(a, b, t):
    A, B = _h2t(a), _h2t(b); return _t2h([A[i] * (1 - t) + B[i] * t for i in range(3)])
def get_accent():
    try:
        v = open(ACCENTFILE).read().strip()
        return v if len(v) == 7 and v.startswith('#') and int(v[1:], 16) >= 0 else '#0a7cff'
    except Exception: return '#0a7cff'
def apply_accent(hexc=None):
    hexc = hexc or get_accent(); r, g, b = _h2t(hexc)
    ACC.update(base=hexc, top=mix_hex(hexc, '#ffffff', 0.16), glow='rgba(%d,%d,%d,0.38)' % (r, g, b))
    P['light']['primary'] = P['dark']['primary'] = hexc
    P['light']['pill'] = P['light']['tile'] = mix_hex(hexc, '#ffffff', 0.9)
    P['dark']['pill'] = P['dark']['tile'] = mix_hex(hexc, '#1c2029', 0.78)
def set_accent(hexc):
    os.makedirs(CONF, exist_ok=True); open(ACCENTFILE, 'w').write(hexc)

# ------------------------------------------------------------------ dock / top bar settings
import json
DOCKFILE = os.path.join(CONF, 'dock.json'); BARFILE = os.path.join(CONF, 'topbar.json')
DOCK_DEFAULT = dict(items=['apps', 'files', 'browser', 'terminal', 'calculator', 'settings'], size='medium', trash=True)
BAR_DEFAULT = dict(activities=True, appname=True, lang=True, bell=True, wifi=True, vol=True, bat=True, clock=True)
def load_json(path, default):
    d = dict(default)
    try:
        x = json.load(open(path))
        if isinstance(x, dict): d.update({k: x[k] for k in x if k in default})
    except Exception: pass
    return d
def save_json(path, d):
    os.makedirs(CONF, exist_ok=True); tmp = path + '.tmp'; json.dump(d, open(tmp, 'w')); os.replace(tmp, path)
def load_dock(): return load_json(DOCKFILE, DOCK_DEFAULT)
def load_bar(): return load_json(BARFILE, BAR_DEFAULT)

class State: mode = 'light'
def pal(k): return P[State.mode][k]
apply_accent()

def hex2rgb(h):
    if h.startswith('rgba'):
        v = h[5:-1].split(','); return [int(v[0])/255, int(v[1])/255, int(v[2])/255, float(v[3])]
    h = h.lstrip('#'); return [int(h[i:i+2], 16)/255.0 for i in (0, 2, 4)] + [1.0]

# ------------------------------------------------------------------ CSS
def build_css(mode):
    p = P[mode]; r = lambda n: '%dpx' % px(n)
    return f"""
window.osb {{ background: transparent; }}
.win {{ background-color:{p['win']}; border-radius:{r(28)}; border:1px solid {p['border']}; }}
.sidebar {{ background-color:{p['sidebar']}; border-radius:{r(28)} 0 0 {r(28)}; border-right:1px solid {p['border']}; }}
.hline {{ background-color:{p['border']}; }}
.pill {{ background-color:{p['pill']}; border-radius:{r(12)}; }}
.btnp {{ background-image: linear-gradient(180deg,{ACC['top']},{ACC['base']}); border-radius:{r(14)}; box-shadow: 0 {r(8)} {r(20)} {ACC['glow']}; }}
.card {{ background-color:{p['card']}; border:1px solid {p['border']}; border-radius:{r(18)}; }}
.store {{ background-color:{p['storebg']}; border:1px solid {p['border']}; border-radius:{r(14)}; }}
.tile-blue {{ background-color:{TINTS['blue']}; border-radius:{r(11)}; }}
.tile-purple {{ background-color:{TINTS['purple']}; border-radius:{r(11)}; }}
.tile-red {{ background-color:{TINTS['red']}; border-radius:{r(11)}; }}
.tile-green {{ background-color:{TINTS['green']}; border-radius:{r(11)}; }}
.tile-sm {{ background-color:{TINTS['blue']}; border-radius:{r(8)}; }}
.avatar {{ background-image: linear-gradient(135deg,#2f7bff 0%,#7a5af8 62%,#d46fb5 100%); border-radius:{r(11)}; border:1px solid rgba(255,255,255,0.45); }}
.panel {{ background-color:{p['panel']}; border-radius:{r(26)}; border:1px solid {p['panelb']}; }}
.qstile {{ background-color:{p['tile']}; border-radius:{r(16)}; }}
.qsicon {{ background-image: linear-gradient(180deg,{ACC['top']},{ACC['base']}); border-radius:{r(10)}; }}
.qsrow {{ background-color:{p['row']}; border-radius:{r(14)}; }}
textview.osblog, textview.osblog text {{ background-color:{p['row']}; color:{p['muted']}; font-family:monospace; font-size:{r(11)}; }}
.seg {{ background-color:{p['seg']}; border-radius:{r(10)}; }}
.segact {{ background-color:{p['pill']}; border-radius:{r(8)}; }}
.player {{ background-image: linear-gradient(100deg,#2a2545 0%,#1e2f4f 100%); border-radius:{r(16)}; }}
.art {{ background-image: linear-gradient(145deg,#f0847c 0%,#7a5af8 55%,#3eb0c8 100%); border-radius:{r(12)}; }}
.dock {{ background-color:{p['tray']}; border-radius:{r(22)}; border:1px solid {p['trayb']}; }}
.rowline {{ background-color:{p['border']}; }}
.menu-popup {{ background-color:{p['panel']}; border-radius:{r(16)}; border:1px solid {p['border']}; box-shadow: 0 {r(14)} {r(40)} {p['shadow']}; }}
menu, .menu {{ background-color:{p['panel']}; border-radius:{r(12)}; border:1px solid {p['border']}; padding:{r(6)} {r(4)}; color:{p['text']}; }}
menuitem {{ border-radius:{r(8)}; padding:{r(6)} {r(12)}; color:{p['text']}; }}
menuitem:hover {{ background-color:{p['pill']}; }}
menuitem:disabled {{ color:{p['muted']}; }}
separator {{ background-color:{p['border']}; min-height:1px; margin:{r(4)} {r(8)}; }}
.popup {{ background-color:transparent; }}
.mi {{ border-radius:{r(10)}; }}
.mi:hover {{ background-color:{p['pill']}; }}
.hov:hover {{ background-color:{p['row']}; }}
"""

_providers = {}
def apply_css(mode):
    scr = Gdk.Screen.get_default()
    old = _providers.get('p')
    if old: Gtk.StyleContext.remove_provider_for_screen(scr, old)
    prov = Gtk.CssProvider(); prov.load_from_data(build_css(mode).encode())
    Gtk.StyleContext.add_provider_for_screen(scr, prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)
    _providers['p'] = prov

def init_mode():
    State.mode = get_mode(); apply_css(State.mode)

# ------------------------------------------------------------------ icons (24x24 line icons)
def _gear():
    pts = []
    for i in range(8):
        a = math.radians(i * 45)
        for da, R in ((-9, 8.6), (9, 8.6), (22.5 - 8, 6.5), (22.5 + 8, 6.5)):
            ang = a + math.radians(da); pts.append((12 + R*math.cos(ang), 12 + R*math.sin(ang)))
    return '<path d="M' + ' L'.join('%.2f %.2f' % p for p in pts) + 'Z"/><circle cx="12" cy="12" r="2.9"/>'
def _sun():
    rays = ''.join('<path d="M%.2f %.2fL%.2f %.2f"/>' % (12+6.4*math.cos(math.radians(a)), 12+6.4*math.sin(math.radians(a)),
                    12+8.6*math.cos(math.radians(a)), 12+8.6*math.sin(math.radians(a))) for a in range(0, 360, 45))
    return '<circle cx="12" cy="12" r="3.5"/>' + rays
ICONS = {
 'home': '<path d="M4 11.2 12 4l8 7.2V19a1.5 1.5 0 0 1-1.5 1.5h-3.2V14h-6.6v6.5H5.5A1.5 1.5 0 0 1 4 19z"/>',
 'clock': '<circle cx="12" cy="12" r="8.2"/><path d="M12 7.5V12l3 2"/>',
 'star': '<path d="M12 3.8l2.5 5.2 5.7.8-4.1 4 1 5.7L12 16.8 6.9 19.5l1-5.7-4.1-4 5.7-.8z"/>',
 'image': '<rect x="4" y="4" width="16" height="16" rx="3.2"/><circle cx="9" cy="9.5" r="1.6"/><path d="M4.5 17l4.8-4.6 3.4 3.2 2.6-2.4 4.2 4"/>',
 'music': '<path d="M9.2 17.5V6.2l9.6-1.9v11.2"/><circle cx="7" cy="17.5" r="2.2"/><circle cx="16.8" cy="15.5" r="2.2"/>',
 'download': '<path d="M12 4v11M7.5 11l4.5 4.5 4.5-4.5M5 20h14"/>',
 'trash': '<path d="M4.5 7h15M9.5 7V5a1 1 0 0 1 1-1h3a1 1 0 0 1 1 1v2M6.5 7l.8 11.5a1.5 1.5 0 0 0 1.5 1.4h6.4a1.5 1.5 0 0 0 1.5-1.4L17.5 7M10 11v5M14 11v5"/>',
 'search': '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l4 4"/>',
 'grid': '<rect x="4" y="4" width="6.5" height="6.5" rx="2"/><rect x="13.5" y="4" width="6.5" height="6.5" rx="2"/><rect x="4" y="13.5" width="6.5" height="6.5" rx="2"/><rect x="13.5" y="13.5" width="6.5" height="6.5" rx="2"/>',
 'dots': '<circle cx="5.5" cy="12" r="1.2" fill="currentColor"/><circle cx="12" cy="12" r="1.2" fill="currentColor"/><circle cx="18.5" cy="12" r="1.2" fill="currentColor"/>',
 'chev-l': '<path d="M15 5l-7 7 7 7"/>', 'chev-r': '<path d="M9 5l7 7-7 7"/>', 'chev-d': '<path d="M5.5 9l6.5 6.5L18.5 9"/>',
 'plus': '<path d="M12 5v14M5 12h14"/>',
 'folder': '<path d="M3.5 8A2.5 2.5 0 0 1 6 5.5h3.6l2 2.4h6.4A2.5 2.5 0 0 1 20.5 10.4V17a2.5 2.5 0 0 1-2.5 2.5H6A2.5 2.5 0 0 1 3.5 17z"/>',
 'globe': '<circle cx="12" cy="12" r="8.6"/><ellipse cx="12" cy="12" rx="3.8" ry="8.6"/><path d="M3.6 12h16.8"/>',
 'terminal': '<rect x="3.5" y="5" width="17" height="14" rx="3.6"/><path d="M7.5 10l3 2.5-3 2.5M13 15.5h4"/>',
 'calendar': '<rect x="4" y="5.5" width="16" height="14.5" rx="3.6"/><path d="M8 3.5v4M16 3.5v4M4 10h16"/><circle cx="8.6" cy="14" r=".6" fill="currentColor"/><circle cx="12" cy="14" r=".6" fill="currentColor"/><circle cx="15.4" cy="14" r=".6" fill="currentColor"/><circle cx="8.6" cy="17" r=".6" fill="currentColor"/><circle cx="12" cy="17" r=".6" fill="currentColor"/>',
 'gear': _gear(),
 'wifi': '<path d="M3.2 9.4a12.2 12.2 0 0 1 17.6 0M6.2 12.5a8 8 0 0 1 11.6 0M9.2 15.6a3.7 3.7 0 0 1 5.6 0"/><circle cx="12" cy="18.6" r="1" fill="currentColor"/>',
 'volume': '<path d="M4 9.5v5h3.5l4.5 3.8V5.7L7.5 9.5z"/><path d="M15.5 9a4 4 0 0 1 0 6M18.2 6.4a7.6 7.6 0 0 1 0 11.2"/>',
 'battery': '<rect x="2.5" y="7.5" width="17" height="9" rx="2.6"/><rect x="5" y="10" width="12" height="4" rx="1" fill="currentColor"/><path d="M22 11v2"/>',
 'bluetooth': '<path d="M7 8l10 8-5 4.2V3.8L17 8 7 16"/>',
 'sun': _sun(),
 'moon': '<path d="M20 14.3A8 8 0 1 1 9.7 4a6.4 6.4 0 0 0 10.3 10.3z"/>',
 'calculator': '<rect x="5" y="3.2" width="14" height="17.6" rx="2.6"/><path d="M8.2 7.6h7.6M8.6 12h.01M12 12h.01M15.4 12h.01M8.6 15.6h.01M12 15.6h.01M15.4 15.6h.01"/>',
 'play': '<path d="M8.4 5.6v12.8L18.6 12z" fill="currentColor" stroke="none"/>',
 'pause': '<rect x="8" y="5.5" width="2.4" height="13" rx="1.2" fill="currentColor"/><rect x="13.6" y="5.5" width="2.4" height="13" rx="1.2" fill="currentColor"/>',
 'logo': '<path d="M4.2 5.2c0-1 .8-1.9 1.8-2.1l2.4-.5c.9-.2 1.7.5 1.7 1.4v15.6c0 .9-.8 1.7-1.7 1.9l-2.4.5c-1 .2-1.8-.5-1.8-1.5z M13.6 8.7c0-.9.8-1.7 1.7-1.9l2.4-.5c1-.2 1.8.5 1.8 1.4v11.9c0 .9-.7 1.7-1.7 1.9l-2.4.5c-1 .2-1.8-.5-1.8-1.4z" fill="currentColor" stroke="none"/>',
 'bell': '<path d="M6.5 16.5V11a5.5 5.5 0 0 1 11 0v5.5l1.5 2H5z"/><path d="M10 20.5a2 2 0 0 0 4 0"/>',
 'power': '<path d="M12 3.5v8"/><path d="M6.6 6.8a7.8 7.8 0 1 0 10.8 0"/>',
 'restart': '<path d="M19.5 12a7.5 7.5 0 1 1-2.4-5.5"/><path d="M19.8 4.2v4.4h-4.4"/>',
 'logout': '<path d="M10 4.5H6.5A2 2 0 0 0 4.5 6.5v11a2 2 0 0 0 2 2H10"/><path d="M15 8l4 4-4 4M19 12H9.5"/>',
 'user': '<circle cx="12" cy="8.2" r="3.9"/><path d="M4.6 20c.4-3.9 3.6-6.2 7.4-6.2s7 2.3 7.4 6.2"/>',
 'lock': '<rect x="5" y="10.5" width="14" height="9.5" rx="2.6"/><path d="M8.2 10.5V8a3.8 3.8 0 0 1 7.6 0v2.5"/>',
 'keyboard': '<rect x="3" y="6.5" width="18" height="11" rx="3"/><path d="M7 10.5h.01M11 10.5h.01M15 10.5h.01M7.5 14h9"/>',
 'monitor': '<rect x="3.5" y="4.5" width="17" height="11.5" rx="2.6"/><path d="M9 20h6M12 16.5V20"/>',
 'download': '<path d="M12 4v10.5M7.5 10.2 12 14.7l4.5-4.5M5 19.5h14"/>',
 'info': '<circle cx="12" cy="12" r="8.6"/><path d="M12 11v5.5M12 7.8h.01"/>',
 'palette': '<path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.4 0 2-.9 1.5-2-.5-1.2.3-2.5 1.7-2.5H17a3.5 3.5 0 0 0 3.5-3.5C20.5 7 16.8 3.5 12 3.5z"/><path d="M8 11h.01M11 7.8h.01M15 8.8h.01"/>',
 'speaker': '<path d="M4 9.5v5h3.5l4.5 3.8V5.7L7.5 9.5z"/><path d="M15.5 9a4 4 0 0 1 0 6"/>',
 'disk': '<ellipse cx="12" cy="7" rx="7.5" ry="3"/><path d="M4.5 7v5c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3V7M4.5 12v5c0 1.7 3.4 3 7.5 3s7.5-1.3 7.5-3v-5"/>',
 'backspace': '<path d="M9 5.5h9.5a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9L3.5 12z"/><path d="M12.5 9.5l4 4M16.5 9.5l-4 4"/>',
 'check': '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
 'x': '<path d="M6 6l12 12M18 6L6 18"/>',
 'file': '<path d="M7 3.5h6.5L18.5 8.5V19a1.5 1.5 0 0 1-1.5 1.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5z"/><path d="M13.5 3.5v5h5"/>',
}
_pbcache = {}
def icon_pixbuf(name, size, color, stroke=1.7):
    key = (name, size, color, stroke)
    if key in _pbcache: return _pbcache[key]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="%d" height="%d" fill="none" stroke="%s" '
           'stroke-width="%s" stroke-linecap="round" stroke-linejoin="round" color="%s">%s</svg>') % (
           size, size, color, stroke, color, ICONS[name].replace('currentColor', color))
    ld = GdkPixbuf.PixbufLoader.new_with_type('svg'); ld.write(svg.encode()); ld.close()
    _pbcache[key] = ld.get_pixbuf(); return _pbcache[key]

def draw_icon(cr, name, x, y, size, color, stroke=1.7):
    pb = icon_pixbuf(name, max(1, int(round(size))), color, stroke)
    Gdk.cairo_set_source_pixbuf(cr, pb, x, y); cr.paint()

# ------------------------------------------------------------------ text
_texts = []
from .i18n import tr as _tr, LANG as _LANG, _LOG as _ILOG
if _LANG == 'ar' or _ILOG:
    _orig_set_text = Gtk.Label.set_text
    Gtk.Label.set_text = lambda self, t: _orig_set_text(self, _tr(t))
    _orig_append = Gtk.ComboBoxText.append_text
    Gtk.ComboBoxText.append_text = lambda self, t: _orig_append(self, _tr(t))
def make_label(text, size, weight='normal', color='text', xalign=0.0, spacing=0, w=None, h=None, family=FONT):
    from .i18n import tr
    l = Gtk.Label(label=tr(text)); l.set_xalign(xalign); l.set_yalign(0.5)
    l.set_single_line_mode(True); l.set_ellipsize(Pango.EllipsizeMode.END)
    wsz = int(w) if w else -1; hsz = int(h) if h else int(size * 1.5)
    l.set_size_request(wsz, hsz)
    _texts.append([l, size, weight, color, spacing, family]); style_label(_texts[-1]); return l
_W = {'normal': Pango.Weight.NORMAL, 'medium': Pango.Weight.MEDIUM, 'semibold': Pango.Weight.SEMIBOLD, 'bold': Pango.Weight.BOLD}
def style_label(rec):
    l, size, weight, color, spacing, family = rec
    attrs = Pango.AttrList()
    attrs.insert(Pango.attr_family_new(family))
    attrs.insert(Pango.attr_size_new_absolute(int(size * S * Pango.SCALE)))
    attrs.insert(Pango.attr_weight_new(_W[weight]))
    c = hex2rgb(pal(color) if not color.startswith('#') else color)
    attrs.insert(Pango.attr_foreground_new(int(c[0]*65535), int(c[1]*65535), int(c[2]*65535)))
    if spacing: attrs.insert(Pango.attr_letter_spacing_new(int(spacing * S * Pango.SCALE)))
    l.set_attributes(attrs)
def restyle_labels():
    for rec in list(_texts):
        if rec[0].get_parent() is None and not rec[0].get_realized(): continue
        style_label(rec)

# ------------------------------------------------------------------ widgets
def rounded_rect(cr, x, y, w, h, r):
    r = min(r, w/2.0, h/2.0)
    cr.new_sub_path()
    cr.arc(x+w-r, y+r, r, -math.pi/2, 0); cr.arc(x+w-r, y+h-r, r, 0, math.pi/2)
    cr.arc(x+r, y+h-r, r, math.pi/2, math.pi); cr.arc(x+r, y+r, r, math.pi, 3*math.pi/2); cr.close_path()

class Box(Gtk.Box):
    """A plain styled rectangle (CSS class) with an explicit size."""
    def __init__(self, cls, w, h):
        super().__init__(); self.get_style_context().add_class(cls); self.set_size_request(int(w), int(h))

class Icon(Gtk.DrawingArea):
    def __init__(self, name, size, color='text', stroke=1.7):
        super().__init__(); self.name, self.size, self.color, self.stroke = name, size, color, stroke
        self.set_size_request(int(size), int(size)); self.connect('draw', self._d)
    def _d(self, w, cr):
        col = pal(self.color) if not self.color.startswith('#') else self.color
        draw_icon(cr, self.name, 0, 0, self.size, col, self.stroke); return False
    def set_name_(self, name): self.name = name; self.queue_draw()

def draw_emblem(cr, x, y, size, col):
    """Osborne emblem: a bold ring with a small orbiting dot."""
    cr.save(); cr.translate(x, y); u = size / 24.0; cr.set_source_rgba(*(hex2rgb(col) if isinstance(col, str) else col))
    cr.set_line_width(3.3 * u); cr.arc(11.2 * u, 12.8 * u, 7.3 * u, 0, 6.2832); cr.stroke()
    cr.arc(19.2 * u, 4.8 * u, 2.7 * u, 0, 6.2832); cr.fill(); cr.restore()

class Emblem(Gtk.DrawingArea):
    def __init__(self, size, color='bar'):
        super().__init__(); self.size, self.color = size, color; self.set_size_request(int(size), int(size)); self.connect('draw', self._d)
    def _d(self, w, cr):
        col = pal(self.color) if not self.color.startswith('#') else self.color; draw_emblem(cr, 0, 0, self.size, col); return False

def beep():
    import subprocess
    for f in ('/usr/share/sounds/freedesktop/stereo/audio-volume-change.oga', '/usr/share/sounds/freedesktop/stereo/bell.oga', '/usr/share/sounds/alsa/Front_Center.wav'):
        if os.path.exists(f):
            try: subprocess.Popen(['paplay', f], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL); return
            except Exception: pass
    try: subprocess.Popen(['speaker-test', '-t', 'sine', '-f', '700', '-l', '1', '-p', '1'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except Exception: pass

class Slider(Gtk.DrawingArea):
    """Design slider: 4px track, blue fill, 14px white thumb with shadow."""
    def __init__(self, w, value, on_change=None, on_release=None):
        super().__init__(); self.w = w; self.value = value; self.on_change = on_change; self.on_release = on_release
        self.set_size_request(int(w), px(20)); self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK | Gdk.EventMask.POINTER_MOTION_MASK)
        self.connect('draw', self._d); self.connect('button-press-event', self._p); self.connect('motion-notify-event', self._m); self.connect('button-release-event', self._r)
        self.drag = False
    def _d(self, wd, cr):
        W = self.w; H = px(20); cy = H/2.0; th = pxf(4); r = pxf(7.2); x0 = r; x1 = W - r
        rounded_rect(cr, 0, cy-th/2, W, th, th/2); cr.set_source_rgba(*hex2rgb(pal('track'))); cr.fill()
        fx = x0 + (x1-x0)*self.value
        rounded_rect(cr, 0, cy-th/2, fx, th, th/2); cr.set_source_rgba(*hex2rgb(pal('primary'))); cr.fill()
        cr.arc(fx, cy+pxf(1.2), r+pxf(0.8), 0, 2*math.pi); cr.set_source_rgba(0, 0, 0, 0.16); cr.fill()
        cr.arc(fx, cy, r, 0, 2*math.pi); cr.set_source_rgba(1, 1, 1, 1); cr.fill()
        return False
    def _set(self, x):
        r = pxf(7.2); v = (x - r) / max(1.0, (self.w - 2*r)); self.value = max(0.0, min(1.0, v)); self.queue_draw()
        if self.on_change: self.on_change(self.value)
    def _p(self, w, e): self.drag = True; self._set(e.x); return True
    def _r(self, w, e):
        self.drag = False
        if self.on_release: self.on_release(self.value)
        return True
    def _m(self, w, e):
        if e.state & Gdk.ModifierType.BUTTON1_MASK: self._set(e.x)
        return True

def set_rgba_visual(win):
    scr = win.get_screen(); vis = scr.get_rgba_visual()
    if vis: win.set_visual(vis)
    win.set_app_paintable(True)

def new_menu():
    """Gtk.Menu with a transparent (RGBA) popup window so rounded corners don't show black corners."""
    m = Gtk.Menu()
    try:
        tl = m.get_toplevel(); vis = tl.get_screen().get_rgba_visual()
        if vis: tl.set_visual(vis)
        tl.set_app_paintable(True)
    except Exception as e: print('menu', e, file=sys.stderr)
    return m

def gradient_tile(cr, w, h, r, stops, angle=135, shadow=True):
    """Dock-icon tile: rounded gradient + soft top highlight."""
    rad = math.radians(angle); dx, dy = math.sin(rad), -math.cos(rad)
    cx, cy = w/2.0, h/2.0; L = abs(w*dx) / 2 + abs(h*dy) / 2
    g = cairo.LinearGradient(cx - dx*L, cy - dy*L, cx + dx*L, cy + dy*L)
    for off, col in stops: g.add_color_stop_rgba(off, *hex2rgb(col))
    rounded_rect(cr, 0, 0, w, h, r); cr.set_source(g); cr.fill()
    hg = cairo.LinearGradient(0, 0, 0, h*0.55); hg.add_color_stop_rgba(0, 1, 1, 1, 0.22); hg.add_color_stop_rgba(1, 1, 1, 1, 0)
    rounded_rect(cr, 0, 0, w, h, r); cr.set_source(hg); cr.fill()

def rainbow_tile(cr, w, h, r):
    n = int(w)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, n, n); data = surf.get_data(); stride = surf.get_stride()
    for y in range(n):
        for x in range(n):
            a = math.atan2(y - n/2.0, x - n/2.0) / (2*math.pi) + 0.5
            hh = (a * 1.0 + 0.62) % 1.0
            rr, gg, bb = colorsys.hsv_to_rgb(hh, 0.72, 1.0)
            i = y*stride + x*4; data[i] = int(bb*255); data[i+1] = int(gg*255); data[i+2] = int(rr*255); data[i+3] = 255
    surf.mark_dirty()
    rounded_rect(cr, 0, 0, w, h, r); cr.save(); cr.clip(); cr.set_source_surface(surf, 0, 0); cr.paint(); cr.restore()
    hg = cairo.LinearGradient(0, 0, 0, h*0.55); hg.add_color_stop_rgba(0, 1, 1, 1, 0.20); hg.add_color_stop_rgba(1, 1, 1, 1, 0)
    rounded_rect(cr, 0, 0, w, h, r); cr.set_source(hg); cr.fill()

def render_wallpaper(w, h, mode):
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h); cr = cairo.Context(surf)
    if mode == 'light':
        g = cairo.LinearGradient(0, 0, w, h)
        g.add_color_stop_rgb(0, 0.933, 0.945, 0.965); g.add_color_stop_rgb(0.55, 0.965, 0.972, 0.985); g.add_color_stop_rgb(1, 0.985, 0.985, 0.99)
        cr.set_source(g); cr.paint()
        # soft blue wash on the left and faint curved shapes (design wallpaper)
        rg = cairo.RadialGradient(w*0.08, h*0.55, 0, w*0.08, h*0.55, w*0.35)
        rg.add_color_stop_rgba(0, 0.70, 0.78, 0.92, 0.28); rg.add_color_stop_rgba(1, 0.70, 0.78, 0.92, 0)
        cr.set_source(rg); cr.paint()
        cr.set_line_width(max(1, h*0.002)); cr.set_source_rgba(1, 1, 1, 0.55)
        cr.save(); cr.translate(w*0.80, h*0.62); cr.scale(w*0.28, h*0.55); cr.arc(0, 0, 1, 0, 2*math.pi); cr.restore(); cr.stroke()
        cr.set_source_rgba(0.8, 0.84, 0.92, 0.25)
        cr.save(); cr.translate(w*0.86, h*0.70); cr.scale(w*0.22, h*0.50); cr.arc(0, 0, 1, 0, 2*math.pi); cr.restore(); cr.stroke()
    else:
        g = cairo.LinearGradient(0, 0, w, h)
        g.add_color_stop_rgb(0, 0.05, 0.063, 0.10); g.add_color_stop_rgb(0.6, 0.065, 0.085, 0.13); g.add_color_stop_rgb(1, 0.075, 0.09, 0.14)
        cr.set_source(g); cr.paint()
        # large rounded grey-blue shapes: right edge and bottom-left (design wallpaper)
        cr.new_path(); cr.move_to(w*0.805, h*0.215); cr.curve_to(w*0.90, h*0.12, w*0.985, h*0.10, w*1.01, h*0.16)
        cr.line_to(w*1.01, h*0.80); cr.curve_to(w*0.97, h*0.78, w*0.90, h*0.74, w*0.815, h*0.58); cr.curve_to(w*0.79, h*0.45, w*0.78, h*0.30, w*0.805, h*0.215); cr.close_path()
        sg = cairo.LinearGradient(w*0.8, 0, w, h*0.8); sg.add_color_stop_rgb(0, 0.145, 0.157, 0.18); sg.add_color_stop_rgb(1, 0.23, 0.245, 0.285)
        cr.set_source(sg); cr.fill()
        cr.new_path(); cr.move_to(0, h*0.70); cr.line_to(w*0.115, h*0.99); cr.line_to(0, h*1.05); cr.close_path()
        cr.set_source_rgb(0.17, 0.185, 0.22); cr.fill()
        cr.new_path(); cr.move_to(0, h*0.70); cr.curve_to(w*0.05, h*0.74, w*0.10, h*0.84, w*0.115, h*0.99); cr.line_to(w*0.075, h*1.02); cr.line_to(0, h*0.98); cr.close_path()
        cr.set_source_rgba(0.22, 0.24, 0.28, 0.6); cr.fill()
    return surf


WALLS = {
 'aurora':   dict(light=((0.92, 0.95, 0.99), (0.86, 0.93, 0.97), (0.40, 0.75, 0.85), (0.60, 0.55, 0.95)), dark=((0.04, 0.07, 0.12), (0.06, 0.13, 0.19), (0.10, 0.45, 0.55), (0.35, 0.25, 0.65))),
 'sunset':   dict(light=((0.99, 0.94, 0.92), (0.99, 0.89, 0.88), (1.0, 0.62, 0.45), (0.85, 0.45, 0.65)), dark=((0.10, 0.06, 0.10), (0.16, 0.08, 0.12), (0.75, 0.30, 0.25), (0.45, 0.20, 0.55))),
 'forest':   dict(light=((0.93, 0.97, 0.94), (0.88, 0.95, 0.90), (0.45, 0.78, 0.55), (0.30, 0.65, 0.65)), dark=((0.04, 0.09, 0.07), (0.06, 0.14, 0.10), (0.12, 0.50, 0.30), (0.10, 0.40, 0.45))),
 'ocean':    dict(light=((0.92, 0.96, 1.0), (0.85, 0.92, 1.0), (0.25, 0.55, 0.95), (0.20, 0.35, 0.85)), dark=((0.03, 0.06, 0.14), (0.05, 0.10, 0.22), (0.10, 0.35, 0.85), (0.15, 0.20, 0.65))),
 'graphite': dict(light=((0.95, 0.95, 0.96), (0.90, 0.91, 0.93), (0.70, 0.72, 0.78), (0.55, 0.58, 0.66)), dark=((0.07, 0.07, 0.08), (0.11, 0.11, 0.13), (0.30, 0.32, 0.38), (0.22, 0.24, 0.30))),
}
WALLFILE = os.path.join(CONF, 'wallpaper')
def get_wall():
    try: return open(WALLFILE).read().strip() or 'default'
    except Exception: return 'default'
def set_wall(v):
    os.makedirs(CONF, exist_ok=True); open(WALLFILE, 'w').write(v)
def render_wall(w, h, mode, which=None):
    which = which or get_wall()
    if which.startswith('builtin:') and which[8:] in WALLS:
        a, b, c1, c2 = WALLS[which[8:]][mode]; surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h); cr = cairo.Context(surf)
        g = cairo.LinearGradient(0, 0, w, h); g.add_color_stop_rgb(0, *a); g.add_color_stop_rgb(1, *b); cr.set_source(g); cr.paint()
        for (cx, cy, rad, col, al) in ((0.18, 0.78, 0.55, c1, 0.55 if mode == 'dark' else 0.45), (0.85, 0.25, 0.50, c2, 0.50 if mode == 'dark' else 0.38), (0.55, 0.55, 0.35, c1, 0.18)):
            rg = cairo.RadialGradient(w*cx, h*cy, 0, w*cx, h*cy, w*rad); rg.add_color_stop_rgba(0, *col, al); rg.add_color_stop_rgba(1, *col, 0); cr.set_source(rg); cr.paint()
        return surf
    if which.startswith('/') and os.path.isfile(which):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file(which); iw, ih = pb.get_width(), pb.get_height(); sc = max(w / iw, h / ih)
            pb = pb.scale_simple(max(w, int(iw * sc)), max(h, int(ih * sc)), GdkPixbuf.InterpType.BILINEAR)
            surf = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h); cr = cairo.Context(surf); Gdk.cairo_set_source_pixbuf(cr, pb, (w - pb.get_width()) / 2, (h - pb.get_height()) / 2); cr.paint(); return surf
        except Exception: pass
    return render_wallpaper(w, h, mode)
_wmon = []
def watch_wall(cb):
    os.makedirs(CONF, exist_ok=True); f = Gio.File.new_for_path(WALLFILE); m = f.monitor_file(Gio.FileMonitorFlags.NONE, None); _wmon.append(m); m.connect('changed', lambda *a: cb())

# ------------------------------------------------------------------ profile (name + avatar)
PROFILE = os.path.join(CONF, 'profile'); AVATARF = os.path.join(CONF, 'avatar'); AVATARPNG = os.path.join(CONF, 'avatar.png')
AVATAR_PRESETS = [('#2f7bff', '#7a5af8', 'emblem'), ('#12b886', '#2f7bff', 'rings'), ('#ff7a45', '#ff3d7f', 'emblem'), ('#f5a524', '#ef4444', 'bars'),
                  ('#7a5af8', '#22d3ee', 'rings'), ('#334155', '#64748b', 'diamond'), ('#0ea5e9', '#14b8a6', 'bars'), ('#ec4899', '#8b5cf6', 'diamond')]
def display_name():
    try:
        n = open(PROFILE).read().strip().splitlines()[0].strip()
        if n: return n
    except Exception: pass
    import pwd, getpass
    try: full = pwd.getpwnam(getpass.getuser()).pw_gecos.split(',')[0] or getpass.getuser()
    except Exception: full = getpass.getuser()
    full = full.strip() or getpass.getuser(); return full[:1].upper() + full[1:]
def set_display_name(n):
    os.makedirs(CONF, exist_ok=True); open(PROFILE, 'w').write(n.strip() + '\n')
def name_initials(n):
    p = n.split() or ['?']; return (p[0][0] + (p[1][0] if len(p) > 1 else (p[0][1:2] or ''))).upper()
def get_avatar():
    try: return open(AVATARF).read().strip() or 'initials'
    except Exception: return 'initials'
def set_avatar(v):
    os.makedirs(CONF, exist_ok=True); open(AVATARF, 'w').write(v)
def import_avatar(path):
    pb = GdkPixbuf.Pixbuf.new_from_file(path); w, h = pb.get_width(), pb.get_height(); m = min(w, h)
    pb = pb.new_subpixbuf((w - m) // 2, (h - m) // 2, m, m).scale_simple(256, 256, GdkPixbuf.InterpType.BILINEAR)
    os.makedirs(CONF, exist_ok=True); pb.savev(AVATARPNG, 'png', [], []); set_avatar('file')
def draw_avatar(cr, size, kind=None, ini='?'):
    kind = kind or get_avatar(); rr = size * 0.30
    rounded_rect(cr, 0, 0, size, size, rr); cr.save(); cr.clip()
    if kind == 'file' and os.path.isfile(AVATARPNG):
        try:
            pb = GdkPixbuf.Pixbuf.new_from_file_at_size(AVATARPNG, int(size), int(size)); Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0); cr.paint(); cr.restore(); return
        except Exception: pass
    a, b, sym = ('#2f7bff', '#7a5af8', None)
    if kind.startswith('preset:'):
        try: a, b, sym = AVATAR_PRESETS[int(kind[7:])]
        except Exception: pass
    g = cairo.LinearGradient(0, 0, size, size); g.add_color_stop_rgba(0, *hex2rgb(a)); g.add_color_stop_rgba(1, *hex2rgb(b)); cr.set_source(g); cr.paint()
    cr.set_source_rgba(1, 1, 1, 0.95); u = size / 24.0
    if sym == 'emblem': draw_emblem(cr, size * 0.17, size * 0.17, size * 0.66, (1, 1, 1, 0.95))
    elif sym == 'rings':
        cr.set_line_width(2.0 * u)
        for r in (3.2, 6.2, 9.2): cr.arc(12 * u, 12 * u, r * u, 0, 6.2832); cr.stroke(); cr.set_source_rgba(1, 1, 1, 0.95 if r < 9 else 0.6)
    elif sym == 'bars':
        for x, y0, y1 in ((6, 9, 17), (10.5, 5, 19), (15, 8, 16)): rounded_rect(cr, x * u, y0 * u, 3 * u, (y1 - y0) * u, 1.5 * u); cr.fill()
    elif sym == 'diamond':
        cr.move_to(12 * u, 4.5 * u); cr.line_to(19.5 * u, 12 * u); cr.line_to(12 * u, 19.5 * u); cr.line_to(4.5 * u, 12 * u); cr.close_path(); cr.set_line_width(2.2 * u); cr.stroke()
        cr.arc(12 * u, 12 * u, 2.3 * u, 0, 6.2832); cr.fill()
    else:
        lay = PangoCairo.create_layout(cr); lay.set_font_description(Pango.FontDescription('%s Bold %d' % (FONT, max(6, int(size * 0.34 * 0.75))))); lay.set_text(ini, -1)
        tw, th = lay.get_pixel_size(); cr.move_to((size - tw) / 2.0, (size - th) / 2.0); PangoCairo.show_layout(cr, lay)
    cr.restore()
    rounded_rect(cr, 0.5, 0.5, size - 1, size - 1, rr); cr.set_source_rgba(1, 1, 1, 0.45); cr.set_line_width(1); cr.stroke()

class Avatar(Gtk.DrawingArea):
    def __init__(self, size, kind=None, name=None):
        super().__init__(); self.size, self.kind, self.name = size, kind, name; self.set_size_request(int(size), int(size)); self.connect('draw', self._d)
    def _d(self, w, cr): draw_avatar(cr, self.size, self.kind, name_initials(self.name or display_name())); return False
    def refresh(self): self.queue_draw()
_amon = []
def watch_profile(cb):
    os.makedirs(CONF, exist_ok=True)
    for f in (PROFILE, AVATARF, AVATARPNG):
        m = Gio.File.new_for_path(f).monitor_file(Gio.FileMonitorFlags.NONE, None); _amon.append(m); m.connect('changed', lambda *a: cb())

class OsbWindow(Gtk.Window):
    draggable = False
    def _base_drag(self, w, e):
        if not self.draggable or getattr(self, 'custom_drag', False) or e.button != 1 or e.type != Gdk.EventType.BUTTON_PRESS: return False
        self.begin_move_drag(1, int(e.x_root), int(e.y_root), e.time); return True
    def __init__(self, cw, ch, margin=0, hint=None, title='osb'):
        super().__init__(type=Gtk.WindowType.TOPLEVEL); self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK); self.connect('button-press-event', self._base_drag)
        self.get_style_context().add_class('osb'); self.set_title(title)
        self.set_decorated(False); set_rgba_visual(self); self.M = margin; self.cw, self.ch = cw, ch
        self.set_resizable(False); self.set_default_size(cw + 2*margin, ch + 2*margin)
        self.set_skip_taskbar_hint(True); self.set_skip_pager_hint(True)
        if hint: self.set_type_hint(hint)
        self.fixed = Gtk.Fixed(); self.add(self.fixed)
        self.content = Gtk.Fixed(); self.content.set_size_request(cw, ch); self.fixed.put(self.content, margin, margin)
        self.connect('realize', self._shape); self.shadow = None; self.connect('draw', self._shadow_draw)
    def _shadow_draw(self, w, cr):
        if not self.shadow: return False
        r, dy, blur = self.shadow; c = hex2rgb(pal('shadow')); N = 24
        cr.set_operator(cairo.OPERATOR_OVER)
        for i in range(N):
            e = pxf(blur) * (1 - i / float(N))
            rounded_rect(cr, self.M - e, self.M + pxf(dy) - e, self.cw + 2*e, self.ch + 2*e, pxf(r) + e)
            cr.set_source_rgba(c[0], c[1], c[2], c[3] / N * 0.9); cr.fill()
        return False
    def _shape(self, *_):
        gw = self.get_window()
        if gw: gw.input_shape_combine_region(cairo.Region(cairo.RectangleInt(self.M, self.M, self.cw, self.ch)), 0, 0)
    def put(self, w, x, y): self.content.put(w, int(x), int(y)); return w
    def set_content_size(self, cw, ch):
        self.cw, self.ch = int(cw), int(ch); self.content.set_size_request(self.cw, self.ch)
        self.fixed.set_size_request(self.cw + 2*self.M, self.ch + 2*self.M); self.resize(self.cw + 2*self.M, self.ch + 2*self.M)
        self._shape(); self.queue_draw()
    def enable_escape(self):
        self.connect('key-press-event', lambda w, e: (self.close(), True)[-1] if e.keyval == Gdk.KEY_Escape else False)

def traffic_lights(win, x=16, y=25, on_max=None, parent=None):
    """macOS-style close / minimise / maximise dots that actually work."""
    parent = parent or win
    specs = (('#ff5f57', lambda: win.close()), ('#febc2e', lambda: win.iconify()), ('#28c840', on_max))
    for i, (col, fn) in enumerate(specs):
        d = Gtk.DrawingArea(); d.set_size_request(px(14), px(14)); d.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.ENTER_NOTIFY_MASK | Gdk.EventMask.LEAVE_NOTIFY_MASK)
        d.fn = fn; d.hover = False
        def draw(w, cr, col=col):
            cr.arc(px(7), px(7), px(6), 0, 6.3); c = hex2rgb(col if w.fn else '#c9ccd3'); cr.set_source_rgba(*c); cr.fill()
            if w.hover and w.fn:
                cr.set_source_rgba(0, 0, 0, 0.45); cr.set_line_width(max(1.2, pxf(1.4)))
                if col == '#ff5f57': cr.move_to(px(4.5), px(4.5)); cr.line_to(px(9.5), px(9.5)); cr.move_to(px(9.5), px(4.5)); cr.line_to(px(4.5), px(9.5))
                elif col == '#febc2e': cr.move_to(px(4), px(7)); cr.line_to(px(10), px(7))
                else: cr.move_to(px(4.5), px(9.5)); cr.line_to(px(9.5), px(4.5)); cr.move_to(px(4.5), px(4.5)); cr.line_to(px(4.5), px(9.5)); cr.move_to(px(4.5), px(9.5)); cr.line_to(px(9.5), px(9.5))
                cr.stroke()
            return False
        d.connect('draw', draw)
        d.connect('enter-notify-event', lambda w, e: (setattr(w, 'hover', True), w.queue_draw(), False)[-1])
        d.connect('leave-notify-event', lambda w, e: (setattr(w, 'hover', False), w.queue_draw(), False)[-1])
        d.connect('button-press-event', lambda w, e: ((w.fn() if w.fn else None), True)[-1])
        parent.put(d, px(x + i * 20), px(y))


_mon = []
def watch_mode(cb):
    f = Gio.File.new_for_path(os.path.expanduser('~/.config/osborne/mode'))
    os.makedirs(os.path.dirname(f.get_path()), exist_ok=True)
    m = f.monitor_file(Gio.FileMonitorFlags.NONE, None); _mon.append(m)
    def ch(*a):
        nm = get_mode()
        if nm != State.mode: State.mode = nm; apply_css(nm); restyle_labels(); cb(nm)
    m.connect('changed', ch)


def watch_conf(name, cb):
    """Call cb() whenever ~/.config/osborne/<name> changes (written by another process)."""
    os.makedirs(CONF, exist_ok=True)
    m = Gio.File.new_for_path(CONF).monitor_directory(Gio.FileMonitorFlags.NONE, None); _mon.append(m)
    pend = [False]
    def fire():
        pend[0] = False; cb(); return False
    def ch(mon, f, other, ev):
        if f.get_basename() == name and ev in (Gio.FileMonitorEvent.CHANGES_DONE_HINT, Gio.FileMonitorEvent.CREATED, Gio.FileMonitorEvent.CHANGED) and not pend[0]:
            pend[0] = True; GLib.timeout_add(300, fire)
    m.connect('changed', ch)

class PulseBar(Gtk.DrawingArea):
    """Progress bar that always moves (so it never looks frozen). fraction=None -> indeterminate."""
    def __init__(self, w, h=8):
        super().__init__(); self.w, self.h = int(w), px(h); self.frac = None; self.ph = 0.0; self.tid = None; self.set_size_request(self.w, self.h); self.connect('draw', self._d)
    def _d(self, wd, cr):
        W, H = self.w, self.h; rounded_rect(cr, 0, 0, W, H, H / 2.0); cr.set_source_rgba(*hex2rgb(pal('track'))); cr.fill()
        cr.save(); rounded_rect(cr, 0, 0, W, H, H / 2.0); cr.clip()
        if self.frac is None:
            sw = W * 0.28; x = (W + sw) * self.ph - sw; rounded_rect(cr, x, 0, sw, H, H / 2.0); cr.set_source_rgba(*hex2rgb(pal('primary'))); cr.fill()
        else:
            fw = max(H, W * self.frac); rounded_rect(cr, 0, 0, fw, H, H / 2.0); cr.set_source_rgba(*hex2rgb(pal('primary'))); cr.fill()
            sw = W * 0.12; x = (fw + sw) * self.ph - sw; g = cairo.LinearGradient(x, 0, x + sw, 0); g.add_color_stop_rgba(0, 1, 1, 1, 0); g.add_color_stop_rgba(0.5, 1, 1, 1, 0.55); g.add_color_stop_rgba(1, 1, 1, 1, 0)
            cr.rectangle(0, 0, fw, H); cr.clip(); cr.set_source(g); cr.rectangle(x, 0, sw, H); cr.fill()
        cr.restore(); return False
    def start(self):
        if self.tid is None: self.tid = GLib.timeout_add(40, self._tick)
    def _tick(self):
        self.ph = (self.ph + 0.018) % 1.0; self.queue_draw(); return True
    def stop(self):
        if self.tid is not None: GLib.source_remove(self.tid); self.tid = None
        self.queue_draw()
    def set_fraction(self, f): self.frac = f; self.queue_draw()

class Switch(Gtk.DrawingArea):
    """Design toggle: 40x24 pill, blue when on, white knob."""
    def __init__(self, on=False, cb=None):
        super().__init__(); self.on = on; self.cb = cb; self.set_size_request(px(42), px(26)); self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('draw', self._d); self.connect('button-press-event', self._p)
    def _d(self, w, cr):
        W, H = px(42), px(26); rounded_rect(cr, 0, 0, W, H, H / 2.0); cr.set_source_rgba(*hex2rgb(pal('primary') if self.on else pal('track'))); cr.fill()
        r = H / 2.0 - pxf(3); cx = W - H / 2.0 if self.on else H / 2.0
        cr.arc(cx, H / 2.0 + pxf(0.8), r + pxf(0.6), 0, 6.3); cr.set_source_rgba(0, 0, 0, 0.14); cr.fill()
        cr.arc(cx, H / 2.0, r, 0, 6.3); cr.set_source_rgba(1, 1, 1, 1); cr.fill(); return False
    def _p(self, w, e):
        if e.type != Gdk.EventType.BUTTON_PRESS or e.button != 1: return True
        self.set_on(not self.on); (self.cb(self.on) if self.cb else None); return True
    def set_on(self, v): self.on = bool(v); self.queue_draw()
