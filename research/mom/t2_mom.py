"""T2-MOM tang 2 (docs/prereg/PREREG_T2_MOM.md, commit 758729a8). Chay: python3 t2_mom.py
Tuan: ngay tin hieu s, vao close s+lag, thoat close s+lag+7. Nhan tuan = s+1 (Thu Hai, giong tang 1)."""
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/screen"))
import sw_run as S  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("t2mom")
OUT = os.path.expanduser("~/claude_master/1016/t2mom")
CB = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/gate_skipfull_detail_equity.csv")
os.makedirs(OUT, exist_ok=True)

D = pd.read_parquet(S.W + "/d1.parquet")
C = D.pivot(index="day", columns="sym", values="close").sort_index()
assert (C.index == pd.date_range(C.index.min(), C.index.max(), freq="D")).all(), "index ngay khong lien tuc"
Q = D.pivot(index="day", columns="sym", values="qv").reindex(C.index)
FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
CF = C.ffill()
first = C.apply(lambda s: s.first_valid_index())
qv30 = Q.rolling(30, min_periods=20).median()
FEATS = {lb: C / C.shift(lb) - 1 for lb in (14, 21, 28)}
END = pd.Timestamp("2026-09-30")


def run(lb=21, offset=0, lag=1, ca=0.001, cb=0.0006, q=10, surv=True, detail=False):
    F = FEATS[lb]
    wd = (6 + offset) % 7
    sdays = [d for d in C.index if d.weekday() == wd and d >= pd.Timestamp("2021-02-28") and d + pd.Timedelta(days=lag + 7) <= END]
    if not surv:  # V1: dung dung khung tang 1 (Thu Hai 2021-03-01..2026-09-21)
        sdays = [d for d in sdays if pd.Timestamp("2021-03-01") <= d + pd.Timedelta(days=1) <= pd.Timestamp("2026-09-21")]
    rows, pos, ffill_n, long_n = [], [], 0, 0
    pT, pB, pU = set(), set(), set()
    for s in sdays:
        ent = s + pd.Timedelta(days=lag); ex = ent + pd.Timedelta(days=7)
        assert s <= ent < ex
        age_ok = first[first <= s + pd.Timedelta(days=1) - pd.Timedelta(days=60)].index
        u = qv30.loc[s]; u = u[u >= 20e6].index.intersection(age_ok)
        u = [x for x in u if x[:-4] not in S.STABLE]
        if surv:
            u = [x for x in u if not math.isnan(C.at[ent, x])]
            ret = (CF.loc[ex, u] / C.loc[ent, u] - 1).dropna()
        else:
            ret = (C.loc[ex, u] / C.loc[ent, u] - 1).dropna()
        if len(ret) < 30:
            continue
        fs = FD.loc[ent + pd.Timedelta(days=1):ex, ret.index].sum()
        f = F.loc[s, ret.index].dropna()
        n = max(3, len(f) // q)
        top = list(f.nlargest(n).index); bot = list(f.nsmallest(n).index); U = set(ret.index)
        if surv:
            miss = [x for x in top if math.isnan(C.at[ex, x])]
            ffill_n += len(miss); long_n += len(top)
            if detail and miss:
                log.info("V3 ffill %s %s", ex.date(), miss)
        toT = 1 - len(set(top) & pT) / n; toB = 1 - len(set(bot) & pB) / n
        toU = 1 - len(U & pU) / len(U) if pU else 1.0
        pT, pB, pU = set(top), set(bot), U
        rL_raw = ret[top].mean(); fL = fs[top].mean()
        rU_raw = ret.mean(); fU = fs.mean()
        rS_raw = ret[bot].mean(); fS = fs[bot].mean()
        rB = CF.at[ex, "BTCUSDT"] / C.at[ent, "BTCUSDT"] - 1
        fB = FD.loc[ent + pd.Timedelta(days=1):ex, "BTCUSDT"].sum()
        costL = toT * 2 * ca
        h0 = rL_raw - fL - costL
        h1 = h0 - rB + fB - abs(rL_raw - rB) * cb
        h2 = h0 - rU_raw + fU - ca * (abs(rL_raw - rU_raw) + toU * 2)
        h3 = h0 - rS_raw + fS - toB * 2 * ca
        exc = h0 - rU_raw  # khung tang 1 (bench khong tru funding)
        rows.append((s + pd.Timedelta(days=1), h0, h1, h2, h3, exc, rB, len(ret), toT, ent, ex))
        if detail:
            for x in top:
                pos.append((s, x, 1.0 / n / qv30.at[s, x]))
    df = pd.DataFrame(rows, columns=["t", "H0", "H1", "H2", "H3", "exc", "rB", "nu", "to", "ent", "ex"]).set_index("t")
    return df, (ffill_n, long_n), pd.DataFrame(pos, columns=["s", "sym", "p_per_usd"])


def sh(r):
    r = r.dropna()
    return float(r.mean() / r.std() * np.sqrt(52)) if len(r) > 10 and r.std() > 0 else 0.0


def summ(r):
    eq = (1 + r).cumprod()
    E = r[r.index <= S.E1]; Cc = r[(r.index >= S.C0) & (r.index <= S.C1)]
    yrs = r.groupby(r.index.year).sum()
    return {"sh_full": sh(r), "sh_E": sh(E), "sh_C": sh(Cc), "ann": float(r.mean() * 52), "maxdd": float((eq / eq.cummax() - 1).min()),
            "worst_w": float(r.min()), "worst_4w": float(r.rolling(4).sum().min()), "skew": float(r.skew()), "n": int(len(r)),
            "years": {int(k): round(float(v), 4) for k, v in yrs.items()}, "years_pos": int((yrs > 0).sum()), "n_years": int(len(yrs))}


def boot_p(r, block=4, B=5000, seed=20261016):
    x = r.dropna().values; T = len(x); rng = np.random.default_rng(seed)
    nb = int(np.ceil(T / block)); means = np.empty(B)
    for b in range(B):
        st = rng.integers(0, T, nb)
        idx = (st[:, None] + np.arange(block)[None, :]).ravel()[:T] % T
        means[b] = x[idx].mean()
    return float((means <= 0).mean())


def dsr(r, N=50):
    x = r.dropna().values; T = len(x); sr = x.mean() / x.std(ddof=1)
    g3 = float(pd.Series(x).skew()); g4 = float(pd.Series(x).kurt()) + 3
    em = 0.5772156649
    sr0 = np.sqrt(1.0 / T) * ((1 - em) * norm.ppf(1 - 1.0 / N) + em * norm.ppf(1 - 1.0 / (N * np.e)))
    z = (sr - sr0) * np.sqrt(T - 1) / np.sqrt(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2)
    return {"sr_w": float(sr), "sr0_w": float(sr0), "dsr": float(norm.cdf(z)), "T": T}


def main():
    res = {}
    # ---- V1
    v1, _, _ = run(lag=0, ca=0.0005, surv=False)
    E = v1.exc[v1.index <= S.E1]; Cc = v1.exc[(v1.index >= S.C0) & (v1.index <= S.C1)]
    v1E, v1C = sh(E), sh(Cc)
    ref = [l for l in open(S.W + "/sw_diag.log") if l.startswith("X1 goc")][0]
    rE = float(ref.split("exc E Sh ")[1].split()[0]); rC = float(ref.split("C Sh ")[1].split()[0])
    res["V1"] = {"mine": [v1E, v1C], "ref": [rE, rC], "pass": abs(v1E - rE) <= 0.01 and abs(v1C - rC) <= 0.01}
    log.info("V1 %s", res["V1"])
    # ---- BASE
    base, (ffn, ln), pos = run(detail=True)
    base.to_csv(OUT + "/base_weeks.csv")
    res["V2"] = {"weeks": int(len(base)), "univ_min": int(base.nu.min()), "pass": len(base) >= 280 and base.nu.min() >= 30}
    res["V3"] = {"ffill": ffn, "long_cw": ln, "frac": ffn / max(ln, 1), "pass": ffn / max(ln, 1) <= 0.02}
    log.info("V2 %s | V3 %s", res["V2"], res["V3"])
    res["base"] = {h: summ(base[h]) for h in ("H0", "H1", "H2", "H3")}
    for h in ("H0", "H1", "H2", "H3"):
        log.info("BASE %s %s", h, res["base"][h])
    c2, _, _ = run(ca=0.002, cb=0.0012)
    res["cost2x"] = {h: summ(c2[h]) for h in ("H0", "H1", "H2", "H3")}
    log.info("COST2X sh_full %s", {h: round(v["sh_full"], 3) for h, v in res["cost2x"].items()})
    # ---- do ben (H1)
    rob = {}
    for k in range(7):
        rob[f"off{k}"] = summ(run(offset=k)[0].H1)
    for lb in (14, 28):
        rob[f"lb{lb}"] = summ(run(lb=lb)[0].H1)
    rob["quintile"] = summ(run(q=5)[0].H1)
    for lg in (0, 2):
        rob[f"lag{lg}"] = summ(run(lag=lg)[0].H1)
    res["robust_H1"] = rob
    for k, v in rob.items():
        log.info("ROB %-8s sh_full %+.2f E %+.2f C %+.2f maxdd %.2f", k, v["sh_full"], v["sh_E"], v["sh_C"], v["maxdd"])
    # ---- rui ro
    h1 = base.H1
    crash = base[base.rB < -0.10]
    res["risk"] = {"corr_btc_H0": float(base.H0.corr(base.rB)), "corr_btc_H1": float(h1.corr(base.rB)),
                   "btc_dn10_weeks": int(len(crash)), "H1_mean_btc_dn10": float(crash.H1.mean()) if len(crash) else None,
                   "H0_mean_btc_dn10": float(crash.H0.mean()) if len(crash) else None,
                   "boot_p_H1": boot_p(h1), "dsr_H1": dsr(h1), "mean_turnover": float(base.to.mean())}
    # crash-buy C2
    cb = pd.read_csv(CB, parse_dates=["date_utc"]).set_index("date_utc")["C2_mtm_close"]
    w = [(t, cb[r.ex] / cb[r.ent] - 1) for t, r in base.iterrows() if r.ent in cb.index and r.ex in cb.index]
    cw = pd.Series(dict(w))
    j = pd.concat([h1.rename("h1"), cw.rename("cb")], axis=1).dropna()
    worst = j.nsmallest(10, "cb")
    res["V5"] = {"overlap": int(len(j)), "pass": len(j) >= 200}
    res["risk"].update({"corr_crashbuy": float(j.h1.corr(j.cb)), "H1_in_cb_worst10": float(worst.h1.mean()), "cb_worst10_mean": float(worst.cb.mean())})
    # capacity
    pp = pos.p_per_usd
    p95 = float(pp.quantile(0.95))
    res["capacity"] = {"p95_part_50k": p95 * 5e4, "p95_part_200k": p95 * 2e5, "p95_part_1M": p95 * 1e6, "cap_usd_p95_0.5pct": 0.005 / p95}
    log.info("V5 %s | RISK %s | CAP %s", res["V5"], res["risk"], res["capacity"])
    # ---- tieu chi
    b = res["base"]["H1"]
    G = {"G1": b["sh_full"] >= 0.60, "G2": b["sh_E"] >= 0.20 and b["sh_C"] >= 0.60, "G3": res["cost2x"]["H1"]["sh_full"] >= 0.35,
         "G4": sum(rob[f"off{k}"]["sh_full"] > 0.30 for k in range(7)) >= 5,
         "G5": rob["lb14"]["sh_full"] > 0.30 and rob["lb28"]["sh_full"] > 0.30,
         "G6": b["years_pos"] >= 4, "G7": b["maxdd"] >= -0.45, "G8": res["risk"]["boot_p_H1"] < 0.05,
         "G9": res["risk"]["corr_crashbuy"] <= 0.50}
    res["criteria"] = {k: bool(v) for k, v in G.items()}
    vok = all(res[v]["pass"] for v in ("V1", "V2", "V3", "V5"))
    res["verdict"] = ("GO" if all(G.values()) else "NO-GO") if vok else "DATA-FAIL"
    log.info("CRITERIA %s | VERDICT %s", res["criteria"], res["verdict"])
    json.dump(res, open(OUT + "/t2mom_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
