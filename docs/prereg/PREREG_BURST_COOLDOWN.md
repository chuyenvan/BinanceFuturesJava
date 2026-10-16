# PRE-REG — BURST_COOLDOWN (ngắt mạch sau đợt lớn của selector)

> MASTER 2026-10-16. Commit này đi TRƯỚC commit code và TRƯỚC mọi số đo. Nền: `docs/result/BURST_RISK_1016.md`, `docs/plan/VZ_NEXT_1016.md` §R1 (branch research/vz-e1 e0514dc5).

## 0. Giả thuyết + cơ chế
Hệ vào lệnh theo "đợt" (nhiều chân PREDICT_SYMBOL_TRADE cùng một phút) khi tín hiệu p15 mức thị trường vượt gate. Đợt lớn = ~20 coin tương quan ≈ 1, đặt 26–36 % equity margin. Trong ngày sụp đổ hệ thống (2022-05-05: 3 đợt trong 41′, ~−14,8 % equity) các đợt kế tiếp đợt lớn là bắt dao rơi lặp lại.
H: chặn chân PREDICT mới trong T phút sau một đợt ≥ N chân giảm maxDD MTM mà không làm giảm Calmar.

## 1. Định nghĩa (cố định)
- Chỉ áp cho chân `PREDICT_SYMBOL_TRADE` mở mới (không DCA-signal, không NSEL core-add). **BIG_DOWN và DCA_LEVEL1 KHÔNG bị chặn và KHÔNG được đếm** (bằng chứng cũ: BIG_DOWN là cơ chế cứu đợt underwater — `PREREG_CONCENTRATION_SAFETYCAP.md` §0).
- Đếm: số chân PREDICT THỰC SỰ mở trong cùng phút (sau mọi cổng: gate, budget, tier). Khi đếm chạm N trong phút m ⇒ cooldown tới hết phút m + T phút. Các chân còn lại của chính phút m vẫn được mở.
- Chặn: chân PREDICT ở phút khác phút kích hoạt, có thời điểm < hết cooldown ⇒ bỏ (đặt SAU gate ⇒ buffer gate rolling không đổi; TRƯỚC budget).
- Key sim: `SIM_BURST_COOLDOWN_N` (int), `SIM_BURST_COOLDOWN_MIN` (int phút). Thiếu một trong hai hoặc ≤ 0 ⇒ tắt ⇒ byte-identical.

## 2. Biến thể (đúng 3, K = 3)
| arm | N | T |
|---|---|---|
| V1 | 13 | 120′ |
| V2 | 13 | 360′ |
| V3 | 6 | 360′ |

## 3. Thực thi
- Jar: branch `feat/burst-cooldown` từ `128290af` (nguồn jar `sim-jar-gqsf` sha 0944841c) ⇒ dataset `sim-jar-bcd`.
- Baseline (OFF) = 8 run có sẵn `gqsf-{a1,s7,s13,s21,s99,s123,s777,s2024}` (K24 + GATE_QUOTA_SKIP_WHEN_FULL=true, profile r4_kg0_k16_f015_g155 + B0OV). ON = cùng cấu hình + key của arm, cùng pred/seed.
- Cổng parity P0: jar mới, key vắng, seed A1 ⇒ md5 printDone PHẢI = `gqsf-a1`. FAIL ⇒ dừng, không chạy ON.
- Unit test lớp `BurstCooldown` (đếm, kích hoạt, chặn, phút kích hoạt không bị chặn, tắt ⇒ không chặn).
- Kaggle ≤ 2 kernel; 24 kernel ON.

## 4. Thước (cửa sổ 2022-01-01 → 2025-12-30, rebase 2021-12-31, MTM như `gate_skipfull_driver.score`)
Ghép cặp theo seed, Δ = ON − OFF, n = 8, t(0,975; 7) = 2,3646.

## 5. Luật GO (mỗi arm; chốt trước)
- G1 rủi ro: mean Δ dd_mtm22 ≥ +2,0 pp (bớt âm) VÀ cận dưới CI95 t ghép cặp > 0.
- G2 hiệu quả: mean Calmar22 ON ≥ mean Calmar22 OFF.
- G3 chi phí: mean Δ CAGR22 ≥ −3,0 pp.
- G4 an toàn: mọi seed |dd_mtm| ≤ 40 %.
GO arm ⇔ G1–G4 đều đạt và đủ 8 seed hợp lệ. Nhiều arm GO ⇒ chọn Calmar22 trung bình cao nhất. Không arm nào GO ⇒ ĐÓNG, không thử (N, T) khác.

## 6. Báo kèm (không quyết định)
Số lần kích hoạt và số chân bị chặn mỗi năm; Σ PnL của chân OFF nằm trong cửa sổ bị chặn; theo năm; ngày 2022-05-05, 2022-11-09, 2025-03-02, 2025-10-10/11.

## 7. Nếu GO
Không deploy. Bước sau: (a) chạy arm thắng trên HO 2026 (Vision) chỉ báo cáo; (b) port live (DetectEntrySignal2TradeNormal) + parity; (c) owner duyệt.
