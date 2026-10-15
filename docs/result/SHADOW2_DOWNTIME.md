# SHADOW2_DOWNTIME — đoạn loại khỏi thước (MASTER 10-15 17:53)

Sự kiện: **VPS Oracle crash + reboot**, 2026-10-15. Điều tra **CHỈ ĐỌC** (không restart service).

## 1. Bằng chứng (shadow)
```
systemctl status:
  shadow-c3.service   Active: active (running) since Thu 2026-10-15 15:44:15 +07   Main PID 805 (java)
  shadow-c3b.service  Active: active (running) since Thu 2026-10-15 15:44:15 +07   Main PID 807 (java)
Log cuối TRƯỚC reboot:  c3 15:43:52.846  ·  c3b 15:43:52.611
Gate persist nạp lại:   c3 15:44:19.178 · c3b 15:44:19.171  ->  warm-up = ARMED
   c3  buffer size=305056 firstTs=20261001 13:00 (warm-up=armed)
   c3b buffer size=233224 firstTs=20261008 14:49 (warm-up=armed)
droppedChunks / backupCorruptFile : KHÔNG có (không xuất hiện trong log)
jar sha256 (c3 & c3b): 0c2f4d72a5ae77c9b86526d5…  ✅ khớp bản triển khai 0c2f4d72
```
- **KHÔNG** rơi vào `fallback base` sau reboot — cả hai vào thẳng **armed** (pct=0,99995083, window=90d, file `run/gate_ratio_live.bin`).
- jar giữ đúng **0c2f4d72** ⇒ không có thay đổi binary do reboot.

## 2. Downtime (đoạn phải LOẠI khỏi mọi so khớp thước shadow #2)
| mốc | thời gian (+07) |
|---|---|
| tick cuối trước crash (c3) | **2026-10-15 15:43:52.8** |
| service active lại | **2026-10-15 15:44:15** |
| gate armed lại | **2026-10-15 15:44:19.2** |
| **downtime (tick→active)** | **≈ 22 giây** |
| **downtime (tick→gate armed)** | **≈ 26 giây** |

⇒ **Đoạn loại khỏi thước `PREREG_SHADOW2_PROMOTION`**: `[2026-10-15 15:43:52.8 , 2026-10-15 15:44:19.2] (+07)` — không có tick/quyết định vào lệnh trong khoảng này.

## 3. Coverage gap của collector liquidation (P2)
| mốc | giá trị |
|---|---|
| crash (tick cuối) | 2026-10-15 ~15:43:53 |
| collector restart (pidfile) | 2026-10-15 15:45:01 |
| **gap [crash, restart]** | **≈ 68 giây** |
| event gần nhất | `2026-10-15.csv.gz` = **7 328 dòng**, ts cuối **1792063602142** (= 18:26 +07, hiện tại) ⇒ **có event trong 10 phút gần nhất** ✅ |
- **Watchdog tự lên sau reboot: ĐÃ CÓ** — cron `*/5 * * * * …/liq_watchdog.sh` (đã tự restart lúc 15:45:01) + systemd `liq-collector.service` (nhô lên 15:44:15). ⇒ đủ điều kiện MASTER; (tuỳ chọn: thêm `@reboot` để hồi phục < 60 s thay vì ≤5 phút).

## 4. Ghi chú
- Toàn bộ mục 1–3 là **đọc**; không start/stop/restart service nào (đúng lệnh).

## 5. CẬP NHẬT — reboot #3 (18:33:42, cùng ngày)
| mốc | thời gian (+07) |
|---|---|
| tick cuối trước crash (c3 & c3b) | **2026-10-15 18:32:30** |
| service active lại | **2026-10-15 18:33:44** |
| gate armed lại | **2026-10-15 18:33:48** (c3 & c3b, warm-up=**ARMED**) |
| **downtime** | **≈ 74 s** (tick→active) · **≈ 78 s** (tick→gate armed) |
- jar sha256 vẫn `0c2f4d72a5ae77c9b86526d5…` ✅ · `droppedChunks`/`backupCorruptFile`: KHÔNG có.
- Boot list hôm nay: `-2` 12/10 06:11→**15/10 15:43:58** · `-1` 15:44:13→**18:33:28** · `0` 18:33:42→nay ⇒ **2 lần crash hôm nay**.

⇒ **Đoạn LOẠI khỏi thước `PREREG_SHADOW2_PROMOTION` (cộng dồn)**:
`[2026-10-15 15:43:52.8 , 15:44:19.2]` và `[2026-10-15 18:32:30 , 18:33:48]` (+07)
— vì mỗi lần cắt chuỗi "4 tuần sạch" (~11–12).
