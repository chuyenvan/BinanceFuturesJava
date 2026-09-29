# PREREG_PASS_SPEED_V3 — B6: hạ 1 lượt live về ~1s (ticker cache + OI double-buffer + S1 prefetch), GIỮ PARITY

Chốt lúc: **2026-09-29**, TRƯỚC khi chạy bất kỳ phép đo nào. Commit file này PHẢI có TRƯỚC mọi
commit kết quả. Nếu đảo thứ tự → toàn bộ số đo PASS-SPEED-V3 bị coi là VOID.

Nền: B5 (`f98208d`) bỏ market-only skip (đúng, bắt lỗi CS-rank), parity toàn pipeline PASS
(60/60). Còn 2 nghẽn: (1) **ticker 1000' đọc lại MỖI tick ~1.8–2.4s** (phần lớn 1 lượt);
(2) **OI cold refresh ~30s/giờ** + **S1 ~12.5s/giờ** vẫn chặn tick. Owner mục tiêu ~1s.

Phạm vi: **CHỈ code live (selector/shadow Oracle)** + bench read-only. **KHÔNG deploy, KHÔNG restart
shadow-c3, KHÔNG ghi gì lên 242**. KHÔNG chạm 2026/HOLDOUT, 0 sim/0 train.

---

## 0. Vì sao (audit MASTER B5 `f98208d`)

B5 đúng: bỏ market-only skip bắt được lỗi cross-sectional rank (parity hole của B4). Còn lại:
1. **Parity B5 mới chỉ 60 coin × 1 snapshot** (feature45/pNoPump/net015), chưa kiểm S1 score sau khi
   `S1RankerLive.ensureOi` đổi sang batch, chưa MAP/GATE.
2. **Steady ~2.1–2.7s**, trong đó ticker 1000' đọc lại MỖI tick 1.8–2.4s = phần lớn. Mỗi giờ 1 tick
   chặn ~30s (OI cold) + S1 ~12.5s.

## 1. NGUYÊN TẮC PARITY (BẮT BUỘC, mở rộng từ B5)

Mọi **output quyết định** phải BIT-IDENTICAL cũ (`f98208d`) vs mới trên **≥30 tick liên tiếp** và
**FULL universe (KHÔNG subset 60)**: feature 45 mọi coin, `pNoPump`, `net015`, **S1 score (mọi coin)**,
**[MAP] multiset**, **[GATE] thr/n_pass**, **danh sách symbol sẽ vào lệnh** (BIG_DOWN/DCA/
PREDICT_SYMBOL_TRADE). Bench read-only, stub mọi ghi, KHÔNG ghi 242.

## 2. THIẾT KẾ CHỐT (trước khi đo)

### 2.1 Ticker cache (bỏ đọc lại 1000' mỗi tick) — THẮNG CHÍNH
`DetectEntrySignal2TradeNormal.checkMarketLevelChange2Trade` hiện gọi
`readDataForSymbols(now - 1000', 1000)` mỗi tick = đọc+giải nén+parse 1000 phút × ~736 symbol ≈ 7MB.

Thiết kế `LiveTickerWindow` (class mới, instance trong `DetectEntrySignal2TradeNormal`):
- Cache per-symbol các nến 1m ĐÃ parse (`KlineObjectSimple`) theo cửa sổ trượt 1000'.
- Mỗi tick CHỈ đọc (BatchRead, retry sẵn) các phút MỚI `(lastLoadedMinute, floor(now)-1']`, append;
  drop phút `< floor(now)-999'` (trượt cửa sổ).
- **Full reload** khi: khởi động (cache rỗng), thiếu phút (gap/jump thời gian), đổi kích thước cửa sổ.
- Trả `Map<String, List<KlineObjectSimple>>` time-ascending, cùng quy ước append-`USDT` y hệt
  `readDataForSymbols`.

**Cơ sở parity (chốt trước):**
(a) Nội dung nến (open/high/low/close/volume) từ CÙNG record Aerospike ⇒ BIT-IDENTICAL.
(b) `startTime` nến cũ (full-read) = `now-1000'+i·1'` (KHÔNG căn phút), cache nạp tăng dần căn phút ⇒
    lệch nhau ≤1' (offset sub-phút của `now`, tick nổ ở giây 6–10). Chứng minh offset này **VÔ HẠI**:
    mọi consumer của `time`/`startTime` đều chuẩn hoá về phút hoặc thô hơn — `getTopCoin` (chia nguyên
    `/TIME_MINUTE`), OI `floorKey` (merge_asof 2h), S1 `(now/H)·H` (căn giờ), `normalizeDateYYYYMMDDHHmm`
    (format cắt giây), `saveAiPrediction1M` (key cắt phút). ⇒ feature45/pNoPump/net015/S1/MAP/GATE
    BIT-IDENTICAL. (c) `time` = startTime nến BTC cuối (luôn là phút mới ⇒ tươi).
- **Đo: ≥30 tick liên tiếp full universe, parity toàn pipeline (mục 1).**

### 2.2 OI cold refresh KHÔNG chặn tick — double-buffer
`LiveOiFeatProvider.refreshIfStale` hiện reload ĐỒNG BỘ trong `beginTick` khi `pipelineFreshTs` tăng
(~30s/giờ). Đổi:
- `volatile` **Snapshot** (`Map<String,TreeMap<Long,Float>[]>` + `freshTs`) đọc qua tham chiếu nguyên tử.
- Thread nền (đã có, 10s) phát hiện `pipelineFreshTs() > current.freshTs` ⇒ tải buffer MỚI ở nền ⇒
  `current = newSnapshot` (swap nguyên tử tại ranh giới tick, KHÔNG chặn tick).
- `beginTick` chỉ đăng ký universe + khởi động nền; `lookup` đọc `current` (không chặn).
- **Độ trễ tối đa so bản cũ:** tick rơi trong cửa sổ reload nền (~30s, 1 lần/giờ) dùng OI cũ hơn bản
  cũ ≤ **~30s** (thời gian reload). OI merge_asof tol 2h + cadence OI 60' ⇒ **vô hại** (dữ liệu OI vốn
  chỉ đổi mỗi giờ). Guard `OI_STALE_HALT` vẫn đọc `pipelineFreshTs()` THẬT (không qua cache) ⇒ không đổi.
- **KHÔNG ghi 242.** Tùy chọn chunk-NGÀY (writer ghi thêm vào Aerospike LOCAL Oracle 127.0.0.1:3222):
  KHÔNG làm ở task này (cần sửa phía ghi + backfill); double-buffer đã bỏ chặn tick. Ghi rõ ở result.

### 2.3 S1 hourly (~12.5s) — prefetch nền + swap nguyên tử
`S1RankerLive.ensureOi` đọc OI 2 set (chunk-tháng ~24h) mỗi giờ ~12.5s chặn tick selector đầu giờ. Đổi:
- Thread nền (daemon) prefetch OI cho giờ kế (dùng `lastUniverse` ghi nhớ từ tick trước) khi
  `pipelineFreshTs` vượt mốc giờ; swap vào `oiBuffer` (volatile) nguyên tử.
- `ensureOi` dùng buffer prefetch nếu đúng giờ, ngược lại fallback đọc đồng bộ (hiếm, tick đầu/cold).
- **Parity S1 score:** bench so OLD vs NEW trên CÙNG snapshot (dữ liệu bất biến) ⇒ cùng OI/closes ⇒
  score BIT-IDENTICAL. Trên live, độ trễ nạp OI ≤ ~1 chu kỳ reload, cùng bản chất mục 2.2.

### 2.4 Instrument timing
`[PASS-TIMING]` thêm mốc: ticker (cache-hit vs full), OI (hit vs swap), S1, tổng. Thuần LOG.

## 3. BENCH (read-only, stub ghi, KHÔNG ghi 242)
`PassSpeedBenchV3` (mới): replay **≥30 tick liên tiếp** trên FULL universe, so OLD (`f98208d` full-read
ticker + OI sync) vs NEW (ticker cache + OI double-buffer + S1 prefetch) trên CÙNG `now` mỗi tick:
feature45 + pNoPump + net015 + **S1 score mọi coin** + **[MAP] multiset** + **[GATE] thr/n_pass** +
**danh sách symbol vào lệnh**. Shadow nặng gây EOF ⇒ chạy ngoài giờ tick / giảm tần suất, KHÔNG thu hẹp
universe (báo rõ nếu phải làm).

## 4. TIMING (end-to-end p50/p95/max, kể cả tick đầu giờ)
Mục tiêu: **p50 ≤ 1s, p95 ≤ 3s, max ≤ 5s**. Báo thật nếu không đạt + phần còn nghẽn.

## 5. RÀNG BUỘC CỨNG
- `mvn -o test` 0 fail (181 PASS cũ B5 + test mới). Cấm `System.out`/`printStackTrace` (SLF4J).
- KHÔNG đổi hằng số gate/selector/sizing/feature 45. KHÔNG đổi thứ tự đọc.
- DEV ≤ 2025-12-31; 2026 = HOLDOUT. KHÔNG ghi 242. KHÔNG push file dữ liệu lớn.
- KHÔNG deploy/restart shadow-c3 (app tự restart theo `ThreadAutoRestartProgram`, không phải mình).

## 6. THỨ TỰ
1. Commit file này (ghi hash).
2. Implement 2.1–2.4 + unit test.
3. Build `mvn -o test` → 0 fail.
4. Bench `PassSpeedBenchV3` parity + timing.
5. Viết `docs/result/RESULT_PASS_SPEED_V3.md` + cập nhật `PLAN_DEPLOY_R4_1M_V3.md`. Commit SAU.
