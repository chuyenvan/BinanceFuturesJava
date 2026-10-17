#!/usr/bin/env python3
"""GATE_VZ cham (PREREG_GATE_VZ.md ee97237b muc 6). MTM moi run (ca baseline) tinh lai bang gvz_mtm (nguon Vision).
Usage: python3 gvz_score.py ARM [--seeds 42,7,...] ; ARM = VA | VB"""
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  (patch R truoc khi import khac)
import gvz_sim as S  # noqa: E402

R, G, GA = MT.R, S.G, S.GA
log = logging.getLogger("gvzsc")
D = "/home/ubuntu/claude_master/gvz"
SEEDS8 = [42, 7, 13, 21, 99, 123, 777, 2024]
TQ = {7: 2.841, 15: 2.490}            # t_{0.9875; df}
MTMF = D + "/mtm.json"


GQSF = {7, 13, 21, 99, 123, 777, 2024}


def base_tag(seed):
    return "gqsf-s%d" % seed if seed in GQSF else S.tag("B_S%d" % seed)


def metrics(t, mtm):
    daily = R.load_daily(t)
    eq = daily["equity"]
    legs = R.load_legs(t)
    cl = legs[(legs["te"] >= "2022-01-01") & (legs["te"] < "2025-01-01")]
    m = dict(cagr_dev=G.cagr_from(eq, "2021-12-31", "2024-12-31"), cagr22=G.cagr_from(eq, "2021-12-31", "2025-12-30"),
             yret=G.year_ret(eq), dd_dev=mtm["dd_dev"], dd_total=mtm["dd_total"], dd_win=mtm["dd_win"],
             uw_dev=mtm["uw_dev_days"], n_dev_per_year=len(cl) / 3.0, gate_min=GA.gate_minutes(t)["per_year"],
             missing=mtm["missing"])
    m["calmar_dev"] = m["cagr_dev"] / abs(m["dd_dev"]) if m["dd_dev"] else float("nan")
    return m


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
    arm = sys.argv[1]
    seeds = SEEDS8
    if "--seeds" in sys.argv:
        seeds = [int(x) for x in sys.argv[sys.argv.index("--seeds") + 1].split(",")]
    runs = {s: "%s_S%d" % (arm, s) for s in seeds}
    bruns = ["B_S%d" % s for s in seeds if s not in GQSF]
    par = S.parity(list(runs.values()) + bruns)
    void = [r for r in list(runs.values()) + bruns if not par.get(r, {}).get("ok")]
    assert not void, ("VOID -> chay lai, khong cham", void)
    tags = sorted({S.tag(runs[s]) for s in seeds} | {base_tag(s) for s in seeds})
    cache = json.load(open(MTMF)) if os.path.exists(MTMF) else {}
    need = [t for t in tags if t not in cache or cache[t].get("md5") != R.md5_of(t)]
    if need:
        new = MT.run(need)
        for t in need:
            new[t]["md5"] = R.md5_of(t)
            cache[t] = new[t]
        json.dump(cache, open(MTMF, "w"), indent=1)
    M = {t: metrics(t, cache[t]["legacy"]) for t in tags}
    rows, d = {}, {k: [] for k in ("cagr_dev", "calmar_dev", "dd_dev", "y2022", "y2023", "y2024", "y2025", "cagr22")}
    for s in seeds:
        a, b = M[S.tag(runs[s])], M[base_tag(s)]
        r = {k: a[k] - b[k] for k in ("cagr_dev", "calmar_dev", "dd_dev", "cagr22")}
        for y in (2022, 2023, 2024, 2025):
            r["y%d" % y] = a["yret"][y] - b["yret"][y]
        for k in d:
            d[k].append(r[k])
        rows[s] = dict(delta=r, arm=a, base=b)
        log.info("ROW S%-4d CAGRdev %6.2f->%6.2f (%+5.2f) Cal %5.3f->%5.3f DDdev %6.2f->%6.2f y22 %+5.2f y23 %+5.2f "
                 "y24 %+5.2f y25 %+5.2f n/y %4.0f->%4.0f", s, b["cagr_dev"], a["cagr_dev"], r["cagr_dev"], b["calmar_dev"],
                 a["calmar_dev"], b["dd_dev"], a["dd_dev"], r["y2022"], r["y2023"], r["y2024"], r["y2025"],
                 b["n_dev_per_year"], a["n_dev_per_year"])
    n = len(seeds)
    x = np.array(d["cagr_dev"])
    tq = TQ[n - 1]
    hw = tq * x.std(ddof=1) / math.sqrt(n)
    worst_dd = max(abs(min(M[S.tag(runs[s])]["dd_total"], M[S.tag(runs[s])]["dd_dev"])) for s in seeds)
    ym = {y: float(np.mean(d["y%d" % y])) for y in (2022, 2023, 2024)}
    need_pos = 12 if n == 16 else 6
    rule = dict(
        C1=dict(mean=float(x.mean()), ci=[float(x.mean() - hw), float(x.mean() + hw)], t=tq,
                ok=bool(x.mean() > 0 and x.mean() - hw > 0)),
        C2=dict(n_pos=int((x > 0).sum()), need=need_pos, ok=bool((x > 0).sum() >= need_pos)),
        C3=dict(mean_dcal=float(np.mean(d["calmar_dev"])), mean_ddd=float(np.mean(d["dd_dev"])), worst_dd=worst_dd,
                ok=bool(np.mean(d["calmar_dev"]) >= 0 and np.mean(d["dd_dev"]) >= -2.0 and worst_dd <= 40.0)),
        C4=dict(mean_year=ym, ok=bool(sum(v > 0 for v in ym.values()) >= 2 and min(ym.values()) >= -3.0)),
        C5=dict(mean_y2025=float(np.mean(d["y2025"])), ok=bool(np.mean(d["y2025"]) >= -1.0)))
    rule["GO"] = all(rule[c]["ok"] for c in ("C1", "C2", "C3", "C4", "C5"))
    rule["EXT_6_3"] = bool(not rule["C1"]["ok"] and n == 8 and x.mean() >= 1.5 and (x > 0).sum() >= 5
                           and x.mean() - hw <= 0)
    log.info("RULE %s %s", arm, json.dumps(rule))
    out = dict(prereg="docs/prereg/PREREG_GATE_VZ.md", prereg_commit="ee97237b", arm=arm, seeds=seeds, rule=rule,
               rows=rows, parity={k: par[k] for k in par if k in runs.values() or k in bruns})
    json.dump(out, open(D + "/score_%s_n%d.json" % (arm, n), "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
