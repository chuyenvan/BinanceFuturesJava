# UNIVERSE_A1_V11 — bộ lọc TradFi+INDEX cho v1.1 / shadow (CHUẨN BỊ, CHƯA DEPLOY)

Ngày 2026-10-30 (bản **fixA** sau audit Opus). Nhánh `v1.1/universe-a1`, worktree `~/claude_master/v11_univ`,
base `824a5789` (bản đầu — audit kết luận WRONG ở 4 điểm: lọc trong ingestor, lazy init nuốt lỗi, nguồn SDK dump,
thiếu point-in-time). Bản này sửa lại toàn bộ; **chưa deploy, chưa push**.

## 1. Sửa theo audit (file:line của bản này)

| # | Audit | Sửa |
|---|---|---|
| P0-1 | Lọc trong ingestor làm hỏng dữ liệu chung JVM collectData | **Bỏ hẳn** filter khỏi `websocket/TickerIngestor2AerospikeNew.java` (file trở lại byte-identical với `16de49a6`, `git diff 16de49a6 -- …` = 0 dòng) |
| P0-2 | Phải lọc ĐÚNG MỘT CHỖ trong trading JVM sau `tickerWindow.read` | `trading/DetectEntrySignal2TradeNormal.java:213-214` (filter ngay sau read :212) → `symbol2FinalTicker`, `calRateChangeAvg` (:281-283), `cascadeUniverse` (:365), `predictAllCandidates` funding/OI (:371), `getTopSymbol` (:385) cùng một tập. Seed lịch sử lọc cùng hàm (`initData`, `:1512`). Cùng hàm cho replay `ai_ml/features/export/gate/ExportGateDataset.java:176-177` (initEager :145, market rate A1 :154,195,201) + `AltEwIndex` + `calMarketData` |
| P0-3 | Fail-fast thật, không nằm trong try/catch nuốt lỗi | `UniverseA1Filter.initEager()` gọi ở `DetectEntrySignal2TradeNormal.start()` (:131, **ngoài** try/catch `initData` :1501-1541), `ExportGateDataset.replayToCsv` (dòng đầu). `initialized=true` chỉ sau parse OK; lỗi lưu `initError` và **ném lại mọi lần gọi** (kể cả `isExcluded`) |
| P1-1 | Nguồn phải là raw `/fapi/v1/exchangeInfo`, không dùng dump SDK | `UniverseA1Filter.load()`: bắt buộc `UNIVERSE_A1_EXCHANGE_INFO` (không fallback `EXCHANGE_INFO_PATH`), assert `nTradFi >= 200` (snapshot 10-27: **229 TF, 3 INDEX, 936 symbol**, sha256 log) |
| P1-2 | Point-in-time | `UniverseA1Filter.isExcluded(sym, tMs)`: TF/INDEX chỉ bị loại khi `tMs >= onboardDate`. MDTUSDT: crypto tới 2026-10-13, TF Medtronic onboard 2026-10-21 (`onboardDate=1792574400000`) ⇒ trước mốc đó vẫn là crypto. Dùng ở live (`filter(snap, now)`), replay (`filterMinutes` theo từng phút), `calMarketData(..., tsMs)`, `AltEwIndex.feed(ts,…)` |
| P1-3 | Symbol niêm yết sau snapshot | `isExcluded`: symbol **không có** trong snapshot mà `tMs > serverTime` ⇒ loại (fail-closed) + log 1 lần/symbol. JVM reload theo mtime (`maybeReload`, stat ≤1/phút, reload lỗi/<200 TF ⇒ fail-fast). Script `tools/refresh_exchange_info_raw.sh` (validate raw + cài file) — **KHÔNG cài cron**, nguồn phải từ 242 (ssh đọc) hoặc file owner cấp |
| P2 | Fixture SPXUSDT sai; import lệch | Fixture dùng record thật: `SPXUSDT = PERPETUAL/COIN` (SPX6900). Import `UniverseA1Filter` chuyển vào nhóm import chuẩn ở `ExportGateDataset` |

## 2. Định nghĩa (giữ nguyên văn HO2026_TRADFI_AUDIT §2)

TF ⇔ `contractType` chứa `TRADIFI`/`TRADFI` HOẶC `underlyingType` ∉ {COIN, INDEX, PREMARKET};
INDEX ⇔ `underlyingType=INDEX` HOẶC symbol trong `UNIVERSE_A1_INDEX_LIST` (mặc định `ALLUSDT,BTCDOMUSDT,DEFIUSDT`).
`underlyingType` thiếu ⇒ **không** TF (giống TradFiClassifier `verified=false`). PREMARKET (PREDICTUSDT) = crypto.

## 3. Cờ cấu hình

| key | mặc định | loại | ý nghĩa |
|---|---|---|---|
| `UNIVERSE_A1` | `0` (TẮT) | tham số giao dịch (profile/env) | `1` = bật lọc ở mọi tầng |
| `UNIVERSE_A1_EXCHANGE_INFO` | *(trống)* | hạ tầng | **bắt buộc** khi bật: raw exchangeInfo JSON (plain; script refresh ghi plain) |
| `UNIVERSE_A1_INDEX_LIST` | `ALLUSDT,BTCDOMUSDT,DEFIUSDT` | hạ tầng | INDEX bổ sung |

Bật: `UNIVERSE_A1=1` + `UNIVERSE_A1_EXCHANGE_INFO=/duong/dan/exchangeInfo_raw.json`. Thiếu file/hỏng/<200 TF ⇒
`IllegalStateException` tại `start()` (JVM không chạy nửa vời) và **mọi lần gọi sau**.

## 4. Vì sao đủ "live + sim/replay (parity)"

- Live: snapshot sau `tickerWindow.read` là nguồn DUY NHẤT; `LiveFeaturePipeline` lọc lại (cùng hàm, point-in-time)
  cho seed/catch-up/phút quyết định → history, `CoinRankManager` basket, funding-45, gate input, ALT_EW đều A1.
- Replay gate (`ExportGateDataset.replayToCsv`): lọc `today/tomorrow` theo từng phút; **khi cờ bật** còn tính lại
  market rate trên universe A1 bằng `MarketDataInlineGenerator` (cùng công thức `ExportMarketData2File`,
  died = `Constants.diedSymbol`) thay vì `time2Rate` (store A0). Phút đầu/cửa sổ lạnh generator trả null ⇒ fallback
  store (ghi rõ, xem §6).
- `calMarketData(..., tsMs)` và `AltEwIndex.feed(ts,…)` dùng `isExcluded(sym, ts)` — cùng luật point-in-time.
- **Đính chính claim cũ**: symbol TF/INDEX **VẪN NẰM trong ticker cache / Aerospike** (ingestor không lọc — đúng:
  dữ liệu dùng chung). Chúng bị loại ở trading JVM ngay sau khi đọc cache. Vì vậy `LiveTickerWindow.prevCount`
  (settle) vẫn đếm cả TF/INDEX — không đổi hành vi settle; mọi tập quyết định phía sau mới là A1.

## 5. Kiểm chứng (số thật, 2026-10-30)

- `mvn -o package`: **BUILD SUCCESS — 427 test / 0 fail / 0 error / 1 skip** (trước: 415; +12 test mới).
- `UniverseA1FilterTest` 13/13: cờ TẮT identity (cùng object), định nghĩa TF/INDEX, PREMARKET/thiếu trường không loại,
  **MDT trước/sau onboard**, symbol sau snapshot fail-closed, `filterMinutes` point-in-time, parity replay↔live từng phút
  (1440 phút), thiếu file/JSON hỏng **ném mọi lần gọi**, 199 TF bị từ chối / 200 TF hợp lệ, reload theo mtime,
  và **snapshot thật 10-27** (≥200 TF, INDEX=3, SPXUSDT=COIN, MDT point-in-time).
- `UniverseA1ParityTest` 3/3: tập S1/candidates/funding-OI/breadth sinh từ 1 map lọc không còn TF/INDEX;
  `rateDownAvg` = 0 khi bật (TF −10 % không kéo breadth) vs −0,05 khi tắt; ALT_EW chỉ còn crypto, MDT trước onboard vẫn tính.
- `AltEwIndexTest` 5/5 (test cũ giữ nguyên, không sửa).
- `tools/refresh_exchange_info_raw.sh --check <snapshot.gz>`: `symbols=936 tf=229 index=3 with_fields=936`, serverTime 10-27.

## 6. Rủi ro / điều kiện (owner quyết)

1. **Deploy file**: phải đặt raw exchangeInfo lên host live và trỏ `UNIVERSE_A1_EXCHANGE_INFO`. Oracle **không** gọi
   Binance; nguồn từ 242 hoặc owner. Script refresh chỉ được viết, **chưa cài crontab**; nếu cài, đặt giờ thấp điểm và
   giám sát `OK/FAIL` (mặc định từ chối snapshot cũ >72 h).
2. **Snapshot cũ**: symbol niêm yết sau serverTime bị loại fail-closed đến khi refresh; refresh quá 72 h ⇒ script báo FAIL.
3. **Reset cửa sổ parity**: mọi ngày trước khi bật là A0; đóng sổ cửa sổ hiện tại (từ 2026-10-21), mở cửa sổ mới từ nến
   quyết định đầu tiên có `UNIVERSE_A1=1`, ghi mốc vào prereg.
4. **ALT_EW live**: state 30 ngày đã tích luỹ theo A0 không tự sửa; phải dựng lại state A1 (replay Vision) trước khi bật,
   nếu không 30 ngày đầu là hỗn hợp. Cờ X14 có thể đổi (audit: noTFIDX 18 ngày vs 15).
5. **Replay market rate**: chỉ tính lại khi cờ bật; phút thiếu cửa sổ (null) fallback `time2Rate` (A0) — chấp nhận cho
   warmup, cần kiểm khi so parity sát biên ngày.
6. **Vị thế đang mở** ở symbol TF/INDEX khi bật: DCA bỏ qua symbol không còn ticker (log `[UNIVERSE-A1] DCA bo qua`),
   không NPE; owner nên đóng/không mở mới các symbol này trước khi bật.
7. Sim HO2026 (repo/kernel khác) vẫn phải dựng universe A1 ở tầng dữ liệu như `PREREG_HO2026_NOTF`; lớp này chỉ bảo đảm
   v1.1 live/replay.
8. Chưa deploy, không sửa 242, không push. Build dùng `PrivateConfig` STUB (không in nội dung).
