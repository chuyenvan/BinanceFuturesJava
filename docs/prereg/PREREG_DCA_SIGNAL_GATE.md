# PREREG_DCA_SIGNAL_GATE — chia doi margin/lenh + DCA leg-2 THEO TIN HIEU (gate + top-K)

Viet va COMMIT TRUOC khi code mot dong nao. Khoa toan bo tham so tai day; KHONG tune lai sau khi thay ket qua.
KHONG cham box 242, KHONG git push, holdout 2026 NGUYEN VEN (SIM_END_DATE=20251231).

## 0. Cau hoi cua user
"Chia nho margin/lenh => san sang DCA voi margin do cua coin do khi no dang lo x% VA no nam trong top-K
(hoac dieu kien tuong ung khi vao lenh moi) => tu duy la gia tang so lenh => ti le loss se tang, dung DCA
de giam ti le nay xuong."

Nghia la phai tra loi TRUC DIEN bang so ba cau:
  (i)   so lenh tang bao nhieu % so voi T170?
  (ii)  ti le lenh lo RAW (moi leg tinh rieng) co TANG nhu gia thuyet khong?
  (iii) ti le lo HIEU DUNG o muc VI THE (sau khi DCA-signal gop/cuu) so voi T170 ra sao?
Chu khong chi tra loi qua CAGR/UW tong the.

## 1. Khac gi voi hai thu DA CO (bat buoc doc truoc)
(a) **Grid DCA hien co** (`DcaUtils.shouldDcaGrid`, DCA_GRID_LEVELS=-0.50,-0.75,-0.90, legs=3,
    weights 1,1,3,8, SCALE=19.5): nhoi MU theo % lo gia tren `firstEntryPrice`, KHONG dieu kien tin hieu,
    va chi o vung lo THAM HOA (-50% tro xuong). Tren wfo_ds_x1_2021 no chi ban 20 leg / 1089 leg (1.8%).
    => GIU NGUYEN, KHONG tat, KHONG sua. Thi nghiem nay phai chay DOC LAP voi no.
(b) **Thi nghiem #52 (RESULT_2X_HALFSIZE, def3db1)**: chia nho margin de mo THEM COIN MOI (lenh doc lap).
    FAIL ca 3 config: UW 92 -> 221-223 (vi pham tran 120), CAGR 29.27 -> 21.4-24.0.
    => Bai nay KHONG lap lai: von du tru KHONG duoc day sang coin khac, chi duoc nhoi lai CHINH coin do.

Diem khac cot loi: leg-2 o day chi ban khi symbol DOC LAP pass DUNG pipeline admit lenh moi
(S1 ranker top-K + EntryGate dyn_thr scale 1.70) tai tick hien tai => loc theo TIN HIEU MO HINH,
khong phai luoi gia mu, va o vung lo NONG (-5/-8/-12%) chu khong phai -50%.

## 2. Diem code THUC TE (doc code truoc khi thiet ke — co SAI KHAC voi mo ta ban dau, ghi ro o day)
- Duong SIM la `research/SimulatorMarketLevelTicker1MStopLoss.java`, KHONG phai
  `trading/DetectEntrySignal2TradeNormal.java` (do la duong LIVE). Hai duong dung CHUNG cong gate
  (`AIRejectFilter.entryGate` -> `tradecore.EntryGate`) nhung vong chon ung vien la rieng.
- Vong chon ung vien moi tick: `SimulatorMarketLevelTicker1MStopLoss.java` ~ dong 340-378.
  `chosenCands` = K phan tu dau cua `symbol2Pred` (da sort tang theo pNoPump) khi SELECTOR_RANK_TOPK>0
  (profile T170: K=8). `selRank` 1-based dem tren TOAN pool da chon (cap-then-skip).
- **Noi loc "da co vi the thi loai khoi ung vien" chinh xac la** `if (!isSymbolRunning(targetId))`
  (dong ~367). Day la diem RE NHANH duy nhat can sua. KHONG viet lai phep tinh rank/gate.
- Cong gate + sizing + tao leg + merge cum nam trong `createOrder(...)` (dong ~945-1105):
  `aiRejectFilter.entryGate(predict, symbolPred, isPredictSymbolTrade)` -> `TradeUtils.managerBudget`
  -> khoi `if (Configs.DCA_GRID_ENABLED) { legIdx = cur.size(); budget *= gridLegWeightRatio(legIdx) }`
  -> `orders.add(order)` -> `mergeOrder(orders, ticker, prev)` (VWAP, da sua o 46095eb).
  => leg-2 chi can goi LAI chinh `createOrderBUY(targetId, ticker, PREDICT_SYMBOL_TRADE, marketData,
     symbolPred, selRank)`; moi thu con lai (gate, budget throttle, VWAP merge, ke toan PnL) tu chay dung.
- `ShadowBookC3` (Map->Cluster, 46095eb) la infra doi chieu LIVE/shadow; duong sim dung `mergeOrder`.
  Khong viet lai ca hai.

## 3. THIET KE (khoa cung)

### 3.1 Flag + tham so (tat ca default OFF / no-op)
| key profile | field Configs | default | y nghia |
|---|---|---|---|
| `SIM_DCA_SIGNAL_GATE` | `DCA_SIGNAL_GATE` | `false` | bat/tat toan bo co che |
| `SIM_DCA_SIGNAL_LOSS` | `DCA_SIGNAL_LOSS` | `-0.08` | nguong X (am), do tren `firstEntryPrice` |
| `SIM_DCA_SIGNAL_BASE_RATIO` | `DCA_SIGNAL_BASE_RATIO` | `0.5` | ti le margin leg dau (va leg-2) so voi binh thuong |
| `SIM_DCA_SIGNAL_COOLDOWN_MIN` | `DCA_SIGNAL_COOLDOWN_MIN` | `60` | phut toi thieu ke tu leg-1 |

Khi `DCA_SIGNAL_GATE=false`: KHONG nhanh nao doc ba key con lai, `isSymbolRunning` filter giu nguyen,
sizing giu nguyen => printDone.csv PHAI byte-identical.

### 3.2 Sizing (chia doi von/lenh)
Hien tai (T170): `budget = equity * F_BASE * throttle / 13` roi `budget *= gridLegWeightRatio(legIdx)`
voi FIX_B2=true => `ratio = w[legIdx] * DCA_GRID_SCALE` (w = 1,1,3,8; SCALE = 19.5).
Leg mo cum (legIdx=0) => ratio 19.5.

Khi flag ON:
- **Leg mo cum (grid slot 0), MOI levelChange**: `ratio *= DCA_SIGNAL_BASE_RATIO` (=> 9.75). Tuc 50% von.
- **Leg-2 DCA-signal**: dung CHINH grid slot 0 (`gridLegWeightRatio(0)`) roi `*= DCA_SIGNAL_BASE_RATIO`
  => cung 9.75. Tuc dung 50% von DU TRU cua chinh lenh do.
- **Leg grid DCA cu (slot >= 1)**: KHONG doi mot ly (van w=1/3/8 x 19.5).
=> Neu leg-2 khong bao gio ban thi coin do song ca doi voi 50% von. CHAP NHAN — day LA mot phan gia thuyet
   dang test; von du thua KHONG duoc tu dong day sang coin khac (do la #52 da FAIL).

### 3.3 Dieu kien ban leg-2 (TAT CA phai dung cung mot tick)
Kiem tra dat o nhanh `else` cua `if (!isSymbolRunning(targetId))` trong vong `chosenCands`:
- **(a)** cum dang mo tren symbol S va **chua ban leg-2 DCA-signal lan nao** (tran: toi da 1 leg-signal / cum).
  Dem rieng: leg grid DCA cu KHONG tinh vao tran nay (hai co che doc lap — dung tinh than master).
- **(b)** `ticker.priceClose / cluster.firstEntryPrice - 1 <= X` (cung convention `firstEntryPrice`
  BAT BIEN qua DCA ma `DcaUtils.shouldDcaGrid` dung). X thuoc {-0.05, -0.08, -0.12} — NONG hon nhieu
  so voi bac dau grid (-0.50) nen hai co che khong chong lan.
- **(c)** S nam trong `chosenCands` cua tick (top-K = 8, S1 ranker + bins map_s1a2_x1) VA pass
  `AIRejectFilter.entryGate` voi `GATE_DYN_SCALE=1.70`. Dieu (c) duoc thuc thi bang cach GOI LAI
  `createOrderBUY(... PREDICT_SYMBOL_TRADE ..., selRank)` — cong gate nam BEN TRONG createOrder, nen
  day dung la "tai su dung chinh xac pipeline admit lenh moi", khong phai tinh lai rank/gate rieng.
- **(d)** `time - cluster.clusterFirstLegTime >= DCA_SIGNAL_COOLDOWN_MIN * 60000` (60 phut).

### 3.4 Ke toan: leg-signal KHONG duoc an mat bac grid DCA
`legIdx` cua khoi grid-sizing dang la `symbol2OrdersEntry[sym].size()`, va `cluster.legCount = orders.size()`
duoc `shouldDcaGrid` dung lam bac grid. Neu de nguyen thi mot leg-signal se DAY grid len mot bac
(leg grid dau tien nhay tu w=1 sang w=3) => hai co che DINH nhau.
=> Them field `public boolean dcaSignalLeg = false` vao `OrderTargetInfoTest`;
   `legIdx` va `legCount` dem **chi cac leg KHONG phai signal**. Khi flag OFF khong leg nao la signal
   => `legIdx`/`legCount` y het `size()` => byte-identical.

## 4. Ba config SWEEP (khoa truoc, chay TUAN TU, KHONG tune lai sau khi thay ket qua config truoc)
Profile goc = `profiles/x1_gs_t170.properties` (incumbent T170), chi THEM 4 key.

| tag | profile | X (`SIM_DCA_SIGNAL_LOSS`) |
|---|---|---|
| `DS_DCA5`  | `profiles/ds_dca5.properties`  | -0.05 |
| `DS_DCA8`  | `profiles/ds_dca8.properties`  | -0.08 |
| `DS_DCA12` | `profiles/ds_dca12.properties` | -0.12 |

Ba key con lai GIONG NHAU o ca 3: `SIM_DCA_SIGNAL_GATE=true`, `SIM_DCA_SIGNAL_BASE_RATIO=0.5`,
`SIM_DCA_SIGNAL_COOLDOWN_MIN=60`. KHONG co config nao khac. KHONG them bien the sau khi thay so.

## 5. Dataset + harness (giong het cac bai truoc)
- Dataset `/home/ubuntu/wfo_ds_x1_2021` (DEV 2021-07..2025-12), config `configs/sim_dev_file_2021.properties`,
  `SIM_END_DATE=20251231`, harness `/home/ubuntu/k_runarm.sh` (`k_runarm.sh <TAG> <PROFILE>`).
- Baseline doi chieu = **T170** (`RG_A_T170`): md5 printDone `efb793e2468ca3a7318da0f0ad23d4fc`, n=1089,
  equity 111,070, CAGR 29.27, maxDD -11.84, UW 92, win% 88.25, TSloss% 9.73, meanP 5.24.
  (T100 md5 `dc16e4da...` n=2559 chi la tham chieu PHU, KHONG phai muc tieu.)

## 6. CONG PARITY — BAT BUOC PASS TRUOC KHI CHAY BAT KY CONFIG ON NAO
| cong | tag | profile | ky vong |
|---|---|---|---|
| (P1) OFF const | `DS_PARITY_T170` | `x1_gs_t170.properties` (khong them key nao) | md5 = `efb793e2...`, n=1089 |

Neu P1 FAIL => DUNG, sua code, KHONG duoc bao cao bat ky ket qua ON nao.
Ngoai ra: build `mvn -o package` + chay TOAN BO test suite hien co phai PASS het. Khong xoa/sua test cu
de ne fail; neu co chu dich doi hanh vi mot test cu thi viet test MOI thay the va giai thich trong RESULT.

## 7. Cham diem + LUAT THANG/THUA (khoa truoc)
- Cong cu: `research/analysis/x1_rates.py` (dung lai may bootstrap cua `c3_rates.py` — KHONG viet script CI moi).
  Bootstrap khoi 72h, block-paired, NREP=2000, CI nhan x1.21. Lenh chay: `python3 x1_rates.py <DS_X> RG_A_T170`
  => bang CI in ra hieu (RG_A_T170 - DS_X), tuc **duong = T170 tot hon**.
  Luu y trung thuc: hang so trong repo la `SEED=20260905` va `CI_INFLATE=1.21` (theo PREREG_2X_HALFSIZE muc 5,
  x1.21 la muc noi rong DA BAO k=3 multiplicity cua du an). Ta dung DUNG hang so co san trong repo,
  KHONG doi seed/inflate cho rieng bai nay.
- **Rang buoc cung (theo tung nam, `hard_by_year`)**: maxDD <= 15%, UW <= 120 ngay, return nam >= 0,
  return quy >= -5%.
- **THANG** = (>= 2 rate CHAT LUONG trong {win%, TSloss%, meanP} nam NGOAI CI theo huong TOT cho config,
  tuc hieu (T170 - DS_X) am cho win%/meanP va duong cho TSloss%) **VA** rang buoc cung PASS TAT CA cac nam.
- Moi truong hop khac => **NULL**. Khong dien giai mem, khong tune lai, khong them config de "cuu".

## 8. Bao cao bat buoc trong RESULT_DCA_SIGNAL_GATE.md
Ngoai bang chuan (n, win%, TSloss%, meanP, mMargin, maxDD%, UW, equity, CAGR%) + CI + hard-constraint
theo nam, PHAI co ba so tra loi truc dien cau hoi cua user:
- **(i)** so leg va so CUM (vi the) cua moi config vs T170 (1089 leg / 1069 cum), % thay doi.
- **(ii)** ti le LO RAW muc LEG: `100 * (profit <= 0).mean()` tren TOAN BO dong printDone.csv.
- **(iii)** ti le LO HIEU DUNG muc VI THE: gom theo cum `(sym, end)`, cong `profit` cua moi leg trong cum,
  roi `100 * (sum_profit <= 0).mean()`. So sanh voi cung phep tinh tren T170.
- Bo sung chan doan: so leg-signal da ban, ti le cum duoc "cuu" (cum co leg-signal ma tong profit > 0 trong
  khi leg-1 cua no profit < 0).

## 9. CAM KET
- Tham so o muc 3-4 DA KHOA truoc khi code. Khong tune sau khi thay ket qua. Khong them config.
- KHONG deploy 242. KHONG `git push`. Chi commit LOCAL tren box Oracle (branch `module`).
- Holdout 2026 KHONG mo (SIM_END_DATE=20251231 co dinh).
- Neu FAIL parity hoac khong tim thay diem re nhanh => dung va bao cao, khong tu che duong vong.
