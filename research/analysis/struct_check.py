"""KIEM CAU TRUC truoc khi ket luan. Cau hoi:
 1. p15 la gia tri THEO TICK (muc thi truong) hay THEO COIN?
 2. gate_dyn_ok la quyet dinh theo tick hay theo coin?
 3. pool moi tick lon bao nhieu?
 4. huong cua score: rank-IC cua score vs g1_replay TRONG cung tick la duong hay am?"""
import numpy as np, pandas as pd
from scipy.stats import spearmanr

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "p15", "dyn_thr", "gate_dyn_ok", "score_g015", "g1lite"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
L = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet", columns=["ts", "sym", "g1_replay"])
M = C.merge(P, on=["ts", "sym"], how="inner").merge(L, on=["ts", "sym"], how="left")
M["gate_ok"] = M.gate_dyn_ok.astype(bool)

print("1) p15 co bien thien TRONG mot tick khong?")
v = M.groupby("ts").p15.nunique()
print("   so gia tri p15 khac nhau moi tick: trung vi=%.0f max=%d  => %s"
      % (v.median(), v.max(), "THEO COIN" if v.median() > 1 else "THEO TICK"))
v2 = M.groupby("ts").dyn_thr.nunique()
print("   dyn_thr khac nhau moi tick: trung vi=%.0f  => %s"
      % (v2.median(), "THEO COIN" if v2.median() > 1 else "THEO TICK"))
v3 = M.groupby("ts").score_g015.nunique()
print("   score_g015 khac nhau moi tick: trung vi=%.0f" % v3.median())

print("\n2) gate_dyn_ok trong mot tick:")
gg = M.groupby("ts").gate_ok.agg(["mean", "size"])
print("   ticks TAT CA deu ok: %d | TAT CA deu khong: %d | HON HOP: %d"
      % ((gg["mean"] == 1).sum(), (gg["mean"] == 0).sum(), ((gg["mean"] > 0) & (gg["mean"] < 1)).sum()))

print("\n3) kich thuoc pool moi tick:")
print("   tat ca:      trung vi=%.0f  p90=%.0f  max=%d" % (gg["size"].median(), gg["size"].quantile(.9), gg["size"].max()))
op = M[M.gate_ok].groupby("ts").size()
cl = M[~M.gate_ok].groupby("ts").size()
print("   hang gate MO/tick:   n_tick=%d trung vi=%.0f  tong=%d" % (len(op), op.median(), op.sum()))
print("   hang gate DONG/tick: n_tick=%d trung vi=%.0f  tong=%d" % (len(cl), cl.median(), cl.sum()))

print("\n4) HUONG cua score (rank-IC trong tung tick, chi tick co >=10 hang):")
for lab, sub in [("gate MO", M[M.gate_ok]), ("gate DONG", M[~M.gate_ok]), ("tat ca", M)]:
    s = sub.dropna(subset=["g1_replay"])
    ics = []
    for t, g in s.groupby("ts"):
        if len(g) < 10:
            continue
        r = spearmanr(g.score, g.g1_replay).correlation
        if not np.isnan(r):
            ics.append(r)
    ics = np.array(ics)
    if len(ics):
        print("   %-10s n_tick=%5d  IC_tb=%+.4f  IC_trungvi=%+.4f  ti_le_IC>0=%.3f"
              % (lab, len(ics), ics.mean(), np.median(ics), (ics > 0).mean()))

print("\n5) doi chieu voi score_g015 (baseline) tren cung tap:")
for lab, sub in [("gate MO", M[M.gate_ok]), ("gate DONG", M[~M.gate_ok])]:
    s = sub.dropna(subset=["g1_replay"])
    ics = []
    for t, g in s.groupby("ts"):
        if len(g) < 10:
            continue
        r = spearmanr(g.score_g015, g.g1_replay).correlation
        if not np.isnan(r):
            ics.append(r)
    ics = np.array(ics)
    if len(ics):
        print("   %-10s n_tick=%5d  IC_tb=%+.4f  ti_le_IC>0=%.3f" % (lab, len(ics), ics.mean(), (ics > 0).mean()))
