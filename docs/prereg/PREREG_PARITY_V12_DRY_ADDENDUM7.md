# PREREG_PARITY_V12_DRY — ADDENDUM 7: lấp ngày 2026-10-28 bằng REST (2026-11-03, TRƯỚC khi tải)

Gốc: ADD3 (299f00b0) … ADD6 (4d8bc2a7). Sự kiện: Vision KHÔNG có klines 1m ngày 2026-10-28 (UTC) ở cả monthly (file 2026-10 = 43 200 dòng,
khe 1 441 phút từ 10-27 23:59) lẫn daily (404), kiểm BTC/SOL 11-03. `gs-tk26` vì vậy ERROR (miss 20261028). MASTER chọn (b′) 11-03.

1. **Nguồn 10-28 (UTC 00:00–23:59):** `GET https://fapi.binance.com/fapi/v1/klines?interval=1m` (nến đã đóng từ lâu), gọi TỪ ORACLE
   (không Kaggle — IP có thể 451; không 242). Universe = danh sách symbol có klines monthly 2026-10 trong `universe_by_month.json` của
   `gs-x26-q4`. Lưu đúng dạng Vision: `{S}-1m-2026-10-28.zip` chứa `{S}-1m-2026-10-28.csv` có header Vision, 12 cột theo thứ tự REST.
   Đóng gói dataset Kaggle private `gst-kline-1028`; kernel x26-q4 nạp các file này cho ngày 10-28 (các ngày khác giữ Vision monthly).
2. **Giới hạn gọi:** ≤ 300 weight/phút (đọc header `X-MBX-USED-WEIGHT-1M`, ngủ khi chạm); 1 luồng; HTTP 429 hoặc 418 ⇒ DỪNG NGAY, không thử lại.
3. **Cổng tương đương R (đo TRƯỚC khi tải 10-28):** tải REST ngày 2026-10-27 cho BTCUSDT, ETHUSDT, SOLUSDT, PARTIUSDT, BLESSUSDT; so với
   Vision daily 2026-10-27 trên các cột exporter dùng (`_parse`: open_time, open, high, low, close, quote_volume = cột 0,1,2,3,4,7):
   ĐẠT ⇔ trùng TỪNG BYTE chuỗi giá trị cả 1 440 dòng × 6 cột × 5 symbol. Báo thêm (không quyết định): trùng float32. TRƯỢT ⇒ DỪNG, không dùng REST.
4. Funding (monthly 2026-10) và metrics daily 10-28: Vision đã có ⇒ dùng Vision.
5. Mọi tiêu chí V-OVL (ADD4) và luật re-seed (ADD6) giữ nguyên.
