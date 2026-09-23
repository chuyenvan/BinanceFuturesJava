#!/usr/bin/env python3
"""FUNDING_TOPK_LONG — huong DOI XUNG: LONG top-K coin FUNDING CAO, do offline (0-sim).

Pre-reg: docs/PREREG_FUNDING_TOPK_LONG.md (commit da76e41, chot TRUOC khi chay; KHONG sua thiet ke).

Thuan Python. Chi DOC: Aerospike test.funding_data + raw/<sym>.f32 (1m OHLCV) + cache2.npz (neo MOM15)
+ printDone.csv cua run T170 (proxy universe he thong, causal).

Quy uoc dau (KHOA, = Binance that, kiem chung o docs/RESULT_FUNDING_SIGN.md):
  rate > 0  =>  LONG TRA, SHORT THU.   f_cyc = 100*sum(rate) tren (t_e, t_x]  (%/notional).
  => LONG top-decile funding CAO: funding la CHI PHI (-f_cyc). KHONG duoc bo qua.

Bien the: V1 pure (long top-decile f_sig) | V2 loc momentum (f_sig>p90 & ret24>0)
          V3 trong universe he thong (T170 printDone causal)
Doi chung: U long universe EW | L2 long bottom-decile (huong long-side da thua)
           S1 short top-decile (tai lap RESULT_SHORT_CARRY V1) | neo MOM15 (cache2, M-LEVEL k=1)

Out (ngoai repo): /home/ubuntu/claudedata/funding_topk_long/{grid.npz,anchor.npz,report.txt,summary.json}
"""
import os
import json
import time
import logging
import datetime as dt

import numpy as np
import pandas as pd
import aerospike
import cramjam

OUT = os.environ.get("FKL_OUT", "/home/ubuntu/claudedata/funding_topk_long")
RAW = os.environ.get("FKL_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
CACHE2 = os.environ.get("FKL_CACHE2", "/tmp/funding_factor/cache2.npz")
T170 = os.environ.get("FKL_T170",
                       "/home/ubuntu/java/devrun/X1_GS_T170_2021_SEL_DROP_TOP8/storage/printDone.csv")
AERO = ("127.0.0.1", 3222)
NS, SET = "test", "funding_data"

SEED = 20260905
NREP = 2000
NULL_REPS = 300
MDE_OUTER, MDE_INNER = 2000, 200
BLOCK_MIN = 72 * 60
CI_INFLATE = 1.21
MDE_GRID = [0.01, 0.02, 0.05, 0.10, 0.20, 0.50]   # %/chu ky
MIN_SYM = 50
HOLD = 480                     # 8h
LEVEL = 480
DD_BIG = 0.20                  # drawdown > 20% (canh bao mua dinh)
ANCHOR_HOLD = 1440             # MOM15 M-LEVEL 24h
FEE_ANCHOR = 0.0010            # 0,10% round-trip (quy uoc vong truoc cho MOM15)

# chi phi
FEE_TAKER = 0.0005             # 0,05%/chan
FEE_MAKER = 0.0002             # 0,02%/chan
SLIP_FLAT_HI = 0.0014          # 0,140%/chan
SLIP_FLAT_LO = 0.0001          # 1 bp/chan

UTC = dt.timezone.utc
BASE = int(dt.datetime(2021, 1, 1, tzinfo=UTC).timestamp() // 60)      # 26824320
NMIN = int(dt.datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60) - BASE   # 2629440
DEV_LO = int(dt.datetime(2022, 1, 1, tzinfo=UTC).timestamp() // 60)
DEV_HI = int(dt.datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

os.makedirs(OUT, exist_ok=True)
log = logging.getLogger("fklong")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())
log.addHandler(logging.FileHandler(OUT + "/report.txt", mode="a"))
REP = []


def say(s=""):
    REP.append(str(s))
    log.info(s)


def utc_min(m):
    return pd.Timestamp((BASE + int(m)) * 60000, unit="ms", tz="UTC").strftime("%Y-%m-%d %H:%M")


def nb(x):
    return f"{int(x):,}".replace(",", " ")


# =====================================================================================
# STAGE A — grid (mark, symbol) + neo MOM15
# =====================================================================================
def build():
    files = sorted(f for f in os.listdir(RAW) if f.endswith(".f32"))
    symidx = {f[:-4]: i for i, f in enumerate(files)}
    marks = np.arange(0, NMIN - HOLD, LEVEL, dtype=np.int64)
    M, S = len(marks), len(files)
    say("=" * 100)
    say("FUNDING_TOPK_LONG — build grid | %d symbol | %d moc | pre-reg da76e41" % (S, M))
    say("=" * 100)

    # ---- neo MOM15: cache2 (fire8 = phut fire, ml_* = M-LEVEL k=1 rows) ----
    z2 = np.load(CACHE2)
    ref_total_rows = int(z2["total_rows"])
    fire8 = z2["fire8"].astype(np.int64)
    ml_min = z2["ml_min"].astype(np.int64)
    ml_sym = z2["ml_sym"].astype(np.int64)
    say("[A0] cache2: total_rows=%s fire8=%d ml_rows=%d | fire8 range [%d, %d] | ml range [%d, %d]"
        % (nb(ref_total_rows), len(fire8), len(ml_min), fire8.min(), fire8.max(),
           ml_min.min(), ml_min.max()))
    is_fire = np.zeros(NMIN, dtype=bool)
    ff = fire8[(fire8 >= 0) & (fire8 < NMIN)]
    is_fire[ff] = True
    csum_fire = np.concatenate(([0], np.cumsum(is_fire.astype(np.int32))))
    # MOM15-active(r): co it nhat 1 phut fire trong [r-1440, r]
    lo_f = np.clip(marks - ANCHOR_HOLD, 0, NMIN)
    mom_active = (csum_fire[np.clip(marks, 0, NMIN)] - csum_fire[lo_f]) > 0
    slot_m = np.argsort(ml_sym, kind="stable")
    ml_sym_s = ml_sym[slot_m]
    bounds_m = np.searchsorted(ml_sym_s, np.arange(S + 1))

    # ---- universe he thong (proxy T170 printDone, causal) ----
    t170_start = np.full(S, np.iinfo(np.int64).max, dtype=np.int64)
    n_t170_seen = 0
    if os.path.exists(T170):
        d = pd.read_csv(T170, usecols=["sym", "start"])
        for sym, st in zip(d["sym"].astype(str), d["start"].astype(str)):
            i = symidx.get(sym)
            if i is None:
                i = symidx.get(sym + "USDT")          # printDone khong co hau to USDT
            if i is None:
                continue
            try:
                ts = pd.Timestamp(st.strip(), tz="UTC")
            except Exception:
                continue
            if pd.isna(ts):
                continue
            mm = int(ts.timestamp() // 60) - BASE
            t170_start[i] = min(t170_start[i], max(mm, 0))
            n_t170_seen += 1
    n_t170_sym = int((t170_start < np.iinfo(np.int64).max).sum())
    # in_t170[s, t] = symbol da co >=1 lenh mo tai/before moc r  (causal, mo rong dan)
    in_t170 = (t170_start[:, None] <= marks[None, :])
    say("[A0b] T170 proxy: %d dong | %d/%d symbol co lenh | universe tai moc cuoi: %d symbol"
        % (n_t170_seen, n_t170_sym, S, int(in_t170[:, -1].sum())))

    t0 = time.time()
    cli = aerospike.client({"hosts": [AERO], "policies": {"timeout": 60000}}).connect()

    F = {k: np.full((S, M), np.nan, dtype=np.float32) for k in
         ("c_e", "c_x", "slip_e", "slip_f", "f_sig", "f_cyc", "ret24", "dd", "up")}
    FL = {k: np.zeros((S, M), dtype=np.int8) for k in ("valid", "delist")}

    # neo MOM15 accumulators
    A = {k: [] for k in ("raw", "slip", "fund", "ok", "blk")}
    nfund = nerr = 0
    for si, fn in enumerate(files):
        sym = fn[:-4]
        try:
            a = np.fromfile(os.path.join(RAW, fn), dtype=DT)
        except Exception:
            nerr += 1
            continue
        if len(a) < 30:
            continue
        ts = a["ts"].astype(np.int64) - BASE
        o = np.argsort(ts, kind="stable")
        ts, h, l, c = ts[o], a["h"][o].astype(np.float32), a["l"][o].astype(np.float32), a["c"][o].astype(np.float32)
        keep = (ts >= 0) & (ts < NMIN)
        ts, h, l, c = ts[keep], h[keep], l[keep], c[keep]
        n = len(ts)
        if n < 480:
            continue

        # ---- entry/exit ----
        i1 = np.searchsorted(ts, marks)
        i1c = np.clip(i1, 0, n - 1)
        e_ok = (i1 < n) & (ts[i1c] == marks)
        i2 = np.searchsorted(ts, marks + HOLD)
        i2c = np.clip(i2, 0, n - 1)
        x_ok = (i2 < n) & (ts[i2c] == marks + HOLD)
        delist = (~x_ok) & e_ok & (ts[-1] > marks)
        idx_x = np.where(x_ok, i2c, n - 1)
        ok = e_ok & (x_ok | delist)

        c_e = c[i1c].astype(np.float32)
        c_x = np.where(ok, c[idx_x].astype(np.float32), np.nan)
        h_e, l_e = h[i1c].astype(np.float32), l[i1c].astype(np.float32)
        slip_e = np.where(ok & (c_e > 0), 0.5 * (h_e - l_e) / np.maximum(c_e, 1e-12), np.nan)
        slip_f = np.where(ok, 0.5 * (h[idx_x] - l[idx_x]) / np.maximum(c[idx_x], 1e-12), np.nan).astype(np.float32)
        ok = ok & (c_e > 0)
        c_x = np.where(ok, c_x, np.nan)

        # ---- ret24 ----
        i0 = np.searchsorted(ts, marks - 1440)
        i0c = np.clip(i0, 0, n - 1)
        ok24 = (i0 < n) & (ts[i0c] == marks - 1440) & ok
        ret24 = np.where(ok24, c[i0c] / np.maximum(c_e, 1e-12) - 1.0, np.nan).astype(np.float32)

        # ---- MAE long = drawdown (min low), MFE = max high, trong (mark, mark+480] ----
        hf = np.full(NMIN, np.nan, dtype=np.float32)
        lf = np.full(NMIN, np.nan, dtype=np.float32)
        hf[ts], lf[ts] = h, l
        rmax = pd.Series(hf).rolling(HOLD, min_periods=1).max().shift(-HOLD).to_numpy(dtype=np.float32)
        rmin = pd.Series(lf).rolling(HOLD, min_periods=1).min().shift(-HOLD).to_numpy(dtype=np.float32)
        dd = np.where(ok, rmin[marks] / np.maximum(c_e, 1e-12) - 1.0, np.nan).astype(np.float32)   # ADVERSE cho long
        up = np.where(ok, rmax[marks] / np.maximum(c_e, 1e-12) - 1.0, np.nan).astype(np.float32)   # FAVOR cho long
        del hf, lf, rmax, rmin

        # ---- funding ----
        ft = fr = cum = None
        rec = cli.get((NS, SET, sym))
        bd = rec[2] if isinstance(rec, tuple) else None
        if bd and "f_data" in bd:
            d = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(bd["f_data"]))))
            if d:
                ks = np.fromiter((int(k) for k in d), dtype=np.int64, count=len(d))
                vs = np.fromiter((float(d[str(k)]) for k in ks), dtype=np.float64, count=len(ks))
                od = np.argsort(ks, kind="stable")
                ft, fr = ks[od], vs[od]
                cum = np.concatenate(([0.0], np.cumsum(fr)))
                nfund += 1
        if ft is not None:
            t_e = (BASE + marks) * 60000
            t_x = np.where(x_ok, (BASE + marks + HOLD) * 60000, (BASE + int(ts[-1])) * 60000)
            lo = np.searchsorted(ft, t_e, side="right")
            hi = np.searchsorted(ft, t_x, side="right")
            f_cyc = (100.0 * (cum[hi] - cum[lo])).astype(np.float32)
            j = lo - 1
            f_sig = np.where(j >= 0, fr[np.clip(j, 0, len(fr) - 1)], np.nan).astype(np.float32)
        else:
            f_cyc = np.full(M, np.nan, np.float32)
            f_sig = np.full(M, np.nan, np.float32)

        elig = ok & np.isfinite(f_sig) & np.isfinite(f_cyc)
        F["c_e"][si] = c_e
        F["c_x"][si] = c_x
        F["slip_e"][si] = slip_e
        F["slip_f"][si] = slip_f
        F["f_sig"][si] = np.where(elig, f_sig, np.nan)
        F["f_cyc"][si] = np.where(elig, f_cyc, np.nan)
        F["ret24"][si] = ret24
        F["dd"][si] = np.where(elig, dd, np.nan)
        F["up"][si] = np.where(elig, up, np.nan)
        FL["valid"][si] = elig.astype(np.int8)
        FL["delist"][si] = (delist & elig).astype(np.int8)

        # ---- neo MOM15 (M-LEVEL k=1 rows cua symbol nay, HOLD 24h) ----
        i0m, i1m = bounds_m[si], bounds_m[si + 1]
        if i1m > i0m and ft is not None:
            rows = slot_m[i0m:i1m]
            m_e = ml_min[rows]
            ep = np.searchsorted(ts, m_e)
            epc = np.clip(ep, 0, n - 1)
            okm = (ep < n) & (ts[epc] == m_e)
            m_e2, ep = m_e[okm], ep[okm]
            if len(m_e2):
                m_x = m_e2 + ANCHOR_HOLD
                cens = m_x > (NMIN - 1)
                ep_end = np.clip(np.searchsorted(ts, m_x, side="right") - 1, 0, n - 1)
                entry = c[ep].astype(np.float64)
                rawm = np.where(~cens & (entry > 0), c[ep_end].astype(np.float64) / np.maximum(entry, 1e-12) - 1.0, np.nan)
                slipm = np.where(entry > 0, 0.5 * (h[ep].astype(np.float64) - l[ep].astype(np.float64)) / np.maximum(entry, 1e-12), np.nan)
                lo = np.searchsorted(ft, (BASE + m_e2) * 60000, side="right")
                hi = np.searchsorted(ft, (BASE + m_x) * 60000, side="right")
                fundm = (cum[hi] - cum[lo])
                good = np.isfinite(rawm) & np.isfinite(slipm)
                if good.any():
                    A["raw"].append(rawm[good].astype(np.float32))
                    A["slip"].append(slipm[good].astype(np.float32))
                    A["fund"].append(fundm[good].astype(np.float32))
                    A["ok"].append((m_e2[good] >= DEV_LO - BASE).astype(np.int8))
                    A["blk"].append(((BASE + m_e2[good]) // BLOCK_MIN).astype(np.int64))

        if (si + 1) % 100 == 0:
            say("   ... %d/%d symbol | %d co funding | %.0fs" % (si + 1, S, nfund, time.time() - t0))
    cli.close()

    np.savez(OUT + "/grid.npz", syms=np.array(files, dtype=object), marks=marks,
             mom_active=mom_active, in_t170=in_t170, t170_start=t170_start, **F, **FL)
    a_ok = np.concatenate(A["ok"]).astype(bool) if A["ok"] else np.zeros(0, dtype=bool)
    if len(a_ok):
        np.savez(OUT + "/anchor.npz", m_raw=np.concatenate(A["raw"]), m_slip=np.concatenate(A["slip"]),
                 m_fund=np.concatenate(A["fund"]), m_dev=a_ok, m_blk=np.concatenate(A["blk"]),
                 ref_total_rows=np.array(ref_total_rows), ref_fire8=np.array(len(fire8)),
                 ref_ml_rows=np.array(len(ml_min)), fire8_n=np.array(len(ff)))
    nel = FL["valid"].sum(axis=0)
    say("[A1] grid xong: %d x %d = %s o | %d symbol co funding | %d symbol co lenh T170 | el %.0fs"
        % (S, M, nb(S * M), nfund, n_t170_sym, time.time() - t0))
    say("[A2] n_elig/moc: min %d med %d max %d | moc n_elig>=%d: %d/%d | moc MOM15-active: %d (%.1f%%)"
        % (nel.min(), int(np.median(nel)), nel.max(), MIN_SYM, int((nel >= MIN_SYM).sum()), M,
           int(mom_active.sum()), 100 * mom_active.mean()))
    say("[A3] anchor MOM15 rows: %d (DEV %d)" % (len(a_ok), int(a_ok.sum())))
    return None


# =====================================================================================
# STAGE B — portfolio + thong ke
# =====================================================================================
def block_ids(mark):
    return ((BASE + mark) // BLOCK_MIN).astype(np.int64)


def summ(net, blk, seed=SEED):
    _, inv = np.unique(blk, return_inverse=True)
    nbk = inv.max() + 1
    sums = np.bincount(inv, weights=net, minlength=nbk)
    cnts = np.bincount(inv, minlength=nbk)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, nbk, size=(NREP, nbk))
    m = sums[idx].sum(axis=1) / cnts[idx].sum(axis=1)
    obs = float(net.mean())
    lo, hi = np.percentile(m, [2.5, 97.5])
    half = (hi - lo) / 2.0 * CI_INFLATE
    return dict(n=len(net), nblk=int(nbk), obs=obs, half=float(half), ci_lo=obs - half,
                ci_hi=obs + half, p_gt0=float((m > 0).mean()))


def mde_of(net, blk, seed=SEED):
    net = net - net.mean()
    _, inv = np.unique(blk, return_inverse=True)
    nbk = inv.max() + 1
    sums = np.bincount(inv, weights=net, minlength=nbk)
    cnts = np.bincount(inv, minlength=nbk)
    rng = np.random.default_rng(seed)
    hs = np.empty(MDE_OUTER)
    for r in range(MDE_OUTER):
        idx = rng.integers(0, nbk, nbk)
        IDX = idx[rng.integers(0, nbk, size=(MDE_INNER, nbk))]
        m = sums[IDX].sum(axis=1) / cnts[IDX].sum(axis=1)
        lo, hi = np.percentile(m, [2.5, 97.5])
        hs[r] = (hi - lo) / 2.0 * CI_INFLATE
    power = {X: float((hs < X).mean()) for X in MDE_GRID}
    mde80 = next((X for X in MDE_GRID if power[X] >= 0.80), None)
    return dict(p50=float(np.percentile(hs, 50)), mde80=mde80, power=power)


def stats():
    z = np.load(OUT + "/grid.npz", allow_pickle=True)
    syms = list(z["syms"])
    marks = z["marks"].astype(np.int64)
    S, M = len(syms), len(marks)
    c_e, c_x = z["c_e"], z["c_x"]
    slip_e, slip_f = z["slip_e"], z["slip_f"]
    f_sig, f_cyc, ret24 = z["f_sig"], z["f_cyc"], z["ret24"]
    dd, up = z["dd"], z["up"]
    valid, delist = z["valid"].astype(bool), z["delist"].astype(bool)
    mom_active = z["mom_active"].astype(bool)
    in_t170 = z["in_t170"]

    blk = block_ids(marks)
    devm = (BASE + marks >= DEV_LO)
    year = pd.to_datetime((BASE + marks) * 60000, unit="ms", utc=True).year.values
    ret = np.where(valid, (c_x / c_e - 1.0), np.nan) * 100.0        # %/notional (LONG)

    n_elig = valid.sum(axis=0)
    use = n_elig >= MIN_SYM
    zz = np.load(OUT + "/anchor.npz")
    ref_total_rows = int(zz["ref_total_rows"])
    ref_fire8 = int(zz["ref_fire8"])
    ref_ml_rows = int(zz["ref_ml_rows"])

    say()
    say("=" * 100)
    say("STAGE B — LONG top-decile funding CAO | moc dung duoc: %d/%d | pre-reg da76e41"
        % (int(use.sum()), M))
    say("=" * 100)

    # ---------------- 0. NEO MOM15 ----------------
    m_raw = zz["m_raw"].astype(np.float64)
    m_slip = zz["m_slip"].astype(np.float64)
    m_fund = zz["m_fund"].astype(np.float64)
    m_dev = zz["m_dev"].astype(bool)
    net_m = m_raw - m_slip - m_fund                       # long TRA funding
    ok_m = np.isfinite(net_m)
    say()
    say("-- B0: NEO MOM15 (harness con luc? PHAI khop, neu khong => VOID) --")
    say("%-46s %14s %14s %s" % ("kiem chung", "vong nay", "tham chieu", "khop"))
    chk = [("total_rows (cache2)", ref_total_rows, 619073711),
           ("phut MOM15 fire (fire8)", ref_fire8, 13150),
           ("M-LEVEL MOM15 k=1 rows (ALL)", ref_ml_rows, 11367),
           ("M-LEVEL MOM15 k=1 rows (DEV)", int((m_dev & ok_m).sum()), 7128)]
    anch_ok = True
    for nm, g, w in chk:
        good = (g == w)
        anch_ok &= good
        say("%-46s %14s %14s %s" % (nm, nb(g), nb(w), "OK" if good else "**LECH**"))
    # net MOM15 @0,10% (fee round-trip tru 1 lan, quy uoc vong truoc)
    v_dev = m_dev & ok_m
    net_anchor_dev = float(net_m[v_dev].mean()) - FEE_ANCHOR
    net_anchor_all = float(net_m[ok_m].mean()) - FEE_ANCHOR
    m_blk = zz["m_blk"].astype(np.int64)
    s_anch = summ(net_m[v_dev], m_blk[v_dev])
    say("%-46s %13.4f%% %13.4f%% %s" % ("MOM15 DEV 24h net @0,10%", 100 * net_anchor_dev, 1.6690,
                                        "OK" if abs(net_anchor_dev - 0.016690) < 0.0005 else "**LECH**"))
    say("%-46s %13.4f%% %13.4f%% %s" % ("MOM15 ALL 24h net @0,10%", 100 * net_anchor_all, 2.2622,
                                        "OK" if abs(net_anchor_all - 0.022622) < 0.0005 else "**LECH**"))
    say("%-46s %13d %13d %s" % ("N_blk MOM15 DEV", int(s_anch["nblk"]), 301,
                                 "OK" if int(s_anch["nblk"]) == 301 else "**LECH**"))
    say("%-46s %12.4f%% [%9.4f%% %9.4f%%] %s" % ("MOM15 DEV CI72h x1.21 (NUONG 0,10% da tru)",
                                                  100 * net_anchor_dev, 100 * s_anch["ci_lo"], 100 * s_anch["ci_hi"], ""))
    anch_ok &= abs(net_anchor_dev - 0.016690) < 0.0005
    say("=> Neo MOM15: **%s** (N_dev=%d)" % ("TAI TAO DUNG (bo do con luc)" if anch_ok else "SAI KHOP => VOID",
                                             int(v_dev.sum())))
    say("HinV: moc MOM15-active (co fire trong 24h truoc): %d/%d moc dung duoc (%.1f%%)"
        % (int((mom_active & use).sum()), int(use.sum()), 100 * mom_active[use].mean()))

    # ---------------- build W ----------------
    def build_W(mode):
        W = np.zeros((M, S), dtype=np.float32)
        for t in range(M):
            if not use[t]:
                continue
            el = np.flatnonzero(valid[:, t])
            n = len(el)
            K = max(1, int(round(n / 10.0)))
            fs = f_sig[el, t]
            order = np.argsort(-fs, kind="stable")          # funding CAO nhat truoc
            top = el[order[:K]]
            if mode == "V1":
                W[t, top] = +1.0 / K
            elif mode == "V2":
                p90 = np.percentile(fs, 90.0)
                cand = el[(fs > p90) & (ret24[el, t] > 0)]
                if len(cand):
                    W[t, cand] = +1.0 / len(cand)
            elif mode == "V3":
                el3 = np.array([e for e in el if in_t170[e, t]], dtype=np.int64)
                if len(el3) >= 3:
                    K3 = max(1, int(round(len(el3) / 10.0)))
                    o3 = np.argsort(-f_sig[el3, t], kind="stable")
                    W[t, el3[o3[:K3]]] = +1.0 / K3
            elif mode == "U":                                # doi chung: long universe EW
                W[t, el] = +1.0 / n
            elif mode == "L2":                               # doi chung: long bottom-decile (funding thap nhat)
                W[t, el[order[-K:]]] = +1.0 / K
            elif mode == "S1":                               # doi chung: short top-decile (tai lap SHORT_CARRY V1)
                W[t, top] = -1.0 / K
            elif mode == "NULL":
                rng = np.random.default_rng(SEED + t)
                W[t, rng.choice(el, size=K, replace=False)] = +1.0 / K
        return W

    def eval_W(W, fee, slip_mode="emp", long_side=True):
        Wa = np.abs(W)
        Wp = np.vstack([np.zeros((1, S), dtype=np.float32), W])
        dW = np.abs(W - Wp[:-1])
        if slip_mode == "emp":
            sl = np.where(np.isfinite(slip_e), slip_e, 0.0).astype(np.float64)
        elif slip_mode == "flat14":
            sl = np.full((S, M), SLIP_FLAT_HI)
        elif slip_mode == "flat1bp":
            sl = np.full((S, M), SLIP_FLAT_LO)
        elif slip_mode == "exit":
            sl = np.where(np.isfinite(slip_f), slip_f, 0.0).astype(np.float64)
        csl = (fee + sl).T
        cost = (dW * csl).sum(axis=1) * 100.0
        tau = dW.sum(axis=1)
        rr = np.where(np.isfinite(ret), ret, 0.0).T                     # (M,S)
        lm = (W > 0)
        px = (lm * Wa * rr).sum(axis=1) - ((W < 0) * Wa * rr).sum(axis=1)
        fcy = np.where(np.isfinite(f_cyc), f_cyc, 0.0).T
        sgn = np.where(W > 0, -1.0, np.where(W < 0, +1.0, 0.0))          # long TRA, short THU
        fund = (Wa * sgn * fcy).sum(axis=1)
        net = px + fund - cost
        return dict(net=net, gross=px + fund, px=px, fund=fund, cost=cost, tau=tau, W=W)

    VAR = [("V1", "V1 pure: LONG top-decile funding CAO"),
           ("V2", "V2 loc momentum: f_sig>p90 & ret24>0"),
           ("V3", "V3 trong universe he thong (T170 proxy)"),
           ("U", "U doi chung: long universe EW"),
           ("L2", "L2 doi chung: long bottom-decile (funding thap nhat)"),
           ("S1", "S1 doi chung: short top-decile (tai lap SHORT_CARRY)")]

    RES = {}
    WS = {}
    say()
    say("-- B1: ket qua (chi phi CHINH = taker 0,05%/chan + slip proxy 0,5xrange/chan; funding TRA that) --")
    say("%-4s %8s %10s %24s %8s %9s %9s %9s %9s %8s %8s %8s" %
        ("var", "N_cyc", "net/cyc", "CI72h x1.21", "%cyc>0", "gross", "gia", "funding", "cost",
         "turnover", "cost/gross", "p(null)"))
    for key, desc in VAR:
        W = build_W(key)
        WS[key] = W
        e = eval_W(W, FEE_TAKER, "emp")
        mkk = use & (e["tau"] > 0) if key in ("V2", "V3") else use
        netv, blkv = e["net"][mkk], blk[mkk]
        st = summ(netv, blkv)
        pnull = np.nan
        if key in ("V1", "V2", "V3"):
            vT = valid.T
            vals = np.where(np.isfinite(ret), ret, 0.0).T - np.where(np.isfinite(f_cyc), f_cyc, 0.0).T
            slT = np.where(np.isfinite(slip_e), slip_e, 0.0).T
            Ks = np.array([max(1, int(round(int(vT[t].sum()) / 10.0))) for t in range(M)])
            rng = np.random.default_rng(SEED)
            nl = np.empty(NULL_REPS)
            mt = np.flatnonzero(mkk)
            for r in range(NULL_REPS):
                R = rng.random((M, S))
                R[~vT] = 2.0
                order = np.argsort(R, axis=1, kind="stable")
                vv = np.take_along_axis(np.where(vT, vals, 0.0), order, axis=1)
                ss = np.take_along_axis(slT, order, axis=1)
                kk = np.maximum(Ks[mt], 1)
                cv = np.cumsum(vv[mt], axis=1)[np.arange(len(mt)), kk - 1] / kk
                cs = np.cumsum(ss[mt], axis=1)[np.arange(len(mt)), kk - 1] / kk
                nl[r] = float(np.mean(cv - (FEE_TAKER + cs) * 100.0))
            pnull = float((nl >= netv.mean()).mean())
            RES[key + "_nullq"] = dict(mean=float(nl.mean()), p05=float(np.percentile(nl, 5)),
                                       p95=float(np.percentile(nl, 95)))
        md = mde_of(netv, blkv)
        RES[key] = dict(desc=desc, n=int(len(netv)), obs=st["obs"], ci_lo=st["ci_lo"], ci_hi=st["ci_hi"],
                        p_gt0=st["p_gt0"], nblk=st["nblk"], pos_pct=float(100 * (netv > 0).mean()),
                        gross=float(e["gross"][mkk].mean()), px=float(e["px"][mkk].mean()),
                        fund=float(e["fund"][mkk].mean()), cost=float(e["cost"][mkk].mean()),
                        tau=float(e["tau"][mkk].mean()) / 2.0, mde80=md["mde80"], pnull=pnull,
                        fund_pos_pct=float(100 * (f_cyc[:, mkk] > 0).sum() / max(1, valid[:, mkk].sum())))
        r = RES[key]
        say("%-4s %8d %9.4f%%  [%9.4f%% %9.4f%%] %7.1f%% %8.4f%% %8.4f%% %8.4f%% %8.4f%% %7.2f%% %7.0f%% %8.3f" %
            (key, r["n"], r["obs"], r["ci_lo"], r["ci_hi"], r["pos_pct"], r["gross"], r["px"],
             r["fund"], -r["cost"], 100 * r["tau"], 100 * r["cost"] / max(1e-12, abs(r["gross"])), r["pnull"]))
        say("     MDE80=%s | null: mean %+.4f%% p05 %+.4f%% p95 %+.4f%%" %
            (("nan" if md["mde80"] is None else "%.2f%%" % md["mde80"]),
             *[RES.get(key + "_nullq", {}).get(k, np.nan) for k in ("mean", "p05", "p95")]))

    # ---------------- B1b: DEV ----------------
    say()
    say("-- B1b: DEV 2022-2025 (CHINH) --")
    say("%-4s %8s %10s %24s %8s %9s %9s %9s %9s" % ("var", "N_cyc", "net/cyc", "CI72h x1.21",
                                                     "%cyc>0", "gross", "gia", "funding", "cost"))
    for key, _ in VAR:
        e = eval_W(WS[key], FEE_TAKER, "emp")
        mkk = (use & (e["tau"] > 0)) if key in ("V2", "V3") else use
        m2 = mkk & devm
        netv, blkv = e["net"][m2], blk[m2]
        st = summ(netv, blkv)
        say("%-4s %8d %9.4f%%  [%9.4f%% %9.4f%%] %7.1f%% %8.4f%% %8.4f%% %8.4f%% %8.4f%%" %
            (key, len(netv), st["obs"], st["ci_lo"], st["ci_hi"], 100 * (netv > 0).mean(),
             e["gross"][m2].mean(), e["px"][m2].mean(), e["fund"][m2].mean(), -e["cost"][m2].mean()))
        RES[key + "_dev"] = dict(n=int(len(netv)), obs=float(st["obs"]), ci_lo=float(st["ci_lo"]),
                                 ci_hi=float(st["ci_hi"]), pos_pct=float(100 * (netv > 0).mean()),
                                 px=float(e["px"][m2].mean()), fund=float(e["fund"][m2].mean()),
                                 cost=float(e["cost"][m2].mean()),
                                 tau=float(e["tau"][m2].mean()) / 2.0)

    # ---------------- B2: chi phi ----------------
    say()
    say("-- B2: do ben theo CHI PHI (V1) --")
    say("%-34s %10s %24s %9s" % ("cost variant", "net/cyc DEV", "CI72h x1.21", "%cyc>0"))
    W1 = WS["V1"]
    for lbl, fee, sm in [("taker .05 + slip proxy (CHINH)", FEE_TAKER, "emp"),
                         ("maker .02 + slip proxy", FEE_MAKER, "emp"),
                         ("taker .05 + slip phang 0,140%/chan", FEE_TAKER, "flat14"),
                         ("taker .05 + slip 1bp/chan", FEE_TAKER, "flat1bp"),
                         ("taker .05 + slip nen-ra", FEE_TAKER, "exit")]:
        e = eval_W(W1, fee, sm)
        netv = e["net"][use & devm]
        st = summ(netv, blk[use & devm])
        RES["V1cost_" + lbl] = dict(obs=st["obs"], ci_lo=st["ci_lo"], ci_hi=st["ci_hi"])
        say("%-34s %9.4f%% [%9.4f%% %9.4f%%] %7.1f%%" % (lbl, st["obs"], st["ci_lo"], st["ci_hi"],
                                                          100 * (netv > 0).mean()))
    e = eval_W(W1, FEE_TAKER, "emp")
    sl_book = np.where(np.isfinite(slip_e), slip_e, 0.0)
    nz = np.abs(W1) > 0
    avg_slip = np.where(nz, sl_book.T, np.nan)
    with np.errstate(invalid="ignore"):
        avg_slip = np.nanmean(avg_slip, axis=1)
    cost_rt = 2.0 * (FEE_TAKER + np.where(np.isfinite(avg_slip), avg_slip, 0.0)) * 100.0
    net_rt = e["gross"] - cost_rt
    m2 = use & devm
    st = summ(net_rt[m2], blk[m2])
    say("%-34s %9.4f%% [%9.4f%% %9.4f%%] %7.1f%%" %
        ("taker .05 + round-trip/cyc (can tren)", st["obs"], st["ci_lo"], st["ci_hi"],
         100 * (net_rt[m2] > 0).mean()))
    RES["V1cost_roundtrip"] = dict(obs=st["obs"], ci_lo=st["ci_lo"], ci_hi=st["ci_hi"])

    # ---------------- B3: theo nam ----------------
    say()
    say("-- B3: net/chu ky theo NAM (chi phi chinh) --")
    say("%-4s %s" % ("var", " ".join("%10d" % y for y in range(2021, 2026))))
    for key, _ in VAR:
        e = eval_W(WS[key], FEE_TAKER, "emp")
        mkk = (use & (e["tau"] > 0)) if key in ("V2", "V3") else use
        row = []
        for y in range(2021, 2026):
            m = mkk & (year == y)
            row.append("%9.4f%%" % e["net"][m].mean() if m.sum() else "       n/a")
        say("%-4s %s" % (key, " ".join(row)))
        RES[key + "_byyear"] = {int(y): (float(e["net"][mkk & (year == y)].mean())
                                         if (mkk & (year == y)).sum() else None) for y in range(2021, 2026)}

    # ---------------- B4: MAE long ----------------
    say()
    say("-- B4: RUI RO LONG — MAE = drawdown (duoi) trong (r, r+480] + MFE (max high) --")
    say("%-4s %7s %9s %9s %9s %9s %9s %9s %9s   %s" %
        ("var", "n_pos", "DD p50", "p10", "p05", "p01", "min", "MFE p50", "MFE p90", "%DD>20%"))
    for key in ("V1", "V2", "V3", "U"):
        W = WS[key]
        lg = (W > 0) & valid.T
        dv = dd.T[lg]
        uv = up.T[lg]
        dv = dv[np.isfinite(dv)]
        uv = uv[np.isfinite(uv)]
        big = float(100 * (dv < -DD_BIG).mean())
        q = [100 * np.percentile(dv, p) for p in (50, 10, 5, 1)]
        say("%-4s %7d %8.2f%% %8.2f%% %8.2f%% %8.2f%% %8.2f%% %8.2f%% %8.2f%%   %.2f%%" %
            (key, len(dv), q[0], q[1], q[2], q[3], 100 * dv.min(),
             *[100 * np.percentile(uv, p) for p in (50, 90)], big))
        RES[key + "_mae"] = dict(n=int(len(dv)), p50=float(q[0]), p10=float(q[1]), p05=float(q[2]),
                                 p01=float(q[3]), min=float(dv.min()),
                                 mfe_p50=float(np.percentile(uv, 50)),
                                 mfe_p90=float(np.percentile(uv, 90)), dd20_pct=big)
    W1 = WS["V1"]
    lg = (W1 > 0) & valid.T
    ws = np.argwhere(lg)
    vals = dd.T[lg]
    fin = np.isfinite(vals)
    ws, vals = ws[fin], vals[fin]
    od = np.argsort(vals)[:8]
    say("   worst 8 drawdown (V1):")
    for i in od:
        t, s = ws[i]
        say("     %-12s %s  drawdown %+8.2f%%  (f_sig %+7.4f %% ; f_cyc %+7.4f %%)" %
            (syms[s], utc_min(marks[t]), 100 * vals[i], f_sig[s, t], f_cyc[s, t]))
    RES["V1_worst"] = [dict(sym=syms[ws[i][1]], mark=utc_min(marks[ws[i][0]]),
                            drawdown=float(100 * vals[i])) for i in od]

    # ---------------- B5: phan ra V1 ----------------
    say()
    say("-- B5: phan ra gross vs net (V1, DEV) --")
    e = eval_W(W1, FEE_TAKER, "emp")
    m2 = use & devm
    say("   chan GIA (long): %+.4f%%/chu ky | FUNDING TRA: %+.4f%%/chu ky | gross: %+.4f%% | cost: -%.4f%% | net: %+.4f%%" %
        (e["px"][m2].mean(), e["fund"][m2].mean(), e["gross"][m2].mean(), e["cost"][m2].mean(),
         e["net"][m2].mean()))
    say("   turnover 1 ve: %.2f%%/chu ky | cost drag: %.4f%%/chu ky | cost/gross: %.0f%% | %%chu ky f_cyc>0: %.1f%%" %
        (100 * e["tau"][m2].mean() / 2, e["cost"][m2].mean(),
         100 * e["cost"][m2].mean() / max(1e-12, abs(e["gross"][m2].mean())),
         100 * (f_cyc[:, m2] > 0).sum() / max(1, valid[:, m2].sum())))
    RES["V1_decomp"] = dict(px=float(e["px"][m2].mean()), fund=float(e["fund"][m2].mean()),
                            gross=float(e["gross"][m2].mean()), cost=float(e["cost"][m2].mean()),
                            net=float(e["net"][m2].mean()), tau_1s=float(100 * e["tau"][m2].mean() / 2))
    say("   ALL net %+.4f%% | DEV net %+.4f%% | median net (DEV) %+.4f%%" %
        (e["net"][use].mean(), e["net"][m2].mean(), np.median(e["net"][m2])))

    # ---------------- B6: basket dac trung ----------------
    say()
    say("-- B6: dac trung basket V1 (DEV) --")
    sel = np.zeros((M, S), dtype=bool)
    for t in np.flatnonzero(use):
        el = np.flatnonzero(valid[:, t])
        K = max(1, int(round(len(el) / 10.0)))
        o = np.argsort(-f_sig[el, t], kind="stable")
        sel[t, el[o[:K]]] = True
    sel_t = sel & valid.T
    fs = f_sig.T[sel_t]
    fs = fs[np.isfinite(fs)]
    fy = f_cyc.T[sel_t]
    fy = fy[np.isfinite(fy)]
    fu = f_cyc[valid]
    fu = fu[np.isfinite(fu)]
    say("   f_sig top-decile: mean %+.4f bp | med %+.4f bp | %%>0 %.1f%%" %
        (1e4 * fs.mean(), 1e4 * np.median(fs), 100 * (fs > 0).mean()))
    say("   f_cyc top-decile: mean %+.4f %% | med %+.4f %% | %%>0 %.1f%%  (-> long TRA tung nay)" %
        (fy.mean(), np.median(fy), 100 * (fy > 0).mean()))
    say("   f_cyc universe  : mean %+.4f %% | %%>0 %.1f%%" % (fu.mean(), 100 * (fu > 0).mean()))
    RES["basket"] = dict(fsig_bp=float(1e4 * fs.mean()), fcyc_top=float(fy.mean()),
                         fcyc_top_pospct=float(100 * (fy > 0).mean()), fcyc_uni=float(fu.mean()),
                         fcyc_uni_pospct=float(100 * (fu > 0).mean()))

    # ---------------- B7: doi chieu MOM15 (overlap + redundancy) ----------------
    say()
    say("-- B7: DOI CHIEU MOM15 (trung lap?) --")
    say("%-4s %10s %10s %24s %10s" % ("var", "net ACTIVE", "net QUIET", "CI quiet", "n_q/n_a"))
    for key in ("V1", "V2", "V3"):
        e = eval_W(WS[key], FEE_TAKER, "emp")
        mkk = (use & (e["tau"] > 0)) if key in ("V2", "V3") else use
        ia = mkk & mom_active
        iq = mkk & (~mom_active)
        netv = e["net"][iq]
        stq = summ(netv, blk[iq]) if iq.sum() > 2 else dict(obs=np.nan, ci_lo=np.nan, ci_hi=np.nan)
        say("%-4s %9.4f%% %9.4f%% [%9.4f%% %9.4f%%] %5d/%5d" %
            (key, e["net"][ia].mean() if ia.sum() else np.nan,
             e["net"][iq].mean() if iq.sum() else np.nan, stq["ci_lo"], stq["ci_hi"],
             int(iq.sum()), int(ia.sum())))
        RES[key + "_mom15split"] = dict(net_active=float(e["net"][ia].mean()) if ia.sum() else None,
                                        net_quiet=float(e["net"][iq].mean()) if iq.sum() else None,
                                        n_active=int(ia.sum()), n_quiet=int(iq.sum()))
    RES["mom15_anchor"] = dict(net_dev=float(net_anchor_dev), net_all=float(net_anchor_all),
                               n_dev=int(v_dev.sum()), anchor_ok=bool(anch_ok),
                               mom_active_pct=float(100 * mom_active[use].mean()))

    with open(OUT + "/summary.json", "w") as f:
        json.dump({k: v for k, v in RES.items()}, f, indent=1, default=str)
    say()
    say("[done] summary -> %s/summary.json" % OUT)


if __name__ == "__main__":
    import sys
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    say("\n### RUN %s | %s | NMIN=%d" % (st, dt.datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"), NMIN))
    if st in ("build", "all"):
        if not (st == "all" and os.path.exists(OUT + "/grid.npz")):
            build()
    if st in ("stats", "all"):
        stats()
