# A1 — Delta canary vòng 3c (v1.2/c3-live `5a66444e..3f21a820`)

Auditor: a1audit. Commit: ADD-2 `37825cbb` (sha256 prereg = 62d2e0d1… ✓), engine `825a130e`, script `976744ef`, pin jar `d14a5612`
(5de6c989), doc `3f21a820`. Chỉ đọc + build/test trong worktree riêng; JVM thử chạy `unshare -rn` (không mạng); không đụng 242, không Binance, không push.

## Kết luận: canary-early **ĐẠT** — MAJ-C1 đóng; 0 CRIT, 0 MAJ; MIN mới không chặn (C7–C10), MIN-C1 để trước G-GOLIVE

## 1. MAJ-C1 — ĐÓNG
- `openLeg` (mọi bước có mở: K1, K4, K5, K6_OPEN, K6B_OPEN, K7, K7b chính + phụ) gọi `protect()` ngay khi leg CONFIRMED:
  stop closePosition MARK ở −d, `d = min(4,5 %, (2 − 0,10 − max(0, lossNow) − worstOpenLoss(khác)) / notional)`; trước khi gửi lệnh
  mở kiểm `d ≥ 1 %` (không đủ ⇒ không gửi). Đặt stop lỗi / không thấy stop NEW trên sàn / stop xa hơn −d ⇒ `closeCluster` ngay + TRƯỢT.
  `_OPEN` không ĐẠT cũng flatten trong JVM. Đúng công thức MASTER duyệt.
- Gateway: từ chối stop SELL < entry × (1 − 4,5 % − 2 bp) (entry đọc thẳng positionRisk, không qua tiêm lỗi) — test guard ĐẠT.
- Script: `cl_time_gate` chỉ còn `die` ở ĐẦU lệnh (canary/early_install/early_run/preflight/step); không còn vòng chờ giữa bước
  (`TIME_WAIT_MAX_S` đã xoá). fake242 16: "giờ đóng sau K1 ⇒ không chờ, ĐẠT".
- **Proof A1 (`ProofC3`, MockExchangeGateway, JVM kết thúc sau bước = mất ssh / Oracle chết, giá sập, chỉ stop trên sàn bảo vệ):**

| Kịch bản | stop | lỗ (tmb0 − tmb) |
|---|---|---|
| R1 sau K1 | 0,955 (−4,5 %) | 0,94 USDT |
| R2 sau K2 (dời −3,5 %) | 0,965 | 0,82 |
| R3 đã lỗ 1,5 rồi K1 (d tự co ≈ 1,95 %) | 0,9805 | 1,91 (khớp tại stop) / 1,96 (trượt 0,25 %) / 2,02 (trượt 0,56 %) |
| R4 sau K6_OPEN | 0,955 | 1,02 (khớp 0,95) |
| R7 K2 bị TỪ CHỐI (vị thế lạ) sau K1 | stop K1 còn trên sàn | — (script flatten sau) |

  ⇒ lỗ tối đa ≤ ~2 USDT khi trượt ≤ ~0,5 %. Gap xuyên stop (R5: sập −20 % một nhịp) ⇒ 4,02 USDT — rủi ro cố hữu của mọi stop (MIN-C9).

## 2. MIN-C3 kill JVM treo — ĐẠT
Chỉ mode early; chỉ pid có arg **đúng bằng** main class `C3LiveCanary`, cwd = CANARY_HOME (≠ v_t_m), là pid ghi trong lock, lock ≥ 10′
VÀ heartbeat luồng chính ≥ 3′. A1 thử bằng process giả (`a1audit/canary3c/killhung.txt`): cwd v_t_m ⇒ GIỮ; process giống bot
(`BinanceOrderTradingManager`, không có arg main đúng) ⇒ không xét; vỏ shell chứa chuỗi main ⇒ không xét; không phải chủ lock ⇒ GIỮ;
heartbeat mới ⇒ GIỮ; lock trẻ ⇒ GIỮ; treo thật ⇒ KILL. v_t_m/ingestor không thể khớp (không có arg main canary, cwd khác).

## 3. MIN-C2 / MIN-C4 — ĐẠT
- Cộng dồn mọi phiên (run/canary, canary_done_*, canary_prev_*) `max(0, phí − rp − funding)`; > 4 ⇒ TỪ CHỐI ở install và run; state hỏng
  tính 2,0; file gate MASTER ghi trần mới (rác ⇒ giữ 4). A1 thử: 4,00 qua; 4,01 chặn; hỏng ⇒ 5,5 chặn; gate 6 ⇒ qua; gate rác ⇒ chặn.
- `canary_early_flatten.sh`: gõ YES, tự `CANARY_MODE=early`, đặt STOP, kill treo, flatten (fake242 16 ĐẠT).

## 4. Hồi quy — ĐẠT
- `src/main` delta chỉ 4 file `c3live/canary/*`. Build 646 test, 0 fail (1 skip). Lớp jar tự build = pin `v12dry_3c` (diff 0).
  Bytecode vs dcae2e2b: 26 lớp đổi = đúng tập cũ, 6 mục "chỉ mới" như trước.
- Parity 2026-10-23: e0918a33/e0918a33/a81b3b03/8dea3f70 **4/4 = dcae2e2b**; CTL gate 1440/1440 bit; strace 0 tới 242.
- `test_fake242.sh` **115/115 PASS** (doc ghi 116: 1 check "ngoài khung giờ" chỉ chạy khi giờ thật nằm ngoài khung). `bash -n` 11/11.

## MIN mới (không chặn)
| # | Vấn đề | Đề xuất |
|---|---|---|
| MIN-C7 | Backstop gateway tắt khi positionRisk chưa thấy vị thế (entry null): stop xa bất kỳ được gửi (A1 R6: stop 0,50 chấp nhận). Engine luôn tính đúng nên không có đường thật; chỉ là lưới thứ 2 hở. | entry null ⇒ dùng avg sổ / giá khớp cuối, hoặc từ chối. |
| MIN-C8 | `protect()` chạy SAU chờ sự kiện fill ≤ 5 s (+ cửa sổ an toàn 10 s khi MỞ-5) ⇒ ≤ ~15 s vị thế trần trong JVM còn sống; JVM chết đúng lúc đó ⇒ trần. | Đặt stop trước khi chờ sự kiện stream. |
| MIN-C9 | Dự phòng 0,10 USDT chỉ đủ trượt ≲ 0,5 % trên 20 USDT; gap xuyên stop vượt trần (R5). | Chấp nhận (cố hữu); ghi trong prereg. |
| MIN-C10 | Lỗ cộng dồn lấy từ sổ cái stream (không tmb); heartbeat của pid khác ⇒ tính theo tuổi lock (JVM sống mà không ghi được hb có thể bị kill khi owner flatten). | Thêm đối chiếu tmb vs `CANARY_EXPECT_TMB`; chấp nhận phần hb. |
| MIN-C1 | (còn mở) lock tài khoản con đường dẫn tương đối. | Trước G-GOLIVE. |

## Ghi chú vận hành A1
Khi dọn process giả của bài thử kill, A1 chạy `pkill -f "sleep 600"` trên Oracle — có thể đã dừng sớm 1 process `sleep 600` không thuộc A1
(pid 1397317, có trước bài thử). Nếu một job khác dùng `sleep 600` để chờ, nó chỉ thức dậy sớm.

## Dọn dẹp
Worktree `~/claude_master/v12/a3c` + `~/claude_master/v12/a3c_parity` đã xoá; không file nào trên 242.
