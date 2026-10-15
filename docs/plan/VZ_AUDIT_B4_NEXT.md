# VZ_AUDIT_B4_NEXT — rà lại kết quả B4 NO-GO + hàng đợi giả thuyết mới (MASTER 2026-10-15)

## 0. Luật rà soát (chốt TRƯỚC khi rà — commit file này trước khi chạy bất kỳ kiểm nào)
- Rà soát chỉ được phép làm mất hiệu lực lần chạy Q6 nếu tìm ra LỖI THỰC THI hoặc LỖI DỮ LIỆU theo đúng các tiêu chí A–D dưới đây (kiểm được, có số). Khi đó: sửa lỗi, chạy lại Q6 đúng MỘT lần với cùng pre-reg (như luật "chạy lại khi lỗi hạ tầng").
- Không có lỗi ⇒ NO-GO giữ nguyên. Cấm: đổi chân trời, đổi biên quintile, đổi định nghĩa sự kiện/feature, bỏ năm, tách regime để "cứu" B4.
- Mọi kiểm ghi `docs/result/VZ_AUDIT_B4.md` (bảng PASS/FAIL + số), commit.

## A. Tái lập — kiểm quan trọng nhất
A1. Chạy `e1_confirm.py` với đúng pre-reg B4 nhưng `--years 2024` (năm khám phá, cờ `--audit-2024` để guard cho phép, ghi rõ không phải xác nhận) ⇒ phải ra lại đúng B4 2024 của T9: spread net_1440 −0,01306 (bản sau sửa phí: mức dịch nhưng spread giữ), mono −1,00, n 65 886. Lệch > 1e-9 ⇒ FAIL (runner xác nhận ≠ code khám phá) ⇒ lỗi thực thi.
A2. So code đường đi: diff logic tính `tss_reversal`, cụm 30′, net_1440 giữa `e1_t9.py` (khám phá) và `e1_confirm.py` (xác nhận). Liệt kê mọi khác biệt.

## B. Dữ liệu năm xác nhận
B1. Cột taker: phân phối `taker_buy_quote/quote_volume` (median, p1, p99) theo THÁNG 2021-12→2025-12 và 2024; tỉ lệ dòng có taker_buy_quote = 0 hoặc = quote_volume. Nhảy bậc đột ngột giữa các tháng ⇒ nghi đổi định dạng nguồn ⇒ điều tra.
B2. Đơn vị thời gian: số file/tháng có ts micro giây đã đổi (2025+) — kiểm khớp outcome: với 1 000 sự kiện ngẫu nhiên mỗi năm, close(ts+1440′) đọc trực tiếp từ zip/parquet bằng tay = giá runner dùng.
B3. Thứ tự cột kline theo năm (file có/không header) — kiểm 5 file/năm: cột 10/11 đúng là taker_buy_volume/taker_buy_quote.
B4. Số sự kiện: 2022 38 049 · 2023 36 626 · 2024 65 886 · 2025 153 973. Giải thích bằng số symbol active/tháng và số sự kiện/symbol; 2025 gấp 4 lần 2023 phải có nguyên nhân (listing tăng? biến động?) — nếu do một nhóm symbol rác (stale, volume giả) ⇒ ghi lại.
B5. Anomalies: số dòng bị loại theo năm.

## C. Định nghĩa / thống kê
C1. Biên quintile 2024 áp lên từng năm: % sự kiện mỗi quintile theo năm (lý tưởng ~20%). Lệch mạnh (vd quintile cao chỉ 5%) ⇒ ghi là giới hạn thiết kế (KHÔNG đổi biên).
C2. Outcome thiếu: tỉ lệ sự kiện bị bỏ vì không có close +1440′ (gỡ niêm yết trong 24h) theo năm × quintile — nếu tập trung ở quintile cao ⇒ thiên lệch sống sót, ghi lại.
C3. Cụm sự kiện cùng phút (sập toàn thị trường): phân phối số sự kiện/phút theo năm; spread khi chỉ lấy 1 sự kiện/phút (báo kèm, KHÔNG dùng để quyết).
C4. Bootstrap: xác nhận block theo ngày UTC 5 ngày, NREP 2000, seed đúng pre-reg.

## D. Pre-reg
D1. Kiểm commit pre-reg (997f18f3) có trước thời điểm chạy Q6 (log time) và nội dung YAML = markdown.
D2. Ghi nhận (không phải lỗi): 24h là chân trời được CHỌN vì mạnh nhất ở khám phá ⇒ thiên lệch chọn — đã nở CI theo k = 38.

## E. Hàng đợi giả thuyết mới (sau khi A–D xong)
Nguyên tắc: năm xác nhận 2022/2023/2025 đã dùng 1 lần ⇒ mọi xác nhận sau nở CI theo K = tổng số phép thử trong ledger tại thời điểm chạy (hiện 50 + mới). 2021 = phụ. Mỗi ứng viên cần CƠ CHẾ rõ trước khi đo.

**E1 — đi thẳng xác nhận (đã có kết quả 2024, pre-reg từng cái trước khi chạy):**
- C1-AGE (trên CHÂN CỦA HỆ, không phải sự kiện thô): T9/Q2 2024 net 240′ của chân giảm đơn điệu theo tuổi symbol (0–7 ngày +4,22 % → >90 ngày +1,31 %). Cơ chế: coin mới đang tìm giá ⇒ biên độ hồi lớn hơn. Dữ liệu xác nhận: ledger chân EXEC DEV 2022/2023/2025 (`ll_h2/leadlag_h2_legs.csv.gz`, có close_M) + tuổi từ `vz-symbols` (dựng sau Phase 1c) hoặc first_date trong lake. GO: spread (0–7 ngày) − (>90 ngày) net 240′ > 0 gộp với CI nở theo K, mỗi năm > 0, mono < 0 theo tuổi.
- C2-DOI60 (sự kiện thô, 4h): B1 2024 −0,54 % [−0,96; −0,14]. Cùng họ với B4 đã chết ⇒ ưu tiên thấp; chỉ chạy nếu owner muốn "kiểm nốt".

**E2 — họ khám phá mới trên 2024 (≤ 8 biến thể/họ, config commit trước, ghi ledger), outcome net 60′/240′/24h, trên CẢ sự kiện crash thô VÀ chân của hệ:**
- H-G sập hệ thống vs sập riêng lẻ: sự kiện cùng phút BTC ret ≤ −1 % (hoặc ≥ 20 % symbol cùng sập) vs sập đơn lẻ. Cơ chế: cú sốc thanh khoản toàn thị trường hồi, cú sốc thông tin riêng (tin xấu) đi tiếp.
- H-H sập kèm volume cực lớn vs volume thấp (volume z 60′ quintile). Cơ chế: bán tháo cưỡng bức (capitulation) hồi; sập trên thanh khoản mỏng không có người mua.
- H-I đã bơm trước khi sập: ret 24h / 7 ngày trước sự kiện quintile. Cơ chế: pump-and-dump đang xả thì không hồi; coin đã giảm sâu thì hồi.
- H-J giờ/ngày: phiên Á/Âu/Mỹ, cuối tuần. Cơ chế: thanh khoản mỏng cuối tuần ⇒ vượt đà mạnh hơn ⇒ hồi mạnh hơn. (rủi ro data-mining cao ⇒ tối đa 4 biến thể)
- H-K funding dấu × sập ở 24h (H-B chỉ đo 60′): funding dương lớn khi sập = long đông bị thanh lý ⇒ hồi.
Sau E2: chọn ≤ 2 ứng viên có cơ chế + đơn điệu + ổn định theo quý 2024 ⇒ pre-reg xác nhận (K cộng dồn).

## F. Thứ tự
A → B → C → D (báo kết luận rà soát) → E1 C1-AGE pre-reg (MASTER duyệt nội dung trước khi chạy) → E2 khám phá → báo. Song song Phase 1 / P2 / P3 như cũ.
