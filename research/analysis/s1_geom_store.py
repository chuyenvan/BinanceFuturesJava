#!/usr/bin/env python3
"""S1_FEAT_GEOM — store OHLC 1h moi tu Aerospike test.kline_1m_opt (pre-reg docs/prereg/PREREG_S1_FEAT_GEOM.md muc 1).
Stage: month [--procs 3]  -> WORK/m/YYYYMM.parquet (long: ts_h, sym, o, h, l, c, qv, nmin)
       merge              -> /home/ubuntu/java/fsrun/OHLCV_1H_v2.bin + .manifest.json + sanity S1/S2 (FAIL => exit 3)
Quy uoc: nen gio [h, h+1h) -> ts_h = h + 1h (gio DONG, nhu CLOSES_1H). Lineage v2: bo gio ngoai [floor_h(first_real), floor_h(last_real)].
KHONG ghi de file co san. DEV <= 2025-12-31 23:59 UTC.
"""
import argparse, glob, hashlib, json, logging, os, sys, time
import numpy as np
import pandas as pd
REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(process)d %(message)s", stream=sys.stdout)
log = logging.getLogger("geom_store")
WORK = "/home/ubuntu/claude_master/1003/geom/store"
OUT = "/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin"
MAN = "/home/ubuntu/java/fsrun/OHLCV_1H_v2.manifest.json"
V2 = "/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin"
LIN = os.path.join(REPO, "data/meta/symbol_lineage_v2.csv")
MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
MIN, H = 60000, 3600000
DEV_M1 = 1767225600000 // MIN - 1
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("o", ">f4"), ("h", ">f4"), ("l", ">f4"), ("c", ">f4"), ("qv", ">f4")])
DTV2 = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
SEED = 20260905
MONTHS = [y * 100 + m for y in range(2021, 2026) for m in range(1, 13)]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def lineage():
    L = pd.read_csv(LIN)
    mp = pd.read_csv(MAP)
    s2i = dict(zip(mp.symbol, mp.symId))
    ms = lambda s: pd.to_datetime(s).astype("int64") // 10 ** 6  # noqa: E731
    L["sid"] = L.symbol.map(s2i)
    assert L.sid.notna().all(), "lineage co symbol khong co trong symbol_map"
    L["h_first"] = ms(L.first_real_ts) // H * H
    L["h_last"] = ms(L.last_real_ts) // H * H
    return L.set_index("symbol")


def month(ym):
    import short_v3_r1_fade as R1
    fp = os.path.join(WORK, "m", "%d.parquet" % ym)
    if os.path.exists(fp):
        return ym, -1, 0.0
    t0 = time.time()
    y, mo = divmod(ym, 100)
    s0 = pd.Timestamp(year=y, month=mo, day=1, tz="UTC")
    b0 = int(s0.value // 10 ** 9 // 60)
    b1 = min(int((s0 + pd.offsets.MonthBegin(1)).value // 10 ** 9 // 60) - 1, DEV_M1)
    arr, names, nrec = R1.stream(b0, b1, str(ym))
    N, S = arr.shape[1], arr.shape[2]
    assert N % 60 == 0 and b0 % 60 == 0
    nh = N // 60
    O, Hh, Lw, C, V = (arr[k].reshape(nh, 60, S) for k in range(5))
    fc, fo = np.isfinite(C), np.isfinite(O)
    cnt = fc.sum(axis=1)
    i_last = 59 - np.argmax(fc[:, ::-1, :], axis=1)
    i_first = np.argmax(fo, axis=1)
    close = np.take_along_axis(C, i_last[:, None, :], axis=1)[:, 0, :]
    opn = np.take_along_axis(O, i_first[:, None, :], axis=1)[:, 0, :]
    with np.errstate(all="ignore"):
        import warnings
        warnings.simplefilter("ignore")
        hi = np.nanmax(Hh, axis=1)
        lo = np.nanmin(Lw, axis=1)
    qv = np.nansum(V, axis=1)
    hh, ss = np.nonzero(cnt > 0)
    df = pd.DataFrame({"ts_h": (b0 * MIN + (hh.astype(np.int64) + 1) * H), "sym": np.asarray(names)[ss],
                       "o": opn[hh, ss], "h": hi[hh, ss], "l": lo[hh, ss], "c": close[hh, ss],
                       "qv": qv[hh, ss].astype(np.float32), "nmin": cnt[hh, ss].astype(np.int16)})
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    df.to_parquet(fp, index=False)
    log.info("MONTH %d nsym %d nrec %d rows %d %.0fs", ym, S, nrec, len(df), time.time() - t0)
    return ym, len(df), time.time() - t0


def merge():
    for p in (OUT, MAN):
        if os.path.exists(p) and os.environ.get("FORCE_OHLCV") != "1":
            raise SystemExit("%s da ton tai — khong ghi de" % p)
    fs = sorted(glob.glob(os.path.join(WORK, "m", "*.parquet")))
    assert len(fs) == len(MONTHS), ("thieu thang", len(fs))
    A = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    n_raw, nsym_raw = len(A), A.sym.nunique()
    L = lineage()
    A = A[A.sym.isin(L.index)].copy()
    n_notlin = n_raw - len(A)
    A["sid"] = A.sym.map(L.sid).astype(np.int64)
    hopen = A.ts_h - H
    hf, hl = A.sym.map(L.h_first), A.sym.map(L.h_last)
    head = hf.notna() & (hopen < hf)
    tail = hl.notna() & (hopen > hl)
    A = A[~(head | tail)].sort_values(["ts_h", "sid"]).reset_index(drop=True)
    assert not A.duplicated(["ts_h", "sid"]).any()
    assert A.ts_h.max() <= DEV_M1 * MIN + MIN, "qua DEV"
    b = np.empty(len(A), dtype=DT)
    b["ts"], b["sym"] = A.ts_h.to_numpy(np.int64), A.sid.to_numpy(np.int16)
    for k in ("o", "h", "l", "c", "qv"):
        b[k] = A[k].to_numpy(np.float32)
    b.tofile(OUT)
    log.info("ghi %s rec %d (raw %d, ngoai lineage %d, head %d, tail %d)", OUT, len(b), n_raw, n_notlin,
             int(head.sum()), int(tail.sum()))
    chk = sanity(b)
    yrs = pd.Series(pd.to_datetime(A.ts_h - H, unit="ms").dt.year).value_counts().sort_index()
    man = dict(created_utc=str(pd.Timestamp.utcnow())[:19], script="research/analysis/s1_geom_store.py (month -> merge)",
               prereg="docs/prereg/PREREG_S1_FEAT_GEOM.md",
               source="Aerospike test.kline_1m_opt (1 luot stream theo thang, short_v3_r1_fade.stream; field5 = quoteVol USDT)",
               minutes_utc="2021-01-01 00:00 .. 2025-12-31 23:59",
               rule=dict(bar="nen gio [h,h+1h): ts_h = h+1h (gio DONG); open = O phut huu han dau; high = max H; low = min L; "
                             "close = C phut huu han cuoi; quoteVol = sum V; gio khong co phut nao -> khong co rec",
                         lineage="symbol trong data/meta/symbol_lineage_v2.csv (627); bo gio h < floor_h(first_real_ts) "
                                 "hoac h > floor_h(last_real_ts) (F_HEAD/F_TAIL nhu CLOSES_1H_v2)",
                         stable="STABLE cua short_v3_r1_fade bi loai khi stream"),
               format="30 B/rec big-endian [ts_h:int64 close-time ms][symId:int16 symbol_map.csv][open,high,low,close,quoteVol:float32], sort (ts_h, symId)",
               symbol_map=MAP, lineage=dict(path="data/meta/symbol_lineage_v2.csv", md5=md5f(LIN)),
               out=dict(path=OUT, md5=md5f(OUT), n_rec=int(len(b)), n_sym=int(A.sid.nunique()), bytes=os.path.getsize(OUT),
                        ts_first=str(pd.to_datetime(int(b["ts"].min()), unit="ms")), ts_last=str(pd.to_datetime(int(b["ts"].max()), unit="ms"))),
               drop=dict(raw_rows=int(n_raw), raw_nsym=int(nsym_raw), not_in_lineage=int(n_notlin), head=int(head.sum()), tail=int(tail.sum())),
               rec_by_year={int(k): int(v) for k, v in yrs.items()}, sanity=chk)
    json.dump(man, open(MAN, "w"), indent=1, ensure_ascii=False)
    log.info("MANIFEST %s", json.dumps({k: man[k] for k in ("out", "drop", "sanity")}))
    if not (chk["S1_pass"] and chk["S2_pass"]):
        log.info("SANITY_FAIL")
        sys.exit(3)
    log.info("SANITY_PASS")


def sanity(b):
    o, h, l, c = (b[k].astype(np.float32) for k in ("o", "h", "l", "c"))
    nan_c = int((~np.isfinite(c)).sum())
    nan_o = int((~np.isfinite(o)).sum())
    nan_hl = int((~np.isfinite(h) | ~np.isfinite(l)).sum())
    mx = np.fmax(o, c)
    mn = np.fmin(o, c)
    bad_h = int((~(h >= mx)).sum())
    bad_l = int((~(l <= mn)).sum())
    v = np.fromfile(V2, dtype=DTV2)
    V = pd.DataFrame({"ts": v["ts"].astype(np.int64), "sym": v["sym"].astype(np.int64), "c": v["c"].astype(np.float32)})
    V = V[np.isfinite(V.c)]
    S = pd.DataFrame({"ts": b["ts"].astype(np.int64), "sym": b["sym"].astype(np.int64), "cs": c})
    rng = np.random.default_rng(SEED)
    vc = V.sym.value_counts()
    pool = np.sort(vc.index[vc.to_numpy() >= 48].to_numpy())
    syms = rng.choice(pool, 30, replace=False)
    pick = []
    for s in syms:
        r = V[V.sym == s].sort_values("ts")
        i = int(rng.integers(0, len(r) - 24 + 1))
        pick.append(r.iloc[i:i + 24])
    P = pd.concat(pick).merge(S, on=["ts", "sym"], how="left")
    s1_ok = int((P.cs.to_numpy() == P.c.to_numpy()).sum())
    M = V[["ts", "sym"]].merge(S[["ts", "sym"]], on=["ts", "sym"], how="left", indicator=True)
    cov_v2 = float((M._merge == "both").mean())
    yr = pd.to_datetime(M.ts, unit="ms").dt.year
    cov_v2_year = {int(k): float(x) for k, x in (M._merge == "both").groupby(yr).mean().items()}
    J = S.merge(V, on=["ts", "sym"], how="inner")
    eq_all = float((J.cs.to_numpy() == J.c.to_numpy()).mean())
    rel = np.abs(J.cs.to_numpy() / J.c.to_numpy() - 1)
    out = dict(S1_n=int(len(P)), S1_eq=s1_ok, S1_pass=bool(s1_ok == len(P) == 720), S1_syms=[int(x) for x in syms],
               S2_bad_high=bad_h, S2_bad_low=bad_l, S2_pass=bool(bad_h == 0 and bad_l == 0), nan_close=nan_c,
               nan_open=nan_o, nan_high_or_low=nan_hl, cov_v2_in_store=cov_v2, cov_v2_in_store_by_year=cov_v2_year,
               store_rows_in_v2=float(len(J) / len(S)), close_eq_v2_all_joined=eq_all,
               close_rel_diff_v2_q999=float(np.quantile(rel, 0.999)), close_rel_diff_v2_max=float(rel.max()),
               n_close_ne_v2=int((J.cs.to_numpy() != J.c.to_numpy()).sum()))
    log.info("SANITY %s", json.dumps(out))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["month", "merge"])
    ap.add_argument("--months", default="all")
    ap.add_argument("--procs", type=int, default=3)
    a = ap.parse_args()
    if a.stage == "month":
        ms = MONTHS if a.months == "all" else [int(x) for x in a.months.split(",")]
        from multiprocessing import Pool
        t0 = time.time()
        if a.procs <= 1:
            for m in ms:
                month(m)
        else:
            with Pool(a.procs) as p:
                for ym, n, secs in p.imap_unordered(month, ms):
                    log.info("done %d rows %d %.0fs (tong %.0fs)", ym, n, secs, time.time() - t0)
        log.info("MONTH_ALL_DONE %.0fs", time.time() - t0)
    else:
        merge()


if __name__ == "__main__":
    main()
