"""LEVZ T2 step 2: exit tables from the REAL ENTRY MINUTE (PREREG_LEVZ_T2 sec 2-3 + ADD1 M2) for 211 exits, WITHOUT changing B1 / T1 code.
Entry at absolute minute m = 60 kb + r (0 <= r <= 59), entry price px (E0: close; EL: limit level; EB / EO / placebo: close x 0.999).
(1) m-frame path p (len NPATH): p[0] = px, p[i] = close1m[c, m + i] (ffilled, padded with last value beyond the data end), gap mask /
    missing-run exit exactly as B1 exits.path_of with base minute m. B1 exits.exits_core (195 exits) and T1 exits_t1.Cur / bracket (STATE)
    / part (PART) are called UNCHANGED on p => j, reason, xr, mx, flag, j1, xr1 are measured from the real entry minute (time stop = 60 H
    minutes after m; SL / trailing / TP from minute m + 1). STATE: finalised W7 rows kb + h, h >= 1 (exits_t1.state_hour(cond, kb, c))
    -> exit at the bar 60 (kb + h) = m-frame minute 60 h - r.
(2) Port frame (B1 port.py works on hours): entry hour kb = floor(m / 60) (ADD1 M2). j' = j + r (minute from T_kb) => port's
    kx = kb + ceil(j' / 60). Hourly arrays on the kb-aligned path P2 (len NPATH2 = 721 x 60 + 1): P2[0..r] = px (not filled before m:
    mark = entry price), P2[i] = close1m[c, 60 kb + i] for i > r. mk[h] = P2[60 h] / px, hm[h] = max P2(60 (h-1), 60 h] / px (hm[0] = 1),
    fh[h] = FR[kb + h, c] x P2[60 h - 1] / px if 60 h - 1 > r (entry bar closes strictly before the settlement) else 0, h = 1..721;
    width HW = 722. fund / mxh (and PART fund / mxh_eff) recomputed in the kb frame with the B1 / T1 formulas:
    fund = fc[min((j' + 1) // 60, 721)], mxh = max P2[60 ((j' - 1) // 60) + 1 .. j'] / px; PART: fc[m1] + 0.5 (fc[m2] - fc[m1]),
    mxh_eff = 0.5 xr1 + 0.5 mxh_raw, max(mxh_raw, .) if the partial (j1' = j1 + r) lies in the exit hour window.
For E0 (r = 0, px = close) every array equals B1 exits.npz / T1 exits_t1_<FAM>.npz (test_t2 a).
Port views: B1 -> port.XView; STATE -> port.XView; PART -> exits_t1.PartView on hourly arrays cut to 721 columns (PART H <= 168 h).
Table rows = filled candidates of one entry type: k (signal hour), c, s-independent; m, kb, r, px, d (delay min).
usage: python3 code/exits_t2.py build [ENTRY ...]   (real filled candidates -> work/exits_t2_<E>.npz; hygiene only, no profit)"""
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np

log = C.setup_log('exits')
CB = C.CB
C1 = C.C1
XB1 = C.b1('exits')
P = C.b1('port')
E1 = C.t1('exits_t1')
BIG = XB1.BIG
NX = XB1.NX
OUTK = ('j', 'rs', 'xr', 'fund', 'mx', 'mxh', 'flag')
TK = ('j', 'rs', 'rt', 'xr', 'fund', 'mx', 'mxh', 'flag')


def path_m(st, c, m, px):
    """m-frame path (B1 path_of with base minute m and p[0] = px). Returns p, nv, miss_m, gm."""
    b = int(m)
    nv = min(C.NPATH, st.NMIN - b)
    assert nv >= 1
    raw = np.asarray(st.mm[c, b:b + nv], dtype=np.float64)
    assert np.isfinite(raw[0]), 'no 1m bar at entry'
    p = np.empty(C.NPATH)
    p[:nv] = raw
    p[nv:] = raw[-1]
    p[0] = px
    gm = np.zeros(C.NPATH, dtype=bool)
    miss_m = BIG
    if int(c) in st.gaps:
        g0, g1 = st.gaps[int(c)]
        assert not (len(g0) and np.any((g0 <= b) & (g1 > b))), 'entry minute inside a gap'
        i = int(np.searchsorted(g0, b, 'right'))
        while i < len(g0) and g0[i] < b + nv:
            a, e = int(g0[i]) - b, min(int(g1[i]) - b, nv)
            gm[a:e] = True
            if int(g1[i]) - int(g0[i]) > CB.MISS_MIN and miss_m == BIG:
                miss_m = int(g0[i]) + CB.MISS_MIN - b
            i += 1
    return p, nv, miss_m, gm


def frame_kb(st, c, m, px):
    """kb-aligned path + hourly arrays (width HW). Returns kb, r, mk, hm, fh, fc0 (fc with leading 0, len HW), rmh."""
    kb, r = divmod(int(m), 60)
    b = 60 * kb
    nv = min(C.NPATH2, st.NMIN - b)
    raw = np.asarray(st.mm[c, b:b + nv], dtype=np.float64)
    P2 = np.empty(C.NPATH2)
    P2[:nv] = raw
    P2[nv:] = raw[-1]
    P2[:r + 1] = px
    nh = C.HW - 1
    mk = P2[::60] / px
    hm = np.concatenate([[1.0], P2[1:].reshape(nh, 60).max(axis=1) / px])
    fh = np.zeros(C.HW)
    hh = np.arange(1, C.HW)
    kk = kb + hh
    ok = (kk < st.NH) & (60 * hh - 1 > r)
    fh[1:][ok] = st.FR[kk[ok], c] * P2[60 * hh[ok] - 1] / px
    fc0 = np.concatenate([[0.0], np.cumsum(fh[1:])])
    rmh = np.maximum.accumulate(P2[1:].reshape(nh, 60), axis=1).ravel()
    return kb, r, mk, hm, fh, fc0, rmh


def _fund(fc0, jp):
    return fc0[np.minimum((np.asarray(jp) + 1) // 60, C.HW - 1)]


def one(st, c, m, px, conds):
    """all 211 exits for one entry. Returns dict b1 (195 arrays), part / state (lists of dicts), hourly (mk, hm, fh), kb, r."""
    p, nv, miss_m, gm = path_m(st, c, m, px)
    kb, r, mk, hm, fh, fc0, rmh = frame_kb(st, c, m, px)
    zero = np.zeros(C.HMAX + 1)
    b1 = XB1.exits_core(p, nv, miss_m, zero, gm)
    jp = b1['j'].astype(np.int64) + r
    b1['j'] = jp.astype(np.int32)
    b1['fund'] = _fund(fc0, jp)
    b1['mxh'] = rmh[jp - 1] / px
    cu = E1.Cur(p, nv, miss_m, zero, gm)
    part = []
    for x in C1.fam_cfgs('PART'):
        d = E1.part(cu, x['s'], x['H'])
        j = int(d['j']) + r
        d['j'] = j
        mxh_raw = rmh[j - 1] / px
        if d['j1'] < 0:
            d['fund'] = float(_fund(fc0, j))
            d['mxh'] = d['mxh_raw'] = mxh_raw
        else:
            i1 = int(d['j1']) + r
            d['j1'] = i1
            m1, m2 = min((i1 + 1) // 60, C.HW - 1), min((j + 1) // 60, C.HW - 1)
            d['fund'] = fc0[m1] + (1.0 - C1.PART_FRAC) * (fc0[m2] - fc0[m1])
            eff = C1.PART_FRAC * d['xr1'] + (1.0 - C1.PART_FRAC) * mxh_raw
            if i1 > 60 * ((j - 1) // 60):
                eff = max(mxh_raw, eff)
            d['mxh'], d['mxh_raw'] = eff, mxh_raw
        part.append(d)
    sth = {zo: E1.state_hour(conds[zo], kb, c) for zo in C1.STATE_Z}
    state = []
    for x in C1.fam_cfgs('STATE'):
        h = sth[x['zo']]
        d = E1.bracket(cu, x['s'], None, x['H'], 60 * h - r if h < BIG else BIG)
        j = int(d['j']) + r
        d['j'] = j
        d['fund'] = float(_fund(fc0, j))
        d['mxh'] = rmh[j - 1] / px
        state.append(d)
    return dict(b1=b1, part=part, state=state, mk=mk, hm=hm, fh=fh, kb=kb, r=r, sth=[sth[z] for z in C1.STATE_Z])


def load_conds():
    sig = E1.load_sig()
    return {zo: E1.state_cond(sig, zo) for zo in C1.STATE_Z}


def compute(st, ms, cs, pxs, conds):
    """exit tables for entries (abs minute ms, coin cs, entry price pxs)."""
    n = len(ms)
    T = {'B1': {kk: [] for kk in OUTK}}
    fam = {f: {kk: np.empty((n, C1.NFAM[f])) for kk in TK} for f in ('PART', 'STATE')}
    for kk in ('j1', 'xr1', 'mxh_raw'):
        fam['PART'][kk] = np.empty((n, C1.NFAM['PART']))
    fam['STATE']['sth'] = np.empty((n, len(C1.STATE_Z)))
    mk = np.empty((n, C.HW))
    hm = np.empty((n, C.HW))
    fh = np.empty((n, C.HW))
    kb = np.empty(n, dtype=np.int64)
    rr = np.empty(n, dtype=np.int64)
    for i in range(n):
        o = one(st, int(cs[i]), int(ms[i]), float(pxs[i]), conds)
        for kk in OUTK:
            T['B1'][kk].append(o['b1'][kk])
        for f, rows in (('PART', o['part']), ('STATE', o['state'])):
            for xi, d in enumerate(rows):
                for kk, v in d.items():
                    fam[f][kk][i, xi] = v
        fam['STATE']['sth'][i] = o['sth']
        mk[i], hm[i], fh[i], kb[i], rr[i] = o['mk'], o['hm'], o['fh'], o['kb'], o['r']
    out = {}
    for kk in OUTK:
        out['B1_' + kk] = np.vstack(T['B1'][kk]) if n else np.zeros((0, NX))
    for f in ('PART', 'STATE'):
        t = fam[f]
        t['j'] = t['j'].astype(np.int32)
        t['rt'] = t['rt'].astype(np.int8)
        t['rs'] = C1.RT2RS[t['rt']]
        t['flag'] = t['flag'].astype(np.int8)
        if f == 'PART':
            t['j1'] = t['j1'].astype(np.int32)
        for kk, v in t.items():
            out['%s_%s' % (f, kk)] = v
    out.update(mk=mk, hm=hm, fh=fh, kb=kb, r=rr, m=np.asarray(ms, dtype=np.int64), c=np.asarray(cs, dtype=np.int64),
               px=np.asarray(pxs, dtype=np.float64))
    return out


# ---------------------------------------------------------------- port views
def tables(out):
    """exit table dict -> {'B1': T, 'PART': T, 'STATE': T} in port.XView / PartView layout (fc = cumsum fh)."""
    fc = np.cumsum(out['fh'], axis=1)
    hw = dict(mk=out['mk'], hm=out['hm'], fh=out['fh'], fc=fc)
    h721 = {kk: v[:, :C.HMAX + 1] for kk, v in hw.items()}
    res = {}
    for f in ('B1', 'PART', 'STATE'):
        T = {kk[len(f) + 1:]: v for kk, v in out.items() if kk.startswith(f + '_')}
        T.update(h721 if f == 'PART' else hw)
        res[f] = T
    if len(out['m']):
        assert (res['PART']['j'] <= 60 * C.HMAX).all(), 'PART exit beyond 720 h (721-column view)'
    return res


def view(TT, xfam, xi):
    if xfam == 'PART':
        return E1.PartView(TT['PART'], int(xi))
    return P.XView(TT[xfam], int(xi))


def entry_rows(en, e):
    """filled candidates of entry type e from entry_t2 arrays: (idx into union, m, c, px)."""
    idx = np.flatnonzero(en[e + '_m'] >= 0)
    return idx, en[e + '_m'][idx], en['c'][idx], en[e + '_px'][idx]


def path_out(e):
    return '%s/exits_t2_%s.npz' % (C.WORK, e)


def load_table(e):
    z = np.load(path_out(e))
    return {kk: z[kk] for kk in z.files}


def _work(args):
    ms, cs, pxs = args
    return compute(G['st'], ms, cs, pxs, G['conds'])


G = {}


def compute_par(st, ms, cs, pxs, conds, nproc=3, chunk=200):
    """parallel compute (fork, chunks in order) -> identical to compute()."""
    n = len(ms)
    if nproc <= 1 or n <= chunk:
        return compute(st, ms, cs, pxs, conds)
    import multiprocessing as mp
    G['st'], G['conds'] = st, conds
    parts = [(ms[a:a + chunk], cs[a:a + chunk], pxs[a:a + chunk]) for a in range(0, n, chunk)]
    with mp.get_context('fork').Pool(nproc) as pool:
        res = pool.map(_work, parts, chunksize=1)
    out = {}
    for kk in res[0]:
        out[kk] = np.concatenate([r[kk] for r in res], axis=0)
    return out


def build(entries):
    EN = C.load('entry_t2')
    en = EN.load_entries()
    st = XB1.Store()
    conds = load_conds()
    for e in entries:
        t0 = time.time()
        idx, ms, cs, pxs = entry_rows(en, e)
        out = compute_par(st, ms, cs, pxs, conds)
        out['uidx'] = idx
        out['k'] = en['k'][idx]
        out['cid_b1'] = en['cid_b1'][idx]
        out['d'] = ms - 60 * en['k'][idx]
        fn = path_out(e)
        np.savez(fn + '.tmp.npz', **out)
        os.replace(fn + '.tmp.npz', fn)
        log.info('exits_t2 %s n=%d %.1fs', e, len(ms), time.time() - t0)
        hygiene(e, out)


def hygiene(e, out):
    """NO profit: NaN counts, exit-reason shares (B1 all 195 / PART / STATE), r distribution."""
    rs = out['B1_rs']
    sh = {CB.RNAMES[x]: round(float((rs == x).mean()), 4) for x in range(len(CB.RNAMES)) if (rs == x).any()}
    st = {}
    for f in ('PART', 'STATE'):
        rt = out[f + '_rt']
        st[f] = {C1.RTNAMES[x]: round(float((rt == x).mean()), 4) for x in range(len(C1.RTNAMES)) if (rt == x).any()}
    log.info('hygiene %s rows=%d nan_xr=%d nan_fund=%d nan_mk=%d r>0=%.3f B1 reasons=%s PART=%s STATE=%s', e, len(out['m']),
             int(np.isnan(out['B1_xr']).sum()), int(np.isnan(out['B1_fund']).sum()), int(np.isnan(out['mk']).sum()),
             float((out['r'] > 0).mean()), sh, st['PART'], st['STATE'])


if __name__ == '__main__':
    build(sys.argv[2:] or list(C.ENTRIES))
