"""SUA LOI HUONG: pred_s1*.parquet co score THAP = TOT (ghi trong memory selector_s1_ledger).
Lan truoc toi xep giam dan => dao nguoc => ket luan sai. Chay lai cho dung.
Cau hoi goc: gate co dang chan nham tick ma top-K theo S1 van lai tot khong?"""
import numpy as np, pandas as pd
from scipy.stats import spearmanr

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "p15", "dyn_thr", "gate_dyn_ok", "score_g015", "g1lite"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
R = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet", columns=["ts", "sym", "g1_replay"])
M = C.merge(P, on=["ts", "sym"], how="inner").merge(R, on=["ts", "sym"], how="left")
M["gate_ok"] = M.gate_dyn_ok.astype(bool)
M = M.dropna(subset=["g1_replay"])

print("=== rank-IC TRONG tick (score THAP=tot => dung -score) ===")
for lab, sub in [("gate MO", M[M.gate_ok]), ("gate DONG", M[~M.gate_ok])]:
    for col, nm in [("score", "S1"), ("score_g015", "G015")]:
        ics = [spearmanr(-g[col], g.g1_replay).correlation
               for _, g in sub.groupby("ts") if len(g) >= 10]
        ics = np.array([x for x in ics if not np.isnan(x)])
        print("  %-10s %-5s n_tick=%5d IC_tb=%+.4f IC_trungvi=%+.4f ti_le>0=%.3f"
              % (lab, nm, len(ics), ics.mean(), np.median(ics), (ics > 0).mean()))

def topk(df, k):
    d = df.copy(); d["rk"] = d.groupby("ts").score.rank(ascending=True, method="first")  # THAP=TOT
    return d[d.rk <= k]

def rnd(df, k=8):
    return df.sample(frac=1.0, random_state=0).groupby("ts").head(k)

print("\n===== g1_replay: GATE MO vs GATE DONG (top-K theo S1, huong DUNG) =====")
print("%-18s %8s %8s %10s %10s %10s" % ("nhom", "n_tick", "n_row", "tb", "trung_vi", "ti_le>0"))
for name, sub in [("GATE MO", M[M.gate_ok]), ("GATE DONG", M[~M.gate_ok])]:
    for k in (1, 3, 8):
        t = topk(sub, k)
        print("%-18s %8d %8d %10.4f %10.4f %10.3f"
              % (f"{name} top{k}", t.ts.nunique(), len(t), t.g1_replay.mean(),
                 t.g1_replay.median(), (t.g1_replay > 0).mean()))
    r = rnd(sub, 8)
    print("%-18s %8d %8d %10.4f %10.4f %10.3f"
          % (f"{name} random8", r.ts.nunique(), len(r), r.g1_replay.mean(),
             r.g1_replay.median(), (r.g1_replay > 0).mean()))

print("\n===== GATE DONG theo do 'suyt mo' (p15/dyn_thr), top8 S1, g1_replay =====")
D = M[~M.gate_ok].copy()
D["ratio"] = D.p15 / D.dyn_thr
D["bucket"] = pd.cut(D.ratio, [-np.inf, .25, .5, .75, .9, 1.0],
                     labels=["<0.25", "0.25-0.5", "0.5-0.75", "0.75-0.9", "0.9-1.0"])
T = topk(D, 8)
print(T.groupby("bucket", observed=True).agg(
    n_tick=("ts", "nunique"), n=("g1_replay", "size"), tb=("g1_replay", "mean"),
    trung_vi=("g1_replay", "median"), ti_le_duong=("g1_replay", lambda s: (s > 0).mean())).round(4).to_string())

print("\n(tham chieu) GATE MO top8 = %.4f | GATE MO random8 = %.4f"
      % (topk(M[M.gate_ok], 8).g1_replay.mean(), rnd(M[M.gate_ok], 8).g1_replay.mean()))
