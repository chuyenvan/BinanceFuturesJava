#!/usr/bin/env python3
"""leadlag_exist.py -- PREREG_LEADLAG_EXIST (commit e0e7bd54): test TON TAI lead-lag BTC->alt, gia-only, DEV 2022-25.

H1: IC_t = Spearman cat ngang(g_perp_{i,k}(t), y_{i,h}(t)) moi gio co >= 30 coin; 4 bien the k in {1,3}h x h in {1,4}h.
    Block bootstrap theo ngay (khoi 10 ngay, NREP 2000, seed 20261013); CI no sqrt(2 ln 4) = 1,665.
V1: tai tao tay beta, g, y cho 3 (coin, t) ngau nhien (seed co dinh) tu ban ghi tho, khop 1e-6.
V2: placebo -- xao chuoi r_BTC 1h theo khoi ngay (hoan vi ngay, seed co dinh), tinh lai toan bo H1.
H2/V3: KHONG chay trong script nay -- ledger chan EXEC (legs.pkl co close_M) da bi xoa cung cache kline 1m
       (docs/result/EXEC_RESULT.md par.8); MASTER cam tu dung ledger khac.
0 sim, 0 Java, 0 Binance REST, 0 du lieu 2026 (moi du lieu dung <= 2025-12-31 23:00 UTC), 0 kho backcast.

Usage: python3 leadlag_exist.py full OUT.json      (lan cham)
       python3 leadlag_exist.py smoke OUT.json     (CHI DE DEBUG: t trong 2022-01)
"""
import hashlib
import json
import logging
import math
import statistics
import sys
import time
import warnings

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("leadlag_exist")
warnings.filterwarnings("ignore", category=RuntimeWarning)

PREREG = "e0e7bd54"
BIN = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
H = 3600000
DAY = 86400000
T_GRID0 = 1609459200000      # 2021-01-01 00:00 UTC: dau file, chi dung cho lookback (beta 30d / sigma 7d / lich su 30d)
T_EVAL0 = 1640995200000      # 2022-01-01 00:00 UTC: gio t dau tien duoc cham
T_END = 1767222000000        # 2025-12-31 23:00 UTC: moc du lieu cuoi duoc doc (ca forward); khong doc 2026
T_SMOKE1 = 1643673600000     # 2022-02-01 00:00 UTC (smoke: t < moc nay)
BTC = 1
W_BETA = 720                 # 30 ngay: r 1h co s in [t-719h, t-k] (nam tron trong [t-30d, t-k])
MIN_BETA = 500
W_SIG = 168                  # 7 ngay: r_i 1h co s in [t-167h, t] (nam tron trong [t-7d, t]), ddof=1
MIN_SIG = 120                # pre-reg khong ghi: chon >= 120/168 diem
PRE, POST = 73, 4            # universe: du close tai moi gio t-73h..t+4h (78 diem)
MIN_HIST = 720               # >= 30 ngay lich su: close dau tien <= t-720h
MIN_CS = 30
KS = (1, 3)
HS = (1, 4)
MAIN = (3, 4)
NREP, BLOCK, SEED = 2000, 10, 20261013
INFL = math.sqrt(2.0 * math.log(4.0))
STABLE = ("USDC", "FDUSD", "TUSD", "BUSD")
EXCL_FIXED = ("BTCUSDT", "ETHUSDT", "BTCDOMUSDT")
TOL_V1 = 1e-6


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def is_excluded(name):
    if name in EXCL_FIXED:
        return True
    # base stable (USDCUSDT...) va cap niem yet bang stable (xxxUSDCUSDT...). TUSDT (token T) / BUSDT (token B) KHONG bi loai.
    return any(name.endswith(b + "USDT") for b in STABLE)


def load():
    dt = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    raw = np.fromfile(BIN, dtype=dt)
    ts = raw["ts"].astype(np.int64)
    sym = raw["sym"].astype(np.int64)
    c = raw["c"].astype(np.float64)
    del raw
    meta = dict(n_rec=int(len(ts)), ts_min=int(ts.min()), ts_max=int(ts.max()),
                n_offgrid=int((ts % H != 0).sum()), n_after_end=int((ts > T_END).sum()),
                n_before_grid=int((ts < T_GRID0).sum()), n_bad_close=int((~(np.isfinite(c) & (c > 0))).sum()))
    keep = (ts % H == 0) & (ts >= T_GRID0) & (ts <= T_END) & np.isfinite(c) & (c > 0)
    ts, sym, c = ts[keep], sym[keep], c[keep]
    T = (T_END - T_GRID0) // H + 1
    N = int(sym.max()) + 1
    row = (ts - T_GRID0) // H
    key = row * N + sym
    meta["n_dup"] = int(len(key) - len(np.unique(key)))
    lp = np.full((T, N), np.nan)
    lp[row, sym] = np.log(c)
    mp = pd.read_csv(MAP)
    names = dict(zip(mp["symId"].astype(int), mp["symbol"].astype(str).str.strip()))
    excl = sorted(i for i in range(N) if i not in names or is_excluded(names[i]))
    meta.update(T=int(T), N=N, n_kept=int(len(ts)), n_map=len(names),
                excluded=[names.get(i, "?id%d" % i) for i in excl if np.isfinite(lp[:, i]).any()])
    log.info("load: %s", json.dumps({k: v for k, v in meta.items() if k != "excluded"}))
    log.info("excluded (co du lieu): %s", meta["excluded"])
    return lp, excl, names, (ts, sym, c), meta


def wsum(a, rows, lo_off, hi_off):
    """Tong a[s] voi s in [t+lo_off, t+hi_off] cho moi t in rows (a: [T, N], NaN da duoc thay 0 boi caller)."""
    cp = np.zeros((a.shape[0] + 1, a.shape[1]))
    np.cumsum(a, axis=0, out=cp[1:])
    return cp[rows + hi_off + 1] - cp[rows + lo_off]


def ret1(lpx):
    r = np.full(lpx.shape, np.nan)
    r[1:] = lpx[1:] - lpx[:-1]
    return r


def prep_common(lp, rows, excl):
    """universe (khong phu thuoc BTC) + sigma 7d."""
    T, N = lp.shape
    P = np.isfinite(lp).astype(np.float64)
    full = wsum(P, rows, -PRE, POST) >= PRE + POST + 1 - 0.5
    del P
    has = np.isfinite(lp).any(0)
    first = np.where(has, np.argmax(np.isfinite(lp), axis=0), T + 10)
    hist = first[None, :] <= (rows - MIN_HIST)[:, None]
    univ = full & hist
    univ[:, excl] = False
    R = ret1(lp)
    V = np.isfinite(R)
    y = np.where(V, R, 0.0)
    n = wsum(V.astype(np.float64), rows, -(W_SIG - 1), 0)
    s1 = wsum(y, rows, -(W_SIG - 1), 0)
    s2 = wsum(y * y, rows, -(W_SIG - 1), 0)
    del y, V
    var = (s2 - s1 * s1 / n) / (n - 1)
    sig = np.sqrt(np.maximum(var, 0.0))
    sig[(n < MIN_SIG) | ~(sig > 0)] = np.nan
    return univ, sig, R


def ic_rows(g, rev, yv, M):
    """IC_t = Spearman(phan du OLS cat ngang g ~ 1 + rev, y) cho hang co >= MIN_CS coin."""
    cnt = M.sum(1)
    use = np.flatnonzero(cnt >= MIN_CS)
    ic = np.full(len(cnt), np.nan)
    if len(use) == 0:
        return ic, cnt, 0
    Mu = M[use]
    gm = np.where(Mu, g[use], np.nan)
    rm = np.where(Mu, rev[use], np.nan)
    ym = np.where(Mu, yv[use], np.nan)
    dg = gm - np.nanmean(gm, 1)[:, None]
    dr = rm - np.nanmean(rm, 1)[:, None]
    b = np.nansum(dg * dr, 1) / np.nansum(dr * dr, 1)
    res = dg - b[:, None] * dr
    del gm, rm, dg, dr
    r1 = pd.DataFrame(res).rank(axis=1).to_numpy()
    r2 = pd.DataFrame(ym).rank(axis=1).to_numpy()
    a1 = r1 - np.nanmean(r1, 1)[:, None]
    a2 = r2 - np.nanmean(r2, 1)[:, None]
    ic[use] = np.nansum(a1 * a2, 1) / np.sqrt(np.nansum(a1 * a1, 1) * np.nansum(a2 * a2, 1))
    ncoin = int(Mu.any(0).sum())
    return ic, cnt, ncoin


def core(lp, R, lpB, rows, univ, sig, samp=False):
    """Tinh IC_t cho 4 bien the voi chuoi log-gia BTC lpB (that hoac placebo). samp -> lay 3 diem V1 moi bien the."""
    rb = ret1(lpB[:, None])[:, 0]
    out, samples = {}, {}
    for k in KS:
        V = np.isfinite(R) & np.isfinite(rb)[:, None]
        x = np.where(V, rb[:, None], 0.0)
        y = np.where(V, R, 0.0)
        n = wsum(V.astype(np.float64), rows, -(W_BETA - 1), -k)
        del V
        sx = wsum(x, rows, -(W_BETA - 1), -k)
        sy = wsum(y, rows, -(W_BETA - 1), -k)
        sxx = wsum(x * x, rows, -(W_BETA - 1), -k)
        sxy = wsum(x * y, rows, -(W_BETA - 1), -k)
        del x, y
        beta = (sxy - sx * sy / n) / (sxx - sx * sx / n)
        beta[~(n >= MIN_BETA)] = np.nan
        del sx, sy, sxx, sxy
        rik = lp[rows] - lp[rows - k]
        rbk = lpB[rows] - lpB[rows - k]
        g = (beta * rbk[:, None] - rik) / sig
        rev = -rik / sig
        del rik
        for h in HS:
            yv = (lp[rows + h] - lp[rows]) - beta * (lpB[rows + h] - lpB[rows])[:, None]
            okb = np.isfinite(rbk) & np.isfinite(lpB[rows + h] - lpB[rows])
            M = univ & np.isfinite(g) & np.isfinite(rev) & np.isfinite(yv) & okb[:, None]
            ic, cnt, ncoin = ic_rows(g, rev, yv, M)
            used = np.isfinite(ic)
            out[(k, h)] = dict(ic=ic, cnt=cnt, ncoin=ncoin, coinhours=int(cnt[used].sum()))
            if samp:
                Mu = M & used[:, None]
                flat = np.flatnonzero(Mu)
                rng = np.random.default_rng(SEED + 100 * k + h)
                pick = rng.choice(flat, size=3, replace=False)
                rr, ii = np.unravel_index(pick, Mu.shape)
                samples[(k, h)] = [dict(row=int(rows[a]), sym=int(b), beta=float(beta[a, b]), g=float(g[a, b]),
                                        y=float(yv[a, b])) for a, b in zip(rr, ii)]
            del yv, M
            log.info("  k=%d h=%d: gio dung %d, coin/gio TB %.1f, IC TB tho %.5f", k, h, int(used.sum()),
                     float(cnt[used].mean()) if used.any() else float("nan"), float(np.nanmean(ic)))
        del beta, g, rev
    return out, samples


def mbb(s, c):
    """Moving block bootstrap theo ngay (khoi BLOCK ngay) cho thong ke sum(IC)/sum(gio)."""
    D = len(s)
    m = float(s.sum() / c.sum())
    rng = np.random.default_rng(SEED)
    bl = min(BLOCK, D)
    nb = int(math.ceil(D / bl))
    st = rng.integers(0, D - bl + 1, size=(NREP, nb))
    idx = (st[:, :, None] + np.arange(bl)[None, None, :]).reshape(NREP, -1)[:, :D]
    stat = s[idx].sum(1) / np.maximum(c[idx].sum(1), 1e-12)
    sd = float(np.std(stat, ddof=1))
    plo, phi = (float(v) for v in np.percentile(stat, [2.5, 97.5]))
    r = dict(mean=m, sd=sd, lo=m - 1.96 * sd, hi=m + 1.96 * sd, plo=plo, phi=phi,
             lo_infl=m - INFL * 1.96 * sd, hi_infl=m + INFL * 1.96 * sd,
             plo_infl=m - INFL * (m - plo), phi_infl=m + INFL * (phi - m))
    r["lo_dec"] = min(r["lo_infl"], r["plo_infl"])   # can duoi quyet dinh = can bao thu hon trong 2 cach
    return r


def summarize(res, rows):
    t = T_GRID0 + rows.astype(np.int64) * H
    day = (t - T_EVAL0) // DAY
    D = int(day.max()) + 1
    yr = pd.to_datetime(T_EVAL0 + np.arange(D) * DAY, unit="ms").year.to_numpy()
    out = {}
    for (k, h), v in res.items():
        ic = v["ic"]
        ok = np.isfinite(ic)
        s = np.bincount(day[ok], weights=ic[ok], minlength=D)
        c = np.bincount(day[ok], minlength=D).astype(np.float64)
        r = dict(full=mbb(s, c), n_hours=int(ok.sum()), n_days=int((c > 0).sum()), ncoin_distinct=v["ncoin"],
                 coin_per_hour_mean=float(v["cnt"][ok].mean()) if ok.any() else None,
                 coin_per_hour_min=int(v["cnt"][ok].min()) if ok.any() else None,
                 coinhours=v["coinhours"], frac_ic_pos=float((ic[ok] > 0).mean()) if ok.any() else None, years={})
        for y in sorted(set(yr.tolist())):
            dm = yr == y
            if c[dm].sum() > 0:
                b = mbb(s[dm], c[dm])
                yh = ok & (pd.to_datetime(t, unit="ms").year.to_numpy() == y)
                b.update(n_hours=int(c[dm].sum()), coin_per_hour_mean=float(v["cnt"][yh].mean()))
                r["years"][str(y)] = b
        out["k%d_h%d" % (k, h)] = r
    return out


def hand_check(rawrec, sm, k, h):
    """V1: tinh lai beta, g, y bang vong lap Python tu ban ghi tho (khong dung luoi/cumsum)."""
    ts, sym, c = rawrec
    t0 = T_GRID0 + sm["row"] * H

    def ser(s):
        m = sym == s
        return dict(zip(ts[m].tolist(), c[m].tolist()))

    ci, cb = ser(sm["sym"]), ser(BTC)

    def lr(d, a, b):
        return math.log(d[b] / d[a]) if (a in d and b in d) else None

    xs, ys = [], []
    for j in range(W_BETA - 1, k - 1, -1):
        s = t0 - j * H
        ri, rbv = lr(ci, s - H, s), lr(cb, s - H, s)
        if ri is not None and rbv is not None:
            xs.append(rbv)
            ys.append(ri)
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    beta = sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / sum((a - mx) ** 2 for a in xs)
    rs = [lr(ci, t0 - j * H - H, t0 - j * H) for j in range(W_SIG - 1, -1, -1)]
    sig = statistics.stdev([v for v in rs if v is not None])
    g = (beta * lr(cb, t0 - k * H, t0) - lr(ci, t0 - k * H, t0)) / sig
    y = lr(ci, t0, t0 + h * H) - beta * lr(cb, t0, t0 + h * H)
    d = dict(beta=abs(beta - sm["beta"]), g=abs(g - sm["g"]), y=abs(y - sm["y"]))
    return dict(t=pd.Timestamp(t0, unit="ms").isoformat(), sym_id=sm["sym"], n_beta=len(xs),
                n_sig=sum(v is not None for v in rs), hand=dict(beta=beta, g=g, y=y),
                vec=dict(beta=sm["beta"], g=sm["g"], y=sm["y"]), absdiff=d, ok=max(d.values()) <= TOL_V1)


def placebo_btc(lpB):
    """V2: hoan vi cac ngay (24h) cua chuoi r_BTC 1h, seed co dinh, dung lai log-gia placebo."""
    rb = ret1(lpB[:, None])[:, 0]
    D = len(rb) // 24
    assert D * 24 == len(rb)
    perm = np.random.default_rng(SEED).permutation(D)
    rbp = rb.reshape(D, 24)[perm].reshape(-1)
    inc = np.nan_to_num(rbp)
    inc[0] = 0.0
    lpp = np.cumsum(inc)            # muc goc tuy y (chi dung hieu log-gia); lpB[0] = NaN vi file bat dau 01:00
    lpp[np.isnan(rbp)] = np.nan
    return lpp, perm


def decide(sm, v1ok, v2ok):
    m = sm["k%d_h%d" % MAIN]
    yrs = {y: b["mean"] for y, b in m["years"].items()}
    c1 = m["full"]["mean"] > 0
    c2 = m["full"]["lo_dec"] > 0
    c3 = sum(v > 0 for v in yrs.values()) >= 3
    h1 = bool(c1 and c2 and c3)
    if not h1:
        verdict = "DONG"
        why = "H1 bien the chinh khong dat (mean>0: %s, CI no duoi>0: %s, >=3/4 nam mean>0: %s) -> luat par.4 'nguoc lai' -> DONG, bat ke H2" % (c1, c2, c3)
    else:
        verdict = "CHUA_KET_LUAN_H2_THIEU"
        why = "H1 dat nhung GO can them H2 (Delta>+0,30%% & CI duoi>0); H2 khong chay duoc (ledger close_M da xoa)"
    if not (v1ok and v2ok):
        why += "; CANH BAO: V1=%s V2=%s" % (v1ok, v2ok)
    return dict(h1_pass=h1, c_mean_pos=bool(c1), c_lo_infl_pos=bool(c2), c_years_pos=bool(c3), years_mean=yrs,
                h2="KHONG_CHAY", verdict=verdict, why=why)


def main():
    t_start = time.time()
    mode, outp = sys.argv[1], sys.argv[2]
    assert mode in ("full", "smoke")
    lp, excl, names, rawrec, meta = load()
    T = lp.shape[0]
    rows = np.arange((T_EVAL0 - T_GRID0) // H, T - POST)
    if mode == "smoke":
        rows = rows[T_GRID0 + rows * H < T_SMOKE1]
    log.info("mode %s: %d gio t (%s .. %s)", mode, len(rows), pd.Timestamp(T_GRID0 + rows[0] * H, unit="ms"),
             pd.Timestamp(T_GRID0 + rows[-1] * H, unit="ms"))
    univ, sig, R = prep_common(lp, rows, excl)
    lpB = lp[:, BTC].copy()
    log.info("universe: coin-gio %d; that ...", int(univ.sum()))
    real, samples = core(lp, R, lpB, rows, univ, sig, samp=True)
    sm_real = summarize(real, rows)
    v1 = {}
    for kh, lst in samples.items():
        v1["k%d_h%d" % kh] = [hand_check(rawrec, s, *kh) for s in lst]
    v1ok_main = all(x["ok"] for x in v1["k%d_h%d" % MAIN])
    v1ok_all = all(x["ok"] for l in v1.values() for x in l)
    log.info("V1 main ok=%s, all ok=%s", v1ok_main, v1ok_all)
    lpp, perm = placebo_btc(lpB)
    log.info("placebo ...")
    plc, _ = core(lp, R, lpp, rows, univ, sig, samp=False)
    sm_plc = summarize(plc, rows)
    v2 = {}
    for key in sm_real:
        a, b = sm_real[key]["full"], sm_plc[key]["full"]
        small = abs(b["mean"]) < abs(a["mean"]) / 3.0
        has0 = (b["lo"] <= 0 <= b["hi"]) and (b["plo"] <= 0 <= b["phi"])
        v2[key] = dict(real_mean=a["mean"], placebo=b, ratio=abs(b["mean"]) / abs(a["mean"]) if a["mean"] else None,
                       small=bool(small), ci_has0=bool(has0), ok=bool(small or has0))
    v2ok_main = v2["k%d_h%d" % MAIN]["ok"]
    v2ok_all = all(x["ok"] for x in v2.values())
    js = dict(prereg=PREREG, mode=mode, script="research/analysis/leadlag_exist.py",
              data=dict(bin=BIN, bin_md5=md5f(BIN), map=MAP, map_md5=md5f(MAP), **meta),
              params=dict(W_BETA=W_BETA, MIN_BETA=MIN_BETA, W_SIG=W_SIG, MIN_SIG=MIN_SIG, PRE=PRE, POST=POST,
                          MIN_HIST=MIN_HIST, MIN_CS=MIN_CS, NREP=NREP, BLOCK=BLOCK, SEED=SEED, INFL=INFL,
                          eval_t0=str(pd.Timestamp(T_GRID0 + rows[0] * H, unit="ms")),
                          eval_t1=str(pd.Timestamp(T_GRID0 + rows[-1] * H, unit="ms")), n_rows=int(len(rows))),
              h1=sm_real, v1=dict(ok_main=v1ok_main, ok_all=v1ok_all, samples=v1),
              v2=dict(ok_main=v2ok_main, ok_all=v2ok_all, perm_md5=hashlib.md5(perm.tobytes()).hexdigest(),
                      variants=v2, placebo_h1=sm_plc),
              h2=dict(status="KHONG_CHAY", reason="ledger chan EXEC (legs.pkl co close_M) da bi xoa cung cache kline 1m "
                      "(EXEC_RESULT par.8); MASTER cam tu dung ledger khac"),
              v3=dict(status="KHONG_CHAY"),
              decision=decide(sm_real, v1ok_main, v2ok_all), runtime_s=round(time.time() - t_start, 1))
    with open(outp, "w") as f:
        json.dump(js, f, indent=1, sort_keys=True, default=float)
    log.info("ghi %s md5 %s; quyet dinh %s; %.0fs", outp, md5f(outp), js["decision"]["verdict"], time.time() - t_start)
    for key, r in sm_real.items():
        f_ = r["full"]
        log.info("%s mean %.5f CI [%.5f, %.5f] CI_no [%.5f, %.5f] lo_dec %.5f | nam %s", key, f_["mean"], f_["lo"],
                 f_["hi"], f_["lo_infl"], f_["hi_infl"], f_["lo_dec"],
                 {y: round(b["mean"], 5) for y, b in r["years"].items()})
        log.info("   placebo mean %.5f CI [%.5f, %.5f] ok %s", v2[key]["placebo"]["mean"], v2[key]["placebo"]["lo"],
                 v2[key]["placebo"]["hi"], v2[key]["ok"])


if __name__ == "__main__":
    main()
