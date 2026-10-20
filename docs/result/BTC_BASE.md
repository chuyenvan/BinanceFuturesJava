# BTC_BASE — sleeve BTC "lấp thời gian chờ" dưới crash-buy K24+skipFull (kết quả)

Ngày 2026-10-20. Pre-reg `docs/prereg/PREREG_BTC_BASE.md` commit **3173e50d** (gồm Bước 0; commit trước mọi phép đo overlay; sau đó
không đổi biến thể/lưới/G/phí/luật). Script `docs/result/btc_base/{px_build.py, bb_core.py, bb_step0.py, bb_run.py, bb_tab.py}`,
JSON `docs/result/btc_base/{step0.json, bb_res_small.json}`, bảng đầy đủ `bb_tab.md`. Chỉ đo hậu kiểm trên chân lệnh có sẵn
(ECMEAS bucket DEV, `ho4-k24-b` HO): 0 sim Java, 0 đụng 242/shadow/live, 0 Binance REST.

## 0. Kết luận

1. **(1) CAGR trong giới hạn DD: GO ở w\* = 0,3** (theo luật). O(0,3): CAGR22 **44,9 %** (median; [43,6; 47,4]) vs B0 35,8 % —
   ΔCAGR +8,9…+9,5pp, 8/8 seed. DD luật (tệ hơn của ngày/giờ, toàn kỳ DEV) **−37,8 % [−38,8; −30,5]** ≤ 40 %. w = 0,4/0,5 vượt
   (−47,1 / −54,5 % seed tệ nhất).
   **Nhưng rủi ro tăng nhanh hơn lợi nhuận**: Calmar 1,71 → 1,18; DD gần gấp đôi (−20,9 → −37,8); **DD phút seed tệ nhất −40,5 % (vượt 40 %)**
   — w\* đạt luật chỉ vì luật lấy mẫu giờ/ngày. Tháng tệ nhất −11,7 → −16,7 % (05/2022). Năm 2022: −9,6k (CB +1,4k, BTC −11,1k).
2. **(2) "Lấp chỗ trống" KHÔNG có giá trị theo luật ⇒ chỉ là beta allocation.** O(0,3) hơn S'(0,3) về CAGR22 8/8 seed (+10,9…+12,3pp)
   nhưng DD seed tệ nhất tệ hơn 3,2pp (−38,8 vs −35,6) > 2pp ⇒ FAIL. Quan trọng hơn: **cơ chế lấp chỗ trống không bao giờ kích hoạt ở w ≤ 0,4**
   — n_t max 0,52 nên G − n_t ≥ 0,48 > w ⇒ b\* ≡ w, b/E trung bình = 0,2999 = w, **0 lần bán RA** (w = 0,5: 5–10 lần/4,5 năm, 2,5k USD).
   O(w) thực chất = "crash-buy đủ size + w·E BTC rebalance ngày" (gross ≤ 0,82). Phần hơn S' (+11pp) là do không pha loãng crash-buy
   (dùng tiền nhàn rỗi = thêm phơi nhiễm), không phải do canh thời điểm.
3. **(3) Vào/ra khi nào:** với G = 1 thì không có quy tắc thời điểm nào có tác dụng — chỉ là giữ w·E BTC liên tục, rebalance 00:00 UTC.
   Thành phần thời điểm duy nhất làm thay đổi DD là bộ lọc T (chỉ báo cáo, xem §3) — cần pre-reg riêng.
4. **HO 2026 W9: CONFIRM (theo luật) nhưng gần như vô nghĩa về kinh tế.** ΔROI O(0,3) − B0 = +0,16…+0,28pp, 8/8 > 0; DD luật tệ nhất
   −13,7 % ≤ 40 %. Đổi lại DD W9 −4,6 → −13,2 % (median). BTC buy&hold W9 −3,7 % (DD giờ −40,3 %); BTC sleeve vẫn +1,0k nhờ rebalance
   ngày trong đường đi đi ngang; bản perp (trừ funding) ROI 10,39 % < B0 10,92 %.
5. Chia tĩnh S(w) **giảm** CAGR22 ở mọi w (8/8 seed; BTC chỉ ~+17 %/năm trong cửa sổ 2022–2025 < crash-buy ~36 %) và tăng DD.
6. Khuyến nghị (risk-first): **không** coi đây là "edge lấp chỗ trống". Nếu owner muốn tiêu ngân sách DD 40 % thì tham chiếu
   ISO_RISK B15 (crash-buy size ×1,5: CAGR22 45,1 %, maxDD22 phút −24,7 %, Calmar 1,83 — mode chi phí/cửa sổ khác, OFF ở đó 37,0 %/−22,5 %,
   chỉ so tương đối; chưa trừ impact thanh khoản): cùng mức CAGR, O(0,3) tốn thêm ~15pp DD. BTC beta là phơi nhiễm dễ có nhưng đắt về DD
   khi bear kéo dài (2022).

## 1. Kiểm vệ sinh

| kiểm | ngưỡng | đo | kết |
|---|---|---|---|
| V1 B0 tái lập | ≤ 0,3pp | DEV CAGR22/maxDD22/ΣPnL trùng ECMEAS tới 1e-9 (8/8); HO ROI/DD/eq0 W9 trùng ho_mtm.json (8/8) | PASS |
| V2 MTM missing | 0 | DEV 0 chân không giá, 0 phút thiếu sau ffill 60′; HO 0/0; BTC/ETH 0 phút thiếu | PASS |
| V3 O(w=0) ≡ B0 | ≤ 1e-6 USD | max \|ΔE\| 1,2e-10 (DEV), HO PASS | PASS |
| V4 n+b ≤ G sau RA | ≤ 1e-3 | max vượt 1,5e-5 (phí) | PASS |
| V5 không look-ahead | giao dịch trước mốc cắt không đổi khi xáo giá sau 2023-06-01 | O0.5, OT0.5, OE0.5, S0.5: 8/8 PASS | PASS |
| equity vòng sự kiện vs vector | ≤ 1e-9 | 2e-15 | PASS |

Sự cố: lần chạy 1 dừng vì IndexError trong hàm xáo giá V5 (chỉ số ngày vượt cửa sổ) **trước khi in bất kỳ kết quả nào**; sửa mask, chạy lại toàn bộ.

## 2. Bảng chính DEV (median [min; max] qua 8 seed; CAGR22 = 2022-01→2026-01 +07; DD luật = toàn kỳ 2021-07→2025-12, tệ hơn của mẫu ngày/giờ)

| biến thể | CAGR22 % | DD luật % | DD phút % | Calmar (luật) | tháng tệ nhất % | (n+b)/E TB | ΔCAGR vs B0 (min; max) |
|---|---|---|---|---|---|---|---|
| B0 | 35,8 [34,6; 37,9] | −20,9 [−22,6; −15,4] | −22,9 [−24,7; −20,1] | 1,71 | −11,7 | 0,044 | — |
| S(0,2) | 34,7 [33,7; 36,4] | −28,6 [−29,5; −22,3] | −30,2 [−31,1] | 1,22 | −12,6 | 0,235 | −1,54; −0,91 (0/8 > 0) |
| S(0,3) | 33,6 [32,7; 35,0] | −34,9 [−35,6; −28,0] | −35,4 [−36,1] | 0,96 | −13,0 | 0,330 | −2,85; −1,89 (0/8) |
| S(0,4) | 32,1 [31,4; 33,4] | −42,7 [−43,3; −37,5] | −43,2 [−43,8] | 0,75 | −13,5 | 0,426 | −4,52; −3,22 (0/8) |
| S(0,5) | 30,3 [29,7; 31,4] | −50,1 [−50,6; −46,4] | −50,6 [−51,0] | 0,60 | −16,8 | 0,521 | −6,53; −4,89 (0/8) |
| O(0,2) | 42,2 [40,9; 44,5] | −31,8 [−32,9; −24,1] | −33,8 [−34,8] | 1,33 | −15,0 | 0,244 | +6,26; +6,62 |
| **O(0,3) = w\*** | **44,9 [43,6; 47,4]** | **−37,8 [−38,8; −30,5]** | **−39,6 [−40,5]** | **1,18** | **−16,7** | 0,344 | **+8,94; +9,49** |
| O(0,4) ✗ | 47,3 [46,0; 49,9] | −46,0 [−47,1; −37,3] | −46,6 [−47,7] | 1,02 | −18,4 | 0,444 | +11,29; +12,03 |
| O(0,5) ✗ | 49,3 [47,9; 52,1] | −53,6 [−54,5; −45,9] | −54,1 [−55,1] | 0,92 | −20,2 | 0,544 | +13,30; +14,21 |
| S'(0,3) (w̄ = 0,2999) | 33,6 [32,7; 35,0] | −34,9 [−35,6; −28,0] | −35,3 [−36,1] | 0,96 | −13,0 | 0,330 | |
| S'_bh(0,3) mua 1 lần | 30,4 [29,4; 31,8] | −35,1 [−36,0; −30,1] | −36,6 [−37,4] | 0,87 | −13,0 | 0,272 | |

Biến thể chỉ báo cáo (KHÔNG dùng để chọn), w = 0,3 (đủ lưới trong `bb_tab.md`):

| biến thể | CAGR22 % | DD luật % | DD phút % | Calmar | ghi chú |
|---|---|---|---|---|---|
| O(0,3)+T (cắt 70 %/180 ngày, vào lại > max 30 ngày) | 54,4 [53,0; 56,7] | −25,9 [−27,0; −17,9] | −27,7 [−28,8] | 2,12 | 475 ngày OFF, 41 lần đổi trạng thái; sleeve DD −32,9 % |
| O(0,3)-ETH (rổ 50/50) | 42,1 [40,8; 44,5] | −39,9 [−41,4; −31,1] | −40,7 [−42,1] | 1,06 | tệ hơn BTC thuần |
| O(0,3)-perp (trừ funding thật) | 41,8 [40,5; 44,2] | −38,7 [−39,8; −31,1] | −40,2 [−41,1] | 1,07 | funding 9,1k USD (−3,1pp CAGR) |
| O(0,3, G = 1,5) | 44,9 | −37,8 | −39,6 | 1,18 | ≡ O(0,3): G không ràng buộc |

Ở w = 0,5: O+T 66,8 % / −30,3 %; G=1,5 ≡ O vì gross max của O(0,5) chỉ 1,00–1,03.

## 3. PnL, sự kiện, 2022 (median)

| biến thể | PnL tổng / CB / BTC (k USD) | DD sleeve BTC (TWR) | số lần bán RA | PnL bán RA vs giá vốn | phí (k) | 2022 tổng / CB / BTC (k) | DD 2022 | DD sâu nhất (seed tệ nhất) |
|---|---|---|---|---|---|---|---|---|
| B0 | 105,5 / 105,5 / 0 | — | 0 | — | 0 | +2,4 / +2,4 / 0 | −22,9 | 05-05→05-12-2022 (LUNA) |
| S(0,3) | 104,3 / 74,8 / 29,6 | −77,3 | 0 | — | 0,1 | −9,0 / +1,4 / −10,4 | −30,4 | 2021-11-15→2022-11-10 |
| O(0,3) | 167,4 / 133,1 / 34,3 | −77,4 | **0** | — | 0,5 | −9,6 / +1,4 / −11,1 | −35,7 | 2021-11-15→2022-05-12 |
| O(0,5) | 207,3 / 150,4 / 57,0 | −77,3 | 8 [5; 10] | +371 [141; 630] USD | 0,7 | −17,6 / +0,9 / −18,5 | −47,9 | 2021-11-15→2022-11-10 |
| O(0,3)+T | 183,8 / 144,0 / 39,8 | −32,9 | 0 | — | 0,9 | +1,9 / +2,2 / −0,4 | −22,9 | 2021-11-15→2022-05-12 |

- Tương quan ngày (+07) BTC vs crash-buy B0: toàn kỳ 0,19–0,22; trong ngày có lệnh mới 0,29–0,35 (≈ 165 ngày/seed) — tương quan tăng đúng lúc sập.
- DD sleeve BTC −77 % (owner chấp nhận 80 %: sát ngưỡng).
- Tháng tệ nhất: 7/8 seed rơi vào 05/2022 ở mọi biến thể (LUNA chồng lên BTC giảm).

## 4. HO 2026 W9 (xác nhận O(w\*), median [min; max])

| biến thể | ROI W9 % | DD luật % | DD phút % | PnL CB / BTC (k) |
|---|---|---|---|---|
| B0 | 10,92 [5,67; 12,58] | −4,61 [−6,44; −2,39] | −5,66 [−6,67; −5,14] | 15,4 / 0 |
| **O(0,3)** | **11,12 [5,90; 12,81]** | **−13,20 [−13,74; −11,61]** | −16,89 [−17,48] | 14,6 / 1,0 |
| S(0,3) / S'(0,3) | 8,33 [4,79; 9,24] | −12,3 | −15,2 | 10,3 / 1,4 |
| O(0,3)-perp | 10,39 | −13,25 | −16,94 | 14,5 / 0,0 |
| O(0,3)+T | 15,10 | −6,62 | −7,61 | 15,3 / 6,1 |
| BTC buy&hold W9 | −3,74 | −40,3 (giờ) / −39,9 (ngày) | | |

Luật HO: ΔROI > 0 ở 8/8 (+0,16…+0,28pp), DD luật tệ nhất −13,7 % ⇒ **CONFIRM**. HO chỉ là MỘT đường BTC (đi ngang, sập −40 % rồi hồi):
dấu dương đến từ rebalance ngày (mua thấp bán cao), không phải edge; với funding perp thì âm.

## 5. Giới hạn

- **Beta**: DEV BTC +157 % (2021-07 → 2025-12) — số CAGR của mọi biến thể có BTC phụ thuộc đường đi này; bear 2022 (BTC −77 %) quyết định DD.
- **Tương quan tại đáy**: crash-buy và BTC cùng giảm trong LUNA/FTX; luật DD dùng mẫu giờ/ngày, DD phút O(0,3) tệ nhất đã −40,5 %.
- **Liquidation/cross-margin không mô phỏng** (giả định tài khoản tách, spot không đòn bẩy). Nếu chung tài khoản futures, BTC perp
  + crash-buy cùng margin ⇒ rủi ro thanh lý tại đáy không được đo ở đây.
- Size crash-buy scale bậc 1 theo ρ = E/E_B0 (không chạy lại sim: throttle/trần/selector giữ đường B0).
- Giá spot proxy bằng close perp USDT-M (bỏ qua basis). Funding chỉ ở biến thể perp.
- Bộ lọc T trông rất tốt (DEV CAGR 54 %, DD −26 %; HO 15,1 %) nhưng là luật trend trên MỘT tài sản với MỘT bear market (2022) — rủi ro
  overfit cao; không được chọn theo pre-reg. Muốn dùng phải pre-reg riêng + kiểm ngoài mẫu (2018–2020 niêm phong / đa tài sản).

## 6. Lệch khỏi prereg

Không có lệch về biến thể/lưới/luật. Diễn giải đã ghi trong prereg: S'(w\*) = S(w̄) rebalance tháng, w̄ theo từng seed; biến thể báo cáo
tính cho mọi w; HO overlay bắt đầu ở đầu W9 với vốn = equity B0.
