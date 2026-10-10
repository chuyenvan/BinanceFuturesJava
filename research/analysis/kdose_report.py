#!/usr/bin/env python3
"""KDOSE report: gom kdose_d1/chk170/base/post -> e*, nguong canh bao, bang md + KDOSE_RESULT.json (pre-reg §6)."""
import json, logging, sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kdose")
WD = "/home/ubuntu/claude_master/1010/kdose"
REPO = "/home/ubuntu/src/BinanceFuturesJava"
L = lambda n: json.load(open(WD + "/" + n))
d1, c170, base, post = L("kdose_d1.json"), L("kdose_chk170.json"), L("kdose_base.json"), L("kdose_post.json")
A = post["agg"]
ebar = d1["ebar_pct"] / 100
GR = [0.005, 0.01, 0.02, 0.05]


def key(rg, e):
    return "%s|%s" % (rg, e)


def estar(rg, use_ci):
    ok_e, best = True, 0.0
    for e in GR + ["all"]:
        a = A.get(key(rg, e))
        if a is None:
            continue
        p = a["dpnl_pct"]
        f1, f2 = a["G1_42_flip_pass_pct"], a["G2_flip_pass_pct"]
        if use_ci:
            c = max(abs(p["lo"]), abs(p["hi"])) <= 3 and f1["hi"] <= 2 and f2["hi"] <= 2
        else:
            c = abs(p["mean"]) <= 3 and f1["mean"] <= 2 and f2["mean"] <= 2
        if not c:
            break
        best = ebar if e == "all" else e
    return best


def interp0(rg):
    """e* noi suy tuyen tinh tren [0; 0,5%] (m(0) = 0) neu 0,5% da vuot."""
    a = A[key(rg, 0.005)]
    xs = []
    for m, thr in ((abs(a["dpnl_pct"]["mean"]), 3.0), (a["G1_42_flip_pass_pct"]["mean"], 2.0), (a["G2_flip_pass_pct"]["mean"], 2.0)):
        if m > thr:
            xs.append(0.005 * thr / m)
    return min(xs) if xs else None


def f(c, nd=2):
    return "%.*f [%.*f; %.*f]" % (nd, c["mean"], nd, c["lo"], nd, c["hi"]) if c["n"] > 1 else "%.*f" % (nd, c["mean"])


def table(rg):
    h = ("| e | flipPASS G0 | G1 (K24+SF s42) | G2 (K16) | phút có đổi G1 | Δp15 p50/p99 | Δq p99 G1 | S1 top24/đáy24 đổi | "
         "Δgiá vào bps (mọi chân / chân lỗi) | ΔΣPnL% [CI] |")
    rows = [h, "|" + "---|" * 10]
    for e in GR + ["all"]:
        a = A.get(key(rg, e))
        if a is None:
            continue
        lab = "ē=%.1f%%" % (100 * ebar) if e == "all" else "%.1f%%" % (100 * e)
        rows.append("| %s | %s | %s | %s | %s | %.2f%% / %.1f%% | %.2f%% | %.0f%% / %.0f%% | %+.2f / %+.2f | %s |" % (
            lab, f(a["G0_flip_pass_pct"], 1), f(a["G1_42_flip_pass_pct"], 1), f(a["G2_flip_pass_pct"], 1),
            f(a["G1_42_min_any_pct"], 3), 100 * a["dp15_p50"]["mean"], 100 * a["dp15_p99"]["mean"],
            100 * a["G1_42_dq_p99"]["mean"], a["s1_K24_top_changed_pct"]["mean"], a["s1_K24_bot_changed_pct"]["mean"],
            a["entry_mean_bps_all"]["mean"], a["entry_mean_bps_aff"]["mean"], f(a["dpnl_pct"], 2)))
    return "\n".join(rows)


res = dict(prereg="docs/prereg/PREREG_KDOSE.md", ebar_pct=100 * ebar, d1=d1, d1_sample170=c170, base=base, post=post,
           estar={rg: dict(mean=estar(rg, False), ci=estar(rg, True),
                           interp=(interp0(rg) if estar(rg, False) == 0 else None)) for rg in ("R1", "R2")})
for rg in ("R1", "R2"):
    es = res["estar"][rg]
    e_use = es["mean"] if es["mean"] > 0 else (es["interp"] or 0.0)
    res["estar"][rg]["alert_warn_pct"] = 100 * e_use / 2
    res["estar"][rg]["alert_crit_pct"] = 100 * e_use
json.dump(res, open(REPO + "/docs/result/KDOSE_RESULT.json", "w"), indent=1, default=float)
open(WD + "/kdose_tables.md", "w").write("### R1\n" + table("R1") + "\n\n### R2\n" + table("R2") + "\n")
log.info("estar %s", res["estar"])
