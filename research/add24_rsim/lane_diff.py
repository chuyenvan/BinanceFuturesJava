#!/usr/bin/env python3
"""ERRATA2 2b: so lane DO NHAY (O-H-L-C) voi lane CHINH (O-L-H-C): so cum doi phut thoat, phan bo Delta gia thoat (%) sens vs chinh. Khong PnL."""
import json, sys, statistics
a = {(o['sym'], o['start']): o for o in json.load(open(sys.argv[1]))['rows'] if o.get('rig_exit_ms')}
b = {(o['sym'], o['start']): o for o in json.load(open(sys.argv[2]))['rows'] if o.get('rig_exit_ms')}
ks = sorted(set(a) & set(b)); MIN = 60000
chg = [k for k in ks if a[k]['rig_exit_ms'] // MIN != b[k]['rig_exit_ms'] // MIN]
d = sorted(100 * (b[k]['rig_exit_px'] - a[k]['rig_exit_px']) / a[k]['rig_exit_px'] for k in ks)
q = lambda p: d[min(len(d) - 1, int(p * (len(d) - 1)))] if d else None
print(json.dumps(dict(n_common=len(ks), only_main=len(set(a) - set(b)), only_sens=len(set(b) - set(a)), exit_minute_changed=len(chg),
                      delta_px_pct=dict(mean=(statistics.mean(d) if d else None), p05=q(0.05), p25=q(0.25), median=q(0.5), p75=q(0.75), p95=q(0.95), min=(d[0] if d else None), max=(d[-1] if d else None)),
                      changed=[(k[0], k[1], (b[k]['rig_exit_ms'] - a[k]['rig_exit_ms']) // MIN) for k in chg][:40]), indent=1))
