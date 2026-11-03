"""GATE_SMART Pha 0b kernel (prereg 6d92cdba §2.3): forward return 24h/72h tu close phut sau, cho o near-miss / pass_low.
Input: dataset gsm-s4-cells (s4_cells.parquet), vz-kline1m-2022..2026. Output /kaggle/working/s4_fwd.parquet"""
import glob, json, sys, time
import numpy as np, pandas as pd, pyarrow.parquet as pq
M1, H24, H72 = 60000, 86400000, 3 * 86400000
cp = [p for p in glob.glob("/kaggle/input/**/s4_cells.parquet", recursive=True)]
assert cp, "thieu s4_cells"
X = pd.read_parquet(cp[0])
F = {}
for p in glob.glob("/kaggle/input/**/kline1m-*.parquet", recursive=True):
    F[p.split("kline1m-")[-1][:7]] = p
print("months", len(F), min(F), max(F), flush=True)
X["ym"] = pd.to_datetime(X.ts, unit="ms").dt.strftime("%Y-%m")
out = []
t0 = time.time()
for ym, g in X.groupby("ym"):
    y, m = int(ym[:4]), int(ym[5:])
    nx = "%04d-%02d" % (y + (m == 12), 1 if m == 12 else m + 1)
    syms = sorted(g.sym.unique())
    parts = []
    for k in (ym, nx):
        if k in F:
            parts.append(pq.read_table(F[k], columns=["ts", "sym", "close"], filters=[("sym", "in", syms)]).to_pandas())
    K = pd.concat(parts, ignore_index=True).drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"])
    idx = {s: (d.ts.to_numpy(np.int64), d.close.to_numpy(np.float64)) for s, d in K.groupby("sym")}
    res = {"c0": [], "c24": [], "c72": []}
    for s, t in zip(g.sym.tolist(), g.ts.tolist()):
        tt, cc = idx.get(s, (np.zeros(0, np.int64), np.zeros(0)))
        for key, off in (("c0", M1), ("c24", M1 + H24), ("c72", M1 + H72)):
            j = np.searchsorted(tt, t + off, "right") - 1
            ok = j >= 0 and len(tt) and (t + off - tt[max(j, 0)]) <= 5 * M1
            res[key].append(cc[j] if ok else np.nan)
    gg = g.copy()
    for k, v in res.items():
        gg[k] = v
    out.append(gg)
    print(ym, len(g), "nan72", int(np.isnan(gg.c72).sum()), round(time.time() - t0), flush=True)
R = pd.concat(out, ignore_index=True)
R.to_parquet("/kaggle/working/s4_fwd.parquet", index=False)
json.dump(dict(n=len(R), nan0=int(R.c0.isna().sum()), nan72=int(R.c72.isna().sum())), open("/kaggle/working/s4_meta.json", "w"))
print("S4_DONE", len(R))
