"""Interface translation (English -> Levantine Arabic). Text that has no entry stays in English."""
import os
try: LANG = open(os.path.join(os.path.expanduser('~/.config/osborne'), 'lang')).read().strip()
except Exception: LANG = 'en'
_LOG = os.environ.get('OSB_I18N_LOG')
AR = {}
PACK = {}   # strings of a downloaded language pack (only when that language is selected)
def tr(t):
    if _LOG and t:
        try: open(_LOG, 'a').write(t + '\n')
        except Exception: pass
    if LANG == 'ar' and t in AR: return AR[t]
    if t in PACK: return PACK[t]
    return t
try:
    if LANG == 'ar': from .i18n_ar import AR as _A; AR.update(_A)
except Exception: pass
try:
    if LANG not in ('en', 'ar'):
        import json as _json
        _d = _json.load(open(os.path.join(os.path.expanduser('~/.config/osborne/lang-packs'), LANG + '.json')))
        PACK.update({k: v for k, v in _d.items() if not k.startswith('_') and isinstance(v, str)})
except Exception: pass
