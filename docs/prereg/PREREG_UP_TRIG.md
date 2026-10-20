# PREREG UP_TRIG — Tầng A (offline): dùng rateUpAvg làm CỬA VÀO MỚI "thị trường đang tăng" cho top-K — 2026-10-20

Owner 10-20: rateDown15MAvg/rateDownAvg bắt big-down để vào; tương tự dùng **rateUpAvg** (TB return 1m của ~100 coin tăng mạnh nhất, `MarketBigChangeDetector.calMarketData`) để vào top-K khi thị trường đang tăng. Cao = tốt, thấp = xấu: phân giải (cắt lớp) rateUpAvg, đối chiếu return top-K sau đó; nếu đẹp mới làm ngưỡng rolling. Hệ cũ/shadow KHÔNG đụng; nếu đi tiếp chỉ là ứng viên v1.1. 2026 KHÔNG dùng.
Lưu ý trước: code từng có nhánh BIG_UP/SMALL_UP (đã tắt cứng) — agent tìm kết quả cũ nếu có (chỉ mô tả). `rateUpAvg` thuộc nhóm chưa kiểm look-ahead (GATE_INVENTORY) ⇒ V1 bắt buộc.

## Dữ liệu
- rateUpAvg theo phút: market.bin DEV (đọc theo `ExportMarketBinFromTicker`/`WfoDataset` format; ưu tiên bản dùng cho sim DEV gqsf). Phải kiểm: giá trị phút t tính từ nến 1m ĐÓNG tại t (không dùng nến sau).
- Giá: kline1m Vision (`~/vz_e1/raw/kline1m-YYYY-MM.parquet`, `~/claude_master/gvz/k2021/` cho 2021) cột ts, sym, close, quote_volume.
- Mẫu: phút mỗi 15' (00, 15, 30, 45) từ 2021-08-01. Khám phá D = 2021-08→2023-12; Xác nhận C = 2024-01→2025-12.

## Giỏ top-K tại phút t (trọng số đều, trừ BTC/ETH, coin có giá tại t)
- B_LIQ24: 24 coin quote_volume 24h trước t lớn nhất.
- B_RISE24: 24 coin return 1m tại t cao nhất (nhóm đang kéo rateUpAvg).
- Mô tả: BTC.
Selector S1 của K24 chỉ có điểm lúc gate mở ⇒ KHÔNG dùng (ghi giới hạn). Vào tại close t (+1 phút trễ: giá close t+1 làm giá vào), giữ H ∈ {1h, 4h, 24h}. Phí 0,10 % khứ hồi.

## Bước 1 — cắt lớp (mô tả, trên D và C riêng)
- Biến: x = rateUpAvg(t) thô, và x_r = phân vị rolling của rateUpAvg(t) trong 90 ngày TRƯỚC t (như cách gate rolling; warm-up 14 ngày).
- Chia 10 decile x_r (theo D) + đuôi riêng: x_r ≥ 0,99 và ≥ 0,999.
- Mỗi lớp × giỏ × H: n, return TB gross/net, median, win %, t-stat (sai số chuẩn theo cụm ngày).
- Tách "sau sập" (có phút BIG_DOWN hoặc chân mở crash-buy trong 24h trước t; dùng printDone gqsf-a1) vs "êm".

## Bước 2 — luật rolling (chỉ chọn trên D bằng thủ tục cố định)
- Ứng viên = (giỏ ∈ {LIQ24, RISE24}, H ∈ {1h,4h,24h}, q ∈ {0,99, 0,999}): sự kiện = phút có x_r ≥ q, bỏ trùng (cách nhau ≥ H), CHỈ nhóm "êm" (không sau sập — để không trùng gate cũ).
- Chọn trên D: ứng viên có return net TB/sự kiện lớn nhất trong các ứng viên có ≥ 50 sự kiện và net TB > 0. Không có ⇒ ĐÓNG.
- Xác nhận trên C với đúng ứng viên đó: net TB > 0, t-stat > 2, dương ở cả 2024 và 2025, ≥ 30 sự kiện. Đạt ⇒ viết prereg tầng B (sim/vốn, tương tác với crash-buy). Trượt ⇒ ĐÓNG (không thử q/H/giỏ khác).
- Mô tả kèm: tương quan PnL theo ngày của ứng viên với crash-buy (gqsf-a1) trên D và C.

## Validate
V1 look-ahead rateUpAvg: tính lại rateUpAvg từ kline1m cho 20 phút ngẫu nhiên theo đúng công thức (100 coin tăng mạnh nhất, cap 4/5 universe, bỏ coin >+30 %), khớp market.bin (sai số nhỏ cho phép do universe; báo). V2 x_r chỉ dùng dữ liệu < t. V3 giá vào là close t+1, ra close t+1+H. V4 không dùng C để chọn.

## Ước lượng trước (MASTER): P(qua) ~10 %. Lý do: phút rateUpAvg cao thường là nhịp bật sau sập (đã thuộc gate cũ) hoặc pump ngắn; momentum alt đã NO-GO nhiều lần.
