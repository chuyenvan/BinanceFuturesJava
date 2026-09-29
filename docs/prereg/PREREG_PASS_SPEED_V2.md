# PREREG_PASS_SPEED_V2 — hoàn tất B4: parity TOÀN pipeline + xử lý pha cold refresh (~30s/giờ), CHƯA deploy

Chốt lúc: **2026-09-29**, TRƯỚC khi chạy bất kỳ phép đo nào. Commit file này PHẢI có TRƯỚC
mọi commit kết quả. Nếu đảo thứ tự → toàn bộ số đo PASS-SPEED-V2 bị coi là VOID.

Phạm vi: **CHỈ code live (selector/shadow Oracle)** + bench read-only. **KHÔNG deploy, KHÔNG restart
shadow-c3, KHÔNG ghi gì lên 242** (bench thuần đọc, stub mọi hàm ghi). KHÔNG chạm 2026/HOLDOUT,
0 sim/0 train. Đây là B5 — hoàn tất 2 lỗ hổng của B4 (`876250e`) trước khi MASTER giao deploy.

---

## 0. Vì sao (audit MASTER B4)

B4 (`876250e`) đúng hướng (OI cache + BatchRead + recent → ~250ms steady, parity 60/60 OI) nhưng còn
**2 lỗ hổng**:
1. **Parity mới chỉ kiểm 5 giá trị OI lookup** (60+20 coin), chưa kiểm MỌI output quyết định. Thay đổi
   market-only (chỉ predict symbol đang giữ) làm đổi tập ghi `LATEST_SEL_PNOPUMP`/`selPnp` — phải chứng
   minh không consumer nào khác đổi hành vi.
2. **Cold refresh ~30s/giờ** (đọc lại cả tháng chunk khi pipeline push). KHÔNG được ghi 242; KHÔNG cần
   chunk-ngày phía ghi nếu đọc được phần MỚI phía server.

MASTER chốt: chọn **phương án A (đồng bộ, giữ parity tuyệt đối)** thay B (async) của PLAN_R4_LIVE_1M_V2 —
vì B4 steady ~250ms đã làm async không còn cần thiết.

---

## 1. NGUYÊN TẮC PARITY (BẮT BUỘC, mở rộng từ B4)

Mọi **output quyết định** phải BIT-IDENTICAL cũ vs mới trên ≥30 tick selector + ≥30 tick market-only
(replay/ghi lại cùng snapshot 242): feature 45 mọi coin, `pNoPump`, `net015`, S1 score, `[MAP]` multiset,
`[GATE]` thr/n_pass, danh sách symbol BIG_DOWN/DCA/PREDICT_SYMBOL_TRADE sẽ vào lệnh, `LATEST_SEL_PNOPUMP`
cho symbol đang giữ.

## 2. PHÁT HIỆN (đọc code TRƯỚC khi đo — chốt thiết kế)

### 2.1 Lỗ hổng parity của market-only skip (B4) — NGUYÊN NHÂN GỐC
`predictAllCandidates` chạy PASS-2 cross-sectional rank (#33..#35 = fundingRankCS/volumeZRankCS/
momentumRankCS) qua `FundingCrossSectional.apply(csList)` với `csList = aiCandidates ∩ csPop`.
`csPop = EntrySignalFilter.selectCoins(...)` là full universe (độc lập aiCandidates), nhưng `csList`
trong tick market-only chỉ còn **held ∩ csPop** ⇒ rank percentile tính trên tập CON thay vì full population
⇒ #33..#35 khác ⇒ `pNoPump` của symbol đang giữ KHÁC ⇒ parity vỡ (ảnh hưởng trực tiếp `LATEST_SEL_PNOPUMP`
+ trailing `tsGap` + DCA big-loss).

### 2.2 Quyết định FIX (chốt TRƯỚC khi đo)
**Bỏ market-only skip** (xoá `marketOnlyUniverse` + nhánh `if (!selectorLeg && levelChange == null)`),
giữ NGUYÊN OI cache + BatchRead + recent-read (đây mới là thắng lợi thật của B4). Lý do:
- Sau OI cache, predict full universe ~250ms (cache hit) — market-only skip chỉ tiết kiệm predictBatch
  cho non-held (sub-giây), KHÔNG đáng đánh đổi parity.
- Tick market-only khi đó = predict full universe = **byte-identical 876250e^** (không còn tập con).
- `LIVE_ENTRY_GRID_MIN=1` (deploy R4) ⇒ selector mỗi phút ⇒ market-only tick KHÔNG bao giờ chạy — skip vô dụng cho deploy.
Chứng minh: (a) unit test `FundingCrossSectional` cho thấy rank trên tập con ≠ full population; (b) bench
full-pipeline old vs new; (c) grep MỌI reader LATEST_SEL_PNOPUMP/selPnp/selFeat45 (mục 4).

### 2.3 Cold refresh — kiểm kiểu bin `oi_feat_*`
Đọc code `writeMonthChunk`/`decodeMap`: bin `f_data` là **Snappy JSON blob `Map<String,Float>`**, KHÔNG phải
Aerospike Map nguyên sinh ⇒ `MapOperation.getByKeyRange` **KHÔNG áp dụng được** (chỉ áp cho native Map bin).
⇒ Báo cấu trúc thật + đề xuất (vẫn KHÔNG ghi 242):
- (Đề xuất, cần MASTER duyệt, phía GHI): chunk-NGÀY `SYMBOL_yyyyMMdd` cho `oi_feat_*` (như B4_RESULT §5 đã nêu)
  ⇒ đọc 24h chỉ ~2 chunk-ngày ≈ 11MB ⇒ refresh ≤1s. Đây là thay đổi phía ghi (viết 242), NGOÀI phạm vi task.
- (Read-only, giữ nguyên): refresh nền (daemon 10s) + guard đồng bộ `beginTick` khi `pipelineFreshTs` tăng.
  Guard này CHẶN tick khi pipeline push trùng tick (hiếm, ~1 lần/giờ) — đây chính là điều GIỮ parity
  (không serve dữ liệu cũ hơn bản cũ). Đo p50/p95 của pha refresh này.

## 3. BENCH (read-only, stub ghi, KHÔNG ghi 242)
Mở rộng `PassSpeedBench` → `PassSpeedBenchV2`: đọc snapshot ticker 242 → `updateMarketHistory` →
extractFeatures + OI lookup toàn universe → PASS-2 CS rank → `predictBatch` (funding) → net015 →
đo per-phase. So sánh OLD (full-history OI per-coin) vs NEW (batch recent + cache) trên CÙNG snapshot:
feature 45 + pNoPump + net015 BIT-IDENTICAL. Đo p50/p95 1 lượt selector (full universe) và market-only.
Mục tiêu: steady ≤1s (B4 đã đạt ~250ms), refresh p50/p95 đo riêng.

## 4. GREP MỌI READER LATEST_SEL_PNOPUMP/selPnp/selFeat45 — chứng minh không đổi hành vi
- `BinanceOrderTradingManager.tsGap` (L485): đọc `LATEST_SEL_PNOPUMP.get(symbol)` cho symbol ĐANG GIỮ
  (vòng `processDynamicTP_SL` duyệt `symbol2Pos`) ⇒ luôn tươi sau khi bỏ skip.
- `paperSymbolPred` (DetectEntry L100-105) → `shadowHandleOrder` (L230): chỉ gọi trong vòng SELECTOR
  (order mới), không chạy ở tick market-only.
- `cachedPredFor` (cascade): chỉ đọc khi `ENTRY_CASCADE>0`; deploy R4 đặt `ENTRY_CASCADE=0` ⇒ không chạy.
- `selPnp`/`selFeat45` (L523-525): reset mỗi tick, CHỈ đọc trong block SELECTOR (buildS1Pool/buildValueMap)
  ⇒ không đọc ở tick market-only.
Sau khi bỏ skip: tick market-only predict full universe ⇒ mọi reader thấy giá trị y hệt bản cũ.

## 5. RÀNG BUỘC CỨNG
- 183 test cũ 0 fail + test mới PASS. `mvn -o test` 0 fail.
- Cấm `System.out`/`System.err`/`printStackTrace` trong khối chạm vào (SLF4J).
- KHÔNG đổi hằng số gate/selector/sizing. KHÔNG đổi thứ tự feature 45.
- DEV ≤ 2025-12-31; 2026 = HOLDOUT. KHÔNG push file dữ liệu lớn. KHÔNG ghi 242.

## 6. THỨ TỰ
1. Commit file này (ghi hash).
2. FIX 2.2 (bỏ market-only skip) + unit test; GIỮ OI cache.
3. Build `mvn -o test` → 0 fail.
4. Bench `PassSpeedBenchV2` đo timing + parity (old vs new).
5. Viết `docs/result/RESULT_PASS_SPEED_V2.md` + `docs/plan/PLAN_DEPLOY_R4_1M_V3.md` + cập nhật
   `PLAN_R4_LIVE_1M_V2.md` (chốt A thay B). Commit SAU.
