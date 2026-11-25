"""V1 (causality: perturb-after-t + raw re-derivation), V2 (funding sign), V3 (entry price) on EXPLORE only."""
import json
import logging
import numpy as np
import pandas as pd
import common as C
import levz as L

C.setup_log()
log = logging.getLogger('checks')


def eq(a, b, tol=1e-9):
    if not np.isfinite(a) and not np.isfinite(b):
        return True
    if np.isfinite(a) != np.isfinite(b):
        return False
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def main():
    D = L.Data('2024-01')
    S = {W: L.signals(D, W) for W in L.WS}
    ra, rb = (L.ms('2022-01-01') - L.H0) // L.H, (L.ms('2024-01-01') - L.H0) // L.H
    rng = np.random.default_rng(L.SEED)
    rr, cc = np.nonzero(np.isfinite(S[14]['zoi'][ra:rb]) & D.U[ra:rb])
    pick = rng.choice(len(rr), size=200, replace=False)
    samp = sorted(zip((rr[pick] + ra).tolist(), cc[pick].tolist()))
    res = {}
    # V1a perturb everything after t
    bad = 0
    for r, c in samp:
        t = int(D.tms[r])
        for W in L.WS:
            Wh = W * 24
            X1 = D.X[:, [c]].copy()
            X1[r + 1:] = rng.normal(5.0, 3.0, size=X1[r + 1:].shape)
            CL1 = D.CL[:, [c]].copy()
            CL1[r:] = np.exp(rng.normal(0, 2.0, size=CL1[r:].shape))
            z1, _ = L.oi_z(X1, Wh)
            zr1 = L.ret_z(CL1, Wh)
            ok = eq(z1[r, 0], S[W]['zoi'][r, c]) and eq(zr1[r, 0], S[W]['zr'][r, c])
            fs = D.F.get(c)
            if fs is not None:
                fs1 = {k: v.copy() for k, v in fs.items()}
                m = fs1['ts'] > t - C.M_MS
                fs1['rate'][m] = rng.normal(0, 0.01, size=m.sum())
                fs1['r8'] = fs1['rate'] * 8.0 / fs1['ih']
                f1, zf1, _ = L.fund_z(fs1, D.tms, Wh)
                ok = ok and eq(f1[r], S[W]['f'][r, c]) and eq(zf1[r], S[W]['zf'][r, c])
            if not ok:
                bad += 1
                log.info('V1a MISMATCH r=%d c=%s W=%d', r, D.syms[c], W)
    res['V1a_samples'] = len(samp)
    res['V1a_mismatch'] = bad
    # V1b raw re-derivation of x(t), close(t), p0(t), f(t)
    bad_b = {'x': 0, 'cl': 0, 'p0': 0, 'f': 0}
    nchk = {'x': 0, 'cl': 0, 'p0': 0, 'f': 0}
    fund = pd.concat([C.read_funding(y, L.ms('2024-02-01')) for y in (2021, 2022, 2023, 2024)], ignore_index=True)
    byym = {}
    for r, c in samp:
        ym = pd.Timestamp(int(D.tms[r]), unit='ms').strftime('%Y-%m')
        byym.setdefault(ym, []).append((r, c))
    allm = C.months('2021-12', '2024-01')
    for ym, lst in sorted(byym.items()):
        i = allm.index(ym)
        mons = [allm[i - 1], ym] if i > 0 else [ym]
        syms = {D.syms[c] for _, c in lst}
        met = pd.concat([C.read_metrics(m) for m in mons], ignore_index=True)
        met = met[met['sym'].isin(syms)]
        kl = pd.concat([C.read_kline(m) for m in mons], ignore_index=True)
        kl = kl[kl['sym'].isin(syms)]
        for r, c in lst:
            t = int(D.tms[r])
            s = D.syms[c]
            m = met[(met['sym'] == s) & (met['ts'] <= t - 10 * C.M_MS) & (met['ts'] > t - 70 * C.M_MS) & (met['oi'] > 0)]
            xr = float(np.log(m.sort_values('ts')['oi'].iloc[-1])) if len(m) else np.nan
            nchk['x'] += 1
            bad_b['x'] += 0 if eq(xr, D.X[r, c]) else 1
            k = kl[(kl['sym'] == s) & (kl['ts'] >= t - 60 * C.M_MS) & (kl['ts'] <= t - C.M_MS)]
            clr = float(k.sort_values('ts')['close'].iloc[-1]) if len(k) else np.nan
            nchk['cl'] += 1
            bad_b['cl'] += 0 if eq(clr, D.CL[r - 1, c]) else 1
            k0 = kl[(kl['sym'] == s) & (kl['ts'] == t)]
            p0r = float(k0['close'].iloc[0]) if len(k0) else np.nan
            nchk['p0'] += 1
            bad_b['p0'] += 0 if eq(p0r, D.P0[r, c]) else 1
            fr = fund[(fund['sym'] == s) & (fund['ts'] <= t - C.M_MS)].sort_values('ts')
            if len(fr) and np.isfinite(S[14]['f'][r, c]):
                v = float(fr['rate'].iloc[-1] * 8.0 / fr['interval_h'].iloc[-1])
                nchk['f'] += 1
                bad_b['f'] += 0 if eq(v, S[14]['f'][r, c]) else 1
        del met, kl
    res['V1b_checked'] = nchk
    res['V1b_mismatch'] = bad_b
    # V2 / V3 from explore events
    a1 = pd.read_parquet('%s/events_A1_explore.parquet' % L.OUT)
    a2 = pd.read_parquet('%s/events_A2_explore.parquet' % L.OUT)
    a1 = a1[a1['nop'] == 0]
    a2 = a2[a2['nop'] == 0]
    v2 = []
    for _, e in a1[a1['fund_24'] > 0].sort_values('t0').head(3).iterrows():
        fr = fund[(fund['sym'] == e['sym']) & (fund['ts'] > e['te'] + C.M_MS) & (fund['ts'] <= e['te'] + 24 * L.H + C.M_MS)]
        v2.append(dict(sym=e['sym'], te=str(pd.Timestamp(int(e['te']), unit='ms')), settlements=[[str(pd.Timestamp(int(a), unit='ms')), float(b)] for a, b in zip(fr['ts'], fr['rate'])],
                       raw_sum=float(fr['rate'].sum()), fund_24=float(e['fund_24']), gross_24=float(e['gross_24']), net_24=float(e['net_24']),
                       net_minus_gross_plus_fee=float(e['net_24'] - e['gross_24'] + L.FEE)))
    res['V2'] = v2
    v3 = []
    smp = pd.concat([a1.sort_values('t0').iloc[::max(1, len(a1) // 5)].head(5), a2.sort_values('t0').iloc[::max(1, len(a2) // 5)].head(5)])
    for _, e in smp.iterrows():
        ym = pd.Timestamp(int(e['te']), unit='ms').strftime('%Y-%m')
        kl = C.read_kline(ym)
        k = kl[(kl['sym'] == e['sym']) & (kl['ts'] == int(e['te']))]
        pr = float(k['close'].iloc[0]) if len(k) else np.nan
        v3.append(dict(sym=e['sym'], te=str(pd.Timestamp(int(e['te']), unit='ms')), p_te=float(e['p_te']), raw_close_1m_open_te=pr, match=eq(pr, e['p_te'])))
        del kl
    res['V3'] = v3
    with open('%s/checks_explore.json' % L.OUT, 'w') as fh:
        json.dump(res, fh, indent=1, sort_keys=True, default=float)
    log.info('checks %s', json.dumps(res, default=float)[:3000])


if __name__ == '__main__':
    main()
