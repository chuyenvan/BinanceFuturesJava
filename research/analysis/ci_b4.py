"""B4 — CI cua HIEU CAGR giua 3 bien the rolling-percentile gate va C2b.

Phuong phap chot TRUOC o docs/PREREG_B4.md (commit a0c7ad6), muc 3/4/5:
  - equity = b+unP (mark-to-market), y het qret.py
  - block-bootstrap GHEP CAP, moving-block circular, block chinh 21 ngay (kiem 10 va 42),
    2000 rep, seed 20260903  (docs/PREREG_CI.md 2.1-2.4)
  - TIEU CHI CHINH: d = CAGR(RG) - CAGR(C2b) DAT khi d > 1.48*sd_boot, 1.48 = sqrt(2 ln 3)
  - RANG BUOC CUNG: maxDD >= -15.12%, tang equity, KHONG bootstrap (PREREG_CI 2.5)
  - TIEU CHI PHU: cat theo ngay, bear 2022-01-01..2022-12-31 vs hoi phuc 2023-01-01..2023-12-31
"""
import logging, re, sys
import numpy as np, pandas as pd

OUT = "/home/ubuntu/java/stage/ci_b4.out"
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler(OUT, "w"), logging.StreamHandler()])
L = logging.getLogger("ciB4")

B = "/home/ubuntu/java/devrun"
SEED = 20260903
NREP = 2000
BLOCKS = [21, 10, 42]
CAP0 = 35000.0
KMULT = np.sqrt(2.0 * np.log(3.0))     # = 1.4823 — hieu chinh so sanh boi cho 3 bien the
DD_FLOOR = -15.12                      # rang buoc cung (%), maxDD phai >= moc nay
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")

BASE = "C2b"
VAR = ["B4_RG95", "B4_RG97", "B4_RG95W180"]
REGIMES = [("BEAR 2022", "2022-01-01", "2022-12-31"),
           ("HOI PHUC 2023", "2023-01-01", "2023-12-31")]


def eq(tag):
    """Y het qret.py: equity = b+unP, giu ban ghi cuoi cung trong ngay."""
    rows = []
    for line in open(f"{B}/{tag}/logs/sim.out", errors="ignore"):
        m = RX.search(line)
        if m:
            rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


def maxdd(s):
    """maxDD % QUAN SAT tren duong equity ngay — y het qret.py:19. KHONG bootstrap."""
    return float(((s / s.cummax() - 1) * 100).min())


def underwater(s):
    uw = (s < s.cummax())
    return int(uw.groupby((~uw).cumsum()).sum().max())


def idxmat(n, blen, nrep, seed):
    """moving-block circular; nb block ghep lai roi cat con dung n (PREREG_CI 2.3)."""
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    off = np.arange(blen)
    ix = (starts[:, :, None] + off[None, None, :]) % n
    return ix.reshape(nrep, nb * blen)[:, :n]


TAGS = [BASE] + VAR
E = {t: eq(t) for t in TAGS}
try:
    E["B4_OFF"] = eq("B4_OFF")
except Exception as ex:
    L.info("khong doc duoc B4_OFF: %s", ex)

idx0 = E[BASE].index
for t in TAGS:
    if not E[t].index.equals(idx0):
        L.info("*** LICH NGAY KHAC NHAU: %s (%d ngay) vs %s (%d ngay) -> DUNG",
               t, len(E[t]), BASE, len(idx0))
        sys.exit(2)
N = len(idx0)
L.info("n ngay=%d (%.4f nam) %s .. %s", N, N / 365.0, idx0[0].date(), idx0[-1].date())

L.info("\n=== 0. VOID CHECK cong nghiem thu: B4_OFF vs C2b ===")
if "B4_OFF" in E:
    same = bool(np.array_equal(E["B4_OFF"].values, E[BASE].values))
    L.info("  chuoi equity ngay B4_OFF giong het C2b: %s (equity cuoi %d vs %d)",
           same, int(E["B4_OFF"].iloc[-1]), int(E[BASE].iloc[-1]))

# log(1+r) theo ngay; r_1 = E_1/CAPITAL_START - 1 (PREREG_CI 2.1)
LR = {}
for t in TAGS:
    v = np.concatenate([[CAP0], E[t].values.astype(float)])
    assert (v > 0).all(), t
    LR[t] = np.diff(np.log(v))


def cagr_of(lr, n):
    return np.exp(lr.sum() * 365.0 / n) - 1.0


L.info("\n=== 1. DIEM UOC LUONG tren DEV (911 ngay) + RANG BUOC CUNG maxDD >= %.2f%% ===", DD_FLOOR)
L.info("%-14s %9s %8s %8s %9s %6s", "run", "eq_cuoi", "CAGR%", "maxDD%", "underwater", "cung?")
stat = {}
for t in TAGS:
    c = cagr_of(LR[t], N) * 100
    dd = maxdd(E[t])
    ok = dd >= DD_FLOOR
    stat[t] = dict(eq=int(E[t].iloc[-1]), cagr=c, dd=dd, uw=underwater(E[t]), hard_ok=ok)
    L.info("%-14s %9d %+8.2f %8.2f %6d ngay %6s", t, stat[t]["eq"], c, dd, stat[t]["uw"],
           "DAT" if ok else "VI PHAM")

L.info("\n=== 2. TIEU CHI CHINH: d = CAGR(RG) - CAGR(C2b), nguong %.4f * sd_boot (block 21) ===", KMULT)
IX = {b: idxmat(N, b, NREP, SEED) for b in BLOCKS}
res = {}
for t in VAR:
    row = {}
    for b in BLOCKS:
        ix = IX[b]
        da = np.exp(LR[t][ix].sum(axis=1) * 365.0 / N) - np.exp(LR[BASE][ix].sum(axis=1) * 365.0 / N)
        row[b] = (float(np.percentile(da, 2.5)), float(np.percentile(da, 97.5)),
                  float(da.std(ddof=1)), float((da > 0).mean()))
    res[t] = row

L.info("%-14s %9s %9s %9s %9s %8s %6s", "run", "d(pp)", "lo95_21", "hi95_21", "sd_21", "P(d>0)", "n_eff")
for t in VAR:
    d = (cagr_of(LR[t], N) - cagr_of(LR[BASE], N)) * 100
    lo, hi, sd, p = res[t][21]
    L.info("%-14s %+9.3f %+9.3f %+9.3f %9.3f %8.3f %6d", t, d, lo * 100, hi * 100, sd * 100, p,
           int(np.ceil(N / 21)))


L.info("\n--- CI95 cua d o ca 3 do dai block (block 21 la CHINH) ---")
L.info("%-14s %4s %+9s %+9s %9s", "run", "L", "lo95", "hi95", "sd")
for t in VAR:
    for b in BLOCKS:
        lo, hi, sd, p = res[t][b]
        L.info("%-14s %4d %+9.3f %+9.3f %9.3f", t, b, lo * 100, hi * 100, sd * 100)

L.info("\n--- PHAN QUYET theo PREREG_B4 muc 3 + 4 ---")
verdict = {}
for t in VAR:
    d = (cagr_of(LR[t], N) - cagr_of(LR[BASE], N)) * 100
    sd = res[t][21][2] * 100
    thr = KMULT * sd
    pass_main = d > thr
    hard = stat[t]["hard_ok"]
    excl = ["Y" if not (res[t][b][0] <= 0 <= res[t][b][1]) else "n" for b in BLOCKS]
    cls = "KHONG PHAN BIET DUOC" if "n" in excl else ("SONG" if d > 0 else "DAO CHIEU")
    verdict[t] = dict(d=d, sd=sd, thr=thr, pass_main=pass_main, hard=hard, cls=cls,
                      excl="".join(excl))
    L.info("%-14s d=%+.3fpp  sd_boot=%.3fpp  nguong=+%.3fpp  -> tieu chi chinh %s | rang buoc cung %s | loai_tru0=%s -> %s",
           t, d, sd, thr, "DAT" if pass_main else "KHONG DAT",
           "DAT" if hard else "VI PHAM", verdict[t]["excl"], cls)

n_hard_ok = sum(1 for t in VAR if verdict[t]["hard"])
n_win = sum(1 for t in VAR if verdict[t]["hard"] and verdict[t]["pass_main"])
if n_win >= 1:
    doc = "(a) co >=1 bien the dat CA rang buoc cung VA d > 1.48*sd_boot -> B4 GIU MO, de nghi L3"
elif n_hard_ok == 0:
    doc = "(c) khong bien the nao dat rang buoc cung maxDD -> DONG B4 bang RANG BUOC CUNG"
else:
    doc = "(b) dat rang buoc cung nhung khong vuot nguong -> KHONG PHAN BIET DUOC bang DEV -> DONG B4"
L.info("\n*** CACH DOC (PREREG_B4 muc 7): %s ***", doc)
L.info("    (bien the dat rang buoc cung: %d/3; bien the vuot nguong: %d/3)", n_hard_ok, n_win)


L.info("\n=== 3. TIEU CHI PHU (PREREG_B4 muc 5) — cat theo NGAY, chot TRUOC. KHONG dung de tuyen bo thang. ===")
for name, d0, d1 in REGIMES:
    m = (idx0 >= pd.Timestamp(d0)) & (idx0 <= pd.Timestamp(d1))
    ns = int(m.sum())
    L.info("\n--- %s (%s..%s, %d ngay, n_eff = %d khoi 21 ngay) ---", name, d0, d1, ns,
           int(np.ceil(ns / 21)))
    ixs = idxmat(ns, 21, NREP, SEED)
    lrb = LR[BASE][m]
    sb = E[BASE][m]
    L.info("  %-14s %8s %8s", "run", "CAGR%", "maxDD%")
    L.info("  %-14s %+8.2f %8.2f", BASE, cagr_of(lrb, ns) * 100, maxdd(sb))
    for t in VAR:
        lrt = LR[t][m]
        L.info("  %-14s %+8.2f %8.2f", t, cagr_of(lrt, ns) * 100, maxdd(E[t][m]))
    L.info("  %-14s %9s %9s %9s %8s", "hieu vs C2b", "d(pp)", "lo95", "hi95", "P(d>0)")
    for t in VAR:
        lrt = LR[t][m]
        da = np.exp(lrt[ixs].sum(axis=1) * 365.0 / ns) - np.exp(lrb[ixs].sum(axis=1) * 365.0 / ns)
        dpt = (cagr_of(lrt, ns) - cagr_of(lrb, ns)) * 100
        L.info("  %-14s %+9.3f %+9.3f %+9.3f %8.3f", t, dpt,
               np.percentile(da, 2.5) * 100, np.percentile(da, 97.5) * 100, (da > 0).mean())

L.info("\n=== 4. SANITY: tai lap so cu ===")
L.info("  C2b eq_cuoi=%d (cho doi 60390) CAGR=%+.2f%% (cho doi +24.43) maxDD=%.2f%% (cho doi -13.12)",
       stat[BASE]["eq"], stat[BASE]["cagr"], stat[BASE]["dd"])
L.info("  run cu 2026-09-03 (code truoc refactor): RG95 56683 / RG97 52045 / RG95w180 59120;"
       " maxDD -12.88 / -12.33 / -13.12")
L.info("\nket qua day du: %s", OUT)
