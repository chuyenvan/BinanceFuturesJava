# PREREG ENTRY_CONFIRM — Tầng A (chẩn đoán offline, sàng lọc) — 2026-10-20

Owner 10-20: thử hướng 3 "chờ nhịp bật xác nhận rồi mới vào" thay vì mua đúng phút gate mở. Hệ cũ/shadow KHÔNG đụng; nếu đi tiếp chỉ là ứng viên v1.1.

## Câu hỏi tầng A
Luật xác nhận có PHÂN BIỆT được cụm lệnh lỗ (sập 2 nhịp, time-stop) với cụm lãi không, và ước lượng thô ΔPnL có đủ lớn để đáng làm tầng B (sửa simulator Java, 8 seed) không? Tầng A KHÔNG phải kết luận GO cho chiến lược.

## Dữ liệu (đóng băng)
- Lệnh: DEV K24+skipFull phí gốc `~/kaggle_sim/out/gqsf-{a1,s7,s13,s21,s99,s123,s777,s2024}/storage/printDone.csv` (2021-07→2025-12), đọc bằng `reset_rule_score.load_legs` + `load_legs_minute` (như TS_AFTER).
- Giá: close 1m Binance Vision qua `gvz_mtm.month_close(ym)` (import gvz_mtm trước reset_rule_score).
- Cụm = các chân cùng (sym, m1) (đóng cùng phút). Chân mở = chân có m0 nhỏ nhất của cụm. M = m0 chân mở; P0 = entry chân mở; N0 = margin chân mở; PnL cụm = Σ pnl.

## Luật xác nhận R(c, W)
Sau M: L_t = min close trên (M, t]; xác nhận tại phút t đầu tiên, M < t ≤ M+W, có close_t ≥ L_t·(1+c) VÀ close_t > 0. Giá vào mới Pc = close_t. Không xác nhận trong W ⇒ cụm BỎ.
- **A1 (chính): c = 2 %, W = 4h.**
- A2 (mô tả): c = 1 %, W = 1h. A3 (mô tả): c = 3 %, W = 24h.
Chỉ A1 dùng để quyết định; A2/A3 chỉ báo cáo (không chọn arm tốt nhất).

## Chỉ số (mỗi seed, mỗi arm)
- skip_rate = % cụm bị bỏ; PnL_skip = Σ PnL cụm bỏ; PnL/cụm bỏ vs PnL/cụm xác nhận; % cụm time-stop (status STOP_LOSS_DONE) trong nhóm bỏ vs nhóm xác nhận.
- lost = Σ_{xác nhận} N0·(Pc/P0 − 1) (dương = vào đắt hơn; âm = vào rẻ hơn).
- ΔPnL_thô = −PnL_skip − lost. Theo năm (năm của M, +07) 2022–2025.
- Giới hạn biết trước (ghi vào result): bỏ qua DCA neo lại theo Pc, đường thoát mới, hiệu ứng vốn/slot/quota (path divergence) ⇒ chỉ là sàng lọc.

## Luật đi tiếp tầng B (A1, TB 8 seed) — TẤT CẢ phải đạt
- D1 skip_rate trong [5 %, 60 %].
- D2 PnL/cụm bỏ < PnL/cụm xác nhận ở ≥ 6/8 seed VÀ PnL_skip < 0 ở ≥ 6/8 seed.
- D3 ΔPnL_thô TB > +8 000 USD/seed, ≥ 6/8 seed dương, ≥ 3/4 năm 2022–25 dương.
Trượt bất kỳ ⇒ ĐÓNG hướng 3 (không thử c/W khác). Đạt ⇒ viết prereg tầng B (pending-entry trong simulator, P0 parity, 8 seed, MTM Vision, luật GO kiểu TS_MKT_EXT) trước khi code.

## Validate
V1 số cụm và ΣPnL mỗi seed khớp TS_AFTER/ISO (cùng load_legs). V2 P0 so close(M) Vision: |P0/close_M − 1| trung vị < 0,2 %. V3 không thiếu giá (cụm thiếu close trong cửa sổ ⇒ đếm, phải < 1 %).
