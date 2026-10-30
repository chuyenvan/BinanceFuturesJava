# HO2026_NOTF_MECH — Cơ chế ΔROI +3,3 pp (W9) của A1 (bỏ TF+INDEX) so A0 (2026-10-30, MÔ TẢ)

Phạm vi: **chỉ mô tả** phân rã leg A0 vs A1 của `HO2026_NOTF.md`; **không tune**, **không chạy kernel mới**, không đổi luật/ngưỡng.
Nguồn số: `printDone.csv` của 48 kernel Kaggle (6 chuỗi = 3 cấu hình × A0/A1, mỗi chuỗi 8 seed), tải **chỉ** file `storage/printDone.csv`
(~1 MB/kernel, 48 MB tổng) từ `chuyendinh/sim-ho4-k24-{s,b}-s<seed>`, `chuyendinh/sim-tsx-ho-x14-s<seed>`,
`chuyendinh/sim-nt-{k24-s,k24-b,x14}-s<seed>`; script `~/claude_master/oc1030/an3k.py`, `an3k_deep.py`, `an3k_days.py`, `an3k_sym.py`.

## 0. TL;DR

1. **V1 ĐẠT tuyệt đối**: với mọi (cấu hình, cửa sổ, seed), `−TF_pnl + Δcommon + new_pnl − lost_pnl = Δrealized`, **max|sai số| = 0,00 cent** (số float, 0.0).
2. ΔPnL W9 = **+27 210,45** (k24-s) và **+38 222,55** (x14) trên 8 seed; **trùng khít** ΔMTM của bảng HO2026_NOTF
   (3401,31 × 8 = 27 210,45; 4777,82 × 8 = 38 222,55) ⇒ phân rã realized giải thích đúng ΔROI +3,28/+3,33 pp.
3. Cơ chế: **3 thành phần cùng dấu**, không phải "đổi TF lấy crypto 1-1":
   (a) leg TF bị bỏ **lỗ** −6 083,52 ⇒ bỏ đi **+6 083,52**; (b) 1 473 leg crypto **mới** +43 633,73; (c) 1 194 leg crypto
   **mất** từng lãi +28 277,21 ⇒ −28 277,21; (d) 2 203 leg **chung** (cùng symbol+giờ vào) **to hơn ~7,4 %** ⇒ +5 770,41.
   Tổng +27 210,45. Hiệu ứng **net của tái phân bổ slot** = new − lost = **+15 356,52**, không phải +43,6k.
4. Tập trung cực mạnh: **06-02..06-06 = +21 480,8 (78,9 %)** Δ W9 k24-s; 5 ngày này **7–8/8 seed dương**. Ngày 06-25
   (+13 072,6; 7/8 seed, nhiều symbol cùng lãi) và 07-28 (+8 448,1; chỉ 4/8 seed, **BANKUSDT** +8 568) là 2 ngày lớn còn lại.
5. 3 ngày cờ X14 **không** phải động lực: 06-06 +5 740 (8/8, nhưng đây cũng là ngày đợt TF), 06-07 **0 leg**, 06-10 −71,2 (k24-s);
   đóng góp biên của x14 so k24-s trên 3 ngày = +2 357 / 0 / +344.
6. Q3 xấu thêm vì **cùng cơ chế nhưng ngược dấu**: new −7 302,9, lost +8 751,7 (mất lãi), TF +1 446,3 (mất lãi) ⇒ −16 440,3.
7. **Nghi vấn bảng**: k24-b và x14 Q3 trùng số ở 2 chữ số thập phân là **làm tròn**, KHÔNG chép nhầm — số chưa làm tròn khác nhau,
   leg cùng key nhưng PnL lệch 11–216/seed (xem §7).

## 1. Phương pháp (độc lập với pipeline chấm)

- Cửa sổ: **W9** = `start ∈ [2026-01-01, 2026-10-01)`; **Q3** = `[2026-07-01, 2026-10-01)`. `start` = giờ vào lệnh (printDone).
  Loc theo `start` (giống D5 của `HO2026_NOTF.md`), `pnl` = realized của leg.
- Ghép leg theo **key = (symbol, start nguyên văn)**; trong 1 key nhiều leg (DCA/cùng phút) ghép **multiset**: lấy
  `min(n_A0, n_A1)` cặp, xếp theo hạng `pnl`; phần dư của A0 = **mất**, phần dư của A1 = **mới**.
- TF = symbol thuộc `~/claude_master/ho_tradfi_wk/X_notf_v2.txt` (230 symbol). Kiểm `assert`: A1 **0 leg** thuộc X.
- Định nghĩa (i)…(iv) và V1:
  `Δ = Σpnl_A1 − Σpnl_A0`; `V1 = Δ − [ −(i) + (ii) + (iii) − (iv) ]` với (i)=PnL leg TF (A0), (iv)=PnL leg crypto mất (A0).
- Tái lập: `python3 ~/claude_master/oc1030/fetch_legs.py` (tải lại 48 `printDone.csv`, ~48 MB) rồi `an3k.py` (bảng tổng),
  `an3k_deep.py` (per-seed/day), `an3k_days.py`, `an3k_sym.py`.

## 2. Phân rã (i)–(iv) — 8 seed cộng lại

| Cấu hình | Cửa sổ | (i) TF bỏ: leg / PnL | (ii) leg chung: n / ΔPnL | (iii) crypto MỚI: leg / PnL | (iv) crypto MẤT: leg / PnL | Δ realized | V1 |
|---|---|---|---|---|---|---|---|
| k24-s | W9 | 238 / −6 083,52 | 2 203 / **+5 770,41** | 1 473 / **+43 633,73** | 1 194 / +28 277,21 | **+27 210,45** | 0,0 |
| k24-s | Q3 | 17 / +1 446,27 | 633 / +1 060,56 | 565 / −7 302,89 | 652 / +8 751,71 | **−16 440,32** | 0,0 |
| x14 | W9 | 236 / −6 367,04 | 2 203 / +5 865,25 | 1 488 / +64 503,98 | 1 196 / +38 513,71 | **+38 222,55** | 0,0 |
| x14 | Q3 | 16 / +2 091,33 | 642 / +560,93 | 577 / −8 167,79 | 651 / +7 705,34 | **−17 403,53** | 0,0 |

Đối chiếu D5 của `HO2026_NOTF.md`: khớp **từng số** (238/−6084; 1473/+43634; 1194/+28277; 2203/+5770; Δ 27210 …).

**Theo seed (k24-s)** — V1 = 0 ở cả 16 dòng:

| seed | W9: (i) n/PnL | (ii) Δ | (iii) n/PnL | (iv) n/PnL | Δ W9 | Q3 Δ |
|---|---|---|---|---|---|---|
| 42 | 26 / −581,0 | +1 504,8 | 157 / +3 562,3 | 136 / +5 714,8 | −66,7 | −4 107,5 |
| 7 | 32 / −1 275,8 | +662,2 | 179 / +3 204,8 | 139 / +288,6 | +4 854,3 | −2 257,0 |
| 13 | 32 / −342,3 | +393,6 | 166 / +3 046,3 | 137 / +3 042,3 | +739,9 | −441,7 |
| 21 | 29 / −1 399,9 | +929,7 | 231 / +6 778,4 | 171 / +4 903,2 | +4 204,8 | −3 349,4 |
| 99 | 32 / −574,4 | +527,2 | 179 / +8 197,9 | 123 / +5 188,6 | +4 110,9 | −5 984,2 |
| 123 | 30 / −715,6 | +557,3 | 183 / +8 284,4 | 141 / +5 292,5 | +4 264,7 | −150,6 |
| 777 | 30 / −252,5 | +879,0 | 185 / +5 240,8 | 161 / +803,1 | +5 569,2 | −60,4 |
| 2024 | 27 / −942,1 | +316,6 | 193 / +5 318,8 | 186 / +3 044,3 | +3 533,3 | −89,4 |

x14 W9 theo seed: Δ = +1 300,4 / +9 604,6 / −382,9 / +5 304,0 / +913,3 / +7 537,2 / +8 648,0 / +5 298,1
(seed 13 âm nhẹ; còn lại dương). Chi tiết trong `~/claude_master/oc1030/an3k_deep.json`.

## 3. (ii) Leg chung: đổi **size**, không đổi logic thoát

| Cấu hình | cửa sổ | cặp chung | qty **y hệt** (n / ΔPnL) | qty **khác** (n / ΔPnL) | mean \|Δqty\| | qty tăng / giảm |
|---|---|---|---|---|---|---|
| k24-s | W9 | 2 203 | 187 / **−0,17** | 2 016 / **+5 770,58** | 7,40 % | 1 577 / 439 |
| x14 | W9 | 2 203 | 178 / **0,00** | 2 025 / **+5 865,25** | 7,22 % | 1 590 / 435 |
| k24-s | Q3 | 633 | 1 / 0,00 | 632 / +1 060,56 | 6,60 % | 445 / 187 |

⇒ Cùng symbol + cùng giờ vào: leg **giữ nguyên qty** thì PnL gần như **không đổi** (−0,17 USDT/187 leg); toàn bộ +5 770
đến từ leg **qty lớn hơn** (+7,4 % trung bình). Vậy biến đổi ở (ii) là **size/margin** (không phải đổi cách thoát/DCA).

### 3.1 ĐÍNH CHÍNH (2026-10-30) — đọc lại §2(b)/§3/§4/§9 sau audit độc lập

Mục này **không sửa** số cũ; nó ghi lại ba chỗ đọc sai nghĩa (audit độc lập `~/claude_master/audit_1030/mech.py`, `mech2.py`).

**(a) "+7,4 % size" là trung bình |Δqty| trên các cặp CÓ đổi qty, không phải mức tăng size.**
Đo lại (k24-s, W9, 8 seed, ghép 1-1 theo `(symbol, start)`):

| đại lượng | giá trị |
|---|---|
| cặp chung | 2 203 (qty y hệt 187, qty khác **2 016**) |
| mean \|Δqty\| — **trên 2 016 cặp đổi** | **7,40 %** ← con số đã in ở §3 |
| mean \|Δqty\| — trên **cả 2 203 cặp** | **6,77 %** |
| mean **có dấu** Δqty | **+4,99 %** |
| median Δqty | **+3,75 %** |
| cặp tăng / giảm | 1 577 (71,6 %) / 439 (19,9 %) |
| equity A1/A0 **tại giờ vào** (MTM) | **+1,74 %** (x14 +1,48 %) |
| corr(log q, log equity) | 0,158 (x14 0,112) |
| mean(log q − log equity) | +2,83 % (sd 7,74 %) |

⇒ Câu "leg chung to hơn ~7,4 %" ở §3/§9 phải đọc là **"nửa phân bố tăng, trung bình tuyệt đối 7,4 % trên nhóm đổi"**,
không phải "mọi leg được scale lên 7,4 %". Lãi kép (equity lớn hơn 1,74 %) giải thích **~1/3** mức tăng có dấu
(1,74/4,99 = 35 %); **phần còn lại (~+3,2 pp mỗi cặp, hoặc +2,83 pp sau khi trừ equity) CHƯA GIẢI THÍCH** — không có log
sizing per-leg để truy nguyên. Vì vậy "+5 770 từ size" vẫn đúng về kế toán nhưng **cơ chế chưa xác định**.

**(b) Bỏ câu "87 % leg mới trên symbol A0 vẫn trade" (hoặc phải so tỉ lệ nền 94,7 %).**
1 279/1 473 = 86,8 % leg mới nằm trên symbol mà A0 **có** trade. Nhưng tỉ lệ nền của **toàn bộ** leg A1 W9 trên
symbol A0 đã trade là **3 482/3 676 = 94,7 %**. Tức leg **mới** còn **ít** tập trung vào universe cũ hơn mức trung bình,
**ngược** với hàm ý "slot cũ được tái dùng" trong §4/§9. Kết luận đúng: phần lớn leg mới là **cùng universe crypto,
khác giờ vào**; không có bằng chứng chúng thay thế trực tiếp leg TF.

**(c) V1 = 0,00 cent là ĐẲNG THỨC KẾ TOÁN, không phải bằng chứng độc lập.**
Trong định nghĩa §1, (ii) "leg chung" được lấy bằng **phần dư** `Δ − [−(i)+(iii)−(iv)]`, nên V1 ≡ 0 theo cấu trúc.
Giá trị thật của V1 chỉ là: (1) không có sai số dấu trong cài đặt; (2) các kiểm tra kèm theo đều sạch —
`qdiff=0` (margin/entry khớp qty), `sell=0` (không có leg SELL), số leg khớp printDone. **Không** được trích V1 như
"kiểm tra độc lập xác nhận phân rã"; muốn vậy phải tính (ii) từ dữ liệu (qty từng leg) rồi so, hiện chưa làm.

## 4. (iii) Leg crypto MỚI: phần lớn không phải "slot TF cùng phút"

| Cấu hình | cửa sổ | mới (n / PnL) | symbol A0 **đã có** (n / PnL) | symbol **chưa từng** (n / PnL) | mở đúng phút có leg TF ở A0 (n / PnL) |
|---|---|---|---|---|---|
| k24-s | W9 | 1 473 / +43 633,7 | 1 279 / +43 133,1 | 194 / +500,7 | 274 / +7 127,0 |
| x14 | W9 | 1 488 / +64 504,0 | 1 292 / +60 616,2 | 196 / +3 887,8 | 271 / +11 176,6 |
| k24-s | Q3 | 565 / −7 302,9 | 458 / −7 401,8 | 107 / +98,9 | 0 / 0 |

⇒ 87 % leg mới nằm trên symbol A0 **vẫn trade** (chỉ khác giờ vào) ⇒ chủ yếu là **slot/capacity + trạng thái gate/market
đổi** làm A1 vào thêm lệnh, **không** phải thay 1 leg TF bằng 1 leg crypto cùng phút (chỉ 274 leg / +7 127, tức 16 % PnL mới).

## 5. (iv) Leg crypto MẤT: gồm cả "tránh được lỗ"

1194 leg mất ở W9 k24-s từng lãi **+28 277** (nên mất đi là −28 277), nhưng phân bố rất lệch. Ví dụ điển hình
(k24-s W9, cộng 8 seed):

| symbol | A0 leg / PnL | A1 leg / PnL | leg mất / PnL(A0) | Δ |
|---|---|---|---|---|
| BANKUSDT | 19 / −8 728,4 | 6 / +618,3 | 18 / **−8 831,7** | **+9 346,7** |
| TAIKOUSDT | 4 / −4 164,5 | 0 / 0 | 4 / −4 164,5 | +4 164,5 |
| TUTUSDT | 19 / −873,0 | 18 / +2 094,2 | 10 / +680,4 | +2 967,2 |

⇒ Một phần lớn Δ là **A1 không vào lại các chuỗi lỗ** (BANK 18 leg −8 832; TAIKO 4 leg −4 165).
(Lưu ý: ASTSUSDT **thuộc X** nên 8 leg/−2 652 của nó nằm ở (i) TF, không phải (iv).)

## 6. Ngày đóng góp (k24-s W9, Δ realized theo `start`, cộng 8 seed)

| # | ngày | Δ | seed dương |
|---|---|---|---|
| 1 | 2026-06-25 | **+13 072,6** | 7/8 |
| 2 | 2026-07-28 | **+8 448,1** | **4/8** (13/123/777/2024; BANK +8 568) |
| 3 | 2026-06-06 | +5 740,2 | **8/8** |
| 4 | 2026-06-04 | +4 669,5 | 7/8 |
| 5 | 2026-06-03 | +4 478,2 | **8/8** |
| 6 | 2026-06-02 | +3 509,1 | **8/8** |
| 7 | 2026-07-02 | +3 342,1 | 6/8 |
| 8 | 2026-06-05 | +3 083,8 | **8/8** |
| 9 | 2026-04-18 | +2 645,2 | — |
| 10 | 2026-06-11 | +2 132,9 | — |

- Tổng 10 ngày trên = **+51 122** > Δ tổng +27 210 ⇒ **các ngày còn lại cộng lại −23 911**: Δ là "vài ngày thắng lớn bù lỗ rải rác".
- **06-02..06-06 = +21 480,8 (78,9 %)**; 163/238 leg TF (**68,5 %**, khớp "69 %" trong `HO2026_NOTF.md`) rơi vào 06-02..05
  với PnL TF −7 900; riêng 06-02 TF −4 870, 06-04 −2 161. Đây là **cơ chế chính, lặp 7–8/8 seed**.
- 06-25 không do 1 symbol: GUA +1 766, CLO +1 412, BEL +1 208, ESPORTS +1 020 … (nhiều symbol, ngày thị trường rộng).
- 07-28 **chỉ 4/8 seed** và **BANKUSDT +8 568** ⇒ hiệu ứng **phụ thuộc seed/symbol**, không phải luật.
- Theo **ngày thoát** (`end`): top-10 đổi thứ tự (06-25 +13 544; 08-04 +10 269; 06-06 +6 497; 08-03 +4 930; 08-09 +4 818 …),
  nhưng **06-02..06 vẫn +17 685 (65 %)** ⇒ kết luận June không phụ thuộc cách quy ngày.
- x14 W9: 06-02..06 = +28 117,6 (73,6 %); 06-25 +19 754,1; 07-28 +12 064,0.

## 7. Q3 — cùng cơ chế, ngược dấu

k24-s Q3: TF +1 446,3 (bỏ ⇒ −1 446,3), common +1 060,6, **new −7 302,9**, **lost +8 751,7** ⇒ −16 440,3.
Leg mới Q3 lỗ nặng: AIN −9 115, AKE −7 194, BOME −3 680, CYS −3 421; leg mất Q3 từng lãi: BEAT +4 508, AKE +3 111,
BULLA +2 773. ⇒ Trong Q3, capacity giải phóng sinh **entry xấu** và **bỏ entry tốt** — ngược hẳn W9. Q3 vẫn FAIL ở cả A0/A1.

## 8. Nghi vấn bảng: k24-b và x14 Q3 "trùng số" 0,27/−4,07 → −1,03/−4,16

**Không phải chép nhầm.** Đối chiếu file gốc:

- `notf_score.json` (chưa làm tròn): k24-b Q3 A0 ROI **0,2741709879**, maxDD **−4,07489502**; x14 Q3 A0 ROI **0,2740395768**,
  maxDD **−4,07495298**. A1: k24-b **−1,02508804** / **−4,15971045**; x14 **−1,02516434** / **−4,15973792**.
  Chênh ~1,3e-4 pp (ROI) và 6e-5 pp (DD) ⇒ làm tròn 2 chữ số ra **cùng số**, không phải copy.
- Leg-level `printDone` Q3: k24-b và x14 **cùng tập key** (số key đối xứng = 0) và **cùng số leg mỗi seed**
  (158/154/160/170/139/152/173/203 ở A0; 141/156/162/161/145/144/146/164 ở A1), nhưng **PnL từng seed lệch**
  (A0: +11,1 / −41,5 / −50,8 / −21,0 / +108,1 / −63,5 / −215,8 / −98,3; A1: −43,4 … −167,6) ⇒ **cùng entry, khác exit**
  (X14 hoãn time-stop 168 h ở ngày mở rộng ⇒ giá thoát khác). Vì vậy số Q3 **khác thật** ở 3–4 chữ số thập phân.

## 9. Kết luận cơ chế +3,3 pp (W9)

1. **Bỏ TF** loại 238 leg **lỗ** (−6 084) ⇒ +6 084, tập trung 06-02..06 (68,5 % leg TF).
2. **Capacity/slot giải phóng** ⇒ +1 473 leg crypto mới (+43 634) nhưng **đồng thời mất 1 194 leg** (+28 277 lãi cũ):
   net +15 357. Phần lớn leg mới là **cùng universe crypto** nhưng **khác giờ vào** — do trạng thái portfolio/gate/market đổi.
3. **Size trên leg chung tăng ~7,4 %** (margin/equity tái phân bổ) ⇒ +5 770; leg cùng qty gần như không đổi.
4. Tổng: **+6 084 + 5 770 + 43 634 − 28 277 = +27 210** ⇒ +3,28 pp ROI (k24-s) / +3,33 pp (x14, +38 223).
5. **Tập trung ngày**: 06-02..06 = +21 481 (79 %), lặp 7–8/8 seed ⇒ có cơ sở hệ thống, **không** phải may mắn 1 seed;
   nhưng 06-25 (+13 073, 7/8 seed) và 07-28 (+8 448, 4/8 seed) là hiệu ứng ngày/symbol. **3 ngày cờ X14 không phải động lực.**

## 10. CHƯA GIẢI THÍCH (không suy đoán)

- **Vì sao 06-25 và 07-28 lại lãi lớn**: chỉ biết 06-25 nhiều symbol cùng lãi (thị trường rộng), 07-28 do BANKUSDT và
  chỉ 4/8 seed. Chưa truy được chuỗi quyết định (slot nào, gate nào, size nào) ở mức order.
- **Vì sao qty leg chung tăng 7,4 %**: giả thuyết là margin/equity khả dụng tăng khi không còn vị thế TF, nhưng chưa đo
  trực tiếp biến sizing trong từng nhịp (không có log sizing per-leg trong artefact).
- **Vì sao A1 bỏ đúng chuỗi lỗ BANK/TAIKO/ASTS**: khớp về mặt kế toán (leg mất có PnL âm) nhưng cơ chế chọn
  (rank/gate/slot ở thời điểm đó) chưa được tái dựng.
- **Q3 −1,7 pp**: mô tả đủ (new −7 303, lost +8 752, TF +1 446) nhưng chưa biết vì sao entry mới Q3 xấu (AIN/AKE/BOME).
- ΔMTM Q3 lệch Δrealized **91–181 USDT/8 seed (−0,6…−1,0 %)**: do vị thế còn mở tại 2026-10-01 được MTM theo mark
  (không nằm trong realized); W9 khớp tuyệt đối (0,01 USDT). Không ảnh hưởng kết luận W9.

## 11. Artefact & dung lượng

- Số: `~/claude_master/oc1030/an3k_agg.json`, `an3k_deep.json`, `an3k_days.json`, `an3k_sym.json`.
- Script: `~/claude_master/oc1030/fetch_legs.py`, `an3k.py`, `an3k_deep.py`, `an3k_days.py`, `an3k_sym.py`.
- Tải: 48 file `printDone.csv` (48 MB) từ Kaggle kernel outputs; **đã xoá `~/claude_master/oc1030/legs/` sau khi tính**
  (báo cáo ở payload). Không tải dữ liệu giá/kline; không gọi Binance API.
