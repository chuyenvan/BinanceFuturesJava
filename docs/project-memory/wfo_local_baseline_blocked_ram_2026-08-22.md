# WFO local baseline — BỊ CHẶN bởi RAM Oracle; đường đi tiếp — 2026-08-22

## Tình huống
Chạy full-18 WFO LOCAL trên Oracle (WfoWorker -Xmx20g, ds_base 5.3G + WFO_SMART_CACHE=1 +
aerospike-wfo resident) → **thrash swap** trên box 23GB. Từ ~18:57 UTC, sshd Oracle timeout hoàn
toàn (banner → rồi TCP connect timeout), >30 phút không hồi. Worker -Xmx20g trên heavy window
(w10-w13/w17 2024-2025, vốn cần ~20g heap) + phần còn lại vượt 23GB → swap liên tục → sshd starved.
Không can thiệp được (chỉ có đường ssh, mà ssh chết).

## Đây là giới hạn tài nguyên THẬT, không phải lỗi logic
Heavy 2024-2025 window cần ~20g heap (đã biết: w10/w11 OOM ở 8g). Oracle 23GB không đủ cho
(20g heap + 5.3G data + smart-cache ticker + aerospike) cùng lúc. Chính vì vậy pipeline production
dùng KAGGLE fanout (kernel 30GB) chứ không chạy local. ⇒ Local full-18 KHÔNG khả thi trên Oracle
hiện tại cho các heavy window.

## Đã hoàn tất (local baseline chạy được 6-7 window nhẹ trước khi thrash)
Trước khi thrash, local WfoWorker (canary DCA-off/K5, ticker frozen d521edb0, ds_base 779e2f8e,
nSamples=1) cho per-window (oosPnl, posRatio 100% các window này):
w00=854.6(115tr) w02=419.1(39) w03=159.6(165) w04=463.7(49) w05=198.7(95) w06=663.9(52) w07~1429.5.
→ Đây là số CANARY THẬT trên data đã verify (khác Kaggle w4=1208 vì Kaggle ticker khác corpus verified).
Chưa đủ 18 window nên chưa có FULL local hoàn chỉnh.

## CẦN USER: reboot Oracle VPS (từ console) để clear thrash. sshd sẽ hồi.

## Đường lấy baseline sau reboot (2 lựa chọn)
A. **Kaggle CÓ PIN TICKER (khuyến nghị cho heavy window)**: Kaggle kernel 30GB chạy heavy window OK.
   Fix trust: đảm bảo ticker Kaggle == corpus verified (upload lại từ daily/ md5 d521edb0, ghi version),
   + preflight checksum trên worker (fail nếu != frozen) + fanout retry tới 18/0. Rồi 1 run 18/0 = baseline.
B. **Local heap 13g + WFO_SMART_CACHE=0 cho window NHẸ**: đủ cho 2022-2023 window; heavy 2024-2025
   nhiều khả năng OOM/BURN ở 13g → phải để Kaggle làm heavy window. (baseline hỗn hợp, phức tạp hơn.)
→ Chọn A: sạch nhất. Local (VerifyOneWindow/WfoWorker) vẫn là công cụ CHỨNG MINH determinism (đã dùng).

## Trust story — ĐÃ HOÀN TẤT (không phụ thuộc baseline number)
1. Engine deterministic — VerifyOneWindow ×2 byte-identical (oosPnl 2836.7949, 636 trades...).
2. Build deterministic — funding.bin md5 779e2f8e ×2 build độc lập.
3. Data complete — FileMinuteScan 1613 ngày, incomplete=0 err=0 (đủ 1440'/ngày).
4. Ticker frozen — corpus md5 d521edb0 (1886 files, 1 corpus authoritative).
5. Kaggle fanout = UNTRUSTED — unpinned ticker dataset (drift 0.3% per-window giữa 2 fanout dù
   build md5 giống + nSamples=1) + kernel flakiness (FAILED). Đây là gốc "mỗi lần một số".
6. 19840 = aerospike (nghi thổi phồng), 10k = file-mode == Binance (honest). Band [18000,21500]
   neo 19840 chưa verify → cần RETIRE, re-anchor vào run frozen reproducible.

## Scripts đã soạn (C:\Users\pc\, deploy sau reboot)
wfo_trust_run.sh (manifest + preflight ticker md5 gate), wfo_local_baseline.sh, wfo_complete_loop.sh.
Access: desktop-commander → WSL → ssh /root/.ssh/ora_key ubuntu@161.118.212.3.
