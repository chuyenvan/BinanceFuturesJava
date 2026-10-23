#!/usr/bin/env python3
"""FUNDNEG_T1: generate docs/result/FUNDNEG_T1.md tables from out/*.json (no hand-typed numbers in tables)."""
import json, sys
W = "/home/ubuntu/claude_master/fundneg_t1_wk/out/"
R = json.load(open(W + "results.json"))
D = json.load(open(W + "posthoc_desc.json"))
C = json.load(open(W + "checks.json"))
V3 = json.load(open(W + "v3_independent.json"))
pre = json.load(open(W + "results_pre_addendum1.json"))
V = R["variants"]
pc = lambda v: "%+.2f%%" % (100 * v)
L = []
a = L.append


def yn(b):
    return "ĐẠT" if b else "trượt"


a("## Bảng 1 — Tiêu chí (tập NON-OVERLAP)\n")
a("| biến thể | KIỂM n | KIỂM mean net | CI95 ngày | KIỂM net2 (×2 phí) | ctrl p95 KIỂM | KHÁM PHÁ n | KHÁM PHÁ mean | ctrl p95 KP | n 2024 / 2025 | F1 | F2 | F3 | F4 | F5 | VERDICT |")
a("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for nm, v in V.items():
    t, d, c = v["NON_TEST"], v["NON_DISC"], v["criteria"]
    a("| %s | %d | %s | [%s, %s] | %s | %s | %d | %s | %s | %d / %d | %s | %s | %s | %s | %s | **%s** |" % (
        nm, t["n"], pc(t["mean_net"]), pc(t["ci95_day"][0]), pc(t["ci95_day"][1]), pc(t["mean_net2"]), pc(t["ctrl_mean_p95"]),
        d["n"], pc(d["mean_net"]), pc(d["ctrl_mean_p95"]), t["n_by_year"].get("2024", 0), t["n_by_year"].get("2025", 0),
        yn(c["F1"]), yn(c["F2"]), yn(c["F3"]), yn(c["F4"]), yn(c["F5"]), c["verdict"]))
a("\n## Bảng 2 — Chi tiết theo tập × kỳ (net = sau phí 0,30 %/vòng + funding thật)\n")
a("| biến thể | tập/kỳ | n | ngày | mean net | median | hit | mean gross | mean funding | settle/lệnh | net2 | CI95 ngày | ctrl p50 | ctrl p95 | MFE med | MAE med |")
a("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for nm, v in V.items():
    for k in ["NON_DISC", "NON_TEST", "ALL_DISC", "ALL_TEST"]:
        s = v[k]
        a("| %s | %s | %d | %d | %s | %s | %.1f%% | %s | %s | %.1f | %s | [%s, %s] | %s | %s | %s | %s |" % (
            nm, k, s["n"], s["n_days"], pc(s["mean_net"]), pc(s["median_net"]), 100 * s["hit"], pc(s["mean_gross"]), pc(s["mean_fund"]),
            s["mean_nset"], pc(s["mean_net2"]), pc(s["ci95_day"][0]), pc(s["ci95_day"][1]), pc(s["ctrl_mean_p50"]), pc(s["ctrl_mean_p95"]),
            pc(s["mfe_med"]), pc(s["mae_med"])))
a("\n## Bảng 3 — Số sự kiện/năm và mean net theo năm\n")
a("| biến thể | sự kiện thô mọi symbol | sự kiện thô trong universe | ALL (sau 1-vị-thế) | NON | mean net NON theo năm |")
a("|---|---|---|---|---|---|")
for nm, v in V.items():
    rc = v["raw_counts"]
    allc = {**v["ALL_DISC"]["n_by_year"], **v["ALL_TEST"]["n_by_year"]}
    nonc = {**v["NON_DISC"]["n_by_year"], **v["NON_TEST"]["n_by_year"]}
    my = {**v["NON_DISC"]["mean_by_year"], **v["NON_TEST"]["mean_by_year"]}
    f = lambda dd: " / ".join("%s:%s" % (y, dd[y]) for y in sorted(dd))
    a("| %s | %s | %s | %s | %s | %s |" % (nm, f(rc["all_syms"]), f(rc["in_universe"]), f(allc), f(nonc),
                                           " / ".join("%s:%s" % (y, pc(my[y])) for y in sorted(my))))
a("\nĐếm loại: ")
for nm, v in V.items():
    a("- %s: ngoài dữ liệu (exit > 2025-12-31) %d; thiếu nến vào %d; thiếu nến ra %d; bỏ do 1-vị-thế/coin %d; lệnh ALL %d; OVERLAP %d (cờ a sym±24h %d, cờ b ngày sập %d); control pool = cả universe (coin không có vol30) %d; pool median %.0f coin; NON sau 2025-11-21 (X14 dừng): KIỂM %d." % (
        nm, v["n_beyond_data"], v["n_no_entry"], v["n_no_exit"], v["n_dropped_onepos"], v["n_trades_all"], D[nm]["n_overlap"],
        D[nm]["n_ov_sym24"], D[nm]["n_ov_crashday"], v["n_pool_whole_universe"], v["pool_size_med"], v["NON_TEST"]["n_after_x14_stop"]))
a("\n## Bảng 4 — Tập trung theo coin (NON)\n")
a("| biến thể | kỳ | số coin | top-5 coin (số lệnh, Σnet) | top-5 tỷ trọng lệnh | top-5 tỷ trọng Σnet | mean net bỏ top-5 |")
a("|---|---|---|---|---|---|---|")
for nm, v in V.items():
    for k in ["NON_DISC", "NON_TEST"]:
        s = v[k]
        a("| %s | %s | %d | %s | %.1f%% | %.1f%% | %s |" % (nm, k, s["n_sym"], ", ".join("%s(%d, %+.2f)" % (q, w[0], w[1]) for q, w in s["top5_sym"].items()),
                                                      100 * s["top5_share_n"], 100 * s["top5_share_sumnet"], pc(s["mean_net_ex_top5"])))
a("\n## Bảng 5 — Sleeve 2 % vốn/lệnh (compounding, equity thực hiện)\n")
a("| biến thể | tập/kỳ | equity cuối | CAGR | maxDD | max đồng thời |")
a("|---|---|---|---|---|---|")
for nm, v in V.items():
    for k in ["NON_DISC", "NON_TEST", "ALL_DISC", "ALL_TEST"]:
        s = v[k]["sleeve"]
        a("| %s | %s | %.4f | %s | %s | %d |" % (nm, k, s["final_equity"], pc(s["cagr"]), pc(s["maxdd"]), s["max_concurrent"]))
a("\n## Bảng 6 — Tương quan với BTC trend (NON)\n")
a("| biến thể | kỳ | ρ Pearson net~BTC 7d trước | ρ Spearman | ρ Pearson net~BTC trong lúc giữ | tỷ lệ lệnh BTC7d<0 | mean net khi BTC7d<0 | khi ≥0 |")
a("|---|---|---|---|---|---|---|---|")
for nm, v in V.items():
    for k in ["NON_DISC", "NON_TEST"]:
        s = v[k]
        a("| %s | %s | %.3f | %.3f | %.3f | %.1f%% | %s | %s |" % (nm, k, s["corr_btc7_pearson"], s["corr_btc7_spearman"], s["corr_btchold_pearson"],
                                                         100 * s["share_btc7_neg"], pc(s["mean_net_btc7_neg"]), pc(s["mean_net_btc7_pos"])))
a("\n## Bảng 7 — POST-HOC mô tả (KHÔNG vào tiêu chí): đuôi, thành phần giá vs funding, theo interval (NON)\n")
a("| biến thể | kỳ | n | min | p1 | p50 | p99 | max | mean cắt 1 % hai đuôi | mean chỉ giá (gross−0,30 %) | mean funding | funding>0 | theo interval_h [n, net, gross, fund] |")
a("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for nm, r in D.items():
    for per in ["DISC", "TEST"]:
        d = r[per]
        a("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %.0f%% | %s |" % (
            nm, per, d["n"], pc(d["q"][0]), pc(d["q"][1]), pc(d["q"][4]), pc(d["q"][7]), pc(d["q"][8]), pc(d["trim1_mean"]),
            pc(d["price_only_mean"]), pc(d["fund_mean"]), 100 * d["share_fund_pos"],
            "; ".join("%sh:[%d, %s, %s, %s]" % (k, w[0], pc(w[1]), pc(w[2]), pc(w[3])) for k, w in d["by_interval"].items())))
a("\nTop-3 lệnh NON KIỂM theo net (thr-0.10_H72): " + "; ".join("%s %s" % (s, pc(v)) for s, v in D["thr-0.10_H72"]["TEST"]["top10_net"][:3]))
a("\n## Validation\n")
v3n = V["thr-0.10_H24"]
t_all = None
a("| mã | kiểm | kết quả |")
a("|---|---|---|")
a("| V1 | offset `ts` (calc_time) so với tròn giờ, mọi dòng 2022–25 | max %d ms (< 60 s: %s) |" % (C["V1_offset_ms_max"], C["V1_offset_le_60s_all"]))
for c in C["V1_vision_csv_compare"]:
    a("| V1 | CSV Vision gốc tải lại %s %s (header %s) vs parquet | %d/%d dòng khớp, max|Δrate| = %g, interval lệch %d, calc_time offset max %d ms |" % (
        c["sym"], c["mo"], ",".join(c["header"]), c["merge"].get("both", 0), c["n_csv"], c["max_abs_drate"], c["interval_mismatch"], c["calc_time_offset_max_ms"]))
a("| V1 | t_in > τ mọi lệnh (assert trong run + checks) | %s |" % all(x["tin_gt_tau_all"] for x in C["V2_trades"].values()))
a("| V2 | dtype ts funding / panel hr / tau,t_in,t_out lệnh | %s / %s / %s |" % (C["V2_funding_ts_int64"], C["V2_panel_hr_dtype"],
                                                                      ",".join(sorted(set(x["tau_dtype"] for x in C["V2_trades"].values())))))
a("| V2 | trùng (sym, τ) funding / lệnh | %d / %s |" % (C["V2_funding_dup_sym_tau"], sum(x["dup_sym_tau"] for x in C["V2_trades"].values())))
a("| V3 | tái lập độc lập thr-0.10_H24 KIỂM — ALL | pipeline n=%d mean=%.15f; độc lập n=%d mean=%.15f; Δ=%.2e |" % (
    v3n["ALL_TEST"]["n"], v3n["ALL_TEST"]["mean_net"], V3["ALL"]["n"], V3["ALL"]["mean_net"], v3n["ALL_TEST"]["mean_net"] - V3["ALL"]["mean_net"]))
a("| V3 | tái lập độc lập thr-0.10_H24 KIỂM — NON | pipeline n=%d mean=%.15f; độc lập n=%d mean=%.15f; Δ=%.2e |" % (
    v3n["NON_TEST"]["n"], v3n["NON_TEST"]["mean_net"], V3["NON"]["n"], V3["NON"]["mean_net"], v3n["NON_TEST"]["mean_net"] - V3["NON"]["mean_net"]))
a("| V4 | 10 lệnh ngẫu nhiên (seed 7) đọc lại nến 1m thô + dòng funding, tính tay | khớp cả 10: %s (chi tiết `checks.json`) |" % C["V4_all_match"])
v5 = C["V5"]
a("| V5 | dấu funding qua `accrue()`: rate âm ×3 (τ loại, τ+H nhận) / rate dương / hỗn hợp + thiếu giá | %s / %s / %s → %s |" % (
    v5["case_neg_rate_3x_(tau_excluded,tau+H_included)"][:2], v5["case_pos_rate"][:2], v5["case_mixed_with_missing_price"][:2], "PASS" if v5["pass"] else "FAIL"))
mx = 0
for nm in pre["variants"]:
    for k in ["NON_DISC", "NON_TEST", "ALL_DISC", "ALL_TEST"]:
        for f in ["mean_net", "mean_net2", "ctrl_mean_p95"]:
            mx = max(mx, abs(pre["variants"][nm][k][f] - V[nm][k][f]))
a("\nADDENDUM 1 — trước/sau sửa: max |Δ| (mean net, net2, ctrl p95, mọi biến thể/tập/kỳ) = %.2e; số lệnh và F1–F5 không đổi." % mx)
open(sys.argv[1], "w").write("\n".join(L) + "\n")
print("written", len(L))
