#!/usr/bin/env python3
"""Chi tiet theo QUY cho GATEDYN: n lenh, win%, TSloss%, pnl, maxDD (tu printDone + equity hang ngay tu log)."""
import sys, os, re
import pandas as pd
import numpy as np

B = "/home/ubuntu/java/devrun"
TAGS = sys.argv[1:] or ["X1_C3_FULL_PARITY_R", "X1_C3_FULL_GD92"]

def q_of(s):
    s = str(s).strip().strip("'")
    y, m = s[:4], int(s[5:7])
    return f"{y}Q{(m-1)//3+1}"

# doc equity hang ngay tu log BudgetManagerSimple: "Update 20220104 07:00 => b:35000 ..."
def daily_equity(tag):
    log = os.path.join(B, tag, "logs/sim.out")
    out = {}
    if not os.path.exists(log):
        return out
    pat = re.compile(r"Update (\d{4})(\d{2})(\d{2}) 07:00 => b:([0-9]+)")
    with open(log, errors="ignore") as f:
        for line in f:
            m = pat.search(line)
            if m:
                y, mo, d, b = m.group(1), int(m.group(2)), int(m.group(3)), float(m.group(4))
                out[f"{y}{mo:02d}{d:02d}"] = b
    return out

def quarter_range(qs):
    y, q = int(qs[0]), int(qs[1])
    return f"{y}Q{q}"

rows = []
for tag in TAGS:
    df = pd.read_csv(os.path.join(B, tag, "storage/printDone.csv"))
    df["q"] = df["time_start_format"].map(q_of)
    eq = daily_equity(tag)
    # equity dau ky = equity ngay dau cua ky truoc do (lay b dau tien <= quy), dung approx:
    # tinh maxDD noi bo theo quy tu chuoi equity hang ngay
    eq_series = pd.Series(eq).sort_index()
    for q in [f"{y}Q{q}" for y in range(2022, 2026) for q in range(1, 5)]:
        sub = df[df.q == q]
        n = len(sub)
        if n == 0:
            win = tsl = pnl = np.nan
        else:
            win = (sub.profit > 0).mean() * 100
            tsl = (sub.status == "STOP_LOSS_DONE").mean() * 100
            pnl = sub.pnl.sum()
        # maxDD trong quy: tu equity hang ngay
        y, qn = q[:4], int(q[5])
        eqq = eq_series.loc[[k for k in eq_series.index if k.startswith(f"{y}")]]
        # loc thang quy
        months = {1: ["01","02","03"], 2:["04","05","06"], 3:["07","08","09"], 4:["10","11","12"]}[qn]
        eqm = eq_series[[k for k in eq_series.index if k[:4]==str(y) and k[4:6] in months]]
        mdd = np.nan
        if len(eqm) >= 2:
            peak = eqm.cummax()
            dd = (eqm - peak) / peak
            mdd = dd.min() * 100
        rows.append(dict(tag=tag, quy=q, n=n, win_pct=round(win,2) if win==win else None,
                         tsl_pct=round(tsl,2) if tsl==tsl else None, pnl=round(pnl,1) if pnl==pnl else None,
                         mdd_q=round(mdd,2) if mdd==mdd else None))

out = pd.DataFrame(rows)
piv_n = out.pivot(index="quy", columns="tag", values="n")
piv_w = out.pivot(index="quy", columns="tag", values="win_pct")
piv_t = out.pivot(index="quy", columns="tag", values="tsl_pct")
piv_p = out.pivot(index="quy", columns="tag", values="pnl")
piv_m = out.pivot(index="quy", columns="tag", values="mdd_q")
t0, t1 = TAGS[0], TAGS[1]
print("=== SO LENH (n) ==="); print(piv_n.to_string())
print("\n=== WIN% ==="); print(piv_w.to_string())
print("\n=== TSLOSS% ==="); print(piv_t.to_string())
print("\n=== PNL (USD, tong lenh dong trong quy) ==="); print(piv_p.to_string())
print("\n=== maxDD noi bo QUY (%) — tu equity hang ngay ==="); print(piv_m.to_string())
# tong ket
print("\n=== TONG ===")
for tag in TAGS:
    s = out[out.tag==tag]
    print(f"{tag}: n={s.n.sum()} pnl={s.pnl.sum():.0f} winTB={(s.win_pct*s.n).sum()/s.n.sum():.2f}%")
