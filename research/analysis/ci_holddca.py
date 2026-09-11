"""HOLDDCA — CI cua HIEU CAGR giua 3 bien the om-bag + DCA 1:1 va PARITY_R
(docs/PREREG_HOLDDCA.md commit 877694c, muc 3).

Tai su dung Y HET khuon research/analysis/ci_bookcap.py (da dung cho BOOKCAP/GATEDYN), chi doi:
  - VAR mac dinh = 3 tag HOLDDCA (E25/E50/E100), OUT = /home/ubuntu/x1log/ci_holddca.out
  - THEM muc 8: do cac chi so CO CHE rieng cua HOLDDCA (leg [DCA13] theo nam, % cum PST co DCA,
    vi the mo cuoi ky, von khoa TB, entries/ngay, concentration top-5%, coin het gia, MTM cuoi ky).
Giu nguyen may bootstrap: equity = b+unP (mark-to-market) doc tu logs/sim.out, giu ban ghi cuoi
cung trong ngay; block-bootstrap GHEP CAP, moving-block circular, block chinh 21 ngay (kiem 10 va
42), 2000 rep, seed 20260903; k=3 => KMULT = sqrt(2 ln 3) = 1.4823; maxDD / underwater = so QUAN
SAT, KHONG bootstrap (PREREG_CI 2.5).

Theo PREREG_HOLDDCA muc 4, PASS <=> d CAGR > 1.4823*sd_boot VA qua rang buoc cung 4 nam.
UW chi BAO CAO (quyet dinh user 11/09), KHONG la rang buoc.
"""
import logging, re, sys
import numpy as np, pandas as pd

OUT = "/home/ubuntu/x1log/ci_holddca.out"
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(OUT, "w"), logging.StreamHandler()])
L = logging.getLogger("ciHD")

B = "/home/ubuntu/java/devrun"
SEED, NREP, BLOCKS, CAP0 = 20260903, 2000, [21, 10, 42], 35000.0
KVAR = 3
KMULT = np.sqrt(2.0 * np.log(float(KVAR)))
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?m:\s*(-?\d+).*?unP:\s*(-?\d+)")
RX_DCA = re.compile(r"\[DCA13\] sym=(\S+) leg=(\d+) avg=(\S+) px=(\S+) usdt=(\S+) t=(\d{8})")

BASE = "X1_C3_FULL_PARITY_R"
VAR = [t for t in sys.argv[1:]] or ["X1_HD_E25", "X1_HD_E50", "X1_HD_E100"]
YEARS = [("2022", "2022-01-01", "2022-12-31"), ("2023", "2023-01-01", "2023-12-31"),
         ("2024", "2024-01-01", "2024-12-31"), ("2025", "2025-01-01", "2025-12-31")]


def parse_sim(tag):
    """Tra ve DataFrame theo ngay: b (realized), m (margin dang khoa), unP (unrealized)."""
    rows = []
    for line in open(f"{B}/{tag}/logs/sim.out", errors="ignore"):
        m = RX.search(line)
        if m:
            rows.append((m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4))))
    e = pd.DataFrame(rows, columns=["d", "b", "m", "unP"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d")


def maxdd(s):
    return float(((s / s.cummax() - 1) * 100).min())


def underwater(s):
    uw = (s < s.cummax())
    return int(uw.groupby((~uw).cumsum()).sum().max()) if uw.any() else 0


def idxmat(n, blen, nrep, seed):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    off = np.arange(blen)
    ix = (starts[:, :, None] + off[None, None, :]) % n
    return ix.reshape(nrep, nb * blen)[:, :n]


def cagr_of(lr, n):
    return np.exp(lr.sum() * 365.0 / n) - 1.0


TAGS = [BASE] + VAR
SIM = {t: parse_sim(t) for t in TAGS}
E = {t: (SIM[t].b + SIM[t].unP) for t in TAGS}
idx0 = E[BASE].index
for t in TAGS:
    if not E[t].index.equals(idx0):
        L.info("*** LICH NGAY KHAC: %s (%d) vs %s (%d) -> DUNG", t, len(E[t]), BASE, len(idx0))
        sys.exit(2)
N = len(idx0)
L.info("n ngay=%d (%.4f nam) %s .. %s | k=%d bien the, KMULT=%.4f",
       N, N / 365.0, idx0[0].date(), idx0[-1].date(), KVAR, KMULT)

LR = {}
for t in TAGS:
    v = np.concatenate([[CAP0], E[t].values.astype(float)])
    assert (v > 0).all(), t
    LR[t] = np.diff(np.log(v))

L.info("\n=== 1. DIEM UOC LUONG TOAN CUA SO (maxDD/UW = QUAN SAT, khong CI) ===")
L.info("equity cham diem = b + unP (mark-to-market). Cot b = realized, unP = unrealized cuoi ky.")
L.info("%-14s %10s %10s %10s %8s %8s %6s", "run", "eq(b+unP)", "b", "unP", "CAGR%", "maxDD%", "UW")
for t in TAGS:
    L.info("%-14s %10d %10d %10d %+8.2f %8.2f %6d", t, int(E[t].iloc[-1]),
           int(SIM[t].b.iloc[-1]), int(SIM[t].unP.iloc[-1]),
           cagr_of(LR[t], N) * 100, maxdd(E[t]), underwater(E[t]))

L.info("\n=== 2. d = CAGR(var) - CAGR(%s), TOAN CUA SO 48 thang ===", BASE)
L.info("PASS dieu kien (i) <=> d > %.4f * sd_boot (block 21, k=%d)", KMULT, KVAR)
IX = {b: idxmat(N, b, NREP, SEED) for b in BLOCKS}
L.info("%-14s %9s %9s %9s %9s %8s %10s %14s", "run", "d(pp)", "lo95", "hi95", "sd_boot",
       "P(d>0)", "nguong", "so voi nguong")
for t in VAR:
    d = (cagr_of(LR[t], N) - cagr_of(LR[BASE], N)) * 100
    ix = IX[21]
    da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
          - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
    lo, hi = np.percentile(da, [2.5, 97.5])
    sd, p = float(da.std(ddof=1)), float((da > 0).mean())
    thr = KMULT * sd
    L.info("%-14s %+9.3f %+9.3f %+9.3f %9.3f %8.3f %10.3f %14s", t, d, lo, hi, sd, p, thr,
           "VUOT" if d > thr else "khong vuot")

L.info("\n=== 3. Do ben theo do dai block (block 21 CHINH) ===")
L.info("%-14s %4s %9s %9s %9s", "run", "L", "lo95", "hi95", "sd")
for t in VAR:
    for b in BLOCKS:
        ix = IX[b]
        da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
              - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
        lo, hi = np.percentile(da, [2.5, 97.5])
        L.info("%-14s %4d %+9.3f %+9.3f %9.3f", t, b, lo, hi, float(da.std(ddof=1)))

L.info("\n=== 4. d THEO TUNG NAM (bootstrap trong nam, block 21) — CHI BAO CAO ===")
L.info("%-14s %5s %5s %9s %9s %9s %9s %8s %10s %12s", "run", "nam", "nday", "d(pp)", "lo95",
       "hi95", "sd_boot", "P(d>0)", "nguong", "so voi nguong")
for t in VAR:
    for name, a, b_ in YEARS:
        msk = (idx0 >= a) & (idx0 <= b_)
        ny = int(msk.sum())
        if ny < 30:
            continue
        lrv, lrb = LR[t][msk], LR[BASE][msk]
        d = (cagr_of(lrv, ny) - cagr_of(lrb, ny)) * 100
        ixy = idxmat(ny, 21, NREP, SEED)
        da = (np.exp(lrv[ixy].sum(axis=1) * 365.0 / ny)
              - np.exp(lrb[ixy].sum(axis=1) * 365.0 / ny)) * 100
        lo, hi = np.percentile(da, [2.5, 97.5])
        sd, p = float(da.std(ddof=1)), float((da > 0).mean())
        thr = KMULT * sd
        L.info("%-14s %5s %5d %+9.3f %+9.3f %+9.3f %9.3f %8.3f %10.3f %12s", t, name, ny, d, lo,
               hi, sd, p, thr, "vuot" if d > thr else "khong vuot")

# =====================================================================================
# 5. RANG BUOC CUNG THEO NAM (PREREG_HOLDDCA muc 3/4): maxDD >= -15%, ret_nam >= 0,
#    quy >= -5%. UW CHI BAO CAO — KHONG la rang buoc (quyet dinh user 11/09).
# =====================================================================================
HARD_DD, HARD_Q = -15.0, -5.0


def quarter_returns(s):
    """Loi nhuan tung quy tren chuoi equity ngay; quy dau tien so voi CAP0."""
    q = s.resample("QE").last()
    prev = pd.concat([pd.Series([CAP0], index=[q.index[0]]), q]).iloc[:-1]
    prev.index = q.index
    return (q / prev - 1.0) * 100


L.info("\n=== 5. RANG BUOC CUNG THEO NAM — QUAN SAT (khong bootstrap, PREREG_CI 2.5) ===")
L.info("nguong: maxDD >= %.0f%%, ret_nam >= 0, quy min >= %.0f%%. UW = CHI BAO CAO.",
       HARD_DD, HARD_Q)
L.info("%-14s %5s %8s %9s %9s %6s %10s", "run", "nam", "maxDD%", "ret_nam%", "quy_min%",
       "UW", "rang buoc")
HARD_OK = {}
for t in TAGS:
    qr_all = quarter_returns(E[t])
    ok_all = True
    for name, a, b_ in YEARS:
        msk = (idx0 >= a) & (idx0 <= b_)
        s = E[t][msk]
        if len(s) < 30:
            continue
        ry = (s.iloc[-1] / s.iloc[0] - 1.0) * 100
        dd = maxdd(s)
        qy = qr_all[qr_all.index.year == int(name)]
        qmin = float(qy.min()) if len(qy) else float("nan")
        ok = (dd >= HARD_DD) and (ry >= 0.0) and (qmin >= HARD_Q)
        ok_all = ok_all and ok
        L.info("%-14s %5s %8.2f %+9.2f %+9.2f %6d %10s", t, name, dd, ry, qmin,
               underwater(s), "OK" if ok else "VI PHAM")
    HARD_OK[t] = ok_all
L.info("qua het 4 nam: %s", {t: ("OK" if v else "VI PHAM") for t, v in HARD_OK.items()})

L.info("\n=== 6. maxDD THEO NAM — HIEU so voi baseline (duong = TOT hon, it am hon) ===")
L.info("%-14s %5s %9s %9s %9s", "run", "nam", "maxDD_var", "maxDD_base", "delta_pp")
for t in VAR:
    for name, a, b_ in YEARS:
        m = (idx0 >= a) & (idx0 <= b_)
        if int(m.sum()) < 30:
            continue
        dv, db = maxdd(E[t][m]), maxdd(E[BASE][m])
        L.info("%-14s %5s %9.2f %9.2f %+9.2f", t, name, dv, db, dv - db)
L.info("\nGhi chu: maxDD/UW theo nam tinh tren chuoi equity CAT trong nam.")


# =====================================================================================
# 7. QUAN SAT THEO NAM tu printDone.csv. Cach tinh book theo ngay lay y
#    research/analysis/dev_collapse_check.py: lenh "dang mo" tai ngay D <=> start <= D < end.
# =====================================================================================
def trades(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv",
                    usecols=lambda c: c and not c.startswith("Unnamed"))
    d["ts"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d.end, format="%Y%m%d %H:%M")
    d["sl"] = d.status.eq("STOP_LOSS_DONE")
    d["pnl"] = pd.to_numeric(d.pnl, errors="coerce")
    d["entry"] = pd.to_numeric(d.entry, errors="coerce")
    d["tp"] = pd.to_numeric(d.tp, errors="coerce")
    d["margin"] = pd.to_numeric(d.margin, errors="coerce")
    return d


def book(d):
    days = pd.date_range(d.ts.min().normalize(), d.te.max().normalize(), freq="D")
    return pd.Series([int(((d.ts <= D) & (d.te > D)).sum()) for D in days],
                     index=days, name="open")


TR = {t: trades(t) for t in TAGS}
BK = {t: book(TR[t]) for t in TAGS}

L.info("\n=== 7. QUAN SAT THEO NAM tu printDone (collapse-day, ngay te nhat, book mo) ===")
L.info("%-14s %5s %6s %8s %10s %12s %9s %9s", "run", "nam", "n_leg", "collapse", "pnl_ngay_te",
       "ngay_te_nhat", "open_max", "open_p90")
for t in TAGS:
    d, bk = TR[t], BK[t]
    slday = d[d.sl].groupby(d.te.dt.normalize()).size()
    pnlday = d.groupby(d.te.dt.normalize()).pnl.sum()
    for y in (2022, 2023, 2024, 2025):
        dy = d[d.ts.dt.year == y]
        sy = slday[slday.index.year == y] if len(slday) else slday
        py = pnlday[pnlday.index.year == y] if len(pnlday) else pnlday
        by = bk[bk.index.year == y]
        L.info("%-14s %5d %6d %8d %10.0f %12s %9d %9.1f", t, y, len(dy),
               int((sy >= 4).sum()) if len(sy) else 0,
               float(py.min()) if len(py) else float("nan"),
               str(py.idxmin().date()) if len(py) else "-",
               int(by.max()) if len(by) else 0,
               float(by.quantile(0.9)) if len(by) else 0.0)
L.info("\nGhi chu: collapse-day = ngay co >=4 lenh dong STOP_LOSS_DONE (DEV_COLLAPSE_CHECK).")
L.info("pnl_ngay_te = tong pnl cua cac LEG dong trong ngay do (khong phai equity ngay).")


# =====================================================================================
# 8. CO CHE HOLDDCA (PREREG muc 3, gach dau dong cuoi). Cum = nhom leg cung (sym, end):
#    closeOrder()/vong ket thuc chep CUNG timeUpdate cho moi leg cua cum nen (sym,end) la
#    khoa cum dung. Nguon cum = level cua leg co start NHO NHAT.
# =====================================================================================
def clusters(d):
    g = d.sort_values("ts").groupby(["sym", "end"], sort=False)
    c = g.agg(nleg=("sym", "size"), ts=("ts", "min"), te=("te", "max"),
              pnl=("pnl", "sum"), margin=("margin", "sum"),
              src=("level", "first"), tp=("tp", "last"),
              has_dca=("level", lambda s: bool((s == "DCA_LEVEL1").any())))
    q = d.assign(qe=d.entry * d.quantity).groupby(["sym", "end"]).agg(
        qe=("qe", "sum"), qty=("quantity", "sum"))
    c = c.join(q)
    c["avg_entry"] = c.qe / c.qty
    c["rate"] = c.tp / c.avg_entry - 1.0
    return c.reset_index()


def dca_legs(tag):
    rows = []
    for line in open(f"{B}/{tag}/logs/sim.out", errors="ignore"):
        m = RX_DCA.search(line)
        if m:
            rows.append((m.group(1), int(m.group(2)), float(m.group(5)), m.group(6)))
    if not rows:
        return pd.DataFrame(columns=["sym", "leg", "usdt", "d"])
    r = pd.DataFrame(rows, columns=["sym", "leg", "usdt", "d"])
    r["d"] = pd.to_datetime(r.d, format="%Y%m%d")
    return r


CL = {t: clusters(TR[t]) for t in TAGS}
DL = {t: dca_legs(t) for t in TAGS}
LAST_TE = {t: TR[t].te.max() for t in TAGS}

L.info("\n=== 8a. LEG DCA THEO NAM ([DCA13] trong sim.out) + cum co DCA ===")
L.info("%-14s %5s %9s %9s %9s %11s %11s", "run", "nam", "leg_dca", "usdt_TB", "n_cum",
       "n_cum_PST", "%PST co DCA")
for t in TAGS:
    dl, cl = DL[t], CL[t]
    for y in (2022, 2023, 2024, 2025):
        dy = dl[dl.d.dt.year == y] if len(dl) else dl
        cy = cl[cl.ts.dt.year == y]
        cp = cy[cy.src == "PREDICT_SYMBOL_TRADE"]
        L.info("%-14s %5d %9d %9.0f %9d %11d %11.2f", t, y, len(dy),
               float(dy.usdt.mean()) if len(dy) else 0.0, len(cy), len(cp),
               100.0 * cp.has_dca.mean() if len(cp) else 0.0)
    L.info("%-14s %5s %9d %9s %9d %11d %11.2f", t, "TONG", len(dl), "-", len(cl),
           int((cl.src == "PREDICT_SYMBOL_TRADE").sum()),
           100.0 * cl[cl.src == "PREDICT_SYMBOL_TRADE"].has_dca.mean()
           if (cl.src == "PREDICT_SYMBOL_TRADE").any() else 0.0)

L.info("\n=== 8b. VON KHOA (m: = marginRunning trong sim.out) + entries/ngay + vi the mo ===")
L.info("%-14s %5s %10s %10s %9s %11s %9s %9s", "run", "nam", "margin_TB", "margin_max",
       "%equity_TB", "entry/ngay", "open_TB", "open_cuoi")
for t in TAGS:
    sm, cl, bk = SIM[t], CL[t], BK[t]
    eq = (sm.b + sm.unP)
    for y in (2022, 2023, 2024, 2025):
        my = sm[sm.index.year == y]
        ey = eq[eq.index.year == y]
        cy = cl[cl.ts.dt.year == y]
        by = bk[bk.index.year == y]
        L.info("%-14s %5d %10.0f %10.0f %9.2f %11.2f %9.1f %9d", t, y,
               float(my.m.mean()), float(my.m.max()),
               100.0 * float((my.m / ey).mean()) if len(ey) else float("nan"),
               len(cy) / float(len(my)) if len(my) else float("nan"),
               float(by.mean()) if len(by) else 0.0, int(by.iloc[-1]) if len(by) else 0)

L.info("\n=== 8c. VI THE MO CUOI KY + MTM (cum bi dong cuoi ky: end == %s) ===", "max(end)")
L.info("%-14s %14s %8s %12s %12s %12s %10s", "run", "end_cuoi", "n_cum_mo", "margin_mo",
       "pnl_cum_mo", "b_cuoi", "eq_cuoi")
for t in TAGS:
    cl = CL[t]
    op = cl[cl.te == LAST_TE[t]]
    L.info("%-14s %14s %8d %12.0f %12.0f %12d %10d", t, str(LAST_TE[t]), len(op),
           float(op.margin.sum()), float(op.pnl.sum()),
           int(SIM[t].b.iloc[-1]), int(E[t].iloc[-1]))
L.info("Ghi chu: vi the con mo cuoi 2025-12-31 VAN nam trong printDone.csv — vong ket thuc cua")
L.info("  SimulatorMarketLevelTicker1MStopLoss gan priceTP = lastPrice roi putOrderDone (MTM theo")
L.info("  gia cuoi), NHUNG KHONG goi updatePnl => cot b: cua sim.out KHONG chua phan nay; no nam o")
L.info("  unP:. Vi vay equity cham diem = b + unP (muc 1) va pnl_cum_mo ~ unP cuoi ky.")

L.info("\n=== 8d. CONCENTRATION top-5%% cum + coin het gia (rate <= -95%%) ===")
L.info("%-14s %8s %12s %12s %11s %11s %10s", "run", "n_cum", "pnl_tong", "pnl_top5%",
       "%pnl_top5%", "n_het_gia", "%cum")
for t in TAGS:
    cl = CL[t].sort_values("pnl", ascending=False)
    k = max(1, int(np.ceil(0.05 * len(cl))))
    tot, top = float(cl.pnl.sum()), float(cl.pnl.head(k).sum())
    dead = int((cl.rate <= -0.95).sum())
    L.info("%-14s %8d %12.0f %12.0f %11.1f %11d %10.2f", t, len(cl), tot, top,
           100.0 * top / tot if tot != 0 else float("nan"), dead,
           100.0 * dead / len(cl) if len(cl) else 0.0)
L.info("Ghi chu: rate = priceTP / gia von TB cua cum - 1 (cum con mo: priceTP = gia cuoi ky).")

L.info("\n=== 9. PHAN QUYET SO BO (PREREG muc 4: PASS <=> (i) d > nguong VA (ii) 4 nam OK) ===")
for t in VAR:
    d = (cagr_of(LR[t], N) - cagr_of(LR[BASE], N)) * 100
    ix = IX[21]
    da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
          - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
    thr = KMULT * float(da.std(ddof=1))
    i_ok = d > thr
    L.info("%-14s (i) d=%+.3f vs nguong %.3f -> %s | (ii) rang buoc 4 nam -> %s | => %s",
           t, d, thr, "DAT" if i_ok else "KHONG DAT", "DAT" if HARD_OK[t] else "KHONG DAT",
           "PASS" if (i_ok and HARD_OK[t]) else "KHONG PASS")
L.info("\nUW KHONG la rang buoc trong bai nay (quyet dinh user 11/09) — xem muc 5 de doi chieu.")
