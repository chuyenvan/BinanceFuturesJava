"""test_klite.py - toan bo kiem chung TONG HOP cua Giai doan 1 (E2a, E2b, E2c, test bien, doi chieu 2 cai dat doc lap,
khong nhin tuong lai, thong ke (RW studentized, INSUFFICIENT, merge/luat), tier, allowlist, V2/V6, s_hat, va runner end-to-end
tren lake GBM gia).
Chay: python3 test_klite.py [OUTDIR] [--no-runner]. Ghi OUTDIR/test_results.json + OUTDIR/hand_units.txt.
KHONG dung du lieu that.
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
import klite  # noqa: E402
import kref   # noqa: E402
import synth  # noqa: E402
import stats  # noqa: E402

log = logging.getLogger("test")
RES = []
SEED = 2026112050


def rec(name, ok, **kw):
    RES.append(dict(name=name, ok=bool(ok), **kw))
    log.info("%-38s %s %s", name, "PASS" if ok else "FAIL", json.dumps(kw, default=float)[:300])


def grid_from_paths(px, tpm, valid=None, delist=-1):
    O, H, L, C = synth.bars_from_trades(px, tpm)
    O, H, L, C = synth.concat_grid(O, H, L, C)
    v = np.ones(C.size, bool) if valid is None else valid
    return klite.prepare_grid(O, H, L, C, v, delist), (O, H, L, C, v)


def lists(G):
    return [[None if not np.isfinite(x) else float(x) for x in G[k]] for k in ("O", "H", "L", "C")]


def alt_side(n):
    return np.where(np.arange(n) % 2 == 0, 1, -1).astype(np.int8)


def mse(x):
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    return float(x.mean()), float(x.std(ddof=1) / math.sqrt(x.size)), int(x.size)


# ------------------------------------------------------------------ E2a: dong nhat ke toan
def t_e2a(rng):
    px = synth.lattice_paths(rng, 1, 60000 * 4, 20000, bounce_h=2) * 0.01
    valid = np.ones(60000, bool)
    valid[10000:10020] = False
    valid[20000:20200] = False
    G, _ = grid_from_paths(px, 4, valid, delist=55000)
    t0 = np.arange(61, 54000, 7)
    t0 = t0[G["valid"][t0 - 1]]
    fs = np.arange(3, 60000, 240)
    fr = rng.normal(1e-4, 3e-4, fs.size)
    worst = 0.0
    worst_fee = 0.0
    n = 0
    for model in ("OPT", "PESS"):
        for d in (0.0005, 0.002):
            for withf in (False, True):
                R = klite.run_units(G, t0, d, 300, 300, 0.01, 7e-4, model, alt_side(t0.size), fs if withf else None, fr if withf else None)
                f = R["filled"]
                n += int(f.sum())
                if not withf:
                    worst = max(worst, float(np.max(np.abs((R["net"] - R["gross"] + R["fee"] + R["slip"])[f]))))
                    assert np.all(R["fund"][f] == 0)
                else:
                    worst = max(worst, float(np.max(np.abs((R["net"] - R["gross"] - R["fund"] + R["fee"] + R["slip"])[f]))))
                # phi tinh lai doc lap theo loai thoat
                fm = klite.FEE_MAKER[model]
                q = R["xpx"][f] / R["entry"][f]
                k = R["kind"][f]
                fx = np.where(k == 1, fm, np.where(k == 2, fm if model == "OPT" else 5e-4, 5e-4))
                worst_fee = max(worst_fee, float(np.max(np.abs(R["fee"][f] - 1e4 * (fm + fx * q)))))
                if model == "OPT":
                    assert np.all(R["slip"][f] == 0)
    rec("E2a_accounting_identity", worst < 1e-9 and worst_fee < 1e-9, n_units=n, max_abs_resid_bps=worst,
        max_abs_fee_resid_bps=worst_fee)


# ------------------------------------------------------------------ E2b: qua trinh co dap an
def lattice_run(rng, npath, dt, k, tick=0.01, p0=1000, p_up=0.5, phi=0.0, h=0, tpm=1):
    T = int(round(k * dt * dt / tpm)) if tpm > 1 else int(round(k * dt * dt))
    nmin = 2 * T + 64
    px = synth.lattice_paths(rng, npath, nmin * tpm, p0, p_up=p_up, phi=phi, bounce_h=h).astype(np.float64) * tick
    G, raw = grid_from_paths(px, tpm)
    t0 = np.arange(npath) * nmin + 1
    d = dt * tick / (p0 * tick)
    return G, raw, px, t0, d, T, nmin


def t_e2b_lattice(rng):
    for (dt, k) in ((10, 2), (12, 8)):
        G, raw, px, t0, d, T, nmin = lattice_run(rng, 12000, dt, k)
        for model in ("OPT", "PESS"):
            R = klite.run_units(G, t0, d, T, T, 0.01, 0.0, model, alt_side(t0.size))
            f = R["filled"]
            res = R["gross"][f].copy()
            ans = "0 (martingale, cham dung muc tren luoi)"
            if model == "PESS":
                res = res + 1e4 * 0.01 / R["entry"][f] * (1 + (R["kind"][f] == 1))
                ans = "-tick/L x (1 + 1[thoat limit]) (xuyen 1 tick)"
            m, se, n = mse(res)
            g, gse, _ = mse(R["gross"][f])
            sd_ = R["side"][f]
            zb = mse(res[sd_ == 1]); zs = mse(res[sd_ == -1])
            rec("E2b_lattice_%s_d%dt_k%d" % (model, dt, k), abs(m) <= 3 * se and n >= 5000 and abs(zb[0]) <= 3 * zb[1]
                and abs(zs[0]) <= 3 * zs[1], answer=ans, n=n, mean_gross=g, se_gross=gse, resid_mean=m, resid_se=se, z=m / se, T=T,
                z_buy=zb[0] / zb[1], z_sell=zs[0] / zs[1], p_lim=float(np.mean(R["kind"][f] == 1)))


def t_e2b_drift(rng):
    dlt = 0.02
    G, raw, px, t0, d, T, nmin = lattice_run(rng, 12000, 10, 8, p_up=0.5 + dlt)
    for model in ("OPT", "PESS"):
        R = klite.run_units(G, t0, d, T, T, 0.01, 0.0, model, alt_side(t0.size))
        f = R["filled"]
        side = R["side"][f].astype(float)
        res = R["gross"][f] - 1e4 * side * 2 * dlt * 0.01 * R["dur"][f] / R["entry"][f]
        if model == "PESS":
            res = res + 1e4 * 0.01 / R["entry"][f] * (1 + (R["kind"][f] == 1))
        m, se, n = mse(res)
        g, gse, _ = mse(R["gross"][f])
        zb = mse(res[side == 1]); zs = mse(res[side == -1])
        gb, gs_ = mse(R["gross"][f][side == 1])[0], mse(R["gross"][f][side == -1])[0]
        rec("E2b_drift_%s" % model, abs(m) <= 3 * se and n >= 5000 and abs(zb[0]) <= 3 * zb[1] and abs(zs[0]) <= 3 * zs[1],
            answer="Wald: E = side x 2 delta tick x thoi gian giu", n=n, mean_gross=g, se_gross=gse, resid_mean=m, resid_se=se,
            z=m / se, z_buy=zb[0] / zb[1], z_sell=zs[0] / zs[1], gross_buy=gb, gross_sell=gs_)


def te_mc(rng, npath, dt, k, phi=0.0, h=0, mode="touch", p0=1000, tick=0.01):
    """Dap an mo phong DOC LAP: engine muc giao dich tren duong moi (seed khac)."""
    T = int(round(k * dt * dt))
    nmin = 2 * T + 64
    px = synth.lattice_paths(rng, npath, nmin, p0, phi=phi, bounce_h=h).astype(np.float64) * tick
    d = dt / p0
    out = []
    for i in range(npath):
        r = synth.trade_engine_path(px[i], 1, 1, d, T, T, tick, mode, 1 if i % 2 == 0 else -1)
        if r is not None:
            out.append(r[0])
    return mse(out)


def t_e2b_indep(rng):
    NP = 18000
    for lab, phi, h in (("bounce_h2", 0.0, 2), ("ar1_m0.3", -0.3, 0), ("ar1_m0.3_bounce1", -0.3, 1)):
        G, raw, px, t0, d, T, nmin = lattice_run(rng, NP, 10, 2, phi=phi, h=h)
        for model, mode in (("OPT", "touch"), ("PESS", "through")):
            R = klite.run_units(G, t0, d, T, T, 0.01, 0.0, model, alt_side(t0.size))
            m1, s1, n1 = mse(R["gross"][R["filled"]])
            m2, s2, n2 = te_mc(np.random.default_rng(rng.integers(1 << 62)), NP, 10, 2, phi=phi, h=h, mode=mode)
            z = (m1 - m2) / math.sqrt(s1 ** 2 + s2 ** 2)
            # cung duong: tung don vi phai TRUNG KHOP (tpm = 1 => K = muc giao dich)
            mx = 0.0
            for i in range(0, NP, 7):
                r = synth.trade_engine_path(px[i], 1, 1, d, T, T, 0.01, mode, 1 if i % 2 == 0 else -1)
                g = R["gross"][i]
                if r is None:
                    mx = max(mx, 0.0 if not R["filled"][i] else 1e9)
                else:
                    mx = max(mx, abs(r[0] - g) if R["filled"][i] else 1e9)
            rec("E2b_indepMC_%s_%s" % (lab, model), abs(z) <= 3 and n1 >= 5000 and mx < 1e-9,
                pipeline_mean=m1, pipeline_se=s1, answer_mc_mean=m2, answer_mc_se=s2, z=z, n=n1,
                paired_same_path_max_abs_diff=mx)


def t_bracket(rng):
    """Nhieu giao dich/phut: K_OPT >= muc giao dich touch, K_PESS <= muc giao dich through (theo trung binh)."""
    out = {}
    for lab, gen in (("lattice_tpm10_bounce1", "lat"), ("gbm_tpm10", "gbm")):
        for (dt, k) in ((4, 2), (6, 8), (12, 2), (12, 8)):
            tpm = 10
            if gen == "lat":
                T = max(int(round(k * dt * dt / tpm)), 1)
                nmin = 2 * T + 64
                px = synth.lattice_paths(rng, 5000, nmin * tpm, 1000, bounce_h=1).astype(np.float64) * 0.01
                tick, d = 0.01, dt / 1000.0
            else:
                c = dt / 120.0 if dt >= 12 else dt / 160.0
                T = max(klite.unit_T(c, k), 1)
                nmin = 2 * T + 64
                px, tick = synth.gbm_paths(rng, 5000, nmin, tpm, 0.04)
                d = c * 0.04
            G, raw = grid_from_paths(px, tpm)
            t0 = np.arange(5000) * nmin + 1
            row = {}
            for model, mode in (("OPT", "touch"), ("PESS", "through")):
                R = klite.run_units(G, t0, d, T, T, tick, 0.0, model, alt_side(5000))
                tr = np.full(5000, np.nan)
                for i in range(5000):
                    r = synth.trade_engine_path(px[i], tpm, 1, d, T, T, tick, mode, 1 if i % 2 == 0 else -1)
                    if r is not None:
                        tr[i] = r[0]
                kk = np.where(np.isfinite(R["gross"]), R["gross"], 0.0)
                tt = np.where(np.isfinite(tr), tr, 0.0)
                both = R["filled"] | np.isfinite(tr)
                diff = (kk - tt)[both]
                m, se, n = mse(diff)
                row[model] = dict(K_mean=mse(R["gross"][R["filled"]])[0], trade_mean=mse(tr)[0], paired_diff=m, se=se,
                                  fill_K=float(R["filled"].mean()), fill_trade=float(np.isfinite(tr).mean()))
                ok = (m >= -3 * se) if model == "OPT" else (m <= 3 * se)
                rec("bracket_%s_d%d_k%d_%s" % (lab, dt, k, model), ok, **row[model])
            out[(lab, dt, k)] = row
    return out


# ------------------------------------------------------------------ E2c: bounce
def t_e2c(rng):
    # mid co dinh 100,00; giao dich 100 +- 0,05 (h = 5 tick), 4 giao dich/phut, d = 4 bps
    tick, h, tpm, npath = 0.01, 5, 4, 2000
    W = T = 60
    nmin = 2 * T + 64
    eps = np.where(rng.random((npath, nmin * tpm)) < 0.5, 1, -1)
    px = (10000 + h * eps).astype(np.float64) * tick
    G, raw = grid_from_paths(px, tpm)
    t0 = np.arange(npath) * nmin + 1
    d = 0.0004
    bad = 0
    O, H, L, C, v = raw
    for model in ("OPT", "PESS"):
        for sdv in (1, -1):
            R = klite.run_units(G, t0, d, W, T, tick, 0.0, model, sdv)
            for i in range(npath):
                hiM = abs(R["m0"][i] - 100.05) < 1e-9
                if sdv == 1 and not hiM:
                    exp = None                     # mua tai 99,91 khong bao gio cham (bid 99,95)
                elif sdv == -1 and hiM:
                    exp = None                     # ban tai 100,10 khong bao gio cham (ask 100,05)
                elif sdv == 1:
                    exp = (100.04 - 100.00) / 100.00 * 1e4
                elif model == "OPT":
                    exp = (99.99 - 99.95) / 99.99 * 1e4
                else:      # PESS ban 99,99; muc thoat 99,95 khong bao gio bi XUYEN -> taker ngay neu dong phut <= 99,95, con lai het han
                    f = R["f"][i]
                    cx = 99.95 if C[f] <= 99.95 + 1e-9 else C[f + T]
                    exp = (99.99 - cx) / 99.99 * 1e4
                if exp is None:
                    bad += int(bool(R["filled"][i]))
                elif not R["filled"][i] or abs(R["gross"][i] - exp) > 1e-9:
                    bad += 1
    sp = [klite.ar_spread(H[i * 1440:(i + 1) * 1440], L[i * 1440:(i + 1) * 1440], C[i * 1440:(i + 1) * 1440])
          for i in range(len(C) // 1440)]
    sp_m = float(np.nanmean(sp)) * 1e4
    sp_exp = 10.0 * math.sqrt(7.0 / 8.0)   # AR voi 4 giao dich/phut: phut 1 phia (xs 1/8) dong gop 0
    rec("E2c_bounce_fixed_mid_deterministic", bad == 0 and abs(sp_m - sp_exp) < 0.2, n_bad=bad,
        ar_spread_bps=sp_m, ar_spread_expected_bps=sp_exp, ar_spread_true_bps=10.0, note="K cham-la-khop an tron bounce: +4 bps/don vi khi mid khong doi")
    # RW mid + bounce: tru phan bat spread uoc tinh (C4) so voi cung duong mid khong bounce
    T = 115
    nmin = 2 * T + 64
    npath = 6000
    mid = synth.lattice_paths(rng, npath, nmin * tpm, 10000, bounce_h=0)
    epsb = np.where(rng.random(mid.shape) < 0.5, 1, -1)
    rows = {}
    for lab, pxx in (("nobounce", mid), ("bounce_h5", mid + 5 * epsb)):
        G, raw = grid_from_paths(pxx.astype(np.float64) * tick, tpm)
        t0 = np.arange(npath) * nmin + 1
        R = klite.run_units(G, t0, 0.002, T, T, tick, 0.0, "OPT", alt_side(t0.size))
        rows[lab] = R
    gb, gn = rows["bounce_h5"], rows["nobounce"]
    mb, sb, nb = mse(gb["gross"][gb["filled"]])
    mn, sn, nn = mse(gn["gross"][gn["filled"]])
    cap = 5.0 * gb["n_maker"][gb["filled"]]          # s/2 = 5 bps tren gia ~100 x so chan maker
    ma, sa, _ = mse(gb["gross"][gb["filled"]] - cap)
    z = (ma - mn) / math.sqrt(sa ** 2 + sn ** 2)
    rec("E2c_rw_bounce_C4_deduction", abs(z) <= 3, gross_bounce=mb, se_b=sb, gross_nobounce=mn, se_n=sn, cap_est_mean=float(cap.mean()),
        gross_bounce_minus_cap=ma, z=z, note="d = 20 tick >> s/2 = 5 tick; khi d ~ s/2 phan tru C4 qua tay (bao thu)")


# ------------------------------------------------------------------ test bien (nen tay)
def mk(bars, delist=-1):
    O = np.array([b[0] if b else np.nan for b in bars])
    H = np.array([b[1] if b else np.nan for b in bars])
    L = np.array([b[2] if b else np.nan for b in bars])
    C = np.array([b[3] if b else np.nan for b in bars])
    v = np.array([b is not None for b in bars])
    return klite.prepare_grid(O, H, L, C, v, delist)


def flat(n, p=100.0):
    return [(p, p, p, p)] * n


def t_edges():
    tick = 0.01
    # hai don vi BUY/SELL doc lap cung phut cham ca 99,00 va 101,00 (khong OCO): moi ben khop + tinh rieng
    b = flat(200)
    b[1] = (100.2, 101.5, 98.5, 99.0)
    G = mk(b)
    Ob = klite.run_units(G, [1], 0.01, 10, 10, tick, 0.0, "OPT", 1)
    Os = klite.run_units(G, [1], 0.01, 10, 10, tick, 0.0, "OPT", -1)
    Pb = klite.run_units(G, [1], 0.01, 10, 10, tick, 5e-4, "PESS", 1)
    Ps = klite.run_units(G, [1], 0.01, 10, 10, tick, 5e-4, "PESS", -1)
    ok1 = (Ob["filled"][0] and Os["filled"][0] and Ob["x"][0] == 1 and Os["x"][0] == 1
           and abs(Ob["gross"][0] - (99.99 - 99.0) / 99.0 * 1e4) < 1e-9 and abs(Os["gross"][0] - (101.0 - 99.99) / 101.0 * 1e4) < 1e-9
           and Pb["kind"][0] == 1 and Pb["x"][0] == 2 and Ps["kind"][0] == 4 and Ps["x"][0] == 2)
    rec("edge_two_independent_sides_same_minute", ok1, opt_buy=float(Ob["gross"][0]), opt_sell=float(Os["gross"][0]),
        pess_buy_kind=klite.EXIT_NAMES[int(Pb["kind"][0])], pess_sell_kind=klite.EXIT_NAMES[int(Ps["kind"][0])])
    # gia nhay qua muc: phut 3 mo 97 (duoi 99) -> khop TAI 99,00
    b = flat(200)
    b[3] = (97.0, 97.5, 96.5, 97.2)
    G = mk(b)
    R = [klite.run_units(G, [1], 0.01, 10, 10, tick, 0.0, m, 1) for m in ("OPT", "PESS")]
    ok2 = all(r["entry"][0] == 99.0 and r["f"][0] == 3 and r["side"][0] == 1 for r in R)
    rec("edge_gap_through_level_fill_at_limit", ok2, entry=[float(r["entry"][0]) for r in R])
    # PESS: dong phut khop da vuot muc thoat -> taker tai X o phut f+1; OPT: vong tron cung phut
    b = flat(200)
    b[2] = (100.0, 100.5, 98.9, 100.3)
    G = mk(b)
    Ro = klite.run_units(G, [1], 0.01, 10, 10, tick, 5e-4, "OPT", 1)
    Rp = klite.run_units(G, [1], 0.01, 10, 10, tick, 5e-4, "PESS", 1)
    X = math.ceil(99.0 * 1.01 / tick - 1e-7) * tick
    ok3 = (Ro["kind"][0] == 1 and Ro["x"][0] == 2 and Rp["kind"][0] == 4 and Rp["x"][0] == 3 and abs(Rp["xpx"][0] - X) < 1e-9
           and abs(Rp["fee"][0] - 1e4 * (4e-4 + 5e-4 * X / 99.0)) < 1e-9 and abs(Rp["slip"][0] - 5.0 * X / 99.0) < 1e-9)
    rec("edge_exit_beyond_at_entry_minute", ok3, opt=klite.EXIT_NAMES[int(Ro["kind"][0])], pess=klite.EXIT_NAMES[int(Rp["kind"][0])],
        pess_fee=float(Rp["fee"][0]), pess_slip=float(Rp["slip"][0]))
    # het han: khop phut 2, T = 5 -> dong close phut 7; neu phut 7 lo -> phut hop le ke tiep
    b = flat(300)
    b[2] = (99.5, 99.5, 98.9, 99.1)
    for i in range(3, 8):
        b[i] = (99.1, 99.3, 99.0, 99.2)
    b[7] = (99.2, 99.4, 99.1, 99.35)
    G = mk(b)
    R = [klite.run_units(G, [1], 0.01, 10, 5, tick, 6e-4, m, 1) for m in ("OPT", "PESS")]
    ok4 = all(r["kind"][0] == 2 and r["x"][0] == 7 and r["xpx"][0] == 99.35 for r in R)
    ok4 &= abs(R[0]["fee"][0] - 1e4 * (2e-4 + 2e-4 * 99.35 / 99.0)) < 1e-9
    ok4 &= abs(R[1]["fee"][0] - 1e4 * (4e-4 + 5e-4 * 99.35 / 99.0)) < 1e-9 and abs(R[1]["slip"][0] - 6.0 * 99.35 / 99.0) < 1e-9
    b2 = list(b)
    b2[7] = None
    b2[8] = (99.3, 99.4, 99.2, 99.33)
    G2 = mk(b2)
    R2 = klite.run_units(G2, [1], 0.01, 10, 5, tick, 0.0, "OPT", 1)
    ok4 &= R2["x"][0] == 8 and R2["xpx"][0] == 99.33 and R2["excl"][0] == 0
    rec("edge_timeout_and_timeout_in_gap", ok4, x=int(R[0]["x"][0]), x_gap=int(R2["x"][0]))
    # delist giua don vi: khop phut 2, delist o phut 4 (close 98,5)
    b = flat(300)
    b[2] = (99.5, 99.5, 98.9, 99.1)
    b[3] = (99.1, 99.2, 99.0, 99.1)
    b[4] = (99.0, 99.0, 98.4, 98.5)
    G = mk(b, delist=4)
    R = [klite.run_units(G, [1], 0.01, 10, 50, tick, 6e-4, m, 1) for m in ("OPT", "PESS")]
    ok5 = all(r["kind"][0] == 3 and r["x"][0] == 4 and r["xpx"][0] == 98.5 for r in R)
    ok5 &= abs(R[0]["fee"][0] - 1e4 * (2e-4 + 5e-4 * 98.5 / 99)) < 1e-9 and R[0]["slip"][0] == 0
    ok5 &= abs(R[1]["slip"][0] - 50.0 * 98.5 / 99) < 1e-9
    Gd = mk(flat(300), delist=3)
    Rd = klite.run_units(Gd, [1], 0.01, 10, 10, tick, 0.0, "OPT", 1)
    ok5 &= (not Rd["filled"][0])
    rec("edge_delist_mid_unit", ok5, opt_net=float(R[0]["net"][0]), pess_net=float(R[1]["net"][0]))
    # lo du lieu: lo ngan (30') luc gia cham muc -> khong khop trong lo; lo dai (90') -> don vi bi loai
    b = flat(400)
    for i in range(5, 35):
        b[i] = None
    b[35] = (99.5, 99.6, 99.4, 99.5)
    G = mk(b)
    R = klite.run_units(G, [1], 0.01, 100, 100, tick, 0.0, "OPT", 1)
    ok6 = (not R["filled"][0]) and R["excl"][0] == 0
    b = flat(400)
    b[36] = (99.5, 99.5, 98.0, 98.5)
    for i in range(37, 40):
        b[i] = (98.5, 98.6, 98.4, 98.5)
    for i in range(40, 130):
        b[i] = None
    G = mk(b)
    R = klite.run_units(G, [1], 0.01, 100, 100, tick, 0.0, "OPT", 1)
    ok6 &= R["filled"][0] and R["excl"][0] == 1
    rec("edge_short_gap_no_fill_long_gap_excluded", ok6)
    # tick: ngay doi tick 0,01 -> 0,001 => chon 0,001; lam tron muc ra XA mid
    p1 = np.round(100 + 0.01 * np.arange(500), 2)
    p2 = np.round(100 + 0.001 * np.arange(1, 600, 3), 3)
    t_mix = klite.infer_tick(np.r_[p1, p2])
    t_ref = kref.ref_tick(list(np.r_[p1, p2]))
    t5 = klite.infer_tick(np.round(np.arange(500) * 0.5 + 7, 1))
    r = np.random.default_rng(3)
    agree = 0
    for _ in range(200):
        tk = [1e-1, 5e-2, 1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 2e-1][r.integers(9)]
        base = r.uniform(0.001, 50000)
        pp = np.round((base + tk * r.integers(0, 5000, 300)) / tk) * tk
        agree += klite.infer_tick(pp) == kref.ref_tick(list(pp))
    Lb = klite.floor_tick(100.0 * (1 - 0.00123), 0.01)
    Ls = klite.ceil_tick(100.0 * (1 + 0.00123), 0.01)
    ok7 = t_mix == 0.001 and t_ref == 0.001 and t5 == 0.5 and agree == 200 and abs(Lb - 99.87) < 1e-12 and abs(Ls - 100.13) < 1e-12
    rec("edge_tick_change_and_rounding", ok7, tick_mixed=t_mix, tick_ref=t_ref, tick_half=t5, agree_200=int(agree),
        Lb=float(Lb), Ls=float(Ls))
    # funding: moc trung phut khop (s = f) KHONG tinh; s = x CO tinh; dau theo chieu; mark = close phut s-1
    b = flat(300)
    b[2] = (99.5, 99.5, 98.9, 99.1)
    for i in range(3, 300):
        b[i] = (99.5, 99.6, 99.4, 99.5)
    b[9] = (99.5, 100.2, 99.4, 99.9)     # thoat limit tai X = 99,99 o phut 9
    b[8] = (99.5, 99.6, 99.4, 99.55)
    G = mk(b)
    R = klite.run_units(G, [1], 0.01, 10, 50, tick, 0.0, "OPT", 1, np.array([2, 5, 9, 10]), np.array([1e-3, 1e-4, 2e-4, 5e-3]))
    exp = -1 * (1e-4 * 99.5 + 2e-4 * 99.55) / 99.0 * 1e4
    rr = kref.simulate_unit(*lists(G), 1, 0.01, 10, 50, tick, 0.0, "OPT", 1, [(2, 1e-3), (5, 1e-4), (9, 2e-4), (10, 5e-3)])
    ok8 = R["x"][0] == 9 and abs(R["fund"][0] - exp) < 1e-9 and abs(rr["fund"] - exp) < 1e-9
    rec("edge_funding_boundaries", ok8, fund_bps=float(R["fund"][0]), expected=exp, ref=rr["fund"])


# ------------------------------------------------------------------ doi chieu 2 cai dat + in tay
def t_ref_compare(rng, outdir):
    lines = []
    tot, bad, nfill = 0, 0, 0
    kinds = np.zeros(5, int)
    for case in range(4):
        tpm = [1, 4, 10, 6][case]
        nmin = 40000
        px = synth.lattice_paths(rng, 1, nmin * tpm, 30000, phi=[0, -0.2, 0, 0.1][case], bounce_h=[0, 2, 1, 3][case]) * 0.01
        valid = rng.random(nmin) > 0.003
        valid[15000:15070] = False
        valid[25000:25045] = False
        dl = 35600 if case in (1, 2) else -1
        G, _ = grid_from_paths(px, tpm, valid, dl)
        Ls_ = lists(G)
        fs = np.arange(17, nmin, [480, 240, 60, 480][case])
        fr = rng.normal(1e-4, 2e-4, fs.size)
        fl = list(zip(fs.tolist(), fr.tolist()))
        t0 = np.arange(70, 35500, 61)
        t0 = t0[G["valid"][t0 - 1]]
        for model in ("OPT", "PESS"):
            for (d, W) in ((0.00015, 20), (0.0025, 400)):
                sides = alt_side(t0.size)
                R = klite.run_units(G, t0, d, W, W, 0.01, 6e-4, model, sides, fs, fr)
                for i, t in enumerate(t0):
                    r = kref.simulate_unit(*Ls_, int(t), d, W, W, 0.01, 6e-4, model, int(sides[i]), fl, dl)
                    tot += 1
                    same = r["filled"] == bool(R["filled"][i]) and r["excluded"] == bool(R["excl"][i])
                    if same and r["filled"]:
                        nfill += 1
                        kinds[R["kind"][i]] += 1
                        same = (r["side"] == R["side"][i] and r["f"] == R["f"][i] and r["x"] == R["x"][i] and
                                all(abs(r[k] - R[k][i]) < 1e-9 for k in ("gross", "fee", "slip", "fund", "net")))
                    bad += 0 if same else 1
                    if r["filled"] and len(lines) < 26 and (i % 37 == 0 or R["kind"][i] in (3, 4)):
                        lines.append("case%d %-4s d=%.4f W=T=%d t0=%d m0=%.2f side=%+d f=%d x=%d kind=%s entry=%.2f exit=%.2f | "
                                     "klite gross=%.4f fee=%.4f slip=%.4f fund=%.4f net=%.4f | kref net=%.4f | %s" % (
                                         case, model, d, W, t, R["m0"][i], R["side"][i], R["f"][i], R["x"][i],
                                         klite.EXIT_NAMES[int(R["kind"][i])], R["entry"][i], R["xpx"][i], R["gross"][i],
                                         R["fee"][i], R["slip"][i], R["fund"][i], R["net"][i], r["net"],
                                         "TRUNG" if abs(r["net"] - R["net"][i]) < 1e-9 else "LECH"))
    with open(os.path.join(outdir, "hand_units.txt"), "w") as fh:
        fh.write("In tay: klite (vector) vs kref (python thuan, doc lap) - %d don vi mau\n" % len(lines))
        fh.write("\n".join(lines) + "\n")
    rec("ref_vs_klite_all_units", bad == 0 and len(lines) >= 20 and kinds[3] > 0 and kinds[4] > 0, n_units=tot, n_filled=nfill,
        n_mismatch=bad, exit_kinds=dict(limit=int(kinds[1]), timeout=int(kinds[2]), delist=int(kinds[3]), taker_beyond=int(kinds[4])),
        n_hand=len(lines))


def t_lookahead(rng):
    px = synth.lattice_paths(rng, 1, 30000 * 5, 30000, bounce_h=1) * 0.01
    G, raw = grid_from_paths(px, 5)
    tc = 14000
    t0 = np.arange(61, tc, 13)
    fs = np.arange(5, 30000, 480)
    fr = np.full(fs.size, 1e-4)
    tc = 14000
    O, H, L, C, v = [np.array(a, copy=True) for a in raw]
    O[tc:] = rng.uniform(1, 1000, O.size - tc)
    H[tc:] = O[tc:] * 2
    L[tc:] = O[tc:] / 2
    C[tc:] = O[tc:]
    v[tc:] = rng.random(v.size - tc) < 0.7
    G2 = klite.prepare_grid(O, H, L, C, v, -1)
    fr2 = np.where(fs >= tc, 0.05, fr)
    nb, nchk = 0, 0
    for model in ("OPT", "PESS"):
        R1 = klite.run_units(G, t0, 0.002, 300, 300, 0.01, 5e-4, model, alt_side(t0.size), fs, fr)
        R2 = klite.run_units(G2, t0, 0.002, 300, 300, 0.01, 5e-4, model, alt_side(t0.size), fs, fr2)
        end = np.where(R1["filled"], R1["x"], t0 + 299)
        k = end < tc - 1
        nchk += int(k.sum())
        for key in ("filled", "side", "f", "x", "kind", "excl"):
            nb += int(np.sum(R1[key][k] != R2[key][k]))
        nb += int(np.sum(np.abs(np.nan_to_num(R1["net"][k]) - np.nan_to_num(R2["net"][k])) > 0))
    # dac trung ngay ex-ante
    Gd = klite.prepare_grid(*raw[:4], raw[4], -1)
    nday = 30000 // 1440
    f1 = klite.daily_features(Gd, nday)
    f2 = klite.daily_features(G2, nday)
    s1, s2 = klite.sigma_exante(f1["close"], 5, 3), klite.sigma_exante(f2["close"], 5, 3)
    dc = tc // 1440
    feat_ok = np.allclose(s1[: dc + 1], s2[: dc + 1], equal_nan=True) and np.array_equal(f1["tick"][:dc], f2["tick"][:dc], equal_nan=True)
    rec("no_lookahead_kernel_and_features", nb == 0 and nchk > 1000 and feat_ok, n_checked=nchk, n_diff=nb, feat_ok=bool(feat_ok))


def t_sigma_T():
    r = np.random.default_rng(5)
    close = 100 * np.exp(np.cumsum(r.normal(0, 0.04, 200)))
    close[50:53] = np.nan
    s = klite.sigma_exante(close)
    bad = 0
    for D in range(0, 200):
        a = s[D]
        b = kref.ref_sigma(list(close), D) if D >= 30 else float("nan")
        if not ((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-12):
            bad += 1
    Ts = {(c, k): klite.unit_T(c, k) for c in (0.1, 0.2, 0.4) for k in (2, 8)}
    ok = bad == 0 and Ts[(0.1, 2)] == 29 and Ts[(0.4, 8)] == 1843 and Ts[(0.2, 2)] == 115
    rec("sigma_exante_vs_ref_and_T", ok, n_bad=bad, T_minutes={"%s_%s" % k: v for k, v in Ts.items()})


def _null_panel(rng, D, J, heavy=False):
    common = rng.normal(0, 1, (D, 1))
    if heavy:
        Z = 0.6 * common + 0.8 * rng.standard_t(4, (D, J)) / math.sqrt(2.0)
        N = rng.poisson(rng.uniform(20, 200, J)[None, :] * (1 + 0.5 * (rng.random((D, 1)) < 0.2)), (D, J)).astype(float)
    else:
        Z = 0.6 * common + 0.8 * rng.normal(0, 1, (D, J))
        N = np.full((D, J), 100.0)
    return Z, N


def t_stats(rng):
    # SE khoi (tong khoi khong chong lan) vs giai tich (iid ngay)
    D, J = 731, 20
    N = rng.integers(50, 150, (D, J)).astype(float)
    sd = 30.0
    S = rng.normal(0, sd, (D, J)) * np.sqrt(N)
    st = stats.cell_stats(S, N, 0.0, 1, B=1000)
    se_an = sd / np.sqrt(N.sum(0))
    ratio = st["SE"] / se_an
    ok1 = np.all((ratio > 0.65) & (ratio < 1.35)) and abs(ratio.mean() - 1) < 0.06   # ~37 khoi => SE co sai so ~12 %/o
    rec("stats_block_se_vs_analytic", ok1, se_ratio_mean=float(ratio.mean()), se_ratio_min=float(ratio.min()),
        se_ratio_max=float(ratio.max()), alpha=st["alpha"], alpha_upper=st["alpha_upper"], method=st["method"])
    # FWER RW studentized @ 4 % duoi null 32 o tuong quan (M = san): Gauss + duoi day / N Poisson khong deu
    nsim = 300
    lim = stats.ALPHA_FWER + 3 * math.sqrt(stats.ALPHA_FWER * (1 - stats.ALPHA_FWER) / nsim)
    for heavy in (False, True):
        fw, fw_unadj, marg = 0, 0, []
        for s_ in range(nsim):
            Z, N = _null_panel(rng, D, 32, heavy)
            S = 4.0 * N + 30.0 * Z * np.sqrt(N)
            r = stats.cell_stats(S, N, 4.0, 1000 + s_, B=300)
            fw += int(r["rw_reject"].any())
            fw_unadj += int((r["p_marg"] <= 0.05).any())
            marg.append(float(np.mean(r["p_marg"] <= 0.05)))
        rate = fw / nsim
        rec("stats_rw_studentized_fwer_null_%s" % ("heavy" if heavy else "gauss"), rate <= lim, fwer_rw=rate, limit=lim,
            alpha=stats.ALPHA_FWER, fwer_unadjusted=fw_unadj / nsim, marginal_size_5pct=float(np.mean(marg)), nsim=nsim)
    # hieu ung cay: 4 / 32 o co M = san + 5 SE that; con lai = san
    nsim = 200
    lim = stats.ALPHA_FWER + 3 * math.sqrt(stats.ALPHA_FWER * (1 - stats.ALPHA_FWER) / nsim)
    hit, false_any = np.zeros(4), 0
    for s_ in range(nsim):
        Z, N = _null_panel(rng, D, 32, True)
        sd_cell = 30.0 / np.sqrt(N.sum(0)) * 1.0
        mu = np.full(32, 4.0)
        mu[:4] += 5.0 * sd_cell[:4]
        S = mu[None, :] * N + 30.0 * Z * np.sqrt(N)
        r = stats.cell_stats(S, N, 4.0, 5000 + s_, B=300)
        hit += r["rw_reject"][:4]
        false_any += int(r["rw_reject"][4:].any())
    pw = hit / nsim
    rec("stats_rw_studentized_planted_effect", bool(pw.min() >= 0.6 and false_any / nsim <= lim), power_per_cell=pw.tolist(),
        fwer_among_null=false_any / nsim, limit=lim, nsim=nsim)
    # INSUFFICIENT + can tren 95 % rieng
    Z, N = _null_panel(rng, D, 6, False)
    N[:, 1] = 0.0                                  # khong co don vi
    N[:, 2] = 0.0
    N[:150, 2] = 1.0                               # 150 < 200 don vi
    N[:, 3] = 0.0
    N[:250, 3] = 1.0                               # 250 >= 200
    S = -20.0 * N + 30.0 * Z * np.sqrt(N)
    S[:, 2] = 500.0 * N[:, 2]                      # o 2: M rat lon nhung INSUFFICIENT
    r = stats.cell_stats(S, N, 4.0, 11, B=500)
    r1 = stats.cell_stats(S, N, 4.0, 11, B=500, alpha_upper=0.01)
    ins = r["insufficient"].tolist()
    ok_i = (ins == [False, True, True, False, False, False] and not r["rw_reject"][2] and r["p_rw"][1] == 1.0 and r["p_rw"][2] == 1.0
            and np.isinf(r["t"][1]) and r["t"][1] < 0 and np.isnan(r["upper_sim95"][1]) and np.isnan(r["p_marg"][2])
            and np.all(np.isfinite(r["upper_sim95"][[0, 3, 4, 5]])) and r1["c_upper"] > r["c_upper"]
            and r["alpha_upper"] == 0.05 and r["alpha"] == 0.04)
    p_one = stats.single_p(S[:, 2], N[:, 2], 4.0, 3)
    rec("stats_insufficient_and_upper95", ok_i and np.isnan(p_one[2]), insufficient=ins, p_rw=r["p_rw"].tolist(),
        c_upper_95=r["c_upper"], c_upper_99=r1["c_upper"], single_p_insufficient=str(p_one[2]))


def t_tiers():
    import runner_kaggle as rk
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
          T["S58USDT"][D] == 2 and T["S59USDT"][D] == 3 and T["S00USDT"][D2] == 1 and T["S09USDT"][D2] == 2)
    rec("tiers_point_in_time", ok, n_sym=len(T))


# ------------------------------------------------------------------ runner end-to-end tren lake GBM gia
def gbm_answer(rng, c, k, sig, model, npath=20000, tpm=10):
    """Dap an DOC LAP cho gross K-model tren GBM: duong moi, sigma_hat ~ RMS 30 return ngay (phan phoi dung), kref."""
    T = klite.unit_T(c, k)
    nmin = 2 * T + 64
    out = []
    done = 0
    while done < npath:
        m = min(500, npath - done)
        px, q = synth.gbm_paths(rng, m, nmin, tpm, sig)
        O, H, L, C = synth.bars_from_trades(px, tpm)
        r30 = rng.normal(-0.5 * sig * sig, sig, (m, 30))
        sh = np.sqrt((r30 ** 2).mean(1))
        for i in range(m):
            rr = kref.simulate_unit(O[i].tolist(), H[i].tolist(), L[i].tolist(), C[i].tolist(), 1, c * sh[i], T, T, q, 0.0, model,
                                    1 if (done + i) % 2 == 0 else -1)
            if rr["filled"]:
                out.append(rr["gross"])
        done += m
    return mse(out)


def t_runner(rng, outdir):
    import runner_kaggle as rk
    import pandas as pd
    root = os.path.join(outdir, "_fake_lake")
    ro = os.path.join(outdir, "_fake_run")
    for p in (root, ro):
        shutil.rmtree(p, ignore_errors=True)
    meta = synth.write_fake_lake(root)
    extra = _add_premonths(root)                       # R5-4: thang truoc DATA_START - 31 ngay (pass1 bo qua)
    meta["rows"][2021] = meta["rows"][2021] + sum(extra.values())
    os.makedirs(ro, exist_ok=True)
    os.environ.update(GRIDV2_INPUT=root, GRIDV2_OUT=ro, GRIDV2_SHARD="0/1", GRIDV2_KEEP_SYM="1")
    tov = dict(registry=meta["rows"], mkt_sym="AAAUSDT", cond={"A": dict(z=2.5, vmult=0.5)})
    t = time.time()
    v, man = rk.run(test_overrides=tov)
    secs = time.time() - t
    rec("runner_V0_V6_on_fake_lake", v["all_pass"] and not man["prereg_constants"],
        V0=v["V0"]["ok_registry"] and v["V0"]["ok_read_eq_meta"], V1=v["V1"]["ok"],
        V2=dict(ok=v["V2"]["ok"], max_bad_frac=v["V2"]["max_bad_frac"]), V3=dict(long_gaps=v["V3"]["long_gaps"],
                                                                             excl_gap=v["V3"]["units_excl_gap"]),
        V4=[(c["n_checked"], c["n_diff"]) for c in v["V4"]["checks"]], V5=[c["ok"] for c in v["V5"]["checks"]],
        V6=v["V6"], seconds=secs)
    fs = v["V0"]["V0b"]["files_skipped"]
    rec("runner_V0b_skipped_premonths", v["V0"]["ok_V0a"] and v["V0"]["ok_V0b"]
        and [f["file"] for f in fs] == ["kline1m-2021-01.parquet", "kline1m-2021-02.parquet", "kline1m-2021-03.parquet"]
        and [f["meta_rows"] for f in fs] == [extra[(2021, m)] for m in (1, 2, 3)]
        and v["V0"]["V0b"]["by_year"][2021]["meta_skipped"] == sum(extra.values()),
        files_skipped=fs, v0b_2021=v["V0"]["V0b"]["by_year"][2021],
        V4=[(c["sym"], c["tc_min"], c["tc_range"], c["n_checked"], c["n_diff"]) for c in v["V4"]["checks"]],
        v4_skipped=v["V4"]["v4_skipped"])
    v5v = v["V5"]
    rec("runner_V5_full_coverage", v5v["ok"] and v5v["coverage"]["ck"] == list(range(6)) and v5v["coverage"]["side"] == [-1, 1]
        and v5v["coverage"]["model"] == ["OPT", "PESS"] and 8 <= len(v5v["checked"]) <= 12 and not v5v["missing_ck"]
        and all(len(r) == 6 for r in v5v["checked"]), checked=v5v["checked"], coverage=v5v["coverage"])
    # R3-11: chay lai tu checkpoint -> bo dem V3 giong het
    v3a = {k: v["V3"][k] for k in ("long_gaps", "units_excl_gap", "units_excl_noend", "feat_mismatch_days", "sym_month_missing")}
    tov2 = dict(tov, v4_syms=0)
    vb, _ = rk.run(test_overrides=tov2)
    v3b = {k: vb["V3"][k] for k in v3a}
    rec("runner_checkpoint_keeps_V3_counters", v3a == v3b and vb["V3"]["n_sym_from_checkpoint"] > 0,
        first=v3a, restart=v3b, n_from_ckpt=vb["V3"]["n_sym_from_checkpoint"])
    os.environ.pop("GRIDV2_KEEP_SYM", None)
    try:
        rk.merge(os.path.join(ro, "merged_x"), [ro], nboot=1000)
        refused = False
    except RuntimeError:
        refused = True
    res, TT = rk.merge(os.path.join(ro, "merged"), [ro], nboot=1000, allow_test=True)
    rec("merge_refuses_test_shard_without_allow_test", refused and res["alpha_fwer"] == 0.04 and res["alpha_upper"] == 0.05)
    A = TT["agg"]
    nday = (rk.SEAL - rk.DATA_START) // rk.DAY
    d0 = (rk.STUDY_START - rk.DATA_START) // rk.DAY
    cmp = []
    for cell in rk.cells()[:18]:
        if cell["tier"] != 1:
            continue
        for model in ("OPT", "PESS"):
            sub = A[(A.cell == cell["id"]) & (A.model == model)]
            S = np.zeros((nday - d0, 1))
            N = np.zeros((nday - d0, 1))
            g = sub.groupby("day")[["gross", "fill"]].sum()
            S[g.index - d0, 0] = g.gross.to_numpy()
            N[g.index - d0, 0] = g.fill.to_numpy()
            st = stats.cell_stats(S, N, 0.0, 7, B=1000)
            m_ans, se_ans, n_ans = gbm_answer(np.random.default_rng(rng.integers(1 << 62)), cell["c"], cell["k"], 0.04, model)
            z = (st["M"][0] - m_ans) / math.sqrt(st["SE"][0] ** 2 + se_ans ** 2)
            cmp.append(dict(cell=cell["name"], model=model, M_gross_pipeline=float(st["M"][0]), se_pipeline=float(st["SE"][0]),
                            n_units=int(N.sum()), answer_mc=m_ans, se_answer=se_ans, n_answer=n_ans, z=float(z)))
            rec("runner_GBM_gross_vs_answer_%s_%s" % (cell["name"], model), abs(z) <= 3 and n_ans >= 5000, **cmp[-1])
    json.dump(dict(rule=res["rule"], cmp=cmp, merged_B_M=res["models"]["OPT"]["B"]["M"]),
              open(os.path.join(outdir, "runner_fake_summary.json"), "w"), indent=1, default=float)
    shutil.rmtree(root, ignore_errors=True)            # lake gia tam thoi (~150 MB) - xoa sau test


# ------------------------------------------------------------------ feature M3: tinh tay + doi chieu kref
def t_features(rng):
    bad = []
    # ER30
    n = 40
    hc = np.full(n * 24, np.nan)
    hc[:] = 100 + np.arange(n * 24) * 0.1                       # tang deu -> ER = 1
    e1 = klite.er30(hc, n)[35]
    z = np.where(np.arange(n * 24) % 2 == 0, 100.0, 101.0)       # rang cua: |cuoi-dau| = 1 hoac 0 / tong lon
    e2 = klite.er30(z, n)[35]
    e2r = kref.ref_er30(list(z), 35)
    h3 = hc.copy()
    h3[(35 - 30) * 24:(35 - 30) * 24 + 130] = np.nan               # con 590 < 600 -> NaN
    e3 = klite.er30(h3, n)[35]
    h4 = 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n * 24)))
    h4[rng.random(n * 24) < 0.1] = np.nan
    e4 = klite.er30(h4, n)
    e4r = [kref.ref_er30([None if np.isnan(v) else v for v in h4], D) for D in range(n)]
    agree_er = all((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-12 for a, b in zip(e4, e4r))
    ok_er = abs(e1 - 1) < 1e-12 and abs(e2 - e2r) < 1e-15 and e2 < 0.01 and np.isnan(e3) and agree_er
    # SMA20 / UP / DOWN
    up_s = 100 + np.arange(60.0)
    dn_s = 200 - np.arange(60.0)
    fl_s = np.full(60, 100.0)
    u1, d1 = klite.up_down(up_s)
    u2, d2 = klite.up_down(dn_s)
    u3, d3 = klite.up_down(fl_s)
    rs = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 300)))
    rs[rng.random(300) < 0.08] = np.nan
    ur, dr = klite.up_down(rs)
    agree_ud = all((bool(ur[D]), bool(dr[D])) == kref.ref_updown([None if np.isnan(v) else v for v in rs], D) for D in range(300))
    sm = klite.sma20(rs)
    agree_sma = all((np.isnan(sm[d]) and np.isnan(kref.ref_sma20([None if np.isnan(v) else v for v in rs], d)))
                    or abs(sm[d] - kref.ref_sma20([None if np.isnan(v) else v for v in rs], d)) < 1e-9 for d in range(300))
    ok_ud = u1[40] and not d1[40] and d2[40] and not u2[40] and not u3[40] and not d3[40] and agree_ud and agree_sma
    # beta
    bx = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, 80)))
    lx = np.log(bx)
    y15 = np.exp(1.5 * lx + 0.3)
    y5 = np.exp(5 * lx)
    ym = np.exp(-lx)
    b1 = klite.beta_btc(y15, bx)[60]
    b2 = klite.beta_btc(y5, bx)[60]
    b3 = klite.beta_btc(ym, bx)[60]
    yq = y15.copy()
    yq[40:56] = np.nan
    b4 = klite.beta_btc(yq, bx)[60]
    yr = bx * np.exp(rng.normal(0, 0.02, 80))
    yr[rng.random(80) < 0.1] = np.nan
    brk = klite.beta_btc(yr, bx)
    agree_b = all(abs(brk[D] - kref.ref_beta([None if np.isnan(v) else v for v in yr], list(bx), D)) < 1e-9 for D in range(80))
    ok_b = abs(b1 - 1.5) < 1e-9 and b2 == 3.0 and b3 == 0.0 and b4 == 1.0 and agree_b
    # F3
    t0ms = 1_700_000_000_000 - 1_700_000_000_000 % 86400000
    ev = [(t0ms + 8 * 3600000 * i, 1e-4, 8.0) for i in range(30)] + [(t0ms + 10 * 86400000 + 4 * 3600000 * i, 1e-4, 4.0)
                                                                     for i in range(30)]
    ts_, rt_, ih_ = map(np.array, zip(*ev))
    F = klite.f3_funding(ts_, rt_, ih_, 20, t0ms)
    refs = [kref.ref_f3(ev, t0ms + D * 86400000) for D in range(20)]
    agree_f = all((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-15 for a, b in zip(F, refs))
    ok_f = np.isnan(F[0]) and abs(F[5] - 1e-4) < 1e-15 and abs(F[14] - 2e-4) < 1e-15 and agree_f
    # ADX
    nd = 80
    o = 100 + np.arange(nd, dtype=float)
    hh, ll, cc = o + 1.0, o - 0.5, o + 0.8
    a1 = klite.adx14(o, hh, ll, cc)
    ro = 100 * np.exp(np.cumsum(rng.normal(0, 0.03, nd)))
    rh, rl = ro * np.exp(np.abs(rng.normal(0, 0.02, nd))), ro * np.exp(-np.abs(rng.normal(0, 0.02, nd)))
    rc = np.clip(ro * np.exp(rng.normal(0, 0.01, nd)), rl, rh)
    rc[[10, 33]] = np.nan
    a2 = klite.adx14(ro, rh, rl, rc)
    dl_ = [None if np.isnan(rc[i]) else (ro[i], rh[i], rl[i], rc[i]) for i in range(nd)]
    a2r = [kref.ref_adx14(dl_, D) for D in range(nd)]
    agree_a = all((np.isnan(a) and np.isnan(b)) or abs(a - b) < 1e-9 for a, b in zip(a2, a2r))
    ok_a = abs(a1[70] - 100) < 1e-9 and np.isnan(a1[20]) and agree_a
    # phan vi cat ngang
    vals = {("S%d" % i): rng.normal(0, 1, 30) for i in range(25)}
    elig = {k: rng.random(30) < 0.8 for k in vals}
    p = klite.xs_percentile(vals, elig, 100.0 / 3.0)
    pr = [kref.ref_percentile([vals[k][d] for k in vals if elig[k][d]], 100.0 / 3.0) for d in range(30)]
    ok_p = np.allclose(p, pr, atol=1e-12)
    rec("features_ER30_hand_and_ref", ok_er, er_ramp=e1, er_zigzag=e2, er_missing=str(e3), agree_ref=bool(agree_er))
    rec("features_SMA20_UPDOWN_hand_and_ref", ok_ud, agree_ref=bool(agree_ud and agree_sma))
    rec("features_beta_hand_and_ref", ok_b, beta_15=b1, beta_clip5=b2, beta_neg=b3, beta_short=b4, agree_ref=bool(agree_b))
    rec("features_F3_hand_and_ref", ok_f, f3_8h=float(F[5]), f3_4h=float(F[14]), agree_ref=bool(agree_f))
    rec("features_ADX14_hand_and_ref", ok_a, adx_trend=float(a1[70]), agree_ref=bool(agree_a))
    rec("features_xs_percentile_vs_ref", ok_p)


def mini_universe(rng, nday=200, ncoin=4, tpm=2):
    """Universe tong hop trong bo nho: BTCUSDT + alt (beta), qv co soc, funding 8h/4h, tuoi khac nhau."""
    import runner_kaggle as rk
    nmin = nday * 1440
    sb = 0.03 / np.sqrt(1440.0 * tpm)
    zb = rng.standard_normal(nmin * tpm)
    arrs, funds, firsts = {}, {}, {}
    names = ["BTCUSDT"] + ["X%dUSDT" % i for i in range(ncoin - 1)]
    for j, s in enumerate(names):
        if j == 0:
            inc = sb * zb - 0.5 * sb * sb
        else:
            b = 0.6 + 0.4 * j
            sa = 0.05 / np.sqrt(1440.0 * tpm)
            si = np.sqrt(max(sa * sa - (b * sb) ** 2, 1e-12))
            inc = b * sb * zb + si * rng.standard_normal(nmin * tpm) - 0.5 * sa * sa
        shock = rng.random(nmin) < 1.0 / 3000                          # soc gia + khoi luong (COND_A)
        jm = np.nonzero(shock)[0] * tpm
        inc[jm] += np.where(rng.random(jm.size) < 0.5, 1, -1) * 0.04
        p = np.exp(np.log(100.0 * (j + 1)) + np.cumsum(inc)).reshape(nmin, tpm)
        O, H, L, C = p[:, 0], p.max(1), p.min(1), p[:, -1]
        r = np.r_[0, np.diff(np.log(C))]
        QV = 1e5 * (0.5 + (r / (0.05 / np.sqrt(1440))) ** 2)
        QV[shock] *= 200
        valid = np.ones(nmin, bool)
        valid[rng.random(nmin) < 0.002] = False
        arrs[s] = (O, H, L, C, QV, valid)
        ft = rk.DATA_START + np.arange(0, nday * 24, 8 if j % 2 == 0 else 4) * 3600000 + 5
        funds[s] = (ft.astype(np.int64), rng.normal(1e-4, 4e-4, ft.size), np.full(ft.size, 8.0 if j % 2 == 0 else 4.0))
        firsts[s] = rk.DATA_START - (400 if j < 2 else 20) * rk.DAY
    return names, arrs, funds, firsts


def t_masks_neth(rng):
    import runner_kaggle as rk
    nday = 150
    names, arrs, funds, firsts = mini_universe(rng, nday)
    hcs, tiers, qvd = {}, {}, {}
    for j, s in enumerate(names):
        G = klite.prepare_grid(*arrs[s][:4], arrs[s][5], -1)
        hcs[s] = klite.hourly_close(G, nday)
        tiers[s] = np.full(nday, 1 if j < 2 else 2, np.int8)
        qvd[s] = arrs[s][4].reshape(nday, 1440).sum(1)
    thr, er_p1, sg_p1 = rk.cross_section(tiers, hcs, nday)
    mkt = rk.market_context(arrs["BTCUSDT"], -1, nday)
    s = names[1]
    ctx = dict(nday=nday, tier=tiers[s], qvd=qvd[s], fund=funds[s], dl=-1, first_ms=firsts[s], mkt=mkt, mkt_sym="BTCUSDT",
               thr=thr, CP=rk.cond_params(), er_p1=er_p1[s], sig_p1=sg_p1[s])
    res = rk.process_symbol(s, arrs[s], ctx, collect_units=True)
    # dac trung doc lap (kref) theo ngay
    O, H, L, C, QV, valid = arrs[s]
    Cl = [float(C[m]) if valid[m] else None for m in range(C.size)]
    Cb = [float(arrs["BTCUSDT"][3][m]) if arrs["BTCUSDT"][5][m] else None for m in range(C.size)]
    hourly = [kref.ref_hourly_close(Cl, h) for h in range(nday * 24)]
    hourly_b = [kref.ref_hourly_close(Cb, h) for h in range(nday * 24)]
    dcl = [next((v for v in reversed(Cl[d * 1440:(d + 1) * 1440]) if v is not None), None) for d in range(nday)]
    dcb = [next((v for v in reversed(Cb[d * 1440:(d + 1) * 1440]) if v is not None), None) for d in range(nday)]
    ev = list(zip(funds[s][0].tolist(), funds[s][1].tolist(), funds[s][2].tolist()))
    feat_ref = {}
    nmis, nchk, nh_bad = 0, 0, 0
    CL = rk.cells()
    cp = rk.cond_params()
    for (ci, model), u in res["units"].items():
        idx = rng.choice(u["t0"].size, size=min(150, u["t0"].size), replace=False)
        for i in idx:
            D = int(u["D"][i])
            if D not in feat_ref:
                up_, dn_ = kref.ref_updown(dcl, D)
                ub, db = kref.ref_updown(dcb, D)
                feat_ref[D] = dict(er=kref.ref_er30(hourly, D), sig=kref.ref_sigma(dcl, D), up=up_, dn=dn_, up_b=ub, dn_b=db,
                                   f3=kref.ref_f3(ev, rk.DATA_START + D * rk.DAY), beta=kref.ref_beta(dcl, dcb, D),
                                   age=(rk.DATA_START + D * rk.DAY - firsts[s]) // rk.DAY, tier=int(tiers[s][D]),
                                   er_p33=float(thr["er_p33"][D]), sig_p10=float(thr["sig_p10"][D]),
                                   sig_p90=float(thr["sig_p90"][D]))
            f = dict(feat_ref[D])
            t0 = int(u["t0"][i])
            # COND_A / COND_B doc lap
            c1, c61 = Cl[t0 - 1], Cl[t0 - 61]
            q60 = float(QV[t0 - 60:t0].sum())
            qref = float(qvd[s][D - 30:D].sum()) / 30.0 / 24.0
            f["condA"] = bool(c1 is not None and c61 is not None and abs(math.log(c1 / c61)) >= cp["A"]["z"] * f["sig"] / math.sqrt(24)
                              and q60 >= cp["A"]["vmult"] * qref and qref > 0)
            hh = t0 // 60
            lrs = []
            for k_ in range(hh - 24, hh):
                a_, b_ = (hourly_b[k_ - 1] if k_ - 1 >= 0 else None), (hourly_b[k_] if k_ >= 0 else None)
                if a_ is not None and b_ is not None:
                    lrs.append(math.log(b_ / a_) ** 2)
            sgb = kref.ref_sigma(dcb, D)
            f["condB"] = bool(len(lrs) >= 20 and sgb == sgb and sgb > 0 and math.sqrt(sum(lrs)) / sgb >= cp["B"]["ratio"])
            want = kref.ref_masks(f, int(u["side"][i]), s, "BTCUSDT")
            got = set(CL[cid]["set"] for cid, m_ in u["memb"].items() if m_[i] and CL[cid]["set"] is not None)
            ck = rk.CK_ALL[ci]
            want = set(w for w in want if (w in ("ER_LOW", "IDEAL_N", "COND_A", "COND_B") and ck in rk.S_CK)
                       or (w in ("TREND_BUY", "TREND_SELL") and ck in rk.D_CK))
            nchk += 1
            nmis += int(want != got)
            if u["ok"][i]:
                R = u["R"]
                fi, xi = int(R["f"][i]), int(R["x"][i])
                bf = next(v for v in reversed(Cb[:fi + 1]) if v is not None)
                bx_ = next(v for v in reversed(Cb[:xi + 1]) if v is not None)
                exp = R["net"][i] - int(u["side"][i]) * f["beta"] * (bx_ - bf) / bf * 1e4
                nh_bad += int(abs(exp - u["neth"][i]) > 1e-9)
    sets_seen = {}
    for (ci, model), u in res["units"].items():
        for cid, m_ in u["memb"].items():
            if CL[cid]["set"]:
                sets_seen[CL[cid]["set"]] = sets_seen.get(CL[cid]["set"], 0) + int(m_.sum())
    rec("masks_runner_vs_kref", nmis == 0 and nchk > 1000 and all(sets_seen.get(k, 0) > 0 for k in
                                                                  ("ER_LOW", "IDEAL_N", "COND_A", "COND_B", "TREND_BUY", "TREND_SELL")),
        n_checked=nchk, n_mismatch=nmis, units_per_set=sets_seen)
    rec("neth_identity_vs_independent", nh_bad == 0, n_bad=nh_bad)


def t_runner_beta(rng, outdir):
    """Lake GBM drift + beta biet truoc: net_h (gross_h) cua tap TREND ~ dap an khong drift (kref, MC doc lap)."""
    import runner_kaggle as rk
    root = os.path.join(outdir, "_fake_lake_b")
    ro = os.path.join(outdir, "_fake_run_b")
    for p in (root, ro):
        shutil.rmtree(p, ignore_errors=True)
    meta = synth.write_fake_lake(root, seed=2026112032, tpm=5, variant="beta")
    os.makedirs(ro, exist_ok=True)
    os.environ.update(GRIDV2_INPUT=root, GRIDV2_OUT=ro, GRIDV2_SHARD="0/1")
    v, man = rk.run(test_overrides=dict(registry=meta["rows"], v4_syms=1))
    rec("runner_beta_lake_V0_V6", v["all_pass"], V4=[(c["n_checked"], c["n_diff"]) for c in v["V4"]["checks"]],
        V5=[c["ok"] for c in v["V5"]["checks"]], V6=v["V6"]["ok"], seconds=man["seconds"])
    res, TT = rk.merge(os.path.join(ro, "merged"), [ro], nboot=1000, allow_test=True)
    dg = json.load(open(os.path.join(ro, "merged", "diag.json")))
    rec("merge_diag_tables_11_12_13", len(dg["tier_split"]) > 0 and len(dg["excl_rate"]) == 32 * 4 and len(dg["hedge_fee"]) == 6 * 4
        and all(h["M_neth_minus_hedge_fee"] <= h["M_neth"] + 1e-12 for h in dg["hedge_fee"])
        and any(h["M_neth_minus_hedge_fee"] < h["M_neth"] for h in dg["hedge_fee"]),
        n_tier_rows=len(dg["tier_split"]), n_excl=len(dg["excl_rate"]), hedge_fee=dg["hedge_fee"][:2])
    A = TT["agg"]
    nday = (rk.SEAL - rk.DATA_START) // rk.DAY
    d0 = (rk.STUDY_START - rk.DATA_START) // rk.DAY
    cache = {}
    for cell in rk.cells():
        if cell["grp"] != "D":
            continue
        for model in ("OPT", "PESS"):
            sub = A[(A.cell == cell["id"]) & (A.model == model)]
            S = np.zeros((nday - d0, 2))
            N = np.zeros((nday - d0, 2))
            g = sub.groupby("day")[["grossh", "gross", "fill"]].sum()
            S[g.index - d0, 0], S[g.index - d0, 1] = g.grossh.to_numpy(), g.gross.to_numpy()
            N[g.index - d0, 0] = N[g.index - d0, 1] = g.fill.to_numpy()
            st = stats.cell_stats(S, N, 0.0, 9, B=1000)
            key = (cell["c"], cell["k"], model)
            if key not in cache:
                cache[key] = gbm_answer(np.random.default_rng(rng.integers(1 << 62)), cell["c"], cell["k"], 0.045, model, npath=8000,
                                        tpm=5)
            m_ans, se_ans, n_ans = cache[key]
            z = (st["M"][0] - m_ans) / math.sqrt(st["SE"][0] ** 2 + se_ans ** 2)
            rec("runner_beta_%s_%s" % (cell["name"], model), abs(z) <= 3 and n_ans >= 3000, M_grossh=float(st["M"][0]),
                se=float(st["SE"][0]), M_gross_raw=float(st["M"][1]), answer_nodrift=m_ans, se_answer=se_ans, z=float(z),
                n_units=int(N[:, 0].sum()))
    shutil.rmtree(root, ignore_errors=True)


def _fake_reduced(root, rng, mu, nper, muh=None, manifest=None):
    """Bang reduced gia cho merge: mu (2 nua x 32) bps/don vi net, muh (tuy chon) bps/don vi net_h, nper (2 nua x 32) don vi/ngay;
    6 symbol chia deu (shalf). manifest (dict) -> ghi them manifest.json + validate.json (all_pass True)."""
    import runner_kaggle as rk
    import pandas as pd
    nday = (rk.SEAL - rk.DATA_START) // rk.DAY
    d0 = (rk.STUDY_START - rk.DATA_START) // rk.DAY
    dB = (rk.HALF_B - rk.DATA_START) // rk.DAY
    rows, sh = [], []
    for model in ("OPT", "PESS"):
        for hv, (lo, hi) in enumerate(((d0, dB), (dB, nday))):
            Dn = hi - lo
            for c in range(32):
                n = np.full(Dn, float(nper[hv][c]))
                if nper[hv][c] <= 0:
                    continue
                if nper[hv][c] < 1:                     # it don vi: chi mot so ngay co 1 don vi
                    n = (rng.random(Dn) < nper[hv][c]).astype(float)
                z = rng.normal(0, 1, Dn)
                net = mu[hv][c] * n + 40.0 * np.sqrt(n) * z
                neth = net + ((muh[hv][c] - mu[hv][c]) * n if muh is not None else 0.0)
                df = pd.DataFrame({k: np.zeros(Dn) for k in rk.SUM_COLS})
                df["place"], df["fill"], df["net"], df["neth"], df["gross"], df["grossh"] = n, n, net, neth, net + 4 * n, neth + 4 * n
                df["day"], df["cell"], df["model"] = np.arange(lo, hi), c, model
                rows.append(df[df.place > 0])
                for k in range(6):
                    sh.append(dict(sym="S%d" % k, cell=c, model=model, half=hv, net=net.sum() / 6, neth=neth.sum() / 6,
                                   fill=n.sum() / 6))
    os.makedirs(os.path.join(root, "reduced"), exist_ok=True)
    pd.concat(rows, ignore_index=True).to_parquet(os.path.join(root, "reduced", "agg.parquet"), index=False)
    pd.DataFrame(sh).to_parquet(os.path.join(root, "reduced", "shalf.parquet"), index=False)
    if manifest is not None:
        json.dump(manifest, open(os.path.join(root, "manifest.json"), "w"))
        json.dump(dict(all_pass=True), open(os.path.join(root, "validate.json"), "w"))


def t_merge_rules(rng, outdir):
    """R3-12: merge / luat L-A..L-D / can tren 95 % / o NaN + INSUFFICIENT voi ALPHA_FWER 0.04, ALPHA_UPPER 0.05."""
    import runner_kaggle as rk
    base = os.path.join(outdir, "_merge_t")
    shutil.rmtree(base, ignore_errors=True)
    out = {}
    neg = [[-25.0] * 32, [-25.0] * 32]
    many = [[60.0] * 32, [60.0] * 32]
    scen = {}
    scen["LA"] = (neg, many)
    m2 = [list(many[0]), list(many[1])]
    m2[1][5] = 0.0                                          # o 5 khong co don vi nua B (NaN)
    scen["nan_cell"] = (neg, m2)
    m3 = [list(many[0]), list(many[1])]
    m3[1][9] = 0.2                                          # o 9 ~146 don vi nua B < 200
    scen["insufficient_cell"] = (neg, m3)
    mu4 = [list(neg[0]), list(neg[1])]
    mu4[0][7] = mu4[1][7] = 30.0                            # o 7 that su > san o ca 2 nua
    mu4[0][9] = mu4[1][9] = 400.0                           # o 9 lon nhung INSUFFICIENT -> khong PASS
    scen["pass_cell"] = (mu4, m3)
    for name, (mu, nper) in scen.items():
        d = os.path.join(base, name)
        _fake_reduced(d, np.random.default_rng(rng.integers(1 << 62)), mu, nper)
        res, _ = rk.merge(os.path.join(d, "merged"), [d], nboot=500, allow_test=True)
        out[name] = res
    cl = [c["name"] for c in rk.cells()]
    r = out["LA"]
    ok_la = r["rule_core"] == "L-A" and r["rule"] == "TEST_ONLY:L-A" and r["TEST_ONLY"] is True and r["models"]["OPT"]["strong_close_all_upper_lt_floor_B"]
    # can tren dung 95 % (ALPHA_UPPER) - tinh lai doc lap tu stats
    d = os.path.join(base, "LA")
    T_ = rk.load_reduced([d])
    A = T_["agg"]
    Am = A[A.model == "OPT"]
    nday = (rk.SEAL - rk.DATA_START) // rk.DAY
    dB = (rk.HALF_B - rk.DATA_START) // rk.DAY
    S, N = rk.day_matrix(Am, dB, nday, "net", 32), rk.day_matrix(Am, dB, nday, "fill", 32)
    st = stats.cell_stats(S, N, 4.0, rk.SEED_BOOT + 1, B=500, alpha=0.04, alpha_upper=0.05)
    st99 = stats.cell_stats(S, N, 4.0, rk.SEED_BOOT + 1, B=500, alpha=0.04, alpha_upper=0.01)
    up_m = np.array(r["models"]["OPT"]["B"]["upper_sim95"], float)
    ok_up = (np.allclose(up_m, st["upper_sim95"]) and st99["c_upper"] > st["c_upper"] and r["alpha_upper"] == 0.05
             and r["alpha_fwer"] == 0.04 and np.allclose(r["models"]["OPT"]["B"]["p_rw"], st["p_rw"]))
    rec("merge_rule_LA_upper95_alpha4", ok_la and ok_up, rule=r["rule"], c_upper_95=st["c_upper"], c_upper_99=st99["c_upper"],
        max_upper=float(np.max(up_m)))
    r = out["nan_cell"]
    rec("merge_nan_cell_blocks_LA", r["rule_core"] == "L-B" and cl[5] in r["models"]["OPT"]["INSUFFICIENT_B"]
        and not r["models"]["OPT"]["strong_close_all_upper_lt_floor_B"], rule=r["rule"],
        insufficient=r["models"]["OPT"]["INSUFFICIENT_B"])
    r = out["insufficient_cell"]
    rec("merge_insufficient_cell_blocks_LA", r["rule_core"] == "L-B" and r["models"]["OPT"]["INSUFFICIENT_B"] == [cl[9]],
        rule=r["rule"], insufficient=r["models"]["OPT"]["INSUFFICIENT_B"],
        n_units_B=r["models"]["OPT"]["B"]["n_units"][9])
    r = out["pass_cell"]
    pas = r["models"]["OPT"]["PASS"]
    rec("merge_pass_cell_and_insufficient_never_pass", r["rule_core"] == "L-D" and pas[7] and not pas[9] and sum(pas) == 1
        and r["models"]["PESS"]["PASS"][7], rule=r["rule"], n_pass=int(sum(pas)), p_rw_7=r["models"]["OPT"]["B"]["p_rw"][7],
        p_marg_A_7=r["models"]["OPT"]["A"]["p_marg"][7])
    shutil.rmtree(base, ignore_errors=True)


def t_r4_stats(rng):
    """R4-1 / R4-2: o INSUFFICIENT loai khoi max (p_RW o khac KHONG doi); dieu kien (ii) so khoi; SE* = 0 -> t* = 0."""
    D = 731
    Z, N = _null_panel(rng, D, 31, True)
    sdc = 30.0 / np.sqrt(N.sum(0))
    S = (4.0 + 3.5 * sdc)[None, :] * N + 30.0 * Z * np.sqrt(N)
    # o thua: 300 don vi trong 3 ngay (12 / 3 khoi khong chong lan < 13) -> INSUFFICIENT (ii); gia tri cuc doan
    Ns = np.zeros((D, 1)); Ss = np.zeros((D, 1))
    Ns[[5, 300, 600], 0] = 100.0
    Ss[[5, 300, 600], 0] = np.array([5000.0, -3000.0, 100.0])
    r31 = stats.cell_stats(S, N, 4.0, 77, B=500)
    r32 = stats.cell_stats(np.hstack([S, Ss]), np.hstack([N, Ns]), 4.0, 77, B=500)
    same = np.array_equal(r31["p_rw"], r32["p_rw"][:31]) and r31["c_upper"] == r32["c_upper"] and r31["crit_rw"] == r32["crit_rw"]
    rec("stats_insufficient_excluded_from_max", same and bool(r32["insufficient"][31]) and r32["p_rw"][31] == 1.0
        and np.isnan(r32["upper_sim95"][31]), reason=r32["insufficient_reason"][31], power_31=float(np.mean(r31["rw_reject"])),
        power_31_with_sparse=float(np.mean(r32["rw_reject"][:31])))
    # (ii): 12 khoi -> INSUFFICIENT, 13 khoi -> du; nua A 914 ngay: 46 khoi -> can 16
    out = {}
    for D_, nbk in ((731, 12), (731, 13), (914, 15), (914, 16)):
        Nn = np.zeros((D_, 1)); Sn = np.zeros((D_, 1))
        days = np.arange(nbk) * 20 * 2
        Nn[days, 0] = 30.0
        Sn[days, 0] = rng.normal(0, 30, nbk) * np.sqrt(30.0)
        r = stats.cell_stats(Sn, Nn, 0.0, 3, B=200)
        out["%d_%d" % (D_, nbk)] = (bool(r["insufficient"][0]), r["insufficient_reason"][0], int(r["min_blocks_with_units"]))
    ok2 = (out["731_12"][0] and out["731_12"][1] == "ii" and not out["731_13"][0] and out["731_13"][2] == 13
           and out["914_15"][0] and not out["914_16"][0] and out["914_16"][2] == 16)
    rec("stats_insufficient_condition_ii_blocks", ok2, cases=out)
    # SE* = 0 / replicate khong don vi -> t* = 0
    Ms = np.array([[1.0, np.nan, 2.0], [3.0, 1.0, 2.5]])
    SEs = np.array([[0.0, np.nan, 0.5], [1.0, 0.5, 0.0]])
    tb = stats.tstar(Ms, np.array([1.0, 1.0, 2.0]), SEs)
    exp = np.array([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]])
    # o co 12 khoi gia tri a va 1 khoi gia tri b: replicate khong chon khoi b co SE* = 0 -> t* = 0 (khong +-inf)
    Nq = np.zeros((731, 1)); Sq = np.zeros((731, 1))
    dq = np.arange(13) * 20 * 2
    Nq[dq, 0] = 20.0
    Sq[dq, 0] = 20.0 * np.r_[np.full(12, 5.0), [50.0]]
    rq = stats.cell_stats(Sq, Nq, 0.0, 9, B=300)
    rec("stats_se_star_zero_tstar_zero", np.array_equal(tb, exp) and np.isfinite(rq["p_marg"][0]) and np.isfinite(rq["c_upper"]),
        tstar=tb.tolist(), p_marg=float(rq["p_marg"][0]))


def t_r4_merge(rng, outdir):
    """R4-3 guard shard + sha; R4-4 TEST_ONLY; R4-5 co BETA."""
    import runner_kaggle as rk
    base = os.path.join(outdir, "_merge_r4")
    shutil.rmtree(base, ignore_errors=True)
    exp_sha = {f: rk.sha256_file(os.path.join(HERE, f)) for f in rk.SHA_FILES}
    shp = os.path.join(base, "EXPECTED_SHA.txt")
    os.makedirs(base, exist_ok=True)
    with open(shp, "w") as fh:
        for f in rk.SHA_FILES:
            fh.write("%s  %s\n" % (exp_sha[f], f))
    man0 = dict(prereg_constants=True, alpha_fwer=rk.ALPHA_FWER, alpha_upper=rk.ALPHA_UPPER, min_units=rk.MIN_UNITS,
                cond=json.loads(json.dumps(rk.COND_PREREG)), mkt_sym=rk.MARKET_SYM, code=dict(exp_sha))
    neg = [[-25.0] * 32, [-25.0] * 32]
    per = [[12.0] * 32, [12.0] * 32]
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
            return False, str(e)[:120]
    ok_v, r_v = tries(dirs)
    cases = dict(valid=ok_v and r_v["TEST_ONLY"] is False and r_v["rule"] == r_v["rule_core"] == "L-A")
    cases["missing_shard"] = not tries(dirs[:4])[0]
    cases["duplicate_dir"] = not tries(dirs[:4] + [dirs[0]])[0]
    dup = os.path.join(base, "dup")
    shutil.copytree(dirs[1], dup)
    cases["duplicate_index"] = not tries(dirs[:4] + [dup])[0]
    cases["no_expected_sha"] = not tries(dirs, es=None)[0]
    bad = dict(exp_sha)
    bad["stats.py"] = "0" * 64
    cases["sha_mismatch"] = not tries(dirs, es=bad)[0]
    for key, val in (("cond", {"A": dict(z=2.5, vmult=0.5), "B": dict(ratio=1.5)}), ("mkt_sym", "AAAUSDT"),
                     ("prereg_constants", False)):
        mf = os.path.join(dirs[2], "manifest.json")
        m0 = json.load(open(mf))
        json.dump(dict(m0, **{key: val}), open(mf, "w"))
        cases["bad_" + key] = not tries(dirs)[0]
        json.dump(m0, open(mf, "w"))
    ok_t, r_t = tries(dirs[:2], es=None, allow_test=True, nboot=500)
    cases["allow_test_marked"] = ok_t and r_t["TEST_ONLY"] is True and r_t["rule"].startswith("TEST_ONLY:")
    rf = json.load(open(os.path.join(base, "m", "result.json")))
    cases["result_json_first_key_TEST_ONLY"] = list(rf.keys())[0] == "TEST_ONLY" and rf["TEST_ONLY"] is True
    rec("merge_shard_guards_sha_TEST_ONLY", all(cases.values()), **cases)
    # R4-5: co BETA
    mu = [[-25.0] * 32, [-25.0] * 32]
    muh = [[-25.0] * 32, [-25.0] * 32]
    for hv in (0, 1):
        mu[hv][26], muh[hv][26] = 30.0, -10.0           # net tho > 4, net_h <= 4 -> BETA
        mu[hv][27], muh[hv][27] = 30.0, 30.0            # net_h > 4 o B ...
        mu[hv][28], muh[hv][28] = 2.0, -5.0             # net tho <= 4 -> khong BETA
    muh[0][27] = -20.0                                  # ... nhung nua A net_h am -> khong PASS; luat cu se gan BETA
    d = os.path.join(base, "beta")
    _fake_reduced(d, np.random.default_rng(rng.integers(1 << 62)), mu, [[60.0] * 32, [60.0] * 32], muh=muh)
    r, _ = rk.merge(os.path.join(d, "m"), [d], nboot=500, allow_test=True)
    bf = r["models"]["OPT"]["BETA_flag"]
    rec("merge_beta_flag_R4_5", bf[26] and not bf[27] and not bf[28] and not r["models"]["OPT"]["PASS"][27]
        and len(r["models"]["OPT"]["BETA_detail"]) == 6, beta=[bf[26], bf[27], bf[28]],
        detail=r["models"]["OPT"]["BETA_detail"][:3])
    shutil.rmtree(base, ignore_errors=True)


def _add_premonths(root):
    """Ghi kline1m-2021-01..03 (1 row group AAAUSDT) vao lake gia - thang pass1 phai bo qua (R5-4). Tra {(y, mo): so dong}."""
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


def t_r5_v0():
    """R5-1: V0a / V0b (pure) - dung, lech 1 dong, bo qua sai file, ky vong that."""
    import runner_kaggle as rk
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
    a, b, _ = rk.v0_eval(meta, opened + [(2021, 3)], rows, reg)
    c["skipped_file_opened_fail"] = not b
    a, b, _ = rk.v0_eval(meta, opened, rows, reg, [[2021, 1], [2021, 2]])
    c["expect_mismatch_fail"] = not b
    rec("V0b_eval_pure", all(c.values()), **c)


def t_r5_v4(rng):
    """R5-2: v4_pick (90 ngay, khoang tc), v4_check tren symbol niem yet muon; rac truoc tc -> n_diff != 0 -> FAIL."""
    import runner_kaggle as rk
    nday = 150
    names, arrs, funds, firsts = mini_universe(rng, nday)
    hcs, tiers, qvd = {}, {}, {}
    late = names[2]
    O, H, L, C, QV, valid = arrs[late]
    valid = valid.copy()
    valid[:40 * 1440] = False                              # niem yet ngay 40 (truoc day: tc co the roi truoc -> n_checked 0)
    arrs[late] = (O, H, L, C, QV, valid)
    firsts[late] = rk.DATA_START + 40 * rk.DAY
    for j, s_ in enumerate(names):
        G = klite.prepare_grid(*arrs[s_][:4], arrs[s_][5], -1)
        hcs[s_] = klite.hourly_close(G, nday)
        tiers[s_] = np.full(nday, 1 if j < 2 else 2, np.int8)
        qvd[s_] = arrs[s_][4].reshape(nday, 1440).sum(1)
    tiers[late][:41] = 0
    thr, er_p1, sg_p1 = rk.cross_section(tiers, hcs, nday)
    mkt = rk.market_context(arrs["BTCUSDT"], -1, nday)
    ctx = dict(nday=nday, tier=tiers[late], qvd=qvd[late], fund=funds[late], dl=-1, first_ms=firsts[late], mkt=mkt,
               mkt_sym="BTCUSDT", thr=thr, CP=rk.cond_params(), er_p1=None, sig_p1=None)
    okp, lo, hi, why = rk.v4_pick(valid)
    d0m = (rk.STUDY_START - rk.DATA_START) // rk.MIN
    c = dict(pick_late=okp and lo == max(40 * 1440 + 45 * 1440, d0m + 45 * 1440) and hi == int(np.nonzero(valid)[0][-1]) - 15 * 1440)
    vs = np.zeros(nday * 1440, bool)
    vs[50 * 1440:130 * 1440] = True                        # 80 ngay < 90 -> bo qua
    ok_s, _, _, why_s = rk.v4_pick(vs)
    c["short_skipped"] = (not ok_s) and why_s.startswith("span")
    vo = np.ones(nday * 1440, bool)
    ok_o, lo_o, _, _ = rk.v4_pick(vo)
    c["old_symbol_lo_after_study"] = ok_o and lo_o == d0m + 45 * 1440
    r_ok = rk.v4_check(late, arrs[late], ctx, np.random.default_rng(11), tc_range=(lo, hi))
    r_old = rk.v4_check(late, arrs[late], ctx, np.random.default_rng(11), tc_range=(20 * 1440, 20 * 1440))
    r_junk = rk.v4_check(late, arrs[late], ctx, np.random.default_rng(11), tc_range=(lo, hi), junk_lead_min=3 * 1440)
    c["late_symbol_pass"] = r_ok["ok"] and r_ok["n_checked"] > 0 and r_ok["n_diff"] == 0 and lo <= r_ok["tc_min"] <= hi
    c["tc_before_listing_fail"] = (not r_old["ok"]) and r_old["n_checked"] == 0
    c["junk_before_tc_fail"] = (not r_junk["ok"]) and r_junk["n_diff"] > 0
    rec("V4_pick_and_check_R5", all(c.values()), **c, n_checked=r_ok["n_checked"], n_diff_junk=r_junk["n_diff"], why_short=why_s)


def t_r5_v5():
    """R5-6: v5_select tat dinh, phu du (c,k) / side / model, doi model-side khi thieu, sang symbol ke tiep; v5_eval FAIL khi thieu."""
    import runner_kaggle as rk

    def fake_res(avail, seed):
        r = np.random.default_rng(seed)
        units = {}
        for (ci, model), (nb, ns) in avail.items():
            side = np.r_[np.ones(nb + 5, np.int8), -np.ones(ns + 5, np.int8)]
            ok = np.r_[np.ones(nb, bool), np.zeros(5, bool), np.ones(ns, bool), np.zeros(5, bool)]
            units[(ci, model)] = dict(ok=ok, side=side)
        return dict(units=units)
    full = {(ci, m): (3, 3) for ci in range(6) for m in ("OPT", "PESS")}
    resA = fake_res({k: v for k, v in full.items() if k[0] != 5}, 1)          # symbol A: khong co don vi khop o ci 5
    resA["units"][(4, "OPT")] = dict(ok=np.array([True, False]), side=np.array([-1, 1], np.int8))  # ci 4 OPT chi co SELL
    resB = fake_res(full, 2)
    c = {}
    cnt = {"OPT": 0, "PESS": 0, 1: 0, -1: 0}
    pa = rk.v5_select(resA, set(range(6)), cnt, np.random.default_rng(7), 12)
    cnt2 = {"OPT": 0, "PESS": 0, 1: 0, -1: 0}
    pa2 = rk.v5_select(resA, set(range(6)), cnt2, np.random.default_rng(7), 12)
    c["deterministic"] = pa == pa2
    c["symA_covers_0_4"] = sorted(k[0] for k, _ in pa) == [0, 1, 2, 3, 4]
    c["picked_units_filled"] = all(bool(resA["units"][k]["ok"][i]) for k, i in pa)
    need = set(range(6)) - {k[0] for k, _ in pa}
    pb = rk.v5_select(resB, need, cnt, np.random.default_rng(8), 12 - len(pa))
    c["next_symbol_fills_ci5"] = [k[0] for k, _ in pb] == [5]
    allp = [(k, int(resA["units"][k]["side"][i])) for k, i in pa] + [(k, int(resB["units"][k]["side"][i])) for k, i in pb]
    c["both_models_sides"] = {k[1] for k, _ in allp} == {"OPT", "PESS"} and {sd for _, sd in allp} == {1, -1}
    c["room_respected"] = len(rk.v5_select(resB, set(range(6)), dict(cnt), np.random.default_rng(9), 2)) == 2

    def chk(ck, side, model, ok=True):
        return dict(sym="X", t0=1, ck=ck, c=rk.CK_ALL[ck][0], k=rk.CK_ALL[ck][1], side=side, model=model, ok=ok)
    good = [chk(i, 1 if i % 2 else -1, "OPT" if i % 2 else "PESS") for i in range(6)] + [chk(0, 1, "OPT"), chk(1, -1, "PESS")]
    c["eval_good"] = rk.v5_eval(good)["ok"]
    c["eval_missing_ck_fail"] = (not rk.v5_eval([x for x in good if x["ck"] != 5] + [chk(2, 1, "OPT")])["ok"]
                                 and rk.v5_eval([x for x in good if x["ck"] != 5] + [chk(2, 1, "OPT")])["missing_ck"] == [5])
    c["eval_one_side_fail"] = not rk.v5_eval([chk(i % 6, 1, "OPT" if i % 2 else "PESS") for i in range(8)])["ok"]
    c["eval_too_few_fail"] = not rk.v5_eval(good[:6])["ok"]
    c["eval_mismatch_fail"] = not rk.v5_eval(good[:7] + [chk(1, -1, "PESS", ok=False)])["ok"]
    rec("V5_select_eval_R5_6", all(c.values()), **c)


def t_guards(rng, outdir):
    """R3-1 env cam; R3-7 allowlist; R3-6 V2 nguong; R3-10 V6; R3-5 s_hat thieu."""
    import runner_kaggle as rk
    import pandas as pd
    # env
    res = []
    for k in rk.FORBIDDEN_ENV:
        os.environ[k] = "x"
        try:
            rk.check_env()
            res.append(False)
        except RuntimeError:
            res.append(True)
        try:
            rk.merge(os.path.join(outdir, "_nomerge"), [], allow_test=True)
            res.append(False)
        except RuntimeError:
            res.append(True)
        os.environ.pop(k)
    rk.check_env()
    rec("guard_forbidden_env_aborts", all(res), n=len(res), consts=[rk.ALPHA_FWER, rk.ALPHA_UPPER, rk.MIN_UNITS])
    # allowlist
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
    build(extra=["datasets/u/vz-kline1m-2022/kline1m-2021-07.parquet"]); cases["year_mismatch"] = not ok_run()
    build(drop=["gridp-lifecycle"]); cases["missing_slug"] = not ok_run()
    build(extra=["datasets/u/gridp-lifecycle/sub/lifecycle.parquet"]); cases["two_lifecycle"] = not ok_run()
    build(extra=["datasets/u/gridp-t1-funding/other.parquet"]); cases["stray_parquet"] = not ok_run()
    build(extra=["notes.txt"]); cases["file_outside_slug"] = not ok_run()
    shutil.rmtree(root, ignore_errors=True)
    rec("guard_dataset_allowlist", all(cases.values()), **cases)
    # V2
    a = rk.v2_eval({2022: [10, 10000], 2023: [0, 5000]})
    b = rk.v2_eval({2022: [11, 10000], 2023: [0, 5000]})
    c = rk.v2_eval({2021: [0, 100], 2024: [3, 1000]})
    rec("guard_V2_threshold_0p1pct", a[0] and not b[0] and not c[0], ok_10_per_10k=a[0], ok_11_per_10k=b[0], ok_3_per_1k=c[0])
    # V6

    def fr(rate, ih, inferred=False):
        f = pd.DataFrame({"rate": rate, "interval_h": ih})
        f.attrs["inferred"] = inferred
        return f
    r1 = rng.normal(1e-4, 5e-5, 1000)
    v_ok = rk.v6_eval({2022: fr(r1, np.full(1000, 8.0)), 2023: fr(r1, np.r_[np.full(500, 8.0), np.full(500, 4.0)])})[0]
    v_pct = rk.v6_eval({2022: fr(r1 * 100, np.full(1000, 8.0))})[0]
    v_tiny = rk.v6_eval({2022: fr(r1 * 1e-3, np.full(1000, 8.0))})[0]
    v_ih = rk.v6_eval({2022: fr(r1, np.r_[np.full(999, 8.0), [3.0]])})[0]
    v_inf = rk.v6_eval({2022: fr(r1, np.r_[np.full(995, 8.0), np.full(5, 3.0)], inferred=True)})[0]
    rec("guard_V6_funding_units", v_ok and not v_pct and not v_tiny and not v_ih and v_inf, normal=v_ok, percent_units=v_pct,
        too_small=v_tiny, bad_interval=v_ih, inferred_tolerant=v_inf)
    # s_hat
    sp = np.full(20, np.nan)
    sp[1] = 0.001
    sp[12] = 0.003
    sh = rk.shat_exante(sp)
    exp = np.full(20, np.nan)
    exp[2:9] = 0.001                             # D-1..D-7 chua ngay 1
    exp[13:20] = 0.003
    same = np.all((np.isnan(sh) & np.isnan(exp)) | (np.abs(sh - exp) < 1e-15))
    filled = rk.shat_fill(sh[[0, 5, 10, 10, 10]], np.array([1, 3, 1, 2, 3]))
    exp_f = np.array([4e-4, 0.001, 4e-4, 10e-4, 20e-4])
    rec("guard_shat_missing_ffill7_then_2x_floor", bool(same and np.allclose(filled, exp_f) and np.all(filled > 0)),
        shat=[None if np.isnan(x) else float(x) for x in sh], filled=filled.tolist())


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
    t_e2a(rng)
    t_e2b_lattice(rng)
    t_e2b_drift(rng)
    t_e2b_indep(rng)
    t_bracket(rng)
    t_e2c(rng)
    t_edges()
    t_ref_compare(rng, outdir)
    t_lookahead(rng)
    t_sigma_T()
    t_tiers()
    t_stats(rng)
    t_merge_rules(rng, outdir)
    t_r4_stats(rng)
    t_r4_merge(rng, outdir)
    t_r5_v0()
    t_r5_v4(rng)
    t_r5_v5()
    t_guards(rng, outdir)
    t_features(rng)
    t_masks_neth(rng)
    if "--no-runner" not in sys.argv:
        t_runner(rng, outdir)
        t_runner_beta(rng, outdir)
    allok = all(r["ok"] for r in RES)
    json.dump(dict(all_pass=allok, n=len(RES), n_fail=sum(not r["ok"] for r in RES), seconds=round(time.time() - t, 1), seed=SEED,
                   tests=RES), open(os.path.join(outdir, "test_results.json"), "w"), indent=1, default=float)
    log.info("ALL_PASS=%s (%d test, %d fail) %.0fs", allok, len(RES), sum(not r["ok"] for r in RES), time.time() - t)


if __name__ == "__main__":
    main()
