# Disaster-exit: phân tích trên entry THẬT của hệ thống — 2026-08-21

Dữ liệu: 2863–2955 lệnh WFO thật (entry_paths × entry_pathstats_g008, 2021-04→2025-12) = chính các lệnh hệ thống vào. retEnd = raw (chưa fee/funding), path cap ở 72h; mfe/mae tới 180d + recoverDay/delisted cho outcome dài.

## Bức tranh tổng (retEnd_72h raw)
- Tổng +196.7. **Armed (maxFav72≥15%): +287** (n=1619). **Chưa-arm: −78** (n=1336) = phần kéo lùi.
- **Worst 10% lệnh = 61% toàn bộ loss.** Đuôi tập trung.

## PATTERN A — entry đỉnh-pump rồi dump: CÓ THẬT nhưng KHÔNG cứu được bằng exit
- Định nghĩa forward (maxFav24<5% & maxAdv24<−15%): **252 lệnh (8.5%), −27 P&L, maeFinal med −60%.**
- **Không tách được sớm khỏi dip-then-pump:** trong nhóm dip-first (63%), nhóm "không có favorable trong 12h" (nghi đỉnh-dump) vẫn **24% thành winner** và median retEnd72 **+2%** → cắt là giết luôn 24% hồi.
- Sim "cắt khi chưa favorable & đang lỗ" @12h/24h: **net ÂM** (tổng 205→189/202), tail cải thiện tí, false-cut 10-12%. → cắt sớm phá edge (edge nở 12–72h).
- **VERDICT A: không có exit-side nào cứu.** Đòn bẩy duy nhất = selection/sizing (đừng vào / size nhỏ coin dễ dump), không phải exit.

## PATTERN B — dump dài rồi chết: drag có thật, nhưng exit ngắn KHÔNG cứu; cần time-stop DÀI (chưa test được)
- slow_death (mae3d>−20% nhưng cuối cùng chết): **373 lệnh**, maeFinal med −66%, **nhưng tại 72h vẫn +5.4%**. 58% trong số này ĐÃ arm (+15%) rồi mới chết.
- Bẫy: **max-hold phẳng 72h cắt 58% winner** (winner có sóng lớn SAU 72h: mfe30d > maxFav72+15%). → không dùng max-hold phẳng.
- Time-stop CÓ ĐIỀU KIỆN (chỉ cắt coin CHƯA arm) @12h/24h: **net ÂM** (−51/−12), vì "chưa arm @12-24h" bắt trúng **75% bloomer** (edge nở muộn). @72h = trùng baseline (không kết luận được — data cap 72h).
- **VERDICT B: exit ngắn (≤72h) không cứu được** — vì edge nở 12–72h, coin-sắp-chết và coin-sắp-nở NHÌN GIỐNG NHAU trong 72h đầu. Ứng viên duy nhất khả dĩ = **time-stop DÀI (5–10 ngày) chỉ cho coin chưa-có-lãi** (sau khi cửa sổ nở đã qua). **KHÔNG test được từ file path (cap 72h)** → phải chạy WFO sim.

## KẾT LUẬN CHUNG (flaws-first)
Không có luật exit-theo-giá/thời-gian NGẮN nào cứu được A hay B — vì đuôi trái và winner **không tách được trong 72h đầu** (edge nở muộn). Đây là kết quả âm nhất quán qua mọi lát cắt. 2 đòn bẩy còn thực:
1. **Time-stop DÀI (TIME_STOP_HOURS ~120–240h) chỉ cho lệnh chưa-arm** — ứng viên chính cho pattern B, cắt loser-rot sau khi bloom-window qua. **CẦN A/B trong WFO sim** (có fee/funding + path đầy đủ, không bị cap 72h). Khả thi: TIME_STOP_HOURS là env Configs worker đọc (không dính vụ arm-hook trước đó).
2. **Selection/sizing** (lọc/size nhỏ coin mới-list <30d — collapse doc PH4): độc lập exit, giảm cả A lẫn B ở gốc.

## Đề xuất bước tiếp (tính tiếp)
A/B **TIME_STOP_HOURS ∈ {off, 120, 168, 240}** trên WFO full-18w (DCA-off, K5, arm hiện tại), đo net PnL + maxdd + %quý dương (deflated-t/1SE/worst-window), confirm 2026 holdout. Đây là cách DUY NHẤT test được time-stop dài mà path-data không làm được. Song song: đo lift của filter coin mới-list.
Lưu ý: exit_sweep cũ cho thấy TRAILING lỏng (RATE_PROFIT 0.10, giữ 4.3d) = −4587 — nhưng đó là trailing lỏng, KHÁC hard time-stop; nên vẫn đáng test TIME_STOP_HOURS riêng.

## File: /tmp/disaster.py, /tmp/disaster2.py (Oracle); nguồn entry_paths/entry_pathstats_g008.
