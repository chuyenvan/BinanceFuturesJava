# TASK-125 — Validate độc lập TOÀN BỘ dữ liệu WFO (READ-ONLY trên Oracle) — 2026-07-04

- **Người chạy:** CCD opus. **Máy:** Oracle `161.118.212.3` (aarch64, 4 core, 23GB RAM ~1GB free lúc chạy), Aerospike local `127.0.0.1:3222` ns=`test`.
- **Hàng rào:** READ-ONLY tuyệt đối; mọi tool `nice -n 15 -Xmx2g`; file tạm chỉ trong `~/claudedata/validate125/`. Không đụng jobstore/process/242/226-remote.
- **Bối cảnh:** chạy song song với export bù ticker (`ExportHpoDataKaggle 20210101 20260301`, pid 467639) — mọi lệnh đọc dùng `exists()`/seek/decode-nhẹ, tránh OOM & tránh đụng export.
- **Tool nguồn:** compile trong `~/claudedata/validate125/` dùng `~/java/simulator/binance-futures-task121.jar` làm classpath (aerospike-client + proto `MinuteDataFinal` + Snappy + gson trong fat-jar). 4 tool: `CoverageScan`, `RangeScan`, `GateValidate`, `SymbolConsistency`, `TickerFileCheck`.

---

## ⚠ CẦN XỬ LÝ (bất thường phát hiện)

1. **[Mục 5 — WARN] 4 ghost symbol trong `funding.bin` (wfo_dataset_wf)**: `1000PEPEUSDCUSDT, PENGUUSDCUSDT, WLDUSDCUSDT, WLFIUSDCUSDT` — có trong funding nhưng KHÔNG có trong `universe_birth_death.csv`. Cả 4 là **cặp quote-USDC** (`…USDC`) bị logic `endsWith("USDT")?s:s+"USDT"` dán nhầm hậu tố → `…USDCUSDT`. Chúng lọt vào pool funding-selector nhưng không phải universe USDT-perp thật. Tác động nhỏ (4/669 symbol) nhưng chỉ ra lỗi normalize symbol (cặp USDC không nên bị append USDT / không nên có trong universe USDT-perp). ĐỀ NGHỊ: lọc bỏ cặp quote-USDC ở tầng đọc ticker/funding, hoặc xác nhận cố ý.

2. **[Mục 2 — WARN] Lệch range `funding.bin` giữa 3 bộ và so market/pred**: market/pred cả 3 bộ kết ở `2026-05-13`; nhưng funding `wf`/`leaked_restricted` kết ở `2026-03-31` (ngắn hơn ~43 ngày), còn funding `leaked` (wfo_dataset) kết ở `2026-06-06` (DÀI hơn market/pred ~24 ngày → có tick funding không có market/pred tương ứng). Không phải lỗi toàn vẹn (join theo market ts) nhưng là lệch cửa-sổ-thời-gian giữa các khối; nên biết khi phân tích rìa cuối.

*(Ngoài 2 điểm trên, không phát hiện mất/hỏng dữ liệu nào khác.)*

---

## Mục 1 — Coverage ticker Aerospike Oracle-local (ns=test, set=kline_1m_opt) — **PASS**

Quét theo NGÀY (biên GMT+7-nửa-đêm) `20210101→20260301` = **1886 ngày**. Mỗi ngày: `exists()` batch 1440 key `yyyyMMdd-HHmm` (metadata-only, không đọc bin → nhẹ, không đụng export) đếm phút hiện diện; decode 1 phút mẫu (12:00 hoặc phút đầu) đếm symbol.

| Chỉ số | Kết quả |
|---|---|
| Ngày quét | 1886 (20210101..20260301) |
| Ngày **mất hẳn** (0 phút) | **0** |
| Ngày **partial** (0<phút<1440) | **1**: `20210101` = 1020 phút |
| Ngày đủ 1440 phút | 1885 |
| symbol/phút (mẫu): min / median / max | 75 / 195 / 1131 |
| `20251231` (từng nghi "Date data error") | **1440 phút / 598 symbol — SẠCH** |
| `2025Q2` (Apr–Jun 2025, 91 ngày) | **toàn bộ 1440 phút/ngày — SẠCH** |

- `20210101` partial (1020 phút) là **ĐÚNG BOUNDARY**: data bắt đầu 00:00 UTC = 07:00 GMT+7, nên 420 phút đầu (00:00–06:59 GMT+7) của ngày GMT+7 chưa có data. Khớp `market.bin` first tick `2021-01-01 07:00 GMT+7`.
- Vùng từng thấy "Date data error" (20251231, 2025Q2) nay hoàn toàn đủ 1440 phút → lỗi cũ không còn trong Aerospike hiện tại.

**Lệnh:**
```
# tool: ~/claudedata/validate125/CoverageScan.java (exists() + decode 1 phút/ngày)
cd ~/claudedata/validate125 && javac -cp ~/java/simulator/binance-futures-task121.jar CoverageScan.java -d .
nice -n 15 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx2g -cp "~/java/simulator/binance-futures-task121.jar:." CoverageScan item1_coverage.csv
awk -F, 'NR>1 && $2==0' item1_coverage.csv | wc -l                 # ngày mất hẳn = 0
awk -F, 'NR>1 && $2>0 && $2<1440{print}' item1_coverage.csv         # partial = 20210101,1020
awk -F, 'NR>1 && $3>0{print $3}' item1_coverage.csv | sort -n | awk '{a[NR]=$1}END{print a[1],a[int(NR/2)],a[NR]}'
grep '^20251231,' item1_coverage.csv                                # 20251231,1440,598
```

---

## Mục 2 — 3 bộ WfoDataset (md5 / count / range / funding-quý) — **PASS** (2 WARN range ở mục ⚠)

Format bin (theo `WfoDataset.java`): market `[int count]+count×[ts:long][3 float]`; pred `+count×[ts:long][2 float]`; funding `+count×[ts:long][len:int][len×long]` (long-packed `symbolId<<32 | floatBits`). MD5 trong tool = `MessageDigest MD5` = `md5sum` Linux.

### 2a. MD5 — cả 9 file KHỚP manifest

| bộ | file | md5 đo | md5 manifest | |
|---|---|---|---|---|
| wfo_dataset_wf | market.bin | 65ac483da50558d1328d4bc8543aba76 | 65ac483d… | ✅ |
| wfo_dataset_wf | pred.bin | 44061d681578d7a63d3c1835e96008b8 | 44061d68… | ✅ |
| wfo_dataset_wf | funding.bin | d714390a7b228a59f53c621911ed94e8 | d714390a… | ✅ |
| wfo_dataset (leaked) | market.bin | 16497413efa46927557fc4c86498aa30 | 16497413… | ✅ |
| wfo_dataset (leaked) | pred.bin | 44061d681578d7a63d3c1835e96008b8 | 44061d68… | ✅ |
| wfo_dataset (leaked) | funding.bin | 3dc1c920d4bbd88473aff91d04aee628 | 3dc1c920… | ✅ |
| leaked_restricted | market.bin | 16497413efa46927557fc4c86498aa30 | 16497413… | ✅ |
| leaked_restricted | pred.bin | 44061d681578d7a63d3c1835e96008b8 | 44061d68… | ✅ |
| leaked_restricted | funding.bin | 7fe54adf4d858ae5e125ad2cd3463282 | 7fe54adf… | ✅ |

### 2b. Count + range (RangeScan, RandomAccessFile seek)

| bộ | file | count (khớp manifest) | first | last |
|---|---|---|---|---|
| wf | market | 2804363 ✅ | 2021-01-01 07:00 | 2026-05-13 11:35 |
| wf | pred | 2819841 ✅ | 2021-01-01 07:00 | 2026-05-13 12:20 |
| wf | funding | 2758365 ✅ | 2021-01-01 07:30 | 2026-03-31 23:59 |
| leaked | market | 2804363 ✅ | 2021-01-01 07:00 | 2026-05-13 11:35 |
| leaked | pred | 2819841 ✅ | 2021-01-01 07:00 | 2026-05-13 12:20 |
| leaked | funding | 2827087 ✅ | 2021-01-01 07:00 | 2026-06-06 23:35 |
| leaked_restricted | market | 2804363 ✅ | 2021-01-01 07:00 | 2026-05-13 11:35 |
| leaked_restricted | pred | 2819841 ✅ | 2021-01-01 07:00 | 2026-05-13 12:20 |
| leaked_restricted | funding | 2758319 ✅ | 2021-01-01 07:30 | 2026-03-31 23:59 |

- market/pred first-last KHỚP nhau trong từng bộ. funding lệch (xem ⚠ #2).

### 2c. Funding coins/tick theo quý — KHỚP CHÍNH XÁC audit `funding_coverage_audit_20260702.md`

Recompute per-quý (ticks, coins/tick TB, min, max) cho `wf` và `leaked` → **trùng từng dòng** với bảng audit (vd wf 2021Q1 `129105/9.0/6/11`; leaked 2026Q2 `68663/544.8/11/593`). Không lệch.

**Lệnh:**
```
for d in wfo_dataset_wf wfo_dataset wfo_dataset_leaked_restricted; do for f in market pred funding; do md5sum ~/claudedata/$d/$f.bin; done; done   # so manifest.txt
# tool RangeScan (range + funding-quý CSV):
nice -n 15 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx2g -cp "$JAR:." RangeScan ~/claudedata/<bo> item2_q_<bo>.csv
diff <(recompute) docs/reports/funding_coverage_audit_20260702.md   # khớp
```

---

## Mục 3 — Set gate `ai_pred_market_gate_wfo` (ns=test local) — **PASS**

Key `yyyyMMdd-HHmm` GMT+7; bin `data` = `Snappy(gson(AiPredictionData{timestamp,predReturn15M,predRisk4H}))`. CSV nguồn `~/claudedata/wfo_gate_pred.csv` (1,795,681 dòng = 1 header + **1,795,680** data).

| Kiểm | Kết quả |
|---|---|
| Số record (metadata scanAll) | **1,795,680** = kỳ vọng ✅ |
| = số dòng data CSV | 1,795,680 ✅ |
| Range key set | `20230101-0000` .. `20260531-2359` |
| Range ts CSV | min=1672506000000 (2023-01-01 07:00 GMT+7→key 0000) .. max=1780246740000 (2026-05-31 23:59) ✅ khớp |
| Mẫu hệ thống 1001 record (mỗi 1795 dòng CSV → batch-get Aerospike → decode) | ok=**1001**, mismatch=0, missing_key=0, NaN/null=**0** |
| 20 dòng đầu đối chiếu CSV | tất cả OK (giá trị p15/r4/ts trùng bit-đối-bit) |

**Lệnh:**
```
wc -l ~/claudedata/wfo_gate_pred.csv        # 1795681
# tool GateValidate: pass1 metadata scanAll (count+min/max key), pass2 sample→batch-get→decode→compare
nice -n 15 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx2g -cp "$JAR:." GateValidate ~/claudedata/wfo_gate_pred.csv
# → SET_COUNT=1795680 ; SET_MINKEY=20230101-0000 SET_MAXKEY=20260531-2359 ; sample_ok=1001 mismatch=0 missing=0 nan=0
```

---

## Mục 4 — Bộ ticker file `kaggle_data_hpo/` — **PASS**

Export bù toàn dải (`ExportHpoDataKaggle 20210101 20260301 ticker`, pid 467639) **đã HOÀN TẤT** trong phiên validate lượt 2: log cuối in `🎉 All data exported to: kaggle_data_hpo/` @ `12:41:49`, ghi đủ **1886 file** `ticker_YYYYMMDD.bin.gz` (11G). File mới nhất `ticker_20260228.bin.gz` mtime static @12:41:49 (không còn ghi). *(Ghi chú: process JVM 467639 vẫn treo trong pgrep sau khi in 🎉 — đúng lỗi non-daemon-thread không `System.exit(0)` đã biết; DATA đã hoàn chỉnh & bất biến nên đo được an toàn READ-ONLY.)*

| Kiểm | Kết quả |
|---|---|
| Số file `ticker_*.bin.gz` | **1886** (first `20210101`, last `20260301`) |
| Liên tục 20210101→20260301 (đối chiếu day-list coverage mục 1) | **KHÔNG THIẾU NGÀY** — `comm` cả 2 chiều rỗng (0 ngày coverage-thiếu-file, 0 ngày file-thừa) ✅ |
| `gunzip -t` toàn bộ 1886 file | **1886/1886 PASS** (`GUNZIP_ALL_DONE bad=0`, 0 file hỏng) ✅ |
| Spot-check `20210701` (file vs Aerospike) | minutes 1440=1440, ticks 161280=161280, symbols 112=112 — **DIFF 0** ✅ |
| Spot-check `20230701` | minutes 1440=1440, ticks 273600=273600, symbols 190=190 — **DIFF 0** ✅ |
| Spot-check `20250701` | minutes 1440=1440, ticks 681120=681120, symbols 473=473 — **DIFF 0** ✅ |

3 ngày spot-check (2021/2023/2025) khớp **tuyệt đối bit-count** file-gz vs Aerospike local (số phút, số tick, tập symbol trùng khít, symOnlyFile=symOnlyAero=0). File ticker là ảnh chụp trung thực của Aerospike.

**Lệnh:**
```
tail -5 ~/claudedata/export_ticker_full.log        # 🎉 All data exported ...
ls ~/java/simulator/kaggle_data_hpo/ticker_*.bin.gz | wc -l   # 1886
# continuity: day-list coverage(mục1) vs tên file
comm -23 <(awk -F, 'NR>1{print $1}' item1_coverage.csv|sort) <(ls ...|sed -E 's/ticker_([0-9]{8}).*/\1/'|sort)  # rỗng
comm -13 ... ...   # rỗng
# gunzip integrity: for f in ticker_*.bin.gz; do gunzip -t "$f"; done   # log gunzip_test.log
# spot-check: tool TickerFileCheck (load gz OIS + mirror readDataFromAerospike1M HOUR=7 GMT+7 batch-get + diff)
nice -n 15 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx2g -cp "$JAR:." TickerFileCheck 20210701 ~/java/simulator/kaggle_data_hpo/ticker_20210701.bin.gz
```

---

## Mục 5 — Symbol consistency (funding wf → mapper → universe) — **PASS** (1 WARN: 4 ghost, xem ⚠ #1)

Decode symbolId (`(int)((v>>32)&0xFFFF)`) từ toàn bộ `funding.bin` (wf) → map qua `symbol_mapper` (load READ-ONLY, KHÔNG dùng `getId()` vì nó GHI 242 khi symbol lạ) → đối chiếu `universe_birth_death.csv`.

| Chỉ số | Kết quả |
|---|---|
| funding ticks quét | 2,758,365 |
| tổng long | 55,777,350 |
| symbolId phân biệt | **669** |
| map ra tên (0 UNKNOWN id) | 669 ✅ (không id mồ côi) |
| universe size | 937 |
| **GHOST** (funding có, universe không) | **4**: `1000PEPEUSDCUSDT, PENGUUSDCUSDT, WLDUSDCUSDT, WLFIUSDCUSDT` |
| universe không xuất hiện trong funding | 272 (bình thường — funding leak-free là tập con selector) |

**Lệnh:**
```
# tool SymbolConsistency: load mapper (get global_id_map, read-only) + scan funding.bin + diff universe
nice -n 15 java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx2g -cp "$JAR:." SymbolConsistency ~/claudedata/wfo_dataset_wf/funding.bin ~/claudedata/universe_birth_death.csv
# → DISTINCT_SYMBOLIDS=669 MAPPED_NAMES=669 UNKNOWN_IDS=0 GHOST_COUNT=4 ...
```

---

## Tổng kết

| Mục | Trạng thái |
|---|---|
| 1. Coverage ticker Aerospike | PASS (0 ngày mất; 1 partial đúng-boundary; vùng nghi-lỗi sạch) |
| 2. 3 bộ WfoDataset (md5/count/range/funding-quý) | PASS (2 WARN: lệch range funding) |
| 3. Gate set `ai_pred_market_gate_wfo` | PASS (count/range/1001-mẫu khớp tuyệt đối) |
| 4. Ticker file `kaggle_data_hpo/` | PASS (export xong 1886 file; liên tục 0 gap; gunzip 1886/1886 bad=0; 3 spot-check DIFF-0 khớp Aerospike) |
| 5. Symbol consistency | PASS (1 WARN: 4 ghost USDC-pair) |
