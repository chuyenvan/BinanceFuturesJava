"""LAB2 — bo sung g1lite (NHAN THAT CUA C2b) va g1_replay vao phep so nhan-vs-ROI-that,
va TACH RIENG anh huong cua CHAN TROI (4h/24h/72h) voi CONG THUC (raw / trailing-approx / arm).
Mo ta, khong phai kiem gia thuyet. CHI DEV.
"""
import glob
import logging
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/cov/LAB2.out", "w"),
                              logging.StreamHandler()])
LG = logging.getLogger("lab2")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label

VN = 7 * 3600 * 1000
Q = 900_000

df = pd.read_csv("/home/ubuntu/java/devrun/C2b/storage/printDone.csv")
df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
df["ts"] = (pd.to_datetime(df.start, format="%Y%m%d %H:%M").astype("int64") // 10**6 - VN)
df["ts"] = (df["ts"] // Q) * Q
df["symbol"] = df.sym + "USDT"
df["ret"] = df.pnl / df.margin
pnp = "symbolPred" if df["symbolPred"].notna().any() else "risk4h"
df["pnp"] = df[pnp]
LG.info("C2b lenh PST=%d | ret TB=%.4f win=%.3f", len(df), df.ret.mean(), (df.ret > 0).mean())

H = ["4h", "24h", "72h"]
cols = ["tEpochMs", "symbol"] + [f"{k}_{h}" for h in H for k in ("maxFav", "maxAdv", "retEnd")]
files = (sorted(glob.glob("/home/ubuntu/label_15m/funding_label_2022*.pb"))
         + sorted(glob.glob("/home/ubuntu/label_15m/funding_label_2023*.pb"))
         + sorted(glob.glob("/home/ubuntu/label_15m/funding_label_20240101*.pb"))
         + sorted(glob.glob("/home/ubuntu/label_15m/funding_label_20240401*.pb")))
parts, cs = [], []
want = df[["symbol", "ts"]].drop_duplicates()
for f in files:
    L = read_label(f, usecols=cols)
    for h in H:
        L[f"g1_{h}"] = np.where(L[f"maxFav_{h}"] >= 0.05,
                                L[f"maxFav_{h}"] - np.minimum(0.5 * L[f"maxFav_{h}"], 0.08),
                                L[f"retEnd_{h}"])
    L["g1arm7_72h"] = np.where(L["maxFav_72h"] >= 0.07,
                               L["maxFav_72h"] - np.minimum(0.5 * L["maxFav_72h"], 0.08),
                               L["retEnd_72h"])
    L["pathq_72h"] = L["maxFav_72h"] / (L["maxAdv_72h"].abs() + 0.01)
    agg = {f"med_g1_{h}": (f"g1_{h}", "median") for h in H}
    agg["med_fav72"] = ("maxFav_72h", "median")
    cs.append(L.groupby("tEpochMs").agg(**agg))
    for c in ["g1_72h", "g1_24h", "g1_4h", "maxFav_72h", "pathq_72h", "g1arm7_72h"]:
        L[f"rk_{c}"] = L.groupby("tEpochMs")[c].rank(pct=True)
    parts.append(L.merge(want, left_on=["symbol", "tEpochMs"], right_on=["symbol", "ts"],
                         how="inner"))
Lb = pd.concat(parts)
CS = pd.concat(cs)
m = df.merge(Lb.drop(columns=["ts"]), left_on=["symbol", "ts"],
             right_on=["symbol", "tEpochMs"], how="inner").merge(
    CS, left_on="ts", right_index=True, how="left")
LG.info("join label = %d (%.1f%%)", len(m), 100 * len(m) / len(df))

# g1_replay tu path_labels (pool da lay mau => bao cao do phu)
mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
sym2id = dict(zip(mp.symbol, mp.symId))
m["symId"] = m.symbol.map(sym2id)
PL = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                     columns=["ts", "sym", "g1_replay"])
m = m.merge(PL.rename(columns={"sym": "symId"}), on=["ts", "symId"], how="left")
LG.info("co g1_replay: %d / %d (%.1f%%)", m.g1_replay.notna().sum(), len(m),
        100 * m.g1_replay.notna().mean())


def rep(name, x):
    ok = x.notna() & m.ret.notna()
    if ok.sum() < 50 or x[ok].nunique() < 2:
        LG.info("  %-42s (khong du du lieu, n=%d)", name, ok.sum())
        return
    r = spearmanr(x[ok], m.ret[ok]).correlation
    auc = roc_auc_score((m.ret[ok] > 0).astype(int), x[ok])
    q = pd.qcut(x[ok].rank(method="first"), 5, labels=False)
    r5 = m.ret[ok].groupby(q).mean()
    LG.info("  %-42s spearman=%+.3f AUC=%.3f n=%4d | Q1..Q5 = %s%%", name, r, auc, ok.sum(),
            " ".join(f"{v*100:+.1f}" for v in r5.values))


LG.info("\n=== A. NHAN THAT DANG DUNG ===")
rep("g1lite 72h  <= NHAN THAT CUA S1/C2b", m.g1_72h)
rep("g1_replay 72h (mo phong exit G1)", m.g1_replay)
rep("-pNoPump = diem G015 dang deploy", -m.pnp)
rep("maxFav_4h>=6% <= NHAN THAT CUA G015", (m.maxFav_4h >= 0.06).astype(float))

LG.info("\n=== B. TACH CHAN TROI (cung cong thuc g1lite, doi h) ===")
for h in ["4h", "24h", "72h"]:
    rep(f"g1lite {h}", m[f"g1_{h}"])

LG.info("\n=== C. TACH CONG THUC (cung chan troi 72h) ===")
rep("maxFav_72h (tho)", m.maxFav_72h)
rep("g1lite 72h (arm 5%, cap 8%)", m.g1_72h)
rep("g1lite 72h ARM 7% (khop C2b that)", m.g1arm7_72h)
rep("retEnd_72h", m.retEnd_72h)
rep("pathq 72h = fav/abs(adv)", m.pathq_72h)

LG.info("\n=== D. CROSS-SECTIONAL (tru trung vi / rank trong tick) ===")
rep("g1lite 72h - median(univ)", m.g1_72h - m.med_g1_72h)
rep("rank pct g1lite 72h trong tick", m.rk_g1_72h)
rep("rank pct maxFav_72h trong tick", m.rk_maxFav_72h)
rep("rank pct pathq 72h trong tick", m.rk_pathq_72h)
rep("rank pct g1lite ARM7 72h", m.rk_g1arm7_72h)

LG.info("\n=== E. WITHIN-TICK (vai tro SELECTOR), tick co >=4 lenh ===")
g = m.groupby("ts")
big = [k for k, v in g.size().items() if v >= 4]
LG.info("  ticks >=4 lenh: %d (tong %d lenh)", len(big), int(sum(g.size()[big])))
cand = {
    "g1lite 72h  <= NHAN C2b": m.g1_72h,
    "g1lite 72h ARM7": m.g1arm7_72h,
    "maxFav_72h": m.maxFav_72h,
    "pathq 72h": m.pathq_72h,
    "g1_replay 72h": m.g1_replay,
    "retEnd_72h": m.retEnd_72h,
    "g1lite 24h": m.g1_24h,
    "g1lite 4h": m.g1_4h,
    "maxFav_4h": m.maxFav_4h,
    "-pNoPump (G015 deploy)": -m.pnp,
}
for name, x in cand.items():
    rs = []
    for k in big:
        idx = g.groups[k]
        xx, rr = x.loc[idx], m.ret.loc[idx]
        ok = xx.notna() & rr.notna()
        if ok.sum() >= 4 and xx[ok].nunique() > 1 and rr[ok].nunique() > 1:
            rs.append(spearmanr(xx[ok], rr[ok]).correlation)
    rs = np.array(rs, dtype=float)
    LG.info("  %-28s rho TB=%+.3f  %%tick>0=%3.0f%%  n=%d", name,
            np.nanmean(rs), 100 * np.nanmean(rs > 0), len(rs))
LG.info("\nDONE_LAB2")
