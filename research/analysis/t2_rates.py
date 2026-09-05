"""T2 — rate PRIMARY + phan bo status + CI block-bootstrap 72h x1.21.

Usage: t2_rates.py <TAG_A> <TAG_B> [<TAG...>]
Chan dau tien duoc dung lam GOC khi tinh CI cua hieu (A - B) cho moi cap (A, B_i>0).
"""
import logging, sys, warnings
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
LOG = logging.getLogger("t2")
warnings.simplefilter("ignore")
B = "/home/ubuntu/java/devrun"
RNG = np.random.default_rng(20260905)
NBOOT = 4000
BLOCK_MS = 72 * 3600 * 1000
WIDEN = 1.21


def load(tag):
    df = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", index_col=False)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df["profit"] = pd.to_numeric(df["profit"], errors="coerce")
    df["margin"] = pd.to_numeric(df["margin"], errors="coerce")
    df["ts"] = pd.to_datetime(df["start"], format="%Y%m%d %H:%M", errors="coerce")
    df["blk"] = (df.ts.astype("int64") // 10**6) // BLOCK_MS
    return df.dropna(subset=["profit", "ts"])


def rates(df):
    n = len(df)
    sm = df.status == "STOP_MARKET_DONE"
    sl = df.status == "STOP_LOSS_DONE"
    return {
        "n": n,
        "TSloss%": 100.0 * sl.sum() / n,
        "win%": 100.0 * (df.profit > 0).sum() / n,
        "mP|SM": df.profit[sm].mean() if sm.any() else float("nan"),
        "mP|SL": df.profit[sl].mean() if sl.any() else float("nan"),
        "mP": df.profit.mean(),
        "medP": df.profit.median(),
        "mean(margin)": df.margin.mean(),
        "sum(margin)": df.margin.sum(),
    }


def boot_ci_all(a, b, keys):
    """CI cua hieu rate(a)-rate(b) cho MOI key, block-bootstrap 2 mau doc lap, noi rong x1.21.
    Vector hoa: moi block duoc rut gon thanh vector tong, resample = cong cac tong."""
    def prep(df):
        g = df.groupby("blk")
        m = pd.DataFrame({
            "n": g.size(),
            "nsl": g.apply(lambda x: (x.status == "STOP_LOSS_DONE").sum()),
            "nsm": g.apply(lambda x: (x.status == "STOP_MARKET_DONE").sum()),
            "nwin": g.apply(lambda x: (x.profit > 0).sum()),
            "psl": g.apply(lambda x: x.profit[x.status == "STOP_LOSS_DONE"].sum()),
            "psm": g.apply(lambda x: x.profit[x.status == "STOP_MARKET_DONE"].sum()),
            "p": g.profit.sum(),
            "mg": g.margin.sum(),
        })
        return m.to_numpy(dtype=float)

    A, Bm = prep(a), prep(b)

    def stats(S):
        n, nsl, nsm, nwin, psl, psm, p, mg = S
        return {
            "TSloss%": 100.0 * nsl / n,
            "win%": 100.0 * nwin / n,
            "mP|SM": psm / nsm if nsm else np.nan,
            "mP|SL": psl / nsl if nsl else np.nan,
            "mP": p / n,
            "mean(margin)": mg / n,
        }

    acc = {k: [] for k in keys}
    for _ in range(NBOOT):
        sa = A[RNG.integers(0, len(A), len(A))].sum(axis=0)
        sb = Bm[RNG.integers(0, len(Bm), len(Bm))].sum(axis=0)
        ra, rb = stats(sa), stats(sb)
        for k in keys:
            acc[k].append(ra[k] - rb[k])
    out = {}
    for k in keys:
        d = np.array([x for x in acc[k] if np.isfinite(x)])
        lo, hi = np.percentile(d, [2.5, 97.5])
        mid, half = (lo + hi) / 2.0, (hi - lo) / 2.0 * WIDEN
        out[k] = (mid - half, mid + half)
    return out


def main():
    tags = sys.argv[1:]
    data = {t: load(t) for t in tags}
    tbl = pd.DataFrame({t: rates(d) for t, d in data.items()}).T
    LOG.info("=== RATE PRIMARY ===\n%s", tbl.round(4).to_string())

    LOG.info("\n=== PHAN BO STATUS (dem / %%) ===")
    for t, d in data.items():
        vc = d.status.value_counts()
        LOG.info("%s (n=%d): %s", t, len(d),
                 {k: f"{v} ({100.0*v/len(d):.2f}%)" for k, v in vc.items()})

    LOG.info("\n=== PHAN BO LEVEL (nguon leg entry) ===")
    for t, d in data.items():
        vc = d.level.value_counts()
        LOG.info("%s: %s", t, {k: f"{v} ({100.0*v/len(d):.2f}%)" for k, v in vc.items()})

    if len(tags) >= 2:
        a = tags[0]
        for b in tags[1:]:
            LOG.info("\n=== CI 95%% block-72h x1.21 : %s - %s ===", a, b)
            keys = ["TSloss%", "win%", "mP|SM", "mP|SL", "mP", "mean(margin)"]
            ci = boot_ci_all(data[a], data[b], keys)
            for k in keys:
                lo, hi = ci[k]
                dd = tbl.loc[a, k] - tbl.loc[b, k]
                flag = "KHAC" if (lo > 0 or hi < 0) else "trong CI"
                LOG.info("  %-13s d=%+9.4f  CI [%+9.4f, %+9.4f]  %s", k, dd, lo, hi, flag)


if __name__ == "__main__":
    main()
