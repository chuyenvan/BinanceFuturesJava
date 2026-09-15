# RESULT ? GD92 chay lai tren dataset chuan `wfo_ds_x1_2021`

Pre-reg: `docs/PREREG_GD92_RECHECK.md` (commit `f9eda30`, viet TRUOC khi build/chay).
Branch `gd92-recheck` (KHONG merge vao `module`), commit code `1db0613`.
Jar `a8ea360583d14c1cf4be449a08985d6f` (`mvn -o package`, tests BAT, BUILD SUCCESS).

## 0. Xac minh truoc khi chay ? ca hai deu DAT

**(a) Code khop git history 100%**

| nguon | dong | md5 |
|---|---|---|
| `git show f1c43a3^:.../GateRollingThreshold.java` | 149 | `e1e99295c76bfd066493ca25ebeb1243` |
| block java trong `gate_feat_study/GD92_CODE_AND_RESULTS.md` | 149 | `e1e99295c76bfd066493ca25ebeb1243` |

`diff` rong. Dung ban `git show` (khong dung ban trich tu `.md`).

**(b) Cong parity ? BYTE-IDENTICAL**

| tag | profile | md5 do duoc | md5 tham chieu |
|---|---|---|---|
| `GD_PARITY_C3` | `x1_c3_full.properties` | `dc16e4da6ff6cb7b8d41c592bc3d9c45` | `dc16e4da6ff6cb7b8d41c592bc3d9c45` |

`b:121770`, 2559 leg. Ba thay doi code (them lai class + 1 dong `thrBase` + 2 cho `init`)
**KHONG dich mot bit nao** khi `SIM_GATE_ROLLING_PCT` khong khai bao.

**(c) Cau hinh GD92 dung ban goc**: `PROFILE_HASH=52ee74bb5477b363 keys=21` ? **khop chinh xac**
`PROFILE_HASH` cua run GD92 cu (`devrun/X1_C3_FULL_GD92`). Dung `profiles/archive/x1_gd92.properties`
nguyen van, khong soan moi.

**(d) `[GATE-ROLL]` da BAT that:** `pct=0.92 window=90d | 39510 moc gio | moc dau 1624989600000
(2021-06-30) | nguong min=0.00456 max=0.01265`.
**KHONG co canh bao `truy van TRUOC moc gio dau tien`** => `nBeforeFirst = 0`, toan bo cua so
2021-07..2025-12 co nguong truot that. (Du doan trong pre-reg la se co khoang trong warm-up
dau 2021 ? **SAI**: `predictionMap` co du lieu truoc ngay bat dau sim nen moc dau da san sang.)
Nguong truot chay trong dai **0.456% - 1.265%** quanh hang so cu 0.800%.

---

## 1. Bang chinh ? 3 config tren CUNG dataset `wfo_ds_x1_2021`

| | T100 (nen cua GD92) | **GD92** | T170 (INCUMBENT) |
|---|---|---|---|
| gate scale | 1.00 | 1.00 | 1.70 |
| rolling gate | khong | **p15 pct=0.92 W=90d** | khong |
| leg | 2559 | 2632 | 1089 |
| equity cuoi | 121,770 | **133,944** | 111,070 |
| **CAGR** | 31.94% | **34.76%** | 29.27% |
| maxDD toan ky | -16.13% | **-16.55%** | **-11.84%** |
| UW toan ky (ngay) | 248 | **278** | **92** |
| doan UW dai nhat | 2021-11-16 -> 2022-07-21 | 2021-11-16 -> 2022-08-20 | 2024-04-10 -> 2024-07-10 |
| max tap trung 1 coin | ? | 14.32% | 8.71% |

## 2. Theo nam

**GD92** ? rang buoc cung **theo nam**: PASS

| nam | n | win% | TSloss% | meanP | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|
| 2021 | 277 | 79.78 | 20.22 | 1.66 | 3.83 | -7.74 | 47 | -0.65 | 36,342 |
| 2022 | 416 | 79.57 | 19.71 | 1.28 | 7.26 | -13.21 | 69 | -3.81 | 38,980 |
| 2023 | 509 | 86.05 | 16.50 | 4.66 | 74.11 | -5.24 | 63 | 13.32 | 67,868 |
| 2024 | 792 | 84.47 | 16.29 | 3.57 | 43.91 | -11.36 | 114 | -4.59 | 97,935 |
| 2025 | 638 | 85.11 | 11.60 | 3.97 | 36.77 | -6.11 | 116 | 1.72 | 133,944 |

**T100** ? theo nam: FAIL (2024 UW 121 | 2025 UW 227). **T170** ? theo nam: PASS.

## 3. CI (k=2, `sqrt(2 ln 2) = 1.177410`, block 72h, 2000 rep, seed 20260905)

**(GD92) ? (T170)** ? phep thu chinh

| rate | hieu | lo | hi | ngoai CI | huong |
|---|---|---|---|---|---|
| win% | **-4.583** | -7.445 | -2.164 | CO | **XAU** |
| TSloss% | **+6.414** | +3.967 | +8.947 | CO | **XAU** |
| meanP | **-1.929** | -2.953 | -0.989 | CO | **XAU** |

=> **0 TOT / 3 XAU.** GD92 thua T170 o CA BA ty le chat luong, ca ba deu ngoai CI.

**(GD92) ? (T100)** ? tach rieng CONG CUA ROLLING (cung gate scale 1.0)

| rate | hieu | lo | hi | ngoai CI | huong |
|---|---|---|---|---|---|
| win% | -0.667 | -4.583 | +3.451 | - | - |
| TSloss% | +0.790 | -3.514 | +5.087 | - | - |
| meanP | +0.142 | -1.723 | +1.955 | - | - |

=> **0 TOT / 0 XAU.** Co che rolling **khong tao ra khac biet chat luong lenh nao do duoc**
so voi chinh cai nen cua no.

---

## 4. CHO QUAN TRONG NHAT ? "PASS theo nam" cua GD92 la ao anh cua goc nhin

Rang buoc cung tinh **theo nam** cho GD92 ra PASS. Nhung `research/analysis/c3_rates.py`
? harness da dung de chot incumbent ? kiem `maxDD` va `UW` tren **TOAN KY**:

| config | maxDD toan ky | UW toan ky | ket luan theo harness |
|---|---|---|---|
| T170 | -11.84% | 92 | **PASS** |
| T100 | -16.13% | 248 | FAIL |
| **GD92** | **-16.55%** | **278** | **FAIL ? te hon ca T100** |

Doan duoi nuoc 278 ngay cua GD92 la **2021-11-16 -> 2022-08-20**, **vat qua ranh gioi nam**
(47 ngay roi vao 2021 + 69 ngay roi vao 2022 theo goc nhin nam), nen bang theo-nam khong nhin thay no.

### Vi sao lan truoc GD92 bao "UW 227 -> 116 PASS"?
Run GD92 goc chay tren `wfo_ds_x1` bat dau **2022-01-01** ? tuc **bat dau O GIUA** doan sut nay.
Backtest khoi dong lai `equity = 35000` va reset dinh, nen phan duoi nuoc da dien ra truoc
2022-01-01 **bi xoa khoi so sach**. Them 1.5 nam 2021 (dung bai test "kho hon" ma master yeu cau)
lam lo ra doan 278 ngay do.

Day **khong** phai loi cua nguoi chay GD92 ? do la dieu tat yeu khi doi cua so du lieu.
Nhung no co nghia: **con so UW cua GD92 lan truoc khong so sanh duoc voi con so UW hom nay.**

## 5. VERDICT

| so sanh | rate (k=2) | rang buoc cung (toan ky) | ket luan |
|---|---|---|---|
| GD92 vs **T170** | 0 TOT / **3 XAU** | GD92 **FAIL** (maxDD -16.55, UW 278) | **GD92 THUA** |
| GD92 vs **T100** | 0 TOT / 0 XAU | ca hai FAIL | **NULL** |

**GD92 KHONG dao duoc incumbent. T170 giu nguyen.**

GD92 co **equity cao nhat (133,944) va CAGR cao nhat (34.76%)** trong ba config ? nhung
theo luat da khoa tu truoc, equity/CAGR **khong phai tieu chi**; tieu chi la 3 ty le chat luong
+ rang buoc cung. GD92 thua ca hai: 3/3 ty le xau hon T170 va truot ca maxDD lan UW toan ky.

### Phai cong nhan cho GD92 (khong duoc giau)
Tren **goc nhin theo nam**, GD92 that su sua duoc benh cua T100: 2025 UW **227 -> 116**,
2024 UW **121 -> 114**. Neu chi nhin theo nam thi GD92 la ban T100 "da chua benh UW".
Nhung (a) cai gia la maxDD va UW toan ky **te hon** T100, va (b) so voi T170 thi chat luong
lenh kem han ba mat.

---

## 6. PHAN BIEN (bat buoc theo pre-reg muc 7 ? nhanh (b): GD92 THUA/NULL)

**Day la bang chung doc lap THU HAI cung cho ket luan cua `docs/AUDIT_GATEDYN_GD92.md`,
khong phai trung hop.** Bon thu khac nhau giua hai lan:

| | audit lan 1 (11/09) | lan nay (15/09) |
|---|---|---|
| dataset | `wfo_ds_x1` (2022-01..2025-12) | `wfo_ds_x1_2021` (2021-07..2025-12) |
| baseline doi chieu | PARITY_R (T100 cua thoi do) | **T170** (incumbent hien tai) + T100 |
| he so CI | 1.21 (hang so sai) | **sqrt(2 ln 2) = 1.177410** |
| so nam rang buoc cung | 4 | **5** |
| ket luan | d CAGR +4.98pp, CI [-4.47, +16.09] **chua 0** => khong phan biet duoc | GD92 ? T100: **0/3 rate ngoai CI** => khong phan biet duoc |

Hai duong hoan toan khac nhau (mot do hieu CAGR, mot do 3 ty le chat luong; khac dataset,
khac baseline, khac he so) cung ra **cung mot ket luan: rolling gate khong tao khac biet do duoc.**
Lan nay con manh hon vi co them 1.5 nam du lieu GD92 chua tung thay, va chinh phan du lieu
them do lam lo ra doan duoi nuoc 278 ngay ma cua so cu che mat.

**Ve multiplicity cap chuong trinh:** k=2 o day chi phu cho **vong nay**. Tinh ca chuong trinh,
day la phep thu thu **~24** da chay chong T170 (11 huong nghien cuu truoc + FLATGRID 2 bien the
+ GD92). Neu GD92 co thang thi cung **khong du** de dao incumbent voi mot ket qua don le ?
se phai qua holdout 2026 truoc. Vi GD92 **thua**, van de multiplicity khong can vien den:
ket luan khong doi du chinh he so the nao.

**Ve cam ket khong do them:** da chay **DUNG 1 cau hinh** (pct=0.92, W=90d). Khong chay
0.88/0.90/0.94/0.96, khong chay W=60/120/180, khong chay lang gieng nao. Dong lai tai day ?
dung nhu pre-reg muc 1 da khoa, va dung de khong lap lai vi pham ma audit da vach ra o GATEDYN2.

## 7. Doi chieu voi du doan ghi truoc (pre-reg muc 6)

| du doan | thuc te | dung/sai |
|---|---|---|
| GD92 se NULL (0-1 rate ngoai CI) vs T170 | **3 rate ngoai CI, tat ca XAU** | **SAI** ? GD92 con te hon du doan |
| GD92 FAIL rang buoc cung o 2025 | 2025 PASS (UW 116); FAIL o **toan ky** (UW 278, 2021-11->2022-08) | **SAI cho nam, DUNG cho ket cuc** |
| co khoang trong warm-up rolling dau 2021 | `nBeforeFirst = 0`, khong co khoang trong | **SAI** |

Ba du doan deu lech. Ghi lai day du thay vi im lang.

## 8. Ky luat
Khong push. Branch `gd92-recheck` **khong merge** vao `module`. Khong cham 242.
Khong dong holdout 2026. Khong do them bien the GD92. Khong doi incumbent.
