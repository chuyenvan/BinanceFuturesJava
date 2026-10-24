"""LIQX_S1 step 6: X14 legs (8 seeds) placed on episode phases — PERIOD A ONLY (prereg §11). Descriptive.
Rows are filtered to start_u in A BEFORE the pnl column is used. Out: art/x14A_legs.csv, art/x14A_phase.json."""
import json
import os
import sys
import numpy as np
import pandas as pd
from common import S1, DAY, M1, T_A0, T_B0

KS = "/home/ubuntu/kaggle_sim/out"
TAGS = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]
H = 3_600_000
OUT = sys.argv[1] if len(sys.argv) > 1 else S1 + "/art"
os.makedirs(OUT, exist_ok=True)


def load_A():
    fr = []
    for tag in TAGS:
        d = pd.read_csv(os.path.join(KS, "tsx-x14-" + tag, "storage", "printDone.csv"), index_col=False, dtype=str)
        d.columns = [c.strip() for c in d.columns]
        st = pd.to_datetime(d["start"].str.strip(), format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
        t = st.values.astype("datetime64[ms]").astype(np.int64)
        keep = (t >= T_A0) & (t < T_B0)          # filter BEFORE touching pnl
        d = d[keep].copy()
        d["t"] = t[keep]
        for c in ("entry", "pnl", "margin"):
            d[c] = pd.to_numeric(d[c], errors="coerce")
        d["sym"] = d["sym"].astype(str).str.strip()
        d["sym"] = np.where(d["sym"].str.endswith("USDT"), d["sym"], d["sym"] + "USDT")
        d = d.dropna(subset=["entry", "pnl"])
        d = d[d.entry > 0]
        d["seed"] = tag
        fr.append(d[["seed", "sym", "t", "entry", "pnl", "margin"]])
    x = pd.concat(fr, ignore_index=True)
    assert x.t.dtype == np.int64 and x.t.max() < T_B0
    x["roi"] = x.pnl / x.margin
    return x


def phase(t, eps):
    """eps sorted by T_on. Returns phase str array, ep id array, lag_on_h, lag_exh_h."""
    on = eps.T_on.values
    exh = eps.T_exh.values
    k = np.searchsorted(on - 6 * H, t, "right") - 1
    ph = np.full(len(t), "NGOAI", dtype=object)
    epi = np.full(len(t), -1, dtype=np.int64)
    lon = np.full(len(t), np.nan)
    lex = np.full(len(t), np.nan)
    for i in np.flatnonzero(k >= 0):
        j = k[i]
        o, x, tt = on[j], exh[j], t[i]
        if tt < o:
            p = "TRUOC"
        elif x >= 0:
            p = "TRONG_TRUOC_EXH" if tt < x + M1 else ("SAU_EXH" if tt < x + 24 * H else "NGOAI")
        else:
            p = "TRONG_TRUOC_EXH" if tt < o + 6 * H else ("SAU_NOEXH" if tt < o + 24 * H else "NGOAI")
        ph[i] = p
        if p != "NGOAI":
            epi[i] = eps.ep.values[j]
            lon[i] = (tt - o) / H
            lex[i] = (tt - (x + M1)) / H if x >= 0 else np.nan
    return ph, epi, lon, lex


def boot(v, cl, B=10000, seed=7):
    u, inv = np.unique(cl, return_inverse=True)
    if len(u) < 2:
        return [np.nan, np.nan]
    s, c = np.bincount(inv, weights=v), np.bincount(inv).astype(float)
    idx = np.random.default_rng(seed).integers(0, len(u), size=(B, len(u)))
    m = s[idx].sum(1) / c[idx].sum(1)
    return [float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))]


def summarize(x, phcol, epcol):
    out = {}
    tot = x.groupby("seed").pnl.sum()
    for p, g in x.groupby(phcol):
        day = (g.t // DAY).astype(np.int64)
        cl = np.where(g[epcol] >= 0, g[epcol].astype(str), "d" + day.astype(str))
        clus = g.seed + "|" + g.sym + "|" + pd.Series(cl, index=g.index)
        share = (g.groupby("seed").pnl.sum() / tot).reindex(tot.index).fillna(0)
        out[p] = dict(n_leg=int(len(g)), n_cluster=int(clus.nunique()), n_ep=int(len(set(g[epcol][g[epcol] >= 0]))),
                      roi_mean=float(g.roi.mean()), roi_median=float(g.roi.median()), roi_ci=boot(g.roi.values, cl),
                      pnl_mean=float(g.pnl.mean()), pnl_ci=boot(g.pnl.values, cl),
                      pnl_share_mean_8seed=float(share.mean()), win=float((g.pnl > 0).mean()),
                      lag_on_h_median=float(np.nanmedian(g.lag_on)) if g.lag_on.notna().any() else None,
                      lag_exh_h_median=float(np.nanmedian(g.lag_exh)) if g.lag_exh.notna().any() else None)
    return out


def main():
    E = pd.read_parquet(S1 + "/episodes.parquet")
    E = E[E.variant == "main"]
    em = E[E.level == "MKT"].sort_values("T_on").reset_index(drop=True)
    x = load_A()
    ph, epi, lon, lex = phase(x.t.values, em)
    x["phase_mkt"], x["ep_mkt"], x["lag_on"], x["lag_exh"] = ph, epi, lon, lex
    ec = E[E.level == "COIN"]
    pc = np.full(len(x), "NO_THETA", dtype=object)
    epc = np.full(len(x), -1, dtype=np.int64)
    lonc, lexc = np.full(len(x), np.nan), np.full(len(x), np.nan)
    th = json.load(open(S1 + "/thresholds.json"))["coin"]
    for s, g in x.groupby("sym"):
        if s not in th:
            continue
        es = ec[ec.sym == s].sort_values("T_on").reset_index(drop=True)
        a, b, c_, d_ = phase(g.t.values, es) if len(es) else (np.full(len(g), "NGOAI", dtype=object), np.full(len(g), -1),
                                                              np.full(len(g), np.nan), np.full(len(g), np.nan))
        ii = x.index.get_indexer(g.index)
        pc[ii], epc[ii], lonc[ii], lexc[ii] = a, b, c_, d_
    x["phase_coin"], x["ep_coin"] = pc, epc
    x["t_utc"] = pd.to_datetime(x.t, unit="ms").dt.strftime("%Y-%m-%d %H:%M")
    x.to_csv(OUT + "/x14A_legs.csv", index=False, float_format="%.6g")
    res = {"MKT": summarize(x, "phase_mkt", "ep_mkt")}
    xc = x.copy()
    xc["lag_on"], xc["lag_exh"] = lonc, lexc
    res["COIN"] = summarize(xc, "phase_coin", "ep_coin")
    ema = em[em.period == "A"]
    first = x[x.ep_mkt >= 0].sort_values("t").groupby(["ep_mkt"]).first()
    res["mkt_eps_A"] = int(len(ema))
    res["mkt_eps_A_with_leg"] = int(x[x.ep_mkt.isin(ema.ep)].ep_mkt.nunique())
    res["first_leg_phase_per_ep"] = first.phase_mkt.value_counts().to_dict()
    res["n_leg_total_A"] = int(len(x))
    res["pnl_total_A_per_seed_mean"] = float(x.groupby("seed").pnl.sum().mean())
    json.dump(res, open(OUT + "/x14A_phase.json", "w"), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float)[:6000])


if __name__ == "__main__":
    main()
