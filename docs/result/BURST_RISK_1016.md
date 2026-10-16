# BURST_RISK_1016 — rủi ro theo đợt của hệ K24+skipFull (MASTER 2026-10-16, mô tả, 0 phép thử)

Nguồn: sim `gqsf-a1` printDone (2021-07-09 → 2025-11-21, 3 541 lệnh, vốn đầu 35 000, equity realized cuối 146 079). Script `/tmp/m1016_risk.py`, output `/tmp/m1016_bursts.csv` (Oracle).
Equity tại đợt = vốn đầu + Σpnl các lệnh đã đóng trước thời điểm đó (REALIZED, không MTM ⇒ đánh giá thấp mức lỗ tạm thời).
Lưu ý: 2021–2025 là DEV của hệ.

| cỡ đợt | n đợt | PnL đợt/equity p5 · p50 · min | margin đợt/equity p50 · p95 · max | tổng margin mở/equity p95 · max |
|---|---|---|---|---|
| 1–5 | 622 | −0,23 % · +0,05 % · −2,03 % | 1 · 5 · 10 % | 48 · 52 % |
| 6–12 | 91 | −0,32 % · +0,51 % · −2,64 % | 10 · 20 · 22 % | 48 · 49 % |
| 13–24 | 88 | −1,87 % · +0,95 % · **−9,82 %** | **26 · 36 · 36 %** | 48 · 52 % |

10 đợt tệ nhất (PnL/equity): 2022-05-05 22:09 (18 lệnh) **−9,82 %**; 2021-12-04 (22) −4,09 %; 2022-11-09 (18) −3,47 %; 2022-05-05 22:50 (9) −2,64 %; 2023-03-03 (24) −2,23 %; 2025-10-01 (1) −2,03 %; 2025-03-02 (19) −1,91 %; 2024-04-13 (20) −1,78 %; 2022-05-05 22:25 (3) −1,67 %; 2023-10-16 (23) −1,65 %.
Ngày vào lệnh tệ nhất: 2022-05-05 **−6 558 (~−14,8 % equity, 3 đợt trong 41 phút)**; 2025-03-02 −2 460; 2025-10-01 −2 376; 2022-11-09 −2 120; 2024-06-08 −1 845.
maxDD realized −15,05 % (2022-05-12). maxDD MTM theo bảng 8 seed: −22,6 %.

## Đọc
- Một đợt lớn đặt 26–36 % equity margin vào ~20 coin cùng tick, tương quan ≈ 1 ⇒ về rủi ro là MỘT lệnh.
- "Trần theo đợt" (hướng C) ≈ trục K: K16 vs K24 đã đo (CAGR22 32,8 vs 37,0; maxDD −18,9 vs −22,6; Calmar 1,74 vs 1,65), owner chọn K24 ngày 10-05 ⇒ C KHÔNG phải nghiên cứu mới, là quyết định khẩu vị.
- Rủi ro đuôi tập trung ở ngày sụp đổ hệ thống (LUNA 2022-05, FTX 2022-11): nhiều đợt liên tiếp trong cùng ngày. Đây là chỗ một luật ngắt mạch ngày (circuit breaker) có cơ chế rõ, ít bậc tự do.
- Số liệu cho kill-switch: lỗ 1 đợt tối đa ~10 % equity, lỗ 1 ngày ~15 %, DD MTM ~23 %.
