#!/usr/bin/env python3
"""HO4: tap symbol trong ticker DEV theo ngay (so voi mapper) — chi dem/ten. Usage: ho4_tksyms.py <out.json> day1 day2 ..."""
import json, logging, sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho3_b2_kline_as as k1
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4tk")
mp = set(pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")["symbol"].astype(str))
res = {}
for day in sys.argv[2:]:
    mm = k1.load_ticker(day)
    syms = {}
    for ms, m in mm.items():
        for s in m:
            syms[s] = syms.get(s, 0) + 1
    S = set(syms)
    suf = {}
    for s in S:
        k = "USDT" if s.endswith("USDT") else ("USDC" if s.endswith("USDC") else ("_" if "_" in s else "other"))
        suf[k] = suf.get(k, 0) + 1
    res[day] = dict(n_min=len(mm), n_sym=len(S), suffix=suf, not_in_map=sorted(S - mp)[:80], n_not_in_map=len(S - mp),
                    few_min=sorted([s for s, c in syms.items() if c < 1440])[:80], sample=sorted(S)[:10])
    log.info("%s n_min=%d n_sym=%d suffix=%s not_in_map=%d", day, len(mm), len(S), suf, len(S - mp))
json.dump(res, open(sys.argv[1], "w"), indent=1)
