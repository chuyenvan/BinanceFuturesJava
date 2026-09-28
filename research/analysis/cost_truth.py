#!/usr/bin/env python3
"""cost_truth.py — D1: CHI PHI THAT (0 sim).

(i)  doc code SIM: gia vao/ra o dau  ->  docs/prereg/PREREG_COST_TRUTH.md  §2
(ii) slip CO DAU tach theo LOAI LEG tren 991 chan THAT (block-72h, 2000 rep, seed 20260905, inflate(k=5))
(iii) chot 3 muc base/stress/legacy (%/vong)

Thuan Python, offline, KHONG sim/train, KHONG cham 242.
Input (da co trong repo, KHONG fetch lai):
  research/live_fills_audit/data/trades.csv   (991 chan that)
  research/live_fills_audit/data/orders.csv   (388 lenh)
  research/live_fills_audit/data/slips.json   (976 chan khop nen 1m)
Output: docs/result/cost_truth.json
"""
import csv, json, os, math, datetime as dt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
D = os.path.join(REPO, "research", "live_fills_audit", "data")
OUT = os.path.join(REPO, "docs", "result", "cost_truth.json")

BLOCK_H, NREP, SEED = 72, 2000, 20260905
T0 = dt.datetime(2026, 6, 24, 13, 31, tzinfo=dt.timezone.utc).timestamp()
CRASH_PROXY = -0.01      # bar return <= -1.0%  (pre-reg §3 buoc C)


def inflate(k):
    k = int(k)
    if k < 1:
        raise ValueError
    return 1.0 if k == 1 else math.sqrt(2.0 * math.log(k))


# ---------------- load ----------------
trades = list(csv.DictReader(open(os.path.join(D, "trades.csv"))))
orders = {r["orderId"]: r for r in csv.DictReader(open(os.path.join(D, "orders.csv")))}
slips = json.load(open(os.path.join(D, "slips.json")))

for t in trades:
    t["t"] = int(t["time_ms"]); t["q"] = float(t["qty"])
    t["px"] = float(t["price"]); t["pnl"] = float(t["realizedPnl"])

# ---------------- buoc A: vai tro lenh (order level) ----------------
od = {}
for t in trades:
    o = od.setdefault(t["orderId"], dict(q=0.0, pnl=0.0, side=None, t=0, sym=None, role=None))
    o["q"] += t["q"]; o["pnl"] += t["pnl"]; o["side"] = t["side"]
    o["t"] = max(o["t"], t["t"]); o["sym"] = t["symbol"]
    r = orders.get(t["orderId"])
    o["role"] = ("CLOSE" if (r["reduceOnly"] == "True" or r["closePosition"] == "True")
                 else "OPEN") if r else "UNKNOWN"

# ---------------- buoc B: trang thai vi the (signed qty) ----------------
bysym = {}
for oid, o in od.items():
    sgn = +1 if o["side"] == "BUY" else -1
    bysym.setdefault(o["sym"], []).append((o["t"], oid, sgn, o["q"], o["pnl"], o["role"]))
order_type = {}
for sym, lst in bysym.items():
    lst.sort()
    pos = 0.0
    for ts, oid, sgn, q, pnl, role in lst:
        if role == "CLOSE":
            ty = "EXIT_STOP_MARKET" if pnl >= 0 else "EXIT_STOP_LOSS"
        elif role == "OPEN":
            ty = "DCA" if ((pos > 1e-9 and sgn > 0) or (pos < -1e-9 and sgn < 0)) else "ENTRY"
        else:
            ty = "UNKNOWN"
        order_type[oid] = ty
        pos += sgn * q

# ---------------- buoc C: ENTRY -> PREDICT / BIG_DOWN (proxy nen) ----------------
bar_ret = {}
for s in slips:
    key = (s["symbol"], s["side"], s["time"])
    bar_ret[key] = (s["c"] - s["o"]) / s["o"] if s["o"] else 0.0

key_order = {}
for t in trades:
    key_order[(t["symbol"], t["side"], t["t"])] = t["orderId"]

# map leg -> class (bar-dependent for ENTRY)
legs = []
for s in slips:
    sym, side, ts = s["symbol"], s["side"], s["time"]
    oid = key_order.get((sym, side, ts))
    ty = order_type.get(oid, "UNKNOWN") if oid is not None else "UNKNOWN"
    if ty == "ENTRY":
        r = bar_ret[(sym, side, ts)]
        ty = "ENTRY_BIG_DOWN" if r <= CRASH_PROXY else "ENTRY_PREDICT"
    legs.append(dict(sym=sym, side=side, ts=ts, cls=ty, s_close=s["s_close"],
                     s_open=s["s_open"], bar_ret=bar_ret[(sym, side, ts)],
                     proxy=s["proxy"], abs_slip=abs(s["s_close"])))

# count ALL legs (incl. those without kline) by order type
legs_all_n = {}
for t in trades:
    ty = order_type.get(t["orderId"], "UNKNOWN")
    legs_all_n[ty] = legs_all_n.get(ty, 0) + 1

# UNKNOWN legs (no kline) : count by order_type
all_legs_n = len(trades)
matched_n = len(slips)


def blk(ts):
    return int((ts / 1000.0 - T0) // (BLOCK_H * 3600))


def boot_ci(vals, blocks, infl, stat="mean"):
    rng = np.random.default_rng(SEED)
    v = np.asarray(vals, float); b = np.asarray(blocks)
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


INFL5 = inflate(5)
CLASSES = ["ENTRY_PREDICT", "ENTRY_BIG_DOWN", "DCA", "EXIT_STOP_MARKET", "EXIT_STOP_LOSS", "UNKNOWN"]
res = {}
for c in CLASSES:
    xs = [l for l in legs if l["cls"] == c]
    if not xs:
        res[c] = dict(n=0); continue
    vals = [100.0 * x["s_close"] for x in xs]   # %/chan
    bl = [blk(x["ts"]) for x in xs]
    m = boot_ci(vals, bl, INFL5, "mean")
    md = boot_ci(vals, bl, INFL5, "median")
    nb = len(set(bl))
    res[c] = dict(
        n=len(xs), n_blocks=nb, n_all_legs=legs_all_n.get(c, 0),
        mean_pct=m["point"], mean_ci95_raw=[m["lo_raw"], m["hi_raw"]],
        mean_ci95_inf5=[m["lo_inf"], m["hi_inf"]],
        median_pct=md["point"], median_ci95_inf5=[md["lo_inf"], md["hi_inf"]],
        mean_abs_pct=float(np.mean([100.0 * x["abs_slip"] for x in xs])),
        mean_s_open_pct=float(np.mean([100.0 * x["s_open"] for x in xs])),
        bar_ret_mean_pct=float(np.mean([100.0 * x["bar_ret"] for x in xs])),
        ci_degenerate=(nb <= 1),
        signif_pos=(m["lo_inf"] > 0),
        signif_neg=(m["hi_inf"] < 0),
    )

# sensitivity: crash proxy thresholds on ENTRY legs
ent = [l for l in legs if l["cls"] in ("ENTRY_PREDICT", "ENTRY_BIG_DOWN")]
sens = {}
for nm, thr in [("-1.0%", -0.01), ("-3.157%", -0.03157), ("<0 (moi nen do)", 0.0)]:
    xs = [l for l in ent if l["bar_ret"] <= thr]
    sens[nm] = dict(n=len(xs),
                    mean_pct=float(np.mean([100.0 * x["s_close"] for x in xs])) if xs else None,
                    median_pct=float(np.median([100.0 * x["s_close"] for x in xs])) if xs else None)

# overall + non-UNKNOWN
ov = [100.0 * l["s_close"] for l in legs]
ov_nu = [100.0 * l["s_close"] for l in legs if l["cls"] != "UNKNOWN"]

# ---------------- costs ----------------
FEE_LEG = 0.0491           # %/chan (measured, RESULT_LIVE_FILLS_AUDIT)
FEER = 2 * FEE_LEG         # 0.0982
H2_MED = 0.1116 - FEER     # 0.0134
H2_P90 = 0.1500 - FEER     # 0.0518
base = FEER + H2_MED
stress = FEER + H2_P90
legacy = 0.20 + 0.60

# crash-entry extra per round (share of ENTRY legs x mean slip), reported SEPARATELY
ent_all = [l for l in legs if l["cls"] in ("ENTRY_PREDICT", "ENTRY_BIG_DOWN")]
share_crash = (sum(1 for l in ent_all if l["cls"] == "ENTRY_BIG_DOWN") / len(ent_all)) if ent_all else 0.0
mean_crash = res["ENTRY_BIG_DOWN"].get("mean_pct", 0.0) if res["ENTRY_BIG_DOWN"]["n"] else 0.0
crash_extra_per_legmix = share_crash * mean_crash   # %/vong contribution on the ENTRY side

out = dict(
    generated=dt.datetime.utcnow().isoformat() + "Z",
    prereg="docs/prereg/PREREG_COST_TRUTH.md", prereg_commit="8895f82",
    n_legs=all_legs_n, n_legs_matched_kline=matched_n,
    all_legs_by_type=legs_all_n,
    block_h=BLOCK_H, nrep=NREP, seed=SEED, inflate_k5=INFL5,
    classes=res, sensitivity_crash_proxy=sens,
    overall_mean_pct=float(np.mean(ov)), overall_median_pct=float(np.median(ov)),
    overall_mean_pct_exUNKNOWN=float(np.mean(ov_nu)) if ov_nu else None,
    costs_pct_per_round=dict(base=base, stress=stress, legacy=legacy),
    costs_pct_per_leg=dict(base=base / 2, stress=stress / 2, legacy=legacy / 2),
    crash_entry=dict(share_of_entries=share_crash, mean_slip_pct=mean_crash,
                     extra_pct_per_round_legmix=crash_extra_per_legmix),
)
json.dump(out, open(OUT, "w"), indent=1, ensure_ascii=False)

# ---------------- print ----------------
print("=== D1 COST TRUTH ===  legs=%d matched_kline=%d  inflate(5)=%.4f" % (all_legs_n, matched_n, INFL5))
print("%-18s %4s %9s %9s %18s %8s" % ("class", "n", "mean%", "median%", "mean CI95(infl5)%", "mean|.|%"))
for c in CLASSES:
    r = res[c]
    if not r["n"]:
        print("%-18s %4d" % (c, 0)); continue
    print("%-18s %4d %+9.4f %+9.4f  [%+.4f,%+.4f] %8.4f  sig%+d" % (
        c, r["n"], r["mean_pct"], r["median_pct"], r["mean_ci95_inf5"][0], r["mean_ci95_inf5"][1],
        r["mean_abs_pct"], 1 if r["signif_pos"] else (-1 if r["signif_neg"] else 0)))
print("overall mean=%+.4f%% median=%+.4f%%  (ex-UNKNOWN mean=%+.4f%%)" % (
    out["overall_mean_pct"], out["overall_median_pct"], out["overall_mean_pct_exUNKNOWN"]))
print("costs /round: base=%.4f%%  stress=%.4f%%  legacy=%.4f%%" % (base, stress, legacy))
print("crash entry: share=%.3f  mean=%+.3f%%  extra/round(legmix)=%+.4f%%" % (
    share_crash, mean_crash, crash_extra_per_legmix))
print("wrote", OUT)
