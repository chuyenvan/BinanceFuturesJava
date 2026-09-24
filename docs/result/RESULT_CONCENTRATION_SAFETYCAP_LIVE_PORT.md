# RESULT — PORT 2 guard CONC-CAP sang duong LIVE

> Nen: spec goc `docs/prereg/PREREG_CONCENTRATION_SAFETYCAP.md`; ban SIM da verify parity 6/6 tai commit
> `5e82983` (`docs/result/RESULT_CONCENTRATION_SAFETYCAP.md`); bao cao chan Buoc 0 + 3 cau hoi tai
> `docs/diag/DIAG_CONCENTRATION_SAFETYCAP_LIVE_PORT_BLOCKER.md` (`873c7f5`).
>
> **MASTER da chot ca 3 cau** (tu so = tu track theo TUNG leg; co "dang DCA" = suy tu chinh
> structure do; mau so = `walletBalance` doc rieng, KHONG dung `balanceBasic`). Tai lieu nay ghi
> lai ban da lam theo dung quyet dinh do.
>
> ## ⚠️ 4 FLAG VAN DEFAULT **OFF** TREN LIVE
> `CONC_CAP_AGG_DCA_ENABLED=false` · `CONC_CAP_BD_RATE_ENABLED=false`.
> **Code da vao nhung guard CHUA hoat dong.** User phai **TU BAT BANG TAY** trong profile/config
> production khi san sang. Khong co gi tu dong bat.

---

## 1. Hai structure moi

Ca hai nam trong **mot lop moi duy nhat**:
`src/main/java/com/binance/chuyennd/tradecore/ConcCapLiveGuard.java` (singleton,
`ConcCapLiveGuard.getInstance()`).

**Vi sao tach lop rieng thay vi nhet het vao `DetectEntrySignal2TradeNormal`:** lop do phu thuoc
Redis + Binance client nen **khong unit-test duoc**. Toan bo trang thai va phep quyet dinh cua guard
la **ham thuan, khong I/O**, nen dat rieng de co test THAT (yeu cau muc 3 cua de bai) — cung khuon
voi `ShadowBookC3` / `LegacySymbols` da co. `DetectEntrySignal2TradeNormal` chi goi 6 ham cua lop nay.

### 1.1 Guard 1 — `symbol2DcaLegMargin`

```java
private final Map<String, List<Float>> symbol2DcaLegMargin = new HashMap<>();
```

| | |
|---|---|
| Ban chat | `symbol` -> margin cua **TUNG leg** DCA-grid bac>=1 dang mo cua symbol do |
| Ghi | `recordDcaLeg(symbol, margin)` — goi **sau khi order da thuc su duoc day di** (Redis queue / `shadowHandleOrder`), khong dem ung vien bi loai |
| Doc | `aggDcaLegMargin()` = cong don **toan so** |
| Co "dang o bac DCA>=1" | `isInDcaTier(symbol)` = symbol co it nhat 1 entry trong list. **KHONG dung `BudgetManager.symbol2Level`** (co do bi ghi de boi level lenh moi nhat `BinanceOrderTradingManager:181` va bi XOA sau 30 phut `:326-330`) |
| Don rac | `retainSymbols(BudgetManager.symbol2Pos.keySet())` — goi **truoc moi lan doc aggregate**. Cum dong xong bien mat. **Bat buoc**: thieu buoc nay thi structure chi phinh ra va guard se binding NHAM roi chan lenh that |
| Quyet dinh | `blockDcaLeg(legNewMargin, equity)` = `(agg + legNewMargin) / equity > CONC_CAP_AGG_DCA_PCT` (dau `>`, dung spec, khong phai `>=`) |

**KHONG dung `PositionHelper.callMargin`** (margin ca cum da gop) — da xac nhan lech **1.08x-2.00x**
so voi dai luong da verify ben sim (BLOCKER muc 3.1).

### 1.2 Guard 2 — `bdOpenTimes`

```java
private final ArrayDeque<Long> bdOpenTimes = new ArrayDeque<>();
```

| | SIM | **LIVE (ban nay)** |
|---|---|---|
| Moc thoi gian | `ticker.startTime` (thoi gian sim) | **`System.currentTimeMillis()`** (dong ho that) |
| Reset | `concBdOpenTimes = null` trong `initData()/initDataReady()` | **KHONG co reset** — cua so **tu troi**: moi lan doc thi `pollFirst()` het cac moc `<= now - 60 phut` |
| Ghi | sau `orders.add(order)` | `recordBigDownLeg(now)` sau khi order da day di that |
| Quyet dinh | `nBd >= CONC_CAP_BD_PER_HOUR` | `blockBigDownLeg(now)`, cung dau `>=` |

### 1.3 Mau so — `BudgetManager.liveEquitySnapshot`

```java
public static volatile Float liveEquitySnapshot = null;
```

Gan **DUNG MOT CHO**, ngay canh dong da co san trong `BudgetManager.updateBudget()`:

```java
Float balanceCurrent = umInfo.getWalletBalance().floatValue();
liveEquitySnapshot = balanceCurrent;          // <- them
BUDGET_PER_ORDER = balanceBasic / Configs.number_order_budget;   // <- KHONG doi
```

Khong them mot API call nao (tai su dung `getAccountUMInfo()` von da goi va truoc day **chi de ghi
log**). Nhip cap nhat = nhip san co cua `updateBudget()` (luc khoi tao + moi gio) — du cho mot
safety-net, dung nhu MASTER da chot.

---

## 2. Diem chen — MOT phieu duy nhat, doi xung voi ban sim

`DetectEntrySignal2TradeNormal.createOrderBuyRequest`, **ngay sau**
`if (quantity != null && quantity != 0) {`, **truoc** `new OrderTargetInfo(...)`.

Ca 3 nguon leg deu di qua day: BIG_DOWN/market-signal (`:289`), DCA-grid nhanh market-level (`:303`),
DCA-grid nhanh `isDcaAlt` (`:324`).

Tai diem nay da qua **toan bo** cong hien co: `prediction == null` -> `EntryGate` -> kill-switch mat
do -> `managerBudget`/`U_MAX` -> `TIER_3_SHITCOIN` -> `tierMultiplier` -> sizing `price_realtime` ->
`calQuantity`. Va **chua** co order nao ton tai, **chua** day vao Redis queue.

Margin du kien cua leg: `quantity * ticker.priceClose / Configs.LEVERAGE_ORDER` — **cung cong thuc
voi ban sim** (`quantity * entry / leverage`), va cung dung `ticker.priceClose` ma `OrderTargetInfo`
ghi vao.

Ghi nhan (`recordDcaLeg` / `recordBigDownLeg`) dat **sau** `rpush` Redis queue / `shadowHandleOrder`,
truoc `writeOrder2File` — chi dem leg **DA THUC SU gui di**.

---

## 3. FAIL-OPEN khi chua co equity — quyet dinh co chu dich

Neu `liveEquitySnapshot == null` hoac `<= 0` (API chua goi duoc / loi key), guard 1 **BO QUA va cho
lenh di**, kem mot dong `LOG.warn`.

Ly do: guard nay la **bao hiem khong binding tren lich su**. Bien mot su co doc API thanh "chan sach
moi leg DCA" la **doi chien luoc**, khong phai bao ve — va do la thay doi khong ai pre-reg. Huong sai
duoc chon la "bo sot", dong huong voi caveat restart da duoc MASTER chap nhan.

---

## 4. Build + test

| | |
|---|---|
| Lenh | `mvn -o package` (co test) |
| Ket qua | **BUILD SUCCESS** |
| Test | **Tests run: 146, Failures: 0, Errors: 0, Skipped: 0** |
| Truoc round nay | 137 test |
| Moi | **+9 test** trong `src/test/java/com/binance/chuyennd/tradecore/ConcCapLiveGuardTest.java` |

**Ha tang test cho luong live:** `DetectEntrySignal2TradeNormal` **khong** unit-test duoc (Redis +
Binance client + executor). Da **khong** dung framework moi. Thay vao do toan bo logic guard nam o
`ConcCapLiveGuard` (ham thuan) va duoc test that bang JUnit 4 san co — cung cach `ShadowBookC3Test`
dang lam. 9 case:

1. `defaultOff_khongChanGiCa` — nap trang thai cuc doan hon moi nguong, **ca 2 flag OFF => khong chan gi**.
2. `guard1_duoiNguongThiChoQua_vuotNguongThiChan` — 0.40 cho qua, 0.44 cho qua, **0.46 chan**.
3. `guard1_dungBangNguongThiKHONGChan_chiVUOTmoiChan` — dau `>` chu khong phai `>=`.
4. `guard1_failOpenKhiChuaCoEquity` — `equity <= 0` => khong chan.
5. `guard1_coDcaTier_suyTuStructure_khongDungSymbol2Level`.
6. `guard1_retainSymbols_bo_cum_da_dong` — cum dong => bien mat khoi aggregate, khong phinh mai.
7. `guard1_nhieuLegCungMotSymbolDeuDuocCong`.
8. `guard2_chanKhiDuNguong_vaCuaSoTuTroiTheoThoiGianThat` — du cap thi chan; **61 phut sau tu het chan**.
9. `guard2_chiDemLegTrongDungCuaSo60Phut`.

---

## 5. Chung minh khong dung vao sizing

`git diff --numstat` cua round nay:

```
12   0   src/main/java/com/binance/chuyennd/trading/BudgetManager.java
42   0   src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java
```

**Cot thu hai = 0 o CA HAI file: KHONG MOT DONG NAO BI XOA HOAC SUA — toan bo la THEM MOI.**
Suy ra truc tiep: `balanceBasic`, `BUDGET_PER_ORDER`, va moi dong cua duong sizing hien co **con
nguyen tung ky tu**. (Hai file con lai la file MOI: `ConcCapLiveGuard.java`, `ConcCapLiveGuardTest.java`.)

Doc lai bang lap luan: khi 2 flag = `false`, moi khoi guard deu la `if (Configs.CONC_CAP_*_ENABLED
&& ...)` => short-circuit ngay o dieu kien dau, khong ham nao cua `ConcCapLiveGuard` duoc goi, khong
cau truc nao duoc cap phat, khong bien nao cua luong cu bi doc/ghi. **Luong live khi flag OFF chay y
het truoc round nay.**

### Hoi quy duong SIM

Duong sim dung `BudgetManagerSimple` (khac lop voi `BudgetManager`), va `SimulatorMarketLevel...`
khong doi mot dong nao trong round nay. Van chay lai cong parity T170 tren build MOI de chac:

| run | profile | md5 `printDone.csv` | ky vong | ket qua |
|---|---|---|---|---|
| `CC_LIVE_PAR_T170` | `x1_gs_t170.properties` | *(xem muc 7)* | `efb793e2468ca3a7318da0f0ad23d4fc` | *(xem muc 7)* |

---

## 6. ⚠️ TRANG THAI FLAG — PHAI DOC TRUOC KHI DEPLOY

| flag | default | trang thai hien tai |
|---|---|---|
| `CONC_CAP_AGG_DCA_ENABLED` | `false` | **OFF** |
| `CONC_CAP_AGG_DCA_PCT` | `0.45` | (chi co tac dung khi flag tren = true) |
| `CONC_CAP_BD_RATE_ENABLED` | `false` | **OFF** |
| `CONC_CAP_BD_PER_HOUR` | `75` | (chi co tac dung khi flag tren = true) |

- **Code da vao nhung guard CHUA chay.** Deploy ban nay len live = **khong doi hanh vi gi**.
- Muon bat: khai bao `CONC_CAP_AGG_DCA_ENABLED=true` / `CONC_CAP_BD_RATE_ENABLED=true` trong
  **profile/config production**, do **user tu quyet dinh va tu lam**. Khong co co che tu dong bat.
- Nho ky luat `Cfg`: da dung `TRADING_PROFILE` thi 4 key nay **phai khai trong profile**, khong duoc
  dat qua env (tien to `CONC_CAP_` da nam trong `Cfg.TRADING_PREFIXES` tu commit `5e82983`).

### Hai caveat da duoc MASTER chap nhan, ghi lai de khong quen

1. **Restart mat trang thai.** Ca hai structure nam trong bo nho tien trinh. Sau restart chung rong
   => guard **long hon thuc te** cho toi khi co leg moi ghi nhan lai (guard 2: toi da 60 phut;
   guard 1: cho toi khi cac cum DCA cu dong het hoac co leg DCA moi). Huong sai la **bo sot**, khong
   phai **chan nham**.
2. **Guard 1 chi "thay" cac leg DCA do CHINH tien trinh nay mo.** Leg DCA mo truoc khi tien trinh
   khoi dong khong co trong aggregate.

---

## 7. Ket qua cong parity SIM — **PASS**

Chay lai baseline T170 tren build MOI (co code live-port), profile `x1_gs_t170.properties`,
harness `/home/ubuntu/k_runarm.sh`, dataset `wfo_ds_x1_2021`, `SIM_END_DATE=20251231`:

| run | n leg | equity `b:` | md5 `printDone.csv` | baseline | ket qua |
|---|---|---|---|---|---|
| `CC_LIVE_PAR_T170` | 1089 | 111,070 | `efb793e2468ca3a7318da0f0ad23d4fc` | `efb793e2468ca3a7318da0f0ad23d4fc` | **KHOP** |

=> Code live-port **khong cham mot bit nao** vao duong sim. Cong hoi quy chuan cua du an van xanh.

---

## 8. File thay doi

| file | loai | dong them / xoa |
|---|---|---|
| `src/main/java/com/binance/chuyennd/tradecore/ConcCapLiveGuard.java` | **MOI** | 172 / 0 |
| `src/test/java/com/binance/chuyennd/tradecore/ConcCapLiveGuardTest.java` | **MOI** | 183 / 0 |
| `src/main/java/com/binance/chuyennd/trading/BudgetManager.java` | sua | **12 / 0** |
| `src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java` | sua | **42 / 0** |

**KHONG dong vao**: `Configs.java` (4 flag da co tu `5e82983`), `Cfg.java`,
`SimulatorMarketLevelTicker1MStopLoss.java`, `DcaUtils`, `DcaProcessor`, `EntryGate`, `TradeUtils`,
`MarketBigChangeDetector`, `BinanceOrderTradingManager`, `PositionHelper`.
