# A1 — Audit công cụ CANARY v1.2/c3-live (vòng 3 `47b29566` + 3b `05f55fac..5a66444e`)

Auditor: a1audit (độc lập). Phạm vi: `src/main/java/.../c3live/canary/*`, `runtime/C3LiveAccountLock`, `C3LiveRuntime` (+13),
`C3LiveClient`/`ExchangeGateway` (`tickers24h`), `ops/c3live/canary/*.sh`, `test_fake242.sh` mục 14–15. Chỉ đọc + build/test
trong worktree riêng (detached 5a66444e). Không đụng 242, không gọi Binance (mọi JVM thử chạy dưới `unshare -rn` = không có mạng), không push.

## Kết luận: canary-early **TRƯỢT** (1 MAJ, 0 CRIT)

Lỗi chặn duy nhất: trần lỗ 2 USDT **không được canh giữa 2 JVM**, và K1 để lại vị thế **không có stop** qua ranh giới JVM.
Sửa nhỏ (script + ~3 dòng engine), re-audit delta nhanh. Mọi điểm còn lại (key, guard cứng, cô lập v_t_m, MỞ-5, script, shadow) **ĐẠT**.

## MAJ-C1 — vị thế mở không được canh trần lỗ giữa các bước (khung giờ + K1 không stop)

- Mỗi bước = 1 JVM; `checkLoss` (tmb0 − tmb, phí + rp) chỉ chạy **khi có JVM** (`CanaryEngine.tick/begin`).
- Bước để lại vị thế cho bước sau: **K1 → K2** (vị thế 20 USDT, **0 stop** — `k1()` không gọi trailing), **K2 → K3** (stop −18 %),
  **K6 → K6B** (stop −20 %).
- `canary_early_run.sh:80` (và `canary.sh:194`) gọi `cl_time_gate wait` **trước mọi bước**, kể cả K2/K3/K6B: K1 bắt đầu :43–:44
  → kết thúc sau :44 → script **chờ tới 3600 s** (07:xx/19:xx: chờ hết 1 h rồi mới flatten) với vị thế trần, không JVM nào canh.
- Mất ssh Oracle→242 (hoặc Oracle chết) ngay sau K1: `cl_vtm_check` thất bại → flatten cũng qua ssh → thất bại → vị thế **không stop,
  không hạn thời gian**. Với stop K2/K6 (−18/−20 % × 20 USDT = 3,6–4 USDT) lỗ vẫn có thể > trần 2 USDT khi không có JVM.
- Xác suất thấp, số tiền nhỏ, nhưng đây là giới hạn CỨNG của prereg (§ trần lỗ) và đúng câu hỏi mục 3 ("bước nào để lại vị thế").

**Sửa tối thiểu (đề xuất):**
1. Script (`canary_early_run.sh`, `canary.sh`): không `cl_time_gate wait` trước bước **tiếp nối vị thế** (K2, K3, K6B); hoặc nếu phải chờ
   thì `flatten` trước. Thêm case test_fake242 (gate đóng giữa K1→K2 ⇒ không chờ khi đang giữ vị thế).
2. Engine: cuối K1 (sau khi xác nhận khớp) **arm stop closePosition −20 %** (`trailRate(s, -0.20f)`) — K2(a) vẫn ĐẠT vì `k2()` chấp nhận
   stop có sẵn (dòng 1213), (b)/(d) vẫn MOVE lên −19/−18 %. Tuỳ MASTER: siết về −10/−9,5/−9 % để stop tự nó ≤ trần 2 USDT (đổi số prereg K2).

## MIN (không chặn)

| # | Vấn đề | Đề xuất |
|---|---|---|
| MIN-C1 | Lock tài khoản con dùng đường dẫn **tương đối cwd** (`run/c3live_account.lock`): canary-early (c3canary/run) và runtime live (v_t_m/run) **không loại trừ nhau**. Hiện an toàn nhờ script kiểm `LIVE_ADAPTER` rỗng + PID v_t_m trước/sau mỗi bước. | Trước G-GOLIVE: `LIVE_C3_ACCOUNT_LOCK` tuyệt đối dùng chung (vd `/root/.config/c3live/account.lock`). |
| MIN-C2 | `CANARY_RESET=1` → phiên mới, `tmb0` mới ⇒ ngân sách lỗ 2 USDT **mỗi phiên**; tổng nhiều phiên không có trần code. K0 chỉ kiểm tmb ±1 % `CANARY_EXPECT_TMB`. | MASTER ghi số lần reset; đặt `CANARY_EXPECT_TMB` = tmb thực mỗi lần. |
| MIN-C3 | JVM treo > `STEP_MAX_S` (7200 s) ⇒ rc 5 ⇒ flatten bị TỪ CHỐI (lock còn giữ, `cl_check_242` thấy JVM canary khác); không có lệnh kill JVM treo. | rc 5: script kill đúng JVM canary (cwd c3canary) rồi flatten. |
| MIN-C4 | `canary_flatten.sh` ở early cần `CANARY_MODE=early`; thiếu ⇒ fail-closed (md5 jar v_t_m ≠ pin, chết TRƯỚC mọi ghi) — an toàn nhưng dễ nhầm lúc khẩn cấp; đang có bước chạy ⇒ chỉ đặt STOP. | Thêm `canary_early_flatten.sh` (1 lệnh). |
| MIN-C5 | `revalidateSymbols` chỉ kiểm cấu trúc (không hạng): sửa tay state sang symbol khác đủ cấu trúc vẫn chạy. | Chấp nhận (thao tác người vận hành); ghi chú. |
| MIN-C6 | `CanaryIsolationTest` chỉ cấm Aerospike/Redis/mapper, **không** cấm `PrivateConfig`/`ClientSingleton`/`com.binance.client.*`. | Thêm vào mẫu cấm (A1 đã chạy tay — xem mục 1). |

## Checklist

1. **Key — ĐẠT.** `C3LiveClient` chỉ nạp `C3LiveKeys` từ `LIVE_C3_KEYS_FILE` (script: `/root/.config/c3live/keys.env`); C3LiveKeys từ chối
   owner sai và thư mục cha ghi được bởi group/other (A1 thử: TỪ CHỐI đúng). Class-load JVM con (`-Xlog:class+load`, `env -i`, không mạng):
   bộ test canary (20 test, 3 840 lớp) + jar thật `C3LiveCanary status|keycheck|preflight|flatten|step K1|cleanup` (1 737–3 482 lớp/lần)
   ⇒ **0** `PrivateConfig` / `ClientSingleton` / `BinanceFuturesClientSingleton` / `com.binance.client.*` / Aerospike / Redis / mapper / `chuyennd.config.*`.
   `Utils` chỉ nạp cho Telegram (`<clinit>` chỉ LOG/gson/format; gọi thử `sendSms2Telegram` offline ⇒ vẫn 0 lớp trên). Key giả không xuất hiện
   trong stdout/journal/log/state. Lỗi REST chỉ `method + path` (không query/signature); listenKey: `Redacted`, URL WS che, JSON `listenKey` che;
   file kết quả có bộ quét mẫu bí mật (⇒ che + TRUOT).
2. **Guard cứng — ĐẠT (trong JVM).** `CanaryLimits` là hằng (20/25/40/2,0/2 symbol/1x), không env. `CanaryGateway`: mọi lệnh ghi chỉ 2 symbol
   trong state; MỞ = BUY không RO, notional = qty × giá ticker mới ≤ 25, tổng mở ≤ 40 (đọc positionRisk, symbol lạ ⇒ từ chối), chạm trần ⇒ từ chối;
   cấm SELL không RO / BUY RO; stop chỉ SELL, qty ⇒ RO; leverage = 1; CROSSED; dual = false. `begin()`: aborted ⇒ TỪ CHỐI, foreignExposure,
   revalidate luật, `checkLoss(true)` trước mọi lệnh. Chạm trần ⇒ `aborted` ghi file (atomic) ⇒ flatten ⇒ mọi bước sau TỪ CHỐI (restart giữ nguyên).
   Bypass thử: env cấm (`LIVE_PROFILE`, `TRADING_PROFILE`, `LIVE_TS_MKT_EXT`) qua env **và** `-D` ⇒ TỪ CHỐI (A1 chạy); script `env -i` + regex tham số;
   CANARY_STOP chỉ dừng giữa bước; CANARY_RESET xem MIN-C2; sửa tay state = thao tác người (MIN-C5). **Ngoại lệ: giữa 2 JVM ⇒ MAJ-C1.**
3. **Flatten / dừng khẩn — TRƯỢT do MAJ-C1**; phần còn lại đúng: phiên nền `setsid nohup` (đóng terminal không dừng), JVM 242 `nohup setsid`
   (mất ssh không giết JVM), bước không ĐẠT ⇒ `safeFlatten` trong JVM + flatten của script; JVM chết ⇒ rc ≠ 0 ⇒ flatten; flatten chỉ 2 symbol
   canary, MARKET RO c3x-, huỷ stop c3s- qua OwnStopGuard sau khi positionRisk + account cùng phẳng. JVM treo: MIN-C3.
4. **Cô lập v_t_m — ĐẠT.** Early: thư mục riêng (700), jar riêng (md5 pin 5405dfb2 trước/sau copy), lock/run riêng; v_t_m chỉ đọc
   (md5 jar/env/start, PID+cwd, environ: c3_shadow + SHADOW_NO_PUSH=true + không LIVE_ADAPTER) trước install, sau copy, sau keycheck, sau K0,
   trước + sau MỖI bước, sau flatten, cuối phiên; khác ⇒ dừng + flatten. RAM ≥ 1 GB/768 MB (hằng). LEGACY đọc `cat` (chỉ đọc). JVM `-Xmx384m`.
5. **MỞ-5 — an toàn để chạy `CANARY_INJECT_TIMEOUT=1` lần đầu.** Tiêm CHỈ phía client SAU khi sàn trả lời (lệnh thật gửi đúng 1 lần);
   `injectTimeoutUsed` ghi file TRƯỚC khi gửi ⇒ lần 2 TỪ CHỐI; executor chờ `safeRetryMs` 10 s ≥ recvWindow 5 s rồi `queryOrder(cid)` ⇒ FILLED ⇒ không gửi lại.
   Tệ nhất (query báo vắng sai): gửi lại CÙNG cid, bị trần tổng mở 40 chặn ở lần 3, `sends(cid)==1` ⇒ TRUOT ⇒ flatten (RO không lật short).
6. **Script owner — ĐẠT (trừ MAJ-C1).** 2 lệnh owner; YES (gõ 1 lần / `YES=1`); `bash -n` 10/10 OK; key qua `read -s` + stdin ssh;
   không xoá/huỷ ngoài phạm vi canary (rm duy nhất: bản sao legacy trong c3canary; mv run/canary). `test_fake242.sh`: **102/102 PASS**,
   mục 14+15 = 62/62. (Lần chạy đầu 100/102 do chính JVM thử của A1 chạy song song khiến `pgrep` thấy "JVM canary khác" ⇒ từ chối đổi tên —
   đúng hành vi guard; chạy lại sạch PASS.)
7. **Shadow — ĐẠT.** Build 642 test, 0 fail (1 skip). Class của jar tự build = jar pin `v12dry_3b` (diff 0 file). Bytecode vs `dcae2e2b`:
   **26 lớp đổi = đúng tập cũ**, 5 lớp thêm ngoài c3live như 2h; diff nguồn 05f55fac..HEAD trong `src/main` chỉ chạm `c3live/*`.
   Parity offline 2026-10-23 (drv.py): out_BT/out_NEW2/fund_BT/fund_NEW2 = e0918a33/e0918a33/a81b3b03/8dea3f70 **4/4 trùng dcae2e2b**;
   CTL gate 1440/1440 bit; strace 0 AF_INET non-loopback, 0 tới 242.

## Dọn dẹp
Worktree `~/claude_master/v12/a1c` + `~/claude_master/v12/a1c_parity` (jar, parity, fake242, class-load) đã xoá. Không file nào trên 242.
