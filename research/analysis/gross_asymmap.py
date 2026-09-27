"""gross_asymmap.py — docs/prereg/PREREG_GROSS_ASYMMAP.md (commit 3f6993b).

DOC artifact: (A) doi chieu 2 dinh nghia `gross` tren CUNG artifact; (B) re-score
toan bo run co ledger theo RAO MOI (a)/(b') + 4 THUOC CHUAN + asym + ban do cau truc.
KHONG train, KHONG sim, KHONG cham 2026. DEV only <= 2025-12-31.

Usage:
  python3 gross_asymmap.py scan   --json docs/result/gross_asymmap.json [--md out.md]
  python3 gross_asymmap.py partA  --tag cd-sel15
"""
import argparse
import glob
import json
import math
import os
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import size_count_score as S          # gross(), tail(), legs()

RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")
RX_WIN = re.compile(r"SIMULATE T[UỪ] (\d{8}) .*?[ĐD]?[ẾE]N (\d{8})")
RX_CFG = re.compile(r"\[(?:SELECTOR-RANK|SELECTOR|RANK)-CFG\].*?TOPN?=(-?\d+)")
ROOTS = ["/home/ubuntu/kaggle_sim/out", "/home/ubuntu/java/devrun",
         "/home/ubuntu/java/fsrun/runs", "/home/ubuntu/runs"]
END_DEV = "20251231"
S0_ANCHOR = 0.02          # neo post-hoc "2,0%/lenh" (cap70_fee06.py)


def run_dirs():
    out = []
    for r in ROOTS:
        for p in glob.glob(os.path.join(r, "*", "storage", "printDone.csv")):
            base = os.path.dirname(os.path.dirname(p))
            if os.path.exists(os.path.join(base, "logs", "sim.out")) or \
               os.path.exists(os.path.join(base, "logs", "sim.out.gz")):
                out.append(base)
    # nested (out/<tag> only) already covered
    return sorted(set(out))


def load_equity(base):
    p = os.path.join(base, "logs", "sim.out")
    if not os.path.exists(p):
        gz = p + ".gz"
        if not os.path.exists(gz):
            return None
        import gzip
        fh = gzip.open(gz, "rt", errors="ignore")
    else:
        fh = open(p, errors="ignore")
    rows, win = [], None
    with fh as f:
        for line in f:
            if win is None:
                m = RX_WIN.search(line)
                if m:
                    win = (m.group(1), m.group(2))
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    if not rows:
        return None, win
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity, win


def run_meta(base):
    tag = os.path.basename(base)
    prof, topk, cadence, roothint = None, None, None, base.rsplit("/out/", 1)[0]
    rj = os.path.join(base, "result.json")
    if os.path.exists(rj):
        try:
            j = json.load(open(rj))
            prof = j.get("profile")
            ov = j.get("overrides", {}) or {}
            topk = ov.get("SELECTOR_RANK_TOPK")
            cadence = ov.get("SIM_ENTRY_SAMPLE_MIN")
        except Exception:
            pass
    return dict(tag=tag, root=os.path.dirname(base), profile=prof,
                topk=topk, cadence_min=cadence)


def ledger_tail_plus(d):
    """tail() from size_count_score + old-analog gross d_mean/d_max (distinct coins)."""
    out = dict(S.tail(d))
    dd = d.dropna(subset=["t_end"]).copy()
    dd = dd[pd.to_numeric(dd["margin"], errors="coerce").notna()]
    if len(dd) == 0:
        return out
    t0 = dd["ts"].min()
    a = (dd["ts"] - t0).dt.total_seconds().to_numpy(float)
    b = (dd["t_end"] - t0).dt.total_seconds().to_numpy(float)
    sym = dd["sym"].to_numpy()
    ev = []
    for i in range(len(dd)):
        if np.isfinite(a[i]) and np.isfinite(b[i]) and b[i] >= a[i]:
            ev.append((a[i], sym[i], +1))
            ev.append((b[i], sym[i], -1))
    ev.sort(key=lambda x: (x[0], -x[2]))
    op, wcoin, wt, cmax, prev = {}, 0.0, 0.0, 0, None
    for t, s, sg in ev:
        if prev is not None and t > prev:
            dt = t - prev
            wcoin += len(op) * dt
            wt += dt
            cmax = max(cmax, len(op))
        if sg > 0:
            op[s] = op.get(s, 0) + 1
        else:
            op[s] = op.get(s, 0) - 1
            if op[s] <= 0:
                op.pop(s, None)
        prev = t
    if wt > 0:
        out["old_d_mean"] = wcoin / wt
        out["old_d_max"] = cmax
        out["old_gross_mean"] = 100.0 * S0_ANCHOR * (wcoin / wt)
        out["old_gross_max"] = 100.0 * S0_ANCHOR * cmax
    return out


def score_dir(base):
    meta = run_meta(base)
    pdone = os.path.join(base, "storage", "printDone.csv")
    try:
        d = S.legs(base)          # G.trades(base) works on any base path
    except Exception as e:
        d = None
        meta["err"] = "trades:%s" % e
    res = dict(meta)
    if d is None or len(d) == 0:
        res["missing"] = "no_legs"
        return res
    try:
        res.update(ledger_tail_plus(d))
    except Exception as e:
        res["missing_tail"] = str(e)
    try:
        eq, win = load_equity(base)
        res["win"] = list(win) if win else None
        if eq is not None and len(eq):
            g = S.gross(d, eq)
            res.update(g)
            res["eq_min"] = int(eq.min())
            res["eq_max"] = int(eq.max())
            res["eq_last"] = int(eq.iloc[-1])
        else:
            res["missing_gross"] = "no_equity"
    except Exception as e:
        res["missing_gross"] = str(e)
    # window + guard: never touch 2026
    dts = d["ts"].dropna()
    res["d_first"] = dts.min().strftime("%Y%m%d") if len(dts) else None
    res["d_last"] = dts.max().strftime("%Y%m%d") if len(dts) else None
    dmax = d["t_end"].dropna()
    res["d_last_end"] = dmax.max().strftime("%Y%m%d") if len(dmax) else None
    # structure proxies
    res["multi_leg_frac"] = float((d.groupby(["sym", "ts"]).size() > 1).mean()) \
        if len(d) else float("nan")
    res["hold_med"] = float(d["hold_min"].median()) if "hold_min" in d.columns else \
        float(((d["t_end"] - d["ts"]).dt.total_seconds() / 60).median())
    res["ts_loss_frac"] = float((d["status"] == "STOP_LOSS_DONE").mean()) \
        if "status" in d.columns else float("nan")
    res["ts_mkt_frac"] = float((d["status"] == "STOP_MARKET_DONE").mean()) \
        if "status" in d.columns else float("nan")
    return res


def cmd_scan(a):
    dirs = run_dirs()
    print("dirs=%d" % len(dirs), flush=True)
    rows = []
    for i, b in enumerate(dirs):
        r = score_dir(b)
        rows.append(r)
        if (i + 1) % 50 == 0:
            print("  %d/%d" % (i + 1, len(dirs)), flush=True)
    df = pd.DataFrame(rows)
    # guard DEV
    bad = df[(df.get("d_last").notna()) & (df["d_last"] > END_DEV)]
    if len(bad):
        print("WARN >%s: %s" % (END_DEV, bad["tag"].tolist()), flush=True)
    os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
    df.to_json(a.json, orient="records", indent=0)
    print("wrote %s rows=%d" % (a.json, len(df)), flush=True)
    return df


def cmd_partA(a):
    tag = a.tag
    base = os.path.join("/home/ubuntu/kaggle_sim/out", tag)
    d = S.legs(base)
    eq = S.eq_series(base)
    g = S.gross(d, eq)
    t = ledger_tail_plus(d)
    print("### PART A tag=%s n=%d" % (tag, len(d)))
    print("G_new  = %.3f%% (max %.3f%%)" % (g["gross_mean"], g["gross_max"]))
    print("G_old[ledger] = %.3f%% (max %.3f%%) d_mean=%.3f d_max=%d" % (
        t["old_gross_mean"], t["old_gross_max"], t["old_d_mean"], t["old_d_max"]))
    print("coin_mean=%.3f coin_max=%d" % (g["coin_mean"], g["coin_max"]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "partA"])
    ap.add_argument("--json", default="docs/result/gross_asymmap.json")
    ap.add_argument("--tag", default="cd-sel15")
    a = ap.parse_args()
    if a.cmd == "scan":
        cmd_scan(a)
    else:
        cmd_partA(a)


if __name__ == "__main__":
    main()
