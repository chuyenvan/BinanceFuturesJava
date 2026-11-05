# E2E_REPLAY_RESULT — ngày sập 10-30 trên code v1.2 HEAD 33a81398 (lớp thực thi c3_live)

Tiêu chí: `docs/c3live/E2E_REPLAY.md` (commit 788acf95, viết TRƯỚC code). Chạy 2026-11-05 trên Oracle qua
`flock oracle_heavy.lock`, `LIVE_IS_SHADOW_HOST=true`, PrivateConfig STUB, config không host 242. Không đổi code production.
Đầu ra: `~/claude_master/e2e1105/out/<run>/{result.json,check_ref.json,trace_dec.csv.gz,outcomes.csv,events.csv,run/}`.

## 1. Phát hiện (rủi ro trước)
1. **PREMARKET lệch tín hiệu ↔ R7 (production, parity):** `UniverseA1Classifier.java:46` coi `underlyingType=PREMARKET` là CRYPTO
   (giữ ở tầng tín hiệu, = sim A1), nhưng R7 `SymbolUniverseLive.java:247` (strictCoin) loại `NOT_COIN`. 10-30: PREDICTUSDT
   (PREMARKET, hạng 2 đợt 1, shadow v1.1 có vào) PASS gate 6 phút ⇒ cả 6 lần `NOT_BUYABLE NOT_COIN`; không giữ ⇒ chiếm slot
   top-24 và tiếp tục nạp r mỗi phút (sim sẽ giữ ⇒ không nạp). Lệnh live vẫn là tập con của sim nhưng buffer q lệch dần.
   Cần MASTER chọn: loại PREMARKET ở A1 (cả sim) hoặc cho R7 mua PREMARKET.
2. **Phí khớp mất khi user stream rớt (production, MINOR):** phí chỉ ghi ở `FillAccounting.java:141` (sự kiện stream); đường
   xác nhận REST `C3LiveOrderExecutor.java:300` không ghi phí, nối lại không bù. F1 (rớt 12′ giữa đợt 1, 15 leg): phí sổ 0,359
   vs sàn 0,549 USDT (thiếu 35 %) ⇒ equity c3/C6/A40 và ledger lạc quan nhẹ. Realized khớp.
3. **C3 không latch khi 429 chỉ dính lệnh (thiết kế, cần MASTER xác nhận):** F2b 6 lệnh MARKET 429 liên tiếp nhưng xen call đọc
   thành công ⇒ bộ đếm "lỗi liên tiếp" reset, không latch. Leg 429 huỷ giữ chỗ đúng, không cid trùng; phút sau gate PASS lại ⇒
   quyết định mới vào (F2: 29, F2b: 32 SUBMITTED vs 26). Rủi ro: 429 kéo dài trên lệnh không có ngắt.
4. **MERGED: realized sổ ≠ rp sàn** (F5, EVAAUSDT 1,0353 vs 0,8135): sàn tính rp trên giá vốn gộp LEGACY+c3 — bản chất one-way,
   không phải lỗi; ledger c3 đúng theo VWAP c3. Đối soát realized phải loại symbol MERGED.

## 2. Bảng tiêu chí
| mục | kết quả | ghi chú |
|---|---|---|
| D0 GateHeldReplay1030R4hTest | ĐẠT (gián tiếp) | E2b tái lập đúng số của test (cùng dữ liệu); test gốc không chạy riêng |
| E2a bám buffer live | **TRƯỢT theo công thức** (98,98 %) | 102 600/102 600 bản ghi live khớp bit (0 lệch phía live); 1 056 bản ghi harness sau 11-01 06:14 = hết bản chụp buffer (iii dữ liệu) |
| E2b neo MASTER | ĐẠT | q04 = 0,00756445155; đợt 2 mới = CAP CT DOS IDOL IRYS NIL PARTI Q (q đóng băng 29 pass; q theo giờ production 8 pass, cùng 8) |
| E1 R0 ≡ REF numpy | ĐẠT | 103 656 dòng, 72 giờ q, PASS/rank/gated/q/nạp r trùng 100 % (R0, R0-DRY, F2b, F5) |
| X1 vào lệnh | **TRƯỢT** mọi lượt | chỉ do phát hiện 1 (6× NOT_BUYABLE PREDICT); còn lại 25/25 PASS ⇒ SUBMITTED |
| X2 khớp 1 lần, sổ=sàn | ĐẠT mọi lượt | xác nhận ≤ 9 s |
| X3 arm + stop | ĐẠT mọi lượt | R0: 22 arm, 91 đặt, 69 dời, tối đa 1 stop/symbol |
| X4 dời stop | ĐẠT | |
| X5 không mồ côi | ĐẠT mọi lượt | |
| X6 đối soát | ĐẠT trừ F1 (phát hiện 2), F5 (phát hiện 4) | qty khớp tuyệt đối mọi lượt |
| X7 0 exception | ĐẠT; F5 ERROR = cảnh báo MERGED do chính lỗi tiêm | |
| X8 kill-switch | ĐẠT (R0/R0-DRY 0 latch) | |
| X9 rate | ĐẠT | đỉnh 264 weight/phút (03:47), 13 lệnh/10 s |
| X10 DCA | KHÔNG XẢY RA tự nhiên; S-DCA ĐẠT | 1 due ⇒ 1 SUBMITTED |
| F1 WS rớt | ĐẠT (trừ X6) | 15 leg trong khoảng rớt, xác nhận REST ≤ 9 s |
| F2 / F2b 429 | ĐẠT / **TRƯỢT** (phát hiện 3) | |
| F3 thiếu avgPrice | ĐẠT | 0 C2 giả |
| F4 EXPIRE +4 ms | ĐẠT | sau ADDENDUM (ghép FLATTEN), 2 stop sàn tự EXPIRE |
| F5 LEGACY/MERGED | ĐẠT | 0 call c3 lên LEGACY, r vẫn nạp, MERGED ⇒ stop qty, cuối sàn = qty LEGACY |
| F6a DD | ĐẠT | latch C6+A40 ngay 10:00, phẳng 10:01, 0 stop, 0 lệnh sau |
| F6b C1 | ĐẠT (một phần rỗng) | latch 12:05, gỡ 12:37; không có PASS trong latch ⇒ KS_BLOCKED chưa được thử |

So shadow v1.1: R0 đợt 1 = 16/17 coin non-TF của shadow (thiếu PREDICT) + AGT vào lại; đợt 2 = AGT (BIG_DOWN) + đúng 8 coin MASTER kỳ vọng.

## 3. Sửa sau lần chạy 1 (khai, viết SAU khi thấy số; không đổi ngưỡng)
- harness X6 cộng phí cụm mở 2 lần ⇒ bỏ; rig thiếu `qtyModeFor(scope::isMerged)` (runtime có) ⇒ thêm (F5 X3 giả);
  sàn giả thiếu từ chối -2021 ⇒ bật `rejectWouldTrigger` (F2 X3 giả); F4 rỗng (mọi thoát R0 do stop kích) ⇒ ghép FLATTEN.
## 4. Giới hạn thêm (ngoài §6)
- Không nối `FlatConfirm` (dùng đồng hồ thật) ⇒ nhánh "nghi phẳng" chưa thử; cầu dao mật độ `is50PercentOrderLossProd` không mô hình;
  bookFull theo sổ c3 (production đọc sổ giấy twin); 43 ô TradFi trong top-24 ở phút có PASS ⇒ R0 có thể thiếu leg hạng 25+.

## 5. Chạy lại trên r4p (2026-11-05 11:06, HEAD 2822bf78, jar r4p md5 ed0c30e9)
Rig nối như runtime r4p: `ApiObserver.onOrderResult`, `setCostRecovery(acct)`, `tickCosts` trong vòng ops. X6 realized loại rp sàn
của symbol MERGED (sàn tính trên giá vốn gộp LEGACY+c3); phần MERGED của sổ so với rp VWAP c3 tính độc lập từ khớp sàn. Tiêu chí
không đổi. Log `~/claude_master/e2e1105/logs/test_110622.log`.

| mục | lần 1 (33a81398) | r4p |
|---|---|---|
| F1 X6 phí | TRƯỢT 0,359 / 0,549 | **ĐẠT** 0,5491 / 0,5491; realized khớp |
| F2 (3×429) | ĐẠT, không latch | ĐẠT, không latch |
| F2b (6×429 MARKET xen đọc OK) | TRƯỢT, không latch | **ĐẠT**: latch C3 03:47:06, gỡ 04:23:00 (36′); 14 SUBMITTED / 56 KS_BLOCKED; X6 ĐẠT |
| F5 X6 realized | TRƯỢT 1,0353 vs 0,8135 (EVAAUSDT) | **ĐẠT**: sổ 31,1732 − c3 MERGED 1,0353 = 30,1379 = Σrp sàn non-MERGED |
| X6 mọi lượt khác | ĐẠT | ĐẠT (phí sổ = sàn tới 1e-6) |
| X1 | TRƯỢT mọi lượt (PREDICT, phát hiện 1) | không đổi — chờ owner chọn PREMARKET (a)/(b) |
| F5 X7 | ERROR do chính lỗi tiêm | không đổi |
| E2a | TRƯỢT theo công thức (hết bản chụp buffer) | không đổi |

Khai: lần chạy r4p đầu (11:00, trước 2822bf78) F2b latch 2 lần — 429 thứ 6 xếp hàng rơi vào lệnh 07:18 và cộng dồn với bộ đếm cũ ⇒
sửa production (429 ngoài cửa sổ giữ 5′ đếm lại từ 1) + test, rồi chạy lại toàn bộ (bảng trên).

## 6. Chạy lại trên r4q (2026-11-05 11:59, HEAD 00a1f1f6, jar r4q md5 1590d606)
- Code r4q gồm PREMARKET (b): A1 loại PREMARKET (MASTER 4q), queue LEGACY bị chặn khi c3_live, cùng Java 4p.
- Sửa harness (khai): trước đây `CrashDayRig.a1Excluded` chỉ loại TradFi. Nay nó mirror `UniverseA1Filter` production và loại cả
  TRADFI, INDEX, PREMARKET. Tiêu chí không đổi.
- Log: `test_115940.log`. `check_ref.py` đã chạy lại cho R0, R0-DRY, F2b, F5.

| mục | r4p | r4q |
|---|---|---|
| X1 | TRƯỢT mọi lượt (PREDICT NOT_BUYABLE) | **ĐẠT mọi lượt**: PREDICTUSDT bị A1_EXCLUDED ở tầng tín hiệu, 0 NOT_BUYABLE. R0 có 26 SUBMITTED |
| E1 R0 ≡ REF numpy | ĐẠT | ĐẠT (R0, R0-DRY, F2b, F5: diff = {}) |
| X2–X6, X8, X9, F1–F4, F6a/b, S-DCA | ĐẠT | ĐẠT. Phí sổ = sàn mọi lượt; F2b có phí 0,2213, khác trước vì slot PREDICT đã trống |
| F5 X7 | ERROR do chính lỗi tiêm | không đổi |
| E2a | TRƯỢT theo công thức (hết bản chụp buffer) | không đổi |
