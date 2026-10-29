# ROUND3J — ACK MARKET `FILLED` thiếu `avgPrice` (K4 10-28: qty có thật bị xoá khỏi sổ, vị thế không stop)

Branch `v1.2/c3-live`, trên `a5946799` (3i, A1 PASS-WITH-MINOR). Chỉ code + test + pin + doc; **không** gọi Binance,
**không** ssh 242, **không** chạy script canary, **không** đụng `~/claude_master/canary_3i` hay bản `canary_*` đã audit,
**không** push, **không** `git config`.

## 1. Bug và bằng chứng

Phiên canary 10-28, bước K4 (`~/claude_master/canary/report_20261028_092055/files/canary_20261028_091916_step_K4.jsonl`):

```
09:20:01.683  CALL_W newMarketOrder:BUY cid=c3-ZECUSDT-29885900-0 ok=true status=FILLED
              orderId=812083551851 executedQty=0.015  (KHONG co avgPrice)
09:20:01.685  [C3-LIVE-EXEC] FILL ZECUSDT c3-ZECUSDT-29885900-0 qty=0.015 avg=0.0 ...
09:20:01.712  WS ORDER_TRADE_UPDATE c=c3-ZECUSDT-29885900-0 X=FILLED z=0.015 ap=1310.36   (den SAU ACK ~30 ms)
09:20:02.687  LEG_DONE confirmed=false err="leg bi huy (khong khop)"
```

Chuỗi nhân quả: `C3LiveOrderExecutor.apply` thấy `status=FILLED`, `avgPrice=null` ⇒ `px=0.0` ⇒
`LiveBookC3.confirm(cid, 0.015, 0.0, …)` mà bản cũ coi `avgPx <= 0` là **exec=0** ⇒ `cancel()` ⇒ cụm bị xoá ⇒
`CanaryEngine.openLeg` đọc sổ rỗng ⇒ K4 TRƯỚT. Trên tài khoản, `positionRisk` vẫn `ZECUSDT 0.015 @1310.36`.
Trong LIVE: vị thế thật **không có trong sổ** và **không có stop** (cleanup của canary đóng nó; LIVE thì không).

K1 "xanh" trước đó không chứng minh được nhánh ACK: K1 chạy `injectTimeout=true` nên đi nhánh timeout → `queryOrder`
(có `avgPrice`). Đây là lỗ hổng test, không phải may mắn.

## 2. Yêu cầu → sửa → test

| # | yêu cầu | sửa (file:line) | test |
|---|---|---|---|
| R1 | `executedQty > 0` do sàn báo (ACK / queryOrder / `z` của stream) ⇒ sổ **phải** ghi qty; không bao giờ suy "không khớp" từ giá thiếu/0 | `LiveBookC3.confirm` (:596) tách điều kiện: `execQty<=0` ⇒ cancel (như cũ); `qty>0 & avgPx<=0` ⇒ `LOG.error` + `return false` (giữ leg, KHÔNG huy). `confirmProvisional` (:616) ghi qty + giá TẠM. `C3LiveOrderExecutor.apply` (:248-330) luôn ghi qty khi `exec>0`. `FillAccounting.onBuy` (:160-190) không cancel khi thiếu giá | T1, T2, T3, T6, T6b, `bookConfirmKeepsQuantityWhenPriceMissing`; control trên HEAD §7 |
| R2 | Giá khi ACK thiếu `avgPrice`, thứ tự (a) stream `ap`/`L` → (b) `queryOrder` (lui đọc-sau-ghi 3e) → (c) `userTrades` (bình quân gia quyền), tổng ≤ 3 s; vẫn không có ⇒ ghi qty với giá TẠM = mark (`pxProvisional`, journal `PX_PROVISIONAL`), sửa lại khi có giá thật; loss/stop dùng giá xấu nhất của mark và last | `FillPriceResolver` (mới): `observe` (:113) cache từ stream; `resolve` (:145/:153) (a) chờ ≤ 600 ms → (b) `QUERY_BACKOFF_MS {250,500,1000,1250}` chừa 500 ms cho (c) → (c) `userTrades`; `DEFAULT_BUDGET_MS=3000`. `C3LiveOrderExecutor.apply` gọi resolver (a)(b)(c), hết ⇒ `markPrice()` (positionRisk mark → tickers24h → ref) + `confirmProvisional`. `correctProvisional()` (:345) sửa giá TẠM (throttle 5 s). `LiveBookC3.correctPrice` (:651). `CanaryEngine.budgetEntry` (:1017) = max(mark, last, entry sàn, giá sổ) khi còn giá TẠM; `trailRateAt` (:1000) đặt stop theo giá xấu nhất; `lossNow` (:331) và `worstOpenLoss` (:744) dùng `budgetEntry` | T3 (PX_PROVISIONAL → PX_CORRECTED → ledger), `resolverOrderStreamThenQueryThenTradesThenNone`, `weightedAverageOfTrades`, T1, T2 |
| R3 | Stop bảo vệ đặt NGAY sau khi executor xác nhận qty (không chờ stream FILLED) — đóng A1 3i MINOR-1; giữ hạn 61 s từ lúc gửi lệnh mở; giữ làn khẩn cấp khi quá hạn | `CanaryEngine.openLeg` (:874): đọc sổ → nếu CONFIRMED thì `protect(sym, sentRef + PROTECT_MAX_MS)` **trước** `waitFor(ORDER_TRADE_UPDATE FILLED)`; chờ stream chỉ để lấy bằng chứng/độ trễ rồi mới `LEG_DONE` | T1, T2, T3 (stop/entry đúng), T5, T7 (K4 DAT), toàn bộ `CanaryEngineTest`/`A1*` |
| R4 | `executedQty == 0` với `FILLED`/không rõ ⇒ UNKNOWN (không cancel) + trả sàn; chỉ cancel khi sàn nói `CANCELED/EXPIRED/REJECTED` với `exec=0` | `C3LiveOrderExecutor.apply`: FILLED & exec=0 ⇒ `markUnknown` + `requeryIfPossible` (:335); cancel chỉ ở nhánh `{CANCELED, EXPIRED, EXPIRED_IN_MATCH, REJECTED}` & exec=0 (:311-319); `FillAccounting.onBuy` (:191) chỉ cancel với 4 trạng thái đó | T4, `cancelWithExecZeroStillCancels`, T3 (stream FILLED `z=0.015` + `ap=0`) |
| R5 | Giữ nguyên 3e–3i (scope guard, RED, ledger định lượng, rate guard, làn khẩn cấp); `A1AdversarialTest`/`A1G3Test` không đổi byte nào | Không sửa 2 file test đó; không sửa `CanaryLimits`, `RateGuard`, `CanaryGateway` phần guard (chỉ thêm `userTrades` đọc + weight 5) | `git status` không có 2 file; 785 test pass (gồm 39 + 24 test kế thừa của 2 lớp A1) |

Test mới:

| test | nội dung | kết quả |
|---|---|---|
| T1 | ACK `FILLED` không `avgPrice`, stream `ap` đến sau 300 ms ⇒ leg giữ, giá = ap, 1 stop closePosition, K1 DAT, `PX_RESOLVED source=STREAM_AP`, 0 `PX_PROVISIONAL` | `CanaryK4NoPriceTest.t1…` |
| T2 | ACK không giá, stream bị giữ (đến sau 1,5 s), `queryOrder` có `avgPrice` ⇒ giá từ `queryOrder`, `PX_RESOLVED source=QUERY`, stop đặt, K1 DAT | `t2…` |
| T3 | Không nguồn nào có giá ⇒ `PX_PROVISIONAL` = mark (1305), stop theo giá xấu nhất (1310), sau đó `queryOrder` trả 1310 ⇒ `PX_CORRECTED source=QUERY`; đóng vị thế ⇒ dòng ledger `avg_entry=1310` (không phải 1305), `realized=-0.075` = (1305−1310)×0,015 | `t3…` |
| T4 | ACK `FILLED` `executedQty=0` → trả sàn thấy `FILLED 0.015` ⇒ leg CONFIRMED, 1 lần gửi, 0 cancel | `ExecNoPriceTest.t4…` |
| T5 | ACK mất (MO-5 inject) ⇒ hành vi cũ: 1 lần gửi, `queryOrder` theo cid, K1 DAT, stop đặt | `t5…` |
| T6 | Đường production `C3LiveOrderExecutor` + ACK không giá + không stream/query/trades ⇒ sổ giữ `qty=0.015`, `pxProvisional`, `avg=mark`, journal `PX_PROVISIONAL`, 0 cancel | `t6…` |
| T6b | ACK không giá, `queryOrder` có giá ⇒ giá THẬT (không provisional) | `t6b…` |
| T7 | Tái hiện **nguyên văn** chuỗi 10-28: ACK `cid=c3-ZECUSDT-29885900-0 orderId=812083551851 qty=0.015` không `avgPrice` + raw `ORDER_TRADE_UPDATE ap=1310.36` (cùng phút 29885900, cùng cid) ⇒ `openLeg` CONFIRMED, `LEG_DONE avg=1310.36`, K4 chạy hết: stop kích, cụm đóng `TRAILING_STOP`, ledger `qty=0.015 avg_entry=1310.36` | `t7…` |

## 3. R1 — danh sách call-site (đã rà từng chỗ, cả canary và production)

Ghi trạng thái leg:

| call-site | đường | hành vi sau 3j |
|---|---|---|
| `exec/C3LiveOrderExecutor.java:299` `book.confirm` | production + canary (ACK/queryOrder) | chỉ gọi khi `px > 0`; `px<=0` đã được resolver/provisional xử lý trước |
| `exec/C3LiveOrderExecutor.java:286` `book.confirmProvisional` | production + canary | ghi qty + giá TẠM = mark, `pxProvisional=true`, journal `PX_PROVISIONAL` |
| `fill/FillAccounting.java:183` `book.confirm` | production + canary (stream) | `px = ap > 0 ? ap : L`; thiếu cả hai ⇒ **không** confirm, **không** cancel, chỉ WARN (executor đang giải giá) |
| `exec/C3LiveOrderExecutor.java:138,156,170,187,314,417,426` `book.cancel` | production + canary | 138/156 (executor từ chối / persist fail trước khi gửi: chưa gửi ⇒ đúng), 170 (`isDefinitelyNotExecuted`), 187/417/426 (queryOrder khẳng định ABSENT), 314 (chỉ CANCELED/EXPIRED/EXPIRED_IN_MATCH/REJECTED + exec=0) |
| `fill/FillAccounting.java:193` `book.cancel` | stream | chỉ 4 trạng thái kết thúc chắc chắn + `z=0` |
| `canary/CanaryEngine.java` | — | **không** gọi `confirm/cancel` trực tiếp (chỉ đọc `book.leg`, đặt stop, journal) |
| `recon/Reconciler.java` | production + canary (startup) | `overrideFromExchange` (qty/gia theo sàn) — nay xoá cờ `pxProvisional` của cụm vì giá sàn là giá THẬT |
| `risk/C3LiveFlattener.java`, `exit/TrailingStopManager.java` | — | không ghi trạng thái leg |

Đọc `avgPrice`/`avgPx` (rà hết):

| nơi đọc | dùng làm gì | sau 3j |
|---|---|---|
| `C3LiveOrderExecutor.apply` (:254) | giá khớp từ ACK | nguồn của bug; nay `px<=0` ⇒ resolver ⇒ provisional |
| `FillAccounting.onBuy` (:163) | giá khớp từ stream | `ap` trước, rồi `L`; không có ⇒ giữ leg |
| `FillPriceResolver` (:184) | `queryOrder.avgPrice` | nguồn (b) |
| `CanaryEngine.onStreamText` (:580) | sửa giá TẠM khi `ap` đến | `correctPrice` + journal `PX_CORRECTED source=STREAM_AP` |
| `LiveBookC3.Cluster.avgPrice/avgEntryF/confirmedMargin/firstEntryPrice` | VWAP cụm | tính từ `execQty*avgPx` của leg CONFIRMED ⇒ giá TẠM được thay bằng giá thật |
| `LiveBookC3.appendLedger` (:937) | dòng `c3live_ledger.csv` | viết lúc đóng cụm ⇒ dùng giá đã hiệu chỉnh |
| `CanaryEngine.protect` (:784), `budgetEntry` (:1017), `lossNow` (:331), `worstOpenLoss` (:744) | ngân sách lỗ, khoảng cách stop | giá xấu nhất (mark, last, entry sàn, giá sổ) khi còn giá TẠM |
| `CanaryEngine.bookMatchesExchange` (:2191) | K1 đối chiếu sổ ↔ `positionRisk.entryPrice` (≤ 1 tick) | giữ nguyên: nếu giá vẫn là TẠM và lệch > 1 tick thì K1 TRƯỢT (fail-closed, đúng ý) |
| `Reconciler` (:393-397, :700) | phát hiện lệch qty/giá, UPL thông tin | dùng `avgPrice` của sổ; startup sửa từ sàn |
| `TrailingStopManager` (:197) | VWAP cho trailing | giá TẠM ⇒ `protect` quy đổi tỷ lệ để stop rơi đúng giá xấu nhất; sau hiệu chỉnh ratchet chỉ tăng (an toàn) |
| `C3LiveClient.auditOk` (:165), `CanaryGateway.describe` (:525) | audit log/journal | chỉ ghi nhận, không quyết định |

## 4. Chi tiết R2

- Ngân sách: `FillPriceResolver.DEFAULT_BUDGET_MS = 3000` cho cả (a)+(b)+(c); (a) chờ tối đa 600 ms (K4 thật: `ap` đến
  sau ACK 7–480 ms); (b) lùi `250/500/1000/1250 ms` như 3e và **dừng trước hạn 500 ms** để chừa (c); `resolve(..., 0)`
  dùng cho luồng hiệu chỉnh định kỳ (không chờ stream).
- Giá TẠM = **mark hiện tại** (`positionRisk.markPrice`; không có vị thế ⇒ `tickers24h.lastPrice`; cuối cùng ⇒ `refPx` của
  leg). Không đọc được cả ba ⇒ giữ leg UNKNOWN (không huy).
- Ngân sách lỗ/stop khi còn giá TẠM: `budgetEntry = max(mark, last, entryPrice sàn, giá sổ)`. Lý do của `entryPrice sàn`:
  `CanaryGateway.preStop` từ chối stop thấp hơn `entry × (1 − 4,5 % − tol)`; nếu chỉ dùng mark (có thể thấp hơn entry thật)
  thì stop hợp lệ theo sổ lại bị guard từ chối ⇒ `PROTECT_FAIL` + đóng vị thế. Với long, entry cao hơn ⇒ notional và stop
  cao hơn ⇒ bảo thủ hơn về lỗ. `lossNow` cộng thêm `qty × (max(mark,last) − mark)` (lấy max với UPL thật của sàn).
- Hiệu chỉnh: 4 đường — stream `ap` (`CanaryEngine.onStreamText`, `FillAccounting.onBuy`), luồng định kỳ
  `executor.correctProvisional()` (canary `tick()` 1 Hz + production mỗi `RESOLVE_EVERY_MS`, throttle 5 s, 0 call khi không
  có leg TẠM), và nhánh `apply` khi ACK/queryOrder sau đó có giá. `correctPrice` idempotent, xoá cờ, tính lại VWAP cụm,
  `adjQty/adjAvg`, `peak`; dòng ledger lúc đóng dùng giá đã hiệu chỉnh. PnL đã chốt vẫn lấy `rp` của sàn (không bao giờ suy
  từ giá TẠM).

## 5. Chi tiết R3/R4

- `openLeg`: `executor.submit` → nếu sổ CONFIRMED (giá thật **hoặc** giá TẠM) ⇒ `protect(sym, sentRef + 61 s)` **ngay**,
  rồi mới chờ `ORDER_TRADE_UPDATE FILLED` (≤ `fillEventWaitMs`) để ghi `streamLatMs`/`LEG_DONE` và cập nhật `avg` sau hiệu
  chỉnh. Hạn 61 s tính từ `CanaryGateway.firstSentMs` (≤ lúc khớp) như 3i; quá hạn/không xác nhận ⇒ `PROTECT_FAIL` ⇒ đóng
  phần canary trong làn khẩn cấp (không đổi).
- Nếu sau `submit` sổ **chưa** CONFIRMED (ACK mất, trạng thái không rõ) ⇒ chờ thêm bằng chứng stream tối đa
  `fillEventWaitMs` rồi đọc lại; vẫn không ⇒ TRƯỢT như cũ (không đặt stop khi chưa biết qty).
- R4: `FILLED` + `executedQty=0` ⇒ `markUnknown("filled_exec0")` + 1 lần `queryOrder` ngay; `queryOrder` trả qty > 0 ⇒ áp
  tiếp; vẫn 0 ⇒ giữ UNKNOWN cho `resolveUnresolved` (không gửi lại, không huy). Chỉ 4 trạng thái kết thúc chắc chắn với
  `exec=0` mới huy giữ chỗ.

## 6. Thay đổi so với 3i (tóm tắt để A1 đối chiếu)

1. `LiveBookC3`: `pxProvisional` (persist `px_provisional`), `confirmProvisional`, `correctPrice`, `provisionalLegs`,
   `ClusterView.hasProvisional/provisionalQty`, `overrideFromExchange` xoá cờ; `confirm` thêm nhánh R1 (return false + ERROR).
2. `C3LiveOrderExecutor`: `FillPriceResolver`, `PriceObserver`, `apply(cid,o,resolvePrice,requery)`, `correctProvisional`,
   `markPrice`, `nProvisional`, `stats()` thêm `provisional=`.
3. `FillAccounting`: cache giá (`observe`), `ap||L`, không cancel khi thiếu giá, hiệu chỉnh giá TẠM, cancel theo 4 trạng thái.
4. `CanaryEngine`: `openLeg` (R3), `budgetEntry`/`trailRateAt`, `lossNow`/`worstOpenLoss`, `tick()` hiệu chỉnh, journal
   `PX_PROVISIONAL`/`PX_CORRECTED`, `build()` chia sẻ 1 `FillPriceResolver`.
5. `ExchangeGateway.userTrades` (+`TradeFill`, `C3LiveClient` weight 5, `DryGateway`, `CanaryGateway`), `C3LiveRuntime` chia
   sẻ resolver + gọi `correctProvisional()` trong vòng định kỳ.
6. Không đổi: `CanaryLimits`, `RateGuard`, `CanaryGateway` guard/scope, `Reconciler` logic, `C3LiveFlattener`,
   `A1AdversarialTest`, `A1G3Test`, `deploy_v12_dry.sh`.

## 7. Kết quả kiểm

- `mvn -o package -DskipTests=false`: **Tests run: 785, Failures: 0, Errors: 0, Skipped: 1 — BUILD SUCCESS**
  (3i: 773; +12 = `CanaryK4NoPriceTest` 5 + `ExecNoPriceTest` 7).
- **Control trên code CŨ** (`git archive a5946799` → `/tmp/c3j_ctl`, `PrivateConfig` = stub dummy của scratch oc1028):
  cùng assertion "px<=0 KHÔNG được coi là khớp" ⇒ **FAIL** `AssertionError: px<=0 KHONG duoc coi la khop`
  (`confirm()` trả true và xoá leg) ⇒ test bắt đúng bug, không phải test "xanh vô nghĩa".
- `ops/c3live/canary/test_fake242.sh` trên bản `git archive` của branch (242 giả, không ssh, không Binance; `ops/` y hệt
  HEAD cuối): 2 lần — **149/149** (08:0x, ngoài khung giờ nên có thêm 2 kiểm "từ chối ngoài khung giờ") và **147/147**
  (08:11, trong khung giờ nên 2 kiểm đó bỏ qua). 0 FAIL cả hai lần; chênh 149 vs 147 đúng bằng 2 kiểm phụ thuộc giờ.
- Không có test cũ nào bị sửa/nới; 2 file A1 byte-identical (`git status` sạch với chúng).

## 8. Jar + pin

- `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3j`, md5 **`28566071ad87c508f142c2dd2a70a709`**.
- `ops/c3live/canary/canary_lib.sh`: `CANARY_JAR_MD5=28566071ad87c508f142c2dd2a70a709` (3i: `b6de7ddb…`).
  `ops/c3live/deploy_v12_dry.sh` giữ pin 3d (`ddd8fe17…`) — không đụng.
- Kiểm bí mật jar (CHỈ đếm, không mở/không in nội dung): 3i 8917 entry / 7783 class → 3j 8922 entry / 7788 class (+5 class =
  `api/TradeFill`, `exec/FillPriceResolver`, `FillPriceResolver$Source`, `FillPriceResolver$Resolved`,
  `C3LiveOrderExecutor$PriceObserver`), không thêm tài nguyên/dữ liệu nào khác.

## 9. Chưa làm / còn mở

1. **Chưa chạy lại canary thật** (đúng lệnh cấm): K4 mới chỉ được chứng minh bằng mock + fixture. Owner chạy
   `canary_early_all.sh` sau audit A1.
2. `userTrades` mới chỉ đọc `symbol+orderId` (weight 5); **chưa** đối chiếu `time` với cửa sổ phiên, chưa dùng để phát hiện
   fill lạ.
3. Nếu vẫn không nguồn nào có giá và mark cũng không đọc được ⇒ leg giữ UNKNOWN và phiên TRƯỢT (fail-closed). Chưa có
   đường tự động đóng vị thế khi qty biết nhưng giá hoàn toàn không đọc được — ngân sách 3 s + 3 nguồn được coi là đủ
   (chưa có bằng chứng thực tế nào vượt).
4. `bookMatchesExchange` (K1) vẫn đòi VWAP sổ ≈ `entryPrice` sàn ≤ 1 tick: nếu giá còn TẠM và lệch, K1 TRƯỢT (cố ý). Cần
   theo dõi tần suất `PX_PROVISIONAL` trong phiên thật.
5. Chênh lệch chi phí 0.0201 vs 0.0304 của phiên 10-28 (ghi ở `CANARY_K4.md` §3) **vẫn CHƯA GIẢI THÍCH** — ngoài phạm vi 3j.
