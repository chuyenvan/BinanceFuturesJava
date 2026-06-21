#!/usr/bin/env python3
"""
TASK-039 phu tro: do PHAN BO base_rate cua label theo (nguong maxFav x horizon x nam).
Muc dich: chon TARGET sao cho base_rate ~10-30% (selector co dat tao lift + du mau positive),
thay vi train mu o +6% co the qua de. KHONG train - chi doc label, groupby.
Env: LABEL_CSV. Doc chi cot can (nhe RAM).
"""
import os
import pandas as pd
import numpy as np

LABEL = os.environ["LABEL_CSV"]
H_STEPS = {"4h": 16, "12h": 48, "24h": 96, "72h": 288}
THR = [0.06, 0.10, 0.15, 0.20, 0.30]

cols = ["tEpochMs"] + [f"maxFav_{h}" for h in H_STEPS] + [f"nBars_{h}" for h in H_STEPS] \
       + [f"maxAdv_{h}" for h in H_STEPS]
df = pd.read_csv(LABEL, usecols=cols)
df["year"] = pd.to_datetime(df["tEpochMs"], unit="ms").dt.year
print(f"Tong dong label: {len(df):,}")

for h, steps in H_STEPS.items():
    fav, adv, nb = f"maxFav_{h}", f"maxAdv_{h}", f"nBars_{h}"
    full = df[df[nb] >= steps]
    print(f"\n===== H={h} (chi dong nBars>={steps} du; n={len(full):,}) =====")
    # base_rate cham +X% (maxFav), toan ky + theo nam
    print("  P(cham +X%) toan-ky | theo nam:")
    for t in THR:
        overall = (full[fav] >= t).mean()
        by = full.groupby("year").apply(lambda g: (g[fav] >= t).mean(), include_groups=False)
        ys = "  ".join(f"{y}:{v:.0%}" for y, v in by.items())
        print(f"    +{int(t*100):2d}% : {overall:5.1%} | {ys}")
    # them goc nhin triple-barrier: cham +6% TRUOC khi sup >-10% (xap xi: maxAdv > -0.10)
    for t in [0.06, 0.10]:
        cond = (full[fav] >= t) & (full[adv] > -0.10)
        print(f"    [+{int(t*100)}% & khong sup qua -10%] = {cond.mean():.1%}")
