"""osb-calc: calculator in the Osborne design."""
import ast, operator, sys, subprocess
from .common import *

OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}
def ev(node):
    if isinstance(node, ast.Expression): return ev(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS: return OPS[type(node.op)](ev(node.left), ev(node.right))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)): return -ev(node.operand) if isinstance(node.op, ast.USub) else ev(node.operand)
    raise ValueError

def fmt(v):
    if isinstance(v, float) and v == int(v) and abs(v) < 1e15: return str(int(v))
    s = ('%.10g' % v) if isinstance(v, float) else str(v); return s

KEYS = [['AC', '⌫', '%', '÷'], ['7', '8', '9', '×'], ['4', '5', '6', '−'], ['1', '2', '3', '+'], ['±', '0', '.', '=']]

class Calc(OsbWindow):
    def __init__(self):
        cw, ch, m = px(340), px(520), px(40)
        super().__init__(cw, ch, m, None, 'Calculator'); self.shadow = (28, 16, 32)
        self.set_wmclass('osb-calc', 'Osb-calc'); self.set_position(Gtk.WindowPosition.CENTER); self.enable_escape()
        self.put(Box('win', cw, ch), 0, 0); traffic_lights(self, 16, 18)
        self.expr = ''; self.last = ''
        self.hist = make_label('', 11, 'normal', 'muted', xalign=1.0, w=px(300), h=px(18)); self.put(self.hist, px(20), px(58))
        self.disp = make_label('0', 44, 'bold', 'text', xalign=1.0, spacing=-1, w=px(300), h=px(64)); self.put(self.disp, px(20), px(80))
        for r, row in enumerate(KEYS):
            for c, k in enumerate(row):
                b = Gtk.Button(label=k); b.set_size_request(px(68), px(62)); sc = b.get_style_context(); sc.add_class('osb-key')
                if k in '÷×−+%': sc.add_class('osb-op')
                if k == '=': sc.add_class('osb-eq')
                b.connect('clicked', lambda w, k=k: self.press(k)); self.put(b, px(20 + c * 76), px(170 + r * 70))
        self.connect('key-press-event', self.key)
    def show(self, t): self.disp.set_text(t or '0')
    def key(self, w, e):
        n = Gdk.keyval_name(e.keyval); m = {'Return': '=', 'KP_Enter': '=', 'BackSpace': '⌫', 'Escape': 'AC', 'asterisk': '×', 'KP_Multiply': '×', 'slash': '÷', 'KP_Divide': '÷', 'minus': '−', 'KP_Subtract': '−', 'plus': '+', 'KP_Add': '+', 'period': '.', 'KP_Decimal': '.', 'percent': '%'}
        k = m.get(n) or (e.string if e.string and e.string in '0123456789' else None)
        if k == 'AC' and n == 'Escape': return False
        if k: self.press(k); return True
        return False
    def press(self, k):
        if k == 'AC': self.expr = ''; self.hist.set_text(''); self.show('0'); return
        if k == '⌫': self.expr = self.expr[:-1]; self.show(self.expr); return
        if k == '±':
            if self.expr.startswith('-'): self.expr = self.expr[1:]
            elif self.expr: self.expr = '-' + self.expr
            self.show(self.expr); return
        if k == '=':
            try:
                e = self.expr.replace('×', '*').replace('÷', '/').replace('−', '-').replace('%', '/100')
                r = ev(ast.parse(e, mode='eval')); self.hist.set_text(self.expr + ' ='); self.expr = fmt(r); self.show(self.expr)
            except ZeroDivisionError: self.expr = ''; self.show('Cannot divide by 0')
            except Exception: self.show('Error'); self.expr = ''
            return
        if k in '÷×−+' and not self.expr: 
            if k == '−': self.expr = '-'; self.show(self.expr)
            return
        if k in '÷×−+' and self.expr and self.expr[-1] in '÷×−+': self.expr = self.expr[:-1]
        self.expr += k; self.show(self.expr)

def main():
    init_mode(); w = Calc(); w.connect('destroy', Gtk.main_quit); w.show_all(); watch_mode(lambda m: w.queue_draw()); Gtk.main()
