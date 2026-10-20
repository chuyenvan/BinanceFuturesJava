#!/usr/bin/env python3
"""MD_STRAT tang A (offline, cat lop) - dung PREREG_MD_STRAT.md (142c87fb).
Cum = (sym, m1) nhu ENTRY_CONFIRM (ec_a.py); chan mo = m0 nho nhat (tie -> thu tu dong).
Dot = cac cum SELECTOR (chan mo PREDICT_SYMBOL_TRADE) mo cung phut M trong 1 seed.
Hang r trong dot = thu tu symbolPred TANG dan (pNoPump thap = tot; xac minh code: symbol2Pred sort tang,
selectCands lay K phan tu dau, SELRANK rank 1 = pNoPump thap nhat). Tie -> selRank log.
Nam/chia mau theo gio +07 cua M. Cutoff tercile chi tinh tren D (2021-07..2023-12), ap nguyen cho C (2024..2025)."""
import json
import logging
import os
import re
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402,F401  (theo ec_a: import truoc reset_rule_score)
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402
import reset_rule_score as R  # noqa: E402

OUTD = "/home/ubuntu/claude_master/md_strat"
SIMD = "/home/ubuntu/kaggle_sim/out"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ms")
SEEDS = I.SEEDS
NS = len(SEEDS)
assert NS == 8, SEEDS
DAY0 = pd.Timestamp(R.DAY0)
VARS = ["dow", "up", "dow15m"]
RG = {"R1": (1, 5), "R2": (6, 12), "R3": (13, 24)}
TS = ["T1", "T2", "T3"]
PERIODS = ["D", "C"]
C_END = pd.Timestamp("2026-01-01")
D_END = pd.Timestamp("2024-01-01")
SELRE = re.compile(r"SELRANK sym=(\S+) tOpen=(\d{8} \d{2}:\d{2}) tMs=(\d+) rank=(\d+) pred=(\S+)")

# ---------------- cum (y het ec_a) ----------------
CL, V2 = [], {}
for s in SEEDS:
    L = R.load_legs_minute(R.load_legs(I.OFF[s]))
    L = L.reset_index(drop=True)
    L["_ord"] = np.arange(len(L))
    V2[s] = dict(n_leg=int(len(L)), sum_pnl_leg=float(L["pnl"].sum()))
    for (sym, m1), g in L.groupby(["sym", "m1"], sort=False):
        mn = g["m0"].min()
        o = g[g["m0"] == mn].sort_values("_ord").iloc[0]
        CL.append(dict(seed=s, sym=str(sym) + "USDT", m1=int(m1), M=int(o["m0"]), start=str(o["start"]).strip(),
                       level=str(o["level"]).strip(), dow=float(o["dow"]), up=float(o["up"]), dow15m=float(o["dow15m"]),
                       sp=float(o["symbolPred"]) if pd.notna(o["symbolPred"]) else np.nan,
                       pnl=float(g["pnl"].sum()), ts=bool((g["status"].astype(str).str.strip() == "STOP_LOSS_DONE").any()),
                       n_leg=int(len(g))))
C = pd.DataFrame(CL)
C["t7"] = DAY0 + pd.to_timedelta(C["M"], unit="m") + pd.Timedelta(hours=7)
C["year"] = C["t7"].dt.year
C["period"] = np.where(C["t7"] < D_END, "D", np.where(C["t7"] < C_END, "C", "X"))
log.info("tong cum %d; level chan mo: %s; period: %s", len(C), C["level"].value_counts().to_dict(),
         C["period"].value_counts().to_dict())

# ---- V2: khop ENTRY_CONFIRM ----
ecj = json.load(open("/home/ubuntu/claude_master/entry_confirm/ec_a.json"))["V1"]
pq = pd.read_parquet("/home/ubuntu/claude_master/entry_confirm/ec_a_clusters.parquet")
mg = C.merge(pq[["seed", "sym", "m1", "M", "pnl", "ts"]], on=["seed", "sym", "m1"], how="outer", suffixes=("", "_ec"), indicator=True)
V2["parquet_join"] = dict(n_ours=int(len(C)), n_ec=int(len(pq)), both=int((mg["_merge"] == "both").sum()),
                          M_eq=int((mg["M"] == mg["M_ec"]).sum()), pnl_eq=int((np.abs(mg["pnl"] - mg["pnl_ec"]) < 1e-6).sum()),
                          ts_eq=int((mg["ts"] == mg["ts_ec"]).sum()))
V2["parquet_join"]["ok"] = bool(all(V2["parquet_join"][k] == len(C) == len(pq) for k in ("both", "M_eq", "pnl_eq", "ts_eq")))
okv2 = V2["parquet_join"]["ok"]
for s in SEEDS:
    g = C[C["seed"] == s]
    V2[s].update(n_cluster=int(len(g)), sum_pnl_cluster=float(g["pnl"].sum()), ec_sum_pnl=float(ecj[s]["sum_pnl"]),
                 ec_n_cluster=int(ecj[s]["n_cluster"]), sum_pnl_selector=float(g.loc[g["level"] == "PREDICT_SYMBOL_TRADE", "pnl"].sum()),
                 sum_pnl_bigdown_opener=float(g.loc[g["level"] != "PREDICT_SYMBOL_TRADE", "pnl"].sum()),
                 n_selector=int((g["level"] == "PREDICT_SYMBOL_TRADE").sum()))
    V2[s]["diff"] = V2[s]["sum_pnl_cluster"] - V2[s]["ec_sum_pnl"]
    okv2 = okv2 and abs(V2[s]["diff"]) < 1e-3 and V2[s]["n_cluster"] == V2[s]["ec_n_cluster"]
    log.info("V2 %-6s cum %d (ec %d) sumPnL %.2f (ec %.2f, lech %+.4f) | selector %d cum %.2f | BIG_DOWN-mo %.2f",
             s, V2[s]["n_cluster"], V2[s]["ec_n_cluster"], V2[s]["sum_pnl_cluster"], V2[s]["ec_sum_pnl"], V2[s]["diff"],
             V2[s]["n_selector"], V2[s]["sum_pnl_selector"], V2[s]["sum_pnl_bigdown_opener"])
V2["ok"] = bool(okv2)
log.info("V2 parquet join %s -> %s", V2["parquet_join"], "OK" if V2["ok"] else "FAIL")

# ---------------- SELRANK log (thu tu sim ghi) ----------------
SR = []
for s in SEEDS:
    fn = os.path.join(SIMD, I.OFF[s], "logs", "full.log")
    with open(fn, errors="replace") as f:
        for line in f:
            if "SELRANK" in line:
                m = SELRE.search(line)
                if m:
                    SR.append(dict(seed=s, sym=m.group(1), start=m.group(2), tMs=int(m.group(3)), selRank=int(m.group(4)),
                                   sp_log=float(m.group(5))))
SR = pd.DataFrame(SR)
dupe = int(SR.duplicated(["seed", "sym", "start"]).sum())
S = C[C["level"] == "PREDICT_SYMBOL_TRADE"].copy()
n_before = len(S)
S = S.merge(SR, on=["seed", "sym", "start"], how="left")
assert len(S) == n_before, "SELRANK join nhan ban dong"
V1 = {}
V1["selrank_join"] = dict(n_selector_cluster=int(len(S)), n_log=int(len(SR)), dup_log=dupe, matched=int(S["selRank"].notna().sum()),
                          sp_eq=int((np.abs(S["sp"] - S["sp_log"]) <= 1e-6 * np.maximum(1, np.abs(S["sp"]))).sum()),
                          tMs_eq=int((S["tMs"] == (pd.to_datetime(S["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
                                                   - pd.Timestamp("1970-01-01")) // pd.Timedelta(milliseconds=1)).sum()),
                          M_eq_tMs=int((S["tMs"] == (S["M"] * 60000 + int((DAY0 - pd.Timestamp("1970-01-01")) // pd.Timedelta(milliseconds=1)))).sum()))
log.info("V1 SELRANK join: %s", V1["selrank_join"])
# so luong selRank log == so chan PREDICT_SYMBOL_TRADE (moi chan selector ghi 1 dong)
assert S["selRank"].notna().all(), "SELRANK join khong 100%"

# ---------------- dot + hang ----------------
S = S.sort_values(["seed", "M", "sp", "selRank"], kind="mergesort").reset_index(drop=True)
S["r"] = S.groupby(["seed", "M"]).cumcount() + 1
S["nW"] = S.groupby(["seed", "M"])["r"].transform("max")
# huong: trong dot, thu tu theo sp tang phai trung thu tu selRank tang
S["sr_ord"] = S.groupby(["seed", "M"])["selRank"].rank(method="first").astype(int)
dir_ok = float((S["sr_ord"] == S["r"]).mean())
wconst = S.groupby(["seed", "M"])[VARS].nunique().max()
# chan BIG_DOWN cung phut: cung marketData?
B = C[C["level"] != "PREDICT_SYMBOL_TRADE"][["seed", "M"] + VARS]
bw = B.merge(S.groupby(["seed", "M"])[VARS].first().reset_index(), on=["seed", "M"], suffixes=("_b", ""))
bd_same = int(np.all([np.abs(bw[v + "_b"] - bw[v]).max() < 1e-9 for v in VARS])) if len(bw) else -1


def grp(r):
    for k, (a, b) in RG.items():
        if a <= r <= b:
            return k
    return "R>24"


S["Rg"] = S["r"].map(grp)
S["Rg_sel"] = S["selRank"].map(grp)
V3 = dict(max_r=int(S["r"].max()), n_r_gt24=int((S["r"] > 24).sum()), max_selRank=int(S["selRank"].max()),
          r_eq_nW_at_max=bool((S.groupby(["seed", "M"])["r"].max() == S.groupby(["seed", "M"]).size()).all()),
          r_le_selRank=float((S["r"] <= S["selRank"]).mean()), order_sp_asc_eq_selRank=dir_ok,
          wave_var_const=bool((wconst <= 1).all()), wave_var_nunique_max={k: int(v) for k, v in wconst.items()},
          bigdown_same_minute_same_market=bd_same, n_bigdown_same_minute=int(len(bw)),
          frac_Rgroup_differs_vs_selRank=float((S["Rg"] != S["Rg_sel"]).mean()),
          n_wave=int(S.groupby(["seed", "M"]).ngroups), wave_size_dist=S.groupby(["seed", "M"]).size().describe().to_dict())
V3["ok"] = bool(V3["n_r_gt24"] == 0 and V3["r_eq_nW_at_max"] and V3["wave_var_const"] and dir_ok == 1.0)
log.info("V3 %s -> %s", V3, "OK" if V3["ok"] else "CHECK")
log.info("period selector: %s ; X (ngoai D/C): %d", S["period"].value_counts().to_dict(), int((S["period"] == "X").sum()))

# ---------------- V1 phu: so voi market.bin ----------------
MB = "/home/ubuntu/marketdump/market.bin"
V1["market_bin"] = {"file": MB}
try:
    raw = np.fromfile(MB, dtype=np.uint8)
    n = int(np.frombuffer(raw[:4].tobytes(), dtype=">i4")[0])
    rec = np.frombuffer(raw[4:4 + n * 20].tobytes(), dtype=np.dtype([("ts", ">i8"), ("d", ">f4"), ("u", ">f4"), ("d15", ">f4")]))
    mk = pd.DataFrame({"tMs": rec["ts"].astype(np.int64), "d": rec["d"].astype(np.float64), "u": rec["u"].astype(np.float64),
                       "d15": rec["d15"].astype(np.float64)}).drop_duplicates("tMs", keep="last")
    Wm = S.groupby(["seed", "M"]).first().reset_index()[["seed", "M", "tMs"] + VARS]
    j = Wm.merge(mk, on="tMs", how="left")
    found = j["d"].notna()
    tol = lambda a, b: np.abs(a - b) <= 1e-6 + 1e-4 * np.abs(b)  # noqa: E731  (printDone ghi float->string)
    eq = found & tol(j["dow"], j["d"]) & tol(j["up"], j["u"]) & tol(j["dow15m"], j["d15"])
    # thu lech 1 phut (kiem phut vao co dung la phut cua marketData)
    jm1 = Wm.assign(tMs=Wm["tMs"] - 60000).merge(mk, on="tMs", how="left")
    eqm1 = jm1["d"].notna() & tol(jm1["dow"], jm1["d"]) & tol(jm1["up"], jm1["u"]) & tol(jm1["dow15m"], jm1["d15"])
    V1["market_bin"].update(n_rec=n, ts_min=int(mk["tMs"].min()), ts_max=int(mk["tMs"].max()), n_wave=int(len(Wm)),
                            found=int(found.sum()), eq_same_minute=int(eq.sum()), eq_minute_minus1=int(eqm1.sum()),
                            examples=j.head(3)[["seed", "tMs", "dow", "d", "up", "u", "dow15m", "d15"]].to_dict("records"))
    log.info("V1 market.bin: %s", {k: v for k, v in V1["market_bin"].items() if k != "examples"})
    for e in V1["market_bin"]["examples"]:
        log.info("   %s", e)
except Exception as e:  # noqa: BLE001
    V1["market_bin"]["error"] = repr(e)
    log.info("V1 market.bin loi: %r", e)

# ---------------- dot -> tercile (cutoff CHI tu D) ----------------
W = S.groupby(["seed", "M"]).agg(period=("period", "first"), dow=("dow", "first"), up=("up", "first"),
                                  dow15m=("dow15m", "first"), mpnl=("pnl", "mean"), n=("pnl", "size")).reset_index()
WD = W[W["period"] == "D"]
CUT = {v: [float(x) for x in np.quantile(WD[v].to_numpy(), [1 / 3, 2 / 3])] for v in VARS}
V4 = dict(n_wave_D_used=int(len(WD)), periods_in_cut_sample=sorted(WD["period"].unique().tolist()),
          note="cutoff = np.quantile tren dot D gop 8 seed; chon o chi doc bang D")
assert V4["periods_in_cut_sample"] == ["D"]
log.info("cutoff (D, %d dot): %s", len(WD), CUT)


def terc(x, c):
    return np.where(x <= c[0], "T1", np.where(x <= c[1], "T2", "T3"))


for v in VARS:
    W[v + "_T"] = terc(W[v].to_numpy(), CUT[v])
    S[v + "_T"] = terc(S[v].to_numpy(), CUT[v])
TSHARE = {p: {v: W[W["period"] == p][v + "_T"].value_counts(normalize=True).sort_index().round(4).to_dict() for v in VARS} for p in PERIODS}
log.info("ty le dot theo tercile: %s", TSHARE)


def cell(g):
    """g: cum trong 1 o (moi seed). Tra so lieu tong hop TB 8 seed."""
    per = {s: float(g.loc[g["seed"] == s, "pnl"].sum()) for s in SEEDS}
    nn = len(g)
    return dict(n_per_seed=nn / NS, pnl_per_cluster=float(g["pnl"].mean()) if nn else np.nan,
                win=float((g["pnl"] > 0).mean()) if nn else np.nan, ts_rate=float(g["ts"].mean()) if nn else np.nan,
                sum_pnl_per_seed=float(np.mean(list(per.values()))), sum_by_seed=per)


TAB = {}
for p in PERIODS:
    SP = S[S["period"] == p]
    TAB[p] = {}
    for v in VARS:
        TAB[p][v] = {}
        for t in TS:
            gt = SP[SP[v + "_T"] == t]
            TAB[p][v][t] = {rg: cell(gt[gt["Rg"] == rg]) for rg in RG}
            g23 = gt[gt["Rg"].isin(["R2", "R3"])]
            c23 = cell(g23)
            TAB[p][v][t]["R2+R3"] = dict(sum_pnl_per_seed=c23["sum_pnl_per_seed"], sum_by_seed=c23["sum_by_seed"],
                                         n_seed_neg=int(sum(x < 0 for x in c23["sum_by_seed"].values())),
                                         n_per_seed=c23["n_per_seed"], pnl_per_cluster=c23["pnl_per_cluster"])
            TAB[p][v][t]["ALL"] = cell(gt)
BASE = {p: {rg: cell(S[(S["period"] == p) & (S["Rg"] == rg)]) for rg in RG} for p in PERIODS}

# ---------------- in bang ----------------
for p in PERIODS:
    log.info("==== %s ==== baseline (khong cat): %s", p, {rg: (round(BASE[p][rg]["n_per_seed"], 1), round(BASE[p][rg]["pnl_per_cluster"], 2),
                                                           round(BASE[p][rg]["sum_pnl_per_seed"])) for rg in RG})
    for v in VARS:
        for t in TS:
            for rg in RG:
                q = TAB[p][v][t][rg]
                log.info("%s %-6s %s %s n/seed %6.1f PnL/cum %+7.2f win %5.1f%% ts %5.1f%% SumPnL/seed %+9.0f",
                         p, v, t, rg, q["n_per_seed"], q["pnl_per_cluster"], 100 * q["win"], 100 * q["ts_rate"], q["sum_pnl_per_seed"])
            q = TAB[p][v][t]["R2+R3"]
            log.info("%s %-6s %s R2+R3 SumPnL/seed %+9.0f, seed am %d/8 | theo seed %s", p, v, t, q["sum_pnl_per_seed"], q["n_seed_neg"],
                     {k: round(x) for k, x in q["sum_by_seed"].items()})

# ---------------- luat (chon tren D) ----------------
cands = []
for v in VARS:
    for t in TS:
        q = TAB["D"][v][t]["R2+R3"]
        if q["sum_pnl_per_seed"] < 0 and q["n_seed_neg"] >= 6:
            cands.append((q["sum_pnl_per_seed"], v, t))
cands.sort()
RULE = dict(candidates_D=[dict(var=v, terc=t, sum_r23_D=x) for x, v, t in cands])
if not cands:
    RULE.update(selected=None, verdict="DONG - khong o nao dat D")
else:
    x, v, t = cands[0]
    qc = TAB["C"][v][t]["R2+R3"]
    dP = -qc["sum_pnl_per_seed"]
    c1, c2, c3 = qc["sum_pnl_per_seed"] < 0, qc["n_seed_neg"] >= 6, dP > 5000
    RULE.update(selected=dict(var=v, terc=t, sum_r23_D=x, n_seed_neg_D=TAB["D"][v][t]["R2+R3"]["n_seed_neg"]),
                confirm_C=dict(sum_r23_C=qc["sum_pnl_per_seed"], n_seed_neg_C=qc["n_seed_neg"], dpnl_raw_C=dP,
                               c_mean_neg=bool(c1), c_6of8=bool(c2), c_dpnl_gt5000=bool(c3)),
                verdict="DAT D+C -> viet prereg tang B" if (c1 and c2 and c3) else "DONG - dat D nhung truot C")
loosen = []
for v in VARS:
    for t in TS:
        a, b = TAB["D"][v][t]["R1"]["pnl_per_cluster"], TAB["D"][v][t]["R3"]["pnl_per_cluster"]
        if pd.notna(a) and pd.notna(b) and b > a:
            loosen.append(dict(var=v, terc=t, R1=a, R3=b))
RULE["loosen_descr_D_R3_gt_R1"] = loosen
log.info("LUAT: %s", RULE)

# ---------------- Spearman theo dot ----------------
SPR = {}
for p in PERIODS:
    Wp = W[W["period"] == p]
    SPR[p] = {}
    for v in VARS:
        rho, pv = spearmanr(Wp[v], Wp["mpnl"])
        SPR[p][v] = dict(rho=float(rho), p=float(pv), n_wave=int(len(Wp)))
log.info("Spearman dot (var vs PnL/cum TB dot): %s", SPR)

# ---------------- V1 ket luan code ----------------
V1["code"] = ("TraceOrderDone.printOrderTestDone: cot dow/up/dow15m = order.marketData.rateDownAvg/rateUpAvg/rateDown15MAvg; "
              "createOrder gan order.marketData = time2MarketData.get(time) cua tick vao (timeStart = ticker.startTime); "
              "symbolPred = gia tri float trong time2SymbolPred[time] (pNoPump S1) ghi tu object LEG; "
              "symbol2Pred sort TANG (preprocessFundingData), selectCands lay SELECTOR_RANK_TOPK=24 phan tu DAU => "
              "rank 1 = symbolPred NHO nhat (nho = tot). Prereg ghi 'giam dan' -> SAI chieu; dung TANG dan (thu tu sim dung).")
V1["ok"] = bool(V1["selrank_join"]["matched"] == V1["selrank_join"]["n_selector_cluster"]
                and V1["selrank_join"]["sp_eq"] == V1["selrank_join"]["n_selector_cluster"])

out = dict(prereg="PREREG_MD_STRAT.md@142c87fb", seeds=SEEDS, split=dict(D="2021-07..2023-12 (+07 cua M)", C="2024-01..2025-12 (+07)"),
           rank_def="r = thu tu symbolPred tang dan trong dot (seed,M) cua cum selector; tie -> selRank log",
           wave_def="dot = cum co chan mo PREDICT_SYMBOL_TRADE cung (seed, M); cum mo bang BIG_DOWN (symbolPred null) loai khoi cat lop",
           cutoffs_D=CUT, tercile_share=TSHARE, V1=V1, V2=V2, V3=V3, V4=V4, baseline=BASE, table=TAB, rule=RULE, spearman=SPR,
           limits="offline: bo lenh hang 6-24 co the giai phong von/slot -> lenh khac vao (TICK_BLOCK) => dPnL offline co the ao")
json.dump(out, open(os.path.join(OUTD, "ms_a.json"), "w"), indent=1, default=float)
S.drop(columns=["t7"]).to_parquet(os.path.join(OUTD, "ms_a_clusters.parquet"))
log.info("ghi %s", os.path.join(OUTD, "ms_a.json"))
