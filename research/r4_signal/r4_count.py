#!/usr/bin/env python3
"""R4_SIGNAL_SCREEN buoc A (prereg docs/prereg/PREREG_R4_SIGNAL_SCREEN.md 5db738e2) §3: CHI DEM + xuat o.
- B0 / C1 SURPRISE60 / C2 NOVELTY15 / C3 pool (luat B0 pct_3 = 1,5 x B0) tren gate_offline, pred n4f-b0 8 seed.
- pct chon tren LUOI co dinh 60 diem log-deu 1-pct in [5e-6, 5e-4], muc tieu Sigma 8 seed DEV, |N/target-1|<=5% else LOAI.
- Quota nam (C1, C2): median 8 seed arm/B0 moi nam 2022..2025 in [0,85;1,15].
Output: OUT/count.json, OUT/cells.parquet (seed, ts, sid, sym, set, feature C3, sat), OUT/r4s_cells.parquet. Khong fwd/PnL."""
import json
import logging
import math
import shutil
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import gate_offline as GO  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r4count")
R3 = "/home/ubuntu/claude_master/res1109/r3_gate/"
OUT = "/home/ubuntu/claude_master/res1109/r4_signal/screen/"
SEEDS = {"S42": "a1", "S7": "s7", "S13": "s13", "S21": "s21", "S99": "s99", "S123": "s123", "S777": "s777", "S2024": "s2024"}
GO.SEEDS = {k: (int(k[1:]), R3 + "pred/pred_s%s.bin" % k[1:], "n4f-b0-" + v) for k, v in SEEDS.items()}
GO.OUTK = "/home/ubuntu/claude_master/nup4_fix/results/"
H, D, M1, J = 3600000, 86400000, 60000, 2048
T21 = 1625072400000                    # 2021-07-01 +07
YB = {2022: 1640970000000, 2023: 1672506000000, 2024: 1704042000000, 2025: 1735664400000, 2026: 1767200400000}
DEV0, DEV1 = YB[2022], YB[2026]
YRS = (2022, 2023, 2024, 2025)
PCT0 = float(np.float32(GO.PCT))
GRID = sorted({float(np.float32(1.0 - x)) for x in np.logspace(math.log10(5e-6), math.log10(5e-4), 60)})
PCTS = np.array([PCT0] + GRID, dtype=np.float64)      # index 0 = B0
TOL, QLO, QHI = 0.05, 0.85, 1.15


def guard():
    fr = int(open("/proc/meminfo").read().split("MemAvailable:")[1].split()[0]) // 1024
    du = shutil.disk_usage("/home/ubuntu")
    log.info("MemAvailable %d MB, disk free %.1f GB", fr, du.free / 1e9)
    assert fr >= 4000 and du.free >= 15e9, "DUNG: thieu RAM/dia"


def minute_feats(pts, p15, ts):
    """b60 = TB [t-60,t-1] (>=48), m60 = TB [t-59,t] (>=48), novel = p15(t) > max [t-15,t-1] (>=12)."""
    n = int((pts[-1] - pts[0]) // M1) + 1
    a = np.full(n, np.nan)
    a[(pts - pts[0]) // M1] = p15.astype(np.float64)
    s = pd.Series(a)
    sh = s.shift(1)
    b60 = sh.rolling(60, min_periods=48).mean().to_numpy()
    m60 = s.rolling(60, min_periods=48).mean().to_numpy()
    mx15 = sh.rolling(15, min_periods=12).max().to_numpy()
    i = (ts - pts[0]) // M1
    ok = (i >= 0) & (i < n)
    ii = np.clip(i, 0, n - 1)
    b, m, x, cur = b60[ii].copy(), m60[ii].copy(), mx15[ii].copy(), a[ii]
    b[~ok] = np.nan
    m[~ok] = np.nan
    x[~ok] = np.nan
    return b, m, np.isfinite(x) & (cur > x)


def multi_q(vals, hours, first):
    """q theo gio cho MOI pct trong PCTS, cung ngu nghia GO.hourly_q (jj-th lon nhat trong [h-90d, h))."""
    tree, qh, h0 = GO.mk_tree(vals, hours, J)
    W = 90 * 24
    Q = np.full((len(PCTS), len(qh)), np.nan, np.float32)
    jmax = 0
    for i, hh in enumerate(qh.tolist()):
        if hh * H - first < 7 * D:
            continue
        hi = hh - h0
        lo = max(0, hi - W)
        m = int(tree.cum[hi] - tree.cum[lo])
        if m == 0:
            continue
        k = np.minimum(m - 1, np.maximum(0, np.floor(PCTS * (m - 1)).astype(np.int64)))
        jj = m - 1 - k
        need = int(jj.max()) + 1
        assert need <= J, (need, J)
        jmax = max(jmax, need - 1)
        parts = []
        l, r = lo + tree.size, hi + tree.size
        while l < r:
            if l & 1:
                parts.append(tree.T[l])
                l += 1
            if r & 1:
                r -= 1
                parts.append(tree.T[r])
            l >>= 1
            r >>= 1
        x = np.concatenate(parts)
        top = np.sort(np.partition(x, len(x) - need)[len(x) - need:])[::-1]
        Q[:, i] = top[jj]
    del tree
    return Q, qh, jmax


def gate_cells(ts, stat, fac, valid, extra):
    """o (row, col) co the pass o pct THAP nhat (va extra); P[i_pct, o] = pass o pct do."""
    r = stat[:, None] / (fac * GO.GS)
    rows, cols = np.nonzero(valid)
    first = int(ts[rows[0]])
    Q, qh, jmax = multi_q(r[rows, cols], (ts // H)[rows], first)
    del rows, cols, r
    qq = np.where(np.isnan(Q), GO.BASE, Q).astype(np.float32)
    idx = np.clip(np.searchsorted(qh, ts // H), 0, len(qh) - 1)
    lowest = int(np.argmin(PCTS))
    thr_lo = (qq[lowest][idx][:, None] * fac) * GO.GS
    cand = valid & ~(stat[:, None] < thr_lo) & extra[:, None]
    del thr_lo
    rr, cc = np.nonzero(cand)
    thr = (qq[:, idx[rr]] * fac[rr, cc][None, :]) * GO.GS
    P = ~(stat[rr][None, :] < thr)
    return dict(rr=rr, cc=cc, P=P, q=qq[:, idx[rr]], jmax=jmax)


def year_of(t):
    y = np.zeros(len(t), int)
    for yy in YRS:
        y[(t >= YB[yy]) & (t < YB[yy + 1])] = yy
    y[(t >= T21) & (t < YB[2022])] = 2021
    return y


def main():
    guard()
    B = dict(np.load(GO.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(GO.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    id2s = {v: k + "USDT" for k, v in s2id.items()}
    cnt = {a: {} for a in ("B0r", "C1", "C2", "P3")}
    keep = {}
    for s in SEEDS:
        C = GO.build(s, B, s2id)
        pts, p15 = GO.load_pred(GO.SEEDS[s][1])
        ts, SP, SY, valid, p = C["ts"], C["SP"], C["SY"], C["valid"], C["p15"]
        fac = np.maximum(GO.DYN_MIN, (SP / GO.SCORE_BASE) * GO.DYN_MULT)
        b60, m60, novel = minute_feats(pts, p15, ts)
        u = (p.astype(np.float32) - b60.astype(np.float32)).astype(np.float32)
        yr = year_of(ts)
        g = gate_cells(ts, p, fac, valid, np.ones(len(ts), bool))
        yy, nov = yr[g["rr"]], novel[g["rr"]]
        cnt["B0r"][s] = {y: g["P"][:, yy == y].sum(1).tolist() for y in YRS}
        cnt["C2"][s] = {y: g["P"][:, nov & (yy == y)].sum(1).tolist() for y in YRS}
        cnt["P3"][s] = cnt["B0r"][s]
        v1 = valid & np.isfinite(u)[:, None]
        g1 = gate_cells(ts, u, fac, v1, p >= np.float32(0.008))
        y1 = yr[g1["rr"]]
        cnt["C1"][s] = {y: g1["P"][:, y1 == y].sum(1).tolist() for y in YRS}
        d = C["d"]
        st, en = np.sort(d["s_ms"].to_numpy(np.int64)), np.sort(d["e_ms"].to_numpy(np.int64))
        openn = np.searchsorted(st, ts, "right") - np.searchsorted(en, ts, "right")
        devm = (ts >= DEV0) & (ts < DEV1)
        sat_thr = float(np.percentile(openn[devm], 95))
        keep[s] = dict(g=g, g1=g1, ts=ts, sy_r=SY[g["rr"], g["cc"]], sy_u=SY[g1["rr"], g1["cc"]], p15=p, u=u, m60=m60,
                       novel=novel, fac_r=fac[g["rr"], g["cc"]], openn=openn, sat=openn >= sat_thr, sat_thr=sat_thr)
        log.info("%s: r cand %d jmax %d | u cand %d jmax %d | B0 DEV %s | sat_thr %.0f", s, len(g["rr"]), g["jmax"],
                 len(g1["rr"]), g1["jmax"], [cnt["B0r"][s][y][0] for y in YRS], sat_thr)
        del C, SP, SY, valid, fac, v1
    json.dump(dict(pcts=PCTS.tolist(), cnt=cnt), open(OUT + "count_raw.json", "w"))
    T = sum(cnt["B0r"][s][y][0] for s in SEEDS for y in YRS)
    res = dict(prereg="5db738e2", T_B0=T, grid_n=len(GRID), b0_by_seed={s: [cnt["B0r"][s][y][0] for y in YRS] for s in SEEDS}, arms={})
    for a, tgt in (("C1", T), ("C2", T), ("P3", 1.5 * T)):
        tot = np.array([sum(cnt[a][s][y][i] for s in SEEDS for y in YRS) for i in range(len(PCTS))])
        i = min(range(1, len(PCTS)), key=lambda j: abs(tot[j] / tgt - 1))
        ok = abs(tot[i] / tgt - 1) <= TOL
        qy = {y: float(np.median([cnt[a][s][y][i] / max(cnt["B0r"][s][y][0], 1) for s in SEEDS])) for y in YRS}
        ent = dict(idx=int(i), pct=float(PCTS[i]), pct_str="%.9f" % PCTS[i], N=int(tot[i]), target=float(tgt),
                   ratio=round(float(tot[i] / tgt), 4), iso_ok=bool(ok), quota_year_med=qy)
        if a in ("C1", "C2"):
            ent["quota_ok"] = bool(all(QLO <= v <= QHI for v in qy.values()))
            ent["LOAI"] = bool(not (ok and ent["quota_ok"]))
        else:
            ent["LOAI"] = bool(not ok)
        res["arms"][a] = ent
        log.info("%s %s", a, ent)
    res["sat_thr"] = {s: keep[s]["sat_thr"] for s in SEEDS}
    json.dump(res, open(OUT + "count.json", "w"), indent=1)
    iC1, iC2, iP3 = (res["arms"][a]["idx"] for a in ("C1", "C2", "P3"))
    rows = []
    for s, K in keep.items():
        g, g1, ts = K["g"], K["g1"], K["ts"]
        tr = ts[g["rr"]]

        def emit(name, rr, sy, m, lo, extra=None):
            t = ts[rr]
            mm = m & (t >= lo) & (t < DEV1)
            df = pd.DataFrame(dict(seed=s, ts=t[mm], sid=sy[mm].astype(int), set=name, sat=K["sat"][rr][mm], nopen=K["openn"][rr][mm]))
            for k, v in (extra or {}).items():
                df[k] = v[mm]
            return df
        rows.append(emit("B0", g["rr"], K["sy_r"], g["P"][0], DEV0))
        rows.append(emit("C2", g["rr"], K["sy_r"], g["P"][iC2] & K["novel"][g["rr"]], DEV0))
        rows.append(emit("C1", g1["rr"], K["sy_u"], g1["P"][iC1], DEV0))
        m3 = g["P"][iP3] & (tr >= T21) & (tr < DEV1)
        pm = np.unique(tr[m3])
        gap = np.r_[True, np.diff(pm) > 60 * M1]
        epstart = pm[np.maximum.accumulate(np.where(gap, np.arange(len(pm)), 0))]
        j = np.clip(np.searchsorted(pm, tr, "right") - 1, 0, len(pm) - 1)
        tsince = np.where(pm[j] <= tr, (tr - epstart[j]) / M1, np.nan)
        ct = np.sort(tr[m3])
        n60 = np.searchsorted(ct, tr, "left") - np.searchsorted(ct, tr - 60 * M1, "left")
        r_cell = (K["p15"][g["rr"]] / (K["fac_r"] * GO.GS)).astype(np.float32)
        ex = dict(f_rq=r_cell / g["q"][iP3], f_u=K["u"][g["rr"]], f_m60=K["m60"][g["rr"]].astype(np.float32), f_tsince=tsince,
                  f_n60=n60, f_rank=g["cc"] + 1, f_lopen=np.log1p(K["openn"][g["rr"]]))
        rows.append(emit("P3", g["rr"], K["sy_r"], m3, T21, ex))
    A = pd.concat(rows, ignore_index=True)
    A["sym"] = A.sid.map(id2s)
    A["year"] = year_of(A.ts.to_numpy())
    A.to_parquet(OUT + "cells.parquet", index=False)
    log.info("cells %s unmapped %d", A.groupby("set").size().to_dict(), int(A.sym.isna().sum()))
    U = A[["ts", "sym"]].drop_duplicates()
    U.to_parquet(OUT + "r4s_cells.parquet", index=False)
    log.info("unique (ts,sym) %d -> r4s_cells.parquet", len(U))


if __name__ == "__main__":
    main()
