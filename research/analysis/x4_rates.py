"""X4 - cham diem 10 run: quet 4 hang so trailing (G/W/R/H) + truc U tren jar SACH.

Xem docs/PREREG_X4.md muc 4-6. Dung lai may bootstrap khoi-72h x1.21 cua c3_rates.
Khac x3_rates.py:
  - khong doc log SELRANK (khong sua engine trong dot nay); nhanh STRONG/WEAK duoc SUY
    CHINH XAC tu printDone.csv: STRONG <=> symbolPred_leg1 <= thr CUA CHINH ARM DO
    (null -> WEAK), dung dung boolean ma OrderTargetInfoTest.trailRate() tinh.
  - bang don dieu theo TUNG TRUC + phan quyet theo PREREG_X4 muc 6.
  - cong C4: n STOP_LOSS_DONE phai BAT BIEN qua moi arm.

Usage: python3 x4_rates.py            (mac dinh 10 tag cua X4)
"""
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

PARITY = "X4_PARITY"
AXES = {                       # truc -> [(tag, muc)] theo thu tu TANG cua muc
    "G  SIM_TS_MAX_GAP":       [("X4_G05", 0.05), (PARITY, 0.08), ("X4_G12", 0.12)],
    "W  SIM_TS_MAX_GAP_WEAK":  [("X4_W015", 0.015), (PARITY, 0.03), ("X4_W05", 0.05)],
    "R  TS_GIVEBACK_RATIO":    [("X4_R03", 0.3), (PARITY, 0.5), ("X4_R07", 0.7)],
    "H  SIM_TS_PNOPUMP_THR":   [("X4_H20", 0.20), (PARITY, 0.29), ("X4_H40", 0.40)],
}
ARMS = ["X4_G05", "X4_G12", "X4_W015", "X4_W05",
        "X4_R03", "X4_R07", "X4_H20", "X4_H40", "X4_U05"]
TAGS = [PARITY] + ARMS
# ban le hieu dung cua tung arm (de suy nhanh STRONG/WEAK dung nhu engine)
THR = {t: 0.29 for t in TAGS}
THR["X4_H20"], THR["X4_H40"] = 0.20, 0.40
# (cap_strong, cap_weak, giveback_ratio) hieu dung - chi de in ra cho doc de
CFG = {t: (0.08, 0.03, 0.5) for t in TAGS}
CFG["X4_G05"] = (0.05, 0.03, 0.5)
CFG["X4_G12"] = (0.12, 0.03, 0.5)
CFG["X4_W015"] = (0.08, 0.015, 0.5)
CFG["X4_W05"] = (0.08, 0.05, 0.5)
CFG["X4_R03"] = (0.08, 0.03, 0.3)
CFG["X4_R07"] = (0.08, 0.03, 0.7)
CFG["X4_U05"] = (0.05, 0.05, 0.5)

KEYS4 = ("n", "win", "tsloss", "mp_sm", "mp_sl", "meanP", "margin",
         "p10sm", "p25sm", "medsm", "p75sm", "p90sm", "p10loss")
LBL = {"n": "n", "win": "win%", "tsloss": "TSloss%", "mp_sm": "mean|SM", "mp_sl": "mP|SL",
       "meanP": "meanP", "margin": "mMargin", "p10sm": "p10|SM", "p25sm": "p25|SM",
       "medsm": "med|SM", "p75sm": "p75|SM", "p90sm": "p90|SM", "p10loss": "p10loser"}
QUALITY = ("win", "tsloss", "mp_sm", "mp_sl", "meanP", "p90sm", "medsm", "p10loss")
BLK0 = pd.Timestamp("2022-01-01")
HARD_DD, HARD_Q = 15.0, -5.0
NOISE_PP = 2.57 * np.sqrt(2 * np.log(len(TAGS)))     # N=10 -> 5.5pp


def trades4(tag):
    d = C.trades(tag)
    d["blk"] = ((d.ts - BLK0) / pd.Timedelta(hours=C.BLOCK_H)).astype(int)
    return d


def rates4(d):
    r = C.rates(d)
    sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"]
    sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"]
    for k, q in (("p10sm", .10), ("p25sm", .25), ("medsm", .50), ("p75sm", .75), ("p90sm", .90)):
        r[k] = float(sm.quantile(q)) if len(sm) else float("nan")
    r["p10loss"] = float(sl.quantile(.10)) if len(sl) else float("nan")
    r["minloss"] = float(sl.min()) if len(sl) else float("nan")
    r["n_sm"] = len(sm)
    r["n_sl"] = len(sl)
    r["sumpnl_sm"] = float(d.loc[d.status == "STOP_MARKET_DONE", "pnl"].sum())
    return r


def ci_pair(da, db):
    if len(da) == 0 or len(db) == 0:
        return {k: (float("nan"),) * 3 + (False,) for k in KEYS4}
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(C.SEED)
    ra0, rb0 = rates4(da), rates4(db)
    obs = {k: ra0[k] - rb0[k] for k in KEYS4}
    draws = {k: [] for k in KEYS4}
    for _ in range(C.NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        la = [ga[b] for b in pick if b in ga]
        lb = [gb[b] for b in pick if b in gb]
        ra = rates4(pd.concat(la) if la else da.iloc[:0])
        rb = rates4(pd.concat(lb) if lb else db.iloc[:0])
        for k in KEYS4:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in KEYS4:
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
    log.info("%-10s %5s %5s %5s %5s %6s %7s %6s %9s %9s %9s %9s", "tag", "capS", "capW",
             "rat", "thr", "n", "win%", "TSl%", "mean|SM", "mP|SL", "meanP", "sumPnl|SM")
    for t in TAGS:
        r = rates4(dd[t]); s, w, g = CFG[t]
        log.info("%-10s %5.3f %5.3f %5.2f %5.2f %6.0f %7.2f %6.2f %9.3f %9.3f %9.3f %9.0f",
                 t, s, w, g, THR[t], r["n"], r["win"], r["tsloss"], r["mp_sm"],
                 r["mp_sl"], r["meanP"], r["sumpnl_sm"])
    log.info("")
    log.info("=== PHAN BO WINNER `profit | STOP_MARKET_DONE` (muc tieu that cua X4) ===")
    log.info("%-10s %6s %8s %8s %8s %8s %8s %8s", "tag", "n_SM",
             "p10", "p25", "med", "p75", "p90", "mean")
    for t in TAGS:
        r = rates4(dd[t])
        log.info("%-10s %6d %8.3f %8.3f %8.3f %8.3f %8.3f %8.3f", t, r["n_sm"],
                 r["p10sm"], r["p25sm"], r["medsm"], r["p75sm"], r["p90sm"], r["mp_sm"])


def c4_gate(dd):
    log.info("")
    log.info("=== CONG C4 - n STOP_LOSS_DONE PHAI BAT BIEN (trailing chi tac dong SAU arm) ===")
    base = rates4(dd[PARITY])["n_sl"]
    ok = True
    log.info("%-10s %8s %8s %8s", "tag", "n_SL", "TSloss%", "== parity?")
    for t in TAGS:
        r = rates4(dd[t]); good = (r["n_sl"] == base); ok &= good
        log.info("%-10s %8d %8.2f %8s", t, r["n_sl"], r["tsloss"], "OK" if good else "**KHAC**")
    log.info("  => C4 %s (base n_SL=%d)", "PASS" if ok else "**FAIL - DUNG VA TIM BUG**", base)
    return ok


def c4_deep(dd):
    """C4 sau hon: ghep (sym,start) voi PARITY de tach 'doi TRANG THAI' khoi 'doi TAP LENH'.

    Trailing chi tac dong SAU arm => KHONG duoc bien mot lenh SM thanh SL (hay nguoc lai) tren
    CUNG mot (sym,start). Neu n_SL lech ma so chuyen trang thai = 0 thi lech do den tu TAP LENH
    (thoat som/muon doi thoi diem giai phong margin => lenh vao sau khac), khong phai tu trailing
    cham nhanh pre-arm.
    """
    log.info("")
    log.info("=== C4-DEEP: ghep (sym,start) voi PARITY - chuyen trang thai vs doi tap lenh ===")
    pk = dd[PARITY][dd[PARITY].leg == 0].drop_duplicates(subset=["sym", "start"]).set_index(
        ["sym", "start"])["status"]
    log.info("%-10s %7s %8s %8s %9s %9s %9s %9s", "tag", "n_SL", "ghep%", "chung",
             "SM->SL", "SL->SM", "moi", "mat")
    for t in TAGS:
        d = dd[t][dd[t].leg == 0].drop_duplicates(subset=["sym", "start"]).set_index(
            ["sym", "start"])["status"]
        common = d.index.intersection(pk.index)
        a, b = d.loc[common], pk.loc[common]
        sm2sl = int(((b == "STOP_MARKET_DONE") & (a == "STOP_LOSS_DONE")).sum())
        sl2sm = int(((b == "STOP_LOSS_DONE") & (a == "STOP_MARKET_DONE")).sum())
        log.info("%-10s %7d %7.1f%% %8d %9d %9d %9d %9d", t,
                 int((d == "STOP_LOSS_DONE").sum()), 100.0 * len(common) / len(d), len(common),
                 sm2sl, sl2sm, len(d) - len(common), len(pk) - len(common))
    log.info("  => SM->SL = SL->SM = 0 o moi arm => C4 dat VE CHAT: trailing khong cham pha truoc arm")


def branch_table(dd):
    log.info("")
    log.info("=== NHANH TRAILING STRONG/WEAK (ban le CUA CHINH ARM; null -> WEAK) ===")
    log.info("%-10s %5s %7s %7s %8s %11s %11s %11s %11s", "tag", "thr", "nSTRONG", "nWEAK",
             "STRONG%", "mP_STRONG", "mP_WEAK", "mSM_STRONG", "mSM_WEAK")
    for t in TAGS:
        d = dd[t][dd[t].leg == 0]
        thr = THR[t]
        strong = d[d.symbolPred.notna() & (d.symbolPred <= thr)]
        weak = d[d.symbolPred.isna() | (d.symbolPred > thr)]
        f = lambda g: g.loc[g.status == "STOP_MARKET_DONE", "profit"]
        note = "  (ban le VO HIEU: capS==capW)" if CFG[t][0] == CFG[t][1] else ""
        log.info("%-10s %5.2f %7d %7d %7.1f%% %11.3f %11.3f %11.3f %11.3f%s",
                 t, thr, len(strong), len(weak),
                 100.0 * len(strong) / len(d) if len(d) else float("nan"),
                 strong.profit.mean() if len(strong) else float("nan"),
                 weak.profit.mean() if len(weak) else float("nan"),
                 f(strong).mean() if len(f(strong)) else float("nan"),
                 f(weak).mean() if len(f(weak)) else float("nan"), note)


def year_table(dd):
    log.info("")
    log.info("=== RATE THEO NAM ===")
    log.info("%-10s %5s %5s %6s %7s %8s %8s %8s %9s", "tag", "nam", "n", "win%",
             "TSloss%", "mean|SM", "med|SM", "p90|SM", "mP|SL")
    for t in TAGS:
        for y, g in dd[t].groupby(dd[t].ts.dt.year):
            r = rates4(g)
            log.info("%-10s %5d %5d %6.2f %7.2f %8.3f %8.3f %8.3f %9.3f", t, y, int(r["n"]),
                     r["win"], r["tsloss"], r["mp_sm"], r["medsm"], r["p90sm"], r["mp_sl"])


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
            for k in KEYS4:
                o, lo, hi, o2 = r[k]
                log.info("%-9s %10.3f %11.3f %11.3f %8s", LBL[k], o, lo, hi, "YES" if o2 else "-")
            log.info("  => rate CHAT LUONG ngoai CI: %d", nout)
    return res


def hard_by_year():
    log.info("")
    log.info("=== RANG BUOC CUNG THEO NAM (R1 maxDD<=%.0f%%, R2 khong nam am, R3 quy>=%.0f%%) ===",
             HARD_DD, HARD_Q)
    log.info("    UW ghi lam CHI BAO, KHONG loai arm (PREREG_X4 muc 0.4 / X3 muc 6.1)")
    rows, verdict = {}, {}
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
    log.info("%-10s %5s %9s %6s %9s %9s %6s", "tag", "nam", "maxDD%", "UW",
             "ret_nam%", "quy_min%", "PASS")
    for t in TAGS:
        allok = True
        for y in sorted(rows[t]):
            mdd, uwmax, ry, qmin = rows[t][y]
            ok = (mdd >= -HARD_DD) and (ry >= 0) and (qmin >= HARD_Q)
            allok &= ok
            log.info("%-10s %5d %9.2f %6d %9.2f %9.2f %6s", t, y, mdd, uwmax, ry, qmin,
                     "PASS" if ok else "**FAIL**")
        verdict[t] = allok
    log.info("  => PASS R1-R3: %s", {t: ("PASS" if v else "FAIL") for t, v in verdict.items()})
    return verdict, rows


def axis_verdict(dd, ci, hard):
    log.info("")
    log.info("=== PHAN QUYET TUNG TRUC (PREREG_X4 muc 6) ===")
    r = {t: rates4(dd[t]) for t in TAGS}
    chosen = {}
    for name, lv in AXES.items():
        ms = [r[t]["mp_sm"] for t, _ in lv]
        up = all(ms[i] < ms[i + 1] for i in range(len(ms) - 1))
        dn = all(ms[i] > ms[i + 1] for i in range(len(ms) - 1))
        mono = up or dn
        log.info("")
        log.info("--- TRUC %s ---", name)
        log.info("  muc      : %s", [x for _, x in lv])
        log.info("  mean|SM  : %s -> don dieu: %s", [round(x, 3) for x in ms],
                 "TANG" if up else ("GIAM" if dn else "KHONG"))
        log.info("  med|SM   : %s", [round(r[t]["medsm"], 3) for t, _ in lv])
        log.info("  p90|SM   : %s", [round(r[t]["p90sm"], 3) for t, _ in lv])
        log.info("  win%%     : %s", [round(r[t]["win"], 3) for t, _ in lv])
        if not mono:
            log.info("  (1) don dieu: KHONG => GIU BASE cho truc nay")
            chosen[name] = PARITY
            continue
        best, bestv = PARITY, r[PARITY]["mp_sm"]
        for t, x in lv:
            if t == PARITY:
                continue
            w = ci[(t, None)]["win"]
            winok = not (w[3] and w[0] < 0)
            if r[t]["mp_sm"] > bestv and winok and hard[t]:
                best, bestv = t, r[t]["mp_sm"]
            log.info("  ung vien %s (muc %s): mean|SM %.3f | win%% hieu %+.3f ngoaiCI=%s | R1-R3 %s",
                     t, x, r[t]["mp_sm"], w[0], "YES" if w[3] else "-",
                     "PASS" if hard[t] else "FAIL")
        log.info("  (1) don dieu: CO. (2)+(3) => CHON: %s", best)
        chosen[name] = best
    t = "X4_U05"
    o, lo, hi, out = ci[(t, None)]["mp_sm"]
    log.info("")
    log.info("--- TRUC U (mot cap duy nhat 0.05, ban le vo hieu) ---")
    log.info("  mean|SM  U=%.3f vs base=%.3f | hieu %+.3f CI[%.3f,%.3f] ngoaiCI=%s",
             r[t]["mp_sm"], r[PARITY]["mp_sm"], o, lo, hi, "YES" if out else "-")
    log.info("  R1-R3: %s | rate CL ngoai CI: %d", "PASS" if hard[t] else "FAIL",
             sum(int(ci[(t, None)][k][3]) for k in QUALITY))
    log.info("  => %s", "ban le 0.29 VO DUNG -> khuyen nghi U (don gian thang khi hoa)"
             if (not out and hard[t]) else "U KHAC base hoac FAIL rang buoc -> khong khuyen nghi")
    nchg = sum(1 for v in chosen.values() if v != PARITY)
    log.info("")
    log.info("=== CAU HINH CHOT: %d truc doi ===", nchg)
    for k, v in chosen.items():
        log.info("  %-26s -> %s%s", k, v, "  (BASE)" if v == PARITY else "  **DOI**")
    if nchg >= 2:
        log.info("  >= 2 truc doi => PHAI chay X4_COMBO (run 11, da dang ky PREREG_X4 muc 6.4)")
    elif nchg == 0:
        log.info("  => TRAILING DONG, BASE GIU")
    return chosen


def equity_table():
    log.info("")
    log.info("=== EQUITY / CAGR - KHONG PHAI TIEU CHI (N=%d => 2.57*sqrt(2 ln N) = %.1fpp) ===",
             len(TAGS), NOISE_PP)
    log.info("%-10s %10s %8s %9s %6s", "tag", "equity", "CAGR%", "maxDD%", "UW")
    for t in TAGS:
        s = C.equity(t)
        ddv = (s / s.cummax() - 1) * 100
        uw = s < s.cummax()
        years = (s.index[-1] - s.index[0]).days / 365.25
        cagr = ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100
        log.info("%-10s %10.0f %8.2f %9.2f %6d", t, s.iloc[-1], cagr, ddv.min(),
                 int(uw.groupby((~uw).cumsum()).sum().max()))


def main():
    dd = {t: trades4(t) for t in TAGS}
    main_table(dd)
    c4_gate(dd)
    c4_deep(dd)
    branch_table(dd)
    year_table(dd)
    ci = ci_all(dd)
    hard, _ = hard_by_year()
    axis_verdict(dd, ci, hard)
    equity_table()


if __name__ == "__main__":
    main()
