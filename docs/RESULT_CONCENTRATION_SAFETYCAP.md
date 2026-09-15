# RESULT — CONCENTRATION SAFETY-CAP: 2 guard KHONG BINDING tren lich su, PASS

> Pre-reg: `docs/PREREG_CONCENTRATION_SAFETYCAP.md` (commit `9804c62`, viet & commit TRUOC code).
> Code: commit `5e82983`. Branch `module`. Nen so lieu: `docs/DIAG_DCA_CONCURRENCY.md` (`f03a4f1`).
>
> **KET LUAN: PASS.** Ca 6 run (3 baseline x {guard OFF, guard ON}) ra **dung md5 baseline**.
> Hai guard **khong he bind mot lan nao** trong 4.5 nam du lieu, o ca 3 gate. Bat chung len
> **khong ton mot diem CAGR nao**.

---

## 1. Buoc 0 — xac minh co che (ket qua doc code, khong suy doan)

Gia dinh cua MASTER **DUNG**: BIG_DOWN va DCA-grid la HAI co che tach biet hoan toan.

| | **BIG_DOWN** | **DCA-grid** |
|---|---|---|
| Ban chat | **MO VI THE MOI** (leg DAU cua cum) | **CONG THEM leg** vao cum DA MO |
| Tap symbol | `getTopSymbolArray(..., symbolLocked, ...)`, `symbolLocked` = moi symbol dang chay => **chi coin CHUA co vi the** | `DcaProcessor.getDCA` stream tren vi the DANG MO => **chi coin DA co vi the** |
| Kich hoat | `MarketBigChangeDetector.getMarketStatus1M(...) == BIG_DOWN` | `DcaUtils.shouldDcaGrid`: `lastPrice/firstEntryPrice - 1 <= -0.50 / -0.75 / -0.90` |
| Tran/tick | `NUMBER_ENTRY_EACH_SIGNAL=2` | **khong co tran** (vong lap khong `break`/`limit`) |
| Call-site | `Simulator...:336` (`levelChange` = `BIG_DOWN`) | `:344` va `:362` (`MarketLevelChange.DCA_LEVEL1`) |
| Gate | `createOrder:1122` bo qua `EntryGate` cho BIG_DOWN | qua `EntryGate` nhung `symbolPred=null` => khong an `GATE_DYN_SCALE` |

Tap symbol cua hai duong **BU NHAU** (`symbolLocked`): mot leg khong the vua BIG_DOWN vua DCA-grid.

**Diem chen guard** (mot phieu duy nhat): ca 4 call-site deu do vao `createOrder(...)`. Guard dat
**ngay truoc khi construct `OrderTargetInfoTest`, sau khi `quantity` da tinh** — la diem SAU moi
cong hien co (`predict==null`, `EntryGate`, `TIER_3_SHITCOIN`, `U_MAX` qua `managerBudget`,
`gridLegWeightRatio`) va TRUOC khi order ton tai. Sau diem do khong con duong `return` som nao,
nen "qua guard" = "leg chac chan duoc mo".

Phat sinh **duy nhat** so voi pre-reg (khong doi thiet ke, chi la chi tiet trien khai): rolling
window BIG_DOWN duoc reset o **CA HAI** ham khoi tao — `initData()` **va** `initDataReady()` —
chu khong chi `initDataReady()` nhu pre-reg muc 3 viet. Ly do: ca hai deu goi
`BudgetManagerSimple.resetInstance()`, bo sot mot cai se de ro ri trang thai giua cac lan chay.

---

## 2. Code da lam (commit `5e82983`)

| File | Thay doi |
|---|---|
| `tradecore/Configs.java` | +4 field: `CONC_CAP_AGG_DCA_ENABLED` (false), `CONC_CAP_AGG_DCA_PCT` (0.45), `CONC_CAP_BD_RATE_ENABLED` (false), `CONC_CAP_BD_PER_HOUR` (75) — doc qua `Cfg.get`/`Cfg.getOr` dung convention `DCA_GRID_*` / `DCA_SIGNAL_*` |
| `tradecore/Cfg.java` | +tien to `CONC_CAP_` vao `TRADING_PREFIXES` (chiu dung ky luat fail-fast "da co profile thi cam dat qua env") |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | 2 khoi check trong `createOrder` + `concAggDcaGridMargin()` + rolling window `concBdOpenTimes` (`concBdCountLastHour` / `concBdRecord`) + reset o 2 ham init |

**KHONG dong** vao `DcaUtils`, `DcaProcessor`, `EntryGate`, `TradeUtils`, va **khong dong vao
duong LIVE** (`DetectEntrySignal2TradeNormal`). Guard chi ton tai o duong sim.

Build `mvn -o package` (co test): **BUILD SUCCESS, Tests run: 137, Failures: 0, Errors: 0**.

---

## 3. CONG PARITY — 6/6 PASS

Harness `/home/ubuntu/k_runarm.sh <TAG> <PROFILE>`, dataset `/home/ubuntu/wfo_ds_x1_2021`,
`configs/sim_dev_file_2021.properties`, `SIM_END_DATE=20251231` — y het moi round truoc.

| run | profile | guard | n leg | equity `b:` | **md5 `printDone.csv`** | vs baseline |
|---|---|---|---|---|---|---|
| `CC_OFF_T170` | `x1_gs_t170.properties` | OFF | 1089 | 111,070 | `efb793e2468ca3a7318da0f0ad23d4fc` | **KHOP** |
| `CC_ON_T170` | `cc_on_x1_gs_t170.properties` | **ON** | 1089 | 111,070 | `efb793e2468ca3a7318da0f0ad23d4fc` | **KHOP** |
| `CC_OFF_T130` | `x1_gs_t130.properties` | OFF | 1580 | 92,616 | `68510567e9b17430b3453b08abe03e9b` | **KHOP** |
| `CC_ON_T130` | `cc_on_x1_gs_t130.properties` | **ON** | 1580 | 92,616 | `68510567e9b17430b3453b08abe03e9b` | **KHOP** |
| `CC_OFF_T100` | `x1_c3_full.properties` | OFF | 2559 | 121,770 | `dc16e4da6ff6cb7b8d41c592bc3d9c45` | **KHOP** |
| `CC_ON_T100` | `cc_on_x1_c3_full.properties` | **ON** | 2559 | 121,770 | `dc16e4da6ff6cb7b8d41c592bc3d9c45` | **KHOP** |

md5 khop => **moi cot cua moi dong `printDone.csv` giong het** => CAGR / maxDD / UW / win% / so
leg / equity **khong doi mot bit nao**. Khong can cham diem lai bang bootstrap: khong co gi de cham.

Profile ON = profile goc + **DUNG 4 dong** (`diff` xac nhan), gia tri dung pre-reg:
`CONC_CAP_AGG_DCA_ENABLED=true`, `CONC_CAP_AGG_DCA_PCT=0.45`, `CONC_CAP_BD_RATE_ENABLED=true`,
`CONC_CAP_BD_PER_HOUR=75`. Log `[CFG]` xac nhan profile ON nap **24 key** (T170/T130) va **23 key**
(T100) = 20/19 key goc + 4, va `Cfg.auditProfile()` **khong bao key nao khong duoc doc** — tuc ca
4 key guard deu THUC SU duoc code hoi, khong phai go sai ten roi am tham roi ve default.

Grep `CONC-CAP` trong `logs/sim.out` cua ca 3 run ON: **0 dong**. Tuc guard **khong chan mot leg
nao** trong toan bo 4.5 nam, o ca 3 gate.

---

## 4. TEST PHAN CHUNG (falsification) — guard KHONG phai code chet

"Byte-identical" mot minh no chua chung minh guard hoat dong: code khong bao gio chay cung cho ra
byte-identical. Nen chay them mot run co Y siet nguong xuong RAT THAP:

`CC_TIGHT_T170` = profile `CC_ON_T170` doi **dung 2 so**: `CONC_CAP_AGG_DCA_PCT=0.05`,
`CONC_CAP_BD_PER_HOUR=5`.

| | `CC_ON_T170` (0.45 / 75) | `CC_TIGHT_T170` (0.05 / 5) |
|---|---|---|
| md5 | `efb793e2468ca3a7318da0f0ad23d4fc` | **`fad1b63ea52cf874795bfe8d64a4dd83`** |
| n leg | 1089 | **1008** |
| equity `b:` | 111,070 | **99,487** |
| dong log `SKIP DCA-grid leg` | 0 | **111** |
| dong log `SKIP BIG_DOWN leg` | 0 | **83** |

=> **CA HAI guard deu song va deu chan dung loai leg cua minh.** Chung khong bind o 0.45 / 75 vi
lich su chua bao gio cham toi do, **khong phai** vi code khong chay.

(Run nay chi la bang chung co che. **KHONG** phai mot config duoc de xuat: siet xuong 0.05/5 lam
mat 81 leg va -10.4% equity cuoi — dung nhu du bao cua DIAG truoc rang cat BIG_DOWN la cat vao
co che cuu ho.)

---

## 5. Doi chieu nguong vs dinh lich su

| | dinh LICH SU (4.5 nam, 3 baseline) | nguong | bien du | so lan bind thuc te |
|---|---|---|---|---|
| aggregate margin DCA-grid / equity | 0.4120 (T100) · 0.4040 (T130) · 0.2925 (T170) | **0.45** | +8.3% tuyet doi tren dinh cao nhat | **0** |
| leg BIG_DOWN / gio | 54 (giong nhau ca 3 gate, `2025-10-11 04:13`) | **75** | +21 leg | **0** |

---

## 6. KET LUAN

1. **Guard da verify KHONG BINDING tren toan bo lich su da quan sat** (2021-07 -> 2025-12, 3 gate
   1.00 / 1.30 / 1.70). Bat len cho ra ket qua **byte-identical**.
2. **An toan de can nhac bat trong production** nhu mot lop bao ve bo sung: no **khong ton mot
   diem CAGR nao**, khong doi mot lenh nao, chi dung yen cho mot kich ban chua tung xay ra.
3. Y nghia thuc te: neu tuong lai co mot cu sap **te hon moi thu trong 4.5 nam** (aggregate DCA
   vuot 45% equity, hoac hon 75 leg BIG_DOWN trong 1 gio), he thong se tu dung nap them thay vi
   nhoi tiep den khi cham `U_MAX=0.60`.
4. **Hai nguong nay KHONG phai gene.** Khong duoc dua vao HPO/WFO/grid-search. Muon doi chung
   phai co mot pre-reg rieng — vi doi chung la doi **muc bao hiem**, khong phai toi uu hoa loi nhuan.

### Gioi han phai ghi ro

- Guard 1 do **margin danh nghia luc dat lenh** (`quantity * priceEntry / leverage`), khong
  mark-to-market — cung quy uoc `marginRunning` / `U_MAX` dang dung, nhat quan trong toan he.
- Mau so equity cua Guard 1 la `balanceBasic` trong `createOrder` (= `equityNow()` khi `FIX_B3`),
  **cung mau so voi `U_MAX`** — co y chon vay de hai tran khong lech pha.
- Guard chi nam o **duong sim**. Muon co hieu luc THAT tren tai khoan live phai lam mot buoc port
  rieng sang `DetectEntrySignal2TradeNormal` — **chua lam trong round nay**.
- Parity chi chung minh khong binding **tren dataset `wfo_ds_x1_2021`**. Dataset khac (hoac
  profile sizing khac, vd `DCA_GRID_SCALE` khac 19.5) co the co bien do aggregate khac.

---

## 7. Artifact

| | |
|---|---|
| devrun | `/home/ubuntu/java/devrun/CC_{OFF,ON}_T{170,130,100}`, `/home/ubuntu/java/devrun/CC_TIGHT_T170` |
| profile ON | `profiles/cc_on_x1_gs_t170.properties`, `cc_on_x1_gs_t130.properties`, `cc_on_x1_c3_full.properties` |
| profile falsification | `profiles/cc_tight_t170.properties` |
| commit pre-reg | `9804c62` |
| commit code | `5e82983` |
