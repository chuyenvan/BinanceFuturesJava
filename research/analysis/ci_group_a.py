"""Nhom A: CI cua HIEU CAGR giua cac cap run, block-bootstrap GHEP CAP tren chuoi
loi nhuan NGAY. Phuong phap chot o docs/PREREG_CI.md (commit 2493eca)."""
import logging, os, re
import numpy as np, pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/ci/ciA.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("ciA")

B = "/home/ubuntu/java/devrun"
SEED = 20260903
NREP = 2000
BLOCKS = [21, 10, 42]
CAP0 = 35000.0
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")


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


TAGS = ["C2b", "C2b_MIN", "C2_g015", "H1a_mom006", "N4_a8s175", "RND1_2dp", "RND2_rnd",
        "map_s1a2_g1", "G1_giveback5", "H1b_rmax30", "H1c_both", "RG95", "RG97",
        "RG95w180", "BR1_margin", "BR2_both", "BR3_mg006", "K0_h1a_prof",
        "K1_conc25", "K2_conc20"]
E = {t: eq(t) for t in TAGS}
idx0 = E["C2b"].index
for t in TAGS:
    assert E[t].index.equals(idx0), t
N = len(idx0)
T_YEARS = N / 365.0
L.info("n ngay=%d  (%.4f nam)  %s .. %s", N, T_YEARS,
       idx0[0].date(), idx0[-1].date())

# loi nhuan ngay: r_1 = E_1/35000 - 1
LR = {}
for t in TAGS:
    v = np.concatenate([[CAP0], E[t].values.astype(float)])
    assert (v > 0).all(), t
    LR[t] = np.diff(np.log(v))          # log(1+r), do dai N
    cagr = np.exp(LR[t].sum() * 365.0 / N) - 1.0
    L.info("  %-14s eq_cuoi=%7d  CAGR=%+.4f%%", t, int(E[t].iloc[-1]), cagr * 100)


def idxmat(n, blen, nrep, seed):
    """moving-block circular; nb block ghep lai roi cat con dung n."""
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    off = np.arange(blen)
    ix = (starts[:, :, None] + off[None, None, :]) % n
    return ix.reshape(nrep, nb * blen)[:, :n]


def cagr_boot(t, ix):
    return np.exp(LR[t][ix].sum(axis=1) * 365.0 / N) - 1.0


PAIRS = [
    ("A1", "C2b", "C2_g015", +1, "S1 dong gop +7.35pp CAGR (bang chung C6-phay)"),
    ("A2", "C2b", "H1a_mom006", +1, "C2b hon H1a (H1a truot maxDD)"),
    ("A3", "C2b", "N4_a8s175", -1, "N4 co equity cao hon C2b (bi luat pre-reg cam chon)"),
    ("A4a", "C2b", "RND1_2dp", +1, "hang so 5 chu so KHONG load-bearing (mat 387 USDT)"),
    ("A4b", "C2b", "RND2_rnd", +1, "hang so 5 chu so KHONG load-bearing (mat 544 USDT)"),
    ("A4c", "RND1_2dp", "RND2_rnd", +1, "RND1 vs RND2"),
    ("A5", "map_s1a2_g1", "G1_giveback5", +1, "S1 thang G015 o thang arm5/scale1"),
    ("A6a", "C2b", "H1b_rmax30", +1, "H1b tham hoa (RATE_MAX 0.30 = truc chet)"),
    ("A6b", "C2b", "H1c_both", +1, "H1c tham hoa"),
    ("A6c", "C2b", "RG95", +1, "rolling-pct gate THUA tren nen C2b"),
    ("A6d", "C2b", "RG97", +1, "rolling-pct gate THUA tren nen C2b"),
    ("A6e", "C2b", "RG95w180", +1, "rolling-pct gate THUA tren nen C2b"),
    ("A6f", "C2b", "BR1_margin", +1, "breaker MARGIN khong doi gi (-118 USDT)"),
    ("A6g", "K0_h1a_prof", "BR3_mg006", +1, "breaker khong cuu duoc DD cua noi gate"),
]

L.info("\n=== VOID CHECK (giong het tung byte thi KHONG bootstrap) ===")
for a, b in [("C2b", "C2b_MIN"), ("K0_h1a_prof", "K1_conc25"),
             ("K0_h1a_prof", "K2_conc20"), ("BR1_margin", "BR2_both")]:
    same = np.array_equal(E[a].values, E[b].values)
    L.info("  %-14s vs %-12s chuoi equity ngay giong het: %s", a, b, same)

L.info("\n=== NHOM A — CI95 cua HIEU CAGR (percentile, %d rep, seed %d) ===", NREP, SEED)
L.info("%-5s %-14s %-13s %4s %9s %9s %9s %9s %8s %6s",
       "id", "A", "B", "L", "d_diem", "lo95", "hi95", "sd", "P(d>0)", "n_eff")
res = {}
for L_ in BLOCKS:
    ix = idxmat(N, L_, NREP, SEED)
    for pid, a, b, s_old, note in PAIRS:
        da = np.exp(LR[a].sum() * 365.0 / N) - np.exp(LR[b].sum() * 365.0 / N)
        d = cagr_boot(a, ix) - cagr_boot(b, ix)
        lo, hi = np.percentile(d, [2.5, 97.5])
        res[(pid, L_)] = (da, lo, hi, d.std(ddof=1), (d > 0).mean())
        L.info("%-5s %-14s %-13s %4d %+8.4f%% %+8.4f%% %+8.4f%% %8.4f%% %8.3f %6d",
               pid, a, b, L_, da * 100, lo * 100, hi * 100,
               d.std(ddof=1) * 100, (d > 0).mean(), int(np.ceil(N / L_)))

L.info("\n=== PHAN LOAI (theo PREREG_CI section 4) ===")
for pid, a, b, s_old, note in PAIRS:
    excl = [not (res[(pid, l)][1] <= 0 <= res[(pid, l)][2]) for l in BLOCKS]
    dsign = np.sign(res[(pid, BLOCKS[0])][0])
    if all(excl):
        cls = "SONG" if dsign == s_old else "DAO CHIEU"
    else:
        cls = "KHONG PHAN BIET DUOC"
    L.info("%-5s %-14s vs %-13s d=%+.3fpp  loai_tru0=%s -> %-20s | %s",
           pid, a, b, res[(pid, BLOCKS[0])][0] * 100,
           "".join("Y" if e else "n" for e in excl), cls, note)

L.info("\n=== CONG SUAT (PREREG_CI section 5): can bao nhieu ngay de phan biet 3pp ===")
for pid in ["A1", "A2", "A3", "A4b"]:
    sd = res[(pid, 21)][3]
    for pw, z in [("80%", 1.95996 + 0.84162), ("50%", 1.95996)]:
        s_can = 0.03 / z
        Tc = N * (sd / s_can) ** 2
        L.info("  %-5s sd(d)=%.4f%%  cong suat %s -> can %.0f ngay = %.2f nam (DEV co %.2f nam)",
               pid, sd * 100, pw, Tc, Tc / 365.0, T_YEARS)
