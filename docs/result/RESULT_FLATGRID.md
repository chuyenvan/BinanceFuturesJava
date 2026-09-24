# RESULT ? Lam phang luoi DCA 1,1,3,8 -> 1,1,1,1

Pre-reg: `docs/prereg/PREREG_FLATGRID.md` (commit `59a7291`, viet TRUOC khi chay).
Dataset `wfo_ds_x1_2021` (2021-07..2025-12). Jar `a577c8481727c159062e9353f612c256`.
**KHONG sua mot dong code Java** ? chi doi 1-2 key trong profile.

## 0. Cong parity ? PASS

| tag | profile | md5 printDone.csv | ky vong |
|---|---|---|---|
| `FG_PARITY_T170` | `x1_gs_t170.properties` | `efb793e2468ca3a7318da0f0ad23d4fc` | `efb793e2468ca3a7318da0f0ad23d4fc` |

**BYTE-IDENTICAL.** 1089 leg, `b:111070`. Cong parity mo.

---

## 1. Bang chinh

| | T170 (goc) | FG_KEEPSCALE | FG_KEEPLEG0 |
|---|---|---|---|
| `DCA_GRID_WEIGHTS` | 1,1,3,8 | **1,1,1,1** | **1,1,1,1** |
| `DCA_GRID_SCALE` | 19.5 | 19.5 | **6.0** |
| margin bac 0 (danh dinh) | 4.500% | **14.625%** | 4.500% |
| margin bac 1/2/3 | 4.5 / 13.5 / 36.0% | 14.625% x3 | 4.5 / 4.5 / 4.5% |
| **TRAN tap trung 1 coin (ly thuyet)** | **58.5%** | **58.5%** | **18.0%** |
| leg | 1089 | 1025 | 1085 |
| equity cuoi | 111,070 | 178,182 | 103,083 |
| **CAGR** | **29.27%** | 43.59% | **27.14%** |
| maxDD toan ky | -11.84% | -15.61% | -11.21% |
| **UW toan ky (ngay)** | **92** | **178** | **147** |
| max tap trung 1 coin (DO DUOC) | 8.71% | 16.73% | **6.98%** |
| max margin bac 0 (DO DUOC) | 4.544% | **15.659%** | 4.549% |

## 2. Theo nam

**T170 (goc)** ? rang buoc cung theo nam: PASS

| nam | n | win% | TSloss% | meanP | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | 149 | 92.62 | 7.38 | 4.37 | 12.21 | -2.46 | 37 | 4.44 | 39,272 |
| 2022 | 198 | 83.84 | 11.11 | 3.86 | 19.58 | -11.84 | 72 | 2.90 | 46,960 |
| 2023 | 126 | 88.10 | 15.87 | 8.07 | 34.96 | -2.73 | 63 | -0.37 | 63,378 |
| 2024 | 281 | 90.04 | 10.68 | 4.77 | 32.14 | -6.60 | 92 | -0.92 | 83,695 |
| 2025 | 335 | 87.46 | 6.87 | 5.78 | 32.71 | -4.23 | 52 | 1.27 | 111,070 |

**FG_KEEPSCALE** ? rang buoc cung theo nam: **FAIL** (2022 maxDD -15.61 | 2024 UW 178, qmin -5.58 | 2025 UW 128)

| nam | n | win% | TSloss% | meanP | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | 136 | 91.91 | 8.09 | 4.27 | 15.33 | -5.27 | 38 | 6.79 | 40,366 |
| 2022 | 184 | 82.61 | 14.67 | 2.58 | 21.33 | **-15.61** | 73 | -3.37 | 48,977 |
| 2023 | 126 | 88.10 | 15.87 | 8.07 | 68.56 | -8.20 | 89 | -1.79 | 82,554 |
| 2024 | 261 | 89.27 | 11.49 | 4.44 | 56.10 | -14.39 | **178** | **-5.58** | 128,612 |
| 2025 | 318 | 86.79 | 9.12 | 7.37 | 38.54 | -11.42 | **128** | 0.85 | 178,182 |

**FG_KEEPLEG0** ? rang buoc cung theo nam: PASS; **theo TOAN KY: FAIL (UW 147 > 120)** ? xem muc 4

| nam | n | win% | TSloss% | meanP | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | 149 | 92.62 | 7.38 | 4.37 | 12.21 | -2.46 | 37 | 4.44 | 39,272 |
| 2022 | 196 | 82.65 | 14.29 | 2.24 | 12.59 | -11.21 | 72 | -1.08 | 44,215 |
| 2023 | 126 | 88.10 | 15.87 | 8.07 | 34.96 | -2.73 | 63 | -0.37 | 59,673 |
| 2024 | 281 | 90.04 | 10.68 | 4.77 | 32.13 | -6.60 | 92 | -0.92 | 78,801 |
| 2025 | 333 | 87.99 | 6.91 | 6.42 | 30.81 | -4.23 | 52 | 1.27 | 103,083 |

Chu y: 2021 / 2023 / 2024 cua KEEPLEG0 **trung KHIT** T170 (cung n, cung win/TSloss/meanP).
Dung nhu du doan trong pre-reg: bac 0 va bac 1 co margin y het nhau, chi bac 2-3 moi khac,
ma bac 2 chi xay ra 4 lan.

## 3. CI (k=2, `CI_INFLATE = sqrt(2 ln 2) = 1.177410`, block 72h, 2000 rep, seed 20260905)

**(FG_KEEPSCALE) ? (T170)**

| rate | hieu | lo | hi | ngoai CI | huong |
|---|---|---|---|---|---|
| win% | -0.734 | -1.420 | -0.120 | CO | **XAU** |
| TSloss% | +1.681 | +0.225 | +3.029 | CO | **XAU** |
| meanP | +0.195 | -0.800 | +1.344 | - | - |

=> **0 TOT / 2 XAU**.

**(FG_KEEPLEG0) ? (T170)**

| rate | hieu | lo | hi | ngoai CI | huong |
|---|---|---|---|---|---|
| win% | -0.043 | -0.514 | +0.397 | - | - |
| TSloss% | +0.589 | -0.084 | +1.416 | - | - |
| meanP | -0.097 | -0.680 | +0.459 | - | - |

=> **0 TOT / 0 XAU** ? khong phan biet duoc voi T170 o ca 3 ty le chat luong.

## 4. DIEM QUAN TRONG NHAT ? UW toan ky cua KEEPLEG0 (khong duoc giau)

Rang buoc cung tinh **theo nam** cho KEEPLEG0 ra PASS. Nhung `research/analysis/c3_rates.py`
? chinh la harness da dung de chot incumbent T170 ? kiem `UW` tren **TOAN KY**. Do tren toan ky:

| config | UW toan ky | doan dai nhat |
|---|---|---|
| T170 (goc) | **92** | 2024-04-10 -> 2024-07-10 |
| FG_KEEPLEG0 | **147** | **2022-11-09 -> 2023-04-04** |
| FG_KEEPSCALE | **178** | 2024-04-10 -> 2024-10-04 |

Doan 147 ngay cua KEEPLEG0 **vat qua ranh gioi nam** (72 ngay roi vao 2022 + 63 ngay roi vao 2023),
nen goc nhin theo-nam **khong nhin thay no**. Tren T170 chinh doan do chi dai **63 ngay**
(2022-11-13 -> 2023-01-14).

**Nguyen nhan co hoc, truy duoc den tung cum:** do la cu sup FTT thang 11/2022. Cum
`FTT 2022-11-09`:

| config | tong margin | % equity | **PnL** |
|---|---|---|---|
| T170 (bac 1,1,3,8) | 3,957 | 8.71% | **+353** |
| FG_KEEPLEG0 (bac 1,1,1,1) | 2,844 | 6.39% | **-1,261** |

Bac sau nang (w=3) chinh la thu da **cuu** cum FTT tren T170. Lam phang no => mat cai cuu do
=> lo, va thoi gian duoi nuoc keo tu 63 len 147 ngay.

**=> Day chinh xac la cai gia cua "khong cuu duoc thi thoi" ma user chap nhan.** Nhung phai noi ro:
gia do **khong** hien ra o do sau drawdown (maxDD con TOT hon: -11.21 vs -11.84), ma hien ra o
**thoi gian duoi nuoc**.

## 5. Tap trung rui ro ? muc tieu that su cua yeu cau nay

| | T170 | KEEPSCALE | KEEPLEG0 |
|---|---|---|---|
| TRAN ly thuyet nhoi het luoi | 58.5% | **58.5% (KHONG doi)** | **18.0%** |
| max % equity 1 coin (do duoc) | 8.71% | 16.73% | **6.98%** |
| p99 % equity 1 coin | ? | 14.63% | 4.50% |
| max margin bac 0 | 4.544% | **15.659%** | 4.549% |
| so cum cham bac 1 / 2 / 3 | 16 / 4 / 0 | 15 / 4 / 0 | 16 / 4 / 0 |

- **KEEPLEG0 dat dung muc tieu:** tran tap trung **58.5% -> 18.0%** (giam 3.25 lan), rui ro
  entry dau **khong doi** (4.544% -> 4.549%), max thuc te 8.71% -> 6.98%.
- **KEEPSCALE khong giam gi ca** ? tran van 58.5% ? va con lam rui ro entry dau **tang 3.44 lan**
  (4.544% -> 15.659%). Dung nhu canh bao o muc 0 cua pre-reg.

## 6. VERDICT

| config | rate (k=2) | rang buoc cung theo nam | rang buoc cung toan ky | verdict |
|---|---|---|---|---|
| FG_KEEPSCALE | 0 TOT / **2 XAU** | **FAIL** (3/5 nam) | **FAIL** (UW 178) | **LOAI** |
| FG_KEEPLEG0 | 0 TOT / 0 XAU (NULL) | PASS | **FAIL** (UW 147) | **NULL ? khong dat luat thang** |

**Khong doi incumbent. T170 giu nguyen.** Luat thang doi hoi >= 2 rate ngoai CI huong TOT;
KEEPLEG0 duoc 0. Va no truot rang buoc UW toan ky.

### Tra loi thang cau hoi "doi sang luoi phang mat bao nhieu de doi lay giam rui ro tap trung"

| | gia phai tra | doi lay |
|---|---|---|
| CAGR | **29.27% -> 27.14% (-2.13 pp)** | |
| equity cuoi | 111,070 -> 103,083 (**-7.19%**) | |
| UW toan ky | **92 -> 147 ngay (+55)** | |
| maxDD toan ky | -11.84% -> -11.21% (**tot hon**) | |
| chat luong lenh | khong doi (0/3 rate khac biet) | |
| | | **tran tap trung 1 coin 58.5% -> 18.0%** |
| | | max thuc te 8.71% -> 6.98% |
| | | rui ro entry dau KHONG doi |

Neu user chap nhan **-2.13 pp CAGR va +55 ngay duoi nuoc** de doi lay **tran rui ro 1 coin
giam tu 58.5% xuong 18.0%**, thi `FLAT_KEEPLEG0` la cau hinh dung. Day la **quyet dinh khau vi
rui ro, khong phai quyet dinh thong ke** ? so lieu noi hai cau hinh cho chat luong lenh
KHONG phan biet duoc.

**Neu chon doi:** phai dung `DCA_GRID_SCALE=6.0` cung luc voi `DCA_GRID_WEIGHTS=1,1,1,1`.
Doi mot minh `DCA_GRID_WEIGHTS` (= KEEPSCALE) la **cai bay**: khong giam rui ro gi, ma
phong to moi lenh len 3.25 lan va pha vo rang buoc cung o 3/5 nam.

## 7. Doi chieu voi du doan ghi truoc (pre-reg muc 5)

| du doan | thuc te | dung/sai |
|---|---|---|
| KEEPLEG0 ~ trung T170, 0/3 rate ngoai CI | 0/3 rate ngoai CI | **DUNG** |
| KEEPLEG0 equity lech trong +/-3% | lech **-7.19%** | **SAI** (lech gap doi du doan) |
| KEEPLEG0 hard-constraint PASS y T170 | PASS theo nam, **FAIL toan ky UW 147** | **SAI mot phan** |
| KEEPSCALE FAIL rang buoc cung, maxDD>15 it nhat 1 nam | FAIL 3/5 nam, 2022 maxDD -15.61 | **DUNG** |
| KEEPSCALE tap trung KHONG giam (~58.5%) | tran van 58.5% | **DUNG** |
| KEEPLEG0 max thuc te ~5-6% | **6.98%** | gan dung (hoi cao hon) |

Hai cho du doan sai deu do cung mot nguyen nhan chua luong het: bo bac nang w=3/w=8 khong chi
"it dung den" ma con **bo mat chuc nang cuu cum trong su kien duoi sau** (FTT 11/2022).

## 8. Ky luat
Khong push. Khong cham 242. Khong dong holdout 2026. Khong do them bo trong so / SCALE nao
ngoai 2 bien the da khoa trong pre-reg. Khong sua/xoa test cu. Khong doi incumbent.
