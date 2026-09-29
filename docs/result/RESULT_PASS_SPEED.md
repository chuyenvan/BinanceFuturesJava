# RESULT_PASS_SPEED — hạ 1 lượt live từ ~250s xuống ~250ms steady (GIỮ PARITY), CHƯA deploy

Ngày: **2026-09-29**. Pre-reg: **`docs/prereg/PREREG_PASS_SPEED.md`** (commit **`99f43ad`**, chốt TRƯỚC khi đo).
Phạm vi: **CHỈ code live (selector/shadow Oracle)** + bench read-only. **KHÔNG deploy, KHÔNG restart shadow-c3,
KHÔNG ghi gì lên 242** (bench thuần đọc). KHÔNG chạm 2026/HOLDOUT, 0 sim/0 train.

---

## 0. KẾT LUẬN (một dòng)

> Nghẽn chính xác nhận = **IO từ xa** (mỗi tick reload FULL-history OI: ~3250 GET qua WAN ~685MB), KHÔNG phải ONNX.
> Fix (BatchRead 1 lần cho mọi coin + chỉ đọc chunk-tháng gần + cache qua tick + market-only bỏ predict universe)
> đưa 1 lượt **~250s → ~250ms steady** (cache hit) / **~30s cold** (1 lần/giờ khi pipeline push). **PARITY BIT-IDENTICAL**.
> Phần còn nghẽn (~30s cold) = **chunk-tháng quá thô** (đọc 24h vẫn phải kéo cả tháng ~93KB/set/coin ≈ 342MB) —
> để xuống ≤1s cho cả refresh cần **chunk-NGÀY** cho `oi_feat_*` trên 242 (thay đổi phía ghi, ngoài phạm vi read-only này).

## 1. ĐO ĐƯỢC (bench read-only trên Oracle, trỏ 242 — giống config shadow_c3)

| pha | CŨ (full-history per-coin) | MỚI (batch recent + cache) |
|---|---|---|
| ticker read 1000' | **1742–2150 ms** | giữ nguyên (không đổi) |
| OI load (bottleneck) | **p50 = 333 ms/coin** (p95 380, max 484; n=60) ⇒ 736 coin ≈ **~250 s** | **29839 ms cold / 2489 ms (60 coin) / ~250 ms cache-hit** |
| funding extract + predictBatch + S1 | không đổi (CPU, sub-giây) | không đổi |

- **Trước (CŨ):** 1 lượt selector ≈ **~250 s** (khớp MASTER đo 09:13–09:17 ~230–250 s). Nghẽn = `LiveOiFeatProvider.clear()`
  mỗi tick → `load()` gọi TUẦN TỰ 5×`getMetricMap242` (FULL history ~81 chunk-tháng ~30k điểm, rồi mới cắt 24h)
  ⇒ ~736 coin × 5 set ≈ **3680 GET tuần tự** qua WAN (RTT ~60 ms) + ~685 MB transfer.
- **Sau (MỚI):** BatchRead 1 lần cho mọi coin (`getMetricMap242RecentBatch`) ~**4 round-trip** (thay ~3680) + chỉ đọc
  chunk-tháng gần (1 tháng thay 81 key). **Cold ~30 s** (đọc 736 coin × 5 set × ~1 tháng ≈ 342 MB), **cache-hit ~250 ms**.

## 2. PARITY — BIT-IDENTICAL (BẮT BUỘC)

Bench `PassSpeedBench parity` đọc CÙNG snapshot 242, so 5 giá trị lookup (`oiDelta24h, oiZ, lsGlobal, lsToptrader,
takerBuy`) CŨ (full-history + cut 24h) vs MỚI (batch recent + cache):

| mẫu | kết quả |
|---|---|
| 60 coin | **60/60 BIT-IDENTICAL, maxDiff = 0.0** |
| 20 coin (subset đầu) | **20/20 BIT-IDENTICAL, maxDiff = 0.0** |

Cơ sở lý thuyết (đã chốt ở pre-reg): `lookup` chỉ dùng `floorKey(t)` trong `MERGE_TOL_MS=2h`; cửa sổ 24h >> 2h ⇒ cắt
`tailMap(24h)` của recent đọc ra y hệt full-history. `getMetricMap242Recent` đọc các tháng `[month(since), month(now)]`
bao trọn mọi điểm ≥ now-24h ⇒ `lastKey`/`floorKey` không đổi.

**Tick market-only (selectorLeg=false, levelChange==null):** chỉ predict symbol đang giữ (`marketOnlyUniverse`) —
đủ cho DCA big-loss (`isDcaAlt`) + giữ `pNoPump` tươi cho trailing `tsGap` (chỉ đọc cho symbol đang giữ) ⇒ **danh sách
lệnh BIT-IDENTICAL**. Tick có `levelChange != null` và mọi selector tick (15') VẪN predict full universe (y hệt cũ).

## 3. THAY ĐỔI CODE (đều PARITY-SAFE, có unit test)

1. `DataManagerAerospikeFloatSim`: thêm `getMetricMap242Recent` + `getMetricMap242RecentBatch` + `monthsBetween`
   (đọc chunk-tháng gần); tách lõi `getMetricMapMonths` (dùng chung, KHÔNG đổi `getMetricMap242` full).
2. `LiveOiFeatProvider`: cache qua tick + `beginTick(universe)` batch-load + refresh nền (daemon 10s) + guard đồng bộ
   (parity) khi `pipelineFreshTs` tăng. `clear()` thành no-op (giữ API).
3. `DetectEntrySignal2TradeNormal`: `beginTick(allSymbols)`; market-only tick skip full universe; `[PASS-TIMING]`
   instrument (SLF4J, 1 dòng/lượt); `printStackTrace` → `LOG.error` trong khối chạm vào.
4. `S1RankerLive`: `ensureOi` đổi 1472 đọc tuần tự → BatchRead 1 lần (2 set).
5. **Nguồn LOCAL Oracle (226):** kiểm tra writer `ComputeOiFeat2Live242.writeFeatures` → CHỈ ghi `writeMetricMap242`
   (242), KHÔNG mirror về 226 ⇒ feature `oi_feat_*` **chỉ có trên 242** ⇒ không áp "ưu tiên 226" (raw OI có trên 226
   nhưng feature đã-tính thì không; live không tự tính — đúng thiết kế).
6. **Song song hoá (item 5):** KHÔNG cần — sau khi bỏ IO OI, funding extract + predictBatch là CPU nhưng sub-giây
   (MASTER đo CPU 94% idle, java ~20% ⇒ IO-bound, không CPU-bound). `predictBatch` đã batch sẵn.

## 4. TEST

- `mvn -o test`: **183 PASS, 0 fail** (174 cũ + 9 mới: `MonthsBetweenTest` 5 + `MarketOnlyUniverseTest` 4).
- Không `System.out`/`System.err`/`printStackTrace` trong code mới (khối chạm vào đã chuyển `LOG.error`).

## 5. CÒN NGHẼN (báo thật, KHÔNG đạt p50≤1s cho pha COLD refresh)

- **Cold refresh (~30 s, 1 lần/giờ)** khi `pipelineFreshTs` tăng: đọc 736 coin × 5 set × ~1 tháng ≈ **342 MB**
  (mỗi chunk-tháng ~93 KB, chứa ~29 ngày 5m). Đọc "24h" vẫn phải kéo CẢ tháng vì `oi_feat_*` ghi theo **chunk-THÁNG**
  (`SYMBOL_yyyyMM`), Aerospike trả nguyên bin — không đọc được phần trong bin.
- **Steady-state (cache hit) ~250 ms** — đạt mục tiêu ≤1s. ticker read (~1.7–2.1 s) là pha riêng, không thuộc "250 s" gốc.
- **Để xuống ≤1s cho cả refresh:** cần ghi `oi_feat_*` theo **chunk-NGÀY** (`SYMBOL_yyyyMMdd`, ~3 KB) trên 242
  (sửa `writeFeatures` + backfill) ⇒ đọc 24h chỉ ~2 chunk-ngày ≈ ~11 MB. Đây là thay đổi **phía GHI** (viết lên 242),
  ngoài phạm vi task này (bench thuần đọc, KHÔNG ghi 242). Đề xuất làm task sau, cần MASTER duyệt.

## 6. TÁI LẬP

```bash
# build + test
cd /home/ubuntu/src/BinanceFuturesJava && mvn -o test            # 183 PASS
# bench (config trỏ 242 read-only, giống shadow_c3): xem config /home/ubuntu/pass_speed_bench/config.properties
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx6g \
  -cp target/binance-java-sdk-1.2.4.jar \
  com.binance.chuyennd.research.passspeed.PassSpeedBench parity 60   # parity + timing
# instrument [PASS-TIMING] hiện trên full.log khi shadow restart (sau deploy — task sau)
```
