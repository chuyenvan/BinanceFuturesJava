#!/usr/bin/env python3
"""NUP3 V2 — co phut W_mkt cho sim (PREREG_NUP3 §3, dinh nghia = NUP3-S0 W_mkt).

flag(t) = 1  <=>  ALT_EW 24h toi phut t-1 = expm1( sum ew_r cua bar mo luc [t-1440', t-1'] ) <= -0.08
  - t = moc MO bar 1m, UTC epoch ms (= ticker.startTime cua sim; sim in gio +07 nhung ms la UTC that).
  - ew_r = TB log-return 1m cac alt USDT-M (EDGE_ATTR), bar thieu tren luoi phut = 0 (nhu S0), cua so khong co
    bar nao hoac chua du 1440 bar luoi => khong co (0).
  - Nguon: edge_attr/index.npz (2021-07 .. 2025-12) + tsx/ho/ew_out/ew_2026.npz CHI phan >= 2026-01-01 UTC
    (giong s0.EW). HO 2026 chi de sim chay du ky; KHONG dung chon/tune.
Output (~/claude_master/nup3_wk/ds_nup3-mkt-flag): nup3_mkt_flag.csv (khoang [start_ms,end_ms) gop lien tiep),
nup3_mkt_flag_meta.json. Kiem: ts int64, bat phut, tang chat, so phut duy nhat = ky vong, tong do dai khoang = so co,
doi chieu DOC LAP (tong truc tiep tren mang tho, khong dung luoi/cumsum) tai moi bien khoang +- 1' va 5000 phut ngau nhien.
"""
import hashlib
import json
import os
import sys

import numpy as np

EW_DEV = "/home/ubuntu/claude_master/edge_attr/index.npz"
EW_HO = "/home/ubuntu/claude_master/tsx/ho/ew_out/ew_2026.npz"
OUT = "/home/ubuntu/claude_master/nup3_wk/ds_nup3-mkt-flag"
MM = 60000
WIN = 1440
THR = -0.08
T2026 = int(np.datetime64("2026-01-01T00:00", "ms").astype(np.int64))


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load():
    z, h = np.load(EW_DEV), np.load(EW_HO)
    assert z["ew_ts"].dtype == np.int64 and h["ew_ts"].dtype == np.int64
    m = h["ew_ts"] >= T2026
    t = np.concatenate([z["ew_ts"], h["ew_ts"][m]])
    r = np.concatenate([z["ew_r"], h["ew_r"][m]]).astype(np.float64)
    assert t.dtype == np.int64 and np.all(np.diff(t) > 0) and np.all(t % MM == 0)
    assert int(z["ew_ts"][-1]) < T2026 <= int(h["ew_ts"][m][0])
    assert np.all(np.isfinite(r))
    return t, r


def build(t, r):
    g0 = int(t[0])
    n = int((t[-1] - g0) // MM) + 1
    R = np.zeros(n)
    N = np.zeros(n, np.int64)
    k = (t - g0) // MM
    R[k], N[k] = r, 1
    assert int(N.sum()) == len(t)
    C = np.concatenate([[0.0], np.cumsum(R)])
    CN = np.concatenate([[0], np.cumsum(N)])
    i = np.arange(WIN, n + 1, dtype=np.int64)          # bar mo luc t; cua so = bar [i-1440, i-1]
    s = C[i] - C[i - WIN]
    cnt = CN[i] - CN[i - WIN]
    ret = np.where(cnt > 0, np.expm1(s), np.nan)
    flag = (cnt > 0) & (ret <= THR)
    tm = (g0 + i * MM).astype(np.int64)
    assert tm.dtype == np.int64 and len(np.unique(tm)) == len(tm) == n - WIN + 1
    return g0, n, tm, ret, cnt, flag


def intervals(tm, flag):
    d = np.diff(np.concatenate([[0], flag.astype(np.int8), [0]]))
    st = np.where(d == 1)[0]
    en = np.where(d == -1)[0]
    S = tm[st]
    E = tm[en - 1] + MM
    assert S.dtype == np.int64 and E.dtype == np.int64
    assert np.all(E > S) and np.all(S[1:] > E[:-1])
    assert int(((E - S) // MM).sum()) == int(flag.sum())
    return S, E


def indep_ret(t, r, q):
    """DOC LAP: tong truc tiep ew_r cua bar co ts trong [q-1440', q-1'] tren mang tho (khong luoi, khong cumsum)."""
    a = np.searchsorted(t, q - WIN * MM, "left")
    b = np.searchsorted(t, q - MM, "right")
    if b <= a:
        return np.nan
    return float(np.expm1(np.sum(r[a:b])))


def main():
    os.makedirs(OUT, exist_ok=True)
    t, r = load()
    g0, n, tm, ret, cnt, flag = build(t, r)
    S, E = intervals(tm, flag)
    # --- doi chieu doc lap: moi bien khoang +-1' + 5000 phut ngau nhien
    rng = np.random.default_rng(20261026)
    probe = np.unique(np.concatenate([S, S - MM, E - MM, E, rng.choice(tm, 5000, replace=False)]))
    probe = probe[(probe >= tm[0]) & (probe <= tm[-1])]
    pos = (probe - tm[0]) // MM
    mism, near = 0, 0
    for q, p in zip(probe, pos):
        v = indep_ret(t, r, int(q))
        f2 = bool(np.isfinite(v) and v <= THR)
        if f2 != bool(flag[p]):
            if np.isfinite(v) and abs(v - THR) < 1e-9:
                near += 1
            else:
                mism += 1
        if np.isfinite(v) and np.isfinite(ret[p]):
            assert abs(v - ret[p]) < 1e-9, (int(q), v, ret[p])
    assert mism == 0, "lech doc lap %d" % mism
    # --- doi chieu S0 (s0.EW.ret24, nguon chot cua NUP3-S0)
    sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup3_s0")
    import s0  # noqa: E402
    ew = s0.EW()
    r2, _ = ew.ret24(tm)
    f_s0 = np.isfinite(r2) & (r2 <= THR)
    n_diff_s0 = int((f_s0 != flag).sum())
    assert n_diff_s0 == 0, "lech S0 %d phut" % n_diff_s0
    # --- ghi
    csv = OUT + "/nup3_mkt_flag.csv"
    with open(csv, "w") as f:
        f.write("start_ms,end_ms\n")
        for a, b in zip(S.tolist(), E.tolist()):
            f.write("%d,%d\n" % (a, b))
    yrs = {}
    yy = (tm.astype("datetime64[ms]").astype("datetime64[Y]").astype(int) + 1970)
    for y in np.unique(yy):
        sel = yy == y
        yrs[int(y)] = dict(minutes=int(sel.sum()), flag_minutes=int(flag[sel].sum()),
                           flag_days_utc=int(len(np.unique(tm[sel & flag] // 86400000))))
    meta = dict(prereg="docs/prereg/PREREG_NUP3.md c2b4c462", definition="expm1(sum ew_r bar [t-1440',t-1']) <= -0.08",
                sources={EW_DEV: md5f(EW_DEV), EW_HO: md5f(EW_HO)}, ew_bars=int(len(t)), grid_first_ms=g0,
                grid_bars=n, first_eval_ms=int(tm[0]), last_eval_ms=int(tm[-1]), n_eval_minutes=int(len(tm)),
                n_intervals=int(len(S)), n_flag_minutes=int(flag.sum()), n_nan_minutes=int(np.isnan(ret).sum()),
                per_year=yrs, indep_probe=int(len(probe)), indep_mismatch=mism, indep_near_thr=near,
                s0_diff_minutes=n_diff_s0, csv_md5=md5f(csv), csv_bytes=os.path.getsize(csv))
    json.dump(meta, open(OUT + "/nup3_mkt_flag_meta.json", "w"), indent=1)
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main()
