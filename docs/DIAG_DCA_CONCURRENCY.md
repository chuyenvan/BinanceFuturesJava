# DIAG — DCA "vao o at": bao nhieu coin cung lun sau MOT LUC (concurrency)

> **Tai lieu SU THAT/RUI RO (descriptive), KHONG phai thi nghiem.** Khong pre-reg, khong doi
> tham so, khong chay sim moi — moi so lay tu code trong repo (branch `module`) + artifact
> `printDone.csv` / `logs/sim.out` cua cac run DA CHAY tren dataset chuan `wfo_ds_x1_2021`.
> Tai lieu KHONG de xuat nguong cap — viec chon nguong la quyet dinh pre-reg cua MASTER.

Cau hoi goc (user): *"DCA vao o at — nhieu coin cung lun sau mot luc thi tong von bi khoa la
bao nhieu?"* — khac cau hoi cua `docs/DIAG_BIGDOWN_CONCENTRATION.md` (do PER-COIN: 1 coin nhoi
het luoi = 58.5% tran ly thuyet / 39.2% ky luc that). Day do **AGGREGATE toan so**.

---

## 0. Pham vi & nguon so lieu

| | |
|---|---|
| Baseline chinh | **T170** (`GATE_DYN_SCALE=1.70`, INCUMBENT) |
| Run tai su dung | `/home/ubuntu/java/devrun/X1_GS_T170_2021` (1089 leg, 1069 cum) |
| So sanh | T130 = `X1_GS_T130_2021` (1580 leg), T100 = `NB_PAR_T100` (2559 leg) |
| Dataset | `wfo_ds_x1_2021`, 2021-07 -> 2025-12, `SIM_END_DATE=20251231` |
| KHONG chay lai sim | dung 100% artifact san co (cum/leg count khop y bang muc 4 cua DIAG_BIGDOWN_CONCENTRATION) |

Bac (tier) suy tu `printDone.csv`: leg dau cum = bac 0; moi leg `DCA_LEVEL1` ke tiep = bac 1, 2, 3.
Cum = nhom leg cung symbol, mo boi 1 leg khong-phai-DCA, cac leg `DCA_LEVEL1` sau do gan vao cum
dang mo. **0 leg mo coi (orphan)** o ca 3 run -> quy uoc gop cum la nhat quan.

---

## 1. Co che trigger DCA — XAC MINH LAI TU CODE

### 1.1 Dieu kien kich hoat 1 leg (`DcaUtils.shouldDcaGrid`, dong 32-42)

```java
if (legCount < 1 || legCount > Configs.dcaGridLegs()) return false;  // het bac grid
float level = Configs.dcaGridLevel(legCount - 1);
if (level >= 0f) return false;
float drop = lastPrice / firstEntryPrice - 1f;                        // am khi lo
return drop <= level;
```

Ket luan doc duoc:

1. **CHI co dieu kien GIA.** `drop` do tren `firstEntryPrice` (gia leg DAU cua cum, bat bien qua
   DCA) — khong phai `avgEntry`. Nguong: `DCA_GRID_LEVELS=-0.50,-0.75,-0.90`.
2. **KHONG co cooldown thoi gian giua cac leg.** Ham nay khong nhan `time`/`orderTimeStart`.
   Nhanh cu `shouldDca()` co `isTimeConditionMet()` (`DCA_TIME_BIG_DOWN` phut) nhung nhanh do
   **khong chay** khi `DCA_GRID_ENABLED=true` (profile `x1_gs_t170.properties` dat `=true`).
   => 2 leg DCA cua cung 1 coin co the khop **trong cung 1 phut** neu gia thung qua 2 moc.
3. **KHONG co dieu kien topK / rank / selector tai thoi diem DCA.** Leg DCA duoc tao bang
   `createOrderBUY(..., MarketLevelChange.DCA_LEVEL1, ..., null)` — tham so cuoi la `symbolPred`.
   Trong `EntryGate.threshold()`: `if (symbolPred == null) return thrBase;` => leg DCA an nguong
   **CO SO**, **khong** nhan `GATE_DYN_SCALE`. Tuc T170 siet gate 1.70 cho leg MO CUM nhung
   **khong siet mot chut nao** cho leg DCA cua cum da mo.
4. **TRAN so leg = do dai grid** (`DCA_GRID_LEGS=3`) — day la tran duy nhat, va no la **per-coin**.

### 1.2 Duong goi — co gioi han bao nhieu leg DCA moi tick khong? KHONG.

`SimulatorMarketLevelTicker1MStopLoss` goi DCA o **hai** cho moi tick 1m:

- dong 325-327: `DcaProcessor.getDCA(levelChange, time, budget, activeOrderMap)` — khi
  `MarketBigChangeDetector.getMarketStatus1M(...)` tra ve mot level khac null.
- dong 356-358: `DcaProcessor.getDCA(null, time, budget, getActiveOrderMap())` — khi
  `MarketBigChangeDetector.isDcaAlt(...)` bat.

`DcaProcessor.getDCA` la mot `stream().filter(...).collect()` tren **TOAN BO** vi the dang mo, tra
ve **TAT CA** symbol thoa dieu kien. Vong lap tieu thu no (dong 341-346, 359-364) khong co bien
dem, khong co `break`, khong co `limit`:

```java
for (short symbolId : symbolDcaLevel) {
    ... createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, ...);
}
```

`dsFilterGrid()` (dong 603) chi la tie-break cua DCA-SIGNAL V2 va **no-op khi `DCA_SIGNAL_GATE=false`**
(T170: false). `NUMBER_ENTRY_EACH_SIGNAL=2` chi cap so leg **MO CUM MOI** moi tin hieu — khong dong
gi den nhanh DCA.

=> **Trong 1 tick, so leg DCA duoc mo = so coin dang thoa dieu kien gia, khong co tran.**

### 1.3 Sizing (xac nhan lai, khop DIAG_BIGDOWN_CONCENTRATION)

`margin(bac i) = equity x F_BASE(0.03) x throttle x tierMult(1.0) x w[i] x DCA_GRID_SCALE(19.5) / sum(w)(13)`
= `equity x 4.5% x throttle x w[i]`, voi `w = [1,1,3,8]`.

`throttle = clamp(1 - u/U_MAX, 0, 1)`, `u = marginRunning(CA SO) / equity`.

---

## 2. CO hay KHONG gioi han o cap PORTFOLIO? — **CHI CO DUY NHAT `U_MAX`**

Da grep toan bo `Simulator*.java`, `DcaProcessor.java`, `Configs.java`, `EntryGate.java`,
`TradeUtils.java` voi cac tu khoa `MAX_ORDER / MAX_POSITION / MAX_CONCURRENT / MAX_DCA / DCA_MAX /
MAX_RUNNING / TOTAL_MARGIN / MAX_SYMBOL / BREAKER`. Ket qua:

| Co che | Ton tai? | Chi tiet |
|---|---|---|
| **`U_MAX` = 0.60** | **CO — duy nhat** | `TradeUtils.managerBudget`: `u = marginRunning/equity; if (u >= U_MAX) return null;` Chan MOI lenh moi (ke ca DCA) khi tong margin >= 60% equity, va bop `throttle` tuyen tinh truoc do. |
| Cap so coin dong thoi o bac DCA >= 1 | **KHONG** | khong ton tai key/bien nao |
| Cap tong margin danh rieng cho DCA | **KHONG** | khong ton tai |
| Cap so leg DCA moi tick | **KHONG** | vong lap khong gioi han (muc 1.2) |
| Cap so vi the dang mo | **KHONG** | `NUMBER_ENTRY_EACH_SIGNAL=2` chi cap leg MO CUM moi tin hieu, khong cap ton kho |
| Circuit breaker toan so | **KHONG (DA XOA)** | `Configs.java:640-643`: *"co che circuit-breaker DA BI XOA 2026-09-03. Chi ho tro SIM_BREAKER_MODE=OFF."* |
| Loc TIER cho DCA | **CO — nhung PER-COIN** | `Simulator...java:1173-1178`: coin `TIER_3_SHITCOIN` bi chan leg `DCA_LEVEL1`. `TIER_FLAT=1` chi lam phang **budget multiplier** (`CoinRankManager:117`), **khong** tat phan loai tier — nen loc nay VAN CHAY. |
| Tran so bac | **CO — PER-COIN** | `DCA_GRID_LEGS=3` |

**Ket luan muc 2: he thong hien tai KHONG co bat ky gioi han nao o cap portfolio danh rieng cho
DCA. Phanh duy nhat la `U_MAX=0.60` tren TONG margin — no khong phan biet leg mo cum voi leg DCA,
va no la phanh MEM (throttle) truoc khi thanh phanh CUNG (chan) o 60%.**

---

## 3. DO LUONG THUC NGHIEM — T170 (baseline)

Phuong phap: dung time series su kien (moi leg mo = +1, moi leg dong = -1), tinh o **moi moc su
kien**, **trong so theo do dai doan** (duration-weighted) cho percentile/mean. Tong thoi gian phu:
**1588.2 ngay**.

### 3.1 Phan bo so coin dong thoi

| Chi so | max | p99 | p95 | p50 | mean | % thoi gian > 0 |
|---|---|---|---|---|---|---|
| So cum dang mo (moi loai) | **28** | 12 | 5 | 0 | 0.807 | 23.11% |
| So coin o **bac >= 1** (da qua -50%) | **8** | 0 | 0 | 0 | 0.011 | **0.847%** |
| So coin o **bac >= 2** (-75%) | **2** | 0 | 0 | 0 | 0.001 | **0.054%** |
| So coin o **bac = 3** (-90%) | **0** | 0 | 0 | 0 | 0.000 | **0.000%** |

Cum theo bac sau nhat: `{bac0: 1053, bac1: 12, bac2: 4, bac3: 0}` / 1069 cum. Chi **20 leg DCA**
trong 4.5 nam (so voi 821 leg PREDICT_SYMBOL_TRADE + 248 leg BIG_DOWN).

### 3.2 Tong margin bi khoa — AGGREGATE (% equity)

| Chi so | max | p99 | p95 | p50 | mean |
|---|---|---|---|---|---|
| **Tong margin cua MOI coin dang o bac>=1** (ca leg bac 0) | **29.25%** | 0.00 | 0.00 | 0.00 | 0.049 |
| Chi rieng cac leg DCA (bac>=1) | 9.53% | 0.00 | 0.00 | 0.00 | 0.020 |
| Tong margin CA SO (= `u` trong cong thuc throttle) | **52.85%** | 31.42 | 15.67 | 0.00 | 2.479 |

### 3.3 Dem so lan (episode = doan lien tuc thoa dieu kien)

| Dieu kien | so episode | tong gio |
|---|---|---|
| >= 2 coin cung o bac>=1 | 3 | 67.5 |
| **>= 3 coin cung o bac>=1 ("pile-in")** | **1** | **26.8** |
| >= 4 coin cung o bac>=1 | 1 | 0.2 |
| >= 5 coin cung o bac>=1 | 1 | 0.2 |
| >= 1 coin o bac>=2 | 3 | 20.7 |
| >= 2 coin cung o bac>=2 | 1 | 0.1 |
| >= 3 coin cung o bac>=2 | 0 | 0.0 |

| Nguong aggregate | so episode | tong gio |
|---|---|---|
| margin-trong-DCA >= 10% equity | 2 | 42.3 |
| margin-trong-DCA >= 20% equity | 1 | 0.1 |
| **margin-trong-DCA >= 30% equity** | **0** | **0.0** |
| **margin-trong-DCA >= 50% equity** | **0** | **0.0** |
| **margin-trong-DCA >= 70% equity** | **0** | **0.0** |
| tong margin ca so >= 30% equity | 45 | 465.2 |
| tong margin ca so >= 50% equity | 6 | 1.0 |
| tong margin ca so >= 60% equity (= `U_MAX`) | 0 | 0.0 |

### 3.4 Toan bo episode co >= 2 coin cung o bac>=1 (T170 chi co 3)

| bat dau | ket thuc | gio | peak n(bac>=1) | peak n(bac>=2) | peak agg USD | **peak agg %eq** |
|---|---|---|---|---|---|---|
| **2025-10-11 04:19** | 2025-10-12 19:51 | 39.5 | **8** | 1 | 28,859 | **29.25%** |
| 2022-11-10 03:41 | 2022-11-10 19:21 | 15.7 | 2 | 1 | 5,351 | 11.77% |
| 2022-05-12 10:05 | 2022-05-12 22:22 | 12.3 | 2 | 1 | 4,027 | 9.99% |

### 3.5 Toan bo 16 cum tung cham bac>=1 cua T170

| sym | mo | dong | bac | margin cum | PnL | level mo cum |
|---|---|---|---|---|---|---|
| GAL | 2022-05-11 13:18 | 2022-05-11 20:51 | 1 | 2,908 | +296.5 | PREDICT_SYMBOL_TRADE |
| DAR | 2022-05-11 14:00 | 2022-05-12 22:22 | 1 | 2,073 | +60.3 | PREDICT_SYMBOL_TRADE |
| ANC | 2022-05-12 07:46 | 2022-05-12 23:23 | 2 | 1,954 | +99.0 | PREDICT_SYMBOL_TRADE |
| FTT | 2022-11-09 01:27 | 2022-11-10 23:09 | 2 | 3,957 | +352.6 | PREDICT_SYMBOL_TRADE |
| SOL | 2022-11-09 10:29 | 2022-11-10 19:21 | 1 | 1,394 | +272.1 | PREDICT_SYMBOL_TRADE |
| SRM | 2022-11-11 21:46 | 2022-11-14 14:39 | 1 | 2,157 | +118.8 | PREDICT_SYMBOL_TRADE |
| **AIA** | 2025-10-11 03:57 | 2025-10-11 04:26 | 2 | 7,430 | +1,250.9 | PREDICT_SYMBOL_TRADE |
| **EVAA** | 2025-10-11 03:57 | 2025-10-11 04:28 | 2 | 5,797 | +471.6 | PREDICT_SYMBOL_TRADE |
| **XAN** | 2025-10-11 03:57 | 2025-10-18 03:58 | 1 | 3,261 | **-1,071.8** | PREDICT_SYMBOL_TRADE |
| **STBL** | 2025-10-11 03:57 | 2025-10-12 19:51 | 1 | 4,671 | +223.2 | PREDICT_SYMBOL_TRADE |
| **XPL** | 2025-10-11 04:00 | 2025-10-11 04:32 | 1 | 2,777 | -65.9 | PREDICT_SYMBOL_TRADE |
| **EDEN** | 2025-10-11 04:13 | 2025-10-12 07:09 | 1 | 2,466 | +102.6 | BIG_DOWN |
| **MYX** | 2025-10-11 04:13 | 2025-10-11 04:22 | 1 | 2,868 | +172.1 | BIG_DOWN |
| **ALPINE** | 2025-10-11 04:17 | 2025-10-11 04:33 | 1 | 1,769 | +418.8 | BIG_DOWN |
| EVAA | 2025-11-03 23:00 | 2025-11-10 23:01 | 1 | 7,452 | **-3,647.8** | PREDICT_SYMBOL_TRADE |
| JELLYJELLY | 2025-11-05 08:39 | 2025-11-07 10:12 | 1 | 7,630 | -151.4 | PREDICT_SYMBOL_TRADE |

8 cum in dam deu mo trong **30 phut** cua 2025-10-11 03:57-04:17 — day chinh la episode dinh diem
o muc 3.4. 8 cum do dong loat cham bac>=1 va 2 trong so do cham bac 2.

---

## 4. SO SANH T130 / T100 (gate long hon)

| Chi so | **T170** | T130 | T100 |
|---|---|---|---|
| cum / leg DCA | 1069 / 20 | 1549 / 31 | 2505 / 54 |
| cum theo bac sau nhat {1,2,3} | 12 / 4 / **0** | 14 / 7 / **1** | 31 / 10 / **1** |
| **max coin dong thoi bac>=1** | **8** | **8** | **10** |
| p99 / p95 coin bac>=1 | 0 / 0 | 1 / 0 | 2 / 0 |
| max coin dong thoi bac>=2 | 2 | 2 | **3** |
| max coin dong thoi bac=3 | 0 | 1 | 1 |
| % thoi gian co >= 1 coin bac>=1 | 0.85% | 1.74% | **2.69%** |
| **max aggregate margin-trong-DCA (%eq)** | **29.25%** | **40.40%** | **41.20%** |
| p99 aggregate (%eq) | 0.00 | 5.75 | 8.74 |
| max margin CA SO (%eq) | 52.85% | 54.95% | **57.13%** |
| p99 / p95 margin ca so (%eq) | 31.42 / 15.67 | 37.70 / 24.43 | 45.82 / 31.86 |
| episode >= 3 coin bac>=1 (so lan / gio) | 1 / 26.8 | 2 / 56.2 | **4 / 213.5** |
| episode >= 5 coin bac>=1 | 1 / 0.2 | 1 / 0.2 | **3 / 75.8** |
| episode agg >= 30% eq | **0 / 0.0** | 1 / 9.4 | **3 / 136.2** |
| episode agg >= 50% eq | 0 | 0 | 0 |
| episode agg >= 70% eq | 0 | 0 | 0 |
| episode tong margin ca so >= 50% eq | 6 / 1.0h | 8 / 42.8h | **22 / 193.3h** |
| episode tong margin ca so >= 60% eq (`U_MAX`) | 0 | 0 | 0 |

Top episode cua T130 / T100:

| run | bat dau | gio | peak n1 | peak n2 | peak n3 | **peak agg %eq** |
|---|---|---|---|---|---|---|
| T130 | 2025-10-11 04:18 | 39.5 | 8 | 1 | 0 | 28.46% |
| T130 | 2022-05-11 19:32 | 27.4 | 4 | 2 | 0 | 24.00% |
| T130 | 2025-11-08 22:21 | 48.7 | 2 | 0 | 0 | 12.51% |
| T100 | 2022-05-11 14:38 | 31.8 | **10** | 1 | 0 | 35.97% |
| T100 | 2025-10-11 04:18 | 104.0 | 9 | 2 | 0 | 31.73% |
| T100 | **2025-11-06 22:35** | 126.5 | 5 | **3** | **1** | **39.79%** |
| T100 | 2025-03-10 21:05 | 15.2 | 3 | 0 | 0 | 11.82% |

**Quan sat:** bien dinh cua aggregate (29-41%) **thap hon** tran per-coin ly thuyet 58.5% va chi
nhinh hon ky luc per-coin 39.2% — vi `throttle` bop nho moi leg dung luc so day. Nhung gia phai
tra la o cho khac: T100 co **193 gio** voi tong margin ca so >= 50% equity (T170: **1 gio**).

---

## 5. DOI CHIEU VOI 3 CUA SO HE THONG DA BIET

| run | cua so | gio co >=2 coin bac>=1 | gio co >=1 coin bac>=1 | peak n(bac>=1) | peak agg %eq | so leg DCA |
|---|---|---|---|---|---|---|
| **T170** | 2021-11-16 -> 2022-08-20 | 12.3 | 20.6 | 2 | 9.99% | 4 |
| **T170** | 2024-04-10 -> 2024-08-01 | **0.0** | **0.0** | 0 | 0.00% | **0** |
| **T170** | 2025-03-04 -> 2025-10-11 | 19.7 | 19.7 | **8** | **29.25%** | 10 |
| T130 | 2021-11-16 -> 2022-08-20 | 27.4 | 33.5 | 4 | 24.00% | 7 |
| T130 | 2024-04-10 -> 2024-08-01 | 0.0 | 91.2 | 1 | 5.75% | 1 |
| T130 | 2025-03-04 -> 2025-10-11 | 19.7 | 44.2 | 8 | 28.46% | 11 |
| T100 | 2021-11-16 -> 2022-08-20 | 31.8 | 32.6 | **10** | 35.97% | 13 |
| T100 | 2024-04-10 -> 2024-08-01 | 88.5 | 114.0 | 2 | 9.80% | 2 |
| T100 | 2025-03-04 -> 2025-10-11 | 34.9 | 293.0 | 9 | 31.73% | 18 |

Ti le leg DCA roi vao 3 cua so: **T170 14/20 (70%)**, T130 19/31 (61%), T100 33/54 (61%).

**Khong rai rac — no TUM TUM.** Va tum tum o muc con chat hon 3 cua so: voi T170, **8/20 leg DCA
(40%) roi vao dung 30 phut** 2025-10-11 03:57-04:27, va **3/20** nua roi vao 2022-05-11..12,
**3/20** vao 2022-11-09..11. Ba ngay lich su chiem 14/20 leg DCA cua 4.5 nam.

Luu y cua so 2024-04-10 -> 2024-08-01: T170 co **0** leg DCA. Do la cua so sut giam CHAM
(grind-down) chu khong phai sap dot ngot — grid -50/-75/-90 tren `firstEntryPrice` gan nhu khong
bao gio cham trong loai thi truong do (exit `LOSER_TIME_STOP_HOURS=168` cat lenh truoc).

---

## 6. PHAT HIEN PHU (KHONG nam trong de bai nhung doi huong) — kenh "o at" THAT SU la BIG_DOWN

DCA cua T170 rat hiem (20 leg / 4.5 nam). Nhung **so leg VAO dong loat** thi khong hiem chut nao —
no di qua duong **mo cum moi**, khong phai duong DCA:

| run | max cum MO trong 1 gio | thoi diem | max cum MO trong 24 gio |
|---|---|---|---|
| T170 | **66** (trong do **54 la BIG_DOWN**) | **2025-10-11 04:13** | **122** |
| T130 | 65 (54 BIG_DOWN) | 2025-10-11 04:13 | 119 |
| T100 | 65 (54 BIG_DOWN) | 2025-10-11 04:13 | 124 |

Con so **54 leg BIG_DOWN trong 1 gio la GIONG HET nhau o ca 3 gate** — dung nhu code: leg BIG_DOWN
co `symbolPred=null` nen **bypass hoan toan `GATE_DYN_SCALE`** (muc 1.1 diem 3). Siet gate tu 1.00
len 1.70 cat 1436 cum PREDICT (2257 -> 821) nhung **khong cat mot leg BIG_DOWN nao** (248 o ca 3 run).

Concurrency cum dang mo theo loai (time-weighted, T170): BIG_DOWN max=18 / p99=3; PREDICT max=22 /
p99=11. Va tong margin ca so cham **52.85% equity** — tuc da di 88% quang duong toi `U_MAX=0.60`.

=> **Neu muc tieu la chong "vao o at", DCA khong phai kenh chinh o T170; BIG_DOWN moi la.**
Cung dung 1 gio 2025-10-11 04:13 vua la dinh BIG_DOWN vua la goc cua 8 coin lun bac>=1 sau do.

---

## 7. GIOI HAN PHUONG PHAP (phai ghi ro)

1. `margin` lay tu `printDone.csv` la margin **danh nghia luc dat lenh** (entry x quantity), khong
   mark-to-market. "Margin bi khoa" o day = von da bo ra, khong phai gia tri thi truong hien tai.
2. `equity` lay tu dong `Update <ngay> 07:00 => b:... unP:...` trong `logs/sim.out`, tuc **anh chup
   07:00 hang ngay**, khong phai equity intraday. Cac ti le `% equity` vi vay co sai so nho; trong
   cac dinh diem (sap manh, equity dao trong ngay) sai so nay co the vai phan tram tuyet doi.
3. Bac grid suy tu thu tu leg trong `printDone.csv`, khong doc truc tiep bien `legCount` trong sim.
   Da doi chieu: `{bac1,bac2,bac3}` = T170 {12,4,0}, T130 {14,7,1}, T100 {31,10,1} — khop y bang
   muc 4 cua `docs/DIAG_BIGDOWN_CONCENTRATION.md` (T170 16/4/0, T130 22/8/1, T100 42/11/1 doc theo
   quy uoc ">= bac k"). **0 leg DCA mo coi** o ca 3 run.
4. Percentile/mean deu la **time-weighted theo do dai doan giua hai su kien**, khong phai sampling
   deu. p95/p99 cua cac chuoi "hau het bang 0" vi vay bang 0 — con so co nghia o day la **max**,
   **so episode** va **tong gio**, khong phai percentile.
5. T100 dung run `NB_PAR_T100` (2559 leg / 2505 cum — khop bang T100 cua DIAG truoc); T130 dung
   `X1_GS_T130_2021` (1580 leg / 1549 cum — khop). Span cua 3 run khac nhau nhe (T170 het
   2025-12-01, T100 het 2025-12-24) vi leg cuoi dong khac ngay; khong anh huong ket luan.
6. Khong chay lai sim nao. Script phan tich: `/tmp/dca_conc.py` tren may Oracle (read-only, khong
   commit vao repo).
