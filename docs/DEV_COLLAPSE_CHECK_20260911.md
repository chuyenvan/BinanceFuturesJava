# DEV_COLLAPSE_CHECK_20260911 — pattern "collapse" cua shadow live co trong 2,266 lenh DEV X1_C3_FULL khong?

Cau hoi (user, 11/09): shadow 242 sau 4.3 ngay co 27 lenh mo, 26/27 am, avg -22.5% (`docs/SHADOW_EVAL_20260911.md`).
DEV (X1_C3_FULL canonical = `devrun/X1_C3_FULL_PARITY_R/printDone.csv`, 2,266 lenh, 2022-2025) co the khong, dac biet 2025?
Script: `research/analysis/dev_collapse_check.py`. Parity tham so exit: `x1_c3_full.properties` arm 0.07 / TS_GIVEBACK 0.5 /
LOSER_TIME_STOP 168h / TOPK 8 = `LiveProfileC3` (0.07 / ratchet lien tuc / 168h / 8). => so sanh duoc.

## 1. TRA LOI: CO. Live dang TAI HIEN dung co cau rui ro cua DEV, khong phai lech.
| nam | n | win% | SL%(=time-stop) | meanRet win | meanRet loss | p5 | min | n<-20% | n<-40% | pnl_SM | pnl_SL | pnl_SL/pnl_SM |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022 | 406 | 82.3 | 17.0 | +7.7 | -23.3 | -25.2 | -72.8 | 32 | 14 | +17,166 | -11,109 | 65% |
| 2023 | 308 | 88.6 | 13.6 | +8.3 | -14.2 | -13.2 | -43.4 | 8 | 1 | +33,848 | -9,128 | 27% |
| 2024 | 668 | 86.2 | 14.5 | +7.2 | -16.7 | -19.4 | -61.1 | 31 | 4 | +67,642 | -37,731 | 56% |
| **2025** | 884 | 83.3 | 14.8 | +8.4 | **-26.6** | **-32.3** | **-91.4** | **81** | **35** | +112,122 | **-96,381** | **86%** |

- **Cohort "song >= 96h"** (tuong duong "con mo sau 4 ngay" o live): 402/2,266 lenh (17.7%), **79% ket thuc time-stop**,
  meanRet **-15.2%**, tong pnl **-144,992** — TOAN BO lo cua chien luoc nam o day. 2025: 154 lenh, 80% SL, meanRet **-20.9%**,
  74 lenh < -20%, pnl **-92,446**. Live 26/27 am avg -22.5% sau 4.3 ngay = dung phan phoi 2025 nay.
- **Book theo ngay**: open median 4, p90 12-15, max 27-30. Live 27 mo = max cua DEV. `evSL%` (ti le lenh dang mo se ket thuc
  SL) median **75%** moi nam — snapshot book luc nao cung toan loser-tuong-lai vi winner thoat trong vai gio (hold median 8-13h),
  loser nam toi 168h. Live 96% nam trong nhom 20 ngay te nhat DEV: 2022-05-07..11 (LUNA), 2025-03-08..10, 2025-11-11..12,
  2025-11-26..28 (evSL 87-100%, evRet -26..-48%).
- **Collapse day** (>=4 SL cung ngay): 25 ngay/48 thang; te nhat 2025-11-12 (7 SL, **-8,641** = -7.7% equity/ngay: CUDIS x4 +
  JELLYJELLY x3 = dung "bag cuoi chain"), 2024-04-17 (-5,561), 2025-04-21 (-4,954), 2025-11-28 (-4,759), 2025-03-11 (-4,239).
- **2025 la nam mong nhat**: time-stop an **86%** lai trailing (2023: 27%); Q3 va Q4 (chi PREDICT_SYMBOL_TRADE) **AM** (-2,172 / -4,108);
  Q4 meanRet loss -34.6%, p5 -46%, min -91%. Universe 2025 = meme low-cap (AIA 36 lenh, ALCH 32, FARTCOIN 27, MYX, PIPPIN, COAI)
  — cung loai coin voi live (IOST/SOPH/USELESS/BULLA/CYS/COLLECT).

## 2. RE-ENTRY CHAIN — trong DEV la FEATURE co lai, khong phai bug
- 677/2,266 (29.9%) la vao lai cung coin <=24h sau lenh truoc; 2025: **39%**. Re-entry KHONG te hon fresh: 2025 ret_reentry +4.8
  vs fresh +1.0, SL% 13.0 vs 16.0. Chain dai >=3: 131 chain, tong pnl **+32,078**; lenh cuoi chain ket thuc SL (bag) **25.2%**
  vs 18.2% lenh don. Chain dai nhat: AIA 15 (+718), AIA 13 (+2,501), MYX 13 (+1,531), FTT 14 (2022, bag), ANC 14 (2022, bag -43%),
  **JELLYJELLY 13 (-2,630, bag)**.
- => Live IOST 9+1 / SOPH 5+1 / USELESS 6+1 la dung hanh vi DEV. Gioi han re-entry se cat ca phan lai (+32k), KHONG phai ung vien tot.

## 3. Y NGHIA
1. Shadow khong "hong": chi phi tail (time-stop) la thuoc tinh da co trong DEV; `L1_SHADOW_C3` muc 0.5 da goi day la "kenh mat tien
   lon nhat cua C3". Doc live phai theo chu ky **>= 168h + vai vong**, khong theo tuan dau.
2. Nhung DEV 2025 cho thay edge mong (SL an 86% lai, 2 quy am) — neu regime 2026 giong 2025H2 thi shadow se am keo dai. Day la
   rui ro that, da co trong so lieu, khong phai phat hien moi.
3. Khong gian EXIT da duoc do: `E0_EXIT_CF` (counterfactual horizon — gate FAIL, khong xep hang duoc), `PREREG_EXIT` (E1 horizon
   time-stop tren C2b, 04/09), `HOLD_TO_DIE` (306 lenh time-stop X1_C3: giu tiep chi 38% ve BE trong 14 ngay, MDD tiep -33.9%
   => time-stop dung). Truoc khi de xuat doi time-stop/hard-SL PHAI doc ket qua E1 (neu co) de khong mo lai nhanh da dong.
4. HOLDOUT 2026: **KHONG cham**. Khong co ung vien nao qua DEV/VAL de xac nhan (K12/5MGRID/G015ABL/B4/GATEDYN deu NULL); shadow
   live chinh la forward test dang tieu thu 2026 theo thoi gian thuc; cham holdout luc nay = dot tai nguyen mot lan cho mot cau
   hoi chua co gia thuyet.

## 4. KHONG LAM
Khong sua gi tren 242/Oracle ngoai them 2 file nay. Khong doi neo. Khong tune theo tuan live.

## 5. BO SUNG (cung ngay) — khong gian EXIT DA DONG, khong de xuat mo lai
- `E1_EXIT_RESULT.md` (C2b, 04/09): grid time-stop 168/120/96/72 -> chon 72 theo luat "ngan nhat thoa P1+P2", ghi ro "khong phai
  muc toi uu da chung minh", quota het.
- `X2_EXIT48.md` (X1_C3, 48 thang, 6 run): truc T (time-stop 120/96/72) cai thien mP|SL va p10loser don dieu (2025: mP|SL -28.9 ->
  -18.9) NHUNG win% giam ngoai CI o ca 3 muc va **5/5 arm FAIL rang buoc cung**; truc S (pre-arm hard SL -30/-20) khong don dieu,
  S30 xau hon parity. **=> CA HAI TRUC NULL.** Cat time-stop/hard-SL chi "dun duoi lo len thanh cot o muc cat", khong cuu lenh nao.
- Vay tail time-stop cua C3_FULL la chi phi da do va da thu cat bang 2 cach: khong cat duoc theo luat du an. Huong con chua do:
  tang **book/von** (cap so lenh mo dong thoi / cap notional khi book nang loser) — la overlay rui ro, can PREREG rieng.
