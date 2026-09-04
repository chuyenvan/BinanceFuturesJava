# C4H_RESULT — do lai o chan troi 4h voi nhan `maxFav_4h` va nhan NHI PHAN `maxFav_4h >= 6%`

Chay 2026-09-04, Oracle CPU. `research/analysis/c4h.py`, log `/home/ubuntu/cov/C4H.out`.
**MO TA (descriptive)** — khong chon ung vien, khong verdict pass/fail => khong can pre-reg.
CHI DEV. 772,011 dong / **4,595 tick** / 303 khoi 72h — **cung tap tick** voi `CEIL_RESULT`.
Nguon nhan 4h: `label_15m/funding_label_202[2-4]*.pb`, `usecols=[maxFav_4h, retEnd_4h, nBars_4h]`,
loc `nBars_4h >= 16` (y `PREREG_G015CUT §1`). `meta.json` xac nhan file nhan co **4 chan troi:
4h / 12h / 24h / 72h**.

## 0. DINH NGHIA (de doc bang)

- `edge5` = trung binh **theo tick** cua (mean outcome cua **top-5** theo ranker) − (mean outcome
  **toan pool tick do**). San = 0 = chon bua trong cung tick.
- **tran ORACLE** = dung `edge5` nhung ranker chinh la **outcome that** (gian lan, biet truoc
  tuong lai). Do la muc **cao nhat co the** cua `edge5` tai `K=5`.
- **`%bat`** = `edge5(model) / edge5(oracle)`.
  ⚠️ Tran la **du bao hoan hao**, nen `%bat` khong bao gio ky vong gan 100%. No dung de
  **so cac ranker tren CUNG nhan** va de tra loi "con du dia hay khong", **khong** phai
  "phan tram loi nhuan dang bo lai". Va no phu thuoc **K** va **nhan** — doi nhan la doi mau so.

## 1. THONG KE NEN CUA NHAN 4h

| | gia tri |
|---|---|
| `P(maxFav_4h >= 6%)` tren pool | **12.43%** |
| `maxFav_4h` trung binh | **+3.07%** |
| `retEnd_4h` trung binh | +0.23% |
| **spearman(`maxFav_4h`, `maxFav_72h`)** | **0.4626** |
| spearman(`maxFav_4h`, `g1lite`) | 0.4175 |

⇒ **Nhan 4h va nhan 72h chi trung nhau ~46% ve thu hang.** Day khong phai chi tiet — do la
**hai muc tieu khac nhau**.

## 2. TRAN ORACLE + %BAT, theo tung outcome (cung 4,595 tick)

| outcome | tran ORACLE | S1 | **S1 %bat** | CI95 | G015 %bat | `vol_7d` tho %bat |
|---|---|---|---|---|---|---|
| **`maxFav_4h`** | +8.68% | +2.24% | **25.8%** | [20.9%, 32.0%] | 18.0% | **28.5%** |
| **`hit6_4h`** (nhan G015 THAT) | +63.40pp | +16.20pp | **25.5%** | [21.8%, 29.8%] | 19.0% | **26.6%** |
| `retEnd_4h` | +6.98% | +0.002% | **0.0%** | [-2.5%, +2.4%] | 1.0% | 0.1% |
| `g1lite` (72h) | +38.04% | +6.67% | 17.5% | [13.1%, 22.1%] | 11.6% | 20.0% |
| `maxFav_72h` | +38.35% | +7.78% | 20.3% | [15.9%, 24.8%] | 13.8% | 23.3% |
| `g1_replay` (72h, `CEIL_RESULT`) | +22.93% | +1.18% | **5.2%** | [1.4%, 8.9%] | 3.4% | 4.9% |

## 3. rank-IC theo tick (spearman, 4,224 tick co du lieu)

| outcome | S1 | G015 | `vol_7d` tho |
|---|---|---|---|
| `maxFav_4h` | +0.2525 | +0.1839 | **+0.3314** |
| `hit6_4h` | +0.1672 | +0.1102 | **+0.1878** |
| `g1lite` | +0.1813 | +0.1088 | **+0.2083** |

## 4. HIEU GHEP CAP (khoi 72h, kem hieu chinh do phu `f=1.21` cua `COV_RESULT`)

| outcome | S1 − G015 | sau `f` | S1 − `vol_7d` | sau `f` |
|---|---|---|---|---|
| `maxFav_4h` | +0.68% | **[+0.05, +1.31] LOAI TRU 0** | -0.23% | [-0.72, +0.26] chua 0 |
| **`hit6_4h`** | **+4.17pp** | **[+1.68, +6.66] LOAI TRU 0** | -0.64pp | [-3.22, +1.93] chua 0 |
| `retEnd_4h` | -0.07% | [-0.27, +0.14] chua 0 | -0.01% | [-0.26, +0.24] chua 0 |
| `g1lite` | +2.25% | **[+0.73, +3.76] LOAI TRU 0** | -0.93% | [-3.78, +1.92] chua 0 |
| `maxFav_72h` | +2.48% | **[+0.88, +4.07] LOAI TRU 0** | -1.17% | [-3.91, +1.56] chua 0 |

## 5. NAM KET LUAN

1. **`%bat` phu thuoc gan nhu HOAN TOAN vao viec chon nhan** — cung mot model S1, cung mot tap
   tick: **25.8%** (`maxFav_4h`) · 20.3% (`maxFav_72h`) · 17.5% (`g1lite`) · **5.2%**
   (`g1_replay`) · **0.0%** (`retEnd`). Bien do gap **hon 5 lan** giua 4h va `g1_replay`.
   ⇒ Moi phat bieu dang "he bat duoc X% tran, con Y% du dia" **vo nghia neu khong ghi ro nhan**.
   Con so **17.8%** dang duoc dan khap noi la con so cua **`g1lite`**.
2. **S1 xep hang tot hon G015 NGAY TREN NHAN RUOT CUA G015.** Tren `hit6_4h`
   (= dung `maxFav_4h >= 0.06` ma G015 duoc train): S1 **25.5%** vs G015 **19.0%**, hieu
   **+4.17pp**, **loai tru 0** ke ca sau hieu chinh `f=1.21`. G015 duoc train tren chinh nhan nay
   con S1 train tren nhan 72h — vay S1 **khong** thang nho trung nhan.
3. **Vol-confound KHONG chi o `g1lite`/72h — no co o 4h va con MANH HON.** `vol_7d` tho:
   `%bat` 28.5% vs S1 25.8% tren `maxFav_4h`; rank-IC **+0.3314** vs S1 **+0.2525**. Va
   `S1 − vol_7d` **chua 0 o MOI nhan da thu**. Ly do co hoc giong nhau: moi nhan ho `maxFav`
   thuong **bien do**, nen coin bien dong manh tu dong ghi diem.
4. **`retEnd` = 0 o CA HAI chan troi.** `retEnd_4h` S1 bat **0.0%** [-2.5, +2.4];
   `retEnd_72h` S1 bat -0.1% [-6.0, +5.8]. **Khong ranker nao du bao duoc loi suat hien thuc
   hoa**, chi du bao duoc ho "no da leo cao bao nhieu".
5. **Nhan 4h va 72h chi trung 46% thu hang** ⇒ chon chan troi la mot **nga re that**. Va
   `AUDIT A11` — phep so nhan da dung de ket luan "khong can doi nhan"
   (`g1lite 0.584 > maxFav_72h 0.574 > g1_replay 0.507` so voi ROI that) — **chua tung bao gom
   ho 4h**. Do la lo hong cu the: **chua ai do tuong quan `maxFav_4h` voi ROI that cua sim.**

## 6. Cai job nay KHONG lam

Khong train, khong sinh bins, khong chay java, khong cham VALIDATION/HOLDOUT. Khong ket luan
nhan nao "tot hon" — muon vay phai pre-reg va phai do voi ROI THAT cua sim (muc 5.5).
Khong sua verdict nao da co.
