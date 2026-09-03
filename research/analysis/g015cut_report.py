"""G015CUT — ap dung dieu kien chot cua docs/PREREG_G015CUT.md len g015cut_final.json."""
import json, logging, sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s")
L = logging.getLogger("rep")
F = json.load(open(sys.argv[1] if len(sys.argv) > 1 else "/home/ubuntu/g015/g015cut_final.json"))
pt, B = F["point"], F["boot"]
K = B["k_mult"]
BLS = ("72h", "24h", "168h")
MOC, DA = 0.1675, 0.0050
DRS = (0.005, 0.010, 0.020)


def vd(r, dl):
    if r["wide_lo"] > -dl and r["wide_hi"] < dl:
        return "TUONG DUONG"
    if r["wide_lo"] > -dl:
        return "KHONG KEM (NI)"
    if r["wide_hi"] < -dl:
        return "KEM HON RO"
    return "KHONG KET LUAN"


L.info("=== 0. CONG TAI LAP (PREREG 5.1) ===")
rf = pt["full45"]["rho"]
L.info("rho(full45) = %.5f | moc = %.4f | lech = %+.5f -> %s", rf, MOC, rf - MOC,
       "PASS" if abs(rf - MOC) <= 0.010 else ("MARGINAL" if abs(rf - MOC) <= 0.019 else "FAIL"))
L.info("mono20(full45)=%.3f | rho theo nam %s", pt["full45"]["mono20"],
       dict((k, round(v, 4)) for k, v in pt["full45"]["rho_year"].items()))
L.info("admit full45: n=%d rate=%.5f q=%.5f", pt["full45"]["n_admit"],
       pt["full45"]["admit_rate"], pt["full45"]["q_admit"])
if "p_old" in pt:
    r = B["p_old|rho|72h"]
    L.info("ban DA DEPLOY p_old: rho=%.5f mono=%.3f | d(p_old - full45)=%+.5f sd=%.5f "
           "wideCI=[%+.5f,%+.5f]", pt["p_old"]["rho"], pt["p_old"]["mono20"], r["d_obs"],
           r["sd"], r["wide_lo"], r["wide_hi"])

c = B.get("crude")
if c:
    sa = B["no_oi|rho|72h"]["sd"]
    L.info("")
    L.info("=== 1. KIEM CHUNG XAP XI frozen-rank ===")
    L.info("sd xap xi=%.6f | sd tho (%d rep)=%.6f | lech %.1f%% -> %s", sa, c["n_rep"],
           c["sd_crude"], 100 * abs(c["sd_crude"] - sa) / max(sa, 1e-12),
           "OK" if abs(c["sd_crude"] - sa) / max(sa, 1e-12) <= 0.20 else "LOAI XAP XI")

L.info("")
L.info("=== 2. DOI CHUNG AM (PREREG 5.2) ===")
nf = 0.0
for v in ("noise46_a", "noise46_b"):
    if v not in pt:
        continue
    r = B["%s|rho|72h" % v]
    nf = max(nf, abs(r["d_obs"]))
    L.info("%-11s d_rho=%+.5f sd=%.5f CI95=[%+.5f,%+.5f] wide=[%+.5f,%+.5f] chua0=%s |d|<0.010=%s",
           v, r["d_obs"], r["sd"], r["ci_lo"], r["ci_hi"], r["wide_lo"], r["wide_hi"],
           r["wide_lo"] <= 0 <= r["wide_hi"], abs(r["d_obs"]) < 0.010)
L.info("SAN NHIEU QUY TRINH = %.5f", nf)

L.info("")
L.info("=== 3. BANG BIEN THE (khoi 72h) ===")
rows = []
for v in pt:
    if v == "full45":
        continue
    r, q = B["%s|rho|72h" % v], B["%s|q_admit_matched|72h" % v]
    row = {"bienthe": v, "nf": pt[v]["n_feat"], "rho": round(pt[v]["rho"], 5),
           "d_rho": round(r["d_obs"], 5), "sd": round(r["sd"], 5),
           "CI95": "[%+.4f,%+.4f]" % (r["ci_lo"], r["ci_hi"]),
           "wideCI": "[%+.4f,%+.4f]" % (r["wide_lo"], r["wide_hi"]),
           "mono": pt[v]["mono20"], "yrmin": round(min(pt[v]["rho_year"].values()), 4),
           "admR": round(pt[v]["admit_rate"], 5), "qnat": round(pt[v]["q_admit"], 5),
           "qm": round(pt[v]["q_admit_matched"], 5), "d_qm": round(q["d_obs"], 5),
           "sd_qm": round(q["sd"], 5), "qm_wide_lo": round(q["wide_lo"], 5),
           "vd_rho": vd(r, 0.010), "vd_q": vd(q, DA)}
    for bl in BLS:
        row["wlo" + bl] = round(B["%s|rho|%s" % (v, bl)]["wide_lo"], 5)
    rows.append(row)
T = pd.DataFrame(rows)
pd.set_option("display.width", 400)
pd.set_option("display.max_columns", 80)
L.info("\n%s", T.to_string(index=False))
T.to_csv("/home/ubuntu/g015/g015cut_table.csv", index=False)

L.info("")
L.info("=== 4. QUYET DINH: no_oi (PREREG 5.3) ===")
r, q = B["no_oi|rho|72h"], B["no_oi|q_admit_matched|72h"]
for dl in DRS:
    ok = all(B["no_oi|rho|%s" % bl]["wide_lo"] > -dl for bl in BLS)
    L.info("Delta_rho=%.3f: (A) 3 khoi deu wide_lo>-Delta = %s | %s", dl, ok, vd(r, dl))
L.info("(A) wide_lo: %s | K*sd=%.5f", dict((bl, round(B["no_oi|rho|%s" % bl]["wide_lo"], 5))
                                          for bl in BLS), K * r["sd"])
L.info("(B) mono=%.3f >=0.95:%s | nam >0 het:%s", pt["no_oi"]["mono20"],
       pt["no_oi"]["mono20"] >= 0.95, all(x > 0 for x in pt["no_oi"]["rho_year"].values()))
L.info("(C) d_qm=%+.5f sd=%.5f wide=[%+.5f,%+.5f] > -%.4f:%s | %s | K*sd=%.5f",
       q["d_obs"], q["sd"], q["wide_lo"], q["wide_hi"], DA, q["wide_lo"] > -DA, vd(q, DA),
       K * q["sd"])
L.info("(C) admit_rate=%.5f trong [0.001,0.004]:%s", pt["no_oi"]["admit_rate"],
       0.001 <= pt["no_oi"]["admit_rate"] <= 0.004)
