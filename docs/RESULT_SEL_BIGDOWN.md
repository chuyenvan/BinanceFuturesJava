# RESULT_SEL_BIGDOWN — doi cach chon 2 coin cua leg BIG_DOWN theo drop 1-phut causal, trigger giu nguyen

**Verdict: NULL — giu nguyen T170 (parity).**

Selection theo drop 1-phut KHONG doi chat luong rieng leg BIG_DOWN mot cach Y NGHIA THONG KE:
ca 3 bien the deu **0/3 rate PRIMARY ngoai CI**. DROP co point-estimate `pnl/leg` tang rat lon
(+54 USD/leg, +82%) va end-equity +28% nhung CI bootstrap qua RONG (duoi nang) nen KHONG ngoai CI;
khong duoc chon theo equity (pre-reg). KHONG tune lai sau khi thay so. KHONG push.
DEV 2021-07..2025-12 (`wfo_ds_x1_2021`).

- Pre-reg: `docs/PREREG_SEL_BIGDOWN.md` (commit `4de6b6e`).
- Baseline parity md5 `efb793e2468ca3a7318da0f0ad23d4fc` = byte-identical `X1_GS_T170_2021`.

## 1. Cong parity (bat buoc)
Flag `BD_SEL_MODE=off` (profile goc `x1_gs_t170` KHONG khai key) => `printDone.csv` **byte-identical**
`efb793e2468ca3a7318da0f0ad23d4fc` (1090 dong, 1089 trade). PASS.

## 2. n leg BIG_DOWN (chan cung #1)
| tag | n leg BIG_DOWN | n ALL leg | end equity | md5 printDone |
|---|---|---|---|---|
| PARITY | **248** | 1089 | 111070 | efb793e2468ca3a7318da0f0ad23d4fc |
| DROP | **248** | 1187 | 142218 | c23dd79ad757920d89d01866af8e4e3e |
| MIX | **248** | 1147 | 120254 | d94b13f0bc5a06f7afa7c7e12f5625af |
| DROP_TOP8 | **248** | 1118 | 117487 | 21c98c9b746da8be85d2bef5320c43c0 |

n = 248 o ca 4 (trigger khong doi). PASS (khong doi so ve).
Ghi chu minh bach: doi coin chon lam TONG so leg tang (1089 -> 1187/1147/1118) — cac coin rot sau
cham DCA-grid nhieu hon => them leg DCA_LEVEL1 (second-order, NAM NGOAI PRIMARY; duoc bat boi chan #3/#4).

## 3. PRIMARY — chat luong rieng leg BIG_DOWN (so sanh tung bien the vs parity)
CI block 72h x1.21, 2000 resample, seed 20260905. "Tot" = pnl/leg & meanP tang, TSloss% giam.

| tag | pnl/leg (USD) | meanP | TSloss% | win% |
|---|---|---|---|---|
| PARITY | 65.54 | 4.786 | 8.47 | 88.71 |
| DROP | 119.67 | 8.742 | 8.87 | 87.10 |
| MIX | 61.19 | 5.307 | 8.87 | 87.10 |
| DROP_TOP8 | 73.92 | 5.528 | 6.45 | 88.31 |

Hieu (variant - parity) + CI + so rate ngoai CI cung huong tot:

| bien the | pnl_leg | meanP | tsloss | n ngoai CI (tot) |
|---|---|---|---|---|
| DROP | +54.13 (CI -9.61, +108.74) | +3.956 (CI -0.434, +8.198) | +0.403 (CI -5.128, +7.057) | **0/3** |
| MIX | -4.35 (CI -47.63, +40.09) | +0.521 (CI -1.090, +1.979) | +0.403 (CI -4.609, +6.038) | **0/3** |
| DROP_TOP8 | +8.38 (CI -14.80, +32.88) | +0.741 (CI -0.277, +1.725) | -2.016 (CI -7.884, +3.878) | **0/3** |

- `meanP` co point-estimate DUONG o ca 3 bien the (huong tot) nhung KHONG ngoai CI o bat ky bien the nao.
- `pnl/leg` DROP +54 USD/leg la duoi nang (vai leg thang lon keo mean) -> CI qua rong -> KHONG ngoai CI.
- `TSloss%` DROP_TOP8 giam -2.02pp (6.45 vs 8.47) nhung CI van chua 0.
=> Khong bien the nao dat PRIMARY (>=2/3 rate ngoai CI cung huong tot).

## 4. Tap trung (chan cung #2)
`max % equity 1 coin` = 9.77% (parity) vs 9.76% (DROP) / 9.79% (MIX) / 9.79% (DROP_TOP8).
KHONG tang (DROP con giam nhe). PASS.

## 5. Rang buoc cung tu equity THAT (`sim.out`) theo nam (chan cung #3)
Tolerance pre-reg: maxDD nam khong xau hon parity qua +3pp; khong nam am; UW khong xau hon qua +30 ngay.

| nam | PARITY maxDD/UW/ret% | DROP | MIX | DROP_TOP8 |
|---|---|---|---|---|
| 2021 | -2.46 / 37 / +12.21 | -2.69 / 37 / +13.96 | -2.85 / 37 / +12.24 | -2.46 / 38 / +12.60 |
| 2022 | -11.84 / 72 / +19.58 | -11.65 / 72 / +20.70 | -11.66 / 72 / +20.78 | -11.56 / 72 / +19.02 |
| 2023 | -2.73 / 63 / +34.96 | -1.09 / 65 / +41.81 | -0.80 / 43 / +38.77 | -1.13 / 31 / +39.70 |
| 2024 | -6.60 / 92 / +32.14 | -5.95 / 119 / +36.11 | -6.81 / 119 / +34.46 | -6.84 / 119 / +31.15 |
| 2025 | -4.23 / 52 / +32.71 | -3.35 / 52 / +53.04 | -5.29 / 52 / +35.84 | -4.19 / 52 / +36.70 |

- Khong nam am o bat ky bien the nao.
- maxDD nam xau nhat so parity: DROP/MIX/DROP_TOP8 deu trong +3pp (xau nhat la MIX 2025 -5.29 vs -4.23 = -1.06pp).
- UW 2024 = 119 (ca 3 bien the) vs parity 92 = **+27 ngay**, trong +30 ngay (sat nguong, giong nhu truc SIZE_ADAPT).
=> PASS het, nhung chu y: chon coin khac lam UW 2024 dai hon (119 vs 92) — phuc hoi cham hon.

## 6. Rate TOAN BO leg (chan cung #4)
win%/TSloss%/meanP toan bo leg: khong rate nao XAU ngoai CI o ca 3 bien the. PASS.

| tag | n | win% | TSloss% | meanP |
|---|---|---|---|---|
| PARITY | 1089 | 88.25 | 9.73 | 5.244 |
| DROP | 1187 | 88.37 | 9.44 | 6.228 |
| MIX | 1147 | 88.14 | 9.68 | 5.832 |
| DROP_TOP8 | 1118 | 88.01 | 9.39 | 5.434 |

## 7. Tong quan danh muc (tham khao, KHONG phai tieu chi)
| tag | end equity | CAGR% | maxDD% | UW ngay |
|---|---|---|---|---|
| PARITY | 111070 | 29.27 | -11.84 | 92 |
| DROP | 142218 | 36.57 | -11.65 | 119 |
| MIX | 120254 | 31.57 | -11.66 | 119 |
| DROP_TOP8 | 117487 | 30.89 | -11.56 | 119 |

DROP tang end-equity +28% / CAGR +7.3pp (chon coin rot sau -> pnl/leg cao hon, nhieu leg hon),
nhung KHONG duoc dung lam tieu chi chon (pre-reg muc 2) va UW dai hon (+27 ngay).

## 8. Multiplicity
k=3 bien the x 3 rate PRIMARY. Nguong thang dung he so B4 `sqrt(2 ln 3) = 1.4823` khi so tren cung
khung. Khong bien the nao cham du 1/3 rate ngoai CI (chua noi 2/3) => khong can noi rong them.
Ket luan NULL KHONG phu thuoc he so multiplicity.

## 9. Ket luan
Selection theo drop 1-phut (drop / mix / drop_top8) cho leg BIG_DOWN KHONG sinh ra thay doi Y NGHIA
THONG KE tren chat luong rieng leg (`pnl/leg`, `meanP`, `TSloss%`) o n=248 leg voi duoi nang. DROP
co point-estimate `pnl/leg` +82% va end-equity +28% nhung CI bootstrap qua rong; DROP_TOP8 co TSloss%
-2.02pp (huong tot) nhung cung khong ngoai CI. **NULL — giu T170.**

Hop nhat voi truc SIZING (NULL) va Q5: doi ca SIZING lan SELECTION cua leg BIG_DOWN deu khong doi
duoc chat luong tung lenh mot cach co y nghia thong ke — alpha cua T170 nam o trigger + pipeline
chon coin ban dau (pNoPump), khong nam o hai do this.

## 10. Follow-up (da pre-reg)
Khong dat => KHONG mo stage 2 (khong chay lai sizing tren nen selection). Truc SELECTION dong tai day.
