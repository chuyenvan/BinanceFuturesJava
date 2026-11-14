#!/usr/bin/env python3
"""Sinh docs/result/IND_COMBO_SELECTION.md tu explore.json + selection.json (truoc khi doc Y CONFIRM)."""
import json
import logging
import shutil

logging.basicConfig(level=logging.INFO, format="%(message)s")
W = "/home/ubuntu/claude_master/ind1114/"
R = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/"
E = json.load(open(W + "explore.json"))
S = json.load(open(W + "selection.json"))
L = []
a = L.append
a("# IND_COMBO Pha 0 — SELECTION (khoá TRƯỚC khi đọc Y CONFIRM 2024–25)")
a("")
a("Prereg vz_e1_wt 14ed6c00 (PREREG_IND_COMBO.md md5 1735a8eb, IND_COMBO_P0_PLAN.md md5 f15a6080). Sinh tự động từ explore.json/selection.json.")
a("")
a("## Mẫu EXPLORE (2022–23, +07)")
a("- Leg nt-x14 PREDICT 8 seed: %d leg, %d cụm đợt (≤ 60′, hợp 8 seed); theo năm %s. Số cụm CONFIRM (chỉ đếm, không Y): %d (leg %d)." % (
    E["n_leg_E"], E["n_clu_E"], E["legs_yr"], E["n_clu_C"], E["n_leg_C"]))
a("- Khử trùng (|ρ Spearman| > 0,80 với indicator đứng trước còn giữ; bảng 45 feature S1 không có trong dump): giữ %d = %s." % (len(S["keep"]), ", ".join(S["keep"])))
a("- Bỏ: " + "; ".join("%s (~%s ρ %s)" % (k, v[0], v[1]) for k, v in E["dropped"].items()))
a("")
a("## Track S — EXPLORE (partial Spearman IC, khử rank(hạng S1), rank(điểm S1), dummy năm; CI90 bootstrap cụm 2 000, seed 20261114)")
a("")
a("| X | IC | CI90 | p2 | FDR q0,10 | IC 2022 | IC 2023 | n |")
a("|---|---:|---|---:|:-:|---:|---:|---:|")
order = sorted(S["keep"], key=lambda c: E["single"][c]["p2"])
for c in order + ["CALL", "CTOP5", "ML"]:
    r = E["single"][c]
    a("| %s | %+.4f | [%+.4f; %+.4f] | %.4f | %s | %s | %s | %d |" % (c, r["ic"], r["ci90"][0], r["ci90"][1], r["p2"],
      ("x" if r.get("fdr") else "") if c in S["keep"] else "in-sample", r.get("ic_2022", ""), r.get("ic_2023", ""), r["n"]))
a("")
a("- C_ALL = TB phân vị có dấu (ECDF EXPLORE) của %d indicator coin-level giữ lại; C_TOP5 = %s; ML = xgboost depth 3/200 cây/lr 0,05/subsample 0,8/seed 20261114, mục tiêu = residual rank(Y) theo rank(hạng S1)+năm, feature = %s (model `ml.json` lưu, KHÔNG train lại)." % (
    len([c for c in S["keep"] if c.startswith("C")]), ", ".join(S["top5"]), ", ".join(S["feats"])))
a("- ML IC EXPLORE là in-sample (quá khớp, chỉ báo).")
a("")
a("## ỨNG VIÊN CONFIRM (≤ 6) — chốt")
if S["closeS"]:
    a("- Track S ĐÓNG: không indicator đơn sống FDR và C_ALL p ≥ 0,20.")
else:
    for c in S["candS"]:
        a("- %s: dấu EXPLORE %+d; cutpoint ngũ phân vị XẤU (EXPLORE) %s %.6g; seed 42 IC EXPLORE %s" % (
            c, int(S["sign"][c]), "≤" if S["sign"][c] > 0 else "≥", S["cutS"][c], E["seed42_E"].get(c)))
    a("- Holm một phía α 0,10 trên m = %d ứng viên." % len(S["candS"]))
m = S["mde80"]
a("")
a("## MDE80 (trước khi đọc Y CONFIRM)")
a("- se_E trung vị %.4f; se_C = se_E × √(n_cụm_E/n_cụm_C) = %.4f; MDE80 không chỉnh (α 0,10 một phía) = **%.3f**; Holm m=%d: %.3f." % (
    m["se_E_median"], m["se_C"], m["mde_unadj"], m["m"], m["mde_holm"]))
if m["warn"]:
    a("- ⚠️ MDE > 0,08 ⇒ **khả năng không có power** (vẫn chạy theo prereg).")
a("")
a("## Track G — EXPLORE (Y72 pp, khử cụm R5, Δ so với phút pass B0)")
g = E["G"]
a("- Phút EXPLORE (seed × phút): %s; cụm bootstrap (toàn DEV) %d. Market giữ sau khử trùng: %s + C_ALL_M." % (g["n_min"], g["n_clu"], ", ".join(S["G"]["kept_m"])))
a("")
a("| M | dấu | relax 0,85 Δ [CI90] / Y72 nm∩thuận | relax 0,70 Δ [CI90] / Y72 nm∩thuận | veto Δ [CI90] |")
a("|---|:-:|---|---|---|")
for c, r in g["ind"].items():
    def f(x):
        return "Δ %+.2f [%+.2f; %+.2f] / %+.2f (n %d)" % (x["delta"], x["ci90"][0], x["ci90"][1], x["y_nm_fav"], x["n_nm"]) if "delta" in x else str(x)
    v = r["veto"]
    vv = "Δ %+.2f [%+.2f; %+.2f] (n %d)" % (v["delta"], v["ci90"][0], v["ci90"][1], v["n_adv"]) if "delta" in v else str(v)
    a("| %s | %+d | %s | %s | %s |" % (c, int(g["sign"][c]), f(r["relax_0.85"]), f(r["relax_0.70"]), vv))
a("")
a("- Y72 phút pass B0 (khử cụm) = %+.2f pp." % list(g["ind"].values())[0]["relax_0.85"]["y_pass"])
if S["G"]["cands"]:
    a("- Ứng viên G chọn: %s (Holm m = 14)." % S["G"]["cands"])
else:
    a("- **Không ứng viên G nào đạt luật chọn EXPLORE ⇒ track G ĐÓNG tại EXPLORE (không mở Y CONFIRM cho G).**")
open(R + "IND_COMBO_SELECTION.md", "w").write("\n".join(L) + "\n")
for f in ("selection.json", "explore.json", "ml.json"):
    shutil.copyfile(W + f, R + "ind_combo_p0/" + f)
logging.info("ok")
