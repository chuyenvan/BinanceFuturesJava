"""V0: data coverage check (metadata + counts only, no signals)."""
import json
import logging
import numpy as np
import pandas as pd
import common as C

C.setup_log()
log = logging.getLogger('v0')


def main():
    u = C.universe_days()
    u = u[(u.day >= '2021-12-01') & (u.day < '2026-01-01')]
    u['ym'] = u.day.dt.strftime('%Y-%m')
    res = {}
    cov_rows = []
    fund = {y: C.read_funding(y) for y in range(2021, 2026)}
    for ym in C.months():
        k = C.read_kline(ym)
        k['day'] = pd.to_datetime(k.ts // 86400000 * 86400000, unit='ms')
        g = k.groupby('sym')['ts'].agg(['count', 'min', 'max'])
        span = (g['max'] - g['min']) // C.M_MS + 1
        frac_cont = float((g['count'] / span).median())
        dup = int(k.duplicated(['sym', 'ts']).sum())
        offmin = int((k.ts % C.M_MS != 0).sum())
        cd = k.groupby(['sym', 'day']).size().rename('nmin').reset_index()
        m = C.read_metrics(ym)
        msyms = set(m.sym.unique())
        y = int(ym[:4])
        f = fund[y]
        fm = f[pd.to_datetime(f.ts, unit='ms').dt.strftime('%Y-%m') == ym]
        fsyms = set(fm.sym.unique())
        uu = u[u.ym == ym].merge(cd, on=['sym', 'day'], how='left')
        uu['nmin'] = uu['nmin'].fillna(0)
        usyms = set(uu.sym.unique())
        ksyms = set(g.index)
        r = dict(rows=int(len(k)), nsym=len(ksyms), min_per_sym_med=float(g['count'].median()),
                 min_per_sym_min=int(g['count'].min()), cont_frac_med=frac_cont, dup=dup, off_minute=offmin,
                 met_nsym=len(msyms), met_rows=int(len(m)), fund_nsym=len(fsyms), univ_nsym=len(usyms),
                 univ_cd=int(len(uu)), univ_cd_any=int((uu.nmin > 0).sum()), univ_cd_95=int((uu.nmin >= 1368).sum()),
                 univ_cd_full=int((uu.nmin >= 1440).sum()),
                 univ_cd_met=int(uu.sym.isin(msyms).sum()), univ_cd_fund=int(uu.sym.isin(fsyms).sum()),
                 univ_not_in_kl=sorted(usyms - ksyms)[:15], univ_not_in_met=sorted(usyms - msyms)[:15])
        res[ym] = r
        log.info('%s %s', ym, json.dumps(r))
        del k, m, cd
    yr = {}
    for ym, r in res.items():
        y = ym[:4]
        a = yr.setdefault(y, dict(univ_cd=0, any=0, p95=0, full=0, met=0, fund=0))
        a['univ_cd'] += r['univ_cd']; a['any'] += r['univ_cd_any']; a['p95'] += r['univ_cd_95']
        a['full'] += r['univ_cd_full']; a['met'] += r['univ_cd_met']; a['fund'] += r['univ_cd_fund']
    for y, a in yr.items():
        for kk in ('any', 'p95', 'full', 'met', 'fund'):
            a[kk + '_pct'] = round(100.0 * a[kk] / max(a['univ_cd'], 1), 3)
        log.info('YEAR %s %s', y, json.dumps(a))
    json.dump(dict(months=res, years=yr), open(C.WORK + '/v0.json', 'w'), indent=1, sort_keys=True)


if __name__ == '__main__':
    main()
