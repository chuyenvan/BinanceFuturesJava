# RESULT — BURST_COOLDOWN (MASTER 2026-10-16)

Pre-reg `docs/prereg/PREREG_BURST_COOLDOWN.md` (4e42ef59, chốt trước code). Code 38a3e3e8, jar 108e4c69 (sim-jar-bcd). Driver `research/analysis/burst_cooldown_driver.py`. JSON `~/claude_master/1016/bcd/burst_cooldown.json` (Oracle).

## Cổng
- P0 (key vắng, A1): md5 printDone `ad26fd55` = gqsf-a1 ⇒ byte-identical PASS.
- GPU-CHK (S7 key vắng trên máy GPU): md5 `eca3d5da` = gqsf-s7 ⇒ PASS.
- Parity 24/24 kernel ON PASS (jar, key, log `[BURST-COOLDOWN]`, TOPK 24, skipFull, B0OV).

## Kết quả (8 seed, ghép cặp với gqsf-*, cửa sổ 2022–2025, MTM)
| arm | N, T | maxDD22 OFF→ON | ΔDD (CI95) G1 | CAGR22 OFF→ON | ΔCAGR G3 | Calmar22 OFF→ON G2 | UW22 | lệnh/năm | kích hoạt / chân bị chặn | GO |
|---|---|---|---|---|---|---|---|---|---|---|
| V1 | 13, 120′ | −22,55 → −9,04 | **+13,50** [10,85; 16,16] ✓ | 36,98 → 24,21 | **−12,78 ✗** | 1,65 → 3,06 ✓ | 116 → 220 | 742 → 438 | 58 / 2 503 | **KHÔNG** |
| V2 | 13, 360′ | −22,55 → −7,78 | +14,76 [11,45; 18,07] ✓ | 36,98 → 21,30 | −15,68 ✗ | 1,65 → 3,76 ✓ | 116 → 243 | 742 → 367 | 51 / 4 425 | KHÔNG |
| V3 | 6, 360′ | −22,55 → −6,62 | +15,93 [12,82; 19,05] ✓ | 36,98 → 17,06 | −19,93 ✗ | 1,65 → 3,43 ✓ | 116 → 240 | 742 → 252 | 52 / 5 402 | KHÔNG |
G4 (|dd| ≤ 40 mọi seed) đạt cả 3 arm.

## Kết luận theo pre-reg
**NO-GO cả 3 arm** (G3: CAGR mất 12,8–19,9 pp ≫ ngưỡng −3 pp). Theo §5: ĐÓNG, không thử (N, T) khác.

## Ghi nhận (không đổi kết luận)
- Đánh đổi rõ và ổn định qua 8 seed: maxDD giảm ~13–16 pp, Calmar tăng ×1,9–2,3, nhưng CAGR giảm mạnh, UW gấp đôi, số lệnh giảm 41–66 %.
- So với giảm size thuần (cắt size để CAGR còn ~24 % ⇒ DD ≈ −22,6 × 24/37 ≈ −14,7 %), V1 cho DD −9 % ⇒ cooldown cải thiện hiệu quả rủi ro thật, không chỉ giảm phơi nhiễm.
- Cooldown chặn nhiều hơn dự kiến (~43 chân/lần kích hoạt ở V1) vì K24 đánh giá lại ứng viên mỗi phút.
- Nếu owner muốn hồ sơ rủi ro thấp hơn: đây là quyết định KHẨU VỊ (như K16 vs K24), không phải GO nghiên cứu; cần pre-reg riêng + HO 2026 + port live trước khi dùng.
