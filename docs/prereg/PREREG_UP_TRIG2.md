# PREREG UP_TRIG2 — Tầng A (offline): cùng sự kiện rateUpAvg, đổi GIỎ / K (top-K nhỏ hơn, K theo độ mạnh, selector S1) — 2026-10-20

Bối cảnh: UP_TRIG (RISE24/24h/q0,99/êm) đạt D+C mỏng, HO 2026 INCONCLUSIVE ⇒ đóng (dd3384ce). Owner 10-20: có thể do K quá lớn (rateUp yếu thì K nhỏ hơn) hoặc giỏ không dùng selector phù hợp. Đây là tìm kiếm HẬU KIỂM sau khi đã thấy HO trượt ⇒ HO 2026 đã cháy cho họ này: chỉ báo 2026 dạng MÔ TẢ, KHÔNG dùng để quyết định; nếu qua ⇒ chỉ forward paper log (không đưa vào hệ).

## Cố định (như UP_TRIG)
Mẫu 15', rateUpAvg từ market.bin (+ tính lại sau 2026-08-13 như addendum UP_TRIG), x_r = ECDF 90 ngày trước t, nhóm "êm" (không BIG_DOWN / crash-buy 24h trước), bỏ trùng 24h, giữ H = 24h, vào close t+1', ra close t+1'+24h, phí 0,10 % khứ hồi, trừ BTC/ETH/BTCDOM/USDC. D = 2021-08→2023-12, C = 2024–2025. Tái dùng `~/claude_master/up_trig/ut_a.py`.

## Biến thể (5, cố định trước)
- V1 RISE5: 5 coin return 1m tại t cao nhất; sự kiện x_r ≥ 0,99.
- V2 RISE10: 10 coin; x_r ≥ 0,99.
- V3 S1REX10: 10 coin điểm S1 REX cao nhất của ngày UTC (t) − 1 (`~/claude_master/rex/pred_s1.parquet`, từ 2022-01; D của V3/V4 bắt đầu 2022-01); x_r ≥ 0,99.
- V4 S1REX24: 24 coin S1 REX; x_r ≥ 0,99.
- V5 RISE_SCALED (K theo độ mạnh): sự kiện x_r ≥ 0,95; K = 5 nếu 0,95 ≤ x_r < 0,99, K = 24 nếu x_r ≥ 0,99 (giỏ RISE).

## Luật
- Chọn trên D: biến thể có net TB/sự kiện lớn nhất trong các biến thể có ≥ 50 sự kiện và net TB > 0. Không có ⇒ ĐÓNG họ UP_TRIG.
- Xác nhận C (đúng biến thể đó): net TB > 0 VÀ t_cl ngày > 2 VÀ dương cả 2024 và 2025 VÀ ≥ 30 sự kiện VÀ TB (giỏ − BTC cùng sự kiện, gross) > 0.
- Đạt ⇒ chỉ đề xuất forward paper log (không sim, không vào hệ). Trượt ⇒ ĐÓNG họ UP_TRIG vĩnh viễn (không thử K/giỏ/q/H khác).
- Mô tả (không quyết định): cả 5 biến thể trên D, C và 2026; bỏ top-5; theo năm.

## Validate
V1 giỏ đúng (in 3 sự kiện mỗi biến thể); V2 S1 REX dùng ngày t−1 (không look-ahead); V3 sự kiện V1–V4 trùng tập sự kiện UP_TRIG gốc (cùng x_r/êm/bỏ trùng); V4 không dùng C/2026 khi chọn.
