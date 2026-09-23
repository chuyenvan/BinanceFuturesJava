#!/usr/bin/env python3
"""SHORT_CARRY — luong MOI: SHORT-side funding harvest (carry), do offline (0-sim).

Pre-reg: docs/PREREG_SHORT_CARRY.md (commit edd1e70, chot TRUOC khi chay; KHONG sua thiet ke).

Thuan Python. Chi DOC: Aerospike test.funding_data + raw/<sym>.f32 (kline_1m_opt, 627 sym, 1m OHLCV).
KHONG Java tren Oracle, KHONG claude-run, KHONG push, KHONG cham 2026 (gia het 2025-12-31 16:59 UTC).

Quy uoc dau (KHOA, = Binance that, kiem chung o docs/RESULT_FUNDING_SIGN.md):
  rate > 0  =>  LONG TRA, SHORT THU.   f_cyc = 100*sum(rate) tren (t_e, t_x]  (%/notional).

Bien the: V1 pure carry (short top-decile f_sig) | V2 carry + filter (f_sig>p90 & ret24<=0)
          V3 dollar-neutral (long bottom-decile + short top-decile)
Doi chung: U short universe EW | L1 long bottom-decile (tai lap huong long-side da thua).

Out (ngoai repo): /home/ubuntu/claudedata/short_carry/{grid.npz,report.txt,summary.json}
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

OUT = os.environ.get("SC_OUT", "/home/ubuntu/claudedata/short_carry")
RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
AERO = ("127.0.0.1", 3222)
NS, SET = "test", "funding_data"

SEED = 20260905
NREP = 2000
NULL_REPS = 300
MDE_OUTER, MDE_INNER = 2000, 200
BLOCK_MIN = 72 * 60
CI_INFLATE = 1.21
MDE_GRID = [0.01, 0.02, 0.05, 0.10, 0.20, 0.50]   # %/chu ky (net tinh bang %)
MIN_SYM = 50
HOLD = 480                     # 8h
LEVEL = 480
SQUEEZE = 0.20                 # +20% drawup

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
log = logging.getLogger("shortcarry")
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())
log.addHandler(logging.FileHandler(OUT + "/report.txt", mode="a"))
REP = []


def say(s=""):
    REP.append(str(s))
    log.info(s)


def utc_ms(ms):
    return pd.Timestamp(int(ms), unit="ms", tz="UTC").strftime("%Y-%m-%d %H:%M")


def utc_min(m):
    return pd.Timestamp((BASE + int(m)) * 60000, unit="ms", tz="UTC").strftime("%Y-%m-%d %H:%M")


def pct(x, nd=4):
    return ("%.*f%%" % (nd, 100 * x)) if np.isfinite(x) else "nan"


def nb(x):
    return f"{int(x):,}".replace(",", " ")


# =====================================================================================
# STAGE A — grid: (mark, symbol) -> gia + funding + MAE
# =====================================================================================
def build():
    files = sorted(f for f in os.listdir(RAW) if f.endswith(".f32"))
    _mx = int(os.environ.get("SC_MAXSYM", "0"))
    if _mx:
        files = files[:_mx]
    say("=" * 100)
    say("SHORT_CARRY — build grid | %d symbol | pre-reg edd1e70" % len(files))
    say("=" * 100)
    marks = np.arange(0, NMIN - HOLD, LEVEL, dtype=np.int64)          # r+480 <= NMIN-1
    M = len(marks)
    S = len(files)
    say("[A0] NMIN=%d marks=%d (r+480<=NMIN-1) | BASE=%d | %s .. %s"
        % (NMIN, M, BASE, utc_min(marks[0]), utc_min(marks[-1])))

    t0 = time.time()
    cli = aerospike.client({"hosts": [AERO], "policies": {"timeout": 60000}}).connect()

    F = {k: np.full((S, M), np.nan, dtype=np.float32) for k in
         ("c_e", "c_x", "slip_e", "slip_f", "f_sig", "f_cyc", "ret24", "mae", "mfe")}
    FL = {k: np.zeros((S, M), dtype=np.int8) for k in ("valid", "delist")}

    nfund = 0
    nerr = 0
    for si, fn in enumerate(files):
        sym = fn[:-4]
        try:
            a = np.fromfile(os.path.join(RAW, fn), dtype=DT)
        except Exception:
            nerr += 1
            continue
        if len(a) < 30:
            continue
        ts = a["ts"].astype(np.int64) - BASE          # file luu epoch-phut TUYET DOI; chuyen ve tuong doi
        o = np.argsort(ts, kind="stable")
        ts = ts[o]
        h = a["h"][o].astype(np.float32)
        l = a["l"][o].astype(np.float32)
        c = a["c"][o].astype(np.float32)
        keep = (ts >= 0) & (ts < NMIN)
        ts, h, l, c = ts[keep], h[keep], l[keep], c[keep]
        n = len(ts)
        if n < 480:
            continue

        # ---- entry/exit index ----
        i1 = np.searchsorted(ts, marks)
        i1c = np.clip(i1, 0, n - 1)
        e_ok = (i1 < n) & (ts[i1c] == marks)
        i2 = np.searchsorted(ts, marks + HOLD)
        i2c = np.clip(i2, 0, n - 1)
        x_ok = (i2 < n) & (ts[i2c] == marks + HOLD)
        last_ts = ts[-1]
        delist = (~x_ok) & e_ok & (last_ts > marks)
        idx_x = np.where(x_ok, i2c, n - 1)
        ok = e_ok & (x_ok | delist)

        c_e = c[i1c].astype(np.float32)
        c_x = np.where(ok, c[idx_x].astype(np.float32), np.nan)
        h_e = h[i1c].astype(np.float32)
        l_e = l[i1c].astype(np.float32)
        slip_e = np.where(ok & (c_e > 0), 0.5 * (h_e - l_e) / c_e, np.nan)
        slip_f = np.where(ok, 0.5 * (h[idx_x] - l[idx_x]) / np.maximum(c[idx_x], 1e-12), np.nan).astype(np.float32)
        ok &= (c_e > 0)
        c_x = np.where(ok, c_x, np.nan)

        # ---- ret24 ----
        i0 = np.searchsorted(ts, marks - 1440)
        i0c = np.clip(i0, 0, n - 1)
        ok24 = (i0 < n) & (ts[i0c] == marks - 1440) & ok
        ret24 = np.where(ok24, c[i0c] / np.maximum(c_e, 1e-12) - 1.0, np.nan).astype(np.float32)

        # ---- MAE/MFE: max high / min low trong (mark, mark+480] ----
        hf = np.full(NMIN, np.nan, dtype=np.float32)
        lf = np.full(NMIN, np.nan, dtype=np.float32)
        hf[ts] = h
        lf[ts] = l
        rmax = pd.Series(hf).rolling(HOLD, min_periods=1).max().shift(-HOLD).to_numpy(dtype=np.float32)
        rmin = pd.Series(lf).rolling(HOLD, min_periods=1).min().shift(-HOLD).to_numpy(dtype=np.float32)
        mae = np.where(ok, rmax[marks] / np.maximum(c_e, 1e-12) - 1.0, np.nan).astype(np.float32)   # drawup (adverse cho short)
        mfe = np.where(ok, rmin[marks] / np.maximum(c_e, 1e-12) - 1.0, np.nan).astype(np.float32)   # drawdown (favor cho short)
        del hf, lf, rmax, rmin

        # ---- funding ----
        rec = cli.get((NS, SET, sym))
        bd = rec[2] if isinstance(rec, tuple) else None
        if bd and "f_data" in bd:
            d = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(bd["f_data"]))))
            if d:
                ks = np.fromiter((int(k) for k in d), dtype=np.int64, count=len(d))
                vs = np.fromiter((float(d[str(k)]) for k in ks), dtype=np.float64, count=len(ks))
                od = np.argsort(ks, kind="stable")
                ft = ks[od]
                fr = vs[od]
                cum = np.concatenate(([0.0], np.cumsum(fr)))
                t_e = (BASE + marks) * 60000
                t_x = np.where(x_ok, (BASE + marks + HOLD) * 60000, (BASE + int(last_ts)) * 60000)
                lo = np.searchsorted(ft, t_e, side="right")
                hi = np.searchsorted(ft, t_x, side="right")
                f_cyc = (100.0 * (cum[hi] - cum[lo])).astype(np.float32)
                j = np.searchsorted(ft, t_e, side="right") - 1
                f_sig = np.where(j >= 0, fr[np.clip(j, 0, len(fr) - 1)], np.nan).astype(np.float32)
                nfund += 1
            else:
                f_cyc = np.full(M, np.nan, np.float32)
                f_sig = np.full(M, np.nan, np.float32)
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
        F["mae"][si] = np.where(elig, mae, np.nan)
        F["mfe"][si] = np.where(elig, mfe, np.nan)
        FL["valid"][si] = elig.astype(np.int8)
        FL["delist"][si] = (delist & elig).astype(np.int8)

        if (si + 1) % 63 == 0:
            say("   ... %d/%d symbol | %d co funding | %.0fs" % (si + 1, S, nfund, time.time() - t0))
    cli.close()

    np.savez(OUT + "/grid.npz", syms=np.array(files, dtype=object), marks=marks, **F, **FL)
    say("[A1] grid xong: %d symbol x %d moc = %s o | %d symbol co funding | el %.0fs"
        % (S, M, nb(S * M), nfund, time.time() - t0))
    nel = FL["valid"].sum(axis=0)
    say("[A2] n_elig/moc: min %d med %d max %d | moc n_elig>=%d: %d/%d"
        % (nel.min(), int(np.median(nel)), nel.max(), MIN_SYM, int((nel >= MIN_SYM).sum()), M))
    return None


# =====================================================================================
# STAGE B — portfolios + thong ke
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
                ci_hi=obs + half, p_gt0=float((m > 0).mean()), means=m)


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
    return dict(p50=float(np.percentile(hs, 50)), p80=float(np.percentile(hs, 80)),
                mde80=mde80, power=power)


def stats():
    z = np.load(OUT + "/grid.npz", allow_pickle=True)
    syms = list(z["syms"])
    marks = z["marks"].astype(np.int64)
    S, M = len(syms), len(marks)
    c_e, c_x = z["c_e"], z["c_x"]
    slip_e, f_sig, f_cyc = z["slip_e"], z["f_sig"], z["f_cyc"]
    slip_f = z["slip_f"]
    ret24, mae, mfe = z["ret24"], z["mae"], z["mfe"]
    valid, delist = z["valid"].astype(bool), z["delist"].astype(bool)

    blk = block_ids(marks)
    devm = (BASE + marks >= DEV_LO)
    year = pd.to_datetime((BASE + marks) * 60000, unit="ms", utc=True).year.values
    price_short = np.where(valid, -(c_x / c_e - 1.0), np.nan) * 100.0     # %/notional (short)

    n_elig = valid.sum(axis=0)
    use = n_elig >= MIN_SYM
    say()
    say("=" * 100)
    say("STAGE B — PORTFOLIO (V1/V2/V3 + doi chung) | moc dung duoc: %d/%d" % (int(use.sum()), M))
    say("=" * 100)

    # ---------------- portfolio construction: W (M,S) signed weights, sum|w| = 1 ----------------
    def build_W(mode):
        W = np.zeros((M, S), dtype=np.float32)
        for t in range(M):
            if not use[t]:
                continue
            el = np.flatnonzero(valid[:, t])
            n = len(el)
            K = max(1, int(round(n / 10.0)))
            fs = f_sig[el, t]
            order = np.argsort(-fs, kind="stable")         # rate giam dan -> short dau
            top = el[order[:K]]
            if mode == "V1":
                W[t, top] = -1.0 / K
            elif mode == "V2":
                p90 = np.percentile(fs, 90.0)
                cand = el[(fs > p90) & (ret24[el, t] <= 0)]
                if len(cand):
                    W[t, cand] = -1.0 / len(cand)
            elif mode == "V3":
                bot = el[order[-K:]]
                W[t, top] = -0.5 / K
                W[t, bot] = +0.5 / K
            elif mode == "U":                                # doi chung: short universe EW
                W[t, el] = -1.0 / n
            elif mode == "L1":                               # doi chung: long bottom-decile (huong long-side da thua)
                W[t, el[order[-K:]]] = +1.0 / K
            elif mode == "NULL":
                rng = np.random.default_rng(SEED + t)
                pick = rng.choice(el, size=K, replace=False)
                W[t, pick] = -1.0 / K
        return W

    def eval_W(W, fee, slip_mode="emp", nrep_null=None):
        """tra ve dict: net/gross/funding/cost + tau + chi tiet."""
        Wa = np.abs(W)
        Wp = np.vstack([np.zeros((1, S), dtype=np.float32), W])
        dW = np.abs(W - Wp[:-1])
        rel = np.abs(dW) > 1e-9
        if slip_mode == "emp":
            sl = np.where(np.isfinite(slip_e), slip_e, 0.0).astype(np.float64)
        elif slip_mode == "flat14":
            sl = np.full((S, M), SLIP_FLAT_HI)
        elif slip_mode == "flat1bp":
            sl = np.full((S, M), SLIP_FLAT_LO)
        elif slip_mode == "exit":
            sl = np.where(np.isfinite(slip_f), slip_f, 0.0).astype(np.float64)
        csl = (fee + sl).T                       # (M,S)
        cost = (dW * csl).sum(axis=1) * 100.0    # %/notional/chu ky
        tau = dW.sum(axis=1)
        pf = np.where(np.isfinite(price_short), price_short, 0.0).T      # (M,S)
        gross_p = (W < 0) * Wa * pf              # (M,S): short leg
        gross_p = gross_p.sum(axis=1)
        # long leg (V3/L1): -price
        longmask = (W > 0)
        gross_p = gross_p + (longmask * Wa * (-pf)).sum(axis=1)
        fcy = np.where(np.isfinite(f_cyc), f_cyc, 0.0).T
        sgn = np.where(W < 0, 1.0, np.where(W > 0, -1.0, 0.0))   # short: +f_cyc (THU), long: -f_cyc (TRA)
        fund = (Wa * sgn * fcy).sum(axis=1)
        net = gross_p + fund - cost
        return dict(net=net, gross=gross_p + fund, gross_p=gross_p, fund=fund, cost=cost,
                    tau=tau, W=W, dW=dW, rel=rel, csl=csl, pf=pf, fcy=fcy)

    VAR = [("V1", "V1 pure carry (short top-decile f_sig)"),
           ("V2", "V2 carry + filter (f_sig>p90 & ret24<=0)"),
           ("V3", "V3 dollar-neutral (long bot-decile + short top-decile)"),
           ("U", "U doi chung: short universe EW"),
           ("L1", "L1 doi chung: long bottom-decile (huong long-side da thua)")]

    RES = {}
    WS = {}
    say()
    say("-- B1: ket qua theo bien the (chi phi CHINH = taker 0,05%/chan + slip proxy 0,5xrange/chan) --")
    say("%-4s %8s %10s %24s %8s %9s %9s %9s %9s %8s %8s" %
        ("var", "N_cyc", "net/cyc", "CI72h x1.21", "%cyc>0", "gross", "funding", "cost", "turnover", "cost/gross", "p(null)"))
    for key, desc in VAR:
        W = build_W(key)
        WS[key] = W
        e = eval_W(W, FEE_TAKER, "emp")
        net = e["net"]
        # chi tinh tren moc co vi the (flat => net 0, giu lai de dung so chu ky)
        mkk = use & (e["tau"] > 0) if key == "V2" else use
        netv, blkv = net[mkk], blk[mkk]
        st = summ(netv, blkv)
        # null: N coin NGẪU NHIÊN cùng số lượng (permutation test vectorized)
        pnull = np.nan
        if key in ("V1", "V2"):
            mt = np.flatnonzero(mkk)
            validT = valid.T
            vals = price_short.T + np.where(np.isfinite(f_cyc.T), f_cyc.T, 0.0)
            slT = np.where(np.isfinite(slip_e.T), slip_e.T, 0.0)
            Ks = np.array([max(1, int(round(int(validT[t].sum()) / 10.0))) for t in range(M)])
            rng = np.random.default_rng(SEED)
            nl = np.empty(NULL_REPS)
            ar = np.arange(M)
            for r in range(NULL_REPS):
                R = rng.random((M, S))
                R[~validT] = 2.0
                order = np.argsort(R, axis=1, kind="stable")
                vv = np.take_along_axis(np.where(validT, vals, 0.0), order, axis=1)
                ss = np.take_along_axis(slT, order, axis=1)
                kk = np.maximum(Ks[mt], 1)
                cv = np.cumsum(vv[mt], axis=1)[np.arange(len(mt)), kk - 1] / kk
                cs = np.cumsum(ss[mt], axis=1)[np.arange(len(mt)), kk - 1] / kk
                nl[r] = float(np.mean(cv - (FEE_TAKER + cs) * 100.0))
            pnull = float((nl >= netv.mean()).mean())
            RES[key + "_nullq"] = dict(p95=float(np.percentile(nl, 95)), p05=float(np.percentile(nl, 5)),
                                       mean=float(nl.mean()))
        md = mde_of(netv, blkv)
        RES[key] = dict(desc=desc, n=int(len(netv)), obs=st["obs"], ci_lo=st["ci_lo"], ci_hi=st["ci_hi"],
                        p_gt0=st["p_gt0"], nblk=st["nblk"],
                        pos_pct=float(100 * (netv > 0).mean()),
                        gross=float(e["gross"][mkk].mean()), gross_p=float(e["gross_p"][mkk].mean()),
                        fund=float(e["fund"][mkk].mean()), cost=float(e["cost"][mkk].mean()),
                        tau=float(e["tau"][mkk].mean()) / 2.0,
                        cost_gross=float(e["cost"][mkk].mean() / max(1e-12, abs(e["gross"][mkk].mean()))),
                        mde80=md["mde80"], mde_p50=md["p50"], pnull=pnull)
        r = RES[key]
        say("%-4s %8d %9.4f%%  [%9.4f%% %9.4f%%] %7.1f%% %8.4f%% %8.4f%% %8.4f%% %8.2f%% %7.0f%% %8.3f" %
            (key, r["n"], r["obs"], r["ci_lo"], r["ci_hi"], r["pos_pct"],
             r["gross"], r["fund"], -r["cost"], 100 * r["tau"],
             100 * r["cost_gross"], r["pnull"]))
        say("     MDE80=%s | p50 half=%s | null: mean %+.4f%% p05 %+.4f%% p95 %+.4f%%" %
            (("nan" if md["mde80"] is None else "%.2f%%" % md["mde80"]), "%.4f%%" % md["p50"],
             *[RES.get(key + "_nullq", {}).get(k, np.nan) for k in ("mean", "p05", "p95")]))

    # ---------------- B1b: DEV (2022-2025) la CHINH -------------
    say()
    say("-- B1b: DEV 2022-2025 (CHINH, tai lap tu cung W) --")
    say("%-4s %8s %10s %24s %8s %9s %9s %9s" % ("var", "N_cyc", "net/cyc", "CI72h x1.21", "%cyc>0", "gross", "funding", "cost"))
    for key, desc in VAR:
        W = WS[key]
        e = eval_W(W, FEE_TAKER, "emp")
        net = e["net"]
        mkk = (use & (e["tau"] > 0)) if key == "V2" else use
        m2 = mkk & devm
        netv, blkv = net[m2], blk[m2]
        st = summ(netv, blkv)
        say("%-4s %8d %9.4f%%  [%9.4f%% %9.4f%%] %7.1f%% %8.4f%% %8.4f%% %8.4f%%" %
            (key, len(netv), st["obs"], st["ci_lo"], st["ci_hi"], 100 * (netv > 0).mean(),
             e["gross"][m2].mean(), e["fund"][m2].mean(), -e["cost"][m2].mean()))
        RES[key + "_dev"] = dict(n=int(len(netv)), obs=float(st["obs"]), ci_lo=float(st["ci_lo"]),
                                 ci_hi=float(st["ci_hi"]), pos_pct=float(100 * (netv > 0).mean()))

    # ---------------- B2: bien the chi phi ----------------
    say()
    say("-- B2: do ben theo CHI PHI (V1) — fee x slip --")
    say("%-26s %10s %24s %9s" % ("cost variant", "net/cyc", "CI72h x1.21", "%cyc>0"))
    W1 = build_W("V1")
    for lbl, fee, sm in [("taker .05 + slip proxy", FEE_TAKER, "emp"),
                         ("maker .02 + slip proxy", FEE_MAKER, "emp"),
                         ("taker .05 + slip 0,140%/chan", FEE_TAKER, "flat14"),
                         ("taker .05 + slip 1bp/chan", FEE_TAKER, "flat1bp"),
                         ("taker .05 + slip exit-candle", FEE_TAKER, "exit")]:
        e = eval_W(W1, fee, sm)
        netv = e["net"][use]
        st = summ(netv, blk[use])
        RES["V1cost_" + lbl] = dict(obs=st["obs"], ci_lo=st["ci_lo"], ci_hi=st["ci_hi"],
                                    pos_pct=float(100 * (netv > 0).mean()))
        say("%-26s %9.4f%% [%9.4f%% %9.4f%%] %7.1f%%" %
            (lbl, st["obs"], st["ci_lo"], st["ci_hi"], 100 * (netv > 0).mean()))
    # bien the baO thu: dong/mo toan so moi chu ky
    e = eval_W(W1, FEE_TAKER, "emp")
    tau_rt = 2.0
    slip_book = np.where(np.isfinite(slip_e), slip_e, 0.0)
    nbk = np.asarray(np.abs(W1) > 0)
    avg_slip = np.where(nbk, slip_book.T, np.nan)
    with np.errstate(invalid="ignore"):
        avg_slip = np.nanmean(avg_slip, axis=1)
    cost_rt = tau_rt * (FEE_TAKER + np.where(np.isfinite(avg_slip), avg_slip, 0.0)) * 100.0
    net_rt = e["gross"] - cost_rt
    st = summ(net_rt[use], blk[use])
    say("%-26s %9.4f%% [%9.4f%% %9.4f%%] %7.1f%%" %
        ("taker .05 + round-trip/cyc", st["obs"], st["ci_lo"], st["ci_hi"],
         100 * (net_rt[use] > 0).mean()))
    RES["V1cost_roundtrip"] = dict(obs=st["obs"], ci_lo=st["ci_lo"], ci_hi=st["ci_hi"])

    # ---------------- B3: theo nam (V1/V3 + doi chung) ----------------
    say()
    say("-- B3: net/chu ky theo NAM (chi phi chinh) --")
    say("%-4s %s" % ("var", " ".join("%9d" % y for y in range(2021, 2026))))
    for key, _ in VAR:
        W = build_W(key)
        e = eval_W(W, FEE_TAKER, "emp")
        netv = e["net"]
        row = []
        for y in range(2021, 2026):
            m = use & (year == y)
            row.append("%8.4f%%" % (netv[m].mean()) if m.sum() else "      n/a")
        say("%-4s %s" % (key, " ".join(row)))
        RES[key + "_byyear"] = {int(y): (float(netv[use & (year == y)].mean()) if (use & (year == y)).sum() else None)
                                for y in range(2021, 2026)}

    # ---------------- B4: rui ro short (MAE / squeeze) cho V1, V2, V3 ----------------
    say()
    say("-- B4: RUI RO SHORT — max adverse excursion (drawup trong (r, r+480]) + squeeze --")
    say("%-4s %7s %9s %9s %9s %9s %9s %9s   %s" %
        ("var", "n_pos", "MAE p50", "p90", "p99", "max", "MFE p50", "MFE p90", "%squeeze>20%"))
    for key in ("V1", "V2", "V3", "U"):
        W = build_W(key)
        sh = (W < 0) & valid.T
        mv = mae.T[sh]
        fv = mfe.T[sh]
        mv = mv[np.isfinite(mv)]
        fv = fv[np.isfinite(fv)]
        sq = float(100 * (mv > SQUEEZE).mean())
        say("%-4s %7d %8.2f%% %8.2f%% %8.2f%% %8.2f%% %8.2f%% %8.2f%%   %.2f%%" %
            (key, len(mv), *[100 * np.percentile(mv, q) for q in (50, 90, 99, 100)],
             *[100 * np.percentile(fv, q) for q in (50, 90)], sq))
        RES[key + "_mae"] = dict(n=int(len(mv)), p50=float(np.percentile(mv, 50)), p90=float(np.percentile(mv, 90)),
                                 p99=float(np.percentile(mv, 99)), max=float(mv.max()),
                                 mfe_p50=float(np.percentile(fv, 50)), mfe_p90=float(np.percentile(fv, 90)),
                                 squeeze_pct=sq)
    # worst 8 squeeze V1
    W1 = build_W("V1")
    sh = (W1 < 0) & valid.T
    ws = np.argwhere(sh)
    vals = mae.T[sh]
    fin = np.isfinite(vals)
    ws = ws[fin]
    vals = vals[fin]
    od = np.argsort(-vals)[:8]
    say("   worst 8 drawup (V1):")
    for i in od:
        t, s = ws[i]
        say("     %-6s %s  drawup %+8.2f%%  (f_sig %+7.4f %% ; f_cyc %+7.4f %%)" %
            (syms[s], utc_min(marks[t]), 100 * vals[i], f_sig[s, t], f_cyc[s, t]))
    RES["V1_worst"] = [dict(sym=syms[ws[i][1]], mark=utc_min(marks[ws[i][0]]), drawup=float(100 * vals[i]))
                       for i in od]

    # ---------------- B5: chiet khau (gross/funding/cost) ----------------
    say()
    say("-- B5: phan ra gross vs net (V1) --")
    e = eval_W(W1, FEE_TAKER, "emp")
    say("   gia (short leg): %+.4f%%/chu ky | funding THU: %+.4f%%/chu ky | gross: %+.4f%% | cost: -%.4f%% | net: %+.4f%%" %
        (e["gross_p"][use].mean(), e["fund"][use].mean(), e["gross"][use].mean(),
         e["cost"][use].mean(), e["net"][use].mean()))
    say("   turnover 1 ve: %.2f%%/chu ky | cost drag: %.4f%%/chu ky | cost/gross: %.0f%%" %
        (100 * e["tau"][use].mean() / 2, e["cost"][use].mean(),
         100 * e["cost"][use].mean() / max(1e-12, abs(e["gross"][use].mean()))))
    RES["V1_decomp"] = dict(price=float(e["gross_p"][use].mean()), fund=float(e["fund"][use].mean()),
                            gross=float(e["gross"][use].mean()), cost=float(e["cost"][use].mean()),
                            net=float(e["net"][use].mean()),
                            turnover_1s=float(100 * e["tau"][use].mean() / 2))
    # ALL vs DEV
    say("   DEV (2022-2025) net %+.4f%% | ALL (2021-2025) net %+.4f%%" %
        (e["net"][use & devm].mean(), e["net"][use].mean()))

    # ---------------- B6: funding unconditional tai cac moc (bang chung carry) ----------------
    say()
    say("-- B6: carry budget (unconditional, tai cac moc dung) --")
    fs = f_sig[:, use].ravel()
    fs = fs[np.isfinite(fs)]
    fy = f_cyc[:, use].ravel()
    fy = fy[np.isfinite(fy)]
    say("   f_sig  (rate da settle): %%>0 %.1f%% | mean %+.4f bp | med %+.4f bp" %
        (100 * (fs > 0).mean(), 1e4 * fs.mean(), 1e4 * np.median(fs)))
    say("   f_cyc  (thu ca chu ky 8h): %%>0 %.1f%% | mean %+.4f %% | med %+.4f %%" %
        (100 * (fy > 0).mean(), fy.mean(), np.median(fy)))
    tk_s, tk_c, bk_c = [], [], []
    for t in np.flatnonzero(use):
        el = np.flatnonzero(valid[:, t])
        K = max(1, int(round(len(el) / 10.0)))
        o = np.argsort(-f_sig[el, t], kind="stable")
        tk_s.append(float(f_sig[el[o[:K]], t].mean()))
        tk_c.append(float(f_cyc[el[o[:K]], t].mean()))
        bk_c.append(float(f_cyc[el[o[-K:]], t].mean()))
    tk_s, tk_c, bk_c = np.array(tk_s), np.array(tk_c), np.array(bk_c)
    say("   top-decile f_sig: mean %+.4f bp | med %+.4f bp" % (1e4 * tk_s.mean(), 1e4 * np.median(tk_s)))
    say("   top-decile f_cyc (short THU): mean %+.4f %% | med %+.4f %% | %%>0 %.1f%%" %
        (tk_c.mean(), np.median(tk_c), 100 * (tk_c > 0).mean()))
    say("   bottom-decile f_cyc (long TRA): mean %+.4f %% | med %+.4f %%" % (bk_c.mean(), np.median(bk_c)))
    RES["carry_budget"] = dict(pct_pos_fsig=float(100 * (fs > 0).mean()), mean_fsig_bp=float(1e4 * fs.mean()),
                               mean_fcyc=float(fy.mean()), pct_pos_fcyc=float(100 * (fy > 0).mean()),
                               top_fsig_bp=float(1e4 * tk_s.mean()), top_fcyc=float(tk_c.mean()),
                               bot_fcyc=float(bk_c.mean()), top_fcyc_pospct=float(100 * (tk_c > 0).mean()))

    with open(OUT + "/summary.json", "w") as f:
        json.dump({k: v for k, v in RES.items() if not isinstance(v, np.ndarray)}, f, indent=1, default=str)
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
