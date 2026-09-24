# RESULT_SIZEPROBE — chan doan sizing sim + so giay C3 (diagnostic-only)

Ngay: 2026-09-12. Code: branch `module`, build tu HEAD + 1 dong log `[SIZE]` (guarded).
Baseline canonical: `X1_C3_FULL_PARITY_R`, profile `profiles/x1_c3_full.properties`,
sim `SimulatorMarketLevelTicker1MStopLoss`, dataset `/home/ubuntu/wfo_ds_x1`, `SIM_END_DATE=20251231`.
KHONG sua mot dong logic sizing nao. Chi THEM 1 dong log (chi in). KHONG cham 242. KHONG push.

## 0. Cong parity gate (BAT BUOC) — PASS
Chay lai sim voi jar da build (co log `[SIZE]`, bat `SIZE_PROBE=1`) vao thu muc moi
`devrun/X1_C3_FULL_SIZEPROBE`:

| file | md5 | ky vong | ket qua |
|---|---|---|---|
| printDone.csv (nguyen file) | `2478e90d4e6147bf4cc64f75967ef47d` | `2478e90d...` | KHOP |
| printDone.csv (bo header) | `e13bc39e625b8d2ceebb7b9194f7f4f0` | `e13bc39e...` | KHOP |
| n dong (bo header) | 2266 | 2266 | KHOP |
| equity cuoi (b:) | 111428 | 111428 | KHOP |

=> Dong log `[SIZE]` KHONG doi hanh vi so. Byte-identical. Cong parity **PASS**.

## 1. Cong thuc sizing THAT cua sim (doc code + do bang [SIZE])
Duong code: `SimulatorMarketLevelTicker1MStopLoss.java:977-1016`.

    marginRunning = BudgetManagerSimple.marginRunning
    balanceBasic  = equityNow()                          (SIM_FIX_B3=true -> compound)
    budget = TradeUtils.managerBudget(...)               (:988)
           = balanceBasic * F_BASE * throttle / ladder   (TradeUtils.java:95)
    budget *= tierMultiplier                             (:996)
    if (DCA_GRID_ENABLED) budget *= gridLegWeightRatio(legIdx)   (:1012)
    quantity = calQuantityTest(budget, leverage, entry) (:1017)

Hang so (profile x1_c3_full + Configs):
- `F_BASE = 0.03`, `U_MAX = 0.60`
- `throttle = clamp(1 - (marginRunning/equity)/U_MAX, 0, 1)`
- `ladder = dcaGridTotalWeight() = 13`  (DCA_GRID_WEIGHTS=1,1,3,8)
- `tierMultiplier = 1.0`  (TIER_FLAT=1)
- `gridLegWeightRatio(legIdx)`  voi **SIM_FIX_B2=true** (DcaUtils.java:70):
  tra `w[legIdx] * DCA_GRID_SCALE`  (KHONG chia /total) -> leg0/1 = 1*19.5 = **19.5**, leg2 = 3*19.5 = 58.5, leg3 = 8*19.5 = 156.
- `LEVERAGE_ORDER = 1` -> `calQuantityTest: qty = budget/entry`; `calMargin = qty*entry/lev = budget`.
  => **`budget` chinh la MARGIN cua 1 leg, va notional == margin** (khong co don bay, khong nham notional-vs-margin).

**Cong thuc mot leg (thuc te):**

    margin_leg = equity * 0.03 * throttle / 13 * 1.0 * gridLegWeightRatio(legIdx)
    leg0: margin_leg = equity * 0.03 * throttle / 13 * 19.5 = equity * 0.045 * throttle  = 4.5% * throttle

## 2. Phan ra 7.2x — tung nhan tu, so do bang [SIZE] (n=2266 leg, 1 dong/leg)

Do tu 2266 dong `[SIZE]` (khop 1:1 voi 2266 dong printDone):
- `fbase` = 0.03 (hang so, moi dong)
- `ladder` = 13.0 (hang so)
- `tier`  = 1.0 (hang so — TIER_FLAT co hieu luc)
- `ratio` phan bo: **19.5 x 2254 leg**, 58.5 x 11 leg, 156.0 x 1 leg (nang leg2/leg3 hiem)
- `throttle`: **mean 0.559, median 0.569**
- `pct = margin_leg/equity`: **mean 2.535%, median 2.567%**  (khop do doc 1.2: printDone 2.498%)
- Kiem tra dong nhat: `budget == equity*fbase*throttle/ladder*tier*ratio`, sai so tuyet doi max = 0.001 (lam tron qty).

**Nguon goc "7.2x" (so voi con so 0.346% ma docs/L8 tinh):**

Docs/L8 GIA DINH `gridLegWeightRatio(leg0) = (w0/total)*SCALE = (1/13)*19.5 = 1.5`
(day la nhanh **SIM_FIX_B2=false**). Suy ra "nominal 0.346% * throttle".
NHUNG profile chay **SIM_FIX_B2=true**, nen `gridLegWeightRatio(leg0) = w0*SCALE = 19.5`
(nhanh nay BO lan chia /total; xem comment B2 trong DcaUtils.java) -> **lon gap 13 lan** gia dinh cua L8.

    nhan tu 1 (ratio): 19.5 / 1.5 = 13.000       <- SIM_FIX_B2=true bo lan chia /total(=13)
    nhan tu 2 (throttle thuc): mean = 0.559       <- do duoc
    tich: 13.000 * 0.559 = 7.27x                  (do truc tiep pct_mean/0.346% = 7.32x)

    Kiem chung tuyet doi:
      nominal leg0 @throttle=1 = equity*0.03/13*19.5 = equity*0.045 = 4.5%
      * throttle mean 0.559                       = 2.52%  (do: 2.535%)  KHOP
      L8 nominal (ratio 1.5, throttle=1)          = 0.346%
      2.535% / 0.346% = 7.32x                     KHOP ~7.2x

**Ket luan (2.):** 7.2x = **13 (SIM_FIX_B2=true: gridLegWeightRatio tra w*SCALE thay vi (w/total)*SCALE)**
x **~0.56 (throttle thuc te trung binh)**. KHONG phai leverage (=1), KHONG phai tier (=1.0),
KHONG phai nham notional-vs-margin (bang nhau khi lev=1), KHONG phai compounding.
Sai lam cua L8 la doc nhanh FIX_B2=false trong khi run bat FIX_B2=true, va so con so throttle=1 voi
con so da co throttle. Duong sizing van dang chay DUNG y do (moi coin ~ 1 suat 4.5%*throttle, rai theo grid).

## 3. (B) So giay C3 — bo leg2+ cung coin (xac nhan co che)
File: `ShadowBookC3.java:194-203`.

    public void openPos(String symbol, ...) {
        Pos p = new Pos(...);
        if (open.putIfAbsent(symbol, p) == null) {   // <-- open la Map<String,Pos>
            nOpen++; saveState(); LOG.info("[SHADOW] open ...");
        }
        // else: leg p bi VUT — khong log, khong dem, khong VWAP lai, khong ap ti trong 1:1:3:8
    }

Xac nhan: `open` la `Map<String,Pos>`; khi da giu coin do, `putIfAbsent` tra Pos cu (khac null) ->
nhanh `if` bi bo qua -> leg thu 2+ **bi bo im lang**. `Pos` khong co `legCount`/`avgEntry`/`firstEntryPrice`
nen khong the gop cum. `marginRunning()` cong theo `open.values()` -> chi dem 1 leg/coin.
Duong vao van goi day du (DetectEntry :289/:303/:324/:394) nhung so giay vut leg DCA/BIG_DOWN.

Do lon (do tren chinh backtest, docs/L8 muc 2.2): 2 sleeve so giay khong tai lap duoc
(`BIG_DOWN` 9884.4 + `DCA_LEVEL1` 7407.3) = **17291.7 / 76428.4 = 22.6%** pnl.

### Fix DE XUAT (chua code, chi chu)
Doi `open` sang `Map<String, Cluster>` (Huong B trong L8): `Cluster` giu `avgEntry(VWAP)`, `legCount`,
`firstEntryPrice`, `tsFirstLeg`; `openPos` KHONG dung `putIfAbsent` ma **cong leg vao cluster + tinh lai VWAP**;
`marginRunning()` cong theo cum. BAT BUOC kem 1 unit test "cung chuoi leg => cung avgEntry/legCount/quyet dinh
arm/time-stop" doi chieu voi lop vi the cua sim (mergeOrder/OrderTargetInfoTest), de khong lai tao 2 ban sao
logic cum troi nhau (loi da gay L6/L7). KHONG lam chung dot voi parity gate.

## 4. Sai lech pre-reg / ghi chu
- Da lam DUNG diagnostic-only: khong sua sizing, chi them 1 dong log guarded.
- Dong log `[SIZE]` GIU LAI trong code (guarded boi env `SIZE_PROBE=1`, mac dinh TAT -> byte-identical
  da chung o muc 0). Vi tri: `SimulatorMarketLevelTicker1MStopLoss.java` ngay sau `budget *= ratio;`.
  Ly do giu: la cong cu do lai (verify) cho lan sua sizing sau; vo hai khi tat.
- Sim ket thuc voi shell rc=1 (clamp/shutdown cuoi run) NHUNG printDone day du 2266 dong, equity 111428,
  md5 byte-identical baseline -> khong anh huong parity (baseline canonical cung sinh cung duong).
- (B) chi CHAN DOAN + de xuat bang chu, khong code fix (dung pre-reg).
