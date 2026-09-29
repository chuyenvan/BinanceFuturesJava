# PREREG_PASS_SPEED — hạ 1 lượt live từ ~230s xuống ~1s, GIỮ PARITY (code + bench, CHƯA deploy)

Chốt lúc: **2026-09-29**, TRƯỚC khi chạy bất kỳ phép đo nào. Commit file này PHẢI có TRƯỚC
mọi commit kết quả. Nếu đảo thứ tự → toàn bộ số đo PASS-SPEED bị coi là VOID.

Phạm vi: **CHỈ code live (đường selector/shadow trên Oracle)** + bench read-only. **KHÔNG deploy,
KHÔNG restart shadow-c3**, KHÔNG chạm 242 ngoài đọc, KHÔNG đặt lệnh, KHÔNG ghi Redis/Aerospike.
KHÔNG chạm 2026/HOLDOUT, KHÔNG train, KHÔNG sim.

---

## 0. Vì sao (đọc MASTER đo 09:13–09:17 +07, shadow-c3)

- Đọc ticker 1000' toàn thị trường từ Aerospike-242 = **1.3s**. Sau "Market level change" im lặng
  ~250s tới "Finish" — cả tick market-only cũng ~4–5'. ⇒ nhịp 1' thực tế ~4–5', KHÔNG phải predict chậm.
- Trong lượt: CPU hệ thống 94% idle, java ~20%; mạng vào ~2.5 MB/s liên tục (~600MB/lượt).
- `predictAllCandidates`: `liveOiProvider.clear()` MỖI tick ⇒ ~650 coin × `LiveOiFeatProvider.load()`
  gọi TUẦN TỰ 5×`getMetricMap242` (FULL history ~30k điểm/map, ~81 chunk-tháng, rồi mới cắt 24h)
  ⇒ ~3250 GET lớn qua WAN/lượt. Tick market-only VẪN predict cả universe dù `levelChange==null`.
- ⇒ Nghẽn chính = **IO từ xa (đọc full-history OI mỗi tick)**, KHÔNG phải ONNX (`predictBatch` đã batch).

## 1. NGUYÊN TẮC PARITY (BẮT BUỘC)

Mọi **output quyết định** phải BIT-IDENTICAL cũ vs mới trên ≥30 tick replay/ghi lại:
OI lookup 5 giá trị (#41..#45), feature 45, `pNoPump`, `net015`, S1 score, map, gate, **danh sách lệnh**.
Điều này được chứng minh bằng (a) unit test logic thuần + (b) harness so sánh full-history vs recent
đọc cùng snapshot 242 (đọc-only, cùng một tick). Thứ tự kết quả phải CỐ ĐỊNH khi song song hoá.

## 2. THIẾT KẾ CHỐT (trước khi đo)

### 2.1 Instrument (SLF4J, 1 dòng/lượt `[PASS-TIMING]`)
Thêm mốc timing cho: ticker read, updateMarketHistory, extractAllFeatures+predictAll (entry),
OI load (LiveOiFeatProvider), funding extract loop, PASS-2 CS, predictBatch, net015, S1 score
(+hist read), map, gate, tổng. Mục đích xác nhận/bác bỏ số MASTER. Thuần LOG, KHÔNG đổi quyết định.

### 2.2 LiveOiFeatProvider — bỏ reload full-history mỗi tick
- **Cache giữ qua tick** (không `clear()` mỗi tick; `clear()` giữ API nhưng thành no-op).
- **Đọc CHỈ chunk-tháng gần nhất** (mới `getMetricMap242Recent(set,bin,symbol,sinceTs)` đọc các tháng
  `[month(sinceTs), month(now)]`, thay vì `202001..now` ~81 tháng). `sinceTs = now - 24h`.
  Cắt `tailMap(now-24h)` GIỮ NGUYÊN ⇒ lookup y hệt (chỉ cần floorKey trong 2h << 24h).
- **Refresh NỀN** (thread riêng, định kỳ ~10s) khi `pipelineFreshTs` tăng; kèm **guard đồng bộ
  trong tick** (`beginTick()` kiểm tra freshTs, nếu tăng thì reload ngay) ⇒ cache LUÔN đúng mới nhất
  tại thời điểm lookup ⇒ parity đảm bảo, không race.
- **BatchRead**: `getMetricMap242Recent` vẫn batch-get nhiều key trong 1 lần (BatchPolicy có sẵn).
- **Nguồn LOCAL Oracle (226)**: ĐÃ KIỂM TRA writer `ComputeOiFeat2Live242.writeFeatures` → chỉ ghi
  `writeMetricMap242` (242), KHÔNG mirror về 226 ⇒ **feature `oi_feat_*` chỉ có trên 242** ⇒ KHÔNG áp
  "ưu tiên 226" (raw OI có trên 226 nhưng feature đã-tính thì không; live KHÔNG tự tính — đúng thiết kế).

### 2.3 Tick market-only: không predict cả universe khi `levelChange==null`
Khi `selectorLeg==false` (tick 1') VÀ `levelChange==null`: chỉ predict các symbol ĐANG GIỮ
(`BudgetManager.symbol2Pos` + `ShadowBookC3.openSymbols()` khi C3). Đủ cho DCA big-loss
(`isDcaAlt`) và giữ `LATEST_SEL_PNOPUMP` tươi cho `tsGap` (chỉ đọc cho symbol đang giữ).
Tick có `levelChange != null` VÀ mọi selector tick (15') VẪN predict full universe (y hệt cũ).

### 2.4 S1RankerLive — hist giờ + ticker 1000'
`refresh()` hist close 1h ĐÃ đọc tăng dần (`lastHourLoaded`) — giữ nguyên. `ensureOi()` đổi
`getMetricMap242` full → `getMetricMap242Recent` (chỉ 24h). Không đổi thứ tự/cadence.

### 2.5 Song song hoá (CHỈ khi sau 1–4 còn CPU-bound)
Chỉ parallel `extractFeatures` per-coin nếu `[PASS-TIMING]` cho thấy funding extract loop vẫn
chiếm đa số. Thứ tự kết quả CỐ ĐỊNH (map keyed by symbol, không phụ thuộc lịch thread).

## 3. BENCH (read-only, KHÔNG đặt lệnh, KHÔNG ghi Redis/Aerospike/242)
Harness độc lập chạy 1 lượt predict: đọc snapshot ticker 242 → `updateMarketHistory` →
`extractFeatures`+OI lookup toàn universe → `predictBatch` → (S1/map nếu có) → đo per-phase.
Stub mọi hàm ghi (`saveAiPrediction1M`, `StorageSnappy.writeObject2File`, Redis set/rpush).
Đo **p50/p95** của 1 lượt: cũ (full-history) vs mới (recent+cache). Mục tiêu p50 ≤1s, p95 ≤3s.
Báo thật nếu không đạt + phần còn nghẽn.

## 4. RÀNG BUỘC CỨNG
- 174 test cũ 0 fail + unit test mới PASS.
- Cấm `System.out`/`System.err`/`printStackTrace` (thay = `LOG.error`) trong khối chạm vào.
- KHÔNG đổi bất kỳ hằng số gate/selector/sizing. KHÔNG đổi thứ tự feature 45.
- DEV ≤ 2025-12-31; 2026 = HOLDOUT, không đụng.
- KHÔNG push file dữ liệu lớn.

## 5. THỨ TỰ
1. Commit file này (ghi hash).
2. Implement 2.1–2.4 + unit test.
3. Build `mvn -o test` → 174 test cũ + mới PASS.
4. Bench harness đo cũ vs mới (read-only).
5. Viết `docs/result/RESULT_PASS_SPEED.md` (bảng timing trước/sau + parity). Commit SAU.
