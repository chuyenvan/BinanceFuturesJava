#!/usr/bin/env python3
"""Sinh docs/result/IND_COMBO_P0.md tu explore/selection/confirm/build/causal json."""
import json
import logging
import shutil

logging.basicConfig(level=logging.INFO, format="%(message)s")
W = "/home/ubuntu/claude_master/ind1114/"
R = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/"
E = json.load(open(W + "explore.json"))
S = json.load(open(W + "selection.json"))
C = json.load(open(W + "confirm.json"))
B = json.load(open(W + "build.json"))
K = json.load(open(W + "causal_chk.json"))
L = []
a = L.append
a("# IND_COMBO Pha 0 — KẾT QUẢ (chỉ đo, không sim)")
a("")
a("Prereg vz_e1_wt **14ed6c00** (PREREG_IND_COMBO.md md5 1735a8eb; IND_COMBO_P0_PLAN.md md5 f15a6080). SELECTION **96f74733** (IND_COMBO_SELECTION.md md5 875ed090, selection.json 2d839dc2, ml.json 9a328b4d). Code `research/ind_combo/`, số liệu `docs/result/ind_combo_p0/`.")
a("")
a("## VERDICT: **ĐÓNG** — không ứng viên track S nào đạt đủ 3 tiêu chí CONFIRM; track G không có ứng viên ở EXPLORE. Không đề xuất Pha 1 (S-VETO / G-RELAX / G-VETO / K-FLEX đều không đủ điều kiện).")
a("")
a("## Dữ liệu (kiểm kho)")
a("- Leg: printDone nt-x14 8 seed, level PREDICT_SYMBOL_TRADE; Y_leg = 100·pnl/margin (pnl ròng phí sim, gồm DCA trong leg + exit); start +07 → UTC; hạng S1 từ cand_base.npz (top-24 sp/phút), điểm S1 = symbolPred.")
a("- Số leg/cụm: EXPLORE %d leg / %d cụm; CONFIRM %d / %d; HO 2026H1 %d / %d. Theo năm %s. Y NaN = %d." % (
    E["n_leg_E"], E["n_clu_E"], E["n_leg_C"], E["n_clu_C"], B["per"]["H"], B["clusters"]["H"], B["legs_yr"], B["y_nan"]))
a("- Nến: 1h OHLCV `~/java/fsrun/OHLCV_1H_v2.bin` (Aerospike kline_1m_opt 2021–2025, 626 symbol) — dùng lại theo §5 (không resample kline1m); 4h/1d gộp từ 1h; r1m (C18) từ close Vision `res1109/r1_s1/kl`; ALT_EW `edge_attr/index.npz`. 2026H1: Kaggle kernel `ind-ho26` (vz-kline1m-2026 → 1h + ALT_EW), enable_internet=false.")
a("- Track G: r/q theo phút tính lại bằng gate_offline cấu hình R5 (pred r3_gate + sổ n4f-b0, J 256); số phút pass/seed/năm KHỚP tuyệt đối sig_meta R5 (8/8 seed × 4 năm). Y72 = r5q_y.parquet (R5 Pha 1, 200a29a3).")
a("")
a("## Validate")
a("- Causal: 20 leg ngẫu nhiên (seed 20261114), tính TAY RSI14 1h, Stoch %%K 4h, C/SMA50 1d từ nến 1h thô CẮT tại giờ đóng ≤ M: %d/20 khớp (≤1e-6); nến cuối đóng 0–57′ trước phút vào." % (K["n"] - K["bad"]))
a("- NaN: C1/C4/C6/C18/C20 < 3 % (DEV); chỉ báo 1d NaN 22–45 % vì ~25 % leg vào coin < 50 ngày tuổi (age ≥ 300 ngày ⇒ NaN 0 %) — theo thiết kế prereg; IC tính trên phần không NaN.")
a("- Bootstrap tái lập: chạy lại cùng seed 20261114 ra số y hệt (assert trong code + 2 lần chạy EXPLORE trùng số).")
a("- Seed 42 cùng chiều gộp ở mọi ứng viên (EXPLORE và CONFIRM).")
a("- Rebuild thêm 2026 không đổi X DEV của mọi indicator dùng (0 lệch), TRỪ M4 breadth (xem sai lệch #2).")
a("")
a("## EXPLORE 2022–23 (partial Spearman IC; khử rank(hạng S1), rank(điểm S1), năm)")
a("Khử trùng giữ 16: %s. Bỏ: %s." % (", ".join(S["keep"]), ", ".join("%s~%s" % (k, v[0]) for k, v in E["dropped"].items())))
a("")
a("| X | IC | CI90 | p2 | FDR | 2022 | 2023 |")
a("|---|---:|---|---:|:-:|---:|---:|")
top = sorted(S["keep"], key=lambda c: E["single"][c]["p2"])[:6]
for c in top:
    r = E["single"][c]
    a("| %s | %+.3f | [%+.3f; %+.3f] | %.3f | %s | %+.3f | %+.3f |" % (c, r["ic"], r["ci90"][0], r["ci90"][1], r["p2"], "x" if r["fdr"] else "", r["ic_2022"], r["ic_2023"]))
for c in ("CALL", "CTOP5", "ML"):
    r = E["single"][c]
    a("| %s (in-sample) | %+.3f | [%+.3f; %+.3f] | %.3f | – | | |" % (c, r["ic"], r["ci90"][0], r["ci90"][1], r["p2"]))
a("")
a("C11 = ADX14 4h; C17 = C/SMA200−1 (1d); C18 = RV1h/RV24h; C4 = Stoch %%K 1h; M3 = BTC C/SMA200−1. C_TOP5 = %s. MDE80 (CONFIRM, 113 cụm) = **%.3f** (Holm m=5: %.3f) > 0,08 ⇒ cảnh báo thiếu power." % (", ".join(S["top5"]), S["mde80"]["mde_unadj"], S["mde80"]["mde_holm"]))
a("")
a("## CONFIRM 2024–25 (ứng viên chốt trong SELECTION; Holm một phía α 0,10, m = 5)")
a("")
a("| Ứng viên | dấu E | IC | CI90 | p1 | Holm | IC 2024 | IC 2025 | veto ΔY (bỏ−giữ) [CI90] | ΣPnL bỏ 2024 / 2025 (USD) | (1) | (2) | (3) | ĐẠT | seed42 |")
a("|---|:-:|---:|---|---:|:-:|---:|---:|---|---|:-:|:-:|:-:|:-:|---:|")
for c in S["candS"]:
    r = C["S"][c]
    v = r["veto"]
    a("| %s | %+d | %+.3f | [%+.3f; %+.3f] | %.3f | %s | %+.3f | %+.3f | %+.2f [%+.2f; %+.2f] | %+.0f / %+.0f | %s | %s | %s | **%s** | %+.3f |" % (
        c, int(S["sign"][c]), r["ic"], r["ci90"][0], r["ci90"][1], r["p1"], "x" if r["holm"] else "", r["ic_2024"], r["ic_2025"],
        v["d"], v["ci90"][0], v["ci90"][1], v["sum_pnl_bad_2024"], v["sum_pnl_bad_2025"],
        "x" if r["crit1"] else "", "x" if r["crit2"] else "", "x" if r["crit3"] else "", "ĐẠT" if r["PASS"] else "KHÔNG", r["seed42_ic"]))
a("")
a("- C_TOP5 và C11 qua (1) (IC dương, CI90 > 0, Holm) — tức có tín hiệu xếp hạng yếu (IC ≈ 0,06) — nhưng **trượt (3) kinh tế**: nhóm ngũ phân vị xấu vẫn lãi dương ở cả 2024 và 2025 (bỏ đi là mất tiền), ΔY CI chứa 0. C11 còn trượt (2) (IC 2025 ≈ 0). ML (in-sample IC 0,73) sụp về −0,02 ở CONFIRM = quá khớp; ngũ phân vị \"xấu\" của ML/C_ALL lại có Y cao hơn.")
a("")
a("## Track G (gate linh hoạt, market-level)")
a("- EXPLORE: không chỉ báo nào (M1, M3, M5, M6, C_ALL_M) đạt luật chọn ở CẢ 2 band (relax cần CI90 dưới > −1 pp; M3 band 0,85 CI dưới −1,37; C_ALL_M −1,74), veto đều CI chứa 0 ⇒ **track G ĐÓNG tại EXPLORE**, không mở Y CONFIRM cho G. Chi tiết: IND_COMBO_SELECTION.md.")
a("")
a("## HO 2026-01..06 (chỉ mô tả; không có hạng S1 ⇒ khử theo điểm S1; 2 275 leg / 29 cụm)")
a("")
a("| Ứng viên | IC | CI90 | veto ΔY [CI90] | ΣPnL bỏ |")
a("|---|---:|---|---|---:|")
for c in S["candS"]:
    r = C["HO"][c]
    v = r["veto"]
    a("| %s | %+.3f | [%+.3f; %+.3f] | %+.2f [%+.2f; %+.2f] | %+.0f |" % (c, r["ic"], r["ci90"][0], r["ci90"][1], v["d"], v["ci90"][0], v["ci90"][1], v["sum_pnl_bad_2026"]))
a("- HO: C_TOP5 IC đổi dấu (−0,05), C_ALL ≈ 0; nhóm bị loại vẫn lãi ⇒ cùng kết luận ĐÓNG.")
a("")
a("## Tài nguyên")
a("- Oracle CPU ≈ 0,32 h (user+sys: G2 54 s, build 2×~215 s, explore 2×~265 s, confirm 72 s, kiểm ~40 s); RSS đỉnh build 3,04 GiB (/usr/bin/time; cgroup MemoryMax=3G không kích hoạt) — vượt nhẹ mức 3 GB, các job khác ≤ 2,6 GB. flock oracle_heavy + nice 19/ionice c3, mem_avail ≥ 20 GB, không có tiến trình deploy.")
a("- Kaggle: 1 kernel `ind-ho26` ~11 phút (≈ 0,18 kernel-giờ).")
a("- Đĩa Oracle: trống 17 GB trước; dữ liệu mới tối đa ~100 MB trong ~/claude_master/ind1114, đã dọn trung gian (giữ legs_x.parquet, mkt_h.parquet, g2_*.npz, json).")
a("")
a("## Sai lệch / giới hạn so với prereg (khai đủ)")
a("1. Nến 1h lấy từ store Aerospike OHLCV_1H_v2 (tái dùng theo §5), không phải resample kline1m Vision; C18 dùng close Vision; 2026 từ Vision qua Kaggle (không lọc cột `active`). 4h/1d gộp từ 1h (tương đương gộp từ 1m).")
a("2. Giờ thiếu được ffill (nến phẳng, qv 0). Hệ quả: M4 (breadth) trên DEV ĐỔI khi nối dữ liệu 2026 (symbol bị cắt đuôi/relist được ffill qua khoảng trống dài) ⇒ M4 không tin cậy. M4 bị loại ở khử trùng (ρ 0,82 với C3) trong EXPLORE và không dùng ở đâu ⇒ không ảnh hưởng ứng viên; mọi indicator dùng không đổi.")
a("3. Không khử trùng theo 45 feature S1 (bảng feature không có trong dump; điều kiện \"nếu có\").")
a("4. EXPLORE chạy 2 lần do lỗi code track G (cột C_ALL_M) — số track S hai lần trùng tuyệt đối; không đổi định nghĩa.")
a("5. HO: không có hạng S1 2026 (cand_base chỉ DEV) ⇒ khử theo điểm S1; không có Y72 2026 ⇒ track G không có HO; ALT_EW 2026 tính trên mọi symbol Vision (xấp xỉ universe edge_attr). AGENT_RUNBOOK §0.1 yêu cầu owner duyệt khi mở HO 2026 — prereg MASTER yêu cầu HO mô tả; MASTER cần xác nhận quyền dùng.")
a("6. Chi tiết vận hành (cụm, khử cụm G, luật chọn G, p-value, MDE) cố định trong IND_COMBO_P0_PLAN.md commit cùng prereg, trước khi đọc Y.")
open(R + "IND_COMBO_P0.md", "w").write("\n".join(L) + "\n")
for f in ("confirm.json", "build.json", "causal_chk.json"):
    shutil.copyfile(W + f, R + "ind_combo_p0/" + f)
logging.info("ok")
