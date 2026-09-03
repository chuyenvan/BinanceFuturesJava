"""Nhom A — PHAN TICH BO SUNG, **KHONG PRE-REG** (chay SAU khi da thay ket qua chinh).
Ly do: thong ke chinh (hieu CAGR) la hieu cua HAI HAM EXP => phuong sai cua no bi thoi bang
NHAN TO THI TRUONG CHUNG (resample nao thi truong tot thi ca hai CAGR lon, hieu cua hai exp
cung phong to). Thong ke ghep cap "sach" hon la hieu TOC DO TANG TRUONG LOGA theo NGAY:
   dg = 365 * mean( log(1+r_A,d) - log(1+r_B,d) )
vi tru theo TUNG NGAY nen nhan to chung bi triet tieu.
KHONG duoc dung muc nay de doi phan loai o CI_REAUDIT (phan loai theo PREREG_CI chi dung
thong ke chinh). Muc nay chi de: (a) chi ra thong ke chinh bi confound o dau,
(b) uoc luong nhu cau du lieu (iii) o san duoi lac quan hon.
Cung in maxDD/underwater QUAN SAT (khong CI — PREREG_CI section 2.5 cam bootstrap maxDD)."""
import logging, re
import numpy as np, pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/ci/ciA2.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("ciA2")
B = "/home/ubuntu/java/devrun"
SEED, NREP, BLOCKS, CAP0 = 20260903, 2000, [21, 10, 42], 35000.0
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")


def eq(tag):
    rows = []
    for line in open(f"{B}/{tag}/logs/sim.out", errors="ignore"):
        m = RX.search(line)
        if m:
            rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


TAGS = ["C2b", "C2_g015", "H1a_mom006", "N4_a8s175", "RND1_2dp", "RND2_rnd",
        "map_s1a2_g1", "G1_giveback5", "H1b_rmax30", "H1c_both", "RG95", "RG97",
        "RG95w180", "BR1_margin", "BR3_mg006", "K0_h1a_prof"]
E = {t: eq(t) for t in TAGS}
N = len(E["C2b"])
LR = {t: np.diff(np.log(np.concatenate([[CAP0], E[t].values.astype(float)]))) for t in TAGS}

L.info("=== maxDD / underwater QUAN SAT (mot lan, KHONG CO CI) ===")
for t in TAGS:
    s = E[t].astype(float)
    dd = (s / s.cummax() - 1) * 100
    uw = s < s.cummax()
    longest = uw.groupby((~uw).cumsum()).sum().max()
    L.info("  %-14s maxDD=%7.2f%%  underwater_dai_nhat=%4d ngay", t, dd.min(), int(longest))


def idxmat(n, blen, nrep, seed):
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(n / blen))
    starts = rng.integers(0, n, size=(nrep, nb))
    ix = (starts[:, :, None] + np.arange(blen)[None, None, :]) % n
    return ix.reshape(nrep, nb * blen)[:, :n]


PAIRS = [("A1", "C2b", "C2_g015"), ("A2", "C2b", "H1a_mom006"), ("A3", "C2b", "N4_a8s175"),
         ("A4a", "C2b", "RND1_2dp"), ("A4b", "C2b", "RND2_rnd"), ("A4c", "RND1_2dp", "RND2_rnd"),
         ("A5", "map_s1a2_g1", "G1_giveback5"), ("A6a", "C2b", "H1b_rmax30"),
         ("A6b", "C2b", "H1c_both"), ("A6c", "C2b", "RG95"), ("A6d", "C2b", "RG97"),
         ("A6e", "C2b", "RG95w180"), ("A6f", "C2b", "BR1_margin"),
         ("A6g", "K0_h1a_prof", "BR3_mg006")]

L.info("\n=== BO SUNG: CI95 cua HIEU TOC DO TANG TRUONG LOGA/nam (paired theo ngay) ===")
L.info("%-5s %-14s %-13s %4s %9s %9s %9s %9s %8s", "id", "A", "B", "Lb",
       "dg_diem", "lo95", "hi95", "sd", "P>0")
sd21 = {}
for Lb in BLOCKS:
    ix = idxmat(N, Lb, NREP, SEED)
    for pid, a, b in PAIRS:
        dser = LR[a] - LR[b]
        pt = dser.mean() * 365.0
        bo = dser[ix].mean(axis=1) * 365.0
        lo, hi = np.percentile(bo, [2.5, 97.5])
        if Lb == 21:
            sd21[pid] = (pt, lo, hi, bo.std(ddof=1), (bo > 0).mean())
        L.info("%-5s %-14s %-13s %4d %+8.4f%% %+8.4f%% %+8.4f%% %8.4f%% %8.3f",
               pid, a, b, Lb, pt * 100, lo * 100, hi * 100, bo.std(ddof=1) * 100,
               (bo > 0).mean())

L.info("\n=== BO SUNG: phan loai theo thong ke loga (CHI THAM KHAO, khong thay pre-reg) ===")
for pid, a, b in PAIRS:
    pt, lo, hi, sd, p = sd21[pid]
    tag = "loai tru 0" if not (lo <= 0 <= hi) else "chua 0"
    L.info("  %-5s %-14s vs %-13s dg=%+.3fpp CI[%+.3f,%+.3f] %s",
           pid, a, b, pt * 100, lo * 100, hi * 100, tag)

L.info("\n=== BO SUNG: nhu cau du lieu de phan biet 3pp (thong ke loga, block 21) ===")
for pid in ["A1", "A2", "A3", "A5", "A4b"]:
    sd = sd21[pid][3]
    for pw, z in [("80%", 2.80158), ("50%", 1.95996)]:
        Tc = N * (sd / (0.03 / z)) ** 2
        L.info("  %-5s sd(dg)=%.4f%% cong suat %s -> %.0f ngay = %.2f nam",
               pid, sd * 100, pw, Tc, Tc / 365.0)
