# FIX OOM `LiveOiFeatProvider` — double-buffer OI (R4 1' shadow FAIL/rollback) — 2026-09-30

Phạm vi: **CHỈ code + test + doc**. KHÔNG deploy / restart / chạm 242 / ONNX / LIVE / `SHADOW_NO_PUSH`.
`git push` được phép (đã push). Branch `module`.

## 0. KẾT LUẬN (một dòng)

> OOM **không** phải do "double-buffer copy 2–3×": reader OI **KHÔNG hề cắt cửa sổ 24h** — hằng
> `CACHE_WINDOW_MS` chỉ giới hạn *số chunk-THÁNG* đọc, còn chunk-tháng `SYMBOL_yyyyMM` được writer
> **MERGE-tích-luỹ cả tháng** (~8640 điểm 5m/set) ⇒ RAM OI ≈ **2,2–2,5 GB** (gấp ~30× ý định);
> **double-buffer** dựng bản sao toàn universe trong khi bản cũ còn sống ⇒ đỉnh **~4,4–5,0 GB** >
> `-Xmx4g` ⇒ OOM; OOM bị bắt trong thread nền ⇒ swap không commit ⇒ **retry 10s/lần vĩnh viễn** (45×/2h).
> Fix `inplace`: cắt 24h + nạp từng lô 64 coin vào map đang sống ⇒ steady **~85 MB**, đỉnh **~95 MB**
> (**~50× thấp hơn**), giữ nguyên kết quả `lookup` trong cửa sổ.

## 1. BẰNG CHỨNG (không suy diễn)

- `docs/audit/DEPLOY_R4_LIVE_1M_V3_20260930.md`: deploy 09:38 (jar `01eb271a`), sanity 15' PASS (RSS 4,78 G);
  rollback về `78387f30`; `[GATE]` ~44/145 phút (~30 %).
- `/home/ubuntu/shadow_c3/app/logs/error.log` (read-only): **45 dòng** `[LiveOiFeatRefresh] [OI-LIVE] reload nền lỗi:
  java.lang.OutOfMemoryError: Java heap space`, từ **10:26:46** tới **~13:0x**, cách nhau ~2–3 phút; 1 dòng nhiễm
  sang `ThreadManagerOrder` ("failed reallocation of scalar replaced objects") = GC đã kiệt.
- `shadow_c3/app/bin/start.sh`: `JAVA_OPTS="-server -Xms1g -Xmx4g …"` (xem §6).
- Code: `DataManagerAerospikeFloatSim.getMetricMap242RecentBatch` — **không** cắt phần tử theo `sinceTs`, chỉ chọn
  chunk-tháng (`monthsBetween`) rồi `putAll` nguyên record; writer `writeMonthChunk` MERGE vào record tháng
  (`finalMap = new TreeMap<>(existing); finalMap.putAll(chunkData)`). ⇒ record tháng = **cả tháng**.

## 2. NGUYÊN NHÂN GỐC (3 tầng, có định lượng)

| tầng | cơ chế | hệ quả |
|---|---|---|
| **A. Data phình ~30×** | `GET *_Recent` chỉ lọc chunk-tháng, KHÔNG cắt 24h; chunk-tháng = ~8640 điểm 5m × 5 set/coin | `653 coin × 5 set × 8640 ≈ 28,2M entry × 80–88 B ≈ **2,2–2,5 GB**` (ý định 24h chỉ ~940k entry ≈ 85 MB) |
| **B. Double-buffer** | `reloadLocked(stale=true)` build `loaded` TOÀN BỘ `knownCoins`, còn `current` (map CŨ) vẫn sống tới lúc swap | đỉnh ≈ **2×** ≈ `**4,4–5,0 GB**` > `-Xmx4g` ⇒ OOM |
| **C. Retry-storm** | OOM ném trong `reloadInBackground`, bị `catch(Throwable)`; `current` không đổi ⇒ `freshTs` đứng yên ⇒ `stale=true` MÃI; `scheduleWithFixedDelay(10s)` | **thử lại mỗi 10 s**, mỗi lần lại cấp phát ~2 GB ⇒ GC thrash liên tục ⇒ `[GATE]` chỉ chạy khi GC đủ rảnh ⇒ **44/145 phút** |

Ghi chú: sanity 15' **PASS** vì lúc đó chỉ tồn tại **1 bản** (cold-load). Bản sao chỉ sinh ra ở lần reload
**đầu tiên sau khi có data mới** ⇒ OOM tích luỹ, đúng như bài học "15' không bắt được".

Phụ (nhỏ, không phải nguyên nhân chính): `knownCoins` không bound (phình theo lịch sử universe);
`lookup()` ghi `putIfAbsent` vào Snapshot (phá bất biến, map lớn dần giữa 2 reload);
`getMetricMap242RecentBatch` giữ 1 lúc `List<Key>` + 2 mảng `route*` cho toàn universe (~6,5k phần tử — nhỏ nhưng đã bỏ).

### Định lượng trước/sau (653 coin × 5 set)

| | entry giữ | steady | đỉnh lúc reload |
|---|---|---|---|
| **legacy** (hiện tại) | 653×5×~8640 ≈ **28,2M** | ~2,2–2,5 GB | **~4,4–5,0 GB → OOM** |
| **inplace** (fix) | 653×5×288 ≈ **0,94M** | **~85 MB** | ~ steady + 1 lô 64 coin (~8 MB) + 1 record decode (~0,8 MB) ≈ **~95 MB** |

⇒ đỉnh giảm **~50×**, steady giảm **~28×**. (Giả định "chunk-tháng ≈ cả tháng" **được xác nhận gián tiếp** bởi
chính hiện tượng OOM: nếu chunk chỉ chứa 2 ngày rolling thì steady OI chỉ ~165 MB và không thể OOM ở `-Xmx4g`.)

## 3. THAY ĐỔI CODE

**`src/main/java/.../ai_ml/onnx/funding/LiveOiFeatProvider.java`** (413 dòng)
- L76 `OI_LIVE_REFRESH_MODE` (+ `OI_LIVE_SYM_CHUNK`, `OI_LIVE_MAX_COINS`, `OI_LIVE_EVICT_GRACE_TICKS`,
  `OI_LIVE_FAIL_BACKOFF_MS`); L87 `isInplaceMode()` thuần hàm (mọi giá trị ≠ `inplace` ⇒ legacy).
- L163–175 `beginTick`: ở inplace ghi `lastSeenTick`/`tickSeq`.
- L180–212 `reloadInBackground`: inplace → backoff (`nextAttemptAfterMs`) chặn retry-storm (C).
- L219–249 **LEGACY nguyên vẹn** (`reloadLocked`/`reloadNow` — byte-identical B6).
- L254–268 `reloadNowInplace` (cold-start theo lô + cắt 24h).
- L274–292 `reloadLockedInplace`: nạp **từng lô** vào **CHÍNH** `current.data` (`sink = target.put`), chop
  `since=25h`, `keepFrom=now-24h` ⇒ **không copy toàn map** (B).
- L294–329 `pruneInplace` + `coinsToEvict` (thuần hàm): bỏ coin vắng > 120 tick, trần cứng **1500 coin** (A/knownCoins).
- L334–347 `lookup`: legacy nguyên vẹn; inplace chỉ lazy-cache khi chưa chạm trần (bound).
- L380–385 seam `testSeed` + `maxCoins()` (test-only).

**`src/main/java/.../aerospike/DataManagerAerospikeFloatSim.java`** (L748–825, **method MỚI**)
- `getMetricMap242RecentBatchInto(symbols, setNames, bin, sinceTs, keepFromTs, symChunk, sink)`: dựng `keys`
  **theo từng lô** (giải phóng sau mỗi lô), batch-get, **cắt `[keepFromTs, ∞)` ngay khi decode từng record**
  (chỉ giữ 1 TreeMap-tháng một lúc), `sink.accept(symbol, arr)`. **API cũ không đổi** ⇒ `S1RankerLive` và
  mọi caller khác không bị ảnh hưởng.

**Key mới + default (đề xuất cho `shadow_c3/app/conf/env.sh` — CHƯA ghi vào production):**

```
OI_LIVE_REFRESH_MODE=inplace   # default: legacy  (KHÔNG đặt = hành vi hiện tại)
OI_LIVE_SYM_CHUNK=64           # default
OI_LIVE_MAX_COINS=1500         # default
OI_LIVE_EVICT_GRACE_TICKS=120  # default
OI_LIVE_FAIL_BACKOFF_MS=60000  # default
```

### PARITY
- `OI_LIVE_REFRESH_MODE` vắng/`legacy` ⇒ **đúng byte-identical B6** (nhánh legacy không bị sửa; `clear()` vẫn NO-OP;
  cùng `getMetricMap242RecentBatch`, cùng `Snapshot`, cùng swap).
- `inplace` **giữ nguyên ngữ nghĩa OI**: cùng cửa sổ 24h (`CACHE_WINDOW_MS`), cùng `MERGE_TOL_MS` 2h, cùng
  merge_asof backward, cùng 1 mốc `ref` (oiZ→fallback delta) cho cả 5 set ⇒ `lookup(coin, t)` **trùng legacy**
  với mọi `t` trong cửa sổ 24h (đã chứng minh bằng unit test + lập luận: `floorKey(t)` với tol 2h chỉ chạm
  điểm ≥ t−2h > now−24h = biên cắt).
- Ngoài cửa sổ 24h: inplace trả NaN (legacy có thể có giá trị) — **cố ý**, vì live chỉ lookup `t ≈ now`.
- `pipelineFreshTs()` (guard `OI_STALE_HALT`) **không đổi** — vẫn đọc THẬT từ 242, không qua cache.

## 4. TEST / COMPILE

- **Compile**: `mvn -o -DskipTests package` ⇒ **EXIT=0** (test sources CŨNG được compile:
  `target/test-classes/.../LiveOiFeatProviderTest.class` có mặt). jar sha256:
  `c389b4becfe07197d61dbd4b1265405ac4be9e167e835d572c3120d8abca1e15`.
- **KHÔNG chạy `mvn test`/Java/sim trên Oracle** (shadow LIVE PAPER) — theo ràng buộc. Test là unit thuần
  (không mạng) nhưng **chưa execute**.
- `src/test/java/.../ai_ml/onnx/funding/LiveOiFeatProviderTest.java` (JUnit4, 6 test):
  - `refreshMode_defaultIsLegacy`, `isInplaceMode_onlyInplace` — default = legacy (parity).
  - `trim24h_preservesLookupWithinWindow` — map cỡ chunk-tháng (8640 điểm/set) vs bản cắt 24h ⇒ `lookup`
    **giống nhau** tại mọi `t` trong 24h (parity của fix).
  - `lookup_isOneRefForAllFiveSets`, `lookup_nanWhenOutsideTolerance` — ngữ nghĩa merge_asof không đổi.
  - `coinsToEvict_graceAndCap`, `maxCoins_defaultBounded` — bound `knownCoins`.
- **Bench áp lực heap** (viết sẵn, KHÔNG chạy): `src/main/java/.../research/passspeed/OiReloadHeapBench.java`
  — mô phỏng `nCoins=653`, chunk-tháng 8640 điểm/set; so `legacy` (phải OOM) vs `inplace` (phải PASS).

## 5. KẾ HOẠCH VERIFY (KHÔNG tự chạy — cần owner duyệt)

**(a) Kaggle heap-bench (ưu tiên — không chạm box live).** Kernel Java nhỏ, `-Xmx512m`:
```
java -Xmx512m -cp binance-java-sdk-1.2.4.jar com.binance.chuyennd.research.passspeed.OiReloadHeapBench legacy  653 3 8640
java -Xmx512m -cp binance-java-sdk-1.2.4.jar com.binance.chuyennd.research.passspeed.OiReloadHeapBench inplace 653 3 8640
```
- số chu kỳ reload: **3** (đủ bắt leak tích luỹ giữa các chu kỳ), `nCoins=653`, `points/set=8640`.
- **PASS** = `legacy` **OOM** (`VERDICT FAIL` / `OutOfMemoryError`) **VÀ** `inplace` `VERDICT PASS`, `peakUsed`
  ổn định qua 3 chu kỳ (không tăng đơn điệu), `peakUsed ≤ BENCH_BUDGET_MB` (đặt `BENCH_BUDGET_MB=200`).
- Nếu Kaggle không có: chạy trong **cửa sổ được duyệt** trên box, `-Xmx256m`, **không** song song shadow.

**(b) Canary shadow (cần owner duyệt deploy).** Bật `OI_LIVE_REFRESH_MODE=inplace` + giữ `SHADOW_NO_PUSH=true`;
- **theo dõi RSS/heap NGAY 15–30' đầu** (lúc reload đầu tiên xảy ra — điểm chết của bản cũ) **VÀ đủ 2 h**;
- tiêu chí: `0` dòng `OutOfMemoryError`; `[OI-LIVE] inplace refresh … evicted=… size=…` xuất hiện ≥1 lần;
  RSS **không tăng đơn điệu** (kỳ vọng giảm từ ~4,8 G xuống thấp hơn nhiều); `[GATE]` ≥ 90 % số phút;
  `n_pass`/danh sách symbol **trùng** một tick đối chứng của jar cũ (parity runtime).
- Rollback: gỡ key `OI_LIVE_REFRESH_MODE` (⇒ legacy) + restart.

## 6. `-Xmx` HIỆN TẠI + ĐỀ XUẤT

- Unit `shadow-c3.service` → `ExecStart=…/bin/run_foreground.sh` → `bin/start.sh`:
  `JAVA_OPTS="-server -Xms1g **-Xmx4g** -Duser.timezone=Asia/Ho_Chi_Minh …"`.
- RSS 4,78 G > heap 4 G ⇒ non-heap (Aerospike client, metaspace, direct) ~0,8 G.
- **Đề xuất: KHÔNG cần tăng `-Xmx`** sau fix (steady OI ~85 MB). Nếu muốn biên an toàn, `-Xmx5g` là tối đa
  hợp lý (host `avail ~14,7 G / free ~5,8 G` lúc deploy); **không** vượt 5–6 g để chừa cho OS/`asd`.
  Tăng `-Xmx` **mà không** dùng fix chỉ kéo dài thời gian sống của bug (data vẫn 2× ~2,5 GB + leak).

## 7. KHÔNG LÀM (out of scope)

Deploy/restart/rollback, ghi `env.sh`/`config.properties`, chạm 242/ONNX/LIVE, `mvn test`/Java/sim trên Oracle,
sửa `S1RankerLive` (đã tự cắt 24h) hay API cũ của `DataManagerAerospikeFloatSim`.
