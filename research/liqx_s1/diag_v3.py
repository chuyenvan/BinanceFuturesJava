"""Diagnose V3 mismatch 2022-11-09: which (sym, T) differs between independent code and pipeline coin parquet."""
import numpy as np
import pandas as pd
from v3_indep import load, top100, per_sym, KLP, MTP, utc, DAYMS, FIVE, MIN

S1 = "/home/ubuntu/claude_master/liqx_wk/s1"
D = utc("2022-11-09")
a, b = D - 8 * DAYMS, D + 2 * DAYMS
nbk = (b - a) // FIVE
Tg = a + FIVE * np.arange(1, nbk + 1, dtype=np.int64)
U = top100(utc("2022-11-01"))
import json
Up = json.load(open(S1 + "/uni/2022-11.json"))["uni"]
print("universe equal:", U == Up, set(U) ^ set(Up))
k = load(KLP, ["ts", "sym", "close", "volume", "taker_buy_base", "quote_volume", "taker_buy_quote"], a, b + 3 * DAYMS, set(U))
mt = load(MTP, ["ts", "sym", "oi", "oi_value", "taker_ls_vol"], a - DAYMS, b + DAYMS, set(U), metrics=True)
mt = mt.sort_values(["sym", "ts"]).drop_duplicates(["sym", "ts"], keep="last")
g = pd.read_parquet(S1 + "/coin/2022-11.parquet")
g["sym"] = g.sym.astype(str)
cv = pd.read_parquet(S1 + "/conv/2022-11.parquet")
sel = (Tg > D - DAYMS) & ((Tg - 1) // DAYMS * DAYMS >= utc("2022-11-01"))
bad = []
for s in U:
    ks, ms_ = k[k.sym == s].sort_values("ts"), mt[mt.sym == s]
    G, eff, conv = per_sym(ks, ms_, a, nbk)
    gp = g[g.sym == s].set_index("T")
    for T in Tg[sel]:
        T = int(T)
        j = (T - a) // MIN
        o0, o1 = eff.get(T - FIVE), eff.get(T)
        c1, c0 = G["close"][j - 1], G["close"][j - 6]
        qv, tq = G["quote_volume"][j - 5:j], G["taker_buy_quote"][j - 5:j]
        ok = (o0 is not None and o1 is not None and o0 > 0 and np.isfinite(o1) and np.isfinite(c1) and np.isfinite(c0)
              and np.isfinite(qv).all() and np.isfinite(tq).all())
        if T not in gp.index:
            continue
        pv = bool(gp.loc[T, "valid"])
        if ok != pv or (ok and abs((min(max(0, o0 - o1), max(0, qv.sum() - 2 * tq.sum())) if np.log(c1 / c0) < 0 else 0) - gp.loc[T, "P2"]) > 1e-6):
            bad.append(dict(sym=s, T=pd.Timestamp(T, unit="ms").isoformat(), indep_valid=ok, pipe_valid=pv, o0=o0, o1=o1,
                            pipe_oiv0=gp.loc[T, "oiv0"], pipe_oiv1=gp.loc[T, "oiv1"], c1=c1, pipe_c1=gp.loc[T, "c1"],
                            conv_indep=conv.get(int((T - 1) // DAYMS)), nbar_nan=int((~np.isfinite(qv)).sum())))
print(pd.DataFrame(bad).to_string())
for r in bad[:3]:
    s = r["sym"]
    d = (utc(r["T"][:10]) // DAYMS) * DAYMS
    print(cv[(cv.sym == s) & (cv.day >= d - DAYMS) & (cv.day <= d + DAYMS)].to_string())
    T = utc(r["T"])
    print(mt[(mt.sym == s) & (mt.ts >= T - 3 * FIVE) & (mt.ts <= T + 2 * FIVE)].to_string())
    print(k[(k.sym == s) & (k.ts >= T - 7 * MIN) & (k.ts <= T)].to_string())
