"""LIQX_S1 step 3: episodes + phases (prereg §7-§8) for MKT and COIN, main + sensitivity variants;
control draws (§10). Out: S1/episodes.parquet, S1/ctrl_j.npy (n_ep x 200 int16, row = episodes row order)."""
import json
import numpy as np
import pandas as pd
from common import S1, B5, M1, T_B0, months, maxrss_mb

H = 3_600_000
VARIANTS = {"main": ("99.0", 4.0), "p98": ("98.0", 4.0), "p995": ("99.5", 4.0), "exh3": ("99.0", 3.0), "exh6": ("99.0", 6.0)}
LND = {"MKT": np.log(0.97), "COIN": np.log(0.95)}


def raw_episodes(T, I, c60, theta):
    """Sequential scan: start = valid & I>=theta & c60<=lnD (caller passes c60 already thresholded as bool)."""
    ok = np.isfinite(I)
    start = ok & (I >= theta) & c60
    low = ok & (I < theta / 4.0)
    n = len(T)
    out, nxt_i = [], 0
    for s in np.flatnonzero(start):
        if s < nxt_i:
            continue
        tcap = T[s] + 6 * H
        ecap = int(np.searchsorted(T, tcap, "left"))
        end = None
        for b in range(s + 3, min(ecap, n - 1) + 1):
            if low[b] and low[b - 1] and low[b - 2] and b - 2 > s and T[b] - T[b - 2] == 2 * B5:
                end = b
                break
        if end is None:
            end = ecap if (ecap < n and T[ecap] == tcap) else max(s, ecap - 1)
        out.append([s, end])
        nxt_i = end + 1
    mer = []
    for s, e in out:
        if mer and T[s] - T[mer[-1][1]] < 2 * H:
            mer[-1][1] = e
            mer[-1][2] += 1
        else:
            mer.append([s, e, 1])
    return mer


def exh_idx(T, I, rx, s, div):
    ok = np.isfinite(I)
    lim = int(np.searchsorted(T, T[s] + 6 * H, "right"))
    M, j = I[s], s
    for b in range(s + 1, lim):
        if ok[b] and I[b] > M:
            M, j = I[b], b
        if (b - 1 > j and ok[b] and ok[b - 1] and T[b] - T[b - 1] == B5 and I[b - 1] < M / div and I[b] < M / div
                and np.isfinite(rx[b]) and rx[b] >= -0.005):
            return b
    return -1


def series_eps(level, sym, T, I, c60, rx, theta, div, variant):
    rows = []
    for s, e, nm in raw_episodes(T, I, np.nan_to_num(c60, nan=1.0) <= LND[level], theta):
        seg = I[s:e + 1]
        pk = s + int(np.nanargmax(seg))
        x = exh_idx(T, I, rx, s, div)
        # depth: cumulative r over (T_on-60', T_b], min over b in [on, end]
        lo = int(np.searchsorted(T, T[s] - 60 * M1, "right"))
        cs = np.nancumsum(rx[lo:e + 1])
        depth = float(np.min(cs[s - lo:]))
        rows.append(dict(level=level, variant=variant, sym=sym, T_on=int(T[s]), T_end=int(T[e]), T_peak=int(T[pk]),
                         I_on=float(I[s]), I_peak=float(I[pk]), T_exh=int(T[x]) if x >= 0 else -1,
                         I_maxsofar_exh=float(np.nanmax(I[s:x + 1])) if x >= 0 else np.nan,
                         n_merged=nm, depth=depth, theta=float(theta), div=div))
    return rows


def main():
    th = json.load(open(S1 + "/thresholds.json"))
    K = pd.read_parquet(S1 + "/mkt.parquet")
    T = K["T"].values
    assert T.dtype == np.int64
    rows = []
    for vn, (pc, div) in VARIANTS.items():
        rows += series_eps("MKT", "MKT", T, K.I_mkt.values, K.cum60_mkt.values, K.r_mkt.values, th["mkt"][pc], div, vn)
    # depth for BTC on MKT episodes (descriptive)
    rb = K.r5_btc.values
    for r in rows:
        lo = int(np.searchsorted(T, r["T_on"] - 60 * M1, "right"))
        hi = int(np.searchsorted(T, r["T_end"], "right"))
        on = int(np.searchsorted(T, r["T_on"], "left"))
        r["depth_btc"] = float(np.min(np.nancumsum(rb[lo:hi])[on - lo:]))
    print("MKT eps", sum(1 for r in rows if r["variant"] == "main"), flush=True)
    syms = sorted(th["coin"])
    code = {s: i for i, s in enumerate(syms)}
    parts = {k: [] for k in ("c", "T", "I", "c60", "r5")}
    for y, m in months():
        g = pd.read_parquet(S1 + "/coin/%04d-%02d.parquet" % (y, m), columns=["sym", "T", "I", "cum60", "r5"])
        g["sym"] = g.sym.astype(str)
        g = g[g.sym.isin(code)]
        parts["c"].append(g.sym.map(code).values.astype(np.int32))
        parts["T"].append(g["T"].values)
        parts["I"].append(g.I.values)
        parts["c60"].append(g.cum60.values)
        parts["r5"].append(g.r5.values)
    C = {k: np.concatenate(v) for k, v in parts.items()}
    del parts
    o = np.lexsort((C["T"], C["c"]))
    for k in C:
        C[k] = C[k][o]
    assert C["T"].dtype == np.int64
    bnd = np.searchsorted(C["c"], np.arange(len(syms) + 1))
    print("coin rows", len(C["T"]), round(maxrss_mb()), flush=True)
    for i, s in enumerate(syms):
        a, b = bnd[i], bnd[i + 1]
        Ts = C["T"][a:b]
        assert (np.diff(Ts) > 0).all()
        for vn, (pc, div) in VARIANTS.items():
            rows += series_eps("COIN", s, Ts, C["I"][a:b], C["c60"][a:b], C["r5"][a:b], th["coin"][s][pc], div, vn)
    E = pd.DataFrame(rows)
    E["period"] = np.where(E.T_on <= T_B0, "A", "B")
    E = E.sort_values(["level", "variant", "T_on", "sym"], kind="mergesort").reset_index(drop=True)
    E["ep"] = np.arange(len(E))
    rng = np.random.default_rng(20261024)
    J = np.stack([rng.integers(0, 361, size=200) for _ in range(len(E))]).astype(np.int16)
    E.to_parquet(S1 + "/episodes.parquet", index=False)
    np.save(S1 + "/ctrl_j.npy", J)
    print(E.groupby(["level", "variant", "period"]).size().to_string(), flush=True)
    print("no EXH", E[E.T_exh < 0].groupby(["level", "variant"]).size().to_string(), "maxrss", round(maxrss_mb()))


if __name__ == "__main__":
    main()
