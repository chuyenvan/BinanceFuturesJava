#!/usr/bin/env python3
"""qsleeve_q1.py -- QS1: quiet sleeve dang GIO, danh gia OFFLINE (pre-reg docs/prereg/PREREG_QS1.md, 3b69309e).

1 cau hinh chot truoc, khong tune. 0 sim, 0 Kaggle, 0 Java, 0 cham 242/shadow. DEV 2022-01-01..2025-12-31 +07,
bar >= 2026-01-01 +07 bi cat (chan chua thoat = cut o close cuoi). KHONG mo ~/kaggle_sim/out/nsel-* (khong doc
printDone nao: nen lay tu cache QS0 path.pkl). Proxy thoat = qsleeve_q0 (seg/trail), viet lai vector hoa theo coin.

DIEN GIAI KHAI TRUOC (chot trong code TRUOC khi chay, cho cac cho pre-reg khong noi ro):
  E1 gate core offline = gate_offline.run_g2 (K24, pct 0.999950829, 90 ngay) tren o top-24 hop le, lock = 0
     (khong dung vi the he chinh). Phut pass = >=1 o pass. Phut yen t <=> pass cuoi cung < t cach t > 24h.
  E2 R(t) = max r o hop le top-24 (float32 nhu gate_offline). Q(t) = phan vi nearest-rank 0.9995 cua R tren phut
     yen (R huu han) ngay UTC [u-90, u-1], u = ngay UTC cua t, cap nhat 1 lan/ngay (nhu QS0). ">= 30 ngay phut yen
     tich luy" = so phut yen trong cua so >= 30*1440; thieu => khong co Q, khong kich hoat.
  E3 kich hoat = phut yen & co Q & R >= Q & t trong DEV; hoi chieu 6h tinh tu kich hoat truoc (ke ca kich hoat bi
     bo do tran 5 hoac khong co coin hop le).
  E4 gio: duyet o top-24 theo rank (r khong tang theo rank; tie do san DYN_MIN giu thu tu rank); loai o NaN, coin
     khong co nen 1m tai phut quyet dinh, volume quote nen quyet dinh < 100000 USDT, coin da VAO (gio duoc mo)
     trong 24h truoc; lay 5 coin dau. < 5 coin => gio it chan (notional gio chia deu so chan thuc); 0 coin => khong
     gio. Coin cua gio bi bo do tran KHONG tinh la da vao.
  E5 tran 5: gio mo tu t0 den chan cuoi thoat (dong neu exit_t <= t); >= 5 gio mo => bo, dem.
  E6 ROI gio = TB ROI chan (% notional): net = gross - 0.1116%; stress = net - 1.675pp neu nen quyet dinh
     close/open-1 <= -1%.
  E7 MTM ngay: chan danh dau o close hop le cuoi <= 16:59 UTC (= 23:59 +07); ngay thoat = (px-mark)/E - phi; stress
     tru 1.675% vao ngay vao. r_sleeve = sum gio 0.2 * TB inc chan (von sleeve co dinh, khong lai kep). Nen = equity
     ngay MTM QS0 (path.pkl: 35000 + PnL dong + unP chan mo, phi goc). Stress nen = gkf_rescore post-hoc: moi chan
     printDone (moi level) vao tu 2022-01-01 +07 co nen quyet dinh (phut vao) close/open-1 <= -1% => equity tru
     1.675% x notional tu luc vao. Ghep r = 0.9 r_nen + 0.1 r_sleeve, equity lai kep ngay (can bang lai hang ngay);
     Calmar = CAGR / maxDD equity ngay 2022-25.
  E8 doi chung: pool = 1700 phut ngau nhien/thang local tu luoi phut DEV (RNG 20261008); moi seed giu phut yen
     cua seed (=> deu tren phut yen). Moi lan boc, moi thang lay min(4 n_m, pool) phut (n_m = so gio sleeve duoc mo
     cua seed trong thang), chay CUNG ham greedy (6h / coin 24h / gio 5 / vol / tran 5), roi boc n_m gio trong so
     gio duoc mo cua thang (thieu => lay het, dem). p = ti le lan boc co ROI stress TB gop 8 seed >= sleeve gop.
  E9 bootstrap L1: cum = ngay local vao gio, gop 8 seed, 2000 lan, RNG 20261008; 1 cau hinh => khong inflate.
  E10 tu kiem phut yen vs QS0 (tuoi leg0 nen >= 24h): chi so chinh = Jaccard tren phut DEV; bao them 2 ti le dieu
     kien va ti le dong y. Tu kiem proxy: tai lap ROI net o K24/0.9995 cua QS0 (1,514%) trong +-0,05pp.
Stage: sig | path | eval | all.   Output: docs/result/QS1_RESULT.{md,json}
"""
import gzip
import json
import logging
import math
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HOME = "/home/ubuntu"
REPO = HOME + "/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import gate_offline as GO  # noqa: E402
import jbin  # noqa: E402
import qsleeve_q0 as Q0  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("qs1")

W = HOME + "/claude_master/1008/qs1"
W0 = Q0.W
TICK, LOCK = Q0.TICK, Q0.LOCK
JSON_OUT = REPO + "/docs/result/QS1_RESULT.json"
MD_OUT = REPO + "/docs/result/QS1_RESULT.md"
SEEDS = list(Q0.SEEDS)
H, D, MN, TZ = Q0.H, Q0.D, Q0.MN, Q0.TZ
T22, T26 = Q0.T22, Q0.T26
MS0 = (T22 // D) * D                        # 2021-12-31 00:00 UTC
NM = (T26 - MS0) // MN
U0D, U1D = T22 // D, (T26 - 1) // D         # ngay u: danh dau 16:59 UTC = 23:59 +07 ngay local u
K, PQ, QDAYS, MINQ, JQ = 24, 0.9995, 90, 30 * 1440, 512
NB, VMIN, COOL, COIN, CAPB = 5, 100000.0, 6 * H, 24 * H, 5
SLV, BSZ = 0.10, 0.20
NDRAW, POOLM, OVS, NBOOT, RNG = 1000, 1700, 4, 2000, 20261008
COST, PEN, CRASH = Q0.COST, Q0.PEN, Q0.CRASH
ARM32, GAP32, STEP32 = np.float32(Q0.ARM), np.float32(Q0.GAP), np.float32(Q0.STEP)
YEARS = Q0.YEARS
LV, WC, CH = 14, 256, 20000
TSM = Q0.TSTOP * 60                         # 168h (phut)
QS0_REF = 1.514264                          # QS0 json q4["24|0.9995"].roi_net.mean


def lday(t):
    return (np.asarray(t, np.int64) + TZ) // D


def lmonth(t):
    x = pd.to_datetime(np.asarray(t, np.int64) + TZ, unit="ms")
    return (x.year * 100 + x.month).to_numpy()


def lyear(t):
    return pd.to_datetime(np.asarray(t, np.int64) + TZ, unit="ms").year.to_numpy()


def take_lock(name):
    t0 = time.time()
    while os.path.exists(LOCK):
        if time.time() - t0 > 4 * 3600:
            raise SystemExit("lock khong nha sau 4h")
        log.info("lock dang giu boi %s -> cho 60s", open(LOCK).read().strip())
        time.sleep(60)
    with open(LOCK, "w") as f:
        f.write(name + " %d\n" % os.getpid())


def drop_lock():
    if os.path.exists(LOCK) and open(LOCK).read().startswith("qs1"):
        os.remove(LOCK)


# ---------------------------------------------------------------- sig: phut yen, R, Q, kich hoat, pool doi chung
def load_seed(seed, B):
    pts, p15 = GO.load_pred(GO.SEEDS[seed][1])
    mts, fi = B["mts"], B["fi"]
    j = np.minimum(np.searchsorted(pts, mts), len(pts) - 1)
    has = pts[j] == mts
    ts, p, f = mts[has], p15[j[has]], fi[has]
    SP, SY = B["SP15"][f, :K], B["SY15"][f, :K]
    valid = ~np.isnan(SP) & np.isfinite(p)[:, None]
    fac = np.maximum(GO.DYN_MIN, (SP / GO.SCORE_BASE) * GO.DYN_MULT)
    r = (p[:, None] / (fac * GO.GS)).astype(np.float32)
    return ts, p, SP, SY, valid, r


def qday(R, quiet, ts):
    """Q theo ngay UTC u = phan vi nearest-rank PQ cua R tren phut yen ngay [u-90, u-1]; m < MINQ => khong co."""
    du = ts // D
    uu, st = np.unique(du, return_index=True)
    en = np.append(st[1:], len(du))
    qv = quiet & np.isfinite(R)
    cnt, tops = {}, {}
    for u, a, b in zip(uu.tolist(), st.tolist(), en.tolist()):
        v = R[a:b][qv[a:b]]
        cnt[u] = len(v)
        tops[u] = v if len(v) <= JQ else np.partition(v, len(v) - JQ)[len(v) - JQ:]
    Q, jmax = {}, 0
    for u in uu.tolist():
        win = [w for w in range(u - QDAYS, u) if cnt.get(w, 0) > 0]
        m = sum(cnt[w] for w in win)
        if m < MINQ:
            continue
        x = np.concatenate([tops[w] for w in win])
        jj = m - 1 - int(math.floor(PQ * (m - 1)))
        assert jj < JQ, (jj, JQ)
        jmax = max(jmax, jj)
        Q[u] = float(np.partition(x, len(x) - 1 - jj)[len(x) - 1 - jj])
    return Q, jmax


def q_brute(R, quiet, ts, u):
    w = (ts >= (u - QDAYS) * D) & (ts < u * D) & quiet & np.isfinite(R)
    v = np.sort(R[w])
    return None if len(v) < MINQ else float(v[int(math.floor(PQ * (len(v) - 1)))])


def stage_sig():
    B = dict(np.load(W0 + "/cand_base.npz"))
    s2id, id2s = Q0.s2id_map()
    P = pd.read_pickle(W0 + "/path.pkl")
    legs = P["legs"]
    rng = np.random.default_rng(RNG)
    mts, fi = B["mts"], B["fi"]
    md = mts[(mts >= T22) & (mts < T26)]
    mo = lmonth(md)
    pool = np.concatenate([np.sort(rng.choice(md[mo == m], size=min(POOLM, int((mo == m).sum())), replace=False))
                           for m in np.unique(mo)])
    assert np.all(np.diff(pool) > 0)
    out = dict(pool=pool, seed={})
    for seed in SEEDS:
        t0 = time.time()
        ts, p, SP, SY, valid, r = load_seed(seed, B)
        G = GO.run_g2(dict(ts=ts, p15=p, SP=SP, valid=valid, lock=np.zeros_like(valid)))
        pm, qm = G["P"].any(1), G["qm"]
        del G
        PT = ts[pm]
        j = np.searchsorted(PT, ts, "left") - 1
        lastp = np.where(j >= 0, PT[np.maximum(j, 0)], np.int64(-10 ** 15))
        assert (lastp < ts).all()                                    # chi dung pass TRUOC t
        quiet = (ts - lastp) > 24 * H
        R = np.where(valid, r, -np.inf).max(1)
        del r
        Qd, jmax = qday(R, quiet, ts)
        du = ts // D
        d0 = int(du.min())
        ua = np.full(int(du.max()) - d0 + 1, np.nan)
        for u, q in Qd.items():
            ua[u - d0] = q
        Qm = ua[du - d0]
        dev = (ts >= T22) & (ts < T26)
        cm = quiet & np.isfinite(Qm) & dev & (R >= Qm.astype(np.float32))
        trig, last = [], -10 ** 18
        for i in np.flatnonzero(cm).tolist():
            if int(ts[i]) - last >= COOL:
                trig.append(i)
                last = int(ts[i])
        trig = np.array(trig, np.int64)
        # tu kiem khong lookahead: Q(ngay u) tinh lai brute-force CHI tu phut ts < u*D <= t kich hoat
        tdays = np.unique(du[trig])
        nchk = 0
        for u in rng.choice(tdays, size=min(40, len(tdays)), replace=False).tolist():
            qb = q_brute(R, quiet, ts, u)
            assert qb is not None and qb == Qd[u], (seed, u, qb, Qd.get(u))
            assert u * D <= ts[trig][du[trig] == u].min()
            nchk += 1
        lg = legs[legs["seed"] == seed]
        l0 = np.sort(lg.loc[lg["leg0"], "s_ms"].to_numpy())
        k = np.searchsorted(l0, ts, "right") - 1
        age = np.where(k >= 0, (ts - l0[np.maximum(k, 0)]) / H, np.inf)
        A, Bq = quiet[dev], (age >= 24)[dev]
        ov = dict(n=int(dev.sum()), share_new=float(A.mean()), share_qs0=float(Bq.mean()),
                  jaccard=float((A & Bq).sum() / (A | Bq).sum()), new_in_qs0=float((A & Bq).sum() / A.sum()),
                  qs0_in_new=float((A & Bq).sum() / Bq.sum()), agree=float((A == Bq).mean()))
        yr = lyear(ts)
        ys = {}
        for y in YEARS:
            w = dev & (yr == y)
            ys[y] = dict(quiet=float(quiet[w].mean()), pass_min=int(pm[w].sum()), n_cross=int(cm[w].sum()),
                         n_trig=int((yr[trig] == y).sum()),
                         q_over_qcore_p50=float(np.nanmedian((Qm / qm)[w & quiet])))
        pi = np.minimum(np.searchsorted(ts, pool), len(ts) - 1)
        pok = (ts[pi] == pool) & quiet[pi] & valid[pi].any(1)
        out["seed"][seed] = dict(trig_ts=ts[trig], trig_SY=SY[trig], trig_valid=valid[trig], trig_R=R[trig],
                                 trig_Q=Qm[trig], trig_qcore=qm[trig], pool_ok=pok, overlap=ov, year=ys,
                                 jmax=jmax, n_qdays=len(Qd), first_q=min(Qd) if Qd else None, q_brute_ok=nchk)
        log.info("%s: yen DEV %.3f, jaccard QS0 %.3f, kich hoat %d (%s), jmax %d, %.0fs", seed, ov["share_new"],
                 ov["jaccard"], len(trig), {y: ys[y]["n_trig"] for y in YEARS}, jmax, time.time() - t0)
        del ts, p, SP, SY, valid, R, quiet, Qm, cm, age, pm, qm

    def rows(tt):
        i = np.searchsorted(mts, tt)
        assert (mts[i] == tt).all()
        return B["SY15"][fi[i], :K], B["SP15"][fi[i], :K]
    tt = np.unique(np.concatenate([pool] + [out["seed"][s]["trig_ts"] for s in SEEDS]))
    SYu, SPu = rows(tt)
    ii, cc = np.nonzero(~np.isnan(SPu))
    U = pd.DataFrame(dict(sym=[id2s.get(int(x), "?") for x in SYu[ii, cc].tolist()], t0=tt[ii]))
    c0 = P["cand"]
    c0 = c0[(c0["K"] == 24) & (c0["pct"] == 0.9995)]
    U = pd.concat([U, c0[["sym", "ts"]].rename(columns={"ts": "t0"})]).drop_duplicates(ignore_index=True)
    out["n_unknown_sym"] = int((U["sym"] == "?").sum())
    out["U"] = U[U["sym"] != "?"].reset_index(drop=True)
    bl = legs[(legs["s_ms"] >= T22) & (legs["s_ms"] < T26)]
    out["basept"] = bl[["sym", "s_ms"]].drop_duplicates().rename(columns={"s_ms": "t0"}).reset_index(drop=True)
    out["pool_SY"], out["pool_SP"] = rows(pool)
    pd.to_pickle(out, W + "/sig.pkl")
    log.info("SIG xong: pool %d phut, chan vu tru %d, coin %d, coin la %d", len(pool), len(out["U"]),
             out["U"]["sym"].nunique(), out["n_unknown_sym"])


# ---------------------------------------------------------------- path: proxy thoat (vector hoa theo coin)
def parse_day2(args):
    """1 ngay ticker UTC -> nen dac (4,1440,nb) cho lo coin bs + tra cuu diem (O,C,V) theo req {psym: phut}."""
    day, bs, req = args
    p = TICK + "/ticker_%s.bin.gz" % day
    if not os.path.exists(p):
        return day, None, None
    U0 = int(pd.Timestamp(day).value // 10 ** 6)
    with gzip.open(p, "rb") as f:
        b = f.read()
    bix = {s: j for j, s in enumerate(bs)}
    req = req or {}
    pos = {s: {m: i for i, m in enumerate(v.tolist())} for s, v in req.items()}
    pts = {s: np.full((len(v), 3), np.nan) for s, v in req.items()}
    Rr, Cc, X = [], [], []
    for k, v in jbin.iter_minutes(b):
        mi = (k - U0) // MN
        if mi < 0 or mi >= 1440 or k >= T26:
            continue
        for s, t in v.items():
            j = bix.get(s)
            if j is not None:
                Rr.append(mi)
                Cc.append(j)
                X.append(t)
            ps = pos.get(s)
            if ps is not None:
                i = ps.get(mi)
                if i is not None:
                    pts[s][i] = (t[4], t[3], t[5])         # tuple jbin = (start, max, min, close, open, vol)
    A = np.full((4, 1440, max(1, len(bs))), np.nan, np.float32)
    if Rr:
        Rr, Cc, X = np.array(Rr), np.array(Cc), np.array(X, np.float64)
        for jj, src in enumerate((4, 1, 2, 3)):               # O, H, L, C
            A[jj, Rr, Cc] = X[:, src]
    return day, A, pts


def sparse(a, levels, fn):
    S = [a]
    while len(S) < levels and (1 << len(S)) <= len(a):
        half = 1 << (len(S) - 1)
        S.append(fn(S[-1][:-half], S[-1][half:]))
    return S


def first_gt(S, start, thr, n):
    """chi so dau tien p >= start co a[p] > thr (nhay nhi phan tren bang thua max; tam <= 2^len(S) - 1)."""
    p = start.copy()
    for k in range(len(S) - 1, -1, -1):
        L = 1 << k
        can = p + L <= n
        blk = S[k][np.where(can, p, 0)]
        p = np.where(can & (blk <= thr), p + L, p)
    return p


def rmin(S, a, b):
    k = np.floor(np.log2(b - a + 1)).astype(np.int64)
    out = np.empty(len(a), np.float64)
    for kk in np.unique(k).tolist():
        m = k == kk
        out[m] = np.minimum(S[kk][a[m]], S[kk][b[m] - (1 << kk) + 1])
    return out


def trail32(x):
    return np.floor((x - np.minimum(x, GAP32)) / STEP32 + np.float32(0.5)) * STEP32


def run_legs(sel, e, m0, bars, idx, SH, SL, out):
    """luat thoat QS0 (seg) cho cac chan cung coin: chua arm & qua 168h -> min(open,close); high/E-1 > 7% -> arm,
    SL trail, khong thoat cung nen; da arm -> thoat neu low <= SL truoc do (hoac nen truoc vua doi SL ma close <= SL)
    tai min(SL, open). Het du lieu (T26) -> cut o close cuoi."""
    o, h, l, c = bars
    n = len(c)
    E32 = c[e]
    E64 = E32.astype(np.float64)
    kts = np.searchsorted(idx, m0 + TSM, "right")
    BIG = n + 10 ** 9
    ka = np.full(len(sel), BIG, np.int64)
    start = e + 1
    thr = E64 * 1.07 * (1 - 1e-6)
    todo = np.arange(len(sel))
    while len(todo):
        p = first_gt(SH, start[todo], thr[todo], n)
        pc = np.minimum(p, n - 1)
        f = (p < n) & (h[pc] > thr[todo])
        ex = f & ((h[pc] / E32[todo] - np.float32(1.0)) > ARM32)
        ka[todo[ex]] = p[ex]
        again = f & ~ex
        start[todo[again]] = p[again] + 1
        todo = todo[again]
    tmx = (kts < n) & (kts <= ka)
    arm = ~tmx & (ka < n)
    cut = ~tmx & ~arm
    kx = np.full(len(sel), -1, np.int64)
    pxl = np.full(len(sel), np.nan)
    wh = np.zeros(len(sel), np.int8)
    i = np.flatnonzero(tmx)
    kx[i] = kts[i]
    pxl[i] = np.minimum(o[kts[i]], c[kts[i]]).astype(np.float64)
    wh[i] = 1
    ia = np.flatnonzero(arm)
    if len(ia):
        a_ = ka[ia]
        Ea = E32[ia]
        sl = trail32(h[a_] / Ea - np.float32(1.0)).astype(np.float32)
        pend = c[a_] <= (E64[ia] * (1.0 + sl.astype(np.float64))).astype(np.float32)
        pos = a_ + 1
        act = np.arange(len(ia))
        ar = np.arange(WC)
        while len(act):
            P0 = pos[act]
            cols = P0[:, None] + ar[None, :]
            inb = cols < n
            cc = np.minimum(cols, n - 1)
            hh, ll, cl, oo = h[cc], l[cc], c[cc], o[cc]
            Ec = Ea[act][:, None]
            hr = hh / Ec - np.float32(1.0)
            tr = np.where((hr >= ARM32) & inb, trail32(hr), np.float32(-np.inf))
            after = np.maximum.accumulate(np.maximum(tr, sl[act][:, None]), axis=1)
            before = np.concatenate([sl[act][:, None], after[:, :-1]], axis=1)
            reset = after > before
            pbn = reset & (cl <= (np.float32(1.0) + after) * Ec)
            pb = np.concatenate([pend[act][:, None], pbn[:, :-1]], axis=1)
            exm = ((ll.astype(np.float64) <= Ec.astype(np.float64) * (1.0 + before.astype(np.float64))) | pb) & inb
            hit = exm.any(1)
            kk = exm.argmax(1)
            rr = np.flatnonzero(hit)
            g = ia[act[rr]]
            kh = kk[rr]
            kx[g] = P0[rr] + kh
            pxl[g] = np.minimum(E64[g] * (1.0 + before[rr, kh].astype(np.float64)), oo[rr, kh].astype(np.float64))
            wh[g] = 2
            nh = np.flatnonzero(~hit)
            endm = (P0[nh] + WC) >= n
            cut[ia[act[nh[endm]]]] = True
            cn = nh[~endm]
            g2 = act[cn]
            sl[g2] = after[cn, -1]
            pend[g2] = reset[cn, -1] & (cl[cn, -1] <= (np.float32(1.0) + after[cn, -1]) * Ea[g2])
            pos[g2] = P0[cn] + WC
            act = g2
    ic = np.flatnonzero(cut)
    kx[ic] = n - 1
    pxl[ic] = float(c[n - 1])
    wh[ic] = 3
    ext = MS0 + idx[kx] * MN
    ext[ic] = T26
    a0 = e + 1
    okm = kx >= a0
    mn = np.full(len(sel), np.nan)
    if okm.any():
        mn[okm] = rmin(SL, a0[okm], kx[okm])
    out["E"][sel] = E64
    out["px"][sel] = pxl
    out["exit_t"][sel] = ext
    out["why"][sel] = wh
    out["mae"][sel] = mn / E64 - 1.0


def proc_sym(X, t0):
    """X = (4, NM) O/H/L/C float32 dac theo phut tu MS0; t0 = ms vao (close nen t0). Tra ket qua chan + mark ngay."""
    nl = len(t0)
    out = dict(t0=t0, E=np.full(nl, np.nan), px=np.full(nl, np.nan), exit_t=np.full(nl, -1, np.int64),
               why=np.zeros(nl, np.int8), nobar=np.ones(nl, bool), mae=np.full(nl, np.nan))
    idx = np.flatnonzero(~np.isnan(X[3]))
    n = len(idx)
    mk = np.full(U1D - U0D + 1, np.nan, np.float32)
    if n == 0:
        return out, mk
    bars = (X[0][idx], X[1][idx], X[2][idx], X[3][idx])
    bi = np.searchsorted(idx, np.arange(U1D - U0D + 1) * 1440 + 1019, "right") - 1
    mk = np.where(bi >= 0, bars[3][np.maximum(bi, 0)], np.nan).astype(np.float32)
    m0 = (t0 - MS0) // MN
    e = np.searchsorted(idx, m0)
    ok = (e < n) & (idx[np.minimum(e, n - 1)] == m0)
    out["nobar"][:] = ~ok
    if not ok.any():
        return out, mk
    SH = sparse(bars[1], LV, np.maximum)
    SL = sparse(bars[2], 64, np.minimum)
    for a in range(0, nl, CH):
        sel = np.arange(a, min(nl, a + CH))
        sel = sel[ok[sel]]
        if len(sel):
            run_legs(sel, e[sel], m0[sel], bars, idx, SH, SL, out)
    return out, mk


def stage_path(nb=100, workers=3):
    S = pd.read_pickle(W + "/sig.pkl")
    U = S["U"].copy()
    U["psym"] = U["sym"] + "USDT"
    bp = S["basept"].copy()
    bp["psym"] = bp["sym"] + "USDT"
    allp = pd.concat([U[["psym", "t0"]], bp[["psym", "t0"]]]).drop_duplicates(ignore_index=True)
    allp["u"] = allp["t0"] // D
    allp["mi"] = (allp["t0"] - allp["u"] * D) // MN
    req = {u: {s: g["mi"].to_numpy() for s, g in gu.groupby("psym")} for u, gu in allp.groupby("u")}
    gidx = U.groupby("psym").indices
    syms = U["psym"].value_counts().index.tolist()
    nbat = int(math.ceil(len(syms) / nb))
    batches = [syms[i::nbat] for i in range(nbat)]
    days = [pd.Timestamp(u * D, unit="ms").strftime("%Y%m%d") for u in range(U0D, U1D + 1)]
    log.info("PATH: chan %d, coin %d, lo %d x <= %d, diem tra cuu %d", len(U), len(syms), nbat, nb, len(allp))
    ptrows, res, marks, miss = [], [], {}, set()
    t_start = time.time()
    for bi, bs in enumerate(batches):
        dense = np.full((len(bs), 4, NM), np.nan, np.float32)
        args = [(day, bs, req.get(U0D + di) if bi == 0 else None) for di, day in enumerate(days)]
        with Pool(workers) as pool:
            for di, (day, A, pp) in enumerate(pool.imap(parse_day2, args, chunksize=1)):
                assert day == days[di]
                if A is None:
                    miss.add(day)
                    continue
                off = di * 1440
                lim = min(1440, NM - off)
                dense[:, :, off:off + lim] = A[:, :lim, :].transpose(2, 0, 1)
                if pp:
                    u = U0D + di
                    for s, v in pp.items():
                        ptrows.append((s, u * D + req[u][s].astype(np.int64) * MN, v))
                if di % 200 == 0:
                    log.info("PATH lo %d/%d ngay %s (%d/%d) %.0fs", bi + 1, nbat, day, di, len(days),
                             time.time() - t_start)
        for j, s in enumerate(bs):
            g = gidx[s]
            r, mk = proc_sym(dense[j], U["t0"].to_numpy(np.int64)[g])
            r["row"] = g
            res.append(r)
            marks[s] = mk
        log.info("PATH lo %d/%d xong (%d coin) %.0fs", bi + 1, nbat, len(bs), time.time() - t_start)
        del dense
    row = np.concatenate([r["row"] for r in res])
    R = pd.DataFrame({k: np.concatenate([r[k] for r in res]) for k in ("t0", "E", "px", "exit_t", "why", "nobar", "mae")})
    R["psym"] = U["psym"].to_numpy()[row]
    assert (R["t0"].to_numpy() == U["t0"].to_numpy()[row]).all()
    R = R.sort_values(["psym", "t0"], kind="mergesort").reset_index(drop=True)
    PTS = pd.DataFrame(dict(psym=np.concatenate([np.full(len(t), s, object) for s, t, v in ptrows]),
                            t0=np.concatenate([t for s, t, v in ptrows]),
                            O=np.concatenate([v[:, 0] for s, t, v in ptrows]),
                            C=np.concatenate([v[:, 1] for s, t, v in ptrows]),
                            V=np.concatenate([v[:, 2] for s, t, v in ptrows])))
    pd.to_pickle(dict(R=R, pts=PTS, marks=marks, miss=sorted(miss)), W + "/legs.pkl")
    log.info("PATH xong %.0fs: chan %d, nobar %d, cut %d, ngay thieu %d", time.time() - t_start, len(R),
             int(R["nobar"].sum()), int((R["why"] == 3).sum()), len(miss))


# ---------------------------------------------------------------- eval: gio, tran, doi chung, danh muc ghep, luat
def greedy(T, EL, LS, EX):
    """theo thoi gian: hoi chieu 6h (tinh ca kich hoat bi bo/rong), coin 24h (chi gio duoc mo), <= NB chan theo
    thu tu EL, tran CAPB gio mo (gio dong khi exit_t <= t)."""
    last, lastc, opn = -10 ** 18, {}, []
    acc, drop, empty = [], 0, 0
    for t, el in zip(T, EL):
        if t - last < COOL:
            continue
        last = t
        lg = []
        for lid in el:
            if t - lastc.get(LS[lid], -10 ** 18) < COIN:
                continue
            lg.append(lid)
            if len(lg) == NB:
                break
        if not lg:
            empty += 1
            continue
        opn = [x for x in opn if x > t]
        if len(opn) >= CAPB:
            drop += 1
            continue
        opn.append(max(EX[x] for x in lg))
        for x in lg:
            lastc[LS[x]] = t
        acc.append((t, lg))
    return acc, drop, empty


G = {}


def ctrl_seed(si):
    """NDRAW lan boc phut yen ngau nhien (E8) cho 1 seed -> (tong ROI stress, tong ROI net, so gio, thieu)."""
    seed = SEEDS[si]
    rng = np.random.default_rng([RNG, si])
    PT, PEL, PM = G["PT"], G["PEL"], G["PM"]
    ok, nm = G["pok"][seed], G["nm"][seed]
    LS, EX, STR, NET = G["LS"], G["EX"], G["STR"], G["NET"]
    bym = {m: np.flatnonzero(ok & (PM == m)) for m in nm}
    res = np.zeros((NDRAW, 4))
    for d in range(NDRAW):
        ci = np.sort(np.concatenate([rng.choice(bym[m], size=min(OVS * n, len(bym[m])), replace=False)
                                     for m, n in nm.items() if len(bym[m])]))
        acc, _, _ = greedy(PT[ci].tolist(), [PEL[i] for i in ci.tolist()], LS, EX)
        am = lmonth(np.array([a[0] for a in acc], np.int64)) if acc else np.zeros(0, np.int64)
        s_str = s_net = cnt = short = 0.0
        for m, n in nm.items():
            ii = np.flatnonzero(am == m)
            if len(ii) > n:
                ii = rng.choice(ii, size=n, replace=False)
            short += n - len(ii)
            for k in ii.tolist():
                lg = acc[k][1]
                s_str += float(np.mean(STR[lg]))
                s_net += float(np.mean(NET[lg]))
                cnt += 1
        res[d] = (s_str, s_net, cnt, short)
    return si, res


def leg_inc(t0, ex, E, px, mk):
    """PnL ngay MTM cua 1 chan (don vi notional): mark close <= 16:59 UTC; ngay thoat (px - mark)/E - phi."""
    d0, d1 = int(lday(t0)), min(int(lday(ex)), U1D)
    prev, out = E, []
    for d in range(d0, d1):
        m = float(mk[d - U0D])
        if np.isfinite(m):
            out.append((d, (m - prev) / E))
            prev = m
    out.append((d1, (px - prev) / E - COST))
    return out


def perf(r):
    eq = np.concatenate([[1.0], np.cumprod(1.0 + r)])
    cagr = eq[-1] ** (365.25 / len(r)) - 1.0
    mdd = float((1.0 - eq / np.maximum.accumulate(eq)).max())
    return dict(cagr=100 * cagr, mdd=100 * mdd, calmar=cagr / mdd if mdd > 0 else None)


def boot_day(v, day, rng):
    dd, inv = np.unique(day, return_inverse=True)
    sm, ct = np.bincount(inv, weights=v), np.bincount(inv).astype(float)
    ix = rng.integers(0, len(dd), size=(NBOOT, len(dd)))
    mb = sm[ix].sum(1) / ct[ix].sum(1)
    return [float(x) for x in np.percentile(mb, [2.5, 97.5])]


def mmm(v):
    return Q0.mmm(list(v))


def stage_eval():
    S = pd.read_pickle(W + "/sig.pkl")
    LG = pd.read_pickle(W + "/legs.pkl")
    P0 = pd.read_pickle(W0 + "/path.pkl")
    s2id, id2s = Q0.s2id_map()
    rng = np.random.default_rng(RNG)
    R = LG["R"].merge(LG["pts"], on=["psym", "t0"], how="left")
    R["gross"] = R["px"] / R["E"] - 1.0
    R["br"] = R["C"] / R["O"] - 1.0
    R["crash"] = (R["br"] <= CRASH).to_numpy()
    R["elig"] = ~R["nobar"] & (R["V"] >= VMIN)
    R["net"] = 100 * (R["gross"] - COST)
    R["str"] = R["net"] - 100 * PEN * R["crash"]
    key = {(s, t): i for i, (s, t) in enumerate(zip(R["psym"].tolist(), R["t0"].tolist()))}
    LS = pd.factorize(R["psym"])[0]
    EX = R["exit_t"].to_numpy(np.int64)
    NET, STR = R["net"].to_numpy(), R["str"].to_numpy()
    ELIG = R["elig"].to_numpy()
    js = dict(title="QS1_RESULT 2026-10-08", prereg="docs/prereg/PREREG_QS1.md @3b69309e",
              script="research/analysis/qsleeve_q1.py", checks={}, cfg=dict(
                  K=K, pq=PQ, qdays=QDAYS, minq_min=MINQ, nb=NB, vmin=VMIN, cool_h=6, coin_h=24, cap=CAPB, sleeve=SLV,
                  basket=BSZ, ndraw=NDRAW, poolm=POOLM, ovs=OVS, nboot=NBOOT, cost=COST, pen=PEN))
    js["checks"]["path"] = dict(n_legs=int(len(R)), nobar=int(R["nobar"].sum()), cut=int((R["why"] == 3).sum()),
                                miss_days=LG["miss"][:20], n_unknown_sym=S["n_unknown_sym"],
                                vol_nan=int(R["V"].isna().sum()))
    # tu kiem 1: proxy tai lap QS0 o K24/0.9995 (khong gio)
    c0 = P0["cand"]
    c0 = c0[(c0["K"] == 24) & (c0["pct"] == 0.9995)].merge(P0["R"][["tid", "gross", "nobar", "why"]], on="tid")
    c0 = c0[~c0["nobar"]]
    lid = np.array([key.get((s + "USDT", int(t)), -1) for s, t in zip(c0["sym"], c0["ts"])])
    okl = lid >= 0
    mine = R["gross"].to_numpy()[lid[okl]]
    ref = c0["gross"].to_numpy()[okl]
    wq = c0["why"].to_numpy()[okl]
    wm = np.array([{1: "time", 2: "trail", 3: "cut"}.get(int(x), "?") for x in R["why"].to_numpy()[lid[okl]]])
    rm = float(100 * np.nanmean(mine - COST))
    js["checks"]["proxy_repro"] = dict(n=int(len(c0)), found=int(okl.sum()), mine_nan=int(np.isnan(mine).sum()),
                                       roi_net_mine=rm, roi_net_qs0=float(100 * np.mean(c0["gross"] - COST)),
                                       qs0_json=QS0_REF, diff_pp=rm - QS0_REF,
                                       exact_share=float(np.mean(np.abs(mine - ref) < 1e-9)),
                                       max_abs_diff_pp=float(100 * np.nanmax(np.abs(mine - ref))),
                                       why_match=float(np.mean(wm == wq)),
                                       verdict="PASS" if abs(rm - QS0_REF) <= 0.05 else "FAIL")
    log.info("PROXY REPRO %s", js["checks"]["proxy_repro"])

    def elig_list(t, syr, okr):
        out = []
        for c in range(K):
            if not okr[c]:
                continue
            s = id2s.get(int(syr[c]))
            i = key.get((s + "USDT", t)) if s is not None else None
            if i is not None and ELIG[i]:
                out.append(i)
        return out
    # sleeve
    BK, SQ = [], {}
    for seed in SEEDS:
        sd = S["seed"][seed]
        T = [int(x) for x in sd["trig_ts"]]
        EL = [elig_list(t, sd["trig_SY"][i], sd["trig_valid"][i]) for i, t in enumerate(T)]
        acc, drop, empty = greedy(T, EL, LS, EX)
        tr_y = lyear(np.array(T, np.int64)) if T else np.zeros(0)
        # bat bien: 6h, coin 24h, <=5 gio mo, vol, coin khac nhau trong gio
        okv, lastc, opn = True, {}, []
        for k, (t, lg) in enumerate(acc):
            okv &= k == 0 or t - acc[k - 1][0] >= COOL
            okv &= len(set(LS[lg].tolist())) == len(lg) and bool(ELIG[lg].all()) and len(lg) <= NB
            okv &= all(t - lastc.get(int(x), -10 ** 18) >= COIN for x in LS[lg])
            opn = [x for x in opn if x > t]
            okv &= len(opn) < CAPB
            opn.append(int(EX[lg].max()))
            for x in LS[lg]:
                lastc[int(x)] = t
        dropped_y = {}
        SQ[seed] = dict(n_trig=len(T), n_acc=len(acc), drop_cap=drop, empty=empty, invariants_ok=bool(okv),
                        trig_year={y: int((tr_y == y).sum()) for y in YEARS}, sig_year=sd["year"],
                        overlap=sd["overlap"], q_brute_ok=sd["q_brute_ok"], jmax=sd["jmax"])
        for t, lg in acc:
            BK.append(dict(seed=seed, t=t, nleg=len(lg), net=float(NET[lg].mean()), str=float(STR[lg].mean()),
                           mae=float(np.nanmean(R["mae"].to_numpy()[lg])), exit=int(EX[lg].max()), legs=lg))
        log.info("SLEEVE %s: kich hoat %d, gio %d, bo tran %d, rong %d, bat bien %s", seed, len(T), len(acc), drop,
                 empty, okv)
    BKd = pd.DataFrame(BK)
    BKd["year"], BKd["month"], BKd["day"] = lyear(BKd["t"]), lmonth(BKd["t"]), lday(BKd["t"])
    allleg = np.concatenate(BKd["legs"].map(np.array).tolist())
    MAE = R["mae"].to_numpy()
    LL = BKd[["seed", "year", "legs"]].explode("legs")
    LL["lid"] = LL["legs"].astype(np.int64)

    def blk(b, ll, div):
        if len(b) == 0:
            return dict(n=0)
        return dict(n=int(len(b)), n_rate=len(b) / div, legs=int(len(ll)), legs_rate=len(ll) / div,
                    roi_net=float(b["net"].mean()), roi_str=float(b["str"].mean()),
                    win=float((b["net"] > 0).mean()), win_str=float((b["str"] > 0).mean()),
                    mae_p10_leg=float(np.nanpercentile(100 * MAE[ll["lid"].to_numpy()], 10)),
                    mae_p10_basket=float(np.nanpercentile(100 * b["mae"], 10)),
                    lt5=float((b["nleg"] < NB).mean()), hold_p50_h=float(np.median((b["exit"] - b["t"]) / H)),
                    crash_leg=float(R["crash"].to_numpy()[ll["lid"].to_numpy()].mean()))
    js["pooled"] = blk(BKd, LL, 8 * 4)
    js["pooled"]["boot95_str"] = boot_day(BKd["str"].to_numpy(), BKd["day"].to_numpy(), rng)
    js["pooled"]["boot95_net"] = boot_day(BKd["net"].to_numpy(), BKd["day"].to_numpy(), rng)
    js["year"] = {y: blk(BKd[BKd["year"] == y], LL[LL["year"] == y], 8) for y in YEARS}
    for y in YEARS:
        js["year"][y]["trig_rate"] = float(np.mean([SQ[s]["trig_year"][y] for s in SEEDS]))
        js["year"][y]["quiet"] = mmm([SQ[s]["sig_year"][y]["quiet"] for s in SEEDS])
        js["year"][y]["q_over_qcore_p50"] = mmm([SQ[s]["sig_year"][y]["q_over_qcore_p50"] for s in SEEDS])
    js["seed"] = {s: dict(blk(BKd[BKd["seed"] == s], LL[LL["seed"] == s], 4), **{k: SQ[s][k] for k in (
        "n_trig", "n_acc", "drop_cap", "empty", "invariants_ok", "q_brute_ok", "jmax")}) for s in SEEDS}
    js["checks"]["overlap_qs0"] = {s: SQ[s]["overlap"] for s in SEEDS}
    js["checks"]["overlap_qs0_jaccard"] = mmm([SQ[s]["overlap"]["jaccard"] for s in SEEDS])
    js["checks"]["invariants_ok"] = all(SQ[s]["invariants_ok"] for s in SEEDS)
    js["checks"]["q_lookahead_brute_days"] = sum(SQ[s]["q_brute_ok"] for s in SEEDS)
    js["drop_cap_rate"] = sum(SQ[s]["drop_cap"] for s in SEEDS) / 32.0
    # doi chung (E8)
    pool, pSY, pSP = S["pool"], S["pool_SY"], S["pool_SP"]
    nanok = ~np.isnan(pSP)
    PEL = [elig_list(int(t), pSY[i], nanok[i]) for i, t in enumerate(pool.tolist())]
    G.update(PT=pool, PEL=PEL, PM=lmonth(pool), pok={s: S["seed"][s]["pool_ok"] for s in SEEDS},
             nm={s: BKd[BKd["seed"] == s].groupby("month").size().to_dict() for s in SEEDS},
             LS=LS, EX=EX, STR=STR, NET=NET)
    t0 = time.time()
    with Pool(4) as pp:
        outc = dict(pp.map(ctrl_seed, range(len(SEEDS))))
    log.info("CTRL xong %.0fs", time.time() - t0)
    CR = np.stack([outc[i] for i in range(len(SEEDS))])            # (seed, draw, [str, net, n, thieu])
    cs, cn = CR[:, :, 0].sum(0) / CR[:, :, 2].sum(0), CR[:, :, 1].sum(0) / CR[:, :, 2].sum(0)
    p = js["pooled"]
    js["ctrl"] = dict(mean_str=float(cs.mean()), p05_str=float(np.percentile(cs, 5)), p95_str=float(np.percentile(cs, 95)),
                      mean_net=float(cn.mean()), p95_net=float(np.percentile(cn, 95)),
                      p_str=float(np.mean(cs >= p["roi_str"])), p_net=float(np.mean(cn >= p["roi_net"])),
                      n_mean=float(CR[:, :, 2].sum(0).mean()), short_mean=float(CR[:, :, 3].sum(0).mean()),
                      pool_n=int(len(pool)), pool_ok=mmm([S["seed"][s]["pool_ok"].mean() for s in SEEDS]),
                      seed={s: dict(mean_str=float((CR[i, :, 0] / CR[i, :, 2]).mean()),
                                    p_str=float(np.mean(CR[i, :, 0] / CR[i, :, 2] >= js["seed"][s]["roi_str"])))
                            for i, s in enumerate(SEEDS)})
    log.info("CTRL %s", {k: v for k, v in js["ctrl"].items() if k != "seed"})
    # danh muc ghep (E7)
    eq, legs0, marks = P0["eq"], P0["legs"], LG["marks"]
    days = np.arange(U0D, U1D + 1)
    nd = len(days)
    yrs = pd.to_datetime(days[1:] * D, unit="ms").year.to_numpy()
    Rt0, RE, Rpx, Rps, CRm = (R["t0"].to_numpy(), R["E"].to_numpy(), R["px"].to_numpy(), R["psym"].to_numpy(),
                              R["crash"].to_numpy())
    PF = {}
    for seed in SEEDS:
        e = np.array([eq[seed][int(u)] for u in days])
        lg = legs0[(legs0["seed"] == seed) & (legs0["s_ms"] >= T22) & (legs0["s_ms"] < T26)].copy()
        lg["psym"] = lg["sym"] + "USDT"
        lg = lg.merge(LG["pts"].rename(columns={"t0": "s_ms"}), on=["psym", "s_ms"], how="left")
        cr = (lg["C"] / lg["O"] - 1.0 <= CRASH).to_numpy()
        pen = PEN * (lg["quantity"] * lg["entry"]).to_numpy(float) * cr
        pc = np.zeros(nd)
        np.add.at(pc, lday(lg["s_ms"].to_numpy()) - U0D, pen)
        es = e - np.cumsum(pc)
        rb, rbs = e[1:] / e[:-1] - 1.0, es[1:] / es[:-1] - 1.0
        rs, rss, sdays = np.zeros(nd), np.zeros(nd), set()
        for nleg, lgs in zip(BKd.loc[BKd["seed"] == seed, "nleg"], BKd.loc[BKd["seed"] == seed, "legs"]):
            w = BSZ / nleg
            for x in lgs:
                for d, v in leg_inc(Rt0[x], EX[x], RE[x], Rpx[x], marks[Rps[x]]):
                    rs[d - U0D] += w * v
                    rss[d - U0D] += w * v
                d0 = int(lday(Rt0[x]))
                if CRm[x]:
                    rss[d0 - U0D] -= w * PEN
                sdays.update(range(d0, min(int(lday(EX[x])), U1D) + 1))
        rs, rss = rs[1:], rss[1:]
        comb, combs = 0.9 * rb + 0.1 * rs, 0.9 * rbs + 0.1 * rss
        cl = legs0[legs0["seed"] == seed].groupby("pid").agg(s=("s_ms", "min"), e=("e_ms", "max"))
        bd = Q0.day_set(cl["s"], cl["e"], U0D + 1, U1D + 1)
        sd = {d for d in sdays if U0D + 1 <= d <= U1D}
        csum = np.concatenate([[0.0], np.cumsum(rss)])
        PF[seed] = dict(base=perf(rb), base_s=perf(rbs), comb=perf(comb), comb_s=perf(combs),
                        corr=float(np.corrcoef(rs, rb)[0, 1]), corr_s=float(np.corrcoef(rss, rbs)[0, 1]),
                        sleeve_ann=100 * rs.sum() / 4, sleeve_ann_s=100 * rss.sum() / 4,
                        sleeve_mdd_s=100 * float((np.maximum.accumulate(csum) - csum).max()),
                        days_sleeve=len(sd) / (nd - 1), days_base=len(bd) / (nd - 1), days_union=len(sd | bd) / (nd - 1),
                        base_crash_legs=int(cr.sum()), base_legs=int(len(lg)),
                        base_entry_match=float((np.abs(lg["C"] / lg["entry"] - 1) < 1e-5).mean()),
                        year={int(y): dict(base_s=100 * (np.prod(1 + rbs[yrs == y]) - 1),
                                           comb_s=100 * (np.prod(1 + combs[yrs == y]) - 1),
                                           sleeve_s=100 * rss[yrs == y].sum()) for y in YEARS})
    js["pf_seed"] = PF
    js["pf"] = {k: mmm([PF[s][a][b] for s in SEEDS]) for k, (a, b) in dict(
        base_cagr=("base", "cagr"), base_mdd=("base", "mdd"), base_calmar=("base", "calmar"),
        base_s_cagr=("base_s", "cagr"), base_s_mdd=("base_s", "mdd"), base_s_calmar=("base_s", "calmar"),
        comb_cagr=("comb", "cagr"), comb_mdd=("comb", "mdd"), comb_calmar=("comb", "calmar"),
        comb_s_cagr=("comb_s", "cagr"), comb_s_mdd=("comb_s", "mdd"), comb_s_calmar=("comb_s", "calmar")).items()}
    for k in ("corr", "corr_s", "sleeve_ann", "sleeve_ann_s", "sleeve_mdd_s", "days_sleeve", "days_base",
              "days_union", "base_entry_match"):
        js["pf"][k] = mmm([PF[s][k] for s in SEEDS])
    js["pf"]["year"] = {y: {k: mmm([PF[s]["year"][y][k] for s in SEEDS]) for k in ("base_s", "comb_s", "sleeve_s")}
                        for y in YEARS}
    nsp = sum(js["seed"][s]["roi_str"] > 0 for s in SEEDS)
    nyp = sum(js["year"][y]["roi_str"] > 0 for y in YEARS)
    v = dict(L1=bool(p["roi_str"] > 0 and p["boot95_str"][0] > 0 and nsp >= 6),
             L2=bool(js["ctrl"]["p_str"] < 0.05), L3=bool(nyp >= 3),
             L4=bool(js["pf"]["comb_s_calmar"]["mean"] >= js["pf"]["base_s_calmar"]["mean"]
                     and js["pf"]["corr_s"]["mean"] <= 0.5))
    v.update(n_seed_pos=int(nsp), n_year_pos=int(nyp), GO=all(v.values()))
    js["verdict"] = v
    log.info("VERDICT %s", v)
    pd.to_pickle(dict(BK=BKd, CR=CR, PF=PF), W + "/eval.pkl")
    os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
    json.dump(GO.tojs(js), open(JSON_OUT, "w"), indent=1, ensure_ascii=False)
    write_md(GO.tojs(js))


f2, fm, tbl = Q0.f2, Q0.fm, Q0.tbl


def write_md(js):
    v, p, c, pf, ck = js["verdict"], js["pooled"], js["ctrl"], js["pf"], js["checks"]
    L = ["# QS1_RESULT — quiet sleeve dạng GIỎ (đánh giá OFFLINE, DEV 2022–25)", "",
         "Pre-reg `docs/prereg/PREREG_QS1.md` (3b69309e, commit TRƯỚC khi đo). Script `research/analysis/qsleeve_q1.py`; "
         "JSON `docs/result/QS1_RESULT.json`. 1 cấu hình, không tune; 0 sim/Kaggle/Java, 0 chạm 242/shadow, không mở nsel-*.",
         "", "**Verdict DEV: %s** — L1 %s · L2 %s · L3 %s · L4 %s" % (
             "GO" if v["GO"] else "NO-GO", *["PASS" if v[k] else "FAIL" for k in ("L1", "L2", "L3", "L4")]), ""]
    hp = W + "/qs1_head.md"
    if os.path.exists(hp):
        L += open(hp).read().rstrip().split("\n") + [""]
    pr = ck["proxy_repro"]
    L += ["## Tự kiểm",
          "- Proxy tái lập QS0 K24/0,9995 (không giỏ): ROI net %s%% vs QS0 %s%% (Δ %s pp, ngưỡng ±0,05) → **%s**; "
          "trùng từng lệnh %s%%, cùng lý do thoát %s%%, n %d." % (
              f2(pr["roi_net_mine"], 3), f2(pr["qs0_json"], 3), f2(pr["diff_pp"], 3), pr["verdict"],
              f2(100 * pr["exact_share"], 2), f2(100 * pr["why_match"], 2), pr["found"]),
          "- Phút yên mới vs QS0 (tuổi leg0 ≥ 24h), phút DEV, TB 8 seed: Jaccard %s; yên-mới ⊂ QS0 %s; QS0 ⊂ yên-mới %s; "
          "đồng ý %s; tỉ lệ yên mới %s vs QS0 %s." % (
              fm(ck["overlap_qs0_jaccard"], 3),
              f2(np.mean([o["new_in_qs0"] for o in ck["overlap_qs0"].values()]), 3),
              f2(np.mean([o["qs0_in_new"] for o in ck["overlap_qs0"].values()]), 3),
              f2(np.mean([o["agree"] for o in ck["overlap_qs0"].values()]), 3),
              f2(np.mean([o["share_new"] for o in ck["overlap_qs0"].values()]), 3),
              f2(np.mean([o["share_qs0"] for o in ck["overlap_qs0"].values()]), 3)),
          "- Không lookahead: assert pass < t (mọi phút); Q(ngày u) tính lại brute-force chỉ từ phút < u·D ≤ t "
          "trùng tuyệt đối %d ngày kích hoạt (8 seed). Bất biến giỏ (6h, coin 24h, ≤5 mở, vol, coin khác nhau): %s." % (
              ck["q_lookahead_brute_days"], "PASS" if ck["invariants_ok"] else "FAIL"),
          "- Đường đi: %d chân vũ trụ (phút kích hoạt ∪ pool đối chứng × top-24), nobar %d, cut %d, ngày ticker thiếu %d, "
          "symbol lạ %d." % (ck["path"]["n_legs"], ck["path"]["nobar"], ck["path"]["cut"], len(ck["path"]["miss_days"]),
                             ck["path"]["n_unknown_sym"]),
          "- Nền stress post-hoc: chân nền khớp entry = close nến quyết định %s; đối chứng thiếu giỏ TB %s/1000 lần." % (
              fm(pf["base_entry_match"], 4), f2(c["short_mean"], 1)), ""]
    L += ["## T1. Theo năm (gộp 8 seed; tỉ lệ = /năm/seed)"]
    rows = []
    for y in list(map(str, YEARS)) + ["2022–25"]:
        b = js["year"][y] if y in js["year"] else p
        rows.append([y, f2(b.get("trig_rate"), 1) if "trig_rate" in b else "—", f2(b["n_rate"], 1), f2(b["legs_rate"], 1),
                     f2(b["roi_net"]), f2(b["roi_str"]), f2(100 * b["win"], 1), f2(100 * b["win_str"], 1),
                     f2(b["mae_p10_leg"], 1), f2(b["mae_p10_basket"], 1), f2(100 * b["lt5"], 1), f2(b["hold_p50_h"], 0),
                     f2(100 * b["crash_leg"], 1)])
    L += tbl(["năm", "kích hoạt", "giỏ", "chân", "ROI net %", "ROI stress %", "win net %", "win stress %",
              "MAE p10 chân", "MAE p10 giỏ", "% giỏ <5 chân", "giữ p50 h", "% chân sập"], rows)
    L += ["", "Bootstrap cụm ngày 95%% (gộp, %d lần): ROI stress [%s; %s], ROI net [%s; %s]. Giỏ bị bỏ do trần 5: %s/năm/seed." % (
        NBOOT, f2(p["boot95_str"][0]), f2(p["boot95_str"][1]), f2(p["boot95_net"][0]), f2(p["boot95_net"][1]),
        f2(js["drop_cap_rate"], 1)), "", "## T2. Theo seed (DEV 2022–25)"]
    rows = []
    for s in SEEDS:
        b, q = js["seed"][s], js["pf_seed"][s]
        rows.append([s, b["n_trig"], b["n_acc"], b["drop_cap"], b["empty"], f2(b["n_rate"], 1), f2(b["roi_net"]),
                     f2(b["roi_str"]), f2(100 * b["win"], 1), f2(c["seed"][s]["p_str"], 3), f2(q["base_s"]["calmar"], 3),
                     f2(q["comb_s"]["calmar"], 3), f2(q["corr_s"], 3)])
    L += tbl(["seed", "kích hoạt", "giỏ mở", "bỏ trần", "rỗng", "giỏ/năm", "ROI net %", "ROI stress %", "win %",
              "p đối chứng (seed)", "Calmar nền S", "Calmar ghép S", "corr S"], rows)
    L += ["", "## T3. Đối chứng phút yên ngẫu nhiên (%d lần, pool %d phút, cùng giỏ/tháng/seed)" % (NDRAW, c["pool_n"]),
          "- Sleeve gộp: ROI stress %s%%, net %s%%. Đối chứng gộp: stress TB %s%% [p5 %s; p95 %s], net TB %s%% [p95 %s]." % (
              f2(p["roi_str"]), f2(p["roi_net"]), f2(c["mean_str"]), f2(c["p05_str"]), f2(c["p95_str"]),
              f2(c["mean_net"]), f2(c["p95_net"])),
          "- **p một phía (stress) = %s**; p (net) = %s. Giỏ/lần TB %s (sleeve %d)." % (
              f2(c["p_str"], 3), f2(c["p_net"], 3), f2(c["n_mean"], 0), p["n"]), "",
          "## T4. Danh mục ghép 0,9 nền + 0,1 sleeve vs nền 1,0× (MTM ngày 2022–25; TB 8 seed [min..max])"]
    rows = []
    for nm, k in (("nền 1,0× (phí gốc)", "base"), ("nền 1,0× stress", "base_s"), ("ghép (phí gốc)", "comb"),
                  ("ghép stress", "comb_s")):
        rows.append([nm, fm(pf[k + "_cagr"], 2), fm(pf[k + "_mdd"], 2), fm(pf[k + "_calmar"], 3)])
    L += tbl(["danh mục", "CAGR22 %", "maxDD22 %", "Calmar22 ngày"], rows)
    L += ["", "- Tương quan return ngày sleeve vs nền: stress %s, phí gốc %s. Sleeve (vốn sleeve, không lãi kép): "
          "stress %s%%/năm, maxDD %s%%. %% ngày có vị thế: sleeve %s, nền %s, hợp %s." % (
              fm(pf["corr_s"], 3), fm(pf["corr"], 3), fm(pf["sleeve_ann_s"], 2), fm(pf["sleeve_mdd_s"], 2),
              fm({k: 100 * x for k, x in pf["days_sleeve"].items()}, 1), fm({k: 100 * x for k, x in pf["days_base"].items()}, 1),
              fm({k: 100 * x for k, x in pf["days_union"].items()}, 1)), "", "Theo năm (stress, TB 8 seed):"]
    rows = [[y, fm(pf["year"][y]["base_s"], 2), fm(pf["year"][y]["comb_s"], 2), fm(pf["year"][y]["sleeve_s"], 2)]
            for y in map(str, YEARS)]
    L += tbl(["năm", "nền 1,0× stress %", "ghép stress %", "sleeve stress % vốn sleeve"], rows)
    L += ["", "## Luật GO DEV (pre-reg)", ""]
    rows = [["L1", "ROI stress gộp > 0 & cận dưới bootstrap > 0 & ≥ 6/8 seed > 0",
             "%s%%; [%s; %s]; %d/8" % (f2(p["roi_str"]), f2(p["boot95_str"][0]), f2(p["boot95_str"][1]), v["n_seed_pos"]),
             "PASS" if v["L1"] else "FAIL"],
            ["L2", "p đối chứng (gộp) < 0,05", f2(c["p_str"], 3), "PASS" if v["L2"] else "FAIL"],
            ["L3", "≥ 3/4 năm ROI stress > 0", "%d/4" % v["n_year_pos"], "PASS" if v["L3"] else "FAIL"],
            ["L4", "Calmar ghép S ≥ Calmar nền S & corr S ≤ 0,5", "%s vs %s; %s" % (
                f2(pf["comb_s_calmar"]["mean"], 3), f2(pf["base_s_calmar"]["mean"], 3), f2(pf["corr_s"]["mean"], 3)),
             "PASS" if v["L4"] else "FAIL"]]
    L += tbl(["luật", "điều kiện", "số", "kết quả"], rows)
    L += ["", "**%s**" % ("DEV GO → holdout 2026 theo pre-reg." if v["GO"] else
                          "DEV NO-GO → không mở holdout 2026, dừng (theo pre-reg).")]
    open(MD_OUT, "w").write("\n".join(L) + "\n")
    log.info("ghi %s", MD_OUT)


def main():
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    os.makedirs(W, exist_ok=True)
    heavy = st in ("sig", "path", "eval", "all")
    if heavy:
        take_lock("qs1-" + st)
    try:
        if st in ("sig", "all"):
            stage_sig()
        if st in ("path", "all"):
            stage_path()
        if st in ("eval", "all"):
            stage_eval()
        if st == "md":
            write_md(json.load(open(JSON_OUT)))
    finally:
        if heavy:
            drop_lock()


if __name__ == "__main__":
    main()
