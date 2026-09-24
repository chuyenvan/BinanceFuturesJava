#!/usr/bin/env python3
"""PRESCREEN Stage 0 — TINH feature nhom B (regime thi truong) tu B_C.npy (luoi GIO, 627 coin).
Pre-reg: docs/prereg/PREREG_PRESCREEN_FEAT.md. Ra: /tmp/prefeat/B.parquet (day_ms, <feature>).
volRegime dung quantile TRUOT 365 ngay (KHONG expanding).
"""
import os, sys, time, logging
import numpy as np, pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("mkB")
OUT = "/tmp/prefeat"
K0 = int(pd.Timestamp("2021-12-31 00:00", tz="UTC").value // 3_600_000_000_000)
K1 = int(pd.Timestamp("2024-07-01 00:00", tz="UTC").value // 3_600_000_000_000)
W = 168
MINP = 84


def pre(x):
    return np.concatenate([np.zeros((x.shape[0], 1)), np.cumsum(x, axis=1)], axis=1)


def main():
    t0 = time.time()
    C = np.load(os.path.join(OUT, "B_C.npy")).astype(np.float64)
    syms = open(os.path.join(OUT, "B_syms.txt")).read().split("\n")
    n, nh = C.shape
    R = np.log(C[:, 1:] / C[:, :-1])            # R[j] = return cua gio (j+1)
    log.info("C=%s R=%s (%.0fs)", C.shape, R.shape, time.time() - t0)
    valid = ~np.isnan(R)
    X = np.where(valid, R, 0.0)
    p_cs, p_cs2, p_cnt = pre(X), pre(X * X), pre(valid.astype(np.float64))
    jends = np.arange(W, R.shape[1] + 1)        # j_end = chi so R cuoi cua cua so
    sl = slice(None)
    k = jends
    cnt = p_cnt[:, k] - p_cnt[:, k - W]
    s1 = p_cs[:, k] - p_cs[:, k - W]
    s2 = p_cs2[:, k] - p_cs2[:, k - W]
    sd = np.where(cnt >= MINP, np.sqrt(np.maximum(s2 - s1 * s1 / np.maximum(cnt, 1), 0) / np.maximum(cnt - 1, 1)), np.nan)
    # j_end -> hour index (C index) = j_end ; day = (K0 + j_end)//24 ; gio cuoi ngay: K0+j_end ≡ 23 (mod 24)
    hour = K0 + jends
    isdayend = (hour % 24) == 23
    mrv = np.nanmedian(sd[:, isdayend], axis=0)          # mktRealizedVol7D theo ngay
    dayhour = hour[isdayend]
    days = dayhour // 24
    # --- corr voi BTC, cua so 168 gio, tai cac gio cuoi ngay ---
    ib = syms.index("BTCUSDT")
    Rb = R[ib]; vb = valid[ib]
    sel = np.where(isdayend)[0]
    corr_mat = np.full((n, len(sel)), np.nan)
    for i in range(n):
        inter = valid[i] & vb
        Z = np.where(inter, R[i] * Rb, 0.0)
        z_cs = np.concatenate([[0.0], np.cumsum(Z)])
        bi_cs = np.concatenate([[0.0], np.cumsum(np.where(inter, R[i], 0.0))])
        bb_cs = np.concatenate([[0.0], np.cumsum(np.where(inter, Rb, 0.0))])
        bq_cs = np.concatenate([[0.0], np.cumsum(np.where(inter, R[i] ** 2, 0.0))])
        bq2_cs = np.concatenate([[0.0], np.cumsum(np.where(inter, Rb ** 2, 0.0))])
        cc = np.concatenate([[0.0], np.cumsum(inter.astype(np.float64))])
        j = sel + 1                                  # j_end (R idx) -> prefix index
        lo = j - W
        nn = cc[j] - cc[lo]
        sxy = z_cs[j] - z_cs[lo]; sx = bi_cs[j] - bi_cs[lo]; sy = bb_cs[j] - bb_cs[lo]
        sxx = bq_cs[j] - bq_cs[lo]; syy = bq2_cs[j] - bq2_cs[lo]
        with np.errstate(invalid="ignore", divide="ignore"):
            cov = sxy - sx * sy / np.maximum(nn, 1)
            vx = sxx - sx * sx / np.maximum(nn, 1)
            vy = syy - sy * sy / np.maximum(nn, 1)
            r = cov / np.sqrt(vx * vy)
        r[nn < MINP] = np.nan
        corr_mat[i] = r
        if i % 100 == 0:
            log.info(" corr %d/%d (%.0fs)", i, n, time.time() - t0)
    acorr = np.nanmean(corr_mat, axis=0)
    log.info("corr done (%.0fs)", time.time() - t0)
    # --- daily ---
    D_C = C[:, 23::24]
    ndays = D_C.shape[1]
    dnum = K0 // 24 + np.arange(ndays)
    log.info("ndays=%d mrv=%d acorr=%d", ndays, len(mrv), len(acorr))
    # can khop do dai: mrv/acorr theo ngay (dayhour//24) -> map
    mrv_s = pd.Series(mrv, index=days)
    corr_s = pd.Series(acorr, index=days)
    dz = pd.Index(dnum)
    mrv_d = mrv_s.reindex(dz)
    corr_d = corr_s.reindex(dz)
    dclose = pd.DataFrame(D_C.T, index=dnum)          # rows = NGAY, cols = coin
    ma7 = dclose.rolling(7, min_periods=7).mean()
    ret7 = dclose / dclose.shift(7) - 1.0
    msk = dclose.notna() & ma7.notna()
    breadth = ((dclose > ma7) & msk).sum(axis=1) / msk.sum(axis=1).replace(0, np.nan)
    r7m = ret7.notna()
    altb = ((ret7 > 0) & r7m).sum(axis=1) / r7m.sum(axis=1).replace(0, np.nan)
    disp = ret7.std(axis=1, ddof=1)
    bc = dclose.iloc[:, ib]
    bm7 = (bc / bc.shift(7) - 1.0); bm30 = (bc / bc.shift(30) - 1.0)
    vv = mrv_d.values
    vr = np.full(len(vv), np.nan)
    for i in range(len(vv)):
        if np.isnan(vv[i]):
            continue
        w = vv[max(0, i - 365):i + 1]
        w = w[~np.isnan(w)]
        if len(w) >= 200:
            vr[i] = (w <= vv[i]).mean()
    B = pd.DataFrame({
        "day_ms": [int((d * 24 + 23) * 3600000) for d in dnum],
        "btcMom7d": bm7.values, "btcMom30d": bm30.values,
        "marketBreadth7D": breadth.values, "mktRealizedVol7D": mrv_d.values,
        "volRegime": vr, "dispersion7D": disp.values,
        "avgCorrToBtc7D": corr_d.values, "altBreadthMom7D": altb.values,
    })
    B = B[B.day_ms >= int(pd.Timestamp("2022-01-01", tz="UTC").value // 10 ** 6)].reset_index(drop=True)
    B.to_parquet(os.path.join(OUT, "B.parquet"), index=False)
    log.info("WROTE B.parquet rows=%d (%.0fs)", len(B), time.time() - t0)
    log.info("\n%s", B.describe().T.to_string())


if __name__ == "__main__":
    main()
