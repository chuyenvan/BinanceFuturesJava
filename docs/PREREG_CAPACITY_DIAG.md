# PREREG_CAPACITY_DIAG — chan doan "vi sao NULL suot": hap thu cong suat + thuoc do cho exit

Viet **TRUOC** khi do bat ky so nao (chot 2026-09-23). **Khong sua thiet ke sau khi thay ket qua.**
Nguon: brief Uni 2026-09-23 + `docs/RESULT_EXIT_FIT.md` (commit `8f3194f`, `eb4c0de`),
`docs/TICKLOG_RESULT.md`, `docs/RESULT_TRAIL_LADDER.md`, `docs/RESULT_TRAIL_HINGE.md`.

## 0. Hai nghi van phai kiem

- **H1 (hap thu cong suat)**: neu he **thuong xuyen kin cho** (tran `NUMBER_ENTRY_EACH_SIGNAL=2`/tick,
  khoa symbol `isSymbolRunning`/`symbolLocked`, `managerBudget` tra `null` khi `u >= U_MAX=0.60`, gate
  reject, `CONC_CAP_*`) thi moi thay doi exit/sizing/selection chi la **xao lai cung mot tap lenh** ⇒
  NULL la **tat yeu**, khong phai "khong tim ra cong thuc".
- **H2 (thuoc do sai cho exit)**: `TSloss%` / `win%` (rate cu) duoc **chinh luat exit dinh nghia**
  ⇒ so 2 luat exit bang rate do la **so 2 thuoc khac nhau**; va bo tham so incumbent (0.07 / 0.5 / 3% / 8%)
  da duoc fit tren **DEV** ⇒ test tren DEV la **thien vi incumbent**.

## 1. Rang buoc

1. KHONG dung `claude-run`/Claude Code. 2. **KHONG chay Java/sim tren Oracle** (shadow active) ⇒
**thuan Python offline**, dung lai artifacts da co (`X1_GS_T170_2021`, `tl-*`, `pc-*`, `X1_TH_*`).
Neu buoc nao BAT BUOC phai sim ⇒ Kaggle (vong nay **khong** can). 3. DEV only (2021-07..2025-12), khong 2026.
4. Ket qua trung gian ghi ra file **ngoai repo**: `/home/ubuntu/capdiag/`. 5. KHONG push.

## 2. VIEC A — do "muc do kin cho" (chot TRUOC cach do + nguong ket luan)

### 2.1 Liet ke MOI cho chan entry (doc code, ghi file:dong) — TRUOC khi do

| # | cho chan | dieu kien | file:dong |
|---|---|---|---|
| C1 | tran so lenh moi tin hieu | `numberOrder = NUMBER_ENTRY_EACH_SIGNAL (2)`; `SMALL_UP`/`SMALL_DOWN_15M` ⇒ `numberOrder/=2` (=1) | `Simulator…StopLoss.java:333`, `:339-342` |
| C2 | khoa symbol | `symbolLocked.addAll(activeRunningIds)` ⇒ `getTopSymbolArray` **skip** symbol dang chay | `:336`, `:347-353`, `MarketBigChangeDetector.java:117-127` |
| C3 | khoa symbol (nhanh selector) | `if (!isSymbolRunning(targetId))` moi vao lenh ⇒ symbol dang chay bi **bo qua** | `:431`, `:760-765` |
| C4 | budget = null | `managerBudget` tra `null` khi `u = marginRunning/equity >= U_MAX (0.60)` hoac `balanceBasic<=0` | `TradeUtils.java:125-143`, `Configs.java:156` |
| C5 | nghet suat DCA | `gridLegWeightRatio(legIdx) <= 0` ⇒ return (het bac grid) | `:1359-1362` |
| C6 | tier3 + DCA | `TIER_3_SHITCOIN && levelChange==DCA_LEVEL1` ⇒ return | `:1306-1311` |
| C7 | gate AI | `AIRejectFilter.entryGate` REJECT ⇒ `return` (tru `BIG_DOWN`) | `:1255-1266` |
| C8 | pump-dump filter | `PumpDumpFilter.shouldSkip` ⇒ return | `:1272-1275` |
| C9 | predict null | `predictionMap.get(ticker.startTime)==null` ⇒ return | `:1246-1249` |
| C10 | ticker unavailable | `Utils.isTickerAvailable(ticker)==false` ⇒ skip | `:363-370`, `:432-435` |
| C11 | tick block (moi, OFF) | `TickWeakBlock.step` chan CA LUOT | `:320-323` |
| C12 | tran tap trung (moi, OFF) | `CONC_CAP_*` chan HAN | `:1395+` |

**Ghi chu 🔴 (chot TRUOC, quan trong):** tran `NUMBER_ENTRY_EACH_SIGNAL=2` 🔴 **chi ap cho leg tin hieu
thi truong** (`getTopSymbolArray(numberOrder,…)` — `:347-353`), **KHONG** ap cho leg selector
(`PREDICT_SYMBOL_TRADE` — vong `selectCands` `:415-451` di het top-K = 8). Vi vay H1 **khong** duoc
phep quy cho "tran 2 lenh/tick" mot cach may moc; phai do **tung cho**.

### 2.2 Nguon so (co san, khong chay lai sim)

| nguon | noi dung | pham vi |
|---|---|---|
| `X1_GS_T170_2021/logs/sim.out` | `[GATE] n_cand=… n_pass=…` (`:592`); dong `BudgetManagerSimple: Update … b:… m:… max:… run:x/y` moi ngay (`BudgetManagerSimple.java:268-271`) | T170, 2021-07-01..2025-12-31 |
| `tl-l1/l2/l3`, `pc-close`, `tl-part`, `pc-part` `logs/sim.out` | nhu tren, cho tung bien the | T170-nen, cung cua so |
| `X1_TH_GAP05/12/WEAK17_2021/logs/sim.out` | nhu tren | hinge V1/V2/V3 |
| `docs/TICKLOG_RESULT.md` (+ `tick.bin.gz` tai `/home/ubuntu/tick/{C2b_TLON,R5_TL,R6_TL}/`) | **phan ra quyet dinh tung phut-ung-vien theo LY DO** (`D_GATE_REJECT`, `D_ALREADY_OPEN`, `D_NO_BUDGET`, `D_TOPK_CUT`, `D_ENTERED`, `D_GRID_EXHAUSTED`, `D_NO_TICKER`) | profile **C2b** (khac T170), DEV 2022-01..2024-06 |

### 2.3 Dai luong do (dinh nghia chot TRUOC)

- **U(t)** = `marginRunning / equity` tai tung dong ngay (`m:` va `max:` — lay `max(m, max)` lam dinh ngay).
  `U_MAX = 0.60`.
- **run_legs(t)** = truong `run:x/y` (so leg dang mo / dinh).
- **gate_pass_rate** = `n_pass / n_cand` cua dong `[GATE]`.
- **phan ra theo ly do** chi doc duoc tren nguon TICKLOG (C2b) — ghi RO profile nao.

### 2.4 NGUONG KET LUAN (chot TRUOC)

**H1 = DUNG ("he kin cho")** neu **bat ky** dieu kien sau dat tren T170/DEV:
- (a) `max U(t) >= 0.9 × U_MAX = 0.54` tren >= **1%** so ngay, **hoac** `NO_BUDGET` (C4) chiem >= **1%**
  tong ung vien; **hoac**
- (b) `D_ALREADY_OPEN` (C2/C3 — khoa symbol) chiem >= **20%** tong quyet dinh ung vien; **hoac**
- (c) so **phut** co `>= numberOrder` ung vien **khong khoa** bi cat boi tran C1 chiem >= **20%** so phut
  co tin hieu.

**H1 = SAI ("khong kin cho")** neu ca 3 deu KHONG dat. Truong hop trung gian (1 trong 3 dat nhung
< nguong nho) ⇒ ghi **"kin cho CUC BO"** va neu ro cho nao.

**Bat buoc:** neu **khong co du lieu** de do mot chi tieu nao ⇒ ghi **RO** (khong bia), va **khong** duoc
coi "khong dat" nhu bang chung "khong kin cho".

## 3. VIEC C — do lai cac bien the exit bang THUOC KHAC (chot TRUOC)

### 3.1 Bo bien the (moi cai co `printDone.csv` rieng)

| tag | dir | md5 printDone | n |
|---|---|---|---|
| **P0** baseline | `/home/ubuntu/kaggle_sim/out/t170-x1-2021` | `efb793e2` | 1089 |
| **L1/L2/L3** trail ladder | `/home/ubuntu/kaggle_sim/out/tl-l1|l2|l3` | `89b3419a` / `dd2dd161` / `f6335d74` | 1086/1087/1089 |
| **F3** peak=CLOSE | `/home/ubuntu/kaggle_sim/out/pc-close` | `13134467` | 1039 |
| **V1/V2/V3** hinge | `/home/ubuntu/java/devrun/X1_TH_GAP05|GAP12|WEAK17_2021` | `b3f995ab` / `ddcbb6b2` / `19a0e4f3` | 1095/1091/1095 |

### 3.2 Thuoc CU (dinh nghia lai tu printDone) — de so

- `win%` = so leg `pnl > 0` / n. `TSloss%` = so leg `status == STOP_LOSS_DONE` / n.
- `meanP` = tong `pnl` / n (leg). **Day la bo rate exit da dung o 5 vong truoc.**

### 3.3 Thuoc MOI (chot TRUOC, khong chon sau)

| # | thuoc | dinh nghia | nguon |
|---|---|---|---|
| M1 | `SumPnL` | tong cot `pnl` cua printDone (leg) | printDone |
| M2 | `CAGR%` | `(b_last/b_first)^(365/(so ngay)) − 1` | series `b:` trong `logs/sim.out` |
| M3 | `maxDD%` | dinh-am cua duong `b:` ngay | series `b:` |
| M4 | `Calmar` | `CAGR% / |maxDD%|` | M2/M3 |
| M5 | `Sortino` | `mean(r)/downside-dev(r)` tren return NGAY cua `b:` | series `b:` |
| M6 | `turnover` | `Σ(end−start)/ (so ngay × 24h)` (tong thoi gian giu / thoi gian), tinh tren leg | printDone |
| M7 | `cap_med_ge20/50/100` | **capture ratio** = `ratePct / peakPct` tren cac cum co `peak ≥ 20/50/100%`, lay **trung vi** | `trailTrace.csv` (P0 = `tl-part`), hoac bars |
| M8 | `n_leg`, `leg/ngay`, `cum=so lan vao lenh` | dem | printDone |

**Cach tinh M2–M5:** dung chuoi `b:` NGAY tu `logs/sim.out` (moi bien the deu co `sim.out`), cung so ngay
⇒ so sanh truc tiep duoc. 🔴 Neu `sim.out` thieu ⇒ ghi RO, **khong** suy tu `SumPnL`.

### 3.4 TIEU CHI KET LUAN (chot TRUOC)

Tinh **hai xep hang** tren cung tap bien the:
- hang **CU**: theo `meanP` (thuoc ma 5 vong truoc dung lam tieu chi chinh);
- hang **MOI**: theo **Calmar (M4)** lam tieu chi chinh, kem `SumPnL` (M1) lam thu hai.

Doi chieu bang **Kendall tau** giua 2 xep hang (`n=7` bien the) va dem **so cap dao dau**
(cap A/B ma A > B theo thuoc CU nhung A < B theo thuoc MOI).

- **H2 = DUNG ("thuoc cu sai cho exit")** neu `tau <= 0` **hoac** co **>= 2 cap dao dau**
  trong so cac bien the **khac P0**.
- **H2 = SAI** neu `tau >= 0.5` va **<= 1 cap dao dau**.
- Trung gian ⇒ ghi "phu thuoc thuoc do", neu ro.

### 3.5 Gioi han (ghi TRUOC, khong phai bao chua sau)

1. M2–M5 tinh tren `b:` **ngay** (khong phai phut) ⇒ `maxDD` la **can duoi** cua maxDD that; Calmar vi
   vay la **can tren** — du de SO SANH giua cac bien the (cung mot do phan giai), **khong** duoc doc
   nhu maxDD/CAGR tuyet doi.
2. `SumPnL` la **tong PnL tung leg**, KHONG phai equity (khong compound) — giong gioi han §5.1 cua
   `RESULT_EXIT_FIT`.
3. M7 chi tinh duoc cho bien the co `trailTrace.csv` (P0=`tl-part`, L1/L2/L3, F3=`pc-close`);
   hinge V1/V2/V3 **khong co** `trailTrace.csv` ⇒ ghi **RO** (khong suy dien).
4. Moi so la **in-sample DEV**; khong ket luan forward.

## 4. Ket qua se ghi vao

`docs/RESULT_CAPACITY_DIAG.md` (+ trung gian `/home/ubuntu/capdiag/`). Commit, **khong push**.
