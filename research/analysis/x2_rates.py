"""X2 — cham diem 6 arm (2 truc exit) tren cua so 48 thang. Xem docs/PREREG_X2.md muc 5-7.

Dung lai may bootstrap khoi-72h x1.21 cua research/analysis/c3_rates.py.
Them so voi x1_rates.py:
  - `p10loss` = phan vi 10 cua phan bo profit cua LENH THUA (profit < 0) -> DUOI, muc tieu that
  - luoi khoi CHUNG neo o mot goc CO DINH (2022-01-01) => 6 arm dung chung index khoi
  - rang buoc UW TUONG DOI (<= 1.2 x UW cua parity cung nam), theo X1_EXTEND muc 7
  - P5: dem cum bi cat (SL) o arm ma o PARITY ket thuc STOP_MARKET_DONE = "cat oan"

Usage: python3 x2_rates.py            (mac dinh 6 tag cua X2)
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

PARITY = "X2_PARITY"
ARMS = ["X2_T120", "X2_T96", "X2_T72", "X2_S20", "X2_S30"]
TAGS = [PARITY] + ARMS
AXIS = {"X2_T120": "T", "X2_T96": "T", "X2_T72": "T", "X2_S20": "S", "X2_S30": "S"}
TSH = {"X2_PARITY": 168, "X2_T120": 120, "X2_T96": 96, "X2_T72": 72,
       "X2_S20": 168, "X2_S30": 168}
KEYS2 = ("n", "win", "tsloss", "mp_sm", "mp_sl", "p10loss", "meanP", "margin")
LBL = {"n": "n", "win": "win%", "tsloss": "TSloss%", "mp_sm": "mP|SM", "mp_sl": "mP|SL",
       "p10loss": "p10loser", "meanP": "meanP", "margin": "mMargin"}
QUALITY = ("win", "tsloss", "mp_sm", "mp_sl", "p10loss", "meanP")   # bo n, margin (bien co hoc)
BLK0 = pd.Timestamp("2022-01-01")
HARD_DD, HARD_Q, UW_MULT = 15.0, -5.0, 1.2
PRE_RX = re.compile(r"PREARM_SL sym=(\S+) first=(\S+) stop=(\S+) exit=(\S+) tOpen=(\d+) tNow=(\d+)")


def trades2(tag):
    """C.trades + luoi khoi neo o goc CO DINH => 6 arm dung chung index khoi (paired that)."""
    d = C.trades(tag)
    d["blk"] = ((d.ts - BLK0) / pd.Timedelta(hours=C.BLOCK_H)).astype(int)
    return d


def rates2(d):
    r = C.rates(d)
    loser = d.loc[d.profit < 0, "profit"] if len(d) else pd.Series(dtype=float)
    r["p10loss"] = float(loser.quantile(0.10)) if len(loser) else float("nan")
    r["p25loss"] = float(loser.quantile(0.25)) if len(loser) else float("nan")
    r["medloss"] = float(loser.median()) if len(loser) else float("nan")
    r["minloss"] = float(loser.min()) if len(loser) else float("nan")
    r["n_loser"] = int(len(loser))
    return r


def ci_pair(da, db):
    """CI khoi-72h paired cua hieu (A - B) tren hai bang trade da loc (luoi khoi CHUNG)."""
    if len(da) == 0 or len(db) == 0:
        return {k: (float("nan"),) * 3 + (False,) for k in KEYS2}
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(C.SEED)
    ra0, rb0 = rates2(da), rates2(db)
    obs = {k: ra0[k] - rb0[k] for k in KEYS2}
    draws = {k: [] for k in KEYS2}
    for _ in range(C.NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        la = [ga[b] for b in pick if b in ga]
        lb = [gb[b] for b in pick if b in gb]
        ra = rates2(pd.concat(la) if la else da.iloc[:0])
        rb = rates2(pd.concat(lb) if lb else db.iloc[:0])
        for k in KEYS2:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in KEYS2:
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


def main_table(dd):
    log.info("=== BANG CHINH 48 THANG (equity/CAGR KHONG phai tieu chi) ===")
    log.info("%-10s %5s %6s %8s %8s %9s %9s %8s %8s %8s", "tag", "n", "win%", "TSloss%",
             "mP|SM", "mP|SL", "p10loser", "medloser", "minloser", "meanP")
    for t in TAGS:
        r = rates2(dd[t])
        log.info("%-10s %5.0f %6.2f %8.2f %8.3f %9.3f %9.2f %8.2f %8.2f %8.3f", t, r["n"],
                 r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"], r["p10loss"],
                 r["medloss"], r["minloss"], r["meanP"])


def year_table(dd):
    log.info("")
    log.info("=== RATE THEO NAM ===")
    log.info("%-10s %5s %5s %6s %8s %8s %9s %9s %8s %8s", "tag", "nam", "n", "win%",
             "TSloss%", "mP|SM", "mP|SL", "p10loser", "minloser", "meanP")
    for t in TAGS:
        d = dd[t]
        for y, g in d.groupby(d.ts.dt.year):
            r = rates2(g)
            log.info("%-10s %5d %5d %6.2f %8.2f %8.3f %9.3f %9.2f %8.2f %8.3f", t, y,
                     int(r["n"]), r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"],
                     r["p10loss"], r["minloss"], r["meanP"])


def ci_all(dd):
    for t in ARMS:
        for sub in [None, 2022, 2023, 2024, 2025]:
            da, db = dd[t], dd[PARITY]
            if sub is not None:
                da, db = da[da.ts.dt.year == sub], db[db.ts.dt.year == sub]
            r = ci_pair(da, db)
            nout = sum(int(r[k][3]) for k in QUALITY)
            log.info("")
            log.info("--- CI khoi-72h x%.2f : %s - %s [%s] (n_A=%d n_B=%d)", C.CI_INFLATE,
                     t, PARITY, sub or "TOAN CUA SO", len(da), len(db))
            log.info("%-9s %10s %11s %11s %8s", "rate", "hieu", "lo", "hi", "ngoaiCI")
            for k in KEYS2:
                o, lo, hi, out = r[k]
                log.info("%-9s %10.3f %11.3f %11.3f %8s", LBL[k], o, lo, hi,
                         "YES" if out else "-")
            log.info("  => rate CHAT LUONG ngoai CI: %d", nout)


def hard_by_year():
    log.info("")
    log.info("=== RANG BUOC CUNG THEO NAM (maxDD<=%.0f%%, khong nam am, quy>=%.0f%%, "
             "UW <= %.1f x UW parity cung nam) ===", HARD_DD, HARD_Q, UW_MULT)
    base = {}
    rows = {}
    for t in TAGS:
        s = C.equity(t)
        rows[t] = {}
        for y, sy in s.groupby(s.index.year):
            dd = (sy / sy.cummax() - 1) * 100
            uw = sy < sy.cummax()
            uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
            qe = sy.resample("QE").last()
            q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
            qr = (qe.values / q0.values - 1) * 100
            ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
            rows[t][y] = (float(dd.min()), uwmax, float(ry), float(qr.min()))
        if t == PARITY:
            base = {y: v[1] for y, v in rows[t].items()}
    log.info("%-10s %5s %9s %6s %9s %9s %9s %6s", "tag", "nam", "maxDD%", "UW",
             "UW_tran", "ret_nam%", "quy_min%", "PASS")
    verdict = {}
    for t in TAGS:
        allok = True
        for y in sorted(rows[t]):
            mdd, uwmax, ry, qmin = rows[t][y]
            cap = UW_MULT * base.get(y, uwmax)
            ok = (mdd >= -HARD_DD) and (uwmax <= cap) and (ry >= 0) and (qmin >= HARD_Q)
            allok &= ok
            log.info("%-10s %5d %9.2f %6d %9.1f %9.2f %9.2f %6s", t, y, mdd, uwmax, cap,
                     ry, qmin, "PASS" if ok else "**FAIL**")
        verdict[t] = allok
    log.info("  => PASS toan bo R1-R4: %s",
             {t: ("PASS" if v else "FAIL") for t, v in verdict.items()})
    return verdict


def prearm_log(tag):
    """Doc dong PREARM_SL tu sim.out -> DataFrame (sym, tOpen ms)."""
    rows = []
    try:
        with open(f"{C.B}/{tag}/logs/sim.out", errors="ignore") as fh:
            for ln in fh:
                m = PRE_RX.search(ln)
                if m:
                    rows.append((m.group(1), int(m.group(5))))
    except FileNotFoundError:
        return pd.DataFrame(columns=["sym", "tOpen"])
    return pd.DataFrame(rows, columns=["sym", "tOpen"])


def cost_of_sl(dd):
    """P5 — chi phi that: cum bi cat o arm ma o PARITY ket thuc STOP_MARKET_DONE."""
    log.info("")
    log.info("=== P5 — CHI PHI CUA SL/TIME-STOP (cum bi cat ma PARITY thang) ===")
    p = dd[PARITY]
    pk = p[p.leg == 0].drop_duplicates(subset=["sym", "start"]).set_index(["sym", "start"])
    log.info("%-10s %8s %9s %9s %9s %11s %11s", "tag", "n_SL", "ghep%", "cat_oan",
             "oan%_SL", "pnl_parity", "profit%_tb")
    for t in ARMS:
        d = dd[t]
        sl = d[(d.status == "STOP_LOSS_DONE") & (d.leg == 0)]
        key = list(zip(sl.sym, sl.start))
        hit = [k for k in key if k in pk.index]
        matched = len(hit) / len(key) * 100 if len(key) else float("nan")
        sub = pk.loc[hit] if hit else pk.iloc[:0]
        won = sub[sub.status == "STOP_MARKET_DONE"]
        log.info("%-10s %8d %8.1f%% %9d %8.1f%% %11.1f %11.3f", t, len(sl), matched,
                 len(won), 100.0 * len(won) / len(sl) if len(sl) else float("nan"),
                 float(won.pnl.sum()) if len(won) else 0.0,
                 float(won.profit.mean()) if len(won) else float("nan"))
    log.info("  (ghep% < 80 => KHONG do duoc dang tin cay; hai arm phan ky theo thoi gian)")

    log.info("")
    log.info("=== P5b — TACH LY DO THOAT o truc S (log PREARM_SL vs time_order) ===")
    log.info("%-10s %10s %12s %12s %10s", "tag", "n_SL", "n_prearm_log", "n_hold<TSH",
             "n_timestop")
    for t in ARMS:
        d = dd[t]
        sl = d[d.status == "STOP_LOSS_DONE"]
        nlog = len(prearm_log(t))
        short = int((pd.to_numeric(sl.time_order, errors="coerce") < TSH[t]).sum())
        log.info("%-10s %10d %12d %12d %10d", t, len(sl), nlog, short, len(sl) - short)
    log.info("  (truc T: n_prearm_log = 0 la DUNG; n_hold<TSH > 0 nghia la co lenh dong "
             "vi ly do khac time-stop dung han)")


def equity_table():
    log.info("")
    log.info("=== EQUITY / CAGR — KHONG PHAI TIEU CHI (N=6 => 2.57*sqrt(2 ln 6) = 4.9pp) ===")
    log.info("%-10s %10s %8s %9s %6s", "tag", "equity", "CAGR%", "maxDD%", "UW")
    for t in TAGS:
        s = C.equity(t)
        dd = (s / s.cummax() - 1) * 100
        uw = s < s.cummax()
        years = (s.index[-1] - s.index[0]).days / 365.25
        cagr = ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100
        log.info("%-10s %10.0f %8.2f %9.2f %6d", t, s.iloc[-1], cagr, dd.min(),
                 int(uw.groupby((~uw).cumsum()).sum().max()))


def main():
    tags = sys.argv[1:] or TAGS
    dd = {t: trades2(t) for t in tags}
    main_table(dd)
    year_table(dd)
    ci_all(dd)
    hard_by_year()
    cost_of_sl(dd)
    equity_table()


if __name__ == "__main__":
    main()
