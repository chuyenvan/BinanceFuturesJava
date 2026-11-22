#!/usr/bin/env python3
"""ADD24 cong V8 (P6): banner cau hinh cua rig phai TRUNG banner bot live in luc khoi dong 2026-11-20 06:17 (log pull242),
tru truong KHAI TRUOC la khac (adapter, duong dan, host, trang thai file KILL_SWITCH luc swap).
- Tag co ca o rig va live: so tung cap key=value (+ phan chu sau khi bo truong khai truoc).
- Tag live KHONG in o rig (vong main / ops khong chay trong rig): so gia tri banner voi env rig (whitelist + override) qua bang anh xa.
- Hang so bao size s9.3 (P7): F_BASE, SCALE, weights, ratio(leg0), sizeCap, U_MAX - lay tu banner; thieu => liet ke bien.
Chi doc: file banner da trich (add24/a/v8_live_banner_*), run.log + result.json + env_used.sh cua luot rig. Khong doc env.sh that.
usage: v8_check.py --rig <dir luot> --live-main <txt> --live-other <txt> --out v8.json
"""
import argparse, json, logging, re, sys

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('v8')
TAGS = ['LIVE-SIZING', 'LIVE_PROFILE=c3_live', 'C3-LEGACY', 'LIVE-DCA-GRID', 'UNIVERSE-A1', 'MINUTE-GUARD', 'MINUTE-FIN', 'GATE-RATIO',
        'GATE-QUOTA', 'TS-EXT', 'KILLSW', 'OPS', 'CADENCE-SPLIT', 'CADENCE-SPLIT-V2', 'R4-1M', 'FEAT-PIPE', 'SELECTOR_TIER1_NET015=true',
        'GATE-PRE', 'C3-LIVE', 'SHADOW', 'C3-RATE']
# truong khai truoc la khac (adapter / duong dan / host / trang thai file luc swap) - prereg P6
DECLARED = {'file', 'killSwitch', 'exists', 'adapter', 'gateway', 'book', 'tai_khoan', 'stream', 'ledger', 'state', 'dinh_luu', 'size',
            'firstTs', 'sha256', 'serverTime', 'days_loaded', 'open', 'realized',
            'PUSH',            # = ham cua killSwitch exists (file KILL_SWITCH do script swap dat luc khoi dong), khong phai cau hinh
            'LIVE_TS_MKT_EXT'}  # override khai truoc rig (X14 can ALT_EW Aerospike; K2: X14 khong kich trong OW2) - ERRATA_PROPOSED_A E-A4
KV = re.compile(r'([A-Za-z0-9_().]+)=(\[[^\]]*\]|[^\s,;|)]+)')
# tag live khong in o rig -> (regex trich gia tri live, ten env, ham so)
ENVMAP = [
    ('UNIVERSE-A1', r'\[UNIVERSE-A1\] BAT', 'UNIVERSE_A1', lambda m, v: v == '1'),
    ('GATE-QUOTA', r'SKIP_WHEN_FULL=ON', 'GATE_QUOTA_SKIP_WHEN_FULL', lambda m, v: v == 'true'),
    ('KILLSW', r'\[KILLSW\] BAT mode=(\w+)', 'LIVE_KILLSW_MODE', lambda m, v: v == m.group(1)),
    ('KILLSW', r'C2 signed=(\d)', 'LIVE_KILLSW_C2_SIGNED', lambda m, v: v == m.group(1)),
    ('OPS', r'LIVE_PERIODIC_RESET_HOURS=(\d+)h', 'LIVE_PERIODIC_RESET_HOURS', lambda m, v: v == m.group(1)),
    ('CADENCE-SPLIT', r'MARKET_SCAN_MIN=(\d+)', 'MARKET_SCAN_MIN', lambda m, v: v == m.group(1)),
    ('CADENCE-SPLIT-V2', r'MARKET_SCAN_PRIORITY=(\d+)', 'MARKET_SCAN_PRIORITY', lambda m, v: v == m.group(1)),
    ('R4-1M', r'LIVE_ENTRY_GRID_MIN=(\d+)', 'LIVE_ENTRY_GRID_MIN', lambda m, v: v == m.group(1)),
    ('FEAT-PIPE', r'LIVE_SEED_EXCLUDE_DECISION_MIN=(\d+)', 'LIVE_SEED_EXCLUDE_DECISION_MIN', lambda m, v: v == m.group(1)),
    ('SELECTOR_TIER1_NET015=true', r'SELECTOR_TIER1_NET015=(\w+)', 'SELECTOR_TIER1_NET015', lambda m, v: v == m.group(1)),
    ('TS-EXT', r'\[TS-EXT\] BAT LIVE_TS_MKT_EXT=(\d)', 'LIVE_TS_MKT_EXT', lambda m, v: v == m.group(1)),
    ('C3-LIVE', r'c3_capital=([0-9.]+)', 'C3_CAPITAL', lambda m, v: float(v) == float(m.group(1))),
    ('C3-LIVE', r'X14=(\w+)', 'LIVE_TS_MKT_EXT', lambda m, v: (v == '1') == (m.group(1) == 'true')),
    ('GATE-RATIO', r'pct=([0-9.]+)', 'LIVE_GATE_ROLLING_PCT', lambda m, v: abs(float(v) - float(m.group(1))) < 1e-8),
    ('GATE-RATIO', r'window=(\d+)d', 'LIVE_GATE_ROLLING_DAYS', lambda m, v: v == m.group(1)),
    ('GATE-RATIO', r'mode=(\w+)', 'LIVE_GATE_ROLLING_MODE', lambda m, v: v == m.group(1)),
]
# override khai truoc cua rig R-LIVE (prereg s5 + P6) - lech o day KHONG tinh la truot V8
DECL_ENV = {'LIVE_ADAPTER', 'LIVE_IS_SHADOW_HOST', 'LIVE_GATE_ROLLING_FILE', 'LIVE_TS_MKT_EXT'}


def strip(line):
    m = re.search(r'\] [a-zA-Z.0-9]+: (.*)$', line)
    return (m.group(1) if m else line).strip()


def tag_of(body):
    for t in sorted(TAGS, key=len, reverse=True):
        if '[' + t + ']' in body:
            return t
    return None


def banners(path, startup_only=False):
    out = {}
    for ln in open(path, errors='replace'):
        b = strip(ln)
        t = tag_of(b)
        if not t:
            continue
        if any(x in b for x in (' SUBMIT ', 'C3-LIVE-TRAIL', 'C3-LIVE-FILL', 'HOURLY', 'TIME-STOP', 'DA DONG', 'status now=')):
            continue
        out.setdefault(t, []).append(b)
    return out


def load_env(p):
    e = {}
    for ln in open(p):
        s = ln.strip()
        if s.startswith('export '):
            s = s[7:]
        s = s.split('#', 1)[0].strip()
        if '=' in s and re.match(r'^[A-Z0-9_]+=', s):
            k, v = s.split('=', 1)
            for part in [s] if ' ' not in v else [s]:
                pass
            e[k] = v.split()[0] if v else ''
    return e


def kvs(b):
    return {k: v for k, v in KV.findall(b)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig', required=True); ap.add_argument('--live-main', required=True); ap.add_argument('--live-other', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    live = banners(a.live_main)
    for t, v in banners(a.live_other).items():
        live.setdefault(t, []).extend(v)
    rig = banners(a.rig + '/run.log')
    env = load_env(a.rig + '/env_used.sh')
    res = {'live_tags': sorted(live), 'rig_tags': sorted(rig), 'both': [], 'env_map': [], 'mismatch': [], 'declared_diff': [],
           'size_constants': {}, 'missing_for_v8': []}
    for t in sorted(set(live) & set(rig)):
        L = {}
        for b in live[t]:
            L.update(kvs(b))
        R = {}
        for b in rig[t]:
            R.update(kvs(b))
        row = {'tag': t, 'equal': [], 'diff': [], 'declared': [], 'live_only': [], 'rig_only': []}
        for k in sorted(set(L) | set(R)):
            if k in L and k in R:
                if L[k] == R[k]:
                    row['equal'].append(k)
                elif k in DECLARED:
                    row['declared'].append('%s: live=%s rig=%s' % (k, L[k], R[k]))
                else:
                    row['diff'].append('%s: live=%s rig=%s' % (k, L[k], R[k]))
            elif k in L:
                row['live_only'].append(k)
            else:
                row['rig_only'].append(k)
        res['both'].append(row)
        res['mismatch'] += ['%s %s' % (t, d) for d in row['diff']]
        res['declared_diff'] += ['%s %s' % (t, d) for d in row['declared']]
    alltxt = {t: ' || '.join(v) for t, v in live.items()}
    for t, rx, name, f in ENVMAP:
        txt = alltxt.get(t, '')
        m = re.search(rx, txt)
        v = env.get(name)
        row = {'tag': t, 'env': name, 'live': m.group(0) if m else None, 'rig_env': v}
        if m is None:
            row['st'] = 'LIVE_KHONG_IN'
        elif v is None:
            row['st'] = 'RIG_THIEU_BIEN'
            res['missing_for_v8'].append(name)
        else:
            ok = f(m, v)
            row['st'] = 'OK' if ok else ('KHAI_TRUOC' if name in DECL_ENV else 'LECH')
            if not ok and name not in DECL_ENV:
                res['mismatch'].append('%s env %s: live "%s" rig %s=%s' % (t, name, m.group(0), name, v))
            elif not ok:
                res['declared_diff'].append('%s env %s: live "%s" rig %s=%s' % (t, name, m.group(0), name, v))
        res['env_map'].append(row)
    s = alltxt.get('LIVE-SIZING', '') + ' ' + alltxt.get('LIVE-DCA-GRID', '') + ' ' + alltxt.get('LIVE_PROFILE=c3_live', '')
    for k, rx in (('F_BASE', r'F_BASE=([0-9.]+)'), ('DCA_GRID_SCALE', r'DCA_GRID_SCALE=([0-9.]+)'), ('weights', r'weights=(\[[^\]]*\])'),
                  ('ratio_leg0', r'ratio\(leg0\)=([0-9.]+)'), ('sizeCap', r'sizeCap=([0-9.]+%)'), ('levels', r'levels=(\[[^\]]*\])'),
                  ('arm', r'arm=([0-9.]+)'), ('timeStop', r'timeStop=(\d+h)'), ('U_MAX', r'U_MAX=([0-9.]+)')):
        m = re.search(rx, s)
        res['size_constants'][k] = m.group(1) if m else None
        if m is None:
            res['missing_for_v8'].append('hang_so_bao_size:' + k)
    try:
        cfg = json.load(open(a.rig + '/result.json')).get('cfg_effective', {})
        res['rig_cfg_effective'] = cfg
    except Exception:
        res['rig_cfg_effective'] = None
    res['ok'] = not res['mismatch'] and not [x for x in res['missing_for_v8'] if not x.startswith('hang_so_bao_size:U_MAX')]
    res['verdict'] = 'PASS' if res['ok'] else 'FAIL'
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('verdict', 'mismatch', 'declared_diff', 'missing_for_v8', 'size_constants')}, indent=1))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
