#!/usr/bin/env python3
"""HO4-P1: gom universe_excl.json 3 kernel quy 2026 (fetch file nho) -> no_funding_union.json; in so tom tat (khong so 2026)."""
import json, logging, sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ho4p1_exp_kernel as E
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
W = "/home/ubuntu/claude_master/1011/ho4p1/"
nof, tail, res = set(), {}, {}
for q in ("q1", "q2", "q3"):
    k = "ho4p1-x26-" + q
    E.fetch(k, r"(^|/)(universe_excl\.json|result\.json|MANIFEST\.json|ticker_raw_md5\.json)$")
    u = json.load(open(W + "kaggle/out/%s/out/universe_excl.json" % k))
    r = json.load(open(W + "kaggle/out/%s/result.json" % k))
    nof |= set(u["no_funding_vision"])
    for s, v in u["settle_tail"].items():
        tail.setdefault(s, v)
    res[q] = dict(ok=r.get("ok"), rc={t["name"]: t["rc"] for t in r["tasks"]}, secs={t["name"]: t["secs"] for t in r["tasks"]},
                  n_universe=u["n_universe"], no_funding=u["no_funding_vision"], n_tail=len(u["settle_tail"]),
                  manifest_n=r.get("manifest_n"), lifecycle=r["steps"].get("lifecycle"))
json.dump(dict(no_funding_vision=sorted(nof), settle_tail=tail, per_q=res), open(W + "no_funding_union.json", "w"), indent=1)
logging.info("NOFU %s", json.dumps(dict(no_funding=sorted(nof), n_tail=len(tail), per_q={q: {k: v for k, v in x.items() if k != "lifecycle"} for q, x in res.items()})))
