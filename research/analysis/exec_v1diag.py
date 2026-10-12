#!/usr/bin/env python3
"""exec_v1diag.py -- EXEC dieu tra V1 (aggTrades vs kline 1m Vision): phan loai phut lech theo nam, loai lech, do lon."""
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import exec_measure as M  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("v1diag")


def diag(sym, ev):
    K = M.load_npz(M.W + "/kl/%sUSDT_*.npz" % sym, ("t", "x"))
    A = M.load_npz(M.W + "/agg/%sUSDT_*.npz" % sym, ("t", "p", "q", "m"))
    rows = []
    for s in ev["s_ms"]:
        a, b = s + M.DEC_OFF - M.WIN_PRE, s + M.DEC_OFF + M.WIN_POST
        for m in range(int(-(-a // M.MN) * M.MN), int(b + 1 - M.MN) + 1, M.MN):
            k = np.searchsorted(K["t"], m)
            if k >= len(K["t"]) or K["t"][k] != m:
                continue
            i0, i1 = np.searchsorted(A["t"], m), np.searchsorted(A["t"], m + M.MN)
            p, q = A["p"][i0:i1], A["q"][i0:i1]
            o, h, l, c, v = K["x"][k]
            if len(p) == 0:
                rows.append(dict(m=m, n=0, v=v, dv=-v, do=np.nan, dh=np.nan, dl=np.nan, dc=np.nan))
                continue
            rows.append(dict(m=m, n=len(p), v=v, dv=q.sum() - v, do=p[0] / o - 1, dh=p.max() / h - 1,
                             dl=p.min() / l - 1, dc=p[-1] / c - 1))
    return pd.DataFrame(rows)


def main():
    ev = pd.read_pickle(M.W + "/legs.pkl")["ev"]
    parts = []
    for sym, g in ev.groupby("sym"):
        d = diag(sym, g)
        d["sym"] = sym
        parts.append(d)
    D = pd.concat(parts, ignore_index=True).drop_duplicates(["sym", "m"])
    D["year"] = pd.to_datetime(D["m"], unit="ms").dt.year
    D["ym"] = pd.to_datetime(D["m"], unit="ms").dt.strftime("%Y-%m")
    D["okp"] = (D[["do", "dh", "dl", "dc"]].abs().max(axis=1) == 0) | ((D["n"] == 0) & (D["v"] == 0))
    D["okv"] = D["dv"].abs() <= 1e-6 * D["v"] + 1e-9
    D["ok"] = D["okp"] & D["okv"]
    D["rv"] = D["dv"] / D["v"].where(D["v"] > 0)
    out = dict(n=int(len(D)), ok=float(D["ok"].mean()),
               by_year=D.groupby("year")["ok"].mean().round(5).to_dict(),
               by_ym_bad=D.groupby("ym")["ok"].mean().round(4)[lambda s: s < 0.999].to_dict(),
               bad_only_vol=int((D["okp"] & ~D["okv"]).sum()), bad_price=int((~D["okp"]).sum()),
               vol_sign_neg=float((D.loc[~D["okv"], "dv"] < 0).mean()),
               rv_q=D.loc[~D["okv"], "rv"].quantile([0.05, 0.25, 0.5, 0.75, 0.95]).round(6).to_dict(),
               hl_bad=int(((D["dh"] != 0) | (D["dl"] != 0)).sum()), oc_bad=int(((D["do"] != 0) | (D["dc"] != 0)).sum()),
               dh_q=D.loc[D["dh"] != 0, "dh"].quantile([0.05, 0.5, 0.95]).round(6).to_dict(),
               dl_q=D.loc[D["dl"] != 0, "dl"].quantile([0.05, 0.5, 0.95]).round(6).to_dict(),
               n_zero_trade=int((D["n"] == 0).sum()),
               bad_syms_top=D.groupby("sym")["ok"].mean().sort_values().head(8).round(3).to_dict())
    with open(M.W + "/v1diag.json", "w") as f:
        json.dump(out, f, indent=1, default=str)
    D.to_pickle(M.W + "/v1diag.pkl")
    log.info("V1DIAG %s", json.dumps(out, default=str))


if __name__ == "__main__":
    main()
