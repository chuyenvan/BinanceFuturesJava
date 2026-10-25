# V12_ROUND2E — vòng 2e: MAJ-3 + cụm ma + nhãn adapter file latch + TZ hậu kiểm LATCH (A1_DELTA_2D @5c152489)

Branch `v1.2/c3-live` (worktree `~/claude_master/v12/c3live`), tiếp từ `d2a42596`. Agent v12exit (Claude Opus), 2026-10-25.
Báo cáo audit: `~/claude_master/v12/a1/docs/result/A1_DELTA_2D.md`; proof `docs/result/a1audit/2d/ProofFlat2.java` (bản chép: `round2e/ProofFlat2_A1.java.txt`).
Không push, không merge, không deploy, không gọi Binance, không đụng 242.

| commit | nội dung |
|---|---|
| `32d69c7e` | MAJ-3: `OwnStopGuard` = điểm DUY NHẤT huỷ stop `c3s-`; Reconciler/FillAccounting/Flattener/Trailing đi qua guard; cụm ma: nhắc 6 h + `Reconciler.ghostClear` qua file lệnh; test ProofFlat2 D/E |
| `d1b3004f` | ops: `c3live_ghost_clear.sh` (YES=1); hậu kiểm LATCH ép `TZ=Asia/Ho_Chi_Minh`; `test_fake242` 41/41 |
| `e86c1f11` | kill-switch: file latch gắn nhãn `adapter`; khác nhãn → GIỮ latch + WARN + Telegram hướng dẫn `killsw_reset.sh` |
| `de063042` | pin jar 2e trong `deploy_v12_dry.sh` |
| (commit docs) | tài liệu này + `docs/result/round2e/` |

## 0. Risk-first

1. **Stop `c3s-` bị GIỮ khi sàn chưa xác nhận phẳng → chặn TOÀN BỘ mở mới (UNKNOWN_POSITION)** cho tới khi cả positionRisk lẫn account báo phẳng và stop huỷ được.
   - Ca thường gặp: stream báo `pa=0` nhưng positionRisk REST trễ vài trăm ms → guard giữ stop + UNKNOWN; Reconciler đọc lại mỗi 30 s, huỷ stop, rồi gỡ chặn sau 2 lần đọc nhất quán (≈ 60–90 s chặn mở mới). Bảo thủ, có chủ đích.
   - UNKNOWN vẫn chặn toàn hệ thống (hành vi có sẵn từ C9), không chỉ symbol đó.
2. **`/fapi/v3/account` mảng `positions` vẫn CHƯA XÁC MINH với sàn thật** (như 2d). Nếu sàn không trả mảng → guard KHÔNG BAO GIỜ huỷ stop mồ côi (KEPT_READ_ERROR) và chặn mở mới khi có stop mồ côi. Fail-safe nhưng có thể kẹt; kiểm ở canary K0.
3. **Sàn có tự huỷ stop closePosition khi vị thế về 0 hay không: CHƯA XÁC MINH.** Nếu không, stop giữ lại trên symbol phẳng chỉ bị huỷ khi Reconciler xác nhận phẳng (vòng thử lại 30 s). UNKNOWN không gỡ khi `guard.hasKept(sym)` → không mở lại symbol đó trong lúc còn stop cũ.
4. **Hai đường huỷ KHÔNG qua kiểm vị thế (có chủ đích):** `cancelReplaced` (stop cũ vừa được stop mới đã lên sàn + thành active thay) và `cancelRetired` (DCA reset gỡ arm như sổ giấy). Cả hai chỉ chạy trên cụm sổ đang giữ.
5. **Margin cụm ma vẫn tính vào marginUsed/U** (không sửa — xem §3). Hướng sai là bảo thủ; owner gỡ bằng `c3live_ghost_clear.sh`.
6. **Flattener không còn huỷ stop KHÔNG phải của bot** khi chốt cụm (trước: huỷ mọi stop mở của symbol). Stop tay của owner được giữ nguyên.

## 1. Finding × fix × test

| mã | sửa | test | trạng thái |
|---|---|---|---|
| **MAJ-3** ca D (startup) | vòng stop mồ côi trong `Reconciler.startup` → `guard.cancelOwnStopGuarded`; giữ → `Report.orphanKept` + alert khởi động | `proofFlat2CaseD_startupKeepsOwnStopOfRealPositionMissingFromBook` | **ĐÃ SỬA** |
| **MAJ-3** ca E (hằng giờ) | `sweepOrphanStops` → guard | `proofFlat2CaseE_hourlySweepKeepsOwnStopOfForeignPosition` | **ĐÃ SỬA** |
| MAJ-3 mọi đường huỷ khác | grep `cancelStop(` trong `src/main`: chỉ còn `OwnStopGuard.doCancel` (ngoài impl gateway `C3LiveClient`, và `BinanceOrderTradingManager` cũ — không phải c3_live). FillAccounting.closedOnExchange, C3LiveFlattener.finalizeClosed, TrailingStopManager (orphan/DCA/promote) đều gọi guard | `streamFlatButRestStillHoldsKeepsStopUntilBothFlat`, `unknownNotReleasedWhileOwnStopStillKept`, `guardReadErrorKeepsStopThenRetriesAndReleases`, `orphanOwnStopCancelledWhenBothSourcesFlat`; test cũ Flattener/Trailing/FillAccounting vẫn xanh | ĐÃ SỬA |
| Cụm ma: nhắc 6 h | `FlatConfirm.GHOST_REMIND_MS`; Telegram lần đầu ngay + mỗi 6 h; nội dung chỉ lệnh `c3live_ghost_clear.sh SYM` | `ghostClusterReminderEverySixHours` | ĐÃ SỬA |
| Cụm ma: script owner | `ops/c3live/c3live_ghost_clear.sh SYMBOL` + `Reconciler.ghostClear` + runtime đọc `run/c3live_ghost_clear.req` | `ghostClearRefusesWithPositionAndClearsWhenFlat`; `test_fake242` #13 (5 mục) | ĐÃ SỬA |
| Cụm ma: margin | không sửa (§3) | — | GHI LÝ DO |
| File latch nhãn adapter | `persistLatch` ghi `adapter`; `loadLatch` khác nhãn + có latch/C2 → GIỮ + WARN + Telegram (cảnh báo phát sinh trước `setAlert` được gửi khi `setAlert`, chỉ c3_live); không có gì để giữ → INFO | `latchFromOtherAdapterKeptWithWarnUntilOwnerReset`, `untaggedEmptyLatchFileOnlyInfo` | ĐÃ SỬA |
| Hậu kiểm LATCH TZ | mốc start so sánh bằng `TZ=Asia/Ho_Chi_Minh date -d @$ST`; deploy in `tz_shell` + mốc +07 | `test_fake242` #10–#12 (daemon giả ghi log theo +07), #12 thêm check tz | ĐÃ SỬA |

### Chi tiết `OwnStopGuard.cancelOwnStopGuarded(sym, cid, why)`
Thứ tự kiểm:
1. `openStops(sym)` lỗi → **KEPT_READ_ERROR**; `cid` không còn mở → **GONE** (không gọi huỷ).
2. Sổ giữ cụm với stop active khác `cid` và stop active đó ĐANG MỞ trên sàn → huỷ (vẫn có bảo vệ).
3. `positions()` (positionRisk) lỗi → giữ.
4. `account().positions` lỗi / null → giữ.
5. Tổng `|amt|` của symbol trên một trong hai nguồn ≠ 0 → **KEPT_POSITION** (dùng `|amt|` để LONG+SHORT hedge không bù trừ thành "phẳng"); cả hai = 0 → huỷ.

Khi giữ:
- Sổ không giữ symbol → `unknownSink` (Reconciler.onUnknownPosition, không lấy khoá — xếp hàng, xả ở phương thức synchronized kế tiếp; tránh đảo thứ tự khoá FillAccounting ↔ Reconciler).
- Ghi vào danh sách `kept` (cid → sym). `Reconciler.checkPositions` → `retryKeptStops` (thưa ≥ 30 s) thử huỷ lại các stop giữ không còn được sổ tham chiếu. `unknownCheck` KHÔNG gỡ UNKNOWN cho symbol còn stop giữ.
- Telegram lần đầu ngay, nhắc lại mỗi 6 h/symbol.

Runtime dùng MỘT guard chung (`C3LiveRuntime` → `setStopGuard` cho Reconciler, FillAccounting, Flattener, Trailing; unknown → `rec::onUnknownPosition`).

FillAccounting.closedOnExchange: gom cid (active/pending/orphan + mọi `c3s-` đang mở) → `book.removeCluster` TRƯỚC → huỷ từng cid qua guard (sổ đã bỏ symbol → nếu giữ thì symbol vào UNKNOWN).

### Chi tiết ghost clear
- Owner (trên Oracle): `bash ~/claude_master/deploy/c3live_ghost_clear.sh XRPUSDT` = chỉ xem (ssh 242, in 5 dòng log liên quan). `YES=1 …` = ghi `run/c3live_ghost_clear.req` (atomic) rồi chờ `GHOST_WAIT` (30 s) đọc `run/c3live_ghost_clear.req.result`. Exit: 0 OK, 4 REFUSED, 5 bot chưa xử lý, 2 symbol sai, 1 ssh lỗi.
- Bot (opsLoop): đọc symbol → xoá file yêu cầu → `Reconciler.ghostClear(sym)`: symbol `[A-Z0-9]{2,30}`, sổ phải giữ cụm, positionRisk + account phải = 0 (lỗi/mảng null → REFUSED), huỷ `c3s-` đang mở qua guard (còn stop không huỷ được → REFUSED, giữ cụm), `removeCluster(sym, "GHOST_CLEAR_OWNER")`, Telegram. Ghi `"<ms> OK|REFUSED …"` vào `.result`.
- Script không gọi sàn, không đọc/in key; việc đọc vị thế/stop do chính jar đang chạy (client tài khoản con) làm.

## 2. Build / test / parity / jar

- Build: `mvn -o -q package -DskipTests=false` → **610 test, 0 fail, 0 error, 1 skip (`tests=610 fail=0 err=0 skip=1`)** (2d: 600). Tóm tắt: `round2e/surefire_summary.txt`.
- `test_fake242.sh`: **41/41 PASS** (`round2e/test_fake242_out.txt`).
- Parity 10-23 (cách A1: `drv.py`, mỗi lượt tự dựng cache), jar 2e vs tham chiếu dcae2e2b, md5 giải nén:

| file | 2e | tham chiếu | khớp |
|---|---|---|---|
| `out_BT` (1441 dòng) | `e0918a333a52be3aefe2a3b62a5ac8f4` | `e0918a333a52be3aefe2a3b62a5ac8f4` | ✅ |
| `out_NEW2` (1441 dòng) | `e0918a333a52be3aefe2a3b62a5ac8f4` | `e0918a333a52be3aefe2a3b62a5ac8f4` | ✅ |
| `fund_BT` (49204 dòng) | `a81b3b03915a44d418ee23488d71d226` | `a81b3b03915a44d418ee23488d71d226` | ✅ |
| `fund_NEW2` (49204 dòng) | `8dea3f700aaddfd6abad961af1c65ea7` | `8dea3f700aaddfd6abad961af1c65ea7` | ✅ |
| ctl_gate / ctl_fund | 1440 / 49203 dòng chung, only_ref = only_new = 0 | như 2d (`cand`, `f3` < 1.0 ở ctl_fund có sẵn từ 2d) | ✅ |
| strace AF_INET non-loopback connect | 0 (BT + 3 seg NEW2) | 0 | ✅ |

  Chi tiết `round2e/r2e_compare.json`.
- Jar dry 2e: `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_2e`, md5 **`989d235450b13eec0ce7df590ce18533`**, 100 257 205 B. Pin `NJ`/`NJ_MD5` trong `ops/c3live/deploy_v12_dry.sh`. `KILLSW_MD5` giữ `6f8d8348…` (killsw_reset.sh không đổi). Jar 2d đã xoá.

## 3. Margin cụm ma — đánh giá

Cụm ma (sổ giữ, vị thế thật đã phẳng, còn stop `c3s-` NEW) vẫn được tính vào marginUsed/U của sổ. **Không sửa**:
- Loại cụm ma khỏi U phải đụng đường sizing/throttle dùng chung với logic quyết định (rủi ro lệch parity / quyết định) để xử lý một ca hiếm.
- Hướng sai là bảo thủ: U cao hơn thật → throttle chặt hơn, không vượt rủi ro.
- Có đường gỡ nhanh, an toàn: Telegram nhắc mỗi 6 h + `c3live_ghost_clear.sh` (bot tự kiểm cả hai nguồn = 0 trước khi gỡ).

## 4. Còn mở

1. `/fapi/v3/account` `positions` + sàn có tự huỷ stop closePosition khi phẳng: CHƯA XÁC MINH → kiểm ở canary K0.
2. UNKNOWN chặn toàn hệ thống (không chỉ symbol) — giữ như thiết kế C9.
3. MIN-9, symbolConfig, manage-only chưa có test runtime (như 2d).
4. Chưa có script chuyển dry → canary (khi viết: reset latch có chủ đích; nay file latch khác nhãn được giữ + cảnh báo thay vì âm thầm mang sang).
5. Stop `c3s-` lạ trên cụm sổ ĐANG GIỮ, không phải stop active, trong khi stop active không mở → giữ (KEPT_POSITION) + Telegram 6 h; khi trailing có stop active mới đang mở, lượt quét hằng giờ sẽ huỷ nó (nhánh "bị thay").
6. Hedge mode: guard dùng `|amt|`, nhưng mock chỉ có 1 vị thế/symbol nên chưa có test LONG+SHORT riêng (bot chạy one-way, hedge `dualSidePosition=true` bị `AccountModeGuard` chặn).
