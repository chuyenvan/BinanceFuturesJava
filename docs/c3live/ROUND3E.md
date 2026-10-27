# ROUND3E — canary-early sau phiên 2026-10-27 22:17 (K2 TRƯỢT, FLATTEN TRƯỢT, weight 1494)

Branch `v1.2/c3-live`, trên `668c23e8` (3d, chưa audit). Chỉ code + test + script; không gọi Binance, không đụng 242, không push.
Bằng chứng: `~/claude_master/canary/report_20261027_221907/files/` (journal K1/K2/flatten + `canary_jvm.log` đã kéo về Oracle).

## 1. Nguyên nhân gốc

### 1.1 K2: `queryStop b/d = KHONG CO` — đọc-sau-ghi trễ của `GET /fapi/v1/algoOrder`
| ts (ms, K2 journal) | sự kiện |
|---|---|
| …299752 | POST algoOrder b `c3s-ZECUSDT-29885238-3` → algoStatus NEW (ALGO_UPDATE NEW tới trước đó 17 ms) |
| …299944 | `openAlgoOrders?symbol` đã thấy b NEW (+192 ms) |
| …300037 | `GET algoOrder?clientAlgoId=b` → không có (`present:false`, +285 ms) |
| …300953 / …301141 / …301232 | d: đặt NEW / openAlgoOrders thấy / query không có (+279 ms) |
| …299252 | a `c3s-ZECUSDT-29885237-1` (đặt 27 s trước, ở JVM K1) → query **NEW**, cùng endpoint, cùng tham số |

Loại trừ: sai id/tham số (a và b/d cùng `C3LiveClient.queryStop` — chỉ `clientAlgoId`, cid khớp `caid` của ALGO_UPDATE);
sai endpoint (a tìm thấy qua chính endpoint đó); đọc sai trường (a đọc `algoStatus`=NEW đúng). Còn lại: query endpoint trễ
so với list mở (~0,3 s). `present:false` = `UNKNOWN_ORDER` (-2011/-2013) bị nuốt thành `Optional.empty()` — 3e ghi http/code vào log.

**Sửa** (`CanaryEngine.queryStopSettled`): chỉ lặp khi sàn báo KHÔNG CÓ; lùi 250/500/1000/1250 ms (tổng ≤ 3 s, 5 lần đọc);
journal `QUERY_STOP_RETRY` mỗi lần + `QUERY_STOP_DONE`; data `<a|b|d>.queryStopAttempts`, `.queryStopMs`.
Có trạng thái khác NEW ⇒ trả ngay (không lặp). Tiêu chí K2 **không đổi**: phải CÓ + NEW + response NEW.

### 1.2 FLATTEN: chính rate guard của ta từ chối
`RateGuard.waitNeeded`: số sàn báo cùng phút + weight > ngân sách 1200 ⇒ chờ hết phút; flatten (22:18:46, giây :46) cần chờ
12 801 ms > `rateMaxWaitMs` 2000 ⇒ `RATE_LIMIT notExecuted` ngay ở `positions()` đầu tiên. Không có ngoại lệ cho flatten.

**Sửa**: `RateGuard.Lane` (theo luồng, `try (RateGuard.Lane l = RateGuard.emergencyLane())`): bỏ qua ngân sách 50 % và số IP;
vẫn chờ khi sàn chặn 429/418 (≤ 125 s; dài hơn ⇒ lỗi do sàn) và khi số sàn báo + call > 100 % giới hạn sàn (chờ sang phút).
Dùng ở `flatten()`, `cleanupCheck()`, `flattenAll` (tự flatten bước TRƯỢT / trần lỗ), đóng khi `PROTECT_FAIL`.
`flatten()` đọc `foreignExposure` (chỉ thông tin, 85 weight) SAU khi đóng.

### 1.3 Weight 1494: KHÔNG do canary — LEGACY kline ingest dùng chung IP 242
| JVM | weight canary tự gọi (ước tính W_*) | header tại call đầu | phần ngoài canary |
|---|---|---|---|
| K1 22:17:38–53 | 217 | 841 (giây :38) | ≥ 836 trước khi K1 gọi |
| K2 22:18:16–23 | 181 | 491 (giây :16) | 486 trước K2; +≈770 trong :24–:46 (K2 đã thoát) |
| flatten 22:18:46 | 1 | 1494 | ≥ 1312 trong phút :18 |
| K0 20:26 / SETUP 20:25 | 215 / 167 | 101 / 77 (giây :27) | ~100 |

`TickerIngestor2AerospikeNew` (v_t_m): REST settle mỗi phút giây :30 cho MỌI symbol (`KLINE_SETTLE_SEC=30`, limit 3, ~500+ weight)
+ REST sớm giây 2–4. Canary không thể làm IP < 1200 trong phút LEGACY nặng. Mẫu K0 cũ (34/124/39) đều lấy ở giây :27–:30, trước pass settle.

Trước/sau 3e (canary tự gọi, mỗi JVM): K0 ~215, SETUP ~167, K1 ~217, K2 ~181 (+ tối đa 4 query × 3 nhãn khi trễ), flatten ~150, cleanup ~85
— **không đổi đáng kể**: phần lớn là kiểm an toàn (openOrders/openAlgoOrders toàn tài khoản 80/bước, chế độ tài khoản 60/lệnh mở),
không cắt. 3e thêm `wOwn` trong journal, `ownWeight1mMax` trong data bước, dòng thông tin ở tiêu chí 5 (verdict giữ nguyên).

## 2. Thay đổi
| file | nội dung |
|---|---|
| `rate/RateGuard.java` | `Lane`, `acquireEmergency`, `emergencyWait`, đếm `emergencyCalls/OverBudget/Blocked` |
| `canary/CanaryEngine.java` | `queryStopSettled`, lane ở flatten/cleanup/flattenAll/PROTECT_FAIL, `Deps.rateGuard`, data `rate.*`, `ownWeight1mMax` |
| `canary/CanaryGateway.java` | `estWeight`, `wOwn`, `maxOwnWeight1m` |
| `client/C3LiveClient.java` | queryStop KHÔNG CÓ ⇒ log INFO http/code |
| `canary/C3LiveCanary.java` | `d.rateGuard = rg` |
| `ops/c3live/canary/canary_report.sh` | tiêu chí 5: thêm thông tin canary vs IP ngoài canary (verdict không đổi) |
| `ops/c3live/canary/canary_lib.sh` | pin jar 3e |

Giữ nguyên: trần 20/25/40 USDT, trần lỗ 2, cộng dồn 4, công thức stop bảo vệ, md5/PID v_t_m, RAM, env cấm, FORCE_TIME.

## 3. Test
- `mvn -o -q package -DskipTests=false`: **658 test, 0 fail, 0 error, 1 skip** (3d: 648; +5 RateGuardTest, +5 CanaryEngineTest).
- Mới: `emergencyLaneRunsWhenServerWeightExceedsBudget` (header 1494 ⇒ thường bị chặn, khẩn cấp 21 call không chờ),
  `emergencyLaneRunsWhenInternalBudgetExhausted`, `emergencyLaneStillBacksOffOnExchange429And418`,
  `emergencyLaneWaitsForNextMinuteOnlyAtFullExchangeLimit`, `emergencyLaneIsPerThreadAndNested`;
  `emergencyFlattenNotBlockedByOwnRateGuard` (K1 mở, guard hết ngân sách ⇒ flatten ĐẠT, vị thế 0, 0 stop),
  `stepRefusedByRateGuardStillAutoFlattens`, `k2QueryStopReadAfterWriteLagRetriedWithinBound` (trễ 2 lần ⇒ ĐẠT, 3 lần đọc),
  `k2QueryStopStillMissingAfterBoundFails` (không bao giờ thấy ⇒ TRƯỢT, 5 lần đọc, đã đóng), `queryStopBackoffSumsToBound`.
- `test_fake242.sh` tren ban sao `git archive HEAD ops` (894bbf75): **TEST PASS 134/134**.

## 4. Jar
`~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3e`, md5 **`f3fd2cc3d048122f79306e251d916b9b`**, pin `canary_lib.sh`
(`canary_early_all.sh` dùng pin của lib). `deploy_v12_dry.sh` GIỮ 3d (jar 3e chưa chạy parity c3_shadow).
Kiểm bí mật jar (`nup3_wk/jar_sec_check.py`, chỉ đếm): kết quả **giống hệt jar 3d** trừ +1 class (`RateGuard$Lane`);
cờ `ok=false` có sẵn từ trước (PrivateConfig/ClientSingleton của LEGACY, file untracked trên đĩa) — không do 3e.

## 5. Còn mở (A1 / MASTER)
1. Tiêu chí 5 (header IP < 1200) không kiểm soát được bằng code canary khi LEGACY settle nặng — MASTER quyết (addendum: đo
   phần canary tự gọi, hoặc giờ LEGACY nhẹ, …). Hệ quả chức năng: call thường của canary sau giây :30 phút nặng bị guard từ chối
   (`LIVE_C3_RATE_MAX_WAIT_MS` 2000) ⇒ bước có thể TRƯỢT ngẫu nhiên (an toàn: tự flatten nay qua lane khẩn cấp).
2. Retry K2 chỉ chứng minh offline; phiên thật cần thấy `QUERY_STOP_DONE attempts>1 present=true` + log code sàn.
3. `DELETE /fapi/v1/algoOrder` trả header weight 1/2/3 (journal K2) ⇒ `RateGuard.serverWeight` bị ghi đè thấp tạm thời.
4. Production `C3LiveFlattener` (kill-switch) chưa dùng lane khẩn cấp — cùng rủi ro khi LEGACY nặng.
5. Jar đổi ⇒ K0 đầu tiên với jar 3e chạy đủ 65' (không dùng lại keepAlive của jar 3c/3d).

## 6. Owner (sau audit)
```
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_all.sh
```
