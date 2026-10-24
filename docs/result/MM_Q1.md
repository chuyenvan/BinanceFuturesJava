# MM_Q1 — Pilot markout market making thụ động lúc thị trường YÊN (kết quả)

Prereg: `docs/prereg/PREREG_MM_Q1.md` (commit e2766839, sha256 7d34902d…b8e3) + `PREREG_MM_Q1_ADDENDUM1.md` (commit e43b09b4, sha256 ae20c650…0315). Code: `research/mm_q1/`. Artefact: `docs/result/mm_q1/` (lần 2 = chính thức; `run1_before_addendum/` = số trước sửa bug). Không có dữ liệu thô cryptohftdata trong repo (chỉ thống kê theo symbol-giờ).

## Verdict: NO-GO ⇒ ĐÓNG họ MM thụ động retail (theo §8)
- Tiêu chí (L = 300 ms, fill bảo thủ, d0, h = 60 s, net sau phí maker 2 bps): KHÔNG tier nào đạt ở kỳ nào. Net/fill: lớn −3,26 / −3,16 bps (D / K), vừa −4,15 / −4,03, nhỏ −4,60 / −6,22; cận TRÊN CI 95 % đều < −3 bps. Biến thể +1 tick (ỨNG VIÊN) cũng trượt: −3,10 … −7,46 bps.
- Âm cả TRƯỚC phí: gross (adverse selection) từ −0,85 tới −6,38 bps/fill ở MỌI tổ hợp (144) L ∈ {0, 100, 300} ms × d ∈ {0, +1 tick} × rule ∈ {bảo thủ, lạc quan} × h ∈ {1, 10, 60, 300} s × tier × kỳ; net tốt nhất −2,85 bps, cận trên CI95 tốt nhất −2,96 bps (Bảng 2–3, `mm_q1/configs.csv`). Muốn hoà vốn cần rebate maker > ~0,9–6 bps/fill, vượt xa mọi bậc phí retail.
- Điều kiện fill/giờ (≥ 20) đạt dư ở hầu hết tier (lớn 641–1 019 fill/50 phút) — vấn đề là edge âm, không phải thiếu fill.
- Độ trễ làm xấu thêm có hệ thống: L 300 ms so với 0 ms có gross thấp hơn ở 100 % tổ hợp (0,04–3,45 bps) và nhiều fill hơn ở 92 % tổ hợp (quote cũ bị "ăn").
- Ước lợi nhuận thô (1 lot 100 USD/fill, không inventory risk): tier lớn −486 … −797 USD/ngày/symbol; vừa −310 … −549; nhỏ −73 … −189.

## Rủi ro / giới hạn (đọc trước khi dùng số)
1. Fill bảo thủ = cận dưới theo cấu trúc: chỉ fill khi trade XUYÊN mức quote ⇒ mọi fill đều kèm giá đi qua mình ≥ 1 tick. Không đo được trường hợp lệnh nằm đầu hàng đợi lâu (fill tại touch không xuyên). Biến thể lạc quan (queue ahead = qty mức đó trong sổ, cửa sổ 1 s) chỉ thêm ít fill và vẫn âm (gross −0,85 … −5,60 bps mọi tổ hợp). Một MM thật có queue priority (nhiều giờ nằm sẵn, độ trễ thấp) có thể khác — nhưng đó không phải hồ sơ retail 242 (300 ms).
2. Quote độc lập mỗi giây, 1 đơn vị, không quản inventory, không giới hạn vị thế — đây là phép đo markout/fill, không phải backtest chiến lược.
3. Sổ dựng từ RỖNG (không snapshot), bỏ 300 s warm-up. V1 ≥ 99 % ở mọi tier-kỳ trừ nhỏ-K 98,71 % (PORTAL-K 98,2 %; min theo giờ 94,8 %) ⇒ theo §8(iv) tier nhỏ kỳ K là "KHÔNG ĐO ĐƯỢC" — không ảnh hưởng verdict (net vẫn −6,2 bps).
4. Tiêu chí yên dùng dự phòng |r_sym| < 2 %, |r_BTC| < 1 % cho mọi giờ (I_mkt/EW-alt 2026 không tính được trên Oracle) + loại ±6 h quanh đợt MKT ở D. Mô tả: trong 71 giờ lịch D được nhận, 5 giờ sẽ trượt |EW-alt 1h| ≥ 1,5 % và 3 giờ có bucket I_mkt ≥ θ_MKT nếu áp LIQX_S1 (không lọc).
5. Giờ mẫu dùng chung thứ tự ứng viên ⇒ chỉ 63–70 giờ lịch khác nhau mỗi tier-kỳ; CI bootstrap theo cụm GIỜ lịch đã phản ánh điều này (CI vẫn rất hẹp vì hiệu ứng lớn và đồng nhất giữa symbol/giờ trong ngày).
6. Hai bug dữ liệu phát hiện SAU khi thấy kết quả lần 1 ⇒ ADDENDUM1, chạy lại toàn bộ (mục dưới). Sửa bug làm kết quả XẤU hơn (đúng chiều kỳ vọng: fill giả không có adverse selection), không đổi verdict.

## ADDENDUM1 — số trước/sau (L300, cons, d0, h60, net bps/fill)
| tier | D lần 1 | D lần 2 | K lần 1 | K lần 2 |
|---|---|---|---|---|
| lớn | −3,08 | −3,26 | −2,90 | −3,16 |
| vừa | −4,15 | −4,15 | −3,97 | −4,03 |
| nhỏ | −4,63 | −4,60 | −5,29 | −6,22 |
- Bug 1 (chính): file trades cryptohftdata có hàng `order_type = NA`, price = 0, qty = 0 (127 149 hàng trong 1 440 symbol-giờ; 0,21 % trade tier lớn, 0,02 % vừa, 0,006 % nhỏ; 0 hàng NA có giá ≠ 0) ⇒ tạo fill BID giả. Phát hiện nhờ V5 (tỉ lệ lần 1 = 858 ở tier lớn). Ngoài NA còn `INSURANCE_FUND` (giá thật, giữ).
- Bug 2: kline cryptohftdata không phải nến đóng (1 bản tin/phút, nhận ~0,4–1 s sau khi nến MỞ) ⇒ r_1h lần 1 ≈ 59 phút; V2b lần 1 lệch 649/720 giờ (max 0,45 %). Lần 2 r từ trades.
- Điểm 3: từ 2026-04 orderbook có hàng snapshot (non-update) — lần 2 loại giờ có snapshot (30 ứng viên K, hầu hết cũng đứt pu).

## Validation (lần 2)
- V1: tier-kỳ 98,71–99,64 % (Bảng 1); theo symbol-giờ min 94,8 %, p5 98,9 %. Trượt ngưỡng 99 % duy nhất: nhỏ-K (xem rủi ro 3).
- V2: ts int64 (assert E, trade_time); trade_id trùng 0; trade không bội tick 0; message trùng 0; E không nhất quán trong message 0; mọi symbol-giờ đủ 3 000 mốc quote; hàng non-update trong giờ nhận 0. V2b: r_1h từ trades vs kline Oracle: 656/720 khớp < 1e-9; 64 lệch ≤ 0,09 % (≈ 1 tick) — ĐÃ GIẢI THÍCH: 1–3 trade cuối giờ nằm ở file giờ sau (file chia theo received_time; kiểm 4 ca: hợp file H, H+1 ⇒ khớp close Oracle). Không ảnh hưởng mô phỏng (mốc quote dừng ở 3 300 s).
- V3: script độc lập `mm_v3.py` (Decimal, sổ list sắp xếp + bisect, vòng Python thuần; không import pipeline) trên SOLUSDT và NEOUSDT 2025-07-19 22:00: 108/108 khoá cons + 108/108 opt khớp, max |Δ Σ markout| = 0,0 (< 1e-9); kiểm cả lần 1 và lần 2 (lần 2 bỏ 13 / 1 trade giá 0 độc lập).
- V4: 5 fill SOL + 5 fill NEO in tay (`mm_q1/v3_v4_*.log`): sổ dùng có E ≤ t − 300 ms, giá quote = best bid/ask, trade kích hoạt là SELL (is_buyer_maker = true) giá < quote (hoặc BUY > quote cho ask), trong cửa sổ [t, t+1 s); mid(t_fill + 60 s) và markout tái tính độc lập trùng. Vd SOL bid 175,33, trade bán 175,32 @ …704 820, mid60 = 175,455 ⇒ +7,13 bps; NEO ask 7,035, mid60 7,0545 ⇒ −27,7 bps (dấu đúng).
- V5: quote tại mid, tỉ lệ AS0/(−nửa spread) = 1,04 (lớn 1,04; vừa 1,06; nhỏ 1,03) ∈ [0,8; 2,0] ⇒ đạt (lần 1 trượt do bug 1).

## Dữ liệu nguồn — lưu ý cho task khác dùng cryptohftdata (CHƯA có trong kết luận chd)
- trades: có in giá 0 / qty 0 (`NA`) — PHẢI lọc trước khi dùng giá trade (min/max, fill, VWAP…).
- kline: bản tin không phải nến đóng — không dùng close/high/low/volume của file kline như nến 1m.
- orderbook: từ 2026-04 có snapshot xen kẽ, thường đi kèm đứt pu (reconnect).
- Thiếu dữ liệu: BTC trades thiếu 11 giờ 2026-08-21…09-28 (rej_btc_r_missing); BTC/ETH/XRP thiếu file 2026-04-02 22h, 04-03 03h, 04-09 12h, 14h.

## Bảng chi tiết (sinh tự động bởi research/mm_q1/mm_report.py)

**Bảng 1 — Tiêu chí, lần chạy 2 (ADDENDUM1, CHÍNH THỨC)** (L = 300 ms, cons, h = 60 s; bps/fill; CI 95 % bootstrap theo giờ lịch)

| d | tier | kỳ | n sym-giờ | n fill | gross | net | CI95 net | fill/giờ trung vị (3 000 s) | V1 | đạt? |
|---|---|---|---|---|---|---|---|---|---|---|
| d0 | big | D | 240 | 291041 | -1.26 | -3.26 | [-3.35, -3.18] | 1018.5 | 99.53 % | KHÔNG |
| d0 | big | K | 240 | 189420 | -1.16 | -3.16 | [-3.25, -3.07] | 641.0 | 99.64 % | KHÔNG |
| d0 | mid | D | 240 | 172497 | -2.15 | -4.15 | [-4.35, -3.97] | 551.0 | 99.45 % | KHÔNG |
| d0 | mid | K | 240 | 120230 | -2.03 | -4.03 | [-4.16, -3.90] | 320.5 | 99.34 % | KHÔNG |
| d0 | small | D | 240 | 66741 | -2.60 | -4.60 | [-4.85, -4.39] | 171.0 | 99.34 % | KHÔNG |
| d0 | small | K | 240 | 21463 | -4.22 | -6.22 | [-7.19, -5.10] | 49.0 | 98.71 % | KHÔNG |
| d1 | big | D | 240 | 254216 | -1.22 | -3.22 | [-3.32, -3.14] | 847.5 | 99.53 % | KHÔNG |
| d1 | big | K | 240 | 147950 | -1.10 | -3.10 | [-3.19, -3.02] | 435.0 | 99.64 % | KHÔNG |
| d1 | mid | D | 240 | 115703 | -2.02 | -4.02 | [-4.27, -3.80] | 290.0 | 99.45 % | KHÔNG |
| d1 | mid | K | 240 | 76210 | -1.84 | -3.84 | [-3.99, -3.69] | 133.5 | 99.34 % | KHÔNG |
| d1 | small | D | 240 | 39523 | -2.33 | -4.33 | [-4.68, -4.02] | 71.5 | 99.34 % | KHÔNG |
| d1 | small | K | 240 | 9202 | -5.46 | -7.46 | [-8.87, -4.81] | 13.0 | 98.71 % | KHÔNG |

**Bảng 1b — Tiêu chí, lần chạy 1 (TRƯỚC sửa bug; chỉ để so)** (L = 300 ms, cons, h = 60 s; bps/fill; CI 95 % bootstrap theo giờ lịch)

| d | tier | kỳ | n sym-giờ | n fill | gross | net | CI95 net | fill/giờ trung vị (3 000 s) | V1 | đạt? |
|---|---|---|---|---|---|---|---|---|---|---|
| d0 | big | D | 240 | 315881 | -1.08 | -3.08 | [-3.17, -3.00] | 1150.0 | 99.48 % | KHÔNG |
| d0 | big | K | 240 | 206329 | -0.90 | -2.90 | [-2.97, -2.83] | 722.5 | 99.61 % | KHÔNG |
| d0 | mid | D | 240 | 175547 | -2.15 | -4.15 | [-4.37, -3.95] | 562.5 | 99.23 % | KHÔNG |
| d0 | mid | K | 240 | 119756 | -1.97 | -3.97 | [-4.09, -3.85] | 317.0 | 99.30 % | KHÔNG |
| d0 | small | D | 240 | 66527 | -2.63 | -4.63 | [-4.88, -4.42] | 170.5 | 99.35 % | KHÔNG |
| d0 | small | K | 240 | 17524 | -3.29 | -5.29 | [-5.71, -4.93] | 47.0 | 99.78 % | KHÔNG |
| d1 | big | D | 240 | 279575 | -0.99 | -2.99 | [-3.09, -2.90] | 990.0 | 99.48 % | KHÔNG |
| d1 | big | K | 240 | 168488 | -0.71 | -2.71 | [-2.80, -2.61] | 526.5 | 99.61 % | KHÔNG |
| d1 | mid | D | 240 | 118547 | -2.01 | -4.01 | [-4.28, -3.78] | 311.0 | 99.23 % | KHÔNG |
| d1 | mid | K | 240 | 76556 | -1.76 | -3.76 | [-3.89, -3.62] | 133.0 | 99.30 % | KHÔNG |
| d1 | small | D | 240 | 39588 | -2.38 | -4.38 | [-4.73, -4.07] | 72.0 | 99.35 % | KHÔNG |
| d1 | small | K | 240 | 5871 | -2.91 | -4.91 | [-5.42, -4.51] | 12.0 | 99.78 % | KHÔNG |

**Bảng 2 — Mọi cấu hình ở h = 60 s, lần chạy 2** (net bps/fill [CI95]; fill/giờ trung vị)

| kỳ | tier | L ms | d | rule | gross | net [CI95] | fill/giờ |
|---|---|---|---|---|---|---|---|
| D | big | 0 | d0 | cons | -1.21 | -3.21 [-3.30, -3.13] | 871.0 |
| D | big | 0 | d0 | opt | -1.15 | -3.15 [-3.25, -3.08] | 912.5 |
| D | big | 0 | d1 | cons | -1.17 | -3.17 [-3.28, -3.09] | 708.0 |
| D | big | 0 | d1 | opt | -1.15 | -3.15 [-3.26, -3.07] | 718.5 |
| D | big | 100 | d0 | cons | -1.22 | -3.22 [-3.32, -3.14] | 927.0 |
| D | big | 100 | d0 | opt | -1.18 | -3.18 [-3.27, -3.11] | 972.0 |
| D | big | 100 | d1 | cons | -1.18 | -3.18 [-3.28, -3.10] | 750.5 |
| D | big | 100 | d1 | opt | -1.17 | -3.17 [-3.27, -3.09] | 764.5 |
| D | big | 300 | d0 | cons | -1.26 | -3.26 [-3.35, -3.18] | 1018.5 |
| D | big | 300 | d0 | opt | -1.23 | -3.23 [-3.31, -3.15] | 1065.0 |
| D | big | 300 | d1 | cons | -1.22 | -3.22 [-3.32, -3.14] | 847.5 |
| D | big | 300 | d1 | opt | -1.20 | -3.20 [-3.30, -3.12] | 868.5 |
| D | mid | 0 | d0 | cons | -1.93 | -3.93 [-4.13, -3.76] | 500.5 |
| D | mid | 0 | d0 | opt | -1.69 | -3.69 [-3.86, -3.54] | 645.5 |
| D | mid | 0 | d1 | cons | -1.81 | -3.81 [-4.06, -3.61] | 240.0 |
| D | mid | 0 | d1 | opt | -1.71 | -3.71 [-3.96, -3.51] | 257.0 |
| D | mid | 100 | d0 | cons | -2.03 | -4.03 [-4.23, -3.86] | 528.5 |
| D | mid | 100 | d0 | opt | -1.79 | -3.79 [-3.96, -3.64] | 659.0 |
| D | mid | 100 | d1 | cons | -1.92 | -3.92 [-4.16, -3.71] | 252.0 |
| D | mid | 100 | d1 | opt | -1.82 | -3.82 [-4.05, -3.62] | 270.0 |
| D | mid | 300 | d0 | cons | -2.15 | -4.15 [-4.35, -3.97] | 551.0 |
| D | mid | 300 | d0 | opt | -1.92 | -3.92 [-4.10, -3.76] | 676.5 |
| D | mid | 300 | d1 | cons | -2.02 | -4.02 [-4.27, -3.80] | 290.0 |
| D | mid | 300 | d1 | opt | -1.93 | -3.93 [-4.18, -3.72] | 306.0 |
| D | small | 0 | d0 | cons | -2.32 | -4.32 [-4.54, -4.13] | 156.5 |
| D | small | 0 | d0 | opt | -2.00 | -4.00 [-4.20, -3.83] | 303.0 |
| D | small | 0 | d1 | cons | -2.07 | -4.07 [-4.35, -3.82] | 62.5 |
| D | small | 0 | d1 | opt | -1.96 | -3.96 [-4.23, -3.72] | 74.5 |
| D | small | 100 | d0 | cons | -2.42 | -4.42 [-4.63, -4.23] | 160.0 |
| D | small | 100 | d0 | opt | -2.08 | -4.08 [-4.28, -3.92] | 300.0 |
| D | small | 100 | d1 | cons | -2.19 | -4.19 [-4.50, -3.91] | 64.5 |
| D | small | 100 | d1 | opt | -2.07 | -4.07 [-4.36, -3.80] | 77.0 |
| D | small | 300 | d0 | cons | -2.60 | -4.60 [-4.85, -4.39] | 171.0 |
| D | small | 300 | d0 | opt | -2.25 | -4.25 [-4.46, -4.08] | 297.5 |
| D | small | 300 | d1 | cons | -2.33 | -4.33 [-4.68, -4.02] | 71.5 |
| D | small | 300 | d1 | opt | -2.20 | -4.20 [-4.53, -3.91] | 79.5 |
| K | big | 0 | d0 | cons | -1.12 | -3.12 [-3.21, -3.04] | 548.5 |
| K | big | 0 | d0 | opt | -1.07 | -3.07 [-3.16, -3.00] | 567.0 |
| K | big | 0 | d1 | cons | -1.06 | -3.06 [-3.14, -2.98] | 355.0 |
| K | big | 0 | d1 | opt | -1.04 | -3.04 [-3.13, -2.96] | 365.5 |
| K | big | 100 | d0 | cons | -1.13 | -3.13 [-3.21, -3.05] | 579.0 |
| K | big | 100 | d0 | opt | -1.09 | -3.09 [-3.17, -3.01] | 605.5 |
| K | big | 100 | d1 | cons | -1.06 | -3.06 [-3.15, -2.98] | 383.5 |
| K | big | 100 | d1 | opt | -1.05 | -3.05 [-3.13, -2.97] | 391.0 |
| K | big | 300 | d0 | cons | -1.16 | -3.16 [-3.25, -3.07] | 641.0 |
| K | big | 300 | d0 | opt | -1.13 | -3.13 [-3.22, -3.04] | 667.0 |
| K | big | 300 | d1 | cons | -1.10 | -3.10 [-3.19, -3.02] | 435.0 |
| K | big | 300 | d1 | opt | -1.08 | -3.08 [-3.17, -3.00] | 443.0 |
| K | mid | 0 | d0 | cons | -1.87 | -3.87 [-3.99, -3.74] | 291.0 |
| K | mid | 0 | d0 | opt | -1.62 | -3.62 [-3.72, -3.53] | 418.5 |
| K | mid | 0 | d1 | cons | -1.66 | -3.66 [-3.82, -3.52] | 112.0 |
| K | mid | 0 | d1 | opt | -1.54 | -3.54 [-3.70, -3.40] | 119.5 |
| K | mid | 100 | d0 | cons | -1.94 | -3.94 [-4.06, -3.81] | 298.5 |
| K | mid | 100 | d0 | opt | -1.68 | -3.68 [-3.79, -3.58] | 416.5 |
| K | mid | 100 | d1 | cons | -1.74 | -3.74 [-3.89, -3.59] | 121.0 |
| K | mid | 100 | d1 | opt | -1.61 | -3.61 [-3.76, -3.47] | 129.0 |
| K | mid | 300 | d0 | cons | -2.03 | -4.03 [-4.16, -3.90] | 320.5 |
| K | mid | 300 | d0 | opt | -1.78 | -3.78 [-3.89, -3.68] | 432.0 |
| K | mid | 300 | d1 | cons | -1.84 | -3.84 [-3.99, -3.69] | 133.5 |
| K | mid | 300 | d1 | opt | -1.73 | -3.73 [-3.88, -3.58] | 140.0 |
| K | small | 0 | d0 | cons | -3.14 | -5.14 [-5.52, -4.86] | 44.5 |
| K | small | 0 | d0 | opt | -2.41 | -4.41 [-4.72, -4.15] | 91.5 |
| K | small | 0 | d1 | cons | -2.49 | -4.49 [-5.30, -4.21] | 12.0 |
| K | small | 0 | d1 | opt | -2.13 | -4.13 [-4.79, -3.90] | 13.0 |
| K | small | 100 | d0 | cons | -3.47 | -5.47 [-5.80, -4.99] | 46.5 |
| K | small | 100 | d0 | opt | -2.77 | -4.77 [-5.07, -4.42] | 90.0 |
| K | small | 100 | d1 | cons | -3.65 | -5.65 [-6.06, -4.61] | 12.0 |
| K | small | 100 | d1 | opt | -3.00 | -5.00 [-5.30, -4.30] | 13.0 |
| K | small | 300 | d0 | cons | -4.22 | -6.22 [-7.19, -5.10] | 49.0 |
| K | small | 300 | d0 | opt | -3.15 | -5.15 [-5.83, -4.50] | 90.5 |
| K | small | 300 | d1 | cons | -5.46 | -7.46 [-8.87, -4.81] | 13.0 |
| K | small | 300 | d1 | opt | -4.50 | -6.50 [-7.58, -4.53] | 14.0 |

**Bảng 3 — Theo horizon (L300, cons, d0), lần chạy 2: gross = adverse selection trước phí**

| kỳ | tier | h=1 s | h=10 s | h=60 s | h=300 s |
|---|---|---|---|---|---|
| D | big | -1.05 / -3.05 | -1.20 / -3.20 | -1.26 / -3.26 | -1.22 / -3.22 |
| D | mid | -1.88 / -3.88 | -2.03 / -4.03 | -2.15 / -4.15 | -2.16 / -4.16 |
| D | small | -2.26 / -4.26 | -2.51 / -4.51 | -2.60 / -4.60 | -2.61 / -4.61 |
| K | big | -1.07 / -3.07 | -1.22 / -3.22 | -1.16 / -3.16 | -1.03 / -3.03 |
| K | mid | -1.93 / -3.93 | -2.08 / -4.08 | -2.03 / -4.03 | -2.05 / -4.05 |
| K | small | -3.68 / -5.68 | -3.94 / -5.94 | -4.22 / -6.22 | -4.52 / -6.52 |

(ô = gross / net, bps/fill)


**Bảng 4 — Theo symbol (L300, cons, d0, h60), lần chạy 2**

| kỳ | symbol | tier | spread trung vị bps (tick) | V1 % (min giờ) | fill/giờ | gross | net [CI95] |
|---|---|---|---|---|---|---|---|
| D | BTCUSDT | big | 0.009 (1.0) | 99.80 (99.3) | 691.5 | -1.18 | -3.18 [-3.27, -3.10] |
| D | ETHUSDT | big | 0.029 (1.0) | 99.35 (97.8) | 1354.0 | -1.14 | -3.14 [-3.20, -3.08] |
| D | SOLUSDT | big | 0.599 (1.0) | 99.64 (98.9) | 1179.5 | -1.34 | -3.34 [-3.45, -3.22] |
| D | XRPUSDT | big | 0.392 (1.0) | 99.52 (97.5) | 1021.5 | -1.39 | -3.39 [-3.56, -3.26] |
| D | 1000SHIBUSDT | mid | 0.846 (1.0) | 99.84 (99.0) | 369.0 | -2.00 | -4.00 [-4.18, -3.84] |
| D | NEIROUSDT | mid | 3.718 (1.0) | 99.89 (99.6) | 95.0 | -2.41 | -4.41 [-4.88, -4.04] |
| D | TAOUSDT | mid | 0.306 (1.0) | 99.12 (97.0) | 944.0 | -1.97 | -3.97 [-4.19, -3.75] |
| D | VIRTUALUSDT | mid | 0.880 (1.0) | 99.48 (97.4) | 749.0 | -2.40 | -4.40 [-4.76, -4.08] |
| D | MASKUSDT | small | 0.833 (1.0) | 99.65 (98.8) | 234.0 | -2.39 | -4.39 [-4.60, -4.19] |
| D | NEOUSDT | small | 1.774 (1.0) | 99.81 (99.2) | 142.5 | -2.46 | -4.46 [-4.99, -4.03] |
| D | NXPCUSDT | small | 1.828 (1.5) | 98.89 (95.3) | 230.0 | -2.61 | -4.61 [-4.98, -4.27] |
| D | PORTALUSDT | small | 4.334 (1.0) | 99.16 (94.8) | 134.5 | -3.05 | -5.05 [-5.52, -4.58] |
| K | BTCUSDT | big | 0.014 (1.0) | 99.70 (98.0) | 654.0 | -1.06 | -3.06 [-3.15, -2.97] |
| K | ETHUSDT | big | 0.049 (1.0) | 99.47 (98.2) | 928.5 | -1.04 | -3.04 [-3.14, -2.94] |
| K | SOLUSDT | big | 1.216 (1.0) | 99.92 (99.6) | 411.0 | -1.37 | -3.37 [-3.55, -3.21] |
| K | XRPUSDT | big | 0.723 (1.0) | 99.81 (99.4) | 410.0 | -1.34 | -3.34 [-3.44, -3.23] |
| K | 1000SHIBUSDT | mid | 1.729 (1.0) | 99.85 (99.4) | 162.5 | -2.09 | -4.09 [-4.32, -3.85] |
| K | NEIROUSDT | mid | 1.772 (1.0) | 99.54 (97.9) | 192.5 | -2.48 | -4.48 [-4.86, -4.15] |
| K | TAOUSDT | mid | 0.414 (1.0) | 99.06 (98.4) | 917.0 | -1.79 | -3.79 [-3.91, -3.66] |
| K | VIRTUALUSDT | mid | 1.519 (1.0) | 99.73 (98.9) | 379.5 | -2.29 | -4.29 [-4.48, -4.10] |
| K | MASKUSDT | small | 2.289 (1.0) | 99.83 (99.0) | 89.5 | -3.02 | -5.02 [-5.54, -4.56] |
| K | NEOUSDT | small | 3.682 (1.0) | 99.98 (99.8) | 34.0 | -3.10 | -5.10 [-5.77, -4.54] |
| K | NXPCUSDT | small | 3.588 (1.0) | 99.70 (95.2) | 47.0 | -3.35 | -5.35 [-5.89, -4.82] |
| K | PORTALUSDT | small | 8.190 (1.0) | 98.25 (97.8) | 30.5 | -5.80 | -7.80 [-8.73, -5.27] |

**Bảng 5 — Mô tả tier: spread, giờ trong ngày (UTC), lợi nhuận/ngày thô (1 lot 100 USD/fill, KHÔNG tính inventory risk), lần chạy 2**

| kỳ | tier | spread bps | net h60 [0,8) | [8,16) | [16,24) | fill/giờ | USD/ngày/symbol (×1,2) |
|---|---|---|---|---|---|---|---|
| D | big | 0.162 | -3.26 | -3.15 | -3.34 | 1018.5 | -797 (-957) |
| D | mid | 0.862 | -4.05 | -3.82 | -4.45 | 551.0 | -549 (-658) |
| D | small | 1.779 | -4.53 | -4.42 | -4.78 | 171.0 | -189 (-227) |
| K | big | 0.272 | -3.20 | -3.06 | -3.21 | 641.0 | -486 (-583) |
| K | mid | 1.544 | -4.06 | -3.89 | -4.17 | 320.5 | -310 (-372) |
| K | small | 3.662 | -6.92 | -5.12 | -5.98 | 49.0 | -73 (-88) |

**Bảng 6 — V5 (quote tại mid, L0): AS0 = side×(giá trade − m)/m; tỉ lệ = AS0/(−nửa spread)**

| tier | lần 2: AS0 bps | nửa spread bps | tỉ lệ | lần 1: tỉ lệ |
|---|---|---|---|---|
| big | -0.182 | 0.174 | 1.042 | 858.0 |
| mid | -0.706 | 0.665 | 1.061 | 15.8 |
| small | -1.743 | 1.684 | 1.035 | 1.6 |
| all | -0.458 | 0.437 | 1.046 | 237.7 |

**Bảng 7 — Ứng viên giờ đã duyệt theo lý do (lần chạy 2)**

| kỳ\|symbol | ok | rej_btc_r_missing | rej_btc_ret | rej_episode | rej_no_data | rej_pu | rej_snapshot | rej_sym_ret |
|---|---|---|---|---|---|---|---|---|
| D|1000SHIBUSDT | 60 | 0 | 4 | 8 | 0 | 1 | 0 | 1 |
| D|BTCUSDT | 60 | 0 | 4 | 8 | 0 | 3 | 0 | 0 |
| D|ETHUSDT | 60 | 0 | 4 | 8 | 0 | 3 | 0 | 1 |
| D|MASKUSDT | 60 | 0 | 4 | 8 | 0 | 1 | 0 | 3 |
| D|NEIROUSDT | 60 | 0 | 5 | 8 | 0 | 2 | 0 | 7 |
| D|NEOUSDT | 60 | 0 | 4 | 8 | 0 | 2 | 0 | 3 |
| D|NXPCUSDT | 60 | 0 | 4 | 8 | 0 | 2 | 0 | 2 |
| D|PORTALUSDT | 60 | 0 | 5 | 8 | 0 | 1 | 0 | 13 |
| D|SOLUSDT | 60 | 0 | 4 | 8 | 0 | 1 | 0 | 0 |
| D|TAOUSDT | 60 | 0 | 4 | 8 | 0 | 1 | 0 | 4 |
| D|VIRTUALUSDT | 60 | 0 | 5 | 8 | 0 | 1 | 0 | 7 |
| D|XRPUSDT | 60 | 0 | 4 | 8 | 0 | 3 | 0 | 1 |
| K|1000SHIBUSDT | 60 | 11 | 3 | 0 | 0 | 3 | 3 | 0 |
| K|BTCUSDT | 60 | 11 | 3 | 0 | 4 | 5 | 4 | 0 |
| K|ETHUSDT | 60 | 11 | 3 | 0 | 4 | 5 | 4 | 0 |
| K|MASKUSDT | 60 | 11 | 3 | 0 | 0 | 3 | 3 | 1 |
| K|NEIROUSDT | 60 | 11 | 3 | 0 | 1 | 3 | 1 | 1 |
| K|NEOUSDT | 60 | 11 | 3 | 0 | 0 | 2 | 4 | 0 |
| K|NXPCUSDT | 60 | 11 | 3 | 0 | 0 | 5 | 4 | 4 |
| K|PORTALUSDT | 60 | 11 | 3 | 0 | 0 | 5 | 2 | 6 |
| K|SOLUSDT | 60 | 11 | 3 | 0 | 0 | 2 | 2 | 0 |
| K|TAOUSDT | 60 | 11 | 3 | 0 | 0 | 5 | 2 | 4 |
| K|VIRTUALUSDT | 60 | 11 | 3 | 0 | 0 | 6 | 2 | 6 |
| K|XRPUSDT | 60 | 11 | 3 | 0 | 4 | 5 | 4 | 0 |
