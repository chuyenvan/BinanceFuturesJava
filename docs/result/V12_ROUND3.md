# V12_ROUND3 — G-CANARY: prereg chốt + công cụ `C3LiveCanary` + 7 script owner

Branch `v1.2/c3-live`, agent v12exit, 2026-10-25. **Chưa chạy canary thật** (Oracle cấm REST Binance; không đụng 242). Mọi kiểm thử chạy trên
`MockExchangeGateway` (Java) và "242 giả" trên đĩa Oracle (script). **A1 audit vòng này trước khi canary chạy** (prereg §10).

## 1. Hash, prereg, jar

| mục | giá trị |
|---|---|
| prereg chốt (commit riêng, TRƯỚC code) | `2dd69ff0` — `docs/prereg/GCANARY_PREREG.md` sha256 `06a7c1c55a37dd3b7c22ddb4aaea8dc4a10c7d34b05548ea81d9b168a1370178` |
| lock tài khoản con + ticker 24h | `045292ce` |
| `C3LiveCanary` + test | `7912fd05` |
| 7 script owner + test_fake242 mục 14 | `fe499996` |
| pin jar | `d259460a` |
| jar dùng chung dry + canary | `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3`, md5 **`e702cc2d85e2402e8f9c1cf841eef875`** (pin trong `deploy_v12_dry.sh` NJ_MD5 và `ops/c3live/canary/canary_lib.sh` CANARY_JAR_MD5). Jar 2h (`e1b1b7ec`) đã xoá. |
| build | 640 test, 0 fail, 0 error (621 vòng 2h + 19 test canary: CanaryEngineTest 9, CanaryGuardTest 10) |
| test script | `ops/c3live/test/test_fake242.sh`: **77/77 PASS** (mục 14 mới: script canary) |
| parity 10-23 (c3_shadow, jar 3 vs dcae2e2b) | **PASS** — out_BT `e0918a33` khớp, out_NEW2 `e0918a33` khớp, fund_BT `a81b3b03` khớp, fund_NEW2 `8dea3f70` khớp; ctl only_ref = only_new = 0; strace AF_INET non-loopback = 0 (`docs/result/round3/r3_compare.json`) |

Delta code ngoài package canary (A1 cần xem): `C3LiveRuntime` lấy lock `run/c3live_account.lock` **chỉ khi `LIVE_ADAPTER=live`** (không lấy
được ⇒ `initFailed`, không chạy); dry/shadow không đổi hành vi. `ExchangeGateway.tickers24h` (default ném UnsupportedOperation) +
`C3LiveClient` (GET `/fapi/v1/ticker/24hr`, không ký, weight 1 / 40). Đường c3_shadow: parity ở trên.

## 2. Kiến trúc canary

- **JVM riêng** `com.binance.chuyennd.c3live.canary.C3LiveCanary <lệnh>` chạy trên 242 bằng jar đang deploy, `cwd = APP_DIR`, thư mục
  `run/canary/` (sổ `c3live_book.json`, `canary_state.json`, journal `canary_<TS>_<lệnh>.jsonl`, log `canary_jvm.log` qua
  `logback-canary.xml`). Không ghi `logs/full.log` của bot, không Aerospike, không đụng JVM dry.
- **Lệnh:** `keycheck | preflight (K0) | setup | step <K> | flatten | cleanup | status`. Dòng cuối stdout `RESULT <K> DAT|TRUOT|TU_CHOI [| lý do]`;
  mã thoát 0 / 3 / 2 (4 = lỗi).
- **Dùng lại đúng lớp c3_live** trên `CanaryGateway`: `C3LiveOrderExecutor` (cid `c3-…`), `LiveBookC3`, `FillAccounting`, `TrailingStopManager`,
  `OwnStopGuard`, `Reconciler` (lớp A/B), `FlatConfirm`, `UserStream` (2 URL, keepAlive), `AccountModeGuard`, `C3LiveFlattener`.
- **Lock tài khoản con** (`C3LiveAccountLock`, FileChannel.tryLock): canary lấy lock trước khi tạo client; runtime chính chỉ lấy khi adapter live
  ⇒ canary chạy song song dry (MỞ-1) nhưng **không bao giờ** song song live; 2 canary cũng loại trừ nhau.
- **Sổ cái độc lập** từ sự kiện stream (rp, phí stable, funding) trong `canary_state.json` — dùng cho trần lỗ và K8 (K6b làm mất sổ chính).
- **cid không trùng giữa các cụm:** mở cụm mới / đóng cụm luôn sang phút mới so với lần trước của cùng symbol.

## 3. Giới hạn CỨNG (hằng số trong code, không config/env)

| guard | ở đâu | test |
|---|---|---|
| chỉ 2 symbol do LUẬT §3 chọn (hạng 1 chính, hạng 2 phụ K7b); kiểm lại luật cấu trúc mỗi bước | `CanaryGateway`, `SymbolPicker`, `CanaryEngine.revalidateSymbols` | `otherSymbolsAndForbiddenActionsRefused`, `moreThanTwoSymbolsRejected`, `symbolRuleRanksByQuoteVolumeAndFilters`, fullSession ("0 lệnh ngoài 2 symbol") |
| notional ≤ 25 USDT/lệnh mở (lệnh chuẩn 20), giá lấy mới từ ticker | `CanaryLimits.MAX_ORDER_NOTIONAL_USDT` | `notionalAboveCapRefused`, `readFailureForPriceOrPositionsRefusesOpen` |
| tổng mở ≤ 40 USDT (vị thế đọc từ sàn) | `MAX_OPEN_NOTIONAL_USDT` | `openTotalAboveCapRefused` |
| trần lỗ 2 USDT = max(phí + lỗ đã chốt từ stream, tmb0 − tmb) ⇒ tự flatten, phiên DỪNG (bước sau TU_CHOI; flatten vẫn chạy) | `CanaryEngine.checkLoss`, `CanaryGateway` (từ chối lệnh mở) | `lossCapFlattensAndStopsSession`, `lossCapRefusesOpenButAllowsClose` |
| không chạm vị thế/lệnh/algo ngoài 2 symbol; có ⇒ từ chối bước; flatten chỉ đóng 2 symbol | `foreignExposure`, `CanaryGateway` | `foreignPositionRefusesWithoutTouchingIt`, `foreignPositionBlocksOpen` |
| từ chối khi lock tài khoản con đang bị giữ (runtime live / canary khác) | `C3LiveCanary.run` | `accountLockIsExclusiveAndCanaryRefusesWhileRuntimeHoldsIt`; script 14g |
| chiều lệnh: SELL phải reduceOnly, BUY không reduceOnly; stop chỉ SELL; stop qty phải reduceOnly; leverage chỉ 1; marginType chỉ CROSSED; dualSide chỉ false | `CanaryGateway` | `otherSymbolsAndForbiddenActionsRefused` (13 lần từ chối) |
| MỞ-5: tiêm timeout **1 lần/phiên**, cờ `CANARY_INJECT_TIMEOUT=1` mặc định tắt, ghi trạng thái TRƯỚC khi gửi | `CanaryGateway.armTimeoutAfterNextOpen`, `CanaryEngine.k1` | `mo5InjectionOnlyOncePerSession`, `injectionsAreClientSideOnly`; script 14c/14g |
| tiêm lỗi (MỞ-5, K7, K7b) chỉ phía client, không gửi request lạ | `CanaryGateway`, `StreamTap` | `injectionsAreClientSideOnly` |

Mọi từ chối là `GuardException` (definitelyNotExecuted) + sự kiện `GUARD_REFUSE` trong journal.

## 4. Bảng K × test (prereg §4)

| K | kiểm trong code (ĐẠT khi) | test Java (MockExchangeGateway) | script |
|---|---|---|---|
| K0 | chỉ đọc (0 lệnh ghi); tmb ≈ CANARY_EXPECT_TMB ±1 %; multiAssets=true; dual=false; CROSSED/1x cả 2 symbol; 0 vị thế (positionRisk **và** account.positions), 0 lệnh, 0 algo; WS mở ≤ 5 s; keepAlive ≥ 2 trong 65′; chọn symbol + mốc tmb0 | fullSession K0; `k0FailsWithoutExpectedTmbOrWrongMarginMode` (thiếu tmb ⇒ TRƯỢT, tmb0 null; ISOLATED/3x ⇒ TRƯỢT gợi ý SETUP; SETUP sửa) | `canary_preflight.sh` (14b) |
| K1 | MARKET 20 USDT qua executor, FILLED, sổ = sàn (qty, avg ±1 tick), ORDER_TRADE_UPDATE FILLED; MỞ-5: queryOrder(cid) + 0 gửi lại | fullSession K1 (MỞ-5 bật: 1 newMarketOrder, ≥ 1 queryOrder); `mo5InjectionOnlyOncePerSession`; `k1RefusedWhenNotFlat` | `canary.sh` (INJ=0 mặc định), `canary_step.sh K1` + `CANARY_INJECT_TIMEOUT=1` |
| K2 | (a) −20 % closePosition; (b) dời −19 % (đặt mới → NEW → huỷ cũ); (c) closePosition thứ 2 cùng chiều (ghi −4130 hay nhận); (d) qty+reduceOnly; sau mỗi bước đúng 1 stop c3s- NEW, `queryStop` khớp, `algoStatus=NEW` | fullSession K2 với `rejectSecondClosePosition` (−4130 ngay ở (b) ⇒ trailing chuyển qty+RO `fallbackQty=1`; (c) được nhận rồi guard huỷ CANCELLED; còn 1 stop) | `canary.sh` |
| K3 | stop trên mark ⇒ −2021 ⇒ MARKET reduce-only (TRAILING_IMMEDIATE), vị thế 0, 0 stop | fullSession K3 (`rejectWouldTrigger`) | `canary.sh` |
| K4 | stop mark −0,15 %, chờ kích ≤ 30′; lý do TRAILING (EXTERNAL ⇒ MIN, không dừng); 0 stop mồ côi ≤ 30 s (> 60 s ⇒ TRƯỢT); ledger 1 dòng | fullSession K4 (`triggerStops` sau 120 s, ledger TRAILING_STOP) | `canary.sh` |
| K5 | `closeCluster(TIME_STOP_168H)`: c3x- FILLED, guard huỷ stop CANCELLED, 0 algo, sổ xoá cụm | fullSession K5 | `canary.sh` |
| K6 | K6_OPEN (mở + arm, `Runtime.halt(0)`) → K6_RESTART (JVM mới): 12 trường cụm bit-identical, 0 lệnh ghi trước/trong reconcile khởi động, 1 stop, nhịp trailing không đặt stop trùng, sổ = sàn | fullSession K6 (0 newMarketOrder/newStopMarket mới) | `canary.sh` (2 JVM) |
| K6b | K6B_OPEN → script đổi tên sổ → K6B_RESTART: stop c3s- **vẫn còn** (orphanKept), 0 huỷ stop, symbol vào UNKNOWN (A), Telegram; rồi flatten | fullSession K6b; `k6bFailsIfBookNotRenamed` | `canary.sh` (đổi tên `.k6b_<TS>`, flatten sau) |
| K7 | cắt WS phía client 330 s: phát hiện ≤ 15 s, REST ~10 s/lần, Telegram sau 5′, nối lại + bù REST; 0 cụm/stop xoá sai; sổ = sàn | fullSession K7 (detectMs ≤ 15 s, telegramDown) | `canary.sh` |
| K7b | reconcile khởi động trước; symbol chính chốt khi positionRisk lỗi (client): (B) chỉ chặn symbol chính, symbol phụ **vào được 1 leg thật**; (A) không có nếu < 10′ (≥ 10′ ⇒ A + Telegram); gỡ B sau 2 lần đọc phẳng + account phẳng; timeline 10 s | fullSession K7b (A không xuất hiện; B gỡ ở ~150 s) | `canary.sh` |
| K8 | 0 vị thế / 0 lệnh / 0 algo; \|tmb0 + rp − phí + funding − tmb\| / tmb ≤ 1 %; chi phí ≤ 2 USDT; phí tài sản ngoài stable ⇒ TRƯỢT | fullSession K8 (diffFrac < 1e-6) + cleanupCheck | `canary.sh`, `canary_report.sh` |
| bí mật | journal che listenKey, không có signature | `journalHasNoListenKeyOrSecrets`; `NoSecretInClassesTest` | report đếm trên 242 (14d) |

Tiền điều kiện chung mỗi bước: phiên chưa DỪNG, đã chọn symbol + có tmb0, không có exposure ngoài canary, symbol còn đúng luật cấu trúc,
kiểm trần lỗ (`stepsRefusedBeforePreflight`). TRƯỢT ⇒ engine tự flatten (trừ `_OPEN`, K8, K6B_RESTART — script flatten sau).

## 5. 7 script owner (`ops/c3live/canary/`, chạy trên Oracle, ssh 242)

| prereg §6 | script | việc | an toàn |
|---|---|---|---|
| golive_keys_install | `c3live_keys_install.sh` | `read -s` key/secret → stdin ssh → `/root/.config/c3live/keys.env` (600, thư mục 700, đúng định dạng `C3LiveKeys`); đã có ⇒ cần `REPLACE=1` (backup `.bak_<TS>`); rồi `keycheck` chỉ đọc. Repo **không có** `setup_c3live_key` nào — đây là script cài key duy nhất | YES=1; key không vào dòng lệnh/log; `CHECK_ONLY=1` chỉ kiểm |
| golive_canary_preflight | `canary_preflight.sh` | điều kiện vào §2 (gate MASTER, jar md5, bot adapter dry ≥ 5 ngày từ `run/.v12_start_epoch`, 0 `[KILLSW] LATCH` / 0 `[C3-LIVE-ORDER]` từ mốc đó, không adapter live, không JVM canary khác, time_ok) → K0 65′ (YES=1) | không YES ⇒ chỉ kiểm |
| golive_canary | `canary.sh` | K1 K2 K3 K4 K5 K6 K6b K7 K7b K8; dừng ở bước đầu không ĐẠT ⇒ flatten; ngoài khung giờ giữa các bước ⇒ chờ ≤ 60′ | YES=1; `CANARY_SEQ` cho bản rút gọn sau đổi jar |
| golive_canary_step | `canary_step.sh <K>` | 1 bước (SETUP, K1..K8, K6, K6B, K7B, hoặc từng nửa _OPEN/_RESTART); không ĐẠT ⇒ flatten | YES=1, danh sách trắng |
| golive_canary_flatten | `canary_flatten.sh` | đóng 2 symbol canary + huỷ stop c3s- qua guard + in trạng thái; không chốt giờ | YES=1 |
| golive_canary_report | `canary_report.sh [dir]` | trên 242 đếm bí mật từng file (giá trị key/secret đọc ngay trên 242, chỉ in SỐ ĐẾM; `signature=`, chuỗi ≥ 56, token TG) + LATCH từ lúc mở phiên; chỉ kéo file sạch; tính §5 ⇒ `canary_report_<TS>.txt` | chỉ đọc; tự che + TRƯỢT nếu chính báo cáo khớp mẫu bí mật |
| golive_canary_cleanup | `canary_cleanup.sh` | `cleanup` (0 vị thế/algo/lệnh toàn tài khoản) ⇒ đổi tên `run/canary` → `run/canary_done_<TS>` | YES=1; không đổi tên nếu còn JVM canary |

Chung (`canary_lib.sh`): md5 jar trên 242 = pin; từ chối nếu bot ở `LIVE_ADAPTER=live` hoặc có JVM canary khác; JVM chạy `nohup setsid`
(-Xmx384m) và script poll mỗi 15 s ⇒ mất ssh Oracle↔242 không giết JVM giữa bước tiền thật; tham số vào lệnh ssh đều qua regex;
log `~/claude_master/canary/<script>_<TS>.log`. test_fake242 mục 14: YES, md5, gate, dry < 5 ngày, LATCH, time_ok, chỉ-kiểm, chuỗi đủ thứ tự
(K6/K6b 2 JVM + đổi tên sổ), TRƯỢT dừng chuỗi + flatten, MỞ-5 cờ, lock, JVM canary khác, adapter live, report không chứa key + file rò bị
giữ lại trên 242, cleanup đổi tên.

## 6. Tiêu chí tổng §5 trong `canary_report.sh`

1 cid trùng (journal: cid được nhận > 1 lần, hoặc −4116) · 2/3 từ kết quả bước · 4 LATCH log bot từ lúc mở phiên · 5 max
`X-MBX-USED-WEIGHT-1M` < 1200 và 0 HTTP 429/418 (không có mẫu ⇒ TRƯỢT) · 6 bí mật (242 + log Oracle) · 7 K6b + K7b, số ms (B)/(A) · 8 độ trễ
(thông tin) · 9 chi phí ≤ 2 USDT · 10 dữ liệu §7 có mặt. Thiếu bước nào trong K0..K8/K6b/K7b ⇒ TRƯỢT.

## 7. Sửa trong lúc test vòng này (A1 lưu ý)

- K6: ảnh chụp 12 trường lưu dạng **chuỗi** (Gson đọc long 64-bit thành double ⇒ mất bit `doubleToLongBits`).
- K7b: chạy `rec.startup()` trước (chặn `STARTUP_RECON` toàn hệ của JVM mới làm symbol phụ bị chặn giả).
- Kiểm lại symbol mỗi bước chỉ theo luật **cấu trúc** (giá trượt sau K4 làm tick/giá vượt 0,01 % ⇒ TU_CHOI giả).
- tmb0 `Double` nullable; journal `sanitize` NaN/Inf; bỏ chuỗi Gson bị `NoSecretInClassesTest` bắt nhầm.

## 8. Điểm mở

1. **Chưa có `allOrders`** trong client ⇒ §5.1 đếm cid từ journal (+ queryOrder), không độc lập với log công cụ. A1/owner đối chiếu thêm trên
   web/allOrders, hoặc thêm endpoint (cần A1 delta).
2. **Phí bằng tài sản ngoài stable (BNB)** ⇒ K8 TRƯỢT theo thiết kế (sổ cái không quy đổi). Owner nên tắt "dùng BNB trả phí" ở tài khoản con.
3. **Quyền rút / IP restrict** (`apiRestrictions`, sapi) không đọc được bằng key futures ⇒ owner tự xác nhận khi tạo key (K0 ghi rõ).
4. **Tên file gate** `~/claude_master/deploy/gates/GOLIVE_GATE_CODE_V12.ok` + `GOLIVE_GATE_PROMO_V11.ok` là đề xuất của agent — MASTER tạo/đổi
   (biến `GATE_FILES`). Các điều kiện §2.3 khác (100 % `[LIVE-DRY]`, 0 exception adapter, UNKNOWN không giải thích) vẫn do MASTER/A1 xét
   qua file gate; script chỉ tự kiểm ngày, LATCH và `[C3-LIVE-ORDER]`.
5. K7 cắt kết nối **phía client** (đóng socket + chặn nối lại); K6 "kill" bằng `Runtime.halt(0)` (không shutdown hook) chứ không phải SIGKILL.
6. MIN-20: bước chờ stop mới NEW có thể ngủ tối đa 1 s (2 lần kiểm).
7. JVM canary −Xmx384m chạy cạnh bot dry trên 242: owner xem RAM trống trước phiên; `JAVA_242` mặc định `java` (phải cùng JDK bot).
8. Lặp lại rút gọn sau mỗi đổi jar (prereg §5): `canary_preflight.sh` + `CANARY_SEQ="K1 K2 K4 K6" YES=1 canary.sh`.
9. Canary chỉ chạy được khi jar 3 đã deploy dry trên 242 (deploy sau 2026-11-18) và dry đủ 5 ngày ⇒ sớm nhất ~11-23.
