# DESIGN_HEDGED_BOOK — thiet ke de xuat (TASK 2), DUNG o cong Buoc 1

Ngay: 2026-09-20. Che do: **RECON ONLY** (doc code, khong sua code logic, khong chay sim).
Trang thai: 🔴 **BLOCKED AT GATE — cho Uni duyet thiet ke truoc khi code.**

Nhiem vu goc: HEDGED_BOOK = long top-k S1 + SHORT BTCUSDT perp theo beta, nham giam
tuong quan CHEO-LENH trong ngay (`ICC = 0.247`, tran ~4 cuoc doc lap/ngay,
`docs/NBETS_RESULT.md`) de tang `n_eff` va thu hep CI cho moi phep so sanh selector
ve sau (`docs/power_wall.md`).

## 0. TL;DR — tai sao DUNG

Cong dung Buoc 1 yeu cau DUNG neu **(i)** uoc tinh >~400 dong **HOAC** **(ii)** phai
cham vao loi co che sizing/margin hien co. **CA HAI deu kich hoat:**

- **(i)** Uoc tinh **630–870 dong** Java moi/sua (bang chi tiet muc 3). > 400.
- **(ii)** Mot hedged book DUNG NGHIA **bat buoc** chay qua `BudgetManagerSimple.equityNow()`
  (goc sizing) va `marginRunning` (→ `throttle` → admission). Do KHONG phai "them mot leg
  doc lap ben canh" — do la doi goc sizing cua TOAN BO sach long. Chi tiet muc 4.

Ngoai ra recon phat hien mot **phuong an RE HON NHIEU (A — OVERLAY)** tra loi DUNG cau hoi
nghien cuu cua TASK 2 voi **~0 dong Java**, va co uu the KHOA HOC (counterfactual sach,
khong confound). Khuyen nghi: chay A truoc; chi build B (Java) neu A cho ket qua duong.

Toan bo so lieu duoi day la **doc code / doc file**, chua chay bat ky sim nao.

## 1. Tra loi 3 cau hoi recon bat buoc

### (a) Sim co mo duoc vi the SELL doc lap khong (khong qua `ENABLE_SHORT`)? — **KHONG**

- `SimulatorMarketLevelTicker1MStopLoss.java:353` con nguyen comment:
  `{   // co ENABLE_SHORT da go 2026-09-03 (long-only)`.
- `ENABLE_SHORT` / `SHORT_SL_PCT` / `SHORT_TIME_STOP_HOURS` **KHONG con trong
  `tradecore/Configs.java`**; chung chi con trong file backup **khong compile**
  `Configs.java.bak_cfg` (dong 476–489).
- Git history: `8d93f93` (them order-side SHORT, flag-gated) → `df542c5` (wire ENTRY short
  `createOrderSELL` vao selector) → **`5f40a90` "refactor(engine): xoa 40 co-che TRO"** da go
  toan bo. Moi call-site con lai trong sim chi goi `createOrderBUY(...)`
  (dong 349, 357, 375, 411). **Khong co `createOrderSELL`.**
- Khop voi `docs/RESEARCH_SHORT.md` muc 1.1 (2026-09-14) — tai lieu do ket luan y het.

**He qua:** phai VIET LAI duong ENTRY short. PnL hai chieu thi van con
(`OrderTargetInfoTest.calTp()` co nhanh `side == OrderSide.SELL`), nhung do la TAT CA
nhung gi con lai.

### (b) Funding co duoc tinh cho vi the SELL khong? — **CO ha tang, nhung DAU SAI cho hedge**

- Funding **DANG BAT** o T170: `profiles/x1_gs_t170.properties` co `SIM_APPLY_FUNDING=true`
  va `SIM_FUNDING_MARK=true` (mac dinh Java la `APPLY_FUNDING_FEE=false`, profile bat len).
  => sach long hien tai **da** chiu phi funding. Khong co bat doi xung "long mien phi".
- 🔴 **Dau cho SELL la SAI so voi Binance that.** `OrderTargetInfoTest.computeFundingOnClose()`
  dong 326–333 ghi ro (comment DRAFT 2026-07-18):
  > "short TRA khi funding duong -> feeTotal DUONG khi rate>0 (giong long), calTp(SELL) van
  > tru calFundingFee() -> short BI TRU khi funding duong (mo hinh BAO THU/pessimistic)...
  > ⚠️ REVIEW-POINT: funding THUC te cua Binance = SHORT NHAN khi funding duong."
- **Vi sao day la van de LON, khong phai chi tiet nho:** hedge BTC la vi the giu LIEN TUC
  48 thang. Funding BTC perp duong phan lon thoi gian => short BTC **NHAN** funding, va do la
  mot nguon thu DANG KE cho hedge. Mo hinh no thanh CHI PHI se **dao dau** mot trong nhung so
  hang lon nhat cua thi nghiem, va se lam hedge trong te hon thuc te mot cach co he thong.
- **Nguon du lieu funding — DINH CHINH de bai:** de bai neu `label_15m/funding_label_*.pb`
  hoac `claudedata/funding_lf.bin`. Ca hai file **co ton tai**, nhung **KHONG cai nao la nguon
  funding rate cua sim**:
  - `label_15m/funding_label_*.pb` = **LABEL dataset** (meta: `hNames [4h,12h,24h,72h]`,
    `emittedRows 50,873,458`, 828 coin) — day la nhan forward-return cho ML, **khong phai
    funding rate**.
  - `claudedata/funding_lf.bin` (479 MB) = binary feature/label dan xuat.
  - 🟢 **Nguon THAT ma engine dung la Aerospike**: `FundingFeeManager.initData()` goi
    `DataManagerAerospikeFloatSim.getAllFundingMap()`, va `getFundingHistory(symbol)` goi
    `DataManagerAerospikeFloatSim.getFundingMap(symbol)`. Bat ky mo hinh chi phi hedge nao
    cung **phai** lay funding BTCUSDT tu day de dong nhat voi chan long.

### (c) Co san cho de ghep "portfolio-level leg" khong? — **KHONG, phai them khai niem moi**

Toan bo state vi the trong sim **duoc dia chi hoa bang `symbolId`**:

- `OrderTargetInfoTest[] symbol2OrderRunning = new OrderTargetInfoTest[1000]`
- `List<OrderTargetInfoTest>[] symbol2OrdersEntry = new ArrayList[1000]`
- `short[] activeRunningIds` + `activeRunningCount`, `isSymbolRunning(short id)`

Khong co bat ky khai niem "vi the khong thuoc coin do selector chon". Hau qua cu the:

1. **Va slot symbol.** BTCUSDT co `symId = 1` (`selector_pred_out/symbol_map.csv`) va NAM
   TRONG universe. Mot hedge leg dat vao `symbol2OrderRunning[1]` se lam `isSymbolRunning(1)`
   tra `true` VINH VIEN => selector **khong bao gio** mo duoc long BTCUSDT nua.
   (Do thuc te: T170 `printDone.csv` co **0 dong** BTCUSDT tren 1,089 lenh / 358 coin — nen
   rui ro nay hien **khong bind**, nhung no la rang buoc CAU TRUC, khong phai su that vinh vien.)
2. **O nhiem `printDone.csv`.** Cuoi ky, moi `OrderTargetInfoTest` con mo deu duoc day vao
   `allOrderDone` roi ghi ra `storage/printDone.csv` (`Simulator...:550`). Hedge leg se thanh
   nhung DONG MOI trong file do. **Moi script cham diem deu gia dinh 1 dong = 1 lenh selector**:
   `research/analysis/x1_rates.py`, `c3_rates.py` (`trades()`), `qret_ladder.py`,
   `java/fsrun/qret.py`, va `beta_decomp_t170.py` (TASK1). Them dong hedge = **pha het**,
   va pha AM THAM (khong loi, chi ra so khac).
3. **`VolTargetSizing` KHONG phai tien le.** No la portfolio-level **MULTIPLIER** (mot so
   `float` nhan vao budget), khong phai portfolio-level **POSITION**. No khong giu state vi the,
   khong mark-to-market, khong an margin. Khong tai su dung duoc cho hedge.

## 2. Khac biet voi hai huong da dong (de khong lap lai nham)

- **`docs/RESEARCH_SHORT.md`** (short-only mirror, DA DONG): ket luan "KHONG dang build short
  duoi dang mirror cua top-8 BUY" — vi edge long BAT DOI XUNG (pump-lottery), soi guong ra
  gross ~0% roi am sau cost. **Nhung chinh tai lieu do muc 0 ghi:** "Chi dang xem xet lai NEU
  muc tieu la **market-neutral hedge (giam beta)** chu khong phai alpha short doc lap — va do
  la **scope khac han**." => TASK 2 nam dung trong cai ngoai le do. Khong mau thuan.
- **`ENABLE_SHORT`**: co DAO TIN HIEU (chon high-score thay vi low-score) — da go khoi engine.
  Hedge BTC **khong dung selector chut nao**: no la mot leg co dinh tren MOT symbol, size theo
  beta cua danh muc. Khac han ve ban chat.

## 3. Uoc luong dong code (duong Java — Phuong an B)

| Hang muc | Dong | Ghi chu |
|---|---|---|
| `tradecore/HedgeBook.java` (moi) | 300–400 | state vi the, rebalance 20%/4h, mark-to-market moi tick, funding accrual dau dung, taker fee 0.05%, slippage 1bp, ledger |
| `tradecore/HedgeBeta.java` (moi) | 90–130 | beta rolling 30d CAUSAL (V2); nap BTC 1h tu `CLOSES_1H.bin` |
| `tradecore/Configs.java` | 12–15 | `HEDGE_MODE` (OFF/V1/V2), `HEDGE_BETA_TARGET`, nguong rebalance |
| `research/BudgetManagerSimple.java` | 40–60 | hedge PnL vao equity, hedge notional vao margin, chuoi equity/quy/DD |
| `research/SimulatorMarketLevelTicker1MStopLoss.java` | 50–70 | hook moi tick (mark + rebalance), flush cuoi ky, ghi ledger |
| `research/OrderTargetInfoTest.java` (SUA) | 15–25 | **fix dau funding cho `side == SELL`** (code DUNG CHUNG voi long) |
| Ledger/export writer | 40 | `storage/hedge_ledger.csv` RIENG, **khong dung** `printDone.csv` |
| Unit test (chuan du an: cong hoi quy) | 100–150 | OFF byte-identical, rebalance trigger, dau funding, so hoc beta |
| **TONG** | **647–890** | **>> 400** |

## 4. Diem cham vao LOI (dieu kien (ii) cua cong dung)

Day la phan quyet dinh, khong phai phan uoc luong.

1. 🔴 **`equityNow()` — goc sizing.** `BudgetManagerSimple.equityNow() = balanceCurrent + unProfit`
   la GOC cua `budget = equity x F_BASE x throttle x DCA_GRID_SCALE x w[i]/total`
   (`Simulator...:1290`). Hedge PnL (lai/lo + funding nhan/tra) **phai** chay vao equity, neu
   khong thi khong phai mot "book". Ma vao equity => **doi size cua MOI lenh long**.
2. 🔴 **`marginRunning` → `throttle` → ADMISSION.** `throttle = 1 - marginRunning/(equity x U_MAX)`
   va `TradeUtils.managerBudget(...)` tra `null` khi `u >= U_MAX` => **chan lenh**. Hedge notional
   an margin => `u` tang => mot so tick sat tran von **LAT** quyet dinh admission.
   `docs/AGENT_RUNBOOK.md` muc 4 da ghi nhan chinh xac co che nay o L1: doi exit → doi
   `marginRunning` → doi `throttle` → doi `n` (2,058 → 2,056/2,077). Hedge se lam manh hon nhieu.
3. 🔴 **Code funding DUNG CHUNG.** Sua dau cho `side == SELL` la sua trong
   `computeFundingOnClose()` / `accrueFundingMark()` — dung ham ma **moi lenh long** dang goi.
   Rui ro pha `md5 efb793e2` ngay ca khi `HEDGE_MODE=OFF`.

**He qua khoa hoc nghiem trong cua (1)+(2):** o Phuong an B, V1/V2 **khong chi them hedge** —
chung con **doi tap lenh long duoc chon**. Khi do neu ICC giam, ta **khong tach duoc** bao nhieu
la do hedge va bao nhieu la do sach long da khac di. Do la confound o ngay bien do chinh.

## 5. HAI PHUONG AN

### Phuong an A — OVERLAY (khuyen nghi chay TRUOC). Java: ~0 dong.

Hedge la mot lop PHU tinh tren ngoai engine, **khong** an margin, **khong** vao `equityNow()`.
Sach long giu **byte-identical** voi T170 (`md5 efb793e2` — cong OFF thoa **hien nhien**).

Tai sao du du lieu (da kiem tra):
- `printDone.csv` cua T170 co `start`, `end`, va cot **`margin` THUC RA la NOTIONAL**
  = `quantity x priceEntry` (`beta_decomp_t170.py` da xac minh va tai su dung dung cot nay).
  => **Σ notional long dang mo tai moi thoi diem t tai lap duoc CHINH XAC.**
- Gia BTC 1h: `java/fsrun/CLOSES_1H.bin`, `symId = 1`, loader san
  `research/analysis/trend_rank_ic.py::load_closes()`.
- Funding BTCUSDT: Aerospike (muc 1b) — dump 1 lan ra file de python doc.
- Beta rolling 30d: tai su dung **nguyen van** `research/analysis/beta_decomp_t170.py`
  (TASK1, commit `61a7fc7`), doi cua so tu FULL sang rolling, chi dung du lieu <= t.

Cach do 5 metric:
- **(a) ICC / n_eff**: phan bo hedge PnL **pro-rata theo notional x thoi gian** ve tung lenh long
  (`roi_hedged_i = roi_i + hedge_pnl_share_i / notional_i`), roi chay lai dung cach tinh ICC cua
  `docs/NBETS_RESULT.md` muc 264–267 (`x_i = pnl_i/margin_i`, ANOVA mot chieu, cohort = ngay vao
  lenh, `n_eff(k) = k / (1 + (k-1)*ICC)`). Day la phan **can pre-reg ky nhat** — cong thuc phan bo
  phai chot TRUOC.
- **(b) Sharpe ngay + CI bootstrap**: tu chuoi equity hedged (equity T170 + hedge PnL tich luy).
- **(c) beta sau hedge**: `beta_decomp_t170.py` ap len equity moi.
- **(d) maxDD/UW**: `java/fsrun/qret.py` tren chuoi equity moi.
- **(e) MDE80**: chay lai cap **T170-vs-T100** duoi hedge (chon cap nay vi `docs/ANALYSIS_T170_VS_T100.md`
  da co san ca hai devrun + script cham diem; S1-vs-G015 phai chay lai sim).

Han che phai ghi thang vao RESULT: A gia dinh hedge **khong** phan hoi vao sizing/admission.
Do la **counterfactual** ("neu da hedge thi chuoi PnL se ra sao"), khong phai mot he da chay that.
Doi lai: khong confound, va **do dung cai TASK 2 hoi** — hedge co lam CI cua so sanh selector hep
lai khong.

### Phuong an B — FULL BOOK (Java). 647–890 dong, cham loi.

Hedge la vi the that: an margin, vao equity, phan hoi vao admission. Thuc te hon cho live,
nhung (i) vuot cong dong, (ii) confound muc 4, (iii) can them cong parity rieng cho phan
funding-sign dung chung.

Neu Uni duyet B, thiet ke de xuat:
- `HedgeBook` la **singleton song song**, **KHONG** dung `symbol2OrderRunning[]`
  (tranh va slot symId 1 va o nhiem `printDone.csv`).
- Ledger rieng `storage/hedge_ledger.csv`; `printDone.csv` **tuyet doi khong them dong**.
- `HEDGE_MODE=OFF` => khong nhanh nao chay, khong cap phat => cong `md5 efb793e2`.
- Fix dau funding SELL phai co unit test rieng + chay lai cong repro T170 truoc khi tin so nao.

## 6. Rui ro breaking change (doc lap voi phuong an)

1. **`printDone.csv` la interface ngam cua ~6 script cham diem.** Them cot/dong = pha am tham.
   Runbook da ghi 2 lan "KHONG them cot vao printDone.csv (se pha cong hoi quy byte-identical)".
2. **Dau funding SELL** nam trong code dung chung voi long (muc 4.3).
3. **Hedge rebalance roi rac (20% / 4h)** de lot gap giua hai lan rebalance — **dung muc dich do**,
   phai bao cao chu khong duoc noi long tham so de "cuu" ket qua.
4. **Short BTC trong 2023–2025 (BTC tang manh) se cat phan lon CAGR lich su** — **dung muc dich do**.
   CAGR **khong** phai metric chinh cua TASK 2.
5. **Funding BTC perp** keo dai duong/am co the tro thanh so hang lon nhat cua ket qua; voi dau
   DUNG thi short BTC **nhan** funding phan lon thoi gian => rui ro **thoi phong** hedge neu khong
   tru phi/slippage day du. Phai mo hinh ca hai chieu, ghi gia dinh vao pre-reg.
6. **Chi phi tinh toan**: moi sim run T170 ~13 phut; Oracle chi 1 slot JVM. Phuong an B can toi
   thieu 3 run (OFF + V1 + V2) + cac run cua cap MDE80 => >1 gio sim TUAN TU, chua ke build/debug.

## 7. Can Uni quyet (3 cau, khong tu quyet)

1. **Chay Phuong an A truoc (overlay, ~0 dong Java) hay di thang Phuong an B (Java, ~650–890 dong)?**
   Khuyen nghi cua agent: **A truoc**. Re hon nhieu bac, khong cham loi, khong confound, va tra loi
   dung cau hoi power. B chi dang lam neu A cho ket qua duong (beta ve ~0, ICC giam, CI hep lai).
2. **Neu B: co chap nhan sua dau funding cho `side == SELL` trong code DUNG CHUNG voi long khong?**
   (Bat buoc phai co, neu khong hedge bi mo hinh sai mot cach co he thong.)
3. **Cong thuc phan bo hedge PnL ve tung lenh de tinh ICC** — pro-rata theo `notional x thoi gian`
   la de xuat cua agent. Can Uni chot **TRUOC** khi chay, vi day la bac tu do duy nhat con lai
   ma nguoi chay co the vo tinh dieu chinh sau khi thay so.

## 8. Da KHONG lam (dung ky luat)

- KHONG sua bat ky file `.java` nao.
- KHONG chay sim (cong repro T170 chua chay — dung theo cong dung, khong ton 13 phut JVM).
- KHONG viet `docs/PREREG_HEDGED_BOOK.md` (pre-reg chi duoc chot SAU khi kien truc duoc duyet).
- KHONG dung toi `shadow-c3` (dang DOWN, Uni xu ly rieng), khong SSH 242, khong `git push`,
  khong mo HOLDOUT 2026.
