# DATA_STATE — Trạng thái dữ liệu THẬT (đo 2026-07-07, "đo không đoán")

> **Nguồn sự thật DUY NHẤT về trạng thái dữ liệu hiện tại.** Mọi tài liệu khác nói về "dữ liệu ở đâu, đủ chưa"
> đều trỏ về đây. Số trong file này = ĐO trực tiếp bằng tool (MeasureDataState, PeekTickerFileV2, CoverageDelist),
> KHÔNG suy đoán. Khi trạng thái đổi (nạp Aerospike, re-export) → cập nhật file này + ghi ngày.
>
> Liên quan (KHÔNG lặp): `db/index.md` (topology 242/226/Oracle), `insights/INGEST_FORMAT.md` (format byte ghi/đọc),
> `runbooks/BACKFILL_SURVIVORSHIP.md` (quy trình), `PIPELINE_PROVENANCE.md` (vết truy nguyên artifact→code).

## 1. BỐN TẦNG DỮ LIỆU — trạng thái đo 2026-07-07

| Tầng | Vị trí | Trạng thái (đo) | Ghi chú |
|---|---|---|---|
| **Ticker FILE** | Oracle `kaggle_data_hpo/daily/ticker_YYYYMMDD.bin.gz` | ✅ **ĐẦY ĐỦ** 1886 file (2021-01-01→2026-03-01), 11GB | Có đủ 38 coin delist + ĐUÔI SẬP. Nguồn đầy đủ nhất hiện có. |
| **Ticker Aerospike** | Oracle ns=`test` set `kline_1m_opt` | ✅ **ĐẦY ĐỦ (2026-07-07)** — 2,703,650 record phút, 1886 ngày (2021-01-01→2026-03-01) | Nạp từ file bằng IngestTickerFileToAerospike. 698 symbol, gồm 62 coin DEAD. |
| **symbol_lifecycle** | Oracle ns=`test` set `symbol_lifecycle` | ✅ **DỰNG XONG (2026-07-07)** — 698 symbol (636 LIVE, 62 DEAD) | SymbolLifecycleBuilderLocal. LUNA/ANC=DEAD đúng. ⚠️ trạng thái suy TỪ DATA (last vs maxTicker), không từ exchangeInfo — FTT=LIVE vì có data tới cuối. |
| **market_data_object (Aerospike)** | Oracle ns=`test` | ✅ **GEN XONG (2026-07-07)** từ ticker đầy đủ → set market_data_object. Verify LUNA sập: rateDown15MAvg=-0.029 ngày 12/5 (phản ánh sập đúng). | ExportMarketData2File, đọc/ghi local Oracle (client226=127.0.0.1). |
| **wfo_dataset .bin** | Oracle claudedata/ | ⏳ Chờ export lại từ market_data_object mới (+ features + pred) | wf_v3 cũ market=unchanged (thiếu coin delist). |

**Hệ quả then chốt:** survivorship (38 coin delist) ĐÃ được TASK-005 xử lý — nhưng ở **tầng FILE**, KHÔNG phải Aerospike.
Câu "backfill xong chưa" = ticker file XONG; Aerospike + lifecycle + dataset thì CHƯA.

## 2. HAI ĐƯỜNG TIÊU THỤ TICKER (quan trọng — quyết định luồng)

Codebase có 2 đường đọc ticker, chọn bằng config `TICKER_SOURCE`:

| Đường | Code | Đọc từ | Dùng cho |
|---|---|---|---|
| **file** | `KaggleDataLoader.loadDailyTickersShort` | file `.bin.gz` (ObjectInputStream: `TreeMap<Long,Map<String,KlineObjectSimple>>`) | backtest/WFO (`SimulatorMarketLevelTicker1MStopLoss`, `TICKER_SOURCE=file`) |
| **aerospike** | `DataManagerAerospikeFloatSim.readDataFromAerospikeCustom` | set `kline_1m_opt` (proto MinuteDataFinal) | export features/market, sim khi `TICKER_SOURCE=aerospike` |

⇒ **Backtest/WFO CHẠY ĐƯỢC NGAY trên file đầy đủ (có coin delist), KHÔNG cần Aerospike.**
⇒ **Export features/market cần Aerospike có data** (hoặc sửa để đọc file).

## 3. SURVIVORSHIP — 38 coin delist (nguồn: outputs/survivorship_missing_symbols.csv)

Đã VERIFY trong file ticker (PeekTickerFileV2), giá đuôi khớp CSV:
- LUNA: lastSeen 2022-05-13 13:49, close **$0.008** (sập từ ~$80). ANC: close $0.055. FTT: 2022-11 đủ. AUDIO/ANT/TOMO/SRM/BTS: 2024-05-28 đủ.
- 36 coin "thật" (bỏ 2 tên rác tiếng Trung ở CSV: 我踏马来了USDT, 龙虾USDT).
- Đặc trưng: drawdown TB −60.9%, 12/38 died-near-zero. Đây là đuôi trái mà chiến lược no-SL+DCA cần thấy.

## 4. CẠM BẪY GHI AEROSPIKE (đã xác nhận qua code)

- `writeMinuteBatch`/`writeFundingMap`/`writeOpenInterestMap`/`saveSymbolMapping` trong `DataManagerAerospikeFloatSim`
  **HARDCODE `getClient242()`** → KHÔNG dùng để ghi Oracle local. Tool ghi Oracle PHẢI tự tạo `AerospikeClient("127.0.0.1",3222)`.
  (Tool `BackfillDelistCoin` TASK-140 làm đúng vậy.)
- Config Oracle: `AEROSPIKE_NAMESPACE=test`, `AEROSPIKE_HOST_226=127.0.0.1`, `AEROSPIKE_READ_CLUSTER=226` →
  đọc ticker từ **Aerospike LOCAL Oracle**. Config REPO (Windows) khác: `AEROSPIKE_HOST_226=103.157.218.226` (226 THẬT) —
  nên tool backfill KHÔNG được đọc Configs.AEROSPIKE_HOST_*, phải nhận host qua arg.
- Format ticker Aerospike: key `yyyyMMdd-HHmm` GMT+7, bin `data`=Snappy(MinuteDataFinal), symbol FULL ("LUNAUSDT").
  Format file KHÁC: ObjectInputStream serialize `TreeMap<Long,Map<String,KlineObjectSimple>>`.

## 5. VIỆC CÒN LẠI ĐỂ "ĐỦ + ĐÚNG THEO PIPELINE" (chốt 2026-07-07)

Hướng: file ticker đã đầy đủ → đạt mục tiêu "Aerospike nguồn chuẩn" + export .bin:
1. **Xóa 13 ngày rác** ns=test (tàn dư + pilot LUNA) → nạp sạch.
2. **Nạp 1886 file ticker → Aerospike Oracle ns=test** (coin delist tự theo, vì file đã chứa). Master-worker chia ngày.
3. **Dựng set symbol_lifecycle** (SymbolLifecycleBuilder) trên Oracle.
4. **Export market → features → generate prediction → wfo_dataset** từ Aerospike (pipeline chuẩn); hoặc backtest/WFO đọc thẳng file để đối chứng nhanh.
5. Provenance: mọi artifact ghi manifest (code SHA + nguồn + ngày). Dữ liệu Oracle ns=test = TEST-ONLY, tách 242-source.

## 5a. OI FEATURE (chốt 2026-07-07): DÙNG LẠI bản 226 đã validate
- File `features_oi_percoin_v1/oi_percoin_20210101_to_20260624.bin.gz` (3.1GB, 138M record, nguồn Aerospike 226 backfill từ vision TASK-013).
- **Validate đủ+đúng (2026-07-07):** coin delist có OI bao trùm sập — LUNA 46859 rec (2021-12..2023-05), ANC 19016 (bao 2022-06), FTT 61396 (bao 2022-11), AUDIO 258k (..2024-05), BTC 573k (..2026-06). → DÙNG LẠI, không export lại.
- ⚠️ Đã THỬ export lại từ vision (source=vision) nhưng BỎ: quá chậm (~6-10 phút/coin do fetchSymbol tải toàn lịch sử S3, 780 coin = hàng chục giờ). Bản 226 nhanh + đã đủ. Bài học: vision-per-coin chỉ hợp cho vài coul lẻ, không cho full universe.

## 5b. VẤN ĐỀ SẠCH SẼ (ưu tiên thấp, không chặn luồng)
- **38 ghost `...USDCUSDT`** trong symbol_mapper (781 entry): cặp USDC-margin (BTCUSDC→"BTCUSDCUSDT") bị normalize sai (endsWith USDT). Đã đo (2026-07-07): KHÔNG có ticker/OI thật → mọi bước đọc data bỏ qua tự nhiên → VÔ HẠI về đúng đắn, chỉ phình mapper/universe + WARN khi export OI vision. Xử khi tiện: lọc `USDCUSDT$` khỏi symbol_mapper + universe. Universe thật ~742 coin (780 − 38 ghost).

## 6. LỊCH SỬ
- 2026-07-07 (phiên chiều): NẠP XONG ticker file→Aerospike (1886 ngày, 2.7M record, 0 thiếu) + DỰNG lifecycle (698 sym: 636 LIVE/62 DEAD). Aerospike Oracle giờ = nguồn chuẩn đầy đủ. Verify LUNA/ANC DEAD đúng.
  → 4 tầng: ticker file ✅ + ticker Aerospike ✅ + lifecycle ✅ + dataset ❌ (chờ re-export).
  ⚠️ ĐỊNH VỊ ROADMAP: P1 backfill vốn ĐÃ ĐÓNG (TASK-005 d387229) — việc nạp hôm nay là KHÔI PHỤC ticker Aerospike bị reset về trạng thái P1. Bước kế = re-export feature/train (P2/H1) — CẦN đối chiếu H1/P2 đã tới đâu trước khi chạy (roadmap viết trước khi Aerospike reset).
- 2026-07-07 (phiên sáng): tạo mới sau phiên đo dứt điểm. Phát hiện: ticker đầy đủ ở FILE không phải Aerospike; ns=test gần rỗng; lifecycle chưa dựng. Sửa hiểu lầm "Oracle ns=test có 1886 ngày ticker".
