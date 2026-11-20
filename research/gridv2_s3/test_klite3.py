"""test_klite3.py - kiem chung TONG HOP Giai doan S3 (khong du lieu that).
R3: mo hinh lac quan = K_OPT3 (khoa "OPT"); dap an doc lap K_OPT3 = synth3.trade_engine_path3(mode 'opt3').
(1) ke toan; (2) dap an giai tich / MC doc lap (W = 60, thoat 0,5 d, T co dinh; luoi tick; drift); (3) truong hop bien;
(4) klite3 vs kref3 >= 9000 don vi; (5) khong nhin tuong lai; (6) tap khop K_PESS con cua K_OPT; (7) stats RW 12 o (null FWER,
hieu ung cay, INSUFFICIENT); (8) dieu kien (e'); (9) merge / luat W-D/W-C/W-A/W-B + o SELL; (10) rao chan; (11) runner tren lake
co / khong co rau gia.
Chay: python3 test_klite3.py [OUTDIR] [--no-runner]. Ghi OUTDIR/test_results.json + OUTDIR/hand_units.txt.
"""
import os
import sys
import json
import time
import math
import shutil
import logging
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import klite3  # noqa: E402
import kref3   # noqa: E402
import synth3  # noqa: E402
import stats   # noqa: E402
import stats3_extra  # noqa: E402

log = logging.getLogger("test3")
RES = []
SEED = 2026112150
W = klite3.W_ENTRY
XF = klite3.EXIT_FRAC


def rec(name, ok, **kw):
    RES.append(dict(name=name, ok=bool(ok), **kw))
    log.info("%-44s %s %s", name, "PASS" if ok else "FAIL", json.dumps(kw, default=float)[:300])


def grid_from_paths(px, tpm, valid=None, delist=-1):
    O, H, L, C = synth3.bars_from_trades(px, tpm)
    O, H, L, C = synth3.concat_grid(O, H, L, C)
    v = np.ones(C.size, bool) if valid is None else valid
    return klite3.prepare_grid(O, H, L, C, v, delist), (O, H, L, C, v)


def lists(G):
    return [[None if not np.isfinite(x) else float(x) for x in G[k]] for k in ("O", "H", "L", "C")]


def alt_side(n):
    return np.where(np.arange(n) % 2 == 0, 1, -1).astype(np.int8)


def mse(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    if x.size < 2:
        return float("nan"), float("nan"), int(x.size)
    return float(x.mean()), float(x.std(ddof=1) / math.sqrt(x.size)), int(x.size)


# ------------------------------------------------------------------ (1) ke toan
def t_accounting(rng):
    px = synth3.lattice_paths(rng, 1, 60000 * 4, 20000, bounce_h=2) * 0.01
    valid = np.ones(60000, bool)
    valid[10000:10020] = False
    valid[20000:20200] = False
    G, _ = grid_from_paths(px, 4, valid, delist=55000)
    t0 = np.arange(61, 54900, 7)
    t0 = t0[G["valid"][t0 - 1]]
    fs = np.arange(3, 60000, 240)
    fr = rng.normal(1e-4, 3e-4, fs.size)
    worst = worst_fee = worst_slip = 0.0
    n = 0
    kinds = np.zeros(5, int)
    for model in ("OPT", "PESS"):
        for d in (0.0006, 0.0025):
            for T in klite3.T_LIST:
                for withf in (False, True):
                    R = klite3.run_units(G, t0, d, W, T, 0.01, 7e-4, model, alt_side(t0.size), fs if withf else None,
                                         fr if withf else None)
                    f = R["filled"] & (R["excl"] != 2)
                    n += int(f.sum())
                    kinds += np.bincount(R["kind"][f], minlength=5)
                    resid = R["net"] - R["gross"] - (R["fund"] if withf else 0.0) + R["fee"] + R["slip"]
                    worst = max(worst, float(np.max(np.abs(resid[f]))))
                    if not withf:
                        assert np.all(R["fund"][f] == 0)
                    fm = klite3.FEE_MAKER[model]
                    q = R["xpx"][f] / R["entry"][f]
                    k = R["kind"][f]
                    fx = np.where(k == 1, fm, np.where(k == 2, fm if model == "OPT" else 5e-4, 5e-4))
                    worst_fee = max(worst_fee, float(np.max(np.abs(R["fee"][f] - 1e4 * (fm + fx * q)))))
                    if model == "OPT":
                        sl = np.zeros(k.size)
                    else:
                        sl = np.where(k == 3, 50e-4, np.where((k == 2) | (k == 4), 7e-4, 0.0)) * q * 1e4
                    worst_slip = max(worst_slip, float(np.max(np.abs(R["slip"][f] - sl))))
                    g = R["side"][f] * (R["xpx"][f] - R["entry"][f]) / R["entry"][f] * 1e4
                    worst = max(worst, float(np.max(np.abs(g - R["gross"][f]))))
    rec("acct_identity_fee_slip_gross", worst < 1e-9 and worst_fee < 1e-9 and worst_slip < 1e-9 and np.all(kinds[1:] > 0),
        n_units=n, max_resid_bps=worst, max_fee_resid=worst_fee, max_slip_resid=worst_slip,
        kinds=dict(limit=int(kinds[1]), timeout=int(kinds[2]), delist=int(kinds[3]), taker_beyond=int(kinds[4])))


# ------------------------------------------------------------------ (2) dap an giai tich / MC doc lap
def lattice_units(rng, npath, dt, T, p_up=0.5, phi=0.0, h=0, tpm=1, p0=1000, tick=0.01):
    nmin = W + T + 64
    px = synth3.lattice_paths(rng, npath, nmin * tpm, p0, p_up=p_up, phi=phi, bounce_h=h).astype(np.float64) * tick
    G, raw = grid_from_paths(px, tpm)
    t0 = np.arange(npath) * nmin + 1
    return G, px, t0, dt / p0, nmin


def t_analytic(rng):
    """Luoi tick, 1 giao dich / phut (K = muc giao dich): martingale -> E[gross K_OPT] = 0; K_PESS: gross + tick/L (1 + 1[limit])
    co TB 0 (xuyen 1 tick vao + ra). Drift p_up = 0,5 + delta: Wald E = side x 2 delta tick x thoi gian giu / L."""
    for T in klite3.T_LIST:
        G, px, t0, d, nmin = lattice_units(rng, 20000, 8, T)
        for model in ("OPT", "PESS"):
            R = klite3.run_units(G, t0, d, W, T, 0.01, 0.0, model, alt_side(t0.size))
            f = R["filled"]
            res = R["gross"][f].copy()
            if model == "PESS":
                res = res + 1e4 * 0.01 / R["entry"][f] * (1 + (R["kind"][f] == 1))
            m, se, n = mse(res)
            sd_ = R["side"][f]
            zb, zs = mse(res[sd_ == 1]), mse(res[sd_ == -1])
            rec("analytic_martingale_%s_T%d" % (model, T), abs(m) <= 3 * se and n >= 3000 and abs(zb[0]) <= 3 * zb[1]
                and abs(zs[0]) <= 3 * zs[1], n=n, resid_mean=m, resid_se=se, z=m / se, z_buy=zb[0] / zb[1], z_sell=zs[0] / zs[1],
                p_fill=float(f.mean()), p_lim=float(np.mean(R["kind"][f] == 1)), mean_gross=mse(R["gross"][f])[0])
    dlt = 0.02
    for T in klite3.T_LIST:
        G, px, t0, d, nmin = lattice_units(rng, 20000, 8, T, p_up=0.5 + dlt)
        for model in ("OPT", "PESS"):
            R = klite3.run_units(G, t0, d, W, T, 0.01, 0.0, model, alt_side(t0.size))
            f = R["filled"]
            side = R["side"][f].astype(float)
            res = R["gross"][f] - 1e4 * side * 2 * dlt * 0.01 * R["dur"][f] / R["entry"][f]
            if model == "PESS":
                res = res + 1e4 * 0.01 / R["entry"][f] * (1 + (R["kind"][f] == 1))
            m, se, n = mse(res)
            zb, zs = mse(res[side == 1]), mse(res[side == -1])
            rec("analytic_drift_wald_%s_T%d" % (model, T), abs(m) <= 3 * se and n >= 3000 and abs(zb[0]) <= 3 * zb[1]
                and abs(zs[0]) <= 3 * zs[1], n=n, resid_mean=m, resid_se=se, z=m / se, z_buy=zb[0] / zb[1], z_sell=zs[0] / zs[1],
                gross_buy=mse(R["gross"][f][side == 1])[0], gross_sell=mse(R["gross"][f][side == -1])[0])


def t_indep_mc(rng):
    """Engine muc giao dich DOC LAP (synth3.trade_engine_path3): cung duong (tpm 1) phai trung tung don vi; duong moi -> TB trong 3 SE.
    tpm 10: K_OPT >= touch, K_PESS <= through (theo TB cap don vi)."""
    NP = 16000
    for lab, phi, h in (("bounce_h2", 0.0, 2), ("ar1_m0.3", -0.3, 0), ("drift_bounce1", 0.0, 1)):
        p_up = 0.52 if lab.startswith("drift") else 0.5
        T = 240
        G, px, t0, d, nmin = lattice_units(rng, NP, 8, T, p_up=p_up, phi=phi, h=h)
        for model, mode in (("OPT", "opt3"), ("PESS", "through")):
            R = klite3.run_units(G, t0, d, W, T, 0.01, 0.0, model, alt_side(t0.size))
            m1, s1, n1 = mse(R["gross"][R["filled"]])
            px2 = synth3.lattice_paths(np.random.default_rng(rng.integers(1 << 62)), NP, nmin, 1000, p_up=p_up, phi=phi,
                                       bounce_h=h).astype(np.float64) * 0.01
            out = []
            for i in range(NP):
                r = synth3.trade_engine_path3(px2[i], 1, 1, d, W, T, 0.01, mode, 1 if i % 2 == 0 else -1, XF)
                if r is not None:
                    out.append(r[0])
            m2, s2, n2 = mse(out)
            z = (m1 - m2) / math.sqrt(s1 ** 2 + s2 ** 2)
            mx = 0.0
            for i in range(0, NP, 5):
                r = synth3.trade_engine_path3(px[i], 1, 1, d, W, T, 0.01, mode, 1 if i % 2 == 0 else -1, XF)
                if r is None:
                    mx = max(mx, 0.0 if not R["filled"][i] else 1e9)
                else:
                    mx = max(mx, abs(r[0] - R["gross"][i]) if R["filled"][i] else 1e9)
            rec("indepMC_%s_%s" % (lab, model), abs(z) <= 3 and n1 >= 2000 and mx < 1e-9, pipeline_mean=m1, pipeline_se=s1,
                answer_mean=m2, answer_se=s2, z=z, n=n1, paired_same_path_max_abs_diff=mx)
    for gen in ("lat", "gbm"):
        T, tpm, npath = 240, 10, 4000
        nmin = W + T + 64
        if gen == "lat":
            px = synth3.lattice_paths(rng, npath, nmin * tpm, 1000, bounce_h=1).astype(np.float64) * 0.01
            tick, d = 0.01, 0.008
        else:
            px, tick = synth3.gbm_paths(rng, npath, nmin, tpm, 0.30)
            d = 0.012
        G, raw = grid_from_paths(px, tpm)
        t0 = np.arange(npath) * nmin + 1
        for model, mode in (("OPT", "opt3"), ("PESS", "through")):
            R = klite3.run_units(G, t0, d, W, T, tick, 0.0, model, alt_side(npath))
            tr = np.full(npath, np.nan)
            for i in range(npath):
                r = synth3.trade_engine_path3(px[i], tpm, 1, d, W, T, tick, mode, 1 if i % 2 == 0 else -1, XF)
                if r is not None:
                    tr[i] = r[0]
            both = R["filled"] | np.isfinite(tr)
            diff = (np.where(np.isfinite(R["gross"]), R["gross"], 0.0) - np.where(np.isfinite(tr), tr, 0.0))[both]
            m, se, n = mse(diff)
            # R3: K_OPT3 phai TRUNG TUNG DON VI voi dap an muc giao dich 'opt3' (quy tac bieu dien duoc bang nen); K_PESS <= through
            ok = (bool(np.all(np.abs(diff) < 1e-9)) and np.array_equal(R["filled"], np.isfinite(tr))) if model == "OPT" else (m <= 3 * se)
            rec("bracket_%s_tpm10_%s" % (gen, "OPT3_exact" if model == "OPT" else model), ok and n >= 500, paired_diff=m, se=se, n=n,
                fill_K=float(R["filled"].mean()), fill_trade=float(np.isfinite(tr).mean()))


# ------------------------------------------------------------------ (3) truong hop bien (nen tay) - klite3 VA kref3
def mk(bars, delist=-1):
    O = np.array([b[0] if b else np.nan for b in bars])
    H = np.array([b[1] if b else np.nan for b in bars])
    L = np.array([b[2] if b else np.nan for b in bars])
    C = np.array([b[3] if b else np.nan for b in bars])
    v = np.array([b is not None for b in bars])
    return klite3.prepare_grid(O, H, L, C, v, delist)


def flat(n, p=100.0):
    return [(p, p, p, p)] * n


def both(bars, t0, d, T, model, side, tick=0.01, slip=5e-4, funding=(), delist=-1):
    G = mk(bars, delist)
    fs = np.array([s for s, _ in funding], np.int64) if funding else None
    fr = np.array([r for _, r in funding]) if funding else None
    R = klite3.run_units(G, [t0], d, W, T, tick, slip, model, side, fs, fr)
    k = {key: (v[0] if hasattr(v, "__len__") else v) for key, v in R.items()}
    Ls = lists(G)
    r = kref3.simulate_unit(*Ls, t0, d, W, T, tick, slip, model, side, list(funding), delist, XF)
    same = bool(k["filled"]) == r["filled"] and int(k["excl"]) == r["excl"]
    if same and r["filled"] and r["excl"] != 2:
        same = (int(k["f"]) == r["f"] and int(k["x"]) == r["x"] and klite3.EXIT_NAMES[int(k["kind"])] == r["kind"]
                and all(abs(float(k[q]) - r[q]) < 1e-9 for q in ("gross", "fee", "slip", "fund", "net")))
    return k, r, same


def t_edges():
    T = 240
    n = 700
    t0 = 10
    out = {}
    # E1 khop phut CUOI cua W (t0+59) / phut t0+60 khong khop
    b = flat(n); b[t0 + 59] = (100.0, 100.0, 98.9, 99.0)
    k1, r1, s1 = both(b, t0, 0.01, T, "PESS", 1)
    b = flat(n); b[t0 + 60] = (100.0, 100.0, 98.9, 99.0)
    k2, r2, s2 = both(b, t0, 0.01, T, "OPT", 1)
    out["E1_fill_last_minute_of_W"] = s1 and s2 and k1["filled"] and int(k1["f"]) == t0 + 59 and not k2["filled"]
    # E2 khong khop trong W
    k, r, s = both(flat(n), t0, 0.01, T, "OPT", -1)
    out["E2_no_fill"] = s and not k["filled"] and int(k["excl"]) == 0
    # E3 thoat cung phut (OPT) / phut sau (PESS)
    b = flat(n); f = t0 + 5
    b[f] = (99.6, 99.6, 98.9, 99.2); b[f + 1] = (99.3, 99.6, 99.2, 99.4)
    ko, ro, so = both(b, t0, 0.01, T, "OPT", 1)
    kp, rp, sp = both(b, t0, 0.01, T, "PESS", 1)
    out["E3_close_below_X_OPT3_and_PESS_next_minute"] = (so and sp and int(ko["x"]) == f + 1 and int(ko["kind"]) == 1 and int(kp["x"]) == f + 1
                                               and int(kp["kind"]) == 1 and abs(float(ko["xpx"]) - 99.50) < 1e-9
                                               and abs(float(ko["gross"]) - (99.50 - 99.0) / 99.0 * 1e4) < 1e-9)
    # E4 gia vuot X luc DONG phut khop: PESS taker_beyond tai X o f+1 (taker + truot); OPT limit cung phut
    b = flat(n); b[f] = (100.0, 100.3, 98.9, 99.7)
    ko, ro, so = both(b, t0, 0.01, T, "OPT", 1)
    kp, rp, sp = both(b, t0, 0.01, T, "PESS", 1, slip=6e-4)
    X = 99.50
    out["E4_taker_beyond_PESS"] = (so and sp and int(ko["kind"]) == 1 and int(ko["x"]) == f and int(kp["kind"]) == 4
                                  and int(kp["x"]) == f + 1 and abs(float(kp["xpx"]) - X) < 1e-9
                                  and abs(float(kp["fee"]) - 1e4 * (4e-4 + 5e-4 * X / 99.0)) < 1e-9
                                  and abs(float(kp["slip"]) - 6.0 * X / 99.0) < 1e-9)
    # E5 het han T: khop roi gia nam 99,10 -> close phut f+T
    b = flat(n); b[f] = (99.1, 99.1, 98.9, 99.1)
    for i in range(f + 1, n):
        b[i] = (99.1, 99.1, 99.1, 99.1)
    ko, ro, so = both(b, t0, 0.01, T, "OPT", 1)
    kp, rp, sp = both(b, t0, 0.01, T, "PESS", 1, slip=6e-4)
    g = (99.1 - 99.0) / 99.0 * 1e4
    out["E5_expiry_T"] = (so and sp and int(ko["kind"]) == 2 and int(ko["x"]) == f + T and int(kp["x"]) == f + T
                         and abs(float(ko["gross"]) - g) < 1e-9 and abs(float(ko["fee"]) - 1e4 * (2e-4 + 2e-4 * 99.1 / 99.0)) < 1e-9
                         and abs(float(kp["fee"]) - 1e4 * (4e-4 + 5e-4 * 99.1 / 99.0)) < 1e-9
                         and abs(float(kp["slip"]) - 6.0 * 99.1 / 99.0) < 1e-9)
    # E6 het han roi vao lo ngan (10 phut) -> phut hop le ke tiep, KHONG loai
    b2 = list(b)
    for i in range(f + T, f + T + 10):
        b2[i] = None
    b2[f + T + 10] = (99.2, 99.2, 99.2, 99.2)
    ko, ro, so = both(b2, t0, 0.01, T, "PESS", 1)
    out["E6_expiry_in_short_gap"] = so and int(ko["kind"]) == 2 and int(ko["x"]) == f + T + 10 and int(ko["excl"]) == 0
    # E7 delist giua don vi: thoat close phut hop le cuoi, taker (+50 bps PESS)
    dl = f + 30
    ko, ro, so = both(b, t0, 0.01, T, "OPT", 1, delist=dl)
    kp, rp, sp = both(b, t0, 0.01, T, "PESS", 1, delist=dl)
    out["E7_delist_mid_unit"] = (so and sp and int(ko["kind"]) == 3 and int(ko["x"]) == dl and int(kp["kind"]) == 3
                                and abs(float(kp["slip"]) - 50.0 * 99.1 / 99.0) < 1e-9
                                and abs(float(ko["fee"]) - 1e4 * (2e-4 + 5e-4 * 99.1 / 99.0)) < 1e-9)
    # E8 lo <= 60 phut trong W: khong khop trong lo, lenh van song; lo > 60 -> loai
    b = flat(n)
    for i in range(t0 + 3, t0 + 20):
        b[i] = None
    b[t0 + 25] = (100.0, 100.0, 98.9, 99.0)
    k, r, s = both(b, t0, 0.01, T, "OPT", 1)
    b3 = flat(n)
    for i in range(t0 + 3, t0 + 70):
        b3[i] = None
    k3, r3, s3 = both(b3, t0, 0.01, T, "OPT", 1)
    b4 = flat(n); b4[t0 + 2] = (99.0, 99.0, 98.9, 99.0)
    for i in range(t0 + 3, n):
        b4[i] = (99.0, 99.0, 99.0, 99.0)
    for i in range(t0 + 100, t0 + 170):
        b4[i] = None
    k4, r4, s4 = both(b4, t0, 0.01, T, "OPT", 1)
    out["E8_gap_le60_ok_gt60_excluded"] = (s and s3 and s4 and k["filled"] and int(k["f"]) == t0 + 25 and int(k["excl"]) == 0
                                          and int(k3["excl"]) == 1 and k4["filled"] and int(k4["excl"]) == 1)
    # E9 doi tick: cung m0, d -> muc lam tron theo tick cua don vi
    b = flat(n); b[t0 + 1] = (100.0, 100.0, 98.0, 98.5)
    ka, ra, sa = both(b, t0, 0.0123, T, "OPT", 1, tick=0.01)
    kb, rb, sb = both(b, t0, 0.0123, T, "OPT", 1, tick=0.05)
    out["E9_tick_change"] = (sa and sb and abs(float(ka["entry"]) - 98.77) < 1e-9 and abs(float(kb["entry"]) - 98.75) < 1e-9
                            and abs(float(ka["X"]) - math.ceil(98.77 * (1 + 0.5 * 0.0123) / 0.01 - 1e-7) * 0.01) < 1e-9
                            and abs(float(kb["X"]) - math.ceil(98.75 * (1 + 0.5 * 0.0123) / 0.05 - 1e-7) * 0.05) < 1e-9)
    # E10 moc funding: tinh khi f < s <= x
    b = flat(n); f = t0 + 5
    b[f] = (99.1, 99.1, 98.9, 99.1)
    for i in range(f + 1, f + 50):
        b[i] = (99.1, 99.1, 99.1, 99.1)
    b[f + 50] = (99.2, 99.6, 99.2, 99.5)
    x = f + 50
    fund = [(f, 1e-3), (f + 1, 2e-4), (x, 3e-4), (x + 1, 7e-3)]
    k, r, s = both(b, t0, 0.01, T, "OPT", 1, funding=fund)
    exp = -(2e-4 * 99.1 + 3e-4 * 99.1) / 99.0 * 1e4
    out["E10_funding_window"] = s and int(k["x"]) == x and abs(float(k["fund"]) - exp) < 1e-9
    # E11 BUY va SELL doc lap cung phut
    b = flat(n); b[t0 + 1] = (100.2, 101.5, 98.5, 100.0)
    kb_, rb_, sb_ = both(b, t0, 0.01, T, "OPT", 1)
    ks_, rs_, ss_ = both(b, t0, 0.01, T, "OPT", -1)
    out["E11_buy_sell_independent_same_minute"] = (sb_ and ss_ and kb_["filled"] and ks_["filled"] and int(kb_["f"]) == t0 + 1
                                                   and int(ks_["f"]) == t0 + 1 and int(kb_["x"]) == t0 + 1 and int(ks_["x"]) == t0 + 1
                                                   and abs(float(kb_["gross"]) - (99.50 - 99.0) / 99.0 * 1e4) < 1e-9
                                                   and abs(float(ks_["gross"]) - (101.0 - 100.49) / 101.0 * 1e4) < 1e-9)
    # E12 thoat SAU khi W het (T tinh tu phut khop, khong tu t0)
    b = flat(n); f = t0 + 50
    b[f] = (100.0, 100.0, 98.9, 99.1)
    for i in range(f + 1, f + 200):
        b[i] = (99.1, 99.1, 99.1, 99.1)
    b[f + 200] = (99.2, 99.6, 99.2, 99.5)
    for i in range(f + 201, n):
        b[i] = (99.5, 99.5, 99.5, 99.5)
    k, r, s = both(b, t0, 0.01, T, "PESS", 1)
    out["E12_exit_after_W_ends"] = s and int(k["kind"]) == 1 and int(k["x"]) == f + 200 and f + 200 > t0 + W
    # E14 (R3-1) K_OPT3: phut khop open/high > X nhung close < X (cu roi khong hoi) -> KHONG thoat cung phut; gia nam 99,0 -> het han
    b = flat(n); f = t0 + 5
    b[f] = (100.0, 100.0, 98.9, 99.0)
    for i in range(f + 1, n):
        b[i] = (99.0, 99.0, 99.0, 99.0)
    ko, ro, so = both(b, t0, 0.01, T, "OPT", 1)
    b2 = list(b); b2[f] = (100.0, 100.0, 98.9, 99.5)
    k2, r2, s2 = both(b2, t0, 0.01, T, "OPT", 1)
    out["E14_OPT3_no_same_minute_exit_unless_close_beyond_X"] = (so and s2 and int(ko["kind"]) == 2 and int(ko["x"]) == f + T
                                                                and abs(float(ko["gross"])) < 1e-9 and int(k2["kind"]) == 1
                                                                and int(k2["x"]) == f)
    # E13 muc gia <= 0 bi chan (runner loc truoc): kernel assert
    try:
        klite3.run_units(mk(flat(n)), [t0], 1.2, W, T, 0.01, 0.0, "OPT", 1)
        out["E13_nonpositive_level_asserts"] = False
    except AssertionError:
        out["E13_nonpositive_level_asserts"] = True
    rec("edges_S3_klite3_and_kref3", all(out.values()), **out)


# ------------------------------------------------------------------ (4) klite3 vs kref3 (>= 9000 don vi) + (6) PESS con cua OPT
def t_ref_compare(rng, outdir):
    lines = []
    tot = bad = nfill = 0
    kinds = np.zeros(5, int)
    nexcl = 0
    sub_viol = sub_n = 0
    for case in range(4):
        tpm = [1, 4, 10, 6][case]
        nmin = 40000
        px = synth3.lattice_paths(rng, 1, nmin * tpm, 3000, phi=[0, -0.2, 0, 0.1][case], bounce_h=[0, 2, 1, 3][case]) * 0.01
        valid = rng.random(nmin) > 0.003
        valid[15000:15070] = False
        valid[25000:25045] = False
        dl = 35600 if case in (1, 2) else -1
        G, _ = grid_from_paths(px, tpm, valid, dl)
        Ls_ = lists(G)
        ser = kref3.Series(*Ls_, delist=dl)
        fs = np.arange(17, nmin, [480, 240, 60, 480][case])
        fr = rng.normal(1e-4, 2e-4, fs.size)
        fl = list(zip(fs.tolist(), fr.tolist()))
        t0 = np.arange(70, 35500, 61)
        t0 = t0[G["valid"][t0 - 1]]
        hsd = 7.7 * math.sqrt(tpm) / 3000.0
        for (dk, T) in ((1.0, 240), (2.0, 1440), (0.6, 240)):
            d = dk * hsd
            sides = alt_side(t0.size)
            RR = {}
            for model in ("OPT", "PESS"):
                R = klite3.run_units(G, t0, d, W, T, 0.01, 6e-4, model, sides, fs, fr)
                RR[model] = R
                for i, t in enumerate(t0):
                    r = kref3.simulate_unit(None, None, None, None, int(t), d, W, T, 0.01, 6e-4, model, int(sides[i]), fl, dl,
                                            XF, series=ser)
                    tot += 1
                    same = r["filled"] == bool(R["filled"][i]) and r["excl"] == int(R["excl"][i])
                    nexcl += int(r["excl"] != 0)
                    if same and r["filled"] and r["excl"] != 2:
                        nfill += 1
                        kinds[R["kind"][i]] += 1
                        same = (r["side"] == R["side"][i] and r["f"] == R["f"][i] and r["x"] == R["x"][i] and
                                r["kind"] == klite3.EXIT_NAMES[int(R["kind"][i])] and
                                all(abs(r[k] - R[k][i]) < 1e-9 for k in ("gross", "fee", "slip", "fund", "net")))
                    bad += 0 if same else 1
                    if r["filled"] and r["excl"] != 2 and len(lines) < 30 and (i % 41 == 0 or R["kind"][i] in (3, 4)):
                        lines.append("case%d %-4s d=%.5f W=%d T=%d t0=%d m0=%.2f side=%+d f=%d x=%d kind=%s entry=%.2f X=%.2f exit=%.2f | "
                                     "klite3 gross=%.4f fee=%.4f slip=%.4f fund=%.4f net=%.4f | kref3 net=%.4f | %s" % (
                                         case, model, d, W, T, t, R["m0"][i], R["side"][i], R["f"][i], R["x"][i],
                                         klite3.EXIT_NAMES[int(R["kind"][i])], R["entry"][i], R["X"][i], R["xpx"][i], R["gross"][i],
                                         R["fee"][i], R["slip"][i], R["fund"][i], R["net"][i], r["net"],
                                         "TRUNG" if abs(r["net"] - R["net"][i]) < 1e-9 else "LECH"))
            po, pp = RR["OPT"], RR["PESS"]
            sub_n += int(pp["filled"].sum())
            sub_viol += int(np.sum(pp["filled"] & (~po["filled"] | (po["f"] > pp["f"]))))
    with open(os.path.join(outdir, "hand_units.txt"), "w") as fh:
        fh.write("In tay: klite3 (vector) vs kref3 (python thuan, doc lap) - %d don vi mau\n" % len(lines))
        fh.write("\n".join(lines) + "\n")
    rec("ref3_vs_klite3_all_units", bad == 0 and tot >= 9000 and len(lines) >= 20 and kinds[3] > 0 and kinds[4] > 0 and nexcl > 0,
        n_units=tot, n_filled=nfill, n_excluded=nexcl, n_mismatch=bad,
        exit_kinds=dict(limit=int(kinds[1]), timeout=int(kinds[2]), delist=int(kinds[3]), taker_beyond=int(kinds[4])),
        n_hand=len(lines))
    rec("pess_fill_subset_of_opt", sub_viol == 0 and sub_n > 1000, n_pess_filled=sub_n, violations=sub_viol,
        note="PESS khop => OPT khop va f_OPT <= f_PESS (cung t0, ben)")


# ------------------------------------------------------------------ (5) khong nhin tuong lai (kernel + feature)
def t_lookahead(rng):
    px = synth3.lattice_paths(rng, 1, 30000 * 5, 30000, bounce_h=1) * 0.01
    G, raw = grid_from_paths(px, 5)
    tc = 14000
    t0 = np.arange(61, tc, 13)
    fs = np.arange(5, 30000, 480)
    fr = np.full(fs.size, 1e-4)
    O, H, L, C, v = [np.array(a, copy=True) for a in raw]
    O[tc:] = rng.uniform(1, 1000, O.size - tc)
    H[tc:] = O[tc:] * 2
    L[tc:] = O[tc:] / 2
    C[tc:] = O[tc:]
    v[tc:] = rng.random(v.size - tc) < 0.7
    G2 = klite3.prepare_grid(O, H, L, C, v, -1)
    fr2 = np.where(fs >= tc, 0.05, fr)
    nb, nchk = 0, 0
    for model in ("OPT", "PESS"):
        for T in klite3.T_LIST:
            R1 = klite3.run_units(G, t0, 0.0012, W, T, 0.01, 5e-4, model, alt_side(t0.size), fs, fr)
            R2 = klite3.run_units(G2, t0, 0.0012, W, T, 0.01, 5e-4, model, alt_side(t0.size), fs, fr2)
            end = np.where(R1["filled"], R1["x"], t0 + W - 1)
            k = end < tc - 1
            nchk += int(k.sum())
            for key in ("filled", "side", "f", "x", "kind", "excl"):
                nb += int(np.sum(R1[key][k] != R2[key][k]))
            nb += int(np.sum(np.abs(np.nan_to_num(R1["net"][k]) - np.nan_to_num(R2["net"][k])) > 0))
    Gd = klite3.prepare_grid(*raw[:4], raw[4], -1)
    nday = 30000 // 1440
    f1 = klite3.daily_features(Gd, nday)
    f2 = klite3.daily_features(G2, nday)
    s1, s2 = klite3.sigma_exante(f1["close"], 5, 3), klite3.sigma_exante(f2["close"], 5, 3)
    dc = tc // 1440
    feat_ok = np.allclose(s1[: dc + 1], s2[: dc + 1], equal_nan=True) and np.array_equal(f1["tick"][:dc], f2["tick"][:dc], equal_nan=True)
    rec("no_lookahead_kernel_and_features", nb == 0 and nchk > 1000 and feat_ok, n_checked=nchk, n_diff=nb, feat_ok=bool(feat_ok))


# ------------------------------------------------------------------ (7) thong ke: RW studentized 12 o
def _null_panel(rng, D, J, heavy=False):
    common = rng.normal(0, 1, (D, 1))
    if heavy:
        Z = 0.6 * common + 0.8 * rng.standard_t(4, (D, J)) / math.sqrt(2.0)
        N = rng.poisson(rng.uniform(5, 60, J)[None, :] * (1 + 2.0 * (rng.random((D, 1)) < 0.05)), (D, J)).astype(float)
    else:
        Z = 0.6 * common + 0.8 * rng.normal(0, 1, (D, J))
        N = np.full((D, J), 30.0)
    return Z, N


def t_stats(rng):
    D, J = 731, 12
    nsim = 300
    lim = stats.ALPHA_FWER + 3 * math.sqrt(stats.ALPHA_FWER * (1 - stats.ALPHA_FWER) / nsim)
    for heavy in (False, True):
        fw, marg = 0, []
        for s_ in range(nsim):
            Z, N = _null_panel(rng, D, J, heavy)
            S = 4.0 * N + 300.0 * Z * np.sqrt(N)
            r = stats.cell_stats(S, N, 4.0, 3000 + s_, B=300)
            fw += int(r["rw_reject"].any())
            marg.append(float(np.mean(r["p_marg"] <= 0.05)))
        rate = fw / nsim
        rec("stats_rw12_fwer_null_%s" % ("heavy" if heavy else "gauss"), rate <= lim, fwer_rw=rate, limit=lim,
            alpha=stats.ALPHA_FWER, marginal_size_5pct=float(np.mean(marg)), nsim=nsim, J=J)
    nsim = 200
    lim = stats.ALPHA_FWER + 3 * math.sqrt(stats.ALPHA_FWER * (1 - stats.ALPHA_FWER) / nsim)
    hit, false_any = np.zeros(3), 0
    for s_ in range(nsim):
        Z, N = _null_panel(rng, D, J, True)
        sd_cell = 300.0 / np.sqrt(N.sum(0))
        mu = np.full(J, 4.0)
        mu[:3] += 5.0 * sd_cell[:3]
        S = mu[None, :] * N + 300.0 * Z * np.sqrt(N)
        r = stats.cell_stats(S, N, 4.0, 7000 + s_, B=300)
        hit += r["rw_reject"][:3]
        false_any += int(r["rw_reject"][3:].any())
    pw = hit / nsim
    rec("stats_rw12_planted_effect", bool(pw.min() >= 0.6 and false_any / nsim <= lim), power_per_cell=pw.tolist(),
        fwer_among_null=false_any / nsim, limit=lim, nsim=nsim)
    Z, N = _null_panel(rng, D, 6, False)
    N[:, 1] = 0.0
    N[:, 2] = 0.0
    N[:150, 2] = 1.0
    N[:, 3] = 0.0
    N[np.arange(0, 12 * 20, 20), 3] = 30.0          # 12 khoi co don vi (< 13) -> INSUFFICIENT (ii)
    S = -20.0 * N + 300.0 * Z * np.sqrt(N)
    S[:, 2] = 500.0 * N[:, 2]
    r = stats.cell_stats(S, N, 4.0, 11, B=500)
    ins = r["insufficient"].tolist()
    ok_i = (ins == [False, True, True, True, False, False] and not r["rw_reject"][2] and r["p_rw"][1] == 1.0 and r["p_rw"][2] == 1.0
            and np.isnan(r["upper_sim95"][1]) and np.isnan(r["p_marg"][2]) and np.all(np.isfinite(r["upper_sim95"][[0, 4, 5]]))
            and r["insufficient_reason"][3] == "ii" and r["alpha_upper"] == 0.05 and r["alpha"] == 0.04)
    rec("stats_insufficient_i_ii_iii", ok_i, insufficient=ins, reasons=r["insufficient_reason"], p_rw=r["p_rw"].tolist())


# ------------------------------------------------------------------ (8) (9) merge / luat tren bang reduced gia
def _fake_reduced(root, rng, mu, nper, manifest=None, block_boost=None, sd=300.0):
    """Bang reduced gia 12 o: mu[h][c] bps/don vi net, nper[h][c] don vi/ngay (< 1: xac suat 1 don vi/ngay), h 0 = A, 1 = B.
    block_boost: dict (h, c) -> (ngay_bat_dau_trong_nua, so_ngay, bps_them_moi_don_vi) - cay 1 khoi loi cuc lon."""
    import runner3_kaggle as rk
    import pandas as pd
    nday = (rk.SEAL - rk.DATA_START) // rk.DAY
    d0 = (rk.STUDY_START - rk.DATA_START) // rk.DAY
    dB = (rk.HALF_B - rk.DATA_START) // rk.DAY
    rows, sh = [], []
    for model in ("OPT", "PESS"):
        for hv, (lo, hi) in enumerate(((d0, dB), (dB, nday))):
            Dn = hi - lo
            for c in range(12):
                m_ = mu[model][hv][c] if isinstance(mu, dict) else mu[hv][c]
                npc = nper[hv][c]
                if npc <= 0:
                    continue
                n = np.full(Dn, float(npc)) if npc >= 1 else (rng.random(Dn) < npc).astype(float)
                z = rng.normal(0, 1, Dn)
                net = m_ * n + sd * np.sqrt(n) * z
                if block_boost and (hv, c) in block_boost:
                    a, L_, add = block_boost[(hv, c)]
                    net[a:a + L_] += add * n[a:a + L_]
                df = pd.DataFrame({k: np.zeros(Dn) for k in rk.SUM_COLS})
                df["place"], df["fill"], df["net"], df["neth"], df["gross"] = 3 * n, n, net, net, net + 4 * n
                df["day"], df["cell"], df["model"] = np.arange(lo, hi), c, model
                rows.append(df[df.place > 0])
                for k in range(6):
                    sh.append(dict(sym="S%d" % k, cell=c, model=model, half=hv, net=net.sum() / 6, neth=net.sum() / 6,
                                   fill=n.sum() / 6))
    os.makedirs(os.path.join(root, "reduced"), exist_ok=True)
    pd.concat(rows, ignore_index=True).to_parquet(os.path.join(root, "reduced", "agg.parquet"), index=False)
    pd.DataFrame(sh).to_parquet(os.path.join(root, "reduced", "shalf.parquet"), index=False)
    if manifest is not None:
        json.dump(manifest, open(os.path.join(root, "manifest.json"), "w"))
        json.dump(dict(all_pass=True, V3=dict(skip_px_by_cell={"0": 3}),
                       V5=dict(covered_ctside=[[ci, sd] for ci in range(6) for sd in (1, -1)])),
                  open(os.path.join(root, "validate.json"), "w"))


def t_eprime(rng, outdir):
    """(8) Dieu kien (e'): drop_top_block tinh dung; o co 1 khoi loi cuc lon -> KHONG PASS; pass_cell: chi (e') sai -> khong PASS."""
    import runner3_kaggle as rk
    c = {}
    D = 731
    S = rng.normal(0, 50, (D, 3))
    N = np.ones((D, 3))
    S[400:420, 1] += 10000.0
    S[725:731, 2] += 99999.0                      # khoi cuoi cat (6 ngay)
    r = stats3_extra.drop_top_block(S, N)
    man = []
    for j in range(3):
        best, bk = -np.inf, None
        for a in range(0, D, 20):
            v = S[a:min(a + 20, D), j].sum()
            if v > best:
                best, bk = v, a
        keep = np.ones(D, bool)
        keep[bk:min(bk + 20, D)] = False
        man.append((S[keep, j].sum() / N[keep, j].sum(), bk))
    c["manual_equal"] = all(abs(r["M_drop"][j] - man[j][0]) < 1e-9 and r["top_lo"][j] == man[j][1] for j in range(3))
    c["block_400_found"] = bool(r["top_lo"][1] == 400 and r["top_lo"][2] == 720)
    N2 = N.copy(); N2[:, 0] = 0; N2[100:110, 0] = 1
    S2 = S * N2; S2[100:110, 0] = 500.0
    c["all_units_in_top_block_nan"] = bool(np.isnan(stats3_extra.drop_top_block(S2, N2)["M_drop"][0]))
    # pass_cell: moi dieu kien dung tru (e') -> False
    A = dict(insufficient=[False], M=[30.0], p_marg=[0.01], M_drop_events=[30.0], M_drop_top_block=[3.9], M_drop_top_window=[30.0])
    B = dict(insufficient=[False], rw_reject=[True], M_adj_C4=[20.0], M_drop_top3=[25.0], M_drop_events=[30.0], M_drop_top_block=[30.0],
             M_drop_top_window=[30.0])
    p1, cd1 = rk.pass_cell(A, B, 0)
    A2 = dict(A, M_drop_top_block=[4.1])
    p2, cd2 = rk.pass_cell(A2, B, 0)
    c["only_eprime_fails_blocks_pass"] = (not p1) and cd1["e2_topblock_AB"] is False and sum(not v for v in cd1.values()) == 1 and p2
    B3 = dict(B, M_drop_top_window=[3.99])
    p3, cd3 = rk.pass_cell(A2, B3, 0)
    c["only_e2prime_fails_blocks_pass"] = (not p3) and cd3["e3_topwindow_AB"] is False and sum(not v for v in cd3.values()) == 1
    # merge: o 0 (BUY_c1.0_T240) M nen 0 + 1 khoi 20 ngay +3000 bps/don vi o CA 2 nua -> M tong > 4 nhung bo khoi -> ~0
    base = os.path.join(outdir, "_eprime")
    shutil.rmtree(base, ignore_errors=True)
    mu = [[-30.0] * 12, [-30.0] * 12]
    mu[0][0] = mu[1][0] = 0.0
    nper = [[40.0] * 12, [40.0] * 12]
    _fake_reduced(base, np.random.default_rng(rng.integers(1 << 62)), mu, nper,
                  block_boost={(0, 0): (300, 20, 3000.0), (1, 0): (400, 20, 3000.0)})
    res, TT = rk.merge(os.path.join(base, "m"), [base], nboot=500, allow_test=True)
    R = res["models"]["OPT"]
    A_ = TT["agg"]
    Am = A_[A_.model == "OPT"]
    nday = (rk.SEAL - rk.DATA_START) // rk.DAY
    dB = (rk.HALF_B - rk.DATA_START) // rk.DAY
    Sb, Nb = rk.day_matrix(Am, dB, nday, "net", 12), rk.day_matrix(Am, dB, nday, "fill", 12)
    keep = np.ones(nday - dB, bool)
    keep[400:420] = False
    m_manual = Sb[keep, 0].sum() / Nb[keep, 0].sum()
    c["merge_cell_not_pass"] = (not R["PASS"][0]) and R["B"]["M"][0] > 50 and R["PASS_conditions"][0]["e2_topblock_AB"] is False
    c["merge_M_drop_block_value"] = abs(R["B"]["M_drop_top_block"][0] - m_manual) < 1e-9 and R["B"]["top_block_start"][0] == str(
        (np.datetime64("2024-01-01") + np.timedelta64(400, "D")))
    rec("eprime_drop_top_block", all(c.values()), **c, M_B=R["B"]["M"][0], M_drop_block_B=R["B"]["M_drop_top_block"][0],
        M_manual=m_manual, conds=R["PASS_conditions"][0])
    shutil.rmtree(base, ignore_errors=True)
    # (e'') R2: cum loi 20 ngay VAT QUA ranh gioi 2 khoi phan hoach (ngay 390-409 cua nua) -> (e') qua, (e'') chan
    c = {}
    S = rng.normal(0, 5, (731, 2))
    N = np.ones((731, 2))
    S[390:410, 0] += 1000.0
    tb, tw = stats3_extra.drop_top_block(S, N), stats3_extra.drop_top_window(S, N)
    keep = np.ones(731, bool); keep[390:410] = False
    c["window_found_390"] = bool(int(tw["start"][0]) == 390 and abs(tw["M_drop"][0] - S[keep, 0].sum() / keep.sum()) < 1e-9)
    c["block_drops_only_half"] = bool(tb["M_drop"][0] > 10 and tw["M_drop"][0] < 4)
    base = os.path.join(outdir, "_eprime2")
    shutil.rmtree(base, ignore_errors=True)
    mu = [[-30.0] * 12, [-30.0] * 12]
    mu[0][0] = mu[1][0] = 0.0
    _fake_reduced(base, np.random.default_rng(rng.integers(1 << 62)), mu, [[40.0] * 12, [40.0] * 12], sd=30.0,
                  block_boost={(0, 0): (290, 20, 3000.0), (1, 0): (390, 20, 3000.0)})
    res, TT = rk.merge(os.path.join(base, "m"), [base], nboot=500, allow_test=True)
    R = res["models"]["PESS"]
    cd = R["PASS_conditions"][0]
    c["merge_e1_pass_e2_block"] = (cd["e2_topblock_AB"] is True and cd["e3_topwindow_AB"] is False and not R["PASS"][0]
                                   and R["B"]["top_window_start"][0] == str(np.datetime64("2024-01-01") + np.timedelta64(390, "D")))
    rec("e2prime_sliding_window_straddle", all(c.values()), **c, M_B=R["B"]["M"][0], M_drop_block_B=R["B"]["M_drop_top_block"][0],
        M_drop_window_B=R["B"]["M_drop_top_window"][0], conds=cd)
    shutil.rmtree(base, ignore_errors=True)


def t_merge_rules(rng, outdir):
    """(9) W-D / W-C / W-A / W-B tren bang gia; thu tu uu tien; o SELL ghi rieng; o INSUFFICIENT chan W-A."""
    import runner3_kaggle as rk
    base = os.path.join(outdir, "_rules")
    shutil.rmtree(base, ignore_errors=True)
    neg = [[-60.0] * 12, [-60.0] * 12]
    many = [[60.0] * 12, [60.0] * 12]
    out = {}

    def run_(name, mu, nper):
        d = os.path.join(base, name)
        _fake_reduced(d, np.random.default_rng(rng.integers(1 << 62)), mu, nper)
        r, _ = rk.merge(os.path.join(d, "m"), [d], nboot=500, allow_test=True)
        out[name] = r
        return r
    # W-A: moi o am ro, du don vi
    r = run_("WA", neg, many)
    c = dict(WA=r["rule_core"] == "W-A" and r["rule"] == "TEST_ONLY:W-A" and r["TEST_ONLY"] is True and r["W_A_condition_OPT_B"])
    # W-B: 1 o INSUFFICIENT (150 don vi nua B) -> W-A bi chan
    m2 = [list(many[0]), list(many[1])]
    m2[1][7] = 0.2
    r = run_("WB_insuff", neg, m2)
    c["WB_insufficient_blocks_WA"] = r["rule_core"] == "W-B" and r["W_A_blocked_by_insufficient_OPT"] == [rk.cells()[7]["name"]]
    # W-B: o gan san (khong PASS, can tren > 4)
    mu3 = [[2.0] * 12, [2.0] * 12]
    r = run_("WB_near", mu3, [[8.0] * 12, [8.0] * 12])
    c["WB_near_floor"] = r["rule_core"] == "W-B" and not any(r["models"]["OPT"]["PASS"])
    # W-C: o 1 PASS duoi OPT, PESS am
    mu4 = {"OPT": [list(neg[0]), list(neg[1])], "PESS": [list(neg[0]), list(neg[1])]}
    mu4["OPT"][0][1] = mu4["OPT"][1][1] = 60.0
    r = run_("WC", mu4, many)
    c["WC"] = r["rule_core"] == "W-C" and r["PASS_cells"]["OPT"] == [rk.cells()[1]["name"]] and r["PASS_cells"]["PESS"] == []
    # W-D: o 2 PASS ca 2 mo hinh; uu tien W-D du co o khac chi PASS OPT
    mu5 = {"OPT": [list(neg[0]), list(neg[1])], "PESS": [list(neg[0]), list(neg[1])]}
    for m in ("OPT", "PESS"):
        mu5[m][0][2] = mu5[m][1][2] = 60.0
    mu5["OPT"][0][4] = mu5["OPT"][1][4] = 60.0
    r = run_("WD", mu5, many)
    c["WD_priority"] = (r["rule_core"] == "W-D" and r["PASS_cells"]["PESS"] == [rk.cells()[2]["name"]]
                        and set(r["PASS_cells"]["OPT"]) == {rk.cells()[2]["name"], rk.cells()[4]["name"]})
    # O SELL PASS (chi duoi PESS + OPT) -> W-D + ghi rieng 'SELL (he thong hien long-only)'
    mu6 = {"OPT": [list(neg[0]), list(neg[1])], "PESS": [list(neg[0]), list(neg[1])]}
    for m in ("OPT", "PESS"):
        mu6[m][0][9] = mu6[m][1][9] = 60.0
    r = run_("WD_sell", mu6, many)
    nm = rk.cells()[9]["name"]
    c["WD_sell_noted"] = (r["rule_core"] == "W-D" and nm.startswith("SELL") and
                          r["SELL_PASS_note"]["PESS"] == ["SELL (he thong hien long-only): %s" % nm])
    # o lon nhung INSUFFICIENT khong bao gio PASS
    mu7 = [list(neg[0]), list(neg[1])]
    mu7[0][5] = mu7[1][5] = 500.0
    m7 = [list(many[0]), list(many[1])]
    m7[1][5] = 0.2
    r = run_("insuff_never_pass", mu7, m7)
    c["insufficient_never_pass"] = not r["models"]["OPT"]["PASS"][5] and r["rule_core"] == "W-B"
    rec("merge_rules_WD_WC_WA_WB", all(c.values()), **c)
    shutil.rmtree(base, ignore_errors=True)


def t_merge_guards(rng, outdir):
    """(10) merge: du 5 shard / trung / sha / cond / mkt_sym / prereg_constants / s3_const / inputs (H2) / TEST_ONLY."""
    import runner3_kaggle as rk
    base = os.path.join(outdir, "_mguard")
    shutil.rmtree(base, ignore_errors=True)
    exp_sha = {f: rk.sha256_file(os.path.join(HERE, f)) for f in rk.SHA_FILES}
    shp = os.path.join(base, "EXPECTED_SHA.txt")
    os.makedirs(base, exist_ok=True)
    with open(shp, "w") as fh:
        for f in rk.SHA_FILES:
            fh.write("%s  %s\n" % (exp_sha[f], f))
    man0 = dict(prereg_constants=True, alpha_fwer=rk.ALPHA_FWER, alpha_upper=rk.ALPHA_UPPER, min_units=rk.MIN_UNITS,
                cond=json.loads(json.dumps(rk.COND_PREREG)), mkt_sym=rk.MARKET_SYM, code=dict(exp_sha),
                s3_const=json.loads(json.dumps(rk.S3_CONST)), inputs={"lifecycle.parquet": "ab", "funding-2021.parquet": "cd"})
    neg = [[-60.0] * 12, [-60.0] * 12]
    per = [[12.0] * 12, [12.0] * 12]
    dirs = []
    for i in range(5):
        d = os.path.join(base, "d%d" % i)
        _fake_reduced(d, np.random.default_rng(rng.integers(1 << 62)), neg, per, manifest=dict(man0, shard="%d/5" % i))
        dirs.append(d)

    def tries(dl, es=shp, **kw):
        try:
            r, _ = rk.merge(os.path.join(base, "m"), dl, expected_sha=es, **kw)
            return True, r
        except RuntimeError as e:
            return False, str(e)[:160]
    ok_v, r_v = tries(dirs)
    cases = dict(valid=ok_v and r_v["TEST_ONLY"] is False and r_v["rule"] == r_v["rule_core"] == "W-A"
                 and r_v["skip_px_by_cell"] == {rk.cells()[0]["name"]: 15})
    cases["missing_shard"] = not tries(dirs[:4])[0]
    cases["duplicate_dir"] = not tries(dirs[:4] + [dirs[0]])[0]
    dup = os.path.join(base, "dup")
    shutil.copytree(dirs[1], dup)
    cases["duplicate_index"] = not tries(dirs[:4] + [dup])[0]
    cases["no_expected_sha"] = not tries(dirs, es=None)[0]
    bad = dict(exp_sha)
    bad["stats3_extra.py"] = "0" * 64
    cases["sha_mismatch"] = not tries(dirs, es=bad)[0]
    s3b = json.loads(json.dumps(rk.S3_CONST))
    s3b["EXIT_FRAC"] = 0.6
    for key, val in (("cond", {"B": dict(ratio=1.0), "MKT": dict(z=1.0, win=60)}), ("mkt_sym", "AAAUSDT"),
                     ("prereg_constants", False), ("s3_const", s3b), ("inputs", {"lifecycle.parquet": "zz"})):
        mf = os.path.join(dirs[2], "manifest.json")
        m0 = json.load(open(mf))
        json.dump(dict(m0, **{key: val}), open(mf, "w"))
        cases["bad_" + key] = not tries(dirs)[0]
        json.dump(m0, open(mf, "w"))
    vf = os.path.join(dirs[3], "validate.json")
    v0 = json.load(open(vf))
    json.dump(dict(v0, all_pass=False), open(vf, "w"))
    cases["validate_all_pass_false"] = not tries(dirs)[0]
    json.dump(v0, open(vf, "w"))
    # R2 (MASTER P2): (c,T,ben) = (5, SELL) khong phu o 1 shard -> van chay; khong phu o MOI shard -> abort
    vs = {d: json.load(open(os.path.join(d, "validate.json"))) for d in dirs}
    def drop_cs(d):
        v_ = json.loads(json.dumps(vs[d]))
        v_["V5"]["covered_ctside"] = [k for k in v_["V5"]["covered_ctside"] if k != [5, -1]]
        json.dump(v_, open(os.path.join(d, "validate.json"), "w"))
    drop_cs(dirs[0])
    cases["ctside_uncovered_in_one_shard_ok"] = tries(dirs)[0]
    for d in dirs:
        drop_cs(d)
    okm, msg = tries(dirs)
    cases["ctside_uncovered_all_shards_abort"] = (not okm) and "khong duoc shard nao phu" in msg
    for d in dirs:
        json.dump(vs[d], open(os.path.join(d, "validate.json"), "w"))
    try:
        rk.merge(os.path.join(base, "m"), dirs, expected_sha=shp, nboot=500)
        cases["nboot_not_prereg_refused"] = False
    except RuntimeError:
        cases["nboot_not_prereg_refused"] = True
    # R3-3 (A1 F3): merge tu kiem sha cac file code cua CHINH no - ban sao sua 1 dong -> abort; ban sao nguyen -> chay (B 2000)
    import subprocess
    for lab, mod in (("copy_ok", False), ("copy_modified", True)):
        cd_ = os.path.join(base, "code_" + lab)
        os.makedirs(cd_, exist_ok=True)
        for f in rk.SHA_FILES:
            shutil.copy(os.path.join(HERE, f), cd_)
        if mod:
            with open(os.path.join(cd_, "runner3_kaggle.py"), "a") as fh:
                fh.write("# sua sau khi thay so\n")
        env = {k: v for k, v in os.environ.items() if not (k.startswith("GRIDV3_") or k.startswith("GRIDV2_"))}
        pr = subprocess.run([sys.executable, os.path.join(cd_, "runner3_kaggle.py"), "merge", os.path.join(base, "m_" + lab),
                             "--expected-sha", shp] + dirs, capture_output=True, text=True, env=env, timeout=900)
        cases["R3_self_sha_" + lab] = (pr.returncode == 0) if not mod else (pr.returncode != 0 and "CHINH merge" in pr.stderr)
    ok_t, r_t = tries(dirs[:2], es=None, allow_test=True, nboot=500)
    cases["allow_test_marked"] = ok_t and r_t["TEST_ONLY"] is True and r_t["rule"].startswith("TEST_ONLY:")
    rf = json.load(open(os.path.join(base, "m", "result.json")))
    cases["result_json_first_key_TEST_ONLY"] = list(rf.keys())[0] == "TEST_ONLY" and rf["TEST_ONLY"] is True
    rec("merge_guards_shards_sha_inputs_TEST_ONLY", all(cases.values()), **cases)
    shutil.rmtree(base, ignore_errors=True)


# ------------------------------------------------------------------ (10) rao chan: env, allowlist, V0b, V2, V6, s_hat, V5
def t_guards(rng, outdir):
    import runner3_kaggle as rk
    import pandas as pd
    res = []
    for k in list(rk.FORBIDDEN_ENV) + ["GRIDV3_ALPHA", "GRIDV3_W", "GRIDV3_EXIT_FRAC", "GRIDV2_FOO"]:
        os.environ[k] = "x"
        for fn in (rk.check_env, lambda: rk.merge(os.path.join(outdir, "_nomerge"), [], allow_test=True), rk.run):
            try:
                fn()
                res.append(False)
            except RuntimeError:
                res.append(True)
        os.environ.pop(k)
    for k in rk.ENV_OPS:
        os.environ[k] = os.environ.get(k, "0/1" if k.endswith("SHARD") else "x")
    try:
        rk.check_env()
        ops_ok = True
    except RuntimeError:
        ops_ok = False
    for k in rk.ENV_OPS:
        os.environ.pop(k, None)
    rec("guard_forbidden_env_aborts", all(res) and ops_ok, n=len(res), ops_allowed=ops_ok)
    root = os.path.join(outdir, "_allow")

    def build(extra=(), drop=()):
        shutil.rmtree(root, ignore_errors=True)
        files = ["datasets/u/vz-kline1m-%d/kline1m-%d-0%d.parquet" % (y, y, 5 if y == 2021 else 1) for y in range(2021, 2026)]
        files += ["datasets/u/gridp-t1-funding/funding-2021.parquet", "datasets/u/gridp-lifecycle/lifecycle.parquet",
                  "datasets/u/gridp-t1-funding/README.txt"]
        for f in [f for f in files if not any(d in f for d in drop)] + list(extra):
            os.makedirs(os.path.dirname(os.path.join(root, f)), exist_ok=True)
            open(os.path.join(root, f), "w").close()

    def ok_run():
        try:
            rk.find_inputs(root)
            return True
        except RuntimeError:
            return False
    cases = {}
    build(); cases["valid"] = ok_run()
    build(extra=["datasets/u/vz-funding/funding-2021.parquet"]); cases["foreign_slug"] = not ok_run()
    build(extra=["datasets/u/gridp-t1-funding/funding-2026.parquet"]); cases["file_2026"] = not ok_run()
    build(extra=["datasets/u/vz-kline1m-2025/kline1m-2026-01.parquet"]); cases["kline_2026"] = not ok_run()
    build(extra=["datasets/u/vz-kline1m-2022/kline1m-2021-07.parquet"]); cases["year_mismatch"] = not ok_run()
    build(drop=["gridp-lifecycle"]); cases["missing_slug"] = not ok_run()
    build(extra=["datasets/u/gridp-lifecycle/sub/lifecycle.parquet"]); cases["two_lifecycle"] = not ok_run()
    build(extra=["datasets/u/gridp-t1-funding/other.parquet"]); cases["stray_parquet"] = not ok_run()
    build(extra=["notes.txt"]); cases["file_outside_slug"] = not ok_run()
    build(extra=["datasets/u/vz-funding/gridp-t1-funding/funding-2023.parquet"]); cases["R3_nested_foreign_slug"] = not ok_run()
    build(extra=["datasets/u/gridp-t1-funding/sub/funding-2023.parquet"]); cases["R3_subdir_inside_slug"] = not ok_run()
    build(extra=["other/gridp-t1-funding/funding-2023.parquet"]); cases["R3_slug_at_other_level"] = not ok_run()
    shutil.rmtree(root, ignore_errors=True)
    rec("guard_dataset_allowlist", all(cases.values()), **cases)
    meta = {(2021, m): 100 + m for m in range(1, 13)}
    meta.update({(2022, m): 1000 + m for m in range(1, 13)})
    opened = [k for k in meta if not rk.v0_rule_skipped(*k)]
    rows = {2021: sum(meta[k] for k in opened if k[0] == 2021), 2022: sum(meta[(2022, m)] for m in range(1, 13))}
    reg = {2021: sum(meta[(2021, m)] for m in range(1, 13)), 2022: rows[2022]}
    c = {}
    a, b, d = rk.v0_eval(meta, opened, rows, reg, rk.V0_SKIP_EXPECTED_REAL)
    c["valid"] = a and b and [f["file"] for f in d["files_skipped"]] == ["kline1m-2021-0%d.parquet" % m for m in (1, 2, 3)]
    a, b, _ = rk.v0_eval(meta, opened, {**rows, 2021: rows[2021] - 1}, reg)
    c["read_minus_1_fail"] = a and not b
    a, b, _ = rk.v0_eval(meta, opened, rows, {**reg, 2021: reg[2021] + 1})
    c["registry_plus_1_fail"] = not a and not b
    a, b, _ = rk.v0_eval(meta, [k for k in opened if k != (2021, 4)], rows, reg)
    c["extra_skip_fail"] = not b
    a, b, _ = rk.v0_eval(meta, opened, rows, reg, [[2021, 1], [2021, 2]])
    c["expect_mismatch_fail"] = not b
    rec("guard_V0a_V0b_pure", all(c.values()), **c)
    a = rk.v2_eval({2022: [10, 10000], 2023: [0, 5000]})
    b = rk.v2_eval({2022: [11, 10000], 2023: [0, 5000]})
    rec("guard_V2_threshold_0p1pct", a[0] and not b[0], ok_10_per_10k=a[0], ok_11_per_10k=b[0])

    def fr(rate, ih, inferred=False):
        f = pd.DataFrame({"rate": rate, "interval_h": ih})
        f.attrs["inferred"] = inferred
        return f
    r1 = rng.normal(1e-4, 5e-5, 1000)
    v_ok = rk.v6_eval({2022: fr(r1, np.full(1000, 8.0))})[0]
    v_pct = rk.v6_eval({2022: fr(r1 * 100, np.full(1000, 8.0))})[0]
    v_ih = rk.v6_eval({2022: fr(r1, np.r_[np.full(999, 8.0), [3.0]])})[0]
    rec("guard_V6_funding_units", v_ok and not v_pct and not v_ih, normal=v_ok, percent_units=v_pct, bad_interval=v_ih)
    sp = np.full(20, np.nan)
    sp[1] = 0.001
    sp[12] = 0.003
    sh = rk.shat_exante(sp)
    exp = np.full(20, np.nan)
    exp[2:9] = 0.001
    exp[13:20] = 0.003
    same = np.all((np.isnan(sh) & np.isnan(exp)) | (np.abs(sh - exp) < 1e-15))
    filled = rk.shat_fill(sh[[0, 5, 10, 10, 10]], np.array([1, 3, 1, 2, 3]))
    rec("guard_shat_ffill7_then_2x_floor", bool(same and np.allclose(filled, [4e-4, 0.001, 4e-4, 10e-4, 20e-4])))


def t_v5_pure():
    """V5 (sua J1): 12 vi tri (6 (c,T) x 2 ben, mo hinh xen ke) -> moi (c,T) co CA 2 mo hinh, 4 to hop mo hinh x ben; tat dinh."""
    import runner3_kaggle as rk

    def fake_res(avail, seed):
        units = {}
        for (ci, model), (nb, ns) in avail.items():
            side = np.r_[np.ones(nb + 5, np.int8), -np.ones(ns + 5, np.int8)]
            ok = np.r_[np.ones(nb, bool), np.zeros(5, bool), np.ones(ns, bool), np.zeros(5, bool)]
            units[(ci, model)] = dict(ok=ok, side=side)
        return dict(units=units)
    full = {(ci, m): (3, 3) for ci in range(6) for m in ("OPT", "PESS")}
    resA = fake_res({k: v for k, v in full.items() if k[0] != 5}, 1)
    resA["units"][(4, "PESS")] = dict(ok=np.array([True, False]), side=np.array([-1, 1], np.int8))   # thieu (4, BUY, PESS)? (4,1)=OPT
    resA["units"][(4, "OPT")] = dict(ok=np.array([True, False]), side=np.array([-1, 1], np.int8))    # (4, BUY, OPT) khong co
    c = {}
    need = set(rk.V5_SLOTS)
    pa = rk.v5_select(resA, need, np.random.default_rng(7))
    pa2 = rk.v5_select(resA, need, np.random.default_rng(7))
    c["deterministic"] = pa == pa2
    got = {s_ for s_, _, _ in pa}
    c["symA_missing_ci5_and_4buy"] = need - got == {(5, 1, "PESS"), (5, -1, "OPT"), (4, 1, "OPT")}
    c["picked_units_match_slot"] = all(bool(resA["units"][k]["ok"][i]) and int(resA["units"][k]["side"][i]) == s_[1]
                                       and k == (s_[0], s_[2]) for s_, k, i in pa)
    pb = rk.v5_select(fake_res(full, 2), need - got, np.random.default_rng(8))
    c["next_symbol_fills_rest"] = {s_ for s_, _, _ in pb} == need - got
    slots = rk.V5_SLOTS
    c["slot_design"] = (len(slots) == 12 and {(m, sd) for _, sd, m in slots} == {("OPT", 1), ("OPT", -1), ("PESS", 1), ("PESS", -1)}
                        and all({m for ci_, _, m in slots if ci_ == ci} == {"OPT", "PESS"} for ci in range(6)))

    def chk(slot, ok=True):
        ci, sd, m = slot
        return dict(sym="X", t0=1, ct=ci, c=rk.CT_ALL[ci][0], T=rk.CT_ALL[ci][1], side=sd, model=m, ok=ok)
    good = [chk(s_) for s_ in slots]
    c["eval_good"] = rk.v5_eval(good)["ok"] and rk.v5_eval(good)["uncovered"] == []
    # R2 (MASTER P2): du phong + uncovered <= 2
    need = {slots[-1], slots[-2], slots[-3]}                                  # (5,-1,OPT), (5,1,PESS), (4,-1,PESS)
    fbk = {slots[-1]: dict(chk((slots[-1][0], slots[-1][1], "PESS")), sym="Y")}
    allv, fbl, unc = rk.v5_finalize(good[:-3], need, fbk)
    ev = rk.v5_eval(allv, fbl, unc)
    c["fallback_recorded"] = (len(fbl) == 1 and fbl[0]["slot"] == list(slots[-1]) and fbl[0]["used_model"] == "PESS"
                              and allv[-1]["fallback"] is True)
    c["uncovered_2_pass"] = ev["ok"] and sorted(map(tuple, ev["uncovered"])) == sorted([(5, 1), (4, -1)]) and ev["v5_fallback"] == fbl
    need3 = {slots[-1], slots[-2], slots[-3], slots[-4]}                      # 4 (c,T,ben) khong phu -> FAIL
    allv3, fbl3, unc3 = rk.v5_finalize(good[:-4], need3, {})
    ev3 = rk.v5_eval(allv3, fbl3, unc3)
    c["uncovered_4_fail"] = (not ev3["ok"]) and len(ev3["uncovered"]) == 4 and len(unc3) == 4
    c["eval_mismatch_fail"] = not rk.v5_eval(good[:-1] + [chk(slots[-1], ok=False)])["ok"]
    c["fallback_mismatch_fail"] = not rk.v5_eval(*rk.v5_finalize(good[:-1], {slots[-1]}, {slots[-1]: dict(chk(slots[-1]), ok=False)}))["ok"]
    ev_x = rk.v5_eval(good, (), (), [dict(chk(slots[0]), ok=False, model="PESS")])
    c["R3_unused_fallback_mismatch_fail"] = (not ev_x["ok"]) and ev_x["n_fallback_unused_bad"] == 1
    c["R3_unused_fallback_ok_pass"] = rk.v5_eval(good, (), (), [dict(chk(slots[0]), model="PESS")])["ok"]
    rec("V5_select_eval_12_slots_4_combos", all(c.values()), **c)


# ------------------------------------------------------------------ mini universe: V4, co "toan thi truong", loc gia <= 0, tier
def mini_universe(rng, nday=150, tpm=2):
    import runner3_kaggle as rk
    nmin = nday * 1440
    specs = [("BTCUSDT", 0.03, 30000.0), ("AAAUSDT", 0.04, 50.0), ("BBBUSDT", 0.04, 2.0), ("ZZZUSDT", 0.45, 10000.0)]
    arrs, funds, firsts = {}, {}, {}
    common = None
    crash_min = (100 * 24 + 5) * 60 + 17
    idio_min = (120 * 24 + 9) * 60 + 33
    for s, sg, p0 in specs:
        px, inc = synth3.path_with_events(rng, nmin, tpm, sg, p0, 0.0, "wick", common_inc=common,
                                          beta=(None if s == "BTCUSDT" else 1.0))
        if s == "BTCUSDT":
            common = inc
        lp = np.log(px)
        if s in ("BTCUSDT", "AAAUSDT"):
            A = 0.05 if s == "BTCUSDT" else 0.16
            for k in range(6):
                lp[(crash_min + k) * tpm:(crash_min + k + 1) * tpm] -= A * (1 - k / 6.0)
        if s == "BBBUSDT":
            for k in range(6):
                lp[(idio_min + k) * tpm:(idio_min + k + 1) * tpm] -= 0.16 * (1 - k / 6.0)
        q = 10.0 ** (math.floor(math.log10(p0)) - 8)
        p = (np.round(np.exp(lp) / q) * q).reshape(nmin, tpm)
        O, H, L, C = p[:, 0], p.max(1), p.min(1), p[:, -1]
        QV = np.full(nmin, 1e6)
        arrs[s] = (O, H, L, C, QV, np.ones(nmin, bool))
        ft = rk.DATA_START + np.arange(0, nday * 24, 8) * 3600000 + 5
        funds[s] = (ft.astype(np.int64), np.full(ft.size, 1e-4), np.full(ft.size, 8.0))
        firsts[s] = rk.DATA_START - 400 * rk.DAY
    return arrs, funds, firsts, crash_min, idio_min


def t_universe_checks(rng):
    import runner3_kaggle as rk
    nday = 150
    arrs, funds, firsts, crash_min, idio_min = mini_universe(rng, nday)
    mkt = rk.market_context(arrs["BTCUSDT"], -1, nday)
    CP = rk.cond_params()
    out = {}
    flags = {}
    for s in ("AAAUSDT", "BBBUSDT", "ZZZUSDT"):
        tier = np.full(nday, 1, np.int8)
        ctx = dict(nday=nday, tier=tier, fund=funds[s], dl=-1, mkt=mkt, mkt_sym="BTCUSDT", CP=CP, er_p1=None, sig_p1=None)
        res = rk.process_symbol(s, arrs[s], ctx, collect_units=True)
        flags[s] = res
    # co 'toan thi truong': doi chieu tinh tay cho MOI don vi da khop
    nbad = ncheck = 0
    found = dict(crash=None, idio=None)
    for s in ("AAAUSDT", "BBBUSDT"):
        for (ci, model), u in flags[s]["units"].items():
            R = u["R"]
            for i in np.nonzero(u["ok"])[0]:
                f = int(R["f"][i])
                Bf = mkt["C"][mkt["lv"][f]]
                B60 = mkt["C"][mkt["lv"][f - 60]]
                r = math.log(Bf / B60)
                thr = mkt["sig"][int(u["D"][i])] / math.sqrt(24.0)
                exp = "market" if ((r <= -thr) if u["side"][i] == 1 else (r >= thr)) else "idio"
                ncheck += 1
                nbad += int(exp != u["mflag"][i])
                if s == "AAAUSDT" and f == crash_min and u["side"][i] == 1:
                    found["crash"] = u["mflag"][i]
                if s == "BBBUSDT" and f == idio_min and u["side"][i] == 1:
                    found["idio"] = (u["mflag"][i], exp)
    out["mkt_flag_hand_equal"] = nbad == 0 and ncheck >= 10
    out["crash_unit_market"] = found["crash"] == "market"
    out["idio_unit_matches_hand"] = found["idio"] is not None and found["idio"][0] == found["idio"][1]
    sk = flags["ZZZUSDT"]["skip_px"]
    out["skip_px_buy_c2.5_only"] = sk.get(4, 0) + sk.get(5, 0) > 0 and all(k < 6 for k in sk) and sk.get(0, 0) == 0
    # diag co du chieu S3-8
    dims = set(flags["AAAUSDT"]["diag"].dim.unique())
    out["diag_dims"] = dims == {"tier", "year", "hour", "condB", "mkt", "qvratio", "wick1m"}
    # V4 tren symbol nay (rac sau tc) + rac truoc tc -> FAIL
    s = "AAAUSDT"
    ctx = dict(nday=nday, tier=np.full(nday, 1, np.int8), fund=funds[s], dl=-1, mkt=mkt, mkt_sym="BTCUSDT", CP=CP,
               er_p1=None, sig_p1=None)
    okp, lo, hi, why = rk.v4_pick(arrs[s][5])
    r_ok = rk.v4_check(s, arrs[s], ctx, np.random.default_rng(11), tc_range=(lo, hi))
    r_junk = rk.v4_check(s, arrs[s], ctx, np.random.default_rng(11), tc_range=(lo, hi), junk_lead_min=3 * 1440)
    out["V4_pass"] = okp and r_ok["ok"] and r_ok["n_checked"] > 100 and sum(r_ok["feat_diff"].values()) == 0
    # R3-4 (A1 F5): sigma_1d RO RI (dung ca return ngay D) -> V4 phai FAIL qua so sanh mang feature ngay
    orig = rk.klite3.sigma_exante

    def leaky(close, nwin=30, nmin=20):
        return orig(np.r_[close[1:], np.nan], nwin, nmin)
    rk.klite3.sigma_exante = leaky
    try:
        r_leak = rk.v4_check(s, arrs[s], ctx, np.random.default_rng(11), tc_range=(lo, hi))
    finally:
        rk.klite3.sigma_exante = orig
    out["R3_V4_leaky_sigma_fail"] = (not r_leak["ok"]) and r_leak["feat_diff"].get("sig", 0) > 0
    out["V4_junk_before_tc_fail"] = (not r_junk["ok"]) and r_junk["n_diff"] > 0
    rec("universe_mktflag_skip_diag_V4", all(out.values()), **out, n_mkt_checked=ncheck, skip_ZZZ=sk,
        V4=(r_ok["n_checked"], r_ok["n_diff"]), V4_junk=(r_junk["n_checked"], r_junk["n_diff"]))


def t_tiers():
    import runner3_kaggle as rk
    nday = (rk.SEAL - rk.DATA_START) // rk.DAY
    syms = ["S%02dUSDT" % i for i in range(75)] + ["USDCUSDT", "LATEUSDT", "GONEUSDT"]
    qv = {s: np.full(nday, 1000.0 - i) for i, s in enumerate(syms)}
    qv["USDCUSDT"][:] = 1e9
    qv["LATEUSDT"][:] = 1e8
    qv["GONEUSDT"][:] = 1e7
    act = {s: np.ones(nday, np.int64) for s in syms}
    life = {s: dict(first=rk.DATA_START - 400 * rk.DAY, last=None, ascii=True) for s in syms}
    life["LATEUSDT"]["first"] = rk.ms("2023-01-01")
    life["GONEUSDT"]["last"] = rk.ms("2022-06-01")
    T = rk.build_tiers(qv, act, life, nday)
    D = (rk.ms("2022-03-10") - rk.DATA_START) // rk.DAY
    D2 = (rk.ms("2023-03-10") - rk.DATA_START) // rk.DAY
    ok = ("USDCUSDT" not in T and T["GONEUSDT"][D] == 1 and T["GONEUSDT"][D2] == 0 and T["LATEUSDT"][D] == 0 and
          T["LATEUSDT"][D2] == 1 and T["S00USDT"][D] == 1 and T["S08USDT"][D] == 1 and T["S09USDT"][D] == 2 and
          T["S58USDT"][D] == 2 and T["S59USDT"][D] == 3)
    rec("tiers_point_in_time", ok, n_sym=len(T))


# ------------------------------------------------------------------ (11) runner3 + merge tren lake tong hop co / khong co rau gia
def _add_premonths(root):
    import pyarrow as pa
    import pyarrow.parquet as pq
    out = {}
    d = os.path.join(root, "datasets/x/vz-kline1m-2021")
    for mo, n in ((1, 120), (2, 75), (3, 333)):
        ts = int(np.datetime64("2021-%02d-01T00:00" % mo, "ms").astype(np.int64)) + 60000 * np.arange(n, dtype=np.int64)
        px = np.full(n, 100.0)
        tb = pa.table({"ts": ts, "sym": pa.array(["AAAUSDT"] * n).dictionary_encode(), "open": px, "high": px, "low": px,
                       "close": px, "volume": np.ones(n), "quote_volume": np.ones(n), "active": np.ones(n, bool)})
        pq.write_table(tb, os.path.join(d, "kline1m-2021-%02d.parquet" % mo), row_group_size=n + 1)
        out[(2021, mo)] = n
    return out


def t_runner_lake(rng, outdir):
    import runner3_kaggle as rk
    summ = {}
    for variant in ("wick", "null_mid"):
        root = os.path.join(outdir, "_lake_%s" % variant)
        ro = os.path.join(outdir, "_run_%s" % variant)
        for p in (root, ro):
            shutil.rmtree(p, ignore_errors=True)
        meta = synth3.write_lake3(root, seed=int(rng.integers(1 << 31)), tpm=4, variant=variant, lam_day=0.35)
        extra = _add_premonths(root)
        meta["rows"][2021] = meta["rows"][2021] + sum(extra.values())
        os.makedirs(ro, exist_ok=True)
        os.environ.update(GRIDV3_INPUT=root, GRIDV3_OUT=ro, GRIDV3_SHARD="0/1", GRIDV3_KEEP_SYM="1")
        tov = dict(registry=meta["rows"])
        t = time.time()
        v, man = rk.run(test_overrides=tov)
        secs = time.time() - t
        try:
            rk.merge(os.path.join(ro, "merged_x"), [ro], nboot=500)
            refused = False
        except RuntimeError:
            refused = True
        res, TT = rk.merge(os.path.join(ro, "merged"), [ro], nboot=500, allow_test=True)
        O, P = res["models"]["OPT"], res["models"]["PESS"]
        summ[variant] = dict(rule=res["rule"], seconds=secs, all_pass=v["all_pass"], prereg_constants=man["prereg_constants"],
                             V=dict(V0=v["V0"]["ok_V0a"] and v["V0"]["ok_V0b"], V1=v["V1"]["ok"], V2=v["V2"]["ok"], V3=v["V3"]["ok"],
                                    V4=[(c["n_checked"], c["n_diff"]) for c in v["V4"]["checks"]], V5=v["V5"]["ok"],
                                    V5_combos=v["V5"]["combos"], V5_n=len(v["V5"]["checks"]), V6=v["V6"]["ok"]),
                             skip_px=v["V3"]["units_skip_px"], refused_without_allow_test=refused,
                             M_B_OPT=[round(x, 1) for x in O["B"]["M"]], M_B_PESS=[round(x, 1) for x in P["B"]["M"]],
                             M_A_OPT=[round(x, 1) for x in O["A"]["M"]], M_A_PESS=[round(x, 1) for x in P["A"]["M"]],
                             n_B_OPT=[int(x) for x in O["B"]["n_units"]],
                             n_B_PESS=[int(x) for x in P["B"]["n_units"]], fill_B_PESS=[round(x, 4) for x in P["B"]["fill_rate"]],
                             PASS_OPT=res["PASS_cells"]["OPT"], PASS_PESS=res["PASS_cells"]["PESS"],
                             M_drop_block_B_PESS=[round(x, 1) if x == x else None for x in P["B"]["M_drop_top_block"]])
        if variant == "wick":
            v3a = {k: v["V3"][k] for k in ("long_gaps", "units_excl_gap", "units_excl_noend", "feat_mismatch_days", "sym_month_missing",
                                            "units_skip_px")}
            vb, _ = rk.run(test_overrides=dict(tov, v4_syms=0))
            v3b = {k: vb["V3"][k] for k in v3a}
            rec("runner3_checkpoint_keeps_V3_counters", v3a == v3b and vb["V3"]["n_sym_from_checkpoint"] > 0,
                n_from_ckpt=vb["V3"]["n_sym_from_checkpoint"])
            d = os.path.join(ro, "merged", "diag.json")
            dg = json.load(open(d))
            rec("runner3_diag_S3_8_tables", {x["dim"] for x in dg["diag"]} == {"tier", "year", "hour", "condB", "mkt", "qvratio", "wick1m"}
                and len(dg["monthly"]) > 0 and all(k in P["B"] for k in ("q01_unit", "q05_unit", "q50_unit", "q95_unit",
                                                                        "worst_unit_net", "M_drop_oct2025", "M_stress_slip_x5",
                                                                        "p_lim_exit", "hold_mean_min", "M_neth")),
                n_diag=len(dg["diag"]), n_monthly=len(dg["monthly"]))
        for k in ("GRIDV3_KEEP_SYM",):
            os.environ.pop(k, None)
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(ro, ignore_errors=True)
    w, n = summ["wick"], summ["null_mid"]
    buy = list(range(6))
    rec("runner3_V0_V6_on_lakes", w["all_pass"] and n["all_pass"] and not w["prereg_constants"] and w["V"]["V5_n"] == 12
        and len(w["V"]["V5_combos"]) == 4 and w["refused_without_allow_test"] and n["refused_without_allow_test"],
        wick=w["V"], null=n["V"], seconds=[w["seconds"], n["seconds"]])
    rec("runner3_wick_lake_BUY_large_positive_both_models",
        all(w["M_B_PESS"][c] > 50 and w["M_B_OPT"][c] > 50 for c in buy) and w["rule"] == "TEST_ONLY:W-D"
        and all(rk.cells()[c]["name"] in w["PASS_PESS"] for c in buy), **{k: w[k] for k in ("rule", "M_B_OPT", "M_B_PESS", "n_B_PESS",
                                                                                          "fill_B_PESS", "PASS_PESS",
                                                                                          "M_drop_block_B_PESS")})
    rec("runner3_null_mid_minute_lake_no_pass_WB", n["PASS_OPT"] == [] and n["PASS_PESS"] == [] and n["rule"] == "TEST_ONLY:W-B",
        **{k: n[k] for k in ("rule", "M_B_OPT", "M_B_PESS", "M_A_OPT", "M_A_PESS", "n_B_OPT", "n_B_PESS")})
    json.dump(summ, open(os.path.join(outdir, "runner_lake_summary.json"), "w"), indent=1, default=float)


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.path.join(HERE, "out_synth")
    os.makedirs(outdir, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(outdir, "test.log"), "w")])
    np.seterr(all="ignore")
    import warnings
    warnings.filterwarnings("ignore")
    rng = np.random.default_rng(SEED)
    t = time.time()
    t_accounting(rng)
    t_analytic(rng)
    t_indep_mc(rng)
    t_edges()
    t_ref_compare(rng, outdir)
    t_lookahead(rng)
    t_stats(rng)
    t_eprime(rng, outdir)
    t_merge_rules(rng, outdir)
    t_merge_guards(rng, outdir)
    t_guards(rng, outdir)
    t_v5_pure()
    t_universe_checks(rng)
    t_tiers()
    if "--no-runner" not in sys.argv:
        t_runner_lake(rng, outdir)
    allok = all(r["ok"] for r in RES)
    json.dump(dict(all_pass=allok, n=len(RES), n_fail=sum(not r["ok"] for r in RES), seconds=round(time.time() - t, 1), seed=SEED,
                   tests=RES), open(os.path.join(outdir, "test_results.json"), "w"), indent=1, default=float)
    log.info("ALL_PASS=%s (%d test, %d fail) %.0fs", allok, len(RES), sum(not r["ok"] for r in RES), time.time() - t)


if __name__ == "__main__":
    main()
