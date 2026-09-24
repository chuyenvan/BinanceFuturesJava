# RESULT — GATE-SCALE + CONC_CAP tren NEN PRODUCTION (FLATGRID KEEPLEG0)

Pre-reg: `docs/PREREG_GATESCALE_KEEPLEG0.md` (commit `a75c00a`, viet/chot TRUOC khi push kernel).
Runner: `research/analysis/kg0_run.py`; scorer: `research/analysis/kg0_score.py`.
Cua so **DEV 2021-07-01..2025-12-31** (KHONG cham 2026/holdout/242/shadow). Sim chay **Kaggle CPU
kernel** (`docs/KAGGLE_SIM.md`), **khong** chay Java/sim tren Oracle. Chi phi Kaggle **0**.
Ra soat lai luat: `docs/RISK_APPETITE.md` §6–§7 (maxDD<=40% · UW<=250 · qmin>=-20% · khong nam am ·
conc<=15% · nguong bang chung >=2 rate ngoai CI).

---

## 0. CONG PARITY — PASS CA HAI (dieu kien doc ket qua)

| cong | doi tuong | ket qua |
|---|---|---|
| **P1** | `x1_gs_t170` ⇒ `kaggle_sim/out/t170-x1-2021` md5 `printDone.csv` | `efb793e2468ca3a7318da0f0ad23d4fc` = **dung** ⇒ baseline cu (1,1,3,8) **khong bi dung toi** |
| **P2** | `t170_flat_keepleg0` khong override ⇒ `kg0-g170` | **1,085 leg / equity 103,083** = **dung**; md5 `99e42b75cf1a2142f9cd14dc72e371ba` = **BYTE-IDENTICAL** voi Oracle `java/devrun/FG_KEEPLEG0` (commit `e9e5965`) |

Nen Kaggle (bundle `sim-x1-2021-bundle`, `wfo_ds_x1_2021`) tai hien **tung byte** cau hinh
production dang chay ⇒ moi so duoi day do tren **dung nen that**, khong phai nen nghien cuu.
Jar ca 8 chan: `sha256 2c2f8aef78c98470fdc3b0d464edd7ec2c604a7589985b1f4211c1da05fcdca0`
(= jar mac dinh cua bundle, chinh la jar da tao ra `t170-x1-2021`).

Bien the dien dat bang **override tren `prof_x1_gs_t170`** (bundle la snapshot, chi co 3 profile;
`t170_flat_keepleg0` ≡ `x1_gs_t170` + dung 2 dong `DCA_GRID_WEIGHTS=1,1,1,1`/`DCA_GRID_SCALE=6.0`
— da chung minh bang `diff`). Moi chan giu `prof_run.properties` trong `out/<tag>/` lam bang chung.

---

## 1. NHOM (1) — CONC_CAP_PERCOIN 15% tren nen KEEPLEG0: **KHONG BIND (no-op tuyet doi)**

| chan | override them | `[CONC-PC]` MODE | SUMMARY | dong SKIP | n | md5 |
|---|---|---|---|---|---|---|
| `kg0-g170` (OFF) | — | khong bat | — | — | 1,085 | `99e42b75cf1a…` |
| `kg0-cap` (ON) | `CONC_CAP_PERCOIN_ENABLED=1`, `PCT=0.15` | `pct=0.15` | **`blocked=0`** | **0** | 1,085 | **`99e42b75cf1a…` (y het OFF)** |

⇒ **Guard BIND 0 lan** tren ca cau hinh production: **conc do duoc 7.12% << tran 15%**. Hai chan
**BYTE-IDENTICAL** ⇒ cap **khong mat mot dong PnL nao**, khong doi mot rate nao (CI vo nghia vi
hieu = 0.000 ca 5 rate). Doi chieu o diem nhieu lenh nhat (nhom 3, §7) cung **`blocked=0`**.

**Cach doc (bat buoc theo pre-reg §2.1):** ket qua chan CAP nay la **TAM THUONG (cap no-op)** —
no **khong** tao bang chung an toan nao trong mau nay. Noi dung cua no la: **bao hiem mien phi**
(0 chi phi do duoc) cho tinh huong *"15% chi la chua gap nhung van co the gap"* — trong mau
48+ thang khong co lan nao cham tran, ke ca khi mo gate den 1.00.

---

## 2. BANG CHINH — `n` va RUI RO theo gate-scale tren nen KEEPLEG0

`SIM_GATE_DYN_SCALE` (chi 1 num; moi key khac co dinh). `conc` = max `Σmargin(1 coin)/equity`
theo thoi gian (`gd92xexit_score.conc_max`).

| scale | n | equity | CAGR% | maxDD% | UW | qmin% | conc% | SumPnL | meanP/leg | hold_h | turn | SD ret%/nam |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1.70 (moc)** | 1,085 | 103,083 | 27.14 | −11.21 | 147 | −1.08 | **7.12** | 68,083 | 5.147 | 5.0 | 0.660 | 11.19 |
| 1.55 | 1,245 | 98,039 | 25.73 | −12.37 | 204 | −2.00 | 9.79 | 63,040 | 4.536 | 5.9 | 0.757 | 12.50 |
| 1.40 | 1,411 | 101,044 | 26.58 | −12.62 | 221 | −4.64 | 8.20 | 66,044 | 4.227 | 7.2 | 0.858 | 15.45 |
| 1.25 | 1,701 | 93,642 | 24.46 | −13.71 | 221 | −5.66 | 12.18 | 58,642 | 3.567 | 9.4 | 1.035 | 16.35 |
| 1.10 | 2,145 | **113,475** | **29.89** | −13.70 | 229 | −2.94 | 10.44 | 78,475 | 3.614 | 10.8 | 1.305 | 19.70 |
| **1.00** | **2,549** | **113,998** | **30.02** | −16.32 | **248** | −4.65 | 12.48 | 78,999 | 3.256 | 11.2 | 1.550 | **23.23** |
| 1.70 + CAP | 1,085 | 103,083 | 27.14 | −11.21 | 147 | −1.08 | 7.12 | 68,083 | 5.147 | 5.0 | 0.660 | 11.19 |
| 1.00 + CAP | 2,549 | 113,998 | 30.02 | −16.32 | 248 | −4.65 | 12.48 | 78,999 | 3.256 | 11.2 | 1.550 | 23.23 |

**Co che DUNG chieu (da kiem):** `n` **GIAM DON DIEU** khi scale tang
`1.00 → 2,549 > 1.10 → 2,145 > 1.25 → 1,701 > 1.40 → 1,411 > 1.55 → 1,245 > 1.70 → 1,085`
(scale nho ⇒ gate long hon ⇒ nhieu lenh hon). `n` tang **2.35x** tu moc len 1.00.

Chat luong lenh theo `n`: `win%` 88.20 → 84.31 · `TSloss%` 10.32 → 15.61 · `meanP` 5.147 → 3.256 ·
`hold` 5.0h → 11.2h · `turnover` 0.660 → 1.550 (lenh ngan hon va nhieu hon ⇒ chi phi/thoi gian
giu tang theo).

---

## 3. 5 RATE + CI vs MOC KEEPLEG0 (block-72h, 2000 rep, seed 20260905; **ngoai CA HAI do rong**)

Doi tuong so = **`kg0-g170`** (cau hinh production dang chay). "Ngoai CI" = ngoai o `x1.21`
legacy **VA** ngoai o `inflate(6)=1.893018` (thang 6 diem ⇒ k=6).

| chan | win% | TSloss% | mP\|SM | mP\|SL | meanP | TOT ngoai CI | **XAU ngoai CI** |
|---|---|---|---|---|---|---|---|
| `kg0-cap` | ±0.000 | ±0.000 | ±0.000 | ±0.000 | ±0.000 | 0/5 | 0/5 (byte-identical) |
| `kg0-g155` | −0.894 | +1.244 | −0.165 | −1.085 | −0.611 | 0/5 | 0/5 |
| `kg0-g140` | −1.810 | **+2.576** | −0.233 | −0.111 | −0.919 | 0/5 | **1/5 (TSloss%)** |
| `kg0-g125` | −2.900 | **+4.081** | −0.374 | −1.022 | −1.580 | 0/5 | **2/5 (TSloss%, meanP)** |
| `kg0-g110` | −3.168 | **+4.316** | −0.357 | −0.352 | −1.533 | 0/5 | **1/5 (TSloss%)** |
| `kg0-g100` | −3.895 | **+5.291** | −0.452 | −0.433 | −1.891 | 0/5 | **1/5 (TSloss%)** |

⇒ **KHONG chan nao E-PASS** (khong co >=2 rate ngoai CI huong TOT; `0/5 TOT` o moi chan). Cac
diem 1.40/1.25/1.10/1.00 co rate **XAU** ngoai CI (chinh la `TSloss%` tang: 10.32% → 15.61%).
(Khieu huong XAU ro nhat o 1.25: 2/5.) Doi chieu vs **T170** (phu, khong quyet dinh): 0 TOT; XAU
0/1/2/1/2 cho 1.55/1.40/1.25/1.10/1.00 — cung mot ket luan.

**Khong co bang chung (o nguong >=2 rate) rang tang `n` lam lenh TOT hon.** Chieu chat luong
KHONG TOT hon: win%/meanP giam, TSloss% tang — va o cac diem thap thi ro ra ngoai CI.

---

## 4. RAO CUNG — theo nam VA toan ky

**(R-MOI)** khau vi moi (`RISK_APPETITE` §6–§7): maxDD ≤ 40% · UW ≤ 250 · qmin ≥ −20% · khong nam
am · conc ≤ 15%. **(R-CU)**: maxDD ≤ 30% · UW ≤ 200 · qmin ≥ −15% · khong nam am · conc ≤ 15%.

`maxDD% / UW / ret% / qmin%` theo nam:

| scale | 2021 | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|
| 1.70 | −2.46/37/+12.21/+4.44 | −11.21/72/+12.59/−1.08 | −2.73/63/+34.96/−0.37 | −6.60/92/+32.13/−0.92 | −4.23/52/+30.81/+1.27 |
| 1.55 | −3.73/38/+7.95/+1.12 | −12.37/73/+12.90/−2.00 | −3.25/66/+33.50/−0.37 | −7.58/119/+36.24/−1.59 | −4.92/**204**/+26.44/+1.58 |
| 1.40 | −3.15/27/+10.09/+2.58 | −12.62/**145**/+6.61/−2.47 | −2.35/44/+42.70/+0.98 | −8.36/119/+32.51/−4.64 | −7.04/**221**/+30.17/+1.60 |
| 1.25 | −5.69/47/+9.27/+0.84 | −12.63/113/+8.37/−3.08 | −2.50/42/+47.19/+4.82 | −10.94/141/+30.39/−5.66 | **−13.71/221**/+17.79/+0.17 |
| 1.10 | −5.72/47/+9.84/+1.75 | −12.07/109/+10.17/−1.83 | −2.59/58/+55.30/+6.45 | −10.78/114/+39.80/−2.94 | −10.47/74/+23.49/+1.42 |
| **1.00** | −7.35/47/+9.28/−0.56 | −12.65/64/+15.61/+0.63 | −2.51/45/+60.43/+7.80 | **−11.36/121/+45.36/−4.65** | **−14.17/232/+10.62/−2.47** |

| scale | R-MOI | R-CU |
|---|---|---|
| 1.70 (moc) | **PASS** | PASS |
| 1.55 | **PASS** | FAIL (UW_ky 204; 2025 UW 204) |
| 1.40 | **PASS** | FAIL (UW_ky 221; 2025 UW 221) |
| 1.25 | **PASS** | FAIL (UW_ky 221; 2025 UW 221) |
| 1.10 | **PASS** | FAIL (UW_ky 229) |
| **1.00** | **PASS** | FAIL (UW_ky **248** vs cap 250; 2025 UW 232) |
| 1.70+CAP / 1.00+CAP | PASS | nhu OFF |

- **Ca 6 diem thang (1.00–1.70) PASS toan bo rao khau vi MOI** — sau khi user noi `UW` len 250,
  cac diem nhieu lenh **khong con bi chan boi UW**. Nhung **1.00 chi con cach tran 2 ngay**
  (248/250) va 2025 = 232 ⇒ bien an toan mong, de bi pha bo o ngoai mau.
- **Rao CU (UW ≤ 200)**: chi moc 1.70 qua ⇒ moi diem "nhieu lenh" deu FAIL neu giu nguong cu.
- Khong nam nao am o bat ky diem nao; `qmin` xau nhat −5.66% (1.25) van > −20%.

---

## 5. DO VENH THEO NAM (ret% nam) — rui ro "dao dong" XAU dan khi `n` tang

| scale | 1.70 | 1.55 | 1.40 | 1.25 | 1.10 | 1.00 |
|---|---|---|---|---|---|---|
| SD (pp) | **11.19** | 12.50 | 15.45 | 16.35 | 19.70 | **23.23** |
| range (pp) | 22.76 | 28.29 | 36.09 | 38.83 | 45.46 | **51.16** |
| min ret% | 12.21 | 7.95 | 6.61 | 8.37 | 9.84 | 9.28 |
| max ret% | 34.96 | 36.24 | 42.70 | 47.19 | 55.30 | 60.43 |

⇒ `SD` tang **gap 2.08x** tu moc len 1.00: "on dinh" theo nam **kem hon**, khong tot hon.

---

## 6. BANG PnL CHI TIET THEO NAM (moi chan)

### `kg0-g170` (moc, scale 1.70) — equity cuoi 103,083 · maxDD −11.21% · UW 147 · qmin −1.08 · conc 7.12
| nam | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
|2021|149|92.62|7.38|4.368|4,273|+12.21|−2.46|37|4.44|39,272|
|2022|196|82.65|14.29|2.242|4,943|+12.59|−11.21|72|−1.08|44,215|
|2023|126|88.10|15.87|8.074|15,376|+34.96|−2.73|63|−0.37|59,673|
|2024|281|90.04|10.68|4.769|19,210|+32.13|−6.60|92|−0.92|78,801|
|2025|333|87.99|6.91|6.416|24,282|+30.81|−4.23|52|1.27|103,083|

### `kg0-cap` (scale 1.70 + CONC_CAP 15%) — **y het tung dong bang tren** (md5 `99e42b75cf1a…` khop)

### `kg0-g155` (scale 1.55) — equity 98,039 · maxDD −12.37% · UW 204 · qmin −2.00 · conc 9.79
| nam | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
|2021|161|89.44|10.56|3.387|2,782|+7.95|−3.73|38|1.12|37,781|
|2022|211|82.94|14.22|2.309|4,875|+12.90|−12.37|73|−2.00|42,656|
|2023|152|86.84|16.45|6.596|14,212|+33.50|−3.25|66|−0.37|56,947|
|2024|341|90.03|10.56|4.747|20,667|+36.24|−7.58|119|−1.59|77,535|
|2025|380|86.58|9.47|5.246|20,505|+26.44|−4.92|204|1.58|98,039|

### `kg0-g140` (scale 1.40) — equity 101,044 · maxDD −12.62% · UW 221 · qmin −4.64 · conc 8.20
| nam | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
|2021|167|89.22|10.78|3.696|3,531|+10.09|−3.15|27|2.58|38,530|
|2022|233|80.69|18.03|1.555|2,546|+6.61|−12.62|145|−2.47|41,076|
|2023|178|88.76|14.61|6.985|17,459|+42.70|−2.35|44|0.98|58,615|
|2024|378|88.10|12.43|4.261|19,088|+32.51|−8.36|119|−4.64|77,623|
|2025|455|85.93|10.77|4.684|23,421|+30.17|−7.04|221|1.60|101,044|

### `kg0-g125` (scale 1.25) — equity 93,642 · maxDD −13.71% · UW 221 · qmin −5.66 · conc 12.18
| nam | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
|2021|219|85.39|14.61|3.120|3,246|+9.27|−5.69|47|0.84|38,246|
|2022|270|81.85|18.15|1.794|3,200|+8.37|−12.63|113|−3.08|41,446|
|2023|208|88.94|13.94|6.685|19,477|+47.19|−2.50|42|4.82|61,006|
|2024|434|86.41|14.52|3.824|18,576|+30.39|−10.94|141|−5.66|79,499|
|2025|570|84.74|12.63|3.245|14,143|+17.79|−13.71|221|0.17|93,642|

### `kg0-g110` (scale 1.10) — equity 113,475 · maxDD −13.70% · UW 229 · qmin −2.94 · conc 10.44
| nam | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
|2021|258|83.33|16.67|2.451|3,444|+9.84|−5.72|47|1.75|38,443|
|2022|324|80.86|18.21|2.554|3,909|+10.17|−12.07|109|−1.83|42,352|
|2023|270|88.89|13.70|6.020|23,331|+55.30|−2.59|58|6.45|65,772|
|2024|558|86.74|14.34|3.857|26,209|+39.80|−10.78|114|−2.94|91,892|
|2025|735|84.76|12.93|3.420|21,583|+23.49|−10.47|74|1.42|113,475|

### `kg0-g100` (scale 1.00 — diem `n` cao nhat) — equity 113,998 · maxDD −16.32% · UW 248 · qmin −4.65 · conc 12.48
| nam | n | win% | TSloss% | meanP | PnL(USDT) | ret% | maxDD% | UW | qmin% | equity |
|---|---|---|---|---|---|---|---|---|---|---|
|2021|293|81.57|18.43|2.122|3,248|+9.28|−7.35|47|−0.56|38,247|
|2022|399|82.21|17.29|2.791|5,971|+15.61|−12.65|64|0.63|44,218|
|2023|308|88.64|13.64|5.767|26,625|+60.43|−2.51|45|7.80|70,940|
|2024|668|86.23|14.52|3.902|32,210|+45.36|−11.36|121|−4.65|103,053|
|2025|881|83.20|15.44|2.475|10,945|+10.62|−14.17|232|−2.47|113,998|

### `kg0-cap-s100` (scale 1.00 + CONC_CAP 15%, nhom 3) — **y het tung dong bang tren** (md5 `fa0dc7eba644…` khop; `blocked=0`)

---

## 7. Σfunding / ΣPnL (do theo `n`) — chi phi funding NO LEN theo so lenh

| scale | 1.70 | 1.55 | 1.40 | 1.25 | 1.10 | 1.00 |
|---|---|---|---|---|---|---|
| n | 1,085 | 1,245 | 1,411 | 1,701 | 2,145 | 2,549 |
| Σfunding | −2,358.7 | −2,678.2 | −2,647.6 | −5,255.6 | −6,669.7 | **−9,613.5** |
| ΣPnL | 68,083 | 63,040 | 66,044 | 58,642 | 78,475 | 78,999 |
| **Σfunding/ΣPnL** | **−3.46%** | −4.25% | −4.01% | −8.96% | −8.50% | **−12.17%** |

⇒ Ty trong PnL bi funding an tang **3.5x** khi `n` tang 2.35x (funding ~ `n × eps`; doi chieu
`RESULT_FRAGILITY_N` §6.3: T170 −2.76% · T100 −10.73%).

---

## 8. drop-top-K (bo K leg TOT NHAT ⇒ ΔPnL%) — do "mong manh cua PnL"

| scale | top-1 leg | top-1% | top-5% |
|---|---|---|---|
| **1.70 (moc)** | −4.43% | **−23.74%** | **−55.33%** |
| 1.55 | −4.62% | −25.60% | −60.87% |
| 1.40 | −4.30% | −25.77% | −65.19% |
| 1.25 | −5.07% | −32.98% | −81.32% |
| 1.10 | −3.94% | −32.33% | −82.69% |
| **1.00 (best-n)** | −4.13% | **−40.57%** | **−100.80%** |

⇒ O scale 1.00, bo 5% leg tot nhat ⇒ **mat TOAN BO PnL** (−100.80%): toan bo loi nhuan den tu ~5%
leg tot nhat. Day la kenh rui ro **XAU DI ro ret** khi `n` tang (moc: −55.33%). Cung nghia: loi
nhuan khong den tu "chat luong trung binh" ma tu mot nhom nho leg thang lon.

---

## 9. TRA LOI 4 CAU HOI TRUNG TAM

**(a) Tren nen PRODUCTION, `n` tang theo gate-scale the nao?**
Don dieu nghich (dung co che): **1.70 → 1,085 · 1.55 → 1,245 · 1.40 → 1,411 · 1.25 → 1,701 ·
1.10 → 2,145 · 1.00 → 2,549**. Mo gate tu 1.70 xuong 1.00 ⇒ **n x2.35** (them 1,464 lenh).

**(b) Rui ro TOT hon hay XAU hon khi `n` tang?** ⇒ **XAU hon, dong thoi tren MOI truc rui ro do
duoc**: `maxDD` −11.21% → −16.32%; `UW` 147 → **248** ngay; `SD ret% nam` 11.19 → **23.23 pp**;
`conc` 7.12% → 12.48%; `qmin` −1.08% → −4.65%; `Σfunding/ΣPnL` −3.46% → −12.17%; do mong manh
`top-5%` −55.33% → **−100.80%**. Chieu chat luong lenh cung khong tot hon: `win%` 88.20 → 84.31,
`TSloss%` 10.32 → 15.61, `meanP` 5.147 → 3.256, va **co rate XAU NGOAI CI** o 1.40/1.25/1.10/1.00.
Ngoai le duy nhat co loi: `equity`/`CAGR` **khong don dieu** — 1.10 (113,475) va 1.00 (113,998)
cao hon moc (103,083), con 1.25 thap nhat (93,642). ⇒ **"nhieu lenh" KHONG lam giam rui ro; no lam
TANG rui ro dao dong/thoi gian duoi nuoc/funding, doi lai ky vong loi nhuan cao hon (khong on dinh).**

**(c) Muc scale cho `n` CAO NHAT ma PASS TOAN BO rao khau vi MOI (maxDD≤40 · UW≤250 · qmin≥−20 ·
khong nam am · conc≤15%)?** ⇒ **scale 1.00, n = 2,549** (`kg0-g100`; `kg0-cap-s100` tuong duong,
CAP no-op). **Ca 6 diem 1.00–1.70 deu PASS** rao MOI. NHUNG: (i) 1.00 chi cach tran UW **2 ngay**
(248/250) va 2025 = 232 ⇒ **bien an toan mong**; (ii) diem do **KHONG E-PASS** (0/5 rate ngoai CI
huong TOT, va co rate XAU ngoai CI) ⇒ theo luat day du (**PASS = R-MOI + E-PASS**) thi **KHONG co
muc nao PASS**; (iii) neu giu rao CU (UW ≤ 200) thi **chi moc 1.70** qua.

**(d) Khac gi so voi ket qua tren nen 1,1,3,8?**
- Vong quet gate-scale tren nen 1,1,3,8 (`docs/PREREG_GATESCALE_SWEEP.md`) **CHUA DOI CHIEU DUOC**:
  **khong co** `RESULT_GATESCALE_SWEEP.md`; 4 kernel `gs-t155/t140/t125/t110` duoc push 2026-09-24
  02:21Z nhung bundle **khong chua** `prof_x1_gs_t*.properties` ⇒ `sim-gs-t155` ket thuc **ERROR**
  (`MISSING /kaggle/input/**/prof_x1_gs_t155.properties`), 3 chan con lai khong co run. ⇒ Bat ky so
  nao tu vong do la **khong dung duoc** (khong phai "ket qua xau" ma la "chua chay duoc").
- Doi chieu duoc **bang 2 moc 1,1,3,8 da co san** tren cung cua so/bundle (md5 da kiem o P1 va
  `hn-t100` = `dc16e4da6ff6cb7b8d41c592bc3d9c45`): tai **cung gate-scale 1.00**, nen 1,1,3,8 (T100)
  cho `n=2,559 · equity 121,770 · maxDD −16.13 · UW 248 · qmin −4.64 · conc **27.23%** (FAIL tran 15%)`;
  nen KEEPLEG0 cho `n=2,549 · equity 113,998 · maxDD −16.32 · UW 248 · qmin −4.65 · conc **12.48%
  (PASS tran 15%)`**. ⇒ **Ket qua KHAC o cho quan trong nhat**: tren nen production (luoi phang
  scale 6.0), cung mot muc "nhieu lenh" (n ~ 2.55k, UW 248) **giu duoc tran tap trung 1 coin**
  (12.5% < 15%), trong khi tren nen 1,1,3,8 cung muc `n` **pha tran 15% (27.2%)**. Gia phai tra:
  equity thap hon **−6.4%** va maxDD sau hon mot chut.
- Tai gate 1.70 (moc): 1,1,3,8 (T170) `n=1,089 · eq 111,070 · UW 92 · conc 9.77%` vs KEEPLEG0
  `n=1,085 · eq 103,083 · UW 147 · conc 7.12%` (dung nhu `RESULT_FLATGRID`: mat ~7% equity, doi
  lay giam tap trung; UW dai hon la gia da biet).

---

## 10. Doi chieu voi du doan GHI TRUOC (pre-reg §4)

| du doan | thuc te | dung/sai |
|---|---|---|
| `n` tang theo chieu giam scale | don dieu, 1,085 → 2,549 | **DUNG** |
| `maxDD`/`UW` XAU dan khi `n` tang | maxDD −11.21 → −16.32; UW 147 → 248 | **DUNG** |
| `conc` khong tang manh (da rat phang) | 7.12 → 12.48 (van <= 15) | **DUNG** |
| **(1) CAP gan nhu KHONG bind** (`blocked` nho/0 ⇒ ket qua tam thuong) | `blocked=0` ca hai diem; byte-identical | **DUNG** |
| **(c) "khong co"** (diem nhieu lenh nhat FAIL UW >= 250 hoac maxDD) | **SAI**: 1.00 PASS R-MOI (UW 248) — nhung chi cach tran 2 ngay va van khop ly do bien mong | **SAI (bat ngo)** |

---

## 11. VERDICT + KY LUAT

| cau hoi | ket qua |
|---|---|
| (1) CONC_CAP 15% tren KEEPLEG0 | **no-op tuyet doi** (`blocked=0`, byte-identical) ⇒ khong mat gi, khong chung minh gi; la bao hiem mien phi |
| (2) thang gate-scale 1.70→1.00 | `n` x2.35; **rui ro XAU dan tren moi truc**; 0/5 E-PASS; 1.00 PASS rao MOI nhung UW sat tran (248/250) |
| (3) KEEPLEG0 + CAP + scale tot nhat (1.00) | **cung no-op** (`blocked=0`, byte-identical voi `kg0-g100`) |
| **PASS day du (R-MOI + E-PASS)** | **KHONG co muc nao** ⇒ theo luat §4 la **NULL ve bang chung**; (c) tra loi theo **rao rui ro**: **1.00 (n=2,549)** |

- **UNG VIEN (khong tu tich hop san xuat):** neu owner uu tien "nhieu lenh" va chap nhan khau vi
  moi, **scale 1.00 (hoac 1.10 — equity cao nhat 113,475, SD 19.70, UW 229, conc 10.44, cach tran
  xa hon)** la ung vien **can forward**; day **khong phai** ket qua co bang chung thong ke (0/5 E-PASS)
  va **1.00 rat sat tran UW 250**.
- `CONC_CAP_PERCOIN=15%` **khong** lam thay doi bat ky so nao tren nen nay ⇒ neu bat lam mac dinh thi
  do la quyet dinh **bao hiem** (chi phi do duoc = 0 trong mau), **khong** phai cai thien do duoc.
- Khong doi incumbent, khong doi `profiles/`, khong tu bat guard, khong push, khong cham 2026/242/shadow.
