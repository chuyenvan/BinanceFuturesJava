# RESULT_NOBD_READJUDICATE — T170 co con thang khi TAT HAN leg khong-qua-gate?

Chay 2026-09-15. Pre-reg `docs/prereg/PREREG_NOBD_READJUDICATE.md` (commit 8b2ada8, **TRUOC** khi doi bat cu thu gi).
**KHONG SUA MOT DONG CODE NAO** — chay tren jar HEAD `d3379e5`. Dataset `wfo_ds_x1_2021`,
`SIM_END_DATE=20251231`, harness `k_runarm.sh`. KHONG 242, KHONG push, holdout 2026 nguyen ven.

## 1. HAI CONG BAT BUOC — PASS CA HAI
### 1a. Parity OFF (chung minh jar hien tai van tai lap dung 3 baseline goc)
| cong | tag | md5 ra | ky vong | ket qua |
|---|---|---|---|---|
| OFF scale 1.00 | `NB_PAR_T100` | `dc16e4da6ff6cb7b8d41c592bc3d9c45` (n=2559, b:121770) | `dc16e4da…` | **PASS** |
| OFF scale 1.30 | `NB_PAR_T130` | `68510567e9b17430b3453b08abe03e9b` (n=1580, b:92616) | `68510567…` | **PASS** |
| OFF scale 1.70 | *(cite)* | `efb793e2…` — da PASS 2 lan tren CHINH jar nay (`DS_PARITY_V3`, `DS_PARITY_V4`) | `efb793e2…` | **PASS** |

T100/T130 **chua** tung chay lai tren jar hien tai => cong nay cung chung minh cac thay doi code V1/V2
(`DCA_SIGNAL_*`, tie-break) **khong dung vao** hai baseline do.

### 1b. Cong ZERO-LEG (thay cho unit test — xem PREREG muc 1.2)
| tag | n | BIG_DOWN | DCA_LEVEL1 | PREDICT_SYMBOL_TRADE | ket qua |
|---|---|---|---|---|---|
| `NB_T100_NOBD` | 2323 | **0** | **0** | 2323 (100%) | **PASS** |
| `NB_T130_NOBD` | 1383 | **0** | **0** | 1383 (100%) | **PASS** |
| `NB_T170_NOBD` | 900 | **0** | **0** | 900 (100%) | **PASS** |

## 2. BANG CHINH — 3 ban NOBD vs 3 ban GOC
| tag | n | win% | TSloss% | meanP | mMargin | maxDD% | UW | equity | CAGR% |
|---|---|---|---|---|---|---|---|---|---|
| T100 (goc) | 2559 | 84.33 | 15.36 | 3.173 | 1983 | -16.13 | 248 | **121,770** | **31.94** |
| T130 (goc) | 1580 | 85.57 | 13.48 | 3.755 | 1813 | -18.34 | 221 | 92,616 | 24.15 |
| **T170 (goc)** | 1089 | 88.25 | **9.73** | **5.244** | 1851 | -11.84 | **92** | 111,070 | 29.27 |
| T100_NOBD | 2323 | 84.67 | 15.50 | 2.728 | 1940 | -17.17 | 302 | **106,254** | **28.00** |
| T130_NOBD | 1383 | 86.12 | 13.96 | 3.314 | 1752 | -11.34 | 224 | 86,162 | 22.17 |
| **T170_NOBD** | 900 | **89.22** | **10.56** | **4.466** | 1752 | **-9.90** | 225 | 90,247 | 23.44 |

md5: T100_NOBD `b30a8d15…` · T130_NOBD `99aa3595…` · T170_NOBD `4ecb4b1a…`

**Luu y quan trong — day la COUNTERFACTUAL THAT, khong phai phep tru:** T170 goc co 1089 leg, trong do
248 BIG_DOWN + 20 DCA. Neu chi "tru di" thi con **821**. Thuc te NOBD ra **900** (+79). Ly do: bo hai
nhom leg do **giai phong margin** => throttle `managerBudget` cao hon => **them entry duoc nhan**.
Tuong tu T100: 2559 − 248 − 54 = 2257 nhung thuc te **2323** (+66).
=> **Audit tren giay (d3379e5) khong the thay hieu ung nay.** Day chinh la ly do phai chay sim that.

## 3. MAT BAO NHIEU khi bo BIG_DOWN + DCA_LEVEL1
| scale | equity goc | equity NOBD | **d equity%** | CAGR goc | CAGR NOBD | **d CAGR (pp)** |
|---|---|---|---|---|---|---|
| T100 | 121,770 | 106,254 | **−12.7%** | 31.94 | 28.00 | **−3.94** |
| T130 | 92,616 | 86,162 | **−7.0%** | 24.15 | 22.17 | **−1.98** |
| **T170** | 111,070 | 90,247 | **−18.7%** | 29.27 | 23.44 | **−5.83** |

**T170 mat NHIEU NHAT** — dung theo huong ma audit d3379e5 da do (ti trong PnL khong-qua-gate:
T100 22.7% / T130 27.9% / **T170 38.1%**). Con so nay xac nhan bang thi nghiem that.

## 4. THEO TUNG NAM (ban NOBD, equity THAT tu sim.out)
| tag | nam | ret% | pnl$ | maxDD% | UW | qmin% | n_leg |
|---|---|---|---|---|---|---|---|
| T100_NOBD | 2021 | 7.85 | 2,748 | -7.60 | 47 | -1.60 | 265 |
| T100_NOBD | 2022 | 9.52 | 3,592 | -13.31 | 64 | -4.75 | 360 |
| T100_NOBD | 2023 | 64.26 | 26,567 | -2.63 | 57 | 8.32 | 289 |
| T100_NOBD | 2024 | 42.80 | 29,049 | -11.13 | **121** | -4.59 | 625 |
| T100_NOBD | 2025 | 9.63 | 9,335 | -12.15 | **302** | -2.78 | 784 |
| T130_NOBD | 2021 | 7.14 | 2,499 | -6.44 | 44 | 0.68 | 173 |
| T130_NOBD | 2022 | 9.31 | 3,490 | -11.34 | **129** | -3.42 | 226 |
| T130_NOBD | 2023 | 47.52 | 19,476 | -2.23 | 35 | 4.40 | 173 |
| T130_NOBD | 2024 | 27.89 | 16,853 | -10.08 | **141** | -4.15 | 370 |
| T130_NOBD | 2025 | 11.49 | 8,877 | -9.05 | **224** | -1.29 | 441 |
| **T170_NOBD** | 2021 | 10.66 | 3,732 | -2.64 | 38 | 3.48 | 126 |
| **T170_NOBD** | **2022** | 10.20 | 3,951 | -9.90 | **131** | -2.19 | 171 |
| **T170_NOBD** | 2023 | 36.95 | 15,770 | -0.51 | 43 | 0.00 | 97 |
| **T170_NOBD** | 2024 | 27.31 | 15,962 | -7.12 | 88 | -0.99 | 243 |
| **T170_NOBD** | 2025 | 21.28 | 15,832 | -5.12 | 54 | 0.84 | 263 |

**Rang buoc cung (maxDD<=15, UW<=120, nam>=0, quy>=-5):**
| tag | 2021 | 2022 | 2023 | 2024 | 2025 | tong |
|---|---|---|---|---|---|---|
| T100_NOBD | PASS | PASS | PASS | **FAIL (UW 121)** | **FAIL (UW 302)** | **FAIL** |
| T130_NOBD | PASS | **FAIL (UW 129)** | PASS | **FAIL (UW 141)** | **FAIL (UW 224)** | **FAIL** |
| **T170_NOBD** | PASS | **FAIL (UW 131)** | PASS | PASS | PASS | **FAIL (1 nam duy nhat)** |

## 5. CI — k=2, `CI_INFLATE = sqrt(2·ln 2) = 1.1774` (hieu = variant − T100_NOBD)
Huong TOT cho variant: win% duong, TSloss% am, meanP duong.

### T170_NOBD − T100_NOBD
| rate | hieu | CI 1.177 | ngoai CI |
|---|---|---|---|
| **win%** | **+4.547** | [+0.214, +8.781] | **YES (tot)** |
| **TSloss%** | **−4.942** | [−9.194, −0.525] | **YES (tot)** |
| meanP | +1.738 | [−0.022, +3.705] | - (sat bien) |
=> **2 rate CHAT LUONG ngoai CI, DEU huong TOT.** (o 1.21 doi chieu: cung 2 rate.)

### T130_NOBD − T100_NOBD
| rate | hieu | CI 1.177 | ngoai CI |
|---|---|---|---|
| win% | +1.442 | [−0.381, +3.255] | - |
| TSloss% | −1.542 | [−3.364, +0.352] | - |
| meanP | +0.586 | [−0.102, +1.273] | - |
=> **0 rate.** NULL, y het vong goc.

## 6. PHAN QUYET — noi thang
Luat: **THANG** = (>=2 rate chat luong ngoai CI huong TOT) **VA** (rang buoc cung PASS **MOI nam**).

| config | rate ngoai CI huong tot | hard-constraint | **VERDICT** |
|---|---|---|---|
| **T170_NOBD** | **2** (win%, TSloss%) — **DAT** | **FAIL** (2022, UW=131 > 120) | **NULL** |
| T130_NOBD | 0 | FAIL (2022, 2024, 2025) | **NULL** |

**=> T170_NOBD KHONG THANG.** No dat ve nhanh THONG KE (2 rate) nhung **truot rang buoc cung o dung MOT
nam (2022, UW 131 so voi tran 120)**.

### Diem phai noi ro: **du doan pre-reg cua toi SAI**
PREREG muc 5 ghi: *"ky vong T170_NOBD KHONG dat nguong >=2 rate => NULL"* (dua tren audit giay chi thay
1 rate). **Thuc te sim that cho 2 rate** — `win%` tu `+3.770` (trong CI o phan ra giay) len **`+4.547`
(ngoai CI)**. Ly do: phan ra giay khong tinh duoc phan **79 entry moi** sinh ra khi margin duoc giai
phong. **Ghi nhan: toi da doan sai, va do la ly do bat buoc phai chay sim that thay vi tin audit giay.**

### T170 van la ban TOT NHAT trong ba, nhung khong con "sach tuyet doi"
- **Chat luong**: T170_NOBD tot nhat ca ba rate (win **89.22** / TSloss **10.56** / meanP **4.466**)
  va la ban DUY NHAT co >=2 rate ngoai CI.
- **Rui ro**: maxDD tot nhat (**−9.90** vs −17.17 / −11.34); chi vi pham **1 nam** (T100_NOBD vi pham 2
  nam, T130_NOBD vi pham 3 nam).
- **Nhung**: ban GOC T170 **PASS ca 5 nam tuyet doi** (2022 UW=**72**). Bo BIG_DOWN+DCA ra thi 2022
  **UW no 72 → 131**. **Vay cac leg khong-qua-gate CHINH LA thu giu cho T170 sach o 2022.**
- Loi nhuan: T100_NOBD van cao nhat ve equity (106,254) nhung **rui ro te nhat** (maxDD −17.17, UW 302,
  vi pham 2 nam) => khong phai ung vien thay the.

### Tra loi truc tiep cau hoi nen tang cua vong nay
**"T170 thang la nho entry gioi hay nho leg BIG_DOWN?"** — **CA HAI, va tach ra thi khong con du.**
- Phan **entry** that su tot hon va **du manh ve thong ke** (2 rate ngoai CI, k=2 dung) — manh hon ca
  cai audit giay tuong.
- Nhung phan **rang buoc cung** — thu ma vong goc dung de tuyen bo T170 "PASS ca 5 nam tuyet doi" —
  **phu thuoc vao BIG_DOWN/DCA**. Khong co chung, T170 truot 2022.
=> **Phan quyet goc "T170 THANG" chi dung khi tinh CA hai nguon.** Voi rieng phan `GATE_DYN_SCALE`
dieu khien, T170 tot hon ro nhung **khong du de tu minh PASS bo tieu chi cung.**

### Ranking co doi khong khi ca ba deu khong con BIG_DOWN?
**Khong doi ve chat luong/rui ro** (T170 > T130 > T100 ve win/TSloss/meanP/maxDD; T170 it vi pham nhat).
**Doi ve equity**: T100_NOBD (106,254) > T170_NOBD (90,247) > T130_NOBD (86,162) — nhung equity/CAGR
**khong phai tieu chi** theo luat du an.

## 7. GIOI HAN + VIEC NAY KHONG CHO PHEP LAM GI
- **Day la mot cua so DEV da nhin nhieu lan.** Ket qua tren KHONG phai bang chung out-of-sample.
  Xac nhan that chi co o **holdout 2026**.
- **KHONG** dung ket qua nay de tune `GATE_DYN_SCALE`, nguong BIG_DOWN, `NUMBER_ENTRY_EACH_SIGNAL`
  hay bat ky tham so nao. Day la thi nghiem **danh gia tinh hop le**, khong phai tim cau hinh moi.
- **KHONG** ket luan "phai bo/giu BIG_DOWN". Thi nghiem chi tra loi *T170 co tu dung duoc khong khi bo* —
  no **khong** noi rang bo BIG_DOWN la tot hay xau cho production (ca 3 ban NOBD deu te hon ban goc ve
  moi mat tru maxDD).
- Quyet dinh giu/doi incumbent thuoc ve **master va user**. Audit + thi nghiem nay chi cung cap so.
- KHONG deploy, KHONG 242, KHONG `git push`, holdout 2026 nguyen ven.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_011zpgT8SsGrmcqzxbC93PQT
