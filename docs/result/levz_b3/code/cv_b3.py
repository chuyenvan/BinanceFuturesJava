"""LEVZ B3 ERRATA1 E2 (B) - quarterly CV ("CV - co nhin truoc": a quarter is predicted by a model trained on LATER quarters too).
Folds: quarters 2023Q1 .. 2025Q4 (12). Fold q: validate = candidates with entry in q; train = candidates with entry in
[2022-01-01, 2026-01-01) outside q AND outside the purge band [start(q) - H - 24 h, end(q) + H + 24 h] (both sides, end(q) = last hour of
q, H = H of the exit whose label is used). Model M1, 10 seeds (seed mean). No inner OOF / threshold here.
C1: weighted Spearman(OOF score, label) > 0 in >= 9 / 12 quarters (labels by exit_2025).
C2: one continuous portfolio 2023-01-01 .. 2025-12-31 23:00 (B1 port.run, K5) with OOF scores, threshold = 80th pct of ALL OOF scores
    (2023-2025; slight leak at the threshold, ERRATA1), exit_2025: net pnl > 0 in EACH of 2023, 2024, 2025 and total > BL_S20 on the
    same span (BL_S20 threshold = 80th pct of s over the 2023-2025 pool, CHOICES_B3).
C3: C2 repeated with labels AND exits by exit_2024 (purge with H = 336): 3-year total > 0.
usage: python3 code/cv_b3.py --real I_HAVE_A1_PASS   (DEV must NOT run this on real data)"""
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

log = logging.getLogger('levz_b3.cv')
MOD = C3.b3('model_b3')
WFO = C3.b3('wfo_b3')
P = C3.b1('port')
LABEL = 'CV - co nhin truoc'


def quarter_list():
    return [(y, q) for y in (2023, 2024, 2025) for q in range(4)]


def q_bounds(y, q):
    """(first hour, last hour) of calendar quarter q (0..3) of year y."""
    a = C3.kidx(C3.ms('%d-%02d-01' % (y, 3 * q + 1)))
    ny, nm = (y, 3 * q + 4) if q < 3 else (y + 1, 1)
    b = C3.kidx(C3.ms('%d-%02d-01' % (ny, nm))) - 1
    return a, b


def cv_masks(k, y, q, Hx):
    """validate mask, train mask for quarter fold (y, q)."""
    k = np.asarray(k)
    a, b = q_bounds(y, q)
    va = (k >= a) & (k <= b)
    k0 = C3.kidx(C3.ms(C3.TRAIN_START))
    band = (k >= a - Hx - 24) & (k <= b + Hx + 24)
    tr = (k >= k0) & (k < C3.NH) & ~va & ~band
    return va, tr


def cv_oof(D, xl, seeds=MOD.SEEDS):
    Hx = D.hs[xl]
    y = D.y[:, xl]
    X = D.X.values.astype(np.float64)
    oof = np.full(len(D.k), np.nan)
    folds = []
    for (yy, q) in quarter_list():
        va, tr = cv_masks(D.k, yy, q, Hx)
        iva, itr = np.flatnonzero(va), np.flatnonzero(tr)
        assert not (va & tr).any()
        if len(iva) == 0:
            folds.append(dict(quarter='%dQ%d' % (yy, q + 1), n_val=0, n_train=int(len(itr)), ic=None))
            continue
        ms = [MOD.fit_m1(X[itr], y[itr], D.w[itr], sd) for sd in seeds]
        oof[iva] = np.mean([m.predict(X[iva]) for m in ms], axis=0)
        folds.append(dict(quarter='%dQ%d' % (yy, q + 1), n_val=int(len(iva)), n_train=int(len(itr)),
                          ic=MOD.wspearman(oof[iva], y[iva], D.w[iva])))
    return oof, folds


def cont_port(D, xl, idx, score, K=5):
    k0, kl = C3.year_k0(2023), C3.year_k0(2026) - 1
    cand = P.CandB1(D.k[idx], D.c[idx], np.asarray(score, dtype=np.float64)[idx], idx)
    tr, eq, m = P.run(int(K), cand, P.XView(D.T, xl), k0, kl)
    return tr, eq, m


def span_mask(k):
    """entries allowed in the continuous 2023-2025 portfolio: [2023-01-01, 2025-12-31 23:00)."""
    k = np.asarray(k)
    return (k >= C3.year_k0(2023)) & (k < C3.year_k0(2026) - 1)


def span_thr(v, k):
    """80th pct over the WHOLE span (ERRATA1 C2), not per year."""
    m = span_mask(k) & np.isfinite(v)
    return float(np.quantile(np.asarray(v)[m], 0.80))


def c1_count(folds):
    return int(sum(1 for f in folds if f['ic'] is not None and f['ic'] > 0))


def c2_pass(pc):
    return bool(all(pc['pnl'][y] > 0 for y in (2023, 2024, 2025)) and pc['ret'] > pc['BL_S20']['ret'])


def c3_pass(pc):
    return bool(pc['ret'] > 0)


def portfolio_check(D, xl, oof):
    span = span_mask(D.k)
    isp = np.flatnonzero(span & np.isfinite(oof))
    thr = span_thr(oof, D.k)
    sel = isp[oof[isp] >= thr]
    tr, eq, m = cont_port(D, xl, sel, oof)
    out = dict(thr=thr, n_selected=int(len(sel)), ret=float(m['ret']), n=int(m['n']), maxdd_worst=float(m['maxdd_worst']),
               pnl={y: float(m.get('pnl_%d' % y, np.nan)) for y in (2023, 2024, 2025)})
    isp_all = np.flatnonzero(span)
    ths = span_thr(D.s, D.k)
    sel_s = isp_all[D.s[isp_all] >= ths]
    tr2, eq2, m2 = cont_port(D, xl, sel_s, D.s)
    out['BL_S20'] = dict(thr=ths, n_selected=int(len(sel_s)), ret=float(m2['ret']), n=int(m2['n']),
                         pnl={y: float(m2.get('pnl_%d' % y, np.nan)) for y in (2023, 2024, 2025)})
    return out


def run_all(D, out_path, seeds=MOD.SEEDS):
    t0 = time.time()
    rep = dict(kind=D.kind, label=LABEL)
    oof25, f25 = cv_oof(D, 1, seeds)
    rep['folds_exit2025'] = f25
    rep['C1_n_pos'] = c1_count(f25)
    rep['C1'] = bool(rep['C1_n_pos'] >= 9)
    pc = portfolio_check(D, 1, oof25)
    rep['C2_detail'] = pc
    rep['C2'] = c2_pass(pc)
    oof24, f24 = cv_oof(D, 0, seeds)
    rep['folds_exit2024'] = f24
    pc3 = portfolio_check(D, 0, oof24)
    rep['C3_detail'] = pc3
    rep['C3'] = c3_pass(pc3)
    rep['sec'] = time.time() - t0
    with open(out_path, 'w') as fh:
        json.dump(rep, fh, indent=1, default=float)
    return rep


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    assert len(sys.argv) == 3 and sys.argv[1] == '--real', __doc__
    D = WFO.load_real(sys.argv[2])
    run_all(D, C3.OUT + '/cv_b3.json')
