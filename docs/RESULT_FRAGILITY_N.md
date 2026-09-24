# RESULT_FRAGILITY_N — do do venh theo n + kiem gia thuyet 1x

Thuc thi `docs/PREREG_FRAGILITY_N.md` (commit `d7cf467`). **KHONG chay sim moi** — thuan Python
offline tren artifact da co (`research/analysis/fragility_n.py`, ket qua trung gian
`/home/ubuntu/fragility/`). DEV 2021-07-01..2025-12-30, khong doc 2026. Khong push.

## 0. KET LUAN NGAY (verdict)

1. **VIEC A — 1x: XAC NHAN.** `margin/(quantity*entry) = 1.0000` tren **1089/1089 · 2559/2559 ·
   2632/2632** leg. Exposure cuc dai = **54.7% / 57.1% / 57.5% equity** ⇒ **khong moc nao** exposure
   > equity ⇒ **khong the chay tk**. ⇒ Menh de owner *"chi la so lo TAM THOI"* **DUNG ve mat
   ky quy/liquidation**.
2. **Nhung "MAT THAT" co that, chi la khong den tu 1x:** kenh duy nhat la **tap trung 1 coin**
   (T100 **28.51% equity** — VUOT tran 15% cua `RISK_APPETITE.md`, GD92 14.38%, T170 9.77%) va
   **ngay su kien thi truong** (2022-05-12 LUNA: T100 −12.06%, GD92 −13.55% equity trong **1 ngay**
   realized). 1x **khong** bao ve hai kenh nay.
3. **VIEC B — luan diem owner DUNG MOT NUA:**
   - **DUNG** o tang "bien do mot vai lenh": voi **so leg CO DINH**, anh huong ti le = `k/n`
     ⇒ nen nhieu lenh **nhay it hon 2.35–2.42 lan** (dung bang ty le n). T100/GD92 nhiem it hon
     khi backtest-vs-live lech **ngau nhien**.
   - **SAI** o tang "ket qua bot venh theo n": **do tap trung PnL TANG theo n**, khong giam.
     `share top-1% leg` = **25.9% (T170) → 40.9% (T100) → 37.8% (GD92)**; bo top-1% best lam
     `ΔTongPnL` = **−25.9% / −40.9% / −37.8%`; bo **top-5%** best lam PnL **AM** o ca hai nen nhieu
     lenh (`−96.8% / −85.1%`) nhung T170 chi `−56.7%`.
   - **SAI/THIEU** o tang "nhieu ngau nhien": `relSE` (SE cua mean PnL/leg) **khong** giam ~`1/sqrt(n)`
     — no **TANG**: 0.163 → 0.256 → 0.202; `relSE×sqrt(n)` = 5.37 → 12.96 → 10.36. Ly do do duoc:
     **SD/leg gan nhu khong doi** (323 / 352 / 317 USDT) trong khi **meanP/leg GIAM mot nua**
     (69.9 → 33.9 / 37.6) vi moi leg duoc size nho hon.
   - **THIEU (owner khong nhac)** tang **LECH HE THONG = n×eps**: chi phi **funding/leg** la so hang
     he thong ⇒ `Σfunding/ΣPnL` = **−2.76% (T170) → −10.73% (T100) → −6.33% (GD92)**.
     Nhieu ngau nhien `~sqrt(n)·σ` con lech he thong `~n·eps` ⇒ **ty so bias/noise TANG ~sqrt(n)**.
4. **Chuan rui ro:** `maxDD` da noi len `<=40%/nam` va **KHONG phai rao dang chan** (T170 −11.84% ·
   T100 −16.13% · GD92 −16.55%, deu duoi ca tran CU 30%). Rao dang chan that su la
   **`UW <= 200`** (T100 248 · GD92 278) va **tap trung 1 coin `<= 15%`** (T100 27.23–28.51%).

---

## 1. VIEC A — kiem gia thuyet 1x

### A1. Leverage tung leg (`margin/(quantity*entry)`)

| run | n leg | leg `lv=1` (±1e-6) | `lv` min / max | leg `lv > 1.05` |
|---|---|---|---|---|
| T170 | 1,089 | **1,089** | 0.99999986 / 1.00000015 | 0 |
| T100 | 2,559 | **2,559** | 0.99999987 / 1.00000013 | 0 |
| GD92 | 2,632 | **2,632** | 0.99999987 / 1.00000014 | 0 |

⇒ **`1x isolated` tren 100% leg ca ba nen.** Khong co don bay o bat ky leg nao.

### A2/A3/A4. Max concurrent margin va margin/equity

Quet su kien `start`/`end` tren moc PHUT tu `printDone.csv`; equity = `b + unP` tu `logs/sim.out`.
`hi` = xu ly het `start` roi moi `end` (can tren); `lo` = nguoc lai (can duoi).

| run | `peak_hi` (USDT) | `lo` | thoi diem | /von goc 35,000 | **/equity luc do** | `max_t margin/equity` | kiem cheo tu chuoi NGAY (`mmax/eq`) |
|---|---|---|---|---|---|---|---|
| T170 | **55,964** | **52,151** | 2025-10-11 04:22 / 04:20 | 159.9% / 149.0% | 54.7% / **50.1%** | **54.70%** | 49.52% (2024-04-14) |
| T100 | **67,248** | 66,748 | 2025-11-07 23:03 | 192.1% | 55.6% | **57.13%** | 56.64% (2024-04-14) |
| GD92 | **66,998** | 62,981 | 2025-10-11 04:22 | 191.4% | 56.1% | **57.49%** | 57.08% (2023-10-25) |

> T170 `52,151 @ 2025-10-11` **tai lap dung** so da ghi o `RISK_APPETITE.md` muc 6 (con so do la
> can duoi `lo`). Ty le "~47% equity" cua ban ghi cu = `52,151/111,070 = 46.96%`; do tren **equity
> ngay cua moc dinh** (2025-10-11, `b+unP = 102,303`) thi la **51.0%**.

### A5. Co chay duoc tk khong?

- **So moc co `exposure > equity`: 0** tren ca ba run (`n_exposure_gt_equity = 0`).
- Dinh exposure = **1.74–1.75x "duoi vung"**: equity luon >= 1.74 lan tong margin dang mo.
- ⇒ **KHONG the chay tk.** Tra loi cho owner (2): **DUNG**.

### A6. `Lo TAM THOI` vs `MAT THAT`

**(a) Proxy mat-that (leg `pnl/margin <= -0.90`)** — chot truoc la proxy duy nhat quan sat duoc
(`status` chi co `STOP_MARKET_DONE`/`STOP_LOSS_DONE`, khong co nhan `delist`; khong co dataset
lifecycle phu 2021-2025 trong may):

| run | `pnl/margin` min | leg `<= -0.90` | `Σpnl` cua chung | % tong PnL | leg `<= -0.50` |
|---|---|---|---|---|---|
| T170 | −0.693 | **0** | 0 | 0% | 5 |
| T100 | −0.969 | **1** | −2,088 | −2.41% | 26 |
| GD92 | −0.855 | **0** | 0 | 0% | 19 |

⇒ **Chi 1/6,280 leg mat >= 90% margin** (T100, −2,088 USDT = 2.4% tong PnL). Trong mau nay, "vi the
ve 0 khi dang giu" **gan nhu khong xay ra**: co che stop + DCA + time-stop 168h deu dong vi the
truoc khi gia ve 0. **Luu y: day la "khong co dau vet trong mau", KHONG phai "khong the xay ra".**
Kiem chung gan nhat: **FTT** (sup FTX 2022-11) — T170 giu FTT toi **3,957 USDT (9.8% equity)** luc
2022-11-10 03:51, nhung leg dong trong ~1 ngay, `pnl` = −474 / −169 / +996 ⇒ **FTT net +685 USDT**.
Tuc la stop da cat truoc khi ve 0 — **may man ve thoi diem**, khong phai co che.
Cung vay **LUNA** (2022-05): 4 leg T170 deu duong (+26/+66/+15/+23) vi da thoat tu 2021-09..12.
⇒ Neu mot coin ve 0 **trong khi dang giu**, thiet hai = **toan bo margin cua coin do** (1x).

**(b) Neu 1 coin ve 0 thi mat bao nhieu % equity** = `max_t (margin 1 coin / equity(t))`:

| run | **mat toi da** | coin | thoi diem | margin dinh (USDT) | top-5 coin |
|---|---|---|---|---|---|
| **T170** | **9.77%** | FTT | 2022-11-10 03:51 | 3,957 (AIA 8,623) | FTT 9.77 · AIA 8.43 · GAS 7.91 · STORJ 7.86 · WIF 7.39 |
| **T100** | **28.51%** | CUDIS | 2025-11-12 05:07 | 34,070 | **CUDIS 28.51** · ALPINE 20.31 · FTT 13.02 · DAR 8.55 · BANANAS31 8.54 |
| **GD92** | **14.38%** | JELLYJELLY | 2025-11-07 06:05 | 18,229 | JELLYJELLY 14.38 · FTT 10.75 · DAR 8.20 · WIF 7.89 · OM 7.49 |

⇒ **T100 mat toi 28.51% equity trong MOT cu** — **vuot tran 15%** cua `RISK_APPETITE.md`.
Day la kenh "mat that" **duy nhat co y nghia** va **1x khong bao ve no**. GD92 14.38% (sat tran),
T170 9.77% (duoi tran).

**(c) Ngay su kien = kenh "gan mat that" lon hon delist.** Ngay realized PnL xau nhat / equity ngay
do: **T100 2022-05-12 −4,096 = −12.06%** · **GD92 2022-05-12 −4,356 = −13.55%** ·
T170 2025-11-10 −5,312 = −4.75%. Voi T100/GD92 thi **mot ngay LUNA da an gan het maxDD nam 2022**
(true maxDD 2022: −12.46% / −13.21%).

**(d) Leg xau nhat / equity tai thoi diem do**: T170 −2.32% (AIA, 2025-10-11 — **dung ngay dinh
exposure**) · T100 −4.10% (ALPINE) · GD92 −2.49% (BEL). ⇒ **mot leg don le khong the gay thiet hai
nghiem trong**; chi **tap trung 1 coin** moi gay.

## 2. VIEC B — bang nho-n vs lon-n

14 run do duoc (3 nen + 11 bien the). Bang day du: `/home/ubuntu/fragility/fragility_B_main.csv`,
`fragility_B_dropK.csv`, `fragility_answer_a.csv`, `fragility_years.csv`.

| chi tieu | **T170** (nho-n) | **T100** | **GD92** | huong khi n tang |
|---|---|---|---|---|
| n leg | 1,089 | 2,559 | 2,632 | — |
| # symbol | 358 | 503 | 479 | — |
| # ngay co leg | 110 | 268 | 273 | — |
| **meanP/leg (USDT)** | 69.85 | 33.91 | 37.59 | **GIAM ~1/2** |
| SD/leg (USDT) | 323.2 | 352.2 | 317.4 | ~khong doi |
| **relSE = SE/mean** (boot block-72h ×2000 seed 20260905) | **0.1628** | **0.2561** | **0.2020** | **TANG** |
| relSE_naive = (SD/√n)/mean | 0.1402 | 0.2053 | 0.1646 | tang |
| **relSE × √n** | 5.37 | 12.96 | 10.36 | **khong hang so** |
| **MDE95/leg (USDT)** = 1.96·SE_boot | 22.29 | 17.02 | 14.88 | giam (tuyet doi) |
| MDE95 / meanP | **31.9%** | **50.2%** | **39.6%** | **TANG** |
| ⭐ ΔPnL bo **best 1 leg** | −4.78% | −3.96% | −5.03% | ~khong doi |
| ⭐ ΔPnL bo **best 5 leg** | −16.86% | −14.31% | −15.24% | ~khong doi |
| ⭐ ΔPnL bo **best top-1%** | **−25.90%** | **−40.85%** | **−37.75%** | **TANG (xau hon)** |
| ⭐ ΔPnL bo **best top-5%** | −56.72% | **−96.81%** | **−85.05%** | **TANG → PnL AM** |
| ΔPnL bo **worst 1 leg** | +3.12% | +5.36% | +2.69% | ~khong doi |
| ΔPnL bo **worst top-1%** | +24.15% | +60.85% | +47.78% | TANG |
| ΔPnL bo **worst top-5%** | +55.68% | +153.79% | +115.04% | TANG |
| **share top-1% leg** (% tong PnL) | **25.9%** | **40.9%** | **37.8%** | **TANG** |
| **share top-5%** | 56.7% | **96.8%** | **85.0%** | TANG |
| **share top-10%** | 76.8% | **136.1%** | **118.4%** | TANG (>100 = bo top-10% ⇒ PnL am) |
| **SD ret%/nam** | **9.92** | **22.00** | **28.88** | **TANG** |
| range ret%/nam | 22.76 (12.2..35.0) | 51.15 (9.3..60.4) | 70.28 (3.8..74.1) | TANG |
| **N_eff (overlap cung coin)** | 970 | 2,348 | 2,444 | — |
| **N_eff/n (overlap)** | **0.891** | **0.918** | **0.929** | tang nhe |
| **N_eff (tuan ISO)** | 76 | 143 | 145 | — |
| **N_eff/n (tuan)** | **0.070** | **0.056** | **0.055** | **giam** |
| **maxDD (THAT, `sim.out`)** | −11.84% | −16.13% | −16.55% | **TANG (xau hon)** |
| **UW (THAT, ngay)** | 92 | **248** | **278** | **TANG manh** |
| maxDD proxy (Σpnl realized, neo 35k) | −6.18% | −13.96% | −11.95% | (proxy luon nhe hon that) |
| **conc 1 coin** (`conc_max`) | 9.77% | **27.23%** | 14.38% | TANG |
| **Σfunding / ΣPnL** | **−2.76%** | **−10.73%** | **−6.33%** | **TANG (so hang he thong)** |
| equity cuoi | 111,070 | 121,770 | 133,944 | — |

**Doc ΔmaxDD/ΔUW theo drop-top-K** (proxy; day du trong `fragility_B_dropK.csv`):

| run | base proxy maxDD / UW | K=1 best | K=top-1% best | K=top-5% best |
|---|---|---|---|---|
| T170 | −6.18% / 20 | −6.18 (+0.00) / 20 | −8.11 (**−1.93pp**) / 19 | −12.06 (**−5.88pp**) / 30 |
| T100 | −13.96% / 81 | −14.32 (−0.36) / 82 | −23.73 (**−9.78pp**) / 127 (**+46**) | −55.41 (**−41.45pp**) / 123 |
| GD92 | −11.95% / 85 | −11.95 (0.00) / 85 | −11.95 (0.00) / 93 | −30.26 (**−18.32pp**) / 122 |

⇒ Bo top-1%/top-5% leg **tot nhat** lam **maxDD va UW tang MANH** o hai nen nhieu lenh, va **gan nhu
khong anh huong** T170. (Proxy neo tai 35,000 va khong mark-to-market nen **nhe hon** duong that
— T170 −6.18 vs −11.84 · T100 −13.96 vs −16.13 · GD92 −11.95 vs −16.55; dung no de **so sanh Δ**,
khong dung lam gia tri tuyet doi.)

## 3. Tra loi cu the

### (a) Bo 1% / 2% so lenh ⇒ tong PnL venh bao nhieu %

Kieu chon: `best` (PnL cao nhat) · `worst` (thap nhat) · `random` (2000 lan, seed 20260905).

| run | n | **bo 1%** (k leg) | best | worst | random mean | random p5..p95 |
|---|---|---|---|---|---|---|
| T170 | 1,089 | k=11 | **−25.90%** | +24.15% | **−1.00%** | −3.05 .. +1.38 |
| T100 | 2,559 | k=26 | **−40.85%** | +60.85% | **−0.98%** | −3.95 .. +2.69 |
| GD92 | 2,632 | k=27 | **−37.75%** | +47.78% | **−0.98%** | −3.41 .. +1.85 |
| hn-g-hi | 2,640 | k=27 | −32.17% | +47.94% | −1.00% | −3.40 .. +1.65 |
| hn-t-hi | 2,571 | k=26 | −32.27% | +59.02% | −0.91% | −3.63 .. +2.72 |

| run | n | **bo 2%** (k leg) | best | worst | random mean | random p5..p95 |
|---|---|---|---|---|---|---|
| T170 | 1,089 | k=22 | **−36.44%** | +35.91% | **−2.02%** | −5.48 .. +1.31 |
| T100 | 2,559 | k=52 | **−60.65%** | +94.94% | **−2.12%** | −6.47 .. +2.65 |
| GD92 | 2,632 | k=53 | **−53.59%** | +70.62% | **−1.96%** | −5.68 .. +1.88 |

**Doc ket qua:**
1. **Kieu `random` (lech ngau nhien, giong backtest-vs-live): `ΔPnL%` GAN NHU BANG NHAU o ca ba
   (−1.0% / −1.0% / −1.0% cho 1%; −2.0% / −2.1% / −2.0% cho 2%)** — dung bang ly thuyet
   `E[Δ] = −k/n` khi k ti le theo n. ⇒ nhieu lenh **khong** lam ket qua bot venh theo **ty le %**.
2. Nhung **theo SO LEG CO DINH** thi n co loi: `|ΔPnL%| / leg` = **0.0913% (T170) · 0.0377% (T100) ·
   0.0363% (GD92)** — ty le **1 : 0.413 : 0.398**, dung bang ty le `n` (1 : 0.425 : 0.414).
   ⇒ **mot vai lenh bi lech ngau nhien lam nen nhieu lenh nhay IT hon 2.35–2.42 lan**. **Owner DUNG
   o day.**
3. Nhung neu cac lenh lech **khong ngau nhien** ma roi vao **duoi** (dung nhu thuc te: lenh lon nhat
   = coin bien dong manh nhat = de bi truot gia/funding nhat), thi nen nhieu lenh **venh HON**:
   bo `best top-1%` = **−40.9% / −37.8%** so voi **−25.9%** T170; bo `best top-5%` lam PnL **AM**
   o T100/GD92 (−96.8% / −85.1%) nhung T170 van con +56.7% duong.
4. **Duoi cua bo-ngau-nhien cung xau hon** o n lon: 2% random, T170 p5 = −5.48% con T100 = −6.47%,
   `min` = −9.77% (T170) vs **−14.08%** (T100).

### (b) Neu 1 coin ve 0 thi mat bao nhieu % equity

| run | **mat toi da** | coin | thoi diem | so leg cua coin do | top-2 |
|---|---|---|---|---|---|
| **T170** | **9.77%** | FTT | 2022-11-10 03:51 | 7 | FTT 9.77% · AIA 8.43% |
| **T100** | **28.51%** | CUDIS | 2025-11-12 05:07 | — | CUDIS 28.51% · ALPINE 20.31% |
| **GD92** | **14.38%** | JELLYJELLY | 2025-11-07 06:05 | — | JELLYJELLY 14.38% · FTT 10.75% |

⇒ **T100 se mat 28.5% equity trong mot cu neu coin do ve 0** — **hai lan tran 15%**.
Ngay thuc te **CUDIS chi lun phat nhe** (2025-11-12 la ngay realized xau nhat cua T100: −9,197 USDT
= −8.4% equity), nhung **do la may, khong phai co che**. Trap trung 1 coin **la rang buoc
`RISK_APPETITE.md` dang chan that su va khong nen noi** (khuyen nghi GIU `<=15%`, va **T100 dang FAIL**).

## 4. Ket luan 3 tang + 1 muc 1x

- **(i) Nhieu NGAU NHIEN (SE/MDE): KHONG giam ~1/sqrt(n).** `relSE` **tang** (0.163 → 0.256 → 0.202),
  `relSE×√n` = 5.37 → 12.96 → 10.36. Nguyen nhan do duoc: **SD/leg gan nhu khong doi (323/352/317)
  trong khi meanP/leg GIAM mot nua (69.9 → 33.9/37.6)** — "tang n, giam ti le lai" lam moi leg nho
  di, nen ti le nhieu/leg **tang**. MDE95 **tuyet doi** thi giam (22.3 → 17.0/14.9 USDT/leg) nhung
  **tuong doi** lai tang (31.9% → 50.2%/39.6% cua meanP).
  ⇒ Menh de "nhieu lenh ⇒ bot venh" **KHONG** duoc du lieu ung ho.
- **(ii) RUI RO: XAU HON khi n lon.** maxDD −11.84% → −16.13% / −16.55%; UW 92 → **248 / 278**;
  `SD ret%/nam` 9.9 → 22.0 / 28.9; bo top-1% best lam maxDD proxy −1.9pp (T170) vs −9.8pp (T100).
- **(iii) Lech HE THONG = n×eps: TANG theo n.** `Σfunding/ΣPnL` = −2.76% → **−10.73%** / −6.33%;
  funding/leg = −1.93 → −3.64 / −2.38 USDT. Nhieu ngau nhien `~√n·σ`, lech he thong `~n·eps`
  ⇒ **ti so bias/noise tang ~√n**. Day la tang owner **khong nhac** va no chong lai ket luan
  "nhieu lenh thi an toan hon".
- **(iv) 1x: XAC NHAN "khong chay duoc tk".** Exposure max 54.7–57.5% equity, **0 moc** co
  exposure > equity, `lv = 1` tren 100% leg. **Rui ro MAT THAT nam o:** (1) **tap trung 1 coin**
  — T100 **28.51%** equity (vuot tran 15%), GD92 14.38%; (2) **ngay su kien thi truong** —
  2022-05-12 LUNA: −12.06% / −13.55% equity trong **1 ngay**; (3) **funding** — so hang he thong
  tuyen tinh theo n. **Khong** nam o delist: chi **1/6,280 leg** mat >= 90% margin.

### Owner DUNG o cho nao / SAI o cho nao

| menh de cua owner | ket luan | bang chung |
|---|---|---|
| "maxDD 30-40% deu ok, no chi la so lo TAM THOI" | **DUNG** ve liquidation | `lv = 1` 100% leg; exposure <= 57.5% equity; 0 moc exposure > equity |
| "ko chay duoc tk vi danh 1x" | **DUNG** | A1–A5 |
| "tap lenh nho thi ket qua rat venh" (T170) | **DUNG mot phan** | T170 `share top-1% = 25.9%`, bo top-5% van con +43% PnL |
| "so luong lenh lon thi khac biet o vai lenh ko anh huong lon" | **DUNG** neu lech **ngau nhien + so leg co dinh** (`~k/n`, nhay it hon 2.4x); **SAI** neu lech roi vao **duoi** (top-1% ăn 41%) |
| (ngam) "nhieu lenh ⇒ it venh hon" | **SAI** | relSE tang; share top-1%/5% tang; maxDD/UW/venh nam deu tang; funding drag tang |
| **(thieu) "lo tam thoi" bao gom CA dong von** | **THIEU** | 1x chi chan liquidation. Tap trung 1 coin (T100 28.5%) va funding (n×eps) la **mat that**, khong hoi phuc |

## 5. Canh bao phuong phap (doc truoc khi trich dan)

1. **Confound n ≠ chi n.** Doi chieu kha dung la **T170 (gate dyn scale 1.70, n_pass 841)** vs
   **T100 (scale 1.0, n_pass 2,317)** / **GD92 (scale 1.0 + gate rolling pct 0.92/90d, n_pass 2,468)**.
   Do la dung nghia "mo gate de tang so lenh" — nhung no doi **ca tap leg duoc chon**, khong chi so
   luong. **Moi so sanh T170 vs T100/GD92 o §2 la "n+chien luoc", KHONG phai "n thuan".**
   Ty le n chi **2.35–2.42x** (ky vong `1/√n` chi 1.53x) — bien do nho.
2. **Proxy vs that.** `maxDD`/`UW`/`ΔmaxDD` trong B3 tinh tren duong **Σpnl realized** neo 35,000,
   khong mark-to-market ⇒ **nhe hon** duong that (da doi chieu: −6.18 vs −11.84 · −13.96 vs −16.13 ·
   −11.95 vs −16.55). Dung de **so sanh Δ**, khong trich lam gia tri tuyet doi.
   `maxDD`/`UW`/`ret% nam`/`conc` **THAT** lay tu `logs/sim.out` (`b+unP`) qua
   `gd92xexit_score.equity/summary/yearly_detail` ⇒ **cung cong thuc** voi `RESULT_EXIT_HIGH_N.md`.
3. **Delist khong quan sat duoc truc tiep**: `printDone.status` chi co 2 gia tri; khong co dataset
   lifecycle phu 2021-2025 trong may (`claudedata/gate0_133/lifecycle_oracle.csv` chi tu 2025-09).
   A6(a) la **proxy** `pnl/margin <= -0.90`, da chot TRUOC. **Khong** duoc ket luan "delist khong
   the xay ra".
4. **Khong doc 2026**: `date_last = 20251230`, `ts.year.max() = 2025` tren ca ba run.
5. Ket qua nay **khong** dung de tich hop/go bien the nao.

## 6. De xuat buoc tiep (KHONG tu tich hop)

1. **Do `CONC_CAP_PERCOIN_ENABLED=1 / PCT=0.15` (hoac 0.10) tren nen T100**: T100 `conc 28.51%` la
   kenh mat-that duy nhat co the loai bo bang co che da co san; chi phi (PASS/FAIL) **chua do**.
   Day la ung vien **duy nhat** dang gia.
2. **Neu muon "tang n" ma giam venh tuong doi**: phai **giu meanP/leg khong giam** (size theo
   chat luong chu khong theo so luong) — do duoc ngay rang "n tang 2.4x + meanP/leg giam 2x"
   lam `relSE` tang 1.24–1.57x. Khong co bang chung nao cho thay chi tang n la du.
3. **Them 1 hang vao bang cham diem chuan**: `Σfunding/ΣPnL` (hom nay khong co trong
   `RISK_APPETITE.md`). T100 **−10.73%** la so hang he thong lon nhat do duoc.
4. **Giu nguyen** `UW <= 200` va tap trung 1 coin `<= 15%` — day moi la hai rao **dang binding**;
   `maxDD <= 40%` khong binding voi bat ky run nao.
