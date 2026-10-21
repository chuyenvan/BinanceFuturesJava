# AUDIT_2020_FEASIBILITY — chạy toàn hệ (gói v1.1) trên 2020 (mẫu niêm phong): khả thi?

Ngày 2026-10-21, agent kiểm toán (chỉ metadata). **Không đọc/tải bất kỳ giá/giá trị nào của 2020**: chỉ S3 ListObjects của
`data.binance.vision` (tên file, kích thước, ngày sửa) + đọc tài liệu repo. Không mở dataset/kernel `bcast-*`, không mở
`~/kaggle_sim/sealed/`. Script: `docs/result/audit_1021/vision_ls.py`; số máy đọc: `docs/result/audit_1021/vision_2020_meta.json`.

## Kết luận (rủi ro trước)

1. **Kho 2020 ĐÃ ĐƯỢC DỰNG** (agent BCAST 10-12, pre-reg `596c1ef8`, `docs/result/bcast/BCAST_BUILD.md`): ticker 1′, market.bin,
   store gate 33 cột, pred p15 × 8 seed, net015 × 4 fold, bins × 4, S1, feat_v2, funding.bin; P3-DET 387/387 + 19/19 md5 trùng;
   dataset private `chuyendinh/bcast-2020-2021h1-p1`; sim kỹ thuật `bcast-tech` (B0) đã chạy, printDone niêm phong chưa ai đọc.
   Kho chưa từng được mở (sổ §5 `docs/plan/BACKCAST_RESERVOIR.md` chỉ có dòng dựng kho). ⇒ Không cần dựng dữ liệu mới.
2. **Gói v1.1 = K24 + skipFull + X14 (TS_MKT_EXT ALT_EW)**. Nền `k24` của kho (B0 + `SELECTOR_RANK_TOPK=24` +
   `GATE_QUOTA_SKIP_WHEN_FULL=true`) **chính là v1.1 trừ X14**. Phần thiếu duy nhất: danh sách ngày cờ X14
   (`SIM_LOSER_TS_EXT_DAYS`) cho 2020 + jar sim có X14. Cả hai dựng được từ dữ liệu đã có trong kho (Vision 1′, 80 symbol).
3. **Không dựng được cho 2020**: OI (5 cột OI net015, `ls_global`/`rk_oi_delta24h` của S1) — Vision `metrics` 2020 chỉ có
   BTCUSDT từ 2020-09-01 (122 file), mọi symbol khác bắt đầu ≥ 2021-12; file ghim OI `e3887f63` không có hàng < 2021-01-01
   ⇒ **NaN 100 % kho** (đã khai BCAST §3b). `bookDepth` bắt đầu 2023-01-01 (hệ không dùng). Còn lại dựng đủ.
4. **Khả thi kỹ thuật: CÓ** (≈ 0,5–1 ngày agent + ≈ 2–3 h Kaggle). **Nhưng KHÔNG đủ làm "bài kiểm xác nhận cuối"** cho
   v1.1: universe 11 → 80 symbol (cửa sổ chấm 05..12: 25 → 80) so với DEV 117–600 ⇒ K24 ≈ toàn universe đầu kho (H-A
   k24-vs-b0 gần như không phân biệt), OI NaN toàn kho (lệch phân phối net015/S1 so với lúc train), chế độ 2020 (bull) khác
   DEV, X14 có thể **0 ngày cờ** trong cửa sổ chấm (không biết trước khi mở — tính cờ là đọc giá 2020). Pre-reg kho đã chốt:
   "kho YẾU, bằng chứng PHỤ, KHÔNG thay holdout; PASS = ủng hộ phụ, FAIL = cờ vàng". Dùng được đúng vai đó, mở **1 lần**.

## 1. Dữ liệu Vision UM 2020 (S3 listing, 2026-10-21)

| Loại | 2020 có? | Chi tiết (chỉ metadata) |
|---|---|---|
| klines 1m monthly (`futures/um/monthly/klines`) | **Có** | 81 symbol có ≥ 1 tháng 2020; theo tháng 01..12: **11, 24, 24, 24, 25, 30, 37, 43, 62, 71, 78, 80**; tổng 676 MB zip; LastModified 2021-06-14..06-28; 2021-01: 89 symbol. Daily 1m cũng có (BTCUSDT 366 file 2020) |
| fundingRate monthly | **Có** | per tháng 11, 23, 24, 24, 25, 30, 37, 43, 62, 71, 77, 80; cùng tập 81 symbol với klines; thiếu tháng lẻ: QTUMUSDT 2020-02, LENDUSDT 2020-11 (khớp BCAST §4); BTCUSDT bắt đầu 2020-01 |
| metrics (OI 5m, long/short ratio) daily | **Gần như không** | toàn bộ 1 038 symbol: sớm nhất 2020-09-01 và **chỉ BTCUSDT** (122 file 2020); các symbol khác bắt đầu ≥ 2021-12 |
| bookDepth daily | **Không** | 1 008 symbol, sớm nhất 2023-01-01 |
| aggTrades monthly | Có | 81 symbol, 17,7 GB (2020) |
| premiumIndex / markPrice / indexPrice klines 1m | Có (BTCUSDT kiểm) | 12 file 2020 mỗi loại, bắt đầu 2020-01 |
| spot klines 1m (USDT) | Có | 245 cặp có file 2020 (86 đủ 12 tháng) — hệ futures-only không cần |

## 2. Đối chiếu input của hệ (gói v1.1)

| Thành phần | Input cần | 2020 | Ghi chú / sai khác so với hệ thật |
|---|---|---|---|
| Gate p15 — 33 feature V3FULL (momentum×6, vol×5, breadth×5, rsi/volSpike/distMA20, funding×3, thời gian×4, basket×4) | kline 1′ toàn universe, `market_data_object` (momentum1M/15M ← `calMarketData` trên kline), funding 8h | **Dựng được** (BCAST: 526 620 dòng, NaN 0) | universe nhỏ ⇒ rổ top-50 % chỉ 5–40 coin ⇒ breadth/basket lệch phân phối train; 2020-01-01 không có lead-in ⇒ warm-up. Model: kho dùng 8 seed cut20260101 (recipe DEV), KHÔNG phải `fold_20` live — đúng quy ước DEV (OOS WFO); muốn đúng model live phải predict thêm bằng `fold_20` (ngoài mẫu với 2020, làm được predict-only) |
| GateRollingRatio (q 90 ngày) | chuỗi p15 90 ngày | Dựng được | đầy bộ đệm ~2020-05-01 ⇒ cửa sổ chấm bắt đầu 05-01 (pre-reg) |
| S1 selector — 9 feature (feat_v2 KEEP9) | CLOSES_1H, OI (`ls_global`, `rk_oi_delta24h`) | **Thiếu OI** (NaN) | 7/9 dựng được; 2 cột OI NaN toàn kho |
| net015 (Tool1) — 45 feature | kline, funding, md, OI #41–45 | **Thiếu OI** (NaN) | 40/45 dựng được; live hiện cũng đọc OI từ set khác (V11 §6.2 "OI #41–45 = NaN ở cả hai" trong harness) — cần đo trên DEV tỉ lệ NaN OI lúc train để biết lệch bao nhiêu |
| TS_MKT_EXT X14 — ALT_EW | close 1′ mọi symbol trừ BTC/ETH, cờ ngày = DD 31 ngày ≤ −30 % | **Dựng được** từ ticker kho (≤ 78 alt) | chỉ số EW trên 9–78 alt (DEV hàng trăm) ⇒ nhiễu/biên độ khác; cần 31 ngày đầu ⇒ cờ từ ~2020-02 |
| Universe / DIED_SYMBOLS / lifecycle | lọc LIVE + mapper 863 | Dựng được (BCAST §4) | loại LENDUSDT, BTCSTUSDT (ngoài mapper); Vision có thể thiếu symbol huỷ niêm yết trước 2020 (không kiểm được, cấm REST) |
| Seed lịch sử 2000′ (live `initData`) | 2000 phút trước start | Không áp dụng cho sim | sim replay liên tục từ 2020-01-01; live-only |
| Thanh khoản (quoteVolume, lọc volume, sizing) | kline qv | Dựng được | aggTrades có nếu cần mô hình trượt giá; bookDepth không có |
| Sửa collector v1.1 (snapshot/inline md/died source) | — | Không áp dụng | thay đổi đường LIVE cho khớp backtest; sim vốn là đường backtest |

## 3. Cần dựng gì để chạy v1.1 trên kho (ước công)

1. Pre-reg `docs/prereg/PREREG_BCAST_V11.md` (commit TRƯỚC): giả thuyết E0 (mean ΣPnL_S > 0, ≥ 6/8 seed) + Δ ghép cặp vs nền
   cùng kho; cấu hình v1.1 = nền `k24` + X14 (`SIM_LOSER_TS_EXT_DAYS` tính trong kernel từ ticker kho bằng `tsx_flags.py`,
   luật S7–S9 `docs/plan/V11_TS_MKT_EXT_LIVE.md`); scorer commit cùng. Khai trước: nếu 0 ngày cờ trong 2020-05..12 ⇒ X14 no-op,
   kho chỉ kiểm K24+skipFull. (~1–2 h)
2. Jar sim có X14 (`sim-jar-tsx`) + parity trên kho khi X14 tắt: md5 printDone == `bcast-tech` `2b7ded8f…` (chỉ so md5, không mở
   file). (~1 h + 1 kernel)
3. Nền chuẩn (bắt buộc chạy cùng lần mở đầu): b0, k24 × {phí gốc, stress 0,005} × 8 seed = 32 kernel; v1.1 × 2 × 8 = 16 kernel.
   `bcast-tech` 132 s/kernel; giới hạn 2 kernel đồng thời ⇒ ≈ 2–3 h Kaggle.
4. (Tuỳ chọn, đề xuất) trước khi mở kho: đo trên DEV độ nhạy với OI = NaN (net015/S1) để biết kho 2020 có còn đo đúng hệ không.
   Không đụng 2020. (~2–3 h)

Tổng ≈ **0,5–1 ngày agent + 2–3 h Kaggle**. Mở kho tiêu 1 lần cho họ ý tưởng K24/X14.

## 4. Lệnh bị chặn

Không có. S3 listing chạy từ Oracle (không REST Binance, không 242).
