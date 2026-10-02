#!/usr/bin/env python3
"""AUDIT LONG_LEVERS 2026-10-02 — HIEU CHUAN THUOC: paired per-trade dPnL (size-neutral) cho cac arm exit DA CHAY.
Muc dich: do do rong CI cua thuoc GHEP CAP (khop lenh theo sym+start+level) so voi CI dCalmar da cong bo.
KHONG dung de chon arm (post-hoc, k=9 arm) — chi de uoc MDE cua thuoc. 0-sim, chi doc printDone Kaggle da co.
dPnL_i = (profit_arm - profit_base)/100 * notional_base  (bo troi size do equity khac nhau);
lenh chi co o 1 phia: dong gop +/- profit/100*notional cua chinh no. CI block-72h theo gio vao, 2000 rep, seed 20260905.
"""
import sys, json
import numpy as np, pandas as pd

BASE = "/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv"
B0 = "de-p1"
ARMS = ["trail-g2-t0", "trail-g2-a5", "trail-g2-gv3", "trail-g2-lad", "trail-g2-a5lad",
        "trail2-g2-prop50", "trail2-g2-prop30", "trail2-g2-flat5", "htd-h1"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/ll_paired.json"


def ld(tag):
    d = pd.read_csv(BASE % tag)
    d["t0"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    d["notional"] = d.quantity * d.entry
    d["key"] = d.sym + "|" + d.start + "|" + d.level
    d = d.drop_duplicates("key")
    return d.set_index("key")


b = ld(B0)
rng = np.random.default_rng(20260905)
R = {"base": B0, "n_base": int(len(b)), "sum_profit_x_notional_base": float((b.profit / 100 * b.notional).sum())}
for a in ARMS:
    try:
        x = ld(a)
    except Exception as e:
        R[a] = {"err": str(e)}; continue
    common = b.index.intersection(x.index)
    ob = b.index.difference(x.index); oa = x.index.difference(b.index)
    dm = (x.loc[common, "profit"] - b.loc[common, "profit"]) / 100 * b.loc[common, "notional"]
    db = -(b.loc[ob, "profit"] / 100 * b.loc[ob, "notional"])
    da = x.loc[oa, "profit"] / 100 * x.loc[oa, "notional"]
    t = pd.concat([pd.DataFrame({"t0": b.loc[common, "t0"], "v": dm}), pd.DataFrame({"t0": b.loc[ob, "t0"], "v": db}),
                   pd.DataFrame({"t0": x.loc[oa, "t0"], "v": da})])
    t["blk"] = ((t.t0 - pd.Timestamp("2021-07-01")).dt.total_seconds() // (72 * 3600)).astype(int)
    s = t.groupby("blk").v.sum().values
    bs = np.array([s[rng.integers(0, len(s), len(s))].sum() for _ in range(2000)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    R[a] = {"n_arm": int(len(x)), "n_common": int(len(common)), "n_only_base": int(len(ob)), "n_only_arm": int(len(oa)),
            "dPnL_size_neutral": float(t.v.sum()), "ci95": [float(lo), float(hi)], "halfwidth": float((hi - lo) / 2),
            "d_matched": float(dm.sum()), "frac_matched_changed": float((dm.abs() > 1e-6).mean())}
    print(a, R[a])
json.dump(R, open(OUT, "w"), indent=1)
print("WROTE", OUT)
