# PRE-REG — GATE_SEEDBAND (Pha B chương trình GATE)

- Ngày chốt: 2026-10-04, TRƯỚC mọi retrain/pred.bin/sim của vòng này. Không đổi arm/luật/thước sau khi thấy số.
- Nền: RESULT_GATE_ABLATION.md (7308504a), GATE_INVENTORY_20261004.md (886312a4), driver `research/analysis/gate_ablation_driver.py` (a629ff6f) — tái dùng nguyên hàm `retrain` (cùng script/fold/purge 15'/hyperparam XGB, 33 feature V3FULL, `label_oldbasket`), chỉ đổi `random_state`.
- Tham chiếu A1 = B0@K24 (`~/kaggle_sim/out/n700-a1`, printDone md5 d9abf35f, n 3526; pred.bin gốc md5 5dd6bb4c = seed 42). Seed 7 = `gabl-seed7` (pred md5 b737fb6d, printDone 8f5e2912) — có sẵn, không chạy lại.
- Ràng buộc: 0 sửa .java, 0 build, 0 Java sim trên Oracle; sim chỉ Kaggle, kernel = `tools/kaggle_sim.py` HEAD (md5 8b60b00a, NOWRITE242) + khối chèn `pred_ds` y nguyên vòng GATE_ABLATION; ≤ 2 kernel song song. Dữ liệu ≤ 2025-12-31 (feature/nhãn cắt `< 2026-01-01 +07`). Chế độ tiết kiệm đĩa (df trước mỗi bước ghi lớn; < 500 MB ⇒ dừng).

## 1. Câu hỏi
- Q1 Dải nhiễu seed gate model: phân bố CAGR22 / Calmar22 / maxDD / UW / ΔPnL trên 8 seed; A1 (seed 42) ở z nào?
- Q2 BAG8 (trung bình p15 thô của 8 seed) có ổn định hơn 1 seed (tập phút gate-mở, tập lệnh) không, và nằm đâu trong phân bố seed?
- Q3 Timing: gate thật có hơn null giữ tự tương quan (NULL-BLOCK) không?

## 2. Arm (CỐ ĐỊNH, tổng 8 kernel K24)
| arm | p15 | tag Kaggle | dataset |
|---|---|---|---|
| S13, S21, S99, S123, S777, S2024 | retrain `GA.retrain` seed ∈ {13,21,99,123,777,2024}; ghi thô (không map) vào các phút OOS fold; phút ngoài fold (420 phút cuối, 2026-01-01 00:00–06:59 +07) giữ p15 gốc | gsb-s13 … gsb-s2024 | chuyendinh/gate-sb-s13 … |
| BAG8 | trung bình số học (float64 → float32) 8 chuỗi p15 thô: 42 = p15 pred.bin gốc (đúng chuỗi A1 dùng), 7 = pred_SEED7 (gabl), 6 seed mới. Không map, không trọng số khác | gsb-bag8 | gate-sb-bag8 |
| NULLB | p15 gốc; chỉ phút ts < 2026-01-01 00:00 +07; khối = floor((ts − ts_đầu)/30 ngày); hoán vị thứ tự khối `numpy.random.default_rng(20261004).permutation(n_khối)`; ghép giá trị các khối theo thứ tự hoán vị rồi đặt tuần tự lên các vị trí ts gốc (ts/risk giữ nguyên); phút ≥ 2026 giữ p15 gốc. Dự báo: ΔCAGR22 −15…−30pp | gsb-nullb | gate-sb-nullb |

Seed 42 (A1) và seed 7 (gabl-seed7) KHÔNG chạy lại. KHÔNG thêm arm, KHÔNG thử trọng số bag khác, KHÔNG thử số seed khác.

## 3. Cổng
- G0 format: mỗi pred.bin n = 2 500 260, header/size như gốc, `ts` + `risk4h` byte-identical, p15 hữu hạn (hàm `GA.g1`). md5 điền sau (commit bổ sung md5 TRƯỚC khi đẩy kernel).
- G1: pearson p15 mỗi seed mới vs seed 42 (pred.bin gốc) theo từng fold (19 fold) ≥ 0,97. Thấp hơn ⇒ ghi, KHÔNG loại.
- G2 quota: n lệnh/năm (đóng 2022–2025) và phút gate-mở/năm (phút phân biệt có ≥ 1 entry PREDICT_SYMBOL_TRADE, 2022–2025) trong [0,75; 1,25]× A1 (732 / 146,5). Seed trượt G2: vẫn vào dải (là phương sai tự nhiên của recipe), đánh dấu. BAG8 trượt ⇒ "không diễn giải" BAG8. NULLB trượt ⇒ Q3 "không diễn giải được" (như RND).
- Parity từng run: jar sha 7368be46, mapper ≥ 800, `SELECTOR_RANK_TOPK=24` + B0OV trong prof_run, `pred_md5_base` = 5dd6bb4c, `pred_md5_used` = md5 arm, log Java "md5 verified". Trượt ⇒ run VOID.

## 4. Thước (cố định)
- Cửa sổ 2022-01-01..2025-12-30, MTM ngày rebase 2021-12-31 (hàm `N.arm_metrics`, MTM `R.run_mtm` cost legacy) — y nguyên GATE_ABLATION. Chỉ số: CAGR22, maxDD = `dd_mtm22` (MTM, cửa sổ 2022+; báo kèm `dd_mtm` toàn kỳ), Calmar22 = CAGR22/|dd_mtm22|, UW22 (ngày), PnL 2022–25 (lệnh đóng), n/năm, phút gate-mở/năm.
- Ghép cặp vs A1 (chỉ báo cáo): bootstrap lợi suất NGÀY MTM block 10 ngày, NREP 2000, seed 20260905 (`SAD.daily_boot`) cho ΔCAGR22; ΔPnL theo ngày đóng (`N.pnl_boot`). Inflate half-width × √(2 ln k), k = 8 (6 seed mới + BAG8 + NULLB) = 2,039. Báo theo năm + theo quý.
- Dải seed = 8 seed {42 (A1), 7 (gabl-seed7), 13, 21, 99, 123, 777, 2024}: mean, sd (ddof=1), min, max, median cho CAGR22, Calmar22, dd_mtm22, UW22, ΔPnL vs A1 (ΔPnL A1 = 0). z(A1) = (A1 − mean)/sd.
- Ổn định: (a) Jaccard tập phút gate-mở (2022–2025) cặp đôi giữa 8 seed (TB 28 cặp) và Jaccard(BAG8, seed_i) TB 8; (b) Jaccard lệnh (sym|phút vào, lệnh vào 2022–2025) tương tự. NULLB vs A1 báo cáo.
- BAG8 percentile trong dải = 100 × #{seed: giá trị ≤ BAG8}/8 (cho CAGR22, Calmar22, dd_mtm22 (âm: cao hơn = tốt), PnL).

## 5. Luật diễn giải (cố định)
- Q1: z(A1) trên CAGR22 ≥ +1 ⇒ "A1/B0 may mắn ở tầng gate; kỳ vọng recipe = mean". |z| < 1 ⇒ "A1 điển hình của recipe". z ≤ −1 ⇒ "A1 kém hơn kỳ vọng recipe". Báo z cho các chỉ số khác (chỉ báo cáo).
- Q2: "BAG8 ổn định hơn 1 seed" ⇔ Jaccard phút TB(BAG8, seed_i) > Jaccard phút cặp đôi TB seed (Jaccard lệnh báo kèm). Ứng viên deploy (chỉ đề xuất, owner quyết) ⇔ BAG8 CAGR22 ≥ median seed AND |dd_mtm| ≤ 40 AND |dd_mtm22| ≤ 40 AND Calmar22 ≥ 0,9 × median Calmar22 seed AND Jaccard phút TB(BAG8, seed_i) > Jaccard phút cặp đôi seed AND BAG8 đạt G2. Không có cổng "BAG8 > A1".
- Q3 (NULLB phải đạt G2): CAGR22_NULLB < min(seed) − sd(seed) ⇒ "gate có giá trị timing"; min ≤ CAGR22_NULLB ≤ max ⇒ "timing không đo được"; còn lại (giữa min − sd và min, hoặc > max) ⇒ "không kết luận" (báo cáo).
- Không tune. Mọi thứ ngoài pre-reg = chỉ báo cáo.

## 6. md5 pred.bin (điền sau khi sinh, commit bổ sung TRƯỚC khi đẩy kernel)
| arm | md5 pred.bin | G0 | spearman vs gốc | G1 pearson/fold min / median (fold < 0,97) |
|---|---|---|---|---|
| S13 | `cd6d7b2ed05b9ad326358717fdbdd842` | PASS | 0.9962 | 0.9836 / 0.9935 (0) |
| S21 | `0b541d2259b31cf2794160e0aeafa3ff` | PASS | 0.9953 | 0.9786 / 0.9932 (0) |
| S99 | `5ef90e928cd4f5a7aa55c4b88a1b6bd1` | PASS | 0.9968 | 0.9766 / 0.9938 (0) |
| S123 | `9b1dad9051c3d72b8bba8c0f547623f9` | PASS | 0.9958 | 0.9788 / 0.9935 (0) |
| S777 | `25f738f752d4ed195ac42bd5075c9e94` | PASS | 0.9959 | 0.9797 / 0.9936 (0) |
| S2024 | `3be4fac48ab8b9e2fcec45a3f45417e4` | PASS | 0.9970 | 0.9888 / 0.9933 (0) |
| BAG8 | `8bad71a4c9b816b0e3f2efe5e1472c9f` | PASS | 0.9984 | — |
| NULLB | `0939a4cba68e09dd985bda85354976f3` | PASS | 0.0326 | — |

Thành phần BAG8: 42 = `5dd6bb4c3f98d89d58770005c0001526` (pred.bin gốc), 7 = `b737fb6d64d198c14654ea9c92510b36`, + 6 seed trên. NULLB: 58 khối 30 ngày (khối cuối 26 ngày), rng 20261004.

## 7. Tái lập
`research/analysis/gate_seedband_driver.py` (retrain / bag / nullb / g0 / upload / submit / fetch / parity / score); artefact `~/claude_master/1004/gsb/`; Kaggle out `~/kaggle_sim/out/gsb-*`.
