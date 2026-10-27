# ROUND3H — sửa FAIL của A1 trên 3g (2 MAJOR mới do bản sửa + 1 MINOR)

Branch `v1.2/c3-live`, trên `c3ec07e1` (3g). Chỉ code + test + pin; không gọi Binance, không đụng 242, không push.
A1 xác nhận mọi mục 3f đã sửa. Test đối kháng của A1 (`~/claude_master/a1_3g_scratch/.../A1G3Test.java`) chép NGUYÊN VĂN vào repo (`cmp` giống hệt), không nới assert — PASS.

## Phát hiện → sửa → test
| # | phát hiện A1 | sửa | test |
|---|---|---|---|
| MAJOR-A | `flattenAll0` nhánh MIN-7b: đọc vị thế lỗi 2 lần ⇒ `markRed` ⇒ HUỶ stop `c3s-` ⇒ 20 USDT trần trụi; `state.red` làm mọi flatten sau bỏ qua symbol | tách "không đọc được" khỏi "chứng minh trộn". Không đọc được ⇒ **NOREAD**: không đóng, GIỮ stop `c3s-`, KHÔNG ghi `state.red`, journal `SCOPE_NOREAD_HOLD`, Telegram "canary SYM: khong doc duoc pham vi, stop van giu — KHONG dong"; `flatten()` báo `NOREAD … chay lai flatten sau` (bước TRƯỢT, không ĐỎ); lần flatten sau đọc được ⇒ đóng bình thường. Huỷ `c3s-` + RED bền CHỈ khi có bằng chứng trộn: sàn > ledger, sàn < 0, khớp ngoài không khớp stop canary | `A1G3Test.a1g3UnreadableScopeMustKeepCanaryStop`; `CanaryEngineTest.g3FlattenDoesNotCloseWhenScopeUnreadable` (đổi: NOREAD, stop còn, `red` rỗng, flatten lần 2 ĐẠT đóng) |
| MAJOR-B | `scopeProblem` gọi `ownStopTriggered(s, null)`: BẤT KỲ `c3s-` FINISHED nào cũng là "bằng chứng", rồi ledger := vị thế sàn ⇒ stop kích giữa 2 JVM + LEGACY mua cùng symbol ⇒ canary nhận phần LEGACY rồi bán | bằng chứng phải ĐỊNH LƯỢNG: `applyStopEvidence` — với mỗi stop `c3s-` của mình TRIGGERED/FINISHED có `actualOrderId`: `queryOrderById` (GET `/fapi/v1/order?orderId=`, journal) ⇒ `ledger −= executedQty` (khoá `c3s-fill:<ai>`, không trừ 2 lần); stop `closePosition` FINISHED không đọc được executedQty ⇒ ledger = 0; stop qty không đọc được ⇒ trừ origQty. Sau đó yêu cầu sàn == ledger mới (≤ 1 lot step, `marketStepSize`/`stepSize`), khác ⇒ TRƯỢT-ĐỎ (đã chứng minh). KHÔNG BAO GIỜ đặt ledger từ vị thế sàn | `A1G3Test.a1g3StopFiredBetweenJvmsThenLegacyBuyIsNotSoldByCanary` (executedQty 20 ⇒ ledger 0, sàn 7 ⇒ ĐỎ, 0 lệnh bán); `g3StopTriggeredBetweenJvmsShrinksLedgerOnlyWithEvidence`; `g3StopFillWithNonCanaryCid…` |
| MINOR | `preStop` đọc vị thế TRƯỚC vòng retry ⇒ RATE_LIMIT phía client ở lần đọc đó ⇒ từ chối stop ⇒ PROTECT_FAIL đóng vị thế | `runPre`: lỗi đọc RATE_LIMIT phía client (http 0, không phải GuardException) trong kiểm trước ghi ⇒ `GUARD_WAIT_RETRY` (≤ 2 lần chờ), CHẠY LẠI toàn bộ kiểm mỗi lần; `readFail` dùng cho `preStop`, `foreignOn`, `requireScopeClean`, `openNotional`; lỗi khác vẫn TỪ CHỐI | `CanaryGuardTest.stopPreCheckRateLimitedReadIsRetriedNotRefused` (positions RATE_LIMIT 1 lần ⇒ stop vẫn đặt, có journal `GUARD_WAIT_RETRY`) |
| tự rà | nhánh closePosition (ledger = 0) chạy lại mỗi lần `scopeProblem` thấy sàn < ledger, dù stop cũ đã tính ⇒ canary mở cụm mới thì ledger bị đưa về 0 sai ⇒ RED giả (huỷ stop) | khoá `c3s-fill:<ai>` = `CP_MARK`: stop đã tính ⇒ bỏ qua; `onCanaryExec` thấy `CP_MARK` ⇒ khớp muộn cùng lệnh stop KHÔNG trừ lần 2 | `CanaryEngineTest.h3ClosePositionStopEvidenceIsAppliedOnlyOnce` |
| doc | trần cộng dồn qua file gate | **Nâng trần cộng dồn bằng file gate KHÔNG nâng trần engine 4 USDT.** Engine luôn dùng trần phiên = min(2, 4 − lỗ các phiên trước); file gate chỉ nới kiểm ở script, engine vẫn chặt hơn và sẽ từ chối bước giao dịch khi 4 − lỗ trước ≤ 0,10 | — |

`ExchangeGateway.queryOrderById` mặc định ném `UnsupportedOperationException`; `C3LiveClient` cài (UNKNOWN_ORDER ⇒ rỗng); `CanaryGateway` journal; mock tìm theo orderId + symbol.

## Kết quả
- `mvn -o package -DskipTests=false`: **759 test, 0 fail, 0 error, 1 skip** (3g: 718; +38 A1G3Test — 2 test A1 + 36 kế thừa CanaryEngineTest — +1 CanaryEngineTest `h3…` (+1 kế thừa ở A1AdversarialTest), +1 CanaryGuardTest).
- `test_fake242.sh` (bản sao ops `~/c3e_patch/arch4`): **TEST PASS 145/145** (chạy 01:13–01:24, jar/pin cuối 427eb54b; số kiểm phụ thuộc khung giờ chạy — 3g đo 143 lúc 00:28).
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3h`, md5 **`427eb54bc9ed1aa0b3c4d3568c72cf65`**, pin `canary_lib.sh` (`canary_early_all.sh` dùng pin lib); `deploy_v12_dry.sh` giữ 3d. Kiểm bí mật jar (chỉ đếm): giống jar 3g; so 3d chỉ +2 class.

## Owner (sau audit A1)
```
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_set_key.sh
CANARY_RESET=1 bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_all.sh
```

## Còn mở (A1 kiểm phiên thật)
1. LEGACY mua + bán cùng symbol canary GIỮA 2 JVM mà ròng = 0 ⇒ không phát hiện được; stream sống thì `FOREIGN_FILL` bắt được.
2. Cid thật của lệnh thường sinh từ stop algo / thứ tự ALGO_UPDATE vs ORDER_TRADE_UPDATE — mock phủ cả 2 thứ tự. `queryOrderById(actualOrderId)` giả định orderId lệnh sinh ra truy vấn được qua `/fapi/v1/order` (chưa kiểm trên sàn thật; không đọc được ⇒ nhánh closePosition ⇒ ledger 0 ⇒ sàn ≠ 0 thì ĐỎ, an toàn).
3. NOREAD kéo dài: vị thế canary vẫn được stop `c3s-` bảo vệ, nhưng flatten không hoàn tất cho tới khi đọc được — owner chạy lại flatten.
4. Trần cộng dồn engine cố định 4 USDT (xem dòng doc ở trên).
5. Phí BNB quy theo giá last BNBUSDT — sai số nhỏ.
