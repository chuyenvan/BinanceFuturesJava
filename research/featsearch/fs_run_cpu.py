"""FS do chinh — CPU tren Oracle (moi truong tai lap pred_s1a2 spearman=1.000000).
19 nhanh: base7 + 2 doi chung seed + 16 ung vien. Moi nhanh: 1 dong jsonl + fsync.
Theo PREREG_FS.md commit 992edd5. CHI DEV."""
import logging, sys, os, json, time
import numpy as np, pandas as pd, xgboost as xgb
from scipy.stats import spearmanr
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)

H = 3600000
TZ = 7 * H
PURGE = 72 * H
OUT = "/home/ubuntu/fs/out"
os.makedirs(OUT, exist_ok=True)
JL = f"{OUT}/fs_results_cpu.jsonl"
TKP = f"{OUT}/fs_ticks_cpu.parquet"
BASE7 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d"]
CANDS = ["fs_dvol_7d", "fs_dvol_ratio", "fs_amihud_7d", "fs_trdsize_7d",
         "fs_fund_sum_7d", "fs_fund_slope", "fs_fund_persist",
         "fs_wick_up_7d", "fs_body_ratio_7d", "fs_close_vwap_7d",
         "fs_taker_buy_7d", "fs_up_streak",
         "fs_dd_speed", "fs_pos_7d", "fs_dd_term", "fs_noise"]
CUT_D = ["20220101", "20220401", "20220701", "20221001", "20230101",
         "20230401", "20230701", "20231001", "20240101", "20240401"]
CUT = [int(pd.Timestamp(f"{c[:4]}-{c[4:6]}-{c[6:]}").value // 1e6) - TZ for c in CUT_D]
SELECT_END = int(pd.Timestamp("2024-01-01").value // 1e6) - TZ
T_END = 1719792000000

D = pd.read_parquet("/home/ubuntu/fs/pack/fsdata.parquet")
assert D.ts.max() < T_END, "LEAK ts >= 2024-07-01"
D["med"] = D.groupby("ts").g1lite.transform("median")
D["rel"] = D.g1lite - D.med
D["rkq"] = D.groupby("ts").rel.rank(pct=True, method="first")
D["rel5"] = np.minimum((D.rkq * 5).astype(int), 4)
L.info("pack %s xgb %s", D.shape, xgb.__version__)


def emit(rec):
    with open(JL, "a") as f:
        f.write(json.dumps(rec, default=float) + "\n")
        f.flush()
        os.fsync(f.fileno())


def train_arm(name, FE, seed=42):
    t0 = time.time()
    preds = []
    for i, c in enumerate(CUT):
        hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 1e6) - TZ
        tr = D[D.ts < c - PURGE].sort_values("ts")
        oos = D[(D.ts >= c) & (D.ts < hi)].sort_values("ts")
        assert tr.ts.max() < c, "LEAK"
        m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4,
                          learning_rate=0.05, subsample=0.8, colsample_bytree=0.8,
                          min_child_weight=50, n_jobs=4, tree_method="hist",
                          random_state=seed, lambdarank_pair_method="topk",
                          lambdarank_num_pair_per_sample=8)
        m.fit(tr[FE], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
        preds.append(oos[["ts", "sym"]].assign(score=-m.predict(oos[FE]), fold=i))
    P = pd.concat(preds, ignore_index=True)
    L.info("%s: %d dong OOS %.0fs", name, len(P), time.time() - t0)
    return P


def per_tick(P):
    M = P.merge(D[["ts", "sym", "g1lite", "g1_replay"]], on=["ts", "sym"], how="left")
    rows = []
    for outc in ("g1lite", "g1_replay"):
        S = M.dropna(subset=[outc])
        for ts, g in S.groupby("ts"):
            if len(g) < 10:
                continue
            rows.append((ts, outc, spearmanr(-g.score.to_numpy(),
                                             g[outc].to_numpy()).correlation, len(g)))
    return pd.DataFrame(rows, columns=["ts", "outc", "ic", "n"]).dropna(subset=["ic"])


def edge5(P, outc):
    M = P.merge(D[["ts", "sym", outc]], on=["ts", "sym"], how="left").dropna(subset=[outc])
    M["rk"] = M.groupby("ts").score.rank(method="first")
    return float((M[M.rk <= 5].groupby("ts")[outc].mean()
                  - M.groupby("ts")[outc].mean()).mean())


ARMS = [("base7", BASE7, 42), ("ctrl_seed1", BASE7, 1), ("ctrl_seed7", BASE7, 7)]
ARMS += [(f"cand_{c}", BASE7 + [c], 42) for c in CANDS]
done = set()
if os.path.exists(JL):
    for ln in open(JL):
        try:
            done.add(json.loads(ln)["arm"])
        except Exception:
            pass
TICKS = [pd.read_parquet(TKP)] if os.path.exists(TKP) and done else []
if TICKS:
    TICKS = [TICKS[0][TICKS[0].arm.isin(done)]]
L.info("da xong: %s", sorted(done))

for name, FE, seed in ARMS:
    if name in done:
        continue
    P = train_arm(name, FE, seed)
    T = per_tick(P)
    T["arm"] = name
    TICKS.append(T)
    rec = {"arm": name, "n_feat": len(FE), "seed": seed, "device": "cpu", "feats": FE}
    for outc in ("g1lite", "g1_replay"):
        t = T[T.outc == outc]
        rec[f"rankic_{outc}_all"] = float(t.ic.mean())
        rec[f"rankic_{outc}_sel"] = float(t[t.ts < SELECT_END].ic.mean())
        rec[f"rankic_{outc}_conf"] = float(t[t.ts >= SELECT_END].ic.mean())
        rec[f"ticks_{outc}"] = int(len(t))
        rec[f"edge5_{outc}"] = edge5(P, outc)
    emit(rec)
    pd.concat(TICKS, ignore_index=True).to_parquet(TKP, index=False)
    L.info("SUMM %s replay_sel=%.5f g1lite_sel=%.5f edge5_replay=%.4f", name,
           rec["rankic_g1_replay_sel"], rec["rankic_g1lite_sel"], rec["edge5_g1_replay"])
L.info("ALL_CPU_ARMS_DONE")
