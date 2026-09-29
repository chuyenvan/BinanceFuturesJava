# RESULT_PASS_SPEED_V3 — B6: ticker cache + OI double-buffer + S1 prefetch ⇒ 1 lượt live về ~0.6s (GIỮ PARITY), CHƯA deploy

Ngày: **2026-09-29**. Pre-reg: **`docs/prereg/PREREG_PASS_SPEED_V3.md`** (commit **`c93d6a6`**, chốt TRƯỚC khi đo).
Phạm vi: **CHỈ code live (selector/shadow Oracle)** + bench read-only. **KHÔNG deploy, KHÔNG restart shadow-c3,
KHÔNG ghi gì lên 242**. KHÔNG chạm 2026/HOLDOUT, 0 sim/0 train.

---

## 0. KẾT LUẬN (một dòng)

> Nghẽn cuối = **ticker 1000' đọc lại MỖI tick (~1.8–2.4s)** — đã bỏ bằng **cửa sổ trượt** (đọc chỉ phút MỚI mỗi
> tick, full reload khi lệch/khởi động); **OI cold refresh + S1 hourly chuyển sang nền (double-buffer/prefetch, swap
> nguyên tử)** ⇒ 1 lượt steady **p50 ~0.64s** (ticker cache ~83ms), tick đầu giờ KHÔNG còn chặn ~30s+12.5s.
> **PARITY TOÀN PIPELINE PASS**: ticker 30/30 tick × 736 coin BIT-IDENTICAL, feature45/pNoPump/net015 661/661,
> S1 score 736/736. Cold-start (tick ĐẦU TIÊN của process) vẫn ~28s 1 lần (warmup, không phải tick định kỳ).

---

## 1. ĐO ĐƯỢC (bench read-only `PassSpeedBenchV3`, trỏ 242, FULL universe ~736 coin)

### 1.1 PARITY (code `f98208d` OLD vs mới)

| hạng mục | kết quả |
|---|---|
| **ticker cache vs full-read** (30 tick liên tiếp, 736 coin) | **30/30 BIT-IDENTICAL (prices)** |
| full-read ticker avg | **1016 ms/tick** (cũ) |
| ticker cache avg | **116 ms/tick** (gồm 1 full reload đầu; steady ~83ms) |
| **feature45** (funding pipeline full universe) | **661/661 BIT-IDENTICAL** |
| **pNoPump** | **661/661 BIT-IDENTICAL** |
| **net015** | **661/661 BIT-IDENTICAL** |
| **S1 score** (mọi coin) | **736/736 BIT-IDENTICAL** (determinism 2 lần) |
| [MAP] multiset / [GATE] thr/n_pass / danh sách symbol | **SUY THEO CẤU TRÚC** (xem §2) |

### 1.2 TIMING (40 tick liên tiếp, full universe)

| pha | p50 | p95 | max |
|---|---|---|---|
| **TOTAL end-to-end** (ticker cache + OI + funding + net015) | **642 ms** | **2072 ms** | **28433 ms** |
| ticker (cache) | 83 ms | 146 ms | 1882 ms (1 full reload đầu) |
| OI (lookup, cache-hit) | 43 ms | 1514 ms | 2226 ms |

- **p50 = 642 ms ≤ 1s ĐẠT** · **p95 = 2072 ms ≤ 3s ĐẠT** (p95 đuôi gồm cold-start).
- **max = 28.4s = COLD-START** (tick ĐẦU TIÊN của process: ticker full reload ~1.8s + OI cold-load ~24s). Đây KHÔNG
  phải "tick đầu giờ" — nó là warmup 1 lần lúc khởi động (B5 cũ vậy), còn **tick đầu giờ (hằng giờ) GIỜ KHÔNG CHẶN**
  (xem §3).
- S1 warm-up **~22.2s** (1 lần) + S1 OI **~11.2s/giờ** (GIỜ chạy nền prefetch, không chặn tick).

---

## 2. PARITY — vì sao [MAP]/[GATE]/danh sách symbol suy theo cấu trúc (KHÔNG đo trực tiếp)

Pipeline sau OI/feature là **tất định và KHÔNG bị B6 đổi**. B6 chỉ đổi 2 đầu vào:
1. **ticker map** — đã đo **BIT-IDENTICAL** (30/30 tick × 736 coin, mọi giá open/high/low/close/volume).
2. **OI** — double-buffer KHÔNG đổi dữ liệu (vẫn `getMetricMap242RecentBatch` y hệt `f98208d`), chỉ đổi THỜI ĐIỂM nạp.

⇒ feature45 → pNoPump → net015 (đo bit-identical), S1 score (đo bit-identical) → `[MAP]` multiset
(`LiveBuildMap.assign` thuần hàm) → `[GATE]` thr (`EntryGate.threshold` thuần hàm) → danh sách symbol (vòng selPool +
`AIRejectFilter.entryGate`, `predReturn15M` từ entry-model CÙNG đầu vào) **đều tất định ⇒ bit-identical**.

Cơ sở thêm (giữ từ B5 §4.1): không reader `LATEST_SEL_PNOPUMP`/`selPnp`/`selFeat45` nào đổi hành vi — B6 không đụng
consumer nào, chỉ đổi nguồn cấp ticker + cách nạp OI.

### 2.1 Offset sub-phút của `startTime` (ticker cache căn phút vs full-read giữ offset) — VÔ HẠI
Cache nạp tăng dần căn phút ⇒ `startTime` nến lệch full-read ≤1' (offset sub-phút của `now`). Chứng minh vô hại
(pre-reg §2.1): mọi consumer của `time`/`startTime` đều chuẩn hoá về phút hoặc thô hơn — `getTopCoin` (chia nguyên
`/TIME_MINUTE`), OI `floorKey` (merge_asof 2h), S1 `(now/H)·H` (căn giờ), `normalizeDateYYYYMMDDHHmm` (cắt giây),
`saveAiPrediction1M` (key cắt phút). ⇒ mọi quyết định BIT-IDENTICAL (đã đo ở §1.1).

---

## 3. ĐỘ TRỄ TỐI ĐA SO BẢN CŨ (OI double-buffer + S1 prefetch)

| thành phần | bản cũ (B5) | mới (B6) |
|---|---|---|
| OI cold refresh | chặn tick ~30s **mỗi giờ** | nền (double-buffer), tick KHÔNG chặn; tick rơi trong cửa sổ reload ~30s dùng OI cũ hơn **≤ ~30s** |
| S1 hourly OI | chặn tick ~12.5s **mỗi giờ** | nền (prefetch), swap nguyên tử; fallback đồng bộ chỉ khi prefetch chưa kịp (hiếm) |

OI merge_asof tol **2h** + cadence OI **60'** ⇒ dùng OI cũ hơn ≤~30s là **VÔ HẠI** (dữ liệu OI vốn chỉ đổi mỗi giờ).
Guard `OI_STALE_HALT` vẫn đọc `pipelineFreshTs()` THẬT từ 242 (KHÔNG qua cache) ⇒ không đổi.

**Chunk-NGÀY OI (tùy chọn, KHÔNG làm task này):** writer `oi_feat` có thể ghi THÊM bản chunk-NGÀY vào Aerospike LOCAL
Oracle (đã kiểm: `asd` local nghe `127.0.0.1:3222` trên box này) để shadow đọc nhanh hơn. Cần sửa phía ghi + backfill,
NGOÀI phạm vi read-only; double-buffer đã bỏ chặn tick nên không bắt buộc. **KHÔNG ghi gì lên 242.**

---

## 4. THAY ĐỔI CODE

1. `LiveTickerWindow.java` (mới): cửa sổ nến 1m trượt — cache per-symbol, đọc chỉ phút MỚI (BatchRead), full reload
   khi khởi động/clock nhảy/đổi kích thước cửa sổ. `windowBounds()` thuần hàm (unit test).
2. `DetectEntrySignal2TradeNormal`: thay `readDataForSymbols(now-1000', 1000)` bằng `tickerWindow.read(now, 1000)`.
3. `LiveOiFeatProvider`: double-buffer (`volatile Snapshot` data+freshTs, swap nguyên tử); `beginTick` chỉ load đồng bộ
   khi cold-start (`freshTs==0`); thread nền reload khi `pipelineFreshTs` tăng. `clear()`/`pipelineFreshTs()` giữ API.
4. `S1RankerLive`: prefetch OI nền cho giờ kế (`loadOi` tách riêng, `ensureOi` swap buffer prefetch nếu đúng giờ,
   fallback đồng bộ).
5. `PassSpeedBenchV3.java` (mới): bench parity (ticker/funding/S1) + timing, read-only.
6. Test: `LiveTickerWindowTest` (3 test) — window bounds.

## 5. TEST

- `mvn -o test`: **184 PASS, 0 fail** (181 B5 + 3 mới). Không `System.out`/`printStackTrace` trong khối chạm vào (SLF4J).

## 6. TÁI LẬP

```bash
cd /home/ubuntu/src/BinanceFuturesJava && mvn -o test            # 184 PASS
# parity + timing (trỏ 242 read-only; timeout batch nới để tránh EOF khi shadow cạnh tranh)
cd /home/ubuntu/pass_speed_v3   # config.properties có AEROSPIKE_READ_CLUSTER=242
AEROSPIKE_BATCH_TOTAL_TIMEOUT_MS=30000 AEROSPIKE_BATCH_SOCKET_TIMEOUT_MS=20000 \
java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx6g \
  -Dfunding.model=/home/ubuntu/shadow_c3/storage/ai_ml_data/models_funding/Funding_Classifier_Final.onnx \
  -cp binance-java-sdk-1.2.4.jar com.binance.chuyennd.research.passspeed.PassSpeedBenchV3 parity 0 30
# timing: ... PassSpeedBenchV3 timing 0 40
```

## 7. JAR

- sha256: `31a24f90981e6eb8518cbaea8eb7007431f8677c9e1d8c494e1f6c484dda32d5` (build 2026-09-29).
