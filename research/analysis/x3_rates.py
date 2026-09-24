"""X3 — cham diem 5 run: trailing cap theo RANK selector (viec A) + pre-arm SL -50% (viec B).

Xem docs/prereg/PREREG_X3.md muc 4-6. Dung lai may bootstrap khoi-72h x1.21 cua c3_rates.
Them so voi x2_rates.py:
  - phan bo `profit | STOP_MARKET_DONE` (p10/p25/med/p75/p90/mean) — muc tieu that cua viec A
  - bang 8 hang RANK -> n, %STRONG (ban le 0.29), mean(profit|SM)  [doc dong SELRANK trong sim.out]
  - dem cum bi cat tai -50 va bao nhieu trong so do PARITY ket thuc STOP_MARKET_DONE

Usage: python3 x3_rates.py            (mac dinh 5 tag cua X3)
"""
import logging
import re
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

PARITY = "X3_PARITY"
ARMS_A = ["X3_R2", "X3_R4", "X3_R6"]
ARMS_B = ["X3_S50"]
ARMS = ARMS_A + ARMS_B
TAGS = [PARITY] + ARMS
NCAP = {"X3_PARITY": 0, "X3_R2": 2, "X3_R4": 4, "X3_R6": 6, "X3_S50": 0}
TSH = 168
KEYS3 = ("n", "win", "tsloss", "mp_sm", "mp_sl", "meanP", "margin",
         "p10sm", "p25sm", "medsm", "p75sm", "p90sm", "p10loss")
LBL = {"n": "n", "win": "win%", "tsloss": "TSloss%", "mp_sm": "mean|SM", "mp_sl": "mP|SL",
       "meanP": "meanP", "margin": "mMargin", "p10sm": "p10|SM", "p25sm": "p25|SM",
       "medsm": "med|SM", "p75sm": "p75|SM", "p90sm": "p90|SM", "p10loss": "p10loser"}
QUALITY = ("win", "tsloss", "mp_sm", "mp_sl", "meanP", "p90sm", "medsm", "p10loss")
BLK0 = pd.Timestamp("2022-01-01")
HARD_DD, HARD_Q, UW_MULT = 15.0, -5.0, 1.2
WEAK_THR = C.WEAK_THR          # 0.29
SEL_RX = re.compile(r"SELRANK sym=(\S+) tOpen=(\d{8} \d\d:\d\d) tMs=(\d+) rank=(\d+) pred=(\S+)")
PRE_RX = re.compile(r"PREARM_SL sym=(\S+) first=(\S+) stop=(\S+) exit=(\S+) tOpen=(\d+) tNow=(\d+)")


def trades3(tag):
    """C.trades + luoi khoi neo o goc CO DINH => moi arm dung chung index khoi (paired that)."""
    d = C.trades(tag)
    d["blk"] = ((d.ts - BLK0) / pd.Timedelta(hours=C.BLOCK_H)).astype(int)
    return d


def rates3(d):
    r = C.rates(d)
    sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"] if len(d) else pd.Series(dtype=float)
    for k, q in (("p10sm", .10), ("p25sm", .25), ("medsm", .50), ("p75sm", .75), ("p90sm", .90)):
        r[k] = float(sm.quantile(q)) if len(sm) else float("nan")
    r["n_sm"] = int(len(sm))
    loser = d.loc[d.profit < 0, "profit"] if len(d) else pd.Series(dtype=float)
    r["p10loss"] = float(loser.quantile(0.10)) if len(loser) else float("nan")
    r["medloss"] = float(loser.median()) if len(loser) else float("nan")
    r["minloss"] = float(loser.min()) if len(loser) else float("nan")
    return r


def _base(sym):
    """printDone.csv ghi sym KHONG co duoi quote (`ANT`), log SLF4J ghi day du (`ANTUSDT`).
    Cat duoi de hai ben ghep duoc. Cat o CUOI chuoi, khong `replace`, de `USUSDT` -> `US`."""
    return sym[:-4] if sym.endswith("USDT") else sym


def selrank(tag):
    """Doc dong SELRANK tu sim.out -> DataFrame(sym, start, rank, pred). Khoa ghep = (sym, start)."""
    rows = []
    try:
        with open(f"{C.B}/{tag}/logs/sim.out", errors="ignore") as fh:
            for ln in fh:
                m = SEL_RX.search(ln)
                if m:
                    rows.append((_base(m.group(1)), m.group(2), int(m.group(4)),
                                 float(m.group(5)) if m.group(5) != "null" else float("nan")))
    except FileNotFoundError:
        pass
    return pd.DataFrame(rows, columns=["sym", "start", "rank", "pred_log"])


def prearm(tag):
    rows = []
    try:
        with open(f"{C.B}/{tag}/logs/sim.out", errors="ignore") as fh:
            for ln in fh:
                m = PRE_RX.search(ln)
                if m:
                    rows.append((_base(m.group(1)), int(m.group(5))))
    except FileNotFoundError:
        pass
    return pd.DataFrame(rows, columns=["sym", "tOpen"])


def main_table(dd):
    log.info("=== BANG CHINH 48 THANG (equity/CAGR KHONG phai tieu chi) ===")
    log.info("%-11s %5s %6s %8s %8s %9s %9s %9s %8s", "tag", "n", "win%", "TSloss%",
             "mean|SM", "mP|SL", "p10loser", "minloser", "meanP")
    for t in TAGS:
        r = rates3(dd[t])
        log.info("%-11s %5.0f %6.2f %8.2f %8.3f %9.3f %9.2f %9.2f %8.3f", t, r["n"],
                 r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"], r["p10loss"],
                 r["minloss"], r["meanP"])
    log.info("")
    log.info("=== A1 — PHAN BO WINNER `profit | STOP_MARKET_DONE` (muc tieu that cua viec A) ===")
    log.info("%-11s %4s %6s %8s %8s %8s %8s %8s %8s", "tag", "N", "n_SM",
             "p10", "p25", "med", "p75", "p90", "mean")
    for t in TAGS:
        r = rates3(dd[t])
        log.info("%-11s %4d %6d %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f", t, NCAP[t], r["n_sm"],
                 r["p10sm"], r["p25sm"], r["medsm"], r["p75sm"], r["p90sm"], r["mp_sm"])


def rank_table(dd):
    log.info("")
    log.info("=== A4 — RANK x STRONG x PROFIT (ban le PARITY: symbolPred <= %.2f = STRONG) ===",
             WEAK_THR)
    for t in TAGS:
        sr = selrank(t)
        d = dd[t]
        if sr.empty:
            log.info("%-11s KHONG co dong SELRANK trong sim.out", t)
            continue
        sr = sr.drop_duplicates(subset=["sym", "start"])
        m = d[d.leg == 0].merge(sr, on=["sym", "start"], how="left")
        cov = 100.0 * m["rank"].notna().mean()
        log.info("")
        log.info("--- %s (N=%d) | ghep rank: %.1f%% cua %d cum leg-1 ---", t, NCAP[t], cov, len(m))
        log.info("%5s %6s %9s %11s %11s %9s", "rank", "n", "%STRONG", "mean(p|SM)",
                 "med(p|SM)", "n_SM")
        for rk in range(1, 9):
            g = m[m["rank"] == rk]
            if not len(g):
                continue
            kn = g.symbolPred.notna()
            pstrong = 100.0 * (g.symbolPred[kn] <= WEAK_THR).mean() if kn.any() else float("nan")
            sm = g.loc[g.status == "STOP_MARKET_DONE", "profit"]
            log.info("%5d %6d %8.1f%% %11.3f %11.3f %9d", rk, len(g), pstrong,
                     sm.mean() if len(sm) else float("nan"),
                     sm.median() if len(sm) else float("nan"), len(sm))
        kn = m.symbolPred.notna()
        small = m.loc[m.status == "STOP_MARKET_DONE", "profit"]
        log.info("%5s %6d %8.1f%% %11.3f %11.3f %9d", "ALL", len(m),
                 100.0 * (m.symbolPred[kn] <= WEAK_THR).mean() if kn.any() else float("nan"),
                 small.mean() if len(small) else float("nan"),
                 small.median() if len(small) else float("nan"), len(small))


def ci_pair(da, db):
    if len(da) == 0 or len(db) == 0:
        return {k: (float("nan"),) * 3 + (False,) for k in KEYS3}
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(C.SEED)
    ra0, rb0 = rates3(da), rates3(db)
    obs = {k: ra0[k] - rb0[k] for k in KEYS3}
    draws = {k: [] for k in KEYS3}
    for _ in range(C.NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        la = [ga[b] for b in pick if b in ga]
        lb = [gb[b] for b in pick if b in gb]
        ra = rates3(pd.concat(la) if la else da.iloc[:0])
        rb = rates3(pd.concat(lb) if lb else db.iloc[:0])
        for k in KEYS3:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in KEYS3:
        arr = np.asarray(draws[k], dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            out[k] = (obs[k], float("nan"), float("nan"), False)
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        c = (lo + hi) / 2.0
        lo, hi = c - (c - lo) * C.CI_INFLATE, c + (hi - c) * C.CI_INFLATE
        out[k] = (obs[k], lo, hi, not (lo <= 0.0 <= hi))
    return out


def ci_all(dd, subs=(None, 2022, 2023, 2024, 2025)):
    res = {}
    for t in ARMS:
        for sub in subs:
            da, db = dd[t], dd[PARITY]
            if sub is not None:
                da, db = da[da.ts.dt.year == sub], db[db.ts.dt.year == sub]
            r = ci_pair(da, db)
            res[(t, sub)] = r
            nout = sum(int(r[k][3]) for k in QUALITY)
            log.info("")
            log.info("--- CI khoi-72h x%.2f : %s - %s [%s] (n_A=%d n_B=%d) ---", C.CI_INFLATE,
                     t, PARITY, sub or "TOAN CUA SO", len(da), len(db))
            log.info("%-9s %10s %11s %11s %8s", "rate", "hieu", "lo", "hi", "ngoaiCI")
            for k in KEYS3:
                o, lo, hi, o2 = r[k]
                log.info("%-9s %10.3f %11.3f %11.3f %8s", LBL[k], o, lo, hi, "YES" if o2 else "-")
            log.info("  => rate CHAT LUONG ngoai CI: %d", nout)
    return res


def hard_by_year():
    log.info("")
    log.info("=== RANG BUOC CUNG THEO NAM (maxDD<=%.0f%%, khong nam am, quy>=%.0f%%, "
             "UW <= %.1f x UW parity cung nam) ===", HARD_DD, HARD_Q, UW_MULT)
    base, rows = {}, {}
    for t in TAGS:
        s = C.equity(t)
        rows[t] = {}
        for y, sy in s.groupby(s.index.year):
            ddv = (sy / sy.cummax() - 1) * 100
            uw = sy < sy.cummax()
            uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
            qe = sy.resample("QE").last()
            q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
            qr = (qe.values / q0.values - 1) * 100
            ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
            rows[t][y] = (float(ddv.min()), uwmax, float(ry), float(qr.min()))
        if t == PARITY:
            base = {y: v[1] for y, v in rows[t].items()}
    log.info("%-11s %5s %9s %6s %9s %9s %9s %6s", "tag", "nam", "maxDD%", "UW",
             "UW_tran", "ret_nam%", "quy_min%", "PASS")
    verdict = {}
    for t in TAGS:
        allok = True
        for y in sorted(rows[t]):
            mdd, uwmax, ry, qmin = rows[t][y]
            cap = UW_MULT * base.get(y, uwmax)
            ok = (mdd >= -HARD_DD) and (uwmax <= cap) and (ry >= 0) and (qmin >= HARD_Q)
            allok &= ok
            log.info("%-11s %5d %9.2f %6d %9.1f %9.2f %9.2f %6s", t, y, mdd, uwmax, cap,
                     ry, qmin, "PASS" if ok else "**FAIL**")
        verdict[t] = allok
    log.info("  => PASS toan bo R1-R4: %s", {t: ("PASS" if v else "FAIL") for t, v in verdict.items()})
    return verdict


def cost_of_sl(dd):
    log.info("")
    log.info("=== B — CHI PHI CUA PRE-ARM SL -50%% (cum bi cat ma PARITY thang) ===")
    p = dd[PARITY]
    pk = p[p.leg == 0].drop_duplicates(subset=["sym", "start"]).set_index(["sym", "start"])
    log.info("%-11s %8s %9s %9s %11s %11s %11s", "tag", "n_SL", "ghep%", "cat_oan",
             "oan%_SL", "pnl_parity", "profit%_tb")
    for t in ARMS_B:
        d = dd[t]
        sl = d[(d.status == "STOP_LOSS_DONE") & (d.leg == 0)]
        key = list(zip(sl.sym, sl.start))
        hit = [k for k in key if k in pk.index]
        matched = len(hit) / len(key) * 100 if len(key) else float("nan")
        sub = pk.loc[hit] if hit else pk.iloc[:0]
        won = sub[sub.status == "STOP_MARKET_DONE"]
        log.info("%-11s %8d %8.1f%% %9d %10.1f%% %11.1f %11.3f", t, len(sl), matched,
                 len(won), 100.0 * len(won) / len(sl) if len(sl) else float("nan"),
                 float(won.pnl.sum()) if len(won) else 0.0,
                 float(won.profit.mean()) if len(won) else float("nan"))
    log.info("  (ghep%% < 80 => KHONG do duoc dang tin cay — ghi trong ngoac)")
    log.info("")
    log.info("=== B — TACH LY DO THOAT (log PREARM_SL vs time_order) ===")
    log.info("%-11s %10s %14s %13s %11s", "tag", "n_SL", "n_prearm_log", "n_hold<168h", "n_timestop")
    for t in TAGS:
        d = dd[t]
        sl = d[d.status == "STOP_LOSS_DONE"]
        nlog = len(prearm(t))
        short = int((pd.to_numeric(sl.time_order, errors="coerce") < TSH).sum())
        log.info("%-11s %10d %14d %13d %11d", t, len(sl), nlog, short, len(sl) - short)


def year_table(dd):
    log.info("")
    log.info("=== RATE THEO NAM ===")
    log.info("%-11s %5s %5s %6s %8s %8s %8s %9s %9s", "tag", "nam", "n", "win%",
             "TSloss%", "mean|SM", "p90|SM", "mP|SL", "p10loser")
    for t in TAGS:
        d = dd[t]
        for y, g in d.groupby(d.ts.dt.year):
            r = rates3(g)
            log.info("%-11s %5d %5d %6.2f %8.2f %8.3f %8.3f %9.3f %9.2f", t, y, int(r["n"]),
                     r["win"], r["tsloss"], r["mp_sm"], r["p90sm"], r["mp_sl"], r["p10loss"])


def verdicts(dd, ci, hard):
    log.info("")
    log.info("=== PHAN QUYET (PREREG_X3 muc 6) ===")
    r = {t: rates3(dd[t]) for t in TAGS}
    seq = [PARITY] + ARMS_A
    p90 = [r[t]["p90sm"] for t in seq]
    msm = [r[t]["mp_sm"] for t in seq]
    mono_p90 = all(p90[i] < p90[i + 1] for i in range(len(p90) - 1))
    mono_msm = all(msm[i] < msm[i + 1] for i in range(len(msm) - 1))
    winok = all(not (ci[(t, None)]["win"][3] and ci[(t, None)]["win"][0] < 0) for t in ARMS_A)
    passok = any(hard[t] for t in ARMS_A)
    log.info("VIEC A: p90|SM theo N (0,2,4,6) = %s -> don dieu tang: %s",
             [round(x, 3) for x in p90], mono_p90)
    log.info("        mean|SM theo N          = %s -> don dieu tang: %s",
             [round(x, 3) for x in msm], mono_msm)
    log.info("        (1) don dieu p90 HOAC mean : %s", mono_p90 or mono_msm)
    log.info("        (2) win%% khong giam ngoai CI: %s", winok)
    log.info("        (3) >=1 muc PASS R1-R4     : %s", passok)
    log.info("        => VIEC A: %s",
             "CO TIN HIEU" if ((mono_p90 or mono_msm) and winok and passok) else "KHONG CO TIN HIEU")
    t = ARMS_B[0]
    o, lo, hi, out = ci[(t, None)]["p10loss"]
    b1 = bool(out and o > 0)
    b2 = not ci[(t, None)]["win"][3]
    b3 = hard[t]
    log.info("VIEC B: (1) p10loser cai thien ngoai CI: %s (hieu %+0.3f CI[%.3f,%.3f])", b1, o, lo, hi)
    log.info("        (2) win%% trong CI              : %s (hieu %+0.3f)", b2, ci[(t, None)]["win"][0])
    log.info("        (3) PASS R1-R4                 : %s", b3)
    log.info("        => VIEC B: %s", "CO TIN HIEU" if (b1 and b2 and b3) else "KHONG CO TIN HIEU")


def equity_table():
    log.info("")
    log.info("=== EQUITY / CAGR — KHONG PHAI TIEU CHI (N=5 => 2.57*sqrt(2 ln 5) = 4.6pp) ===")
    log.info("%-11s %10s %8s %9s %6s", "tag", "equity", "CAGR%", "maxDD%", "UW")
    for t in TAGS:
        s = C.equity(t)
        ddv = (s / s.cummax() - 1) * 100
        uw = s < s.cummax()
        years = (s.index[-1] - s.index[0]).days / 365.25
        cagr = ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100
        log.info("%-11s %10.0f %8.2f %9.2f %6d", t, s.iloc[-1], cagr, ddv.min(),
                 int(uw.groupby((~uw).cumsum()).sum().max()))


def main():
    dd = {t: trades3(t) for t in TAGS}
    main_table(dd)
    rank_table(dd)
    year_table(dd)
    ci = ci_all(dd)
    hard = hard_by_year()
    cost_of_sl(dd)
    verdicts(dd, ci, hard)
    equity_table()


if __name__ == "__main__":
    main()
