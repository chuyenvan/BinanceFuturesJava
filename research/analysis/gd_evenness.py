#!/usr/bin/env python3
"""GATEDYN evenness: do phan bo lenh theo quy (16 quy 2022Q1..2025Q4) + equity cuoi."""
import sys, os
import pandas as pd

B = "/home/ubuntu/java/devrun"
TAGS = sys.argv[1:] or ["X1_C3_FULL_PARITY_R", "X1_C3_FULL_GD88", "X1_C3_FULL_GD92", "X1_C3_FULL_GD96"]

def quarter(s):
    # time_start_format vi du "'2025-12-17 23:22:00" (co dau quote) -> 2025Q4
    s = str(s).strip().strip("'")
    y, m = s[:4], int(s[5:7])
    return f"{y}Q{(m-1)//3+1}"

rows = []
for tag in TAGS:
    df = pd.read_csv(os.path.join(B, tag, "storage/printDone.csv"))
    df["q"] = df["time_start_format"].map(quarter)
    cnt = df.groupby("q").size()
    # chi tinh 16 quy 2022Q1..2025Q4
    full = pd.Series(0, index=[f"{y}Q{q}" for y in range(2022, 2026) for q in range(1, 5)])
    cnt = cnt.reindex(full.index).fillna(0).astype(int)
    n = len(df)
    equity = None
    # equity tuong duong: margin/quantity khong co san -> doc tu log done b:
    rows.append(dict(tag=tag, n=n, std=round(cnt.std(), 1), mean=round(cnt.mean(), 1),
                     cv=round(cnt.std() / cnt.mean(), 3) if cnt.mean() > 0 else float("nan"),
                     minq=int(cnt.min()), maxq=int(cnt.max()),
                     qmin_name=cnt.idxmin(), qmax_name=cnt.idxmax()))

out = pd.DataFrame(rows)
pd.set_option("display.width", 200)
print(out.to_string(index=False))
print()
print("Chi tiet n/quy:")
for tag in TAGS:
    df = pd.read_csv(os.path.join(B, tag, "storage/printDone.csv"))
    df["q"] = df["time_start_format"].map(quarter)
    cnt = df.groupby("q").size()
    full = pd.Series(0, index=[f"{y}Q{q}" for y in range(2022, 2026) for q in range(1, 5)])
    cnt = cnt.reindex(full.index).fillna(0).astype(int)
    print(f"{tag}: " + " ".join(f"{q}:{v}" for q, v in cnt.items()))
