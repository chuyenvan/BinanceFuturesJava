# PREREG — DCA ROUND CAP (siet tong margin moi luot DCA)

> **Pre-reg (chot truoc khi code/run).** Branch `module`. KHONG push. DEV 2021-07..2025-12
> (`wfo_ds_x1_2021`, `SIM_END_DATE=20251231`). Baseline/parity = profile `x1_gs_t170.properties`,
> artifact `X1_GS_T170_2021/storage/printDone.csv` md5 `efb793e2468ca3a7318da0f0ad23d4fc`.

## 0. Muc tieu (user chot trong chat)

*"siet that bang toi da moi lan dca chon theo top xep hang theo co che nao do roi moi luot max 10%
von chang han. loi long hon cai ti le loss moi dca."*

MASTER chot MAC DINH (user uy quyen chi tiet, khong phan hoi kip):

| thu | chot |
|---|---|
| "von" | **equity hien tai** (= `BudgetManagerSimple.equityNow()` = `balanceCurrent + unProfit`) |
| "xep hang" | **rot sau nhat so gia vao dau truoc** (`drop = lastPrice/firstEntryPrice - 1`, tang dan) |
| "loi long nguong loss" | `-0.30 / -0.55 / -0.75` (thay `-0.50 / -0.75 / -0.90`) |

Day la thay doi **KHAU VI RUI RO** (siet tran moi luot + noi nguong kich hoat DCA), KHONG phai
thay doi nguong bang chung. Nguong bang chung GIU NGUYEN (`>=2` rate ngoai CI, bootstrap block-72h
x1.21, 2000 rep, seed 20260905 — `docs/RISK_APPETITE.md`).

## 1. Su that code (da xac minh, khong doi)

- `DcaProcessor.getDCA(...)` (chi duong SIM): stream tren `symbol2OrderRunning`, loc bang
  `DcaUtils.shouldDcaGrid(firstEntryPrice, lastPrice, legCount)` khi `DCA_GRID_ENABLED`; tra ve
  **TOAN BO** ung vien, **KHONG tran**.
- `DcaUtils.shouldDcaGrid`: `legCount < Configs.dcaGridLegs()` (mac dinh 3) va
  `drop = lastPrice/firstEntryPrice - 1 <= Configs.dcaGridLevel(legCount-1)`.
- `Configs.DCA_GRID_LEVELS` mac dinh `-0.50,-0.75,-0.90`; `DCA_GRID_WEIGHTS` mac dinh `1,1,3,8`;
  `DCA_GRID_SCALE=19.5` (profile T170). `DcaUtils.gridLegWeightRatio(legCount) = w[legCount] *
  DCA_GRID_SCALE` khi `FIX_B2=true`.
- `getDCA` duoc goi 2 cho trong `SimulatorMarketLevelTicker1MStopLoss` (nhanh `levelChange != null`
  dong ~335 va nhanh `isDcaAlt` dong ~366), cung `time`, cung tick. **Cung mot tick BIG_DOWN kich
  hoat CA HAI nhanh** (coupling da do o `docs/DIAG_DCA_GUARD_COUPLING.md` muc 3). Sau moi nhanh con
  qua `dsFilterGrid(...)` (DCA-SIGNAL, OFF o experiment nay).
- Sizing leg DCA (`createOrder`, levelChange=DCA_LEVEL1, dcaSignal=false): `balanceBasic =
  FIX_B3 ? equityNow() : balanceBasic`; `budget = TradeUtils.managerBudget(getBudget(),
  marginRunning, balanceBasic, levelChange)` = `balanceBasic * F_BASE * throttle / dcaGridTotalWeight()`
  (`throttle = clamp(1 - marginRunning/balanceBasic/U_MAX, 0, 1)`, `null` neu `u>=U_MAX`);
  `budget *= tierMultiplier` (=1.0 vi `TIER_FLAT=1`); `budget *= gridLegWeightRatio(legIdx)`;
  `quantity = calQuantityTest(budget, ...)` (FLOOR xuong step size) => **margin THAT <= budget uoc**.
- `order.legCount` (== `gridLegCount(orders)`) == `legIdx` dung trong `createOrder` cho leg DCA ke
  tiep (da xac minh: leg dau dung w[0], DCA 1/2/3 dung w[1]=1 / w[2]=3 / w[3]=8).

## 2. Co che (code moi, default OFF)

Flag moi (Configs, **default OFF** => parity OFF byte-identical `efb793e2...`):

| key | default | y nghia |
|---|---|---|
| `DCA_ROUND_CAP_ENABLED` | `false` | bat/tat tran tong margin moi moi luot DCA |
| `DCA_ROUND_CAP_PCT` | `0.10` | tran = PCT x equity hien tai |
| `DCA_RANK_MODE` | `off` | `off` = khong rank/khong cap (hanh vi cu); `drop` = rank theo drop tang dan |

Chi trong `DcaProcessor.getDCA` (chi duong SIM), khi `DCA_ROUND_CAP_ENABLED=true && DCA_RANK_MODE=drop`:

1. Loc ung vien nhu cu (`shouldDcaGrid`).
2. Xep hang theo `drop = lastPrice/firstEntryPrice - 1` **tang dan** (rot sau nhat truoc; su dung
   `firstEntryPrice != null ? firstEntryPrice : priceEntry`).
3. Duyet tu sau nhat, cong don `margin MOI` cua tung ung vien:
   `margin_i = TradeUtils.managerBudget(getBudget(), marginRunning, equityNow, DCA_LEVEL1)
   * CoinRankManager.getBudgetMultiplier(sid) * DcaUtils.gridLegWeightRatio(order.legCount)`.
   (truy DUNG cong thuc sizing trong `createOrder`; `marginRunning`/`equityNow` lay tu
   `BudgetManagerSimple.getInstance()`, `sid` = short key cua map).
4. Giu ung vien sao cho tong `margin MOI <= DCA_ROUND_CAP_PCT * equityNow` (0.10 x equity). Phan
   con lai **KHONG mo luot nay** (khong doi thu tu cac tick sau).
5. **Per-tick, xuyen 2 call-site**: 2 lan goi `getDCA` trong CUNG mot tick chia chung mot budget
   (static field theo `time`), vi BIG_DOWN tick kich hoat ca 2 nhanh. Reset khi `time` doi.

Ghi chu ky thuat:
- `margin_i` la uoc tinh = `budget` truoc `calQuantityTest` (FLOOR) => `margin THAT <= uoc`. Cap
  theo uoc la CONSERVATIVE (tong margin THAT <= tran). Throttle dung `marginRunning` tai thoi diem
  bat dau moi `getDCA` => uoc lon hon that (con conservative).
- `managerBudget` khong dung tham so `levelChange` (FROZEN v1) => truyen DCA_LEVEL1 hay null deu
  nhu nhau.
- `TIER_FLAT=1` => tierMultiplier=1.0 trong moi variant; van tinh qua `getBudgetMultiplier` cho dung.

Log (khong doi printDone => parity byte-identical khi OFF):
- 1 dong mode hieu dung: `[DCA-CAP] MODE ...` (in 1 lan).
- 1 dong aggregate cuoi run: `[DCA-CAP] SUMMARY rounds=<R> roundsCut=<RC> legsCut=<LC> ...`.
- (tuy chon) per-round khi cat: `[DCA-CAP] t=... nCand=... kept=... cut=... sumKept=... cap=... eq=...`.

## 3. Ba bien the (k=3, chot truoc, KHONG them)

Tat ca clone `x1_gs_t170.properties` + key moi; chi doi cac key sau:

| variant | DCA_ROUND_CAP_ENABLED | DCA_RANK_MODE | DCA_ROUND_CAP_PCT | DCA_GRID_LEVELS |
|---|---|---|---|---|
| `CAP10` | true | drop | 0.10 | `-0.50,-0.75,-0.90` (GIU) |
| `CAP10_LOOSE` | true | drop | 0.10 | `-0.30,-0.55,-0.75` (noi) |
| `LOOSE` | false | off | (khong dung) | `-0.30,-0.55,-0.75` (noi) |

- `CAP10` = chi bat tran + rank, giu nguong.
- `CAP10_LOOSE` = tran + rank + noi nguong (thiet ke goc cua user).
- `LOOSE` = chi noi nguong, KHONG tran (tach tac dong cua viec noi nguong).
- **KHONG dung co che nao thay doi `MarketBigChangeDetector`, `isDcaAlt`, hay gene HPO.**
- `DCA_GRID_LEVELS` override duoc vi profile doc key qua `Cfg.get("DCA_GRID_LEVELS")`.

## 4. Tieu chi cham (chot truoc)

### 4.1 PRIMARY = khong duoc lam XAU (safety, khong di san alpha)

Tren **5 rate chat luong toan bo leg** (`win%`, `TSloss%`, `mP|SM`, `mP|SL`, `meanP`), so variant
vs parity: **khong rate nao XAU ngoai CI**. "XAU" = (variant - parity) nam NGOAI CI bootstrap VA
nguoc huong tot. Huong tot: win/mP|SM/mP|SL/meanP UP, TSloss% DOWN.

### 4.2 CO CHE phai dung

Tu `printDone.csv`: nhom leg `level == DCA_LEVEL1` theo cot `start` (phut) = 1 "luot". Kiem
**tong margin moi moi luot <= 10% x equity** (equity tu `sim.out`, map theo phut gan nhat). Bao cao
so luot bi cat va so leg bi cat (tu log `[DCA-CAP] SUMMARY`).

### 4.3 CHAN (veto)

1. **Khong nam am** (tuyet doi).
2. `maxDD <= 30%/nam`, `UW <= 200 ngay`, `quy xau nhat >= -15%` (bar moi, tu equity THAT `sim.out`).
3. **Tap trung**: max % equity vao 1 coin **khong tang** so parity.
4. **So leg DCA / tong n leg**: bao cao (co the tang — do la muc dich cua viec noi nguong, khong phai loi).

### 4.4 MULTIPLICITY

k=3 bien the x 5 rate = 15 test. Dung he so B4 `sqrt(2 ln 3) = 1.4823`. Tong he so no rong CI =
`1.21 (block-bootstrap) * 1.4823 (B4) = 1.7936`. KHONG chon theo equity (equity/CAGR khong phai tieu chi).

### 4.5 QUYET DINH

- PASS neu: co che dung + khong rate nao XAU ngoai CI + het CHAN.
- Neu nhieu variant PASS => bao cao ca 3, **KHONG tu chon mot** (thay doi khau vi rui ro => master/user quyet).
- Neu co gi khong lam duoc (vi du khong truy duoc cong thuc margin) => neu RO, DUNG, bao parent.

## 5. Trinh tu

1. Pre-reg (file nay) commit truoc.
2. Code: Configs + `DcaProcessor.getDCA` + 1 ham thuan `DcaUtils` + 1 dong SUMMARY trong simulator.
3. Build jar + **CONG PARITY**: flag OFF => `printDone.csv` byte-identical `efb793e2...`; khac => DUNG, bao.
4. Chay 3 variant (profile clone) tren `wfo_ds_x1_2021`, TUAN TU, 1 slot JVM, `setsid`/background + poll.
5. Cham dung tieu chi muc 4.
6. Viet `docs/RESULT_DCA_ROUND_CAP.md` + commit (KHONG push).
