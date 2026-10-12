#!/usr/bin/env python3
"""exec_bookticker.py -- EXEC kiem dinh P0 (pre-reg §3): neu Vision co bookTicker futures cho (sym, ngay) cua chan DEV,
lay mau <= 150 (seed 20261012), doc best bid/ask tai t_dec, so voi gia P0 (aggTrades) trong exec/sim.pkl. CHI kiem dinh.
Usage: exec_bookticker.py fetch | cmp
"""
import json
import logging
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exec_fetch as F  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("exec_bt")
W = F.W
DEC_OFF = 66000


def exists(arg):
    sym, day = arg
    url = "%s/daily/bookTicker/%sUSDT/%sUSDT-bookTicker-%s.zip" % (F.BASE, sym, sym, day)
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=60) as r:
            return sym, day, r.status == 200
    except Exception:  # noqa: BLE001 - 404 = khong co
        return sym, day, False


def one(arg):
    sym, day, evs = arg
    tag = "bt_%sUSDT_%s" % (sym, day)
    url = "%s/daily/bookTicker/%sUSDT/%sUSDT-bookTicker-%s.zip" % (F.BASE, sym, sym, day)
    zp, ok = F.fetch_zip(url, tag)
    if zp is None:
        return []
    td = np.array([t for _, t in evs], np.int64)
    best = {}
    try:
        for ch in F.iter_csv(zp, [1, 2, 3, 4, 5], ["bid", "bq", "ask", "aq", "t"]):
            t = F.fix_ms(ch["t"].to_numpy())
            for k, x in enumerate(td):
                m = (t <= x) & (t >= x - 60000)
                if m.any():
                    j = np.flatnonzero(m)[-1]
                    if k not in best or t[j] >= best[k][4]:
                        r = ch.iloc[j]
                        best[k] = (float(r.bid), float(r.bq), float(r.ask), float(r.aq), int(t[j]))
    finally:
        os.remove(zp)
    return [dict(eid=evs[k][0], sha_ok=ok, bid=v[0], bq=v[1], ask=v[2], aq=v[3], lag_ms=int(td[k] - v[4]))
            for k, v in best.items()]


def fetch():
    ev = pd.read_pickle(W + "/legs.pkl")["ev"]
    ev["td"] = ev["s_ms"] + DEC_OFF
    ev["day"] = pd.to_datetime(ev["td"], unit="ms").dt.strftime("%Y-%m-%d")
    sd = sorted(set(zip(ev["sym"], ev["day"])))
    with ThreadPoolExecutor(8) as ex:
        have = [(s, d) for s, d, ok in ex.map(exists, sd) if ok]
    log.info("bookTicker ton tai %d/%d (sym, ngay)", len(have), len(sd))
    rng = np.random.default_rng(20261012)
    pick = [have[i] for i in sorted(rng.choice(len(have), size=min(150, len(have)), replace=False))] if have else []
    args = [(s, d, list(zip(g["eid"], g["td"]))) for s, d in pick
            for g in [ev[(ev["sym"] == s) & (ev["day"] == d)]]]
    out = []
    with ThreadPoolExecutor(4) as ex:
        for r in ex.map(one, args):
            out += r
    pd.to_pickle(dict(rows=pd.DataFrame(out), n_have=len(have), n_sd=len(sd), pick=pick), W + "/bt.pkl")
    log.info("bookTicker: %d su kien co ask tai t_dec", len(out))


def cmp():
    b = pd.read_pickle(W + "/bt.pkl")
    sm = pd.read_pickle(W + "/sim.pkl")
    X = b["rows"]
    if len(X) == 0:
        res = dict(n_have=b["n_have"], n_sd=b["n_sd"], n=0)
    else:
        R = sm["R"]
        p0 = R[(R["size"] == "paper") & (R["pol"] == "P0")].groupby("eid").agg(p0=("cost_bps", "median"), N=("N", "median"))
        X = X.merge(sm["EV"][["eid", "cM", "br"]], on="eid").merge(p0, on="eid")
        X["ask_bps"] = (X["ask"] / X["cM"] - 1) * 1e4
        X["d"] = X["p0"] - X["ask_bps"]
        X["spr"] = (X["ask"] / X["bid"] - 1) * 1e4
        X["depth_ok"] = X["ask"] * X["aq"] >= X["N"]
        cr = X["br"] <= -0.01

        def s(z):
            return dict(n=int(len(z)), p0=float(z["p0"].mean()), ask=float(z["ask_bps"].mean()), d_mean=float(z["d"].mean()),
                        d_med=float(z["d"].median()), d_p90=float(z["d"].quantile(0.9)), spr_med=float(z["spr"].median()),
                        depth_ok=float(z["depth_ok"].mean()), lag_med_ms=float(z["lag_ms"].median()))
        res = dict(n_have=b["n_have"], n_sd=b["n_sd"], n_pick=len(b["pick"]), sha_bad=int((X["sha_ok"] == False).sum()),  # noqa: E712
                   all=s(X), sap=s(X[cr]) if cr.sum() else None, khong_sap=s(X[~cr]))
    with open(W + "/bt_cmp.json", "w") as f:
        json.dump(res, f, indent=1)
    log.info("BT CMP %s", json.dumps(res))


if __name__ == "__main__":
    {"fetch": fetch, "cmp": cmp}[sys.argv[1]]()
