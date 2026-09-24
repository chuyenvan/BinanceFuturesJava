# L8_SIZING_PARITY_BACKLOG — hai viec TACH KHOI L7, chua code mot dong nao

Tach ra theo quyet dinh cua master khi duyet L7: **khong sua sizing va khong sua so giay
multi-leg trong cung dot voi cong parity gate**. File nay ghi **so da do duoc** + de xuat thiet ke,
de lan sau khong phai khao co lai.

Nguon: `docs/audit/LEAN_GATE_AUDIT.md` muc 4.3/4.4 (doc code), **cong them phep do moi o muc 1.2 duoi day**.

---

## 1. SIZING — sim vs live

### 1.1 Cong thuc theo CODE

| ben | duong code | bieu thuc |
|---|---|---|
| chung | `TradeUtils.managerBudget` (`:78-96`) | `balanceBasic x F_BASE(0.03) x throttle / dcaGridTotalWeight()`, `throttle = clamp(1 - (marginRunning/balanceBasic)/U_MAX(0.60), 0, 1)`, `u >= U_MAX` => `null` (chan lenh) |
| SIM | `Simulator...:1062-1070` | `balanceBasic = BudgetManagerSimple.equityNow()` (compound, `SIM_FIX_B3=true`) |
| SIM | `Simulator...:1080-1081` | `x tierMultiplier`; `x1_c3_full` co `TIER_FLAT=1` => **1.0** |
| SIM | `Simulator...:1089-1100` | `x DcaUtils.gridLegWeightRatio(legIdx)`; leg0 = `w0/sum(w) x DCA_GRID_SCALE` = `1/13 x 19.5` = **1.5** |
| LIVE | `DetectEntry...:740-741` | `balanceBasic = ShadowBookC3.equityNow()` = `PAPER_EQUITY + realized + MtM`; `marginRunning = book.marginRunning()` |
| LIVE | `DetectEntry...:745-748` | tran `LiveProfileC3.SIZE_CAP_OF_EQUITY = 0.045` x equity |
| LIVE | `DetectEntry...:761-773` | `x tierMultiplier`; 242 **khong dat** `TIER_FLAT` => tier **1.2/1.0/0.5 CO chay** |
| LIVE | — | **KHONG co** `x gridLegWeightRatio` — `grep` toan repo: duong live khong goi ham do o dong nao |

### 1.2 PHEP DO (moi, 2026-09-11) — con so, khong phai suy dien

**SIM**: `X1_C3_FULL_PARITY_R/storage/printDone.csv` (2,266 dong). `%equity` = `margin` cua leg
chia cho equity tai thoi diem VAO, equity dung lai bang `35000 + sum(pnl cua moi lenh dong truoc do)`.
Script: `research/analysis/sizing_parity_measure.py`.

| nam | n | mean margin (USDT) | median margin | mean equity | **mean %equity** | median %equity |
|---|---|---|---|---|---|---|
| 2022 | 406 | 855.9 | 838.1 | 36,927 | **2.338** | 2.300 |
| 2023 | 308 | 1,688.3 | 1,670.7 | 53,344 | **3.178** | 3.282 |
| 2024 | 668 | 1,943.6 | 1,964.1 | 78,262 | **2.496** | 2.565 |
| 2025 | 884 | 2,534.6 | 2,452.8 | 109,474 | **2.335** | 2.228 |
| **48 thang** | **2,266** | **1,944.6** | **1,814.6** | 79,645 | **2.498** | **2.505** |

**LIVE (so giay C3)**: 8 leg cua MOT tick, do truc tiep trong `docs/experiment/L2_PORT_C3.md` muc 4.1
(2026-09-06, shadow tren Oracle, `PAPER_EQUITY = 35,000`):
`1050.00 / 997.57 / 947.49 / 901.06 / 853.83 / 810.88 / 771.03 / 729.92` USDT
= **3.000% -> 2.085%** equity (giam dan trong tick vi `throttle` tut khi `marginRunning` tang).
Doc do ghi ro `ladder = 1` vi **`DCA_GRID_WEIGHTS=1,0,0,0`** trong env cua shadow do.

### 1.3 KET LUAN — va mot canh bao ve chinh audit truoc

1. **Bac do lon KHOP nhau**: sim **2.50%** equity/leg vs live **2.09-3.00%**. Uoc luong
   "~16x" o `docs/audit/LEAN_GATE_AUDIT.md` muc 4.3 la **SAI** — no suy tu cong thuc chu khong do.
   Muc do la **~1.0-1.2x**, khong phai bac mot con so. **Da ghi dinh chinh vao audit do.**
2. 🔴 **Nhung cong thuc KHONG GIAI THICH DUOC phep do cua sim.** Theo 1.1, sim leg0 phai la
   `equity x 0.03 x throttle x 1.0 x 1.5/13` = **0.346% x throttle**, trong khi do duoc
   **2.50%** — lech **~7.2 lan**. Nghia la **chua ai doc dung duong sizing cua sim**
   (nghi ngo: `margin` trong `printDone` la margin cua CUM sau `mergeOrder` chu khong phai cua
   mot leg; hoac `dcaGridTotalWeight()`/`gridLegWeightRatio` khong chay nhu doc). **Chua duoc
   sua mot dong sizing nao truoc khi giai xong cho nay** — sua theo cong thuc sai se pha mot thu
   dang dung.
3. 🔴 **Rui ro CAU HINH, khong phai cong thuc**: tren 242 `conf/env.sh` **khong dat**
   `DCA_GRID_WEIGHTS` (=> default `1,1,3,8`, `ladder = 13`) va **khong dat** `TIER_FLAT`
   (=> tier 1.2/1.0/0.5 chay). Cung mot jar, cung mot ham, nhung `ladder` 13 thay vi 1 se cho
   leg **nho ~13 lan** so voi cai da do o 1.2. Day la rui ro **co that va kiem duoc ngay**.

### 1.4 Viec cua L8

1. **Do truoc, sua sau.** Chay `X1_C3_FULL` voi `WFO_LOG_ENTRIES=1` (hoac them mot dong log
   `[SIZE] equity throttle ladder ratio tier budget` tai `Simulator:1073-1104`) de lay TUNG
   thua so, roi doi chieu voi `printDone.margin`. Chi khi cong thuc giai thich duoc phep do moi
   duoc noi toi chuyen sua live.
2. **Doi chieu env 242**: xac nhan `DCA_GRID_WEIGHTS` / `TIER_FLAT` / `PAPER_EQUITY` that su la gi
   (user chay, agent khong SSH 242), truoc khi bat so giay chay dai.
3. **De xuat (chua chot)**: cho duong live goi DUNG chuoi cua sim —
   `managerBudget` -> `x tierMultiplier` -> `x gridLegWeightRatio(legIdx)` — va dat
   `TIER_FLAT=1` + `DCA_GRID_WEIGHTS=1,1,3,8` + `DCA_GRID_SCALE=19.5` trong `conf/env.sh`,
   de hai ben chi con khac o `balanceBasic`. **Rui ro**: doi size = doi luat von cua mot may dang
   giu tien that; phai lam RIENG mot dot deploy, co `verify.sh` doc dong `[SIZE]`, khong gop voi gate.

---

## 2. SO GIAY C3 — khong tai lap duoc sleeve DCA / BIG_DOWN nhieu leg

### 2.1 Van de
`ShadowBookC3.open` la `Map<String, Pos>` va `openPos` dung `putIfAbsent`
(`ShadowBookC3.java:193-203`) => leg THU HAI tren cung mot symbol **bi bo im lang**: khong log,
khong dem, khong VWAP lai gia von, khong ap ti trong `1:1:3:8`. `Pos` khong co truong
`legCount` / `firstEntryPrice` / `avgEntry`.

Trong khi do duong vao van goi day du:
`DetectEntry...:289` (leg market-signal), `:303` va `:324` (`DCA_LEVEL1`), `:394` (`PREDICT_SYMBOL_TRADE`).
=> so giay nhan leg DCA nhung **vut di**.

### 2.2 Do lon — do tren chinh backtest
`X1_C3_FULL_PARITY_R`, tach theo `level`:

| sleeve | n | mean margin | mean %equity | **pnl (USDT)** |
|---|---|---|---|---|
| `PREDICT_SYMBOL_TRADE` | 1,996 | 1,987.5 | 2.540 | **59,136.7** |
| `BIG_DOWN` | 216 | 1,555.6 | 2.223 | **9,884.4** |
| `DCA_LEVEL1` | 54 | 1,915.8 | 2.009 | **7,407.3** |
| **tong** | **2,266** | 1,944.6 | 2.498 | **76,428.4** |

=> hai sleeve ma so giay **khong tai lap duoc** dong gop **17,291.7 / 76,428.4 = 22.6%** pnl cua
backtest. So giay do duoc bao nhieu cung **khong the** dem so sanh voi `PARITY_R` trong khi con
thieu 22.6% nay.

### 2.3 De xuat thiet ke (chua code)
- **Huong A — tai dung lop vi the cua sim**: cho so giay dung thang `OrderTargetInfoTest` +
  `mergeOrder` cua `Simulator` thay vi `Pos` rieng. Uu: dinh nghia VWAP/legCount/arm chac chan
  giong sim. Nhuoc: keo mot lop `research` vao duong `trading` (hien hai cay tach han).
- **Huong B — mo rong `ShadowBookC3`**: `Map<String, List<Pos>>` + mot `Cluster` giu
  `avgEntry` (VWAP), `legCount`, `firstEntryPrice`, `tsFirstLeg`; `openPos` khong con
  `putIfAbsent` ma cong leg va tinh lai VWAP; `marginRunning()` cong theo cum.
  Uu: khong dinh toi cay `research`. Nhuoc: lai la mot ban sao logic cum — **dung cai loi da gay
  ra L6/L7** (hai ban sao troi khoi nhau) — nen phai kem unit test doi chieu VWAP/legCount voi
  ham cua sim tren cung chuoi leg.
- **Bat buoc di kem huong nao**: mot test "cung chuoi leg => cung `avgEntry`, `legCount`,
  quyet dinh arm/time-stop" giua hai ben. Khong co test do thi khong duoc merge.

### 2.4 Uu tien
Muc 2 **quan trong hon** muc 1: muc 1 hien do duoc la **khop bac do lon**, con muc 2 la
**thieu han 22.6% pnl** cua chien luoc. Nhung ca hai deu **khong** duoc lam chung dot voi cong
parity gate.
