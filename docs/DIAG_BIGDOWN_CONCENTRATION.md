# DIAG ? Tap trung von 1 coin khi nhoi het luoi DCA 1/1/3/8

> **Day la tai lieu SU THAT/RUI RO (descriptive), KHONG phai thi nghiem.** Khong co pre-reg,
> khong doi tham so, khong chay sim moi. Moi so lay tu code dang co trong repo + printDone.csv /
> sim.out cua cac run DA CHAY. Muc dich: tra loi cau hoi "leg cuoi tan 40% tai khoan a?".

Cau hoi goc (user): *"1/1/3/8 la sao, entry vao da 4.5% roi thi leg cuoi tan 40% tai khoan a,
dinh 1 coin chet la teo?"*

---

## 1. Cong thuc CHINH XAC (doc tu code, khong suy dien)

Ba cho quyet dinh, theo dung thu tu thuc thi:

**(a) `TradeUtils.managerBudget` (dong 87-95)** ? chia cho tong trong so DUNG MOT LAN:
```java
float u = used / balanceBasic;                  // used = marginRunning CA SO, khong rieng coin nay
if (u >= Configs.U_MAX) return null;            // U_MAX = 0.60 -> chan lenh moi
float throttle = 1f - u / Configs.U_MAX;        // clamp [0,1]
float ladder = Configs.dcaGridTotalWeight();    // = 1+1+3+8 = 13
return balanceBasic * Configs.F_BASE * throttle / ladder;   // F_BASE = 0.03
```

**(b) `SimulatorMarketLevelTicker1MStopLoss` dong 1195-1219** ? nhan tier roi nhan ratio bac:
```java
float tierMultiplier = CoinRankManager.getInstance().getBudgetMultiplier(symbolId);
budget *= tierMultiplier;                       // profile dat TIER_FLAT=1 => LUON = 1.00
...
float ratio = DcaUtils.gridLegWeightRatio(legIdx);
budget *= ratio;
```

**(c) `DcaUtils.gridLegWeightRatio` (dong 47-64)** ? voi `FIX_B2=true` thi **KHONG chia lai**:
```java
if (Configs.FIX_B2) return w * Configs.DCA_GRID_SCALE;      // w = DCA_GRID_WEIGHTS[legIdx]
return (w / total) * Configs.DCA_GRID_SCALE;                // nhanh cu (bug chia 2 lan)
```

=> **Cong thuc hop nhat:**

```
margin(bac i) = equity x F_BASE x throttle x tierMult x w[i] x DCA_GRID_SCALE / sum(w)
```

Gia tri THUC TE dang chay (doc tu `profiles/x1_gs_t170.properties` va cac `profiles/ds_*.properties`):

| Tham so | Gia tri | Nguon |
|---|---|---|
| `F_BASE` | 0.03 | `Configs.java:155` (khong profile nao override) |
| `U_MAX` | 0.60 | `Configs.java:156` |
| `DCA_GRID_WEIGHTS` | `1,1,3,8` -> sum = 13 | profile |
| `DCA_GRID_SCALE` | **19.5** | profile (`# --- SIZING ---`) |
| `TIER_FLAT` | 1 -> tierMult = 1.00 | profile + `CoinRankManager.java:117` |
| `LEVERAGE_ORDER` | 1 | `Configs.java:102` ? **khong don bay, khong thanh ly** |

Rut gon: `F_BASE x SCALE / sum(w) = 0.03 x 19.5 / 13 = 0.045`

```
margin(bac i) = equity x 4.5% x throttle x w[i]
```

### Margin tung bac theo % EQUITY (throttle = 1, tuc so con RONG)

| Bac | Muc gia kich hoat | w | % equity | Cong don |
|---|---|---|---|---|
| 0 (entry dau) | ? | 1 | **4.50%** | 4.50% |
| 1 | -50% | 1 | **4.50%** | 9.00% |
| 2 | -75% | 3 | **13.50%** | 22.50% |
| 3 | -90% | 8 | **36.00%** | **58.50%** |

**Con so 4.5% cua user la DUNG chinh xac** (`max_leg0_%eq` do duoc tren du lieu that: 4.54-4.71%,
sai lech nho vi equity lay theo anh chup cuoi ngay chu khong phai equity intraday luc dat lenh).

**"Leg cuoi 36% tai khoan" cung DUNG** ? bac 3 mot minh la 36% equity khi throttle = 1.

---

## 2. Tra loi truc tiep: "tong don vao 1 coin la bao nhieu %?"

Co **ba** con so khac nhau, dung lan la sai:

1. **Tran ly thuyet tuyet doi (throttle = 1 o moi bac): 58.50% equity.**
   Day la `equity x F_BASE x SCALE = 3% x 19.5`. Bang test `DcaGridScalarTest.clusterExposureIsBudgetTimesScale`
   khang dinh dung bat bien nay: *"cham day ladder => exposure cum = equity x F_BASE x SCALE"*.

2. **Tu hoi tiep throttle, so con lai RONG: 44.09% equity.**
   throttle giam dan vi `u = margin dang dung / equity` tang sau moi bac:
   ```
   bac0: throttle=1.0000  margin= 4.50%  cum= 4.50%
   bac1: throttle=0.9250  margin= 4.16%  cum= 8.66%
   bac2: throttle=0.8556  margin=11.55%  cum=20.21%
   bac3: throttle=0.6631  margin=23.87%  cum=44.09%
   ```

3. **Thuc te da xay ra (so day 8 vi the, throttle thap hon nhieu): cao nhat 39.17% equity.**

### Uoc tinh "~36%" cua master: TRUNG SO nhung SAI CO CHE

Master uoc "leg0 ~= 2.785% equity x 13 don vi ~= 36%". Con so ra gan dung nhung lap luan sai hai cho:

- **2.785% la TRUNG BINH da co throttle**, khong phai bac 0 danh dinh (4.50%).
- **Nhan 13 la sai**, vi throttle KHONG co dinh giua cac bac ? no tut xuong dung luc bac nang nhat
  (w=8) dat lenh. Nhan 13 gia dinh throttle dung yen.
- Trung hop con so: `2.785 x 13 = 36.2`, gan bang 36.0% ? nhung 36.0% la **rieng bac 3**, khong phai tong.

**Ket luan muc 2:** tran that la **58.5%** (so rong tuyet doi), **44.1%** (so rong co throttle),
**39.2%** (ky luc that trong 2021-2025). Khong phai 36%.

---

## 3. Doi chieu voi DU LIEU THAT ? cong thuc co khop khong?

Lay cum DUY NHAT cua T100 cham du 4 bac (CUDIS, 2025-11-05 -> 2025-11-12):

| bac | level | entry | margin (USD) | equity | % equity | throttle suy nguoc |
|---|---|---|---|---|---|---|
| 0 | PREDICT_SYMBOL_TRADE | 0.468 | 2,155.07 | 122,889 | 1.754% | 0.390 |
| 1 | DCA_LEVEL1 | 0.072 | 1,993.51 | 122,889 | 1.622% | 0.360 |
| 2 | DCA_LEVEL1 | 0.056 | 4,778.75 | 122,889 | 3.889% | 0.288 |
| 3 | DCA_LEVEL1 | 0.042 | **25,142.25** | 125,099 | **20.098%** | 0.558 |

throttle suy nguoc = `pct / (4.5 x w)`. Ca 4 bac deu ra throttle trong [0.29, 0.56] ? dung dai
hop ly cua mot so dang giu 8 vi the. **Cong thuc khop.**

Kiem chung ty le trong so tren cum GS100/AIA (2025-11-07), noi co ca leg-signal:

| bac grid | level | margin | % equity | throttle suy nguoc |
|---|---|---|---|---|
| 0 (x0.5 vi DCA_SIGNAL_BASE_RATIO) | PREDICT | 1,728.50 | 1.584% | 0.704 |
| leg-signal (x0.5, KHONG an bac) | PREDICT | 1,798.63 | 1.649% | 0.733 |
| 1 (w=1) | DCA_LEVEL1 | 2,905.73 | 2.663% | 0.592 |
| 2 (w=3) | DCA_LEVEL1 | 7,264.68 | 6.364% | 0.471 |

Dung nhu code: leg-signal **khong** an mot bac cua ladder (`gridLegCount` bo qua no), va leg mo cum
+ leg-signal moi cai chi an 50% suat co so.

---

## 4. Da tung xay ra THAT chua? Bao nhieu lan?

Dem tren 27 run da chay (dataset `wfo_ds_x1_2021`, 2021-07 -> 2025-12). "Bac" o day dem theo bac
GRID that (row dau = bac 0; moi row `DCA_LEVEL1` ke tiep = bac 1, 2, 3), da loai leg-signal.

| config | cum | >=bac1 | >=bac2 | **>=bac3** | max % equity 1 coin | max bac0 %eq | PnL cac cum bac3 |
|---|---|---|---|---|---|---|---|
| T100 | 2505 | 42 | 11 | **1** | 27.72% | 4.625% | -5,509 |
| T130 | 1549 | 22 | 8 | **1** | **39.17%** | 4.614% | **-12,400** |
| **T170 (INCUMBENT)** | 1069 | 16 | 4 | **0** | **8.71%** | 4.544% | 0 |
| T100_NOBD | 2323 | 0 | 0 | 0 | 4.63% | 4.625% | 0 |
| T130_NOBD | 1383 | 0 | 0 | 0 | 4.64% | 4.637% | 0 |
| T170_NOBD | 900 | 0 | 0 | 0 | 4.71% | 4.709% | 0 |
| GS100 | 2604 | 42 | 10 | 0 | 18.57% | 2.290% | 0 |
| GS120 | 1886 | 27 | 7 | 0 | 16.42% | 2.284% | 0 |
| GS140 | 1434 | 21 | 6 | 0 | 16.21% | 2.261% | 0 |
| GS085 | 3485 | 65 | 15 | **2** | 37.01% | 2.268% | -4,444 |
| GS070 | 5289 | 95 | 20 | **4** | 33.08% | 2.319% | -5,023 |
| GS055 | 9482 | 153 | 28 | **5** | 15.60% | 2.269% | -479 |
| K10_GS100 | 3037 | 43 | 13 | 0 | 18.57% | 2.303% | 0 |
| K12_GS100 | 3447 | 44 | 13 | 0 | 18.57% | 2.312% | 0 |
| DCA20_GS100 | 2579 | 41 | 10 | 0 | 18.57% | 2.282% | 0 |
| DCA25_GS100 | 2571 | 41 | 10 | 0 | 18.57% | 2.284% | 0 |
| DCA30_GS100 | 2563 | 39 | 9 | 0 | 18.57% | 2.284% | 0 |
| DCA5/8/12_T170 | ~1101 | 17 | 3 | 0 | 7.86-7.87% | 2.256% | 0 |
| DCA30/40/50_T170 | ~1081 | 17 | 3 | 0 | 8.15-9.14% | 2.256% | 0 |
| X2H_V1 | 2066 | 26 | 8 | 0 | 8.43% | 2.284% | 0 |
| X2H_V2 | 2533 | 31 | 9 | 0 | 7.84% | 2.290% | 0 |
| X2H_V3 | 2087 | 26 | 8 | 0 | 8.74% | 2.281% | 0 |
| REGIME | 1781 | 24 | 5 | 0 | 20.13% | 4.625% | 0 |

### Toan bo 13 cum tung cham BAC 3 (-90%, w=8) trong lich su 2021-2025

| config | coin | ngay mo | rows | tong margin | equity | **% equity** | **PnL (USD)** |
|---|---|---|---|---|---|---|---|
| T100 | CUDIS | 2025-11-05 | 4 | 34,070 | 122,889 | 27.72% | **-5,509** |
| T130 | AIA | 2025-11-07 | 4 | 41,222 | 105,243 | **39.17%** | **-12,400** |
| GS085 | LUNA | 2022-05-11 | 4 | 2,411 | 38,672 | 6.23% | +854 |
| GS085 | PUMPBTC | 2025-09-23 | 4 | 31,300 | 84,580 | 37.01% | **-5,298** |
| GS070 | AIA | 2025-10-09 | 5 | 7,144 | 58,498 | 12.21% | +870 |
| GS070 | ANC | 2022-05-09 | 5 | 3,684 | 38,609 | 9.54% | -2,281 |
| GS070 | LUNA | 2022-05-11 | 5 | 643 | 35,933 | 1.79% | -3 |
| GS070 | PUMPBTC | 2025-09-23 | 5 | 20,807 | 62,899 | 33.08% | **-3,610** |
| GS055 | AIA | 2025-10-09 | 5 | 2,695 | 56,274 | 4.79% | +240 |
| GS055 | ANC | 2022-05-09 | 5 | 3,631 | 42,301 | 8.58% | +154 |
| GS055 | BAS | 2025-10-19 | 5 | 8,482 | 54,382 | 15.60% | +688 |
| GS055 | LUNA | 2022-05-11 | 5 | 1,439 | 39,384 | 3.65% | +59 |
| GS055 | PUMPBTC | 2025-09-23 | 5 | 8,208 | 56,752 | 14.46% | -1,621 |

**Tong: 13 cum. 6 thang / 7 thua. Tong PnL = -27,857 USD.**

(rows = 5 o cac run GS* vi co them 1 leg-signal khong an bac grid.)

---

## 5. Tra loi thang cau hoi cua user

**"Entry vao da 4.5% roi?"** ? DUNG. Bac 0 = 4.50% equity khi so rong; thuc te trung binh 2.5-2.8%
vi throttle.

**"Leg cuoi tan 40% tai khoan a?"** ? Gan dung, va con hon the. Bac cuoi mot minh = **36.0% equity**
o throttle=1; tong ca 4 bac = **58.5%** (tran ly thuyet) / **44.1%** (co throttle, so rong).
Trong lich su that, ky luc la **T130/AIA 2025-11-07: 41,222 USD tren equity 105,243 = 39.17% equity
dat vao MOT coin**.

**"Dinh 1 coin chet la teo?"** ? Can tach hai y:

- **Khong "teo" theo nghia chay tai khoan.** `LEVERAGE_ORDER = 1`, khong don bay, khong thanh ly.
  Coin ve 0 thi mat dung phan margin da dat, khong am tai khoan. Va khi bac 3 no thi vi the da
  -90% roi, nen phan von bo them dang mua o ~1/10 gia goc.
- **Nhung mat mat la THAT va LON.** Cum T130/AIA lo **-12,400 USD**, tuc **-11.8% equity chi tu
  mot coin, trong mot cum**. Cum T100/CUDIS lo -5,509 (-4.5% equity). Ca hai deu `STOP_LOSS_DONE`
  toan bo cac bac.
- **Va co che nay TINH TRUNG BINH la LO, khong phai cuu.** 13 lan cham bac 3 -> 6 thang 7 thua,
  tong **-27,857 USD**. Noi cach khac: bac -90% khong phai "bat day cuu lenh", no la cho nhoi
  nhieu von nhat vao dung nhung coin da mat 90% gia tri.

**Rui ro nay la LY THUYET hay THUC TE?** ? Ca hai, tuy config:

- **Voi T170 (incumbent dang dung): THUC TE CHUA BAO GIO XAY RA.** 0/1069 cum cham bac 3;
  chi 4 cum cham bac 2; tap trung toi da vao 1 coin la **8.71% equity**. Gate chat 1.70 loc bot
  dung nhung lenh sau nay se roi -50/-75/-90%.
- **Voi cac config gate LONG hon thi NO XAY RA THAT** va dung vao dung luc xau: GS070 va GS055
  deu cham bac 3 nhieu lan, va ca hai la nhung config co 2025 am nang nhat (-18.58% va -37.55%)
  trong master table. GS085/PUMPBTC dat 37.01% equity vao 1 coin roi lo -5,298.
- **T130 la canh bao ro nhat**: chi 1 lan cham bac 3 trong 5 nam, nhung dung 1 lan do da ngon
  **39.17% equity** va tra ve **-12,400 USD**.

---

## 6. Gioi han phuong phap (phai ghi ro)

1. `equity` lay tu dong `Update <ngay> 07:00 => b:... unP:...` trong `sim.out`, tuc **anh chup
   cuoi ngay**, khong phai equity intraday dung luc dat lenh. Vi vay `% equity` co sai so nho
   (chinh la ly do `max_leg0_%eq` do duoc 4.625% > 4.500% danh dinh).
2. Bac grid duoc suy tu `printDone.csv` (row dau = bac 0, moi row `DCA_LEVEL1` ke tiep = bac ke tiep),
   khong phai doc truc tiep tu bien `legCount` trong sim. Da doi chieu cheo bang ty le margin
   1 : 1 : 3 : 8 va bang crosstab `leg x level` ? khop.
3. `throttle` la so suy nguoc tu `margin / (4.5% x w)`, khong phai so log truc tiep. Dung de kiem
   tra tinh nhat quan, khong dung lam so cong bo.
4. Khong chay lai sim nao. Moi so den tu artifact da co tren dia.
