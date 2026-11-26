"""LEVZ B3 step 1 - pool (PREREG_LEVZ_B3 sec 2): W7 E0 z_min 1.5 with the B1 candidate generator UNCHANGED (B0 sim.candidates,
pxok = B1 hourly has1m, exactly as levz_b1 paths.cand()); only z_min differs. Regression: subsets z >= 2.5 / 3.0 / 3.5 must equal
cand_b1.npz W7_E0_* row by row (k, c, s). Dots: same coin, consecutive candidates < 24 h apart (single linkage); weight = 1 / dot size
(full pool). C0 for Y in 2023..2025 needs H(exit_Y) -> reads out/exitsel_b3.json (exit_2023 not defined => C0_2023 reported with
H = 720 worst case and flagged).
usage: python3 code/cand_b3.py build | c0   -> work/pool_b3.npz, out/cand_b3.json"""
import os
import sys
import json
import logging
sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('common_b3', os.path.join(_HERE, 'common_b3.py'))
C3 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault('common_b3', C3)
_spec.loader.exec_module(C3)
import numpy as np

log = logging.getLogger('levz_b3.cand')
POOL = C3.WORK + '/pool_b3.npz'


def gen_pool(G, has1m, zmin):
    S = C3.CB.load_b0('sim')
    return S.candidates(G['z_oi'], G['z_f'], G['f'], G['z_r'], G['u'], has1m, C3.E, zmin)


def dots(ck, cc, gap=C3.DOT_GAP_H):
    """dot id per candidate (single linkage per coin, new dot iff gap to previous candidate of the coin >= gap h).
    Returns dot (int64, ids in order of (c, k)), size per candidate, weight = 1 / size."""
    ck = np.asarray(ck, dtype=np.int64)
    cc = np.asarray(cc, dtype=np.int64)
    n = len(ck)
    if n == 0:
        z = np.zeros(0, dtype=np.int64)
        return z, z, np.zeros(0)
    o = np.lexsort((ck, cc))
    k2, c2 = ck[o], cc[o]
    new = np.ones(n, dtype=bool)
    new[1:] = (c2[1:] != c2[:-1]) | ((k2[1:] - k2[:-1]) >= gap)
    did = np.cumsum(new) - 1
    dot = np.empty(n, dtype=np.int64)
    dot[o] = did
    size = np.bincount(dot)[dot]
    return dot, size, 1.0 / size


def regress(ck, cc, cs, cz):
    """subset z >= 2.5/3.0/3.5 of pool must equal cand_b1 W7_E0_* row by row (both sorted (k asc, s desc, c asc))."""
    out = {}
    m = json.load(open(C3.CB.L2 + '/work/sig_meta.json'))
    for z in C3.REG_Z:
        key = 'W7_E0_%.1f' % z
        rk, rc, rs = cz[key + '_k'], cz[key + '_c'], cz[key + '_s']
        mk = cs >= z
        # pool s = min(z_oi, z_f) and the LEV filter is z_oi >= z & z_f >= z & f > F_MIN; s >= z <=> both >= z (f filter already in pool)
        a = (ck[mk], cc[mk], cs[mk])
        ok = len(a[0]) == len(rk) and (a[0] == rk).all() and (a[1] == rc).all() and (a[2] == rs).all()
        out[key] = dict(n_pool_subset=int(mk.sum()), n_b1=int(len(rk)), equal=bool(ok))
    return out


def build():
    CB = C3.CB
    S = CB.load_b0('sim')
    SG = S.load_sibling('sig')
    m = CB.meta()
    has1m = np.load(C3.B1WORK + '/hourly.npz')['has1m']
    G = SG.dense_from_sig(C3.W)
    assert G['syms'] == m['syms'] and int(G['tms'][-1]) < C3.CUT
    ck, cc, cs = gen_pool(G, has1m, C3.ZMIN)
    cz = np.load(C3.B1WORK + '/cand_b1.npz')
    reg = regress(ck, cc, cs, cz)
    assert all(v['equal'] for v in reg.values()), reg
    dot, size, w = dots(ck, cc)
    # B1 cid (exits.npz row) for candidates present in the B1 union, else -1
    code_b1 = cz['U_k'] * 10000 + cz['U_c']
    code = ck * 10000 + cc
    pos = np.searchsorted(code_b1, code)
    pos = np.minimum(pos, len(code_b1) - 1)
    b1cid = np.where(code_b1[pos] == code, pos, -1).astype(np.int64)
    yr = C3.year_of_k(ck)
    np.savez(POOL, k=ck, c=cc, s=cs, dot=dot, dsize=size, w=w, year=yr, b1cid=b1cid,
             z_oi=G['z_oi'][ck, cc], z_f=G['z_f'][ck, cc])
    rep = dict(n_pool=int(len(ck)), regression=reg, n_in_b1_union=int((b1cid >= 0).sum()), n_dots=int(dot.max() + 1),
               by_year={})
    for y in range(2021, 2026):
        mk = yr == y
        rep['by_year'][str(y)] = dict(n_cand=int(mk.sum()), n_dots_touching=int(len(np.unique(dot[mk]))))
    # dots counted by the year of their FIRST candidate
    first_k = np.full(dot.max() + 1, np.iinfo(np.int64).max)
    np.minimum.at(first_k, dot, ck)
    fy = C3.year_of_k(first_k)
    for y in range(2021, 2026):
        rep['by_year'][str(y)]['n_dots_starting'] = int((fy == y).sum())
    rep['dot_size'] = dict(median=float(np.median(np.bincount(dot))), max=int(np.bincount(dot).max()),
                           mean=float(np.bincount(dot).mean()))
    os.makedirs(C3.OUT, exist_ok=True)
    with open(C3.OUT + '/cand_b3.json', 'w') as fh:
        json.dump(rep, fh, indent=1)
    log.info('pool n=%d dots=%d regression=%s', len(ck), rep['n_dots'], {k: v['equal'] for k, v in reg.items()})
    for y, v in rep['by_year'].items():
        log.info('year %s cand=%d dots_touching=%d dots_starting=%d', y, v['n_cand'], v['n_dots_touching'], v['n_dots_starting'])


def train_mask(k, Y, Hx):
    """train set of test year Y: TRAIN_START <= T_k and entry hour k <= k0(Y) - Hx - 24 (purge, prereg sec 3: drop k > start - H - 24 h)."""
    k = np.asarray(k)
    k0 = C3.kidx(C3.ms(C3.TRAIN_START))
    lim = C3.year_k0(Y) - int(Hx) - 24
    return (k >= k0) & (k <= lim)


def c0(P, Y, Hx):
    tm = train_mask(P['k'], Y, Hx)
    dots_tr = np.unique(P['dot'][tm])
    last = tm & (P['year'] == Y - 1)
    dots_last = np.unique(P['dot'][last])
    ok = len(dots_tr) >= C3.C0_TOTAL and len(dots_last) >= C3.C0_LAST
    return dict(Y=Y, H_exit=int(Hx), purge_last_k=int(C3.year_k0(Y) - int(Hx) - 24), n_train_cand=int(tm.sum()),
                n_train_dots=int(len(dots_tr)), n_lastyear_cand=int(last.sum()), n_lastyear_dots=int(len(dots_last)), C0=bool(ok))


def main_c0():
    P = dict(np.load(POOL))
    es = json.load(open(C3.OUT + '/exitsel_b3.json'))
    rep = json.load(open(C3.OUT + '/cand_b3.json'))
    rep['C0'] = {}
    for Y in (2023, 2024, 2025):
        e = es.get('exit_%d' % Y)
        if e is None or e.get('xi') is None:
            r = c0(P, Y, 720)
            r['note'] = 'exit_%d khong tinh duoc dung luat; C0 tinh voi H = 720 (purge lon nhat) chi de tham khao' % Y
        else:
            r = c0(P, Y, e['H'])
        rep['C0'][str(Y)] = r
        log.info('C0 %s', r)
    with open(C3.OUT + '/cand_b3.json', 'w') as fh:
        json.dump(rep, fh, indent=1)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'build': build, 'c0': main_c0}[sys.argv[1]]()
