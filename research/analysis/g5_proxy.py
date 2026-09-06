"""G5 PROXY — do nhanh cac ung vien nhan tren pool OOS DEV 48 thang, KHONG chay sim.
Xem docs/PREREG_G5.md muc 4. Output: /home/ubuntu/g5/proxy_table.csv, proxy_ci.csv.

(a) phan phoi p toan pool + per-tick
(b) rank-IC per-tick vs g1lite + edge5; CI block-bootstrap khoi 72h x1.21, GHEP CAP vs net015_4h
(c) admission: raw (dyn_thr tu p tho) vs quantile-map (p -> multiset x26 cua tick)
"""
import glob, logging, os, sys
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("g5proxy")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_cfg

POOLDIR = "/home/ubuntu/g5/pool"
OUT = "/home/ubuntu/g5"
H72 = 72 * 3600_000
FAC, NREP, SEED, MINTICK, TOPK = 1.21, 2000, 20260906, 10, 8
BASE = "net015_4h"


def load_pool():
    D = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet",
                        columns=["ts", "sym", "p_g015", "p15", "g1lite"])
    D = D[D.p_g015.notna() & D.g1lite.notna()].reset_index(drop=True)
    D["ts"] = D.ts.astype(np.int64)
    D["sym"] = D.sym.astype(np.int32)
    D["nt"] = D.groupby("ts").sym.transform("size")
    LOG.info("POOL rows=%d ticks=%d (tick >=%d dong: %d)", len(D), D.ts.nunique(), MINTICK,
             D[D.nt >= MINTICK].ts.nunique())
    return D


def per_tick_stats(df, col):
    g = df.groupby("ts")[col]
    return dict(tick_p10=float(g.quantile(.10).mean()), tick_p50=float(g.median().mean()),
                tick_p90=float(g.quantile(.90).mean()), tick_sd=float(g.std().mean()))


def ic_edge(df, pcol):
    """rank-IC trong tick (spearman) + edge5, VECTOR HOA theo groupby (khong vong lap tick)."""
    d = df[df.nt >= MINTICK]
    rx = d.groupby("ts")[pcol].rank()
    ry = d.groupby("ts").g1lite.rank()
    t = pd.DataFrame({"ts": d.ts.to_numpy(), "x": rx.to_numpy(), "y": ry.to_numpy(),
                      "g": d.g1lite.to_numpy(), "p": d[pcol].to_numpy()})
    g = t.groupby("ts")
    n = g.x.size()
    mx, my = g.x.mean(), g.y.mean()
    sx, sy = g.x.std(ddof=0), g.y.std(ddof=0)
    cxy = g.apply(lambda z: float(np.mean(z.x.to_numpy() * z.y.to_numpy())), include_groups=False)
    ic = (cxy - mx * my) / (sx * sy)
    ic = ic.replace([np.inf, -np.inf], np.nan).dropna()
    t["rk"] = t.groupby("ts").p.rank(method="first", ascending=False)
    top = t[t.rk <= 5].groupby("ts").g.mean()
    allm = g.g.mean()
    ed = (top - allm).dropna()
    j = ic.index.intersection(ed.index)
    return j.to_numpy(), ic.loc[j].to_numpy(), ed.loc[j].to_numpy()


def block_ci(ts, d, nrep=NREP, seed=SEED):
    if len(d) == 0:
        return float("nan"), float("nan"), float("nan"), 0
    b = (np.asarray(ts) // H72).astype(np.int64)
    ub, inv = np.unique(b, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    starts = np.searchsorted(inv[order], np.arange(len(ub)))
    ends = np.append(starts[1:], len(order))
    rng = np.random.default_rng(seed)
    means = np.empty(nrep)
    for r in range(nrep):
        pick = rng.integers(0, len(ub), len(ub))
        idx = np.concatenate([order[starts[p]:ends[p]] for p in pick])
        means[r] = d[idx].mean()
    sd = float(means.std(ddof=1))
    m = float(np.mean(d))
    return m, m - 1.96 * FAC * sd, m + 1.96 * FAC * sd, len(ub)


def qmap(df, pcol):
    """Y HET c4_build_map.py: r = rank(p_cand desc, first); ps = rank(p_x26 desc, first);
    p_new = gia tri p_x26 co ps == r  => giu NGUYEN multiset x26 trong tick."""
    s = df[["ts", pcol, "p_g015"]].copy()
    s["r"] = s.groupby("ts")[pcol].rank(method="first", ascending=False)
    s["ps"] = s.groupby("ts").p_g015.rank(method="first", ascending=False)
    key = s.set_index(["ts", "ps"]).p_g015
    return key.reindex(pd.MultiIndex.from_arrays([s.ts, s.r])).to_numpy()


def admission(df, pvals):
    thr = gate_cfg.dyn_thr(1.0 - np.asarray(pvals, dtype="float64"))
    ok = df.p15.to_numpy() >= thr
    per = pd.Series(ok).groupby(df.ts.to_numpy()).sum()
    return int(ok.sum()), int(np.minimum(per.to_numpy(), TOPK).sum())


def main():
    gate_cfg.describe()
    D = load_pool()
    tags = [os.path.basename(p)[5:-8] for p in sorted(glob.glob(POOLDIR + "/pool_*.parquet"))]
    LOG.info("TAGS: %s", tags)
    rows, store = [], {}
    n_par, adm_par = admission(D, D.p_g015.to_numpy())
    LOG.info("PARITY (x26 raw): pass=%d adm_top8=%d", n_par, adm_par)
    for t in tags:
        P = pd.read_parquet(os.path.join(POOLDIR, "pool_%s.parquet" % t))
        P = P.rename(columns={"p": "p_c"})[["ts", "sym", "p_c"]]
        M = D.merge(P, on=["ts", "sym"], how="inner")
        r = {"tag": t, "n_rows": len(M), "cover": round(len(M) / len(D), 4)}
        r.update({"p10": float(M.p_c.quantile(.10)), "p50": float(M.p_c.median()),
                  "p90": float(M.p_c.quantile(.90)), "mean": float(M.p_c.mean()),
                  "sd": float(M.p_c.std())})
        r.update(per_tick_stats(M, "p_c"))
        ts, ic, ed = ic_edge(M, "p_c")
        store[t] = (ts, ic, ed)
        r["rankIC"], r["edge5"], r["n_tick"] = float(ic.mean()), float(ed.mean()), len(ic)
        nr, ar = admission(M, M.p_c.to_numpy())
        M["p_map"] = qmap(M, "p_c")
        nm, am = admission(M, M.p_map.to_numpy())
        r.update({"pass_raw": nr, "adm8_raw": ar, "pass_map": nm, "adm8_map": am,
                  "pass_parity": n_par, "adm8_parity": adm_par,
                  "raw_vs_par_x": round(nr / max(n_par, 1), 3),
                  "map_eq_parity": bool(nm == n_par and am == adm_par),
                  "map_p10": float(M.p_map.quantile(.10)),
                  "map_p50": float(M.p_map.median()),
                  "map_p90": float(M.p_map.quantile(.90))})
        rows.append(r)
        LOG.info("%-13s p10/50/90=%.4f/%.4f/%.4f sd=%.4f | IC=%+.5f edge5=%+.5f (tick %d) | "
                 "pass_raw=%d (x%.2f) adm8_raw=%d | pass_map=%d adm8_map=%d | map==parity: %s",
                 t, r["p10"], r["p50"], r["p90"], r["sd"], r["rankIC"], r["edge5"], r["n_tick"],
                 nr, r["raw_vs_par_x"], ar, nm, am, r["map_eq_parity"])
        del M, P
    T = pd.DataFrame(rows)
    T.to_csv(OUT + "/proxy_table.csv", index=False)
    if BASE in store:
        tb, icb, edb = store[BASE]
        crows = []
        for t in tags:
            if t == BASE:
                continue
            ts, ic, ed = store[t]
            common, ia, ib = np.intersect1d(ts, tb, return_indices=True)
            for nm2, a, b in (("rankIC", ic[ia], icb[ib]), ("edge5", ed[ia], edb[ib])):
                m, lo, hi, nb = block_ci(common, a - b)
                crows.append({"tag": t, "metric": nm2, "n_tick": len(common), "n_block": nb,
                              "d": m, "lo": lo, "hi": hi, "excl0": bool(lo > 0 or hi < 0)})
                LOG.info("CI %-13s %-7s d=%+.5f [%+.5f,%+.5f] khoi=%d ngoai CI: %s",
                         t, nm2, m, lo, hi, nb, crows[-1]["excl0"])
        pd.DataFrame(crows).to_csv(OUT + "/proxy_ci.csv", index=False)
    pd.set_option("display.width", 320)
    LOG.info("\n%s", T.round(5).to_string(index=False))
    LOG.info("G5_PROXY_DONE")


if __name__ == "__main__":
    main()
