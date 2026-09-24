# RESULT — GATE-SCALE SWEEP: tang so lenh sach (1 num) va do RUI RO theo n

Pre-reg: `docs/PREREG_GATESCALE_SWEEP.md` — commit `bc6082b`, amend `31f4baa` (duong override)
va `4835854` (them chuan S3), **ca ba deu TRUOC khi co bat ky ket qua sim nao**. Code+tag:
commit `a450046`. Chay **2026-09-24**, branch `module`. Sim **tren Kaggle** (`docs/KAGGLE_SIM.md`),
**KHONG** chay Java/sim tren Oracle. Cua so DEV `2021-07-01..2025-12-31` (khong cham 2026).

## 0. KET LUAN (doc cai nay truoc)

**NULL — khong muc scale nao ngoai moc 1.70 dat (S1)**. Tra loi (b) theo dung luat da chot:
**"khong co"**.

Va cau tra loi cho cau hoi cua owner (*"tang nhieu lenh thi toi nghi no GIAM RUI RO"*) la **NGUOC
LAI, co so do duoc**: khi n tang, **moi thu do rui ro deu XAU di don dieu** —

| do | 1.70 (n=1089) | 1.00 (n=2559) | chieu |
|---|---|---|---|
| SD `ret%` theo nam | **9.92pp** | **22.00pp** | XAU 2.22x |
| range `ret%` nam | 22.76pp | 51.15pp | XAU 2.25x |
| UW toan ky (ngay) | **92** | **248** | XAU 2.70x |
| tap trung 1 coin | **9.77%** | **27.23%** | XAU 2.79x |
| `meanP`/leg | 5.244 | 3.173 | GIAM 39% |
| TSloss% | 9.73 | 15.36 | XAU |
| 5 rate ngoai CI vs T170 | — (moc) | 0 TOT / **3 XAU** | khong bao gio TOT |

**Khong co mot diem nao duoi 1.70 co DU 1 rate ngoai CI theo huong TOT** (0/5 o moi diem), trong khi
co 1-3 rate XAU ngoai CI (ngoai o x1.21). Tuc: **tang lenh KHONG mua duoc chat luong, va lam XAU
rui ro** (do venh nam, UW, tap trung) — **tra loi (c) = "tang lenh KHONG giam rui ro trong du lieu
nay"**.

Ngoai le duy nhat dang chu y: **`maxDD` KHONG xau di dang ke** (moi diem −11.84 .. −19.11%, **duoi
ca tran CU 30%**) — dung y `RISK_APPETITE.md` §6 da ghi truoc: maxDD khong phai rang buoc dang chan.
Rang buoc chan **that su** la **UW** va **tap trung 1 coin**, va ca hai **XAU di khi n tang**.

---

## 1. Cong parity + co che + bang theo scale

**CONG PARITY (BAT BUOC) — PASS:**

```
efb793e2468ca3a7318da0f0ad23d4fc  kaggle_sim/out/t170-x1-2021/storage/printDone.csv   (want efb793e2...) OK
dc16e4da6ff6cb7b8d41c592bc3d9c45  kaggle_sim/out/hn-t100/storage/printDone.csv      (want dc16e4da4...) OK
```

**Co che DUNG:** n **don dieu giam** theo scale — `1.00:2559 · 1.10:2156 · 1.25:1708 · 1.40:1416 ·
1.55:1249 · 1.70:1089`. Moi run dung **cung 1 jar** (`sha256 2c2f8aef78c98470…`, = jar trong bundle),
`symbol_mapper=863` (≥ 800), `profile=x1_c3_full` + **DUNG 1 override** `SIM_GATE_DYN_SCALE`.
Kiem chung **hieu luc profile** (parse key=value, bo comment): `prof_run.properties` cua 4 chan moi
khop `profiles/x1_gs_t1*.properties` **20/20 key**, khac DUY NHAT `WFO_FUNDING_PRED_DIR` (bi tro vao
mount Kaggle — dung nhu thiet ke) va dinh dang float (`1.4` vs `1.40`).

| scale | tag | n | meanP/leg | win% | TSloss% | hold med (h) | turn/day | equity | CAGR% | maxDD% | UW | qmin% | conc% | SumPnL |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1.70** (moc) | `t170-x1-2021` | 1089 | 5.244 | 88.25 | 9.73 | 4.8 | 0.662 | 111070 | 29.27 | −11.84 | **92** | −0.92 | **9.77** | 76070 |
| 1.55 | `gs2-t155` | 1249 | 4.672 | 87.35 | 10.81 | 5.8 | 0.760 | 111881 | 29.48 | −12.97 | 204 | −1.59 | 16.46 | 76881 |
| 1.40 | `gs2-t140` | 1416 | 4.356 | 86.44 | 12.22 | 7.0 | 0.861 | **117002** | 30.77 | −13.22 | 221 | −4.64 | **14.57** | 82002 |
| 1.25 | `gs2-t125` | 1708 | 3.597 | 85.36 | 13.99 | 9.3 | 1.039 | **95460** | **24.99** | **−19.11** | 221 | −5.66 | **40.43** | 60461 |
| 1.10 | `gs2-t110` | 2156 | 3.642 | 85.20 | 14.19 | 10.5 | 1.311 | **126128** | **32.97** | −13.49 | 229 | −2.94 | 29.79 | 91129 |
| **1.00** (=T100) | `hn-t100` | 2559 | 3.173 | 84.33 | 15.36 | 11.1 | 1.557 | 121770 | 31.94 | −16.13 | **248** | −4.64 | 27.23 | 86770 |

Doc them: `meanP` **don dieu giam** theo n; TSloss% **don dieu tang**; win% **don dieu giam**;
hold med tang 4.8h → 11.1h; turnover tang 0.66 → 1.56 lenh/ngay.
**Luu y ve hinh dang khong don dieu cua equity/CAGR:** 1.10 la diem TOT NHAT (126128 / 32.97%) con
**1.25 la diem XAU NHAT (95460 / 24.99%, maxDD −19.11%, conc 40.43%)** — tuc duong equity theo scale
khong don dieu (1.25 la mot `dip`), nen "tang lenh" khong keo theo mot xu huong loi nhuan ro rang.

---

## 2. 5 rate + CI block-72h **x1.21** (2000 rep, seed 20260905) so T170

`NGOAI CI` = ngoai o **x1.21** (nhu pre-reg §5.2). Do rong chuan hoa `inflate(k=5)=1.7941` bao kem
(o cot "phu", KHONG quyet dinh).

| scale | rate ngoai CI x1.21 | huong | chi tiet (hieu [lo,hi] @1.21) | [@1.7941] |
|---|---|---|---|---|
| 1.55 | 1/5 | **XAU** | meanP −0.572 [−1.172,−0.044] | 0 XAU |
| 1.40 | 3/5 | **XAU** | win% −1.805 [−3.573,−0.292] · TSloss% +2.484 [0.909,4.252] · meanP −0.888 [−1.686,−0.225] | 1 XAU |
| 1.25 | 3/5 | **XAU** | win% −2.883 [−5.437,−0.630] · TSloss% +4.259 [2.022,6.590] · meanP −1.646 [−2.614,−0.726] | 2 XAU |
| 1.10 | 3/5 | **XAU** | win% −3.042 [−5.776,−0.693] · TSloss% +4.459 [2.116,6.848] · meanP −1.602 [−2.619,−0.695] | 2 XAU |
| 1.00 | 3/5 | **XAU** | win% −3.916 [−6.737,−1.378] · TSloss% +5.624 [3.029,8.204] · meanP −2.071 [−3.156,−1.036] | 3 XAU |

**0/5 rate TOT ngoai CI o MOI diem** (moc 1.55, 1.40, 1.25, 1.10, 1.00); `mP|SM` va `mP|SL` khong bao
gio ngoai CI. `TSloss%` xau hon co y nghia o **moi** diem ≤ 1.40. `meanP` giam co y nghia o **moi**
diem < 1.70. ⇒ **khong diem nao dat E-PASS** (>=2 TOT, 0 XAU).

---

## 3. Rao cung — BAO CAO CA BA CHUAN (theo nam LAN toan ky)

```
S1 = maxDD<=30%/nam | UW<=200 | quy>=-15% | ko nam am | conc<=15%   (nguong QUYET DINH theo task/pre-reg)
S2 = maxDD<=40%/nam | UW<=200 | quy>=-15% | ko nam am | conc<=15%
S3 = maxDD<=40%/nam | UW<=250 | quy>=-20% | ko nam am | conc<=15%   (= RISK_APPETITE §7 HIEN HANH, sau 0c2a8a5)
```

| scale | n | S1 | S2 | S3 | ly do FAIL |
|---|---|---|---|---|---|
| **1.70** | 1089 | **PASS** | **PASS** | **PASS** | — |
| 1.55 | 1249 | FAIL | FAIL | FAIL | UW toan ky 204 (>200) · conc 16.46 (>15) · 2025 UW 204 |
| 1.40 | 1416 | FAIL | FAIL | **PASS** | UW toan ky 221 · 2025 UW 221 |
| 1.25 | 1708 | FAIL | FAIL | FAIL | UW 221 · **conc 40.43** · 2025 UW 221 |
| 1.10 | 2156 | FAIL | FAIL | FAIL | UW 229 · conc 29.79 |
| 1.00 | 2559 | FAIL | FAIL | FAIL | UW 248 · conc 27.23 · 2025 UW 227 |

**Diem quan trong:** (i) **S1 va S2 cho KET QUA Y HET NHAU** o ca 6 diem — chung minh bang so rang
**maxDD khong phai rang buoc dang chan** (maxDD xau nhat = −19.11% o 1.25, van duoi ca tran 30%).
(ii) Rang buoc chan la **UW** (92 → 248) va **tap trung 1 coin** (9.77% → 40.43%). (iii) Ngay ca
khi noi maxDD len 40% (S2) **khong mo khoa duoc mot diem nao**. (iv) Duoi **S3** (rao hien hanh
UW<=250/quy>=-20%) chi **1.40** qua duoc rao cung — nhung 1.40 **khong dat bang chung** (0 TOT,
3 XAU ngoai CI) nen **khong phai PASS day du**.

`khong nam am`: **ca 6 diem deu PASS** (moi nam duong: 2021 +7.95..12.21, 2022 +14.25..20.25,
2023 +33.50..60.43, 2024 +30.39..45.36, 2025 +12.39..40.65). `qmin` te nhat = **−5.66%** (1.25) —
van cao hon nhieu so voi nguong −15%/−20%.

---

## 4. maxDD · UW (output TRUNG TAM) — theo nam

Moi o = `maxDD% / UW / ret% / qmin%`:

| scale | 2021 | 2022 | 2023 | 2024 | 2025 | toan ky maxDD / UW |
|---|---|---|---|---|---|---|
| 1.70 | −2.46/37/+12.21/+4.44 | −11.84/72/+19.58/+2.90 | −2.73/63/+34.96/−0.37 | −6.60/92/+32.14/−0.92 | −4.23/52/+32.71/+1.27 | **−11.84 / 92** |
| 1.55 | −3.73/38/+7.95/+1.12 | −12.97/73/+20.25/+2.34 | −3.25/66/+33.50/−0.37 | −7.57/119/+36.24/−1.59 | **−4.91/204**/+35.48/+1.58 | −12.97 / **204** |
| 1.40 | −3.15/27/+10.09/+2.58 | −13.22/137/+14.25/−0.03 | −2.35/44/+42.70/+0.98 | −8.36/119/+32.51/−4.64 | **−7.04/221**/+40.65/+1.60 | −13.22 / **221** |
| 1.25 | −5.69/47/+9.27/+0.84 | −13.03/109/+15.78/+1.34 | −2.50/42/+47.20/+4.82 | −10.94/141/+30.39/−5.66 | **−19.11/221**/+12.39/−4.42 | **−19.11** / 221 |
| 1.10 | −5.72/47/+9.84/+1.75 | −12.48/109/+16.64/+1.00 | −2.59/58/+55.30/+6.45 | −10.77/114/+39.80/−2.94 | −7.36/74/+29.64/+1.42 | −13.49 / **229** |
| 1.00 | −7.35/47/+9.28/−0.56 | −12.46/64/+17.31/+0.63 | −2.51/45/+60.43/+7.80 | −11.36/121/+45.36/−4.64 | **−10.60/227**/+16.45/−2.47 | −16.13 / **248** |

- **`maxDD` toan ky** xau nhat theo n: −11.84 (1.70) → −12.97 → −13.22 → −19.11 (1.25) → −13.49 →
  −16.13 (1.00). Khong don dieu, muc xau nhat o **1.25**; **moi diem van ≤ 19.11% ⇒ duoi tran 30%**.
- **UW nam 2025** la cho vo: 52 (1.70) → **204** (1.55) → 221 → 221 → 74 (1.10) → 227 (1.00).
  Tu 1.55 tro di **2025 FAIL UW<=200**, rieng 1.10 la 74 (pass nam) nhung **toan ky 229** van fail.
- **UW toan ky**: 92 → 204 → 221 → 221 → 229 → 248, gan nhu don dieu tang theo n (chi 1.25 va 1.40
  bang nhau). ⇒ **1.55 la diem dau tien da vo UW** (204 > 200): chi can giam scale tu 1.70 xuong 1.55
  (n 1089 → 1249, +14.7%) la da pha rao UW.
- **tuong quan n <-> UW rat manh**: n tang 2.35x (1089→2559) thi UW tang 2.70x (92→248).

---

## 5. Do venh theo nam + relative SE (scaling 1/sqrt(n))

| scale | SD `ret%` nam (pp) | range (pp) | min | max | SE(meanP) | relSE = SE/mean | relSE·sqrt(n) | relSE / (relSE_T170·sqrt(n₁₇₀/n)) |
|---|---|---|---|---|---|---|---|---|
| 1.70 | **9.92** | 22.76 | +12.21 | +34.96 | 0.649 | **0.1238** | 4.084 | 1.000 |
| 1.55 | 12.32 | 28.29 | +7.95 | +36.24 | 0.650 | 0.1392 | 4.920 | 1.205 |
| 1.40 | 15.05 | 32.62 | +10.09 | +42.70 | 0.638 | 0.1465 | 5.512 | 1.350 |
| 1.25 | 15.76 | 37.92 | +9.27 | +47.20 | 0.651 | 0.1808 | 7.474 | 1.830 |
| 1.10 | 18.17 | 45.46 | +9.84 | +55.30 | 0.596 | 0.1637 | 7.602 | 1.861 |
| 1.00 | **22.00** | 51.15 | +9.28 | +60.43 | 0.556 | **0.1752** | 8.862 | **2.170** |

- **Do venh nam XAU DON DIEU theo n**: SD 9.92 → 22.00pp (2.22x), range 22.76 → 51.15pp (2.25x).
  Khong co dau hieu "nhieu lenh => chia deu rui ro".
- **relSE KHONG giam theo `1/sqrt(n)`** — no **TANG** (0.1238 → 0.1752). `relSE*sqrt(n)` tu 4.08 len
  8.86 (khong phai hang so). So voi du doan `relSE_T170*sqrt(n_T170/n)`, thuc te / du doan di tu
  **1.00 → 2.17**: tuc o T100, **sai so tuong doi cua meanP/leg lon gap 2.17 lan** muc ma `1/sqrt(n)`
  du doan. Y nghia: **SE(meanP) gan nhu KHONG DOI** (0.649 → 0.556, chi −14%) trong khi n tang 2.35x
  ⇒ lenh moi **khong doc lap** (cum theo thoi diem/coin), nen **khong mua duoc do chinh xac**.
  Day la giai thich co hoc cho viec "0 rate TOT ngoai CI o moi diem".

---

## 6. Bang PnL chi tiet theo nam (n · PnL · ret% · maxDD% · UW · qmin% · equity)

**1.70 (moc)** — equity 111070 | toan ky maxDD −11.84 · UW 92 · qmin −0.92 · conc 9.77 · SumPnL 76070
```
nam     n  win% TSloss%   meanP   PnL(USDT)      ret%   maxDD%   UW   qmin%      equity
2021  149 92.62    7.38   4.368        4273    +12.21    -2.46   37    4.44       39272
2022  198 83.84   11.11   3.861        7688    +19.58   -11.84   72    2.90       46960
2023  126 88.10   15.87   8.074       16331    +34.96    -2.73   63   -0.37       63378
2024  281 90.04   10.68   4.769       20403    +32.14    -6.60   92   -0.92       83695
2025  335 87.46    6.87   5.784       27375    +32.71    -4.23   52    1.27      111070
```
**1.55** — equity 111881 | toan ky maxDD −12.97 · UW 204 · qmin −1.59 · conc 16.46 · SumPnL 76881
```
2021  161 89.44   10.56   3.387        2782     +7.95    -3.73   38    1.12       37781
2022  214 84.11   11.21   3.554        7652    +20.25   -12.97   73    2.34       45433
2023  152 86.84   16.45   6.596       15137    +33.50    -3.25   66   -0.37       60654
2024  341 90.03   10.56   4.747       22013    +36.24    -7.57  119   -1.59       82584
2025  381 86.09    8.66   5.008       29297    +35.48    -4.91  204    1.58      111881
```
**1.40** — equity 117002 | toan ky maxDD −13.22 · UW 221 · qmin −4.64 · conc 14.57 · SumPnL 82002
```
2021  167 89.22   10.78   3.696        3531    +10.09    -3.15   27    2.58       38530
2022  237 81.86   15.19   2.708        5489    +14.25   -13.22  137   -0.03       44019
2023  178 88.76   14.61   6.985       18711    +42.70    -2.35   44    0.98       62816
2024  378 88.10   12.43   4.261       20456    +32.51    -8.36  119   -4.64       83187
2025  456 85.53   10.09   4.505       33815    +40.65    -7.04  221    1.60      117002
```
**1.25** — equity 95460 | toan ky maxDD −19.11 · UW 221 · qmin −5.66 · **conc 40.43** · SumPnL 60461
```
2021  219 85.39   14.61   3.120        3246     +9.27    -5.69   47    0.84       38246
2022  275 82.91   15.64   2.837        6036    +15.78   -13.03  109    1.34       44282
2023  208 88.94   13.94   6.685       20811    +47.20    -2.50   42    4.82       65182
2024  434 86.41   14.52   3.824       19847    +30.39   -10.94  141   -5.66       84940
2025  572 84.44   12.59   2.851       10520    +12.39   -19.11  221   -4.42       95460
```
**1.10** — equity 126128 | toan ky maxDD −13.49 · UW 229 · qmin −2.94 · conc 29.79 · SumPnL 91129
```
2021  258 83.33   16.67   2.451        3444     +9.84    -5.72   47    1.75       38443
2022  333 81.68   16.82   2.729        6397    +16.64   -12.48  109    1.00       44840
2023  270 88.89   13.70   6.020       24701    +55.30    -2.59   58    6.45       69636
2024  558 86.74   14.34   3.857       27749    +39.80   -10.77  114   -2.94       97291
2025  737 84.94   12.21   3.437       28838    +29.64    -7.36   74    1.42      126128
```
**1.00 (T100)** — equity 121770 | toan ky maxDD −16.13 · UW 248 · qmin −4.64 · conc 27.23 · SumPnL 86770
```
2021  293 81.57   18.43   2.122        3248     +9.28    -7.35   47   -0.56       38247
2022  406 82.27   17.00   2.200        6619    +17.31   -12.46   64    0.63       44866
2023  308 88.64   13.64   5.767       27014    +60.43    -2.51   45    7.80       71978
2024  668 86.23   14.52   3.902       32687    +45.36   -11.36  121   -4.64      104567
2025  884 83.26   14.82   2.512       17202    +16.45   -10.60  227   -2.47      121770
```

---

## 7. KET LUAN (a)(b)(c)

**(a) Khi n tang thi rui ro TOT hon hay XAU hon? → XAU HON, va co "duong cong rui ro theo n" nhung
no DI LEN, khong di xuong.**

- **Do venh nam**: SD `ret%` 9.92 → 22.00pp, range 22.76 → 51.15pp — **don dieu XAU** theo n.
- **UW**: 92 → 248 ngay — **XAU** (2.70x); nam 2025 la cho vo (52 → 204 → 227).
- **Tap trung 1 coin**: 9.77% → 27.23% (va **40.43%** o 1.25) — **XAU**; tran 15% bi vuot tu 1.55 tro di.
- **`maxDD` toan ky**: −11.84 → −19.11 → −16.13 — khong don dieu, **nhung khong bao gio cham tran 30%**;
  ⇒ **maxDD la thu DUY NHAT khong xau di** khi tang lenh (dung nhu §6 RISK_APPETITE da ghi).
- **Chat luong lenh**: `meanP` giam 39%, `TSloss%` tang 9.73 → 15.36, win% giam 88.25 → 84.33;
  **0/5 rate TOT ngoai CI o MOI diem**, va 1-3 rate XAU ngoai CI.
- **Do chinh xac khong tang**: `relSE` **tang** (0.1238 → 0.1752) va `relSE*sqrt(n)` **tang** (4.08 → 8.86)
  ⇒ khong theo luat `1/sqrt(n)`; lenh moi **khong doc lap** ⇒ cang them lenh cang khong thu hep duoc
  bat dinh tuong doi.
- Hinh dang cu the: **1.25 la diem XAU NHAT** (maxDD −19.11, conc 40.43, ret 2025 +12.39) va
  **1.10 la diem TOT NHAT** ve equity/CAGR (126128 / 32.97%) — nhung **1.10 van FAIL rao (UW 229,
  conc 29.79)**. ⇒ **khong co diem nao vua "nhieu lenh" vua "an toan".**

**(b) Muc scale nao cho n CAO NHAT ma PASS (S1)? va PASS (S2)?**

- **(S1)** (maxDD≤30% · UW≤200 · quy≥−15% · khong nam am · conc≤15%): **khong co**. Chi **moc 1.70**
  (n=1089) PASS; moi diem ngoai moc **FAIL** — diem dau tien da vo la **1.55** (n=1249, UW 204, conc 16.46).
- **(S2)** (noi maxDD len 40%, giu nguyen phan con lai): **khong co** — ket qua **y het S1** (maxDD
  khong phai rang buoc dang chan o bat ky diem nao).
- **(S3)** (rao HIEN HANH §7: maxDD≤40 · UW≤250 · quy≥−20% · conc≤15%): rao cung **chi mo** duoc
  **1.40** (n=1416: UW 221 ≤ 250, qmin −4.64 ≥ −20%, conc 14.57 ≤ 15) — nhung 1.40 **khong dat
  bang chung** (0/5 TOT, 3/5 XAU ngoai CI x1.21) ⇒ **khong co PASS day du (S3)**, 1.40 chi la
  **ung vien di tiep ve rao**, khong phai bang chung tot hon. Cac diem khac vo o **conc** (1.55 16.46 ·
  1.25 40.43 · 1.10 29.79 · 1.00 27.23).
- Theo dung luat da chot: **khong muc nao ngoai moc PASS (S1)** ⇒ **NULL + tra loi (b) = "khong co"**.

**(c) "Tang lenh KHONG giam rui ro trong du lieu nay" — dung, kem so:**

> Tang n tu 1,089 (scale 1.70) len 2,559 (scale 1.00) = **+135% so lenh** (2.35x) thi:
> **UW 92 → 248 ngay (+170%)**, **tap trung 1 coin 9.77% → 27.23% (+179%, dinh 40.43%)**,
> **SD `ret%` nam 9.92 → 22.00pp (+122%)**, **range nam 22.76 → 51.15pp (+125%)**,
> **`meanP`/leg 5.244 → 3.173 (−39%)**, **`TSloss%` 9.73 → 15.36**,
> va **0/5 rate chat luong ngoai CI theo huong TOT o moi diem** (nguoc lai 1-3 rate XAU ngoai CI).
> Thu duy nhat KHONG xau di: **`maxDD`** (−11.84 → −16.13%, van duoi tran 30%).
> Va do chinh xac khong tang: **`relSE` 0.1238 → 0.1752** (du doan `1/sqrt(n)` la 0.0807) —
> sai so tuong doi **gap 2.17 lan** muc `1/sqrt(n)` bao.

---

## 8. Chi phi / thoi gian Kaggle + bai hoc van hanh

| | |
|---|---|
| Kernel | 4 chan `chuyendinh/sim-gs2-t155/t140/t125/t110` (bundle `sim-x1-2021-bundle`, `-Xmx22g`) |
| JVM sim (s) | t155 **1106.1** · t140 **1205.0** · t125 **1155.4** · t110 **1172.5** |
| Wall (push→COMPLETE) | t155 ~03:21→03:40 · t140 03:41→04:03 · t125 04:11→04:31 · t110 04:23→04:44 |
| Tong thoi gian vong (sau commit pre-reg → fetch xong) | ~2h30m |
| **Chi phi Kaggle** | **0** (CPU kernel khong tinh quota) · slot: toi da **2 kernel cua ta song song** (job OFI v3 cua task khac chiem 5/5 slot phan lon thoi gian) |
| Chan bo | 1 kernel chet `sim-gs-t155` (ERROR) + 3 tag 404 — xem bai hoc duoi |

**Bai hoc van hanh (moi, ghi lai):**
1. **Push kernel khi account dang o tran 5 slot => kernel CHET ma khong bao loi.** `kaggle_sim.submit()`
   khong raise: no ra `404` (kernel khong duoc tao) hoac tao kernel roi `ERROR` ngay khi start, va
   **push LAI vao chinh tag do KHONG tao version moi** (`lastRunTime` dung yen — da kiem: tag
   `gs-t155` push lai 2 lan, `lastRunTime` van `02:21:28`). **Cach chua: doi TAG MOI** (`gs2-*`:
   push xong `RUNNING` sau 45s). ⇒ Truoc khi push phai **kiem slot ranh that su** (`ks.free_slots()`).
2. **Bundle la snapshot**: `sim-x1-2021-bundle` chi chua 3 profile (`prof_x1_c3_full`,
   `prof_x1_gs_t170`, `prof_x1_c3_full_regime_brc`) ⇒ chan dung profile MOI lam kernel exit
   `MISSING /kaggle/input/**/prof_<ten>.properties`. Duong dung la **override** (xem pre-reg §4b).
   (Khi liet ke file dataset **phai phan trang `nextPageToken`** — page 1 chi co 20/28 file.)
3. **Kaggle API rat de 429** khi poll nhieu (`kernels_status` tung kernel). Neu bi 429 thi phai lui
   va **khong duoc poll day**; `Retry-After: 30`.

---

## 9. Canh bao / gioi han — DOC TRUOC KHI DUNG

1. **NEN CU.** Vong nay do tren **nen `x1_c3_full`/`x1_gs_t170` (DCA_GRID_WEIGHTS `1,1,3,8`,
   DCA_GRID_SCALE 19.5)** — 2 cong parity `efb793e2`/`dc16e4da` khoa thang chot vao nen nay. Commit
   `0c2a8a5` (2026-09-24, chay song song) **da doi BASELINE nghien cuu sang `FLATGRID KEEPLEG0`**
   (DCA `1,1,1,1` + scale 6.0, parity `99e42b75`, 1085 leg — xem `docs/DECISION_BASELINE_KEEPLEG0.md`).
   ⇒ **Ket qua nay KHONG tu dong chuyen sang baseline MOI**; muon ket luan cho KEEPLEG0 phai chay
   vong moi voi pre-reg moi (dung nhu canh bao trong commit `0c2a8a5`).
2. **Day la phep DO CO CHE + DO RUI RO, khong phai de xuat san xuat.** Ket qua **NULL**: khong de
   xuat doi `SIM_GATE_DYN_SCALE` khoi `1.70`; giu gate hien tai.
3. **`maxDD` khong phai rang buoc dang chan** — S1 va S2 cho ket qua y het nhau; neu chi nhin maxDD
   se ket luan sai la "moi diem deu an toan".
4. **Tap trung 1 coin la diem vo THAT SU** — o n lon co dinh **40.43%** (1.25) va 29.79% (1.10),
   **vuot tran 15%** va **vuot ca muc 28.51% da ghi nhan truoc day** o T100 (`RESULT_FRAGILITY_N`).
5. **Khong chay 2026/holdout**; **khong push**; **khong tu tich hop**; khong doi thang chot/nguong
   sau khi thay so.
6. Sinh lai toan bo so: `python3 research/analysis/gatescale_score.py --json research/analysis/gatescale_sweep_score.json`
   (doc truc tiep `kaggle_sim/out/{t170-x1-2021,gs2-t155,gs2-t140,gs2-t125,gs2-t110,hn-t100}`).
