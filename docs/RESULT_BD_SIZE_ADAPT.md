# RESULT_BD_SIZE_ADAPT — size leg BIG_DOWN theo severity (rolling causal N=120), trigger giu nguyen

**Verdict: NULL — giu nguyen T170 (parity).**

Severity-based sizing chi RESCALE `pnl/leg` (co hoc, dung nhu ky vong) ma KHONG doi chat luong
(`meanP` khong doi, `TSloss%` khong doi, `win%` khong doi) va KHONG doi rui ro (tap trung 1 coin
khong doi, maxDD/UW/nam-am khong doi qua tolerance). Ket qua Y HET Q5 — "sizing co dieu kien
khong doi chat luong tung lenh". Khong bien the nao dat PRIMARY (>=2/3 rate ngoai CI cung huong
tot). KHONG tune lai sau khi thay so. KHONG push. DEV 2021-07..2025-12 (`wfo_ds_x1_2021`).

- Pre-reg: `docs/PREREG_BD_SIZE_ADAPT.md` (commit `a55f913`).
- Baseline parity md5 `efb793e2468ca3a7318da0f0ad23d4fc` = byte-identical `X1_GS_T170_2021`.

## 1. Cong parity (bắt buộc)
Flag `BD_SIZE_ADAPT=off` (profile `x1_gs_t170` KHONG khai key) => `printDone.csv` **byte-identical**
`efb793e2468ca3a7318da0f0ad23d4fc` (1090 dong, 1089 trade). PASS.

## 2. n leg BIG_DOWN (chan cung #1)
| tag | n leg BIG_DOWN | scaledBdLegs (m != 1) |
|---|---|---|
| PARITY | **248** | — |
| DOWN50 | **248** | 238 |
| DOWN25 | **248** | 238 |
| UP50 | **248** | 238 |

n = 248 o ca 4 (trigger khong doi). 10/248 leg co `sev=0` (vua cham nguong) => khong scale.
PASS (khong doi so ve).

## 3. PRIMARY — chat luong rieng leg BIG_DOWN (so sanh tung bien the vs parity)
CI block 72h x1.21, 2000 resample, seed 20260905. "Tot" = pnl/leg & meanP & win tang, TSloss% giam.

| tag | pnl/leg (USD) | meanP | TSloss% | win% |
|---|---|---|---|---|
| PARITY | 65.54 | 4.786 | 8.47 | 88.71 |
| DOWN50 | 56.86 | 4.710 | 8.47 | 88.71 |
| DOWN25 | 60.73 | 4.653 | 8.47 | 88.71 |
| UP50 | 73.52 | 4.772 | 8.47 | 88.31 |

Hieu (variant - parity) + CI:

| bien the | pnl_leg | meanP | tsloss | win |
|---|---|---|---|---|
| DOWN50 | -8.68 (CI -21.25, +0.92) | -0.076 (CI -0.192, +0.018) | 0.000 | 0.000 |
| DOWN25 | -4.81 (CI -10.19, -0.76) **out** | -0.133 (CI -0.334, +0.032) | 0.000 | 0.000 |
| UP50 | +7.98 (CI -0.03, +18.65) | -0.014 (CI -0.035, +0.003) | 0.000 | -0.403 (CI -1.011, +0.096) |

- `pnl/leg` doi **co hoc** theo huong size (down => giam, up => tang), dung nhu thiet ke.
- `meanP`, `TSloss%`, `win%` deu KHONG ngoai CI o ca 3 bien the => chat luong leg KHONG doi.
- Duy nhat DOWN25 co `pnl_leg` ngoai CI (huong DOWN = khong phai huong tot cho pnl/leg).

=> Khong bien the nao dat PRIMARY (>=2/3 rate ngoai CI CUNG HUONG TOT).

## 4. Tap trung (chan cung #2)
`max % equity 1 coin` = 9.77% o **ca 4** (parity va 3 bien the). KHONG tang. PASS.
(Ghi chu: tap trung khong doi vi no bi chi phoi boi bac DCA-grid, khong phai size leg BIG_DOWN.)

## 5. Rang buoc cung tu equity THAT (`sim.out`) theo nam (chan cung #3)
Tolerance pre-reg: maxDD nam khong xau hon parity qua +3pp; khong nam am; UW khong xau hon qua +30 ngay.

| nam | PARITY maxDD/UW/ret% | DOWN50 | DOWN25 | UP50 |
|---|---|---|---|---|
| 2021 | -2.46 / 37 / +12.21 | -2.47 / 37 / +11.95 | -2.47 / 37 / +12.08 | -2.47 / 37 / +12.43 |
| 2022 | -11.84 / 72 / +19.58 | -11.89 / 72 / +18.91 | -11.87 / 72 / +19.25 | -11.80 / 72 / +20.23 |
| 2023 | -2.73 / 63 / +34.96 | -1.69 / 62 / +35.46 | -2.21 / 62 / +35.24 | -3.77 / 63 / +34.30 |
| 2024 | -6.60 / 92 / +32.14 | -6.81 / 119 / +29.95 | -6.70 / 119 / +31.09 | -6.41 / 88 / +33.99 |
| 2025 | -4.23 / 52 / +32.71 | -4.25 / 52 / +35.55 | -4.24 / 52 / +33.81 | -4.22 / 52 / +30.67 |

- Khong nam am o bat ky bien the nao (parity cung khong).
- maxDD nam xau nhat: DOWN50 -6.81 (2024) vs parity -6.60 => -0.21pp, trong +3pp. UP50 2023 -3.77 vs -2.73 => -1.04pp, trong +3pp.
- UW 2024: DOWN50/DOWN25 = 119 vs parity 92 => +27 ngay, trong +30 ngay (sat nguong). UP50 = 88 (tot hon).
=> PASS het, nhung chu y: down-size lam UW 2024 dai hon (119 vs 92) — phuc hoi cham hon, trai nguoc y dinh "an toan".

## 6. Rate TOAN BO leg (chan cung #4)
win%/TSloss%/meanP toan bo leg: khong rate nao XAU ngoai CI o ca 3 bien the.
`margin/leg` doi co hoc (DOWN50 -64.5 USD, UP50 +64.4 USD, ngoai CI) = dung la size thay doi, khong phai chat luong.

| tag | n | win% | TSloss% | meanP | margin/leg |
|---|---|---|---|---|---|
| PARITY | 1089 | 88.25 | 9.73 | 5.244 | 1851 |
| DOWN50 | 1091 | 88.18 | 9.72 | 5.115 | 1787 |
| DOWN25 | 1090 | 88.26 | 9.72 | 5.125 | 1825 |
| UP50 | 1088 | 88.14 | 9.74 | 5.302 | 1916 |

## 7. Tong quan danh muc (tham khao, KHONG phai tieu chi)
| tag | end equity | CAGR% | maxDD% | UW ngay |
|---|---|---|---|---|
| PARITY | 111070 | 29.27 | -11.84 | 92 |
| DOWN50 | 111113 | 29.28 | -11.89 | 119 |
| DOWN25 | 110899 | 29.22 | -11.87 | 119 |
| UP50 | 111171 | 29.29 | -11.80 | 88 |

## 8. Multiplicity
k=3 bien the x 3 rate PRIMARY. Nguong thang dung he so B4 `sqrt(2 ln 3) = 1.4823` khi so tren cung
khung. Khong bien the nao cham 2/3 rate ngoai CI NGAY CA CHUA ap multiplicity => khong can noi rong
them. Ket luan NULL KHONG phu thuoc he so multiplicity.

## 9. Ket luan
Severity-based sizing leg BIG_DOWN (N=120 causal) **chi doi thang do** (`pnl/leg`, `margin/leg`),
**khong doi chat luong** (`meanP`) **va khong doi rui ro** (`TSloss%`, tap trung, maxDD/UW). Dong
nhau the hien o ca 3 huong: giam (down50/down25) khong giam rui ro (con lam UW 2024 dai hon), tang
(up50) khong tang chat luong (meanP khong doi). **NULL — giu T170.** Hop nhat voi Q5: sizing toan
cuc hay co dieu kien deu khong sinh alpha tren chat luong tung lenh BIG_DOWN.
