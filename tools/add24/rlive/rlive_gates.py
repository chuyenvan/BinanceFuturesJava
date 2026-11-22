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
    ap.add_argument('--lanes', required=True); ap.add_argument('--live-main', required=True); ap.add_argument('--live-other', required=True)
    ap.add_argument('--extra', nargs='*', default=[]); ap.add_argument('--v8-lane', default='L0')
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
    bad3 = [r['cid'] for r in sub if not (S <= int(r['log_ms']) < E + 120000)]
    man = json.load(open(a.fx + '/manifest.json'))
    lanes = a.lanes.split(',')
    for ln in lanes:
        for r in csv.DictReader(open(os.path.join(a.out_dir, ln, 'legs.csv'))):
            if not (S <= int(r['decision_ts']) < E):
                bad3.append(ln + ':' + r['cid'])
    g['V3'] = {'ok': not bad3 and man['START'] == S and man['END'] == E, 'violations': bad3[:20], 'fx_window': [man['START'], man['END']]}
    nsub = sum(1 for r in sub)
    g['V4'] = {'ok': nsub == a.v4_grep, 'parsed': nsub, 'grep': a.v4_grep}
    v5 = {ln: C0.lane_gate(os.path.join(a.out_dir, ln)) for ln in lanes}
    g['V5'] = {'ok': all(x['banners'] and all(x['banners'].values()) and x['env_missing_n'] == 0 and x['net_lines'] == 0 for x in v5.values()),
               'lanes': v5}
    v6 = {}
    for ln in lanes:
        res = json.load(open(os.path.join(a.out_dir, ln, 'result.json')))
        v6[ln] = {'minutes': (res.get('market') or {}).get('minutes'), 'expect': (E - S) // 60000, 'errors': len(res.get('errors', []))}
    # rig 11-17 (fx1105) cung xu ly 12959/12960 phut: phut cuoi [END-1', END) khong co nen sau de quyet dinh => chap nhan expect-1 (ghi ro)
    g['V6'] = {'ok': all(x['minutes'] in (x['expect'], x['expect'] - 1) and x['errors'] == 0 for x in v6.values()), 'lanes': v6}
    rx = re.compile(r'(jpype|py4j|jnius|subprocess|os\.system|\bjava\b\s*-)', re.I)
    v7 = {f: bool(rx.search(open(os.path.join(H, f)).read().split('"""', 2)[-1])) for f in ('ref_size.py', 'rlive_score.py')}
    g['V7'] = {'ok': not any(v7.values()), 'files_with_java_hint': [k for k, v in v7.items() if v]}
    p = subprocess.run([sys.executable, os.path.join(H, 'v8_check.py'), '--rig', os.path.join(a.out_dir, a.v8_lane), '--live-main', a.live_main,
                        '--live-other', a.live_other, '--out', os.path.join(a.out_dir, 'V8.json')], capture_output=True, text=True)
    g['V8'] = {'ok': p.returncode == 0, 'file': os.path.join(a.out_dir, 'V8.json')}
    g['ok'] = all(v['ok'] for k, v in g.items() if isinstance(v, dict) and 'ok' in v)
    json.dump(g, open(os.path.join(a.out_dir, 'gates.json'), 'w'), indent=1)
    print(json.dumps({k: (v['ok'] if isinstance(v, dict) else v) for k, v in g.items()}))
    return 0 if g['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
