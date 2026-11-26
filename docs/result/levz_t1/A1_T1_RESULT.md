# A1_T1_RESULT - audit DOC LAP ket qua LEVZ T1 (2026-11-26 23:3x UTC)
Nguoi audit: agent A1 (khong viet code, khong audit code). Doi tuong: out/grid_t1.parquet, rand_t1.{json,parquet,_parts}, report_t1.{md,json}
(run 26/11 17:41-23:27, GRID_EXIT=0 RAND_EXIT=0 REPORT_EXIT=0; log co 1 dong REPORT_PRERAND_EXIT=1 luc 17:51 = lan report truoc khi co rand, bi thay the).
Cach lam: script rieng (tmp, da xoa) - goi port.py / select_b1.rule / sim.metrics cua B1-B0, bang thoat work/exits_t1_*.npz + cand_b1.npz,
gate B2 opts.mask_at; PART: tu dung lai mang gio hieu dung theo CHOICES 8; HEDGE: tu viet vong ke toan theo prereg muc 3 + ADD1 A2-A3.
Khong goi grid_t1 / select_t1 / report_t1 / hedge_t1 / exits_t1 (rand_t1 chi goi cho muc 3).

## KET LUAN: KET QUA XAC NHAN (0 lech ngoai sai so float)
- 17 cau hinh chay lai x 4 fold (DEV/F1/F2/F3) = 68 fold: so lenh, ret, maxdd, maxdd_worst, hedge_pnl trung grid_t1 (|lech| <= 2,4e-15).
  Gom: top-1 WFO 2024 + 2025 + 1 ngau nhien gate NONE cho ca 5 ho; them 1 ngau nhien G_EW14 cho BRK, STATE, HEDGE.
- Moi so trong bang report_t1.md (ti le co lai, trung vi ret, WFO top-1 / top-20, p, T-a..T-e, ket luan, dong tap trung) tinh lai TRUNG.

## BANG (gate NONE; so tinh lai = report, lech 0)
| ho | co lai F1/F2/F3 | WFO tv top-20 2024 / 2025 | p | T-a T-b T-c T-d T-e | ket luan |
|---|---|---|---|---|---|
| BRK | 74,1 / 46,3 / 49,6 % | +6,2 / -3,7 % | 0,01 | F F T T F | KHONG HON B1 |
| VOL | 75,0 / 47,2 / 70,1 % | -5,4 / +3,5 % | 0,00 | F F T T F | KHONG HON B1 |
| PART | 61,1 / 52,8 / 77,8 % | +2,8 / +4,1 % | 0,00 | T T T T F | CO CAI THIEN, CHUA DU |
| STATE | 100 / 47,2 / 100 % | +0,14 / +35,3 % | 0,00 | T F T T F | CO CAI THIEN, CHUA DU |
| HEDGE | 59,6 / 55,8 / 44,7 % | +4,3 / -5,6 % | 0,07 | F F F T F | KHONG HON B1 |
T-d (trung vi n F2+F3): BRK 245, VOL 220, PART 213,5, STATE 252, HEDGE 245. T-e (bo 5 % lenh loi nhat, fold kiem top-1):
BRK -1474 / -1837; VOL -1181 / -1190; PART -964 / -1317; STATE -1408 / +1239; HEDGE +340 / -1521 (USD tren von 10 000).
Moc B1: 2024 -23,0 %, 2025 +6,1 %; co lai 64 / 20 / 84 %. Khong ho nao "HO DAT".

## G_EW14 (nhan: GATE HAU KIEM - chi mo ta)
Ca 5 ho: WFO "khong cham duoc 2024" VA "khong cham duoc 2025" - report ghi DUNG. Nguyen nhan tinh lai: duoi G_EW14 fold F1 (2022-23)
co toi da 3 lenh / cau hinh (gate gan nhu dong ca 2022-23) => khong cau hinh nao dat n >= 30 o F1. p (hau kiem): BRK 0,03; VOL 0,01;
PART 0,06; STATE 0,13; HEDGE 0,16. Co lai F2 (hau kiem): BRK 92 %, VOL 92 %, PART 96 %, STATE 75 %, HEDGE 86 % - KHONG dung de ket luan.

## Doi chung ngau nhien
1000 file part = 5 ho x 2 gate x 100 luot, rep 0..99 du, 0 trung; p tinh lai tu part = report (10/10); real max score tinh lai trung.
Chay lai bang rand_t1.one_rep: STATE NONE luot 7, 42; STATE G_EW14 luot 93; BRK NONE luot 55 -> n_cand, n_cand_gate, max_score, n_valid,
best_cfg_id trung tung so. LUU Y (khong phai lech, la thiet ke B1): moi luot ngau nhien co 385 ung vien (rut theo dot) vs 1 965 dong ung vien
that lop z 3,0; o 4 luot chay lai n_valid = 0. Do manh cua doi chung phu thuoc vao thiet ke rand B1 (da audit o B1, khong kiem lai o day).

## Hop le
- Bang thoat 4 ho: phut thoat lon nhat = 2 148 479 < NMIN 2 148 480 (2026-01-01); close1m chi co 2 148 480 phut; FR / inputs dung NH gio
  (< 2026); moi lenh chay lai kx <= kl. Khong lenh / funding nao >= 2026-01-01 UTC. Khong cot pnl_2026.
- So cau hinh 9 468 (BRK 810, VOL 432, PART 72, STATE 72, HEDGE 3 348, moi gate); acct_err max 6e-11.
- Nhan "gate hau kiem" co o moi dong G_EW14 cua bang report va rand_t1.json.

## Giai phau (MO TA, ngoai tieu chi)
Ho tot nhat theo WFO = STATE; te nhat = HEDGE (min hai nam -5,6 %; BRK -3,7 %, VOL -5,4 %).
- STATE top-1 2025 (z 3, K 5, z_out 0, SL 30 %, H 168): F3 87 lenh, thang 63 %, state 77 / sl 9 / time 1; +4 568 USD nhung 9/2025 +1 961 va
  11/2025 +3 035 (10/2025 -1 230) => 2 thang chiem > 100 %; bo 5 % con +1 239. Lenh te nhat -35,5 %.
- STATE top-1 2024 (z_out 1, SL 15 %): F2 180 lenh, thang 56 %, state 164 / sl 15 / eod 1; tong -33; lo don o 10-12/2024 (-1 084;
  T1-T9 +1 052). sl tong -3 135 an het state +3 082. WFO 2024 top-20 +0,14 % = sat 0 (T-a dat rat mong).
- HEDGE top-1 2024 (BRK s 12 % R 3 H 168, BTC+ETH, h 0,5): F2 chan long -67 USD (khong cuu 2024); DEV chan long 2022 +35, 2023 -443,
  2024 -84, 2025 -613. Top-1 2025 (BTC h 0,5): chan long 2025 -316 / tong -741. Toan ho (NONE): trung vi hedge_pnl F1 -1,5 %, F2 +0,3 %
  (55 % > 0), F3 -1,2 %, DEV -2,0 %. So voi BRK cung (bxi, z, K): F2 tot hon o 58 % cap (trung vi +1,0 dd) - phan lon do size short nho
  hon 1/(1+h), khong phai do chan long; F1/F3 te hon. => hedge BTC/ETH KHONG cuu 2024.
- TP R nho vs lon (BRK NONE, trung vi ret / co lai): R 0,5: F1 +4,2 % / 80 %, F2 +0,4 % / 54 %, F3 -4,4 % / 31 %, ti le TP ~ 61-66 %.
  R 3: F1 +2,6 % / 69 %, F2 -5,6 % / 29 %, F3 +5,8 % / 72 %, ti le TP 2-13 %. R nho giup 2024, hai 2025; R lon nguoc lai - khong R nao on dinh.
- Tap trung: moi top-1 tru STATE 2025 va HEDGE 2024 am sau khi bo 5 % lenh tot nhat (vd PART 2024: +1 797 -> -964; BRK 2024 +1 464 -> -1 474).

## Duoc noi / khong duoc noi
DUOC: bang tren (gate NONE, WFO, p, T-a..T-e, ket luan tung ho); "khong ho nao dat"; PART va STATE "co cai thien, chua du" va ly do (T-e,
STATE them T-b); hedge BTC/ETH khong cuu 2024 (mo ta).
KHONG DUOC: so in-sample (top-1 DEV, ti le co lai DEV, ret ca giai doan cua mot cau hinh) nhu ky vong; moi so G_EW14 (hau kiem, F1 <= 3 lenh)
nhu bang chung; STATE 2025 +35 % / +46 % nhu loi the (2 thang chi phoi); STATE 2024 "duong" (+0,14 % ~ 0); giai phau la mo ta, khong la tieu chi.

## Chua kiem
Logic bang thoat T1 tu du lieu 1m (dung bang exits_t1_*.npz nhu dau vao, khong tinh lai TP / STATE / VOL u tu gia); mat na G_EW14 (dung B2
opts nguyen ban); thiet ke rut ngau nhien B1; chi 17 / 9 468 cau hinh chay lai (con lai kiem qua thong ke tu grid).
