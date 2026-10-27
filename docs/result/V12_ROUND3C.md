# V12_ROUND3C — sửa MAJ-C1 (trần lỗ giữa 2 JVM) + MIN-C2/C3/C4/C6 sau A1 `audit/a1@9d60cd5b`

Branch `v1.2/c3-live`, agent v12exit, 2026-10-27. Chỉ code + test + script; không gọi Binance, không đụng 242, không push. A1 re-audit delta
`5a66444e..HEAD`.

## 1. Hash, addendum, jar

| mục | giá trị |
|---|---|
| addendum prereg §ADD-2 (commit riêng, TRƯỚC code) | `37825cbb` — `docs/prereg/GCANARY_PREREG.md` sha256 `62d2e0d18d628e2a229de36ef1a035432dcc370b121df4cbf61bfd219e9a25fb` |
| engine: stop bảo vệ −4,5 %, guard gateway, heartbeat, test | `825a130e` |
| script: không chờ khung giờ, lỗ cộng dồn, kill JVM treo, `canary_early_flatten.sh`, test_fake242 | `976744ef` |
| pin jar 3c | `d14a5612` |
| jar (canary-early + dry) | `~/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3c`, md5 **`5de6c9899b09758965a14b91ac836ef7`** (pin `canary_lib.sh` + `deploy_v12_dry.sh`). Jar 3b `5405dfb2` đã xoá. |
| build | 646 test, 0 fail (642 + 4 mới) |
| test script | `test_fake242.sh` **116/116 PASS** (115/115 khi chạy trong khung giờ: 1 kiểm time_ok chỉ chạy ngoài giờ); mới: 14h + mục 16 |
| parity 10-23 (c3_shadow, jar 3c vs dcae2e2b) | **PASS** — out_BT `e0918a33` khớp, out_NEW2 `e0918a33` khớp, fund_BT `a81b3b03` khớp, fund_NEW2 `8dea3f70` khớp; ctl only_ref = only_new = 0; strace AF_INET non-loopback = 0 (`docs/result/round3c/r3c_compare.json`) |

Delta `src/main` chỉ trong `c3live/canary/` (CanaryEngine, CanaryGateway, CanaryLimits, C3LiveCanary). Đường c3_shadow / runtime không đổi.

## 2. MAJ-C1 — trần lỗ giữa 2 JVM

**Engine (stop bảo vệ, prereg §ADD-2):**
- `CanaryEngine.openLeg` → `protect(sym)` ngay sau khi leg CONFIRMED (mọi bước có mở: K1, K4, K5, K6_OPEN, K6B_OPEN, K7, K7b chính + phụ):
  stop closePosition MARK_PRICE qua đúng đường `TrailingStopManager` ở **−d so giá vào**,
  `d = min(4,5 %, (2 − 0,10 − lỗ hiện tại − lỗ xấu nhất của vị thế canary khác) / notional)`. Thường: 4,5 % (20 USDT ⇒ 0,9; 40 USDT ⇒ 1,8 USDT).
- Trước khi gửi lệnh mở: ngân sách chỉ đủ stop < 1 % ⇒ **không mở** (TRƯỢT, 0 lệnh gửi).
- Không đặt được / không thấy stop NEW trên sàn / stop xa hơn −d ⇒ **đóng vị thế ngay** (`closeCluster(PROTECT_FAIL)`) rồi TRƯỢT.
- `CanaryGateway.newStopMarket`: từ chối (GuardException) mọi stop SELL thấp hơn `entry × (1 − 4,5 % − 2 bp)` (entry đọc thẳng positionRisk;
  không đọc được ⇒ vẫn cho đặt — stop chỉ giảm rủi ro). Hằng số `CanaryLimits.MAX_STOP_DIST/STOP_ROUND_TOL/MIN_STOP_DIST/STOP_FEE_RESERVE_USDT`.
- Mặc định trailing của canary: −4,5 % (cũ −20 %). K5/K6/K7/K7b: `ensureProtected` thay cho stop −20 %.
- **K2 (đổi số §ADD-2):** (a) stop bảo vệ có sẵn từ K1 (kiểm `queryStop` NEW; `algoStatus` xem journal K1) → (b) −4,0 % → (c) closePosition
  thứ 2 ở −4,2 % → (d) −3,5 %. K4 giữ (−0,15 % theo mark).
- Bước `_OPEN` không ĐẠT cũng tự flatten trong JVM (trước chỉ khi Abort).

**Script:** `canary.sh` và `canary_early_run.sh` bỏ `cl_time_gate wait` giữa các bước; `cl_time_gate` chỉ còn kiểu `die` và chỉ gọi ở đầu
phiên / đầu lệnh (tài khoản phẳng). Không còn đường nào chờ tới 3600 s khi đang giữ vị thế.

**Kết quả:** sau mỗi bước, mọi vị thế canary còn mở đều có stop trên sàn với lỗ xấu nhất cộng dồn ≤ 2 − 0,10 − lỗ đã có ⇒ trần 2 USDT giữ
được khi không JVM nào canh và khi mất ssh (trừ trượt giá > 0,10 USDT lúc stop kích — điểm mở 1).

## 3. MIN

| # | sửa | ở đâu | test |
|---|---|---|---|
| MIN-C2 | tổng lỗ cộng dồn mọi phiên canary-early (mỗi phiên max(0, phí + lỗ chốt − funding) từ `canary_state.json` của `run/canary`, `canary_done_*`, `canary_prev_*`) + số lần `CANARY_RESET` (= số `canary_prev_*`) ghi vào file kết quả; > **4 USDT** ⇒ install và run TỪ CHỐI; MASTER đổi trần bằng `~/claude_master/deploy/gates/CANARY_EARLY_CUM_CAP.ok` | `cl_cum_loss` | fake 16a, 16b |
| MIN-C3 | flatten (early) + phiên run khi dừng: kill JVM canary TREO trước rồi mới flatten — chỉ process cwd = `c3canary`, có arg đúng = lớp main (không phải vỏ shell), là pid giữ lock ≥ 10′ (`since=` trong file lock) và heartbeat luồng chính `run/canary/canary_jvm.hb` cũ ≥ 3′; TERM rồi KILL. JVM ghi heartbeat trong mọi vòng ngủ của engine (≤ 1 lần/5 s). cwd = v_t_m / mode chuẩn ⇒ không bao giờ kill | `cl_kill_hung`, `C3LiveCanary.Heartbeat` | fake 16c (treo ⇒ kill; heartbeat mới ⇒ giữ; cwd v_t_m ⇒ giữ) |
| MIN-C4 | `canary_early_flatten.sh` một lệnh, tự `CANARY_MODE=early`, hỏi YES, đặt STOP, kill JVM treo, flatten | script mới | fake 16c |
| MIN-C6 | `CanaryIsolationTest` cấm thêm `com.binance.client.*`, `com.binance.chuyennd.config.*`, `*PrivateConfig*`, `*ClientSingleton*` | test | build |
| MIN-C1 | **để vòng sau** (trước G-GOLIVE): lock tài khoản con dùng đường dẫn tuyệt đối chung cho runtime live + canary | — | — |
| MIN-C5 | giữ (chấp nhận: sửa tay state là thao tác người vận hành) | — | — |

## 4. Test mới

- Java: `fullSessionK0toK8` kiểm sau K1 và sau K6_OPEN có đúng 1 stop closePosition ở −4,5 % (±2 bp);
  `protectiveStopTightensWhenLossBudgetShrinks` (lỗ 1,5 USDT ⇒ stop ~−2 %), `noOpenWhenLossBudgetTooSmall` (lỗ 1,85 ⇒ 0 lệnh gửi),
  `protectFailureClosesPositionImmediately` (sàn từ chối stop ⇒ K1 và K6_OPEN đóng vị thế ngay), `stopFartherThanMaxDistFromEntryRefused`
  (gateway). K2 chạy với số mới (−4,0/−4,2/−3,5 %) trong phiên đầy đủ.
- Script (test_fake242): 14h (`canary.sh`: khung giờ đóng sau K1 ⇒ không chờ, chạy đủ chuỗi; ngoài giờ đầu phiên ⇒ từ chối), 16a (early run
  tương tự + file kết quả có lỗ cộng dồn/số reset), 16b (lỗ cộng dồn 4,5 > 4 ⇒ install/run từ chối; trần MASTER 10 ⇒ chạy), 16c (kill JVM
  treo / giữ JVM sống / giữ process cwd v_t_m / `canary_early_flatten.sh`).

## 5. Lệnh owner (trên Oracle)

```
YES=1 CANARY_EXPECT_TMB=10000 bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_install.sh
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_run.sh          # gõ YES một lần
bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_early_flatten.sh      # KHẨN CẤP (gõ YES)
```

## 6. Điểm mở

1. Trượt giá khi stop MARK kích (lệnh MARKET) có thể vượt dự phòng 0,10 USDT trong biến động mạnh ⇒ lỗ thực có thể nhỉnh hơn 2 USDT một chút;
   muốn chặt hơn: tăng dự phòng (giảm d) — MASTER quyết.
2. K2 với ngân sách đã co (d < 4,0 %, tức lỗ trước đó > ~1 USDT): (b) "dời lên −4,0 %" không dời được (ratchet) ⇒ K2 TRƯỢT ⇒ flatten. An toàn,
   chỉ làm phiên dừng sớm.
3. Stop bảo vệ −4,5 % gần hơn −20 % cũ ⇒ biến động lớn trong phiên có thể kích stop ngoài kịch bản (bước sau TRƯỢT vì mất vị thế ⇒ flatten) —
   chấp nhận vì trần lỗ quan trọng hơn.
4. MIN-C1 (lock tuyệt đối) để vòng sau; hiện an toàn nhờ kiểm `LIVE_ADAPTER` rỗng + PID v_t_m trước/sau mỗi bước.
5. Kill JVM treo chỉ ở mode early; mode chuẩn (cwd = v_t_m) chỉ báo, owner xử lý tay.
6. Lỗ cộng dồn tính từ sổ cái stream trong `canary_state.json`; phiên mất sự kiện stream có thể tính thiếu (bù: mỗi phiên vẫn có trần 2 USDT
   theo tmb trong JVM).
