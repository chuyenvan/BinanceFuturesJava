#!/usr/bin/env python3
"""PAIRS_T1 - anomaly/risk description (report only, no rule change): legs held across 1h jumps > ln2,
symbol concentration of selected pairs, top losing legs, M3 beta distribution. Writes out/anom.json."""
import json
import logging
import os
import pickle
import sys
from collections import Counter

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pairs_t1_core as K  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("anom")
OUT = os.path.expanduser("~/claude_master/pairs/out")


def ts(h):
    return str(pd.Timestamp(K.H0_MS + int(h) * 3600000, unit="ms"))


def main():
    P = K.Panel()
    wins = pickle.load(open(os.path.join(OUT, "pairs_main.pkl"), "rb"))
    with np.errstate(all="ignore"):
        J = np.abs(np.diff(np.log(P.CF), axis=0))
    J[~np.isfinite(J)] = 0
    res = {}
    for m in ("M1", "M2", "M3"):
        legs = []
        for w in wins:
            for tr in w["res"][m]["trades"]:
                for l in tr["ledger"]:
                    mj = float(J[l["e"]:max(l["e"] + 1, l["xe"]), l["sym"]].max())
                    legs.append(dict(sym=str(P.syms[l["sym"]]), e=ts(l["e"]), x=ts(l["xe"]), w=l["w"], gross=l["gross"],
                                     fund=l["fund"], maxjump=mj, ret=l["px"] / l["pe"] - 1))
        df = pd.DataFrame(legs)
        jumpy = df[df.maxjump > np.log(2)]
        conc = []
        for w in wins:
            pr = w["p1"] if m in ("M1", "M3") else w["p2"]
            c = Counter()
            for d in pr:
                for s in ((d["y"], d["x"]) if "y" in d else (d["i"], d["j"])):
                    c[s] += 1
            conc.append(max(c.values()) if c else 0)
        conc = np.array(conc)
        bysym = df.groupby("sym").apply(lambda g: (g.gross + g.fund).sum()).sort_values()
        res[m] = dict(n_legs=int(len(df)), n_legs_jump_gt_2x=int(len(jumpy)),
                      pnl_legs_jump=float((jumpy.gross + jumpy.fund).sum()),
                      jump_legs=jumpy.sort_values("gross").head(8).to_dict("records"),
                      worst_legs=df.sort_values("gross").head(8).to_dict("records"),
                      worst_syms=[(s, float(v)) for s, v in bysym.head(6).items()],
                      best_syms=[(s, float(v)) for s, v in bysym.tail(6).items()],
                      max_pairs_one_symbol_median=float(np.median(conc)),
                      frac_weeks_one_symbol_ge3=float((conc >= 3).mean()),
                      frac_weeks_one_symbol_ge5=float((conc >= 5).mean()),
                      abs_w_max=float(df.w.abs().max()), frac_legs_absw_gt_0p08=float((df.w.abs() > 0.08).mean()))
        log.info("%s legs=%d jump>2x=%d pnl=%.4f conc_med=%.1f ge3=%.2f ge5=%.2f worst=%s", m, len(df), len(jumpy),
                 res[m]["pnl_legs_jump"], res[m]["max_pairs_one_symbol_median"], res[m]["frac_weeks_one_symbol_ge3"],
                 res[m]["frac_weeks_one_symbol_ge5"], res[m]["worst_syms"][:3])
    json.dump(res, open(os.path.join(OUT, "anom.json"), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
