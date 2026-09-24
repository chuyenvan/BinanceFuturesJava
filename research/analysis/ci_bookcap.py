"""BOOKCAP — CI cua HIEU CAGR giua 3 bien the cap book va PARITY_R (docs/prereg/PREREG_BOOKCAP.md muc 3).

Tai su dung y het khuon research/analysis/ci_gatedyn.py (da dung cho GATEDYN), chi doi:
  - k = 3 bien the khoa truoc (CAP12 / CAP16 / NOT40) => KMULT = sqrt(2 ln 3) = 1.4823
  - VAR mac dinh = 3 tag BOOKCAP, OUT = /home/ubuntu/x1log/ci_bookcap.out
Giu nguyen: equity = b+unP (mark-to-market) doc tu logs/sim.out, giu ban ghi cuoi cung trong ngay;
block-bootstrap GHEP CAP, moving-block circular, block chinh 21 ngay (kiem 10 va 42), 2000 rep,
seed 20260903; maxDD / underwater = so QUAN SAT, KHONG bootstrap (PREREG_CI 2.5).

**CHI BAO CAO** — theo PREREG_BOOKCAP muc 3/4, d CAGR KHONG doi duoc phan quyet du dau nao.
"""
import logging, re, sys
import numpy as np, pandas as pd

OUT = "/home/ubuntu/x1log/ci_bookcap.out"
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(OUT, "w"), logging.StreamHandler()])
L = logging.getLogger("ciBC")

B = "/home/ubuntu/java/devrun"
SEED, NREP, BLOCKS, CAP0 = 20260903, 2000, [21, 10, 42], 35000.0
KVAR = 3
KMULT = np.sqrt(2.0 * np.log(float(KVAR)))
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")

BASE = "X1_C3_FULL_PARITY_R"
VAR = [t for t in sys.argv[1:]] or ["X1_C3_FULL_CAP12", "X1_C3_FULL_CAP16", "X1_C3_FULL_NOT40"]
YEARS = [("2022", "2022-01-01", "2022-12-31"), ("2023", "2023-01-01", "2023-12-31"),
         ("2024", "2024-01-01", "2024-12-31"), ("2025", "2025-01-01", "2025-12-31")]


def eq(tag):
    rows = []
    for line in open(f"{B}/{tag}/logs/sim.out", errors="ignore"):
        m = RX.search(line)
        if m:
            rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


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
E = {t: eq(t) for t in TAGS}
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
L.info("%-22s %9s %8s %8s %6s", "run", "eq_cuoi", "CAGR%", "maxDD%", "UW")
for t in TAGS:
    L.info("%-22s %9d %+8.2f %8.2f %6d", t, int(E[t].iloc[-1]), cagr_of(LR[t], N) * 100,
           maxdd(E[t]), underwater(E[t]))

L.info("\n=== 2. d = CAGR(var) - CAGR(%s), TOAN CUA SO 48 thang — CHI BAO CAO ===", BASE)
L.info("nguong tham khao: d > %.4f * sd_boot (block 21, k=%d)", KMULT, KVAR)
IX = {b: idxmat(N, b, NREP, SEED) for b in BLOCKS}
L.info("%-22s %9s %9s %9s %9s %8s %10s %8s", "run", "d(pp)", "lo95", "hi95", "sd_boot",
       "P(d>0)", "nguong", "so voi nguong")
for t in VAR:
    d = (cagr_of(LR[t], N) - cagr_of(LR[BASE], N)) * 100
    ix = IX[21]
    da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
          - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
    lo, hi = np.percentile(da, [2.5, 97.5])
    sd, p = float(da.std(ddof=1)), float((da > 0).mean())
    thr = KMULT * sd
    L.info("%-22s %+9.3f %+9.3f %+9.3f %9.3f %8.3f %10.3f %8s", t, d, lo, hi, sd, p, thr,
           "vuot" if d > thr else "khong vuot")

L.info("\n=== 3. Do ben theo do dai block (block 21 CHINH) ===")
L.info("%-22s %4s %9s %9s %9s", "run", "L", "lo95", "hi95", "sd")
for t in VAR:
    for b in BLOCKS:
        ix = IX[b]
        da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
              - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
        lo, hi = np.percentile(da, [2.5, 97.5])
        L.info("%-22s %4d %+9.3f %+9.3f %9.3f", t, b, lo, hi, float(da.std(ddof=1)))

L.info("\n=== 4. d THEO TUNG NAM (bootstrap trong nam, block 21) — CHI BAO CAO ===")
L.info("%-22s %5s %5s %9s %9s %9s %9s %8s %10s %12s", "run", "nam", "nday", "d(pp)", "lo95",
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
        L.info("%-22s %5s %5d %+9.3f %+9.3f %+9.3f %9.3f %8.3f %10.3f %12s", t, name, ny, d, lo,
               hi, sd, p, thr, "vuot" if d > thr else "khong vuot")

L.info("\n=== 5. RANG BUOC CUNG THEO NAM — QUAN SAT (khong bootstrap, PREREG_CI 2.5) ===")
L.info("%-22s %5s %8s %6s %9s", "run", "nam", "maxDD%", "UW", "ret_nam%")
for t in TAGS:
    for name, a, b_ in YEARS:
        s = E[t][(idx0 >= a) & (idx0 <= b_)]
        if len(s) < 30:
            continue
        ry = (s.iloc[-1] / s.iloc[0] - 1.0) * 100
        L.info("%-22s %5s %8.2f %6d %+9.2f", t, name, maxdd(s), underwater(s), ry)

L.info("\n=== 6. maxDD THEO NAM — HIEU so voi baseline (duong = TOT hon, it am hon) ===")
L.info("%-22s %5s %9s %9s %9s", "run", "nam", "maxDD_var", "maxDD_base", "delta_pp")
for t in VAR:
    for name, a, b_ in YEARS:
        m = (idx0 >= a) & (idx0 <= b_)
        if int(m.sum()) < 30:
            continue
        dv, db = maxdd(E[t][m]), maxdd(E[BASE][m])
        L.info("%-22s %5s %9.2f %9.2f %+9.2f", t, name, dv, db, dv - db)
L.info("\nGhi chu: maxDD/UW theo nam tinh tren chuoi equity CAT trong nam (khac x1_rates.py neu"
       " tool do dung cummax toan cuoc) — doc ket hop voi bang x1_rates.py.")


# =====================================================================================
# 7. QUAN SAT THEO NAM tu printDone.csv (PREREG_BOOKCAP muc 3, gach dau dong cuoi).
#    Cach tinh book theo ngay lay y research/analysis/dev_collapse_check.py:
#    lenh "dang mo" tai ngay D <=> start <= D < end.
# =====================================================================================
def trades(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv",
                    usecols=lambda c: c and not c.startswith("Unnamed"))
    d["ts"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d.end, format="%Y%m%d %H:%M")
    d["sl"] = d.status.eq("STOP_LOSS_DONE")
    d["pnl"] = pd.to_numeric(d.pnl, errors="coerce")
    return d


def book(d):
    days = pd.date_range(d.ts.min().normalize(), d.te.max().normalize(), freq="D")
    rows = []
    for D in days:
        rows.append({"day": D, "open": int(((d.ts <= D) & (d.te > D)).sum())})
    return pd.DataFrame(rows).set_index("day")["open"]


L.info("\n=== 7. QUAN SAT THEO NAM tu printDone (collapse-day, ngay te nhat, book mo) ===")
L.info("%-22s %5s %6s %8s %10s %12s %9s %9s", "run", "nam", "n", "collapse", "pnl_ngay_te",
       "ngay_te_nhat", "open_max", "open_p90")
for t in TAGS:
    d = trades(t)
    bk = book(d)
    slday = d[d.sl].groupby(d.te.dt.normalize()).size()
    pnlday = d.groupby(d.te.dt.normalize()).pnl.sum()
    for y in (2022, 2023, 2024, 2025):
        dy = d[d.ts.dt.year == y]
        sy = slday[slday.index.year == y] if len(slday) else slday
        py = pnlday[pnlday.index.year == y] if len(pnlday) else pnlday
        by = bk[bk.index.year == y]
        ncol = int((sy >= 4).sum()) if len(sy) else 0
        worst = float(py.min()) if len(py) else float("nan")
        wday = str(py.idxmin().date()) if len(py) else "-"
        L.info("%-22s %5d %6d %8d %10.0f %12s %9d %9.1f", t, y, len(dy), ncol, worst, wday,
               int(by.max()) if len(by) else 0,
               float(by.quantile(0.9)) if len(by) else 0.0)
L.info("\nGhi chu: collapse-day = ngay co >=4 lenh dong STOP_LOSS_DONE (dinh nghia DEV_COLLAPSE_CHECK).")
L.info("pnl_ngay_te = tong pnl cua cac lenh DONG trong ngay do (khong phai equity ngay).")
