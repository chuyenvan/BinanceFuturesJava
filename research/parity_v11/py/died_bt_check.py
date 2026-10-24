#!/usr/bin/env python3
"""Ngoai parity (D2B muc 5, chi bao cao): sim X14 (printDone, ~/kaggle_sim/out/tsx-x14-s*) co giao dich tren symbol thuoc
DIED_SYMBOLS cua live khong? Sim dung DIED_SYMBOLS=BTCDOM,USDC (chu y chong survivorship); live/harness parity dung danh
sach 143 symbol (config v11_settle/harness = cung danh sach live: 10-23 POWR qua selectCoins 123 phut o BT nhung 0 dong psym
live). Dem leg/PnL DEV 2022-25 tren symbol DIED-live; tach symbol con giao dich (co file Vision 2026-10-23). argv: out.json"""
import glob
import json
import re
import sys

import pandas as pd

cfg = open("/home/ubuntu/claude_master/v11_settle/harness/config.properties").read()
died = {(s if "USDT" in s else s + "USDT") for s in re.search(r"^DIED_SYMBOLS=(.*)$", cfg, re.M).group(1).strip().split(",") if s}
died -= {"BTCDOMUSDT", "USDCUSDT"}
U23 = {x.strip() for x in open("/home/ubuntu/claude_master/parity_v11w/univ/u_20261023.txt") if x.strip()}
still = died & U23
F = pd.read_csv("/home/ubuntu/claude_master/parity_v11w/d/2026-10-23/live/feat45_live.csv.gz", usecols=["symbol"])
rows = []
for d in sorted(glob.glob("/home/ubuntu/kaggle_sim/out/tsx-x14-s*/storage/printDone.csv")):
    seed = d.split("/")[-3]
    sim_died = re.search(r"^DIED_SYMBOLS=(.*)$", open(d.replace("storage/printDone.csv", "config.properties")).read(), re.M).group(1)
    p = pd.read_csv(d)
    p["sym2"] = p.sym.astype(str) + "USDT"
    p = p[p.start.astype(str).str[:4].isin(["2022", "2023", "2024", "2025"])]
    m, ms_ = p.sym2.isin(died), p.sym2.isin(still)
    rows.append({"seed": seed, "sim_DIED_SYMBOLS": sim_died, "legs": int(len(p)), "legs_on_live_died": int(m.sum()),
                 "legs_on_live_died_still_trading": int(ms_.sum()), "pnl": float(p.pnl.sum()),
                 "pnl_on_live_died": float(p.pnl[m].sum()), "pnl_on_still_trading": float(p.pnl[ms_].sum()),
                 "n_died_symbols_traded": int(p.sym2[m].nunique())})
T = pd.DataFrame(rows)
res = {"live_died_n_excl_BTCDOM_USDC": len(died), "live_died_still_trading_2026_10_23": sorted(still),
       "live_died_in_live_psym_2026_10_23": sorted(died & set(F.symbol)), "per_seed": rows,
       "mean_share_legs_on_live_died": float((T.legs_on_live_died / T.legs).mean()),
       "mean_share_pnl_on_live_died": float((T.pnl_on_live_died / T.pnl).mean()),
       "mean_share_legs_still_trading": float((T.legs_on_live_died_still_trading / T.legs).mean()),
       "mean_share_pnl_still_trading": float((T.pnl_on_still_trading / T.pnl).mean())}
json.dump(res, open(sys.argv[1], "w"), indent=1)
print(json.dumps({k: v for k, v in res.items() if k != "per_seed"}, indent=1))
