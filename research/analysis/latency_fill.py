#!/usr/bin/env python3
"""latency_fill.py — D6: ĐỘ TRỄ + GIÁ KHỚP vs NẾN QUYẾT ĐỊNH (0 sim).

Phân biệt (a) lệch mốc đo / (b) latency live / (c) look-ahead sim cho slip "vào lúc sập"
+1,675%/chân (n=37) của RESULT_COST_TRUTH — lần này đo vs CLOSE NẾN QUYẾT ĐỊNH (đúng mốc sim),
có `level` thật từ OrderTargetInfo, và đo latency.

Input:
  --orders  orders_dump.csv  (đầu ra của research/live_fills_audit/OrderIntentDump.java trên 242)
  trades/orders: research/live_fills_audit/data/{trades,orders}.csv
Output:
  --json docs/result/latency_fill.json  + stdout tóm tắt

0 sim · thuần Python · offline.
"""
import argparse, csv, json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
D = os.path.join(REPO, "research", "live_fills_audit", "data")

BLOCK_H, NREP, SEED = 72, 2000, 20260905
# T0 = start of fill window (match RESULT_COST_TRUTH)
import datetime as dt
T0 = dt.datetime(2026, 6, 24, 13, 31, tzinfo=dt.timezone.utc).timestamp()
CRASH = -0.01          # decision-candle bar_ret <= -1%
MATCH_WIN_MS = 3600_000  # 1h


def inflate(k):
    k = int(k)
    if k < 1:
        raise ValueError
    return 1.0 if k == 1 else math.sqrt(2.0 * math.log(k))


def blk(ts_ms):
    return int((ts_ms / 1000.0 - T0) // (BLOCK_H * 3600))


def boot_ci(vals, blocks, infl, stat="mean"):
    rng = np.random.default_rng(SEED)
    v = np.asarray(vals, float)
    b = np.asarray(blocks)
    bidx = {}
    for u in np.unique(b):
        bidx[u] = v[b == u]
    keys = list(bidx.keys())
    est = np.mean(v) if stat == "mean" else np.median(v)
    reps = np.empty(NREP)
    for i in range(NREP):
        pick = rng.choice(keys, size=len(keys), replace=True)
        pool = np.concatenate([bidx[p] for p in pick])
        reps[i] = np.mean(pool) if stat == "mean" else np.median(pool)
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return dict(point=float(est), lo_raw=float(lo), hi_raw=float(hi),
                lo_inf=float(est - (est - lo) * infl), hi_inf=float(est + (hi - est) * infl))


def spearman(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3:
        return float("nan")
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def load_intents(path):
    rows = list(csv.DictReader(open(path)))
    ints = []
    for r in rows:
        ints.append(dict(
            sym=r["symbol"], level=r["level"], startTime=int(r["startTime"]),
            priceOpen=float(r["priceOpen"]), priceClose=float(r["priceClose"]),
            maxPrice=float(r["maxPrice"]), minPrice=float(r["minPrice"]),
        ))
    return ints


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--orders", default=os.path.join(HERE, "..", "..", "latency_fill", "orders_dump.csv"))
    ap.add_argument("--json", default=os.path.join(REPO, "docs", "result", "latency_fill.json"))
    args = ap.parse_args()

    ints = load_intents(args.orders)
    by_sym = {}
    for i in ints:
        by_sym.setdefault(i["sym"], []).append(i)
    for s in by_sym:
        by_sym[s].sort(key=lambda i: i["startTime"])

    trades = list(csv.DictReader(open(os.path.join(D, "trades.csv"))))
    orders = list(csv.DictReader(open(os.path.join(D, "orders.csv"))))

    byoid = {}
    for t in trades:
        byoid.setdefault(t["orderId"], []).append(t)

    buy_entries = [o for o in orders if o["side"] == "BUY" and o["reduceOnly"] == "False"]

    used = set()   # (sym, startTime) intent used once
    legs = []
    unmatched = []
    oid2intent = {}   # orderId -> matched intent (for reconciliation)
    for o in buy_entries:
        sym = o["symbol"]
        ot = int(o["time"])
        cand = [i for i in by_sym.get(sym, [])
                if i["startTime"] <= ot and ot - i["startTime"] <= MATCH_WIN_MS]
        # choose largest startTime not already used
        cand = [i for i in cand if (sym, i["startTime"]) not in used]
        if not cand:
            unmatched.append(dict(sym=sym, time=ot))
            continue
        i = cand[-1]
        used.add((sym, i["startTime"]))
        oid2intent[o["orderId"]] = i
        fs = byoid.get(o["orderId"], [])
        if not fs:
            unmatched.append(dict(sym=sym, time=ot, reason="no-fill"))
            continue
        fill_px = sum(float(x["price"]) * float(x["qty"]) for x in fs) / sum(float(x["qty"]) for x in fs)
        t_fill = min(int(x["time_ms"]) for x in fs)
        st0 = i["startTime"]
        close = i["priceClose"]
        opn = i["priceOpen"]
        bar_ret = (close - opn) / opn if opn else 0.0
        slip_dec = (fill_px - close) / close
        lat = (t_fill - (st0 + 60000)) / 1000.0
        legs.append(dict(sym=sym, level=i["level"], ts_fill=t_fill,
                         bar_ret=100.0 * bar_ret, slip_dec_pct=100.0 * slip_dec, lat_s=lat))

    # ---------- groups ----------
    crash = [l for l in legs if l["bar_ret"] <= 100.0 * CRASH]
    norm = [l for l in legs if l["bar_ret"] > 100.0 * CRASH]
    levels = {}
    for l in legs:
        levels.setdefault(l["level"], []).append(l)

    def summarize(name, arr, infl):
        if not arr:
            return dict(n=0)
        vals = [l["slip_dec_pct"] for l in arr]
        bl = [blk(l["ts_fill"]) for l in arr]
        m = boot_ci(vals, bl, infl, "mean")
        md = boot_ci(vals, bl, infl, "median")
        lats = [l["lat_s"] for l in arr]
        return dict(
            n=len(arr), n_blocks=len(set(bl)),
            mean_pct=m["point"], mean_ci95_raw=[m["lo_raw"], m["hi_raw"]],
            mean_ci95_inf=[m["lo_inf"], m["hi_inf"]],
            median_pct=md["point"], median_ci95_inf=[md["lo_inf"], md["hi_inf"]],
            latency_mean_s=float(np.mean(lats)), latency_median_s=float(np.median(lats)),
            bar_ret_mean_pct=float(np.mean([l["bar_ret"] for l in arr])),
            ci_degenerate=(len(set(bl)) <= 1),
            signif_pos=(m["lo_inf"] > 0), signif_neg=(m["hi_inf"] < 0),
        )

    # correlation slip_dec vs latency in crash group
    rho_crash = spearman([l["lat_s"] for l in crash], [l["slip_dec_pct"] for l in crash])
    pear_crash = float(np.corrcoef([l["lat_s"] for l in crash], [l["slip_dec_pct"] for l in crash])[0, 1]) if len(crash) >= 3 else float("nan")

    # binned mean slip_dec by latency (median-split within crash group)
    binned = []
    if len(crash) >= 4:
        med_lat = float(np.median([l["lat_s"] for l in crash]))
        lo = [l for l in crash if l["lat_s"] <= med_lat]
        hi = [l for l in crash if l["lat_s"] > med_lat]
        binned = [
            dict(bin="<=median_lat", n=len(lo), mean_slip_pct=float(np.mean([l["slip_dec_pct"] for l in lo])) if lo else None),
            dict(bin=">median_lat", n=len(hi), mean_slip_pct=float(np.mean([l["slip_dec_pct"] for l in hi])) if hi else None),
        ]

    INFL2, INFL3, INFL5 = inflate(2), inflate(3), inflate(5)
    res = {
        "n_buy_entry_orders": len(buy_entries),
        "n_matched_legs": len(legs),
        "n_unmatched": len(unmatched),
        "level_counts": {k: len(v) for k, v in sorted(levels.items())},
        "crash_threshold": CRASH,
        "crash": summarize("crash", crash, INFL2),
        "normal": summarize("normal", norm, INFL2),
        "crash_infl5": summarize("crash", crash, INFL5),
        "crash_infl3": summarize("crash", crash, INFL3),
        "levels": {k: summarize(k, v, INFL3) for k, v in sorted(levels.items())},
        "crash_spearman_lat": rho_crash,
        "crash_pearson_lat": pear_crash,
        "crash_binned_lat": binned,
    }

    # ---------- reconciliation vs RESULT_COST_TRUTH (fill-candle crash legs, vs decision close) ----------
    # RESULT_COST_TRUTH "BIG_DOWN proxy" = fill whose FILL-candle bar_ret <= -1%; s_close = (fill-closeFILL)/closeFILL
    # Here we re-map those SAME legs to the DECISION candle close to show the +1.675% is an anchor artifact.
    slips = json.load(open(os.path.join(D, "slips.json")))
    slipmap = {(s["symbol"], s["side"], s["time"]): s for s in slips}
    rec = []
    for t in trades:
        if t["side"] != "BUY" or t["orderId"] not in oid2intent:
            continue
        i = oid2intent[t["orderId"]]
        s = slipmap.get((t["symbol"], "BUY", int(t["time_ms"])))
        if not s:
            continue
        fill = float(t["price"])
        close = i["priceClose"]; opn = i["priceOpen"]
        rec.append(dict(fill_bar_pct=100.0 * (s["c"] - s["o"]) / s["o"] if s["o"] else 0.0,
                        s_close_pct=100.0 * s["s_close"],
                        slip_dec_pct=100.0 * (fill - close) / close,
                        dec_bar_pct=100.0 * (close - opn) / opn if opn else 0.0))
    bd = [r for r in rec if r["fill_bar_pct"] <= 100.0 * CRASH]
    def _m(a, k):
        return float(np.mean([r[k] for r in a])) if a else float("nan")
    res["reconcile"] = dict(
        n_entry_fills_kline=len(rec),
        n_fill_candle_crash=len(bd),
        bd_s_close_mean_pct=_m(bd, "s_close_pct"),     # should reproduce ~+1.675%
        bd_slip_dec_mean_pct=_m(bd, "slip_dec_pct"),   # vs DECISION close (correct)
        bd_dec_bar_mean_pct=_m(bd, "dec_bar_pct"),
        bd_n_dec_crash=sum(1 for r in bd if r["dec_bar_pct"] <= 100.0 * CRASH),
    )

    # ---------- verdict ----------
    c = res["crash"]
    verdict = None
    reason = ""
    if c["n"] == 0:
        verdict = "NO_CRASH_GROUP"
        reason = "không có leg sập (nến quyết định <=-1%)"
    elif c["ci_degenerate"]:
        verdict = "DEGENERATE_CI"
        reason = "CI thoái hoá (n_blocks<=1) — chỉ mô tả"
    elif not (c["signif_pos"] and c["mean_ci95_inf"][0] > 0):
        verdict = "a_anchor"
        reason = "CI slip_dec nhóm sập CHỨA 0 (mean_ci95_inf=[%.3f, %.3f]) ⇒ lệch mốc đo, không bias" % tuple(c["mean_ci95_inf"])
    else:
        # positive outside CI
        if rho_crash > 0.3 and len(binned) == 2 and binned[0]["mean_slip_pct"] is not None and binned[1]["mean_slip_pct"] is not None and binned[1]["mean_slip_pct"] > binned[0]["mean_slip_pct"]:
            verdict = "b_latency"
            reason = "dương ngoài CI và tăng theo latency (rho=%.2f, binned tăng)" % rho_crash
        elif c["latency_median_s"] <= 10:
            verdict = "c_lookahead"
            reason = "dương ngoài CI nhưng latency≈0 (median %.1fs)" % c["latency_median_s"]
        else:
            verdict = "b_latency_weak"
            reason = "dương ngoài CI, latency>10s nhưng tăng-theo-latency yếu (rho=%.2f)" % rho_crash
    res["verdict"] = verdict
    res["verdict_reason"] = reason

    json.dump(res, open(args.json, "w"), indent=2, ensure_ascii=False)

    # ---------- stdout ----------
    print("=" * 70)
    print("LATENCY_FILL — D6")
    print("BUY-entry orders=%d  matched_legs=%d  unmatched=%d" % (len(buy_entries), len(legs), len(unmatched)))
    print("level_counts:", res["level_counts"])
    print("-" * 70)
    for nm in ("crash", "normal"):
        s = res[nm]
        if s["n"] == 0:
            print("%-8s n=0" % nm); continue
        print("%-8s n=%d  mean=%.3f%% CI95_inf2=[%.3f,%.3f]  median=%.3f%%  lat_mean=%.1fs lat_med=%.1fs  bar_ret=%.2f%%" % (
            nm, s["n"], s["mean_pct"], s["mean_ci95_inf"][0], s["mean_ci95_inf"][1],
            s["median_pct"], s["latency_mean_s"], s["latency_median_s"], s["bar_ret_mean_pct"]))
    print("-" * 70)
    for k, s in sorted(res["levels"].items()):
        if s["n"] == 0:
            print("%-28s n=0" % k); continue
        print("%-28s n=%d  mean=%.3f%% CI95_inf3=[%.3f,%.3f]" % (k, s["n"], s["mean_pct"], s["mean_ci95_inf"][0], s["mean_ci95_inf"][1]))
    print("-" * 70)
    print("crash spearman(lat,slip)=%.3f  pearson=%.3f" % (rho_crash, pear_crash))
    for b in binned:
        print("  bin %-14s n=%d mean_slip=%.3f%%" % (b["bin"], b["n"], b["mean_slip_pct"]))
    print("=" * 70)
    print("VERDICT: %s" % verdict)
    print("  %s" % reason)
    r = res["reconcile"]
    print("-" * 70)
    print("reconcile vs RESULT_COST_TRUTH (fill-candle-crash legs):")
    print("  n_fill_candle_crash=%d  s_close_mean=%.3f%%  slip_dec_mean=%.3f%%  dec_bar_mean=%.2f%%  n_dec_crash=%d" % (
        r["n_fill_candle_crash"], r["bd_s_close_mean_pct"], r["bd_slip_dec_mean_pct"],
        r["bd_dec_bar_mean_pct"], r["bd_n_dec_crash"]))
    print("JSON -> %s" % args.json)


if __name__ == "__main__":
    main()
