#!/usr/bin/env python3
"""label_firsthit_report.py — in bang markdown tu label_firsthit_model.json (+ fh_prep.json, net_train_summary) ra stdout."""
import json, logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("rep")
D = "/home/ubuntu/claude_master/1003/fh"
R = json.load(open(sys.argv[1] if len(sys.argv) > 1 else D + "/label_firsthit_model.json"))
P = json.load(open(D + "/fh_prep.json"))
L = log.info
L("### Nhan FH theo nam (toan universe Aerospike, tick 15')")
L("| nam | n | y=1 | proxy SL (hit SL/tie) | tie | khong cham 168h |")
L("|---|---:|---:|---:|---:|---:|")
for r in P["by_year"]:
    L("| %d | %d | %.4f | %.4f | %.2e | %.4f |" % (r["yr"], r["n"], r["y"], r["sl"], r["tie"], r["none"]))
L("")
L("### Train (Kaggle GPU) — n_train / pos theo fold")
L("| fold | n FH | pos FH | n CTRL | pos CTRL |")
L("|---|---:|---:|---:|---:|")
S = {a: json.load(open("%s/out_%s/net_train_summary.json" % (D, a))) for a in ("FH", "CTRL")}
for f in sorted(S["FH"]["folds"]):
    a, b = S["FH"]["folds"][f], S["CTRL"]["folds"][f]
    L("| %s | %d | %.4f | %d | %.4f |" % (f, a["n_train"], a["pos"], b["n_train"], b["pos"]))
L("purge FH %s / CTRL %s buoc; xgb %s; n_label_old %s n_label_fh %s; phut %s / %s" % (
    S["FH"]["purge_steps_fh"], S["CTRL"]["purge_steps_fh"], S["FH"]["xgb"], S["FH"]["n_label_old"],
    S["FH"]["n_label_fh"], S["FH"]["minutes"], S["CTRL"]["minutes"]))
L("")
L("### (i) rank-IC per-tick, mean 16 fold (hang = score, cot = nhan)")
L("| score | IC vs y_FH | IC vs y_old (retEnd_4h>0,015) |")
L("|---|---:|---:|")
for s in ("FH", "CTRL", "ORIG", "FHm", "CTRLm", "B0"):
    L("| %s | %+.4f | %+.4f |" % (s, R["ic_mean"]["%s|y" % s], R["ic_mean"]["%s|y_old" % s]))
L("")
L("| fold | FH|yFH | CTRL|yFH | FH|yold | CTRL|yold | xs FH~ORIG | xs CTRL~ORIG | xs FH~CTRL |")
L("|---|---:|---:|---:|---:|---:|---:|---:|")
for f in sorted(R["ic_fold"]):
    i, x = R["ic_fold"][f], R["xs_fold"][f]
    L("| %s | %+.4f | %+.4f | %+.4f | %+.4f | %.3f | %.3f | %.3f |" % (
        f, i["FH|y"], i["CTRL|y"], i["FH|y_old"], i["CTRL|y_old"], x["FH~ORIG"], x["CTRL~ORIG"], x["FH~CTRL"]))
L("xs mean: %s" % {k: round(v, 3) for k, v in R["xs_mean"].items()})
L("")
L("### (ii) top-16/tick: proxy SL / mean ret168 / y_FH / y_old")
L("| score | nam | SL | ret168 | yFH | yold |")
L("|---|---|---:|---:|---:|---:|")
for s in ("FH", "CTRL", "ORIG", "ALL", "FHm", "CTRLm", "B0"):
    a = R["top16_all"][s]
    L("| %s | all | %.4f | %+.4f | %.4f | %.4f |" % (s, a["sl"], a["ret"], a["yfh"], a["yold"]))
    for y in (2022, 2023, 2024, 2025):
        k = "%s|%d" % (s, y)
        if k in R["top16_year"]:
            a = R["top16_year"][k]
            L("| %s | %d | %.4f | %+.4f | %.4f | %.4f |" % (s, y, a["sl"], a["ret"], a["yfh"], a["yold"]))
L("")
L("### CI paired theo tick (bootstrap khoi, NREP 2000, seed 20260905, k=1)")
L("| cap | thuoc | khoi | delta | CI95 | tick | khoi n |")
L("|---|---|---|---:|---|---:|---:|")
for k, v in R["ci"].items():
    L("| %s | %s | %s | %+.5f | [%+.5f, %+.5f] | %d | %d |" % (tuple(k.split("|", 2)) + (v["mean"], v["ci"][0], v["ci"][1],
                                                                  v["n_ticks"], v["n_blocks"])))
L("")
L("GATE: %s" % json.dumps(R.get("gate", {}), default=float))
