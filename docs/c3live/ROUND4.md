# ROUND4 — c3_live PRODUCTION trên TÀI KHOẢN CHÍNH (spec `docs/plan/ROUND4_MAIN_ACCOUNT.md`, MASTER 2026-10-30)

Branch `v1.2/c3-live`, trên `b4aa33c6` (3k). Spec commit riêng TRƯỚC code: `8398d1d6`. Code `bd34845f`, test `f956e28e`, docs `a1bb70e0`, fix MERGED bat dong bo (commit nay).
Chỉ code + test + doc; **không** gọi Binance, **không** ssh 242, **không** chạy script canary/deploy, **không** đụng
`~/claude_master/canary_*`, **không** push, **không** `git config`, **không** in/sửa `PrivateConfig`.

## 1. Yêu cầu → sửa → test

| # | yêu cầu | sửa | test |
|---|---|---|---|
| R1 | phạm vi cid/sổ c3; đọc toàn tài khoản qua view lọc; không bao giờ cancel/close/modify ngoài phạm vi; dualSide/multiAssets chỉ ĐỌC, hedge ⇒ từ chối; leverage/marginType chỉ symbol sạch | `scope/C3ScopedGateway` bọc gateway thô (live + dry): `positions()/account()` = `C3Scope.view` (ẩn symbol LEGACY; MERGED ⇒ phần c3), `openOrders/openStops` = chỉ cid c3; ghi: cid bắt buộc `c3-`/`c3x-`/`c3s-`, `setDualSidePosition` luôn từ chối, `setLeverage/setMarginType` chỉ khi sàn = qty c3 và 0 lệnh/algo không-c3. Đọc thô chỉ `positionsAll/openOrdersAll/openStopsAll/accountRaw` (CHỈ ĐỌC). `AccountModeGuard.globalPolicy(false,false)` | `scopedGatewayRefusesOutOfScopeWrites`, `h_…` (view rỗng với 44 LEGACY) |
| R2 | LEGACY-busy (mỗi chu kỳ + trước MỌI lệnh mở, trong supplier); MERGED: không đóng, stop closePosition ⇒ qty reduceOnly = qty c3 (giá cũ), chặn mở, Telegram KHẨN, journal; gỡ khi sàn = ledger | `C3LegacyRefresher` (60 s, ~85 weight) → `C3Scope.refreshLegacy`; entry `legacy = LegacySymbols ∨ scope.entryBlocked` (ảnh chụp > 180 s ⇒ chặn hết, fail-closed); `C3ScopedGateway.preOpen` chạy lại trong vòng thử (đọc positionRisk thô + openOrders/openAlgo của symbol). `C3MergedGuard`: stream (lệnh không-c3 KHỚP trên symbol c3) ⇒ ngay; REST (sàn > cận trên c3 / âm) 2 lần cách ≥ 3 s; xử lý: `TrailingStopManager.replaceStopAsQty` (đặt qty trước, huỷ closePosition sau — không khoảng trống), không được ⇒ huỷ closePosition trong lane khẩn cấp; `qtyModeFor(scope::isMerged)` giữ mọi lần dời stop ở qty = phần c3; journal `OrderAuditLog status=MERGED/MERGED_STOP_QTY/MERGED_STOP_CANCEL/MERGED_RELEASED`; persist `run/c3live_merged.txt`; khởi động: sàn > sổ c3 ⇒ MERGED NGAY trước "sàn thắng" của Reconciler | `b_…`, `b2_…`, `b3_…` (co MERGED dong bo, hanh dong tren thread rieng), `c_…`, `c4_…` |
| R3 | LEGACY không còn là chặn (A) | Lớp c3 không thấy LEGACY: view + `C3StreamScope` (bỏ ORDER/ALGO/TRADE_LITE không-c3, mảng `P` chỉ symbol c3 giữ, bỏ mảng `B`). (A) chỉ còn: lỗi đọc/đối soát của c3, startup chưa xong, (B) > 10′, kill-switch. Symbol vừa chốt có hoạt động LEGACY sau đó ⇒ không theo dõi (B) nữa | `a_…` (bot LEGACY ≥ 50 lệnh, 0 chặn (A)), `b2_…` (LEGACY còn lại sau khi c3 đóng ⇒ không (A) sau 15′) |
| R4 | vốn/equity c3 riêng; size từ equity c3; C6/A40 + đỉnh riêng; đối chiếu giờ = qty; tmb chỉ cảnh báo ký quỹ | `risk/C3MainEquity`: equity = C3_CAPITAL + (rp − phí) ledger c3 từ mốc + cụm mở + funding c3 (income FUNDING_FEE theo symbol × khoảng giữ; MERGED ⇒ theo tỉ lệ qty) + UPL c3; `capital() = min(C3_CAPITAL, equity c3, availableBalance + margin c3)`; cảnh báo `availableBalance < 2 × margin c3`. Runtime: `attachEquitySource(c3)`, `onBook(..., equity c3)`, nhãn đỉnh `<adapter>_c3eq`. `Reconciler.setQtyReconcile(true)` ⇒ `hourlyQty` | `d_…`, `e_…`, `fundingCountsOnlyC3SymbolsWhileHeld`, `a_…` (hourly qty) |
| R5 | rate canary 3i cho runtime | `rate/ProductionRatePolicy` = `RateGuard.CanaryPolicy` từ hằng `CanaryLimits` (IP 1800 env `LIVE_C3_IP_WEIGHT_CAP` kẹp ≤ 1920, riêng 600, burst [27,40]→41, đọc chờ ≤ 2×61 s); `GatewayFactory` live dùng nó; `C3ScopedGateway.write` ngủ burst trước kiểm, guard từ chối ⇒ chờ ≤ 61 s, KIỂM LẠI, thử 1 lần; Urgent không chờ quá hạn; lane khẩn cấp không bị lớp này chặn | `C3ProdRateTest` (5) |
| R6 | stop bảo vệ/trailing trong Urgent ngay khi xác nhận; stop bị sàn kết thúc ⇒ đặt lại ≤ 61 s, quá hạn ⇒ đóng qty c3 lane khẩn cấp + Telegram | `exit/C3StopProtector` (ops 5 s + kick ngay qua thread `C3LIVE-PROTECT` khi fill MUA xác nhận / ALGO_UPDATE CANCELED/EXPIRED); `TrailingStopManager.ensureStop(sym, null)` đặt lại theo priceSL đã persist; `exitTick` chạy trong `RateGuard.urgent(now+61 s)` | `r6_…` ×2, `protectiveStop…` ×2 |
| R7 | universe COIN; loại TradFi/INDEX/chưa phân loại; nguồn thô đủ trường, ≥ 200 TF, làm mới ≤ 15′ | `SymbolUniverseLive.Config.strictCoin()` (CHỈ production): `UNCLASSIFIED`, `NOT_COIN`; `sourceProblem` (thiếu contractType/underlyingType hoặc < 200 TRADIFI ⇒ từ chối snapshot + Telegram; snapshot cũ hết hạn 60′ ⇒ STALE); REFRESH 15′ giữ nguyên. Canary (`SymbolPicker`) giữ cấu hình cũ | `C3UniverseStrictTest` (2) |
| R8 | startup: đối soát trong phạm vi; 44 LEGACY = foreign đã biết; xong ⇒ mở được | lượt đầu: `resolveUnresolved` → `legacyRefresher.refreshNow()` (MERGED ngay nếu sàn > sổ) → `reconciler.startup()`; đọc lỗi ⇒ chưa reconcile, giữ `BLOCK_STARTUP`, thử lại 30 s | `h_…` (cả restart) |
| R9 | dry trên tk chính cùng view/phạm vi/vốn ảo; 0 lệnh thật | runtime bọc `DryGateway` bằng CÙNG `C3ScopedGateway` + `C3StreamScope` + `C3MainEquity` (tag `dry`) | `C3DryMainAccountTest` |
| R10 | giữ canary 3e–3k; A1 byte-identical | `git diff b4aa33c6 -- src/main/java/.../canary` rỗng; `A1AdversarialTest` md5 `d300ebb0…`, `A1G3Test` md5 `3faefd28…` (= 3k); thay đổi lớp dùng chung đều mặc định TẮT (`qtyModeFor` rỗng, `strictCoin` false, `qtyReconcile` false, `income` default) | full suite |

## 2. Call site đọc toàn tài khoản / ghi sàn (production, HEAD `f956e28e`)

Mọi lớp dưới đây nhận `gw` = `C3ScopedGateway` (runtime `C3LiveRuntime:233-236`, `this.gw = sgw`); gateway thô chỉ còn trong `sgw`.

| file:line | gọi | trước R4 (tài khoản con) | sau R4 (tài khoản chính) | guard |
|---|---|---|---|---|
| `recon/Reconciler.java:321` (startup), `:811` (quét giờ) | `openStops(null)` | mọi algo của tài khoản; `c3s-` mồ côi huỷ, khác ⇒ WARN | view: CHỈ `c3s-` (LEGACY không bao giờ thấy) | `C3Scope.c3Only` |
| `recon/Reconciler.java:853` (`positionsBySymbol`), `:882` (ghostClear) | `positions()` | vị thế lạ ⇒ UNKNOWN (A) toàn hệ | view: chỉ symbol liên quan c3; LEGACY ẩn ⇒ không (A); MERGED ⇒ phần c3 (không "sàn thắng" bằng vị thế lẫn) | `C3Scope.view` |
| `recon/Reconciler.java:551, 886` | `account()` | positions toàn tài khoản (đối chứng phẳng) | positions = view | `C3Scope.view` |
| `recon/Reconciler.java:647` (hourly) | `account()` tmb | lệch equity sổ vs tmb > 1 % ⇒ chặn | KHÔNG gọi khi `qtyReconcile`: `hourlyQty` so qty c3 (confirmed − exit) vs view | `setQtyReconcile(true)` |
| `recon/FlatConfirm.java:106, 128, 160` | `account()`, `openStops(sym)`, `openOrders(sym)` | toàn bộ lệnh của symbol | view + chỉ cid c3 | view / `c3Only` |
| `recon/OwnStopGuard.java:72, 95, 104` | `openStops(sym)`, `positions()`, `account()` | phẳng theo vị thế symbol | phẳng theo PHẦN c3 (MERGED đã đóng ⇒ 0) | view |
| `recon/OwnStopGuard.java:133` | `cancelStop` | `c3s-` | `c3s-` bắt buộc ở gateway | `requireCid` |
| `exec/C3LiveOrderExecutor.java:163` | `newMarketOrder BUY` | gửi | kiểm LẠI trong supplier: không MERGED, sàn ≤ qty c3, 0 lệnh/algo không-c3; cid `c3-` | `preOpen` + burst + retry 1 lần |
| `exec/C3LiveOrderExecutor.java:380, 389` | `positions()` (mark giá TẠM), `tickers24h` | — | view (mark của symbol c3) | view |
| `exec/C3LiveOrderExecutor.java:216, 338`, `exec/FillPriceResolver.java:171, 194` | `queryOrder`, `userTrades` | theo cid/orderId c3 | không đổi (theo cid/orderId) | — |
| `risk/C3LiveFlattener.java:171` | `newMarketOrder SELL RO` | qty ≤ phần c3 | + gateway: qty ≤ qty c3 theo sổ; cid `c3x-`; lane khẩn cấp không bị chặn | `preClose` |
| `risk/C3LiveFlattener.java:251, 278` | `openStops(sym)`, `positions()` | — | view | view |
| `exit/TrailingStopManager.java:322, 324` | `newStopMarket` qty / closePosition | closePosition mặc định | closePosition: cấm khi MERGED hoặc sàn > cận trên c3 (⇒ nghi MERGED); qty: reduceOnly, ≤ qty c3 (MERGED ⇒ qty = phần c3 mở) | `preStopClosePosition`, `preStopQty`, `qtyModeFor` |
| `exit/TrailingStopManager.java:439` | `openStops(sym)` | — | chỉ `c3s-` | `c3Only` |
| `fill/FillAccounting.java:348` | `openStops(sym)` | mọi stop symbol | chỉ `c3s-` | `c3Only` |
| `guard/AccountModeGuard.java:163, 170` | `multiAssetsMargin`, `dualSidePosition` | multiAssets bắt buộc; hedge ⇒ đặt lại | `globalPolicy(false,false)`: không đọc multiAssets, dualSide CHỈ ĐỌC, hedge ⇒ TỪ CHỐI | gateway cũng từ chối `setDualSidePosition` |
| `guard/AccountModeGuard.java:89, 211, 223` | `symbolConfigs`, `symbolConfig` | — | đọc (không đổi) | — |
| `guard/AccountModeGuard.java:215, 220` | `setMarginType`, `setLeverage` | đặt khi sai | chỉ khi sàn = qty c3 và 0 lệnh/algo không-c3 | `preConfig` |
| `risk/C3MainEquity.java:127` | `positions()` | (C3LiveEquity: tmb) | view: mark của symbol c3 cho UPL c3 | view |
| `risk/C3MainEquity.java:186` | `accountRaw()` | — | CHỈ availableBalance (kiểm ký quỹ + trần vốn) | chỉ đọc |
| `risk/C3MainEquity.java:212` | `income(FUNDING_FEE)` (MỚI, w30, 10′) | funding = mảng `B` stream (cả tài khoản) | income theo symbol, chỉ symbol/khoảng c3 giữ | `heldRatio` |
| `scope/C3LegacyRefresher.java:58-60` | `positionsAll/openOrdersAll/openStopsAll` (MỚI, 60 s) | — | CHỈ ĐỌC ⇒ LEGACY-busy + MERGED | read-only |
| `scope/C3MergedGuard.java:88` | `positionsAll` | — | CHỈ ĐỌC (khi có nghi vấn / MERGED) | read-only |
| `scope/C3MergedGuard.java:218` | `cancelStop` | — | huỷ `c3s-` closePosition của CHÍNH c3 trên symbol MERGED (lane khẩn cấp) | `requireCid` |
| `fill/UserStream` (live) / `DryGateway.setEventSink` (dry) | user-data stream | mọi sự kiện vào `FillAccounting` | qua `C3StreamScope.filter` (`C3LiveRuntime.scopedConnector`) | stream scope |
| `C3LiveCanary`, `canary/*` | — | — | KHÔNG đổi (R10) | `CanaryGateway` 3f–3k |

Không có `cancelAll` nào trong `c3live/` (grep 0).

## 3. Test

- `mvn -o package -DskipTests=false` (nice, MemAvailable ≥ 15 GB): **Tests run: 814, Failures: 0, Errors: 0, Skipped: 1 — BUILD SUCCESS**
  (3k: 793; +21: `C3MainAccountE2ETest` 10, `C3MainEquityKillSwitchTest` 3, `C3ProdRateTest` 5, `C3UniverseStrictTest` 2,
  `C3DryMainAccountTest` 1). Không sửa/nới test cũ nào; A1 byte-identical.
- Gian thử `MainAccountRig`: mock tài khoản chính với 44 vị thế LEGACY (C30..C73) + 1 lệnh LIMIT + 1 algo LEGACY, bot LEGACY
  mở/đóng ngẫu nhiên (seed 42) trên symbol LEGACY + 6 symbol tự do, thành phần c3 THẬT (scope, stream, merged, protector,
  equity c3, Reconciler qty, KillSwitchEngine ACT).
- `ops/c3live/test/test_fake242.sh` trên `git archive HEAD` (`/tmp/arc_r4`): xem §3.1.

### 3.1 fake242
`git archive HEAD` (f956e28e) → `/tmp/arc_r4`, chạy `bash ops/c3live/test/test_fake242.sh /tmp/fake_r4` (242 giả, không ssh, không Binance) 11:47–12:01: **TEST PASS 153/153**, 0 FAIL (= 151 kiểm 3k + 2 kiểm phụ thuộc khung giờ chạy được lúc này; `ops/` không đổi so với 3k nên số kiểm giữ nguyên).

## 4. Jar / pin

- Production: `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4`, 100 466 544 bytes, md5 **`345613dc964cefe3fb6b5e47342b199c`** (build tu HEAD sau fix MERGED bat dong bo)
  (3k: 8 922 entry → r4: 8 935; +13 = `scope/*` 7 class + thư mục, `C3MainEquity`, `C3StopProtector`, `ProductionRatePolicy`,
  `IncomeRecord`, `C3LiveRuntime$2`; không bỏ entry nào).
- Canary: code canary KHÔNG đổi ⇒ **không bump** `CANARY_JAR`/`CANARY_JAR_MD5` (vẫn `…_3k` / `fea29aea…`, kiểm md5sum thật = `fea29aea127886a63f60d23b3b9846dc`).
- `ops/c3live/deploy_v12_dry.sh`: KHÔNG đổi. Để chạy dry R4 từ 11-18 cần cập nhật (owner/MASTER duyệt): pin jar → `…_v12_r4` + md5
  `345613dc…`; env `C3_CAPITAL` (mặc định = `LIVE_C3_PILOT_CAPITAL` = 10 000), tuỳ chọn `LIVE_C3_IP_WEIGHT_CAP`,
  `LIVE_C3_MERGED_FILE`, `LIVE_C3_EQUITY_FILE`; file `LIVE_C3_EXCHANGEINFO_FILE` phải là dump exchangeInfo THÔ đầy đủ (≥ 200
  TRADIFI) — nếu không, universe chặt từ chối ⇒ dry không mua gì.

## 5. MASTER cần duyệt

1. **Không refactor `CanaryGateway`** (giữ canary jar 3k byte-stable, R10): production dùng lớp riêng `C3ScopedGateway`, tái sử dụng
   `RateGuard.CanaryPolicy/Urgent/Lane`, hằng `CanaryLimits`, `C3LiveCids`; vòng "burst → kiểm → gửi → chờ ≤ 61 s → kiểm lại → thử 1
   lần" (~40 dòng) là bản song song của `CanaryGateway.call` — gộp sau go-live.
2. **Vốn size** = `min(C3_CAPITAL, equity c3, availableBalance + margin c3)` — không tự phình theo lãi (giữ Q1b). "≤ availableBalance"
   hiểu là trần theo ký quỹ còn trống + phần c3 đang dùng.
3. **Cảnh báo ký quỹ**: `availableBalance < 2 × margin c3 đang dùng` (sổ c3) ⇒ Telegram (thưa 1 h), KHÔNG chặn.
4. **MERGED + stop**: thay closePosition bằng stop qty TRƯỚC rồi mới huỷ (không khoảng trống); không đặt được ⇒ vẫn huỷ closePosition
   (c3 tạm không stop) + KHẨN. MERGED mất stop > 61 s ⇒ **không** đóng khẩn cấp (R2 thắng R6), chỉ KHẨN + thử tiếp.
5. **Điều kiện MERGED** = sàn > cận trên c3 (confirmed − exit + leg chưa rõ) hoặc âm, hoặc lệnh không-c3 KHỚP trên symbol c3. Sàn
   < sổ c3 (khác 0) ⇒ không MERGED mà do `hourlyQty` (> 1 % ⇒ chặn (A) — lỗi đối soát của chính c3).
6. **R6 đóng khẩn cấp** chỉ khi stop bị SÀN kết thúc (ALGO_UPDATE CANCELED/EXPIRED) và không đặt lại được trong 61 s. Lần arm đầu /
   Reconciler bỏ stop vắng / restart: đặt trong Urgent + Telegram sau 61 s, không ép đóng. Thiết kế c3 KHÔNG có stop trước arm (DCA
   reset arm) ⇒ "ngay khi xác nhận qty" = kick kiểm bảo vệ ngay (không đặt stop cho cụm chưa arm).
7. **multiAssets** không đọc/không bắt buộc trên tài khoản chính (`globalPolicy(false,false)`, như canary 3f); trước đây sub-account
   bắt buộc `true`.
8. **Đỉnh kill-switch** đổi nhãn `<adapter>_c3eq` ⇒ đỉnh tmb cũ bị bỏ qua, học lại từ equity c3 đầu tiên; latch cũ khác nhãn (nếu có)
   vẫn GIỮ (không tự gỡ) như cơ chế 2e.
9. **LEGACY-busy** làm mới 60 s (~85 weight/phút trên trần riêng 600); ảnh chụp > 180 s ⇒ chặn MỌI lệnh mở (cả DCA).
10. **Equity c3 bắt đầu** từ file `run/c3live_equity_c3.json` (mốc = lần chạy đầu); realized = ledger c3 đóng sau mốc + cụm mở;
    đổi adapter (dry → live) ⇒ mốc mới + Telegram. Phí/rp của fill đến SAU khi cụm đã xoá khỏi sổ không vào equity c3 (giống sổ cũ).
11. **Stream**: SELL không-c3 trên symbol c3 KHÔNG tính là thoát của c3 (⇒ MERGED); khớp của stop c3 đã kích nhận diện theo `ai`
    của ALGO_UPDATE `c3s-` hoặc `ot=STOP_MARKET` khi symbol có stop c3 và không có algo không-c3. Lệnh sàn tự đóng (autoclose/ADL/
    delist) trên symbol c3 vẫn tính.
12. Từ chối của lớp phạm vi đi qua executor như lỗi API (`onApiResult(false)`) ⇒ có thể góp vào C3 (≥ 5 lỗi liên tiếp; mọi call
    đọc OK chen giữa đặt lại chuỗi). Không đổi executor để giữ R10.
13. `c3live_reanchor.sh` không còn tác dụng ở chế độ qty (không có mốc tmb).

## 6. Chưa làm / còn mở

1. Chưa chạy trên tài khoản thật (đúng lệnh cấm): cid lệnh sinh ra khi stop algo kích + thứ tự ALGO_UPDATE/ORDER_TRADE_UPDATE vẫn
   cần xác nhận trong dry/micro-live (ảnh hưởng nhận diện khớp stop c3 trên symbol có algo LEGACY).
2. `C3LiveRuntime` (static, Cfg, Aerospike) không có test end-to-end; các thành phần được nối giống hệt trong `MainAccountRig`.
3. `income` mới chỉ FUNDING_FEE; chưa đối chiếu COMMISSION/REALIZED_PNL theo symbol với ledger c3.
4. Weight thực tế production trên IP 242 (LEGACY-busy 85/phút + phần cũ) cần đo trong dry 11-18 (`HOURLY ... scope[...]`).

## 7. Fix sau tu kiem (commit cuoi)

`C3MergedGuard.setActExecutor`: co MERGED + chan mo moi dat DONG BO tren luong phat hien (stream/REST); hanh dong thay/huy stop (co the cho guard toi 61 s trong Urgent) chay tren thread `C3LIVE-PROTECT` (runtime) — khong chan luong websocket. Test `b3_mergedFlagIsSynchronousActionsRunOnActExecutor`. fake242 khong chay lai: `ops/` va code canary khong doi (fake242 dung jar canary pin 3k).
