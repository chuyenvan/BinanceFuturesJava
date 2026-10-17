#!/usr/bin/env python3
"""MTM legacy cho GATE_VZ: y nguyen reset_rule_score.run_mtm, CHI thay nguon gia (ticker bin da bi xoa) bang close
kline1m Vision; them cua so DEV [2022-01-01, 2025-01-01). Kiem: tai lap cache gqsf ON (dd/uw) truoc khi dung."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/analysis")
import reset_rule_score as R  # noqa: E402
import feat_add_v1_score as F  # noqa: E402,F401  (MTMStateW cua so 2022+)

log = logging.getLogger("gvzm")
DEV0, DEV1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2025-01-01")
_CACHE = {}


def kp(ym):
    return os.path.join("/home/ubuntu/claude_master/gvz/k2021" if ym < "2021-12" else "/home/ubuntu/vz_e1/raw",
                        "kline1m-%s.parquet" % ym)


def month_close(ym):
    if ym not in _CACHE:
        _CACHE.clear()
        d = pd.read_parquet(kp(ym), columns=["ts", "sym", "close"])
        d = d.drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"])
        _CACHE[ym] = {s: (g["ts"].to_numpy(np.int64), g["close"].to_numpy(np.float32)) for s, g in d.groupby("sym")}
    return _CACHE[ym]


class MTMStateD(F.MTMStateW):
    def __init__(self):
        super().__init__()
        self.dev = {c: [-np.inf, 0.0, 0, 0] for c in R.MTM_COSTS}

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        day = (pd.Timestamp(R.DAY0) + pd.Timedelta(minutes=int(m_global))).normalize()
        if DEV0 <= day < DEV1:
            for c in R.MTM_COSTS:
                F.MTMStateW._consume(np.asarray(eq[c], float), self.dev[c])


_res_w = R._mtm_result


def _res_d(st):
    out = _res_w(st)
    for c in R.MTM_COSTS:
        out[c]["dd_dev"] = float(st.dev[c][1])
        out[c]["uw_dev_days"] = float(st.dev[c][3] / 1440.0)
    return out


def _work_vision(days):
    res = {}
    for day in days:
        if day not in R._G["need_days"]:
            res[day] = {}
            continue
        t0 = int(pd.Timestamp(day).value // 10 ** 6)
        base = int((pd.Timestamp(day) - pd.Timestamp(R.DAY0)) // pd.Timedelta(days=1)) * 1440
        per, need = {}, {}
        for tag, d in R._G["legs"].items():
            sub = d[(d.m0 < base + 1440) & (d.m1 > base)]
            if len(sub):
                need[tag] = sub
        syms = sorted({s + "USDT" for sub in need.values() for s in sub["sym"].unique()})
        srow = {s: i for i, s in enumerate(syms)}
        C = np.full((max(1, len(syms)), 1440), np.nan, np.float32)
        mc = month_close(pd.Timestamp(day).strftime("%Y-%m"))
        for s, j in srow.items():
            if s not in mc:
                continue
            ts, cl = mc[s]
            sel = (ts >= t0) & (ts < t0 + 1440 * 60000)
            C[j, ((ts[sel] - t0) // 60000).astype(np.int64)] = cl[sel]
        idx = np.where(np.isnan(C).any(axis=1))[0]
        if len(idx):
            C[idx] = pd.DataFrame(C[idx].T).ffill().bfill().to_numpy().T
        allnan = set(np.where(np.isnan(C).all(axis=1))[0].tolist())
        C[np.isnan(C)] = 0.0
        for tag, sub in need.items():
            u = np.zeros(1440, np.float32)
            nmiss = 0
            for sym, q, e, i0, i1 in zip(sub["sym"], sub["quantity"], sub["entry"],
                                         np.maximum(sub["m0"].to_numpy() - base, 0),
                                         np.minimum(sub["m1"].to_numpy() - base, 1440)):
                key = sym + "USDT"
                if i1 <= i0 or key not in srow or (int(srow[key]) in allnan):
                    nmiss += 1
                    continue
                j = srow[key]
                u[i0:i1] += (q * C[j, i0:i1]).astype(np.float32) - np.float32(q * e)
            sp = np.zeros(1440, np.float32)
            sm = np.zeros(1440, np.float32)
            cl = sub[(sub["m1"] >= base) & (sub["m1"] < base + 1440)]
            for pnl, mg, i1 in zip(cl["pnl"], cl["notional"], cl["m1"] - base):
                sp[int(i1)] += np.float32(pnl)
                sm[int(i1)] += np.float32(mg)
            per[tag] = (u, np.cumsum(sp).astype(np.float32), np.cumsum(sm).astype(np.float32), nmiss)
        res[day] = per
    return res


R.MTMState = MTMStateD
R._mtm_result = _res_d
R._work = _work_vision
R.MTM_COSTS = {"legacy": R.LEGACY}


def run(tags, workers=3):
    legs = {t: R.load_legs(t) for t in tags}
    return R.run_mtm(legs, workers=workers, chunk=30)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
    tags = sys.argv[2:]
    out = run(tags)
    p = sys.argv[1]
    old = json.load(open(p)) if os.path.exists(p) else {}
    for t in tags:
        out[t]["md5"] = R.md5_of(t)
        old[t] = out[t]
        log.info("MTM %s %s", t, json.dumps(out[t]["legacy"]))
    json.dump(old, open(p, "w"), indent=1)
