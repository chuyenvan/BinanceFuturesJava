# USDC_X14 — Bao nhiêu crash-buy X14 có thể đi qua USDC-M, tiết kiệm phí bao nhiêu

Phép ĐO MÔ TẢ (không prereg tiêu chí GO, không PnL mới). Ngưỡng "đáng làm" do MASTER nêu trong yêu cầu: giao > 30 % notional VÀ độ sâu USDC >= 50 % USDT ở leg mẫu. Dữ liệu: printDone 8 seed `tsx-x14-{a1,s123,s13,s2024,s21,s7,s777,s99}` (2022-01 → 2025-12, entry theo UTC = start − 7h), Binance Vision S3 (listing, bookDepth, kline 1m; KHÔNG REST). Code + CSV: `~/claude_master/usdcx14_wk/` (step2_overlap.py, step3_liq.py, list_usdc.py).

## Kết luận
**KHÔNG đáng làm.** Giao PIT chỉ 2,09 % notional / 1,71 % leg / 1,42 % PnL (8 seed, 2022–25) — xa ngưỡng 30 %. Ngay cả cận trên không-PIT (symbol nào từng có USDC-M, bất kể ngày) chỉ 9,9 % notional. Độ sâu sổ USDC +1 % bằng trung vị 11,6 % USDT (chỉ 3/28 leg mẫu đạt >= 50 %) — xa ngưỡng. Tiết kiệm phí ≈ 3 USD/năm ở vốn sim (≈ 0,004 %/năm), trượt giá thêm ước thô ăn ~2/3 khoản đó.

## 1. Symbol USDC-M (Vision S3, ngày file daily kline đầu tiên)
40 symbol `*USDC` có trên Vision (vs 1069 symbol USDT-M; X14 chạm 530 symbol riêng biệt). Số symbol có file (chưa delist) tại: 2024-01-04 = 5 (BTC, ETH, BNB, SOL, XRP); 2024-06-30 = 26; 2024-12-31 = 26; 2025-06-30 = 34; 2025-12-31 = 38; 2026-10-23 = 39 (MATICUSDC chỉ 2024-04-25 → 2024-09-11).
**Giới hạn PIT quan trọng:** Vision không có USDC-M trước 2024-01-04, kể cả BTC/ETH — đó là ngày bắt đầu có DỮ LIỆU, không chắc là ngày niêm yết thật (BTC/ETH USDC-M có thể đã niêm yết sớm hơn — CHƯA XÁC MINH, không gọi REST được). Hệ quả: giao 2022–2023 = 0 theo cấu trúc. Độ nhạy "5 symbol lõi coi như đã có từ 2022": giao tổng chỉ tăng lên 2,45 % notional (bảng dưới).

## 2. Giao leg X14 ∩ USDC-M (PIT: entry >= 00:00 UTC ngày file đầu và <= ngày file cuối)
Mapping `XXX` → `XXXUSDT` (530/530 symbol có trong universe Vision) và `XXXUSDC`. Notional = cột `margin` (= quantity*entry, sai lệch < 0,03 %, margin 1x); PnL = cột `pnl` (tổng khớp equity_final − 35000 của result.json cho cả 8 seed). Số: trung bình 8 seed [min–max].

| Năm | leg/seed | leg giao | % leg | % notional | % PnL |
|---|---|---|---|---|---|
| 2022 | 607 | 0 | 0 | 0 | 0 |
| 2023 | 759 | 0 | 0 | 0 | 0 |
| 2024 | 842 | 43,3 | 5,14 [4,85–5,37] | 5,52 [5,20–5,78] | 3,55 [2,58–5,66] |
| 2025 | 740 | 7,3 | 0,98 [0,94–1,14] | 0,74 [0,69–0,92] | 0,70 [0,57–1,19] |
| **2022–25** | 2948 | 50,5 | **1,71 [1,60–1,83]** | **2,09 [1,96–2,21]** | **1,42 [1,02–2,10]** |

Trung bình/seed 2022–25: notional tổng 3,04 M USD, giao 63,5 k; PnL tổng 115,7 k USD, phần giao +1,65 k. Tập giao gồm 404 leg gộp (90 sự kiện (symbol, phút vào) duy nhất), tập trung WIF, 1000PEPE, CRV, DOGE, SUI, 1000BONK.
Cận trên không-PIT ("symbol từng có USDC-M"): 2022 9,2/9,9/11,7; 2023 11,4/12,0/12,3; 2024 13,7/14,5/18,5; 2025 4,8/4,6/4,9; 2022–25 9,97/9,86/11,72 (% leg/notional/PnL) — vẫn < 30 %.
Phép kiểm độc lập (csv + vòng lặp thuần, không import pipeline): 23 583 leg, 404 giao, notional giao 508 351,5, PnL giao 13 218,8 — khớp tuyệt đối với pipeline chính.

## 3. Thanh khoản (30 sự kiện ngẫu nhiên từ 90, rng seed 20261024, bookDepth snapshot gần nhất <= phút vào, tuổi 0–30 s)
28/30 có bookDepth cả hai phía; 2 sự kiện (NEO, XRP, 2024-12-04 00:00:00) chưa có snapshot nào trong ngày <= giờ vào ⇒ loại khỏi tỷ lệ độ sâu (vẫn có volume). Độ sâu = cột `notional` (USD) trong bookDepth; phía MUA (taker buy ăn ask +1 %/+2 %).

| Chỉ số (USDC / USDT) | trung vị | IQR | p90 | max |
|---|---|---|---|---|
| ask +1 % | 0,116 | 0,094–0,226 | 0,469 | 0,848 |
| ask +2 % | 0,131 | 0,108–0,296 | 0,407 | 0,750 |
| bid −1 % | 0,137 | 0,063–0,242 | 0,601 | 133 (*) |
| volume 1h trước lệnh (quote) | 0,036 | 0,029–0,046 | 0,088 | 0,138 |

(*) 2025-10-11 USDT bid mỏng bất thường lúc sập ⇒ tỷ lệ phình; đọc theo trung vị. Chỉ 3/28 leg có ask+1 % USDC >= 50 % USDT (BOME 0,85, ETHFI 0,67, ENA 0,51); 0/30 leg có volume 1h >= 50 %.
Participation = notional lệnh / ask +1 %: USDC trung vị 1,0 % (p90 3,8 %, max 7,6 %) vs USDT 0,2 %. Lệnh sim ~0,5–2,6 k USD rất nhỏ so với sổ, nên trượt tuyệt đối nhỏ ở vốn này.

## 4. Ước tiết kiệm
Giả định: taker USDC-M 0,04 % vs 0,05 % USDT-M (CHƯA XÁC MINH chính thức), 0,01 %/chiều × 2 chiều × notional giao.

| Năm | tiết kiệm USD/seed (TB [min–max]) | % vốn đầu năm |
|---|---|---|
| 2022 | 0 | 0 |
| 2023 | 0 | 0 |
| 2024 | 11,0 [9,95–13,1] | 0,014 % |
| 2025 | 1,70 [1,54–2,29] | 0,001 % |
| TB 2022–25 | ≈ 3,2 USD/năm | ≈ 0,004 %/năm (so CAGR DEV ~27,6 %) |

Bound 100 % giao (mọi leg qua USDC-M): 3,04 M × 0,0002 ≈ 608 USD / 4 năm ≈ 152 USD/năm ≈ 0,21 %/năm vốn đầu năm TB (71 k) ≈ 0,53 % tổng PnL — kể cả kịch bản không thể xảy ra này cũng nhỏ.
Trượt giá thêm thô (book tuyến tính trong 1 %: slip ≈ 0,5 × notional/ask1 × 100 bps, chỉ mô tả định tính): USDC trung vị 0,48 bps (TB 0,81, p90 1,9, max 3,8) vs USDT trung vị 0,10 (TB 0,13). Chênh thêm khi vào: TB 0,68 bps, trung vị 0,37; 5/28 leg > 1 bps, 2/28 > 2 bps. Tiết kiệm 1 bps/chiều = 2 bps vòng; nếu thoát đối xứng, trượt thêm ~1,4 bps vòng ⇒ bù trừ ~2/3 khoản tiết kiệm (TB), âm ở đuôi (p90 ≈ 3,3 bps vòng). Đây là ước thô, bỏ qua khoảng trống trong sổ và độ sâu lúc sập (nhiều mẫu rơi 2024-11-12, 2024-12-09, 2025-10-11).

## Hạn chế / điểm nghi ngờ
- PIT = ngày file Vision đầu tiên (xem §1); 2022–23 = 0 theo cấu trúc. Độ nhạy lõi-5 và cận trên không-PIT đều < 10 % notional nên kết luận không phụ thuộc điểm này.
- Phí 0,04 % USDC-M chưa xác minh; chưa tính funding USDC-M khác USDT-M, chênh lệch spread, rủi ro USDC collateral/chuyển đổi.
- Mẫu thanh khoản: 28 leg từ 90 sự kiện; bookDepth là snapshot ~30 s, không phải sổ đầy đủ.
- Phần "PnL giao" là PnL gộp của các leg giao, không phải lợi ích của việc chuyển sàn.
- Sim fee model của X14 (RATE_FEE trong config) chưa đối chiếu với phí thật; khoản tiết kiệm 2 bps tính theo yêu cầu, không theo fee sim.
