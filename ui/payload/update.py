#!/usr/bin/env python3
"""Osborne OS updater (run as root).

Downloads the UI files from GitHub and runs install.sh. It does NOT need curl or raw.githubusercontent.com:
every file is tried on several routes (jsDelivr, raw.githubusercontent.com, api.github.com) and the first one that works is used,
so it also works on networks where only some GitHub hosts are reachable.

    sudo python3 /usr/local/lib/osborne/update.py
    curl -fsSL -H 'Accept: application/vnd.github.raw' https://api.github.com/repos/tareknahas85-star/Osborne-OS/contents/ui/update.py | sudo python3 -
"""
import os, sys, re, json, time, hashlib, shutil, subprocess, tempfile, urllib.request

OWNER, REPO, BRANCH = 'tareknahas85-star', 'Osborne-OS', 'main'
API = os.environ.get('OSB_API', 'https://api.github.com').rstrip('/')
RAW = os.environ.get('OSB_RAW', 'https://raw.githubusercontent.com').rstrip('/')
CDNS = [c for c in os.environ.get('OSB_CDN', 'https://cdn.jsdelivr.net,https://fastly.jsdelivr.net,https://gcore.jsdelivr.net').split(',') if c]
DATA = os.environ.get('OSB_DATA', 'https://data.jsdelivr.com').rstrip('/')
LOG = os.environ.get('OSB_LOG', '/var/log/osborne-update.log')
CACHE = os.environ.get('OSB_CACHE', '/var/cache/osborne/blobs')
VERFILE = os.environ.get('OSB_VERFILE', '/usr/local/lib/osborne/version')
UA = {'User-Agent': 'osborne-updater'}
dead = {}

def say(*a):
    s = ' '.join(str(x) for x in a)
    print(s, flush=True)
    try:
        with open(LOG, 'a') as f: f.write(s + '\n')
    except Exception: pass

def get(url, timeout=15, headers=None, limit=80 * 1024 * 1024):
    host = url.split('/')[2]
    if dead.get(host, 0) >= 2: raise IOError('%s skipped (unreachable)' % host)
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=dict(UA, **(headers or {}))), timeout=timeout) as r: data = r.read(limit)
        dead[host] = 0; return data
    except Exception as e:
        dead[host] = dead.get(host, 0) + 1; raise IOError('%s: %s' % (host, getattr(e, 'reason', e)))

def first(label, funcs):
    errs = []
    for f in funcs:
        try: return f()
        except Exception as e: errs.append(str(e))
    raise IOError('%s failed (%s)' % (label, '; '.join(dict.fromkeys(errs))[:300]))

def latest_sha():
    s = os.environ.get('OSB_SHA', '').strip()
    if re.fullmatch(r'[0-9a-f]{40}', s): return s
    def via_api():
        d = json.loads(get('%s/repos/%s/%s/commits/%s' % (API, OWNER, REPO, BRANCH), headers={'Accept': 'application/vnd.github+json'})); return d['sha']
    def via_cdn():
        d = json.loads(get('%s/v1/package/resolve/gh/%s/%s@%s' % (DATA, OWNER, REPO, BRANCH))); v = d.get('version', '')
        if not re.fullmatch(r'[0-9a-f]{40}', v): raise IOError('jsdelivr gave no commit id')
        return v
    def via_git():
        # plain git protocol over https: not rate limited like the REST API and never stale like a CDN
        t = get('https://github.com/%s/%s.git/info/refs?service=git-upload-pack' % (OWNER, REPO), headers={'User-Agent': 'git/2.43'}).decode('latin-1')
        m = re.search(r'([0-9a-f]{40}) refs/heads/%s\b' % re.escape(BRANCH), t)
        if not m: raise IOError('git refs had no %s' % BRANCH)
        return m.group(1)
    return first('finding the latest version', [via_api, via_git, via_cdn])

def list_files(sha):
    def via_api():
        d = json.loads(get('%s/repos/%s/%s/git/trees/%s?recursive=1' % (API, OWNER, REPO, sha), headers={'Accept': 'application/vnd.github+json'}, timeout=25))
        if d.get('truncated'): raise IOError('tree too large')
        return [(e['path'], e['sha'], e['size'] if 'size' in e else None) for e in d['tree'] if e['type'] == 'blob' and e['path'].startswith('ui/')]
    def via_cdn():
        d = json.loads(get('%s/v1/package/gh/%s/%s@%s/flat' % (DATA, OWNER, REPO, sha), timeout=25))
        return [(f['name'].lstrip('/'), None, f.get('size')) for f in d['files'] if f['name'].lstrip('/').startswith('ui/')]
    return first('reading the file list', [via_api, via_cdn])

def gitsha(data): return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()

def fetch_file(sha, path, bsha, size):
    cp = os.path.join(CACHE, bsha) if bsha else None
    if cp and os.path.isfile(cp):
        data = open(cp, 'rb').read()
        if gitsha(data) == bsha: return data
    srcs = []
    for c in CDNS: srcs.append(lambda c=c: get('%s/gh/%s/%s@%s/%s' % (c, OWNER, REPO, sha, path)))
    srcs.append(lambda: get('%s/%s/%s/%s/%s' % (RAW, OWNER, REPO, sha, path)))
    if bsha: srcs.append(lambda: get('%s/repos/%s/%s/git/blobs/%s' % (API, OWNER, REPO, bsha), headers={'Accept': 'application/vnd.github.raw'}))
    errs = []
    for s in srcs:
        try:
            data = s()
            if bsha and gitsha(data) != bsha: errs.append('checksum mismatch'); continue
            if size is not None and len(data) != size: errs.append('size mismatch'); continue
            if not bsha and not data: errs.append('empty'); continue
            if cp:
                try: os.makedirs(CACHE, exist_ok=True); open(cp, 'wb').write(data)
                except Exception: pass
            return data
        except Exception as e: errs.append(str(e))
    raise IOError('%s: %s' % (path, '; '.join(dict.fromkeys(errs))[:300]))

def main():
    if os.geteuid() != 0 and not os.environ.get('OSB_DRYRUN'): say('Run this as root (with sudo).'); return 1
    say('=== update %s ===' % time.strftime('%Y-%m-%d %H:%M:%S'))
    say('Looking for the latest version...')
    try: sha = latest_sha()
    except Exception as e: say('ERROR: %s' % e); say('Check that the internet connection works (GitHub could not be reached).'); return 20
    say('Latest version: %s' % sha[:7])
    try: files = list_files(sha)
    except Exception as e: say('ERROR: %s' % e); return 21
    if not any(p == 'ui/install.sh' for p, _, _ in files): say('ERROR: the update is incomplete (no installer found)'); return 22
    T = tempfile.mkdtemp(prefix='osb-upd-'); n = len(files)
    try:
        for i, (path, bsha, size) in enumerate(files, 1):
            try: data = fetch_file(sha, path, bsha, size)
            except Exception as e: say('ERROR: could not download %s' % e); return 23
            dst = os.path.join(T, path); os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'wb') as f: f.write(data)
            if path.endswith('.sh') or '/bin/' in path or '/sbin/' in path or path.endswith('.py') and '/lib/' not in path: os.chmod(dst, 0o755)
            if i == 1 or i % 6 == 0 or i == n: say('DL %d/%d  %s' % (i, n, os.path.basename(path)))
        say('Download finished (%d files). Installing...' % n)
        if os.environ.get('OSB_DRYRUN'): say('DRYRUN ok: %s' % T); return 0
        env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
        p = subprocess.Popen(['bash', os.path.join(T, 'ui', 'install.sh')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        for ln in p.stdout: say(ln.rstrip())
        rc = p.wait()
        if rc != 0: say('ERROR: the installer stopped (code %d)' % rc); return rc
        os.makedirs(os.path.dirname(VERFILE), exist_ok=True); open(VERFILE, 'w').write(sha + '\n')
        say('Update complete.'); return 0
    finally:
        if not os.environ.get('OSB_DRYRUN'): shutil.rmtree(T, ignore_errors=True)

if __name__ == '__main__':
    sys.exit(main())
