"""Weather for the top bar and the weather settings. Free services only (Open-Meteo, ipapi.co): no API key."""
import os, json, time, urllib.request, urllib.parse
from .common import CONF

CFGFILE = os.path.join(CONF, 'weather.json')
UA = {'User-Agent': 'Osborne-OS'}
WMO = {0: 'Clear', 1: 'Mostly clear', 2: 'Partly cloudy', 3: 'Cloudy', 45: 'Fog', 48: 'Fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
       61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 66: 'Freezing rain', 67: 'Freezing rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow',
       77: 'Snow grains', 80: 'Light showers', 81: 'Showers', 82: 'Heavy showers', 85: 'Snow showers', 86: 'Snow showers', 95: 'Thunderstorm',
       96: 'Thunderstorm with hail', 99: 'Thunderstorm with hail'}
DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

def icon_for(code):
    """Name of the top-bar weather icon for a WMO code."""
    c = code or 0
    if c in (0, 1): return 'wx-sun'
    if c in (2, 3): return 'wx-cloud'
    if c in (45, 48): return 'wx-fog'
    if c in (71, 73, 75, 77, 85, 86): return 'wx-snow'
    if c >= 95: return 'wx-storm'
    return 'wx-rain'

def load():
    try: return json.load(open(CFGFILE))
    except Exception: return {'mode': 'auto'}

def save(c):
    os.makedirs(CONF, exist_ok=True); json.dump(c, open(CFGFILE, 'w'))

def _get(url, timeout=10):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r: return json.loads(r.read(2_000_000).decode('utf-8', 'replace'))

def auto_location(cfg=None):
    """Find the city from the internet connection (cached for 6 hours)."""
    cfg = cfg if cfg is not None else load()
    a = cfg.get('auto') or {}
    if a.get('lat') is not None and time.time() - a.get('at', 0) < 6 * 3600: return a
    loc = None
    for url, f in (('https://ipapi.co/json/', lambda d: (d.get('latitude'), d.get('longitude'), d.get('city'))),
                   ('https://ipwho.is/', lambda d: (d.get('latitude'), d.get('longitude'), d.get('city')))):
        try:
            lat, lon, city = f(_get(url))
            if lat is not None and lon is not None: loc = dict(lat=float(lat), lon=float(lon), name=city or '', at=time.time()); break
        except Exception: pass
    if loc is None: raise IOError('could not find your location')
    cfg['auto'] = loc; save(cfg); return loc

def place(cfg=None):
    """(lat, lon, name) the widget should use right now."""
    cfg = cfg if cfg is not None else load()
    if cfg.get('mode') == 'manual' and cfg.get('lat') is not None: return cfg['lat'], cfg['lon'], cfg.get('name', '')
    a = auto_location(cfg); return a['lat'], a['lon'], a.get('name', '')

def forecast(lat, lon):
    q = urllib.parse.urlencode({'latitude': lat, 'longitude': lon, 'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m',
                                'daily': 'weather_code,temperature_2m_max,temperature_2m_min', 'timezone': 'auto', 'forecast_days': 4})
    d = _get('https://api.open-meteo.com/v1/forecast?' + q)
    cur = d['current']; daily = d['daily']
    days = []
    for i in range(1, min(4, len(daily['time']))):
        dt = time.strptime(daily['time'][i], '%Y-%m-%d')
        days.append(dict(day=DAYS[dt.tm_wday], hi=round(daily['temperature_2m_max'][i]), lo=round(daily['temperature_2m_min'][i]), text=WMO.get(daily['weather_code'][i], '')))
    return dict(temp=round(cur['temperature_2m']), humidity=cur.get('relative_humidity_2m'), wind=round(cur.get('wind_speed_10m', 0)),
                text=WMO.get(cur.get('weather_code'), ''), code=cur.get('weather_code'), days=days, at=time.time())

def search(name):
    q = urllib.parse.urlencode({'name': name, 'count': 6, 'language': 'en', 'format': 'json'})
    d = _get('https://geocoding-api.open-meteo.com/v1/search?' + q)
    out = []
    for r in d.get('results', []):
        label = ', '.join(x for x in (r.get('name'), r.get('admin1'), r.get('country')) if x)
        out.append(dict(label=label, name=r.get('name', ''), lat=r['latitude'], lon=r['longitude']))
    return out
