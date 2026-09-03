"""NBETS buoc 5: gop Cau 4 (time-stop) va Cau 5 (kich ban MDE80)."""
import logging, sys, json
import numpy as np
sys.path.insert(0, "/home/ubuntu/nbets")
import nb_lib as N

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/nbets/step5.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("s5")
s1 = json.load(open("/home/ubuntu/nbets/step1.json"))
s2 = json.load(open("/home/ubuntu/nbets/step2.json"))
s3 = json.load(open("/home/ubuntu/nbets/step3.json"))
s4 = json.load(open("/home/ubuntu/nbets/step4.json"))
T_DEV = 911 / 365.0
GEN4 = {k: v for k, v in s2.items() if k.startswith("G4_")}


def pass_set(genkey):
    return [r["L"] for r in s2[genkey]["rows"] if r["flag"] == "PASS"]


def lvalid(l_est, genkey):
    ps = pass_set(genkey)
    for g in N.GRID:
        if g >= l_est and g in ps:
            return g
    return None


L.info("=== L_valid theo PREREG_NBETS section 3.5 (L>=L_est VA qua cong kiem phu G4) ===")
L.info("%-4s %6s %6s %6s %8s %10s %9s %9s", "ma", "L_PW", "L_VR", "L_est",
       "L_valid", "phu@Lvalid", "sd@Lvalid", "MDE80")
LV = {}
for pid in ["Q1", "Q2", "T1", "T2", "T3"]:
    p = s1["pairs"][pid]
    gk = [k for k in GEN4 if k.startswith("G4_%s(" % pid)][0]
    lv = lvalid(p["L_est"], gk)
    LV[pid] = lv
    row = [r for r in s2[gk]["rows"] if r["L"] == lv][0]
    r4 = s4["pairs"]["%s|%d" % (pid, lv)]
    L.info("%-4s %6d %6d %6d %8d %10.3f %9.4f %9.3f", pid, p["L_PW"], p["L_VR"],
           p["L_est"], lv, row["cov_dg"], r4["sd"] * 100, r4["mde"] * 100)


FAM = {"D1": [("A6_ts96", 96), ("D1_full_ts", 168), ("A6_ts336", 336)],
       "R2": [("R2_ts120", 120), ("R0_parity", 168), ("R2_ts240", 240)],
       "S": [("S3_ts168", 168), ("S4_ts720", 720)]}
L.info("\n=== CAU 4: time-stop x do dai khoi x MDE80 (chuoi DON) ===")
L.info("%-4s %-12s %5s %8s %8s %6s %6s %6s %7s %9s %9s", "ho", "run", "TS_h",
       "med_h", "p90_h", "L_PW", "L_VR", "L_est", "n_kh", "sd@Lest", "MDE80")
for fam, runs in FAM.items():
    for tag, ts in runs:
        q = s1["single"][tag]
        lest = N.snap_up(max(q["L_PW"], q["L_VR"]))
        sd = s4["single"]["%s|%d" % (tag, lest)]
        c = s3["conc"][tag]
        L.info("%-4s %-12s %5d %8.1f %8.1f %6d %6d %6d %7d %9.4f %9.3f", fam, tag, ts,
               c["med_hold_h"], c["p90_hold_h"], q["L_PW"], q["L_VR"], lest,
               int(np.ceil(911 / lest)), sd * 100, N.Z80 * sd * 100)
L.info("\n  -- cung mot do dai khoi (L=7) de so sanh sach trong ho --")
for fam, runs in FAM.items():
    vals = [(ts, s4["single"]["%s|7" % tag] * 100) for tag, ts in runs]
    md = [(ts, N.Z80 * v) for ts, v in vals]
    rng = (max(v for _, v in md) - min(v for _, v in md)) / max(v for _, v in md)
    L.info("  ho %-3s MDE80@L7: %s  giam toi da %.1f%% (nguong luat = 25%%)", fam,
           " ".join("TS%d=%.2fpp" % (t, v) for t, v in md), rng * 100)

L.info("\n=== CAU 3 tom tat: hang doc lap ngang ===")
c = s3["conc"]["C2b"]
icc = s3["icc"]["C2b|ngay"]["icc"]
L.info("  C2b: giu dong thoi mean=%.2f (med=%.0f, p90=%.0f, max=%d), mean|>=1=%.2f, "
       "flat %.1f%% gio", c["mean"], c["med"], c["p90"], c["mx"], c["mean_pos"],
       c["frac0"] * 100)
L.info("  ICC(ngay)=%.4f -> n_eff(k=%.2f)=%.2f ; n_eff(30)=%.2f ; TRAN n_eff(k->inf)"
       "=1/ICC=%.2f", icc, c["mean_pos"], s3["icc"]["C2b|ngay"]["neff_kbar"],
       s3["icc"]["C2b|ngay"]["neff_30"], 1.0 / icc)
FH = np.sqrt((1.0 / icc) / s3["icc"]["C2b|ngay"]["neff_kbar"])
L.info("  He so giam sd toi da tu chieu ngang (k hien tai -> k vo han) = %.3f", FH)


L.info("\n=== CAU 5: BANG KICH BAN. MDE80(T, hang ngang) cho cap DE NHAT (Q2 exit-param)")
sd0 = s4["pairs"]["Q2|%d" % LV["Q2"]]["sd"]
L.info("  neo: sd_dev=%.4fpp o L_valid=%d ngay, T_dev=%.4f nam, MDE80=%.3fpp",
       sd0 * 100, LV["Q2"], T_DEV, N.Z80 * sd0 * 100)
Ts = [(2.50, "DEV hien tai"), (2.58, "lui 2021-12, giu OI"),
      (3.96, "DEV+VAL (tieu thu VAL lam du lieu do)"),
      (4.50, "lui 2020-01, BO 5 feature OI, train lai"),
      (6.00, "TOI DA: 2020-01..2025-12 gop"), (6.31, "toi da + 2019-09 (khong thuc te)")]
HZ = [(1.0, "nguyen trang (k=%.2f)" % s3["conc"]["C2b"]["mean_pos"]),
      (np.sqrt(s3["icc"]["C2b|ngay"]["neff_30"] / s3["icc"]["C2b|ngay"]["neff_kbar"]),
       "k=30 vi the/thoi diem"), (FH, "k vo han (TRAN 1/ICC)")]
L.info("%-42s %12s %12s %12s", "kich ban T", "hz nguyen", "hz k=30", "hz TRAN")
best = (9e9, None)
for T, lab in Ts:
    row = []
    for f, _ in HZ:
        m = N.Z80 * sd0 * 100 * np.sqrt(T_DEV / T) / f
        row.append(m)
        if m < best[0]:
            best = (m, "%s + %s" % (lab, _))
    L.info("%-42s %12.3f %12.3f %12.3f", "%.2f nam (%s)" % (T, lab), *row)
L.info("\n  MDE80 SAN kha thi = %.3f pp  (%s)", best[0], best[1])
L.info("  Nguong can = 3.00 pp => %s", "DAT" if best[0] <= 3.0 else "KHONG DAT")
for f, lab in HZ:
    Tneed = T_DEV * (N.Z80 * sd0 * 100 / (3.0 * f)) ** 2
    L.info("  So nam can de MDE80=3pp voi hang ngang '%s': %.1f nam", lab, Tneed)
json.dump(dict(LV=LV, sd0=sd0, FH=float(FH), best=best[0]),
          open("/home/ubuntu/nbets/step5.json", "w"), indent=1)
L.info("\nDONE step5")
