# DIAG — CO CHE TRIGGER BIG_DOWN hien tai + do du lieu cho huong "nguong thich ung"

> **Tai lieu DISCOVERY/DESCRIPTIVE.** Khong pre-reg, khong sua mot dong `.java` nao, khong them
> flag, **khong chay sim moi**. Moi so lay tu code trong repo (branch `module`) + du lieu da co
> (`wfo_ds_x1_2021/market.bin`, `regime_work/btc_daily_close.csv`, `printDone.csv` cua baseline
> T170 `efb793e2...`).
>
> **Tai lieu KHONG de xuat nguong, KHONG de xuat cong thuc, KHONG ket luan "nen chon cai nao".**
> Viec chon la quyet dinh pre-reg cua MASTER. Muc 5 chi ghi cac RUI RO KY THUAT cua huong di.

---

## 0. Tom tat mot dong (de doc nhanh)

"BIG_DOWN" hien tai **khong phai** "gia mot coin giam X% so voi dinh N gio". No la mot **thong ke
CAT NGANG TOAN THI TRUONG tren DUNG MOT NEN 1 PHUT**: trung binh muc giam cua **100 coin giam
manh nhat trong phut do** thap hon mot hang so **`-0.03157`**. Lookback = **1 phut**, khong EMA,
khong rolling high.

---

## 1. Cong thuc CHINH XAC cua "big down" hien tai

### 1.1 Dieu kien kich hoat — `MarketBigChangeDetector.getMarketStatus1M` (dong 174-186)

```java
public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg,
                                                  Float rateDown15MAvg) {
    // 2026-09-03: co OFF_FLAT_HARD da go -> chi con MOT nhanh song la BIG_DOWN
    if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) {      // dong 179
        return MarketLevelChange.BIG_DOWN;             // dong 180
    }
    return null;                                       // dong 185
}
```

**Chi MOT bieu thuc.** `rateUpAvg` va `rateDown15MAvg` duoc truyen vao nhung **khong duoc dung**
o nhanh nay nua (BIG_UP / SMALL_UP / SMALL_DOWN_15M da bi xoa 2026-09-03).

### 1.2 `rateDownAvg` la gi — `calMarketData` (dong 48-95) + `calRateChangeAvg` (dong 149-167)

```java
Float rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);  // dong 67
rateDown2Symbols.put(rateChange, symbol);                                     // dong 75 (TreeMap TANG dan)
...
Float rateChangeDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 100); // dong 86
```

`calRateChangeAvg(map, 100)` duyet TreeMap tu **khoa NHO NHAT** (am nhat) va lay trung binh
**100 phan tu dau** (dong 155-166); neu universe nho thi `period` bi ep xuong `size*4/5`
(dong 152-154).

=> **`rateDownAvg` = trung binh return cua 100 coin GIAM MANH NHAT trong DUNG nen 1 phut hien tai**
(`priceClose/priceOpen - 1` cua chinh nen do). **Khong so voi dinh N gio, khong so voi tick truoc,
khong EMA.**

Ba bo loc truoc khi vao thong ke:

| dong | loc | muc dich |
|---|---|---|
| 63-65 | bo `Constants.diedSymbol` | coin da chet |
| 69-71 | bo coin co `rateChange < -0.15` khi `rateChangeBtc > -0.004` | loai dump rieng le (delist/warning) khi BTC khong giam |
| 72-74 | bo coin co `rateChange > 0.3` | loai pump bat thuong |

### 1.3 Nguong X hien tai + flag

| | |
|---|---|
| Hang so | **`Configs.MS_DOWN_BIG_AVG = -0.03157f`** — `Configs.java:380` |
| Override | `SIM_MS_DOWN_BIG_AVG` — `Configs.java:604` (`if ((v = Cfg.get("SIM_MS_DOWN_BIG_AVG")) != null) MS_DOWN_BIG_AVG = Float.parseFloat(v);`) |
| Profile T170/T130/T100 | **KHONG khai bao key nay** => deu chay hang so `-0.03157` |
| La gene HPO | co, o 3 noi: `WFORunner.java:67` range `[-0.055, -0.020]`; `StrategyWfoTask.java:74` range `[-0.060, -0.025]`; `SensitivityTool.java:69` range `[-0.060, -0.020]` |

**CO DINH. Khong co bat ky dang thich ung nao** (da doc het `MarketBigChangeDetector.java` 307
dong — khong co bien trang thai, khong co lich su, khong co tham so thoi gian truyen vao
`getMarketStatus1M`).

### 1.4 Lookback window — chi co MOT cho co rolling, va no KHONG dung cho BIG_DOWN

| bien | lookback | dung o dau |
|---|---|---|
| `rateDownAvg` | **1 nen 1 phut** (close vs open cua chinh nen do) | **quyet dinh BIG_DOWN** |
| `rateUpAvg` | 1 nen 1 phut | khong con nhanh nao dung |
| `rateDown15MAvg` | **rolling high 15 nen 1m**: `close / max(maxPrice cua 15 nen gan nhat) - 1`, voi `Configs.NUMBER_TICKER_CAL_RATE_CHANGE = 15` (`Configs.java:107`; vong lap `ExportMarketData2File.java:111-128` va `DetectEntrySignal2TradeNormal.java:195-206`) | **CHI dung cho `isDcaAlt`**, khong dung cho BIG_DOWN |

`isDcaAlt` (dong 188-191) — nhanh DCA, **dung lai CHINH hang so cua BIG_DOWN**:

```java
public static boolean isDcaAlt(Float rateDown15MAvg, Float rateDownAvg, Float rateUpAvg) {
    return rateDown15MAvg < Configs.MS_DOWN_BIG_AVG
            || rateDownAvg < Configs.MS_DOWN_BIG_AVG / 3;
}
```

### 1.5 `getTopSymbolArray` chon coin theo tieu chi gi — **KHONG phai theo do sau cu giam**

`MarketBigChangeDetector.getTopSymbolArray` (dong 123-146) chi lam ba viec: duyet `predict2Symbol`
theo thu tu TreeMap, bo `symbolLocked`, dung khi du `period` phan tu.

Nguon `predict2Symbol` — `SimulatorMarketLevelTicker1MStopLoss.java:319` goi
`extractPredict2Symbol(time2SymbolPred.get(time))`, va ham do (dong 733-740) lam
`predict2Symbol.put(pred, symbolId)` voi `pred` = **score selector pNoPump**. `TreeMap<Float,...>`
sap **TANG dan** => `getTopSymbolArray` lay cac coin co **pNoPump THAP NHAT** (= de pump nhat theo
selector).

| cau hoi | tra loi |
|---|---|
| Sap theo muc giam sau nhat? | **KHONG.** Sap theo score selector pNoPump tang dan. |
| `numberOrder` bang bao nhieu? | `Configs.NUMBER_ENTRY_EACH_SIGNAL = 2` (`Configs.java:106`). Voi `SMALL_UP`/`SMALL_DOWN_15M` thi `/2`, nhung hai level do **da chet** nen thuc te luon = **2 coin/tick**. |
| `symbolLocked` | toan bo symbol dang co vi the (`Simulator...:311`) => BIG_DOWN chi mo vi the MOI |

**Kiem chung bang so lieu:** trong 4.5 nam co **124 phut** thoa `rateDownAvg < -0.03157`; baseline
T170 co **248 leg BIG_DOWN**. `124 x 2 = 248` — **khop tuyet doi**. Tuc **moi phut trigger deu mo
dung 2 leg, khong hut mot phut nao** (leg BIG_DOWN bo qua `EntryGate` o `createOrder:1122`).

### 1.6 He thong hien co dung "bien dong thi truong chung" o dau khong?

| co che | co dung khong | chi tiet |
|---|---|---|
| **`EntryGate.GATE_REGIME_ADAPTIVE` + `RegimeSchedule`** (`docs/prereg/PREREG_REGIME_GATE.md`) | **CO — nhung la XU HUONG, khong phai BIEN DONG** | `RegimeSchedule` nap CSV daily; `regime_build.py` tinh `ret30 = close[D-1]/close[D-31] - 1` (BTC), `UP` neu `ret30 > 0`. Map sang HANG SO `REGIME_SCALE_UP=1.00` / `REGIME_SCALE_NOTUP=1.70` (`EntryGate.java:63-65`). `scaleForTime` dung `floorEntry` => **causal**, khong lookahead. |
| Pham vi ap dung cua regime | **CHI nhanh dyn** | `EntryGate.threshold` dong 80: `if (symbolPred == null) return thrBase;` — **truoc** khi dung `CURRENT_REGIME_SCALE` (dong 82-83). Leg BIG_DOWN va DCA co `symbolPred == null` => **regime KHONG he cham toi BIG_DOWN**. |
| Mac dinh | **OFF** (`EntryGate.java:61 GATE_REGIME_ADAPTIVE = false`) | |
| Do bien dong (std/ATR/realized vol) o bat ky dau | **KHONG TIM THAY** | grep toan `src/main/java`: khong co rolling std / ATR / realized-vol / percentile nao tham gia quyet dinh giao dich. |
| `GATE_DYN_SCALE` | **KHONG theo bien dong** | la MOT hang so doc mot lan tu `SIM_GATE_DYN_SCALE` (`EntryGate.java:58`), nhan vao `dyn_thr`. |

**Ket luan muc 1.6: co san MOT khung "adaptive theo lich ngay" (`RegimeSchedule`) da duoc kiem
causal va da co pre-reg rieng — nhung no do XU HUONG BTC 30 ngay, khong do BIEN DONG, va no
KHONG cham vao duong BIG_DOWN.**

---

## 2. Phuong phap do (Phan 2) — nguon va rang buoc causal

| | |
|---|---|
| Nguon chinh | `/home/ubuntu/wfo_ds_x1_2021/market.bin` — **dung file sim doc**. Dinh dang: `int n` roi `n` ban ghi 20B big-endian `long ts \| float rateDownAvg \| float rateUpAvg \| float rateDown15MAvg` (`WfoDataset.java:339-348 / 371-382`). n = **2,554,812** phut, span `2021-01-01 00:00 -> 2025-12-31 23:59` UTC. |
| Cua so phan tich | UTC-day `2021-07-01 .. 2025-12-31` = **1645 ngay**, **2,301,233 phut** |
| BTC daily | `/home/ubuntu/regime_work/btc_daily_close.csv` (1706 ngay tu 2021-05-01), chinh file `RegimeSchedule` dung |
| Leg BIG_DOWN that | `printDone.csv` cua `CC_OFF_T170` (md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089) — cot `level == BIG_DOWN`. Gio trong file la **local GMT+7** (`java -Duser.timezone=Asia/Ho_Chi_Minh`), da tru 7h ve UTC truoc khi gop ngay. |
| **Rang buoc KHONG LOOKAHEAD** | Moi rolling stat cua ngay `D` chi dung du lieu cua cac ngay **`D-N .. D-1`**, **khong gom ngay `D`**. `vol7/vol30` = `std(return ngay, ddof=1)`; `disp7/disp30` = trung binh `dispDaily` cua N ngay truoc. |
| Script | `/tmp/bd_diag.py`, `/tmp/bd_diag2.py` tren Oracle (read-only, **khong commit vao repo** — cung quy uoc `docs/diag/DIAG_DCA_CONCURRENCY.md` muc 7.6) |

**Ve "cross-sectional dispersion cua alt":** `docs/diag/DIAG_UW_WINDOW_202503_202510.md` **KHONG co logic
nay de tai su dung** — muc 2 cua tai lieu do ghi ro gioi han: *"Dung mot chi so alt equal-weight
that su thi phai doc lai ticker nhi phan bang Java (ngoai pham vi 'doc du lieu san')"*. Vi vay o
day dung **proxy san co trong chinh `market.bin`**:

```
dispDaily[D] = trung binh trong ngay cua  (rateUpAvg - rateDownAvg)
```

tuc **khoang cach giua trung binh 100 coin tang manh nhat va 100 coin giam manh nhat trong cung
mot phut** — dung nghia "do phan tan cat ngang cua alt", tinh tu chinh thong ke he thong dang
dung, khong phai uoc luong moi. `disp7/disp30` = trung binh causal cua `dispDaily` 7/30 ngay truoc.

---

## 3. KET QUA DO

### 3.1 Phan phoi cac candidate "bien dong gan day" (causal, 2021-07-01..2025-12-31)

| candidate | n ngay | min | p10 | p25 | **p50** | p75 | p90 | p99 | max | mean |
|---|---|---|---|---|---|---|---|---|---|---|
| **vol7** (std return ngay BTC, 7 ngay truoc) | 1645 | 0.003100 | 0.011457 | 0.016474 | **0.022932** | 0.031792 | 0.042022 | 0.061724 | 0.083731 | 0.025139 |
| **vol30** (std return ngay BTC, 30 ngay truoc) | 1645 | 0.008760 | 0.016221 | 0.020376 | **0.025540** | 0.033213 | 0.038875 | 0.047767 | 0.052277 | 0.026957 |
| **disp7** (dispersion alt, 7 ngay truoc) | 1642 | 0.000522 | 0.000664 | 0.000786 | **0.001127** | 0.002101 | 0.002995 | 0.004547 | 0.005700 | 0.001560 |
| **disp30** (dispersion alt, 30 ngay truoc) | 1630 | 0.000566 | 0.000701 | 0.000804 | **0.000997** | 0.002087 | 0.002946 | 0.004347 | 0.004596 | 0.001545 |

**vol7 vs vol30:** spearman **+0.6255**; ti le `vol7/vol30` p10=0.516 / p50=0.900 / p90=1.396;
so ngay `vol7 > 2 x vol30` = **1 / 1645 (0.06%)**. Tuc vol7 dao manh hon vol30 nhung khong bung no.

### 3.2 Phan phoi cac bien phu thuoc (theo ngay)

| bien | min | p10 | p25 | p50 | p75 | p90 | p99 | max | mean |
|---|---|---|---|---|---|---|---|---|---|
| `nTrigMin` (so phut BIG_DOWN trong ngay) | 0 | 0 | 0 | **0** | 0 | 0 | 2 | **28** | 0.0754 |
| `depthMin` (`rateDownAvg` am nhat trong ngay) | -0.354162 | -0.016327 | -0.010256 | **-0.007316** | -0.005589 | -0.004307 | -0.002613 | -0.001706 | -0.010200 |
| `dispDaily` | 0.000482 | 0.000648 | 0.000778 | **0.001164** | 0.002113 | 0.003051 | 0.004478 | 0.009801 | 0.001565 |

### 3.3 Phan phoi cua CHINH bien bi so sanh voi nguong (`rateDownAvg`, muc 1-phut, n=2,301,233)

| p0 (min) | p0.01 | p0.1 | p0.5 | p1 | p5 | p25 | p50 | p75 | p99 | p100 |
|---|---|---|---|---|---|---|---|---|---|---|
| -0.354162 | **-0.022283** | -0.008814 | -0.005557 | -0.004597 | -0.002836 | -0.001366 | -0.000647 | -0.000079 | +0.002117 | +0.038274 |

mean = -0.000782, std = 0.001376.
**% phut < `-0.03157` = 0.00539% (124 phut / 4.5 nam).** Nguong hien tai nam **thap hon ca p0.01**
cua phan phoi — tuc no bat mot su kien hiem hon 1/10,000 phut.

Doi chieu `rateDown15MAvg` (bien cua `isDcaAlt`): p0.01 = -0.107624, p0.1 = -0.040281,
p1 = -0.021841; **% phut < `-0.03157` = 0.23144%** (gap **43x** so voi `rateDownAvg`).

### 3.4 Trigger theo nam

| nam | so phut | so phut trigger | ti le | `rateDownAvg` am nhat trong nam |
|---|---|---|---|---|
| 2021 (tu 07-01) | 257,613 | 16 | 0.00621% | -0.06776 |
| 2022 | 510,528 | **10** | 0.00196% | -0.04971 |
| 2023 | 510,767 | 25 | 0.00489% | -0.10706 |
| 2024 | 511,798 | 35 | 0.00684% | -0.13720 |
| 2025 | 510,527 | **38** | 0.00744% | **-0.35416** |

Tong: **124 phut trigger / 56 ngay** co it nhat 1 trigger (tren 1645 ngay = **3.4% so ngay**).
T170: **248 leg BIG_DOWN** tren **56 ngay** — khop `124 x 2`.

### 3.5 Quantile TRAILING 30 NGAY (causal) cua `rateDownAvg`

Voi moi ngay `D`, tinh quantile tren TOAN BO phut cua 30 ngay TRUOC `D` (khong gom `D`):

| quantile trailing-30d | min | p10 | p25 | **p50** | p75 | p90 | max | % ngay ma quantile do < `-0.03157` |
|---|---|---|---|---|---|---|---|---|
| p0.01 | -0.12182 | -0.03509 | -0.02583 | **-0.01634** | -0.01363 | -0.01112 | -0.00768 | **16.1%** |
| p0.1 | -0.02509 | -0.01088 | -0.00930 | **-0.00763** | -0.00663 | -0.00584 | -0.00411 | **0.0%** |
| p1.0 | -0.00764 | -0.00580 | -0.00494 | **-0.00408** | -0.00344 | -0.00265 | -0.00197 | **0.0%** |

Doc mo ta: nguong co dinh `-0.03157` nam **sau hon** trailing-30d p0.01 o **83.9%** so ngay, va
**luon** sau hon trailing-30d p0.1 / p1.0. (Day la MO TA vi tri tuong doi, **khong** phai de xuat
thay `-0.03157` bang bat ky quantile nao.)

### 3.6 Tuong quan — bien dong gan day vs tan suat/do sau BIG_DOWN

n = 1630-1645 ngay. Luu y: `legBigDown = 2 x nTrigMin` **chinh xac** (muc 1.5) nen spearman cua no
**bang het** spearman cua `nTrigMin`.

| candidate | vs `nTrigMin` | vs `depthMin` | vs `hasTrig` (ngay co >=1 trigger) |
|---|---|---|---|
| **vol7** | spearman **-0.0400** / pearson -0.0249 | spearman -0.1289 / pearson +0.0052 | spearman -0.0402 / pearson -0.0386 |
| **vol30** | spearman **-0.0499** / pearson -0.0367 | spearman -0.0630 / pearson +0.0391 | spearman -0.0505 / pearson -0.0585 |
| **disp7** | spearman **+0.0219** / pearson +0.0402 | spearman **-0.1686** / pearson -0.0951 | spearman +0.0217 / pearson +0.0145 |
| **disp30** | spearman **+0.0033** / pearson +0.0356 | spearman -0.1326 / pearson -0.0793 | spearman +0.0031 / pearson +0.0012 |

(`depthMin` cang AM cang sau, nen spearman AM = bien dong cao di kem ngay co day SAU hon.)

### 3.7 Bang quintile (mo ta)

**Theo `vol7`** — cut `[0.014573, 0.020520, 0.025591, 0.034240]`

| bucket | nDay | trigMin/ngay | % ngay co trig | med `depthMin` | legBD/ngay | tong legBD |
|---|---|---|---|---|---|---|
| Q1 (yen nhat) | 329 | 0.055 | 4.0% | -0.00687 | 0.109 | 36 |
| Q2 | 329 | **0.170** | 4.9% | -0.00708 | 0.340 | **112** |
| Q3 | 329 | 0.049 | 2.7% | -0.00712 | 0.097 | 32 |
| Q4 | 329 | 0.052 | 2.7% | -0.00744 | 0.103 | 34 |
| Q5 (bien dong nhat) | 329 | 0.052 | 2.7% | **-0.00815** | 0.103 | 34 |

**Theo `vol30`** — cut `[0.019041, 0.023549, 0.028152, 0.035013]`

| bucket | nDay | trigMin/ngay | % ngay co trig | med `depthMin` | legBD/ngay | tong legBD |
|---|---|---|---|---|---|---|
| Q1 | 329 | **0.122** | 3.0% | -0.00697 | 0.243 | **80** |
| Q2 | 329 | 0.076 | 5.5% | -0.00748 | 0.152 | 50 |
| Q3 | 329 | 0.073 | 4.6% | -0.00729 | 0.146 | 48 |
| Q4 | 329 | 0.064 | 2.1% | -0.00747 | 0.128 | 42 |
| Q5 | 329 | **0.043** | 1.8% | -0.00744 | 0.085 | **28** |

**Theo `disp7`** — cut `[0.000750, 0.000915, 0.001557, 0.002522]`

| bucket | nDay | trigMin/ngay | % ngay co trig | med `depthMin` | legBD/ngay | tong legBD |
|---|---|---|---|---|---|---|
| Q1 | 329 | 0.027 | 2.4% | -0.00661 | 0.055 | 18 |
| Q2 | 328 | 0.104 | 4.3% | -0.00710 | 0.207 | 68 |
| Q3 | 328 | 0.034 | 2.1% | -0.00703 | 0.067 | 22 |
| Q4 | 328 | 0.091 | 5.5% | -0.00716 | 0.183 | 60 |
| Q5 | 329 | **0.122** | 2.7% | **-0.00854** | 0.243 | **80** |

**Theo `disp30`** — cut `[0.000772, 0.000911, 0.001559, 0.002466]`

| bucket | nDay | trigMin/ngay | % ngay co trig | med `depthMin` | legBD/ngay | tong legBD |
|---|---|---|---|---|---|---|
| Q1 | 326 | 0.074 | 4.3% | -0.00700 | 0.147 | 48 |
| Q2 | 326 | 0.043 | 2.1% | -0.00704 | 0.086 | 28 |
| Q3 | 326 | 0.052 | 3.1% | -0.00682 | 0.104 | 34 |
| Q4 | 326 | 0.092 | 5.2% | -0.00727 | 0.184 | 60 |
| Q5 | 326 | **0.120** | 2.5% | **-0.00846** | 0.239 | **78** |

### 3.8 Doc bang tren (MO TA, khong suy luan)

1. **Tan suat trigger gan nhu KHONG co quan he don dieu voi bien dong BTC** (|spearman| <= 0.05
   voi ca vol7 va vol30). Voi `vol7`, so trigger tap trung o **Q2** chu khong o Q5.
2. **Voi `vol30`, huong lai NGUOC voi truc giac**: Q1 (BTC yen nhat 30 ngay) co **80** leg
   BIG_DOWN, Q5 (bien dong nhat) chi **28**.
3. **`dispersion` co huong don dieu hon** (Q5 cao nhat ca ve trigMin/ngay lan tong legBD, o ca
   disp7 lan disp30) nhung do lon van rat nho (spearman ~ +0.02 / +0.003).
4. **Quan he ro nhat — nhung van yeu — la voi DO SAU, khong phai tan suat**: `disp7` vs
   `depthMin` spearman **-0.1686** (dispersion cao => day trong ngay sau hon). Voi BTC vol thi
   `vol7` vs `depthMin` chi -0.1289 va `pearson` gan 0.
5. **Co so mau rat mong**: toan bo lich su 4.5 nam chi co **124 phut** trigger tren **56 ngay**.
   Moi thong ke o muc 3.6-3.7 deu dua tren 56 ngay "co su kien".

---

## 4. Nhung gi tai lieu nay **KHONG** tra loi

- **Khong** noi nguong nao tot hon nguong nao.
- **Khong** noi nen dung `vol7`, `vol30`, `disp7`, `disp30` hay quantile nao.
- **Khong** do hieu qua P&L cua bat ky bien the nao (khong chay sim).
- Moi so o muc 3 deu tinh tren **DEV 2021-07..2025-12** — cung cua so da sinh ra moi gia thuyet
  truoc day. Bat ky tham so nao chon tu day deu **da bi nhiem**; xac nhan that chi co o holdout.

---

## 5. RUI RO KY THUAT cua huong "rolling threshold" (phat hien khi doc code)

### 5.1 `MS_DOWN_BIG_AVG` KHONG chi dieu khien BIG_DOWN — no con dieu khien nhanh DCA

`isDcaAlt` (dong 188-191) dung **chinh hang so do**: `rateDown15MAvg < MS_DOWN_BIG_AVG` HOAC
`rateDownAvg < MS_DOWN_BIG_AVG / 3`. Nhanh nay chay o `Simulator...:357` (va live `:313`) va la
**mot trong hai cua vao cua DCA-grid**.

=> Doi hang so / lam no thich ung ma khong tach bien => **doi luon tan suat DCA**. Muon chi doi
BIG_DOWN thi **bat buoc phai tach `MS_DOWN_BIG_AVG` thanh hai duong rieng** (mot cho
`getMarketStatus1M`, mot cho `isDcaAlt`), va viec tach do **tu no la mot thay doi hanh vi can
parity gate rieng**.

Ghi chu do luong: `rateDown15MAvg` cham nguong `-0.03157` o **0.23144%** so phut, con `rateDownAvg`
chi **0.00539%** — tuc nhanh `isDcaAlt` nhay hon **43 lan**. Sua nham cho se doi rat nhieu.

### 5.2 `getMarketStatus1M` dung CHUNG sim va LIVE

| noi goi | file:dong |
|---|---|
| SIM | `research/SimulatorMarketLevelTicker1MStopLoss.java:307` |
| **LIVE** | `trading/DetectEntrySignal2TradeNormal.java:225` |
| Export/diagnostic | `research/ExportMarketData2File.java:133` |

Ham hien tai la **`static`, thuan, khong co tham so thoi gian, khong co trang thai**. Mot nguong
rolling **bat buoc** phai them (a) tham so `time`, hoac (b) trang thai cap class. Ca hai deu cham
vao duong LIVE. Them nua, LIVE **tu tinh** `rateDownAvg` tu ticker trong RAM (`:190-222`), con SIM
**doc lai gia tri da tinh san** tu `market.bin` — hai duong nap du lieu khac nhau, nen mot
implementation rolling phai duoc viet sao cho ca hai cho ra cung ket qua (day dung la loai loi ma
`docs/audit/AUDIT_GATE_DYN_PARITY.md` da tung ghi nhan: hai ban sao cua cung mot cong troi khoi nhau).

### 5.3 KHONG duoc dong vao `calMarketData` — no la duong sinh FEATURE cho model

`calMarketData` con duoc goi boi `ai_ml/features/export/MarketDataInlineGenerator.java:104` (sinh
feature cho model ML) va 3 comparator `ProductionVsBacktest*`. Doi `calMarketData` = **doi feature
dau vao cua model** => phai retrain + pha moi parity hien co. Nguoc lai, doi **rieng**
`getMarketStatus1M` thi khong cham feature. (Day la ranh gioi an toan can giu.)

### 5.4 Du lieu dau vao cho rolling stat: SIM chi co 3 float/phut

`market.bin` chi luu `rateDownAvg / rateUpAvg / rateDown15MAvg` (`WfoDataset.java:345`). Trong sim,
o thoi diem quyet dinh market-level, **khong co gia tung coin**. Nen moi thong ke rolling phai
suy tu **chinh chuoi 3 float do** (kha thi — muc 3.5 da lam duoc) **hoac** tu mot file phu nap
ngoai kieu `RegimeSchedule` (da co tien le, causal, da qua pre-reg rieng).

### 5.5 `MS_DOWN_BIG_AVG` dang la GENE HPO o 3 noi

`WFORunner.java:67`, `StrategyWfoTask.java:74`, `SensitivityTool.java:69`. Neu no tro thanh dai
luong dan xuat (khong con hang so), cac danh sach gene tren se **set mot field khong con tac dung**
— dung loai "loi im lang" ma comment o `DcaUtils.java:34-37` da canh bao tung xay ra.

### 5.6 Mot dac diem co the lam huong nay kem hieu qua hon ky vong

`rateDownAvg` **da la mot dai luong CAT NGANG duoc chuan hoa mot phan**: no la trung binh cua 100
coin giam manh nhat **cung mot phut**. Trong phien bien dong cao, ca `rateUpAvg` lan `rateDownAvg`
cung gian ra (do la ly do `dispDaily = rateUpAvg - rateDownAvg` dung duoc lam thuoc do bien dong o
muc 2). Tuc **mot phan cua "chuan hoa theo bien dong" da nam san trong dinh nghia**. Do la mot cach
giai thich kha di cho viec muc 3.6 do duoc |spearman| <= 0.05 — **nhung day chi la gia thuyet mo ta,
chua kiem chung, khong duoc dung lam can cu quyet dinh.**

### 5.7 Mau su kien qua mong de calibrate

124 phut / 56 ngay tren 4.5 nam. Mot nguong rolling co them **it nhat 2 tham so moi** (cua so N +
muc quantile/he so). Voi 56 ngay co su kien, moi bo tham so se roi vao vung **rat de overfit** —
va ca 3 gate T100/T130/T170 deu cho **cung 248 leg BIG_DOWN** (`docs/diag/DIAG_DCA_CONCURRENCY.md` muc 6),
nen khong the dung gate lam bien doi chung doc lap.

---

## 6. Artifact

| | |
|---|---|
| Script do (khong commit) | `/tmp/bd_diag.py`, `/tmp/bd_diag2.py` tren Oracle; output `/tmp/bd_out.txt`, `/tmp/bd_out2.txt`, `/tmp/bd_diag.json` |
| Du lieu | `/home/ubuntu/wfo_ds_x1_2021/market.bin`, `/home/ubuntu/regime_work/btc_daily_close.csv`, `/home/ubuntu/java/devrun/CC_OFF_T170/storage/printDone.csv` |
| Baseline T170 | md5 `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089, 248 leg BIG_DOWN |
| File code da doc | `MarketBigChangeDetector.java` (307 dong, doc het), `Configs.java`, `EntryGate.java`, `RegimeSchedule.java`, `DcaProcessor.java`, `DcaUtils.java`, `SimulatorMarketLevelTicker1MStopLoss.java`, `DetectEntrySignal2TradeNormal.java`, `ExportMarketData2File.java`, `WfoDataset.java` |
