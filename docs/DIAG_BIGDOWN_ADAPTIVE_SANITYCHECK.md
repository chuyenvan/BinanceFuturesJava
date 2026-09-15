# DIAG — SANITY-CHECK ngUONG ADAPTIVE `mean_N - k*std_N` cho BIG_DOWN (CHI DEM)

> **Tai lieu DEM THUAN TUY.** Khong sua mot dong `.java` nao, khong them flag, **khong chay sim**,
> **khong tinh PnL**. Noi tiep `docs/DIAG_BIGDOWN_TRIGGER_MECHANISM.md` (commit `796ae01`).
>
> Thiet ke duoc MASTER chot truoc khi do:
> ```
> threshold_adaptive(D) = mean_N(D) - k * std_N(D)
> ```
> `mean_N(D)`, `std_N(D)` = trung binh / do lech chuan cua **TOAN BO** gia tri `rateDownAvg`
> (1 gia tri/phut, **moi phut**, khong chi phut co trigger) trong **N ngay lich TRUOC D**, khong
> gom `D` — **causal**, refresh theo ngay (cung nguyen tac `RegimeSchedule` dang dung cho
> `GATE_REGIME_ADAPTIVE`). Luoi `N in {90,120,180}` x `k in {2, 2.5, 3}`.
>
> **Tai lieu KHONG de xuat tham so, KHONG doi cong thuc, KHONG ket luan nen chon gi.** Muc 5 ghi
> hai canh bao dung theo yeu cau muc 4 cua de bai.

---

## 0. Ba dong ket qua

1. **Ca 9/9 to hop deu VUOT NGUONG LOAI** cua chinh de bai (`> 2000 phut`): thap nhat **20,536**
   phut, cao nhat **61,397** phut, so voi **124** phut cua nguong co dinh hien tai — tuc **166x den
   495x**. So ngay co trigger: **1438-1618 / 1645 ngay (87-98%)**, so voi **56 ngay (3.4%)**.
2. `threshold_adaptive` **khong bao gio duong** (0/1645 ngay o ca 9 to hop) — nhung no nam trong
   khoang **-0.00195 .. -0.00807**, tuc **nong hon nguong co dinh `-0.03157` tu 4x den 16x**, va
   **> -0.005 o 1127-1639 / 1645 ngay**.
3. Nguyen nhan do duoc: `rateDownAvg` co **skew = -14.87** va **excess-kurtosis = +2401**. Nguong
   co dinh hien tai tuong duong **-22.4 sigma** (do tren toan span) — khong phai 2-3 sigma.

---

## 1. Nguon du lieu va rang buoc causal

| | |
|---|---|
| Nguon | `/home/ubuntu/wfo_ds_x1_2021/market.bin` — **tai su dung nguyen ven** tu round truoc; n = **2,554,812** phut, span UTC `2021-01-01 .. 2025-12-31` |
| Cua so dem | UTC-day `2021-07-01 .. 2025-12-31` = **1645 ngay** / **2,301,233 phut** |
| Warm-up | `market.bin` bat dau `2021-01-01` nen ngay dau cua span (`2021-07-01`) da co du **181** ngay lich su => **ca 3 gia tri N deu co du lieu cho ca 1645/1645 ngay**, khong ngay nao bi NA |
| Causal | `mean_N(D)`, `std_N(D)` tinh tren `[D-N, D)` — **khong gom ngay D**. Cai dat bang prefix-sum theo ngay (sum, sum-of-squares, count) => dong nhat voi dinh nghia, khong xap xi |
| Doi chieu | nguong co dinh `Configs.MS_DOWN_BIG_AVG = -0.03157` (`Configs.java:380`) => **124 phut / 56 ngay**, T170 mo **248 leg BIG_DOWN** |
| Script | `/tmp/bd_adapt.py`, `/tmp/bd_adapt2.py`, `/tmp/bd_adapt3.py` (read-only, khong commit — cung quy uoc cac DIAG truoc); output `/tmp/bd_adapt.txt`, `/tmp/bd_adapt2.txt`, `/tmp/bd_adapt.json` |

---

## 2. `mean_N` / `std_N` co on dinh khong (yeu cau muc 1)

### 2.1 Phan phoi tren toan span

| N | `mean_N` min | p10 | **p50** | p90 | max | `std_N` min | p10 | **p50** | p90 | max |
|---|---|---|---|---|---|---|---|---|---|---|
| 90 | -0.002030 | -0.001416 | **-0.000489** | -0.000361 | -0.000310 | 0.000751 | 0.000937 | **0.001253** | 0.001742 | 0.002298 |
| 120 | -0.001923 | -0.001399 | **-0.000501** | -0.000366 | -0.000323 | 0.000794 | 0.000954 | **0.001267** | 0.001644 | 0.002105 |
| 180 | -0.001769 | -0.001371 | **-0.000511** | -0.000387 | -0.000341 | 0.000847 | 0.000960 | **0.001305** | 0.001634 | 0.002102 |

Bien do dao dong (max/min): `mean_N` **5.2x - 6.5x**; `std_N` **2.5x - 3.1x**. Tang N tu 90 len 180
lam giam bien do nhung **khong nhieu** (`std_N` 3.06x -> 2.48x).

### 2.2 Theo nam (median trong nam)

| N | nam | median `mean_N` | median `std_N` | median `thr` (k=2.5) |
|---|---|---|---|---|
| 90 | 2021 | -0.000430 | 0.001484 | -0.004141 |
| 90 | 2022 | **-0.000368** | 0.001292 | -0.003597 |
| 90 | 2023 | -0.000431 | **0.000944** | **-0.002790** |
| 90 | 2024 | -0.000811 | 0.001242 | -0.003917 |
| 90 | 2025 | **-0.001412** | 0.001447 | **-0.005029** |
| 120 | 2021 | -0.000440 | 0.001555 | -0.004328 |
| 120 | 2022 | -0.000391 | 0.001326 | -0.003705 |
| 120 | 2023 | -0.000427 | 0.000968 | -0.002846 |
| 120 | 2024 | -0.000817 | 0.001231 | -0.003894 |
| 120 | 2025 | -0.001394 | 0.001405 | -0.004907 |
| 180 | 2021 | -0.000492 | **0.001908** | **-0.005262** |
| 180 | 2022 | -0.000397 | 0.001414 | -0.003932 |
| 180 | 2023 | -0.000425 | 0.000964 | -0.002836 |
| 180 | 2024 | -0.000836 | 0.001250 | -0.003961 |
| 180 | 2025 | -0.001322 | 0.001420 | -0.004871 |

**Mo ta (khong ket luan):**

- `mean_N` **troi manh hon** `std_N`: median theo nam di tu **-0.000368 (2022)** den
  **-0.001412 (2025)** = **3.8x**; trong khi `std_N` chi di tu 0.000944 (2023) den 0.001484 (2021)
  = **1.6x**.
- Dieu nay **nguoc voi truc giac "2022 bear = bien dong cao"**: nam 2022 (bear) lai la nam co
  `mean_N` **gan 0 nhat** va nguong k=2.5 **nong thu hai**; 2025 moi la nam `mean_N` am nhat.
- Tong hop lai, `thr(k=2.5)` dao dong tu **-0.00279 (2023)** den **-0.00503 (2025)** = **1.8x**.

### 2.3 Mot phut cuc doan dieu khien `mean_N`/`std_N` suot N ngay

Phut `rateDownAvg = -0.354162` (dinh lich su, UTC-day **2025-10-10**, tuong ung `2025-10-11 04:13`
gio GMT+7 — dung cum BIG_DOWN 54 leg/gio cua `DIAG_DCA_CONCURRENCY` muc 6):

| ngay (N=90) | `mean_90` | `std_90` | `thr(k=2.5)` |
|---|---|---|---|
| 2025-10-05 (truoc) | -0.001524 | 0.001070 | -0.004198 |
| **2025-10-11 (sau)** | -0.001569 | **0.001901** | **-0.006321** |
| 2025-10-20 | -0.001642 | 0.001955 | -0.006529 |
| 2025-11-15 | -0.001823 | 0.002002 | -0.006829 |
| 2025-12-31 | -0.002030 | 0.001989 | -0.007004 |

| ngay (N=180) | `mean_180` | `std_180` | `thr(k=2.5)` |
|---|---|---|---|
| 2025-10-05 | -0.001465 | 0.001116 | -0.004256 |
| 2025-10-12 | -0.001498 | **0.001582** | -0.005452 |
| 2025-11-15 | -0.001602 | 0.001634 | -0.005688 |
| 2025-12-31 | -0.001769 | 0.001618 | -0.005813 |

**DUNG MOT phut** lam `std_90` tang **+78%** va keo `thr(k=2.5)` sau them **+51%**, va hieu ung do
**giu nguyen suot 90 (resp. 180) ngay tiep theo** roi bien mat dot ngot khi phut do roi khoi cua so.
Day la dac tinh co hoc cua `mean/std` tren phan phoi co outlier lon — ghi lai de MASTER biet, khong
ket luan.

---

## 3. BANG 9 TO HOP (yeu cau muc 2 + 3)

**Doi chieu — nguong co dinh hien tai `-0.03157`: `124` phut / `56` ngay / `248` leg BIG_DOWN (T170),
`43.5%` so phut trigger roi vao 3 cua so he thong.**

**Do phu cua 3 cua so** (`2025-03-04..2025-10-11`, `2021-11-16..2022-08-20`, `2024-04-10..2024-08-01`):
**614/1645 ngay = 37.3%** so ngay va **37.3%** so phut cua span. Day la **muc "ngau nhien"** de doc
cot `%in3win`.

| # | N | k | **phut trigger** | vs 124 | **ngay co trig** | vs 56 | **% in 3win** | `thr` mean | `thr` min | `thr` max | `thr` p50 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 90 | 2.0 | **60,031** | **484x** | 1616 (98.2%) | 28.9x | 37.6% | -0.00333 | -0.00605 | -0.00195 | -0.00322 |
| 2 | 90 | 2.5 | **34,155** | **275x** | 1560 (94.8%) | 27.9x | 37.6% | -0.00397 | -0.00706 | -0.00233 | -0.00389 |
| 3 | 90 | 3.0 | **20,789** | **168x** | 1438 (87.4%) | 25.7x | 37.5% | -0.00462 | -0.00807 | -0.00270 | -0.00457 |
| 4 | 120 | 2.0 | **60,352** | **487x** | 1618 (98.4%) | 28.9x | 36.9% | -0.00332 | -0.00553 | -0.00205 | -0.00326 |
| 5 | 120 | 2.5 | **34,169** | **276x** | 1557 (94.7%) | 27.8x | 36.7% | -0.00397 | -0.00644 | -0.00244 | -0.00393 |
| 6 | 120 | 3.0 | **20,555** | **166x** | 1448 (88.0%) | 25.9x | 37.0% | -0.00462 | -0.00735 | -0.00284 | -0.00460 |
| 7 | 180 | 2.0 | **61,397** | **495x** | 1615 (98.2%) | 28.8x | 35.6% | -0.00333 | -0.00500 | -0.00213 | -0.00332 |
| 8 | 180 | 2.5 | **34,494** | **278x** | 1551 (94.3%) | 27.7x | 35.6% | -0.00398 | -0.00586 | -0.00255 | -0.00404 |
| 9 | 180 | 3.0 | **20,536** | **166x** | 1450 (88.1%) | 25.8x | 35.9% | -0.00464 | -0.00691 | -0.00298 | -0.00471 |

`nDayNA` (ngay khong du lich su) = **0** o ca 9 to hop.

### 3.1 Ba quan sat tu bang (mo ta)

1. **`k` quyet dinh gan nhu toan bo, `N` gan nhu khong.** Doi `N` tu 90 -> 180 (gap doi) lam so
   phut trigger doi **< 2.5%** (vd k=3.0: 20,789 / 20,555 / 20,536). Doi `k` tu 2.0 -> 3.0 lam so
   phut giam **~3x**. Tuc **luoi 3x3 thuc chat chi co 3 diem phan biet**.
2. **Trigger phan bo gan nhu DEU theo thoi gian.** `%in3win` = **35.6-37.6%**, trong khi 3 cua so
   chiem dung **37.3%** so phut cua span. Tuc nguong adaptive **khong tap trung** vao cac giai doan
   he thong da biet la cang thang. Nguong co dinh hien tai cho **43.5%** (co tap trung nhe,
   `1.17x` muc ngau nhien).
3. **Khoang dao dong cua `thr`** (muc 3, cot min/max): `-0.00195 .. -0.00807` — tuc **nong hon
   nguong co dinh `-0.03157` tu 3.9x den 16.2x**, va **khong to hop nao co bat ky ngay nao** dat
   toi muc sau cua nguong hien tai.

### 3.2 Luu y bat buoc ve "so leg"

Bang tren dem **phut trigger**, **khong** quy doi ra leg. Cong thuc `leg = 2 x phut` (dung o
`DIAG_BIGDOWN_TRIGGER_MECHANISM` muc 1.5) **CHI dung o mat do hien tai**; o mat do 20,000-60,000
phut/4.5 nam thi `symbolLocked` (coin da co vi the bi loai) va `U_MAX=0.60` / `throttle` se bind
lien tuc, nen **khong duoc ngoai suy so leg**. Muon biet so leg phai chay sim — ngoai pham vi
round nay.

---

## 4. Vi sao lech — do luong hinh dang phan phoi (bang chung cho muc 5b)

### 4.1 `rateDownAvg` khong he gan chuan

Tren 2,301,233 phut cua span:

| | |
|---|---|
| mean | -0.000782 |
| std | 0.001376 |
| **skew** | **-14.874** (phan phoi chuan = 0) |
| **excess kurtosis** | **+2,401.0** (phan phoi chuan = 0) |

### 4.2 Bang doi chieu `k` <-> so phut (tinh tinh, tren mean/std TOAN SPAN)

| k | `mean - k*std` | so phut < nguong | % phut |
|---|---|---|---|
| 2 | -0.003534 | 57,544 | 2.50057% |
| 2.5 | -0.004222 | 31,197 | 1.35566% |
| 3 | -0.004910 | 18,130 | 0.78784% |
| 4 | -0.006286 | 7,365 | 0.32005% |
| 5 | -0.007662 | 3,595 | 0.15622% |
| 6 | -0.009038 | 2,139 | 0.09295% |
| 8 | -0.011790 | 980 | 0.04259% |
| 10 | -0.014542 | 572 | 0.02486% |
| 15 | -0.021422 | 251 | 0.01091% |
| 20 | -0.028302 | 152 | 0.00661% |
| 22 | -0.031054 | 129 | 0.00561% |
| 23 | -0.032430 | 117 | 0.00508% |
| **NGUONG CO DINH -0.03157** | | **124** | **0.00539%** |

**Nguong co dinh hien tai tuong duong `(thr - mean)/std` = -22.38 sigma.**

### 4.3 "So sigma" cua nguong co dinh theo tung cua so rolling (causal)

| N | min | p10 | **p50** | p90 | max |
|---|---|---|---|---|---|
| 90 | -41.5 | -33.2 | **-24.7** | -17.9 | -13.5 |
| 120 | -39.2 | -32.6 | **-24.2** | -18.8 | -14.7 |
| 180 | -36.8 | -32.4 | **-23.4** | -18.3 | -14.7 |

Tuc de tai lap mat do trigger hien tai bang dang `mean_N - k*std_N`, `k` phai nam quanh **23-25**,
va no **khong on dinh**: dao dong **-13.5 .. -41.5** (gap **3.1x**) theo giai doan. (Day la **do
luong**, khong phai de xuat `k`.)

---

## 5. HAI CANH BAO theo yeu cau muc 4 cua de bai

### (a) To hop cho trigger = 0 hoac > 2000 phut => **BAT — CA 9/9 TO HOP**

| | |
|---|---|
| trigger = 0 | **khong to hop nao** |
| trigger > 2000 phut | **TAT CA 9 to hop**: N=90 k=2.0 (60,031) · k=2.5 (34,155) · k=3.0 (20,789) · N=120 k=2.0 (60,352) · k=2.5 (34,169) · k=3.0 (20,555) · N=180 k=2.0 (61,397) · k=2.5 (34,494) · k=3.0 (20,536) |

To hop "it trigger nhat" (`N=180, k=3.0`) van la **20,536 phut = 166x** muc hien tai, va **vuot
nguong loai 2000 phut 10.3 lan**. **Khong to hop nao trong luoi 3x3 nam trong vung chap nhan duoc
cua chinh de bai.**

### (b) `threshold_adaptive` co giai doan nao duong hoac gan 0 => **BAT (mot phan)**

| kiem tra | ket qua |
|---|---|
| So ngay `thr >= 0` | **0 / 1645** o **ca 9** to hop — `thr` **khong bao gio duong** |
| So ngay `thr > -0.005` | **1127 - 1639 / 1645** tuy to hop (xem bang duoi) |
| `thr` sau nhat tung dat (toan luoi) | **-0.00807** (N=90, k=3.0) — van **nong hon `-0.03157` 3.9 lan** |

| to hop | nDay `thr > -0.005` | to hop | nDay `thr > -0.005` | to hop | nDay `thr > -0.005` |
|---|---|---|---|---|---|
| N=90 k=2.0 | 1546 | N=120 k=2.0 | 1565 | N=180 k=2.0 | 1639 |
| N=90 k=2.5 | 1469 | N=120 k=2.5 | 1436 | N=180 k=2.5 | 1441 |
| N=90 k=3.0 | **1147** | N=120 k=3.0 | **1127** | N=180 k=3.0 | 1216 |

**Doc dung theo mo ta cua de bai:** du `thr` khong bao gio duong, hien tuong ma de bai du lieu
**van xay ra o dang manh**: `rateDownAvg` luon am va **rat gan 0** (median -0.000647), `mean_N` gan
0 (-0.0003 .. -0.0020), `std_N` nho (0.00075 .. 0.0023), nen `k*std` voi `k in {2,2.5,3}` **khong du
keo nguong xuong muc co nghia** — `thr` dung lai o `-0.002 .. -0.008` trong khi su kien BIG_DOWN
that nam o `-0.03` tro xuong.

**Ket luan ky thuat (mo ta, khong doi cong thuc):** dang `mean - k*std` voi `k` hang 2-3 gia dinh
ngam mot phan phoi **gan chuan**. `rateDownAvg` co **skew -14.9** va **excess-kurtosis +2401**
(muc 4.1) — `std` bi chi phoi boi phan than phan phoi (noi 99.99% du lieu nam), trong khi su kien
can bat nam o duoi p0.01. Do la ly do do duoc cua viec `k` phai hang **23-25** (muc 4.3) chu khong
phai 2-3. **Tai lieu nay KHONG tu doi cong thuc** — bao cao de MASTER quyet.

---

## 6. Nhung gi tai lieu nay KHONG lam

- **Khong** chay sim, **khong** tinh PnL/CAGR/maxDD cho bat ky to hop nao.
- **Khong** de xuat `N`, `k`, hay cong thuc thay the (percentile, MAD, EVT... deu **khong** duoc de
  xuat o day).
- **Khong** ngoai suy so leg BIG_DOWN tu so phut trigger (xem muc 3.2).
- Moi so deu tinh tren **DEV 2021-07..2025-12** — cung cua so da sinh ra moi gia thuyet truoc day;
  bat ky tham so nao chon tu day deu **da bi nhiem**, xac nhan that chi co o holdout.

---

## 7. Artifact

| | |
|---|---|
| Script (khong commit) | `/tmp/bd_adapt.py` (luoi 9 to hop), `/tmp/bd_adapt2.py` (hinh dang phan phoi + so sigma), `/tmp/bd_adapt3.py` (anh huong outlier) |
| Output | `/tmp/bd_adapt.txt`, `/tmp/bd_adapt2.txt`, `/tmp/bd_adapt.json` |
| Du lieu | `/home/ubuntu/wfo_ds_x1_2021/market.bin` (tai su dung tu round `796ae01`) |
| Doi chieu | `Configs.MS_DOWN_BIG_AVG = -0.03157` (`Configs.java:380`); baseline T170 md5 `efb793e2468ca3a7318da0f0ad23d4fc` (248 leg BIG_DOWN) |
| Tai lieu nen | `docs/DIAG_BIGDOWN_TRIGGER_MECHANISM.md` (`796ae01`), `docs/DIAG_DCA_CONCURRENCY.md` (`f03a4f1`) |
