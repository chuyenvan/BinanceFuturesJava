# PREREG — DCA AGGREGATE CAP 0.30 + PER-COIN CAP 15%

> **Pre-reg (chot truoc khi code/run).** Branch `module`. KHONG push. DEV 2021-07..2025-12
> (`wfo_ds_x1_2021`, `SIM_END_DATE=20251231`). Baseline/parity = profile `x1_gs_t170.properties`,
> artifact `X1_GS_T170_2021/storage/printDone.csv` md5 `efb793e2468ca3a7318da0f0ad23d4fc`.

## 0. Muc tieu (user chot 2026-09-17 trong chat)

Vong truoc (`docs/RESULT_DCA_ROUND_CAP.md`) ket luan: tran **FLOW** (margin moi mo moi luot DCA) KHONG
chan duoc tap trung — tap trung la **STOCK** (1 coin tich luy margin QUA nhieu luot). Cong cu dung la
tran **STOCK** `CONC_CAP_AGG_DCA_*` (da co san, default OFF, mac dinh 0.45 > max lich su 0.4120 nen chua
bao gio binding).

User chot: *"Ok với 0.3 nhưng chặn max cap trên một coin 15%"*.

| thu | chot |
|---|---|
| aggregate cap | `CONC_CAP_AGG_DCA_ENABLED=true`, `CONC_CAP_AGG_DCA_PCT=0.30` (tran TONG margin nam trong leg DCA-grid bac>=1, toan so) |
| per-coin cap | **them moi** `CONC_CAP_PERCOIN_ENABLED=true`, `CONC_CAP_PERCOIN_PCT=0.15` (tran margin MOT coin) |
| "equity" | = `balanceBasic` (= `BudgetManagerSimple.equityNow()` vi `FIX_B3=true`) — cung denom voi guard aggregate hien co |

Day la thay doi **KHAU VI RUI RO** (siet tran STOCK). Nguong BANG CHUNG **GIU NGUYEN** (`>=2` rate ngoai
CI, bootstrap block-72h x1.21, 2000 rep, seed 20260905 — `docs/RISK_APPETITE.md`).

## 1. Su that code (da xac minh, khong doi)

- Guard AGGREGATE da co san trong `SimulatorMarketLevelTicker1MStopLoss.createOrder` (~1309-1317):
  khi `CONC_CAP_AGG_DCA_ENABLED && levelChange==DCA_LEVEL1 && !dcaSignal`, tinh `legNew = quantity*entry/leverage`,
  `aggNow = concAggDcaGridMargin()` (tong margin cac leg DCA_LEVEL1 dang mo, toan so), va `return` (chan)
  neu `(aggNow+legNew)/balanceBasic > CONC_CAP_AGG_DCA_PCT`.
- `concAggDcaGridMargin()` duyet `activeRunningIds` -> `symbol2OrdersEntry[id]`, cong `calMargin()` cua cac
  leg `marketLevelChange==DCA_LEVEL1 && !dcaSignalLeg`. `calMargin() = quantity*priceEntry/leverage`.
- Guard BD_RATE (`CONC_CAP_BD_RATE_ENABLED`/`CONC_CAP_BD_PER_HOUR`=75) chi cho `BIG_DOWN` — KHONG dong.
- **KHONG co tran per-coin nao** => phai them moi.
- Sizing leg DCA (`createOrder`, levelChange=DCA_LEVEL1): `balanceBasic = FIX_B3 ? equityNow() : balanceBasic`;
  `budget = TradeUtils.managerBudget(...)`; `budget *= tierMultiplier`; `budget *= gridLegWeightRatio(legIdx)`;
  `quantity = calQuantityTest(budget,...)` (FLOOR) => margin THAT <= budget.
- `DCA_GRID_LEVELS` mac dinh `-0.50,-0.75,-0.90`; `DCA_GRID_WEIGHTS=1,1,3,8`; `DCA_GRID_SCALE=19.5`
  (profile T170). `DcaUtils.shouldDcaGrid` dung `drop <= dcaGridLevel(legCount-1)`.
- DCA-SIGNAL (`SIM_DCA_SIGNAL_GATE`) default OFF o experiment nay => khong co leg `dcaSignal` (khong can
  phan biet trong cham diem).

## 2. Co che (code moi, default OFF)

### 2.1 Flag moi (Configs, **default OFF** => parity OFF byte-identical `efb793e2...`)

| key | default | y nghia |
|---|---|---|
| `CONC_CAP_PERCOIN_ENABLED` | `false` | bat/tat tran margin MOT coin |
| `CONC_CAP_PERCOIN_PCT` | `0.15` | tran = PCT x equity hien tai |

### 2.2 Guard per-coin (them vao `createOrder`, dung truoc diem `return` tao lenh)

Tai diem tao lenh (SAU khi `quantity` da tinh, CUNG cho voi guard aggregate hien co):

```
legNew   = quantity * entry / leverage            // margin du kien cua leg sap mo
coinNow  = concPerCoinMargin(symbolId)            // tong margin DANG MO cua coin do (moi leg, moi level)
ratioPc  = (coinNow + legNew) / balanceBasic      // balanceBasic = equity (FIX_B3=true)
neu ratioPc > CONC_CAP_PERCOIN_PCT => KHONG mo lenh (return), tang dem binding.
```

- `concPerCoinMargin(symbolId)` = helper READ-ONLY duyet `symbol2OrdersEntry[symbolId]` va cong `calMargin()`
  cua tung leg con mo (entry + DCA + moi level). Cum dong xong bi xoa khoi `symbol2OrdersEntry` (closeOrder)
  nen day dung la tap "dang mo".
- **Ap cho MOI leg moi** (entry + DCA, moi level). Neu ap dung rong qua (vi du chan qua nhieu leg entry)
  thi BAO CAO trong result — KHONG tu doi pham vi.
- Guard la LOP CUOI CUNG, chan HAN (return), KHONG throttle giam size — cung tinh than `U_MAX` tra null.

### 2.3 Log (khong doi printDone => parity byte-identical khi OFF)

- 1 dong mode hieu dung: `[CONC-PC] MODE pct=...` (in 1 lan, khi guard bat).
- 1 dong SUMMARY cuoi run: `[CONC-PC] SUMMARY blocked=...` (so leg bi chan).
- (tuy chon) per-skip: `[CONC-PC] SKIP sym=... t=... lvl=... coinNow=... legNew=... eq=... ratio=... cap=...`.

## 3. Ba bien the (k=3, chot truoc, KHONG them)

Tat ca clone `x1_gs_t170.properties` + key moi; NEN (base grid) cho ca 3 la nguong noi
`DCA_GRID_LEVELS=-0.30,-0.55,-0.75` (giu `DCA_GRID_WEIGHTS=1,1,3,8`, `DCA_GRID_SCALE=19.5`).

| variant | DCA_GRID_LEVELS | CONC_CAP_AGG_DCA_ENABLED | CONC_CAP_AGG_DCA_PCT | CONC_CAP_PERCOIN_ENABLED | CONC_CAP_PERCOIN_PCT |
|---|---|---|---|---|---|
| `LOOSE_AGG30` | `-0.30,-0.55,-0.75` | true | 0.30 | false | (khong dung) |
| `LOOSE_AGG30_PC15` | `-0.30,-0.55,-0.75` | true | 0.30 | true | 0.15 |
| `LOOSE_PC15` | `-0.30,-0.55,-0.75` | false | (khong dung) | true | 0.15 |

- `LOOSE_AGG30` = noi nguong + aggregate 0.30 (khong per-coin).
- `LOOSE_AGG30_PC15` = noi nguong + aggregate 0.30 + per-coin 15% (thiet ke user chot).
- `LOOSE_PC15` = noi nguong + per-coin 15% (khong aggregate).
- PARITY = profile goc (grid `-0.50,-0.75,-0.90`, tat ca guard OFF).
- **KHONG dung co che nao thay doi `MarketBigChangeDetector`, `isDcaAlt`, `DcaProcessor.getDCA`, hay gene HPO.**

## 4. Tieu chi cham (chot truoc)

### 4.1 PRIMARY = khong duoc lam XAU (safety, khong di san alpha)

Tren **5 rate chat luong toan bo leg** (`win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP`), so variant vs
parity: **khong rate nao XAU ngoai CI**. "XAU" = (variant - parity) nam NGOAI CI bootstrap VA nguoc
huong tot. Huong tot: win/mP|SM/mP|SL/meanP UP, TSloss% DOWN.

### 4.2 CO CHE phai dung (do truc tiep tren printDone.csv/log)

1. **Per-coin**: moi thoi diem `max margin 1 coin <= 15% equity` (cluster peak, do tu printDone; equity
   theo ngay tu `sim.out`).
2. **Aggregate**: moi thoi diem `tong margin DCA-grid (bac>=1) <= 30% equity` (sweep open legs tu printDone).
3. Bao cao so lan guard binding + so leg bi chan (tu log `[CONC-PC] SUMMARY`).

### 4.3 CHAN (veto)

1. **Khong nam am** (tuyet doi).
2. `maxDD <= 30%/nam`, `UW <= 200 ngay`, `quy xau nhat >= -15%` (tu equity THAT `sim.out`).
3. **Tap trung 1 coin <= 15% equity** (rang buoc MOI, user chot 2026-09-17).
4. **So leg DCA / tong n leg**: bao cao (co the tang — do la muc dich cua noi nguong, khong phai loi).

### 4.4 MULTIPLICITY

k=3 bien the x 5 rate = 15 test. Dung he so B4 `sqrt(2 ln 3) = 1.4823`. Tong he so no rong CI =
`1.21 (block-bootstrap) * 1.4823 (B4) = 1.7936`. KHONG chon theo equity (equity/CAGR khong phai tieu chi).

### 4.5 QUYET DINH

- PASS neu: co che dung + khong rate nao XAU ngoai CI + het CHAN.
- Bao cao ca 3, **KHONG tu chon mot** (thay doi khau vi rui ro => master/user quyet).
- Neu khong truy duoc cach tinh margin theo coin chinh xac => DUNG, bao parent RO (khong doan).

## 5. Trinh tu

1. Pre-reg (file nay) commit truoc.
2. Code: Configs 2 key + helper `concPerCoinMargin` + guard trong `createOrder` + SUMMARY log.
3. Build jar + **CONG PARITY**: flag OFF => `printDone.csv` byte-identical `efb793e2...`; khac => DUNG, bao.
4. Chay 3 variant (profile clone) tren `wfo_ds_x1_2021`, TUAN TU, 1 slot JVM, `setsid`/background + poll.
5. Cham dung tieu chi muc 4.
6. Viet `docs/RESULT_DCA_AGG_PERCOIN.md` + cap nhat `docs/RISK_APPETITE.md` (them tap trung 1 coin <= 15%).
7. Commit (KHONG push).
