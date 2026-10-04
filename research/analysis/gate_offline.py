#!/usr/bin/env python3
"""gate_offline.py -- GATE_QUOTA_DIAG (Pha D chuong trinh GATE): mo phong gate G2 (GDV2 ratio) OFFLINE.

THUAN PYTHON, 0 Java/sim/Kaggle, 0 PnL moi, DEV <= 2025-12-31. Pre-reg: docs/prereg/PREREG_GATE_QUOTA_DIAG.md.
Tai lap co che Java (doc code HEAD, jar B0 7368be46):
  - ung vien moi PHUT market (SimulatorMarketLevelTicker1MStopLoss:405-436): bins S1 15m predict_wf_*.bin,
    horizonIdx=0 (manifest wfo_ds_x1_2021) -> sp = 1f - p0, bo NaN (WfoDataset:243-249); forward-fill ra
    moi phut market neu t - moc15 <= 15' (WfoDataset.forwardFillToGrid); sort TANG sp, lay K=24 dau
    (selectCands, cap-then-skip); coin dang giu bi bo TRUOC gate (isSymbolRunning) => khong nap buffer;
    can p15 o phut do (predictionMap.get == null -> return TRUOC gate).
  - r = p15 / (max(DYN_MIN, sp/SCORE_BASE*DYN_MULT) * gs), float32 (GateRollingRatio.threshold).
  - q_h = phan vi nearest-rank k=floor(pct*(m-1)) cua r co ts in [h-90d, h), tinh o truy van dau moi gio
    (GateRatioBuffer.computeQ); warm-up (h - firstTs < 7d hoac m=0) -> q = MIN_MOMENTUM_15M = 0.008.
  - thr = (q*factor)*gs float32 (EntryGate.threshold); PASS <=> !(p15 < thr) (AIRejectFilter.evaluate).
  - Sau warm-up KHONG co san tuyet doi 0.008 cho nhanh PREDICT; "floor" duy nhat = DYN_MIN cua factor.
XAP XI (khai): (1) coin dang giu lay tu printDone cua CHINH run (PREDICT khoa (start,end); level khac [start,end));
  (2) Utils.isTickerAvailable / ticker stale khong tai lap (khong co ticker 1m offline) -> do bang seen/quy vs log;
  (3) tie sp trong 1 moc: Java quicksort khong on dinh, o day lexsort on dinh.
Stage: prep | all.   Output: docs/audit/gate_quota_diag_20261004.json
"""
import glob
import hashlib
import json
import logging
import math
import os
import re
import resource
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("gate_offline")

HOME = "/home/ubuntu"
REPO = HOME + "/src/BinanceFuturesJava"
CACHE = HOME + "/claude_master/1004/gqd"
DS = HOME + "/wfo_ds_x1_2021"
BINS = HOME + "/predwf_map_s1a2_x1_2021"
MAPF = HOME + "/selector_pred_out/symbol_map.csv"
OUTK = HOME + "/kaggle_sim/out/"
JOUT = REPO + "/docs/audit/gate_quota_diag_20261004.json"
SEEDS = {"A1": (42, DS + "/pred.bin", "n700-a1"),
         "S7": (7, HOME + "/claude_master/1004/gabl/ds_SEED7/pred.bin", "gabl-seed7")}
for _s in (13, 21, 99, 123, 777, 2024):
    SEEDS["S%d" % _s] = (_s, "%s/claude_master/1004/gsb/pred_S%d/pred.bin" % (HOME, _s), "gsb-s%d" % _s)
VAL_ARMS = ("A1", "S21", "S777")       # cong D1 (chot trong pre-reg)
K = 24
DYN_MIN, SCORE_BASE, DYN_MULT = np.float32(0.26787), np.float32(0.15), np.float32(1.28760)
GS = np.float32(1.55)
PCT = np.float32(0.999950829)
BASE = np.float32(0.008)
H, D, M15 = 3600000, 86400000, 900000
TZ = 7 * H
T0 = 1625072400000          # 2021-07-01 00:00 GMT+7 (TIME_RUN=20210701)
T1 = 1767200400000          # 2026-01-01 00:00 GMT+7 (2026 niem phong)
YEARS = (2022, 2023, 2024, 2025)
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
LOCK = HOME + "/claude_master/1002/oracle_heavy.lock"


def disk_ok(tag):
    st = os.statvfs(HOME)
    free = st.f_bavail * st.f_frsize / 2 ** 20
    log.info("df %s: free %.0f MB", tag, free)
    if free < 500:
        log.error("df < 500 MB -> DUNG")
        sys.exit(3)


def rss():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2 ** 20, 2)


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def tojs(o):
    if isinstance(o, dict):
        return {str(k): tojs(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [tojs(v) for v in o]
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else round(float(o), 6)
    if isinstance(o, np.bool_):
        return bool(o)
    return o


def prep():
    """bins 15m -> top-24 (sp tang) moi moc + luoi phut market forward-fill (cache tu tao)."""
    os.makedirs(CACHE, exist_ok=True)
    disk_ok("prep")
    fs = sorted(glob.glob(BINS + "/predict_wf_*.bin"))
    assert len(fs) == 18, len(fs)
    T, SP, SY, NC = [], [], [], []
    for f in fs:
        a = np.fromfile(f, dtype=REC)
        p0 = a["p0"].astype(np.float32)
        ok = ~np.isnan(p0)
        ts = a["ts"][ok].astype(np.int64)
        sc = (np.float32(1.0) - p0[ok]).astype(np.float32)
        sy = a["sym"][ok].astype(np.int16)
        o = np.lexsort((sc, ts))
        ts, sc, sy = ts[o], sc[o], sy[o]
        u, st = np.unique(ts, return_index=True)
        cnt = np.diff(np.append(st, len(ts)))
        grp = np.repeat(np.arange(len(u)), cnt)
        rk = np.arange(len(ts)) - st[grp]
        k = rk < K
        M = np.full((len(u), K), np.nan, np.float32)
        S = np.full((len(u), K), -1, np.int16)
        M[grp[k], rk[k]] = sc[k]
        S[grp[k], rk[k]] = sy[k]
        T.append(u); SP.append(M); SY.append(S); NC.append(cnt)
        log.info("bins %s: rec %d moc %d", os.path.basename(f), len(a), len(u))
    T15 = np.concatenate(T)
    assert np.all(np.diff(T15) > 0)
    n = int(np.fromfile(DS + "/market.bin", dtype=">i4", count=1)[0])
    mk = np.fromfile(DS + "/market.bin", offset=4,
                     dtype=np.dtype([("ts", ">i8"), ("a", ">f4"), ("b", ">f4"), ("c", ">f4")]))
    assert len(mk) == n, (len(mk), n)
    mts = mk["ts"].astype(np.int64)
    fi = np.searchsorted(T15, mts, "right") - 1
    okf = (fi >= 0) & (mts - T15[np.maximum(fi, 0)] <= M15)
    nf_utc = int((okf & (mts < 1767225600000)).sum())
    nf_gmt7 = int((okf & (mts < T1)).sum())
    log.info("forwardFill: grid %d filled %d (<2026 UTC %d, <2026 GMT+7 %d; Java log funding=2301065)",
             len(mts), int(okf.sum()), nf_utc, nf_gmt7)
    sel = okf & (mts >= T0) & (mts < T1)
    disk_ok("truoc ghi cache")
    np.savez(CACHE + "/cand_base.npz", T15=T15, SP15=np.vstack(SP), SY15=np.vstack(SY),
             NC15=np.concatenate(NC), mts=mts[sel], fi=fi[sel].astype(np.int32),
             meta=np.array([nf_utc, nf_gmt7, int(okf.sum())], np.int64))
    log.info("cache %s ok, rss %.2f GB", CACHE + "/cand_base.npz", rss())


def load_pred(path):
    n = int(np.fromfile(path, dtype=">i4", count=1)[0])
    a = np.fromfile(path, offset=4, dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("r4", ">f4")]))
    assert len(a) == n
    ts = a["ts"].astype(np.int64)
    assert np.all(np.diff(ts) > 0)
    return ts, a["p15"].astype(np.float32)


def to_ms(col):
    t = pd.to_datetime(col.astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    v = t.values.astype("datetime64[ms]").astype(np.int64) - TZ
    return np.where(t.isna().to_numpy(), np.int64(T1), v)


def load_pd(arm, s2id):
    f = OUTK + SEEDS[arm][2] + "/storage/printDone.csv"
    d = pd.read_csv(f, on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["level"] = d["level"].astype(str).str.strip()
    d["s_ms"] = to_ms(d["start"])
    d["e_ms"] = to_ms(d["end"])
    d["sid"] = d["sym"].map(s2id)
    for c in ("symbolPred", "pred15m", "profit", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    return d.reset_index(drop=True), md5f(f)


def lock_mask(ts, SY, d):
    """coin dang giu (moi level) => khong la ung vien. PREDICT khoa (start,end); level khac [start,end)."""
    L = np.zeros(SY.shape, bool)
    for sid, s, e, lv in zip(d["sid"].tolist(), d["s_ms"].tolist(), d["e_ms"].tolist(), d["level"].tolist()):
        if sid is None or (isinstance(sid, float) and math.isnan(sid)):
            continue
        a = int(np.searchsorted(ts, s, "right" if lv == "PREDICT_SYMBOL_TRADE" else "left"))
        b = int(np.searchsorted(ts, e, "left"))
        if b > a:
            L[a:b] |= SY[a:b] == int(sid)
    return L


def build(arm, B, s2id):
    pts, p15 = load_pred(SEEDS[arm][1])
    mts, fi = B["mts"], B["fi"]
    j = np.minimum(np.searchsorted(pts, mts), len(pts) - 1)
    has = pts[j] == mts
    ts = mts[has]
    p = p15[j[has]]
    f = fi[has]
    SP = B["SP15"][f]
    SY = B["SY15"][f]
    d, pmd5 = load_pd(arm, s2id)
    lock = lock_mask(ts, SY, d)
    valid = ~np.isnan(SP) & ~lock & np.isfinite(p)[:, None]
    loc = pd.to_datetime(ts + TZ, unit="ms")
    yr = loc.year.to_numpy()
    yq = (loc.year * 10 + loc.quarter).to_numpy()
    log.info("%s: phut ung vien %d (khong p15 %d), o hop le %d, khoa %d, rss %.2f GB", arm, len(ts),
             int((~has).sum()), int(valid.sum()), int(lock.sum()), rss())
    return dict(ts=ts, p15=p, SP=SP, SY=SY, valid=valid, lock=lock, d=d, pd_md5=pmd5,
                pred_md5=md5f(SEEDS[arm][1]), yr=yr, yq=yq)


class TopTree:
    """Cay doan tren GIO: moi nut giu top-J gia tri lon nhat -> phan vi duoi cao (j < J) cua cua so gio bat ky."""

    def __init__(self, hidx, vals, nH, J):
        size = 1
        while size < nH:
            size *= 2
        self.size, self.J = size, J
        T = np.full((2 * size, J), -np.inf, np.float32)
        cnt = np.bincount(hidx, minlength=nH)
        st = np.concatenate([[0], np.cumsum(cnt)])
        for h in np.nonzero(cnt)[0].tolist():
            x = vals[st[h]:st[h + 1]]
            if len(x) > J:
                x = np.partition(x, len(x) - J)[len(x) - J:]
            T[size + h, :len(x)] = x
        lv = size
        while lv > 1:
            ch = T[lv:2 * lv].reshape(lv // 2, 2 * J)
            T[lv // 2:lv] = np.partition(ch, J, axis=1)[:, J:]
            lv //= 2
        self.T = T
        self.cum = st

    def kth(self, lo, hi, j):
        """phan tu lon thu j (0-based) trong gio [lo, hi)."""
        assert j < self.J, (j, self.J)
        parts = []
        l, r = lo + self.size, hi + self.size
        while l < r:
            if l & 1:
                parts.append(self.T[l])
                l += 1
            if r & 1:
                r -= 1
                parts.append(self.T[r])
            l >>= 1
            r >>= 1
        x = np.concatenate(parts)
        return x[np.argpartition(-x, j)[j]]


def mk_tree(vals, hours, J):
    qh = np.unique(hours)
    h0 = int(qh[0])
    return TopTree((hours - h0).astype(np.int64), vals, int(qh[-1]) - h0 + 1, J), qh, h0


def hourly_q(vals, hours, first_ts, days, pct, J, ctx=None):
    """q cho moi gio CO truy van (hours sort tang, 1 phan tu / gia tri). NaN = warm-up/m=0 (fallback).
    ctx = (tree, qh, h0) dung lai cay khi chi doi pct (hieu chinh D4)."""
    tree, qh, h0 = ctx if ctx is not None else mk_tree(vals, hours, J)
    W = days * 24
    q = np.full(len(qh), np.nan, np.float32)
    jmax = 0
    for i, hh in enumerate(qh.tolist()):
        if hh * H - first_ts < 7 * D:
            continue
        hi = hh - h0
        lo = max(0, hi - W)
        m = int(tree.cum[hi] - tree.cum[lo])
        if m == 0:
            continue
        k = min(m - 1, max(0, int(math.floor(pct * (m - 1)))))
        jj = m - 1 - k
        jmax = max(jmax, jj)
        q[i] = tree.kth(lo, hi, jj)
    return q, qh, jmax


def run_g2(C, days=90, pct=PCT, J=256):
    """Gate G2 offline tren o ung vien (phut x rank). Tra P (pass), r, q theo phut, co warm-up."""
    ts, p, SP, valid = C["ts"], C["p15"], C["SP"], C["valid"]
    fac = np.maximum(DYN_MIN, (SP / SCORE_BASE) * DYN_MULT)
    r = p[:, None] / (fac * GS)
    rows, cols = np.nonzero(valid)
    vals = r[rows, cols]
    hv = (ts // H)[rows]
    first = int(ts[rows[0]])
    del rows, cols
    q, qh, jmax = hourly_q(vals, hv, first, days, float(pct), J)
    del vals, hv
    warm_h = np.isnan(q)
    qq = np.where(warm_h, BASE, q).astype(np.float32)
    idx = np.clip(np.searchsorted(qh, ts // H), 0, len(qh) - 1)
    qm = qq[idx]
    thr = (qm[:, None] * fac) * GS
    would = ~np.isnan(SP) & ~(p[:, None] < thr)
    P = valid & would
    Hw = C["lock"] & would
    log.info("G2 days=%d: pass %d, jmax %d/J %d, gio warm %d, rss %.2f GB", days, int(P.sum()), jmax, J,
             int(warm_h.sum()), rss())
    return dict(P=P, Hw=Hw, r=r, warm=warm_h[idx], qm=qm, jmax=jmax)


def simlog(tag):
    with open(OUTK + tag + "/logs/full.log", errors="ignore") as f:
        txt = f.read()
    m = re.search(r"GATE-RATIO on [^\n]*", txt)
    line = m.group(0)
    qs = {int(y) * 10 + int(qq): (int(p), int(s)) for y, qq, p, s in re.findall(r"(\d{4})Q(\d):(\d+)/(\d+)", line)}
    tot = re.search(r"seen=(\d+) pass=(\d+)", line)
    return dict(seen=int(tot.group(1)), pass_=int(tot.group(2)), q=qs)


def classify(C, P):
    """Moi lenh PREDICT cua printDone -> o (phut, rank) offline: no_minute/unmapped/not_top24/locked/nopass/pass."""
    ts, SY, SP, lock = C["ts"], C["SY"], C["SP"], C["lock"]
    d = C["d"]
    x = d[d["level"] == "PREDICT_SYMBOL_TRADE"]
    cat, ii, cc, dsp, dp = [], [], [], [], []
    for s, sid, spv, pv in zip(x["s_ms"].tolist(), x["sid"].tolist(), x["symbolPred"].tolist(), x["pred15m"].tolist()):
        i = int(np.searchsorted(ts, s))
        c, k, e1, e2 = -1, "", np.nan, np.nan
        if i >= len(ts) or ts[i] != s:
            k = "no_minute"
        elif sid is None or (isinstance(sid, float) and math.isnan(sid)):
            k = "unmapped"
        else:
            w = np.nonzero(SY[i] == int(sid))[0]
            if len(w) == 0:
                k = "not_top24"
            else:
                c = int(w[0])
                e1, e2 = abs(float(SP[i, c]) - spv), abs(float(C["p15"][i]) - pv)
                k = "locked" if lock[i, c] else ("pass" if P[i, c] else "nopass")
        cat.append(k); ii.append(i); cc.append(c); dsp.append(e1); dp.append(e2)
    x = x.assign(cat=cat, i=ii, c=cc, dsp=dsp, dp=dp)
    x["yr"] = pd.to_datetime(x["s_ms"] + TZ, unit="ms").dt.year
    return x


def qstat(v):
    v = np.asarray(v, float)
    if len(v) == 0:
        return dict(mean=None, p50=None, p90=None, max=None)
    return dict(mean=float(v.mean()), p50=float(np.percentile(v, 50)), p90=float(np.percentile(v, 90)),
                max=float(v.max()))


def d1d2(arm, C, G, sl):
    ts, yr, yq = C["ts"], C["yr"], C["yq"]
    P, valid = G["P"], C["valid"]
    x = classify(C, P)
    E = np.zeros(P.shape, bool)
    xp = x[x["cat"] == "pass"]
    E[xp["i"].to_numpy(int), xp["c"].to_numpy(int)] = True
    npm = P.sum(1)
    openm = npm > 0
    W = x[x["yr"].between(2022, 2025)]
    sim_min = set(W["s_ms"].tolist())
    off_min = set(ts[openm & (yr >= 2022) & (yr <= 2025)].tolist())
    out = dict(pred_md5=C["pred_md5"], printdone_md5=C["pd_md5"], n_predict_rows=int(len(x)),
               cat_all=x["cat"].value_counts().to_dict(), cat_2225=W["cat"].value_counts().to_dict(),
               max_abs_dsp=float(np.nanmax(x["dsp"])) if x["dsp"].notna().any() else None,
               max_abs_dp15=float(np.nanmax(x["dp"])) if x["dp"].notna().any() else None,
               recall_minute_2225=len(sim_min & off_min) / max(1, len(sim_min)),
               recall_pair_2225=float((W["cat"] == "pass").mean()),
               recall_pair_fresh_2225=float((W["cat"] == "pass").sum() / max(1, (W["cat"] != "locked").sum())),
               sim_total=dict(seen=sl["seen"], pass_=sl["pass_"]),
               off_total=dict(seen=int(valid.sum()), pass_=int(P.sum())), year={}, quarter={})
    for q in sorted(set(yq.tolist())):
        s = yq == q
        out["quarter"][q] = dict(seen_off=int(valid[s].sum()), seen_sim=sl["q"].get(q, (0, 0))[1],
                                 pass_off=int(P[s].sum()), pass_sim=sl["q"].get(q, (0, 0))[0])
    for y in YEARS:
        s = yr == y
        ss = s & openm
        Wy = x[x["yr"] == y]
        sim_m = Wy["s_ms"].nunique()
        n_pass, n_ent = int(P[s].sum()), int(E[s].sum())
        sq = [v for k, v in out["quarter"].items() if k // 10 == y]
        out["year"][y] = dict(
            sim_entry_min=int(sim_m), off_open_min=int(ss.sum()),
            ratio_min=float(ss.sum() / max(1, sim_m)),
            seen_off=int(valid[s].sum()), seen_sim=int(sum(v["seen_sim"] for v in sq)),
            pass_off=n_pass, pass_sim=int(sum(v["pass_sim"] for v in sq)),
            sim_predict_rows=int(len(Wy)), entered=n_ent, waste=n_pass - n_ent,
            waste_rate=(n_pass - n_ent) / max(1, n_pass), held_would_pass=int(G["Hw"][s].sum()),
            symmin_per_min=qstat(npm[ss]),
            frac_min_ge5=float((npm[ss] >= 5).mean()) if ss.any() else None,
            share_passes_in_top10pct_min=top_share(npm[ss]))
    return out, x, E


def top_share(c):
    """ti le symbol-phut pass nam trong 10% phut mo 'day' nhat."""
    c = np.sort(np.asarray(c))[::-1]
    if len(c) == 0 or c.sum() == 0:
        return None
    return float(c[:max(1, int(math.ceil(0.1 * len(c))))].sum() / c.sum())


def d3_rates(C, G, edges):
    """pass rate theo decile sp (o hop le, sau warm-up, 2022-2025) + theo nhom rank."""
    m = C["valid"] & ~G["warm"][:, None] & ((C["yr"] >= 2022) & (C["yr"] <= 2025))[:, None]
    sp = C["SP"][m]
    ps = G["P"][m]
    dec = np.clip(np.searchsorted(edges, sp, "right"), 0, 9)
    out = {"decile": [], "rank": []}
    for k in range(10):
        s = dec == k
        out["decile"].append(dict(d=k + 1, n=int(s.sum()), pass_=int(ps[s].sum()),
                                  rate_e5=float(ps[s].mean() * 1e5) if s.any() else None))
    rk = np.broadcast_to(np.arange(1, K + 1), C["SP"].shape)[m]
    for a, b in ((1, 3), (4, 8), (9, 16), (17, 24)):
        s = (rk >= a) & (rk <= b)
        out["rank"].append(dict(r="%d-%d" % (a, b), n=int(s.sum()), pass_=int(ps[s].sum()),
                                rate_e5=float(ps[s].mean() * 1e5) if s.any() else None))
    return out


def d3_roi(x, edges):
    """ROI/lenh that (profit % margin, pnl USD) theo decile sp cua lenh: lenh PREDICT moi (khong locked) 2022-25."""
    t = x[x["yr"].between(2022, 2025) & (x["cat"] != "locked") & x["symbolPred"].notna()].copy()
    t["dpop"] = np.clip(np.searchsorted(edges, t["symbolPred"].to_numpy(np.float32), "right"), 0, 9) + 1
    t["qt"] = pd.qcut(t["symbolPred"].rank(method="first"), 5, labels=False) + 1

    def agg(g):
        pr = g["profit"].to_numpy(float)
        se = pr.std(ddof=1) / math.sqrt(len(pr)) if len(pr) > 1 else float("nan")
        return dict(n=int(len(g)), sp_med=float(g["symbolPred"].median()), roi_mean=float(pr.mean()),
                    roi_ci95=[float(pr.mean() - 1.96 * se), float(pr.mean() + 1.96 * se)],
                    roi_med=float(np.median(pr)), win=float((pr > 0).mean()), pnl_sum=float(g["pnl"].sum()))
    out = dict(n=int(len(t)), by_pop_decile={int(k): agg(g) for k, g in t.groupby("dpop")},
               by_trade_quintile={int(k): agg(g) for k, g in t.groupby("qt")},
               spearman_sp_roi=float(t["symbolPred"].corr(t["profit"], method="spearman")),
               by_year_half={})
    med = t["symbolPred"].median()
    for y, g in t.groupby("yr"):
        lo, hi = g[g["symbolPred"] <= med], g[g["symbolPred"] > med]
        out["by_year_half"][int(y)] = dict(low_sp=agg(lo) if len(lo) > 1 else None,
                                           high_sp=agg(hi) if len(hi) > 1 else None)
    return out


def minute_inputs(C, G):
    has = C["valid"].any(1)
    rmax = np.where(C["valid"], G["r"], -np.inf).max(1).astype(np.float32)
    return has, dict(a=C["p15"][has], b=rmax[has])


def minute_quota(vals, hours, first, rho, ctx):
    """quota theo PHUT: mo phut t <=> v_t >= q_h, q_h = phan vi (1-rho) cua v trong [h-90d, h), moi gio."""
    q, qh, _ = hourly_q(vals, hours, first, 90, 1.0 - rho, None, ctx)
    qm = q[np.clip(np.searchsorted(qh, hours), 0, len(qh) - 1)]
    return ~np.isnan(qm) & ~(vals < qm), qm


def calibrate(vals, hours, first, yr_m, target, ctx):
    """ρ sao cho so phut mo 2022-25 ~ target (A1 sim). Chi DEM; bisection log-rho trong [1e-5, 2e-3]."""
    w = (yr_m >= 2022) & (yr_m <= 2025)
    lo, hi = math.log(1e-5), math.log(2e-3)
    cnt = lambda lr: int((minute_quota(vals, hours, first, math.exp(lr), ctx)[0] & w).sum())
    clo, chi = cnt(lo), cnt(hi)
    assert clo < target < chi, (clo, chi, target)
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        if cnt(mid) < target:
            lo = mid
        else:
            hi = mid
    best = min((lo, hi), key=lambda lr: abs(cnt(lr) - target))
    return math.exp(best), cnt(best)


def mech_metrics(ts, yr, openm, nsym):
    o = dict(year={})
    for y in YEARS:
        s = openm & (yr == y)
        o["year"][y] = dict(min=int(s.sum()), symmin=int(nsym[s].sum()),
                            symmin_per_min=float(nsym[s].mean()) if s.any() else None)
    o["tot2225"] = int(sum(v["min"] for v in o["year"].values()))
    w = openm & (yr >= 2022) & (yr <= 2025)
    return o, ts[w].copy(), ts[openm & (yr == 2022)].copy()


def jac(a, b):
    u = len(np.union1d(a, b))
    return len(np.intersect1d(a, b)) / u if u else None


def summarize(M, S, S22):
    """M[mech][arm] = metrics; S/S22[mech][arm] = tap phut mo (2022-25 / 2022)."""
    out = {}
    for mech, per in M.items():
        arms = list(per)
        y22 = np.array([per[a]["year"][2022]["min"] for a in arms], float)
        tot = np.array([per[a]["tot2225"] for a in arms], float)
        jj = [jac(S[mech][a], S[mech][b]) for i, a in enumerate(arms) for b in arms[i + 1:]]
        j22 = [jac(S22[mech][a], S22[mech][b]) for i, a in enumerate(arms) for b in arms[i + 1:]]
        spm = [per[a]["year"][2022]["symmin_per_min"] or 0 for a in arms]
        out[mech] = dict(min22_mean=y22.mean(), min22_sd=y22.std(ddof=1), min22_cv=y22.std(ddof=1) / y22.mean(),
                         min22_range=[y22.min(), y22.max()], tot2225_mean=tot.mean(), tot2225_sd=tot.std(ddof=1),
                         per_year_mean={y: float(np.mean([per[a]["year"][y]["min"] for a in arms])) for y in YEARS},
                         per_year_sd={y: float(np.std([per[a]["year"][y]["min"] for a in arms], ddof=1)) for y in YEARS},
                         jac2225_mean=float(np.mean(jj)), jac22_mean=float(np.mean(j22)),
                         symmin_per_min22_mean=float(np.mean(spm)), n_arms=len(arms))
    return out


CAGR22_DOC = {"A1": 36.65, "S7": 31.34, "S13": 34.10, "S21": 29.24, "S99": 38.23, "S123": 31.56,
              "S777": 39.34, "S2024": 32.98}       # RESULT_GATE_SEEDBAND.md bang 2 (doi chieu voi json)


def cagr22():
    src = "doc"
    try:
        js = json.load(open(REPO + "/docs/result/gate_seedband.json"))
        mt = js["metrics"]
        v = {a: float(mt[a]["cagr22"]) for a in CAGR22_DOC}
        assert all(abs(v[a] - CAGR22_DOC[a]) < 0.01 for a in v), v
        src = "gate_seedband.json metrics[*].cagr22 (khop bang doc)"
        return v, src
    except Exception as e:      # noqa: BLE001
        log.warning("cagr22 tu json loi (%s) -> dung bang RESULT_GATE_SEEDBAND", e)
        return dict(CAGR22_DOC), src


def corr(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return dict(pearson=float(np.corrcoef(a, b)[0, 1]),
                spearman=float(pd.Series(a).corr(pd.Series(b), method="spearman")))


def wait_lock():
    import time
    for _ in range(120):
        if not os.path.exists(LOCK):
            return
        log.info("lock %s dang co -> cho 60s", LOCK)
        time.sleep(60)
    log.error("lock khong nha sau 2h -> DUNG"); sys.exit(4)


def run_all():
    wait_lock()
    disk_ok("all")
    B = dict(np.load(CACHE + "/cand_base.npz"))
    mp = pd.read_csv(MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    R = dict(meta=dict(script="research/analysis/gate_offline.py", bins=BINS, horizonIdx=0, K=K, pct=float(PCT),
                       gs=float(GS), days=90, fill_counts=B["meta"].tolist(), n_minutes_grid=int(len(B["mts"])),
                       approx=["held tu printDone cua chinh run", "isTickerAvailable khong tai lap",
                               "tie sp: lexsort on dinh"]),
             D1={}, D2={}, D3={"rates": {}}, D4={})
    M = {m: {} for m in ("SIM", "G2off", "a_min_p15", "b_min_rmax", "c_365d")}
    S = {m: {} for m in M}
    S22 = {m: {} for m in M}
    edges, rho = None, {}
    for arm in SEEDS:
        C = build(arm, B, s2id)
        sl = simlog(SEEDS[arm][2])
        G = run_g2(C)
        o, x, _E = d1d2(arm, C, G, sl)
        R["D1"][arm] = o
        log.info("%s D1: recall phut %.4f pair %.4f cat %s | phut/nam off/sim %s", arm, o["recall_minute_2225"],
                 o["recall_pair_2225"], o["cat_2225"],
                 {y: (v["off_open_min"], v["sim_entry_min"]) for y, v in o["year"].items()})
        if edges is None:
            m = C["valid"] & ~G["warm"][:, None] & ((C["yr"] >= 2022) & (C["yr"] <= 2025))[:, None]
            edges = np.quantile(C["SP"][m], np.linspace(0.1, 0.9, 9)).astype(np.float32)
            R["D3"]["edges_sp_decile_A1"] = edges.tolist()
            R["D3"]["roi_A1"] = d3_roi(x, edges)
        R["D3"]["rates"][arm] = d3_rates(C, G, edges)
        ts, yr = C["ts"], C["yr"]
        # SIM: phut vao lenh PREDICT that (printDone)
        sm = np.unique(x["s_ms"].to_numpy(np.int64))
        smy = pd.to_datetime(sm + TZ, unit="ms").year.to_numpy()
        cnt = x.groupby("s_ms").size().reindex(sm).to_numpy()
        M["SIM"][arm], S["SIM"][arm], S22["SIM"][arm] = mech_metrics(sm, smy, np.ones(len(sm), bool), cnt)
        P = G["P"]
        M["G2off"][arm], S["G2off"][arm], S22["G2off"][arm] = mech_metrics(ts, yr, P.any(1), P.sum(1))
        has, mv = minute_inputs(C, G)
        hours = ts[has] // H
        first = int(ts[has][0])
        nval = C["valid"].sum(1)
        for mech, key in (("a_min_p15", "a"), ("b_min_rmax", "b")):
            ctx = mk_tree(mv[key], hours, 320)
            if arm == "A1":
                tgt = M["SIM"]["A1"]["tot2225"]
                rho[key], got = calibrate(mv[key], hours, first, yr[has], tgt, ctx)
                R["D4"]["calib_" + key] = dict(rho=rho[key], target_A1_sim_min_2225=tgt, got=got)
                log.info("hieu chinh %s: rho %.3e -> %d phut (target %d)", key, rho[key], got, tgt)
            om, qm = minute_quota(mv[key], hours, first, rho[key], ctx)
            del ctx
            of = np.zeros(len(ts), bool)
            of[has] = om
            if key == "a":
                ns = nval * of
            else:
                qf = np.full(len(ts), np.nan, np.float32)
                qf[has] = qm
                ns = (C["valid"] & ~(G["r"] < qf[:, None])).sum(1) * of
            M[mech][arm], S[mech][arm], S22[mech][arm] = mech_metrics(ts, yr, of, ns)
        del G
        G3 = run_g2(C, days=365, J=1024)
        M["c_365d"][arm], S["c_365d"][arm], S22["c_365d"][arm] = mech_metrics(ts, yr, G3["P"].any(1),
                                                                              G3["P"].sum(1))
        del G3, C
        log.info("%s xong: phut 2022 SIM/G2off/a/b/c = %s, rss %.2f GB", arm,
                 [M[m][arm]["year"][2022]["min"] for m in M], rss())
    R["D4"]["per_arm"] = M
    R["D4"]["summary"] = summarize(M, S, S22)
    R["D4"]["jac_sim_vs_g2off"] = {a: jac(S["SIM"][a], S["G2off"][a]) for a in SEEDS}
    cg, src = cagr22()
    arms = list(SEEDS)
    D2 = dict(cagr22=cg, cagr22_src=src, rows={})
    for a in arms:
        y = R["D1"][a]["year"]
        D2["rows"][a] = {yy: {k: y[yy][k] for k in ("pass_off", "off_open_min", "sim_entry_min", "entered", "waste",
                                                    "waste_rate", "held_would_pass", "symmin_per_min",
                                                    "frac_min_ge5", "share_passes_in_top10pct_min")} for yy in YEARS}
    c = [cg[a] for a in arms]
    g22 = lambda k: [R["D1"][a]["year"][2022][k] for a in arms]
    D2["corr_vs_cagr22"] = dict(
        off_open_min_2022=corr(g22("off_open_min"), c), sim_entry_min_2022=corr(g22("sim_entry_min"), c),
        pass_off_2022=corr(g22("pass_off"), c), waste_2022=corr(g22("waste"), c),
        waste_rate_2022=corr(g22("waste_rate"), c), entered_2022=corr(g22("entered"), c),
        symmin_per_min_2022=corr([v["mean"] for v in g22("symmin_per_min")], c))
    D2["corr_open_min_vs_pass_2022"] = corr(g22("off_open_min"), g22("pass_off"))
    D2["corr_open_min_vs_symmin_per_min_2022"] = corr(g22("off_open_min"), [v["mean"] for v in g22("symmin_per_min")])
    R["D2"] = D2
    gate = {}
    for a in VAL_ARMS:
        o = R["D1"][a]
        ok_r = o["recall_minute_2225"] >= 0.95
        ok_y = all(abs(o["year"][y]["ratio_min"] - 1) <= 0.10 for y in YEARS)
        gate[a] = dict(recall_minute=o["recall_minute_2225"], recall_ok=ok_r,
                       ratio_min={y: o["year"][y]["ratio_min"] for y in YEARS}, ratio_ok=ok_y)
    R["D1_gate"] = dict(arms=gate, PASS=all(v["recall_ok"] and v["ratio_ok"] for v in gate.values()))
    log.info("CONG D1: %s", R["D1_gate"])
    disk_ok("truoc ghi json")
    with open(JOUT, "w") as f:
        json.dump(tojs(R), f, indent=1, ensure_ascii=False)
    log.info("ghi %s md5 %s, rss %.2f GB", JOUT, md5f(JOUT), rss())


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    if st in ("prep", "both"):
        prep()
    if st in ("all", "both"):
        run_all()
