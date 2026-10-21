#!/usr/bin/env python3
"""TSX_V2 A1 VALIDATE: replay tai lap printDone.
 V-X14: luat X14 (co base, tran 504h) tren moi cum X14 cham moc 168h -> so (status, phut thoat, PnL) voi printDone.
        Yeu cau: >= 99 % cum HOAN khop (|dPnL| <= 1e-3 x max(|PnL|, 1 USD)).
 V-P0 : luat P0 (cat 168h) tren moi cum gqsf cham moc -> 100 % cum bi cat time-stop khop.
 Them: so cum hoan / seed = Java deferClusters (parity.json); tap cum hoan = deferred_clusters.csv (DEEP).
"""
import json
import logging
import sys

import numpy as np
import pandas as pd

import common as CM
import engine as EN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("val")
TOL = 1e-3


def run(C, W, days, arm):
    out = []
    dset = CM.dayints(days)
    for r in C[C["arm"] == arm].itertuples():
        w = W.get(r.wid)
        if arm == "X14":
            res = EN.replay(w, r.legs, dayset=dset, cap_j=CM.CAP504)
        else:
            res = EN.replay(w, r.legs)
        err = abs(res["pnl"] - r.pnl) if np.isfinite(res["pnl"]) else np.inf
        ok_p = err <= TOL * max(abs(r.pnl), 1.0)
        out.append(dict(seed=r.seed, sym=r.sym, te=r.te, age=r.age, st=r.st, pnl=r.pnl, fund=r.fund, tp=r.tp,
                        r_st=res["st"], r_j=res["j"], r_pnl=res["pnl"], r_fund=res["fund"], r_tp=res["tp"],
                        deferred=res["deferred"], armed_pre=res["armed_pre"], laa=res["leg_after_arm"],
                        ok_st=res["st"] == r.st, ok_j=res["j"] == r.age, ok_p=bool(ok_p), err=err))
    R = pd.DataFrame(out)
    R["ok"] = R["ok_st"] & R["ok_j"] & R["ok_p"]
    return R


def summ(R, name):
    d = dict(n=int(len(R)), ok=float(R["ok"].mean()), ok_st=float(R["ok_st"].mean()), ok_j=float(R["ok_j"].mean()),
             ok_p=float(R["ok_p"].mean()), err_p99=float(np.percentile(R["err"].replace(np.inf, 1e9), 99)),
             fund_abs_err_med=float((R["r_fund"] - R["fund"]).abs().median()),
             fund_abs_err_p99=float((R["r_fund"] - R["fund"]).abs().quantile(0.99)))
    log.info("%s %s", name, d)
    return d


def main():
    C, keys, arr, fund = CM.load_all()
    tk = CM.ticks()
    eod = CM.ew_eod()
    days, ok = CM.base_flags_check(eod)
    log.info("co base tinh lai: %d ngay, khop flags.json (sha): %s", len(days), ok)
    assert ok
    out = dict(flags_ok=ok, n_days=len(days))
    nof = CM.nofund_syms(C)
    log.info("sym sim khong co funding (funding=0 moi cum): %s", sorted(nof))
    out["nofund"] = sorted(nof)
    best = None
    for use_tick in (True, False):
        W = CM.Wins(keys, arr, fund, tk, use_tick, nof)
        RX = run(C, W, days, "X14")
        RP = run(C, W, days, "P0")
        tag = "tick" if use_tick else "notick"
        res = dict(X14_all=summ(RX, tag + " X14 all"), X14_def=summ(RX[RX["deferred"]], tag + " X14 deferred"),
                   P0_all=summ(RP, tag + " P0 all"),
                   P0_cut=summ(RP[(RP["st"] == "STOP_LOSS_DONE") & (RP["age"] == EN.MARK)], tag + " P0 cut168"))
        out[tag] = res
        if best is None or res["X14_def"]["ok"] > best[0]:
            best = (res["X14_def"]["ok"], tag, RX, RP)
    _, tag, RX, RP = best
    log.info("quy uoc chon: %s", tag)
    out["convention"] = tag
    # so cum hoan / seed vs Java
    par = json.load(open("/home/ubuntu/claude_master/tsx/parity.json"))
    cmp = {}
    for s in CM.SEEDS:
        j = par["tsx-x14-" + s.lower()]["tsx"]
        cmp[s] = dict(java_deferClusters=j[1], java_cutAfter=j[2], replay_def=int(RX[(RX.seed == s)]["deferred"].sum()),
                      replay_def_cut=int(RX[(RX.seed == s) & RX["deferred"] & (RX["r_st"] == "STOP_LOSS_DONE")].shape[0]))
    out["java_cmp"] = cmp
    log.info("Java vs replay (deferClusters, cutAfter): %s", cmp)
    dp = pd.read_csv("/home/ubuntu/claude_master/vz_e1_wt/docs/result/ts_mkt_ext/deep/deferred_clusters.csv")
    dp = dp[dp["scope"] == "DEV"]
    dp["te"] = pd.to_datetime(dp["te"])
    a = set(zip(dp["seed"], dp["sym"], dp["te"]))
    b = set(zip(RX.loc[RX.deferred, "seed"], RX.loc[RX.deferred, "sym"], RX.loc[RX.deferred, "te"]))
    out["deep_set"] = dict(deep=len(a), replay=len(b), inter=len(a & b), only_deep=len(a - b), only_replay=len(b - a))
    log.info("tap cum hoan DEEP vs replay: %s", out["deep_set"])
    bad = RX[RX["deferred"] & ~RX["ok"]]
    log.info("cum hoan KHONG khop (%d):\n%s", len(bad), bad.head(30).to_string())
    badp = RP[(RP["st"] == "STOP_LOSS_DONE") & (RP["age"] == EN.MARK) & ~RP["ok"]]
    log.info("P0 cut168 KHONG khop (%d):\n%s", len(badp), badp.head(30).to_string())
    oth = RX[~RX["deferred"] & ~RX["ok"]]
    log.info("X14 khong hoan KHONG khop (%d):\n%s", len(oth), oth.head(20).to_string())
    log.info("leg sau arm (X14): %d", int(RX["laa"].sum()))
    out["pass_X14_def"] = bool(out[tag]["X14_def"]["ok"] >= 0.99)
    out["pass_P0_cut"] = bool(out[tag]["P0_cut"]["ok"] == 1.0)
    log.info("PASS X14_def>=99%%: %s | P0_cut 100%%: %s", out["pass_X14_def"], out["pass_P0_cut"])
    RX.to_pickle(CM.D + "/cache/val_x14.pkl")
    RP.to_pickle(CM.D + "/cache/val_p0.pkl")
    json.dump(out, open(CM.D + "/out/validate.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
