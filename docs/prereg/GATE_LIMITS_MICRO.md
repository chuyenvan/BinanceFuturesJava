# GATE_LIMITS_MICRO — giới hạn và khác biệt ĐÃ BIẾT khi bật MICRO (owner đọc và chấp nhận ở câu hỏi YES của golive_micro_on)

Tài liệu này được chép nguyên văn vào gate file. Mỗi dòng là một điều CHƯA được kiểm hoặc một khác biệt live so với sim mà micro vẫn chạy.
Nguồn: audit go-live 11-16 (`~/claude_master/v12/AUDIT_GOLIVE_1116_{A,B,C,D}.md`, `AUDIT_LEGACY_DCA_1116.md`), prereg replay
`PREREG_E2E_REPLAY_V12.md` §7 và các errata `PREREG_E2E_REPLAY_V12_ERRATA1.md`, `PREREG_E2E_REPLAY_V12_ERRATA2.md`,
`PREREG_E2E_REPLAY_V12_ERRATA3.md`, `PREREG_E2E_REPLAY_V12_ERRATA4.md`.

## 0. Ngoại lệ owner đã chấp nhận (ADD23, 2026-11-17)
- 0.1. Phép thử replay (iii) theo đúng chữ prereg gốc là FAIL do tiêu chí E2 (so với log dry thật 11-05): 23/23 khớp coin + phút + thứ tự, 22/23 khớp cỡ lệnh trong 1e-4, AINUSDT lệch 1,35e-4 (35,2176 so với 35,2224 USDT). Audit độc lập: nguyên nhân là bộ replay thiếu dữ liệu trong phút (cache equity 60 s, giá realtime), không phải lỗi jar. Owner chấp nhận cho MICRO ngày 2026-11-17; KHÔNG áp dụng cho PILOT.
- 0.2. Các tiêu chí logic của replay (cấu hình, chọn coin, cỡ leg, DCA tổng hợp, thoát lệnh, chặn coin chưa chốt, không lỗi) đều PASS so với bản tính độc lập. DCA grid tự nhiên KHÔNG xảy ra trong cửa sổ replay: đường DCA mới chỉ được kiểm bằng đường giá tổng hợp.

## A. Phép thử replay (iii) KHÔNG phủ
- A1. Không so với sim engine: không có sim A3 cho năm 2026. Kỳ vọng CAGR 37,7 % / maxDD −22,7 % chỉ đúng tới 2025-12-30. So với sim trên dữ liệu 2026 là điều kiện trước PILOT.
- A2. Vòng main không chạy trong replay: các guard của createOrderBuyRequest0, sổ giấy twin, liveBookFull, sizing theo price_realtime.
- A3. X14 (hoãn time-stop 336 h) tắt trong replay; BIG_DOWN không có trong ngày replay; tierMul gắn 1.
- A4. Dữ liệu replay (Vision) sạch hơn dữ liệu live: không rớt WS, không giá cũ.

## B. Khác biệt live so với sim
- B1. Trailing xử lý theo nhịp trong nến (nhịp exit 10 s): live có thể kích hoạt trailing và khớp stop, hoặc dời SL, trong cùng một phút; sim chờ nến sau. Trên dữ liệu thử 10-30: 4/22 lệnh thoát sớm 1 phút, giá thoát lệch từ −0,26 % tới +0,45 %.
- B2. Ngưỡng gate live chặt hơn sim khoảng 20 % (q live ≈ 0,0095, sim ≈ 0,0075–0,0079) vì buffer gate còn dữ liệu hỏng ngày 30/10 và mới có 46/90 ngày. Hệ quả: ít lệnh hơn sim. Sửa cùng lần đổi jar trước PILOT.
- B3. Vốn tính size = min(C3_CAPITAL, equity theo mark, cache 60 s): lỗ thì size giảm như sim, lãi thì KHÔNG tăng size (sim lãi kép).
- B4. Điều kiện thị trường và ALT_EW ở live tính trên universe A1; sim không lọc A1.
- B5. Giá thoát live thấp hơn sim trung bình khoảng 0,40 % do stop làm tròn xuống theo tick.
- B6. Mọi leg là 2,25 % vốn × (1 − mức dùng vốn / 0,6); leg dưới 5 USDT hoặc dưới min notional của coin bị bỏ (BUDGET_SMALL), không báo Telegram. BTC (min 50 USDT) không vào được ở vốn nhỏ.

## C. Rủi ro vận hành còn mở
- C1. Bước "bỏ qua khi sổ đầy" (skipFull) trên live đọc mức dùng vốn của SỔ GIẤY. Sổ giấy có thể bị tín hiệu DCA của LEGACY thêm leg ngoài lưới; sổ giấy đầy thì lệnh vào thật bị chặn. Theo dõi hằng ngày; sửa gốc cần đổi jar.
- C2. Nhịp thoát dùng giá realtime không kiểm tuổi giá; giá cũ tới ~18 s xảy ra khoảng 10–15 lần/ngày (stop trên sàn theo MARK_PRICE vẫn kích hoạt đúng).
- C3. Đỉnh equity của kill-switch không reset khi đổi C3_CAPITAL: HẠ vốn khi đang chạy sẽ bị coi là sụt giảm lớn và đóng hết vị thế. Không đổi vốn khi chưa có hướng dẫn của MASTER.
- C4. Sau crash hoặc reboot 242, bot tự lên lại ở chế độ LIVE và mở lệnh mới mà không cần duyệt.
- C5. Giám sát: một kênh Telegram; không có dead-man switch (Oracle hoặc cron chết thì không ai báo); RAM 242 còn ~2 GB không có cảnh báo.
- C6. Trước khi trailing kích hoạt, vị thế c3 không có stop trên sàn (thiết kế đã duyệt).
- C7. Lệnh bị sàn từ chối hoặc đóng lỗi chỉ ghi log và được monitor quét (không có Telegram trực tiếp từ JVM).
- C8. Chưa có lệnh thật nào đi qua jar này bằng key tài khoản con trước micro: micro chính là phép thử đầu tiên.

## D. Thước đo
- D1. Harness parity chưa cài ADD21 / ADD22: (ii) và smoke được chứng nhận bằng biên bản tay của MASTER.
- D2. Parity hằng ngày không so sizing, DCA, exit với sim; phép thử duy nhất cho các phần đó là replay (iii).
- D3. Cỡ mẫu micro dự kiến không đủ để kết luận thống kê về trượt giá vào / thoát (G-PILOT).

## E. Dừng khẩn cấp
- E1. Dừng mở lệnh mới: `MODE=drain bash <OPS>/golive_live_off.sh` (không đóng vị thế).
- E2. Đóng vị thế: app Binance → tài khoản phụ → đóng toàn bộ vị thế và lệnh chờ. Chạy E1 TRƯỚC, nếu không bot có thể mở lại.
