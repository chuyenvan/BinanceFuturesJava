#!/usr/bin/env python3
"""NSEL_P0_DATA (2026-10-08): audit KHOP NOI (data) vong NSEL_P0 -- CHI phan tich output Kaggle co san.

0 sim, 0 Kaggle, 0 Java, 0 cham 242/shadow. Chan doan, KHONG chon nguong (MASTER chot o pre-reg sau).
J1 matching DOC LAP (khong import n_deep): don vi chan (dong printDone) va lenh (cum = (sym, end): closeOrder gan
   cung timeUpdate cho moi leg cua cum). Khop 1-1 tham lam theo |dphut| tang dan, khoa (sym) hoac (sym, leg type).
J3 nguyen nhan MAT theo THU TU CODE (SimulatorMarketLevelTicker1MStopLoss:405-436 + createOrder:1322-1420):
   PRED: topK (rank SELRANK nen > K arm) -> giu symbol (isSymbolRunning) -> so day (bookFull: U >= U_MAX 0.60)
   -> gate (gate_offline cau hinh arm, tren duong arm) -> khong giai thich. BIG_DOWN: so day -> giu symbol ->
   chon khac (arm co BIG_DOWN cung phut) -> khac. DCA: lech duong (leg0 cum nen la MAT) -> so day -> khac.
J4 proxy NHAN QUA (chi qua khu cua chinh arm): p1 U truoc khi vao, p2 gio tu leg0 gan nhat, p3 so chan 24h truoc,
   p4 pass gate NEN (K24, pct nen) tai lap offline tren duong arm (dinh nghia 'chan them' dung duoc trong live).
J6 nen nhieu: sd nhieu seed K24/K16 skipFull ON bang thuoc gkf_rescore (MTM phut), MDE 3 seed ghep cap.
U (TradeUtils.managerBudget) = marginRunning / equityNow. marginRunning = sum calMargin (= qty*entry, khop cot margin)
   chan dang mo: cong luc vao (:1575), tru ca cum luc dong (:1135, dong xu ly TRUOC selector trong tick).
   equityNow = balanceCurrent + unProfit, chi cap nhat o updateBalance moi gio (time%60'==0, CUOI tick, sau selector)
   -> chan vao phut t dung equity moc gio ((t-1)//60)*60. Equity moc gio tai lap = 35000 + sum pnl (end <= H)
   + sum qty*(close_H - entry) chan mo (m0 <= H < m1); kiem bang dong 'Update ... b/m/unP' 07:00 cua log.
Usage: python3 research/analysis/nsel_p0_data.py {prep|gate|j6|analyze} [--workers 3]
"""
import argparse
import gzip
import json
import logging
import math
import os
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import jbin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("nsel_p0")
OUT = "/home/ubuntu/kaggle_sim/out/"
TICK = "/home/ubuntu/kaggle_data_hpo"
W = "/home/ubuntu/claude_master/1008/nsel"
JSON_OUT = REPO + "/docs/audit/NSEL_P0_DATA_20261008.json"
MD_OUT = W + "/tables.md"
NDEEP_JSON = REPO + "/docs/audit/N_DEEP_20261008.json"
NDEEP_BAR = "/home/ubuntu/claude_master/1008/ndeep/bar.json"     # cache (o,c) nen 1m: du lieu, khong phai ham n_deep
NDEEP_MTM = "/home/ubuntu/claude_master/1008/ndeep/mtm.json"
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"
CAP0, UMAX, PEN, CRASH = 35000.0, 0.60, 0.01675, -0.01
DAY0_MIN = int(pd.Timestamp("2021-07-01").value // 60_000_000_000)   # truc phut UTC cua bar cache
H0_MIN = DAY0_MIN                                                     # moc gio dau (2021-07-01 00:00 UTC)
SEEDS = ["S42", "S7", "S21"]
GSEED = {"S42": "A1", "S7": "S7", "S21": "S21"}                       # khoa gate_offline.SEEDS (pred.bin p15)
NEN = {"S42": "gqsf-a1", "S7": "gqsf-s7", "S21": "gqsf-s21"}
K0, PCT0 = 24, 0.999950829
ARMS = {"C": (16, 0.99988, {"S42": "gkf-l2-k16", "S7": "gkf2-l2k16-s7", "S21": "gkf2-l2k16-s21"}),
        "D": (32, 0.999915, {"S42": "gkf-l2-k32", "S7": "gkf2-l2k32-s7", "S21": "gkf2-l2k32-s21"})}
NDK = {"C": "C_l2k16", "D": "D_l2k32"}
KCFG = {t: (K0, PCT0) for t in NEN.values()}
for _a, (_k, _p, _m) in ARMS.items():
    KCFG.update({t: (_k, _p) for t in _m.values()})
TAGS9 = list(KCFG)
J6_K24 = ["gqsf-a1", "gqsf-s7", "gqsf-s13", "gqsf-s21", "gqsf-s99", "gqsf-s123", "gqsf-s777", "gqsf-s2024"]
J6_K16 = {"S42": "gqsf16-a1", "S7": "gqsf16-s7", "S21": "gqsf16-s21"}
YEARS = [2022, 2023, 2024, 2025]
LT_ORD = {"BIGD": 0, "DCA": 1, "PRED": 2}
T95_2, T80_2 = 2.919986, 1.060660            # t mot phia df=2: alpha 0,05 / power 80%


def jd(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if not np.isfinite(o) else float(o)
    return str(o)


def take_lock():
    while os.path.exists(LOCK):
        log.info("cho lock %s", LOCK)
        time.sleep(60)
    with open(LOCK, "w") as f:
        f.write("nsel_p0_data %d %s\n" % (os.getpid(), time.ctime()))


def drop_lock():
    if os.path.exists(LOCK):
        os.remove(LOCK)


def seed_of(tag):
    for s in SEEDS:
        if tag == NEN[s] or any(m[s] == tag for _, _, m in ARMS.values()):
            return s
    raise KeyError(tag)


def load(tag):
    """printDone -> bang chan. m0/m1 = phut UTC epoch (gio local -7h). pid = cum (sym, end); leg0 = chan dau cum."""
    raw = pd.read_csv(OUT + tag + "/storage/printDone.csv", on_bad_lines="skip")
    raw.columns = [c.strip() for c in raw.columns]
    for c in ("quantity", "entry", "margin", "pnl"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    ts = pd.to_datetime(raw["start"].astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    te = pd.to_datetime(raw["end"].astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    ok = raw[["quantity", "entry", "margin", "pnl"]].notna().all(axis=1).to_numpy() & ts.notna().to_numpy() & te.notna().to_numpy()
    d = raw[ok].copy()
    d["row"] = np.arange(len(raw))[ok]
    d["ts"], d["te"] = ts[ok], te[ok]
    d["sym"] = d["sym"].astype(str).str.strip()
    lv = d["level"].astype(str).str.strip()
    d["lt"] = np.where(lv == "PREDICT_SYMBOL_TRADE", "PRED", np.where(lv == "BIG_DOWN", "BIGD", "DCA"))
    d["m0"] = d["ts"].values.astype("datetime64[m]").astype(np.int64) - 420
    d["m1"] = d["te"].values.astype("datetime64[m]").astype(np.int64) - 420
    d["year"] = d["ts"].dt.year.to_numpy()
    d["notional"] = (d["quantity"] * d["entry"]).astype(float)
    d = d.sort_values(["m0", "row"], kind="mergesort").reset_index(drop=True)
    d["pid"] = d.groupby(["sym", "m1"], sort=False).ngroup()
    d["leg0"] = ~d.duplicated("pid", keep="first")
    rj = json.load(open(OUT + tag + "/result.json"))
    meta = dict(n_raw=int(len(raw)), n=int(len(d)), n_trades_result=rj.get("n_trades"),
                margin_eq_notional=float(np.max(np.abs(d["margin"] / d["notional"] - 1))))
    return d, meta


RX_SEL = re.compile(r"SELRANK sym=(\S+?)USDT tOpen=\S+ \S+ tMs=(\d+) rank=(\d+)")
RX_UPD = re.compile(r"Update (\d{8}) (\d\d):(\d\d) => b:\s*(-?\d+)\s+pD:\s*(-?\d+)\s+m:\s*(-?\d+).*?unP:\s*(-?\d+)")
RX_CPC = re.compile(r"\[CONC-PC\] SUMMARY blocked=(\d+)")


def logscan(tag):
    """SELRANK (rank 1-based tren pool top-K, ke ca coin dang giu), dong Update 07:00, CONC-PC blocked."""
    sel, upd, cpc = [], [], None
    with open(OUT + tag + "/logs/full.log", errors="ignore") as f:
        for ln in f:
            m = RX_SEL.search(ln)
            if m:
                sel.append((m.group(1), int(m.group(2)) // 60000, int(m.group(3))))
                continue
            m = RX_UPD.search(ln)
            if m:
                t = int(pd.Timestamp(m.group(1) + " %s:%s" % (m.group(2), m.group(3))).value // 60_000_000_000) - 420
                upd.append((t, int(m.group(4)), int(m.group(6)), int(m.group(7))))
                continue
            m = RX_CPC.search(ln)
            if m:
                cpc = int(m.group(1))
    sel = pd.DataFrame(sel, columns=["sym", "m0", "rank"])
    upd = pd.DataFrame(upd, columns=["m", "b", "mg", "unp"]).drop_duplicates("m", keep="last")
    return sel, upd, cpc


def attach(d, sel, bar):
    """rank SELRANK cho chan PRED (khop (sym, m0)); crash = nen 1m quyet dinh lag0 (phut m0) close/open-1 <= -1%."""
    k = sel.drop_duplicates(["sym", "m0"])
    x = d[["sym", "m0"]].merge(k, on=["sym", "m0"], how="left")
    d["rank"] = np.where(d["lt"] == "PRED", x["rank"].to_numpy(float), 0.0)
    o = np.full(len(d), np.nan)
    c = np.full(len(d), np.nan)
    for i, (s, m) in enumerate(zip(d["sym"].tolist(), d["m0"].tolist())):
        v = bar.get("%s|%d" % (s, m - DAY0_MIN))
        if v is not None:
            o[i], c[i] = v
    d["br"] = c / o - 1.0
    d["crash"] = (d["br"] <= CRASH).to_numpy()
    d["hit0"] = np.abs(c / d["entry"].to_numpy(float) - 1.0) < 1e-5
    d["pnl_s"] = d["pnl"].to_numpy(float) - PEN * d["notional"].to_numpy(float) * d["crash"].to_numpy()
    d["roi_s"] = 100.0 * d["pnl_s"] / d["notional"]
    pr = d["lt"] == "PRED"
    return dict(n_sel=int(len(sel)), n_sel_dupkey=int(len(sel) - len(k)), n_pred=int(pr.sum()),
                pred_rank_join=float(d.loc[pr, "rank"].notna().mean()), bar_missing=int(np.isnan(o).sum()),
                hit_lag0=float(d["hit0"].mean()), crash_share=float(100 * d["crash"].mean()))


# ---------------------------------------------------------------- prep: equity moc gio (tai lap equityNow)
def _hw(args):
    """1 ngay ticker UTC: close (ffill trong ngay) tai 24 moc gio cho cac symbol can."""
    day, syms = args
    p = os.path.join(TICK, "ticker_%s.bin.gz" % day)
    if not os.path.exists(p):
        return day, {}
    t0 = int(pd.Timestamp(day).value // 10 ** 6)
    C = {s + "USDT": np.full(1440, np.nan, np.float32) for s in syms}
    with gzip.open(p, "rb") as f:
        b = f.read()
    for k, v in jbin.iter_minutes(b):
        mi = (k - t0) // 60000
        if mi < 0 or mi >= 1440:
            continue
        for s, arr in C.items():
            tup = v.get(s)
            if tup is not None:
                arr[mi] = tup[3]          # (startTime, max, min, close, open, vol): close = tup[3]
    return day, {s[:-4]: pd.Series(a).ffill().to_numpy()[0::60] for s, a in C.items()}


def hour_span(d):
    """chi so gio (tu H0) cua moi moc H voi m0 <= H < m1."""
    a = np.ceil((d["m0"].to_numpy() - H0_MIN) / 60.0).astype(np.int64)
    b = np.ceil((d["m1"].to_numpy() - H0_MIN) / 60.0).astype(np.int64)
    return a, np.maximum(a, b)


def prep(workers):
    L = {t: load(t)[0] for t in TAGS9}
    nH = int(math.ceil((max(int(d["m1"].max()) for d in L.values()) - H0_MIN) / 60.0)) + 2
    need = {}
    for d in L.values():
        a, b = hour_span(d)
        for s, x, y in zip(d["sym"].tolist(), a.tolist(), b.tolist()):
            for dd in range(x // 24, (max(x, y - 1)) // 24 + 1):
                need.setdefault(dd, set()).add(s)
    jobs = [((pd.Timestamp("2021-07-01") + pd.Timedelta(days=dd)).strftime("%Y%m%d"), sorted(v)) for dd, v in sorted(need.items())]
    nH = max(nH, (max(need) + 1) * 24)          # du cho ngay cuoi (moc gio cuoi ngay)
    log.info("PREP: %d ngay ticker, %d gio, %d symbol", len(jobs), nH, len(set().union(*need.values())))
    px = {}
    t0 = time.time()
    with Pool(workers) as pool:
        for i, (day, out) in enumerate(pool.imap_unordered(_hw, jobs, chunksize=4)):
            dd = (pd.Timestamp(day) - pd.Timestamp("2021-07-01")).days
            for s, v in out.items():
                if s not in px:
                    px[s] = np.full(nH, np.nan, np.float32)
                px[s][dd * 24:dd * 24 + 24] = v
            if i % 200 == 0:
                log.info("  PREP %d/%d %.0fs", i, len(jobs), time.time() - t0)
    for s in px:
        px[s] = pd.Series(px[s]).ffill().to_numpy(np.float32)
    np.savez_compressed(W + "/px_hour.npz", **px)
    for t, d in L.items():
        eqh(t, d, px, nH)


def eqh(tag, d, px, nH):
    """equity/margin moc gio: eq = CAP0 + sum pnl (m1 <= H) + sum qty*(close_H - entry) (m0 <= H < m1)."""
    u = np.zeros(nH, np.float64)
    mg = np.zeros(nH, np.float64)
    a, b = hour_span(d)
    miss = 0
    for s, q, e, m, x, y in zip(d["sym"].tolist(), d["quantity"].to_numpy(float), d["entry"].to_numpy(float),
                                d["margin"].to_numpy(float), a.tolist(), b.tolist()):
        if y <= x:
            continue
        mg[x:y] += m
        p = px.get(s)
        if p is None:
            miss += 1
            continue
        pp = p[x:y].astype(np.float64)
        miss += int(np.isnan(pp).sum() > 0)
        u[x:y] += np.where(np.isnan(pp), 0.0, q * (pp - e))
    Hm = H0_MIN + 60 * np.arange(nH)
    o = np.argsort(d["m1"].to_numpy(), kind="mergesort")
    cp = np.concatenate([[0.0], np.cumsum(d["pnl"].to_numpy(float)[o])])
    real = cp[np.searchsorted(d["m1"].to_numpy()[o], Hm, "right")]
    np.savez(W + "/eqh_%s.npz" % tag, Hm=Hm, eq=CAP0 + real + u, real=real, u=u, mg=mg, miss=miss)
    log.info("EQH %-16s gio %d miss %d eq_cuoi %.0f", tag, nH, miss, CAP0 + real[-1] + u[-1])


def okey(d):
    """thu tu trong 1 tick: BIG_DOWN (:352) < DCA (:379,:397) < PRED theo rank selector (:425)."""
    return d["lt"].map(LT_ORD).to_numpy() * 1000 + np.nan_to_num(d["rank"].to_numpy(float), nan=999.0)


class Book:
    """so cua MOT run (chi qua khu cua chinh no): U truoc khi vao, giu symbol, p2, p3 tai phut t."""

    def __init__(self, tag, d):
        z = np.load(W + "/eqh_%s.npz" % tag)
        self.eq = z["eq"]
        self.d = d.assign(key=okey(d))
        m0, m1, mg = d["m0"].to_numpy(), d["m1"].to_numpy(), d["margin"].to_numpy(float)
        o0, o1 = np.argsort(m0, kind="mergesort"), np.argsort(m1, kind="mergesort")
        self.s0, self.c0 = m0[o0], np.concatenate([[0.0], np.cumsum(mg[o0])])
        self.s1, self.c1 = m1[o1], np.concatenate([[0.0], np.cumsum(mg[o1])])
        self.l0 = np.sort(m0[d["leg0"].to_numpy()])

    def state(self, q):
        """q: DataFrame (sym, m0, key). Tra U, mopen, eqp, hold, p2 (gio), p3 (so chan 24h truoc)."""
        t = q["m0"].to_numpy()
        mopen = self.c0[np.searchsorted(self.s0, t, "left")] - self.c1[np.searchsorted(self.s1, t, "right")]
        qq = pd.DataFrame(dict(qi=np.arange(len(q)), sym=q["sym"].to_numpy(), m0=t, key=q["key"].to_numpy()))
        same = qq.merge(self.d[["m0", "key", "margin"]], on="m0", suffixes=("", "_l"))
        same = same[same["key_l"] < same["key"]].groupby("qi")["margin"].sum()
        mopen = mopen + same.reindex(np.arange(len(q)), fill_value=0.0).to_numpy()
        h = (t - 1 - H0_MIN) // 60
        eqp = np.where(h >= 0, self.eq[np.clip(h, 0, len(self.eq) - 1)], CAP0)
        U = np.where(eqp > 0, mopen / np.where(eqp > 0, eqp, 1.0), np.inf)

        hm = qq.merge(self.d[["sym", "m0", "m1", "key"]], on="sym", suffixes=("", "_l"))
        hm = hm[((hm["m0_l"] < hm["m0"]) | ((hm["m0_l"] == hm["m0"]) & (hm["key_l"] < hm["key"]))) & (hm["m1"] > hm["m0"])]
        hold = np.zeros(len(q), bool)
        hold[hm["qi"].unique()] = True
        i = np.searchsorted(self.l0, t, "left") - 1
        p2 = np.where(i >= 0, (t - self.l0[np.maximum(i, 0)]) / 60.0, np.inf)
        p3 = np.searchsorted(self.s0, t, "left") - np.searchsorted(self.s0, t - 1440, "left")
        return dict(U=U, mopen=mopen, eqp=eqp, hold=hold, p2=p2, p3=p3)


# ---------------------------------------------------------------- gate: gate_offline tren duong cua tung run
def cell(g, C, G, kk, ri, col, ok):
    """would (p15 >= thr) va P cua o (phut ri, cot col) duoi cau hinh G (top-kk). Cong thuc y run_g2 (float32)."""
    n = len(ri)
    would, P = np.zeros(n, bool), np.zeros(n, bool)
    v = ok & (col >= 0) & (col < kk)
    r, c = ri[v], col[v]
    sp = C["SP"][r, c]
    fac = np.maximum(g.DYN_MIN, (sp / g.SCORE_BASE) * g.DYN_MULT)
    thr = (G["qm"][r] * fac) * g.GS
    would[v] = ~np.isnan(sp) & ~(C["p15"][r] < thr)
    P[v] = G["P"][r, c]
    return would, P, v


def full_of(C, d, eq):
    """so day theo phut ung vien: U = margin mo (m0 < t <= ... m1 > t) / equity moc gio truoc t >= UMAX."""
    t = C["ts"] // 60000
    m0, m1, mg = d["m0"].to_numpy(), d["m1"].to_numpy(), d["margin"].to_numpy(float)
    o0, o1 = np.argsort(m0, kind="mergesort"), np.argsort(m1, kind="mergesort")
    c0, c1 = np.concatenate([[0.0], np.cumsum(mg[o0])]), np.concatenate([[0.0], np.cumsum(mg[o1])])
    mopen = c0[np.searchsorted(m0[o0], t, "left")] - c1[np.searchsorted(m1[o1], t, "right")]
    h = (t - 1 - H0_MIN) // 60
    eqp = np.where(h >= 0, eq[np.clip(h, 0, len(eq) - 1)], CAP0)
    return (eqp <= 0) | (mopen / np.where(eqp > 0, eqp, 1.0) >= UMAX)


def gate():
    import gate_offline as g
    take_lock()
    try:
        B = dict(np.load(g.CACHE + "/cand_base.npz"))
        mp = pd.read_csv(g.MAPF)
        s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
        L = {t: load(t)[0] for t in TAGS9}
        meta = {}
        for t in TAGS9:
            s = seed_of(t)
            K, pct = KCFG[t]
            g.K = max(K, K0)
            C = g.build(GSEED[s], B, s2id, pd_tag=t)
            eq = np.load(W + "/eqh_%s.npz" % t)["eq"]
            full = full_of(C, L[t], eq)
            sl = lambda k: dict(C, SP=C["SP"][:, :k], SY=C["SY"][:, :k], valid=C["valid"][:, :k], lock=C["lock"][:, :k])
            Gr = g.run_g2(sl(K), pct=np.float32(pct), J=1024, full=full)
            Gb = Gr if t in NEN.values() else g.run_g2(sl(K0), pct=np.float32(PCT0), J=1024, full=full)
            srcs = [t] if t in NEN.values() else [NEN[s], t]
            q = pd.concat([L[x][["sym", "m0", "row"]].assign(src=x) for x in srcs], ignore_index=True)
            ti = q["m0"].to_numpy() * 60000
            ri = np.clip(np.searchsorted(C["ts"], ti), 0, len(C["ts"]) - 1)
            has = C["ts"][ri] == ti
            sid = q["sym"].map(s2id).fillna(-1).astype(int).to_numpy()
            hit = C["SY"][ri, :] == sid[:, None]
            col = np.where(hit.any(1) & has, hit.argmax(1), -1)

            col = np.where((sid >= 0) & (col >= 0), col, -1)
            wr, pr_, vr = cell(g, C, Gr, K, ri, col, has)
            wb, pb, vb = cell(g, C, Gb, K0, ri, col, has)
            lk = np.where(col >= 0, C["lock"][ri, np.maximum(col, 0)], False)
            np.savez(W + "/gate_%s.npz" % t, src=q["src"].to_numpy().astype(str), row=q["row"].to_numpy(), has=has,
                     col=col, lock=lk, full=full[ri] & has, would_run=wr, P_run=pr_, in_run=vr, would_b=wb, P_b=pb, in_b=vb)
            sim = g.simlog(t)
            meta[t] = dict(K=K, pct=pct, pass_off=int(Gr["P"].sum()), pass_sim=sim["pass_"], seen_sim=sim["seen"],
                           seen_off=int((C["valid"][:, :K] & ~full[:, None]).sum()),
                           dev_pass_pct=100.0 * (int(Gr["P"].sum()) - sim["pass_"]) / max(1, sim["pass_"]),
                           full_min=int(full.sum()), n_min=int(len(full)), jmax=int(Gr["jmax"]),
                           pass_off_basecfg=int(Gb["P"].sum()))
            log.info("GATE %-16s %s", t, json.dumps(meta[t], default=jd))
            del C, Gr, Gb, hit
        json.dump(meta, open(W + "/gate_meta.json", "w"), default=jd, indent=1)
    finally:
        drop_lock()


# ---------------------------------------------------------------- j6: nen nhieu (thuoc gkf_rescore, MTM phut)
def j6(workers):
    import gkf_rescore as G
    R = G.R
    G.BAR_CACHE, G.MTM_CACHE = W + "/bar_j6.json", W + "/mtm_j6.json"
    tags = J6_K24 + list(J6_K16.values())
    legs = {t: R.load_legs(t) for t in tags}
    daily = {t: R.load_daily(t) for t in tags}
    md5 = {t: R.md5_of(t) for t in tags}
    bar = G.load_bars(legs, workers)
    conv = {}
    for t in tags:
        m, br, hit = G.crash_mask(legs[t], bar, 0)
        assert not np.isnan(br).any(), ("thieu nen", t)
        conv[t] = dict(crash=int(m.sum()), hit_lag0=float(hit.mean()))
        legs[t + "#S"] = G.stress_legs(legs[t], m)
        daily[t + "#S"] = G.stress_daily(daily[t], legs[t + "#S"])
    keys = tags + [t + "#S" for t in tags]
    km = {k: md5[k.split("#")[0]] + ("#S%.5f:lag0" % PEN if "#" in k else "") for k in keys}
    raw = json.load(open(G.MTM_CACHE)) if os.path.exists(G.MTM_CACHE) else {}
    old = json.load(open(NDEEP_MTM)) if os.path.exists(NDEEP_MTM) else {}
    for k in keys:
        if raw.get(k, {}).get("md5") != km[k] and old.get(k, {}).get("md5") == km[k]:
            raw[k] = old[k]
    miss = {k: legs[k] for k in keys if raw.get(k, {}).get("md5") != km[k]}
    log.info("J6 MTM cache %d/%d, tinh %d: %s", len(keys) - len(miss), len(keys), len(miss), sorted(miss))

    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, v in new.items():
            v["md5"] = km[k]
            raw[k] = v
    json.dump({k: raw[k] for k in keys}, open(G.MTM_CACHE, "w"))
    out = {}
    for k in keys:
        x = G.metrics(k, k.split("#")[0], legs[k], daily[k], raw[k]["legacy"])
        out[k] = dict(md5=km[k], n_per_year=x["n_per_year"], cagr22=x["cagr22"], dd22=x["dd_mtm22"],
                      cal22=x["calmar22"], uw22=x["uw_mtm22"], pnl2225=x["sum_pnl_2022_25"], yret=x["yret"])
        log.info("J6 %-18s n/y %.0f CAGR22 %.2f DD22 %.2f Cal %.3f PnL %.0f", k, x["n_per_year"], x["cagr22"],
                 x["dd_mtm22"], x["calmar22"], x["sum_pnl_2022_25"])
    json.dump(dict(metrics=out, conv=conv), open(W + "/j6.json", "w"), default=jd, indent=1)


# ---------------------------------------------------------------- analyze
def match(b, a, tol, use_lt):
    """Khop 1-1 DOC LAP: cap ung vien cung khoa, |dphut| <= tol; duyet (|dphut|, i_nen, i_arm) tang, tham lam.
    Tra b2a, a2b (-1 = khong khop), so chan nen/arm co >= 2 ung vien (mo ho)."""
    kb = (b["sym"] + "|" + b["lt"]) if use_lt else b["sym"]
    ka = (a["sym"] + "|" + a["lt"]) if use_lt else a["sym"]
    P = pd.DataFrame(dict(k=kb.to_numpy(), mb=b["m0"].to_numpy(), ib=np.arange(len(b)))).merge(
        pd.DataFrame(dict(k=ka.to_numpy(), ma=a["m0"].to_numpy(), ia=np.arange(len(a)))), on="k")
    P["dm"] = (P["ma"] - P["mb"]).abs()
    P = P[P["dm"] <= tol].sort_values(["dm", "ib", "ia"], kind="mergesort")
    amb_b = int((P.groupby("ib").size() > 1).sum())
    amb_a = int((P.groupby("ia").size() > 1).sum())
    b2a, a2b = np.full(len(b), -1), np.full(len(a), -1)
    for ib, ia in zip(P["ib"].to_numpy(), P["ia"].to_numpy()):
        if b2a[ib] < 0 and a2b[ia] < 0:
            b2a[ib], a2b[ia] = ia, ib
    return b2a, a2b, amb_b, amb_a


def win(d):
    return ((d["year"] >= 2022) & (d["year"] <= 2025)).to_numpy()


def j1(b, a, nd):
    """bao toan + nhay dung sai/khoa + so voi N_DEEP (tol 1, khoa sym, cua so entry 2022-25)."""
    res, wb, wa = {}, win(b), win(a)
    for tol in (0, 1, 5):
        for lt in (False, True):
            b2a, a2b, amb_b, amb_a = match(b, a, tol, lt)
            asg = b2a[b2a >= 0]
            ch = int(len(asg))
            r = dict(n_b=len(b), n_a=len(a), chung=ch, mat=int((b2a < 0).sum()), moi=int((a2b < 0).sum()),
                     dup=int(len(asg) - len(np.unique(asg))), amb_b=amb_b, amb_a=amb_a,
                     w_chung=int(((a2b >= 0) & wa).sum()), w_chung_b=int(((b2a >= 0) & wb).sum()),
                     w_mat=int(((b2a < 0) & wb).sum()), w_moi=int(((a2b < 0) & wa).sum()),
                     lt_mism=int((b["lt"].to_numpy()[b2a >= 0] != a["lt"].to_numpy()[asg]).sum()))
            r["cons"] = bool(r["chung"] + r["mat"] == len(b) and r["chung"] + r["moi"] == len(a)
                             and int((a2b >= 0).sum()) == ch and r["dup"] == 0)
            res["tol%d_%s" % (tol, "symlt" if lt else "sym")] = r
    r = res["tol1_sym"]
    cmp = {}
    for k, v in (("CHUNG", r["w_chung"]), ("MOI", r["w_moi"]), ("MAT", r["w_mat"])):
        ref = nd[k]["n"] if k == "CHUNG" else nd[k]["all"]["n"]
        cmp[k] = dict(mine=v, ndeep=ref, dev_pct=100.0 * (v - ref) / ref)
    cmp["lt_mism"] = dict(mine=r["lt_mism"], ndeep=nd["match_leg_mismatch"],
                          dev_pct=100.0 * (r["lt_mism"] - nd["match_leg_mismatch"]) / max(1, nd["match_leg_mismatch"]))
    res["vs_ndeep"] = cmp
    res["ndeep_pass"] = bool(all(abs(x["dev_pct"]) <= 2.0 for x in cmp.values()))
    res["cons_pass"] = bool(all(v["cons"] for k, v in res.items() if k.startswith("tol")))
    return res


def j1_pos(b, a, b2a_leg):
    """don vi LENH (cum): khop leg0 theo (sym, phut) tol 0/1/5; voi cap CHUNG (tol 1): ti le cum giong het
    (moi chan nen khop vao DUNG cum arm, cung so chan) va cung phut dong."""
    pb, pa = b[b["leg0"]].reset_index(drop=True), a[a["leg0"]].reset_index(drop=True)
    out = dict(n_pos_b=len(pb), n_pos_a=len(pa), legs_per_pos_b=len(b) / len(pb), legs_per_pos_a=len(a) / len(pa))
    for tol in (0, 1, 5):
        b2a, a2b, amb_b, amb_a = match(pb, pa, tol, False)
        ch = int((b2a >= 0).sum())
        out["tol%d" % tol] = dict(chung=ch, mat=int((b2a < 0).sum()), moi=int((a2b < 0).sum()), amb_b=amb_b,
                                  cons=bool(ch + int((b2a < 0).sum()) == len(pb) and ch + int((a2b < 0).sum()) == len(pa)),
                                  w_chung=int(((b2a >= 0) & win(pb)).sum()), w_mat=int(((b2a < 0) & win(pb)).sum()),
                                  w_moi=int(((a2b < 0) & win(pa)).sum()))
        if tol == 1:
            nleg_a = a.groupby("pid").size()
            same = same_end = 0
            for ib in np.nonzero(b2a >= 0)[0]:
                pid_b, pid_a = pb.at[ib, "pid"], pa.at[b2a[ib], "pid"]
                lb = np.nonzero(b["pid"].to_numpy() == pid_b)[0]
                mp = b2a_leg[lb]
                same += bool((mp >= 0).all() and (a["pid"].to_numpy()[mp] == pid_a).all() and len(lb) == nleg_a[pid_a])
                same_end += bool(pb.at[ib, "m1"] == pa.at[b2a[ib], "m1"])
            out["tol1"].update(same_comp=same / max(1, ch), same_end=same_end / max(1, ch))
    return out


def gtab(tag, src):
    z = np.load(W + "/gate_%s.npz" % tag)
    m = z["src"] == src
    return pd.DataFrame({k: z[k][m] for k in ("row", "has", "col", "lock", "full", "would_run", "P_run", "in_run",
                                              "would_b", "P_b", "in_b")}).set_index("row")


def j3(b, a, b2a, bk, ga, K, a2b=None):
    """MAT (nen co, arm khong; tol 1 khoa sym): nguyen nhan DOC QUYEN theo thu tu code + co khong doc quyen."""
    m = b[b2a < 0].copy()
    st = bk.state(m.assign(key=okey(m)))
    g = ga.reindex(m["row"].to_numpy())
    lt = m["lt"].to_numpy()
    leg0_of = b[b["leg0"]].set_index("pid").index
    l0idx = pd.Series(np.nonzero(b["leg0"].to_numpy())[0], index=b.loc[b["leg0"], "pid"].to_numpy())
    leg0_lost = (b2a[l0idx.reindex(m["pid"].to_numpy()).to_numpy()] < 0)
    bd_min = set(a.loc[a["lt"] == "BIGD", "m0"].tolist())
    f = dict(topk=(lt == "PRED") & (m["rank"].to_numpy(float) > K), hold=st["hold"], full=st["U"] >= UMAX,
             g_in=g["in_run"].fillna(False).to_numpy(bool), g_would=g["would_run"].fillna(False).to_numpy(bool),
             off_lock=g["lock"].fillna(False).to_numpy(bool), off_full=g["full"].fillna(False).to_numpy(bool),
             leg0_lost=leg0_lost & (lt == "DCA"), bd_same=m["m0"].isin(bd_min).to_numpy() & (lt == "BIGD"))
    del leg0_of

    cause = np.full(len(m), "", object)
    rules = [("PRED", "1_topK", f["topk"]), ("PRED", "2_giu_symbol", f["hold"]), ("PRED", "3_so_day_U", f["full"]),
             ("PRED", "4_gate_offline", f["g_in"] & ~f["g_would"]), ("PRED", "5_offline_khong_thay_o", ~f["g_in"]),
             ("PRED", "6_khong_giai_thich", np.ones(len(m), bool)),
             ("BIGD", "3_so_day_U", f["full"]), ("BIGD", "2_giu_symbol", f["hold"]),
             ("BIGD", "v_chon_khac_cung_phut", f["bd_same"]), ("BIGD", "6_khong_giai_thich", np.ones(len(m), bool)),
             ("DCA", "v_lech_duong_leg0", f["leg0_lost"]), ("DCA", "3_so_day_U", f["full"]),
             ("DCA", "2_giu_symbol_khac_cum", f["hold"]), ("DCA", "6_khong_giai_thich", np.ones(len(m), bool))]
    for t, name, msk in rules:
        sel = (lt == t) & (cause == "") & msk
        cause[sel] = name
    m["cause"] = cause
    for k, v in f.items():
        m["f_" + k] = v
    m["U_arm"], m["mopen_arm"], m["eq_arm"] = st["U"], st["mopen"], st["eqp"]
    w = m[win(m)]
    tot = dict(n=len(w), pnl_s=float(w["pnl_s"].sum()))
    out = dict(total=tot, n_all=len(m), cause={}, flags={}, by_lt={})
    for c, g2 in w.groupby("cause"):
        out["cause"][c] = dict(n=len(g2), share=100.0 * len(g2) / max(1, len(w)), pnl_s=float(g2["pnl_s"].sum()),
                               roi_s=float(g2["roi_s"].mean()), lt=g2["lt"].value_counts().to_dict(),
                               U_band_055_065=int(((g2["U_arm"] >= 0.55) & (g2["U_arm"] < 0.65)).sum()))

    for k in f:
        out["flags"][k] = int(w["f_" + k].sum())
    for t, g2 in w.groupby("lt"):
        out["by_lt"][t] = dict(n=len(g2), pnl_s=float(g2["pnl_s"].sum()))
    pr = w[w["lt"] == "PRED"]
    sub = pr[pr["f_g_in"]]
    out["check"] = dict(sum_ok=bool(sum(v["n"] for v in out["cause"].values()) == tot["n"]
                                    and abs(sum(v["pnl_s"] for v in out["cause"].values()) - tot["pnl_s"]) < 1e-6 * max(1, abs(tot["pnl_s"]))),
                        hold_vs_offlock=float((sub["f_hold"] == sub["f_off_lock"]).mean()) if len(sub) else None,
                        full_vs_offfull=float((pr["f_full"] == pr["f_off_full"]).mean()) if len(pr) else None)
    if a2b is not None:
        out["hold_detail"] = hold_detail(w[w["cause"] == "2_giu_symbol"], a, a2b)
    return out, m


def hold_detail(h, a, a2b):
    """MAT do 'giu symbol': cum arm dang giu coin do mo tu bao gio, leg0 cum do la MOI hay CHUNG, ROI_S leg0 do."""
    l0 = a[a["leg0"]]
    is_moi = pd.Series(a2b[a["leg0"].to_numpy()] < 0, index=l0["pid"].to_numpy())
    rs0 = pd.Series(l0["roi_s"].to_numpy(), index=l0["pid"].to_numpy())
    m0_0 = pd.Series(l0["m0"].to_numpy(), index=l0["pid"].to_numpy())
    x = h[["sym", "m0"]].reset_index().merge(a[["sym", "m0", "m1", "pid"]], on="sym", suffixes=("", "_a"))
    x = x[(x["m0_a"] <= x["m0"]) & (x["m1"] > x["m0"])].sort_values("m0_a").drop_duplicates("index", keep="last")
    if not len(x):
        return dict(n=0)
    dt = (x["m0"].to_numpy() - m0_0.reindex(x["pid"]).to_numpy()) / 60.0
    mo = is_moi.reindex(x["pid"]).to_numpy(bool)
    q = np.percentile(dt, [25, 50, 75, 90])
    return dict(n=int(len(x)), n_h=int(len(h)), share_arm_pos_moi=float(mo.mean()), dt_h_p25_50_75_90=[float(v) for v in q],
                share_dt_le24h=float(np.mean(dt <= 24)), roi_s_mat=float(h["roi_s"].mean()),
                roi_s_arm_leg0=float(np.nanmean(rs0.reindex(x["pid"].unique()).to_numpy())),
                n_arm_pos=int(x["pid"].nunique()))


BK = dict(p1=[0, .1, .2, .3, .4, .5, .6, np.inf], p2=[0, 1, 3, 6, 12, 24, 48, 96, np.inf],
          p3=[0, 1, 3, 6, 11, 21, 41, np.inf])           # bucket CO DINH truoc khi do (khong phai nguong)


def blab(v, e, unit=""):
    i = int(np.clip(np.searchsorted(e, v, "right") - 1, 0, len(e) - 2))
    lo, hi = e[i], e[i + 1]
    return "%02d[%g,%s)" % (i, lo, "inf" if not np.isfinite(hi) else "%g" % hi)


def j4_rows(df, grp, bk, g, K, arm, seed):
    """dac trung nhan qua tai luc vao, chi tu so cua arm (bk)."""
    st = bk.state(df.assign(key=okey(df)))
    gg = g.reindex(df["row"].to_numpy())
    pr = (df["lt"] == "PRED").to_numpy()
    in_b, wb = gg["in_b"].fillna(False).to_numpy(bool), gg["would_b"].fillna(False).to_numpy(bool)
    rk = df["rank"].to_numpy(float)
    p4 = np.where(~pr, "NA", np.where(in_b & wb, "nen", np.where(rk > K0, "noi_rank>24",
                  np.where(in_b, "noi_pct", "NA_offline"))))
    out = pd.DataFrame(dict(arm=arm, seed=seed, grp=grp, year=df["year"].to_numpy(), crash=df["crash"].to_numpy(),
                            lt=df["lt"].to_numpy(), pnl_s=df["pnl_s"].to_numpy(), roi_s=df["roi_s"].to_numpy(),
                            p1=st["U"], p2=st["p2"], p3=st["p3"].astype(float), p4=p4))
    for k, e in BK.items():
        out[k + "b"] = [blab(v, e) for v in out[k].to_numpy()]
    return out


def agg(g):
    """o bang: n/nam (TB seed), sum PnL_S (TB seed), ROI_S gop + tung seed, tach sap/khong sap, theo nam."""
    if not len(g):
        return dict(n=0)
    seeds = {s: x for s, x in g.groupby("seed")}
    r = dict(n=int(len(g)), n_per_year=len(g) / (4.0 * 3), pnl_s=float(g["pnl_s"].sum()) / 3.0,
             roi_s=float(g["roi_s"].mean()), roi_s_seed={s: float(x["roi_s"].mean()) for s, x in seeds.items()},
             n_seed={s: int(len(x)) for s, x in seeds.items()}, pnl_s_seed={s: float(x["pnl_s"].sum()) for s, x in seeds.items()})
    for c, x in g.groupby("crash"):
        r["sap" if c else "khong_sap"] = dict(n_per_year=len(x) / 12.0, roi_s=float(x["roi_s"].mean()),
                                               pnl_s=float(x["pnl_s"].sum()) / 3.0)
    r["year"] = {int(y): dict(n=int(len(x)), roi_s=float(x["roi_s"].mean()), pnl_s=float(x["pnl_s"].sum()) / 3.0)
                 for y, x in g.groupby("year")}
    return r


def j4_summary(J):
    out = {}
    for (arm, grp), g in J.groupby(["arm", "grp"]):
        d = out.setdefault(arm, {}).setdefault(grp, {"all": agg(g)})
        for k in ("p1b", "p2b", "p3b", "p4"):
            d[k] = {b: agg(x) for b, x in g.groupby(k)}
    return out


def checks_run(t, d, meta, am, upd, cpc):
    """tu kiem du lieu + tai lap so (U/equity/gate) tren chinh run t."""
    eq = np.load(W + "/eqh_%s.npz" % t)
    h = ((upd["m"].to_numpy() - H0_MIN) // 60).astype(int)
    v = (h >= 0) & (h < len(eq["eq"]))
    u2, h = upd[v], h[v]
    dmg = np.abs(eq["mg"][h] - u2["mg"].to_numpy())
    db = np.abs(CAP0 + eq["real"][h] - u2["b"].to_numpy())
    du = np.abs(eq["u"][h] - u2["unp"].to_numpy())
    deq = np.abs(eq["eq"][h] / (u2["b"].to_numpy() + u2["unp"].to_numpy()) - 1)
    bk = Book(t, d)
    pr = d[d["lt"] == "PRED"]
    st = bk.state(pr.assign(key=okey(pr)))
    g = gtab(t, t).reindex(pr["row"].to_numpy())
    l0 = d[d["leg0"]]
    ov = 0
    for s, x in l0.sort_values("m0").groupby("sym"):
        ov += int((x["m0"].to_numpy()[1:] < x["m1"].to_numpy()[:-1]).sum())
    c = dict(n=meta["n"], n_result=meta["n_trades_result"], n_raw=meta["n_raw"], margin_eq_notional=meta["margin_eq_notional"],
             **am, conc_pc_blocked=cpc, pos=int(len(l0)), leg0_dca=int((l0["lt"] == "DCA").sum()), pos_overlap=ov,
             upd_days=int(len(u2)), mg_absdiff_p50=float(np.median(dmg)), mg_absdiff_max=float(dmg.max()),
             mg_rel_le1pct=float(np.mean(dmg <= 0.01 * np.abs(u2["mg"].to_numpy()) + 1)),
             b_absdiff_p50=float(np.median(db)), b_absdiff_max=float(db.max()),
             unp_absdiff_p50=float(np.median(du)), unp_absdiff_p99=float(np.percentile(du, 99)),
             eq_relerr_p50=float(np.median(deq)), eq_relerr_p99=float(np.percentile(deq, 99)),
             own_pred_U_ge_umax=float(np.mean(st["U"] >= UMAX)), own_pred_hold=float(np.mean(st["hold"])),
             own_pred_U_p99=float(np.percentile(st["U"], 99)),
             off_in_run=float(g["in_run"].fillna(False).mean()), off_would=float(g["would_run"].fillna(False).mean()),
             off_P=float(g["P_run"].fillna(False).mean()),
             off_rank_eq=float(np.mean(g["col"].fillna(-9).to_numpy() + 1 == pr["rank"].to_numpy())))
    return c


def analyze():
    nd = json.load(open(NDEEP_JSON))
    bar = json.load(open(NDEEP_BAR))["bar"]
    L, CK = {}, {}
    for t in TAGS9:
        d, meta = load(t)
        sel, upd, cpc = logscan(t)
        am = attach(d, sel, bar)
        L[t] = d
        CK[t] = checks_run(t, d, meta, am, upd, cpc)
        log.info("CHECK %-16s %s", t, json.dumps(CK[t], default=jd))
    del bar
    gm = json.load(open(W + "/gate_meta.json"))
    J1, J1P, J3, J3n, Jrows = {}, {}, {}, {}, []
    for arm, (K, pct, m) in ARMS.items():
        for s in SEEDS:
            b, a = L[NEN[s]], L[m[s]]
            key = "%s|%s" % (arm, s)
            J1[key] = j1(b, a, nd["d3"]["%s|%s" % (NDK[arm], s)])
            b2a, a2b, _, _ = match(b, a, 1, False)
            J1P[key] = j1_pos(b, a, b2a)
            bk = Book(m[s], a)
            J3[key], mm = j3(b, a, b2a, bk, gtab(m[s], NEN[s]), K, a2b)
            J3n[key] = mm
            ga = gtab(m[s], m[s])
            wa, wb = win(a), win(b)
            Jrows.append(j4_rows(a[(a2b < 0) & wa], "MOI", bk, ga, K, arm, s))
            Jrows.append(j4_rows(a[(a2b >= 0) & wa], "CHUNG", bk, ga, K, arm, s))
            Jrows.append(j4_rows(b[(b2a < 0) & wb], "MAT", bk, gtab(m[s], NEN[s]), K, arm, s))
            log.info("J1 %s cons=%s ndeep=%s %s", key, J1[key]["cons_pass"], J1[key]["ndeep_pass"], J1[key]["vs_ndeep"])
            log.info("J3 %s %s", key, json.dumps(J3[key]["cause"], default=jd))
    J = pd.concat(Jrows, ignore_index=True)
    J = pd.concat([J, J[J["grp"] != "MAT"].assign(grp="ARM")], ignore_index=True)
    J4 = j4_summary(J)
    J.to_csv(W + "/j4_rows.csv.gz", index=False)
    pd.concat(J3n.values(), keys=list(J3n), names=["key", "i"]).to_csv(W + "/j3_mat_rows.csv.gz")
    J6 = j6_summary(nd) if os.path.exists(W + "/j6.json") else None
    gate_ck = {t: dict(dev_pass_pct=gm[t]["dev_pass_pct"], pass_off=gm[t]["pass_off"], pass_sim=gm[t]["pass_sim"],
                       full_min=gm[t]["full_min"], pass_off_basecfg=gm[t]["pass_off_basecfg"]) for t in TAGS9}
    js = dict(title="NSEL_P0_DATA 2026-10-08", script="research/analysis/nsel_p0_data.py", note=(
        "chi phan tich output co san; 0 sim/Kaggle/Java/242; chan doan, khong chon nguong; MAT/MOI/CHUNG = khop tol 1 khoa sym;"
        " cua so entry 2022-25; stress COST_TRUTH 1,675%/chan nen lag0 sap"), pen=PEN, umax=UMAX, buckets=BK,
        checks=CK, gate=gate_ck, j1=J1, j1_pos=J1P, j3=J3, j4=J4, j6=J6)
    json.dump(js, open(JSON_OUT, "w"), default=jd, indent=1, ensure_ascii=False)
    log.info("ghi %s", JSON_OUT)
    write_md(js)


def msd(v):
    v = [float(x) for x in v if x is not None and np.isfinite(x)]
    return dict(mean=float(np.mean(v)), sd=float(np.std(v, ddof=1)) if len(v) > 1 else None, n=len(v), vals=v)


def mde(sd, n=3):
    return dict(mde50=T95_2 * sd / math.sqrt(n), mde80=(T95_2 + T80_2) * sd / math.sqrt(n)) if sd else None


def j6_summary(nd):
    z = json.load(open(W + "/j6.json"))
    M = z["metrics"]
    ref = {"gqsf-a1": "NEN|S42", "gqsf-s7": "NEN|S7", "gqsf-s21": "NEN|S21", "gqsf16-a1": "R_K16on|S42",
           "gqsf16-s7": "R_K16on|S7", "gqsf16-s21": "R_K16on|S21"}
    flds = ("n_per_year", "cagr22", "dd22", "cal22", "pnl2225")
    bad = [(t + sfx, f, M[t + sfx][f], nd["rows"][k + "|" + rs][f]) for t, k in ref.items()
           for sfx, rs in (("", "b"), ("#S", "#S")) for f in flds
           if abs(M[t + sfx][f] - nd["rows"][k + "|" + rs][f]) > 1e-6 * max(1.0, abs(nd["rows"][k + "|" + rs][f]))]
    out = dict(selfcheck=dict(n_keys=2 * len(ref), n_fields=len(flds), bad=bad, ok=not bad), conv=z["conv"], stat={})
    for sfx, lab in (("", "base"), ("#S", "stress")):
        for f in ("pnl2225", "cagr22", "dd22", "cal22"):
            k24 = msd([M[t + sfx][f] for t in J6_K24])
            k16 = msd([M[t + sfx][f] for t in J6_K16.values()])
            dl = msd([M[J6_K16[s] + sfx][f] - M[NEN[s] + sfx][f] for s in SEEDS])
            out["stat"]["%s|%s" % (lab, f)] = dict(K24=k24, K16=k16, d_K16_K24=dl, mde_pair=mde(dl["sd"]),
                                                    mde_unpaired_rho0=mde(k24["sd"] * math.sqrt(2)))
    out["arms_delta"] = {}
    for k, v in nd["delta"].items():
        if k.endswith("|b") or k.endswith("|#S"):
            x = v.get("pnl2225")
            if isinstance(x, dict) and x.get("sd"):
                out["arms_delta"][k] = dict(mean=x["mean"], sd=x["sd"], n=x.get("n"), mde=mde(x["sd"]))
    return out



def fm(x, nd=2, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return (("%+." if sign else "%.") + str(nd) + "f") % x


def cellj4(r):
    if not r or not r.get("n"):
        return "—"
    v = list(r["roi_s_seed"].values())
    return "%s · %s [%s..%s] · %s" % (fm(r["n_per_year"], 0), fm(r["roi_s"]), fm(min(v)), fm(max(v)), fm(r["pnl_s"] / 1000, 1))


def tbl(h, rows):
    return ["| " + " | ".join(h) + " |", "|" + "---|" * len(h)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in rows]


def write_md(js):
    o = ["### T0. Tu kiem du lieu / tai lap (tung run)"]
    rows = []
    for t, c in js["checks"].items():
        gk = js["gate"][t]
        rows.append([t, "%d/%s" % (c["n"], c["n_result"]), fm(c["pred_rank_join"], 4), c["bar_missing"], fm(c["hit_lag0"], 4),
                     c["conc_pc_blocked"], "%d/%d" % (c["leg0_dca"], c["pos_overlap"]),
                     "%s/%s (%s)" % (fm(c["mg_absdiff_p50"], 1), fm(c["mg_absdiff_max"], 1), fm(c["mg_rel_le1pct"], 4)),
                     "%s/%s" % (fm(100 * c["eq_relerr_p50"], 3), fm(100 * c["eq_relerr_p99"], 3)),
                     "%s/%s" % (fm(100 * c["own_pred_U_ge_umax"], 2), fm(100 * c["own_pred_hold"], 2)), fm(c["own_pred_U_p99"], 3),
                     "%s/%s/%s" % (fm(100 * c["off_in_run"], 1), fm(100 * c["off_P"], 1), fm(100 * c["off_rank_eq"], 1)),
                     "%d/%d (%s%%)" % (gk["pass_off"], gk["pass_sim"], fm(gk["dev_pass_pct"], 2)), gk["full_min"]])
    o += tbl(["run", "n/result", "rank join PRED", "thieu nen", "entry==close lag0", "CONC-PC blocked", "leg0 DCA/cum chong",
              "|dm| p50/max (<=1%)", "eq err% p50/p99", "PRED tu than U>=0,6 % / giu %", "U p99 PRED",
              "offline o/P/rank== %", "pass off/sim (lech)", "phut so day"], rows)
    return write_md2(js, o)


def write_md2(js, o):
    o += ["", "### T1. J1 matching doc lap (don vi chan). CHUNG/MAT/MOI toan run | cua so 2022-25; bao toan; mo ho; trung"]
    rows = []
    for key, r in js["j1"].items():
        for v in ("tol0_sym", "tol1_sym", "tol5_sym", "tol0_symlt", "tol1_symlt", "tol5_symlt"):
            x = r[v]
            rows.append([key, v, "%d/%d/%d" % (x["chung"], x["mat"], x["moi"]), "%d/%d/%d" % (x["w_chung"], x["w_mat"], x["w_moi"]),
                         "PASS" if x["cons"] else "FAIL", "%d/%d" % (x["amb_b"], x["amb_a"]), x["dup"], x["lt_mism"]])
    o += tbl(["arm|seed", "khoa", "CHUNG/MAT/MOI", "cua so 22-25", "bao toan", "mo ho nen/arm", "trung", "lech leg type"], rows)
    o += ["", "So voi N_DEEP (tol 1, khoa sym, cua so 22-25): mine / N_DEEP (lech %)"]
    rows = []
    for key, r in js["j1"].items():
        c = r["vs_ndeep"]
        rows.append([key] + ["%d/%d (%s)" % (c[k]["mine"], c[k]["ndeep"], fm(c[k]["dev_pct"], 2, True))
                             for k in ("CHUNG", "MAT", "MOI", "lt_mism")] + ["PASS" if r["ndeep_pass"] else "FAIL"])
    o += tbl(["arm|seed", "CHUNG", "MAT", "MOI", "lech leg type", "<=2%"], rows)
    o += ["", "Don vi LENH (cum = (sym, end)): leg0 khop tol 0/1/5 -> CHUNG/MAT/MOI; cum CHUNG giong het / cung phut dong"]
    rows = []
    for key, r in js["j1_pos"].items():
        rows.append([key, "%d/%d" % (r["n_pos_b"], r["n_pos_a"])] + ["%d/%d/%d %s" % (r[t]["chung"], r[t]["mat"], r[t]["moi"],
                    "PASS" if r[t]["cons"] else "FAIL") for t in ("tol0", "tol1", "tol5")] +
                    [fm(100 * r["tol1"]["same_comp"], 1), fm(100 * r["tol1"]["same_end"], 1)])
    o += tbl(["arm|seed", "so cum nen/arm", "tol0", "tol1", "tol5", "giong het %", "cung dong %"], rows)
    return write_md3(js, o)


def write_md3(js, o):
    o += ["", "### T2. J3 nguyen nhan MAT (doc quyen, thu tu code; cua so entry 2022-25). O = n (% MAT) · sum PnL_S k · ROI_S %"]
    for arm in ARMS:
        ks = ["%s|%s" % (arm, s) for s in SEEDS]
        causes = sorted({c for k in ks for c in js["j3"][k]["cause"]})
        rows = []
        for c in causes:
            r = [c]
            for k in ks:
                x = js["j3"][k]["cause"].get(c)
                r.append("%d (%s) · %s · %s" % (x["n"], fm(x["share"], 1), fm(x["pnl_s"] / 1000, 1), fm(x["roi_s"]))
                         if x else "0")
            v = [js["j3"][k]["cause"].get(c, {}) for k in ks]
            r.append("%s · %s" % (fm(np.mean([x.get("share", 0) for x in v]), 1), fm(np.mean([x.get("pnl_s", 0) for x in v]) / 1000, 1)))
            rows.append(r)
        rows.append(["TONG"] + ["%d · %s · %s" % (js["j3"][k]["total"]["n"], fm(js["j3"][k]["total"]["pnl_s"] / 1000, 1),
                                                  "PASS" if js["j3"][k]["check"]["sum_ok"] else "FAIL") for k in ks] + [""])
        o += ["", "Arm %s (K%d, pct %s)" % (arm, ARMS[arm][0], ARMS[arm][1])]
        o += tbl(["nguyen nhan", "S42", "S7", "S21", "TB % · TB PnL_S k"], rows)
        rows = [[k] + [js["j3"][k]["flags"][f] for f in ("topk", "hold", "full", "g_in", "g_would", "leg0_lost", "bd_same")] +
                [fm(js["j3"][k]["check"]["hold_vs_offlock"], 4), fm(js["j3"][k]["check"]["full_vs_offfull"], 4)] for k in ks]
        o += ["", "Co KHONG doc quyen (so chan MAT co co) + do khop co giu/so day voi gate_offline:"]
        o += tbl(["arm|seed", "topK", "giu", "so day", "offline co o", "offline would", "leg0 MAT (DCA)", "BD cung phut",
                  "giu==lock off", "full==full off"], rows)
    o += ["", "MAT do 'giu symbol': arm da giu CUNG coin luc nen vao. Cum arm do: % la MOI, gio tu leg0 cum arm den luc nen vao (p25/50/75/90), ROI_S MAT vs ROI_S leg0 cum arm"]
    rows = []
    for k, v in js["j3"].items():
        h = v.get("hold_detail") or {}
        if h.get("n"):
            rows.append([k, "%d/%d" % (h["n"], h["n_h"]), h["n_arm_pos"], fm(100 * h["share_arm_pos_moi"], 1),
                         "/".join(fm(x, 1) for x in h["dt_h_p25_50_75_90"]), fm(100 * h["share_dt_le24h"], 1),
                         fm(h["roi_s_mat"]), fm(h["roi_s_arm_leg0"])])
    o += tbl(["arm|seed", "n tim thay/n", "so cum arm", "cum arm la MOI %", "gio p25/50/75/90", "<=24h %", "ROI_S MAT", "ROI_S leg0 arm"], rows)
    return write_md4(js, o)


def write_md4(js, o):
    o += ["", "### T3. J4 proxy nhan qua (chi qua khu cua arm), cua so entry 2022-25, stress 1,675.",
          "O = n/nam (TB 3 seed) · ROI_S % gop [min..max seed] · sum PnL_S k (TB seed). MAT = chan nen bi mat, dac trung lay tu SO ARM."]
    nm = dict(p1b="p1 = U arm truoc khi vao", p2b="p2 = gio tu leg0 gan nhat cua arm", p3b="p3 = so chan arm vao trong 24h truoc",
              p4="p4 = gate NEN (K24, pct nen) tai lap tren duong arm (chi PRED)")
    for arm in ARMS:
        G = js["j4"][arm]
        for k in ("p1b", "p2b", "p3b", "p4"):
            bs = sorted({b for g in ("MOI", "CHUNG", "MAT", "ARM") for b in G.get(g, {}).get(k, {})})
            rows = []
            for b in bs:
                mo = G["MOI"][k].get(b, {})
                rows.append([b] + [cellj4(G[g][k].get(b)) for g in ("ARM", "MOI", "CHUNG", "MAT")] +
                            ["%s / %s" % (fm(mo.get("sap", {}).get("roi_s")), fm(mo.get("khong_sap", {}).get("roi_s")))] +
                            ["/".join(fm(mo.get("year", {}).get(y, {}).get("roi_s"), 1) for y in YEARS)])
            o += ["", "Arm %s — %s" % (arm, nm[k])]
            o += tbl(["bucket", "ARM (MOI+CHUNG)", "MOI", "CHUNG", "MAT", "MOI ROI_S sap/khong", "MOI ROI_S 22/23/24/25"], rows)
        a = G
        o += ["", "Arm %s tong: ARM %s | MOI %s | CHUNG %s | MAT %s" % (arm, cellj4(a["ARM"]["all"]), cellj4(a["MOI"]["all"]),
                                                                     cellj4(a["CHUNG"]["all"]), cellj4(a["MAT"]["all"]))]
    return write_md5(js, o)


def write_md5(js, o):
    J6 = js["j6"]
    if J6:
        o += ["", "### T4. J6 nen nhieu (thuoc gkf_rescore MTM phut, cua so 2022+; stress 1,675). Tu kiem vs N_DEEP rows: %d khoa x %d truong, lech %d"
              % (J6["selfcheck"]["n_keys"], J6["selfcheck"]["n_fields"], len(J6["selfcheck"]["bad"]))]
        rows = []
        for k, v in J6["stat"].items():
            mp = v["mde_pair"] or {}
            mu = v["mde_unpaired_rho0"] or {}
            rows.append([k, "%s ± %s (n=%d)" % (fm(v["K24"]["mean"]), fm(v["K24"]["sd"]), v["K24"]["n"]),
                         "%s ± %s" % (fm(v["K16"]["mean"]), fm(v["K16"]["sd"])),
                         "%s ± %s" % (fm(v["d_K16_K24"]["mean"], 2, True), fm(v["d_K16_K24"]["sd"])),
                         "%s / %s" % (fm(mp.get("mde50")), fm(mp.get("mde80"))), "%s / %s" % (fm(mu.get("mde50")), fm(mu.get("mde80")))])
        o += tbl(["phi|chi so", "K24 8 seed mean ± sd", "K16 3 seed", "Δ K16−K24 ghep cap (3)", "MDE ghep cap 50%/80%",
                  "MDE khong ghep ρ=0 50%/80%"], rows)
        rows = [[k, fm(v["mean"], 0, True), fm(v["sd"], 0), "%s / %s" % (fm(v["mde"]["mde50"], 0), fm(v["mde"]["mde80"], 0))]
                for k, v in J6["arms_delta"].items()]
        o += ["", "Δ sum PnL22-25 ghep cap theo seed tu N_DEEP (arm − NEN): sd va MDE 3 seed (t df=2, α=0,05 mot phia)"]
        o += tbl(["arm|phi", "mean Δ", "sd Δ", "MDE 50%/80%"], rows)
    with open(MD_OUT, "w") as f:
        f.write("\n".join(o) + "\n")
    log.info("ghi %s", MD_OUT)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["prep", "gate", "j6", "analyze"])
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(W, exist_ok=True)
    {"prep": lambda: prep(a.workers), "gate": gate, "j6": lambda: j6(a.workers), "analyze": analyze}[a.stage]()
