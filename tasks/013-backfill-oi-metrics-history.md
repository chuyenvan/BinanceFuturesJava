---
id: 013
status: CANCELLED
depends_on: []
touches_live_process: false
writes_242_data: false
resource: kaggle_distributed
checkpoint: true
max_retry: 2
report: docs/reports/013.md
require_review: true
---

# TASK-013: Verify + backfill OI / long-short / taker history từ data.binance.vision/metrics

- **status:** TODO (data — mở khoá chân OI cho funding model). CHẠY ĐƯỢC NGAY (độc lập).
- **owner:** _(supervisor giao headless)_ · **status:** code+test DONE, gate user DUYỆT → headless LAUNCH FULL · **updated:** 2026-06-15 · **report:** docs/reports/013.md
- **Liên hệ:** ADR-0011 §5.3 (OI/LS/taker — đảo kết luận "không backfill được"). Forward poll cho live = TASK-007 phần C (riêng). Đây là HISTORY cho train.

## Bối cảnh (user phát hiện 2026-06-13)
`https://data.binance.vision/?prefix=data/futures/um/daily/metrics/<SYMBOL>/` — dump daily, mỗi file 1 ngày, granularity ~5m, **CÓ từ 2020** (user kiểm BTC). Cùng host đã dùng backfill ticker (004/005). Header:
```
create_time, symbol, sum_open_interest, sum_open_interest_value,
count_toptrader_long_short_ratio, sum_toptrader_long_short_ratio,
count_long_short_ratio, sum_taker_long_short_vol_ratio
```
→ `sum_open_interest_value` (USDT) = OI để dùng (chuẩn hoá cross-coin); + long/short (top-trader account & vị thế, global) + taker buy/sell. Giải chân thiếu nhất của funding (ADR-0011).

## BƯỚC 1 — VERIFY (GATE, làm TRƯỚC, KHÔNG backfill vội)
Báo cáo 4 điểm cho user/Desktop soát trước khi tải đại trà:
1. **Granularity + format:** tải 1–2 file daily (BTC + 1 alt) → đếm dòng/ngày (288 = 5m?), xác nhận bước thời gian + timezone của `create_time` (UTC?) + có header/đuôi lạ.
2. **Coverage per-coin (PHÂN TÍCH CHI TIẾT — user nhấn):** lập **bảng mọi coin → [firstSeen, lastSeen] metrics + #ngày thiếu (gap)**. Kiểm cụ thể "đủ lịch sử không": vd coin niêm yết **2023-01-04** thì metrics CÓ đủ từ 2023-01-04 hay khuyết đoạn đầu? **Đối chiếu firstSeen-metrics vs firstSeen-ticker** (từ lifecycle 010): coin có ticker mà thiếu metrics (hoặc ngược) → đánh dấu. Alt chỉ có từ ngày list — KHÔNG giả định mọi coin từ 2020. **Xuất bảng coverage ra file** để Desktop/user soát.
3. **Đơn vị khớp forward:** so `sum_open_interest_value` (metrics) vs `openInterestHist.sumOpenInterestValue` (API, dùng ở 007-C) tại vài mốc TRÙNG → cùng định nghĩa/đơn vị? Lệch → phải chuẩn hoá kẻo **bậc thang train/serve**.
4. **Dedup + gap:** mẫu user dán đã có 2 dòng trùng → cần dedup theo `create_time`; đếm ngày thiếu file.

## BƯỚC 1.5 — CHỐT SCHEMA OI CHUNG (thống nhất history + forward — user: "tránh mỗi ông lưu một kiểu")
History (013) và forward poll (007-C) **PHẢI ghi CÙNG** set + key + value. Chốt 1 schema, cả hai đường tuân + feature extractor chỉ thấy MỘT schema (không phân biệt nguồn):
- **Set/bins:** chốt tên set (vd `open_interest` cho OI value; LS + taker lưu bins/set riêng nhưng CÙNG key+granularity). 
- **Granularity 5m** (theo metrics) — forward poll chuẩn hoá về mốc 5m để khớp (không ghi mốc lổn xộn).
- **Value:** Snappy `Map<Long,Float>` per symbol per metric (như funding), đơn vị thống nhất (OI = USDT notional `sum_open_interest_value`).
- ⚠️ Nếu 007-C (đang làm) đã lỡ ghi khác → **đồng bộ về schema này**; ghi rõ để CCD làm 007-C + 013 dùng chung. Đây là phần "tổ chức lại ingest" user yêu cầu.

## BƯỚC 2 — BACKFILL (chỉ sau VERIFY PASS + user OK)
- Tải metrics 2020→nay cho universe USDT-perp (ưu tiên coin trong scope train).
- Lưu Aerospike: set mới cho OI value (+ set/bins cho LS + taker). Snappy `Map<Long,Float>` per symbol per metric, **bắt chước `writeFundingMap`** (guard chống mất lịch sử). Ghi **226** (train) — Kaggle worker chỉ tới được 226. **KHÔNG ghi 242 từ Kaggle** → đẩy 242 tách riêng **TASK-040** (job chạy TRÊN 226 sync Aerospike 226→242 + validate đầy đủ).
- Dedup theo key 5m; skip+log gap.
- **Validate:** recompute-compare vài mốc; cross-check OI quanh cú sập (OI tụt mạnh khi sập?); coverage per-coin khớp firstSeen (BƯỚC 1).

## An toàn
- Đọc `data.binance.vision` (cơ chế như 004/005). Chỉ THÊM set OI/LS/taker, đọc-only. KHÔNG đụng ticker/funding/live/config. SLF4J. Throttle tải (nhiều file).

## Acceptance
- [x] BƯỚC 1: báo cáo 4 điểm verify (xem (Code điền); coverage.csv 896 symbol). **GATE — chờ user OK.**
- [ ] BƯỚC 2 (sau OK): set OI/LS/taker 2020→nay, dedup, validate recompute + cross-check sập + coverage per-coin.
- [x] Đơn vị khớp forward (007-C) — diff 0.000%, KHÔNG bậc thang train/serve.

## (Code điền)

### BƯỚC 1 — VERIFY (DONE 2026-06-13, GATE — chờ user OK trước BƯỚC 2)
> Tool: `C:\Users\pc\oi-verify\verify_oi_metrics.py` (đọc-only data.binance.vision + fapi). Output: `coverage.csv` (896 dòng) + `verify.log`.

**B1 — granularity + format + tz:**
- Path: `data/futures/um/daily/metrics/<SYMBOL>/<SYMBOL>-metrics-YYYY-MM-DD.zip` (+ `.CHECKSUM`). Header đúng 8 cột như task.
- **Granularity 5m**: file gần đây (BTC 2026-06-10) = **288 dòng/ngày**, step 300s, nhãn theo CUỐI nến (00:05 → 24:00 hôm sau), 0 trùng.
- **TZ = UTC** (xác nhận ở B1-đơn-vị: đọc `create_time` thẳng dạng UTC khớp ms API diff 0%).
- ⚠️ **File CŨ bị NHÂN ĐÔI**: BTC 2020-09-01 = **576 dòng = mỗi create_time lặp 2 lần** (288 trùng), boundary khác (00:00→23:55). ⇒ **BẮT BUỘC dedup theo create_time** + chuẩn hoá mốc 5m khi backfill.

**B1 — coverage per-coin (file `coverage.csv`, 896 symbol; 0 symbol thiếu data):**
- 896 symbol có metrics: **774 USDT**, 39 USDC, ~83 khác (BUSD…). Nhiều hơn ~554 ticker sống ⇒ gồm coin DELIST (giá trị survivorship!).
- **firstSeen theo năm (USDT):** 2020:1(chỉ BTC), 2021:137, 2022:26, 2023:99, 2024:131, 2025:242, 2026:138.
- **PHÁT HIỆN CHỐT — nền metrics bắt đầu ~2021-12-01, KHÔNG phải 2020:** coin list TRƯỚC 2021-12 chỉ có metrics TỪ 2021-12-01 (ETH list 2019→metrics 2021-12-01; LUNA/BTCST tương tự). Coin list 2022+ thì metrics = đúng ngày list. ⇒ cụm "2021:137" thực chất là đống dồn về mốc sàn 2021-12-01. **Chỉ BTC có 2020-09.** Tiêu đề "2020+" chỉ đúng cho BTC.
- Cross-check firstSeen-metrics vs firstSeen-ticker(klines) — mẫu:

  | symbol | ticker_first | metrics_first | metrics_last | mDays | gap | nhận xét |
  |---|---|---|---|---|---|---|
  | APTUSDT | 2022-10-19 | 2022-10-19 | 2026-06-12 | 1333 | 0 | khớp ngày list |
  | SUIUSDT | 2023-05-03 | 2023-05-03 | 2026-06-12 | 1136 | 1 | khớp ngày list |
  | ARBUSDT | 2023-03-23 | 2023-03-23 | 2026-06-12 | 1178 | 0 | khớp |
  | WIFUSDT | 2024-01-18 | 2024-01-18 | 2026-06-12 | 877 | 0 | khớp |
  | 1000BONKUSDT | 2023-11-22 | 2023-11-22 | 2026-06-12 | 934 | 0 | khớp |
  | ETHUSDT | 2019-12-31 | **2021-12-01** | 2026-06-12 | 1655 | 0 | metrics MUỘN hơn list (floor sàn) |
  | LUNAUSDT | 2021-01-28 | **2021-12-01** | 2024-06-20 | 195 | 738 | delist, data THƯA |
  | BTCSTUSDT | 2021-03-04 | **2021-12-01** | 2024-07-15 | 85 | 873 | delist, gần như không có data |
- **Gap:** 101/774 USDT có gap>0. Gap lớn dồn vào coin CŨ/DELIST data thưa (BTCST 873, CVC 863, LUNA 738…). Coin sống gần đây gap 0–1.
- **Delist:** 94 USDT lastSeen < 2026-05 (ngừng cập nhật ⇒ nghi delist) — chính là tập survivorship cần cho train.
- **Khối lượng BƯỚC 2:** tổng ~**545,779 file-ngày** (mọi symbol). LS+taker NẰM CHUNG file metrics ⇒ 1 lần tải đủ 4 metric. ~12KB/file ⇒ ~6.5GB zip; cần throttle + resume.

**B1 — đơn vị metrics vs openInterestHist (007-C):** ✅ **diff = 0.000% tại offset=same** cả 6 mốc (BTC 2026-06-10). `sum_open_interest_value` (metrics) **== `sumOpenInterestValue`** (API), cùng đơn vị USDT-notional, create_time = UTC đọc thẳng, KHÔNG lệch nhãn. ⇒ history (013) + forward (007-C) khớp tuyệt đối, **không bậc thang train/serve**.

### BƯỚC 1.5 — SCHEMA CHUNG — ✅ USER CHỐT 2026-06-14 (cả 4 điểm)
> (1) 5 set như bảng dưới — OK. (2) dedup theo `create_time` + chuẩn mốc 5m — OK. (3) backfill **TOÀN BỘ** (gồm coin delist — survivorship) — OK. (4) ghi **242 (source)** + **replicate sang 226** (tool 034) — OK. Kéo theo: forward 007-C phải mở rộng ghi đủ LS/taker (TASK-035).

Granularity 5m UTC; mỗi metric 1 set, Snappy `Map<Long,Float>` per symbol (như funding), key = symbol UPPER, dedup theo ts. 007-C forward đã dùng `open_interest`/bin `oi_data` cho OI value ⇒ history ghi CÙNG set đó. Đề xuất 4 set còn lại:
| metric (cột CSV) | set đề xuất | ý nghĩa |
|---|---|---|
| sum_open_interest_value | `open_interest` (đã có ở 007-C) | OI notional USDT |
| count_toptrader_long_short_ratio | `oi_ls_toptrader_acc` | L/S top-trader theo tài khoản |
| sum_toptrader_long_short_ratio | `oi_ls_toptrader_pos` | L/S top-trader theo vị thế |
| count_long_short_ratio | `oi_ls_global_acc` | L/S toàn cầu theo tài khoản |
| sum_taker_long_short_vol_ratio | `oi_taker_vol` | taker buy/sell vol ratio |
⚠️ 007-C forward hiện CHỈ ghi OI value (chưa LS/taker). Nếu chốt schema này → 007-C cần mở rộng forward ghi đủ 4 metric kia (cùng set/key) để history+forward đồng bộ.

### BƯỚC 2 — BACKFILL theo MASTER–WORKER phân tán (tái dùng pattern `RunHpoMaster_Distributed` + `RunWorkerKaggle`)
545k file-ngày tuần tự trên 226 quá lâu. Chia nhỏ **per-symbol** → 1 headless MASTER phát task → **5 Kaggle CPU WORKER** chạy song song (Kaggle tới 226). **Queue Aerospike = checkpoint phân tán** (idempotent, resume tự nhiên — rerun chỉ làm symbol chưa DONE, không lặp từ 0).

**Queue (Aerospike 226, giống HPO):**
- `oi_backfill_queue` — task PENDING/RUNNING, mỗi task = 1 symbol (~896, gồm delist). Xong → xoá.
- `oi_backfill_done` — đánh dấu symbol DONE (get by key, KHÔNG scan) → rerun skip.

**MASTER `BackfillOiMaster`** (headless, chạy dev/226 — tới 226): liệt kê universe symbol có metrics (từ B1 `coverage.csv` 896 / lifecycle 010, gồm delist) → symbol chưa DONE thì ném task vào `oi_backfill_queue` (PENDING). Theo dõi đếm DONE, in dashboard; queue rỗng + đủ → `System.exit(0)`.

**WORKER `BackfillOiWorker`** (5 Kaggle CPU, `IS_KAGGLE_MODE=true`): `while(true)` fetchTask race-safe (GenerationPolicy như RunWorkerKaggle) + STALE_RUNNING cướp task chết. Task=1 symbol → tải `metrics/<SYMBOL>/*.zip` 2020→nay → parse 8 cột → **dedup create_time + chuẩn 5m** → ghi **226** 5 set (`open_interest`+`oi_ls_toptrader_acc/pos`+`oi_ls_global_acc`+`oi_taker_vol`) bắt chước `writeFundingMap` (merge guard, không ghi đè rỗng) → mark `oi_backfill_done` + xoá queue. Queue rỗng → `System.exit(0)` (#6). Throttle tải vision/worker.

**ĐẨY 226→242 (source, kiến trúc A):** Kaggle worker chỉ ghi được 226. Sau khi backfill xong (226 đủ), chạy 1 job TRÊN 226 đẩy 5 set 226→242 (bổ sung tool 034 chiều **226→242**, hoặc ghi thẳng 242 từ 226). 242 = source như forward 007-C; 226 đã sẵn cho train.

**resource = `kaggle_distributed`** (master headless + ≤5 Kaggle worker). Queue Aerospike LÀ checkpoint. Validate (require_review): recompute vài mốc (metrics vs API, đã 0% B1); cross-check OI tụt quanh sập; coverage per-coin khớp firstSeen; dedup đúng (không còn create_time trùng).

**B2 kết quả (#record/range/validate):** ✅ CODE+TEST DONE → **REVIEW** (chi tiết: docs/reports/013.md).
- ⚠️ **SCHEMA SỬA (user chốt):** 1-record/symbol "như funding" KHÔNG vừa Aerospike với OI 5m×6năm
  (BTC 607,595 điểm → `Record too big`). → **CHIA THÁNG `SYMBOL_yyyyMM`** (GMT+7), ~8.9k điểm/chunk,
  khớp pattern record-tháng kline/15m/4h. `writeMetricMap226/242`+`getMetricMap226/242` (DataManager) đã
  đổi sang chunk-tháng. bin: OI=`oi_data` (khớp 007-C), LS/taker=`m_data`.
- **TEST (dev→226):** BTCUSDT 2,112 file → 682,837 dòng thô → **607,595 mốc 5m** (dedup nhân-đôi file cũ);
  LUNAUSDT(delist) 46,859. **offGrid5m=0** mọi set. **raw-recompute value maxDiff=0.000000%** (BTC 864 mốc,
  LUNA 576). worker self-verify đọc-lại-count trước mark DONE. 5 set ghi THẬT @226 cho 2 symbol.
- **CODE:** `research/oibackfill/{OiMetricSets,VisionMetricsClient,BackfillOiMaster,BackfillOiWorker,
  BackfillOiVerify,PushOiSetsTo242}` + `BackfillOiMaster --reset` (truncate queue/done).
- **CÒN LẠI sau review OK:** LAUNCH FULL (master no-args enqueue ~894 còn lại + 5 Kaggle worker) → queue cạn
  → `PushOiSetsTo242` TRÊN 226 (đẩy 226→242) → validate cuối (OI tụt quanh sập + coverage firstSeen).
- **❓ REVIEW cần người chốt:** 007-C forward đang ghi OI **1-record/symbol** trên 242 → migrate sang
  chunk-tháng `SYMBOL_yyyyMM` (TASK-035) để history+forward MỘT schema? (đề xuất: có).

## Quy trình HEADLESS làm trọn (code → test → GATE → launch → monitor)
> **TRẠNG THÁI 2026-06-15 — supervisor giao headless:** bước 1–2 (code `research/oibackfill/*` + test 2 symbol BTC/LUNA dev→226, recompute 0.000000%) **DONE**; gate bước 3 **user DUYỆT**. Headless BẮT ĐẦU TỪ **bước 4** — lưu ý CHƯA TừNG chạy Kaggle lần nào, phải setup distributed Kaggle.
Một worker headless tự chạy trọn, CHỈ dừng đúng 1 gate ở bước ghi data thật (trước khi nhân 5 worker):
1. **Code:** viết `BackfillOiMaster` + `BackfillOiWorker` (bê khung `RunHpoMaster_Distributed`/`RunWorkerKaggle`, đổi payload task=symbol, đổi phần chạy-engine → tải-vision-ghi-OI) + tool đẩy `226→242`. javac11 PASS.
2. **TEST NHỎ (bắt buộc):** master ném ~2 symbol (1 sống + 1 delist, vd BTCUSDT + LUNAUSDT) → 1 worker chạy → ghi 226. Verify đưa SỐ vào report: đọc lại 226 đếm record; recompute vài mốc vs API (đã 0% ở B1); dedup đúng (không còn create_time trùng); KHÔNG ghi đè mất data cũ.
3. **GATE = REVIEW:** DỪNG, RESULT `STATUS=REVIEW` kèm số test. Người soát mẫu (rẻ) — schema/dedup/không-mất-data đúng chưa. **KHÔNG launch full khi chưa soát.**
4. **LAUNCH FULL — SETUP KAGGLE DISTRIBUTED (lần đầu):** (a) build jar có `System.exit(0)` → upload Kaggle dataset (như `java-run`); (b) viết kernel chạy `BackfillOiWorker` (IS_KAGGLE_MODE, enable_internet, đọc/ghi 226) theo `docs/RUNBOOK_kaggle_multi_cpu.md`; (c) **TEST 1 kernel Kaggle trước** (rẻ — chưa chạy Kaggle bao giờ): 1 worker lấy vài task từ queue, ghi 226 OK → mới push đủ; (d) `BackfillOiMaster` (no-args) enqueue ~894 symbol vào `oi_backfill_queue`@226; (e) push **5 kernel** worker. Ghi BÀN GIAO #4: dataset slug, 5 kernel slug, cách đếm `oi_backfill_queue`/`oi_backfill_done`. **REPORT THEO CHECKPOINT** vào docs/reports/013.md cho Desktop phân tích: `[jar built][dataset up][1 worker Kaggle test OK][master enqueued N][5 worker running][queue cạn]`. Lỗi bước nào → RESULT `NEEDS_HUMAN` nêu rõ bước + log (đừng nhân lỗi ra 5 kernel).
5. **MONITOR (poll, KHÔNG giữ session nhiều giờ):** poll queue count định kỳ; worker chết → STALE → worker khác cướp (tự lành). Queue cạn → đẩy `226→242` + validate cuối (cross-check OI tụt quanh sập, coverage firstSeen) → RESULT cuối.
> Gate bước 3 là bước RẺ + REVERSIBLE chặn "code sai nhân 5 worker" ở lần đầu ghi data thật (kỷ luật §0.3 AGENT_WORKFLOW). Các bước còn lại headless tự làm, không cần người.
