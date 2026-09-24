"""X1 — cham diem 2 arm tren cua so 48 thang (docs/prereg/PREREG_X1.md muc 4-7).

Dung lai may bootstrap khoi-72h x1.21 cua research/analysis/c3_rates.py (khong viet lai).
Them: bang rate THEO NAM, CI theo nam, DCA leg 2+ theo nam, rang buoc cung theo nam,
cong parity noi bo (cat toi 2024-06-30), n_eff.

Usage: python3 x1_rates.py --k <so_ung_vien> [--appetite old|current] X1_C3 X1_C3_FULL
"""
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

KEYS = C.KEYS
LBL = {"n": "n", "win": "win%", "tsloss": "TSloss%", "mp_sm": "mP|SM",
       "mp_sl": "mP|SL", "meanP": "meanP", "margin": "mMargin"}
# [TASK C 2026-09-20] Hai khau vi rui ro: 'old' = so cu (15/120/-5) de tai lap ket qua da
# cong bo truoc day; 'current' = khau vi HIEN HANH round 09-19 (TASKS_2026-09-20b muc 0.5):
# maxDD<=30, UW<=200, quy>=-15. Chon qua --appetite, mac dinh 'current'. LUU Y: rang buoc
# "tap trung 1 coin <=15% equity" KHONG duoc do trong script nay - da ghi nhan la khoang
# trong o docs/result/RESULT_VOL_TARGET.md muc 3 (can cong cu rieng).
APPETITES = {
    "old": {"dd": 15.0, "uw": 120, "q": -5.0},
    "current": {"dd": 30.0, "uw": 200, "q": -15.0},
}
APPETITE_NAME = "current"
HARD_DD, HARD_UW, HARD_Q = (APPETITES[APPETITE_NAME]["dd"], APPETITES[APPETITE_NAME]["uw"],
                             APPETITES[APPETITE_NAME]["q"])

# [CHUAN HOA 2026-09-17] he so no rong CI - dat MOT LAN o main() tu --k. None = chua dat.
F_INFLATE = None


def ci_pair_df(da, db, tag=""):
    """Block-72h paired bootstrap CI cua hieu (A-B) tren HAI BANG TRADE da loc."""
    if F_INFLATE is None:
        raise RuntimeError("F_INFLATE chua duoc dat - chay qua main() voi --k <so ung vien>.")
    if len(da) == 0 or len(db) == 0:
        return {k: (float("nan"),) * 3 + (False,) for k in KEYS}
    blocks = np.union1d(da.blk.unique(), db.blk.unique())
    ga = {k: v for k, v in da.groupby("blk")}
    gb = {k: v for k, v in db.groupby("blk")}
    rng = np.random.default_rng(C.SEED)
    obs = {k: C.rates(da)[k] - C.rates(db)[k] for k in KEYS}
    draws = {k: [] for k in KEYS}
    for _ in range(C.NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        la = [ga[b] for b in pick if b in ga]
        lb = [gb[b] for b in pick if b in gb]
        ra = C.rates(pd.concat(la) if la else da.iloc[:0])
        rb = C.rates(pd.concat(lb) if lb else db.iloc[:0])
        for k in KEYS:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in KEYS:
        arr = np.asarray(draws[k], dtype=float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            out[k] = (obs[k], float("nan"), float("nan"), False)
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        c = (lo + hi) / 2.0
        lo, hi = c - (c - lo) * F_INFLATE, c + (hi - c) * F_INFLATE
        out[k] = (obs[k], lo, hi, not (lo <= 0.0 <= hi))
    return out


def year_rate_table(tags, dd):
    log.info("")
    log.info("=== RATE THEO NAM ===")
    log.info("%-12s %5s %6s %6s %8s %8s %8s %8s %8s", "tag", "nam", "n", "win%",
             "TSloss%", "mP|SM", "mP|SL", "meanP", "mMargin")
    for t in tags:
        d = dd[t]
        for y, g in d.groupby(d.ts.dt.year):
            r = C.rates(g)
            log.info("%-12s %5d %6.0f %6.2f %8.2f %8.3f %8.3f %8.3f %8.0f",
                     t, y, r["n"], r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"],
                     r["meanP"], r["margin"])


def ci_table(a, b, dd, label, sub=None):
    da, db = dd[a], dd[b]
    if sub is not None:
        da = da[da.ts.dt.year == sub]
        db = db[db.ts.dt.year == sub]
    r = ci_pair_df(da, db)
    log.info("")
    log.info("--- CI khoi-72h x%.4f : %s - %s [%s] (n_A=%d n_B=%d)",
             F_INFLATE, a, b, label, len(da), len(db))
    log.info("%-9s %10s %11s %11s %8s", "rate", "hieu", "lo", "hi", "ngoaiCI")
    nout = 0
    for k in KEYS:
        o, lo, hi, out = r[k]
        nout += int(out and k not in ("n", "margin"))
        log.info("%-9s %10.3f %11.3f %11.3f %8s", LBL[k], o, lo, hi, "YES" if out else "-")
    log.info("  => so rate CHAT LUONG ngoai CI (bo n, mMargin): %d", nout)
    return r, nout


def dca_by_year(tags, dd):
    log.info("")
    log.info("=== DCA THEO NAM (leg>=2 = leg thu 2 tro di trong cum) ===")
    log.info("%-12s %5s %8s %8s %12s %10s", "tag", "nam", "n_leg1", "n_leg2+",
             "pnl_leg2+", "meanP_leg2+")
    for t in tags:
        d = dd[t]
        for y, g in d.groupby(d.ts.dt.year):
            g2 = g[g.leg > 0]
            log.info("%-12s %5d %8d %8d %12.1f %10.3f", t, y, int((g.leg == 0).sum()),
                     len(g2), float(g2.pnl.sum()) if len(g2) else 0.0,
                     float(g2.profit.mean()) if len(g2) else float("nan"))


def hard_by_year(tags):
    log.info("")
    log.info("=== RANG BUOC CUNG THEO NAM [appetite=%s] (maxDD<=%.0f%%, UW<=%d, nam khong am, "
             "quy>=%.0f%%; coin<=15%% KHONG do o day, xem RESULT_VOL_TARGET.md muc 3) ===",
             APPETITE_NAME, HARD_DD, HARD_UW, HARD_Q)
    log.info("%-12s %5s %9s %6s %9s %9s %6s", "tag", "nam", "maxDD%", "UW", "ret_nam%",
             "quy_min%", "PASS")
    for t in tags:
        s = C.equity(t)
        for y, sy in s.groupby(s.index.year):
            dd = (sy / sy.cummax() - 1) * 100
            uw = sy < sy.cummax()
            uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
            qe = sy.resample("QE").last()
            q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
            qr = (qe.values / q0.values - 1) * 100
            ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
            ok = (dd.min() >= -HARD_DD) and (uwmax <= HARD_UW) and (ry >= 0) and (qr.min() >= HARD_Q)
            log.info("%-12s %5d %9.2f %6d %9.2f %9.2f %6s", t, y, dd.min(), uwmax,
                     ry, qr.min(), "PASS" if ok else "**FAIL**")


def parity(tags):
    log.info("")
    log.info("=== CONG PARITY NOI BO (cat end <= 2024-06-30) ===")
    ref = {"X1_C3": ("C3_BASE", 961), "X1_C3_FULL": ("C3_FULL", 1059)}
    for t in tags:
        if t not in ref:
            continue
        rt, nref = ref[t]
        a = pd.read_csv(f"{C.B}/{t}/storage/printDone.csv", on_bad_lines="skip")
        b = pd.read_csv(f"{C.B}/{rt}/storage/printDone.csv", on_bad_lines="skip")
        ae = pd.to_datetime(a["end"], format="%Y%m%d %H:%M", errors="coerce")
        be = pd.to_datetime(b["end"], format="%Y%m%d %H:%M", errors="coerce")
        # Bien 2024-06-30: ban tham chieu chay SIM_END_DATE=20240630 nen lenh CON MO tai moc do
        # bi DONG CUONG BUC; ban X1 chay tiep den 2025-12-31 nen cung lenh do dong MUON hon.
        # => so sanh CHINH tren tap dong TRUOC 2024-06-30, va bao rieng so lenh bien.
        cut = pd.Timestamp("2024-06-30 00:00")
        nb_edge = int((be >= cut).sum())
        a1 = a[ae < cut].reset_index(drop=True)
        b1 = b[be < cut].reset_index(drop=True)
        same = len(a1) == len(b1) and a1.equals(b1)
        log.info("  %s: %d dong (end<2024-06-30) | %s: %d dong (tong %d, ky vong %d; "
                 "%d lenh bi dong cuong buc tai bien) => %s",
                 t, len(a1), rt, len(b1), len(b), nref, nb_edge,
                 "IDENTICAL" if same else "**KHAC**")
        if not same and len(a1) == len(b1):
            for c in a1.columns:
                if not a1[c].equals(b1[c]):
                    log.info("    cot lech: %s", c)
        # phu: so ca tap end<=2024-06-30 23:59 (se lech dung phan bien, ghi de doi chieu)
        a2 = a[ae <= pd.Timestamp("2024-06-30 23:59")].reset_index(drop=True)
        log.info("    (phu) end<=2024-06-30 23:59: X1=%d dong vs tham chieu=%d dong",
                 len(a2), len(b))


def n_eff(tags, dd):
    log.info("")
    # CANH BAO DON VI: 908 cua F4_TIMING la n_eff muc TICK cua tang gate (n=86,615 tick),
    # KHONG phai don vi cua rate muc lenh. Moc so sanh dung cho rate muc lenh la so khoi 72h
    # CO lenh cua ban 30 thang: C3_BASE = 89, C3_FULL = 93.
    ref = {"X1_C3": ("C3_BASE", 89), "X1_C3_FULL": ("C3_FULL", 93)}
    log.info("=== n_eff muc LENH = so khoi 72h CO it nhat 1 lenh ===")
    log.info("    (908 cua F4_TIMING la n_eff muc TICK cua tang gate — KHAC don vi, dung so sanh)")
    for t in tags:
        d = dd[t]
        ne = int(d.blk.nunique())
        if t in ref:
            rt, nr = ref[t]
            log.info("  %-12s n_eff=%d vs %s=%d  (x%.2f => CI hep lai ~x%.2f)",
                     t, ne, rt, nr, ne / nr, np.sqrt(ne / nr))
        else:
            log.info("  %-12s n_eff=%d", t, ne)


def parse_k(argv):
    """[CHUAN HOA 2026-09-17] --k BAT BUOC (docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md)."""
    if "--k" not in argv:
        raise SystemExit(
            "THIEU --k. Usage: python3 x1_rates.py --k <so ung vien> TAG_BASE TAG_VAR [...]\n"
            "  k = so UNG VIEN duoc kiem dinh so voi baseline TRONG round nay (baseline KHONG tinh).\n"
            "  k=1 -> he so 1.0 ; k>=2 -> sqrt(2 ln k). KHONG co gia tri mac dinh.\n"
            "  Xem docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md (hang so cu 1.21 ung k=2.079, da bi go).")
    i = argv.index("--k")
    if i + 1 >= len(argv):
        raise SystemExit("--k thieu gia tri.")
    k = int(argv[i + 1])
    del argv[i:i + 2]
    return k


def parse_appetite(argv):
    """--appetite {old,current}, mac dinh 'current' neu khong truyen (TASKS_2026-09-20b muc
    0.5). 'old' = 15/120/-5 (tai lap so cu). KHONG do rang buoc coin<=15% o day (xem
    docs/result/RESULT_VOL_TARGET.md muc 3)."""
    if "--appetite" not in argv:
        return "current"
    i = argv.index("--appetite")
    if i + 1 >= len(argv):
        raise SystemExit("--appetite thieu gia tri (old|current).")
    v = argv[i + 1]
    if v not in APPETITES:
        raise SystemExit("--appetite phai la 'old' hoac 'current', nhan '%s'." % v)
    del argv[i:i + 2]
    return v


def main():
    global F_INFLATE, HARD_DD, HARD_UW, HARD_Q, APPETITE_NAME
    argv = list(sys.argv[1:])
    k = parse_k(argv)
    APPETITE_NAME = parse_appetite(argv)
    ap = APPETITES[APPETITE_NAME]
    HARD_DD, HARD_UW, HARD_Q = ap["dd"], ap["uw"], ap["q"]
    F_INFLATE = C.inflate(k)
    log.info("### CI_INFLATE = sqrt(2 ln %d) = %.6f | block=%dh nrep=%d seed=%d",
             k, F_INFLATE, C.BLOCK_H, C.NREP, C.SEED)
    log.info("### k = so ung vien trong round (baseline KHONG tinh) | docs/audit/AUDIT_CI_INFLATE_STANDARDIZATION.md")
    log.info("### appetite=%s: maxDD<=%.0f%% UW<=%d quy>=%.0f%% (coin<=15%% KHONG do o day, "
             "xem RESULT_VOL_TARGET.md muc 3)", APPETITE_NAME, HARD_DD, HARD_UW, HARD_Q)
    tags = argv
    dd = {t: C.trades(t) for t in tags}
    C.report(tags)
    year_rate_table(tags, dd)
    if len(tags) >= 2:
        a, b = tags[0], tags[1]
        ci_table(b, a, dd, "TOAN CUA SO")
        for y in sorted(set(dd[a].ts.dt.year) | set(dd[b].ts.dt.year)):
            ci_table(b, a, dd, str(y), sub=y)
    dca_by_year(tags, dd)
    hard_by_year(tags)
    parity(tags)
    n_eff(tags, dd)


if __name__ == "__main__":
    main()
