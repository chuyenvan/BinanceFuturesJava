#!/usr/bin/env python3
"""Cham EXEC-PROBE theo docs/prereg/PREREG_EXEC_PROBE.md (pre-reg TRUOC khi co du lieu that; KHONG sua sau khi xem ket qua).

argv: --log <file log/csv chua dong [EXEC-PROBE]> [--log ...] --paper-equity <PAPER_EQUITY 242> --out <json>
      [--legs <so leg giay cung cua so, de kiem V5>] [--allow-mock] (chi de tu kiem script tren harness)
Chi doc file; khong mang. In ket qua qua logging (stderr) + JSON.
"""
import argparse
import json
import logging
import random
import statistics
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stderr)
log = logging.getLogger("xp_score")

HEADER = ("v,ev,sym,side,lvl,leg,reason,qty,notional,sim_px,bar_open,bar_ret,bucket,t_bar_close,t_dec,t_snap,lat_dec_ms,"
          "lat_snap_ms,ex_lag_ms,bid,ask,mid,spread_bps,l1_bid_ntl,l1_ask_ntl,n_lvl,side_ntl,walk_vwap,fill_frac,walk_lvls,"
          "slip_bps,drift_bps,impact_bps,slip_x025,slip_x4,trig_px,status,src").split(",")
# ECMEAS "thuc" (CI_tren P0, docs/result/EXEC_RESULT.md §6a) va stress (P0max), bps
ASSUME = {"NC": 7.0, "C1": 18.0, "C2": 19.0, "C4": 32.0}
STRESS = {"NC": 23.0, "C1": 33.0, "C2": 41.0, "C4": 101.0}
EXIT_ASSUME = 0.67  # SIM_SLIPPAGE_RATE 0.000067 / chan
N_MIN_E, N_MIN_X, B, SEED = 100, 30, 2000, 20261021


def rows(paths):
    out = []
    for p in paths:
        for line in open(p, encoding="utf-8", errors="replace"):
            i = line.find("[EXEC-PROBE] ")
            s = line[i + 13:] if i >= 0 else line
            s = s.rstrip("\n")
            if s.startswith("#hdr") or not s.startswith("1,"):
                continue
            v = s.split(",")
            if len(v) != len(HEADER):
                continue
            out.append(dict(zip(HEADER, v)))
    return out


def f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def pct(xs, q):
    xs = sorted(xs)
    if not xs:
        return None
    k = (len(xs) - 1) * q
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def boot_median(vals, keys):
    """CI95 cua median bang bootstrap theo cum (cum = phut t_bar_close / t_dec)."""
    groups = {}
    for v, k in zip(vals, keys):
        groups.setdefault(k, []).append(v)
    g = list(groups.values())
    if len(g) < 2:
        return None, None
    rnd = random.Random(SEED)
    meds = []
    for _ in range(B):
        s = []
        for _ in range(len(g)):
            s.extend(g[rnd.randrange(len(g))])
        meds.append(statistics.median(s))
    return pct(meds, 0.025), pct(meds, 0.975)


def desc(xs):
    if not xs:
        return {"n": 0}
    return {"n": len(xs), "median": statistics.median(xs), "mean": statistics.fmean(xs), "p90": pct(xs, 0.9),
            "p99": pct(xs, 0.99), "max": max(xs)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", action="append", required=True)
    ap.add_argument("--paper-equity", type=float, required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--legs", type=int, default=None)
    ap.add_argument("--allow-mock", action="store_true")
    a = ap.parse_args()
    R = rows(a.log)
    col = "slip_x025" if a.paper_equity >= 20000 else "slip_bps"   # cot gan quy mo pilot 10k nhat (pre-reg §3)
    E_all = [r for r in R if r["ev"] in ("ENTRY", "DCA")]
    X_all = [r for r in R if r["ev"] == "EXIT"]
    good = lambda r: r["status"] in ("ok", "short")
    E = [r for r in E_all if good(r) and f(r[col]) is not None]
    X = [r for r in X_all if good(r) and f(r["slip_bps"]) is not None]
    lat_snap = [f(r["lat_snap_ms"]) for r in E + X if f(r["lat_snap_ms"]) is not None]
    ex_lag = [abs(f(r["ex_lag_ms"])) for r in E + X if f(r["ex_lag_ms"]) is not None]
    n_mock = sum(1 for r in R if r["src"] == "mock")
    V = {
        "V1_coverage": (len(E) / len(E_all)) if E_all else None,
        "V2_lat_snap_median_ms": statistics.median(lat_snap) if lat_snap else None,
        "V3_ex_lag_median_ms": statistics.median(ex_lag) if ex_lag else None,
        "V4_mock_lines": n_mock,
        "V5_lines_vs_legs": (len(E_all) / a.legs) if a.legs else None,
    }
    ok = {
        "V1": V["V1_coverage"] is not None and V["V1_coverage"] >= 0.90,
        "V2": V["V2_lat_snap_median_ms"] is not None and V["V2_lat_snap_median_ms"] <= 3000,
        "V3": V["V3_ex_lag_median_ms"] is None or V["V3_ex_lag_median_ms"] <= 2000,
        "V4": n_mock == 0 or a.allow_mock,
        "V5": V["V5_lines_vs_legs"] is None or abs(V["V5_lines_vs_legs"] - 1) <= 0.05,
    }
    slip = [f(r[col]) for r in E]
    exc = [f(r[col]) - ASSUME.get(r["bucket"], ASSUME["NC"]) for r in E]
    exc_st = [f(r[col]) - STRESS.get(r["bucket"], STRESS["NC"]) for r in E]
    keys = [r["t_bar_close"] or r["t_dec"] for r in E]
    lo, hi = boot_median(exc, keys) if exc else (None, None)
    xs = [f(r["slip_bps"]) for r in X if r["reason"] == "TRAILING_STOP"]
    res = {
        "col": col, "n_E": len(E), "n_X": len(X), "validity": V, "validity_ok": ok,
        "slip": desc(slip), "excess_vs_ecmeas": desc(exc), "excess_ci95_median": [lo, hi], "excess_vs_stress": desc(exc_st),
        "by_bucket": {b: desc([f(r[col]) for r in E if r["bucket"] == b]) for b in ("NC", "C1", "C2", "C4")},
        "drift": desc([f(r["drift_bps"]) for r in E if f(r["drift_bps"]) is not None]),
        "impact": desc([f(r["impact_bps"]) for r in E if f(r["impact_bps"]) is not None]),
        "lat_dec_ms": desc([f(r["lat_dec_ms"]) for r in E if f(r["lat_dec_ms"]) is not None]),
        "short_share": (sum(1 for r in E if r["status"] == "short") / len(E)) if E else None,
        "exit_trailing": desc(xs), "exit_all": desc([f(r["slip_bps"]) for r in X]),
    }
    verdict = "NO_VERDICT"
    W = {}
    if all(ok.values()) and len(E) >= N_MIN_E:
        W["W1"] = statistics.median(exc) > 0 and lo is not None and lo > 0
        W["W2"] = pct(slip, 0.9) > 170
        W["W3"] = sum(1 for s in slip if s > 250) / len(slip) > 0.02
        W["W4"] = len(xs) >= N_MIN_X and (statistics.median(xs) > 10 or pct(xs, 0.9) > 170)
        W["W5"] = res["short_share"] > 0.10
        W["W6"] = W["W1"] and statistics.median(exc) > 25
        if W["W2"] or W["W3"] or W["W5"] or W["W6"]:
            verdict = "RED_SIZE"
        elif W["W1"] or W["W4"]:
            verdict = "AMBER"
        else:
            verdict = "GREEN"
    res["warnings"] = W
    res["verdict"] = verdict
    log.info("verdict=%s col=%s n_E=%d n_X=%d validity_ok=%s W=%s", verdict, col, len(E), len(X), ok, W)
    log.info("slip=%s excess=%s ci95=%s", res["slip"], res["excess_vs_ecmeas"], res["excess_ci95_median"])
    json.dump(res, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
