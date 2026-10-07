# PREREG_K32_CONFIRM — phép thử XÁC NHẬN arm `l2-k32` (K32, pct 0,999915, skipFull ON)

Ngày 2026-10-07. MASTER chốt thiết kế; agent thực thi. Commit file này TRƯỚC khi đẩy kernel; không đổi sau khi thấy số.
Nền tảng: docs/audit/AUDIT_GKF_PHASE1_20261007.md (1f9e0e2f), research/analysis/gkf_rescore.py (cùng commit).

## 1. Lý do
- `gkf-l2-k32` được chọn HẬU KIỂM từ 13 arm GATE_K_FRONTIER trên seed 42 (vòng l2 ngoài pre-reg) ⇒ seed 42 bị nhiễm chọn lọc,
  KHÔNG dùng để quyết. Mẫu xác nhận = seed 7 và seed 21 (pred.bin ngoài tập chọn). Seed 42 chỉ báo cáo.
- Số seed 42 đã biết (base): ΔCAGR22 +4,14pp, ΔPnL22–25 +12,7k; stress: ΔCAGR22 +1,35pp, ΔPnL −157;
  Calmar22 MTM 1,558 vs 1,662 (stress 1,155 vs 1,369); maxDD22 −26,34 vs −22,21.

## 2. Arm / nền (2 kernel Kaggle, cost 0 trong sim)
| seed | arm (tag mới) | nền (có sẵn) | pred |
|---|---|---|---|
| 7 | `k32c-s7` | `gqsf-s7` (K24 pct 0,999950829 ON) | dataset gate-abl-seed7, md5 b737fb6d64d198c14654ea9c92510b36 |
| 21 | `k32c-s21` | `gqsf-s21` (K24 pct 0,999950829 ON) | dataset gate-sb-s21, md5 0b541d2259b31cf2794160e0aeafa3ff |
| 42 (báo cáo) | `gkf-l2-k32` | `gqsf-a1` | pred gốc bundle |
- Profile r4_kg0_k16_f015_g155 + override y hệt `gkf-l2-k32` (result.json): SIM_GATE_ROLLING_MODE=ratio, DAYS=90,
  SIM_GATE_ROLLING_PCT=0.999915000, TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03,
  GATE_QUOTA_SKIP_WHEN_FULL=true, SELECTOR_RANK_TOPK=32.
- Jar dataset `sim-jar-shadow2` sha256 20d412e8…; bundle sim-x1-2021-bundle + ticker wfo; sim_end_date 20251231; xmx 22g.
- Kernel = tools/kaggle_sim.py HEAD (md5 8b60b00a…, guard NOWRITE242) + khối pred_ds (gate_ablation_driver.template()).
- Ghi chú jar: nền gqsf-s7/s21 chạy jar sim-jar-gqsf (0944841c); tương đương với shadow2 ở cấu hình nền đã kiểm ở seed 42
  (gkf-nen [shadow2] md5 printDone == gqsf-a1 [gqsf] == ad26fd55…). Không chạy lại nền seed 7/21 (ngân sách 2 kernel).

## 3. Parity (VOID nếu trượt, được chạy lại 1 lần)
jar sha 20d412e8; ok=true; date_last 20251230; symbol_mapper ≥ 800; prof_run có TOPK=32, PCT=0.999915000, skipFull=true,
B0OV đúng; log có `SELECTOR_RANK_TOPK=32 `, `BAT: mode=ratio pct=<f32>`, `[GATE-QUOTA] SKIP_WHEN_FULL=ON`;
pred_md5_used == md5 trong bảng §2; dòng `md5 verified` khớp nền cùng seed. Ghi md5 printDone, n, eq.

## 4. Thước (y hệt gkf_rescore.py; script research/analysis/k32_confirm.py chỉ gọi lại hàm của nó)
- MTM phút (reset_rule_score.run_mtm, phí legacy as-is, cửa sổ 2022+): CAGR22 (equity ngày b+unP), maxDD22 MTM phút,
  Calmar22 = CAGR22/|maxDD22|, UW22, n/năm, % ΣPnL lệnh 0h, ΣPnL top10 ngày, maxDD toàn kỳ.
- STRESS COST_TRUTH: mỗi chân vào nến 1m quyết định (lag xác định bằng khớp entry==close như gkf_rescore, tính trên nền
  từng seed) có close/open−1 ≤ −1% ⇒ giá vào +1,675%, PnL −1,675%×notional; báo % chân vào nến sập.
- Ghép cặp theo seed (arm vs nền cùng seed, cùng mức phí): ΔCAGR22 = MTM ngày paired block-10d NREP 2000 seed 20260905
  (selector_ablation_driver.daily_boot); ΔPnL = n700_driver.pnl_boot. CI95 RAW; k = 1 (một giả thuyết xác nhận, không inflate).
- Theo năm 2022–2025 (ΔROI pp, equity ngày) và ex-2022 (ΔCAGR23). Base VÀ stress.
- Tự kiểm: seed 42 (gkf-l2-k32, gqsf-a1) phải tái tạo đúng số AUDIT_GKF_PHASE1_20261007.json (gkf-l2-k32 / gkf-nen);
  nền seed 7/21 khớp docs/result/gate_skipfull.json ON_S7 / ON_S21 (các trường chung). Lệch ⇒ DỪNG, không báo số.

## 5. Luật GO (cố định; TẤT CẢ phải đạt, quyết chỉ trên seed 7 và 21)
1. ΔPnL22–25 STRESS > 0 ở CẢ seed 7 và 21 (điểm ước lượng).
2. Calmar22 MTM STRESS arm ≥ 0,90 × nền ở cả 2 seed.
3. maxDD MTM (toàn kỳ và 2022+) ≥ −40% mọi seed, base và stress.
4. Trung bình (seed 7, 21) ΔROI năm bản STRESS ≥ 0 ở ≥ 3/4 năm 2022–2025.
5. ΔPnL22–25 BASE > 0 ở cả 2 seed.
Thiếu 1 ⇒ NO-GO ⇒ giữ nền K24 (pct 0,999950829, skipFull ON). CI raw báo kèm, không thay luật.
GO ở đây = đủ điều kiện đề xuất bước tiếp (shadow/review MASTER), KHÔNG tự động triển khai.

## 6. Kỳ vọng khai trước (MASTER)
mean ΔCAGR22 (seed 7/21) base +0…+3pp, stress −1…+1pp; P(GO) 10–15%.

## 7. Phạm vi / ràng buộc
DEV ≤ 2025-12-31 (2026 niêm phong). 0 sửa Java, 0 build, 0 sim trên Oracle, 0 chạm 242/shadow_c3.
Kaggle: tối đa 2 kernel song song tính cả session khác cùng tài khoản; đầy ⇒ chờ (poll 5'), không huỷ kernel người khác.
Kết quả: docs/result/RESULT_K32_CONFIRM.md + docs/result/k32_confirm.json.
