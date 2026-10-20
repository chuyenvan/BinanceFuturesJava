# UP_TRIG tầng A — kết quả (2026-10-20): ĐẠT luật D+C nhưng MỎNG ⇒ chưa đủ để code sim; cần xác nhận độc lập

Prereg `docs/prereg/PREREG_UP_TRIG.md` (81f4fbf3). Raw Oracle `~/claude_master/up_trig/{ut_a.py, ut_a.json, ut_a_events.parquet, ut_a_samples.parquet, ut_a_desc.*}` (agent Opus, MASTER duyệt).

## Dữ liệu / validate
- rateUpAvg phút từ `~/marketdump/market.bin` (dump Aerospike 2026-10-14; cắt < 2026; thiếu 2,8 % phút). Format [count:int] + [ts:long][down][up][down15m] big-endian.
- V1: tính lại 20 phút từ kline1m — market.bin[t] = nến MỞ lúc t (đóng t+1'), sai số median 4,5e-6 ⇒ tín hiệu biết lúc t+1', vào close t+1' ⇒ không look-ahead. V2 x_r = ECDF 90 ngày trước t (brute-force 300 mẫu khớp). V3 giá vào/ra khớp. V4 chọn chỉ trên D.
- "Sau sập" = có phút BIG_DOWN (rateDownAvg < −0,03157) trong 24h trước (3,4 % mẫu).

## Bước 1 (cắt lớp, net %, nhóm êm, 24h)
| lớp x_r | D RISE24 / LIQ24 / BTC | C RISE24 / LIQ24 / BTC |
|---|---|---|
| d1 | +0,05 / +0,01 / +0,00 | −0,12 / −0,18 / +0,02 |
| d5 | −0,29 / −0,33 / −0,12 | −0,29 / −0,32 / −0,00 |
| d10 | +0,21 / +0,10 / +0,06 | +0,17 / +0,07 / +0,13 |
| ≥0,99 | +0,01 / −0,05 / −0,17 | **+1,16 (t 3,4)** / +1,01 / +0,44 |
| ≥0,999 | −1,29 / −1,07 / −1,01 | +1,03 / +0,92 / +0,58 |
H 1h/4h âm gần như mọi lớp (phí). D không đơn điệu (hình U yếu). Nhóm "sau sập" C rất mạnh (≥0,99 +5,05 %, ≥0,999 +8,83 %) nhưng thuộc vùng gate cũ — loại khỏi luật.

## Bước 2
Chọn trên D (12 ứng viên): **RISE24 · 24h · q 0,99** (n 382, net +0,368 %, t 1,23). Xác nhận C: n 341, net +0,709 %, median +0,38 %, t 2,07, 2024 +0,92 % (t 2,10), 2025 +0,50 % (t 0,95, median −0,34 %) ⇒ ĐẠT 4/4 điều kiện C. Corr PnL ngày với crash-buy D −0,03, C −0,11 (không trùng).

## Đánh giá MASTER (risk-first)
1. D không có ý nghĩa (t 1,23); ứng viên là MAX của 12 ⇒ thiên lệch chọn; 5 sự kiện tốt nhất = 69 % PnL D.
2. C sát ngưỡng (t 2,07; tuần 2,03; tháng 2,04), 2025 yếu (t 0,95, median âm), 3/8 quý ≈ 0/âm.
3. Phần lớn là beta: cùng sự kiện C, BTC +0,44 % ⇒ vượt BTC chỉ ~+0,27 %/sự kiện; 2024–25 là bull của BTC.
4. Không cấu trúc liều–đáp ứng ở D (q 0,999 âm, d1 ≈ d10).
5. Prior cũ: nhánh BIG_UP (rateUpAvg > 0,025) NO-GO (`RESULT_BIGUP_MEDIUPDOWN.md`, `RESULT_LEVEL_SENSITIVITY.md`: đổi dấu theo năm, p 0,63).
⇒ Kết luận: đạt luật về kỹ thuật nhưng bằng chứng KHÔNG đủ để đầu tư code simulator. Bước kế hợp lý duy nhất: xác nhận độc lập 1 lần trên HO 2026 (Jan–Aug, market.bin có tới 2026-08-13), đúng luật đã chọn, KHÔNG tune — cần owner đồng ý dùng HO. Nếu không ⇒ để dạng forward log.
