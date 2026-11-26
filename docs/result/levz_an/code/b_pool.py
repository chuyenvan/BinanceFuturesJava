"""B: candidate pool size per year + independent per-candidate short outcomes under 3 FIXED exits (no portfolio);
+ descriptive feature quintiles (pooled edges, split by year) on the W7/W14 E0 z>=2.5 episode pool.
Counting: cond = u & z_oi>=z & z_f>=z & f>1e-4 & 1m bar at T_k (E0, same as B0 candidates()); episode = first hour per coin with
cooldown 72 h from the episode start (tier-1 levz.episodes logic). Years by T_k (UTC), 2022..2025 only.
Outputs out/b_counts.parquet, out/b_outcomes.parquet, out/b_feat_quint.parquet, out/b_feat_spear.parquet, out/b_cands.parquet."""
import sys
import os
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.b')
ZS = (1.0, 1.5, 2.0, 2.5, 3.0, 3.5)
EXITS = {'SL15_H24_t10/5': (0.15, 24, 0.10, 0.05), 'SL30_H72_t10/5': (0.30, 72, 0.10, 0.05), 'SL50_H24_off': (0.50, 24, 0.0, 0.0)}
FEATS = ('z_oi', 'z_f', 'f', 'doi24', 'r24', 'qv30', 'age_d', 'hod', 'btc7', 'ew7')
COOL = 72


def episodes(rows, cols):
    o = np.lexsort((rows, cols))
    rows, cols = rows[o], cols[o]
    keep = np.zeros(len(rows), dtype=bool)
    lr, lc = -10**9, -1
    for i, (r, c) in enumerate(zip(rows.tolist(), cols.tolist())):
        if c != lc or r - lr > COOL:
            keep[i] = True
            lr, lc = r, c
    return rows[keep], cols[keep]


def year_of_k(k):
    return A.dts(A.H0 + np.asarray(k, dtype=np.int64) * A.H).year.values


def main():
    A.setup_log('b_pool')
    CB, P, X = A.b1()
    syms = A.meta()['syms']
    hz = np.load(CB.WORK + '/hourly.npz')
    has1m, CLH = hz['has1m'], hz['CLH']
    k0, kl = A.dev_k()
    cnt = []
    sig = {}
    for W in (7, 14):
        G = A.dense_sig(W, syms)
        sig[W] = G
        for z in ZS:
            with np.errstate(invalid='ignore'):
                m = G['u'] & (G['z_oi'] >= z) & (G['z_f'] >= z) & (G['f'] > 1e-4) & has1m
            r, c = np.nonzero(m)
            er, ec = episodes(r, c)
            for nm, rr in (('hours', r), ('episodes', er)):
                y = year_of_k(rr)
                for yy in (2022, 2023, 2024, 2025):
                    cnt.append(dict(W=W, zmin=z, kind=nm, year=yy, n=int((y == yy).sum())))
            log.info('W%d z%.1f hours=%d episodes=%d', W, z, len(r), len(er))
    pd.DataFrame(cnt).to_parquet(A.OUT + '/b_counts.parquet', index=False)
    # outcomes for z>=2.5 pool (exit table exists)
    T = X.load_table()
    cz = np.load(CB.WORK + '/cand_b1.npz')
    X_oi = A.dense_oi(syms)
    qv30 = A.dense_qv30(syms)
    btc7, ew7 = A.market(CLH, has1m, sig[7]['u'], syms)
    first = np.load(CB.WORK + '/gaps.npz')['first']
    outs, cands = [], []
    for W in (7, 14):
        key = 'W%d_E0_2.5' % W
        ck, cc, cid = cz[key + '_k'], cz[key + '_c'], cz[key + '_cid']
        sel = (ck >= k0) & (ck < kl)
        ck, cc, cid = ck[sel], cc[sel], cid[sel]
        er, ec = episodes(ck, cc)
        ep = set(zip(er.tolist(), ec.tolist()))
        isep = np.array([(a, b) in ep for a, b in zip(ck.tolist(), cc.tolist())])
        df = pd.DataFrame({'W': W, 'k': ck, 'c': cc, 'cid': cid, 'episode': isep, 'year': year_of_k(ck)})
        G = sig[W]
        for f in ('z_oi', 'z_f', 'f'):
            df[f] = G[f][ck, cc]
        with np.errstate(invalid='ignore', divide='ignore'):
            df['doi24'] = X_oi[ck, cc] / X_oi[ck - 24, cc] - 1.0
            df['r24'] = CLH[ck, cc] / CLH[ck - 24, cc] - 1.0
        df['qv30'] = qv30[ck, cc]
        df['age_d'] = (ck * 60 - first[cc]) / 1440.0
        df['hod'] = ck % 24
        df['btc7'] = btc7[ck]
        df['ew7'] = ew7[ck]
        df['s'] = np.fmin(df['z_oi'], df['z_f'])
        for nm, (sl, hh, a, g) in EXITS.items():
            xi = CB.xidx(sl, hh, a, g)
            xr = T['xr'][cid, xi].astype(np.float64)
            fu = T['fund'][cid, xi].astype(np.float64)
            rs = T['rs'][cid, xi]
            df['ret_' + nm] = (1.0 - xr) - 0.0007 * (1.0 + xr) + fu
            df['rs_' + nm] = np.array(CB.RNAMES)[rs]
        cands.append(df)
    D = pd.concat(cands, ignore_index=True)
    D['sym'] = np.array(syms, dtype=object)[D['c'].values]
    D.to_parquet(A.OUT + '/b_cands.parquet', index=False)
    for (W, epi, y), s in D.groupby(['W', 'episode', 'year']):
        for nm in EXITS:
            v = s.loc[s['rs_' + nm] != 'eod', 'ret_' + nm]
            outs.append(dict(W=W, unit='episode' if epi else 'non-first-hour', year=y, exit=nm, n=int(len(v)), win=float((v > 0).mean()),
                             mean=float(v.mean()), median=float(v.median()), sd=float(v.std()), se=float(v.std() / np.sqrt(max(len(v), 1))),
                             n_coins=int(s['c'].nunique()), sl_share=float((s['rs_' + nm] == 'sl').mean())))
    pd.DataFrame(outs).to_parquet(A.OUT + '/b_outcomes.parquet', index=False)
    # feature quintiles on episodes (pooled edges over 2022-2025), per year
    q, sp = [], []
    E = D[D['episode']]
    for W in (7, 14):
        e = E[E['W'] == W]
        for nm in ('SL15_H24_t10/5', 'SL30_H72_t10/5'):
            e2 = e[e['rs_' + nm] != 'eod']
            y_ = e2['ret_' + nm]
            for f in FEATS + ('s',):
                x = e2[f]
                ok = np.isfinite(x)
                if f == 'hod':
                    bins = pd.cut(x, [-1, 3, 7, 11, 15, 19, 23], labels=False)
                else:
                    bins = pd.qcut(x[ok], 5, labels=False, duplicates='drop').reindex(x.index)
                for yy in (2022, 2023, 2024, 2025, 'all'):
                    mk = (e2['year'] == yy) if yy != 'all' else np.ones(len(e2), bool)
                    for b in sorted(pd.Series(bins).dropna().unique()):
                        mm = mk & (bins == b)
                        v = y_[mm]
                        q.append(dict(W=W, exit=nm, feat=f, year=str(yy), bin=int(b), lo=float(x[bins == b].min()), hi=float(x[bins == b].max()),
                                      n=int(len(v)), win=float((v > 0).mean()) if len(v) else np.nan, mean=float(v.mean()) if len(v) else np.nan))
                    sub = e2[mk & ok]
                    sp.append(dict(W=W, exit=nm, feat=f, year=str(yy), n=int(len(sub)),
                                   spear=float(sub[[f, 'ret_' + nm]].corr(method='spearman').iloc[0, 1]) if len(sub) > 10 else np.nan))
    pd.DataFrame(q).to_parquet(A.OUT + '/b_feat_quint.parquet', index=False)
    pd.DataFrame(sp).to_parquet(A.OUT + '/b_feat_spear.parquet', index=False)
    log.info('b_pool done cands=%d episodes=%d', len(D), int(D['episode'].sum()))


if __name__ == '__main__':
    main()
