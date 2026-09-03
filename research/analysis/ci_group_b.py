"""Nhom B (#7,#8,#9): CI cua HIEU o tang XEP HANG, block-bootstrap khoi 72h cua tick.
Phuong phap chot o docs/PREREG_CI.md section 3 (commit 2493eca).
Diem uoc luong tai lap y research/analysis/gate_vs_rank3.py."""
import logging
import numpy as np, pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/ci/ciB.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("ciB")
SEED, NREP = 20260903, 2000
H = 3600_000
BLOCKS_H = [72, 24, 168]

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev.parquet",
                    columns=["ts", "sym", "p15", "dyn_thr", "gate_dyn_ok",
                             "score_g015", "g1lite"])
P = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2.parquet")
R = pd.read_parquet("/home/ubuntu/ledger/path_labels.parquet",
                    columns=["ts", "sym", "g1_replay"])
M = C.merge(P, on=["ts", "sym"], how="inner").merge(R, on=["ts", "sym"], how="left")
M["gate_ok"] = M.gate_dyn_ok.astype(bool)
M = M.dropna(subset=["g1_replay"])
L.info("M rows=%d ticks=%d gate_MO_rows=%d gate_MO_ticks=%d",
       len(M), M.ts.nunique(), int(M.gate_ok.sum()), M[M.gate_ok].ts.nunique())
L.info("ts range %s .. %s", pd.to_datetime(M.ts.min(), unit="ms"),
       pd.to_datetime(M.ts.max(), unit="ms"))

# ---------- per-tick precompute ----------
OPEN = M[M.gate_ok]
CLOSED = M[~M.gate_ok]


def per_tick_ic(sub, col):
    """spearman(-col, g1_replay) trong tung tick, chi tick >= 10 dong (gate_vs_rank3:18-19)."""
    out = {}
    for ts, g in sub.groupby("ts"):
        if len(g) < 10:
            continue
        r = spearmanr(-g[col].values, g.g1_replay.values).correlation
        if not np.isnan(r):
            out[ts] = r
    return pd.Series(out, name=col)


ic_s1 = per_tick_ic(OPEN, "score")
ic_g0 = per_tick_ic(OPEN, "score_g015")
IC = pd.concat([ic_s1.rename("s1"), ic_g0.rename("g015")], axis=1).dropna()
L.info("\n[#7] rank-IC gate MO: n_tick=%d  S1=%+.4f  G015=%+.4f  hieu=%+.4f",
       len(IC), IC.s1.mean(), IC.g015.mean(), IC.s1.mean() - IC.g015.mean())


def topk(df, k):
    d = df.copy()
    d["rk"] = d.groupby("ts").score.rank(ascending=True, method="first")  # THAP=TOT
    return d[d.rk <= k]


def rnd8(df):
    return df.sample(frac=1.0, random_state=0).groupby("ts").head(8)


T8_open = topk(OPEN, 8)
R8_open = rnd8(OPEN)
T8_closed = topk(CLOSED, 8)
L.info("[#8/#9] gate MO top8=%.4f (n=%d) | random8=%.4f (n=%d) | gate DONG top8=%.4f (n=%d)",
       T8_open.g1_replay.mean(), len(T8_open), R8_open.g1_replay.mean(), len(R8_open),
       T8_closed.g1_replay.mean(), len(T8_closed))

TS_MIN = M.ts.min()


def blockagg(s_ts, vals, blen_h):
    """gop (sum, count) theo khoi blen_h gio."""
    bid = ((s_ts - TS_MIN) // (blen_h * H)).astype(np.int64)
    d = pd.DataFrame({"b": bid, "v": vals})
    g = d.groupby("b").v.agg(["sum", "count"])
    return g


def boot(pairs, blen_h, nblocks_all):
    """pairs: list of (sum,count) DataFrame indexed by block id, reindexed to full block list."""
    rng = np.random.default_rng(SEED)
    draw = rng.integers(0, len(nblocks_all), size=(NREP, len(nblocks_all)))
    out = []
    for g in pairs:
        gg = g.reindex(nblocks_all).fillna(0.0)
        S = gg["sum"].values
        Cn = gg["count"].values
        out.append(S[draw].sum(axis=1) / np.maximum(Cn[draw].sum(axis=1), 1e-9))
    return out


L.info("\n=== NHOM B — CI95 cua HIEU (percentile, %d rep, seed %d) ===", NREP, SEED)
L.info("%-4s %-34s %4s %9s %9s %9s %9s %8s %6s", "id", "so sanh", "Lh",
       "d_diem", "lo95", "hi95", "sd", "P(d>0)", "n_blk")
res = {}
for bh in BLOCKS_H:
    allb = np.arange(0, int((M.ts.max() - TS_MIN) // (bh * H)) + 1)
    # #7 IC (tick-weighted: count=1 moi tick)
    a7 = blockagg(pd.Series(IC.index.values), IC.s1.values, bh)
    b7 = blockagg(pd.Series(IC.index.values), IC.g015.values, bh)
    # #8 / #9 (row-weighted)
    a8 = blockagg(T8_open.ts.values, T8_open.g1_replay.values, bh)
    b8 = blockagg(R8_open.ts.values, R8_open.g1_replay.values, bh)
    b9 = blockagg(T8_closed.ts.values, T8_closed.g1_replay.values, bh)
    for pid, ga, gb, nm in [("B7", a7, b7, "rank-IC S1 - rank-IC G015 (gate MO)"),
                            ("B8", a8, b8, "g1_replay: gate MO top8 - random8"),
                            ("B9", a8, b9, "g1_replay: gate MO top8 - gate DONG top8")]:
        xa, xb = boot([ga, gb], bh, allb)
        d = xa - xb
        pt = (ga["sum"].sum() / ga["count"].sum()) - (gb["sum"].sum() / gb["count"].sum())
        lo, hi = np.percentile(d, [2.5, 97.5])
        res[(pid, bh)] = (pt, lo, hi, d.std(ddof=1), (d > 0).mean())
        L.info("%-4s %-34s %4d %+9.5f %+9.5f %+9.5f %9.5f %8.3f %6d",
               pid, nm, bh, pt, lo, hi, d.std(ddof=1), (d > 0).mean(), len(allb))

L.info("\n=== PHAN LOAI (PREREG_CI section 4) ===")
for pid, nm in [("B7", "S1 rank-IC > G015 rank-IC"),
                ("B8", "gate MO top8 > random8 (edge cua xep hang)"),
                ("B9", "gate MO top8 > gate DONG top8 (edge cua gate)")]:
    excl = [not (res[(pid, b)][1] <= 0 <= res[(pid, b)][2]) for b in BLOCKS_H]
    cls = ("SONG" if np.sign(res[(pid, 72)][0]) > 0 else "DAO CHIEU") if all(excl) \
        else "KHONG PHAN BIET DUOC"
    L.info("%-4s d=%+.5f loai_tru0=%s -> %-20s | %s", pid, res[(pid, 72)][0],
           "".join("Y" if e else "n" for e in excl), cls, nm)
