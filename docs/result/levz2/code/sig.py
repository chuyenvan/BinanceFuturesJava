"""LEVZ2 signal table (PREREG_LEVZ2 sec 1). Re-uses the FROZEN tier-1 code (w3/levz/code: common.py, levz.py) by import;
no definition is rewritten here.
Output work/sig_W{14,7}.parquet: sym, t (ms, = tier-1 hour h = decision time; info up to t), z_oi, z_f, f, z_r, u (universe at t).
Rows kept: (sym, t) with u at any hour in [t-24h, t] (E1 needs z_r up to 24h after a universe LEV hour).
S1 check (mandatory): from the written table, apply tier-1 episode rule (z>2.5 both, f>1e-4, cooldown 72h on t0, via levz.episodes)
and E1 rule (levz.e1_entry) -> must reproduce (sym,t0) of events_A1/A3 and (sym,t0,te) of events_A2/A4 (explore+confirm) 100%.
usage: python3 code/sig.py build | s1"""
import json
import logging
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]  # code/select.py must not shadow stdlib select
sys.dont_write_bytecode = True
LEVZ_CODE = '/home/ubuntu/claude_master/w3/levz/code'
sys.path.insert(0, LEVZ_CODE)
import numpy as np
import pandas as pd
import common as C   # frozen tier-1
import levz as L     # frozen tier-1

log = logging.getLogger('levz2.sig')
BASE = '/home/ubuntu/claude_master/w3/levz2'
WORK = BASE + '/work'
EV = '/home/ubuntu/claude_master/w3/levz/out/events_%s_%s.parquet'
DEV_A = 1640995200000  # 2022-01-01
CUT = C.CUTOFF_MS


def build():
    D = L.Data('2025-12')
    assert D.cut == CUT and int(D.tms[-1]) < CUT
    ns = len(D.syms)
    U = D.U
    # dilate universe forward 24h: keep row k if U at any of k-24..k
    keep = U.copy()
    for d in range(1, 25):
        keep[d:] |= U[:-d]
    rr, cc = np.nonzero(keep)
    for W in L.WS:
        g = L.signals(D, W)
        df = pd.DataFrame({'sym': np.array(D.syms, dtype=object)[cc], 't': D.tms[rr],
                           'z_oi': g['zoi'][rr, cc], 'z_f': g['zf'][rr, cc], 'f': g['f'][rr, cc],
                           'z_r': g['zr'][rr, cc], 'u': U[rr, cc]})
        assert int(df['t'].max()) < CUT
        df.to_parquet('%s/sig_W%d.parquet' % (WORK, W), index=False)
        log.info('W%d rows=%d u_rows=%d syms=%d', W, len(df), int(df['u'].sum()), df['sym'].nunique())
        del g, df
    meta = {'H0': int(L.H0), 'NH': int(D.NH), 'syms': D.syms, 'ns': ns}
    with open(WORK + '/sig_meta.json', 'w') as fh:
        json.dump(meta, fh)


def dense_from_sig(W):
    with open(WORK + '/sig_meta.json') as fh:
        meta = json.load(fh)
    syms, NH = meta['syms'], meta['NH']
    col = {s: i for i, s in enumerate(syms)}
    d = pd.read_parquet('%s/sig_W%d.parquet' % (WORK, W))
    assert int(d['t'].max()) < CUT
    r = ((d['t'].values - L.H0) // L.H).astype(np.int64)
    c = d['sym'].map(col).values.astype(np.int64)
    out = {}
    for k in ('z_oi', 'z_f', 'f', 'z_r'):
        a = np.full((NH, len(syms)), np.nan)
        a[r, c] = d[k].values
        out[k] = a
    u = np.zeros((NH, len(syms)), dtype=bool)
    u[r, c] = d['u'].values
    out['u'] = u
    out['tms'] = L.H0 + np.arange(NH, dtype=np.int64) * L.H
    out['syms'] = syms
    return out


def s1():
    res = {}
    allok = True
    for W, b0, b1 in ((14, 'A1', 'A2'), (7, 'A3', 'A4')):
        S = dense_from_sig(W)
        cond = S['u'] & np.isfinite(S['z_oi']) & np.isfinite(S['z_f']) & (S['z_oi'] > L.Z_TH) & (S['z_f'] > L.Z_TH) & (S['f'] > L.F_MIN)
        eps = [(r, c) for r, c in L.episodes(cond) if S['tms'][r] >= DEV_A]
        mine0 = set((S['syms'][c], int(S['tms'][r])) for r, c in eps)
        mine1 = set()
        for r, c in eps:
            re, lag = L.e1_entry(S['z_r'], r, c)
            if re is not None:
                mine1.add((S['syms'][c], int(S['tms'][r]), int(S['tms'][re])))
        ref0, ref1 = set(), set()
        for per in ('explore', 'confirm'):
            e = pd.read_parquet(EV % (b0, per))
            ref0 |= set(zip(e['sym'].astype(str), e['t0'].astype(np.int64).tolist()))
            e = pd.read_parquet(EV % (b1, per))
            ref1 |= set(zip(e['sym'].astype(str), e['t0'].astype(np.int64).tolist(), e['te'].astype(np.int64).tolist()))
        r0 = dict(n_ref=len(ref0), n_mine=len(mine0), n_match=len(ref0 & mine0), only_ref=sorted(ref0 - mine0)[:20],
                  only_mine=sorted(mine0 - ref0)[:20])
        r1 = dict(n_ref=len(ref1), n_mine=len(mine1), n_match=len(ref1 & mine1), only_ref=sorted(ref1 - mine1)[:20],
                  only_mine=sorted(mine1 - ref1)[:20])
        ok = (ref0 == mine0) and (ref1 == mine1)
        allok &= ok
        res['W%d' % W] = {b0: r0, b1: r1, 'pass': ok}
        log.info('S1 W%d %s ref=%d mine=%d match=%d | %s ref=%d mine=%d match=%d pass=%s', W, b0, len(ref0), len(mine0),
                 len(ref0 & mine0), b1, len(ref1), len(mine1), len(ref1 & mine1), ok)
    res['pass'] = bool(allok)
    with open(WORK + '/s1.json', 'w') as fh:
        json.dump(res, fh, indent=1, default=str)
    log.info('S1 PASS=%s', allok)


if __name__ == '__main__':
    C.setup_log()
    {'build': build, 's1': s1}[sys.argv[1]]()
