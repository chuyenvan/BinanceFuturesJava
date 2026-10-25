"""SYMLIFE B2: tap symbol live da quet moi ngay UTC tu pull242 (s1 dump = vu tru S1 moi phut; psym = ung vien co feature).
Doc lap. Output ~/claude_master/symlife_wk/live_syms.parquet (day, symbol, src, n_min) + live_minutes.parquet (src, ts, n)"""
import os, glob, gzip, re, pandas as pd, numpy as np
P = os.path.expanduser("~/claude_master/pull242")
WK = os.path.expanduser("~/claude_master/symlife_wk")
# s1
fs = sorted(set(glob.glob(P + "/2026-10-2*/s1/s1_dump_*.csv.gz")))
seen = {}
for f in fs:
    b = os.path.basename(f)
    if b in seen:
        continue
    seen[b] = f
parts = []
for b, f in sorted(seen.items()):
    d = pd.read_csv(f, usecols=["ts", "symbol"], dtype={"ts": "int64", "symbol": str})
    parts.append(d)
S1 = pd.concat(parts).drop_duplicates()
assert S1.ts.dtype == "int64" and (S1.ts % 60000 == 0).all()
S1["day"] = pd.to_datetime(S1.ts, unit="ms").dt.strftime("%Y-%m-%d")
print("s1 files", len(seen), "rows", len(S1), "ts range", pd.to_datetime(S1.ts.min(), unit="ms"), pd.to_datetime(S1.ts.max(), unit="ms"))
m1 = S1.groupby("ts").size().rename("n").reset_index(); m1["src"] = "s1"
g1 = S1.groupby(["day", "symbol"]).size().rename("n_min").reset_index(); g1["src"] = "s1"
# psym (Java serialized HashMap<String, FundingMarketFeatures>): lay key symbol bang regex TC_STRING
rx = re.compile(rb"t\x00[\x03-\x20]([A-Z0-9]{1,30}USDT)")
rows = []
pf = {}
for f in glob.glob(P + "/2026-10-2*/psym/*/*.features.gz"):
    pf[os.path.basename(f)] = f
for b, f in pf.items():
    ts = int(b.split(".")[0])
    raw = gzip.open(f).read()
    syms = set(m.decode() for m in rx.findall(raw))
    for s in syms:
        rows.append((ts, s))
PS = pd.DataFrame(rows, columns=["ts", "symbol"])
PS["day"] = pd.to_datetime(PS.ts, unit="ms").dt.strftime("%Y-%m-%d")
print("psym files", len(pf), "rows", len(PS))
m2 = PS.groupby("ts").size().rename("n").reset_index(); m2["src"] = "psym"
g2 = PS.groupby(["day", "symbol"]).size().rename("n_min").reset_index(); g2["src"] = "psym"
pd.concat([g1, g2]).to_parquet(WK + "/live_syms.parquet", index=False)
pd.concat([m1, m2]).to_parquet(WK + "/live_minutes.parquet", index=False)
for src, m in (("s1", m1), ("psym", m2)):
    m = m.copy(); m["day"] = pd.to_datetime(m.ts, unit="ms").dt.strftime("%Y-%m-%d")
    print(src, m.groupby("day").n.describe()[["count", "min", "50%", "max"]].to_string())
print(pd.concat([g1, g2]).groupby(["src", "day"]).symbol.nunique().to_string())
