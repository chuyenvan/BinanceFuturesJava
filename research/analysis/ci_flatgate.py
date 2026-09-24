"""FLATGATE — CI cua HIEU CAGR giua X1_C3_FULL_FLATGATE va PARITY_R (docs/prereg/PREREG_FLATGATE.md 5.3).

Khuon research/analysis/ci_bookcap.py, GIU NGUYEN: equity = b+unP (mark-to-market) doc tu
logs/sim.out, ban ghi cuoi cung trong ngay; moving-block circular bootstrap, block chinh 21
ngay (kiem 10 va 42), 2000 rep, seed 20260903; maxDD / underwater = QUAN SAT, KHONG bootstrap.

KHAC ci_bookcap: k = 1 bien the khoa truoc => sqrt(2 ln 1) = 0 la nguong VO NGHIA.
=> KHONG dung nguong k-mult; bao **d CAGR + CI95 hai phia** (percentile 2.5/97.5).

**CHI BAO CAO/MO TA** — theo PREREG_FLATGATE muc 0 va 6, day khong phai ung vien adopt.
"""
import logging, re, sys
import numpy as np, pandas as pd

OUT = "/home/ubuntu/x1log/ci_flatgate.out"
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(OUT, "w"), logging.StreamHandler()])
L = logging.getLogger("ciFG")

B = "/home/ubuntu/java/devrun"
SEED, NREP, BLOCKS, CAP0 = 20260903, 2000, [21, 10, 42], 35000.0
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")

BASE = "X1_C3_FULL_PARITY_R"
VAR = [t for t in sys.argv[1:]] or ["X1_C3_FULL_FLATGATE"]
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
L.info("n ngay=%d (%.4f nam) %s .. %s | k=1 bien the khoa truoc -> dung CI95 hai phia",
       N, N / 365.0, idx0[0].date(), idx0[-1].date())

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

L.info("\n=== 2. d = CAGR(var) - CAGR(%s), TOAN CUA SO 48 thang, CI95 hai phia ===", BASE)
IX = {b: idxmat(N, b, NREP, SEED) for b in BLOCKS}
L.info("%-22s %9s %9s %9s %9s %8s %14s", "run", "d(pp)", "lo95", "hi95", "sd_boot",
       "P(d>0)", "doc CI95")
for t in VAR:
    d = (cagr_of(LR[t], N) - cagr_of(LR[BASE], N)) * 100
    ix = IX[21]
    da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
          - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
    lo, hi = np.percentile(da, [2.5, 97.5])
    sd, p = float(da.std(ddof=1)), float((da > 0).mean())
    verdict = "TE HON ro" if hi < 0 else ("TOT HON ro" if lo > 0 else "chua phan biet")
    L.info("%-22s %+9.3f %+9.3f %+9.3f %9.3f %8.3f %14s", t, d, lo, hi, sd, p, verdict)

L.info("\n=== 3. Do ben theo do dai block (block 21 CHINH) ===")
L.info("%-22s %4s %9s %9s %9s", "run", "L", "lo95", "hi95", "sd")
for t in VAR:
    for b in BLOCKS:
        ix = IX[b]
        da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
              - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
        lo, hi = np.percentile(da, [2.5, 97.5])
        L.info("%-22s %4d %+9.3f %+9.3f %9.3f", t, b, lo, hi, float(da.std(ddof=1)))

L.info("\n=== 4. d THEO TUNG NAM (bootstrap trong nam, block 21) ===")
L.info("%-22s %5s %5s %9s %9s %9s %9s %8s", "run", "nam", "nday", "d(pp)", "lo95",
       "hi95", "sd_boot", "P(d>0)")
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
        L.info("%-22s %5s %5d %+9.3f %+9.3f %+9.3f %9.3f %8.3f", t, name, ny, d, lo,
               hi, float(da.std(ddof=1)), float((da > 0).mean()))

L.info("\n=== 5. RANG BUOC CUNG THEO NAM — QUAN SAT (khong bootstrap, PREREG_CI 2.5) ===")
L.info("%-22s %5s %8s %6s %9s", "run", "nam", "maxDD%", "UW", "ret_nam%")
for t in TAGS:
    for name, a, b_ in YEARS:
        s = E[t][(idx0 >= a) & (idx0 <= b_)]
        if len(s) < 30:
            continue
        ry = (s.iloc[-1] / s.iloc[0] - 1.0) * 100
        L.info("%-22s %5s %8.2f %6d %+9.2f", t, name, maxdd(s), underwater(s), ry)


# =====================================================================================
# 6. CO HOC theo nam tu printDone.csv (PREREG_FLATGATE muc 5.4). Cach dem "dang mo" lay y
#    research/analysis/dev_collapse_check.py: lenh mo tai ngay D <=> start <= D < end.
# =====================================================================================
def trades(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip",
                    usecols=lambda c: c and not c.startswith("Unnamed"))
    d["ts"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M", errors="coerce")
    d["te"] = pd.to_datetime(d.end, format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["ts", "te"])
    d["sl"] = d.status.eq("STOP_LOSS_DONE")
    d["pnl"] = pd.to_numeric(d.pnl, errors="coerce")
    d["margin"] = pd.to_numeric(d.margin, errors="coerce")
    return d


def book(d):
    days = pd.date_range(d.ts.min().normalize(), d.te.max().normalize(), freq="D")
    op, mg = [], []
    for D in days:
        m = (d.ts <= D) & (d.te > D)
        op.append(int(m.sum()))
        mg.append(float(d.margin[m].sum()))
    return pd.DataFrame({"open": op, "margin": mg}, index=days)


L.info("\n=== 6. CO HOC theo nam tu printDone (mo ta, KHONG phai tieu chi) ===")
L.info("%-22s %5s %7s %9s %8s %9s %9s %11s %10s %12s", "run", "nam", "n", "entry/ngay",
       "collapse", "open_max", "open_p90", "von_khoa_max", "pnl_te", "ngay_te")
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
        eqy = E[t][(idx0 >= f"{y}-01-01") & (idx0 <= f"{y}-12-31")]
        nd = max(1, len(eqy))
        vk = float((by["margin"].max() / eqy.mean()) * 100) if len(by) and len(eqy) else float("nan")
        L.info("%-22s %5d %7d %9.2f %8d %9d %9.1f %10.1f%% %10.0f %12s",
               t, y, len(dy), len(dy) / nd, int((sy >= 4).sum()) if len(sy) else 0,
               int(by["open"].max()) if len(by) else 0,
               float(by["open"].quantile(0.9)) if len(by) else 0.0, vk,
               float(py.min()) if len(py) else float("nan"),
               str(py.idxmin().date()) if len(py) else "-")
L.info("\nGhi chu: collapse-day = ngay co >=4 lenh dong STOP_LOSS_DONE (DEV_COLLAPSE_CHECK).")
L.info("von_khoa_max = max(tong margin cac lenh dang mo trong ngay) / equity TB nam, %%.")
L.info("entry/ngay tinh theo so ngay CO ban ghi equity trong nam (moc 242: 17.0 entry/ngay).")
