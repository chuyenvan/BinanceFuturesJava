#!/usr/bin/env python3
"""ADD24 cong V8 (P6 + ERRATA3 A9 - danh sach khai truoc CHOT). MOI dong banner live in luc khoi dong 2026-11-20 06:17 (file trich
add24/a/v8_live_banner_full_1120_0617.txt) phai thuoc dung MOT muc bang PHAN_LOAI duoi; khong thuoc => CHUA_PHAN_LOAI => V8 FAIL.
  RIG  : so tung khoa=gia tri voi dong cung tag cua rig; khoa khac / chi-co-o-live => LECH tru khoa khai truoc (A9) cua tag do.
  ENV  : moi khoa phai duoc so (env rig = whitelist 11-16 + override, hoac su kien rig trong result.json) / khai truoc / la khoa TRANG THAI
         liet ke; khoa khac => LECH.
  NGOAI_RIG : duong production KHONG chay trong rig (vong feature / ops / san that) - liet ke cho A1 (cho khac production #1/#2).
  TRANG_THAI: dong trang thai luc khoi dong (dem, nap file, ket noi) - khong phai cau hinh; liet ke cho A1.
Khai truoc A9: moi gia tri la duong dan (chua '/'); PUSH/killSwitch/exists; [UNIVERSE-A1] sha256/serverTime/so symbol; [TS-EXT]
LIVE_TS_MKT_EXT + truong suy (X14, file, days_loaded); adapter; host.
usage: v8_check.py --rig <dir luot> --live <banner full txt> --out V8.json
"""
import argparse, json, re, sys

KV = re.compile(r'([A-Za-z0-9_().]+)=(\[[^\]]*\]|[^\s,;|)]+)')
DECL_ANY = {'adapter', 'host', 'PUSH', 'killSwitch', 'exists'}
DECL_TAG = {'UNIVERSE-A1': {'sha256', 'serverTime', '(TradFi', 'TradFi', 'INDEX', 'PREMARKET', 'symbol', 'unclassified'},
            'TS-EXT': {'LIVE_TS_MKT_EXT', 'X14', 'file', 'days_loaded'}, 'C3-LIVE': {'X14'}}
# (tag, chuoi con nhan dang dong, lop, dac ta)
# dac ta ENV: {khoa: ('env', TEN, ham) | ('res', khoa_result, ham) | ('state',)}; khoa '_' = kiem tren ca dong
B = lambda x: (lambda v: str(v).lower() in x)
TABLE = [
    ('LIVE-SIZING', '', 'RIG', {}),
    ('LIVE_PROFILE=c3_live', '', 'RIG', {}),
    ('C3-LEGACY', '', 'RIG', {}),
    ('LIVE-DCA-GRID', '', 'RIG', {}),
    ('GATE-RATIO', 'LIVE BAT', 'RIG', {}),
    ('GATE-RATIO', 'n?p buffer', 'TRANG_THAI', 'buffer gate - noi dung so o V10'),
    ('GATE-RATIO', 'buffer', 'TRANG_THAI', 'buffer gate - noi dung so o V10'),
    ('MINUTE-FIN', '', 'ENV', {'_': ('rigline', 'MINUTE-FIN', lambda live, rig: ('BAT' in live) == ('BAT' in (rig or ''))),
                              'LIVE_FIN_GUARD': ('state',)}),   # khoa trong dong live la HUONG DAN rollback, khong phai gia tri
    ('MINUTE-GUARD', '', 'ENV', {'_': ('env', 'LIVE_MINUTE_GUARD', lambda live, v: ('BAT' in live) == (v is None or v.strip() != '0'))}),
    ('UNIVERSE-A1', 'BAT', 'ENV', {'UNIVERSE_A1': ('env', 'UNIVERSE_A1', lambda lv, v: v == lv)}),
    ('UNIVERSE-A1', 'RELOAD', 'TRANG_THAI', 'nap lai exchangeInfo (sha256 khai truoc A9)'),
    ('GATE-QUOTA', '', 'ENV', {'SKIP_WHEN_FULL': ('env', 'GATE_QUOTA_SKIP_WHEN_FULL', lambda lv, v: (lv == 'ON') == (v == 'true'))}),
    ('CADENCE-SPLIT', 'MARKET_SCAN_MIN', 'ENV', {'MARKET_SCAN_MIN': ('env', 'MARKET_SCAN_MIN', lambda lv, v: lv == v)}),
    ('CADENCE-SPLIT-V2', '', 'ENV', {'MARKET_SCAN_PRIORITY': ('env', 'MARKET_SCAN_PRIORITY', lambda lv, v: lv == v)}),
    ('R4-1M', '', 'ENV', {'LIVE_ENTRY_GRID_MIN': ('env', 'LIVE_ENTRY_GRID_MIN', lambda lv, v: lv == v)}),
    ('SELECTOR_TIER1_NET015=true', '', 'ENV', {'_': ('env', 'SELECTOR_TIER1_NET015', lambda live, v: v == 'true')}),
    ('KILLSW', 'BAT mode=', 'ENV', {'mode': ('env', 'LIVE_KILLSW_MODE', lambda lv, v: lv == v), 'signed': ('env', 'LIVE_KILLSW_C2_SIGNED', lambda lv, v: lv == v),
                                    'file': ('state',)}),
    ('KILLSW', 'nap dinh equity', 'TRANG_THAI', 'dinh equity KS (trang thai file)'),
    ('KILLSW', 'nap file latch', 'TRANG_THAI', 'latch KS'),
    ('KILLSW', 'gan EquitySource', 'TRANG_THAI', 'gan nguon equity KS'),
    ('OPS', 'LIVE_PERIODIC_RESET_HOURS', 'ENV', {'LIVE_PERIODIC_RESET_HOURS': ('env', 'LIVE_PERIODIC_RESET_HOURS', lambda lv, v: lv.rstrip('h') == v),
                                                 'LIVE_KILLSW_MODE': ('env', 'LIVE_KILLSW_MODE', lambda lv, v: lv == v),
                                                 'profile': ('env', 'LIVE_PROFILE', lambda lv, v: lv == v),
                                                 'LIVE_HEARTBEAT': ('ngoai_rig',), 'file': ('state',), 'luc': ('state',), '(0': ('state',)}),
    ('GATE-PRE', "nguon 'dang giu'", 'ENV', {'_': ('res', 'held_mode', lambda live, v: ('C3_LIVE_BOOK' in live) == (v == 'OWN_BOOK'))}),
    ('GATE-PRE', 'nguon=', 'TRANG_THAI', 'dem theo phut (bo_dang_giu, a1_bo, ...)'),
    ('C3-LIVE', 'khoi dong adapter=', 'ENV', {'c3_capital': ('env', 'C3_CAPITAL', lambda lv, v: float(lv) == float(v)),
                                             'killSwitchArmed': ('rigfact', 'ks_armed_rig_entry', lambda lv, v: lv == 'true'),
                                             'tai_khoan': ('env_default', 'C3_ACCOUNT', lambda lv, v: v is None and lv.startswith('CHINH')),
                                             'gateway': ('adapter_derived',), 'stream': ('adapter_derived',), 'book': ('state',), 'cum': ('state',),
                                             'leg_treo': ('state',)}),
    ('C3-LIVE', 'UNIVERSE_A1=', 'ENV', {'UNIVERSE_A1': ('env', 'UNIVERSE_A1', lambda lv, v: lv.rstrip(',') == v)}),
    ('C3-LIVE', 'PUSH doi trang thai', 'TRANG_THAI', 'PUSH/killSwitch (khai truoc A9)'),
    ('C3-LIVE', 'client san sang', 'NGOAI_RIG', 'client REST san that (stub: 127.0.0.1:9)'),
    ('C3-LIVE', 'nap SymbolRules', 'TRANG_THAI', ''), ('C3-LIVE', 'khoi phuc sau restart', 'TRANG_THAI', ''),
    ('C3-LIVE', 'reconcile khoi dong', 'TRANG_THAI', ''),
    ('TS-EXT', 'BAT LIVE_TS_MKT_EXT', 'RIG', {}),
    ('TS-EXT', 'nap ', 'TRANG_THAI', 'nap co ngay (X14 tat o rig - K2)'), ('TS-EXT', 'status now=', 'TRANG_THAI', ''),
    ('TS-EXT', 'flag day=', 'TRANG_THAI', ''),
    ('FEAT-PIPE', 'LIVE_SEED_EXCLUDE_DECISION_MIN', 'ENV', {'LIVE_SEED_EXCLUDE_DECISION_MIN': ('env', 'LIVE_SEED_EXCLUDE_DECISION_MIN', lambda lv, v: lv.rstrip(':') == v)}),
    ('FEAT-PIPE', '', 'NGOAI_RIG', 'vong feature -> p15 (rig doc sel_dump live)'),
    ('LEGACY', '', 'TRANG_THAI', 'danh sach LEGACY (C3_EXCLUDE_LEGACY_HELD=false => khong anh huong c3)'),
    ('V11', '', 'NGOAI_RIG', 'funding fee manager (vong main)'),
    ('OPS-REFRESH', '', 'NGOAI_RIG', 'lam moi tai cho'), ('OPS-RESET', '', 'NGOAI_RIG', ''), ('OPS-PROC', '', 'TRANG_THAI', ''),
    ('SHADOW', '', 'TRANG_THAI', 'so giay (K3)'), ('C3-RATE', '', 'NGOAI_RIG', 'rate limit san that (rig dem X9)'),
    ('C3-LIVE-BOOK', '', 'TRANG_THAI', ''), ('C3-LIVE-EQ', '', 'TRANG_THAI', 'trang thai equity c3 (moc, funding)'),
    ('C5', '', 'NGOAI_RIG', 'AccountModeGuard san that'), ('C3-RULES', '', 'TRANG_THAI', ''), ('C3-LIVE-SCOPE', '', 'TRANG_THAI', ''),
    ('C3-LIVE-RECON', '', 'TRANG_THAI', ''), ('HEARTBEAT', '', 'NGOAI_RIG', ''), ('OI-LIVE', '', 'NGOAI_RIG', 'feature OI'),
    ('LIVE-KLINE', '', 'NGOAI_RIG', 'S1 ranker live'),
]
# khoa la HANG SO CODE trong class jar (khong env): bang nhau giua live va rig khi class giong byte (C0 (b): 0 entry khong-key khac).
#   TS-EXT: extH = TsMktExt.EXT_HOURS (TsMktExt.java:50), thr = AltEwIndex.DD_THRESHOLD, minN, profile (chuoi literal :153).
CODE_CONST = {'TS-EXT': {'profile', 'extH', 'thr', 'minN'}}
# khoa so voi khoa KHAC cua rig: TS-EXT baseH = LiveProfileC3.TIME_STOP_HOURS (TsMktExt.java:48) <-> rig [LIVE_PROFILE] timeStop
CROSS = {('TS-EXT', 'baseH'): ('LIVE_PROFILE=c3_live', 'timeStop', lambda lv, rv: rv == lv + 'h')}
C0_JSON = '/home/ubuntu/claude_master/w3/add24/a/C0.json'
TAGRX = re.compile(r'\] ([a-zA-Z.0-9]+): [^A-Za-z0-9]*\[([A-Za-z0-9_ =.-]+)\](.*)$')


def parse_lines(path):
    out = []
    for ln in open(path, errors='replace'):
        m = TAGRX.search(ln.rstrip('\n'))
        if m:
            out.append((m.group(2), m.group(3)))
    return out


def load_env(p):
    e = {}
    for ln in open(p):
        s = ln.strip()
        if s.startswith('export '):
            s = s[7:]
        s = s.split('#', 1)[0].strip()
        if re.match(r'^[A-Z0-9_]+=', s):
            k, v = s.split('=', 1)
            e[k] = v.split()[0] if v.strip() else ''
    return e


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig', required=True); ap.add_argument('--live', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    live = parse_lines(a.live)
    rigl = [x for x in parse_lines(a.rig + '/run.log') if not re.search(r' SUBMIT |TRAIL|FILL|TIME-STOP|DA DONG|HOURLY|status now=', x[1])]
    env = load_env(a.rig + '/env_used.sh')
    res = json.load(open(a.rig + '/result.json'))
    rigfact = {'ks_armed_rig_entry': 'true'}       # CrashDayRig: C3LiveEntry.KsGate.armed() = true (rig luon armed)
    rows, lech, unclassified = [], [], []
    try:
        c0 = json.load(open(C0_JSON)); c0_nonkey_same = c0['jar']['b_nonkey_diff'] == 0 and c0['jar']['stub_md5'] == 'cf0f479241265de68836716ee66a1866'
    except Exception:
        c0_nonkey_same = False
    for tag, body in live:
        ent = next((e for e in TABLE if e[0] == tag and e[1] in body), None)
        row = {'tag': tag, 'class': ent[2] if ent else 'CHUA_PHAN_LOAI', 'checks': [], 'lech': []}
        if ent is None:
            unclassified.append(tag); rows.append(row); continue
        kv = {k: v.rstrip(':,') for k, v in KV.findall(body)}
        if ent[2] == 'RIG':
            rv = {}
            rb = [b for t, b in rigl if t == tag]
            for b in rb:
                rv.update({k: v.rstrip(':,') for k, v in KV.findall(b)})
            if not rb:
                row['lech'].append('rig KHONG in tag')
            for k, v in kv.items():
                decl = k in DECL_ANY or k in DECL_TAG.get(tag, set()) or '/' in v
                if k not in rv and k in CODE_CONST.get(tag, set()):
                    ok = c0_nonkey_same
                    (row['checks'] if ok else row['lech']).append('%s hang so code (C0 b_nonkey_diff=0: %s)' % (k, ok))
                elif k not in rv and (tag, k) in CROSS:
                    t2, k2, fn = CROSS[(tag, k)]
                    r2 = {}
                    for t, b in rigl:
                        if t == t2:
                            r2.update({kk: vv.rstrip(':,') for kk, vv in KV.findall(b)})
                    ok = fn(v, r2.get(k2, ''))
                    (row['checks'] if ok else row['lech']).append('%s live=%s rig[%s].%s=%s' % (k, v, t2, k2, r2.get(k2)))
                elif k not in rv:
                    (row['checks'] if decl else row['lech']).append('%s chi-co-o-live%s' % (k, ' (khai truoc)' if decl else ''))
                elif rv[k] != v:
                    (row['checks'] if decl else row['lech']).append('%s live=%s rig=%s%s' % (k, v, rv[k], ' (khai truoc)' if decl else ''))
                else:
                    row['checks'].append('%s =' % k)
        elif ent[2] == 'ENV':
            spec = ent[3]
            for k, v in list(kv.items()) + ([('_', body)] if '_' in spec else []):
                sp = spec.get(k)
                decl = k in DECL_ANY or k in DECL_TAG.get(tag, set()) or ('/' in v and k != '_')
                if sp is None:
                    (row['checks'] if decl else row['lech']).append('%s khong anh xa%s' % (k, ' (khai truoc)' if decl else ''))
                    continue
                kind = sp[0]
                if kind in ('state', 'adapter_derived', 'ngoai_rig'):
                    row['checks'].append('%s %s' % (k, kind)); continue
                if kind in ('env', 'env_default'):
                    ok = sp[2](v, env.get(sp[1]))
                    src = '%s=%s' % (sp[1], env.get(sp[1]))
                elif kind == 'res':
                    ok = sp[2](v, res.get(sp[1])); src = 'result.%s=%s' % (sp[1], res.get(sp[1]))
                elif kind == 'rigline':
                    rb = ' || '.join(b for t, b in rigl if t == sp[1]); ok = sp[2](v, rb); src = 'rig [%s]' % sp[1]
                else:
                    ok = sp[2](v, rigfact.get(sp[1])); src = sp[1]
                (row['checks'] if ok else row['lech']).append('%s %s %s' % (k, 'OK' if ok else 'LECH', src))
        else:
            row['note'] = ent[3]
        lech += ['[%s] %s' % (tag, x) for x in row['lech']]
        rows.append(row)
    out = {'live_lines': len(live), 'rows': rows, 'lech': lech, 'chua_phan_loai': unclassified,
           'ok': not lech and not unclassified, 'class_count': {}}
    for r in rows:
        out['class_count'][r['class']] = out['class_count'].get(r['class'], 0) + 1
    out['verdict'] = 'PASS' if out['ok'] else 'FAIL'
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps({'verdict': out['verdict'], 'lech': lech, 'chua_phan_loai': unclassified, 'class_count': out['class_count']}, indent=0))
    return 0 if out['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
