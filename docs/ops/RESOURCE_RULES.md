# RESOURCE_RULES — luật tài nguyên trước khi chạy việc nặng (MASTER 10-15)

## Sự cố: 3 lần crash ngày 2026-10-15 = OOM (hết RAM, KHÔNG swap)
- `18:25:20` kernel OOM-killed `python3` anon-rss **10,0 GB** (cgroup openclaw-gateway); load đỉnh 133.
- Nguồn: audit E1 nạp cả 4 năm 1 lượt (~10 GB) + 2 JVM shadow (3,9+3,9 GB) + Aerospike (2,9 GB) + node gateway (0,9 GB) + Phase 1.
- Audit **tự resume sau reboot** (gateway = systemd user service + Linger=yes).
- Hệ quả phụ: crash làm hỏng 9 git object rỗng (đã khôi phục bằng `git fetch origin`).

## LUẬT (bắt buộc TRƯỚC khi chạy)
- **R1 Preflight:** `/home/ubuntu/ops/mem_preflight.sh [MIN_MB]` — rc≠0 (< 2 GB) ⇒ KHÔNG chạy.
- **R2 Trần RAM:** job nặng chạy `systemd-run --user --scope -p MemoryMax=3G -p MemorySwapMax=1G <cmd>` ⇒ vượt trần chỉ giết job đó.
- **R3 Serialize:** audit / kernel / backtest KHÔNG song song Phase 1 hay deploy.
- **R4 Chia nhỏ:** audit chạy TỪNG NĂM (`--years 2022`, rồi 2023…).
- **R5 Watchdog:** `~/ops/mem_watchdog.sh` (cron `*/3`) ghi RAM/load/top; RAM khả dụng < 1,2 GB ⇒ TERM python > 4 GB + Telegram.
- **R6 Swap:** `/swapfile` 8 GB, fstab, `vm.swappiness=10` (đệm, KHÔNG thay R1–R5).
- **R7 Sau reboot:** kiểm `free -h` trước; không để task tự chạy lại khi RAM dưới ngưỡng.
