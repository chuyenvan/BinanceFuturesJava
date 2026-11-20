"""power3.py - CONG SUAT 12 o S3 + do FWER Romano-Wolf STUDENTIZED (stats.cell_stats, alpha 4 %) tren null TONG HOP, chay QUA
DUNG runner3_kaggle.process_symbol (cung 12 o, cung muc / phi / truot / funding), CA K_OPT3 (khoa "OPT") va K_PESS. KHONG du lieu that.
R3-8: moi nhay (rieng coin va toan thi truong) dat o buoc con GIUA phut (open phut nhay = gia truoc nhay).
Moi panel = BTC + 7 alt (tier 1/1/2/2/3/3/3/3), 731 ngay (nua B) + 45 ngay warm-up, 2 buoc/phut. Null = GBM martingale + nhay
VINH VIEN doi xung (khong co loi the hoi gia):
  - nhay rieng coin: Poisson LAM_I / coin / ngay, |log nhay| = U(1, 4) x sigma_1d coin;
  - nhay toan thi truong: Poisson LAM_M / ngay, cung dau cho moi coin, |log| = U(1, 4) x sigma_1d(BTC) x beta.
TAN SUAT nhay (LAM_I, LAM_M) la THAM SO GIA DINH (khong lay tu du lieu that) - quyet dinh so lenh sau duoc khop; 3 kich ban.
FWER: M that tung o (moi mo hinh) = gop moi panel; dich ve san 4 bps (H0 bien) roi chay RW studentized 12 o moi panel (B 1000).
MDE (bps VUOT san) quy ve universe that (nua B: 10 T1 / 50 T2 / 420 T3; nua A: 10 / 50 / 130) bang phan ra phuong sai tong khoi
20 ngay: Var(S_b) = sum_t n_t v_t + sum_{t,t'} n_t (n_t' - 1[t=t']) c_tt' (v: phuong sai rieng / coin, c: hiep phuong sai cheo coin
uoc tu panel) -> SE = sqrt(Var / nb) / N_b. MDE chuan = (z_(1-0,04/12) + 0,84) SE; MDE max-t = (nguong RW max-t median + 0,84) SE.
Chay: python3 power3.py OUTDIR [R_base] [NPROC] [R_alt]
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
import synth3  # noqa: E402
import stats  # noqa: E402
import runner3_kaggle as rk  # noqa: E402

log = logging.getLogger("power3")
SEED = 2026112180                                          # R3: seed moi (bo sinh doi)
WARM = 45
NDAY_B = 731
TPM = 2
# (ten, tier, sigma ngay, beta)
PANEL = [("BTCUSDT", 1, 0.030, None), ("A1USDT", 1, 0.035, 0.9), ("A2USDT", 2, 0.050, 1.1), ("A3USDT", 2, 0.050, 1.2),
         ("A4USDT", 3, 0.065, 1.3), ("A5USDT", 3, 0.065, 1.0), ("A6USDT", 3, 0.080, 1.2), ("A7USDT", 3, 0.080, 0.8)]
NREAL = {"A": {1: 10, 2: 50, 3: 130}, "B": {1: 10, 2: 50, 3: 420}}
NB = {"A": 46, "B": 37}
SCEN = {"base": dict(lam_i=0.10, lam_m=0.02), "low": dict(lam_i=0.03, lam_m=0.005), "high": dict(lam_i=0.30, lam_m=0.05)}
ALPHA = stats.ALPHA_FWER
B_FWER = 1000
Z80 = 0.8416212335729143
MODELS = ("OPT", "PESS")


def norm_ppf(p):
    lo, hi = -10.0, 10.0
    for _ in range(100):
        m = 0.5 * (lo + hi)
        if 1 - stats.norm_sf(m) < p:
            lo = m
        else:
            hi = m
    return 0.5 * (lo + hi)


def make_panel(rng, lam_i, lam_m):
    nday = WARM + NDAY_B + 4
    nmin = nday * 1440
    nm = rng.poisson(lam_m * nday)
    mmins = np.sort(rng.choice(np.arange(10, nmin - 10), size=nm, replace=False)) if nm else np.zeros(0, int)
    msgn = np.where(rng.random(nm) < 0.5, -1.0, 1.0)
    mmag = rng.uniform(1.0, 4.0, nm) * PANEL[0][2]
    arrs, funds = {}, {}
    common = None
    for j, (s, tr, sg, b) in enumerate(PANEL):
        px, inc = synth3.path_with_events(rng, nmin, TPM, sg, 10.0 * (j + 1), lam_i, "jump", depth=(1.0, 4.0),
                                          common_inc=common, beta=b, sign_p_down=0.5, mid=True)
        if s == "BTCUSDT":
            common = inc
        lp = np.log(px)
        if nm:
            dj = np.zeros(nmin * TPM)
            dj[mmins * TPM + 1] = msgn * mmag * (1.0 if b is None else b)          # R3-8: giua phut (TPM 2 -> buoc con 1)
            lp = lp + np.cumsum(dj)
        q = 10.0 ** (math.floor(math.log10(10.0 * (j + 1))) - 8)
        p = (np.round(np.exp(lp) / q) * q).reshape(nmin, TPM)
        O, H, L, C = p[:, 0], p.max(1), p.min(1), p[:, -1]
        arrs[s] = (O, H, L, C, np.full(nmin, 1e6), np.ones(nmin, bool))
        ft = rk.DATA_START + np.arange(0, nday * 24, 8) * 3600000 + 5
        ar = np.zeros(ft.size)
        e = rng.normal(0, 1, ft.size)
        for i in range(1, ft.size):
            ar[i] = 0.97 * ar[i - 1] + 0.243 * e[i]
        funds[s] = (ft.astype(np.int64), 1e-4 + 3e-4 * ar, np.full(ft.size, 8.0))
    return nday, arrs, funds


def run_panel(args):
    seed, scen = args
    rng = np.random.default_rng(seed)
    rk.STUDY_START = rk.DATA_START + WARM * rk.DAY
    rk.HALF_B = rk.STUDY_START
    sc = SCEN[scen]
    nday, arrs, funds = make_panel(rng, sc["lam_i"], sc["lam_m"])
    mkt = rk.market_context(arrs["BTCUSDT"], -1, nday)
    CP = rk.cond_params()
    assert CP == rk.COND_PREREG
    J, K = 12, len(PANEL)
    S = {m: np.zeros((NDAY_B, J, K)) for m in MODELS}
    N = {m: np.zeros((NDAY_B, J, K)) for m in MODELS}
    place = {m: np.zeros(J) for m in MODELS}
    for k, (s, tr, sg, b) in enumerate(PANEL):
        ctx = dict(nday=nday, tier=np.full(nday, tr, np.int8), fund=funds[s], dl=-1, mkt=mkt, mkt_sym="BTCUSDT", CP=CP,
                   er_p1=None, sig_p1=None)
        res = rk.process_symbol(s, arrs[s], ctx)
        ag = res["agg"]
        for m in MODELS:
            a = ag[ag.model == m]
            dd = a.day.to_numpy().astype(int) - WARM
            ok = (dd >= 0) & (dd < NDAY_B)
            np.add.at(S[m], (dd[ok], a.cell.to_numpy().astype(int)[ok], k), a.net.to_numpy()[ok])
            np.add.at(N[m], (dd[ok], a.cell.to_numpy().astype(int)[ok], k), a.fill.to_numpy()[ok])
            place[m] += np.bincount(a.cell.to_numpy().astype(int)[ok], weights=(a.place - a.excl).to_numpy()[ok], minlength=J)
    return dict(seed=seed, scen=scen, S={m: S[m].astype(np.float32) for m in MODELS}, N={m: N[m].astype(np.float32) for m in MODELS},
                place=place)


def fwer_one(args):
    S, N, seed = args
    r = stats.cell_stats(S, N, 4.0, seed, B=B_FWER)
    return dict(any=bool(r["rw_reject"].any()), ins=r["insufficient"].tolist(), crit=r["crit_rw"],
                any_by_alpha={str(a): bool((r["p_rw"] <= a).any()) for a in (0.05, 0.04, 0.03, 0.02, 0.01)})


def var_decomp(Ss, Ns, M):
    """Ss, Ns: list panel (D, K) cua 1 o. Tra theo tier: v_t, n_t (don vi / coin / khoi), c_tt' (hiep phuong sai cheo)."""
    tiers = np.array([p[1] for p in PANEL])
    v = {t: [] for t in (1, 2, 3)}
    n = {t: [] for t in (1, 2, 3)}
    c = {(a, b): [] for a in (1, 2, 3) for b in (1, 2, 3)}
    for S, N in zip(Ss, Ns):
        D = S.shape[0]
        parts = [(a, min(a + 20, D)) for a in range(0, D, 20)]
        Sb = np.array([S[a:b].sum(0) for a, b in parts])
        Nb = np.array([N[a:b].sum(0) for a, b in parts])
        U = Sb - M * Nb
        cov = U.T @ U / len(parts)
        for k in range(len(PANEL)):
            v[tiers[k]].append(cov[k, k])
            n[tiers[k]].append(Nb[:, k].mean())
            for l_ in range(len(PANEL)):
                if l_ != k:
                    c[(tiers[k], tiers[l_])].append(cov[k, l_])
    return ({t: float(np.mean(v[t])) for t in v}, {t: float(np.mean(n[t])) for t in n},
            {k: float(np.mean(x)) for k, x in c.items()})


def se_real(v, n, c, half):
    NR = NREAL[half]
    var = sum(NR[t] * v[t] for t in (1, 2, 3)) + sum(NR[a] * (NR[b] - (a == b)) * c[(a, b)] for a in (1, 2, 3) for b in (1, 2, 3))
    Nb = sum(NR[t] * n[t] for t in (1, 2, 3))
    var_ind = sum(NR[t] * v[t] for t in (1, 2, 3))
    if Nb <= 0:
        return float("nan"), float("nan"), 0.0
    return math.sqrt(max(var, 0.0) / NB[half]) / Nb, math.sqrt(var_ind / NB[half]) / Nb, Nb * NB[half]


def main():
    out = sys.argv[1]
    R = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    R_alt = int(sys.argv[4]) if len(sys.argv) > 4 else 40
    os.makedirs(out, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(out, "power3.log"), "w")])
    import multiprocessing as mp
    t0 = time.time()
    jobs = [(SEED + i, "base") for i in range(R)] + [(SEED + 10000 + i, "low") for i in range(R_alt)] + \
           [(SEED + 20000 + i, "high") for i in range(R_alt)]
    with mp.get_context("fork").Pool(nproc) as pool:
        panels = []
        for i, r in enumerate(pool.imap(run_panel, jobs, chunksize=1)):
            panels.append(r)
            if (i + 1) % 20 == 0:
                log.info("panel %d/%d %.0fs", i + 1, len(jobs), time.time() - t0)
    cl = rk.cells()
    J = 12
    zstd = norm_ppf(1 - ALPHA / J)
    result = dict(seed=SEED, R_base=R, R_alt=R_alt, B=B_FWER, alpha=ALPHA, panel=PANEL, scen=SCEN, NREAL=NREAL, cells=[c["name"] for c in cl],
                  assumption="tan suat nhay LAM_I / LAM_M la THAM SO GIA DINH, khong lay tu du lieu that", by_scen={})
    for scen in ("base", "low", "high"):
        ps = [p for p in panels if p["scen"] == scen]
        rs = dict(n_panel=len(ps), models={})
        for m in MODELS:
            Sagg = [p["S"][m].astype(np.float64).sum(2) for p in ps]
            Nagg = [p["N"][m].astype(np.float64).sum(2) for p in ps]
            Ssum, Nsum = sum(x.sum(0) for x in Sagg), sum(x.sum(0) for x in Nagg)
            Mt = np.where(Nsum > 0, Ssum / np.maximum(Nsum, 1), np.nan)
            plc = sum(p["place"][m] for p in ps)
            mr = dict(M_true_null=Mt.tolist(), fills_per_panel=(Nsum / len(ps)).tolist(),
                      p_fill=(Nsum / np.maximum(plc, 1)).tolist(),
                      fills_per_coin_day=(Nsum / len(ps) / len(PANEL) / NDAY_B).tolist())
            fw = None
            if scen == "base":
                args = []
                for i, (S_, N_) in enumerate(zip(Sagg, Nagg)):
                    Ssh = S_ - np.where(np.isfinite(Mt), Mt - 4.0, 0.0)[None, :] * N_
                    args.append((Ssh, N_, 900000 + i + (0 if m == "OPT" else 50000)))
                with mp.get_context("fork").Pool(nproc) as pool:
                    fr = pool.map(fwer_one, args)
                k = sum(x["any"] for x in fr)
                fw = dict(fwer=k / len(fr), se=math.sqrt(max(k / len(fr) * (1 - k / len(fr)), 1e-12) / len(fr)), n=len(fr),
                          by_alpha={a: float(np.mean([x["any_by_alpha"][a] for x in fr])) for a in fr[0]["any_by_alpha"]},
                          frac_panel_insufficient=np.mean([x["ins"] for x in fr], 0).tolist(),
                          crit_maxt_median=float(np.nanmedian([x["crit"] for x in fr])))
                mr["fwer"] = fw
            crit = (rs["models"]["OPT"]["fwer"]["crit_maxt_median"] if m == "PESS" else fw["crit_maxt_median"]) if scen == "base" else \
                result["by_scen"]["base"]["models"][m]["fwer"]["crit_maxt_median"]
            mde = []
            for c in range(J):
                Ss = [p["S"][m][:, c, :].astype(np.float64) for p in ps]
                Ns = [p["N"][m][:, c, :].astype(np.float64) for p in ps]
                v, n, cc = var_decomp(Ss, Ns, Mt[c] if np.isfinite(Mt[c]) else 0.0)
                row = dict(cell=cl[c]["name"])
                for h in ("B", "A"):
                    se, se_ind, nf = se_real(v, n, cc, h)
                    row[h] = dict(SE=se, SE_indep=se_ind, fills_real=nf, MDE_std=(zstd + Z80) * se, MDE_maxt=(crit + Z80) * se,
                                  insufficient_risk=bool(nf < 200 * 3))
                row["v_t"], row["n_t_per_block"], row["c_cross"] = v, n, {"%d%d" % k: x for k, x in cc.items()}
                mde.append(row)
            mr["mde"] = mde
            rs["models"][m] = mr
        result["by_scen"][scen] = rs
        log.info("scen %s xong %.0fs", scen, time.time() - t0)
    result["seconds"] = round(time.time() - t0, 1)
    json.dump(result, open(os.path.join(out, "power3.json"), "w"), indent=1, default=float)
    lines = ["# power3 - FWER + MDE 12 o S3 (tong hop, gia dinh tan suat nhay)", ""]
    for m in MODELS:
        f = result["by_scen"]["base"]["models"][m]["fwer"]
        lines.append("FWER %s @4%% (base, %d panel): %.3f +- %.3f; by alpha %s; nguong max-t median %.2f (z chuan %.2f)" % (
            m, f["n"], f["fwer"], f["se"], json.dumps(f["by_alpha"]), f["crit_maxt_median"], zstd))
    lines.append("")
    lines.append("| o | mo hinh | kich ban | fill/coin-ngay | P(khop) | M null | SE_B | MDE_B chuan / max-t | SE_A | MDE_A max-t | khop that B (uoc) |")
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for c in range(J):
        for m in MODELS:
            for scen in ("low", "base", "high"):
                mr = result["by_scen"][scen]["models"][m]
                r = mr["mde"][c]
                lines.append("| %s | %s | %s | %.4f | %.4f | %.1f | %.2f | %.1f / %.1f | %.2f | %.1f | %.0f |" % (
                    cl[c]["name"], m, scen, mr["fills_per_coin_day"][c], mr["p_fill"][c], mr["M_true_null"][c],
                    r["B"]["SE"], r["B"]["MDE_std"], r["B"]["MDE_maxt"], r["A"]["SE"], r["A"]["MDE_maxt"], r["B"]["fills_real"]))
    open(os.path.join(out, "power3_table.md"), "w").write("\n".join(lines) + "\n")
    log.info("XONG %.0fs", time.time() - t0)


if __name__ == "__main__":
    main()
