#!/usr/bin/env python3
"""LIQ_PROXY score — IC, partial IC, bootstrap by episode, prereg criteria.
Prereg docs/prereg/PREREG_LIQ_PROXY.md (a468b743).
"""
import json
import os

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
PROX = ["L1", "L2", "L3", "LM"]
OUTS = ["arm168", "pnl", "MFE24", "MAE24"]
CTRL = ["pred15m", "oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy15"]
NREP = 2000
SEED = 20261023


def partial_spearman(x, y, C):
    m = np.isfinite(x) & np.isfinite(y) & np.all(np.isfinite(C), axis=1)
    x, y, C = x[m], y[m], C[m]
    if len(x) < 30:
        return np.nan, len(x)
    rx, ry = rankdata(x), rankdata(y)
    R = np.column_stack([rankdata(C[:, j]) for j in range(C.shape[1])] + [np.ones(len(x))])
    bx = np.linalg.lstsq(R, rx, rcond=None)[0]
    by = np.linalg.lstsq(R, ry, rcond=None)[0]
    ex, ey = rx - R @ bx, ry - R @ by
    if np.std(ex) == 0 or np.std(ey) == 0:
        return np.nan, len(x)
    return float(np.corrcoef(ex, ey)[0, 1]), len(x)


def ic_table(d, kind="cluster"):
    d = d[d.kind == kind].copy()
    C = d[CTRL].to_numpy(float)
    out = {}
    for p in PROX:
        for o in OUTS:
            sub = d[[p, o]].dropna()
            ic = spearmanr(sub[p], sub[o]).correlation if len(sub) >= 30 else np.nan
            pic, n = partial_spearman(d[p].to_numpy(float), d[o].to_numpy(float), C)
            out["%s|%s" % (p, o)] = dict(ic=None if not np.isfinite(ic) else round(float(ic), 4),
                                         pic=None if not np.isfinite(pic) else round(float(pic), 4),
                                         n=int(len(sub)), n_partial=int(n))
    return out


def boot_ci(d, p, o, rng, nrep=NREP):
    d = d[d.kind == "cluster"][[p, o, "episode"]].dropna()
    eps = d.episode.unique()
    idx = {e: np.where(d.episode.to_numpy() == e)[0] for e in eps}
    vals = []
    for _ in range(nrep):
        pick = rng.choice(eps, size=len(eps), replace=True)
        ii = np.concatenate([idx[e] for e in pick])
        x, y = d[p].to_numpy()[ii], d[o].to_numpy()[ii]
        if np.std(x) == 0 or np.std(y) == 0:
            continue
        vals.append(spearmanr(x, y).correlation)
    vals = np.array([v for v in vals if np.isfinite(v)])
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)), len(vals)) if len(vals) else (np.nan, np.nan, 0)


def size_rule(d, p, sign):
    t = d[(d.kind == "cluster") & d[p].notna() & d.pnl.notna()].copy()
    qlo, qhi = t[p].quantile([0.2, 0.8])
    if sign > 0:
        w = np.where(t[p] >= qhi, 1.5, np.where(t[p] <= qlo, 0.5, 1.0))
    else:
        w = np.where(t[p] <= qlo, 1.5, np.where(t[p] >= qhi, 0.5, 1.0))
    return float(np.sum((w - 1.0) * t.pnl.to_numpy()) / 8.0), int((w != 1).sum())


def main():
    d = pd.read_csv(os.path.join(HERE, "samples_outcome.csv"))
    d["anchor"] = pd.to_datetime(d["anchor"])
    rng = np.random.default_rng(SEED)
    res = {"prereg_sha256": "e304fa445af0707f2c0e95068a7552989b48e7aadbd865f1cd28bfb6583e85b2",
           "n": {}, "ic": {}, "boot": {}, "rule": {}}
    for kind in ("cluster", "leg"):
        res["n"][kind] = d[d.kind == kind].groupby("period").size().to_dict()

    dd, dtest = d[d.period == "disc"], d[d.period == "test"]
    ic_d, ic_t = ic_table(dd), ic_table(dtest)
    res["ic"] = {"disc": ic_d, "test": ic_t}

    for p in PROX:
        for o in ("arm168", "pnl"):
            lo, hi, nrep = boot_ci(dtest, p, o, rng)
            res["boot"]["%s|%s" % (p, o)] = dict(lo=None if not np.isfinite(lo) else round(lo, 4),
                                                 hi=None if not np.isfinite(hi) else round(hi, 4), nrep=nrep)

    # criteria
    verdict = {}
    for p in PROX:
        best = None
        for o in ("arm168", "pnl"):
            a = ic_d.get("%s|%s" % (p, o), {}).get("ic")
            b = ic_t.get("%s|%s" % (p, o), {}).get("ic")
            pa = ic_t.get("%s|%s" % (p, o), {}).get("pic")
            if a is None or b is None or pa is None:
                continue
            c1 = (abs(a) >= 0.10 and abs(b) >= 0.10 and np.sign(a) == np.sign(b))
            lo = res["boot"].get("%s|%s" % (p, o), {}).get("lo")
            hi = res["boot"].get("%s|%s" % (p, o), {}).get("hi")
            c2 = (lo is not None and hi is not None and (lo > 0 or hi < 0))
            c3 = (abs(pa) >= 0.07 and np.sign(pa) == np.sign(b))
            dr, nw = size_rule(dtest, p, np.sign(a))
            c4 = dr >= 5000.0
            rec = dict(outcome=o, ic_disc=a, ic_test=b, pic_test=pa, ci=[lo, hi],
                       c1=bool(c1), c2=bool(c2), c3=bool(c3), direct=round(dr, 1), n_w=nw, c4=bool(c4),
                       pass_all=bool(c1 and c2 and c3 and c4))
            if best is None or rec["pass_all"] or (abs(b) > abs(best["ic_test"])):
                best = rec
        verdict[p] = best
    res["verdict"] = verdict
    res["pass_any"] = any(v and v["pass_all"] for v in verdict.values())

    with open(os.path.join(HERE, "liq_proxy_ic.json"), "w") as f:
        json.dump(res, f, indent=1, default=str)

    # markdown
    def tab(t):
        lines = ["| proxy | outcome | IC | IC tăng thêm | n | n partial |", "|---|---|---|---|---|---|"]
        for p in PROX:
            for o in OUTS:
                r = t.get("%s|%s" % (p, o), {})
                lines.append("| %s | %s | %s | %s | %s | %s |" % (
                    p, o, r.get("ic"), r.get("pic"), r.get("n"), r.get("n_partial")))
        return "\n".join(lines)
    with open(os.path.join(HERE, "liq_proxy_tables.md"), "w") as f:
        f.write("## Discovery 2022-2023 (clusters)\n\n" + tab(ic_d) + "\n\n")
        f.write("## Test 2024-2025 (clusters)\n\n" + tab(ic_t) + "\n\n")
        f.write("## Bootstrap 95% (test, clusters, by episode)\n\n| proxy | outcome | lo | hi | nrep |\n|---|---|---|---|---|\n")
        for k, v in res["boot"].items():
            f.write("| %s | %s | %s | %s | %s |\n" % (k.split("|")[0], k.split("|")[1], v["lo"], v["hi"], v["nrep"]))
        f.write("\n## Criteria\n\n| proxy | outcome | IC disc | IC test | pIC test | CI test | C1 | C2 | C3 | direct/seed | C4 | PASS |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|---|\n")
        for p, v in verdict.items():
            if v:
                f.write("| %s | %s | %s | %s | %s | [%s, %s] | %s | %s | %s | %s | %s | %s |\n" % (
                    p, v["outcome"], v["ic_disc"], v["ic_test"], v["pic_test"], v["ci"][0], v["ci"][1],
                    v["c1"], v["c2"], v["c3"], v["direct"], v["c4"], v["pass_all"]))
        f.write("\nPASS ANY: %s\n" % res["pass_any"])
    print(json.dumps(res["verdict"], indent=1, default=str))
    print("PASS ANY", res["pass_any"])


if __name__ == "__main__":
    main()
