# RESULT_RANK_MARGIN — size leg SELECTOR giảm dần theo rank k (linear, trên C2 = K24 + skipFull)

Ngày 2026-10-05 (GMT+7). Pre-reg `docs/prereg/PREREG_RANK_MARGIN.md` (commit **8b6c902d**, chốt TRƯỚC). Code branch `feat/rank-margin` (KHÔNG merge). Driver `research/analysis/rank_margin_driver.py`. Số máy `docs/result/rank_margin.json`.
Ràng buộc giữ: 0 Java sim trên Oracle (chỉ `mvn -o test` + build), 0 chạm 242/shadow_c3, 0 merge, DEV ≤ 2025-12-30, Kaggle ≤ 2 song song.

## 0. KẾT LUẬN (rủi ro trước)
**NO-GO.** Dynamic margin theo rank (linear) KHÔNG cải thiện risk-adjusted return, và KHÔNG tăng n. Cụ thể:
1. **Calmar22 gần như phẳng** trên cả 3 mức α: 1,662 (α=0) → 1,668 / 1,654 / 1,649. Biên ≤ +0,006 là NHIỄU (nhỏ hơn nhiều so với nhiễu seed ±5pp CAGR đã đo ở GATE_ABLATION).
2. **maxDD22 cạn dần nhưng đổi ~1:1 bằng raw return**: −22,21 → −21,00 → −20,05 → −18,87, trong khi CAGR22 tụt −1,88 / −3,74 / −5,78 pp ⇒ cắt rủi ro bằng đúng cái giá cắt lợi nhuận, không có "ăn ít hơn mà ngon hơn".
3. **n/năm GIỮ NGUYÊN ~740** (738 / 740 / 740): vẫn mở đủ 24 slot, chỉ size nhỏ hơn ⇒ lever này không sinh thêm lệnh (mục tiêu n của owner) cũng không tăng edge/lệnh.
4. **2022 ROI CẢI THIỆN** (6,51% → 9,31 / 10,01 / 10,56%) — đúng hướng, vì cắt margin rank thấp đúng lúc sập 2022; NHƯNG đổi lại 2023–2025 tụt đều (68,99→52,50 · 47,68→37,66 · 32,05→27,26).
⇒ Giả thuyết "rank 17–24 kém hơn hẳn về risk-adjusted ⇒ cắt nó nâng Calmar" **KHÔNG được xác nhận**: nếu rank thấp thật sự kém per-unit-risk, cắt sâu hơn phải NÂNG Calmar; thực tế Calmar phẳng.

## 1. Định danh + parity
| mục | giá trị |
|---|---|
| key | `SIM_RANK_MARGIN_ALPHA` (Cfg/Configs, default 0); check_cfg_gateway OK |
| test | `mvn -o test` 240/0 fail |
| class diff (HEAD a5e347a5 vs branch) | đúng 2 class: `Configs`, `SimulatorMarketLevelTicker1MStopLoss` |
| jar | sha256 `d9be91111c7d214ebcc200b1cb50a54e7a57e58a91a9a3328edbeaa56c55fc3f`, dataset `sim-jar-rm` |
| P0 (α=0, C2) | md5 printDone **ad26fd55f0bb5db32038ec8b357cf8e7** ⇒ byte-identical `gqsf-a1` PASS |
| 3 arm parity | `rm-a1-300/500/700` PASS 3/3 (jar, topk24, skipfull, alpha, b0ov, pred md5 verified) |

## 2. Kết quả (seed A1, C2 = K24 + skipFull)
| metric | α=0 (C2) | α=0.3 | α=0.5 | α=0.7 |
|---|---|---|---|---|
| CAGR22 (%) | 36,90 | 35,02 | 33,17 | 31,12 |
| ΔCAGR22 (pp) | — | −1,88 | −3,74 | −5,78 |
| maxDD22 MTM (%) | −22,21 | −21,00 | −20,05 | −18,87 |
| Calmar22 | 1,662 | 1,668 | 1,654 | 1,649 |
| UW22 (ngày) | 117,3 | 117,3 | 117,3 | 117,3 |
| n/năm | 736 | 738 | 740 | 740 |
| ΣPnL 2022–25 (USDT) | 104 461 | 95 582 | 87 453 | 79 016 |
| 2022 ROI (%) | 6,51 | 9,31 | 10,01 | 10,56 |
| 2023 ROI (%) | 68,99 | 62,21 | 57,58 | 52,50 |
| 2024 ROI (%) | 47,68 | 43,98 | 41,04 | 37,66 |
| 2025 ROI (%) | 32,05 | 30,08 | 28,53 | 27,26 |

## 3. Luật GO (pre-reg §5) — KHÔNG ĐẠT
| luật | yêu cầu | đo | kết |
|---|---|---|---|
| C1 | n/năm ≥ 700 | 738–740 | ĐẠT |
| C2 | maxDD22 không sâu hơn C2 (−22,21) VÀ Calmar22 ≥ C2 (1,662) | maxDD ĐẠT (−21,00/−20,05/−18,87); Calmar: 1,668 ĐẠT / 1,654 TRƯỢT / 1,649 TRƯỢT | **TRƯỢT** |
| C3 | ROI 2022 ≥ C2 (6,51%) | 9,31 / 10,01 / 10,56 | ĐẠT |
| **GO** | cả 3 | C2 trượt ở α=0,5 & 0,7 | **NO-GO** |

## 4. Diễn giải + đề xuất
- Lever này là "de-risk 1:1": tắt dần margin rank thấp chỉ thu nhỏ toàn bộ sổ, Calmar không nhúc nhích. Không phải "dồn vốn vào rank cao ăn edge tốt hơn" như giả thuyết.
- Điểm sáng duy nhất = 2022 (bear) nhẹ lại; nếu owner chỉ muốn giảm nhạy cảm năm bear, đây là 1 knob — nhưng đổi bằng CAGR mọi năm.
- Ghi nhận hạn chế: (1) 1 seed A1 — chưa đo phương sai seed; (2) `printDone.csv` KHÔNG xuất cột rank ⇒ chưa đo được ΣPnL theo rank-band 1–8/9–16/17–24 như pre-reg §5 đã khai (ghi rõ: thiếu trường, không suy đoán). Muốn đo rank-band phải thêm export selRank vào printDone (pre-reg riêng).
- **Đề xuất:** đóng hướng dynamic-margin-linear. Nếu muốn khai thác "rank 17–24 kém", hướng đúng hơn là **đo rank-band PnL thật** (thêm cột rank vào printDone, 1 vòng pre-reg) rồi quyết cắt/giữ rank bằng chứng, thay vì quét công thức mù.

## 5. Tái lập
`python3 research/analysis/rank_margin_driver.py jards | p0 --code-sha 8b6c902d | submit --code-sha 8b6c902d | fetch | score`.
