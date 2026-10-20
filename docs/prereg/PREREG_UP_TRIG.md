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


---

## ADDENDUM 1 (2026-10-20) — xác nhận HOLDOUT 2026 (9 tháng), viết TRƯỚC khi tính bất kỳ số 2026 nào

Owner 10-20 duyệt: chạy luật đã chọn trên 2026-01-01 → 2026-09-30, 1 lần, không tune.

1. **Luật đóng băng (từ tầng A, 4a2ba2bb):** giỏ RISE24 (24 coin return 1m tại t cao nhất, trừ BTC/ETH/BTCDOM/USDC, bỏ > +30 %), giữ 24h, vào close t+1', ra close t+1'+24h, phí 0,10 % khứ hồi; sự kiện = mẫu 15' có x_r ≥ 0,99 (x_r = ECDF rateUpAvg trong 90 ngày trước t), chỉ nhóm "êm", bỏ trùng trong 24h.
2. **Nguồn rateUpAvg/rateDownAvg 2026:** `~/marketdump/market.bin` tới hết dữ liệu (2026-08-13); phần sau đó TÍNH LẠI từ kline1m Kaggle `vz-kline1m-2026` theo đúng công thức đã kiểm V1 (open-time t). Kiểm chồng lấn: tính lại cho 2026-07-01..08-12 và so với market.bin (báo median/max sai số, corr; và tỉ lệ mẫu đổi trạng thái x_r ≥ 0,99). Lookback 90 ngày đầu 2026 dùng market.bin 2025.
3. **"Sau sập" 2026:** có phút rateDownAvg < −0,03157 trong 24h trước HOẶC chân BIG_DOWN trong printDone `~/kaggle_sim/out/ho4-k24-b-s42/storage/printDone.csv`.
4. **Giá:** kline1m 2026 từ Kaggle (tải từng tháng về Oracle, xoá sau khi dùng); mẫu có t+1'+24h > 2026-09-30 23:59 bị bỏ.
5. **Kết luận (TB net mỗi sự kiện, t-stat cluster theo ngày):**
   - CONFIRM: n ≥ 20 VÀ net TB > 0 VÀ t ≥ 1,65 VÀ TB (RISE24 − BTC cùng sự kiện, gross) > 0.
   - REJECT: net TB ≤ 0.
   - Còn lại: INCONCLUSIVE.
   Báo thêm (mô tả): theo tháng, nhóm "sau sập" 2026, bỏ top-5 sự kiện.
6. CONFIRM ⇒ viết prereg tầng B (sim, tương tác vốn với crash-buy). REJECT/INCONCLUSIVE ⇒ ĐÓNG UP_TRIG (không đổi giỏ/H/q).
