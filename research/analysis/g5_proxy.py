"""G5 PROXY — do nhanh 8 ung vien nhan tren pool OOS DEV 48 thang, KHONG chay sim.
Xem docs/PREREG_G5.md muc 4. Output: /home/ubuntu/g5/proxy_*.csv + log.

(a) phan phoi p toan pool + per-tick
(b) rank-IC per-tick vs g1lite + edge5, CI block-bootstrap 72h x1.21 (ghep cap vs net015_4h)
(c) admission: raw (dyn_thr tu p tho) va quantile-map (p doi sang multiset x26 cua tick)
"""
import glob, json, logging, os, sys
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("g5proxy")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_cfg

POOLDIR = "/home/ubuntu/g5/pool"
OUT = "/home/ubuntu/g5"
H72 = 72 * 3600_000
FAC = 1.21
NREP = 2000
SEED = 20260906
BASE = "net015_4h"
MINTICK = 10


def load_pool():
    D = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet",
                        columns=["ts", "sym", "p_g015", "p15", "g1lite"])
    D = D[D.p_g015.notna()].reset_index(drop=True)
    D["ts"] = D.ts.astype(np.int64)
    D["sym"] = D.sym.astype(np.int32)
    LOG.info("POOL rows=%d ticks=%d", len(D), D.ts.nunique())
    return D


def per_tick_stats(df, col):
    g = df.groupby("ts")[col]
    return dict(tick_p10=float(g.quantile(.10).mean()), tick_p50=float(g.median().mean()),
                tick_p90=float(g.quantile(.90).mean()), tick_mean=float(g.mean().mean()),
                tick_sd=float(g.std().mean()))


def ic_edge_per_tick(df, pcol):
    """rank-IC (spearman trong tick giua p va g1lite) + edge5 (top-5 theo p giam dan)."""
    ics, ed, tss = [], [], []
    for ts, g in df.groupby("ts", sort=True):
        if len(g) < MINTICK:
            continue
        y = g.g1lite.to_numpy()
        x = g[pcol].to_numpy()
        if np.all(x == x[0]) or np.all(y == y[0]):
            continue
        r = spearmanr(x, y).correlation
        if r != r:
            continue
        k = min(5, len(g))
        top = np.argsort(-x, kind="stable")[:k]
        ics.append(r)
        ed.append(float(y[top].mean() - y.mean()))
        tss.append(ts)
    return np.array(tss), np.array(ics), np.array(ed)


def block_ci(ts, d, nrep=NREP, seed=SEED):
    """block-bootstrap khoi 72h tren hieu GHEP CAP d (cung tap tick)."""
    if len(d) == 0:
        return (np.nan, np.nan, np.nan)
    b = (ts // H72).astype(np.int64)
    ub, inv = np.unique(b, return_inverse=True)
    idx_by = [np.flatnonzero(inv == i) for i in range(len(ub))]
    rng = np.random.default_rng(seed)
    means = np.empty(nrep)
    for r in range(nrep):
        pick = rng.integers(0, len(ub), len(ub))
        means[r] = np.concatenate([idx_by[p] for p in pick]).size and \
            d[np.concatenate([idx_by[p] for p in pick])].mean()
    sd = float(means.std(ddof=1))
    m = float(d.mean())
    return m, m - 1.96 * FAC * sd, m + 1.96 * FAC * sd


def qmap(df, pcol):
    """Doi p cua ung vien sang MULTISET p_g015 cua chinh tick do, theo thu hang cua ung vien.
    Y HET c4_build_map.py: r_score = rank(-p_cand, first); p_sorted = rank(p_x26, desc, first)."""
    s = df[["ts", pcol, "p_g015"]].copy()
    s["r"] = s.groupby("ts")[pcol].rank(method="first", ascending=False)
    s["ps"] = s.groupby("ts").p_g015.rank(method="first", ascending=False)
    key = s.set_index(["ts", "ps"]).p_g015
    return key.reindex(list(zip(s.ts, s.r))).to_numpy()


def admission(df, pvals):
    thr = gate_cfg.dyn_thr(1.0 - np.asarray(pvals, dtype="float64"))
    ok = df.p15.to_numpy() >= thr
    per = pd.DataFrame({"ts": df.ts.to_numpy(), "ok": ok}).groupby("ts").ok.sum()
    return int(ok.sum()), float(ok.mean()), int(np.minimum(per.to_numpy(), 8).sum())


def main():
    gate_cfg.describe()
    D = load_pool()
    tags = [os.path.basename(p)[5:-8] for p in sorted(glob.glob(POOLDIR + "/pool_*.parquet"))]
    LOG.info("TAGS: %s", tags)
    rows, ic_store = [], {}
    for t in tags:
        P = pd.read_parquet(os.path.join(POOLDIR, "pool_%s.parquet" % t))
        P = P.rename(columns={"p": "p_c"})[["ts", "sym", "p_c"]]
        M = D.merge(P, on=["ts", "sym"], how="inner")
        cov = len(M) / len(D)
        r = {"tag": t, "n_rows": len(M), "cover": round(cov, 4), "n_ticks": M.ts.nunique()}
        r.update({"p10": float(M.p_c.quantile(.10)), "p50": float(M.p_c.median()),
                  "p90": float(M.p_c.quantile(.90)), "mean": float(M.p_c.mean()),
                  "sd": float(M.p_c.std())})
        r.update(per_tick_stats(M, "p_c"))
        ts, ic, ed = ic_edge_per_tick(M, "p_c")
        ic_store[t] = (ts, ic, ed)
        r["rankIC"] = float(ic.mean())
        r["edge5"] = float(ed.mean())
        r["n_tick_ic"] = len(ic)
        n_raw, sh_raw, adm_raw = admission(M, M.p_c.to_numpy())
        M["p_map"] = qmap(M, "p_c")
        n_map, sh_map, adm_map = admission(M, M.p_map.to_numpy())
        n_par, sh_par, adm_par = admission(M, M.p_g015.to_numpy())
        r.update({"pass_raw": n_raw, "pass_raw_share": round(sh_raw, 5),
                  "adm8_raw": adm_raw, "pass_map": n_map, "adm8_map": adm_map,
                  "pass_parity": n_par, "adm8_parity": adm_par,
                  "raw_vs_parity_x": round(n_raw / max(n_par, 1), 3),
                  "map_eq_parity": bool(n_map == n_par and adm_map == adm_par)})
        r["map_p10"] = float(M.p_map.quantile(.10))
        r["map_p50"] = float(M.p_map.median())
        r["map_p90"] = float(M.p_map.quantile(.90))
        rows.append(r)
        LOG.info("%-14s rows=%8d cov=%.3f p10/50/90=%.4f/%.4f/%.4f IC=%+.5f edge5=%+.5f "
                 "pass_raw=%d (x%.2f) pass_map=%d parity=%d map==parity:%s",
                 t, len(M), cov, r["p10"], r["p50"], r["p90"], r["rankIC"], r["edge5"],
                 n_raw, r["raw_vs_parity_x"], n_map, n_par, r["map_eq_parity"])
        del M, P
    T = pd.DataFrame(rows)
    T.to_csv(OUT + "/proxy_table.csv", index=False)
    # CI ghep cap vs BASE
    if BASE in ic_store:
        tb, icb, edb = ic_store[BASE]
        crows = []
        for t in tags:
            if t == BASE:
                continue
            ts, ic, ed = ic_store[t]
            common, ia, ib = np.intersect1d(ts, tb, return_indices=True)
            for nm, a, b in (("rankIC", ic[ia], icb[ib]), ("edge5", ed[ia], edb[ib])):
                d = a - b
                m, lo, hi = block_ci(common, d)
                crows.append({"tag": t, "metric": nm, "n_tick": len(common), "d": m,
                              "lo": lo, "hi": hi, "excl0": bool(lo > 0 or hi < 0)})
                LOG.info("CI %-14s %-7s d=%+.5f [%+.5f,%+.5f] ngoai CI: %s",
                         t, nm, m, lo, hi, crows[-1]["excl0"])
        C = pd.DataFrame(crows)
        C.to_csv(OUT + "/proxy_ci.csv", index=False)
    pd.set_option("display.width", 300)
    LOG.info("\n%s", T.round(5).to_string(index=False))
    LOG.info("G5_PROXY_DONE")


if __name__ == "__main__":
    main()
