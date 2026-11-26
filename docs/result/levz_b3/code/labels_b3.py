"""LEVZ B3 step 3 - exit table + labels for the WHOLE pool (PREREG_LEVZ_B3 sec 3) with the B1 engine exits.compute (imported, not
edited). Only the exits needed are kept: exit_2024 and exit_2025 from out/exitsel_b3.json (CHOICES_B3 #8: 2 of 195, the engine still
evaluates all 195 internally; storing 195 x 721 h for 28 864 candidates is not needed and costs disk). Hourly arrays (mk, hm, fh, fc)
are cut to Hmax + 1 columns (port.py never reads beyond hour H of the exit: kx - ke <= ceil(j / 60) <= H).
label[:, i] = net return per unit notional of ONE short trade with exit XS[i] = (1 - xr) - FEE - xr FEE + fund (= port._net / N).
Regression: rows of the pool that are in the B1 union must equal levz_b1/work/exits.npz exactly (all stored arrays).
On REAL labels only hygiene stats are logged (n, NaN, exit-reason counts) - no means, no correlations.
usage: bash code/heavy.sh code/labels_b3.py build   -> work/labels_b3.npz, out/labels_b3.json"""
import os
import sys
import json
import logging
import time
sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('common_b3', os.path.join(_HERE, 'common_b3.py'))
C3 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault('common_b3', C3)
_spec.loader.exec_module(C3)
import numpy as np

log = logging.getLogger('levz_b3.labels')
LAB = C3.WORK + '/labels_b3.npz'
PER = ('j', 'rs', 'xr', 'fund', 'mx', 'mxh', 'flag')
HOURLY = ('mk', 'hm', 'fh', 'fc')
CHUNK = 2000


def exit_list():
    es = json.load(open(C3.OUT + '/exitsel_b3.json'))
    xs, hs = [], []
    for Y in (2024, 2025):
        e = es['exit_%d' % Y]
        xs.append(int(e['xi']))
        hs.append(int(e['H']))
        assert C3.CB.XCFGS[e['xi']] == (e['SL'], e['H'], e['arm'], e['gap'])
    return xs, hs


def label_of(xr, fund, fee):
    return (1.0 - xr) - fee - xr * fee + fund


def compute_table(st, ks, cs, xs, hc):
    X = C3.b1('exits')
    n = len(ks)
    out = {kk: None for kk in PER + HOURLY}
    for a in range(0, n, CHUNK):
        b = min(n, a + CHUNK)
        r = X.compute(st, ks[a:b], cs[a:b])
        for kk in PER:
            v = r[kk][:, xs]
            if out[kk] is None:
                out[kk] = np.empty((n, len(xs)), dtype=v.dtype)
            out[kk][a:b] = v
        for kk in HOURLY:
            v = r[kk][:, :hc]
            if out[kk] is None:
                out[kk] = np.empty((n, hc), dtype=v.dtype)
            out[kk][a:b] = v
        for kk in ('p0', 'longgap'):
            if out.get(kk) is None:
                out[kk] = np.empty(n, dtype=r[kk].dtype)
            out[kk][a:b] = r[kk]
        log.info('exits %d/%d', b, n)
    return out


def regress_b1(out, b1cid, xs, hc):
    T1 = C3.b1('exits').load_table()
    idx = np.flatnonzero(b1cid >= 0)
    rid = b1cid[idx]
    assert (T1['k'][rid] == out['k'][idx]).all() and (T1['c'][rid] == out['c'][idx]).all()
    res = {}
    for kk in PER:
        res[kk] = bool(np.array_equal(T1[kk][rid][:, xs], out[kk][idx]))
    for kk in HOURLY:
        res[kk] = bool(np.array_equal(T1[kk][rid][:, :hc], out[kk][idx]))
    res['p0'] = bool(np.array_equal(T1['p0'][rid], out['p0'][idx]))
    return dict(n_overlap=int(len(idx)), equal=res, all_equal=bool(all(res.values())))


def build():
    t0 = time.time()
    xs, hs = exit_list()
    hc = max(hs) + 1
    P = dict(np.load(C3.WORK + '/pool_b3.npz'))
    ks, cs = P['k'], P['c']
    st = C3.b1('exits').Store()
    out = compute_table(st, ks, cs, xs, hc)
    out['k'], out['c'] = ks, cs
    fee = C3.b1('port').FEE
    out['label'] = label_of(out['xr'], out['fund'], fee)
    out['xs'] = np.array(xs)
    out['hs'] = np.array(hs)
    reg = regress_b1(out, P['b1cid'], xs, hc)
    assert reg['all_equal'], reg
    np.savez(LAB + '.tmp.npz', **out)
    os.replace(LAB + '.tmp.npz', LAB)
    names = C3.CB.RNAMES
    hyg = dict(n=int(len(ks)), xs=xs, hs=hs, hcols=hc, regression_b1=reg, size_mb=os.path.getsize(LAB) / 1e6,
               label_nan=[int((~np.isfinite(out['label'][:, i])).sum()) for i in range(len(xs))],
               reason_counts=[{names[r]: int((out['rs'][:, i] == r).sum()) for r in range(len(names))} for i in range(len(xs))],
               flag_counts=[int(out['flag'][:, i].sum()) for i in range(len(xs))], longgap=int(out['longgap'].sum()),
               sec=time.time() - t0)
    with open(C3.OUT + '/labels_b3.json', 'w') as fh:
        json.dump(hyg, fh, indent=1)
    log.info('labels done %s', {k: hyg[k] for k in ('n', 'xs', 'label_nan', 'size_mb', 'sec')})
    log.info('regression vs B1 exits.npz: %s', reg)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'build': build}[sys.argv[1]]()
