# ROUND3G — sửa FAIL của A1 trên 3f (2 MAJOR + 6 MINOR)

Branch `v1.2/c3-live`, trên `e36979db` (3f). Chỉ code + test + script; không gọi Binance, không đụng 242, không push.
Test đối kháng của A1 (`~/claude_master/a1_3f_scratch/.../A1AdversarialTest.java`) chép NGUYÊN VĂN vào repo, không nới assert — PASS.

## Phát hiện → sửa → test
| # | phát hiện A1 | sửa | test |
|---|---|---|---|
| MAJOR-1 | `scopeProblem` co ledger chỉ vì sàn < ledger 2 lần đọc ⇒ LEGACY SELL (cid web_) cộng dồn one-way vào long canary: K2 ĐẠT, flatten bán nốt, LEGACY bị âm | ledger CHỈ co theo bằng chứng canary: khớp `c3x-` (trừ lúc response / stream z), hoặc stop `c3s-` TRIGGERED/FINISHED có `actualOrderId` (ALGO_UPDATE `ai` / `queryStop`; `OrderInfo.actualOrderId` mới, `parseAlgo` đọc). Vị thế giảm không giải thích được ⇒ TRƯỢT-ĐỎ. Khớp KHÔNG cid canary trên symbol canary (stream `FOREIGN_FILL`, z>0 / TRADE_LITE) ⇒ chờ ≤ 3 s cho ALGO_UPDATE, kiểm queryStop stop canary (actualOrderId = orderId) — không khớp ⇒ TRƯỢT-ĐỎ; không đóng; Telegram **KHAN CAP (URGENT)** | `A1AdversarialTest.a1LegacySellOnMainWhileCanaryLong`; `g3LegacySellFillSeenOnStreamMidStepIsUrgentRedNoClose`; `g3StopTriggeredBetweenJvmsShrinksLedgerOnlyWithEvidence`; `g3StopFillWithNonCanaryCidMatchedByActualOrderId{AlgoFirst,FillFirst}` |
| MAJOR-2 | `GUARD_WAIT_RETRY` gửi lại lệnh ghi sau ≤ 61 s mà không kiểm lại phạm vi | `call(.., pre, ..)`: MỌI kiểm trước ghi (`preOpen`: trần lỗ, giá mới, notional, lệnh/algo ngoài canary, tổng mở + vị thế ≤ ledger; `preSell`: bán ≤ ledger; `preStop`; `requireScopeClean`) chạy trước lần gửi đầu VÀ trước mỗi lần thử lại; lệnh ghi không có `pre` không bao giờ được thử lại; `sends(cid)` chỉ đếm lần thực gửi | `A1AdversarialTest.a1GuardRetryOpenAfterLegacyEntered`; `CanaryGuardTest.guardRetryRechecksBeforeResendingWrite` |
| MIN-3 | trần cộng dồn chỉ kiểm lúc đầu | engine: trần phiên = min(2, 4 − lỗ các phiên trước) (`CANARY_PRIOR_LOSS_USDT`, script truyền tự động qua `cl_run`); ≤ 0,10 hoặc thiếu ⇒ bước giao dịch TỪ CHỐI; dùng trong `lossCapHit`, `checkLoss`, ngân sách stop bảo vệ, K8. Script: `cl_cum_loss` tính `CL_CUM_PRIOR` + trần phiên, ≤ 0,10 ⇒ die | `g3SessionCapIsMinOfTwoAndFourMinusPrior`; fake242 mục 19 (lỗ cộng dồn 3,95 ⇒ dừng trước K0) |
| MIN-4 | phí trả bằng BNB không vào `lossNow` | `feeOtherUsd()` quy `<ASSET>USDT` (giá last, cache 60 s, lỗi ⇒ giá cũ); không có giá ⇒ DỪNG + flatten; `state.feeOtherUsd`; K8 + report tiêu chí 9 + lỗ cộng dồn script tính cả phần quy đổi | `g3BnbFeeCountedAtMarkOrRefused`, `g3NonStableFeeWithoutPriceStopsSession` |
| MIN-5 | state cũ tài khoản con (ZEC/Q): ledger lấy sổ; `JAR_READY=1` trước kiểm lỗ cộng dồn / CANARY_RESET ⇒ die chạy safe_flat trên state cũ | `ledger()` không có bản ghi ⇒ 0 (không lấy sổ); keycheck: state không có ledger ⇒ phạm vi = cid canary; `JAR_READY` đặt SAU kiểm lỗ cộng dồn + phiên cũ; `safe_flat` bỏ qua state trước 3f | `g3PreAddFourStateLedgerIsZeroAndNothingIsClosed`; fake242 17g (không JVM flatten) |
| MIN-6 | `C3LiveFlattener` mine = 0 ⇒ đóng `confirmedQty` | `qty = min(sàn, phần c3)`; phần c3 = 0 ⇒ 0 | `C3LiveFlattenerTest.mineZeroNeverClosesConfirmedQty` |
| MIN-7a | `newStopMarket` không kiểm vị thế sàn ≤ ledger | `preStop`: sàn > ledger ⇒ TỪ CHỐI; không đọc được vị thế ⇒ TỪ CHỐI | `CanaryGuardTest.stopRefusedWhenExchangePositionAboveLedgerOrUnreadable` (cả bán > ledger) |
| MIN-7b | `flattenAll0` vẫn đóng khi `SCOPE_NOREAD` | đọc lại 1 lần sau 1 s; vẫn lỗi ⇒ TRƯỢT-ĐỎ, không đóng | `g3FlattenDoesNotCloseWhenScopeUnreadable` |
| MIN-7c | lỗ đã chốt cộng mọi khớp trên symbol canary | `accountTrade` chỉ cho khớp cid `c3-`/`c3x-` hoặc stop canary (cid `c3s-` / actualOrderId) | `g3RealizedLossCountsOnlyCanaryCidFills` |
| MIN-8 | `legacy_symbols.csv` rỗng / thiếu vẫn chạy | script `cl_copy_legacy` die; engine K0 TRƯỢT khi `legacySize == 0` | `g3EmptyLegacyFileRefusesK0OnMainAccount`; fake242 mục 19 (thiếu / rỗng) |
| doc | ROUND3F ghi fake242 139, A1 đo 141 | 139 trong khung giờ, 141 ngoài khung giờ (2 kiểm "ngoài giờ": mục 1 rollback, 14b preflight) — đã sửa ROUND3F | — |

Mock: stop kích ⇒ stop FINISHED mang `actualOrderId` + ALGO_UPDATE (`ai`), tuỳ chọn cid lệnh thường không mang `c3s-` và ALGO_UPDATE trước/sau khớp.

## Kết quả
- `mvn -o -q package -DskipTests=false`: **718 test, 0 fail, 0 error, 1 skip** (3f: 667; +37 A1AdversarialTest — 2 test A1 + 35 kế thừa CanaryEngineTest — +11 CanaryEngineTest, +2 CanaryGuardTest, +1 C3LiveFlattenerTest).
- `test_fake242.sh` (bản sao ops, chạy 00:28 — trong khung giờ nên kiểm "ngoài giờ" rollback tự bỏ qua): **TEST PASS 143/143** (3f: 139 + 17g MIN-5 + 3 mục 19 MIN-8/MIN-3).
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3g`, md5 **`750291c4dd82933ce37bea15ffd674fb`**, pin `canary_lib.sh` (`canary_early_all.sh` dùng pin lib); `deploy_v12_dry.sh` giữ 3d. Kiểm bí mật jar (chỉ đếm): giống jar 3d trừ +2 class (như 3f).

## Owner (sau audit A1)
```
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_set_key.sh
CANARY_RESET=1 bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_all.sh
```

## Còn mở (A1 kiểm phiên thật)
1. LEGACY mua + bán cùng symbol canary GIỮA 2 JVM (không stream) mà ròng = 0 ⇒ không phát hiện được (vị thế không đổi); stream sống thì `FOREIGN_FILL` bắt được.
2. Cid thật của lệnh thường sinh từ stop algo và thứ tự ALGO_UPDATE / ORDER_TRADE_UPDATE — mock phủ cả 2 thứ tự; chờ tối đa 3 s.
3. Engine dùng trần cộng dồn 4 USDT cố định; MASTER nâng trần bằng file gate chỉ có tác dụng ở script (engine vẫn chặt hơn).
4. Phí BNB quy theo giá last BNBUSDT (không phải giá lúc khớp) — sai số nhỏ.
