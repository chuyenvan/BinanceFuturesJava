# INGEST_FORMAT — format ghi ticker / funding / mapper (TASK-004 bước 0,0a)

> ⚠️ **RÀ 2026-07-07:** File này mô tả FORMAT BYTE ghi/đọc (vẫn đúng). NHƯNG các nhận định về TRẠNG THÁI
> (namespace, ghi 242, "backfill không đo được survivorship") là bối cảnh 2026-06-10 (pilot 226/242) — ĐÃ THAY ĐỔI.
> Trạng thái dữ liệu HIỆN TẠI + hướng đi: xem **[DATA_STATE.md](../DATA_STATE.md)** (nguồn sự thật). Tóm tắt cập nhật:
> Oracle ns=**test** (không phải ticker); backfill ghi qua tool ĐỘC LẬP trỏ Oracle local (BackfillDelistCoin/
> IngestTickerFileToAerospike), KHÔNG qua writeMinuteBatch-242; ticker file .bin.gz ĐÃ đủ 38 coin delist.

> Đọc từ CODE THẬT (file:line). Phục vụ backfill coin chết an toàn. Cập nhật 2026-06-10.

## 1. TICKER 1m (giá) — set `kline_1m_opt`
- Hằng: `DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_TICKER = "kline_1m_opt"` (L40). Namespace = `Configs.AEROSPIKE_NAMESPACE` (config.properties = `ticker`).
- **KEY**: `yyyyMMdd-HHmm` (1 record/PHÚT, GMT+7 — ngày bắt đầu 07:00). `writeMinuteBatch` L146-147.
- **VALUE**: Bin `"data"` = `Snappy.compress(MinuteDataFinal protobuf)`. L153-154.
  - `MinuteDataFinal` = `map<string, KlineObjectOptimized> tickers` (proto `src/main/proto/MinuteDataFloat.proto`).
  - Map key = **FULL symbol** (vd `"SUSHIUSDT"`, `"LUNAUSDT"`) — XÁC NHẬN bằng inspect record thật (TASK-005). Read path `readDataFromAerospike1M_ShortKey` L533 chuẩn hoá `endsWith("USDT") ? key : key+"USDT"` nên chấp cả hai, nhưng record HIỆN HÀNH dùng full ⇒ ghi backfill phải dùng full. (Mapper key cũng full.)
  - `KlineObjectOptimized` = 5 float: `priceOpen, maxPrice, minPrice, priceClose, totalUsdt` (KHÔNG có startTime — lấy từ KEY).
- **READ-MODIFY-WRITE** (giữ coin khác): `writeMinuteBatch` đọc record cũ qua `getExistingTickersMap(key)` → `finalMap.putAll(newTickers)` → ghi đè bin. L150-154. KHÔNG ghi đè trực tiếp.
- **ĐỌC (sim)**: `readDataFromAerospike1M_ShortKey` (L475+) → `KlineObjectSimple[1000]`, index = `SimpleSymbolMapper.getId(fullSymbol)` (L531-536). ⚠️ Mảng **cố định 1000**; id ≥ 1000 → crash. Hiện nextId=760.

## 2. FUNDING RATE (phí funding thực) — set `funding_data`
- Hằng: `AEROSPIKE_SET_NAME_FUNDINGFEE = "funding_data"` (L42).
- **KEY** = `symbol` (vd `"LUNAUSDT"`). **VALUE** = bin `"f_data"` = `Snappy(JSON Map<Long ts, Float rate>)`. Ghi: `writeFundingMap` (L222+, có guard chống xoá lịch sử). Đọc: `getFundingMap` (L269+).
- ⚠️ **funding fee KHÔNG dùng trong backtest**: `OrderTargetInfoTest.updateFundingFee()` (L222-241) **comment toàn bộ** → `time2FundingFee` rỗng → `calFundingFee()`=0 → `calTp()` (L218) trừ 0. ⇒ **backfill funding rate hiện VÔ NGHĨA với PnL sim** (chỉ ticker giá mới ảnh hưởng).

## 3. SYMBOL MAPPER — set `symbol_mapper`
- Hằng: `AEROSPIKE_SET_NAME_MAPPER="symbol_mapper"`, key `"global_id_map"`, bin `"data"` (L52-54). VALUE = CDT `Map<String symbol, Long id>`.
- `SimpleSymbolMapper.getId(symbol)`: chưa có → `++counter` cấp id mới + **ghi NGAY** qua `saveSymbolMapping` (auto). nextId = maxId+1.
- ⚠️ Load mapper qua `getReadClient()` (226 nếu kaggle/hpo, else 242).

## ⚠️ MÂU THUẪN với "pilot chỉ ghi 226, không đụng 242"
Mọi helper GHI **hardcode `getClient242()`**, KHÔNG theo mode:
- `writeMinuteBatch` L154 → 242. `getExistingTickersMap` L378 → 242. `saveSymbolMapping` L134 → 242.
- `getId()` → gọi saveSymbolMapping → **ghi mapper vào 242**. ⇒ cấp id LUNA bằng getId = ĐỤNG 242.

Hệ quả:
1. Pilot ghi 226 **không tái dùng được** các helper trên → cần code client226 riêng (read-modify-write thủ công) + cấp id thủ công (KHÔNG gọi getId).
2. Sim GoldenBacktest (flags=false) đọc ticker qua `getReadClient` → **242**. ⇒ LUNA ghi vào **226 KHÔNG hiển thị với sim**. Pilot-226 chỉ validate FORMAT (đọc lại trên 226); để sim thấy phải ghi **242** (TASK-005).

## ⚠️ 0c — coin thiếu prediction: backfill ticker KHÔNG đủ để sim trade
- Thiếu funding pred (`symbol2Pred==null`) → sim **skip**, không lỗi (Simulator L195).
- Thiếu funding rate → `getNearestFundingFee` null → fee 0 (và fee đã tắt).
- **Quan trọng**: entry của sim do **AI prediction** (`ai_pred_market_full_basket_v2` + funding pred) lái, KHÔNG phải ticker. LUNA chỉ có ticker mà KHÔNG có ai_pred_market/funding_pred cho 2022 ⇒ sim **không có tín hiệu vào LUNA → không trade → backfill ticker đơn lẻ KHÔNG đo được survivorship**. Muốn đo phải SINH cả prediction cho coin backfill (việc nặng, thuộc 005+).

## 0b — DIED_SYMBOLS (đã xác nhận)
`Constants.diedSymbol` = bộ lọc loại-trừ ở lõi chung (`MarketBigChangeDetector:63` SIM+LIVE, ingestor, `DetectEntrySignal2TradeNormal:133`). User đã rút còn `BTCDOMUSDT`. ⚠️ LIVE giờ có thể thử entry coin delist → cần tách SIM(bỏ loại)/LIVE(giữ loại) hoặc kiểm xử lý đặt lệnh coin không tồn tại.
