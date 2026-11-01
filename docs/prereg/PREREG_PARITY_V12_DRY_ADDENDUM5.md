# PREREG_PARITY_V12_DRY — ADDENDUM 5: klines DAILY thay monthly cho 2026-10 (2026-11-01, TRƯỚC mọi tính toán)

Gốc: ADD3 (299f00b0), ADD4 (feb32107). MASTER duyệt 11-01 để kịp hạn 11-03 11:00. Lúc viết: Vision 2026-10 funding monthly = 200, klines monthly = 404, klines daily 10-30 = 200, 10-31 = 404 (kiểm 2026-11-01 08:01 UTC). Chưa có số A/C nào.

1. **Nguồn klines 2026-10:** khi klines monthly 2026-10 chưa phát hành, exporter dùng klines **daily** Vision (trường `days` của cfg x26, URL `.../daily/klines/{s}/1m/{s}-1m-{d}.zip`), các tháng trước vẫn monthly. Nếu monthly 2026-10 phát hành trước khi push kernel x26-q4 thì dùng monthly.
2. **Điều kiện tương đương (cổng E, đo TRƯỚC khi push):** trên tháng mẫu 2026-09 (có cả monthly lẫn daily), 5 symbol BTCUSDT, ETHUSDT, SOLUSDT + 2 alt nhỏ chọn cố định trước: PARTIUSDT, BLESSUSDT. Với mỗi symbol: nối các dòng dữ liệu (bỏ dòng header nếu có) của 30 file daily theo thứ tự ngày, so với các dòng dữ liệu của file monthly. ĐẠT ⇔ trùng TỪNG BYTE cả 5 symbol. Không trùng ⇒ DỪNG, không dùng daily.
3. **T_cut** giữ 2026-11-01 00:00 +07 ⇒ cần daily 2026-10-31 (chờ Vision phát hành); không push x26-q4 khi chưa có.
4. Mọi tiêu chí V-OVL (ADD4) giữ nguyên.
