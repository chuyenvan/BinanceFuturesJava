"""AUDIT_GATEDYN — CI cua HIEU CAGR giua GD92 (rolling gate 0.92/90d) va PARITY_R (gate cung 0.008).

Khuon chot TRUOC o docs/prereg/PREREG_CI.md muc 2.1-2.5 + docs/prereg/PREREG_B4.md muc 3, tai su dung y het
research/analysis/ci_b4.py:
  - equity = b+unP (mark-to-market) doc tu logs/sim.out, giu ban ghi cuoi cung trong ngay
  - block-bootstrap GHEP CAP, moving-block circular, block chinh 21 ngay (kiem 10 va 42),
    2000 rep, seed 20260903
  - d = CAGR(GD92) - CAGR(PARITY_R); nguong DAT: d > sqrt(2 ln 9) * sd_boot = 2.0963 * sd_boot
    (hieu chinh so sanh boi k=9 bien the rolling gate da chay: GD88/92/96 + 6 run grid)
  - maxDD / underwater: so QUAN SAT, KHONG bootstrap (PREREG_CI 2.5)
"""
import logging, re, sys
import numpy as np, pandas as pd

OUT = "/home/ubuntu/x1log/ci_gatedyn.out"
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(OUT, "w"), logging.StreamHandler()])
L = logging.getLogger("ciGD")

B = "/home/ubuntu/java/devrun"
SEED, NREP, BLOCKS, CAP0 = 20260903, 2000, [21, 10, 42], 35000.0
KMULT = np.sqrt(2.0 * np.log(9.0))
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")

BASE = "X1_C3_FULL_PARITY_R"
VAR = [t for t in sys.argv[1:]] or ["X1_C3_FULL_GD92"]
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
L.info("n ngay=%d (%.4f nam) %s .. %s | k=9 bien the, KMULT=%.4f",
       N, N / 365.0, idx0[0].date(), idx0[-1].date(), KMULT)

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

L.info("\n=== 2. d = CAGR(var) - CAGR(%s), TOAN CUA SO 48 thang ===", BASE)
L.info("nguong DAT: d > %.4f * sd_boot (block 21)", KMULT)
IX = {b: idxmat(N, b, NREP, SEED) for b in BLOCKS}
L.info("%-22s %9s %9s %9s %9s %8s %10s %8s", "run", "d(pp)", "lo95", "hi95", "sd_boot",
       "P(d>0)", "nguong", "phan quyet")
for t in VAR:
    d = (cagr_of(LR[t], N) - cagr_of(LR[BASE], N)) * 100
    ix = IX[21]
    da = (np.exp(LR[t][ix].sum(axis=1) * 365.0 / N)
          - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)) * 100
    lo, hi = np.percentile(da, [2.5, 97.5])
    sd, p = float(da.std(ddof=1)), float((da > 0).mean())
    thr = KMULT * sd
    L.info("%-22s %+9.3f %+9.3f %+9.3f %9.3f %8.3f %10.3f %8s", t, d, lo, hi, sd, p, thr,
           "DAT" if d > thr else "KHONG DAT")


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
L.info("%-22s %5s %5s %9s %9s %9s %9s %8s %10s %8s", "run", "nam", "nday", "d(pp)", "lo95",
       "hi95", "sd_boot", "P(d>0)", "nguong", "phan quyet")
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
        L.info("%-22s %5s %5d %+9.3f %+9.3f %+9.3f %9.3f %8.3f %10.3f %8s", t, name, ny, d, lo,
               hi, sd, p, thr, "DAT" if d > thr else "KHONG DAT")

L.info("\n=== 5. RANG BUOC CUNG THEO NAM — QUAN SAT (khong bootstrap, PREREG_CI 2.5) ===")
L.info("%-22s %5s %8s %6s %9s", "run", "nam", "maxDD%", "UW", "ret_nam%")
for t in TAGS:
    for name, a, b_ in YEARS:
        s = E[t][(idx0 >= a) & (idx0 <= b_)]
        if len(s) < 30:
            continue
        ry = (s.iloc[-1] / s.iloc[0] - 1.0) * 100
        L.info("%-22s %5s %8.2f %6d %+9.2f", t, name, maxdd(s), underwater(s), ry)
L.info("\nGhi chu: maxDD/UW theo nam tinh tren chuoi equity CAT trong nam (khac x1_rates.py neu"
       " tool do dung cummax toan cuoc) — doc ket hop voi bang x1_rates.py.")
