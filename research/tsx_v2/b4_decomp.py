#!/usr/bin/env python3
"""TSX_V2 mo ta bo sung (sau Phase B, khong doi luat): tach Delta B4 theo kenh - cum moi duoc hoan (X14 cat o moc),
cum hoan lau hon X14, cum hoan ngan hon; so cum giu lau hon run nguon (dong bang DCA)."""
import json, logging, sys
import numpy as np, pandas as pd
import common as CM, engine as EN
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("b4d")
C, keys, arr, fund = CM.load_all()
W = CM.Wins(keys, arr, fund, CM.ticks(), True, CM.nofund_syms(C))
eod = CM.ew_eod(); base, _ = CM.base_flags_check(eod)
A = pd.read_pickle(CM.D + "/cache/phaseA.pkl")
X = C[C["arm"] == "X14"].reset_index(drop=True)
out = {}
for thr, L in ((-0.25, 20), (-0.25, 30), (-0.25, 45), (-0.30, 20), (-0.30, 45), (-0.35, 20), (-0.35, 30), (-0.35, 45)):
    ds = CM.dayints(CM.flag_days(eod, thr, L)); db = CM.dayints(base)
    rows = []
    for r in X.itertuples():
        w = W.get(r.wid)
        rb = EN.replay(w, r.legs, dayset=db, cap_j=CM.CAP504)
        rv = EN.replay(w, r.legs, dayset=ds, cap_j=CM.CAP504)
        rows.append((r.seed, rb["deferred"], rv["deferred"], rb["j"], rv["j"], rv["pnl"] - rb["pnl"], rv["j"] > r.age))
    D = pd.DataFrame(rows, columns=["seed", "db", "dv", "jb", "jv", "d", "beyond_src"])
    ch = np.select([~D.db & D.dv, D.db & ~D.dv, D.db & D.dv & (D.jv > D.jb), D.db & D.dv & (D.jv < D.jb)],
                   ["moi_hoan", "bo_hoan", "hoan_lau_hon", "hoan_ngan_hon"], "khac")
    D["ch"] = ch
    g = D.groupby("ch").agg(n=("d", "size"), d=("d", "sum"))
    g["n"] /= 8; g["d"] /= 8
    k = "%.2f/%d" % (thr, L)
    out[k] = dict(channels=g.round(1).to_dict("index"), beyond_src_per_seed=float(D.beyond_src.sum() / 8),
                  d_beyond_src=float(D.loc[D.beyond_src, "d"].sum() / 8))
    log.info("%s %s", k, out[k])
json.dump(out, open(CM.D + "/out/b4_decomp.json", "w"), indent=1)
