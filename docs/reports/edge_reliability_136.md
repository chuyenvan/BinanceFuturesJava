# TASK-136 — Điều tra độ tin cậy edge (nghi edge đo sai) — 2026-07-06

**Bối cảnh:** entry-probe cho thấy hệ sống nhờ ~9567 lệnh funding-selector hiếm (0.1% tín hiệu lọt gate).
Nghi edge là artifact. Chạy backtest toàn kỳ, phân tích 4 kiểu "đo sai".

## Kết quả (nhánh PRED = funding-selector, 9567 lệnh, toàn kỳ 2021-2026)
### K1 — Tập trung coin/tháng: LÀNH ✅
- 518 coin khác nhau; **top 5 coin chỉ 13.4% PnL** (không phụ thuộc vài coin).
- 44/64 tháng có lệnh (phủ rộng, không dồn 1 giai đoạn).

### K4 — Phân bố thời gian: LÀNH ✅
- **19/21 quý dương**, trải đều 2021Q1→2026Q1. Chỉ 2022Q2 (-714) và 2023Q1 (-7) âm.
- Không quý nào gánh tất → không phải artifact 1 giai đoạn.

### K3 — Win/loss payoff: CHẤP NHẬN ĐƯỢC ✅
- win-rate 46.2%, payoff ratio 1.8 (lãi TB thắng 5.5 / lỗ TB thua 3.0).
- max 1 lệnh +218, thua đậm nhất -281 (không có cú thua nuốt trọn tài khoản → KHÔNG phải bẫy martingale điển hình).

### K2 — Tập trung PnL: 🚩 CỜ ĐỎ
- **top 1% lệnh (95) gánh 63.5% PnL. Bỏ top 5% → PnL ÂM (-5150). Bỏ top 10% → -9656.**
- Nghĩa: ~5% lệnh trúng đậm gánh toàn bộ lãi; 95% còn lại LỖ RÒNG.

## KẾT LUẬN
Edge KHÔNG phải artifact (K1/K4 loại leak + may rủi tập trung: lãi trải đều 518 coin, 19/21 quý).
NHƯNG là **edge đuôi phải cực lệch**: hệ long-vol bắt pump lớn — mất tiền đều, thắng lớn hiếm bù lại.
- Bản chất khớp thiết kế (pump/dump selector): số ít coin pump mạnh mang lãi lớn.
- Rủi ro: mong manh với tương lai. Nếu tần suất/biên độ pump lớn giảm → hệ thành lỗ.
- Gate MOM15 CHÍNH LÀ bộ lọc giữ các cú đuôi phải (A/B: tắt gate = cháy) → tinh chỉnh gate qua range là đúng hướng.

## HÀM Ý CHO QUYẾT ĐỊNH (Uni về đọc)
1. Đổi range + WFO VẪN đáng làm (K1/K3/K4 lành, gate là bộ lọc đuôi phải hợp lệ). ĐÃ tiến hành theo lệnh Uni.
2. NHƯNG cờ đỏ K2 nghĩa là: đừng kỳ vọng "PnL đều" — hệ này bản chất lời-thưa-lỗ-đều. Cần chấp nhận
   drawdown chuỗi dài giữa các cú trúng, và quản vốn để sống qua chuỗi lỗ tới cú pump kế.
3. Câu hỏi mở cho Uni: đây có phải hồ sơ rủi ro chấp nhận được không? Nếu có → tối ưu tiếp. Nếu muốn PnL đều hơn →
   cần edge thứ 2 bổ sung (khác đuôi phải), không phải tinh chỉnh cái hiện có.
