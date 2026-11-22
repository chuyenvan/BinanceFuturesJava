#!/usr/bin/env python3
"""ADD24 R-SIM verification gates (V1,V2,V3,V5,V6,V9) for a rig run. usage: gates_rsim.py <RUN_DIR> <FX_DIR>. Prints JSON. No PnL."""
import csv, gzip, json, re, subprocess, sys, zlib
from datetime import datetime, timezone, timedelta
D, FX = sys.argv[1], sys.argv[2]
TZ7 = timezone(timedelta(hours=7)); TS_MAX = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
g = {}
fxc = json.load(open(FX + '/fx_check.json')); mc = json.load(open(FX + '/manifest_conv.json'))
res = json.load(open(D + '/result.json'))
g['V1'] = dict(ok=bool(fxc.get('files')) and bool(mc.get('inputs')), fx_files_md5=fxc.get('files'), conv_inputs=mc.get('inputs'),
               jar_md5=res.get('jar_check', {}).get('jar_md5'))
g['V2'] = dict(ok=not fxc['V2_cums_with_missing'], missing=fxc['V2_cums_with_missing'])
g['V3'] = dict(ok=bool(fxc['V3_ok']) and fxc['klines_ts_max'] <= TS_MAX and mc['TS_MAX'] == TS_MAX
               and all(v.get('ts_max', 0) <= TS_MAX for v in mc['inputs'].values() if isinstance(v, dict) and 'ts_max' in v),
               klines_ts_max=fxc['klines_ts_max'])
log = open(D + '/run.log', encoding='utf-8', errors='replace').read()
ban = {b: bool(re.search(r'\[' + re.escape(b) + r'\]', log)) for b in ('LIVE-SIZING', 'LIVE-DCA-GRID', 'GATE-RATIO')}
bh = res.get('banners_harness', '')
ec = res.get('env_check', {})
g['V5'] = dict(ok=all(ban.values()) and 'LiveGridSizing.on=true' in bh and 'LiveDcaGridC3.active=true' in bh and 'fin=true' in bh
               and 'TsMktExt.enabled=true' in bh and not ec.get('missing_names_not_overridden') and not ec.get('differ_not_overridden'),
               banners=ban, harness=bh, env_missing=ec.get('missing_names_not_overridden'), env_differ=ec.get('differ_not_overridden'))
nmin = sum(1 for _ in open(D + '/market.csv')) - 1
sel_min = len({ln.split(',', 1)[0] for ln in gzip.open(FX + '/sel.csv.gz', 'rt') if not ln.startswith('ts')})
exc = len(re.findall(r'Exception|\bERROR\b', log))
meta = open(D + '/add24_meta.txt').read() if __import__('os').path.exists(D + '/add24_meta.txt') else ''
g['V6'] = dict(ok=nmin == sel_min and not res.get('errors') and not res.get('log_errors') and exc == 0 and 'swapped' in meta,
               minutes_processed=nmin, sel_minutes=sel_min, errors=res.get('errors'), log_errors=res.get('log_errors'),
               exception_lines=exc, ks_any_latch=res.get('ks_any_latch'), x14_meta=meta.strip())
import gzip as _gz
simq = {}
for ln in _gz.open('/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/logs/sim.out.gz', 'rt', errors='replace'):
    if 'GATE-RATIO on pct' in ln:
        for q, a, b in re.findall(r'(\d{4}Q\d):(\d+)/(\d+)', ln): simq[q] = int(b)
fq = fxc.get('fed_by_quarter', {})
WQ = {'1767200400000': '2026Q1', '1774976400000': '2026Q2'}   # quarter fully covered by warm-up stream
v9 = {}
for q, n in fq.items():
    full = (q == '2026Q1' and mc['W0'] <= 1767200400000 and mc['LO'] >= 1774976400000) or (q == '2026Q2' and mc['W0'] <= 1774976400000 and mc['LO'] >= 1782838800000)
    if full and q in simq: v9[q] = dict(reconstructed=n, sim_log=simq[q], ratio=n / simq[q], ok=abs(n / simq[q] - 1) <= 1e-4)
g['V9'] = dict(ok=bool(v9) and all(x['ok'] for x in v9.values()), quarters=v9, fed_by_quarter=fq, sim_log_seen=simq,
               warm_rows=fxc.get('warm_rows'), warm_from=fxc.get('warm_from'))
g['ALL_OK'] = all(g[k]['ok'] for k in ('V1', 'V2', 'V3', 'V5', 'V6', 'V9'))
print(json.dumps(g, indent=1, default=str))
