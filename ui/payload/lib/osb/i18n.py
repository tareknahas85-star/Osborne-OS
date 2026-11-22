"""Interface translation (English -> Levantine Arabic). Text that has no entry stays in English."""
import os
try: LANG = open(os.path.join(os.path.expanduser('~/.config/osborne'), 'lang')).read().strip()
except Exception: LANG = 'en'
_LOG = os.environ.get('OSB_I18N_LOG')
AR = {}
def tr(t):
    if _LOG and t:
        try: open(_LOG, 'a').write(t + '\n')
        except Exception: pass
    if LANG == 'ar' and t in AR: return AR[t]
    return t
try:
    if LANG == 'ar': from .i18n_ar import AR as _A; AR.update(_A)
except Exception: pass
