"""power.py (v4, R3-1 + R4-2) - CONG SUAT 32 o + do FWER Romano-Wolf STUDENTIZED (stats.cell_stats, alpha 4 %) tren null TONG HOP
voi dung bo 32 o. Khong du lieu that.
Moi lan lap = 1 panel tong hop "base" (BTC + 5 alt, 731 ngay nua B + warm-up) chay QUA DUNG process_symbol cua runner (cung mat
na 32 o, cung feature), CA K_OPT va K_PESS. Null = martingale (khong drift); M that cua tung o (moi mo hinh) uoc bang gop moi
lan lap, roi dich ve san (H0 bien) de do FWER: (a) dung luat prereg (o < 200 don vi = INSUFFICIENT), (b) khong nguong (min 0).
Cong suat: SE quy doi ve so coin that theo tung o; MDE voi nguong chuan (z 1-0,04/32) va nguong max-t studentized do duoc.
Chay: python3 power.py OUTDIR [R] [NPROC]
"""
import os
import sys
import json
import math
import time
import logging
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import klite  # noqa: E402
import stats  # noqa: E402
import runner_kaggle as rk  # noqa: E402

log = logging.getLogger("power")
SEED = 2026112070
WARM = 45
NDAY_B = 731
TPM = 2
# panel: (ten, tier, sigma ngay, beta, tuoi ngay luc bat dau nua B)
PANEL = [("BTCUSDT", 1, 0.030, None, 2000), ("A1USDT", 1, 0.035, 0.9, 2000), ("A2USDT", 2, 0.050, 1.1, 2000),
         ("A3USDT", 2, 0.050, 1.2, 20), ("A4USDT", 3, 0.065, 1.3, 2000), ("A5USDT", 3, 0.065, 1.0, 40)]
NREAL = {"A": {1: 10, 2: 50, 3: 130}, "B": {1: 10, 2: 50, 3: 420}}
NDAY = {"A": 914, "B": 731}
ALPHA = stats.ALPHA_FWER                                  # 0.04 co dinh (R3-1)
ALPHAS_INFO = [0.05, 0.04, 0.03, 0.02, 0.01]              # chi de tham khao (khong dung de chon)
MODELS = ("OPT", "PESS")
B_FWER = 1000
SPARSE_CELL = 20                                          # S_COND_A_c0.2_k2 (o thua nhat tren du lieu that, A1 G1)
EFFECT_SD = 3.5


def sparsify(Sc, Nc, nblk, block=20, min_units=200):
    """Giu 1 ngay (nhieu don vi nhat) trong moi khoi cua nblk khoi khong chong lan cach deu; nhan S, N cung he so de >= 200 don vi
    (o thua dung (ii) ngay tren / duoi nguong ceil(nb/3), qua (i))."""
    D = Sc.size
    nb = -(-D // block)
    S2, N2 = np.zeros(D), np.zeros(D)
    for b in np.unique(np.round(np.linspace(0, nb - 1, nblk)).astype(int)):
        lo, hi = b * block, min(b * block + block, D)
        k = lo + int(np.argmax(Nc[lo:hi]))
        S2[k], N2[k] = Sc[k], Nc[k]
    f = max(1.0, math.ceil(min_units / max(N2.sum(), 1.0)))
    return S2 * f, N2 * f
Z80 = 0.8416212335729143


def norm_ppf(p):
    lo, hi = -10.0, 10.0
    for _ in range(100):
        m = 0.5 * (lo + hi)
        if 1 - stats.norm_sf(m) < p:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def make_panel(rng):
    nday = WARM + NDAY_B + 4
    nmin = nday * 1440
    sb = PANEL[0][2] / math.sqrt(1440.0 * TPM)
    zb = rng.standard_normal(nmin * TPM)
    arrs, funds, firsts, tiers = {}, {}, {}, {}
    for j, (s, tr, sg, b, age0) in enumerate(PANEL):
        sa = sg / math.sqrt(1440.0 * TPM)
        if b is None:
            inc = sb * zb - 0.5 * sb * sb
        else:
            si = math.sqrt(max(sa * sa - (b * sb) ** 2, 1e-14))
            inc = b * sb * zb + si * rng.standard_normal(nmin * TPM) - 0.5 * sa * sa
        shock = rng.random(nmin) < 1.0 / 4000
        jm = np.nonzero(shock)[0] * TPM
        inc[jm] += np.where(rng.random(jm.size) < 0.5, 1, -1) * 4 * sg / math.sqrt(24)
        p = np.exp(np.log(10.0 * (j + 1)) + np.cumsum(inc)).reshape(nmin, TPM)
        O, H, L, C = p[:, 0], p.max(1), p.min(1), p[:, -1]
        r = np.r_[0, np.diff(np.log(C))]
        QV = 1e6 / tr * (0.5 + (r / (sg / math.sqrt(1440))) ** 2)
        QV[shock] *= 100
        valid = np.ones(nmin, bool)
        arrs[s] = (O, H, L, C, QV, valid)
        ft = rk.DATA_START + np.arange(0, nday * 24, 8) * 3600000 + 5
        ar = np.zeros(ft.size)
        e = rng.normal(0, 1, ft.size)
        for i in range(1, ft.size):
            ar[i] = 0.97 * ar[i - 1] + 0.243 * e[i]
        funds[s] = (ft.astype(np.int64), 1e-4 + 3e-4 * ar, np.full(ft.size, 8.0))
        firsts[s] = rk.DATA_START + (WARM - age0) * rk.DAY
        tiers[s] = np.full(nday, tr, np.int8)
    return nday, arrs, funds, firsts, tiers


def run_panel(seed):
    rng = np.random.default_rng(seed)
    rk.STUDY_START = rk.DATA_START + WARM * rk.DAY
    rk.HALF_B = rk.STUDY_START
    nday, arrs, funds, firsts, tiers = make_panel(rng)
    hcs, qvd = {}, {}
    for s in arrs:
        G = klite.prepare_grid(*arrs[s][:4], arrs[s][5], -1)
        hcs[s] = klite.hourly_close(G, nday)
        qvd[s] = arrs[s][4].reshape(nday, 1440).sum(1)
    thr, _, _ = rk.cross_section(tiers, hcs, nday)
    mkt = rk.market_context(arrs["BTCUSDT"], -1, nday)
    CP = rk.cond_params()
    assert CP == rk.COND_PREREG
    J = 32
    CL = rk.cells()
    S = {m: np.zeros((NDAY_B, J)) for m in MODELS}
    N = {m: np.zeros((NDAY_B, J)) for m in MODELS}
    coin = {}
    place_tot = np.zeros(J)
    for s in arrs:
        ctx = dict(nday=nday, tier=tiers[s], qvd=qvd[s], fund=funds[s], dl=-1, first_ms=firsts[s], mkt=mkt, mkt_sym="BTCUSDT",
                   thr=thr, CP=CP, er_p1=None, sig_p1=None, models=MODELS)
        res = rk.process_symbol(s, arrs[s], ctx)
        a0 = res["agg"]
        a0 = a0[(a0.day >= WARM) & (a0.day < WARM + NDAY_B)]
        for model in MODELS:
            a = a0[a0.model == model]
            dd, cc = a.day.to_numpy().astype(int) - WARM, a.cell.to_numpy().astype(int)
            stat = np.where(np.array([CL[c]["stat"] for c in cc]) == "neth", a.neth.to_numpy(), a.net.to_numpy())
            Sc = np.zeros((NDAY_B, J)); Nc = np.zeros((NDAY_B, J))
            np.add.at(Sc, (dd, cc), stat)
            np.add.at(Nc, (dd, cc), a.fill.to_numpy())
            if model == "OPT":
                np.add.at(place_tot, cc, a.place.to_numpy())
            S[model] += Sc
            N[model] += Nc
            coin[(model, s)] = (Sc, Nc)
    return S, N, coin, place_tot


def worker(args):
    seed, = args
    t = time.time()
    S, N, coin, place = run_panel(seed)
    cs = {k: (v[0].astype(np.float32), v[1].astype(np.float32)) for k, v in coin.items()}
    return seed, S, N, cs, place, time.time() - t


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out_synth")
    R = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    os.makedirs(outdir, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(outdir, "power.log"), "w")])
    np.seterr(all="ignore")
    import warnings
    warnings.filterwarnings("ignore")
    seeds = [SEED + i for i in range(R)]
    res = []
    t0 = time.time()
    if nproc > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(nproc) as pool:
            for r in pool.imap_unordered(worker, [(s,) for s in seeds]):
                res.append(r)
                if len(res) % 10 == 0:
                    log.info("panel %d/%d (%.0fs, %.1fs/panel)", len(res), R, time.time() - t0, r[5])
    else:
        for s in seeds:
            res.append(worker((s,)))
            log.info("panel %d/%d %.1fs", len(res), R, res[-1][5])
    res.sort(key=lambda x: x[0])
    J = 32
    CL = rk.cells()
    floor = rk.FLOOR_BPS
    names = [p[0] for p in PANEL]
    tier_of = {p[0]: p[1] for p in PANEL}
    z_norm = norm_ppf(1 - ALPHA / J)
    out = dict(R=len(res), alpha=ALPHA, method="studentized_block_bootstrap_RW_maxt", B_fwer=B_FWER, models={})
    for model in MODELS:
        Ssum = sum(r[1][model].sum(0) for r in res)
        Nsum = sum(r[2][model].sum(0) for r in res)
        Mtrue = Ssum / np.maximum(Nsum, 1)
        # ---- FWER tren H0 bien (moi o dich ve M = san)
        fw = {}
        crit = []
        n_ins = np.zeros(J)
        for mu, tag in ((stats.MIN_UNITS, "prereg_min200"), (0, "no_min")):
            minp = []
            for i, r in enumerate(res):
                S, N = r[1][model], r[2][model]
                Sp = S - (Mtrue - floor)[None, :] * N
                st = stats.cell_stats(Sp, N, floor, 900000 + i, B=B_FWER, min_units=mu)
                p = np.array(st["p_rw"], float)
                minp.append(float(np.min(p)))
                if mu == stats.MIN_UNITS:
                    crit.append(st["crit_rw"])
                    n_ins += np.array(st["insufficient"], float)
            minp = np.array(minp)
            f = {str(a): float(np.mean(minp <= a)) for a in ALPHAS_INFO}
            fw[tag] = dict(fwer_at_alpha=float(np.mean(minp <= ALPHA)),
                           se=math.sqrt(max(np.mean(minp <= ALPHA) * (1 - np.mean(minp <= ALPHA)), 1e-9) / len(minp)),
                           fwer_info=f, minp=minp.tolist())
        crit_med = float(np.median(crit))
        # ---- R4-2 (2): cong suat 31 o (+3,5 sd that) khi o SPARSE_CELL (null) day / thua ngay tren nguong (ii) / duoi nguong
        Sp_all = [r[1][model] - (Mtrue - floor)[None, :] * r[2][model] for r in res]
        Mp = np.array([Sp.sum(0) / np.maximum(r[2][model].sum(0), 1) for Sp, r in zip(Sp_all, res)])
        sd_true = Mp.std(0, ddof=1)
        others = [c for c in range(J) if c != SPARSE_CELL]
        pw = {}
        for var, nblk in (("dense", None), ("sparse_13blk_above", 13), ("sparse_12blk_below", 12)):
            rj, rej_sp, ins_sp, nsp = [], [], [], []
            for i, (Sp, r) in enumerate(zip(Sp_all, res)):
                N = r[2][model].copy()
                Sa = Sp + (EFFECT_SD * sd_true)[None, :] * N
                Sa[:, SPARSE_CELL] = Sp[:, SPARSE_CELL]                       # o thua o H0 bien
                if nblk is not None:
                    Sa[:, SPARSE_CELL], N[:, SPARSE_CELL] = sparsify(Sp[:, SPARSE_CELL], N[:, SPARSE_CELL], nblk)
                st = stats.cell_stats(Sa, N, floor, 600000 + i, B=B_FWER)
                rr = np.array(st["rw_reject"], bool)
                rj.append(float(rr[others].mean()))
                rej_sp.append(bool(rr[SPARSE_CELL]))
                ins_sp.append(bool(st["insufficient"][SPARSE_CELL]))
                nsp.append(float(N[:, SPARSE_CELL].sum()))
            pw[var] = dict(power_31=float(np.mean(rj)), sparse_rejected=float(np.mean(rej_sp)),
                           sparse_insufficient=float(np.mean(ins_sp)), sparse_units_median=float(np.median(nsp)))
            log.info("%s power31 %s: %s", model, var, pw[var])
        # ---- cong suat: tham so tung o tu panel, quy doi ve so coin that
        rows = []
        for c in range(J):
            cell = CL[c]
            vcd, num, den, pcd_n, pcd_d, phis = [], 0.0, 0.0, 0, 0, []
            for r in res:
                mc = []
                for s in names:
                    Sc, Nc = r[3][(model, s)]
                    mc.append(np.where(Nc[:, c] > 0, Sc[:, c] / np.maximum(Nc[:, c], 1), np.nan))
                    inbase = (cell["grp"] != "N" or tier_of[s] == cell["tier"]) and not (cell["grp"] == "D" and s == "BTCUSDT")
                    if cell["set"] == "IDEAL_N":
                        inbase = tier_of[s] <= 2
                    if inbase:
                        pcd_d += NDAY_B
                        pcd_n += int((Nc[:, c] > 0).sum())
                M = np.stack(mc, 1)
                x = M - np.nanmean(M)
                vcd.append(np.nanvar(M))
                fin = np.isfinite(x)
                xs = np.where(fin, x, 0.0)
                cnt = fin.sum(1)
                s1, s2 = xs.sum(1), (xs ** 2).sum(1)
                g = cnt > 1
                num += float((s1[g] ** 2 - s2[g]).sum())
                den += float(((cnt[g] - 1) * s2[g]).sum())
                S1, N1 = r[1][model][:, c], r[2][model][:, c]
                if (N1 > 0).sum() > 30:
                    st = stats.cell_stats(S1[:, None], N1[:, None], floor, 77, B=50, min_units=0)
                    dm = np.where(N1 > 0, S1 / np.maximum(N1, 1), np.nan)
                    dm = dm[np.isfinite(dm)]
                    naive = np.std(dm, ddof=1) / math.sqrt(dm.size)
                    if naive > 0 and np.isfinite(st["SE"][0]):
                        phis.append(st["SE"][0] / naive)
            v = float(np.nanmean(vcd))
            rho = max(num / den, 0.0) if den > 0 else 0.0
            phi = float(np.median(phis)) if phis else np.nan
            pcd = pcd_n / max(pcd_d, 1)
            row = dict(cell=cell["name"], stat=cell["stat"], units_per_rep=float(Nsum[c] / len(res)), p_coinday=round(pcd, 4),
                       v_coinday=round(v, 1), rho_cc=round(rho, 3), phi=round(phi, 2), M_null_true=round(float(Mtrue[c]), 2),
                       frac_panel_insufficient=round(float(n_ins[c] / len(res)), 3))
            for h in ("A", "B"):
                if cell["grp"] == "N":
                    nreal = NREAL[h][cell["tier"]]
                elif cell["set"] == "IDEAL_N":
                    nreal = NREAL[h][1] + NREAL[h][2]
                else:
                    nreal = sum(NREAL[h].values()) - (1 if cell["grp"] == "D" else 0)
                neff = max(nreal * pcd, 1e-9)               # so coin co don vi trong 1 ngay (ky vong)
                dfrac = min(1.0, neff)                      # ti le ngay co don vi khi neff < 1
                se = (phi * math.sqrt(v * (rho + (1 - rho) / max(neff, 1.0)) / (NDAY[h] * dfrac))
                      if np.isfinite(phi) else float("nan"))
                row["SE_" + h] = round(se, 2)
            row["MDE_B_norm"] = round((z_norm + Z80) * row["SE_B"], 1)
            row["MDE_B_emp"] = round((crit_med + Z80) * row["SE_B"], 1)
            rows.append(row)
        frac = {}
        for c in range(18, 32):
            ci = rk.CK_ALL.index((CL[c]["c"], CL[c]["k"]))
            frac[CL[c]["name"]] = round(float(Nsum[c] / max(Nsum[ci * 3:(ci + 1) * 3].sum(), 1)), 4)
        out["models"][model] = dict(fwer=fw, power31_sparse=pw, crit_rw_median=crit_med, z_norm=z_norm, rows=rows, unit_fraction_vs_GN=frac,
                                    M_null_true=Mtrue.tolist())
        log.info("%s FWER@4%% prereg %.3f / no_min %.3f ; crit_rw median %.2f (z_norm %.2f)", model,
                 fw["prereg_min200"]["fwer_at_alpha"], fw["no_min"]["fwer_at_alpha"], crit_med, z_norm)
    out["assumptions"] = dict(PANEL=PANEL, NREAL=NREAL, NDAY=NDAY, TPM=TPM, models=MODELS, boot_B_fwer=B_FWER, seed=SEED)
    out["seconds"] = round(time.time() - t0, 1)
    json.dump(out, open(os.path.join(outdir, "power32.json"), "w"), indent=1, default=float)
    with open(os.path.join(outdir, "power32_table.md"), "w") as fh:
        for model in MODELS:
            mm = out["models"][model]
            f1, f0 = mm["fwer"]["prereg_min200"], mm["fwer"]["no_min"]
            fh.write("## %s: FWER do (R = %d panel base, H0 bien, 32 o, RW studentized, alpha %.2f, B = %d): luat prereg %.3f +- "
                     "%.3f ; khong nguong 200: %.3f +- %.3f ; tham khao (prereg) %s ; crit max-t median %.2f (z chuan %.2f)\n\n"
                     % (model, len(res), ALPHA, B_FWER, f1["fwer_at_alpha"], f1["se"], f0["fwer_at_alpha"], f0["se"],
                        f1["fwer_info"], mm["crit_rw_median"], z_norm))
            fh.write("| o | stat | don vi/panel | p coin-ngay | rho | phi | M null | ti le panel INSUFF | SE_A | SE_B | MDE_B chuan |"
                     " MDE_B max-t |\n|" + "---|" * 12 + "\n")
            for r in mm["rows"]:
                fh.write("| %s | %s | %.0f | %.3f | %.3f | %.2f | %.2f | %.3f | %.2f | %.2f | %.1f | %.1f |\n" % (
                    r["cell"], r["stat"], r["units_per_rep"], r["p_coinday"], r["rho_cc"], r["phi"], r["M_null_true"],
                    r["frac_panel_insufficient"], r["SE_A"], r["SE_B"], r["MDE_B_norm"], r["MDE_B_emp"]))
            fh.write("\nTi le don vi tap / G-N gop cung (c,k): %s\n" % json.dumps(mm["unit_fraction_vs_GN"]))
            fh.write("Cong suat 31 o (+%.1f sd) theo trang thai o %s (R4-2): %s\n\n" % (EFFECT_SD, CL[SPARSE_CELL]["name"],
                                                                                    json.dumps(mm["power31_sparse"])))
    log.info("XONG (%.0fs)", time.time() - t0)


if __name__ == "__main__":
    main()
