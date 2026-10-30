# ROUND4D — universe A1 (bỏ TradFi + INDEX ở mọi tầng phía tín hiệu) cho dry-run 11-18

Branch `v1.2/c3-live`, trên `6afb59e4` (R4c). Ràng buộc giữ nguyên: không push, không `git config`, không gọi Binance từ
Oracle, không ssh/chạy gì trên 242, không chạy script canary/deploy thật, không đụng `~/claude_master/canary_*`, không in/sửa
`PrivateConfig`. A1AdversarialTest / A1G3Test / A1R4Test / A1R4bTest **byte-identical** (không sửa).

## 1. Vì sao

R7 (R4) chỉ chặn c3_live **mua** TradFi/INDEX. Phía tín hiệu vẫn như v1.1: TF/INDEX nằm trong S1/ứng viên, ALT_EW/X14,
breadth `calMarketData`, input gate, funding/OI. Backtest tin cậy (GOLIVE_QUARTERLY_2026_A1 / HO2026_NOTF A1) bỏ chúng ở **mọi**
tầng ⇒ live ≠ backtest. R4d: cờ `UNIVERSE_A1` (mặc định 0 trong code, script dry đặt 1) lọc universe A1 ở mọi tầng, live và
replay dùng **cùng một hàm**.

## 2. Thiết kế

| Thành phần | Nội dung |
|---|---|
| Bộ phân loại **duy nhất** `tradecore/selector/UniverseA1Classifier` | TRADFI ⇔ `contractType` chứa `TRADIFI` (hoặc `TRADFI`) HOẶC `underlyingType` ∈ {EQUITY, HK_EQUITY, KR_EQUITY, CN_EQUITY, COMMODITY, FX}; INDEX ⇔ `underlyingType=INDEX`; thiếu `underlyingType` = UNCLASSIFIED (không loại ở phía tín hiệu; R7 strict vẫn không mua); còn lại CRYPTO. Kiểm nguồn chung (`sourceProblem`: có contractType, có underlyingType, ≥ **50** hợp đồng TRADIFI) + cảnh báo giảm > 30 % (`tradFiDropped`) — đúng ngưỡng R4b |
| R7 c3_live dùng **cùng** bộ phân loại | `UNIVERSE_A1=1` ⇒ `SymbolUniverseLive.Config.strictCoin().withClassifier(TradFiClassifier.universeA1())` (ủy quyền `UniverseA1Classifier`); `MIN_TRADFI_IN_SOURCE`/`TRADFI_DROP_WARN`/`sourceProblem`/`tradfiCount` của R7 trỏ vào cùng hằng/hàm (giá trị không đổi: 50 / 0,30) |
| `UniverseA1Filter` (point-in-time) | TF/INDEX bị loại tại `t` khi `t ≥ onboardDate` (MDTUSDT crypto trước 2026-10-21). Symbol có trong snapshot là crypto ⇒ **không bao giờ** bị loại. Symbol **không** có trong snapshot xuất hiện sau `serverTime` ⇒ loại (fail-closed, giống R7: không có trong snapshot ⇒ không mua). Snapshot bất biến 1 khối (`Snap`), đổi nguyên khối khi reload |
| Điểm lọc live | `DetectEntrySignal2TradeNormal`: ngay sau `tickerWindow.read` ⇒ `symbol2FinalTicker`, market level/breadth, cascade, `predictAllCandidates` (funding/OI), `getTopSymbol` (S1), DCA; seed `initData` (`filterMinutes`); `LiveFeaturePipeline.filt(snap, minute)` ở mọi đường (seed, seed giữ lại C11, catch-up, phút quyết định) + `md.update(snap, ts)`; `calMarketData(..., ts)`; `AltEwIndex.feed` (point-in-time) ⇒ `TsMktExt` ALT_EW/X14 |
| Replay | `ExportGateDataset.replayToCsv`: `initEager` đầu hàm, `filterMinutes(today/tomorrow)`, rate tính lại trên A1 khi bật (giữ từ bản nháp) |
| Fail-fast | `initEager()` ở `DetectEntrySignal2TradeNormal.start()` (trước `initData`, ngoài try/catch nuốt lỗi; `main` không bắt ⇒ JVM dừng) và đầu `replayToCsv`. Lỗi init (thiếu file, JSON hỏng, thiếu `serverTime`, < 50 TF) được giữ và **ném lại ở MỌI lần gọi** |
| c3_live khi A1 bật | `C3LiveHook.marketIndexOrNull()` / `tradFiFeatureFilterOrNull()` ⇒ null; `MarketIndexFilter` không đặt (A1 là định nghĩa, không hẹp thêm theo `marketIndexMembers`); `TsMktExt` dùng file ngày riêng `run/ts_ext_daily.csv.a1` (cửa sổ 31 ngày tính lại từ store trên universe A1, không trộn tổng ngày A0 của c3_shadow); dry: R7 và bộ lọc phải đọc **cùng** file (`checkA1SameSource`, khác ⇒ ném ⇒ MANAGE-ONLY ⇒ CHK FAIL) |
| Cờ TẮT (mặc định) | `filter`/`filterMinutes` trả **cùng object**; `isExcluded` = false; AltEw/calMarketData/pipeline đi đúng đường cũ; DCA-null chỉ đổi khi bật; `TsMktExt` file cũ; R7 bộ phân loại mặc định; C3LiveHook như cũ ⇒ hành vi = `6afb59e4` (parity shadow v1.1 tới 11-18) |

## 3. Nguồn exchangeInfo trên 242 (chọn: **dùng lại file R7**)

`UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json` = đúng file R7 (`LIVE_C3_EXCHANGEINFO_FILE`) mà bước chuẩn bị của
`deploy_v12_dry_r4.sh` tải **trên 242** (`curl` chạy trong phiên ssh tới 242 — đã có từ R4; Oracle không gọi Binance), kiểm rồi
mới `mv` vào chỗ. Lý do chọn: không thêm đường HTTP mới trong JVM giao dịch (IP dùng chung với LEGACY, RateGuard), R7 và phía
tín hiệu **cùng một snapshot** ⇒ cùng universe theo cấu trúc (JVM kiểm cùng đường dẫn canonical). Phương án "refresh trong JVM"
bị loại: thêm I/O mạng + có thể lệch giữa 2 nguồn. Kiểm 4 lớp: (1) PRE (trước YES, chỉ đọc ra stdout trên 242): nguồn có
> 100 symbol, ≥ 50 TRADIFI, `onboardDate` mọi symbol, `underlyingType`, `serverTime`; (2) bước chuẩn bị: như (1) trên file tải
về; (3) **ngay trước restart** (bot cũ còn chạy): file còn đó + hợp lệ + `env.sh` trỏ cùng file cho R7 và A1 — FAIL ⇒ khôi
phục env, dừng, không đụng bot cũ; (4) CHK sau start: dòng `[UNIVERSE-A1] BAT … TradFi=N` với N ≥ 50 (thiếu ⇒ WAIT ⇒
rollback; N < 50 ⇒ FAIL ⇒ rollback), không có `[UNIVERSE-A1] reload … LOI`. Snapshot cố định suốt dry-run (không có cron
refresh trên 242): symbol niêm yết sau deploy bị loại ở cả R7 lẫn phía tín hiệu (lệch nhỏ so với backtest với listing mới).

## 4. Sai lệch so với bản nháp OpenClaw `3d26f36a` (chưa audit) và lý do

| # | Bản nháp | R4d | Lý do |
|---|---|---|---|
| D1 **P0** | `isExcluded`: không có trong map `onboard` (chỉ chứa TF/INDEX) và `t > serverTime` ⇒ loại; tập `known` không bao giờ được dùng | crypto có trong snapshot ⇒ không bao giờ loại; chỉ symbol **ngoài** snapshot mới fail-closed | Live luôn có `t > serverTime` ⇒ bản nháp loại **mọi** crypto (kể cả BTC) ⇒ vòng entry dừng "thiếu BTC". Test `flagOn_…keepsCrypto`, `realSnapshot_1027` |
| D2 | TF = luật bù `underlyingType ∉ {COIN, INDEX, PREMARKET}` + danh sách INDEX tường minh (`UNIVERSE_A1_INDEX_LIST`) | định nghĩa MASTER (danh sách underlyingType tường minh), INDEX = `underlyingType=INDEX`; bỏ key `UNIVERSE_A1_INDEX_LIST` | 1 bộ phân loại chung với R7. Snapshot thật 10-27: 2 luật cho **cùng** tập (229 TF, 3 INDEX = ALL/BTCDOM/DEFI, 0 khác biệt) — test. underlyingType lạ (không thuộc danh sách, không COIN/INDEX/PREMARKET) ⇒ CRYPTO theo định nghĩa MASTER (bản nháp: TF) |
| D3 | ngưỡng ≥ 200 TF, không cảnh báo giảm | ≥ 50 TRADIFI + cảnh báo giảm > 30 % (dùng chung R7) | yêu cầu R4d / R4b |
| D4 | thiếu `serverTime` ⇒ dùng mtime/now | thiếu `serverTime` ⇒ ném (fail-fast) | file không phải raw `/fapi/v1/exchangeInfo`; mốc fail-closed phải là thời điểm snapshot thật |
| D5 | reload lỗi ⇒ `initError` ⇒ **mọi** lần gọi sau ném, giữa phiên | reload lỗi ⇒ giữ snapshot cũ + ERROR (1 lần/mtime), thử lại khi mtime đổi; lỗi **init** vẫn ném mọi lần | không làm chết vòng giao dịch vì 1 file thay hỏng; giống R7 "giữ cũ" |
| D6 | nhiều trường `volatile` gán rời | 1 `Snap` bất biến | không đọc trạng thái lai khi reload |
| D7 | `norm()` thêm "USDT" vào symbol không kết thúc bằng USDT (`SPCXUSD1` ⇒ `SPCXUSD1USDT`) | so khớp đúng tên symbol | tên sai trong tập loại |
| D8 | DCA bỏ qua ticker null luôn | chỉ khi A1 bật | cờ tắt phải y nguyên |
| D9 | (v1.1, không có) | v1.2: khi A1 bật, tắt các lọc c3_live riêng (`marketIndexOrNull`, `dropTradFi`, `MarketIndexFilter`) | các lọc này hẹp hơn A1 (chỉ `tradable`: bỏ PREMARKET/non-ASCII/EXCLUDE…) và không point-in-time (MDT trước 10-21 bị bỏ khỏi seed) ⇒ lệch backtest |
| D10 | rủi ro #4 (state ALT_EW 30 ngày A0) chỉ ghi chú | `TsMktExt` dùng `run/ts_ext_daily.csv.a1` khi A1 bật; PRE từ chối nếu file `.a1` cũ còn; rollback đổi tên | cửa sổ X14 tính lại hoàn toàn trên A1 |
| D11 | (không có) | R7 dùng `TradFiClassifier.universeA1()`; dry: kiểm cùng file | yêu cầu "1 classifier" + cùng snapshot |
| D12 | `LiveFeaturePipeline` v1.1 | gộp vào `filt(snap, minute)` của v1.2 (có `snapFilter`, seed giữ lại C11) | mọi đường nuôi đều lọc tại đúng phút |
| D13 | `tools/refresh_exchange_info_raw.sh` | **không port** | không cần (nguồn = file R7 tải trên 242); script chứa bộ phân loại thứ hai (Python, luật bù) và ngưỡng 200 |
| D14 | test + fixture `universe_a1_exchange_info.json` | viết lại (`UniverseA1FilterTest`, `UniverseA1R7SharedClassifierTest`, `C3LiveRuntimeA1SourceTest`), fixture sinh trong test | bộ test bản nháp không phát hiện D1; API test đổi (bỏ danh sách INDEX, ngưỡng 50, `serverTime` bắt buộc) |

Giữ từ bản nháp: `ExportGateDataset` (initEager, `filterMinutes`, rate A1), overload `calMarketData(..., ts)` /
`MarketDataInlineGenerator.update(snap, ts)`, `AltEwIndex` point-in-time, `Cfg` (`UNIVERSE_A1` = tham số giao dịch,
`UNIVERSE_A1_EXCHANGE_INFO` = hạ tầng), không lọc trong ingestor. Hạn chế còn lại (không đổi): replay dùng `died =
Constants.diedSymbol` cho rate A1 (live: `LIVE_MD_DIED_SYMBOLS`); phút generator trả null ở warmup replay rơi về store A0.

## 5. Test

| Yêu cầu | Test |
|---|---|
| cờ 1: không TF/INDEX ở S1/ứng viên, breadth, ALT_EW, gate, funding/OI; live == replay | `UniverseA1FilterTest.liveReplayGate_identicalSets_noTfIndex` (239 phút qua mốc MDT: tập điểm lọc live == `filterMinutes` == tập pipeline nuôi/extract, `md.update(snap, ts)`), `breadthAndAltEw_equalCryptoOnly` (calMarketData + ALT_EW bật trên map thô == tắt trên map A1; tắt trên map thô khác), `liveSource_singleFilterPointAfterTickerRead` (điểm lọc ngay sau `tickerWindow.read`, init trước `initData`, seed lọc) |
| MDT trước/sau onboardDate | `flagOn_…`, `realSnapshot_1027`, `liveReplayGate_…` |
| lỗi init ném lại mọi lần | `initFailure_rethrownOnEveryCall` (thiếu file / thiếu serverTime / 49 TF / JSON hỏng; 3 kiểu gọi sau cùng ném **cùng** exception; 50 TF hợp lệ) |
| reload | `reload_newValidAccepted_newBrokenKeepsOld` |
| 1 classifier R7 == tín hiệu | `UniverseA1R7SharedClassifierTest` (snapshot thật qua parser DryGateway: verdict R7 == `UniverseA1Classifier` mọi symbol, TF/INDEX không mua được, mua được ⇒ CRYPTO; 229/3), `classifier_definition` |
| cờ 0 y nguyên | `flagOff_identityEverywhere` (cùng object ở filter/filterMinutes/pipeline), `defaultClassifierUnchanged`; toàn bộ test cũ không sửa vẫn PASS |
| R7/A1 cùng file | `C3LiveRuntimeA1SourceTest` |

- `mvn -o package` (nice): **846 test, 0 fail, 0 error, 1 skip** (R4c 834 + `UniverseA1FilterTest` 9 + `UniverseA1R7SharedClassifierTest` 2 + `C3LiveRuntimeA1SourceTest` 1).
- fake242: **199/199** (R4c 187 + 12: §22 thêm `run/ts_ext_daily.csv.a1` vào kiểm PRE, §24 mới 11 kiểm: ENV_ADD, PRE nguồn thiếu `onboardDate`/`serverTime`, bước chuẩn bị nhận file thiếu `serverTime`, file A1 mất ngay trước restart ⇒ dừng trước khi đụng bot cũ, XONG có dòng init `TradFi=60 INDEX=3`, rollback, thiếu dòng init ⇒ rollback, TF < 50 ⇒ rollback), chạy trên cây làm việc = commit `c95ca8f9`.
- A1 md5 không đổi (`d300ebb0…`, `3faefd28…`; `A1R4Test`, `A1R4bTest` không sửa). Code canary: 0 file đổi. `deploy_v12_dry.sh` + pin cũ giữ.
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4d` md5 `48260625c1f96627922d89aff3b9ef58` (pin `NJ`/`NJ_MD5`, kiểm bằng `md5sum`).
- `rollback_v12.sh` md5 `ae7a5a5f3704688677d5c0d28a358b80` (thêm đổi tên `run/ts_ext_daily.csv.a1`; pin `RB_MD5`).

## 6. Lệnh owner (11-18, trên ORACLE)

```
bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh
```

Từ chối trước 2026-11-18 07:54 +07 (trừ `FORCE=1` khi MASTER báo). Chạy thử: `DRY=1 bash …/deploy_v12_dry_r4.sh` (chỉ đọc;
in thêm `export UNIVERSE_A1=1` + `UNIVERSE_A1_EXCHANGE_INFO=run/c3live_exchangeInfo.json` và dòng `OK exchangeInfo_nguon …`).
Gõ `YES` 1 lần ⇒ job nền (đóng terminal không sao), Telegram kết quả. rc: 0 XONG · 1 DỪNG/đã rollback · 2 ROLLBACK LỖI (PAUSE
còn — chạy đúng lệnh in ra) · 3 XONG nhưng PAUSE còn. Rollback tay: `FORCE_TIME=1 bash ~/claude_master/v12/c3live/ops/c3live/rollback_v12.sh <TS>`.
**Lưu ý vận hành**: bật A1 = mở cửa sổ parity mới (dry-run so với backtest A1 tính từ nến quyết định đầu tiên có `UNIVERSE_A1=1`).
