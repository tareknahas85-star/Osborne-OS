"""Writes the Osborne light/dark theme for every toolkit: GTK3 CSS, Openbox decorations, terminal, notifications, rofi."""
import os, re, subprocess, shutil
HOME = os.path.expanduser('~')
PAL = {
 'light': dict(win='#ffffff', side='#f8f9fb', border='#e8eaee', text='#14151a', muted='#80838e', primary='#0a7cff', pill='#e6f2fe',
               row='#f6f7f9', track='#e5e6e8', field='#f3f4f6', menu='#ffffff', shadow='rgba(40,50,80,0.18)', base='#ffffff'),
 'dark':  dict(win='#1c2029', side='#232730', border='#2b2f38', text='#f2f3f6', muted='#9296a3', primary='#0a7cff', pill='#203552',
               row='#262930', track='#383c45', field='#262930', menu='#22252c', shadow='rgba(0,0,0,0.5)', base='#1c2029'),
}

def _accent():
    try:
        v = open(os.path.join(HOME, '.config/osborne/accent')).read().strip()
        if len(v) == 7 and v.startswith('#'): int(v[1:], 16); return v
    except Exception: pass
    return '#ff8a3d'
def _mix(a, b, t):
    A = [int(a[i:i+2], 16) for i in (1, 3, 5)]; B = [int(b[i:i+2], 16) for i in (1, 3, 5)]
    return '#%02x%02x%02x' % tuple(int(round(A[i] * (1 - t) + B[i] * t)) for i in range(3))
def _pal(m):
    p = dict(PAL[m]); a = _accent(); p['primary'] = a; p['top'] = _mix(a, '#ffffff', 0.16)
    p['pill'] = _mix(a, '#ffffff', 0.9) if m == 'light' else _mix(a, '#1c2029', 0.78); return p

def gtk_css(m):
    p = _pal(m)
    return f"""
@define-color theme_bg_color {p['win']}; @define-color theme_fg_color {p['text']};
@define-color theme_base_color {p['base']}; @define-color theme_text_color {p['text']};
@define-color theme_selected_bg_color {p['primary']}; @define-color theme_selected_fg_color #ffffff;
@define-color borders {p['border']}; @define-color insensitive_fg_color {p['muted']};
* {{ font-family: 'Inter', 'Noto Sans', sans-serif; outline-style: none; }}
window, dialog, .background {{ background-color: {p['win']}; color: {p['text']}; }}
headerbar, .titlebar {{ background-image: none; background-color: {p['win']}; color: {p['text']}; border-bottom: 1px solid {p['border']}; box-shadow: none; border-radius: 0; min-height: 44px; }}
headerbar .title {{ font-weight: 600; }}
.sidebar, .sidebar row, placessidebar, placessidebar row {{ background-color: {p['side']}; color: {p['text']}; }}
button {{ background-image: none; background-color: {p['row']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 12px; padding: 6px 14px; box-shadow: none; text-shadow: none; min-height: 22px; }}
button:hover {{ background-color: {p['pill']}; }}
button:active, button:checked {{ background-color: {p['pill']}; color: {p['primary']}; border-color: {p['primary']}; }}
button:disabled {{ color: {p['muted']}; opacity: 0.6; }}
button.suggested-action, button.default {{ background-image: linear-gradient(180deg, {p['top']}, {p['primary']}); color: #ffffff; border: none; font-weight: 600; }}
button.destructive-action {{ background-image: linear-gradient(180deg, #ff6b61, #f2453d); color: #ffffff; border: none; }}
button.flat, headerbar button, toolbar button {{ background-color: transparent; border-color: transparent; }}
headerbar button:hover, toolbar button:hover {{ background-color: {p['row']}; }}
entry, spinbutton, textview, .view text, combobox button {{ background-color: {p['field']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 12px; padding: 6px 10px; box-shadow: none; caret-color: {p['primary']}; }}
entry:focus, spinbutton:focus {{ border-color: {p['primary']}; box-shadow: 0 0 0 2px alpha({p['primary']}, 0.25); }}
textview, textview text, .view {{ background-color: {p['base']}; color: {p['text']}; }}
selection, *:selected, .view:selected, textview text selection {{ background-color: {p['primary']}; color: #ffffff; }}
window.popup, window.popup.menu {{ background-color: transparent; }}
menu, .menu, .popup, popover, popover.background {{ background-color: {p['menu']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 14px; padding: 6px; box-shadow: 0 10px 30px {p['shadow']}; }}
menuitem, modelbutton {{ border-radius: 9px; padding: 7px 12px; color: {p['text']}; }}
menuitem:hover, modelbutton:hover {{ background-color: {p['pill']}; color: {p['primary']}; }}
menuitem:disabled {{ color: {p['muted']}; }}
separator, menu separator {{ background-color: {p['border']}; min-height: 1px; margin: 4px 6px; }}
menubar {{ background-color: {p['win']}; border-bottom: 1px solid {p['border']}; }}
menubar > menuitem {{ border-radius: 8px; padding: 4px 10px; }}
tooltip, tooltip.background {{ background-color: {p['menu']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 10px; }}
tooltip * {{ color: {p['text']}; }}
scrollbar {{ background: transparent; border: none; }}
scrollbar slider {{ background-color: alpha({p['muted']}, 0.45); border-radius: 8px; min-width: 6px; min-height: 6px; border: 2px solid transparent; }}
scrollbar slider:hover {{ background-color: alpha({p['muted']}, 0.75); }}
scale trough, progressbar trough {{ background-color: {p['track']}; border: none; border-radius: 4px; min-height: 4px; }}
scale highlight, progressbar progress {{ background-color: {p['primary']}; border-radius: 4px; border: none; }}
scale slider {{ background-color: #ffffff; border: none; border-radius: 50%; min-width: 16px; min-height: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.3); }}
switch {{ background-color: {p['track']}; border-radius: 14px; border: none; }}
switch:checked {{ background-color: {p['primary']}; }}
switch slider {{ background-color: #ffffff; border-radius: 50%; border: none; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }}
check, radio {{ background-color: {p['field']}; border: 1px solid {p['border']}; border-radius: 6px; }}
radio {{ border-radius: 50%; }}
check:checked, radio:checked {{ background-color: {p['primary']}; border-color: {p['primary']}; color: #ffffff; }}
notebook > header {{ background-color: {p['side']}; border-color: {p['border']}; }}
notebook > header > tabs > tab {{ border-radius: 10px 10px 0 0; padding: 6px 14px; color: {p['muted']}; }}
notebook > header > tabs > tab:checked {{ color: {p['text']}; background-color: {p['win']}; }}
treeview.view, list, listview, iconview {{ background-color: {p['base']}; color: {p['text']}; }}
row, treeview.view row {{ border-radius: 10px; }}
row:hover, treeview.view:hover {{ background-color: {p['row']}; }}
row:selected, treeview.view:selected, iconview:selected {{ background-color: {p['pill']}; color: {p['primary']}; }}
treeview header button {{ border-radius: 0; background-color: {p['side']}; border: none; border-bottom: 1px solid {p['border']}; }}
statusbar, toolbar, .toolbar {{ background-color: {p['win']}; color: {p['muted']}; border-color: {p['border']}; }}
frame > border, .frame {{ border-color: {p['border']}; border-radius: 12px; }}
infobar, .info {{ background-color: {p['pill']}; color: {p['text']}; border-radius: 12px; }}
messagedialog .dialog-action-area button {{ min-width: 90px; }}
filechooser, filechooser placessidebar {{ background-color: {p['win']}; }}
calendar {{ background-color: {p['base']}; color: {p['text']}; border-radius: 12px; border: 1px solid {p['border']}; }}
calendar:selected {{ background-color: {p['primary']}; color: #fff; border-radius: 8px; }}
.osb-key {{ background-color: {p['row']}; border-radius: 16px; border: none; font-size: 17px; font-weight: 500; }}
.osb-key:hover {{ background-color: {p['pill']}; }}
.osb-op {{ background-color: {p['pill']}; color: {p['primary']}; }}
.osb-eq {{ background-image: linear-gradient(180deg, {p['top']}, {p['primary']}); color: #fff; }}
"""

def _xbm(name, rows):
    bits = ','.join('0x%02x' % int(r[::-1], 2) for r in rows)
    return '#define %s_width 8\n#define %s_height 8\nstatic unsigned char %s_bits[] = { %s };\n' % (name, name, name, bits)
ICON = {
 'close': ['11000011', '11100111', '01111110', '00111100', '00111100', '01111110', '11100111', '11000011'],
 'iconify': ['00000000', '00000000', '00000000', '00000000', '00000000', '00000000', '11111111', '11111111'],
 'max': ['11111111', '11111111', '10000001', '10000001', '10000001', '10000001', '10000001', '11111111'],
 'max_toggled': ['00111111', '00111111', '11100001', '11111101', '10000101', '10000111', '10000100', '11111100'],
 'desk': ['00000000', '01100110', '01100110', '00000000', '00000000', '01100110', '01100110', '00000000'],
 'shade': ['11111111', '11111111', '00000000', '00000000', '00000000', '00000000', '00000000', '00000000'],
}

def openbox_theme(m):
    p = _pal(m); d = os.path.join(HOME, '.themes', 'Osborne-' + m, 'openbox-3'); os.makedirs(d, exist_ok=True)
    for n, rows in ICON.items():
        for suf in ('', '_hover', '_pressed', '_disabled'):
            if n == 'max_toggled' and suf: continue
            open(os.path.join(d, n + suf + '.xbm'), 'w').write(_xbm(n + suf, rows))
    t = f"""border.width: 1
padding.width: 10
padding.height: 7
window.handle.width: 0
window.client.padding.width: 0
window.active.border.color: {p['border']}
window.inactive.border.color: {p['border']}
window.active.title.separator.color: {p['border']}
window.inactive.title.separator.color: {p['border']}
window.active.title.bg: flat solid
window.active.title.bg.color: {p['win']}
window.inactive.title.bg: flat solid
window.inactive.title.bg.color: {p['side']}
window.active.label.bg: parentrelative
window.inactive.label.bg: parentrelative
window.active.label.text.color: {p['text']}
window.inactive.label.text.color: {p['muted']}
window.label.text.justify: left
window.active.handle.bg: flat solid
window.active.handle.bg.color: {p['win']}
window.inactive.handle.bg: flat solid
window.inactive.handle.bg.color: {p['win']}
window.active.grip.bg: flat solid
window.active.grip.bg.color: {p['win']}
window.inactive.grip.bg: flat solid
window.inactive.grip.bg.color: {p['win']}
window.active.client.color: {p['win']}
window.inactive.client.color: {p['win']}
window.active.button.unpressed.bg: flat solid
window.active.button.unpressed.bg.color: {p['win']}
window.active.button.unpressed.image.color: {p['text']}
window.active.button.hover.bg: flat solid
window.active.button.hover.bg.color: {p['pill']}
window.active.button.hover.image.color: {p['primary']}
window.active.button.pressed.bg: flat solid
window.active.button.pressed.bg.color: {p['primary']}
window.active.button.pressed.image.color: #ffffff
window.active.button.disabled.bg: parentrelative
window.active.button.disabled.image.color: {p['muted']}
window.inactive.button.unpressed.bg: parentrelative
window.inactive.button.unpressed.image.color: {p['muted']}
window.inactive.button.hover.bg: flat solid
window.inactive.button.hover.bg.color: {p['pill']}
window.inactive.button.hover.image.color: {p['primary']}
window.inactive.button.pressed.bg: flat solid
window.inactive.button.pressed.bg.color: {p['primary']}
window.inactive.button.pressed.image.color: #ffffff
window.inactive.button.disabled.bg: parentrelative
window.inactive.button.disabled.image.color: {p['muted']}
window.active.button.toggled.bg: parentrelative
window.active.button.toggled.image.color: {p['primary']}
window.inactive.button.toggled.bg: parentrelative
window.inactive.button.toggled.image.color: {p['muted']}
menu.border.width: 1
menu.border.color: {p['border']}
menu.overlap: 0
menu.items.bg: flat solid
menu.items.bg.color: {p['menu']}
menu.items.text.color: {p['text']}
menu.items.disabled.text.color: {p['muted']}
menu.items.active.bg: flat solid
menu.items.active.bg.color: {p['pill']}
menu.items.active.text.color: {p['primary']}
menu.title.bg: flat solid
menu.title.bg.color: {p['side']}
menu.title.text.color: {p['text']}
menu.separator.color: {p['border']}
osd.border.width: 1
osd.border.color: {p['border']}
osd.bg: flat solid
osd.bg.color: {p['menu']}
osd.label.bg: parentrelative
osd.label.text.color: {p['text']}
osd.hilight.bg: flat solid
osd.hilight.bg.color: {p['primary']}
osd.unhilight.bg: flat solid
osd.unhilight.bg.color: {p['track']}
"""
    open(os.path.join(d, 'themerc'), 'w').write(t)
    rc = os.path.join(HOME, '.config/openbox/rc.xml')
    if os.path.exists(rc):
        x = open(rc).read(); n = 'Osborne-' + m
        x2 = re.sub(r'(<theme>\s*<name>)[^<]*(</name>)', r'\g<1>' + n + r'\g<2>', x, count=1)
        x2 = re.sub(r'(<titleLayout>)[^<]*(</titleLayout>)', r'\g<1>LIMC\g<2>', x2, count=1)
        if x2 != x: open(rc, 'w').write(x2)

def lxterminal(m):
    p = PAL[m]; d = os.path.join(HOME, '.config/lxterminal'); os.makedirs(d, exist_ok=True)
    pal16 = ('#2b2d36;#e5484d;#30a46c;#f5a524;#0a7cff;#8e4ec6;#12a594;#d0d3da;#6b6e79;#ff6369;#4cc38a;#ffc53d;#52a9ff;#a18072;#0bd8b6;#ffffff' if m == 'light' else
             '#383c45;#ff6369;#4cc38a;#ffc53d;#52a9ff;#c28ff6;#0bd8b6;#d0d3da;#6b6e79;#ff8589;#6adb9f;#ffd666;#8ec7ff;#d6b8f9;#5ee9d1;#ffffff')
    bg = '#ffffff' if m == 'light' else '#14161c'; fg = '#14151a' if m == 'light' else '#e8eaf0'
    conf = f"[general]\nfontname=JetBrains Mono 11\nselchars=-A-Za-z0-9,./?%&#:_\nscrollback=5000\nbgcolor={bg}\nfgcolor={fg}\npalette_color_0={pal16.split(';')[0]}\ndisallowbold=false\ncursorblinks=true\ncursorunderline=false\naudiblebell=false\nvisualbell=false\ntabpos=top\nhidescrollbar=true\nhidemenubar=true\nhideclosebutton=true\nhidepointer=false\ndisablef10=false\ndisablealt=false\nbgalpha=65535\n"
    for i, c in enumerate(pal16.split(';')): conf += 'palette_color_%d=%s\n' % (i, c)
    open(os.path.join(d, 'lxterminal.conf'), 'w').write(conf + "\n[shortcut]\n")

def dunst(m):
    p = _pal(m); d = os.path.join(HOME, '.config/dunst'); os.makedirs(d, exist_ok=True)
    open(os.path.join(d, 'dunstrc'), 'w').write(f"""[global]
monitor = 0
follow = mouse
width = (300, 360)
height = 140
origin = top-right
offset = 24x56
corner_radius = 18
frame_width = 1
frame_color = "{p['border']}"
separator_height = 0
padding = 14
horizontal_padding = 16
font = Inter 10
markup = full
format = "<b>%s</b>\\n%b"
icon_position = left
max_icon_size = 40
gap_size = 8
mouse_left_click = close_current
[urgency_low]
background = "{p['menu']}"
foreground = "{p['muted']}"
timeout = 5
[urgency_normal]
background = "{p['menu']}"
foreground = "{p['text']}"
timeout = 7
[urgency_critical]
background = "{p['menu']}"
foreground = "{p['text']}"
frame_color = "#ef4444"
timeout = 0
""")

def apply(m, reload=True):
    m = m if m in PAL else 'light'
    os.makedirs(os.path.join(HOME, '.config/osborne'), exist_ok=True); open(os.path.join(HOME, '.config/osborne/mode'), 'w').write(m)
    g = os.path.join(HOME, '.config/gtk-3.0'); os.makedirs(g, exist_ok=True)
    open(os.path.join(g, 'gtk.css'), 'w').write(gtk_css(m))
    dark = 'true' if m == 'dark' else 'false'
    open(os.path.join(g, 'settings.ini'), 'w').write(f"[Settings]\ngtk-theme-name=Adwaita\ngtk-icon-theme-name={'Papirus-Dark' if m=='dark' else 'Papirus'}\ngtk-font-name=Inter 10\ngtk-application-prefer-dark-theme={dark}\ngtk-cursor-theme-name=Adwaita\ngtk-enable-animations=true\n")
    g2 = os.path.join(HOME, '.config/gtk-4.0'); os.makedirs(g2, exist_ok=True)
    open(os.path.join(g2, 'gtk.css'), 'w').write(gtk_css(m)); open(os.path.join(g2, 'settings.ini'), 'w').write(f"[Settings]\ngtk-application-prefer-dark-theme={dark}\ngtk-font-name=Inter 10\n")
    openbox_theme(m); lxterminal(m); dunst(m)
    if reload:
        subprocess.run(['sh', '-c', "gsettings set org.gnome.desktop.interface color-scheme prefer-%s 2>/dev/null; gsettings set org.gnome.desktop.interface gtk-theme Adwaita 2>/dev/null; (openbox --reconfigure 2>/dev/null); (pkill -x dunst; setsid dunst >/dev/null 2>&1 &) 2>/dev/null; true" % m], timeout=8)
