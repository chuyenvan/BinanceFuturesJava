# ROUND3I — rate guard canary vs tải IP LEGACY (phiên thật 3h TRƯỢT trước SETUP/K0)

Branch `v1.2/c3-live`, trên `c0f06c6d` (3h). Chỉ code + test + script + pin; không gọi Binance, không đụng 242, không đụng `~/claude_master/canary_3h`, không push.

## Bằng chứng (Oracle, chỉ đọc)
`~/claude_master/canary/early_all_20261028_051057.log`: 05:11:42 `keycheck TRUOT | GatewayException: rate guard: het ngan sach, can cho 15660 ms > han 2000 ms` ⇒ script DỪNG ở "chờ khung giờ (SETUP/K0)". 05:11:59 keycheck lại: ĐẠT (tài khoản chính, LEGACY pos 44, phạm vi canary phẳng).
Nguyên nhân: guard làn thường so header **cả IP** `X-MBX-USED-WEIGHT-1M` (chung LEGACY, burst REST quanh giây :30, ~1300/phút) với ngân sách 50 % = 1200; keycheck chạy trên client thô (không qua `CanaryGateway`, không thử lại) ⇒ 1 lần từ chối = cả lệnh một-lần DỪNG. §ADD-4 I đã định nghĩa lại tiêu chí 5 là weight canary tự gọi, nhưng ngưỡng guard chưa theo.

## Yêu cầu → sửa → test
| # | yêu cầu | sửa | test |
|---|---|---|---|
| 1 | ngưỡng nhận call thường: IP + cost > 1800 mới chờ/từ chối; cấu hình được; riêng canary ≤ 600 | `RateGuard.CanaryPolicy` (CHỈ JVM canary, `C3LiveCanary`; `null` = hành vi cũ cho c3_live chính): header IP cùng phút + cost > `ipAdmitCap` ⇒ chờ sang phút mới; weight canary tự gọi (cửa sổ trượt 60 s, gồm cả làn khẩn cấp) + cost > `ownCap` 600 ⇒ chờ. `CanaryLimits.IP_WEIGHT_ADMIT_DEFAULT = 1800`, `IP_WEIGHT_ADMIT_MAX = 1920`, `OWN_WEIGHT_1M_CAP = 600`; env `CANARY_IP_WEIGHT_CAP` (không cần file gate) qua whitelist `env -i` của `cl_run` (sai định dạng ⇒ script DỪNG; JVM: rỗng/sai/≤ 0 ⇒ 1800, > 1920 ⇒ 1920). Làn khẩn cấp GIỮ NGUYÊN | `RateGuardTest.i3KeycheckAtSecond30WithIpHeader1494WaitsAndSucceedsNeverAboveCap` (tái hiện 3h: chính sách cũ từ chối; 3i: ngủ tới :41, 7 call keycheck đều IP + cost ≤ 1800, 0 từ chối); `i3OwnWeightCap600`; `i3NoPolicyKeepsOldBehaviour`; `CanaryGuardTest.i3IpWeightCapEnvParsing`; fake242 20c |
| 2 | call đọc bị từ chối: chờ sang phút mới (≤ 61 s, Retry-After + 1 s) tối đa 2 lần; ghi giữ runPre 3h | `RateGuard.acquire(.., read)`: `C3LiveClient` báo GET = đọc; đọc quá `maxWait` ⇒ ngủ `cần chờ + 1 s` (≤ 61 s) tối đa 2 lần rồi lỗi sạch (`retryAfter 0` ⇒ lớp trên không chờ thêm, tổng ≤ 2). GET lồng trong lệnh ghi (đồng bộ giờ) = không chờ (kiểm trước ghi → gửi liền nhau). `CanaryGateway.call`: đọc ≤ 2 lần `GUARD_WAIT_RETRY` (đường mock / lỗi khác RateGuard); ghi: 1 lần thử lại, `runPre` chạy lại trước mỗi lần (3h) | `i3ReadWithIpHeader2300WaitsAtMostTwiceThenFailsCleanly` (2 lần chờ ≤ 61 s, lỗi RATE_LIMIT, 0 gửi; ghi lỗi ngay kèm retryAfter); `i3ReadRefusedOnceSucceedsAfterMinuteRolls`; `CanaryGuardTest.i3ReadRefusedByGuardIsWaitedAtMostTwice` |
| 3 | tránh burst: call thường ở giây [27, 40] ngủ tới :41 | **Heuristic** gắn với v_t_m `TickerIngestor2AerospikeNew` chốt nến quanh :30 (LEGACY gọi REST dồn dập ngay sau). Đọc: trong `RateGuard` trước khi gửi. Ghi: `CanaryGateway.burstWait` TRƯỚC kiểm trước ghi (không chen giữa kiểm và gửi). KHÔNG áp dụng: làn khẩn cấp, phạm vi `RateGuard.Urgent` (stop bảo vệ sau khớp). Giây theo đồng hồ máy chạy JVM (242, cùng máy LEGACY) | `i3BurstWindowSleepSkippedOnEmergencyLaneAndUrgentAndWrites`; `CanaryGuardTest.i3WriteBurstWindowSleepsBeforePreCheckExceptEmergencyAndUrgent` (BURST_WAIT trước CALL_R đầu tiên) |
| 4 | stop bảo vệ sau lệnh mở: khớp → stop XÁC NHẬN ≤ 61 s; không thì đóng phần canary qua làn khẩn cấp, TRƯỢT (A1 3h MINOR-1) | `protect(sym, deadline)`: hạn = mốc gửi THẬT lệnh mở (`CanaryGateway.firstSentMs`, ≤ lúc khớp) + `CanaryLimits.PROTECT_MAX_MS` 61 s. Đặt + xác nhận (đọc algo) trong `RateGuard.urgent(hạn)`: không ngủ burst; mọi lần chờ guard (`RateGuard`, `runPre`, thử lại trong `call`) phải xong trước hạn, không thì lỗi ngay (`GUARD_DEADLINE`). Quá hạn / không xác nhận được / đọc algo lỗi ⇒ `PROTECT_FAIL` ⇒ `closeCluster` trong làn khẩn cấp (chỉ phần canary, `min(sàn, phần c3)`) ⇒ TRƯỢT | `CanaryEngineTest.i3ProtectiveStopNotPlaceableWithin61sFlattensCanaryQtyOnly` (stop luôn bị guard từ chối, REST 2 s: GUARD_DEADLINE, bán bắt đầu 2 s sau lệnh mở ≤ 61 s, trong làn khẩn cấp; MAIN về 0; LEGACY C05USDT 7 nguyên, 0 lệnh trên symbol LEGACY); `CanaryGuardTest.i3UrgentDeadlineStopsGuardWaitsForStop`; `RateGuardTest.i3UrgentDeadlineNeverWaitedPast` |
| 5 | keycheck / K0 / pick / SETUP / chờ khung giờ qua mục 2; lỗi guard tạm thời khi chờ không dừng cả lệnh | JVM canary (mọi lệnh, kể cả keycheck trên client thô) dùng RateGuard chính sách canary ⇒ mọi call đọc theo mục 2. `canary_early_all.sh`: `flat_poll` — keycheck không đọc được ⇒ đếm liên tiếp, thử lại ở lần poll sau, KHÔNG qua khung giờ khi chưa đọc được; DỪNG khi 10 lần liên tiếp; đọc được mà không phẳng ⇒ DỪNG như cũ. (Kiểm "trước K0" vẫn `must_flat`: chỉ dựa mục 2 trong JVM) | fake242 20a (lỗi 2 lần ⇒ thử lại, phiên ĐẠT), 20b (lỗi liên tiếp ⇒ DỪNG đúng lần 10, không preflight/setup, Telegram LOI) |
| 6 | test mock | như trên; fake242 thêm mục 20 (4 kiểm) | — |

## Kết quả
- `mvn -o package -DskipTests=false`: **773 test, 0 fail, 0 error, 1 skip** (3h: 759; +7 RateGuardTest, +4 CanaryGuardTest, +1 CanaryEngineTest `i3…` ×3 lớp kế thừa).
- `test_fake242.sh` (bản sao ops `~/c3e_patch/arch5`): **TEST PASS 147/147** (chạy 05:36–05:48, trong khung giờ nên 2 kiểm "ngoài giờ" tự bỏ qua: 143 + 4 kiểm mục 20; 3h đo 145 ngoài khung).
- Jar `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3i`, md5 **`b6de7ddbcf661994a0d926a94d16b176`**, pin `canary_lib.sh`; `deploy_v12_dry.sh` giữ 3d. Kiểm bí mật jar (chỉ đếm): giống 3h trừ +2 class (`RateGuard$CanaryPolicy`, `RateGuard$Urgent`).

## Owner (sau audit A1)
```
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_set_key.sh
CANARY_RESET=1 bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_all.sh
```
Tuỳ chọn hạ ngưỡng IP (không cần file gate): `CANARY_IP_WEIGHT_CAP=1600 CANARY_RESET=1 bash …/canary_early_all.sh`. Không nâng trần lỗ nào; trần cộng dồn engine vẫn 4 USDT.

## Còn mở (A1 kiểm phiên thật)
1. Cửa sổ burst [27, 40] là heuristic theo lịch v_t_m; LEGACY đổi lịch ⇒ chỉ còn ngưỡng 1800 bảo vệ (header là số của request TRƯỚC, LEGACY có thể dồn thêm giữa 2 request).
2. Header IP chỉ biết qua response của chính canary: sang phút mới guard nhận call đầu tiên (header cũ hết hiệu lực) — đúng với cửa sổ phút cố định của Binance.
3. Đọc chờ tối đa 2 × 61 s / call ⇒ 1 lệnh keycheck có thể kéo ~2 phút khi IP bão hoà lâu; `STEP_MAX_S` 7200 đủ.
4. Hạn 61 s tính từ trước khi gửi lệnh mở (chặt hơn lúc khớp); MO-5 (timeout tiêm) + cửa sổ an toàn executor tiêu một phần hạn.
