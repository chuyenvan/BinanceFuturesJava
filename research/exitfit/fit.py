"""EXIT FIT — BUOC 2: fit co ky luat tren TRAIN, bao cao out-of-sample (TEST).

Chay:  python3 fit.py      # -> /home/ubuntu/exitfit/fit_results.pkl + fit_table.csv + fit_summary.txt
17 policy da chot TRUOC (docs/prereg/PREREG_EXIT_FIT.md muc 3.2): chon tren TRAIN theo net/trade, bao cao TEST
+ CI bootstrap block-ngay (1000 rep, seed 20260923) cho hieu so voi P0.
"""
import datetime as dt
import os
import pickle
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exit_engine as E  # noqa: E402

OUT = "/home/ubuntu/exitfit"
GMT7 = 7 * 3600000
T2022 = dt.datetime(2022, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000
T2024 = dt.datetime(2024, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000
T2026 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc).timestamp() * 1000
DAY = 86400000


def policies():
    ps = [E.make_p0()]
    for a in (0.005, 0.01, 0.02):
        for b in (0.0, 0.15, 0.30):
            ps.append(E.make_f1(a, b))
    for c in (0.5, 0.75, 1.0):
        for k in (60, 240):
            ps.append(E.make_f2(c, k))
    ps.append(E.make_f3())
    return ps


def period(ts):
    t = ts + GMT7
    if t < T2022:
        return "BURNIN"
    if t < T2024:
        return "TRAIN"
    if t < T2026:
        return "TEST"
    return "H2026"


def run_all():
    path = os.path.join(OUT, "fit_results.pkl")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return pickle.load(f)
    clusters = E.load_clusters()
    bars = E.load_bars()
    all_res = {}
    for pol in policies():
        res = []
        for cl in clusters:
            if cl["cid"] not in bars:
                continue
            r = E.simulate(cl, bars, pol)
            if r["ok"]:
                res.append(r)
        all_res[pol.name] = res
        with open(path, "wb") as f:          # luu TUNG policy -> resume duoc
            pickle.dump(all_res, f, protocol=4)
        print("done policy %-14s clusters=%d" % (pol.name, len(res)), flush=True)
    return all_res


def metrics(res, per):
    sel = [r for r in res if period(r["t0"]) == per]
    if not sel:
        return None
    pnl = np.array([r["pnl"] for r in sel])
    peak = np.array([r["peak_rate"] for r in sel])
    reason = np.array([r["reason"] for r in sel])
    out = {
        "n": len(sel), "sum": float(pnl.sum()), "net_per": float(pnl.mean()),
        "med": float(np.median(pnl)), "win": float(np.mean(pnl > 0)),
        "tsloss": float(np.mean(reason == "TS168")),
        "trail_pct": float(np.mean(reason == "TRAIL")),
        "avg_peak": float(peak.mean()),
    }
    exit_rate = np.array([r["price_tp"] / r["entry_exit"] - 1.0 for r in sel])
    out["avg_exit_rate"] = float(exit_rate.mean())
    out["capture_all"] = float(np.mean(np.where(peak > 1e-9, exit_rate / np.maximum(peak, 1e-9), 0.0)))
    for name, lo in (("p20", 0.20), ("p50", 0.50), ("p100", 1.00)):
        m = peak >= lo
        out["n_" + name] = int(m.sum())
        out["cap_" + name] = float(np.mean(exit_rate[m] / peak[m])) if m.sum() else float("nan")
        mt = m & (reason == "TRAIL")
        out["captrail_" + name] = float(np.mean(exit_rate[mt] / peak[mt])) if mt.sum() else float("nan")
    return out


def boot_diff(res_a, res_b, per, nrep=1000, seed=20260923):
    """CI bootstrap BLOCK-NGAY cho hieu net/trade (a - b), cap (t0, sym) de ghep dung."""
    key_a = {(r["t0"], r["sym"]): r for r in res_a if period(r["t0"]) == per}
    key_b = {(r["t0"], r["sym"]): r for r in res_b if period(r["t0"]) == per}
    keys = sorted(set(key_a) & set(key_b))
    day = np.array([((k[0] + GMT7) // DAY) for k in keys])
    da = np.array([key_a[k]["pnl"] for k in keys])
    db = np.array([key_b[k]["pnl"] for k in keys])
    diff = da - db
    days = np.unique(day)
    idx_by_day = {d: np.where(day == d)[0] for d in days}
    rng = np.random.RandomState(seed)
    means = np.empty(nrep)
    for i in range(nrep):
        pick = rng.choice(days, size=len(days), replace=True)
        ix = np.concatenate([idx_by_day[d] for d in pick])
        means[i] = diff[ix].mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(diff.mean()), float(lo), float(hi), len(keys), len(days)


def main():
    all_res = run_all()
    names = list(all_res.keys())
    base = "P0"
    rows = []
    for nm in names:
        mtr = metrics(all_res[nm], "TRAIN")
        mte = metrics(all_res[nm], "TEST")
        mbi = metrics(all_res[nm], "BURNIN")
        if mtr is None:
            continue
        d, lo, hi, nk, nd = boot_diff(all_res[nm], all_res[base], "TEST")
        rows.append({"policy": nm, "train_net_per": mtr["net_per"], "train_sum": mtr["sum"],
                     "test_net_per": mte["net_per"], "test_sum": mte["sum"], "test_n": mte["n"],
                     "test_win": mte["win"], "test_tsloss": mte["tsloss"],
                     "test_cap_p20": mte["cap_p20"], "test_cap_p50": mte["cap_p50"],
                     "test_cap_p100": mte["cap_p100"], "test_captrail_p20": mte["captrail_p20"],
                     "test_avg_peak": mte["avg_peak"], "test_avg_exit": mte["avg_exit_rate"],
                     "burnin_net_per": mbi["net_per"] if mbi else float("nan"),
                     "d_net_per": d, "ci_lo": lo, "ci_hi": hi, "n_pairs": nk, "n_days": nd})
    rows.sort(key=lambda r: -r["train_net_per"])
    with open(os.path.join(OUT, "fit_table.csv"), "w", newline="") as f:
        w = __import__("csv").DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow(r)
    best = rows[0]
    lines = []
    lines.append("SO POLICY DA THU = %d (P0 + F1 x9 + F2 x6 + F3)\n" % len(rows))
    hdr = "%-14s %10s %10s %10s %8s %8s %8s %8s %8s %8s %22s"
    lines.append(hdr % ("policy", "TR_net/tr", "TE_net/tr", "TE_sum", "TE_win%", "TE_tsl%",
                        "capP20", "capP50", "capP100", "dTE/tr", "CI block-ngay"))
    for r in rows:
        lines.append(hdr % (r["policy"], "%.2f" % r["train_net_per"], "%.2f" % r["test_net_per"],
                            "%.0f" % r["test_sum"], "%.1f" % (100 * r["test_win"]),
                            "%.1f" % (100 * r["test_tsloss"]), "%.3f" % r["test_cap_p20"],
                            "%.3f" % r["test_cap_p50"], "%.3f" % r["test_cap_p100"],
                            "%.2f" % r["d_net_per"], "[%.2f, %.2f]" % (r["ci_lo"], r["ci_hi"])))
    n_sig = sum(1 for r in rows if r["policy"] != base and (r["ci_lo"] > 0 or r["ci_hi"] < 0))
    lines.append("\nCHON TREN TRAIN: %s (net/trade TRAIN = %.2f)" % (best["policy"], best["train_net_per"]))
    lines.append("Out-of-sample TEST cua %s: net/trade=%.2f (P0=%.2f)  SumPnL=%.0f  win%%=%.1f  tsloss%%=%.1f"
                 % (best["policy"], best["test_net_per"], rows[[r["policy"] for r in rows].index(base)]["test_net_per"],
                    best["test_sum"], 100 * best["test_win"], 100 * best["test_tsloss"]))
    lines.append("So policy co CI (hieu vs P0 tren TEST) KHONG chua 0: %d / %d" % (n_sig, len(rows) - 1))
    txt = "\n".join(lines)
    print(txt)
    open(os.path.join(OUT, "fit_summary.txt"), "w").write(txt + "\n")


if __name__ == "__main__":
    main()
