# ROUND3F — canary-early trên TÀI KHOẢN CHÍNH (prereg §ADD-4)

Branch `v1.2/c3-live`, trên `4e0745be` (3e). Chỉ code + test + script; không gọi Binance, không đụng 242, không push.
Prereg §ADD-4 commit riêng TRƯỚC code: `ef7c6e10` (nguyên văn MASTER 2026-10-27).

## 1. Thiết kế (một câu mỗi lớp)
| lớp | §ADD-4 | cách làm |
|---|---|---|
| `CanaryGateway` (lớp cứng) | A, C, E, F | **view đọc của lớp c3_live chỉ 2 symbol canary** (`positions()`, `account().positions`, `openOrders/openStops(null)` = gọi theo từng symbol canary); đọc toàn tài khoản chỉ qua `positionsAll/openOrdersAll/openStopsAll` (CHỈ ĐỌC, chỉ engine dùng cho K0/cleanup). Mọi lệnh ghi: symbol canary **và** cid canary (`c3-` mở, `c3x-` đóng, `c3s-` stop/huỷ stop); `setDualSidePosition` luôn từ chối; `setLeverage/setMarginType` chỉ khi symbol 0 vị thế + 0 lệnh/algo ngoài canary; lệnh mở bị từ chối nếu symbol có lệnh/algo ngoài canary hoặc vị thế sàn > ledger canary |
| stream (`CanaryEngine.scopeFilter`) | A | sự kiện ORDER/ALGO/ACCOUNT_CONFIG của symbol ngoài canary bị bỏ trước lớp c3_live (journal gọn `LEGACY_EVENT`); ACCOUNT_UPDATE chỉ giữ vị thế 2 symbol canary; lệnh không cid canary trên symbol canary ⇒ nghi vấn ⇒ kiểm phạm vi ngay |
| ledger canary (`CanaryState.canaryQty`) | C, G | + khớp lệnh `c3-`, − khớp `c3x-` (response / queryOrder / stream z, đếm theo cid không trùng, qua JVM); sàn < ledger 2 lần đọc cách 3 s ⇒ co lại (stop kích) |
| `enforceScope` (đầu mỗi bước, SETUP, mỗi 30 s / ngay khi nghi vấn) | C | vị thế sàn > ledger (2 lần đọc) hoặc âm ⇒ **TRƯỢT-ĐỎ**: ghi `state.red` + `aborted`, huỷ stop `c3s-` CỦA CANARY trên symbol đó (stop closePosition/qty sẽ đóng cả phần LEGACY), KHÔNG đóng, Telegram, mọi bước sau TỪ CHỐI, flatten bỏ qua symbol đó. Lệnh/algo ngoài canary (chưa lẫn) ⇒ đóng phần canary reduce-only (`min(sàn, ledger)`), TRƯỢT + dừng |
| K0 | B, D, E, H | đọc toàn tài khoản 1 lần: loại symbol có vị thế/lệnh/algo + `legacy_symbols.csv` (userTrades 7 ngày BỎ — ~5 weight × symbol, ghi rõ `pick.legacySource`); ảnh chụp LEGACY (vị thế qty@entry, lệnh/algo); bỏ kiểm tmb tuyệt đối, kiểm `availableBalance ≥ 50`; dualSide chỉ đọc (hedge ⇒ TRƯỢT), multiAssets chỉ ghi |
| loss | G | `lossNow` = phí − PnL đã chốt (stream 2 symbol canary) + lỗ chưa chốt vị thế canary; không dùng tmb, bỏ funding (số dư toàn tài khoản) |
| cleanup | C, D | 2 symbol canary 0/0/0; 0 lệnh/algo cid canary ngoài phạm vi; 0 TRƯỢT-ĐỎ; journal phiên 0 lệnh ghi ngoài phạm vi; ảnh chụp LEGACY cuối vs K0 (chỉ đếm) ⇒ `legacy.summary` |
| K8 | G, H | lệch equity so tmb: chỉ ghi (KHONG_AP), giữ kiểm chi phí canary |
| guard client (`CanaryGateway.call`) | I | call thường bị guard client từ chối (IP nặng, chưa gửi) ⇒ chờ ≤ 61 s sang phút sau, thử lại 1 lần (`GUARD_WAIT_RETRY`); lane khẩn cấp 3e giữ nguyên |
| `C3LiveFlattener` (kill-switch production) | — | `step()` FLATTEN và `closeCluster` chạy trong lane khẩn cấp; khối lượng đóng = `min(vị thế sàn, phần c3 = confirmed − exit)` (không bao giờ đóng phần ngoài c3) |
| `AccountModeGuard` | E | `globalPolicy(requireMultiAssets, fixDualSide)`; canary dùng `(false, false)`: không đọc multiAssets, không gọi đổi dualSide |

## 2. Call site toàn tài khoản (cancelAll / closePosition / openOrders / openAlgoOrders) — HEAD sau 3f
Không có `cancelAll` nào trong `c3live/` (grep 0). Mọi lệnh ghi của canary đi qua `CanaryGateway` (symbol + cid canary).
| file:line | gọi | canary thấy gì / guard |
|---|---|---|
| `canary/CanaryGateway.java:543-552` | `openOrders(sym/null)` | view: chỉ 2 symbol canary (gọi theo symbol); `openOrdersAll()` CHỈ ĐỌC |
| `canary/CanaryGateway.java:559-568` | `openStops(sym/null)` (openAlgoOrders) | như trên; `openStopsAll()` CHỈ ĐỌC |
| `canary/CanaryGateway.java:267-268` | `d.openOrders/openStops(sym)` | đọc lệnh/algo ngoài canary trên symbol canary (guard mở lệnh / F) |
| `canary/CanaryGateway.java:449, 491, 513, 520` | newMarketOrder / newStopMarket / cancelOrder / cancelStop | symbol canary + cid `c3-`/`c3x-`/`c3s-`, nếu không ⇒ GuardException, không gửi |
| `canary/CanaryGateway.java:609, 626, 634` | setDualSidePosition / setLeverage / setMarginType | dual: luôn từ chối; leverage/margin: chỉ symbol canary sạch (F) |
| `client/C3LiveClient.java:184` | `closePosition=true` (algo STOP) | chỉ tạo qua `TrailingStopManager.java:316` → gateway (symbol canary, `c3s-`); khi lẫn LEGACY ⇒ TRƯỢT-ĐỎ huỷ stop này (`CanaryEngine.markRed` :1138) |
| `canary/CanaryEngine.java:1071-1072, 1152` | openOrders/openStops(s) | scopeProblem / markRed — symbol canary |
| `canary/CanaryEngine.java:1383-1385` (K0), `2336-2338` (cleanup) | positionsAll / openOrdersAll / openStopsAll | CHỈ ĐỌC: chọn symbol + ảnh chụp LEGACY + cid canary ngoài phạm vi |
| `canary/CanaryEngine.java:1460-1461, 2238-2239, 2334-2335, 661, 1941, 1984` | openOrders/openStops(null/s) | view 2 symbol canary |
| `canary/C3LiveCanary.java:270, 273` | client thẳng `openOrders/openStops(null)` (keycheck) | CHỈ ĐỌC; đếm theo phạm vi canary, LEGACY chỉ đếm |
| `recon/Reconciler.java:299, 728, 819` | openStops(null/sym) | qua view ⇒ chỉ 2 symbol canary; huỷ stop chỉ qua OwnStopGuard (`c3s-`) |
| `recon/FlatConfirm.java:128, 160`, `recon/OwnStopGuard.java:72, 133`, `fill/FillAccounting.java:262`, `exit/TrailingStopManager.java:431`, `risk/C3LiveFlattener.java:251` | openOrders/openStops(sym), cancelStop | theo symbol của sổ c3 (chỉ symbol canary) ; cancelStop chỉ `c3s-` |
| `guard/AccountModeGuard.java:171-176` | setDualSidePosition | canary: `fixDualSide=false` ⇒ không gọi; gateway cũng từ chối |
| `risk/C3LiveFlattener.java:98, 137, 154` | đóng cụm | lane khẩn cấp; qty ≤ phần c3 |

Ghi chú production c3_live (ngoài canary): `C3LiveRuntime` vẫn dùng client thẳng (không có view scoped) — trước khi c3 live chạy trên tài khoản chính cần lớp phạm vi tương tự (theo sổ c3 + cid) — A1/MASTER.

## 3. Script
- `canary_set_key.sh` (MỚI, owner 1 lệnh trên Oracle): YES 1 lần, `read -s` key/secret, ssh stdin tới 242 (như `c3live_keys_install.sh`), backup bản cũ 600, ghi 600/700, không in key; keycheck chỉ đọc nếu jar pin đã có trên 242.
- `canary_lib.sh`: `cl_flat_read` hiểu `legacy=` (chỉ đếm); pin jar 3f.
- `canary_early_all.sh`: bỏ kiểm tmb [9500, 12000] (chỉ ghi vào file tóm tắt); "phẳng" = phạm vi canary; Telegram KHÔNG có số dư (tmb/USDT/assets chỉ trong file tóm tắt), thêm dòng LEGACY (chỉ đếm); flatten trả TRƯỢT-ĐỎ ⇒ báo MASTER, không khuyên chạy flatten.
- `canary_early_run.sh`: cleanup TRƯỚC report (report đọc được ảnh chụp LEGACY cuối); dòng `LEGACY ...` đầu file kết quả; TRƯỢT-ĐỎ ⇒ không khuyên flatten.
- `canary_report.sh`: tiêu chí 5 = `ownWeight1mMax < 600` + 0 HTTP 429/418 (header IP chỉ ghi); tiêu chí 11 (early) = 0 lệnh canary ngoài phạm vi + LEGACY summary + 0 TRƯỢT-ĐỎ.

## 4. Test
- `mvn -o -q package -DskipTests=false`: **667 test, 0 fail, 0 error, 1 skip** (3e: 658; +5 CanaryEngineTest, +2 CanaryGuardTest, +2 C3LiveFlattenerTest; sửa 6 test cũ theo §ADD-4: LEGACY symbol khác ⇒ K1 ĐẠT; lỗ = PnL canary (không dùng tmb); K0 bỏ CANARY_EXPECT_TMB, kiểm availableBalance; guard từ chối ⇒ thử lại phút sau).
- Mới: `legacyElsewhereUntouchedAndPickExcludesLegacySymbols` (LEGACY vị thế/lệnh/algo 3 symbol khác ⇒ chọn C02/C03, K1+flatten+cleanup ĐẠT, LEGACY nguyên vẹn, 0 lệnh ghi trên symbol LEGACY, 0 setDualSide), `legacyFillOnMainBetweenStepsIsRedAndNothingIsClosed`, `legacyFillOnMainMidStepIsRedAndNothingIsClosed` (LEGACY vào S_main giữa K4 ⇒ TRƯỢT-ĐỎ < 5', không đóng), `legacyRestingOrderOnCanarySymbolClosesCanaryPartOnly`, `accountLevelSettingsAreOnlyRead`; CanaryGuardTest `nonCanaryCidAndAccountLevelWritesRefused`, `readViewIsScopedToCanarySymbols`; C3LiveFlattenerTest `killSwitchFlattenAndCloseClusterUseEmergencyLane`, `closeNeverSellsMoreThanC3Qty`.
- `test_fake242.sh` tren ban sao ops (6efcf094 + chk 14d sua theo tieu chi 5 moi): **TEST PASS 139/139** (134 cu + muc 17 cap nhat §ADD-4 + 4 moi muc 18 canary_set_key.sh + 1 Telegram khong so du).

## 5. Jar
`~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3f`, md5 **`d2f1b52c348b57939efc7e0165b9fdee`**, pin `canary_lib.sh`
(`canary_early_all.sh` dùng pin lib). `deploy_v12_dry.sh` GIỮ 3d (chưa parity c3_shadow). Kiểm bí mật jar (`nup3_wk/jar_sec_check.py`, chỉ đếm):
giống jar 3d trừ +2 class (`RateGuard$Lane`, `CanaryGateway$ExecListener`); `ok=false` có sẵn từ trước (PrivateConfig LEGACY untracked trên đĩa).

## 6. A1 kiểm trên phiên thật
1. Lệnh khớp từ algo stop kích (K4) mang cid gì trong ORDER_TRADE_UPDATE — chỉ ảnh hưởng nghi vấn (kiểm thêm), không tạo TRƯỢT-ĐỎ.
2. Key mới đúng tài khoản chính: keycheck `legacy=pos:N` ≈ 44; dualSide=false; quyền rút TẮT + IP 242 (owner xác nhận web).
3. `pick.legacyBusy` / symbol chọn KHÔNG nằm trong 44 symbol LEGACY; `legacy.summary` cuối phiên; tiêu chí 5 `ownWeight1mMax`.
4. Nếu LEGACY mở trên S_main giữa 2 JVM (khoảng ≤ 20 s) ⇒ bước kế TRƯỢT-ĐỎ — xác nhận không có lệnh đóng nào, stop c3s- bị huỷ.
5. CANARY_RESET trên phiên cũ (ZEC/Q tài khoản con): cleanup coi là "trước 3f" — chỉ kiểm cid canary, không quy vị thế LEGACY trên ZEC/Q cho canary.
6. multiAssets tài khoản chính chỉ ghi (E kỳ vọng one-way) — MASTER xác nhận.

## 7. Owner (sau audit), theo thứ tự
```
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_set_key.sh
CANARY_RESET=1 bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_all.sh
```
(`CANARY_RESET=1` vì phiên cũ 10-27 có bước giao dịch trên tài khoản con.)
