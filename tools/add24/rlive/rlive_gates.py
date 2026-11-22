#!/usr/bin/env python3
"""ADD24 cong V1-V8 TRUOC khi cham (prereg s11). Truot => KHONG cham (exit 1), sua dau vao (errata), khong doi tieu chi.
V1 sha256 moi dau vao; V2 kline du phut quanh moi SUBMIT live (thieu => liet ke, cum lien quan INSUFFICIENT - khong chan);
V3 moc thoi gian (live/rig/fixture trong cua so - vuot => HUY); V4 SUBMIT doc duoc == dem doc lap (grep); V5 banner + env thieu = rong
(c0_check.lane_gate); V6 rig xu ly du phut; V7 REF/bo cham khong import Java; V8 v8_check.
usage: rlive_gates.py --out-dir OUT --start --end --v4-grep N --lanes L0,L0-FOLLOW,L0-DRY --live-main --live-other --extra k=path ...
"""
import argparse, csv, gzip, hashlib, json, os, re, sys, subprocess
from datetime import datetime, timedelta, timezone

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..'))
import c0_check as C0
TZ7 = timezone(timedelta(hours=7))


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def ms7(s):
    return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', required=True); ap.add_argument('--fx', required=True); ap.add_argument('--live', required=True)
    ap.add_argument('--start', required=True); ap.add_argument('--end', required=True); ap.add_argument('--v4-grep', type=int, required=True)
    ap.add_argument('--lanes', required=True); ap.add_argument('--live-banner', required=True)
    ap.add_argument('--extra', nargs='*', default=[]); ap.add_argument('--v8-lane', default='L0')
    ap.add_argument('--v4b', required=True, help='v4b.json (v4b.sh)'); ap.add_argument('--v10', default='', help='V10.json (v10_buffer.py); rong => CHUA CHAY = truot')
    ap.add_argument('--mark', default='')
    a = ap.parse_args()
    S, E = ms7(a.start), ms7(a.end)
    g = {}
    v1 = {}
    for d in (a.fx, a.live):
        for f in sorted(os.listdir(d)):
            p = os.path.join(d, f)
            if os.path.isfile(p):
                v1[p] = sha(p)
    for kv in a.extra:
        k, p = kv.split('=', 1); v1[k + ':' + p] = sha(p)
    g['V1'] = {'ok': True, 'n': len(v1), 'sha256': v1}
    bars = set()
    for r in csv.DictReader(gzip.open(a.fx + '/klines.csv.gz', 'rt')):
        bars.add((r['symbol'], int(r['t'])))
    sub = list(csv.DictReader(open(a.live + '/submit.csv')))
    miss = []
    for r in sub:
        d = int(r['cid'].split('-')[-2]) * 60000
        for t in (d - 120000, d - 60000, d, d + 60000):
            if (r['symbol'], t) not in bars:
                miss.append('%s@%d' % (r['symbol'], t))
    g['V2'] = {'ok': True, 'missing_n': len(miss), 'missing': miss[:100], 'note': 'thieu => cum lien quan INSUFFICIENT'}
    # V3 (ERRATA3 A10: phu MOI dau vao): moi ban ghi thoi gian < END; >= START - 1 ngay (lich su cho cua so 15', mkt MKT_PRE, nen UTC
    #   dau ngay) - khai ro; live parse: moi log_ms trong [START, END); rig: moi decision_ts trong [START, END)
    bad3 = []
    lo = S - 86400000
    for f, col in (('klines.csv.gz', 't'), ('mkt.csv.gz', 't'), ('sel.csv.gz', 'ts')) + ((('mark.csv.gz', 't'),) if os.path.exists(a.fx + '/mark.csv.gz') else ()):
        p = os.path.join(a.fx, f)
        if os.path.exists(p):
            for r in csv.DictReader(gzip.open(p, 'rt')):
                t = int(r[col])
                if not (lo <= t < E) or (f == 'sel.csv.gz' and not (S <= t < E)):
                    bad3.append('%s:%d' % (f, t)); break
    for f in sorted(os.listdir(a.live)):
        if f.endswith('.csv'):
            for r in csv.DictReader(open(os.path.join(a.live, f))):
                if 'log_ms' in r and not (S <= int(r['log_ms']) < E):
                    bad3.append('%s:%s' % (f, r['log_ms'])); break
    man = json.load(open(a.fx + '/manifest.json'))
    lanes = a.lanes.split(',')
    for ln in lanes:
        for r in csv.DictReader(open(os.path.join(a.out_dir, ln, 'legs.csv'))):
            if not (S <= int(r['decision_ts']) < E):
                bad3.append(ln + ':' + r['cid'])
    g['V3'] = {'ok': not bad3 and man['START'] == S and man['END'] == E, 'violations': bad3[:20], 'fx_window': [man['START'], man['END']],
               'lookback_allowed_ms': 86400000,
               'lookback_from': datetime.fromtimestamp(lo / 1000, TZ7).strftime('%Y-%m-%d %H:%M +07'),
               'ghi_chu': 'ERRATA4 s2: doc du lieu van hanh / thi truong tu START - 1 ngay (lich su cua so 15 phut, nen UTC dau ngay) toi T_cut'}
    nsub = len(sub)
    g['V4'] = {'ok': nsub == a.v4_grep, 'parsed': nsub, 'grep': a.v4_grep}
    v4b = json.load(open(a.v4b))
    g['V4b'] = {'ok': bool(v4b.get('ok')), 'file': a.v4b, 'unmatched': v4b.get('unmatched_c3live_lines'),
                'bad_rules': [k for k, v in v4b.get('rules', {}).items() if not v['ok']]}
    v5 = {ln: C0.lane_gate(os.path.join(a.out_dir, ln)) for ln in lanes}
    g['V5'] = {'ok': all(x['banners'] and all(x['banners'].values()) and x['env_missing_n'] == 0 and x['net_lines'] == 0
                         and x['jar_check_ok'] is True for x in v5.values()),
               'lanes': v5}
    v6 = {}
    for ln in lanes:
        res = json.load(open(os.path.join(a.out_dir, ln, 'result.json')))
        v6[ln] = {'minutes': (res.get('market') or {}).get('minutes'), 'expect': (E - S) // 60000, 'errors': len(res.get('errors', []))}
    # rig 11-17 (fx1105) cung xu ly 12959/12960 phut: phut cuoi [END-1', END) khong co nen sau de quyet dinh => chap nhan expect-1 (ghi ro)
    g['V6'] = {'ok': all(x['minutes'] in (x['expect'], x['expect'] - 1) and x['errors'] == 0 for x in v6.values()), 'lanes': v6}
    import ast   # V7: REF + bo cham KHONG import cau noi Java / chay tien trinh (kiem AST, khong theo chu trong comment)
    BADMOD = {'jpype', 'py4j', 'jnius', 'subprocess'}
    def java_hint(f):
        tree = ast.parse(open(os.path.join(H, f)).read())
        for nd in ast.walk(tree):
            if isinstance(nd, ast.Import) and any(x.name.split('.')[0] in BADMOD for x in nd.names):
                return True
            if isinstance(nd, ast.ImportFrom) and (nd.module or '').split('.')[0] in BADMOD:
                return True
            if isinstance(nd, ast.Attribute) and nd.attr in ('system', 'popen') and getattr(nd.value, 'id', '') == 'os':
                return True
        return False
    v7 = {f: java_hint(f) for f in ('ref_size.py', 'rlive_score.py')}
    g['V7'] = {'ok': not any(v7.values()), 'files_with_java_hint': [k for k, v in v7.items() if v]}
    p = subprocess.run([sys.executable, os.path.join(H, 'v8_check.py'), '--rig', os.path.join(a.out_dir, a.v8_lane), '--live', a.live_banner,
                        '--out', os.path.join(a.out_dir, 'V8.json')], capture_output=True, text=True)
    g['V8'] = {'ok': p.returncode == 0, 'file': os.path.join(a.out_dir, 'V8.json')}
    v10 = json.load(open(a.v10)) if a.v10 and os.path.exists(a.v10) else None
    g['V10a'] = {'ok': bool(v10 and v10.get('V10a_ok')), 'file': a.v10 or 'CHUA CHAY',
                 'domain_minutes': (v10 or {}).get('domain_minutes'), 'V10a_mismatch_minutes': (v10 or {}).get('V10a_mismatch_minutes')}
    g['ok'] = all(v['ok'] for k, v in g.items() if isinstance(v, dict) and 'ok' in v)
    json.dump(g, open(os.path.join(a.out_dir, 'gates.json'), 'w'), indent=1)
    print(json.dumps({k: (v['ok'] if isinstance(v, dict) else v) for k, v in g.items()}))
    return 0 if g['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
