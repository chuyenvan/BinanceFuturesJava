# TASK-009: Aggregate nến 15m + 4h cho BTC/ETH (từ kline_1m_opt)

- **status:** DONE (historical) — 15m+4h BTC/ETH aggregate từ kline_1m_opt → `kline_15m_btceth`/`kline_4h_btceth` (226+242), validate recompute PASS. Forward-rolling chưa bật (chờ golive).
- **owner:** Claude Code (CCD) · **updated:** 2026-06-13
- **Liên hệ:** ADR-0010 (feature gate dùng BTC/ETH đa khung) + REBUILD_ROADMAP (prerequisite golive: nến 15m/4h). Độc lập task 007/008.

## Mục tiêu
Tạo nến **15m** + **4h** cho **BTC + ETH**, AGGREGATE TỪ `kline_1m_opt` (KHÔNG fetch Binance riêng). Phục vụ feature đầu tàu (ADR-0010: SMA/alignment/regime/momentum đa khung của BTC & ETH).

## Vì sao aggregate, KHÔNG fetch riêng (đã chốt)
Fetch 15m/4h riêng từ Binance → nến có thể lệch nến tự gom (cách chốt biên, làm tròn) → **train (gom) ≠ serve (gom/fetch) = skew**. Gom từ chính 1m ta đang có → train/serve cùng một nguồn, không skew.

## Quy tắc aggregate (chốt)
1 nến 15m = gom 15 nến 1m; 1 nến 4h = gom 240 nến 1m (hoặc 16 nến 15m).
- **Open** = `priceOpen` nến 1m ĐẦU khung
- **High** = max(`maxPrice`) trong khung
- **Low** = min(`minPrice`) trong khung
- **Close** = `priceClose` nến 1m CUỐI khung
- **Volume** = sum(`totalUsdt`)
- **startTime** = mốc đầu khung
- ⚠️ **Biên khung theo UTC** (00:00/00:15/… và 00:00/04:00 UTC — chuẩn Binance) để khớp nếu sau này đối chiếu. `kline_1m_opt` key là **GMT+7** (xem `docs/insights/INGEST_FORMAT.md`) → CCD xác nhận + convert đúng, KHÔNG để lệch 7h.
- ⚠️ **Nến thiếu phút** (gap giữa khung, <15 hoặc <240 phút) → **skip + log + đếm**, KHÔNG tạo nến nửa vời (feature SMA cần nến liền mạch).

## Lưu trữ
- Set mới: `kline_15m_btceth` + `kline_4h_btceth` (hoặc 1 set, key = symbol|interval|startTime). Value = `KlineObjectSimple` (tái dùng), Snappy như 1m.
- Ghi nơi H1/feature đọc: train đọc 226, live đọc 242 → CCD xác nhận read client của H1 rồi ghi cho khớp (mặc định ghi cả 226+242 nếu cần cả train lẫn serve). KHÔNG đụng `kline_1m_opt`.

## Phạm vi
- CHỈ BTC + ETH (không toàn sàn).
- **Historical:** aggregate 2021→nay 1 lần (xử theo chunk thời gian, cẩn thận RAM).
- **Forward:** rolling khi nến 1m mới đủ khung (mỗi 15m/4h chốt) — tích hợp vào luồng ingest hoặc batch định kỳ. <CHỐT với user thời điểm bật forward; golive cần có + warm-up đủ>.

## Validate (recompute-compare)
- Lấy mẫu vài khung → gom lại từ 1m bằng đường độc lập → so O/H/L/C/V.
- Biên: open = 1m đầu, close = 1m cuối khung (kiểm vài khung ngẫu nhiên + biên ngày).
- Gap: đếm khung thiếu phút đã skip.
- (Tùy chọn, KHÔNG gate) đối chiếu vài nến với Binance 15m/4h — chỉ tham khảo (nguồn 1m ta có thể lệch Binance).

## An toàn
- Chỉ THÊM set mới; đọc-only `kline_1m_opt`. Historical batch đọc lớn → chunk + giải phóng RAM.

## Acceptance
- [ ] Set 15m + 4h BTC/ETH; OHLCV đúng quy tắc; biên UTC (convert GMT+7 đúng).
- [ ] Historical 2021→nay; gap khung thiếu phút skip+log+đếm.
- [ ] Validate recompute-compare mẫu PASS.
- [ ] KHÔNG đụng `kline_1m_opt`.

## (Code điền)
Tool: `ai_ml/features/export/Aggregate15m4hBtcEth.java`.
- **Biên khung + convert key 1m (GMT+7→UTC):** key 1m parse qua SDF GMT+7 → **epoch tuyệt đối**; frame = `floor(epochMs/frameMs)*frameMs` (15m=900000ms, 4h=14400000ms). Vì epoch tuyệt đối, floor tự rơi đúng biên UTC (:00/:15/:30/:45 và 00/04/08/12/16/20 UTC) — KHÔNG cần xử 7h thủ công. open=1m đầu (min epoch trong khung), close=1m cuối (max epoch), high=max(maxPrice), low=min(minPrice), vol=Σ totalUsdt.
- **Set + read/write client:** đọc 1m từ **226** (đặt `IS_KAGGLE_MODE=true` → `getReadClient`→226 local, batch theo ngày `readDataFromAerospike1M`). Ghi **CẢ 226 (train) + 242 (live)**. Set `kline_15m_btceth`/`kline_4h_btceth`, **chunk theo THÁNG** (1 record toàn-series ~190k nến vượt giới hạn Aerospike "Record too big" → chia tháng): key=`SYMBOL-YYYYMM`, bin `data`=Snappy(gson(`TreeMap<startMs, float[o,h,l,c,v]>`)). max ~114KB/tháng (<< giới hạn). H1 đọc series: lặp 66 key-tháng/symbol/interval (train→226, live→242). KHÔNG đụng `kline_1m_opt`.
- **Historical kết quả (2021-01-01→2026-06-07):** BTC 15m=190 273 nến (26 khung thiếu phút skip) · BTC 4h=11 877 (19 skip) · ETH 15m=190 238 (28 skip) · ETH 4h=11 874 (20 skip). 66 record-tháng/series. gap rất nhỏ (~0.01%).
- **Validate recompute:** mỗi series 4/4 khung mẫu (đầu/⅓/⅔/cuối) read-back-242 == accumulator; **recompute ĐỘC LẬP** (đọc lại raw 1m của khung đầu qua `readDataFromAerospikeCustom`, tính O/H/L/C/V bằng đường khác, n=15/240 đủ) → **KHỚP ✅** cả 4 series.
- ⚠️ **Forward-rolling CHƯA bật** (historical-only). Golive cần tích hợp rolling (mỗi khung 15m/4h chốt) + warm-up — chốt thời điểm với user.
