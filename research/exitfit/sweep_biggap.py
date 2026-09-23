"""CLOSE_BIGGAP — quet "dinh CLOSE × giveback lon" tren harness offline (thuan Python).

Chot TRUOC: docs/PREREG_CLOSE_BIGGAP.md (commit 7349c39). KHONG sua thiet ke sau khi thay ket qua.

Ham gap: gap_rate = min(ratio * peak_rate, cap) voi peak do bang CLOSE 1m (nhu F3).
  (A) 15 policy chinh: ratio {0.5,0.7,0.9} x cap {0.08,0.12,0.20,0.35,None}
  (B) 3 phu: bac thang L1/L2/L3 (TS_LADDER_LO/GAPS) nhung dinh = CLOSE
  moc: P0/T170 (dinh HIGH, ham gap goc) va F3 (dinh CLOSE, ham gap goc)

Dung:  python3 sweep_biggap.py            # -> /home/ubuntu/exitfit/biggap/
"""
import csv
import datetime as dt
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exit_engine as E  # noqa: E402

OUT = "/home/ubuntu/exitfit"
BIG = os.path.join(OUT, "biggap")
os.makedirs(BIG, exist_ok=True)
RES_PKL = os.path.join(BIG, "results.pkl")

GMT7 = 7 * 3600000
DAY = 86400000
EQ0 = 35000.0
T2022 = dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000
T2024 = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000
T2026 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000

F = np.float32
INF = np.float32(np.inf)

LADDERS = {  # profiles/x1_tl_l1|l2|l3.properties
    "L1": ([0.00, 0.10, 0.25, 0.50, 1.00], [0.04, 0.08, 0.15, 0.25, 0.35]),
    "L2": ([0.00, 0.10, 0.25, 0.50, 1.00], [0.04, 0.10, 0.20, 0.35, 0.50]),
    "L3": ([0.50, 1.00], [0.25, 0.40]),
}


def period(ts):
    t = ts + GMT7
    if t < T2022:
        return "BURNIN"
    if t < T2024:
        return "TRAIN"
    if t < T2026:
        return "TEST"
    return "H2026"


# ------------------------------------------------------------------ policies
def make_bb(ratio, cap):
    r = F(ratio)
    c = INF if cap is None else F(cap)

    def g(peak, atr, pred):
        return np.minimum(F(peak) * r, c)
    tag = "BB_%d_%s" % (round(100 * ratio), "nc" if cap is None else ("%02d" % round(100 * cap)))
    return E.Policy(tag, g, "close", 0, "close-peak: gap=min(%.2f*peak, %s)" % (ratio, cap))


def make_ladder(name):
    lo, gaps = LADDERS[name]
    lo = np.array(lo, dtype=np.float32)
    gaps = np.array(gaps, dtype=np.float32)

    def g(peak, atr, pred):
        i = int(np.searchsorted(lo, F(peak), side="right")) - 1
        if i < 0:
            return F(0)
        return gaps[i]
    return E.Policy("LAD_%s_close" % name, g, "close", 0, "ladder %s, peak=close" % name)


def policies():
    ps = [E.make_p0(), E.make_f3()]                       # moc
    for ratio in (0.5, 0.7, 0.9):
        for cap in (0.08, 0.12, 0.20, 0.35, None):        # 15 chinh
            ps.append(make_bb(ratio, cap))
    for nm in ("L1", "L2", "L3"):                          # 3 phu
        ps.append(make_ladder(nm))
    return ps


# ------------------------------------------------------------------ run
def run_all():
    all_res = {}
    if os.path.exists(RES_PKL):
        with open(RES_PKL, "rb") as f:
            all_res = pickle.load(f)
    todo = [p for p in policies() if p.name not in all_res]
    if not todo:
        return all_res
    clusters = E.load_clusters()
    bars = E.load_bars()
    for pol in todo:
        res = []
        for cl in clusters:
            if cl["cid"] not in bars:
                continue
            r = E.simulate(cl, bars, pol)
            if r["ok"]:
                res.append(r)
        res = [r for r in res if r["n_legs"] >= 1]
        all_res[pol.name] = res
        with open(RES_PKL, "wb") as f:      # luu TUNG policy -> resume duoc
            pickle.dump(all_res, f, protocol=4)
        print("done %-14s n=%d" % (pol.name, len(res)), flush=True)
    return all_res


# ------------------------------------------------------------------ metrics
def equity_metrics(sel):
    """Equity proxy (chot TRUOC §5): cong don SumPnL theo NGAY THOAT, nen = 35000."""
    if not sel:
        return {"cagr": float("nan"), "maxdd": float("nan"), "calmar": float("nan")}
    t0 = min(r["t0"] for r in sel)
    t1 = max(r["exit_ts"] for r in sel)
    d0, d1 = int((t0 + GMT7) // DAY), int((t1 + GMT7) // DAY)
    pnl_by_day = {}
    for r in sel:
        d = int((r["exit_ts"] + GMT7) // DAY)
        pnl_by_day[d] = pnl_by_day.get(d, 0.0) + r["pnl"]
    eq = EQ0
    curve = []
    for d in range(d0, d1 + 1):
        eq += pnl_by_day.get(d, 0.0)
        curve.append(eq)
    curve = np.asarray(curve)
    peak = np.maximum.accumulate(curve)
    dd = curve / peak - 1.0
    maxdd = float(dd.min())
    ndays = max(1, d1 - d0 + 1)
    cagr = float((curve[-1] / EQ0) ** (365.0 / ndays) - 1.0)
    calmar = float(cagr / abs(maxdd)) if maxdd < 0 else float("nan")
    return {"cagr": cagr, "maxdd": maxdd, "calmar": calmar, "n_days": ndays,
            "eq_end": float(curve[-1]), "t0": t0, "t1": t1}


def metrics(res, per):
    sel = [r for r in res if period(r["t0"]) == per]
    if not sel:
        return None
    pnl = np.array([r["pnl"] for r in sel])
    peakh = np.array([r["peak_rate"] for r in sel])          # peak HIGH (co dinh giua policy)
    peakc = np.array([r["close_peak_rate"] for r in sel])
    reason = np.array([r["reason"] for r in sel])
    hold_h = np.array([(r["exit_ts"] - r["t0"]) / 3600000.0 for r in sel])
    exit_rate = np.array([r["price_tp"] / r["entry_exit"] - 1.0 for r in sel])
    out = {
        "n": len(sel), "sum": float(pnl.sum()), "net_per": float(pnl.mean()),
        "med": float(np.median(pnl)), "win": float(np.mean(pnl > 0)),
        "tsloss": float(np.mean(reason == "TS168")),
        "trail_pct": float(np.mean(reason == "TRAIL")),
        "avg_peak_high": float(peakh.mean()), "avg_peak_close": float(peakc.mean()),
        "avg_exit_rate": float(exit_rate.mean()),
        "hold_med_h": float(np.median(hold_h)), "hold_sum_h": float(hold_h.sum()),
    }
    span_days = (max(r["exit_ts"] for r in sel) - min(r["t0"] for r in sel)) / DAY
    out["turnover"] = float(hold_h.sum() / (max(span_days, 1e-9) * 24.0))
    for name, lo in (("p20", 0.20), ("p50", 0.50), ("p100", 1.00)):
        m = peakh >= lo                                    # nhom theo peak HIGH (co dinh)
        out["n_" + name] = int(m.sum())
        out["cap_" + name] = float(np.median(exit_rate[m] / peakh[m])) if m.sum() else float("nan")
        out["sum_" + name] = float(pnl[m].sum())
    out.update(equity_metrics(sel))
    return out


def boot_diff(res_x, res_b, per, nrep=2000, seed=20260923, inflate=1.0):
    """CI bootstrap BLOCK-NGAY cho hieu net/trade (x - b) tren TEST."""
    kx = {(r["t0"], r["sym"]): r for r in res_x if period(r["t0"]) == per}
    kb = {(r["t0"], r["sym"]): r for r in res_b if period(r["t0"]) == per}
    keys = sorted(set(kx) & set(kb))
    day = np.array([((k[0] + GMT7) // DAY) for k in keys])
    diff = np.array([kx[k]["pnl"] - kb[k]["pnl"] for k in keys])
    days = np.unique(day)
    by_day = {d: np.where(day == d)[0] for d in days}
    rng = np.random.RandomState(seed)
    means = np.empty(nrep)
    for i in range(nrep):
        pick = rng.choice(days, size=len(days), replace=True)
        ix = np.concatenate([by_day[d] for d in pick])
        means[i] = diff[ix].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    mid = float(diff.mean())
    half = max(mid - lo, hi - mid) * inflate
    return {"d": mid, "lo": float(lo), "hi": float(hi),
            "lo_i": mid - half, "hi_i": mid + half, "n_pairs": len(keys), "n_days": len(days)}


def main():
    all_res = run_all()
    pols = [p for p in policies()]
    by_name = {p.name: p for p in pols}
    per_day_mean = {}
    rows = []
    # he so multiplicity: 15 policy chinh
    infl = 1.21 * float(np.sqrt(2 * np.log(15)))
    print("inflate = 1.21 * sqrt(2 ln 15) = %.4f" % infl, flush=True)
    base = all_res["P0"]
    for nm in all_res:
        mtr, mte, mbi = metrics(all_res[nm], "TRAIN"), metrics(all_res[nm], "TEST"), metrics(all_res[nm], "BURNIN")
        bd = boot_diff(all_res[nm], base, "TEST", inflate=infl) if nm != "P0" else None
        r = {"policy": nm, "desc": by_name[nm].desc, "peak_mode": by_name[nm].peak_mode}
        r["train_n"] = mtr["n"]
        r["test_n"] = mte["n"]
        r["burnin_n"] = mbi["n"] if mbi else 0
        r["train_sum"] = mtr["sum"]
        r["train_calmar"] = mtr["calmar"]
        r["train_maxdd"] = mtr["maxdd"]
        r["test_sum"] = mte["sum"]
        r["test_net_per"] = mte["net_per"]
        r["test_maxdd"] = mte["maxdd"]
        r["test_cagr"] = mte["cagr"]
        r["test_calmar"] = mte["calmar"]
        r["test_win"] = mte["win"]
        r["test_tsloss"] = mte["tsloss"]
        r["test_avg_peak_high"] = mte["avg_peak_high"]
        r["test_hold_med_h"] = mte["hold_med_h"]
        r["test_turnover"] = mte["turnover"]
        for g in ("p20", "p50", "p100"):
            r["test_n_" + g] = mte["n_" + g]
            r["test_cap_" + g] = mte["cap_" + g]
            r["test_sum_" + g] = mte["sum_" + g]
        r["d_net_per"] = bd["d"] if bd else 0.0
        r["ci_lo"] = bd["lo_i"] if bd else float("nan")
        r["ci_hi"] = bd["hi_i"] if bd else float("nan")
        r["ci_lo_raw"] = bd["lo"] if bd else float("nan")
        r["ci_hi_raw"] = bd["hi"] if bd else float("nan")
        r["n_pairs"] = bd["n_pairs"] if bd else float("nan")
        r["n_days"] = bd["n_days"] if bd else float("nan")
        rows.append(r)

    base_row = [x for x in rows if x["policy"] == "P0"][0]

    def grade(r):
        b = base_row
        ok_a = r["test_sum"] > b["test_sum"] and r["test_calmar"] > b["test_calmar"]
        ok_b = r["train_sum"] >= b["train_sum"] and r["train_calmar"] >= b["train_calmar"]
        ok_c = (r["policy"] != "P0") and (r["ci_lo"] > 0 or r["ci_hi"] < 0) and r["d_net_per"] > 0
        r["ok_a"], r["ok_b"], r["ok_c"] = ok_a, ok_b, ok_c
        if ok_a and ok_b and ok_c:
            r["verdict"] = "GO"
        elif ok_a and ok_b:
            r["verdict"] = "THIEU-CI"
        elif ok_a:
            r["verdict"] = "TEST-only"
        elif r["test_sum"] <= b["test_sum"] and r["test_calmar"] <= b["test_calmar"]:
            r["verdict"] = "duoi-P0"
        else:
            r["verdict"] = "hon-1-chieu"

    for r in rows:
        grade(r)
    rows.sort(key=lambda r: -r["test_sum"])
    with open(os.path.join(BIG, "biggap_table.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---- in bang
    lines = []
    A = lines.append
    A("SO POLICY DO = %d (2 moc P0/F3 + 15 chinh + 3 phu)  |  inflate CI = x%.4f" % (len(rows), infl))
    A("")
    hdr = ("%-14s %9s %9s %8s %8s %7s %7s %6s %6s %6s %6s %9s %18s %s")
    A(hdr % ("policy", "TE_SumPnL", "TE_Calmar", "TE_maxDD", "TE_CAGR", "cap20", "cap50", "n100",
             "cap100", "n", "tsl%", "hold_h", "dTE/tr CI(x1.21m)", "verdict"))
    for r in rows:
        A(hdr % (r["policy"], "%.0f" % r["test_sum"], "%.2f" % r["test_calmar"],
                 "%.2f%%" % (100 * r["test_maxdd"]), "%.1f%%" % (100 * r["test_cagr"]),
                 "%.3f" % r["test_cap_p20"], "%.3f" % r["test_cap_p50"], "%d" % r["test_n_p100"],
                 "%.3f" % r["test_cap_p100"], "%d" % r["test_n"],
                 "%.1f" % (100 * r["test_tsloss"]), "%.0f" % r["test_hold_med_h"],
                 "[%.2f,%.2f]" % (r["ci_lo"], r["ci_hi"]), r["verdict"]))
    A("")
    A("TRAIN (chan):")
    for r in rows:
        A("  %-14s TR_SumPnL=%9.0f  TR_Calmar=%6.2f  TR_maxDD=%7.2f%%  n=%d"
          % (r["policy"], r["train_sum"], r["train_calmar"], 100 * r["train_maxdd"], r["train_n"]))
    A("")
    A("KIEM CHUNG THUOC (chot TRUOC §5):")
    p0 = base_row
    f3 = [x for x in rows if x["policy"] == "F3"][0]
    A("  (1) SumPnL P0 toan DEV = %.0f  (sim that 76070, lech %.2f%%)"
      % (p0_dev_sum(all_res), 100 * abs(p0_dev_sum(all_res) / 76070.0 - 1)))
    A("  (2) Calmar proxy P0=%.2f vs F3=%.2f  => huong %s (sim that: P0 4.64 > F3 3.52)"
      % (p0["test_calmar"], f3["test_calmar"],
         "DUNG" if p0["test_calmar"] > f3["test_calmar"] else "DAO -> proxy KHONG dung duoc"))
    txt = "\n".join(lines)
    print(txt, flush=True)
    open(os.path.join(BIG, "biggap_summary.txt"), "w").write(txt + "\n")
    with open(RES_PKL, "wb") as f:
        pickle.dump(all_res, f, protocol=4)


def base_sum(all_res):
    return sum(r["pnl"] for r in all_res["P0"] if period(r["t0"]) == "TEST")


def p0_dev_sum(all_res):
    return sum(r["pnl"] for r in all_res["P0"])


if __name__ == "__main__":
    main()
