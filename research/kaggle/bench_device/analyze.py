"""BUOC 4 — so between-environment voi between-seed, ca per-tick lan aggregate."""
import itertools
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("analyze")
B = "/home/ubuntu/bench_device"
ENVS = {"oracle_cpu": f"{B}/out",
        "kaggle_cpu": f"{B}/dl/kcpu",
        "kaggle_gpu": f"{B}/dl/kgpu"}
SEEDS = ["42", "43", "44"]


def main():
    ic, meta, ed = {}, {}, {}
    for e, d in ENVS.items():
        ic[e] = pd.read_parquet(f"{d}/{e}_ic.parquet")
        ed[e] = pd.read_parquet(f"{d}/{e}_edge.parquet")
        meta[e] = json.load(open(f"{d}/{e}_meta.json"))
    idx = None
    for e in ENVS:
        idx = ic[e].index if idx is None else idx.intersection(ic[e].index)
    LOG.info("ticks chung %d", len(idx))
    for e in ENVS:
        ic[e] = ic[e].loc[idx]

    LOG.info("\n### HASH DU LIEU")
    for k in ["file_sha256", "X_sha256", "ts_sha256", "y_sha256", "g_sha256"]:
        v = {e: meta[e][k][:16] for e in ENVS}
        LOG.info("%-12s %s  MATCH=%s", k, v, len(set(v.values())) == 1)

    LOG.info("\n### ENV")
    for e in ENVS:
        m = meta[e]
        LOG.info("%-11s xgb=%s np=%s pd=%s py=%s arch=%s cpu=%s nthread=%s dev=%s %.0fs",
                 e, m["xgboost"], m["numpy"], m["pandas"], m["python"], m["machine"],
                 m["cpu_count"], m["booster_cfg"]["nthread"],
                 m["booster_cfg"]["device"], m["elapsed_s"])

    LOG.info("\n### CAY DAU TIEN (n_estimators=1, seed 42)")
    for e in ENVS:
        LOG.info("%-11s rows=%s sha=%s", e, meta[e]["tree1_rows"], meta[e]["tree1_sha"][:16])
    t = {e: pd.read_csv(f"{d}/{e}_tree1.csv") for e, d in ENVS.items()}
    base = t["oracle_cpu"]
    for e in ["kaggle_cpu", "kaggle_gpu"]:
        o = t[e]
        if len(o) != len(base):
            LOG.info("%s: SO NODE KHAC %d vs %d", e, len(o), len(base))
            continue
        for c in ["Feature", "Split", "Gain", "Cover", "Yes", "No"]:
            a, b2 = base[c], o[c]
            if a.dtype.kind in "fc":
                dif = int((~np.isclose(a.fillna(-9e9), b2.fillna(-9e9),
                                       rtol=0, atol=1e-12)).sum())
                mx = float(np.nanmax(np.abs(a - b2))) if dif else 0.0
                LOG.info("  %-11s col=%-7s n_khac=%d/%d max_abs=%.3g", e, c, dif, len(a), mx)
            else:
                dif = int((a != b2).sum())
                LOG.info("  %-11s col=%-7s n_khac=%d/%d", e, c, dif, len(a))

    LOG.info("\n### BETWEEN-SEED (trong CUNG mot moi truong)")
    bs = {}
    for e in ENVS:
        pw = [float(np.abs(ic[e][a] - ic[e][b]).mean())
              for a, b in itertools.combinations(SEEDS, 2)]
        agg_ic = [abs(ic[e][a].mean() - ic[e][b].mean())
                  for a, b in itertools.combinations(SEEDS, 2)]
        agg_ed = [abs(100 * (ed[e][a].mean() - ed[e][b].mean()))
                  for a, b in itertools.combinations(SEEDS, 2)]
        bs[e] = dict(pertick=pw, dic=agg_ic, ded=agg_ed)
        LOG.info("%-11s per-tick mean|dIC| %.5f (min %.5f max %.5f) | "
                 "|d mean rankIC| max %.5f | |d edge5| max %.3fpp",
                 e, np.mean(pw), np.min(pw), np.max(pw), max(agg_ic), max(agg_ed))
    allpt = [x for e in ENVS for x in bs[e]["pertick"]]
    allic = [x for e in ENVS for x in bs[e]["dic"]]
    alled = [x for e in ENVS for x in bs[e]["ded"]]
    LOG.info("BASELINE seed (gop 3 env, 9 cap): per-tick %.5f (max %.5f) | "
             "|d meanIC| %.5f (max %.5f) | |d edge5| %.3fpp (max %.3fpp)",
             np.mean(allpt), np.max(allpt), np.mean(allic), np.max(allic),
             np.mean(alled), np.max(alled))

    LOG.info("\n### BETWEEN-ENV (CUNG seed)")
    rows = []
    for e1, e2 in itertools.combinations(list(ENVS), 2):
        pw, di, de = [], [], []
        for s in SEEDS:
            pw.append(float(np.abs(ic[e1][s] - ic[e2][s]).mean()))
            di.append(abs(ic[e1][s].mean() - ic[e2][s].mean()))
            de.append(abs(100 * (ed[e1][s].mean() - ed[e2][s].mean())))
            LOG.info("  %-11s vs %-11s seed %s | per-tick %.5f | d meanIC %+.5f | d edge5 %+.3fpp",
                     e1, e2, s, pw[-1], ic[e1][s].mean() - ic[e2][s].mean(),
                     100 * (ed[e1][s].mean() - ed[e2][s].mean()))
        rows.append((e1, e2, np.mean(pw), np.max(pw), np.mean(di), np.max(di),
                     np.mean(de), np.max(de)))
    LOG.info("\n| cap moi truong | per-tick tb | per-tick max | d meanIC tb | d meanIC max | d edge5 tb | d edge5 max |")
    LOG.info("|---|---|---|---|---|---|---|")
    for r in rows:
        LOG.info("| %s vs %s | %.5f | %.5f | %.5f | %.5f | %.3fpp | %.3fpp |", *r)
    LOG.info("| **BASELINE between-seed** | %.5f | %.5f | %.5f | %.5f | %.3fpp | %.3fpp |",
             np.mean(allpt), np.max(allpt), np.mean(allic), np.max(allic),
             np.mean(alled), np.max(alled))

    LOG.info("\n### TY LE between-env / between-seed (dung tb)")
    for r in rows:
        LOG.info("%s vs %s: per-tick x%.2f | meanIC x%.2f | edge5 x%.2f",
                 r[0], r[1], r[2] / np.mean(allpt), r[4] / np.mean(allic),
                 r[6] / np.mean(alled))

    p1 = f"{B}/out/oracle_cpu_nj1_ic.parquet"
    if os.path.exists(p1):
        i1 = pd.read_parquet(p1)
        e1 = pd.read_parquet(f"{B}/out/oracle_cpu_nj1_edge.parquet")
        m1 = json.load(open(f"{B}/out/oracle_cpu_nj1_meta.json"))
        j = i1.index.intersection(ic["oracle_cpu"].index)
        a = ic["oracle_cpu"].loc[j, "42"]
        b = i1.loc[j, "42"]
        LOG.info("\n### NTHREAD (oracle_cpu seed 42: n_jobs=4 vs n_jobs=1)")
        LOG.info("tree1 sha nj1=%s nj4=%s MATCH=%s", m1["tree1_sha"][:16],
                 meta["oracle_cpu"]["tree1_sha"][:16],
                 m1["tree1_sha"] == meta["oracle_cpu"]["tree1_sha"])
        LOG.info("per-tick mean|dIC| %.5f | d meanIC %+.5f | d edge5 %+.3fpp",
                 float(np.abs(a - b).mean()), a.mean() - b.mean(),
                 100 * (ed["oracle_cpu"]["42"].mean() - e1["42"].mean()))
        LOG.info("=> so voi baseline seed per-tick %.5f: x%.2f",
                 np.mean(allpt), float(np.abs(a - b).mean()) / np.mean(allpt))
    else:
        LOG.info("\n### NTHREAD: chua co %s", p1)


if __name__ == "__main__":
    main()
