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
| **Ticker Aerospike** | Oracle ns=`test` set `kline_1m_opt` | ❌ **GẦN RỖNG** — chỉ 17690 phút (2022-05-01→05-13) | Tàn dư thí nghiệm + pilot LUNA 2026-07-07. KHÔNG phải 1886 ngày. |
| **symbol_lifecycle** | Oracle ns=`test` set `symbol_lifecycle` | ❌ **CHƯA DỰNG** (0 record) | Cần chạy `SymbolLifecycleBuilder`. Nguồn sự thật vòng đời coin. |
| **market.bin / wfo_dataset** | Oracle | ❌ **KHÔNG THẤY** trên Oracle | features_oi_percoin_v1 có (3GB). market/wfo cần export lại. |

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

## 6. LỊCH SỬ
- 2026-07-07: tạo mới sau phiên đo dứt điểm. Phát hiện: ticker đầy đủ ở FILE không phải Aerospike; ns=test gần rỗng; lifecycle chưa dựng. Sửa hiểu lầm "Oracle ns=test có 1886 ngày ticker".
