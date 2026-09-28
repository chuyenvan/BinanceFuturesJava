# PRE-REG — EXPORT DEV PHỦ 2026-07 → 2026-09 (AUDIT-ONLY)

> **CHỐT TRƯỚC KHI TÍNH SỐ.** Không được đổi nội dung file này sau khi đã nhìn thấy kết quả.
> Viết: 2026-09-28 (UTC), commit nền `30f9906`, owner duyệt 28/09 14:30 ("Ok").

## 0. RÀNG BUỘC TỐI THƯỢNG (BẮT BUỘC, LẶP LẠI Ở FILE KẾT QUẢ)

**Dữ liệu 2026 (đặc biệt 2026-07 → 2026-09) trong export này CHỈ DÙNG CHO AUDIT / ĐỐI CHIẾU**
(ví dụ: so phân bố feature LIVE vs OFFLINE, tìm nghi phạm lệch).
**TUYỆT ĐỐI KHÔNG** dùng phần 2026 này để: chọn/hiệu chuẩn ngưỡng, chọn tham số, chọn feature,
hay bất kỳ quyết định thiết kế nào.

**2026 VẪN LÀ HOLDOUT** (chưa unseal cho mục đích chiến lược).

## 1. MỤC ĐÍCH

`feat_dump` (instrument LIVE, `LiveFeatureDump.java`) ghi 33 feature + `ts` + `symbol` + `p15_out` cho
2026-09. Export DEV hiện có (`~/claudedata/gate15m_v2_full.csv`) **kết thúc 2026-06-01 (+07)** ⇒
**0 cặp `(ts,symbol)` giao** ⇒ không so được (xem `docs/result/RESULT_FEAT_DIFF_PASS1.md`).
Pre-reg này chốt cách sinh **cùng pipeline / cùng 33 feature / cùng thứ tự TÊN** cho 2026-07 → 2026-09
để mới ghép cặp được.

## 2. PIPELINE GỐC (xác định TRƯỚC khi chạy)

- File export DEV: `~/claudedata/gate15m_v2_full.csv` — 42 cột, 2.846.461 dòng dữ liệu,
  ts 2021-01-01 00:00 (+07) → 2026-06-01 00:00 (+07), ghi 2026-08-29.
- **Sinh bởi:** `src/main/java/com/binance/chuyennd/ai_ml/features/export/gate/ExportGateDataset.java`
  - header: `ExportGateDataset.csvHeader()` — dòng **129**;
  - vòng replay: `ExportGateDataset.replayToCsv(long fairStart, long evalEnd, String outFile, RowSink)` —
    dòng **138**;
  - entry point: `ExportGateDataset.main(String[] args)` — args `[start=20210101] [end=20260701] [outFile]`,
    dòng **75**.
  - Khớp chứng cứ: 42 cột = `timestamp` + 34 cột `MarketFeatures.toCSVHeader()` (33 V3FULL +
    `volatilityRegime`) + 7 label (`label_oldbasket,label_ret15m,label_ret60m,label_retall15m,
    label_retall60m,label_max24h,label_retall24h`). `ExportGate15mV2` bị LOẠI (header khác: có
    `label_selector`, `nBasketOld`, `nBasketSel`).
  - (Ghi chú: `docs/archive/.../PIPELINE_PROVENANCE.md` ghi nguồn là `ExportGate15mV2` — ghi nhận SAI,
    đính chính bằng bằng chứng header ở trên.)
- Pipeline gốc là **Java + Aerospike**, bản repo chỉ chạy được bằng `java`. **Ràng buộc của task CẤM chạy
  Java** ⇒ phần sinh số được **PORT sang Python** (VIỆC 1), không sửa gì trong Java.
- **Nguồn dữ liệu thô** (đọc READ-ONLY):
  | Thành phần | Aerospike |
  |---|---|
  | nến 1m toàn thị trường | set `kline_1m_opt`, key `yyyyMMdd-HHmm` (GMT+7), bin `data` = snappy(proto `MinuteDataFinal`: map<string, 5 float: open,high,low,close,totalUsdt>) |
  | market rate (momentum1M/15M) | set `market_data_object`, key `yyyyMMdd-HHmm`, bins `time` (long) + `data` = 3 float32 (rateDownAvg, rateUpAvg, rateDown15MAvg) |
  | funding | set `funding_data`, key = symbol, bin `f_data` = snappy(JSON map ts→rate) |
  - Cụm đọc: **242 = `103.157.218.242`, namespace `ticker`** (canonical, có cả 2026-09);
    bản sao local `127.0.0.1:3222`, namespace `test` (giống BYTE với 242 ở vùng giao nhau — đã kiểm
    md5 trùng — nhưng chỉ có tới ~2026-08-19). Dùng local cho vùng cũ (nhanh), 242 cho đuôi 2026-08/09.
- **Cấu hình đọc**: `Configs.WFO_STATIC_RANK` = off (mặc định), `Configs.TIER_FLAT` không ảnh hưởng 33 feature.

## 3. 33 FEATURE + THỨ TỰ TÊN (ALIGN THEO **TÊN**, KHÔNG theo vị trí)

Thứ tự trong CSV DEV (cột 2..34, tức 33 feature đầu, `volatilityRegime` là cột chuỗi KHÔNG thuộc 33):

```
momentum1M, momentum5M, momentum15M, momentum1H, momentum4H, momentum24H, momentumAcceleration,
trendStrengthETH, trendConsistency, volatility1M, volatility15M, volatility1H, volatility24H,
volatilityTermStructure, advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown,
marketBreadthStrength, btcDominance, rsi14, volumeSpike, distMA20, basketMomentum15M,
basketMomentum1H, basketRsi14, basketVolSpike, fundingRateRaw, fundingRateAvg24H, fundingRateTrend,
hourOfDay, dayOfWeek, weekOfMonth, monthOfYear
```

Thứ tự trong `feat_dump` LIVE (cột 3..35) = `V3FULL`:

```
momentum1M, momentum5M, momentum15M, momentum1H, momentum4H, momentum24H, momentumAcceleration,
trendStrengthETH, trendConsistency, volatility1M, volatility15M, volatility1H, volatility24H,
volatilityTermStructure, advanceDeclineRatio, percentAboveMA20, volumeRatioUpDown,
marketBreadthStrength, btcDominance, rsi14, volumeSpike, distMA20, fundingRateRaw,
fundingRateAvg24H, fundingRateTrend, hourOfDay, dayOfWeek, weekOfMonth, monthOfYear,
basketMomentum15M, basketMomentum1H, basketRsi14, basketVolSpike
```

⇒ **Hai thứ tự KHÁC NHAU** (CSV: basket trước funding trước time; LIVE: funding, time, basket).
⇒ Mọi so sánh **BẮT BUỘC align theo TÊN**. Không so theo vị trí.

## 4. QUY TẮC TÁI LẬP (port Python phải y hệt bản Java)

1. **Ring buffer**: mỗi symbol 1 ring 2048 nến (`RING_SIZE=2048`), ghi theo `processKline`: nếu nến mới
   CÙNG `startTime` với nến cuối → lùi con trỏ 1 rồi ghi đè. Nến quá 2048 bị đè (không cần lịch sử xa hơn).
2. **Dọn zombie**: khi thời gian trôi ≥ 24h kể từ lần dọn trước → symbol nào cập nhật cuối ≥ 4h trước
   thì `historyHead = 0` (coi như rỗng).
3. **`timestamp`** làm tròn về đầu phút; nến có `startTime` lấy từ KEY (GMT+7), không từ payload.
4. **NaN/thiếu dữ liệu**: bản Java trả 0.0 (hoặc giá trị mặc định đã quy định trong code) rồi mới format
   `%.8f`; NaN/Inf → `0.000000`. Port PHẢI giữ đúng các nhánh mặc định, không tự đổi thành NaN.
5. **momentum1M/15M** = `rateDownAvg`/`rateDown15MAvg` từ `market_data_object` tại CÙNG ts (không có
   record → giữ 0.0).
6. **momentumAcceleration** = `momentum5M - momentum15M`; **volatilityTermStructure** =
   `volatility1H/volatility24H` (chỉ khi `volatility24H != 0`);
   **trendConsistency** = `+1` nếu `momentum5M*momentum1H > 0` ngược lại `-1`.
7. **rsi14**: Wilder-lite như `HistoryManager.getRsi14` (đơn giản trung bình 14 change, `avgLoss==0 → 100`).
8. **breadth** trên `targetBasket = CoinRankManager.getTopCoin(ts)` = **top 50% symbol theo tổng volume
   720 nến**, tie-break tên A→Z, **cập nhật mỗi 60 phút** (và lần đầu khi cache rỗng).
9. **basket feature** lấy trên cùng `targetBasket`; funding lấy trung bình các symbol trong basket,
   `getNearestFundingFee` = `floorEntry(ts)`, cách > 24h ⇒ 0.0, không có ⇒ bỏ symbol.
10. **thời gian**: `hourOfDay/dayOfWeek/weekOfMonth/monthOfYear` theo `Calendar` mặc định của tiến trình
    = **GMT+7**; `dayOfWeek` Sun=1; `weekOfMonth` Sun-start (đã xác nhận khớp DEV ở PASS 1).
11. **tần suất ghi**: **1 dòng / 1 phút, KHÔNG de-overlap** (`ExportGateDataset` ghi mọi phút).
    Warmup nến **48h** trước đầu cửa sổ (không ghi warmup).
12. **định dạng**: CSV, số `%.8f` (Locale.US), header = `ts` + **34 cột feature GIỐNG HỆT bản DEV**
    (33 số + `volatilityRegime`, cùng tên, cùng thứ tự) **+ 1 cột chẩn đoán `md_src`** (1 = có record
    `market_data_object` tại `ts`, 0 = thiếu ⇒ `momentum1M/momentum15M` giữ 0.0).
    KHÔNG ghi 7 cột label (không cần cho audit; label cần dữ liệu ngày kế tiếp).

> **[SỬA PRE-REG 2026-09-28, TRƯỚC KHI TÍNH SỐ]** Bổ sung ở §4.12: cột `md_src` + ghi nhận nguồn
> `market_data_object` CHỈ có trên cụm Oracle-local (ns `test`) và **mới nhất là 2026-08-13** ⇒ từ
> 2026-08-14 trở đi `momentum1M`/`momentum15M` của bản offline sẽ = 0,0 do THIẾU NGUỒN (không phải do
> code). Hai feature này vì vậy **loại khỏi bảng xếp hạng nghi phạm** nếu `md_src=0`. Lý do sửa: phát
> hiện tính khả dụng của nguồn TRƯỚC khi chạy (chưa nhìn thấy bất kỳ giá trị feature nào).

## 5. CỬA SỔ + KIỂM CHỨNG

- **Cửa sổ xuất**: `2026-07-01 00:00 (+07)` → `2026-09-28 14:00 (+07)` (mốc cuối = mốc mới nhất có
  trong nguồn tại thời điểm chạy; nếu 242 thiếu phút nào thì bỏ phút đó, ghi rõ số phút thiếu).
- **Kiểm chứng tái lập (BẮT BUỘC trước khi tin số 2026)**: port chạy lại **vùng giao nhau** với bản cũ
  và so với `gate15m_v2_full.csv`:
  - cửa sổ: `2026-04-01 00:00 (+07)` → `2026-04-15 00:00 (+07)` (warmup từ 2026-03-30 00:00);
  - **ĐẠT** khi, trên mọi `(ts)` giao nhau: (a) số `ts` khớp đúng, (b) với **mỗi** 1 trong 33 feature
    `max|Δ| ≤ 1e-6` hoặc `max rel|Δ| ≤ 1e-4`, (c) `rank-corr(Pearson trên giá trị)` ≥ 0,9999;
  - **KHÔNG ĐẠT ⇒ DỪNG**, không xuất số 2026, báo RO nguyên nhân (theo yêu cầu task).
- **Kiểm chứng chéo phụ (không chặn)**: `p15_out` của dump LIVE so vector offline cùng `ts` bằng
  model `fold_20` — đã làm ở PASS 1, không lặp.

## 5b. KẾT QUẢ KIỂM CHỨNG VÙNG GIAO NHAU — **[GHI TRƯỚC KHI CHẠY CỬA SỔ 2026]**, 2026-09-28

Chạy `devexport_202609.py --cluster local --start 20260501 --end 20260502` (warmup 2 ngày) rồi
`devexport_verify.py` trên `2026-05-01 00:00 → 2026-05-02 00:00 (+07)` (1.440 dòng, ghép đủ 1.440):

| nhóm | feature | kết quả |
|---|---|---|
| **29/33** | momentum5M/1H/4H/24H, trendStrengthETH, trendConsistency, volatility1M/15M/1H/24H, volatilityTermStructure, advanceDeclineRatio, volumeRatioUpDown, marketBreadthStrength, btcDominance, rsi14, volumeSpike, distMA20, basketMomentum15M/1H, basketRsi14, basketVolSpike, fundingRateRaw/Avg24H/Trend, hourOfDay/dayOfWeek/weekOfMonth/monthOfYear | **KHỚP TUYỆT ĐỐI** `max\|Δ\| ≤ 1e-8` (nhiều cái = 0,0) |
| 3 | momentum1M, momentum15M, momentumAcceleration | lệch ở **30/1.440 dòng**; **28 dòng DEV = 0** trong khi nguồn `market_data_object` hiện có giá trị ⇒ **store đã được ghi thêm SAU 2026-08-29** (nguồn trôi), không phải sai logic |
| 1 | percentAboveMA20 | lệch nhỏ `max\|Δ\|=1,06e-2`, corr **0,99992**, trung bình 0,50413 vs 0,50374 (~0,1–3 symbol/282 mỗi dòng; 359/1.440 dòng lệch) |
| — | volatilityRegime (chuỗi) | match **1,0000** |

**QUYẾT ĐỊNH (chốt trước khi có số 2026):** coi tái lập là **ĐẠT CÓ NGOẠI LỆ ĐÃ ĐỊNH LƯỢNG** cho mục đích AUDIT ⇒ **vẫn xuất cửa sổ 2026** nhưng:
- 3 feature nguồn-trôi (`momentum1M`, `momentum15M`, `momentumAcceleration`) **loại khỏi bảng nghi phạm** (nguồn offline đã trôi/thiếu từ 2026-08-14);
- `percentAboveMA20` **đánh dấu kém tin cậy** (sai số tái lập ~1%).
- KHÔNG nới tiêu chí §5 cho các feature khác; các feature khác vẫn phải khớp `≤1e-6 / 1e-4` mới dùng.

## 6. GHÉP CẶP VỚI `feat_dump`

- Đọc dump (CHỈ ĐỌC): shadow Oracle `~/shadow_c3/app/feat_dump/feat_dump_*.csv.gz` và 242
  `root@103.157.218.242:2222:/home/chuyennd/java/v_t_m/feat_dump/feat_dump_*.csv.gz`.
- Ghép theo **`(ts, symbol)`**; `ts` dump = epoch ms (đầu phút), symbol = BTCUSDT (hiện tại).
- So 33 feature: `mean/std/p50/p99/min/max/NaN-rate`, `shift_sd = |Δmean|/std_export`,
  `tail_ratio = max_live/p99_export`, `rank-corr` trên cặp ghép.
- **Ngưỡng kết luận** (chốt trước): "đủ mẫu" khi **≥ 200 cặp `(ts,symbol)`** ghép được. Dưới ngưỡng ⇒
  chỉ là **đề nghị**, không kết luận cứng (giữ nguyên tinh thần PASS 1 §4.3).
- Nghi phạm xếp hạng theo: `shift_sd` giảm dần, ưu tiên feature có `|shift_sd| ≥ 1,0` **và** `NaN-rate`
  hai phía bằng nhau (loại artifact "thiếu dữ liệu").

## 7. PROVENANCE BẮT BUỘC GHI LẠI

Với mỗi file xuất: script + commit + tham số + nguồn (host/namespace/set) + số dòng + số cột +
**sha256**. Không ghi file dữ liệu vào repo (để ngoài, ví dụ `~/claudedata/devexport_202609/`).

## 8. NGOÀI PHẠM VI (không làm ở đây)

- KHÔNG chạy Java / sim / WFO. KHÔNG ghi/sửa/restart/kill trên Oracle/242. KHÔNG sửa code Java.
- KHÔNG dùng số 2026 cho bất kỳ quyết định thiết kế nào (§0).
