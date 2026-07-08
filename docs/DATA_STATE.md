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
| **symbol_lifecycle** | Oracle ns=`test` set `symbol_lifecycle` | ✅ **REBUILD sau clean (2026-07-07 tối)** — 661 symbol (589 LIVE, 72 DEAD) | Ticker sạch → FTT/RAY/SC... giờ DEAD ĐÚNG mốc delist (FTT last 2022-11-14, không còn giả LIVE). LUNA/ANC DEAD đúng. Bức tranh survivorship đầy đủ 2 chiều. |
| **market_data_object (Aerospike)** | Oracle ns=`test` | ✅ **REGEN sau clean (2026-07-07 tối)** từ ticker SẠCH. LUNA sập rateDown15MAvg=-0.029 (giữ); 2026-01/02 hết méo do ghost (rateDown ~-0.008 bình thường). | ExportMarketData2File, client226=127.0.0.1 local. |
| **OI feature** | Oracle `features_oi_percoin_v1/oi_percoin_20210101_to_20260624.bin.gz` | ✅ **DÙNG LẠI (validate 2026-07-07)** — 3.1GB, coin delist có OI bao sập (LUNA/ANC/FTT/AUDIO). Xem mục 5a. | Nguồn 226 (backfill vision TASK-013). |
| **Gate feature (ff_*.bin)** | Oracle `claudedata/feat/` | ❌ **CHỈ 1 THÁNG cũ** (ff_202401.bin) → export lại toàn bộ từ market_data_object mới | — |
| **Funding feature + selector pred** | Oracle set/bin | ⏳ Chưa kiểm session này. Model selector v2 có (train 06-25). | — |
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
- 36 coin "thật" (bỏ 2 tên rác tiếng Trung ở CSV: 我踏马来了USDT, 龙虾USDT). ⚠️ **Phân biệt 2 con số:** CSV survivorship gốc = 38 coin (danh sách thủ công TASK-005); symbol_lifecycle đo TỪ DATA = **62 DEAD** (rộng hơn, gồm coin rename như MATIC→POL, và coin ít giao dịch chết lặng). 62 DEAD là bức tranh đầy đủ hơn, dùng cho lọc zombie trong backtest.
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

## 5. VIỆC CÒN LẠI ĐỂ "ĐỦ + ĐÚNG THEO PIPELINE" (cập nhật 2026-07-07 chiều)

ĐÃ XONG: ticker Aerospike ✅, lifecycle ✅, market_data_object ✅, OI feature ✅ (dùng lại, validate đủ).
CÒN LẠI (theo thứ tự):
1. **Gate feature (ff_*.bin)**: export lại TOÀN BỘ từ market_data_object mới (hiện chỉ có ff_202401 1 tháng). Tool: ExportGateFeaturesGroupA/B hoặc RunFullDataCollection. → validate có coin delist + không NaN/leak.
2. **Funding feature + selector pred**: kiểm bản hiện có (model v2 train 06-25) validate đủ/đúng với ticker mới thì dùng, không thì gen lại. Selector pred cần generate lại nếu feature đổi.
3. **Export wfo_dataset .bin**: từ market_data_object mới + gate pred + funding/selector pred + OI. Tool ExportWfoDataset. Ghi manifest provenance đầy đủ (code SHA + nguồn + ngày).
4. **Validate lại** toàn bộ với market object mới (Uni dặn: "đương nhiên validate lại với market object mới").
5. **WFO baseline mới** trên dữ liệu sạch, ngưỡng pre-reg (WFE≥0.5, %OOS+≥70%, maxDD≤50%). Kết quả WFO CŨ chỉ THAM KHẢO (baseline cũ trên data không sạch = vô nghĩa — Uni chốt).

Provenance: mọi artifact ghi manifest (code SHA + nguồn + ngày). Dữ liệu Oracle ns=test = TEST-ONLY, tách 242-source (lên live phải backfill 242 đường chính thức).

## 5a. OI FEATURE (chốt 2026-07-07): DÙNG LẠI bản 226 đã validate
- File `features_oi_percoin_v1/oi_percoin_20210101_to_20260624.bin.gz` (3.1GB, 138M record, nguồn Aerospike 226 backfill từ vision TASK-013).
- **Validate đủ+đúng (2026-07-07):** coin delist có OI bao trùm sập — LUNA 46859 rec (2021-12..2023-05), ANC 19016 (bao 2022-06), FTT 61396 (bao 2022-11), AUDIO 258k (..2024-05), BTC 573k (..2026-06). → DÙNG LẠI, không export lại.
- ⚠️ Đã THỬ export lại từ vision (source=vision) nhưng BỎ: quá chậm (~6-10 phút/coin do fetchSymbol tải toàn lịch sử S3, 780 coin = hàng chục giờ). Bản 226 nhanh + đã đủ. Bài học: vision-per-coin chỉ hợp cho vài coul lẻ, không cho full universe.

## 5b. GHOST + ĐUÔI ĐƠN — ĐÃ XỬ (2026-07-07 tối, task 133 phát hiện)
⚠️ **SỬA kết luận cũ "ghost vô hại":** SAI sau khi nạp ticker file. Đo lại: 38 ghost `...USDCUSDT` CÓ ticker thật 2026-01→02 (BTCUSDC-margin) → méo market basket 2 tháng cuối. VÀ 10 coin delist-futures (FTT/RAY/SC/STRAX/DGB/RAD/GLMR/IDEX/MDT/WAVES) có ĐUÔI ĐƠN: giá phẳng vol=0 kéo dài 628-1353 ngày sau delist (FTT kẹt $1.59 từ 2022-11 tới 2026) = data rác, lifecycle gắn nhầm LIVE.
- **ĐÃ CLEAN (CleanTickerGhostAndTail):** xóa 7400 ghost entry + 12.089.576 đuôi-đơn entry khỏi ticker Aerospike. Verify: FTT sau delist KHÔNG còn, trước delist CÒN. Mốc delist per-coin = volume>0 cuối cùng (MeasureDelistPoint).
- **Hệ quả:** market_data_object + lifecycle gen TRƯỚC clean giờ SAI → phải REGEN cả 2 từ ticker sạch (đang làm).
- symbol_mapper vẫn còn 38 ghost entry (chỉ id-map, không data) — vô hại vì ticker đã sạch; lọc khi tiện.

## 5c. FUNDING DATA (2026-07-08): set funding_data RỖNG -> crawl lại
- Phát hiện: set `funding_data` trống trên Oracle (bị reset như market/OI cũ). Hệ quả: gate feature A (3 cột funding), gate B (b7_pctFundingHigh/Dispersion), selector ff (~10 cột funding #17-27) đều gen ra RỖNG → phải gen lại sau khi có funding.
- Nguồn: crawl fapi.binance.com (HistoricalFundingCrawlerLocal, symbol từ universe 780 gồm coin delist, ghi Oracle local bin f_data). fapi reachable từ Oracle, ~10-20 phút. KHÔNG copy 242 (242 ns khác `test` → replicate lỗi).
- ⚠️ Bài học: sau reset Aerospike, MỌI set phụ (market/OI/funding/lifecycle/15m-4h) đều mất — phải khôi phục hết trước khi gen feature. Kiểm set rỗng TRƯỚC khi gen (tránh gen ra feature thiếu cột).

## 6. LỊCH SỬ
- 2026-07-07 (phiên chiều): NẠP XONG ticker file→Aerospike (1886 ngày, 2.7M record, 0 thiếu) + DỰNG lifecycle (698 sym: 636 LIVE/62 DEAD). Aerospike Oracle giờ = nguồn chuẩn đầy đủ. Verify LUNA/ANC DEAD đúng.
  → 4 tầng: ticker file ✅ + ticker Aerospike ✅ + lifecycle ✅ + dataset ❌ (chờ re-export).
  ⚠️ ĐỊNH VỊ ROADMAP: P1 backfill vốn ĐÃ ĐÓNG (TASK-005 d387229) — việc nạp hôm nay là KHÔI PHỤC ticker Aerospike bị reset về trạng thái P1. Bước kế = re-export feature/train (P2/H1) — CẦN đối chiếu H1/P2 đã tới đâu trước khi chạy (roadmap viết trước khi Aerospike reset).
- 2026-07-07 (phiên sáng): tạo mới sau phiên đo dứt điểm. Phát hiện: ticker đầy đủ ở FILE không phải Aerospike; ns=test gần rỗng; lifecycle chưa dựng. Sửa hiểu lầm "Oracle ns=test có 1886 ngày ticker".
