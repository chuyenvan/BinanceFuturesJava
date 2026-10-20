# UP_TRIG — xác nhận HO 2026 (9 tháng) — kết quả 2026-10-20: **INCONCLUSIVE ⇒ ĐÓNG** (addendum 1 §6)

Prereg addendum 1 `docs/prereg/PREREG_UP_TRIG.md` (0205d8f3). Raw Oracle `~/claude_master/up_trig/{ut_ho.py, ut_ho.json, ut_ho_events.parquet, ut_ho_samples.parquet}` (agent Opus, MASTER duyệt). 1 lần, không tune.

## Validate
- Nguồn rateUpAvg/rateDownAvg: market.bin tới 2026-08-13 08:12 + 70 067 phút tính lại từ kline1m Kaggle `vz-kline1m-2026`. Chồng lấn 2026-07-01..08-12: rateUpAvg sai số median 1,9e-5, corr 0,997; chỉ 6/4 128 mẫu 15' đổi trạng thái x_r ≥ 0,99 khi thay nguồn.
- x_r brute-force 300 mẫu khớp; giá vào/ra khớp parquet; "sau sập" 3,35 % mẫu; thiếu giá coin 1,35 % (cao hơn DEV, universe 2026 nhiều coin inactive).

## Kết quả (RISE24 · 24h · x_r ≥ 0,99 · êm · bỏ trùng 24h)
| Chỉ số | Giá trị | Ngưỡng CONFIRM |
|---|---|---|
| n | 133 | ≥ 20 ✔ |
| net TB | +0,003 % (gross +0,10 %) | > 0 ✔ (sát 0) |
| median / win | −0,21 % / 49,6 % | |
| t_cl ngày | 0,01 | ≥ 1,65 ✘ |
| RISE24 − BTC (gross) | −0,05 % (t −0,15) | > 0 ✘ |
Theo tháng: 01 −1,29 · 02 +0,43 · 03 −0,46 · 04 +1,60 · 05 +0,28 · 06 +0,23 · 07 −0,75 · 08 −0,38 · 09 +0,49 (%). Bỏ top-5: −0,49 %. Không bỏ trùng: −0,28 % (t −0,89). Baseline RISE24 24h mọi mẫu 2026: −0,16 %. Nhóm "sau sập" 2026: 9 sự kiện, +0,44 %, t 0,18 (không thấy hiệu ứng mạnh như C 2024–25).

## Kết luận
Luật hoà vốn trên dữ liệu mới, thua BTC ⇒ INCONCLUSIVE ⇒ ĐÓNG UP_TRIG (không đổi giỏ/H/q). Nhất quán với đánh giá tầng A: phần dương 2024–25 chủ yếu là beta bull + vài sự kiện lớn, không phải edge của rateUpAvg.
