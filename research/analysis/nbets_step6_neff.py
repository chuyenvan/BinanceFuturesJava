"""NBETS buoc 6: n_eff THAT cua C2b + do nhay cua ket luan theo lua chon ICC."""
import logging, sys, json
import numpy as np
sys.path.insert(0, "/home/ubuntu/nbets")
import nb_lib as N

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/nbets/step6.out", "w"),
                              logging.StreamHandler()])
L = logging.getLogger("s6")
s3 = json.load(open("/home/ubuntu/nbets/step3.json"))
s4 = json.load(open("/home/ubuntu/nbets/step4.json"))
T_DEV = 911 / 365.0
x, _ = N.logret("C2b")
n = len(x)
vr, V, v1 = N.var_ratio(x)
L.info("=== n_eff THAT cua C2b (ba cach dem KHAC NHAU, khong duoc tron) ===")
L.info("  (1) so khoi resample = ceil(911/L):")
for bl in [3, 10, 21, 63]:
    L.info("        L=%2d -> %4d khoi", bl, int(np.ceil(n / bl)))
L.info("  (2) ESS variance-ratio = T*V(1)/V(L)  [so NGAY iid tuong duong]:")
for bl in [3, 10, 21, 42, 63]:
    L.info("        L=%2d VR=%.3f -> ESS=%7.1f ngay (T=911)", bl, vr[bl], n / vr[bl])
L.info("  (3) so CUOC hieu dung tren ROI tung lenh (step3 5.3), N=970:")
for bl in [3, 10, 21]:
    g = s3["glob"]["C2b|%d" % bl]
    L.info("        L=%2d -> %.1f cuoc (=%.2f cuoc moi lenh)", bl, g["n_eff"],
           g["n_eff"] / 970)
L.info("  KIEM: sd(dCAGR) cap Q2 o L=1 (iid) = %.4fpp; o L=21 = %.4fpp; ti le=%.3f",
       s4["pairs"]["Q2|1"]["sd"] * 100, s4["pairs"]["Q2|21"]["sd"] * 100,
       s4["pairs"]["Q2|21"]["sd"] / s4["pairs"]["Q2|1"]["sd"])
L.info("  Neu ESS that la 44 (thay vi 911) thi ti le do phai la sqrt(911/44)=%.2f",
       np.sqrt(911 / 44))


L.info("\n=== DO NHAY: ket luan Cau 5 theo lua chon cohort cho ICC ===")
sd0 = s4["pairs"]["Q2|3"]["sd"]
kb = s3["conc"]["C2b"]["mean_pos"]
L.info("%-6s %8s %10s %10s %10s %10s %10s", "cohort", "ICC", "n_eff(kb)",
       "TRAN=1/ICC", "he_so_sd", "MDE80@6.0y", "nam@3pp")
for lab in ["ngay", "72h", "tuan"]:
    icc = s3["icc"]["C2b|%s" % lab]["icc"]
    nk = kb / (1 + (kb - 1) * icc)
    cap = 1.0 / icc
    f = np.sqrt(cap / nk)
    m6 = N.Z80 * sd0 * 100 * np.sqrt(T_DEV / 6.0) / f
    ty = T_DEV * (N.Z80 * sd0 * 100 / (3.0 * f)) ** 2
    L.info("%-6s %8.4f %10.2f %10.2f %10.3f %10.3f %10.1f", lab, icc, nk, cap, f,
           m6, ty)
L.info("\n=== Cap Q1 (selector) va Q2 (exit) o L_valid, quy ve MDE80 theo T ===")
for pid, lv in [("Q1", 10), ("Q2", 3)]:
    sd = s4["pairs"]["%s|%d" % (pid, lv)]["sd"]
    for T in [2.4959, 3.96, 6.00]:
        L.info("  %s L=%2d T=%.2f nam -> MDE80=%.3fpp", pid, lv, T,
               N.Z80 * sd * 100 * np.sqrt(T_DEV / T))
L.info("\nDONE step6")
