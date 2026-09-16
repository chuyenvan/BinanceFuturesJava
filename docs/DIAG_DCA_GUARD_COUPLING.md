# DIAG — guard `isDcaAlt` + ghep BIG_DOWN ↔ DCA + cac diem dat tran moi luot DCA

> **Tai lieu MO TA (descriptive).** KHONG pre-reg, KHONG sua mot dong `.java` nao, KHONG them
> flag, **KHONG chay sim moi**. Moi so lay tu code trong repo (branch `module`) + du lieu DA CO:
> `printDone.csv` cua baseline T170 (`/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv`,
> md5 `efb793e2468ca3a7318da0f0ad23d4fc`) + cac DIAG/PREREG co san trong `docs/`.
> **KHONG de xuat con so nguong.** Viec chon nguong la quyet dinh pre-reg cua MASTER.

Cau hoi goc (user): *"BIG_DOWN gan voi DCA hoi rui ro, kieu co the vao o at ma khong kiem soat.
isdca xem guard chat chua, khong chac cung phai gioi han moi luot DCA mot nguong nao do."*

Doc kem: `docs/DIAG_BIGDOWN_TRIGGER_MECHANISM.md`, `docs/DIAG_BIGDOWN_CONCENTRATION.md`,
`docs/DIAG_DCA_CONCURRENCY.md`, `docs/PREREG_CONCENTRATION_SAFETYCAP.md`,
`docs/DESIGN_ROLLING_BIGDOWN.md`.

---

## 0. Tom tat mot dong

`isDcaAlt` **KHONG chat** (no la cai "o" rong, 0.23% so phut); nhung DCA that su chi no khi
**moi coin rieng** dong thoi thung grid -50/-75/-90% => DCA that hiem (20 leg / 4.5 nam, T170)
va **max 6 leg trong 1 phut, 10 leg trong 1 gio** dung vao dung ngay crash 2025-10-11. Kenh "vao
o at" THAT SU la **BIG_DOWN** (54 leg/gio), khong phai DCA. `MS_DOWN_BIG_AVG` dang **dung chung**
cho ca BIG_DOWN lan DCA => doi trigger ma khong tach la doi ca DCA (nhay hon 43x).

---

## 1. `isDcaAlt` guard chat toi dau?

### 1.1 Dieu kien chinh xac — `MarketBigChangeDetector.isDcaAlt` (dong 188-191)

```java
public static boolean isDcaAlt(Float rateDown15MAvg, Float rateDownAvg, Float rateUpAvg) {
    return rateDown15MAvg < Configs.MS_DOWN_BIG_AVG          // nguong -0.03157
            || rateDownAvg < Configs.MS_DOWN_BIG_AVG / 3;     // nguong -0.01052
}
```

| bien | nghia | nguong dung |
|---|---|---|
| `rateDown15MAvg` | rolling high 15 nen 1m: `close / max(maxPrice 15 nen gan nhat) - 1` (am khi rot so voi dinh 15 phut) | `MS_DOWN_BIG_AVG = -0.03157` |
| `rateDownAvg` | trung binh return cua **100 coin giam manh nhat trong DUNG 1 nen 1 phut** | `MS_DOWN_BIG_AVG / 3 = -0.01052` |
| `rateUpAvg` | **KHONG dung** (tham so thua) | — |

`MS_DOWN_BIG_AVG = -0.03157f` (`Configs.java:380`), override duoc bang `SIM_MS_DOWN_BIG_AVG`
(`Configs.java:630`). Profile T170/T130/T100 **KHONG khai bao key nay** => deu chay hang so.

### 1.2 Tan suat thuc te (4.5 nam, doc tu `market.bin` + printDone.csv)

| dieu kien | % phut thoa | so phut / 2,301,233 phut |
|---|---|---|
| `rateDownAvg < -0.03157` (= BIG_DOWN trigger) | **0.00539%** | **124 phut** |
| `rateDown15MAvg < -0.03157` (nhanh 1 cua isDcaAlt) | **0.23144%** | ~5,325 phut |

(So lieu tu `DIAG_BIGDOWN_TRIGGER_MECHANISM.md` muc 3.3.)

=> Nhanh `rateDown15MAvg` cua `isDcaAlt` **nhay hon 43 lan** so voi chinh BIG_DOWN. Nhung day
moi la "umbrella" cho phep **quet** DCA; **khong** co nghia DCA no 5,325 lan.

### 1.3 Guard THAT SU cua moi leg DCA la dieu kien GIA per-coin, khong phai isDcaAlt

`DcaProcessor.getDCA` (dong 21-55) stream tren **toan bo vi the dang mo**, moi symbol duoc goi
`DcaUtils.shouldDcaGrid(firstEntryPrice, lastPrice, legCount)` (dong 32-42):

```java
if (legCount < 1 || legCount > Configs.dcaGridLegs()) return false;  // het bac grid
float level = Configs.dcaGridLevel(legCount - 1);
float drop = lastPrice / firstEntryPrice - 1f;                        // am khi lo
return drop <= level;                                                  // -0.50 / -0.75 / -0.90
```

=> `isDcaAlt` chi la **cong mo rong thi truong** (cho phep DCA chay ke ca khi khong co BIG_DOWN),
con mot leg DCA chi THUC SU no khi **chinh coin do** da rot >= -50% (bac 1) so voi gia leg dau.
`isDcaAlt` khong co bat ky dieu kien per-coin nao khac (khong cooldown thoi gian, khong rank, khong
selector — `DCA_TIME_BIG_DOWN=8` chi song o nhanh `shouldDca` CU, da CHET khi `DCA_GRID_ENABLED=true`).

**Ket luan Q1:** `isDcaAlt` la guard **LONG (lo), khong chat**. Nhung tac dong cua no bi giam nhe
boi guard per-coin (`shouldDcaGrid`) — duong DCA that su hiem. "Chat" hay khong phai danh gia o
lop per-coin, khong phai o `isDcaAlt`.

---

## 2. "Vao o at" co that khong?

### 2.1 `getDCA` tra ve toi da bao nhieu phan tu? — KHONG co tran

`DcaProcessor.getDCA` (dong 21-55) la `stream().filter(...).map(...).collect(toList())` tren
**toan bo** `symbol2OrderRunning` (vi the dang mo). **Khong co `limit`, khong co `break`, khong co
bien dem.** => so phan tu tra ve toi da = **so vi the dang mo** (`activeRunningCount`, dinh lich su
T170 = 28 cum dang mo dong thoi).

Vong lap tieu thu (Simulator `:341-346` va `:359-364`) cung **khong co gioi han**:

```java
for (short symbolId : symbolDcaLevel) {
    if (Utils.isTickerAvailable(ticker)) {
        createOrderBUY(symbolId, ticker, MarketLevelChange.DCA_LEVEL1, ...);
    }
}
```

`NUMBER_ENTRY_EACH_SIGNAL=2` chi cap so leg **MO CUM MOI** (BIG_DOWN/PREDICT), **khong dong gi**
den nhanh DCA.

### 2.2 Do thuc te tren T170 (printDone.csv, md5 efb793e2...)

**Tong 20 leg DCA / 4.5 nam** (so voi 821 PREDICT + 248 BIG_DOWN).

**So leg DCA mo trong 1 PHUT** (gom theo cot `start`):

| chi so | gia tri |
|---|---|
| max | **6** (2025-10-11 04:19) |
| thu 2 | 2 (2025-10-11 04:20) |
| con lai | 1 leg/phut (12 phut) |
| p50 | 1 |
| p95 | ~2 |
| p99 | ~6 |

**So leg DCA mo trong 1 GIO** (gom theo 10 ky tu dau `start`):

| chi so | gia tri |
|---|---|
| max | **10** (gio 04h 2025-10-11) |
| thu 2 | 2 (gio 03h 2022-11-10) |
| con lai | 1 leg/gio |

**So leg DCA theo SU KIEN (episode)** — tu `DIAG_DCA_CONCURRENCY.md` muc 3.4-3.5:

- 8/20 leg DCA (40%) roi vao **dung 30 phut** 2025-10-11 03:57-04:27; 3/20 vao 2022-05-11..12;
  3/20 vao 2022-11-09..11. **Ba ngay lich su = 14/20 leg DCA**.
- Peak **so coin dong thoi o bac>=1 = 8**; peak aggregate margin-trong-DCA = **29.25% equity**.
- `>= 3 coin cung bac>=1` ("pile-in"): **1 episode / 26.8 gio** trong ca 4.5 nam.

**Ket luan Q2:** "vao o at" cua **DCA** la THAT nhung **hiem va cum dac**: 20 leg / 4.5 nam,
max 6 leg/phut va 10 leg/gio, tat ca tap trung quanh mot vai su kien sap. **Kenh "o at" that su la
BIG_DOWN** (mo vi the moi): 54 leg BIG_DOWN trong 1 gio, 2025-10-11 04:13, giong het nhau o ca 3
gate (leg BIG_DOWN co `symbolPred=null` => bypass `EntryGate`/`GATE_DYN_SCALE` hoan toan).

---

## 3. Coupling: `MS_DOWN_BIG_AVG` dung CHUNG cho BIG_DOWN va DCA

### 3.1 Xac nhan

| ham | dieu kien dung `MS_DOWN_BIG_AVG` | file:dong |
|---|---|---|
| `getMarketStatus1M` (BIG_DOWN) | `rateDownAvg < MS_DOWN_BIG_AVG` | `MarketBigChangeDetector.java:179` |
| `isDcaAlt` (DCA) | `rateDown15MAvg < MS_DOWN_BIG_AVG` **VA** `rateDownAvg < MS_DOWN_BIG_AVG / 3` | `MarketBigChangeDetector.java:189-190` |

=> **CUNG mot hang so** dieu khien ca (a) trigger BIG_DOWN lan (b) ca HAI nhanh cua `isDcaAlt`.

### 3.2 Neu doi `MS_DOWN_BIG_AVG` thi CHINH XAC cai gi doi theo

| call-site | file:dong | he qua khi doi nguong |
|---|---|---|
| `getMarketStatus1M` — SIM | `SimulatorMarketLevelTicker1MStopLoss.java:307` | doi tan suat leg BIG_DOWN (mo vi the moi) |
| `getMarketStatus1M` — LIVE | `DetectEntrySignal2TradeNormal.java:226` | doi tan suat BIG_DOWN tren production (cung ham) |
| `getMarketStatus1M` — export/diagnostic | `ExportMarketData2File.java:133` | doi nhan feature/nhan phan loai o tool offline |
| `isDcaAlt` — SIM | `SimulatorMarketLevelTicker1MStopLoss.java:365` | doi cong DCA (nhanh `rateDown15MAvg`, nhay hon 43x) |
| `isDcaAlt` — LIVE | `DetectEntrySignal2TradeNormal.java:314` | doi cong DCA tren production |

**Diem mat chuyen:** `rateDown15MAvg` cham nguong `-0.03157` o **0.23144%** so phut, con
`rateDownAvg` chi **0.00539%** — tuc nhanh `isDcaAlt` **nhay hon 43 lan**. Sua nham cho => doi
DCA rat nhieu ma khong hay. => Muon chi doi BIG_DOWN thi **bat buoc tach** `MS_DOWN_BIG_AVG`
thanh hai duong rieng (mot cho `getMarketStatus1M`, mot cho `isDcaAlt`), va viec tach do **tu no
la mot thay doi hanh vi can parity gate rieng**.

---

## 4. Guard da co: `CONC_CAP_*` (safety-net, khong phai gene HPO)

Doc tu `Configs.java:499-510` va `PREREG_CONCENTRATION_SAFETYCAP.md`.

| key | default | y nghia | vi tri so voi dinh lich su |
|---|---|---|---|
| `CONC_CAP_AGG_DCA_ENABLED` | **`false`** | bat/tat guard 1 | — |
| `CONC_CAP_AGG_DCA_PCT` | **`0.45`** | tran TONG margin nam trong leg DCA-grid bac>=1 / equity | dinh do duoc **0.4120** (T100) => +9.2% tuong doi |
| `CONC_CAP_BD_RATE_ENABLED` | **`false`** | bat/tat guard 2 | — |
| `CONC_CAP_BD_PER_HOUR` | **`75`** | tran so leg BIG_DOWN mo / 60 phut | dinh do duoc **54 leg/gio** => +38.9% |

**Tra loi Q4:**

1. **Default ca hai deu TAT** (`false`) => khong nhanh nao chay => `printDone.csv` byte-identical
   voi baseline. Guard chi bat khi profile/enable tuong minh.
2. **Nguong dat CAO HON dinh lich su** co chu dich => **KHONG binding tren vung da quan sat**.
   Muc dich la bao hiem truoc kich ban TE HON moi thu da thay trong 4.5 nam.
3. **La "guard an toan", KHONG phai "gene HPO".** PREREG ghi ro: "KHONG duoc dua 0.45 / 75 vao bat
   ky vong HPO/WFO/grid-search nao. Hai so nay la BIEN AN TOAN, khong phai gene."
4. **Pham vi chi o duong SIM**, khong dong vao `DcaUtils/DcaProcessor/EntryGate/TradeUtils` va
   khong dong vao duong LIVE (`DetectEntrySignal2TradeNormal`).

**Luu y quan trong:** hai guard nay **khong phai** "tran moi luot DCA" ma user dang noi. Guard 1
cap **tong margin dang nam** (stock), guard 2 cap **toc do BIG_DOWN** (khong phai DCA). **Khong
guard nao cap "so leg DCA mo trong 1 phut".**

---

## 5. Neu muon dat TRAN MOI LUOT DCA — cac diem co the dat

> Liet ke KHONG kem con so. Moi lua chon can pre-reg rieng + duyet MASTER.

| # | diem dat | noi code | can code? | uu | nhuoc |
|---|---|---|---|---|---|
| A | Tran **so leg DCA mo / phut** (per tick) | trong vong lap tieu thu `Simulator...:341-346` va `:359-364` (them bien dem + `break`) hoac them `limit` trong `DcaProcessor.getDCA` | **CO code** | chan truc tiep "o at" trong 1 tick; don gian nhat ve y nghia | DCA qua hiem (max 6/phut) nen hiem khi binding; phai them trang thai dem cho 2 call-site cung tick |
| B | Tran **so leg DCA dong thoi** (bac>=1) | gan giong `CONC_CAP_AGG_DCA` hien co — dem count thay vi margin | **CO code** (hoac tai su dung counter) | chong "khoa von" dai han; khop truc giac "tong von bi khoa" | trung lap phan lon voi guard 1 da co (margin aggregate); can dinh nghia "dang mo" nhat quan |
| C | Tran **tong margin vao them / phut** (DCA flow) | trong `createOrder` sau `calQuantityTest`, giong guard 1 nhung dem FLOW 60 phut | **CO code** | do dung "dau ra rui ro" (USD, khong phai so leg) | them cau truc rolling window margin; nang hon A |
| D | Tran **theo buoc luoi** (per-coin) | `DCA_GRID_LEGS` / `DCA_GRID_LEVELS` / `DCA_GRID_WEIGHTS` (`Configs.java:187-216`) | **CHI PROFILE** (gene HPO scalar da co) | da co san, chi doi profile; khong them code | la gene per-coin, khong cap PORTFOLIO-level; doi se doi ca hieu qua |
| E | **Cooldown** giua 2 leg DCA cung coin | kich hoat lai `isTimeConditionMet`/`DCA_TIME_BIG_DOWN` trong nhanh grid (hien tai CHET khi `DCA_GRID_ENABLED=true`) | **CO code** | chan "2 leg cung phut do thung 2 moc" | doi hanh vi grid hien tai (can parity); `DCA_TIME_BIG_DOWN=8` la di san HPO cu |
| F | Tran **so leg DCA / gio** (rolling 60 phut) | them rolling window tuong tu `concBdCountLastHour` | **CO code** | cap theo thoi gian, khop "moi luot" | DCA 20 leg/4.5 nam => 10/gio la dinh; rolling window them phuc tap |

**Chi can PROFILE (khong code):** D (buoc luoi), va guard 1/2 da co (bat flag + dat nguong).
**Can CODE:** A, B, C, E, F.

**Nhan xet quan trong (khong phai de xuat):** vi DCA that hiem va cum (muc 2), tran "moi luot
DCA" (A/C/F) chi binding dung 1 lan trong lich su (2025-10-11). Neu muc tieu that su la chong
"vao o at", so lieu chi ra **kenh chinh la BIG_DOWN** (54 leg/gio) — va kenh do da co guard 2
(`CONC_CAP_BD_PER_HOUR`) dat san, chi chua bat.

---

## 6. Rui ro ky thuat neu doi trigger ma KHONG tach nguong (tom tat tu DIAG §5)

1. **5.1 — ghep DCA:** `MS_DOWN_BIG_AVG` dung chung cho `getMarketStatus1M` va `isDcaAlt`;
   `isDcaAlt` nhay hon 43x => doi nguong BIG_DOWN se **doi luon tan suat DCA** mot cach khong kiem
   soat. (Xem muc 3 o day.)
2. **5.2 — sim + LIVE chung ham:** `getMarketStatus1M` la `static`, thuan, khong tham so thoi
   gian, dung chung sim (Simulator:307) + LIVE (DetectEntrySignal2TradeNormal:226). Nguong rolling
   bat buoc them `time` hoac trang thai class => **cham duong LIVE**. Them nua LIVE tu tinh
   `rateDownAvg` tu ticker RAM, sim doc lai gia tri tinh san tu `market.bin` — hai duong nap khac
   nhau, de loi parity (tien le `AUDIT_GATE_DYN_PARITY`).
3. **5.3 — cam dong `calMarketData`:** no la duong sinh feature cho model
   (`MarketDataInlineGenerator.java:104`) => doi la phai retrain + pha moi parity feature.
4. **5.4 — sim chi co 3 float/phut** (`rateDownAvg/rateUpAvg/rateDown15MAvg` trong `market.bin`),
   khong co gia tung coin tai thoi diem quyet dinh => rolling stat phai suy tu chuoi 3 float hoac
   file phu ngoai kieu `RegimeSchedule`.
5. **5.5 — `MS_DOWN_BIG_AVG` la gene HPO o 3 noi** (`WFORunner.java:67`, `StrategyWfoTask.java:74`,
   `SensitivityTool.java:69`) => bien no thanh dai luong dan xuat => 3 noi set field khong con tac
   dung (loi im lang).
6. **5.7 — mau su kien mong:** 124 phut / 56 ngay / 4.5 nam => them >= 2 tham so rolling tren 56
   ngay co su kien = rat de overfit.

---

## 7. Gioi han cua tai lieu nay

1. **Khong chay sim, khong sua code.** Moi ket luan la doc code + do lai artifact `printDone.csv`
   T170 va cac DIAG co san. Khong co so lieu holdout.
2. **So leg DCA / phut / gio** tinh tu cot `start` va `level` cua `printDone.csv` T170 (md5
   `efb793e2...`). `level == DCA_LEVEL1` = leg DCA-grid; leg DCA-SIGNAL khong co trong baseline nay
   vi `DCA_SIGNAL_GATE=false` (mac dinh). Bac grid suy tu thu tu leg trong cum (quy uoc cua
   `DIAG_DCA_CONCURRENCY.md` muc 0), khong doc truc tiep bien `legCount` trong sim.
3. **Phan bo per-phut/per-gio** la dem thuan theo thoi diem MO lenh (cot `start`), **khong** phai
   time-weighted; voi mau qua nho (20 leg) thi `max` co nghia hon `p50/p95/p99` (p50/p95 = 1 vi hau
   het phut chi co 1 leg).
4. **Coupling va rui ro ky thuat** (muc 3, 6) la tom tat tu `DIAG_BIGDOWN_TRIGGER_MECHANISM.md`
   muc 5 va `DESIGN_ROLLING_BIGDOWN.md` muc 0 — khong kiem chung lai doc lap o day.
5. **Khong de xuat nguong, khong ket luan "nen chon cai nao".** Muc 5 chi liet ke cac DIEM DAT co
   the va uu/nhuoc; viec chon la quyet dinh pre-reg cua MASTER.
