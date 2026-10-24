"""LIQX_S1 common: constants, PIT universe, raw readers, per-(sym,day) create_time convention detection,
coin bucket builder. Prereg docs/prereg/PREREG_LIQX_S1.md (commit ad10cc97). All ts int64 ms UTC."""
import os
import resource
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

WK = os.path.expanduser("~/claude_master/liqx_wk")
S1 = WK + "/s1"
KL = "/home/ubuntu/vz_e1/raw/kline1m-%04d-%02d.parquet"
MET = "/home/ubuntu/vz/out/metrics5m/%04d/%04d-%02d.parquet"
DAY, B5, M1 = 86_400_000, 300_000, 60_000
EXCL = {"USDCUSDT", "BTCDOMUSDT", "DEFIUSDT", "FOOTBALLUSDT", "BLUEBIRDUSDT", "PAXGUSDT", "XAUUSDT"}
MAJ = {"BTCUSDT", "ETHUSDT"}
KCOLS = ["ts", "sym", "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote"]
MCOLS = ["ts", "sym", "oi", "oi_value", "taker_ls_vol"]
NMIN = 12  # min pairs for taker convention test
NMIN_P, PR_RATIO = 144, 3.0  # AMEND1 (PREREG_LIQX_S1_AMEND1.md): implied-price fallback


def ms(y, m, d=1):
    return int(pd.Timestamp(year=y, month=m, day=d, tz="UTC").value // 1_000_000)


T_A0, T_B0, T_END = ms(2022, 1, 1), ms(2024, 1, 1), ms(2026, 1, 1)
KL_LAST = ms(2025, 12, 1) + 31 * DAY - M1  # last 1m bar open available (2025-12-31 23:59)


def months():
    return [(y, m) for y in range(2022, 2026) for m in range(1, 13)]


def nxt(y, m):
    return (y, m + 1) if m < 12 else (y + 1, 1)


def prv(y, m):
    return (y, m - 1) if m > 1 else (y - 1, 12)


def maxrss_mb():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def universe(dq, M):
    """dq: daily_qv (sym, day, qv). Returns list of top-100 syms ordered by score desc (tie: sym)."""
    days = M - DAY * np.arange(30, 0, -1, dtype=np.int64)
    w = dq[(dq.day >= days[0]) & (dq.day < M) & ~dq.sym.isin(EXCL)]
    p = w.pivot_table(index="sym", columns="day", values="qv", aggfunc="sum").reindex(columns=days).fillna(0.0)
    sc = pd.Series(np.median(p.values, axis=1), index=p.index)
    o = sorted(sc.items(), key=lambda kv: (-kv[1], kv[0]))
    return [s for s, _ in o[:100]], dict(o)


def _ym_range(lo, hi):
    y, m = int(pd.Timestamp(lo, unit="ms").year), int(pd.Timestamp(lo, unit="ms").month)
    out = []
    while ms(y, m) < hi:
        out.append((y, m))
        y, m = nxt(y, m)
    return out


def read_kline(syms, lo, hi, cols=KCOLS):
    out = []
    for y, m in _ym_range(lo, hi):
        if (y, m) > (2025, 12) or (y, m) < (2021, 12):
            continue
        t = pq.read_table(KL % (y, m), columns=cols,
                          filters=[("sym", "in", sorted(syms)), ("ts", ">=", lo), ("ts", "<", hi)]).to_pandas()
        t["sym"] = t.sym.astype(str)
        out.append(t)
    k = pd.concat(out, ignore_index=True)
    assert k.ts.dtype == np.int64
    k = k.sort_values(["sym", "ts"], kind="mergesort").reset_index(drop=True)
    assert not k.duplicated(["sym", "ts"]).any()
    return k


def read_metrics(syms, lo, hi):
    out = []
    for y, m in _ym_range(lo, hi):
        if (y, m) > (2025, 12) or (y, m) < (2021, 12):
            continue
        t = pq.read_table(MET % (y, y, m), columns=MCOLS,
                          filters=[("sym", "in", sorted(syms)), ("ts", ">=", lo), ("ts", "<", hi)]).to_pandas()
        t["sym"] = t.sym.astype(str)
        out.append(t)
    x = pd.concat(out, ignore_index=True)
    assert x.ts.dtype == np.int64
    x = x.sort_values(["sym", "ts"], kind="mergesort").drop_duplicates(["sym", "ts"], keep="last").reset_index(drop=True)
    return x


def detect_conv(met, kl, days):
    """Per (sym, day of create_time) convention. met: (sym,ts,oi,oi_value,taker_ls_vol); kl: (sym,ts,close,volume,taker_buy_base).
    Returns DataFrame sym, day, n_t, err_old, err_new, n_p, perr_old, perr_new, conv (NEW/OLD/AMBIG), via."""
    k = kl[["sym", "ts", "volume", "taker_buy_base"]].copy()
    k["w"] = (k.ts // B5) * B5
    g = k.groupby(["sym", "w"]).agg(tb=("taker_buy_base", "sum"), v=("volume", "sum"), nb=("ts", "size")).reset_index()
    g = g[(g.nb == 5) & (g.tb > 0) & (g.v - g.tb > 0)]
    g["r"] = g.tb / (g.v - g.tb)
    rr = g[["sym", "w", "r"]]
    m = met[met.ts // DAY * DAY >= days[0]].copy()
    m = m[m.ts // DAY * DAY <= days[-1]]
    m["day"] = (m.ts // DAY) * DAY
    m = m.merge(rr.rename(columns={"w": "ts", "r": "r_new"}), on=["sym", "ts"], how="left")
    m = m.merge(rr.assign(ts=rr.w + B5).drop(columns="w").rename(columns={"r": "r_old"}), on=["sym", "ts"], how="left")
    c = kl[["sym", "ts", "close"]]
    m = m.merge(c.assign(ts=c.ts + M1).rename(columns={"close": "c_old"}), on=["sym", "ts"], how="left")
    m = m.merge(c.assign(ts=c.ts - 4 * M1).rename(columns={"close": "c_new"}), on=["sym", "ts"], how="left")
    x = m.taker_ls_vol
    okx = np.isfinite(x) & (x > 0)
    m["e_old"] = np.where(okx & m.r_old.notna(), (x / m.r_old - 1).abs(), np.nan)
    m["e_new"] = np.where(okx & m.r_new.notna(), (x / m.r_new - 1).abs(), np.nan)
    m["e_both"] = m.e_old.notna() & m.e_new.notna()
    p = np.where((m.oi > 0) & np.isfinite(m.oi_value), m.oi_value / m.oi, np.nan)
    m["p_old"] = np.where(np.isfinite(p) & m.c_old.notna() & m.c_new.notna(), np.abs(p / m.c_old - 1), np.nan)
    m["p_new"] = np.where(np.isfinite(p) & m.c_old.notna() & m.c_new.notna(), np.abs(p / m.c_new - 1), np.nan)
    mb = m[m.e_both]
    a = mb.groupby(["sym", "day"]).agg(n_t=("e_old", "size"), err_old=("e_old", "median"), err_new=("e_new", "median"))
    mp = m[m.p_old.notna()]
    b = mp.groupby(["sym", "day"]).agg(n_p=("p_old", "size"), perr_old=("p_old", "median"), perr_new=("p_new", "median"))
    allk = m.groupby(["sym", "day"]).size().rename("n_rows")
    r = pd.concat([allk, a, b], axis=1).reset_index()
    r["n_t"] = r.n_t.fillna(0).astype("int64")
    r["n_p"] = r.n_p.fillna(0).astype("int64")
    conv = np.full(len(r), "AMBIG", dtype=object)
    via = np.full(len(r), "none", dtype=object)
    tk = r.n_t >= NMIN
    new_t = tk & (r.err_new < r.err_old / 10)
    old_t = tk & (r.err_old < r.err_new / 10)
    pk = (r.n_p >= NMIN_P) & ~new_t & ~old_t   # AMEND1: price fallback 3x, >=144 pairs
    new_p = pk & (r.perr_new < r.perr_old / PR_RATIO)
    old_p = pk & (r.perr_old < r.perr_new / PR_RATIO)
    conv[new_t] = "NEW"; via[new_t] = "taker"
    conv[old_t] = "OLD"; via[old_t] = "taker"
    conv[new_p] = "NEW"; via[new_p] = "price"
    conv[old_p] = "OLD"; via[old_p] = "price"
    r["conv"] = conv
    r["via"] = via
    assert r.day.dtype == np.int64
    return r


def apply_conv(met, conv):
    """Effective ts per prereg §2. Returns (eff frame sym, ts, oi, oi_value), counters."""
    cm = {(s, d): c for s, d, c in zip(conv.sym, conv.day, conv.conv)}
    m = met.copy()
    m["day"] = (m.ts // DAY) * DAY
    cur = np.array([cm.get((s, d), "MISSING") for s, d in zip(m.sym, m.day)], dtype=object)
    prev = np.array([cm.get((s, d - DAY), "MISSING") for s, d in zip(m.sym, m.day)], dtype=object)
    edge = (m.ts.values % DAY) == 0
    use = cur.copy()
    drop = np.zeros(len(m), bool)
    e_old = edge & (prev == "OLD")
    use[e_old] = "OLD"
    drop |= e_old & (cur == "NEW")
    drop |= edge & (prev == "AMBIG")
    drop |= (use != "OLD") & (use != "NEW")
    n_drop = int(drop.sum())
    m = m[~drop].copy()
    use = use[~drop]
    m["ts"] = m.ts.values + np.where(use == "NEW", B5, 0).astype(np.int64)
    dup = m.duplicated(["sym", "ts"], keep=False)
    n_dup = int(dup.sum())
    m = m[~dup]
    assert m.ts.dtype == np.int64
    return m[["sym", "ts", "oi", "oi_value"]].reset_index(drop=True), dict(drop_rows=n_drop, dup_rows=n_dup)


def build_buckets(kl, meff, syms, days):
    """Coin buckets for syms over days (list of day-start ms). Prereg §4."""
    T = np.concatenate([d + B5 * np.arange(1, 289, dtype=np.int64) for d in days])
    g = pd.DataFrame({"sym": np.repeat(list(syms), len(T)), "T": np.tile(T, len(syms))})
    m = meff[["sym", "ts", "oi_value"]]
    g = g.merge(m.rename(columns={"ts": "T", "oi_value": "oiv1"}), on=["sym", "T"], how="left")
    g = g.merge(m.assign(T=m.ts + B5).drop(columns="ts").rename(columns={"oi_value": "oiv0"}), on=["sym", "T"], how="left")
    c = kl[["sym", "ts", "close"]]
    for lag, nm in ((M1, "c1"), (6 * M1, "c0"), (61 * M1, "c60")):
        g = g.merge(c.assign(T=c.ts + lag).drop(columns="ts").rename(columns={"close": nm}), on=["sym", "T"], how="left")
    kb = kl[["sym", "ts", "quote_volume", "taker_buy_quote"]].assign(T=(kl.ts // B5 + 1) * B5)
    s = kb.groupby(["sym", "T"]).agg(nbar=("ts", "size"), qv=("quote_volume", "sum"), tbq=("taker_buy_quote", "sum")).reset_index()
    g = g.merge(s, on=["sym", "T"], how="left")
    g["nbar"] = g.nbar.fillna(0).astype("int64")
    g["valid"] = g.oiv0.notna() & (g.oiv0 > 0) & g.oiv1.notna() & g.c1.notna() & g.c0.notna() & (g.nbar == 5)
    g["oidrop"] = np.maximum(0.0, g.oiv0 - g.oiv1)
    g["tsx"] = np.maximum(0.0, g.qv - 2.0 * g.tbq)
    g["r5"] = np.log(g.c1 / g.c0)
    g["cum60"] = np.log(g.c1 / g.c60)
    p2 = np.where(g.r5 < 0, np.minimum(g.oidrop, g.tsx), 0.0)
    g["P2"] = np.where(g.valid, p2, np.nan)
    g["I"] = np.where(g.valid, g.P2 / g.oiv0, np.nan)
    for col in ("oidrop", "tsx", "r5", "qv"):
        g.loc[~g.valid, col] = np.nan
    g["day"] = ((g["T"] - 1) // DAY) * DAY
    assert g["T"].dtype == np.int64 and g["day"].dtype == np.int64
    cnt = g.groupby(["sym", "day"]).size()
    assert (cnt == 288).all()
    return g[["sym", "T", "day", "valid", "oiv0", "oiv1", "oidrop", "tsx", "qv", "r5", "cum60", "c1", "P2", "I"]]
