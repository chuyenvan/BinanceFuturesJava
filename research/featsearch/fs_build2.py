"""FS buoc 2b (ban 2): build 16 ung vien + GUARD mau so + UNIT TEST nhan qua.
Chay sau khi cache kline day du. Output /home/ubuntu/fs/feat_fs.parquet"""
import logging, sys, os, json, time
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)
sys.path.insert(0, "/home/ubuntu/fs")

KL = "/home/ubuntu/fs/kl"
OUT = "/home/ubuntu/fs"
H = 3600000
EPS = 1e-12
T_END = 1719792000000
T_BEG = 1614556800000          # 2021-03-01
SEED_NOISE = 20260903
FEATS = ["fs_dvol_7d", "fs_dvol_ratio", "fs_amihud_7d", "fs_trdsize_7d",
         "fs_fund_sum_7d", "fs_fund_slope", "fs_fund_persist",
         "fs_wick_up_7d", "fs_body_ratio_7d", "fs_close_vwap_7d",
         "fs_taker_buy_7d", "fs_up_streak",
         "fs_dd_speed", "fs_pos_7d", "fs_dd_term", "fs_noise"]


def check(cond, msg):
    L.info(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit("STOP: " + msg)


def rm(s, w, mp):
    return pd.Series(s).rolling(w, min_periods=mp).mean().to_numpy()


def rs(s, w, mp):
    return pd.Series(s).rolling(w, min_periods=mp).sum().to_numpy()


def dv(num, den):
    """chia co guard: mau so <= 0 hoac khong huu han => NaN."""
    den = np.asarray(den, dtype=np.float64)
    num = np.asarray(num, dtype=np.float64)
    out = np.full(num.shape, np.nan)
    ok = np.isfinite(den) & (den > 0) & np.isfinite(num)
    out[ok] = num[ok] / den[ok]
    return out


def price_feats(d):
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    v, qv, n, tbqv = d["v"], d["qv"], d["n"], d["tbqv"]
    F = {}
    qv7 = rm(qv, 168, 84)
    qv1 = rm(qv, 24, 12)
    n7 = rm(n, 168, 84)
    F["fs_dvol_7d"] = np.where(np.isfinite(qv7) & (qv7 > 0), np.log10(1.0 + qv7), np.nan)
    F["fs_dvol_ratio"] = dv(qv1, qv7)
    F["fs_amihud_7d"] = rm(dv(np.abs(c / o - 1.0), np.log10(1.0 + qv)), 168, 84)
    F["fs_trdsize_7d"] = np.where(np.isfinite(qv7) & (qv7 > 0) & np.isfinite(n7) & (n7 > 0),
                                  np.log10(1.0 + dv(qv7, n7)), np.nan)
    F["fs_wick_up_7d"] = rm(dv(h - np.maximum(o, c), h - l), 168, 84)
    F["fs_body_ratio_7d"] = rm(dv(np.abs(c - o), h - l), 168, 84)
    F["fs_close_vwap_7d"] = dv(c, dv(rs(qv, 168, 84), rs(v, 168, 84))) - 1.0
    F["fs_taker_buy_7d"] = dv(rs(tbqv, 168, 84), rs(qv, 168, 84))
    up = (c > o) & np.isfinite(c) & np.isfinite(o)
    st = np.zeros(len(up))
    run = 0
    for i in range(len(up)):
        run = run + 1 if up[i] else 0
        st[i] = run
    F["fs_up_streak"] = np.minimum(st, 24.0) / 24.0
    Sc = pd.Series(c)
    mx7 = Sc.rolling(168, min_periods=84).max().to_numpy()
    mn7 = Sc.rolling(168, min_periods=84).min().to_numpy()
    mx30 = Sc.rolling(720, min_periods=360).max().to_numpy()
    dd7 = dv(c, mx7) - 1.0
    dd30 = dv(c, mx30) - 1.0
    F["fs_pos_7d"] = dv(c - mn7, mx7 - mn7)
    F["fs_dd_term"] = dd30 - dd7
    N = len(c)
    hsh = np.full(N, np.nan)
    if N >= 168:
        W = np.lib.stride_tricks.sliding_window_view(c, 168)
        cnt = np.isfinite(W).sum(1)
        am = np.where(np.isfinite(W), W, -np.inf).argmax(1).astype(np.float64)
        am[cnt < 84] = np.nan
        hsh[167:] = 167.0 - am
    F["fs_dd_speed"] = dv(dd7, np.maximum(hsh, 1.0))
    for k in F:
        F[k] = np.where(np.isfinite(F[k]), F[k], np.nan)
    return F


def fund_feats(idx_h, s_ts, s_v):
    nan = np.full(len(idx_h), np.nan)
    if s_ts is None or len(s_ts) < 10:
        return {"fs_fund_sum_7d": nan, "fs_fund_slope": nan, "fs_fund_persist": nan.copy()}
    F = {}
    i_last = np.searchsorted(s_ts, idx_h, side="right") - 1
    cs = np.concatenate([[0.0], np.cumsum(s_v)])
    hi = np.clip(i_last + 1, 0, len(s_v))
    lo168 = np.searchsorted(s_ts, idx_h - 168 * H, side="right")
    lo72 = np.searchsorted(s_ts, idx_h - 72 * H, side="right")
    ok = i_last >= 0
    F["fs_fund_sum_7d"] = np.where(ok & (hi > lo168), cs[hi] - cs[lo168], np.nan)
    n72 = (hi - lo72).astype(float)
    nmid = (lo72 - lo168).astype(float)
    m72 = np.where(n72 > 0, (cs[hi] - cs[lo72]) / np.maximum(n72, 1), np.nan)
    mmid = np.where(nmid > 0, (cs[lo72] - cs[lo168]) / np.maximum(nmid, 1), np.nan)
    F["fs_fund_slope"] = np.where(ok, m72 - mmid, np.nan)
    sg = np.sign(s_v)
    runl = np.ones(len(sg))
    for i in range(1, len(sg)):
        runl[i] = runl[i - 1] + 1 if (sg[i] == sg[i - 1] and sg[i] != 0) else 1
    pv = sg * np.minimum(runl, 21.0)
    F["fs_fund_persist"] = np.where(ok, pv[np.clip(i_last, 0, None)], np.nan)
    return F


def fund_of(cli, sym):
    import cramjam
    try:
        _, _, rec = cli.get(("test", "funding_data", sym))
        js = bytes(cramjam.snappy.decompress_raw(bytes(rec["f_data"]))).decode()
        d = {int(k): float(v) for k, v in json.loads(js).items()}
    except Exception:
        return None, None
    if len(d) < 10:
        return None, None
    k = np.array(sorted(d.keys()), dtype=np.int64)
    return k, np.array([d[int(x)] for x in k], dtype=np.float64)


def grid_of(z):
    ot = z["ot"]
    grid = np.arange(ot.min(), ot.max() + H, H)
    pos = ((ot - grid[0]) // H).astype(np.int64)
    d = {}
    for c in ("o", "h", "l", "c", "v", "qv", "n", "tbqv"):
        arr = np.full(len(grid), np.nan)
        arr[pos] = z[c].astype(np.float64)
        d[c] = arr
    return grid, d


def main():
    import aerospike
    mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
    i2s = dict(zip(mp.symId, mp.symbol))
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    files = sorted(int(f[:-4]) for f in os.listdir(KL) if f.endswith(".npz"))
    L.info("cache %d symbol", len(files))
    parts, nfok, t0 = [], 0, time.time()
    keep_for_test = {}
    for k, sid in enumerate(files):
        z = np.load(f"{KL}/{sid}.npz")
        if len(z["ot"]) < 400:
            continue
        grid, d = grid_of(z)
        F = price_feats(d)
        fts = grid + H
        sname = i2s.get(sid)
        st, sv = fund_of(cli, sname) if sname else (None, None)
        nfok += st is not None
        F.update(fund_feats(fts, st, sv))
        F["fs_noise"] = np.random.default_rng([SEED_NOISE, sid]).random(len(fts))
        m = np.isfinite(d["c"]) & (fts <= T_END) & (fts >= T_BEG)
        if m.sum() == 0:
            continue
        df = pd.DataFrame({"ts": fts[m], "sym": np.int32(sid)})
        for nm in FEATS:
            df[nm] = np.asarray(F[nm], dtype=np.float64)[m].astype(np.float32)
        parts.append(df)
        if len(keep_for_test) < 6:
            keep_for_test[sid] = None
        if (k + 1) % 60 == 0:
            L.info("%d/%d %.0fs", k + 1, len(files), time.time() - t0)
    big = pd.concat(parts, ignore_index=True)
    L.info("rows=%d syms=%d funding_ok=%d", len(big), big.sym.nunique(), nfok)
    q = big[FEATS].describe(percentiles=[.01, .5, .99]).T
    q["nan%"] = big[FEATS].isna().mean().round(4)
    L.info("\n%s", q.round(6).to_string())
    for nm in FEATS:
        v = big[nm].to_numpy()
        check(np.isfinite(v[~np.isnan(v)]).all(), f"huu han: {nm}")
    check(big.fs_pos_7d.min() >= -1e-6 and big.fs_pos_7d.max() <= 1 + 1e-6, "range pos_7d in [0,1]")
    check(big.fs_taker_buy_7d.min() >= 0 and big.fs_taker_buy_7d.max() <= 1 + 1e-6,
          "range taker_buy in [0,1]")
    check(big.fs_dd_speed.max() <= 1e-9, "range dd_speed <= 0")
    check(big.fs_dd_term.max() <= 1e-6, "range dd_term = dd30-dd7 <= 0")
    check(abs(big.fs_close_vwap_7d).max() < 50, "range close_vwap hop ly (<50)")
    # ---------- UNIT TEST NHAN QUA: cat chuoi kline tai t-1h, tinh lai 4 feature ----------
    L.info("== unit test nhan qua (200 mau, cat chuoi tai t-1h) ==")
    rgt = np.random.default_rng(11)
    tested = bad = 0
    for sid in sorted(np.unique(big.sym))[:40]:
        z = np.load(f"{KL}/{sid}.npz")
        if len(z["ot"]) < 1500:
            continue
        grid, d = grid_of(z)
        F = price_feats(d)
        fts = grid + H
        valid = np.where(np.isfinite(d["c"]) & (np.arange(len(grid)) >= 800))[0]
        if len(valid) < 5:
            continue
        for i in rgt.choice(valid, min(5, len(valid)), replace=False):
            dc = {kk: vv[:i + 1].copy() for kk, vv in d.items()}   # CAT tai bar i (= t-1h)
            Fc = price_feats(dc)
            for nm in ("fs_dvol_7d", "fs_taker_buy_7d", "fs_wick_up_7d", "fs_pos_7d",
                       "fs_dd_speed", "fs_dd_term"):
                a1, a2 = F[nm][i], Fc[nm][i]
                tested += 1
                if not (np.isnan(a1) and np.isnan(a2)) and not np.isclose(
                        a1, a2, rtol=1e-9, atol=1e-12, equal_nan=True):
                    bad += 1
                    L.info("  MISMATCH %s sid=%d i=%d %s vs %s", nm, sid, i, a1, a2)
    check(bad == 0, f"CAUSALITY {tested} phep so: mismatch={bad}")
    big.to_parquet(f"{OUT}/feat_fs.parquet", index=False)
    json.dump({"feats": FEATS, "n_rows": int(len(big)), "t_end": T_END, "t_beg": T_BEG,
               "src": "data.binance.vision monthly klines 1h (um) + aerospike funding_data",
               "rule": "feature tai gio t chi dung bar co open_time <= t-1h; nhan ts = open_time+1h",
               "anchor": "CLOSES_1H[t] == close(kline open_time=t-1h), relerr<5e-8"},
              open(f"{OUT}/feat_fs.meta.json", "w"), indent=1)
    L.info("SAVED %.0fs ALL_FS_BUILD_PASS", time.time() - t0)


if __name__ == "__main__":
    main()
