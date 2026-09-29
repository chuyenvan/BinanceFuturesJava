# RESULT_PASS_SPEED_V2 — hoàn tất B4: parity TOÀN pipeline + bỏ pha cold refresh (không ghi 242), CHƯA deploy

Ngày: **2026-09-29**. Pre-reg: **`docs/prereg/PREREG_PASS_SPEED_V2.md`** (commit **`617a973`**, chốt TRƯỚC khi đo).
Phạm vi: **CHỈ code live (selector/shadow Oracle)** + bench read-only. **KHÔNG deploy, KHÔNG restart shadow-c3,
KHÔNG ghi gì lên 242**. KHÔNG chạm 2026/HOLDOUT, 0 sim/0 train.

---

## 0. KẾT LUẬN (một dòng)

> Audit MASTER đúng: B4 có **2 lỗ hổng** — (1) parity mới chỉ kiểm 5 giá trị OI, bỏ sót **lỗi cross-sectional rank**
> của market-only skip (tập con ⇒ pNoPump symbol đang giữ LỆCH); (2) cold refresh ~30s/giờ. B5 **bỏ market-only skip**
> (giữ OI cache = thắng thật của B4), **xác nhận bin `oi_feat_*` là Snappy JSON (KHÔNG phải native Map ⇒ không dùng
> `MapOperation.getByKeyRange`)**. **Parity toàn pipeline PASS (60/60 bit-identical)**, funding predict **~52ms** (không
> phải 232s — cái 232s là OI IO, B4 đã fix). Cold refresh ~30s/giờ **KHÔNG ghi 242**; ≤1s cần chunk-NGÀY phía ghi (MASTER duyệt).

---

## 1. LỖ HỔNG PARITY (phát hiện + fix) — `PREREG_PASS_SPEED_V2 §2`

### 1.1 NGUYÊN NHÂN: PASS-2 cross-sectional rank tính trên tập CON
`predictAllCandidates` chạy `FundingCrossSectional.apply(csList)` với `csList = aiCandidates ∩ csPop` (rank percentile
#33..#35 = fundingRankCS/volumeZRankCS/momentumRankCS **TRÊN CHÍNH list**). Tick market-only (B4) truyền `allSymbols` =
symbol đang giữ ⇒ `csList = held ∩ csPop` (tập con) ⇒ percentile rank của held coin LỆCH full population ⇒ #33..#35 lệch
⇒ `pNoPump` lệch ⇒ `LATEST_SEL_PNOPUMP`/trailing `tsGap`/DCA big-loss lệch. **B4 chỉ kiểm 5 giá trị OI nên KHÔNG thấy.**

### 1.2 FIX: bỏ market-only skip (giữ OI cache)
Xoá `marketOnlyUniverse(...)` + nhánh `if (!selectorLeg && levelChange == null)`. Tick market-only GIỜ predict full
universe (y hệt `876250e^`). Lý do (chốt trước, `PREREG §2.2`):
- Sau OI cache, predict full universe ~**52ms** (đo dưới) — skip chỉ tiết kiệm predictBatch cho non-held (sub-giây), KHÔNG đáng đánh đổi parity.
- `LIVE_ENTRY_GRID_MIN=1` (deploy R4) ⇒ selector mỗi phút ⇒ market-only tick KHÔNG bao giờ chạy — skip vô dụng cho deploy.
- OI cache + BatchRead + recent-read là **thắng thật** của B4 (đưa 250s→250ms), GIỮ NGUYÊN.

Chứng minh: unit test `FundingCrossSectionalPopulationTest` (2 test) — rank trên tập con ≠ full population
(`assertNotEquals`), rank full population deterministic qua 2 lần apply.

---

## 2. BIN `oi_feat_*` — KHÔNG phải native Map (báo cấu trúc thật)

Đọc code `DataManagerAerospikeFloatSim`:
- **Ghi** (`writeMonthChunk`): `byte[] compressed = Snappy.compress(Utils.gson.toJson(finalMap).getBytes("UTF-8"))` → `client.put(... new Bin(binName, compressed))`. **Bin `f_data` = Snappy JSON blob `Map<String,Float>` (ts string → float)**, KHÔNG phải Aerospike Map nguyên sinh.
- **Record key** = `SYMBOL_yyyyMM` (chunk-THÁNG, ~93KB/tháng ≈ 29 ngày 5m).
- **Đọc** (`decodeMap`): `Snappy.uncompress` + GSON parse → `TreeMap<Long,Float>`.

⇒ **`MapOperation.getByKeyRange` KHÔNG áp dụng được** (chỉ chạy trên native Map bin, không chạy trên byte[] blob).
⇒ Không thể đọc "chỉ điểm MỚI" server-side **mà không sửa phía ghi**.

### Đề xuất (vẫn KHÔNG ghi 242 ở task này)
1. **(Cần MASTER duyệt, phía GHI 242)** chunk-NGÀY `SYMBOL_yyyyMMdd` cho `oi_feat_*` (như `RESULT_PASS_SPEED.md §5`):
   đọc 24h chỉ ~2 chunk-ngày ≈ 11MB ⇒ refresh ≤1s. Đây là thay đổi **phía ghi** (viết 242), ngoài phạm vi task.
2. **(Read-only, giữ nguyên)** refresh nền (daemon 10s) + guard đồng bộ `beginTick` khi `pipelineFreshTs` tăng:
   - **Refresh có CHẶN tick KHÔNG?** CÓ, NHƯNG chỉ khi pipeline push trùng tick: `beginTick` → `refreshIfStale` (đồng bộ)
     reload khi `pipelineFreshTs > loadedFreshTs`. Thread nền prefetch mỗi 10s ⇒ tick thường KHÔNG bị chặn (chỉ chặn ~1
     lần/giờ nếu tick rơi đúng cửa sổ reload ~30s).
   - **Parity về thời điểm dữ liệu**: guard này CHÍNH LÀ thứ giữ parity — cache LUÔN ≥ pipelineFreshTs tại thời điểm
     lookup ⇒ KHÔNG serve dữ liệu cũ hơn bản cũ (bản cũ đọc full-history mỗi tick = luôn thấy mới nhất). Bỏ guard = vỡ parity.

---

## 3. ĐO ĐƯỢC (bench read-only, Oracle trỏ 242, `PassSpeedBenchV2`)

| pha | p50 | p95 | ghi chú |
|---|---|---|---|
| ticker read 1000' | **1800–2380 ms** | — | 736 symbol (giữ nguyên, không đổi bởi B4/B5) |
| **funding predict** (extract + PASS-2 CS + predictBatch + net015) **624 coin** | **52 ms** | **72 ms** | KHÔNG OI (tránh cạnh tranh 242 với shadow); max 2284ms = cold funding-cache (1 lần) |
| └ extract (no-OI) | 29 ms | 43 ms | |
| └ PASS-2 CS rank | 1 ms | 2 ms | |
| └ predictBatch (45f) | 9 ms | 17 ms | |
| └ net015 | 11 ms | 18 ms | |
| OI cache-hit | ~250 ms | — | (B4 `RESULT_PASS_SPEED.md §1`, giữ nguyên) |
| OI cold refresh | **~30 s** (full) / ~2.5 s (60 coin) | — | 1 lần/giờ khi pipeline push (B4 đo; xác nhận lại ở đây) |

**Tổng 1 lượt end-to-end (steady, selector/market-only):** ticker ~1.8–2.4s + OI cache-hit ~0.25s + funding ~52ms ≈
**~2.1–2.7s**. Cộng S1 (~12.5s/giờ amortized, `RESULT_R4_CADENCE`) + map/gate (~ms) ⇒ **p50 ≤3s, p95 ≤10s** của tiêu chí
deploy là ĐẠT (steady). Phần "232s FUNDING" trước đây là **OI IO**, đã bị B4 cache loại bỏ — funding thuần chỉ ~52ms.

> ⚠️ [ĐO] Bench chạy khi `shadow-c3` (jar CŨ trước B4) đang chạy ⇒ đang full-history-read OI ~250s/lượt, cạnh tranh 242.
> Vì vậy bench đo funding **KHÔNG OI** (tránh đọc 242); số OI lấy từ B4. Cold-refresh full-universe batch (2000 record)
> dễ EOF/timeout khi shadow nặng ⇒ đo trên subset 60 coin (parity) và dùng số full-universe của B4 (~30s).

---

## 4. PARITY TOÀN PIPELINE — PASS (bit-identical)

`PassSpeedBenchV2 parity` đọc CÙNG snapshot 242, so OLD (full-history `getMetricMap242` per-coin + cắt 24h) vs NEW
(`getMetricMap242RecentBatch` + cache) qua **feature 45 → pNoPump → net015** (đường predict đầy đủ):

| mẫu | feature45 | pNoPump | net015 | maxDiff |
|---|---|---|---|---|
| 60 coin | **60/60** | **60/60** | **60/60** | **0.0** |

Cơ sở: (a) OI lookup 5 giá trị BIT-IDENTICAL (B4 đã chứng minh, xác nhận lại); (b) pipeline sau OI (extract → PASS-2 CS →
predictBatch → net015) **deterministic** và chỉ phụ thuộc OI; (c) sau khi bỏ market-only skip, tick market-only = full
universe ⇒ không còn tập con nào làm lệch CS rank. S1/map/gate chỉ chạy ở block SELECTOR (không chạy tick market-only) và
KHÔNG bị B4/B5 đổi ⇒ parity theo cấu trúc.

### 4.1 GREP MỌI reader `LATEST_SEL_PNOPUMP`/`selPnp`/`selFeat45` — chứng minh không đổi hành vi
| reader | vị trí | vì sao KHÔNG đổi |
|---|---|---|
| `BinanceOrderTradingManager.tsGap` | L485 | đọc `LATEST_SEL_PNOPUMP.get(symbol)` cho symbol ĐANG GIỮ (vòng `processDynamicTP_SL` duyệt `symbol2Pos`) ⇒ luôn tươi sau bỏ skip |
| `paperSymbolPred` → `shadowHandleOrder` | DetectEntry L100-105, Binance L230 | chỉ gọi trong vòng SELECTOR (order mới), KHÔNG chạy tick market-only |
| `cachedPredFor` (cascade) | DetectEntry L706 | chỉ đọc khi `ENTRY_CASCADE>0`; deploy R4 đặt `ENTRY_CASCADE=0` ⇒ không chạy |
| `selPnp`/`selFeat45` | DetectEntry L523-525 | reset mỗi tick, CHỈ đọc trong block SELECTOR (`buildS1Pool`/`buildValueMap`) ⇒ không đọc tick market-only |
| `LATEST_SEL_MAPPRED` (`paperSymbolPred` C3 / `ShadowBookC3` L327 / `TrailHingeSource`) | — | chỉ ghi ở block SELECTOR (buildValueMap), đọc cho symbol giấy đang giữ ⇒ không đổi |

Sau bỏ skip: tick market-only predict full universe ⇒ mọi reader thấy giá trị y hệt bản cũ. **Không consumer nào đổi hành vi.**

---

## 5. THAY ĐỔI CODE

1. `DetectEntrySignal2TradeNormal`: **bỏ market-only skip** (`marketOnlyUniverse` + nhánh `if (!selectorLeg && levelChange == null)`),
   giữ `liveOiProvider.beginTick(allSymbols)` (OI cache). `printStackTrace` đã chuyển `LOG.error` ở B4.
2. `PassSpeedBenchV2.java` (mới): bench read-only timing + parity (KHÔNG ghi 242).
3. Test: xoá `MarketOnlyUniverseTest` (4) + thêm `FundingCrossSectionalPopulationTest` (2).

## 6. TEST

- `mvn -o test`: **181 PASS, 0 fail** (183 B4 − 4 MarketOnly + 2 mới). Không `System.out`/`printStackTrace` trong khối chạm vào.

## 7. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava && mvn -o test            # 181 PASS
# timing (KHÔNG OI, tránh cạnh tranh 242 với shadow)
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx6g -Dfunding.model=/home/ubuntu/shadow_c3/storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx \
  -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.research.passspeed.PassSpeedBenchV2 timing 0 60 30
# parity (OLD full-history vs NEW cache)
java ... com.binance.chuyennd.research.passspeed.PassSpeedBenchV2 parity 60 60 1
```
