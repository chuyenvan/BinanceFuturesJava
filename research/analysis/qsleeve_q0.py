#!/usr/bin/env python3
"""qsleeve_q0.py -- QS0 chan doan "quiet sleeve" (co che DOC LAP vao lenh nho o giai doan yen).

CHI phan tich du lieu/output co san: 0 sim, 0 Kaggle, 0 Java, 0 cham 242/shadow, DEV <= 2025-12-31 (bar >= T26 bi cat).
KHONG mo ~/kaggle_sim/out/nsel-nen-*, nsel-m1-*, nsel-m2-*, nsel-m1b-*, nsel-m2b-* (guard() chan cung).
Chan doan: moi luoi KHAI TRUOC, khong chon nguong, khong tune sau khi thay so.

KHAI TRUOC (chot trong code truoc khi do):
  leg0       = chan dau cum (sym, end) trong printDone nen (moi level; leg0 khong bao gio la DCA).
  Q1         = X in {24,72,168}h; cua so yen = khoang giua 2 leg0 lien tiep (+ duoi den T26) dai >= X; dem theo nam
               local cua diem dau, thoi luong cat theo nam; % phut so trong = phut khong cum nao mo.
  phut yen   = (t - leg0 gan nhat <= t) >= 24h (X nho nhat cua luoi). Tang tuoi yen: [24,72), [72,168), >=168h.
  Q3         = r = p15/(max(0.26787, sp/0.15*1.2876)*1.55) tren o hop le top-K (gate_offline: bo coin nen dang giu);
               K in {24,32,50}; nguong sleeve = phan vi nearest-rank pct in {0.999,0.9995,0.9999} cua r tren o hop le
               tai PHUT YEN trong 90 ngay UTC TRUOC ngay hien tai, cap nhat 1 lan/ngay (causal), warm-up >= 7 ngay tu
               ngay yen dau tien va m >= 1000. Ung vien = o yen co r >= nguong. Khu trung: trong 1 phut lay r lon nhat
               con hop le; coin khong vao lai trong 24h (tu lan vao truoc cua sleeve); >= 60' giua 2 lenh sleeve.
               q_core = q cua gate_offline.run_g2 (K24, pct 0.999950829, KHONG mask so day: xap xi).
  Q4 proxy   = vao o close nen 1m quyet dinh; thoat (doc SimulatorMarketLevelTicker1MStopLoss + OrderTargetInfoTest):
               moi nen sau nen vao: (1) chua arm & t-t0 > 168h -> dong min(open,close); (2) chua arm & high/E-1 > 0.07
               -> arm, SL = E*(1+round((peak-min(peak,0.03))/0.005)*0.005), KHONG thoat cung nen; (3) da arm: thoat neu
               low <= SL truoc do (hoac nen truoc vua doi SL ma close <= SL) tai min(SL, open); sau do ratchet SL theo
               high nen. KHONG DCA, KHONG funding, KHONG SL cung. Chi phi = RATE_FEE 0.000982 (2 chan, calTp tru 1 lan)
               + 2*SLIPPAGE 0.000067 = 0.1116% notional. Co sap = close/open-1 <= -1% nen quyet dinh; stress -1.675pp.
  Hieu chuan = cung proxy tren leg0 PRED that cua nen (8 seed, entry 2022-25); so ROI gop proxy vs profit printDone.
               KHONG DANG TIN neu |lech TB| > 1pp/lenh hoac pearson < 0.5 (tren TOAN BO leg0 PRED; tap khong-DCA bao them).
  Q5         = ngay local GMT+7; MTM nen = 35000 + sum pnl da dong + sum qty*(close 16:59 UTC - entry) chan dang mo.
  Inflate CI = half-width * sqrt(2 ln k), k = so o da nhin (9 o K x pct; 27 o K x pct x tang tuoi).
Stage: prep | cand | q6 | path | report | all.  Output: docs/audit/QSLEEVE_Q0_20261008.{md,json}
"""
import gzip
import hashlib
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
HERE = REPO + "/research/analysis"
sys.path.insert(0, HERE)
import gate_offline as GO  # noqa: E402
import jbin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("qs0")

W = HOME + "/claude_master/1008/qs0"
OUTK = HOME + "/kaggle_sim/out/"
TICK = HOME + "/kaggle_data_hpo"
JSON_OUT = REPO + "/docs/audit/QSLEEVE_Q0_20261008.json"
MD_OUT = REPO + "/docs/audit/QSLEEVE_Q0_20261008.md"
LOCK = HOME + "/claude_master/1002/oracle_heavy.lock"
NSEL_W = HOME + "/claude_master/1008/nsel"
NDEEP_BAR = HOME + "/claude_master/1008/ndeep/bar.json"
FORBID = ("nsel-nen-", "nsel-m1-", "nsel-m2-", "nsel-m1b-", "nsel-m2b-")
SEEDS = {"A1": "gqsf-a1", "S7": "gqsf-s7", "S13": "gqsf-s13", "S21": "gqsf-s21", "S99": "gqsf-s99",
         "S123": "gqsf-s123", "S777": "gqsf-s777", "S2024": "gqsf-s2024"}
DARM = {"A1": ("gqsf-a1", "gkf-l2-k32"), "S7": ("gqsf-s7", "gkf2-l2k32-s7"), "S21": ("gqsf-s21", "gkf2-l2k32-s21")}
KS, PCTS, XS = (24, 32, 50), (0.999, 0.9995, 0.9999), (24, 72, 168)
QX, KC, JD = 24, 50, 8192
AGES = ((24, 72), (72, 168), (168, np.inf))
H, D, MN = 3600000, 86400000, 60000
TZ = 7 * H
T22, T26 = 1640970000000, 1767200400000          # 2022-01-01 / 2026-01-01 00:00 GMT+7
YEARS = (2022, 2023, 2024, 2025)
YB = {y: int(pd.Timestamp("%d-01-01" % y).value // 10 ** 6) - TZ for y in range(2021, 2027)}
CAP0 = 35000.0
COST = 0.000982 + 2 * 0.000067
ARM, GAP, STEP, TSTOP = 0.07, 0.03, 0.005, 168
PEN, CRASH = 0.01675, -0.01


def guard(tag):
    if any(tag.startswith(f) for f in FORBID):
        raise SystemExit("CAM mo run %s (dang cho cham chinh thuc)" % tag)


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


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
    if os.path.exists(LOCK) and open(LOCK).read().startswith("qs0"):
        os.remove(LOCK)


def yr_of(ms):
    return pd.to_datetime(np.asarray(ms, np.int64) + TZ, unit="ms").year.to_numpy()


def load_pd(tag, s2id=None):
    """printDone -> bang chan; s_ms/e_ms = ms UTC dau phut (gio local -7h); pid = cum (sym, end); leg0 = chan dau cum."""
    guard(tag)
    f = OUTK + tag + "/storage/printDone.csv"
    raw = pd.read_csv(f, on_bad_lines="skip")
    raw.columns = [c.strip() for c in raw.columns]
    for c in ("quantity", "entry", "margin", "pnl", "profit"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    ts = pd.to_datetime(raw["start"].astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    te = pd.to_datetime(raw["end"].astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    ok = (raw[["quantity", "entry", "pnl", "profit"]].notna().all(axis=1).to_numpy() & ts.notna().to_numpy()
          & te.notna().to_numpy())
    d = raw[ok].copy()
    d["row"] = np.arange(len(raw))[ok]
    d["s_ms"] = ts[ok].values.astype("datetime64[ms]").astype(np.int64) - TZ
    d["e_ms"] = te[ok].values.astype("datetime64[ms]").astype(np.int64) - TZ
    d["sym"] = d["sym"].astype(str).str.strip()
    d["level"] = d["level"].astype(str).str.strip()
    d["lt"] = np.where(d["level"] == "PREDICT_SYMBOL_TRADE", "PRED", np.where(d["level"] == "BIG_DOWN", "BIGD", "DCA"))
    d["year"] = ts[ok].dt.year.to_numpy()
    d["notional"] = (d["quantity"] * d["entry"]).astype(float)
    d = d.sort_values(["s_ms", "row"], kind="mergesort").reset_index(drop=True)
    d["pid"] = d.groupby(["sym", "e_ms"], sort=False).ngroup()
    d["leg0"] = ~d.duplicated("pid", keep="first")
    d["nleg"] = d.groupby("pid")["pid"].transform("size")
    if s2id is not None:
        d["sid"] = d["sym"].map(s2id)
    rj = json.load(open(OUTK + tag + "/result.json"))
    meta = dict(tag=tag, md5=md5f(f), n_raw=int(len(raw)), n=int(len(d)), n_result=rj.get("n_trades"),
                pred_md5_used=rj.get("pred_md5_used"), pred_md5_base=rj.get("pred_md5_base"),
                leg0_dca=int(((d["lt"] == "DCA") & d["leg0"]).sum()))
    return d, meta


def merge_iv(s, e):
    o = np.argsort(s, kind="mergesort")
    s, e = s[o], e[o]
    out, cs, ce = [], int(s[0]), int(e[0])
    for a, b in zip(s[1:].tolist(), e[1:].tolist()):
        if a <= ce:
            ce = max(ce, b)
        else:
            out.append((cs, ce))
            cs, ce = a, b
    out.append((cs, ce))
    return np.array(out, np.int64)


def ovl(a0, a1, b0, b1):
    """tong do dai giao cua cac khoang [a0,a1) voi [b0,b1) (vector a, vo huong b)."""
    return np.clip(np.minimum(a1, b1) - np.maximum(a0, b0), 0, None)


def q1(d):
    l0 = np.sort(d.loc[d["leg0"], "s_ms"].to_numpy())
    cl = d.groupby("pid").agg(s=("s_ms", "min"), e=("e_ms", "max"))
    iv = merge_iv(cl["s"].to_numpy(), cl["e"].to_numpy())
    grid = np.zeros((T26 - T22) // MN, bool)
    for a, b in iv.tolist():
        a2, b2 = max(a, T22), min(b, T26)
        if b2 > a2:
            grid[(a2 - T22) // MN:(b2 - T22) // MN] = True
    st, en = l0, np.append(l0[1:], T26)
    gap = (en - st) / H
    yr_next = yr_of(en)
    gin = (en > T22) & (en < T26)
    out = dict(year={}, check={})
    for y in YEARS:
        a, b = max(YB[y], T22), min(YB[y + 1], T26)
        tot = b - a
        cov = int(ovl(iv[:, 0], iv[:, 1], a, b).sum())
        gcov = int(grid[(a - T22) // MN:(b - T22) // MN].sum()) * MN
        gy = gap[gin & (yr_next == y) & (en < T26)]          # khoang giua 2 leg0 that (bo duoi kiem duyet)
        r = dict(empty_pct=100.0 * (1 - cov / tot), empty_grid_pct=100.0 * (1 - gcov / tot),
                 n_leg0=int(((l0 >= a) & (l0 < b)).sum()),
                 gap_h=dict(zip(("p10", "p25", "p50", "p75", "p90", "p99", "max"),
                                np.percentile(gy, [10, 25, 50, 75, 90, 99, 100]).tolist())) if len(gy) else None,
                 gap_ge={X: float((gy >= X).mean()) for X in XS} if len(gy) else None, X={})
        for X in XS:
            w = gap >= X
            r["X"][X] = dict(n=int((w & (st >= a) & (st < b)).sum()),
                             dur_h=float(ovl(st[w], en[w], a, b).sum() / H),
                             dur_pct=100.0 * float(ovl(st[w], en[w], a, b).sum() / tot),
                             quiet_pct=100.0 * float(ovl(st[w] + X * H, en[w], a, b).sum() / tot))
        out["year"][y] = r
    a = max(T22, int(l0[0]))
    out["check"] = dict(empty_grid_eq=all(abs(out["year"][y]["empty_pct"] - out["year"][y]["empty_grid_pct"]) < 1e-9
                                          for y in YEARS),
                        sum_gaps_eq_span=int(ovl(st, en, T22, T26).sum()) == T26 - a,
                        days_with_pos=int(len(np.unique(np.concatenate([np.arange((s + TZ) // D, (e - 1 + TZ) // D + 1)
                                                                        for s, e in iv.tolist()])))))
    return out, l0, iv


# ---------------------------------------------------------------- prep / build
def stage_prep():
    os.makedirs(W, exist_ok=True)
    GO.CACHE, GO.K_CACHE = W, KC                  # cache TU TAO (K=50 > K_CACHE 48 cua gqd)
    if os.path.exists(W + "/cand_base.npz"):
        log.info("cache %s co san", W + "/cand_base.npz")
        return
    GO.prep()


def s2id_map():
    mp = pd.read_csv(GO.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    return s2id, {v: k for k, v in s2id.items()}


def build(seed, B, s2id):
    pth = GO.SEEDS[seed][1]
    pts, p15 = GO.load_pred(pth)
    mts, fi = B["mts"], B["fi"]
    j = np.minimum(np.searchsorted(pts, mts), len(pts) - 1)
    has = pts[j] == mts
    ts, p, f = mts[has], p15[j[has]], fi[has]
    SP, SY = B["SP15"][f], B["SY15"][f]
    d, meta = load_pd(SEEDS[seed], s2id)
    lock = GO.lock_mask(ts, SY, d)
    valid = ~np.isnan(SP) & ~lock & np.isfinite(p)[:, None]
    fac = np.maximum(GO.DYN_MIN, (SP / GO.SCORE_BASE) * GO.DYN_MULT)
    r = (p[:, None] / (fac * GO.GS)).astype(np.float32)
    del fac
    meta["pred_md5"] = md5f(pth)
    meta["pred_ok"] = meta["pred_md5"] == (meta["pred_md5_used"] or meta["pred_md5_base"])
    return dict(ts=ts, p15=p, SP=SP, SY=SY, valid=valid, lock=lock, r=r), d, meta


def qd(v, qs=(50, 90, 99, 99.9)):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return None
    return dict(n=int(len(v)), **{"p%s" % q: float(np.percentile(v, q)) for q in qs}, max=float(v.max()))


def thresholds(C, quiet, K, du, ub):
    """nguong sleeve theo ngay UTC u: phan vi cua r (o hop le top-K, phut yen) trong ngay [u-90, u-1]."""
    tops, cnt = {}, {}
    for u, a, b in ub:
        qr = quiet[a:b]
        v = C["r"][a:b, :K][qr][C["valid"][a:b, :K][qr]]
        cnt[u] = len(v)
        tops[u] = v if len(v) <= JD else np.partition(v, len(v) - JD)[len(v) - JD:]
    qdays = [u for u, _, _ in ub if cnt[u] > 0]
    first = qdays[0] if qdays else None
    thr = {p: {} for p in PCTS}
    jmax = 0
    for u, _, _ in ub:
        if first is None or u - first < 7:
            continue
        win = [w for w in range(u - 90, u) if w in cnt and cnt[w] > 0]
        m = sum(cnt[w] for w in win)
        if m < 1000:
            continue
        x = np.concatenate([tops[w] for w in win])
        idx = []
        for p in PCTS:
            jj = m - 1 - int(math.floor(p * (m - 1)))
            assert jj < JD, (jj, JD)
            jmax = max(jmax, jj)
            idx.append(len(x) - 1 - jj)
        xs = np.partition(x, idx)
        for p, i in zip(PCTS, idx):
            thr[p][u] = float(xs[i])
    return thr, jmax


def candidates(C, quiet, age, qm, K, thr_p, ub, id2s, seed, pct):
    """o yen co r >= nguong ngay -> khu trung (r max trong phut; coin 24h; >= 60' giua 2 lenh)."""
    T, R, S = [], [], []
    n_cells = 0
    for u, a, b in ub:
        th = thr_p.get(u)
        if th is None:
            continue
        rows = np.arange(a, b)
        ok = (C["ts"][a:b] >= T22) & (C["ts"][a:b] < T26) & quiet[a:b]
        if not ok.any():
            continue
        M = C["valid"][a:b, :K] & ok[:, None] & (C["r"][a:b, :K] >= np.float32(th))
        ii, cc = np.nonzero(M)
        n_cells += len(ii)
        T.append(rows[ii]); R.append(C["r"][rows[ii], cc]); S.append(cc)
    if not T:
        return pd.DataFrame(), n_cells
    I, RR, CC = np.concatenate(T), np.concatenate(R), np.concatenate(S)
    o = np.lexsort((-RR, I))
    I, RR, CC = I[o], RR[o], CC[o]
    acc, last, lsym = [], -10 ** 18, {}
    for i, rv, c in zip(I.tolist(), RR.tolist(), CC.tolist()):
        t = int(C["ts"][i])
        if t - last < 60 * MN:
            continue
        sid = int(C["SY"][i, c])
        if t - lsym.get(sid, -10 ** 18) < 24 * H:
            continue
        acc.append((i, c, rv))
        last, lsym[sid] = t, t
    i = np.array([a[0] for a in acc], np.int64)
    c = np.array([a[1] for a in acc], np.int64)
    sids = C["SY"][i, c].astype(int)
    du = C["ts"][i] // D
    df = pd.DataFrame(dict(seed=seed, K=K, pct=pct, ts=C["ts"][i], sid=sids, sym=[id2s.get(s, "?") for s in sids],
                           rank=c + 1, r=np.array([a[2] for a in acc]), thr=[thr_p[u] for u in du.tolist()],
                           qcore=qm[i], age=age[i], sp=C["SP"][i, c], p15=C["p15"][i]))
    return df, n_cells


def base_wouldpass(C, d, qm):
    """kiem thuoc: leg0 PRED nen 2022-25 -> o (phut, rank<=24), r >= q_core?"""
    x = d[d["leg0"] & (d["lt"] == "PRED") & d["year"].between(2022, 2025)]
    n = hit = cell = 0
    for s, sid in zip(x["s_ms"].tolist(), x["sid"].tolist()):
        i = int(np.searchsorted(C["ts"], s))
        n += 1
        if i >= len(C["ts"]) or C["ts"][i] != s or not np.isfinite(sid):
            continue
        w = np.nonzero(C["SY"][i, :24] == int(sid))[0]
        if len(w) == 0:
            continue
        cell += 1
        hit += bool(C["r"][i, w[0]] >= qm[i])
    return dict(n=n, cell=cell, would=hit, would_share=hit / max(1, cell))


def rdist(C, quiet, age, qm, warm, K, yr):
    rk = np.where(C["valid"][:, :K], C["r"][:, :K], -np.inf).max(1)
    w = (yr >= 2022) & (yr <= 2025) & ~warm & np.isfinite(rk)
    act = w & np.isfinite(age) & (age < QX)
    qq = w & quiet
    out = dict(quiet=dict(rmax=qd(rk[qq]), ratio=qd(rk[qq] / qm[qq], (50, 90, 99, 99.9)),
                          ge1=float((rk[qq] >= qm[qq]).mean()) if qq.any() else None, n_min=int(qq.sum())),
               active=dict(rmax=qd(rk[act]), ratio=qd(rk[act] / qm[act], (50, 90, 99, 99.9)),
                           ge1=float((rk[act] >= qm[act]).mean()) if act.any() else None, n_min=int(act.sum())),
               year={})
    for y in YEARS:
        s = qq & (yr == y)
        out["year"][y] = dict(n_min=int(s.sum()), ratio_p50=float(np.median(rk[s] / qm[s])) if s.any() else None,
                              ratio_p99=float(np.percentile(rk[s] / qm[s], 99)) if s.any() else None)
    return out


def stage_cand(only=None):
    B = dict(np.load(W + "/cand_base.npz"))
    assert B["SP15"].shape[1] >= KC, B["SP15"].shape
    s2id, id2s = s2id_map()
    for seed in SEEDS:
        if only and seed not in only:
            continue
        outp = W + "/cand_%s.pkl" % seed
        if os.path.exists(outp):
            log.info("%s co san", outp)
            continue
        t0 = time.time()
        C, d, meta = build(seed, B, s2id)
        res = dict(meta=meta)
        res["q1"], l0, iv = q1(d)
        i = np.searchsorted(l0, C["ts"], "right") - 1
        age = np.where(i >= 0, (C["ts"] - l0[np.maximum(i, 0)]) / H, np.nan)
        quiet = np.nan_to_num(age, nan=-1.0) >= QX
        G = GO.run_g2(dict(ts=C["ts"], p15=C["p15"], SP=C["SP"][:, :24], valid=C["valid"][:, :24],
                           lock=C["lock"][:, :24]))
        qm, warm = G["qm"], G["warm"]
        del G
        yr = yr_of(C["ts"])
        res["wouldpass"] = base_wouldpass(C, d, qm)
        du = C["ts"] // D
        uu, st = np.unique(du, return_index=True)
        ub = list(zip(uu.tolist(), st.tolist(), np.append(st[1:], len(du)).tolist()))
        res["rdist"], res["thr"], res["ncells"], res["jmax"] = {}, {}, {}, {}
        cands = []
        q0 = {u: float(qm[a]) for u, a, b in ub}
        for K in KS:
            res["rdist"][K] = rdist(C, quiet, age, qm, warm, K, yr)
            thr, res["jmax"][K] = thresholds(C, quiet, K, du, ub)
            for p in PCTS:
                rat = [thr[p][u] / q0[u] for u in thr[p] if T22 <= u * D + D and u * D < T26 and q0[u] > 0]
                res["thr"]["%d|%s" % (K, p)] = dict(n_days=len(thr[p]), thr_over_qcore=qd(rat, (10, 50, 90)))
                df, nc = candidates(C, quiet, age, qm, K, thr[p], ub, id2s, seed, p)
                res["ncells"]["%d|%s" % (K, p)] = nc
                cands.append(df)
                log.info("%s K%d pct%s: o %d -> lenh %d", seed, K, p, nc, len(df))
        cand = pd.concat(cands, ignore_index=True)
        res["dedup_ok"] = dedup_check(cand)
        res["secs"] = time.time() - t0
        pd.to_pickle(dict(res=res, cand=cand), outp)
        log.info("%s xong %.0fs, would %s, pred_ok %s", seed, res["secs"], res["wouldpass"], meta["pred_ok"])
        del C


def dedup_check(cand):
    ok = True
    for _, g in cand.groupby(["seed", "K", "pct"]):
        t = np.sort(g["ts"].to_numpy())
        ok &= bool((np.diff(t) >= 60 * MN).all())
        for _, gs in g.groupby("sid"):
            ok &= bool((np.diff(np.sort(gs["ts"].to_numpy())) >= 24 * H).all())
        ok &= bool((g["age"] >= QX).all() and (g["r"] >= g["thr"].astype(np.float32)).all())
    return ok


# ---------------------------------------------------------------- Q6: tai hien J4 p2 >= 96h (arm D, MOI)
def match1(b, a, tol=1):
    """khop 1-1 tham lam theo (|dphut|, i_nen, i_arm), khoa sym, |dphut| <= tol (viet lai doc lap, y NSEL J1)."""
    P = pd.DataFrame(dict(k=b["sym"].to_numpy(), mb=(b["s_ms"] // MN).to_numpy(), ib=np.arange(len(b)))).merge(
        pd.DataFrame(dict(k=a["sym"].to_numpy(), ma=(a["s_ms"] // MN).to_numpy(), ia=np.arange(len(a)))), on="k")
    P["dm"] = (P["ma"] - P["mb"]).abs()
    P = P[P["dm"] <= tol].sort_values(["dm", "ib", "ia"], kind="mergesort")
    b2a, a2b = np.full(len(b), -1), np.full(len(a), -1)
    for ib, ia in zip(P["ib"].to_numpy(), P["ia"].to_numpy()):
        if b2a[ib] < 0 and a2b[ia] < 0:
            b2a[ib], a2b[ia] = ia, ib
    return b2a, a2b


def stage_q6():
    out = {}
    J = pd.read_csv(NSEL_W + "/j4_rows.csv.gz")
    x = J[(J["arm"] == "D") & (J["grp"] == "MOI") & (J["p2"] >= 96)]
    out["from_nsel_rows"] = dict(n=int(len(x)), n_per_year=len(x) / 12.0, roi_s=float(x["roi_s"].mean()),
                                 lt={k: dict(n=int(len(g)), roi_s=float(g["roi_s"].mean()),
                                             crash=float(g["crash"].mean())) for k, g in x.groupby("lt")},
                                 seed={k: dict(n=int(len(g)), roi_s=float(g["roi_s"].mean())) for k, g in x.groupby("seed")},
                                 crash=float(x["crash"].mean()))
    bar = json.load(open(NDEEP_BAR))["bar"]
    day0 = int(pd.Timestamp("2021-07-01").value // 60_000_000_000)
    rows = []
    for seed, (nt, at) in DARM.items():
        b, _ = load_pd(nt)
        a, ma = load_pd(at)
        _, a2b = match1(b, a, 1)
        l0 = np.sort(a.loc[a["leg0"], "s_ms"].to_numpy())
        t = a["s_ms"].to_numpy()
        i = np.searchsorted(l0, t, "left") - 1
        a["p2"] = np.where(i >= 0, (t - l0[np.maximum(i, 0)]) / H, np.inf)
        oc = [bar.get("%s|%d" % (s, m - day0)) for s, m in zip(a["sym"].tolist(), (t // MN).tolist())]
        a["bar_miss"] = [v is None for v in oc]
        a["br"] = [v[1] / v[0] - 1.0 if v is not None and v[0] > 0 else np.nan for v in oc]
        a["crash"] = (a["br"] <= CRASH).to_numpy()
        a["roi_s"] = 100.0 * (a["pnl"] - PEN * a["notional"] * a["crash"]) / a["notional"]
        a["seed"] = seed
        a["moi"] = a2b < 0
        rows.append(a[a["moi"] & a["year"].between(2022, 2025)])
    R = pd.concat(rows, ignore_index=True)
    y = R[R["p2"] >= 96]
    out["recompute"] = dict(n=int(len(y)), n_per_year=len(y) / 12.0, roi_s=float(y["roi_s"].mean()),
                            bar_miss=int(y["bar_miss"].sum()), crash=float(y["crash"].mean()),
                            lt={k: dict(n=int(len(g)), n_per_year=len(g) / 12.0, roi_s=float(g["roi_s"].mean()),
                                        profit=float(g["profit"].mean()), crash=float(g["crash"].mean()),
                                        leg0=int(g["leg0"].sum())) for k, g in y.groupby("lt")})
    a0 = out["from_nsel_rows"]
    out["match_pass"] = bool(abs(len(y) - a0["n"]) <= 0.02 * a0["n"] and abs(out["recompute"]["roi_s"] - a0["roi_s"]) <= 0.05)
    p = y[(y["lt"] == "PRED") & y["leg0"]]
    out["pred_leg0"] = dict(n=int(len(p)), n_per_year=len(p) / 12.0, roi_s=float(p["roi_s"].mean()),
                            profit=float(p["profit"].mean()), crash=float(p["crash"].mean()),
                            nleg_gt1=float((p["nleg"] > 1).mean()))
    pd.to_pickle(dict(out=out, pred=p[["seed", "sym", "s_ms", "e_ms", "entry", "profit", "pnl", "notional", "crash",
                                       "roi_s", "nleg", "p2"]]), W + "/q6.pkl")
    log.info("Q6 %s", json.dumps(out, default=str)[:1500])


# ---------------------------------------------------------------- path: proxy thoat lenh tren nen 1m (stream theo ngay UTC)
def parse_day(day):
    """1 ngay ticker UTC -> (syms, A[5,1440,nsym] = open/high/low/close/vol, so nen sai OHLC). Bar >= T26 bi bo."""
    p = TICK + "/ticker_%s.bin.gz" % day
    if not os.path.exists(p):
        return day, None
    U0 = int(pd.Timestamp(day).value // 10 ** 6)
    with gzip.open(p, "rb") as f:
        b = f.read()
    syms, R, Cc, V = {}, [], [], []
    for k, v in jbin.iter_minutes(b):
        mi = (k - U0) // MN
        if mi < 0 or mi >= 1440 or k >= T26:
            continue
        for s, t in v.items():
            R.append(mi)
            Cc.append(syms.setdefault(s, len(syms)))
            V.append(t)
    A = np.full((5, 1440, max(1, len(syms))), np.nan, np.float32)
    bad = 0
    if R:
        R, Cc, X = np.array(R), np.array(Cc), np.array(V, np.float64)
        for j, src in enumerate((4, 1, 2, 3, 5)):        # tuple jbin = (start, max, min, close, open, vol)
            A[j, R, Cc] = X[:, src]
        bad = int(((X[:, 2] > X[:, 4] + 1e-12) | (X[:, 2] > X[:, 3] + 1e-12) | (X[:, 1] < X[:, 4] - 1e-12)
                   | (X[:, 1] < X[:, 3] - 1e-12)).sum())
    return day, (list(syms), A, bad)


def trail(x):
    return np.floor((x - np.minimum(x, GAP)) / STEP + 0.5) * STEP


def fin(s, k, px, why, l, h, tm):
    s["minL"] = min(s["minL"], float(l[:k + 1].min()))
    s["maxH"] = max(s["maxH"], float(h[:k + 1].max()))
    s["exit_t"], s["px"], s["why"], s["done"] = int(tm[k]), float(px), why, True


def seg(s, h, l, o, c, tm):
    """1 doan nen hop le lien tiep cua 1 lenh. Tra chi so nen thoat (trong doan) hoac -1."""
    n = len(h)
    if n == 0:
        return -1
    E, i = s["E"], 0
    if not s["armed"]:
        hr = h / E - 1.0
        tsb = np.flatnonzero(tm - s["t0"] > TSTOP * H)
        ab = np.flatnonzero(hr > ARM)
        its = int(tsb[0]) if len(tsb) else n
        ia = int(ab[0]) if len(ab) else n
        if its < n and its <= ia:
            fin(s, its, min(o[its], c[its]), "time", l, h, tm)
            return its
        if ia == n:
            s["minL"], s["maxH"], s["lastc"] = min(s["minL"], float(l.min())), max(s["maxH"], float(h.max())), float(c[-1])
            return -1
        s["armed"], s["sl"] = True, float(trail(hr[ia]))
        s["pend"] = bool(c[ia] <= E * (1 + s["sl"]))
        s["minL"], s["maxH"] = min(s["minL"], float(l[:ia + 1].min())), max(s["maxH"], float(h[:ia + 1].max()))
        s["lastc"] = float(c[ia])
        i = ia + 1
        if i >= n:
            return -1
    hr = h[i:] / E - 1.0
    tr = np.where(hr >= ARM, trail(hr), -np.inf)
    after = np.maximum.accumulate(np.maximum(tr, s["sl"]))
    before = np.concatenate(([s["sl"]], after[:-1]))
    reset = after > before
    pb = np.concatenate(([s["pend"]], (reset & (c[i:] <= E * (1 + after)))[:-1]))
    ex = (l[i:] <= E * (1 + before)) | pb
    k = np.flatnonzero(ex)
    if len(k):
        k = int(k[0])
        fin(s, i + k, min(E * (1 + before[k]), float(o[i + k])), "trail", l, h, tm)
        return i + k
    s["sl"] = float(after[-1])
    s["pend"] = bool(reset[-1] and c[-1] <= E * (1 + after[-1]))
    s["minL"], s["maxH"], s["lastc"] = min(s["minL"], float(l.min())), max(s["maxH"], float(h.max())), float(c[-1])
    return -1


def new_state(sym, t0):
    return dict(sym=sym, t0=int(t0), E=np.nan, armed=False, sl=-np.inf, pend=False, minL=np.inf, maxH=-np.inf,
                lastc=np.nan, mark=np.nan, done=False, exit_t=None, px=np.nan, why=None, br=np.nan, vol=np.nan,
                cut=False, nobar=False, inc=[])


def collect():
    """lenh can proxy: ung vien Q3 (8 seed x 9 o), leg0 PRED nen 2022-25 (8 seed), leg0 PRED MOI p2>=96h (Q6)."""
    keys, tid = [], {}

    def tid_of(sym, t):
        k = (sym, int(t))
        if k not in tid:
            tid[k] = len(keys)
            keys.append(k)
        return tid[k]
    cand = pd.concat([pd.read_pickle(W + "/cand_%s.pkl" % s)["cand"] for s in SEEDS], ignore_index=True)
    cand["tid"] = [tid_of(s, t) for s, t in zip(cand["sym"], cand["ts"])]
    base, legs = [], []
    for seed, tag in SEEDS.items():
        d, _ = load_pd(tag)
        x = d[d["leg0"] & (d["lt"] == "PRED") & d["year"].between(2022, 2025)].copy()
        x["seed"] = seed
        x["tid"] = [tid_of(s, t) for s, t in zip(x["sym"], x["s_ms"])]
        base.append(x[["seed", "sym", "s_ms", "e_ms", "entry", "profit", "pnl", "notional", "nleg", "year", "tid"]])
        legs.append(d[["sym", "s_ms", "e_ms", "entry", "quantity", "pnl", "pid", "leg0"]].assign(seed=seed))
    q6 = pd.read_pickle(W + "/q6.pkl")["pred"].copy()
    q6["tid"] = [tid_of(s, t) for s, t in zip(q6["sym"], q6["s_ms"])]
    return keys, cand, pd.concat(base, ignore_index=True), pd.concat(legs, ignore_index=True), q6


def stage_path(workers=3):
    keys, cand, base, legs, q6 = collect()
    log.info("PATH: %d lenh duy nhat (ung vien %d dong, nen %d, q6 %d), chan MTM %d", len(keys), len(cand),
             len(base), len(q6), len(legs))
    S = [new_state(s, t) for s, t in keys]
    order = sorted(range(len(S)), key=lambda j: S[j]["t0"])
    ptr, active = 0, []
    seeds = list(SEEDS)
    lg_seed = legs["seed"].map({s: i for i, s in enumerate(seeds)}).to_numpy()
    lg_sym = (legs["sym"] + "USDT").to_numpy()
    usym, lg_u = np.unique(lg_sym, return_inverse=True)
    lastpx = np.full(len(usym), np.nan)
    ls, le = legs["s_ms"].to_numpy(), legs["e_ms"].to_numpy()
    lq, len_, lp = legs["quantity"].to_numpy(float), legs["entry"].to_numpy(float), legs["pnl"].to_numpy(float)
    eq = {s: {} for s in seeds}
    u0, u1 = T22 // D, (T26 - 1) // D
    days = [pd.Timestamp(u * D, unit="ms").strftime("%Y%m%d") for u in range(u0, u1 + 1)]
    ck = dict(days=len(days), missing_days=[], bad_ohlc=0, nobar=0, cut=0)
    t_start = time.time()
    with Pool(workers) as pool:
        for di, (day, got) in enumerate(pool.imap(parse_day, days, chunksize=1)):
            u = u0 + di
            U0 = u * D
            assert pd.Timestamp(U0, unit="ms").strftime("%Y%m%d") == day
            if got is None:
                ck["missing_days"].append(day)
                continue
            syms, A, bad = got
            ck["bad_ohlc"] += bad
            ix = {s: j for j, s in enumerate(syms)}
            O, Hh, L, Cc, V = A
            lim = min(1440, (T26 - U0) // MN)
            tm_all = U0 + np.arange(1440, dtype=np.int64) * MN
            vc = ~np.isnan(Cc[:min(lim, 1020)])
            lastidx = np.where(vc, np.arange(vc.shape[0])[:, None], -1).max(0)
            bnd = lim >= 1020
            while ptr < len(order) and S[order[ptr]]["t0"] < U0 + D:
                j = order[ptr]
                ptr += 1
                s = S[j]
                ie = (s["t0"] - U0) // MN
                col = ix.get(s["sym"] + "USDT")
                if s["t0"] < U0 or col is None or ie >= lim or np.isnan(Cc[ie, col]):
                    s["nobar"] = True
                    ck["nobar"] += 1
                    continue
                s["E"] = s["mark"] = s["lastc"] = float(Cc[ie, col])
                s["br"], s["vol"], s["st"] = float(Cc[ie, col] / O[ie, col] - 1.0), float(V[ie, col]), ie + 1
                active.append(j)
            still = []
            for j in active:
                s = S[j]
                st = s.pop("st", 0)
                col = ix.get(s["sym"] + "USDT")
                kx = -1
                if col is not None and st < lim:
                    rr = np.flatnonzero(~np.isnan(Cc[st:lim, col])) + st
                    if len(rr):
                        k = seg(s, Hh[rr, col], L[rr, col], O[rr, col], Cc[rr, col], tm_all[rr])
                        kx = int(rr[k]) if k >= 0 else -1
                m = float(Cc[lastidx[col], col]) if (col is not None and lastidx[col] >= 0) else s["mark"]
                E = s["E"]
                if bnd and st <= 1020 and (kx < 0 or kx > 1019):
                    s["inc"].append((u, (m - s["mark"]) / E))
                    s["mark"] = m
                if kx >= 0:
                    s["inc"].append((u if kx <= 1019 else u + 1, (s["px"] - s["mark"]) / E - COST))
                else:
                    still.append(j)
            active = still
            if bnd:
                cols = np.array([ix.get(x, -1) for x in usym])
                li = np.where(cols >= 0, lastidx[np.maximum(cols, 0)], -1)
                okp = li >= 0
                lastpx[okp] = Cc[li[okp], cols[okp]]
                b = U0 + 1019 * MN
                op, rl = (ls <= b) & (le > b), le <= b
                px = lastpx[lg_u]
                ck["mtm_px_missing"] = ck.get("mtm_px_missing", 0) + int((op & np.isnan(px)).sum())
                unrl = np.where(op & np.isfinite(px), lq * (px - len_), 0.0)
                for si, sd in enumerate(seeds):
                    msk = lg_seed == si
                    eq[sd][u] = CAP0 + float(lp[msk & rl].sum()) + float(unrl[msk].sum())
            if di % 50 == 0:
                log.info("PATH %s (%d/%d) active %d, xong %d, %.0fs", day, di, len(days), len(active), ptr,
                         time.time() - t_start)
    for j in active:
        s = S[j]
        s["cut"], s["done"], s["exit_t"], s["px"], s["why"] = True, True, T26, s["lastc"], "cut"
        s["inc"].append((u1, (s["px"] - s["mark"]) / s["E"] - COST))
        ck["cut"] += 1
    R = pd.DataFrame(dict(tid=np.arange(len(S)), sym=[s["sym"] for s in S], t0=[s["t0"] for s in S],
                          E=[s["E"] for s in S], br=[s["br"] for s in S], vol=[s["vol"] for s in S],
                          exit_t=[s["exit_t"] if s["exit_t"] is not None else -1 for s in S],
                          px=[s["px"] for s in S], why=[s["why"] for s in S], cut=[s["cut"] for s in S],
                          nobar=[s["nobar"] for s in S], minL=[s["minL"] for s in S], maxH=[s["maxH"] for s in S]))
    R["gross"] = R["px"] / R["E"] - 1.0
    R["mae"] = R["minL"] / R["E"] - 1.0
    R["hold_h"] = (R["exit_t"] - R["t0"]) / H
    inc = {j: np.array(s["inc"], float) for j, s in enumerate(S) if s["inc"]}
    pd.to_pickle(dict(R=R, inc=inc, eq=eq, ck=ck, cand=cand, base=base, q6=q6, legs=legs), W + "/path.pkl")
    log.info("PATH xong %.0fs ck %s", time.time() - t_start, json.dumps({k: v for k, v in ck.items() if k != "missing_days"}))


# ---------------------------------------------------------------- report
def mmm(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    return dict(mean=float(np.mean(v)), min=float(np.min(v)), max=float(np.max(v))) if v else None


def ci_day(v, day, k):
    """TB + CI95 cum theo ngay local (sai so chuan cum), half-width nhan sqrt(2 ln k)."""
    v, day = np.asarray(v, float), np.asarray(day)
    n = len(v)
    if n < 3:
        return dict(n=n, mean=float(v.mean()) if n else None, lo=None, hi=None)
    mu = v.mean()
    g = pd.Series(v - mu).groupby(day).sum().to_numpy()
    se = math.sqrt((g ** 2).sum()) / n
    hw = 1.96 * se * (math.sqrt(2 * math.log(k)) if k > 1 else 1.0)
    return dict(n=n, mean=float(mu), lo=float(mu - hw), hi=float(mu + hw), se=float(se))


def roi_block(x, k):
    net = 100 * (x["gross"] - COST)
    st = net - 100 * PEN * x["crash"]
    day = (x["ts"] + TZ) // D
    yrs = yr_of(x["ts"])
    return dict(n=int(len(x)), roi_net=ci_day(net, day, k), roi_stress=ci_day(st, day, k),
                win=float((net > 0).mean()) if len(x) else None,
                mae_p50=float(np.median(100 * x["mae"])) if len(x) else None,
                mae_p10=float(np.percentile(100 * x["mae"], 10)) if len(x) else None,
                hold_p50=float(np.median(x["hold_h"])) if len(x) else None,
                time_stop=float((x["why"] == "time").mean()) if len(x) else None,
                crash=float(x["crash"].mean()) if len(x) else None,
                year={int(y): dict(n=int((yrs == y).sum()), roi_net=float(net[yrs == y].mean()) if (yrs == y).any() else None,
                                   roi_stress=float(st[yrs == y].mean()) if (yrs == y).any() else None) for y in YEARS})


def calib(base, R):
    x = base.merge(R[["tid", "E", "gross", "exit_t", "why", "nobar", "cut", "br"]], on="tid", how="left")
    x = x[~x["nobar"] & ~x["cut"]].copy()
    x["real"] = x["profit"] / 100.0
    x["real_net"] = x["pnl"] / x["notional"]
    x["d"] = 100 * (x["gross"] - x["real"])

    def blk(z):
        if len(z) < 3:
            return None
        return dict(n=int(len(z)), pearson=float(np.corrcoef(z["gross"], z["real"])[0, 1]),
                    spearman=float(z["gross"].corr(z["real"], method="spearman")),
                    bias_pp=float(z["d"].mean()), mad_pp=float(z["d"].abs().median()),
                    proxy_mean=float(100 * z["gross"].mean()), real_mean=float(100 * z["real"].mean()),
                    net_bias_pp=float(100 * ((z["gross"] - COST) - z["real_net"]).mean()),
                    same_exit_min=float((z["exit_t"] == z["e_ms"]).mean()),
                    entry_match=float((np.abs(z["E"] / z["entry"] - 1) < 1e-5).mean()))
    out = dict(all=blk(x), no_dca=blk(x[x["nleg"] == 1]), dca=blk(x[x["nleg"] > 1]),
               year={int(y): blk(g) for y, g in x.groupby("year")},
               year_no_dca={int(y): blk(g) for y, g in x[x["nleg"] == 1].groupby("year")},
               seed={s: blk(g) for s, g in x.groupby("seed")}, n_drop=int(len(base) - len(x)))
    a = out["all"]
    out["verdict"] = "PASS" if (abs(a["bias_pp"]) <= 1.0 and a["pearson"] >= 0.5) else "FAIL"
    nd = out["no_dca"]
    out["verdict_no_dca"] = "PASS" if (abs(nd["bias_pp"]) <= 1.0 and nd["pearson"] >= 0.5) else "FAIL"
    return out


def day_set(s, e, lo, hi):
    out = set()
    for a, b in zip(((np.asarray(s) + TZ) // D).tolist(), ((np.asarray(e) - 1 + TZ) // D).tolist()):
        out.update(range(max(a, lo), min(b, hi - 1) + 1))
    return out


def q5(cand, R, inc, eq, legs):
    C = cand.merge(R[["tid", "exit_t", "nobar"]], on="tid")
    C = C[~C["nobar"]]
    U = np.arange(T22 // D + 1, (T26 - 1) // D + 1)
    res = {}
    for seed in SEEDS:
        lg = legs[legs["seed"] == seed]
        l0d = set(((lg.loc[lg["leg0"], "s_ms"] + TZ) // D).tolist())
        cl = lg.groupby("pid").agg(s=("s_ms", "min"), e=("e_ms", "max"))
        bd = day_set(cl["s"], cl["e"], U[0], U[-1] + 1)
        e = np.array([eq[seed].get(int(x), np.nan) for x in U])
        ep = np.array([eq[seed].get(int(x) - 1, np.nan) for x in U])
        rb = e / ep - 1
        res[seed] = dict(base_days=len(bd), n_days=len(U), rb_nan=int(np.isnan(rb).sum()), cfg={})
        for (K, p), g in C[C["seed"] == seed].groupby(["K", "pct"]):
            cd = ((g["ts"] + TZ) // D).to_numpy()
            sl = np.zeros(len(U))
            for t in g["tid"].tolist():
                a = inc.get(t)
                if a is not None:
                    ii = a[:, 0].astype(int) - U[0]
                    ok = (ii >= 0) & (ii < len(U))
                    np.add.at(sl, ii[ok], a[ok, 1])
            okd = np.isfinite(rb)
            ex = okd & (sl != 0)
            sd = day_set(g["ts"], g["exit_t"], U[0], U[-1] + 1)
            res[seed]["cfg"]["%d|%s" % (K, p)] = dict(
                n=int(len(g)), share_no_leg0_day=float(np.mean([x not in l0d for x in cd.tolist()])),
                pearson=float(np.corrcoef(sl[okd], rb[okd])[0, 1]),
                spearman=float(pd.Series(sl[okd]).corr(pd.Series(rb[okd]), method="spearman")),
                pearson_exposed=float(np.corrcoef(sl[ex], rb[ex])[0, 1]) if ex.sum() > 10 else None,
                sleeve_days=len(sd), union_days=len(bd | sd), add_days=len(sd - bd))
    return res


def stage_report():
    S = {s: pd.read_pickle(W + "/cand_%s.pkl" % s)["res"] for s in SEEDS}
    P = pd.read_pickle(W + "/path.pkl")
    Q6 = pd.read_pickle(W + "/q6.pkl")["out"]
    R, cand, base = P["R"], P["cand"], P["base"]
    js = dict(title="QSLEEVE_Q0 2026-10-08", script="research/analysis/qsleeve_q0.py", cost=COST, pen=PEN,
              grid=dict(K=KS, pct=PCTS, X=XS, quiet_X=QX, ages=[list(a) for a in AGES]), checks={})
    js["checks"]["seed"] = {s: dict(n=S[s]["meta"]["n"], n_result=S[s]["meta"]["n_result"],
                                    pred_ok=S[s]["meta"]["pred_ok"], leg0_dca=S[s]["meta"]["leg0_dca"],
                                    q1=S[s]["q1"]["check"], wouldpass=S[s]["wouldpass"], dedup_ok=S[s]["dedup_ok"],
                                    jmax=S[s]["jmax"]) for s in SEEDS}
    js["checks"]["path"] = {k: v for k, v in P["ck"].items() if k != "missing_days"}
    js["checks"]["path"]["missing_days"] = P["ck"]["missing_days"][:20]
    js["q1"] = {y: {} for y in YEARS}
    for y in YEARS:
        Y = [S[s]["q1"]["year"][y] for s in SEEDS]
        js["q1"][y] = dict(empty_pct=mmm([v["empty_pct"] for v in Y]), n_leg0=mmm([v["n_leg0"] for v in Y]),
                           gap_p50=mmm([v["gap_h"]["p50"] for v in Y]), gap_p90=mmm([v["gap_h"]["p90"] for v in Y]),
                           gap_p99=mmm([v["gap_h"]["p99"] for v in Y]), gap_max=mmm([v["gap_h"]["max"] for v in Y]),
                           X={X: dict(n=mmm([v["X"][X]["n"] for v in Y]), dur_h=mmm([v["X"][X]["dur_h"] for v in Y]),
                                      dur_pct=mmm([v["X"][X]["dur_pct"] for v in Y]),
                                      quiet_pct=mmm([v["X"][X]["quiet_pct"] for v in Y])) for X in XS})
    js["q3_rdist"] = {K: {s: S[s]["rdist"][K] for s in SEEDS} for K in KS}
    js["q3_thr"] = {s: S[s]["thr"] for s in SEEDS}
    js["q3_n"] = {}
    yrs = yr_of(cand["ts"])
    cand = cand.assign(yr=yrs)
    for K in KS:
        for p in PCTS:
            g = cand[(cand["K"] == K) & (cand["pct"] == p)]
            per = {s: len(g[g["seed"] == s]) / 4.0 for s in SEEDS}
            js["q3_n"]["%d|%s" % (K, p)] = dict(
                n_per_year=mmm(list(per.values())), cells=mmm([S[s]["ncells"]["%d|%s" % (K, p)] / 4.0 for s in SEEDS]),
                year={y: mmm([len(g[(g["seed"] == s) & (g["yr"] == y)]) for s in SEEDS]) for y in YEARS},
                thr_over_qcore_p50=mmm([(S[s]["thr"]["%d|%s" % (K, p)]["thr_over_qcore"] or {}).get("p50") for s in SEEDS]),
                r_over_qcore_p50=float(np.median(g["r"] / g["qcore"])) if len(g) else None,
                rank_p50=float(g["rank"].median()) if len(g) else None)
    C = cand.merge(R[["tid", "gross", "mae", "hold_h", "why", "br", "nobar", "cut", "vol"]], on="tid", how="left")
    js["checks"]["cand_nobar"] = int(C["nobar"].sum())
    js["checks"]["cand_cut"] = int(C["cut"].sum())
    C = C[~C["nobar"]].copy()
    C["crash"] = (C["br"] <= CRASH).astype(float)
    js["q4"], js["q4_age"] = {}, {}
    for K in KS:
        for p in PCTS:
            g = C[(C["K"] == K) & (C["pct"] == p)]
            b = roi_block(g, 9)
            b["n_per_year_seed"] = len(g) / 32.0
            b["seed_roi_net"] = mmm([100 * (x["gross"].mean() - COST) for _, x in g.groupby("seed")])
            js["q4"]["%d|%s" % (K, p)] = b
            for lo, hi in AGES:
                ga = g[(g["age"] >= lo) & (g["age"] < hi)]
                js["q4_age"]["%d|%s|%s" % (K, p, lo)] = dict(roi_block(ga, 27), n_per_year_seed=len(ga) / 32.0)
    js["calib"] = calib(base, R)
    q6p = P["q6"].merge(R[["tid", "gross", "nobar", "cut", "hold_h", "why"]], on="tid")
    q6p = q6p[~q6p["nobar"]]
    js["q6"] = dict(Q6, proxy_on_pred_leg0=dict(n=int(len(q6p)), proxy_gross=float(100 * q6p["gross"].mean()),
                                                 real_profit=float(q6p["profit"].mean()),
                                                 proxy_net_stress=float((100 * (q6p["gross"] - COST) - 100 * PEN * q6p["crash"]).mean()),
                                                 real_roi_s=float(q6p["roi_s"].mean()),
                                                 pearson=float(np.corrcoef(q6p["gross"], q6p["profit"])[0, 1]) if len(q6p) > 2 else None))
    q5r = q5(cand, R, P["inc"], P["eq"], P["legs"])
    js["q5_seed"] = q5r
    js["q5"] = {}
    for K in KS:
        for p in PCTS:
            k = "%d|%s" % (K, p)
            V = [q5r[s]["cfg"][k] for s in SEEDS if k in q5r[s]["cfg"]]
            js["q5"][k] = {f: mmm([v[f] for v in V]) for f in ("share_no_leg0_day", "pearson", "spearman",
                                                                  "pearson_exposed", "sleeve_days", "union_days",
                                                                  "add_days")}
    js["q5_base_days"] = mmm([q5r[s]["base_days"] for s in SEEDS])
    js["q5_n_days"] = q5r["A1"]["n_days"]
    js["checks"]["mtm_rb_nan"] = {s: q5r[s]["rb_nan"] for s in SEEDS}
    json.dump(GO.tojs(js), open(JSON_OUT, "w"), indent=1, ensure_ascii=False)
    log.info("ghi %s", JSON_OUT)
    write_md(js)


def f2(x, nd=2):
    return "—" if x is None or (isinstance(x, float) and not np.isfinite(x)) else ("%.*f" % (nd, x)).replace(".", ",")


def fm(m, nd=1):
    if m is None:
        return "—"
    return "%s [%s..%s]" % (f2(m["mean"], nd), f2(m["min"], nd), f2(m["max"], nd))


def tbl(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]


def write_md(js):
    L = []
    hp = W + "/qs0_head.md"
    L += open(hp).read().rstrip().split("\n") if os.path.exists(hp) else ["# QSLEEVE_Q0 (bang tu dong)"]
    L += ["", "## Bang (tu dong tu `research/analysis/qsleeve_q0.py`; o = TB 8 seed [min..max])", "",
          "### T1. Q1 giai phau thoi gian yen (nen K24 skipFull, 8 seed)"]
    rows = []
    for y in YEARS:
        q = js["q1"][y]
        rows.append([y, fm(q["empty_pct"]), fm(q["n_leg0"], 0), fm(q["gap_p50"]), fm(q["gap_p90"]), fm(q["gap_p99"], 0),
                     fm(q["gap_max"], 0)] + ["%s · %s%% (yen %s%%)" % (fm(q["X"][X]["n"], 1), f2(q["X"][X]["dur_pct"]["mean"], 1),
                                                                   f2(q["X"][X]["quiet_pct"]["mean"], 1)) for X in XS])
    L += tbl(["nam", "% phut so trong", "n leg0", "gap p50 h", "gap p90 h", "gap p99 h", "gap max h"]
             + ["X=%dh: n cua so · % thoi gian (phut tuoi>=X)" % X for X in XS], rows)
    L += ["", "### T2. Q3 phan bo r top-K: phut yen (tuoi >= 24h) vs phut co lenh (tuoi < 24h), 2022-25, sau warm-up q_core",
          "ratio = r_max(phut)/q_core(gio). O = TB 8 seed."]
    rows = []
    for K in KS:
        for nm in ("quiet", "active"):
            V = [js["q3_rdist"][K][s][nm] for s in SEEDS]
            rows.append([K, nm, f2(np.mean([v["n_min"] for v in V]) / 4, 0)]
                        + [f2(np.mean([v["ratio"][q] for v in V]), 3) for q in ("p50", "p90", "p99", "p99.9")]
                        + [f2(np.mean([v["ratio"]["max"] for v in V]), 2), f2(100 * np.mean([v["ge1"] for v in V]), 3)])
    L += tbl(["K", "nhom", "phut/nam", "ratio p50", "p90", "p99", "p99.9", "max", "% phut ratio>=1"], rows)
    L += ["", "### T3. Q3 so ung vien/nam (sau khu trung) theo K x pct, va nguong sleeve / q_core"]
    rows = []
    for K in KS:
        for p in PCTS:
            q = js["q3_n"]["%d|%s" % (K, p)]
            rows.append([K, p, fm(q["cells"], 0), fm(q["n_per_year"], 0)] + [fm(q["year"][y], 0) for y in YEARS]
                        + [fm(q["thr_over_qcore_p50"], 3), f2(q["r_over_qcore_p50"], 3), f2(q["rank_p50"], 0)])
    L += tbl(["K", "pct", "o vuot/nam (truoc khu)", "lenh/nam"] + [str(y) for y in YEARS]
             + ["nguong/q_core p50", "r/q_core p50 lenh", "rank p50"], rows)
    L += ["", "### T4. Q4 proxy ROI/lenh (% notional, sau phi 0,1116%; stress -1,675pp neu nen quyet dinh sap)",
          "Gop 8 seed; CI95 cum theo ngay, half-width x sqrt(2 ln 9). n/nam = TB moi seed."]
    rows = []
    for K in KS:
        for p in PCTS:
            b = js["q4"]["%d|%s" % (K, p)]
            rn, rs = b["roi_net"], b["roi_stress"]
            rows.append([K, p, f2(b["n_per_year_seed"], 0), "%s [%s; %s]" % (f2(rn["mean"]), f2(rn["lo"]), f2(rn["hi"])),
                         "%s [%s; %s]" % (f2(rs["mean"]), f2(rs["lo"]), f2(rs["hi"])), fm(b["seed_roi_net"], 2),
                         f2(100 * b["win"], 1), f2(b["mae_p50"], 1), f2(b["mae_p10"], 1), f2(b["hold_p50"], 0),
                         f2(100 * b["time_stop"], 0), f2(100 * b["crash"], 1)]
                        + ["/".join(f2(b["year"][y]["roi_net"], 1) for y in YEARS)])
    L += tbl(["K", "pct", "n/nam", "ROI net [CI]", "ROI stress [CI]", "ROI net theo seed", "win %", "MAE p50",
              "MAE p10", "giu p50 h", "% time-stop", "% sap", "ROI net 22/23/24/25"], rows)
    L += ["", "### T5. Q4 theo tang tuoi yen (gio tu leg0 nen gan nhat); CI x sqrt(2 ln 27)"]
    rows = []
    for K in KS:
        for p in PCTS:
            for lo, hi in AGES:
                b = js["q4_age"]["%d|%s|%s" % (K, p, lo)]
                rn, rs = b["roi_net"], b["roi_stress"]
                rows.append([K, p, "[%d,%s)" % (lo, "inf" if not np.isfinite(hi) else int(hi)), f2(b["n_per_year_seed"], 0),
                             "%s [%s; %s]" % (f2(rn["mean"]), f2(rn["lo"]), f2(rn["hi"])), f2(rs["mean"]),
                             f2(100 * b["win"], 1) if b["win"] is not None else "—", f2(b["hold_p50"], 0)])
    L += tbl(["K", "pct", "tuoi h", "n/nam", "ROI net [CI]", "ROI stress", "win %", "giu p50 h"], rows)
    c = js["calib"]
    L += ["", "### T6. Hieu chuan proxy tren leg0 PRED that cua nen (8 seed, 2022-25): gross proxy vs `profit` printDone",
          "**Ket luan hieu chuan (tieu chi khai truoc, toan bo leg0): %s**; tap khong-DCA: %s." % (c["verdict"], c["verdict_no_dca"])]
    rows = []
    for nm, b in [("tat ca", c["all"]), ("khong DCA (nleg=1)", c["no_dca"]), ("co DCA", c["dca"])] + \
            [("nam %s" % y, c["year"][y]) for y in YEARS] + [("khong DCA %s" % y, c["year_no_dca"].get(y)) for y in YEARS]:
        if b is None:
            continue
        rows.append([nm, b["n"], f2(b["pearson"], 3), f2(b["spearman"], 3), f2(b["bias_pp"]), f2(b["mad_pp"]),
                     f2(b["proxy_mean"]), f2(b["real_mean"]), f2(b["net_bias_pp"]), f2(100 * b["same_exit_min"], 1),
                     f2(100 * b["entry_match"], 1)])
    L += tbl(["tap", "n", "pearson", "spearman", "lech TB pp", "|lech| p50 pp", "proxy TB %", "that TB %",
              "lech net pp", "% cung phut thoat", "% entry khop"], rows)
    L += ["", "### T7. Q5 doc lap (ngay local; tuong quan PnL ngay proxy cua sleeve [don vi notional/lenh] vs return ngay MTM nen)",
          "Ngay co vi the nen: %s / %d ngay." % (fm(js["q5_base_days"], 0), js["q5_n_days"])]
    rows = []
    for K in KS:
        for p in PCTS:
            q = js["q5"]["%d|%s" % (K, p)]
            rows.append([K, p, fm({k: 100 * v for k, v in q["share_no_leg0_day"].items()}, 1), fm(q["pearson"], 3),
                         fm(q["spearman"], 3), fm(q["pearson_exposed"], 3), fm(q["sleeve_days"], 0), fm(q["add_days"], 0)])
    L += tbl(["K", "pct", "% lenh o ngay khong leg0 nen", "pearson", "spearman", "pearson (ngay sleeve co PnL)",
              "ngay sleeve co vi the", "ngay vi the TANG them"], rows)
    q = js["q6"]
    L += ["", "### T8. Q6 tai hien J4 p2 >= 96h (arm D l2-k32, MOI, entry 2022-25, 3 seed)",
          "- tu `j4_rows.csv.gz` NSEL: n %d (%s/nam) · ROI_S %s" % (q["from_nsel_rows"]["n"], f2(q["from_nsel_rows"]["n_per_year"], 1),
                                                              f2(q["from_nsel_rows"]["roi_s"])),
          "- tinh lai doc lap tu printDone (khop tol 1 sym, p2 = gio tu leg0 arm truoc do, sap = bar.json NDEEP): n %d (%s/nam)"
          " · ROI_S %s · khop %s" % (q["recompute"]["n"], f2(q["recompute"]["n_per_year"], 1), f2(q["recompute"]["roi_s"]),
                                    "PASS" if q["match_pass"] else "FAIL")]
    for lt, v in q["recompute"]["lt"].items():
        L.append("  - %s: %s/nam · ROI_S %s · profit gop %s%% · sap %s%% · la leg0 %d" % (
            lt, f2(v["n_per_year"], 1), f2(v["roi_s"]), f2(v["profit"]), f2(100 * v["crash"], 1), v["leg0"]))
    pp = q["pred_leg0"]
    L.append("- leg0 PRED trong nhom: %s/nam · ROI_S %s · profit %s%% · sap %s%% · cum co DCA %s%%" % (
        f2(pp["n_per_year"], 1), f2(pp["roi_s"]), f2(pp["profit"]), f2(100 * pp["crash"], 1), f2(100 * pp["nleg_gt1"], 1)))
    pr = q["proxy_on_pred_leg0"]
    L.append("- proxy (luat thoat don gian, khong DCA) tren chinh cac leg0 PRED do: n %d · gross %s%% vs that %s%% · "
             "net-stress proxy %s vs ROI_S that %s · pearson %s" % (pr["n"], f2(pr["proxy_gross"]), f2(pr["real_profit"]),
                                                                    f2(pr["proxy_net_stress"]), f2(pr["real_roi_s"]),
                                                                    f2(pr["pearson"], 3)))
    L += ["", "### T0. Tu kiem", "```", json.dumps(GO.tojs(js["checks"]), ensure_ascii=False)[:6000], "```"]
    open(MD_OUT, "w").write("\n".join(L) + "\n")
    log.info("ghi %s", MD_OUT)


def main():
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    os.makedirs(W, exist_ok=True)
    heavy = st in ("prep", "cand", "path", "all")
    if heavy:
        take_lock("qs0-" + st)
    try:
        if st in ("prep", "all"):
            stage_prep()
        if st in ("cand", "all"):
            stage_cand(only)
        if st in ("q6", "all"):
            stage_q6()
        if st in ("path", "all"):
            stage_path()
        if st in ("report", "all"):
            stage_report()
    finally:
        if heavy:
            drop_lock()


if __name__ == "__main__":
    main()
