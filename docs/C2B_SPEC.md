# C2b — DAC TA DAY DU (ung vien freeze)

`PROFILE_HASH=1bc17b5075511263` · `CONFIG_HASH=28f7c17882b0b339`
Nguon su that: `profiles/c2b.properties` (22 key) + `configs/sim_dev.properties` (ha tang).

## 0. DINH CHINH — cong thuc gate tung bi ghi SAI

Ban ghi cu (trong memory, `docs/TRADING_CONFIG_REDESIGN.md`, comment cua ca 7 profile, `ledger.py`,
`ledger3.py`, `admit_rate.py`, kernel H3) noi:
`dyn_thr = 0.008 * clamp(score/0.15*1.2876, 0.26787, 2.14135)`, cham tran tu score 0.2494
=> nguong la HANG SO 1.713%. **SAI.** Da sua het ngay 2026-09-03.

Day la loi **GHI CHEP**, khong phai hai phien ban code khac nhau. Truoc kia cau
`Math.min(scaleFactor, AI_DYNAMIC_MAX)` co ton tai nhung bi co `OFF_FLAT_HARD` (luon = true)
vo hieu hoa; ngay 2026-09-03 ca cau clamp lan co da bi **xoa han khoi code**. Doc
`AIRejectFilter.java` hom nay se khong thay ca clamp lan co — dung ket luan "code da doi",
ban ghi kia sai san tu dau vi `OFF_FLAT_HARD=true`.

Co che THAT co HAI TANG:

**TANG 1 — pre-filter ung vien** (`SimulatorMarketLevelTicker1MStopLoss:300-322`)
```java
float maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX;  // 0.15*2.14135 = 0.32120
for (long e : symbol2Pred) { if (score(e) > maxThres) break; nPass++; }   // mang sort TANG
if (SELECTOR_RANK_TOPK > 0) { chon k coin score thap nhat; }             // BO QUA maxThres
else                        { chon nPass coin dau; }                     // cutoff tuyet doi
```
**`AI_DYNAMIC_MAX` lam viec o DAY** — no la TRAN UNG VIEN, khong phai tran clamp cua nguong.
Nhung voi C2b `SELECTOR_RANK_TOPK=8` nen **tang 1 bi BO QUA**: moi tick lay 8 coin score thap
nhat bat ke tran 0.32120 (`nPass`/`maxThres` chi con di vao log debug). Duong LIVE giong het
(`DetectEntrySignal2TradeNormal:322-327`, va `:512` bo nguong per-symbol khi TOPK>0).
Coin score > 0.32120 vi the **van co the duoc chon**, chi la sau do gan nhu chac chan bi tang 2
chan (score 0.7 => nguong 4.8%). Do duoc: 2.006% pool co score <= 0.32120; trong so hang
score > 0.32120 chi 0.017% vuot duoc tang 2.

**TANG 2 — nguong dong** (`AIRejectFilter.checkSignalDynamic:66-71`)
```java
float scaleFactor = (symbolPred / PREDICT_SYMBOL_RATE_MAX_THRESHOLD) * AI_DYNAMIC_MULTIPLIER;
scaleFactor = Math.max(AI_DYNAMIC_MIN, scaleFactor);      // CHI SAN, KHONG CO TRAN
float dynamic_15M = MIN_MOMENTUM_15M * scaleFactor;       // 0.008 * scaleFactor
```
Truoc do con mot **early-hard-gate**: `pred15M < MIN_MOMENTUM_15M && symbolPred > 0.15` => REJECT ngay.

| score | nguong THAT | nguong ghi SAI truoc day |
|---|---|---|
| <=0.0312 | 0.214% (san) | 0.214% |
| 0.15 | 1.030% | 1.030% |
| 0.2494 | 1.713% | 1.713% |
| 0.28 | **1.923%** | 1.713% |
| 0.30 | **2.060%** | 1.713% |
| 0.3212 (tran ung vien) | **2.206%** | 1.713% |

Anh huong len cac so da bao — **do lai 2026-09-03** tren ledger v3 (`cand_dev3.parquet`,
15,442,092 dong co ca `g1lite` va `p_g015`, DEV 2021-04..2024-06). Ba dinh nghia "admit" khac
nhau, phai noi ro dung cai nao:

| dinh nghia admit | admit | g1lite hang admit |
|---|---|---|
| (A) cong thuc SAI co tran, chi tang 2 | 0.3116% | +0.0910 |
| (B) cong thuc DUNG, chi tang 2 (khop C2b vi TOPK=8 bo tang 1) | **0.1998%** | **+0.1066** |
| (C) cong thuc DUNG + ap ca tran ung vien tang 1 (chi dung khi TOPK<=0) | **0.1833%** | **+0.1115** |
| tran ly thuyet: score ORACLE, cong thuc DUNG, tang 2 | 7.7348% | +0.2149 |

(A) la so tung bao va **da nghi huu**. So dung de doi chieu voi sim C2b la **(B)**; ban dac ta
truoc day dung (C) va ghi 0.1833%/+0.1115 — trung khop. Chenh giua (B) va (C) dung bang so hang score > 0.32120 lot
qua tang 2 (2,551 dong, g1lite chi +0.0521 so voi +0.1115 cua (C)). Ca (B) va (C) deu la **proxy**: chung khong mo
phong buoc cat top-8 theo rank moi tick, nen admit thuc trong sim con thap hon nua.

`ledger.py` / `ledger3.py` / `admit_rate.py` / kernel H3 **da duoc sua** (2026-09-03) sang dung
`research/analysis/gate_cfg.py` — module doc tham so VA hinh dang cong thuc truc tiep tu
`profiles/*.properties` + `Configs.java` + `AIRejectFilter.java`. `cand_dev.parquet` va
`cand_dev3.parquet` da sinh lai 2 cot `dyn_thr` / `gate_dyn_ok`; ban cu giu lai duoi ten
`cand_dev_OLDCLAMP.parquet` / `cand_dev3_OLDCLAMP.parquet` de doi chieu.
⚠️ Dataset Kaggle `s1_ledger_v3` DA UPLOAD van chua 2 cot cu — phai upload lai truoc khi
kernel nao doc `dyn_thr` / `gate_dyn_ok` tu do.

## 1. Thanh phan ung vien duoc admit (cong thuc DUNG, dinh nghia B)

| dai score | so dong | g1lite TB | >5% | ti le duoc admit | nguong TB |
|---|---|---|---|---|---|
| <0.10 | 1,171 | +9.18% | 67.2% | 99.66% | 0.574% |
| 0.10-0.20 | 28,288 | +8.54% | 56.2% | 54.86% | 1.145% |
| 0.20-0.2494 | 51,161 | +6.54% | 49.7% | 13.70% | 1.568% |
| 0.2494-0.3212 | 229,137 | +6.10% | 47.5% | **2.011%** | 2.009% |
| >0.3212 | 15,132,335 | +1.30% | 23.2% | 0.017% | 4.168% |

**88.55% hang duoc admit co score < 0.30** (ban ghi cu bao 60.19%) — he chay tren mot dai tu tin
cuc mong, va con mong hon so voi truoc khi sua.

## 2. SELECTOR — chon coin
| key | gia tri | y nghia |
|---|---|---|
| `SELECTOR_RANK_TOPK` | 8 | moi tick 15m lay toi da 8 coin diem tot nhat; **bo qua tran ung vien tang 1** |
| `SELECTOR_ONLY_ENTRY` | 1 | **chi** sleeve selector duoc vao lenh (tat BIG_DOWN / DCA_LEVEL1) |

Model **S1**: XGBoost `rank:ndcg` (LambdaRank), group = tick, 9 feature V3, nhan = ngu phan vi
trong tick cua `g1lite - trung vi pool`, WFO 10 cutoff purge 72h, `qid = pd.factorize(ts, sort=True)`.
Diem duoc **quantile-map** ve phan phoi G015 trong tung tick de gate cu xu y het.
Xac nhan: **100% cua 970 lenh** la `PREDICT_SYMBOL_TRADE`.

## 3. EXIT — phan quyet dinh P&L
| key | gia tri | vai tro |
|---|---|---|
| `SIM_RATE_PROFIT_STOP_MARKET` | 0.07 | **ARM**: chi khi lai dinh > 7% moi dat SL lan dau |
| `SIM_TS_GIVEBACK` | 1 | ratchet **lien tuc** (bo dead-zone) |
| `TS_GIVEBACK_RATIO` | 0.5 | nha lai mot nua lai dinh |
| `TS_MAX_GAP` / `TS_MAX_GAP_WEAK` | 0.08 / 0.03 | tran khoang nha: strong / weak |
| `TS_PNOPUMP_WEAK_THR` | 0.29 | `symbolPred > 0.29` => nhanh WEAK |
| `SIM_LOSER_TIME_STOP_HOURS` | 168 | lenh **chua arm** bi cat sau 7 ngay |
| `TRAIL_PEAK_MODE` | high | dinh do bang **high** cua nen |

Duong code: `updateStatusNew`/`updateTPSL` -> `trailRate()` -> vi `TS_GIVEBACK_MODE=true` nen di
nhanh `calRateLossDynamicBuyPNoPump`:
```
maxGap = (symbolPred > 0.29) ? TS_MAX_GAP_WEAK(0.03) : TS_MAX_GAP(0.08)
gap    = TS_GIVEBACK_FLOOR ? max(peak*0.5, TS_MIN_GAP) : min(peak*0.5, maxGap)   // C2b: FLOOR=false
SL     = round((peak - gap)/0.005)*0.005
```
Tai diem arm 7%: **STRONG khoa +3.5%**, **WEAK khoa +4.0%** (tran nha 3% < 3.5%). Ca hai **tren**
chi phi round-trip 1.0% — day la ly do C2b song qua stress chi phi.

**Truoc khi arm KHONG co stop-loss nao** (`HARD_SL_PCT=0`, `HARD_STOP_LOSS_RATE=0`). Loi ra duy
nhat la time-stop 7 ngay. Khop du lieu: moi lenh `STOP_LOSS_DONE` giu chan 7 ngay.
=> Hinh dang P&L: **85% thoat bang trailing TB +7%, 15% chet bang time-stop TB -19% (DEV) / -25% (VAL)**.

## 4. SIZING
| key | gia tri | |
|---|---|---|
| `CAPITAL_START` | 35,000 | von goc |
| `NUMBER_ORDER_BUDGET` | 50 | => `BASE_BUDGET = 700 USDT/lenh` |
| `DCA_GRID_SCALE` | 1.5 | => ~1,050 danh nghia |
| `TIER_FLAT` | 1 | **tat** he so theo tier coin |

Do duoc: margin/lenh TB 971, min 197, max 1,575 (dao dong do throttle von theo margin dang chay).

## 5. DCA — tat hoan toan
`DCA_GRID_ENABLED=true` nhung `DCA_GRID_WEIGHTS=1,0,0,0` => chi leg dau, dung het budget,
khong nhoi them bao gio. `DCA_GRID_LEVELS=-0.50,-0.75,-0.90` chi con la so trang tri.

## 6. CHI PHI
`SIM_APPLY_FUNDING=true` + `SIM_FUNDING_MARK=true` · fee 0.2%x2 + slippage 0.3%x2 => **round-trip 1.0%**

## 7. BREAKER — tat (CHI tren duong SIM)

`SIM_BREAKER_MODE=OFF` => trong **sim** khong gioi han mat do, khong chan theo margin.
=> `MAX_CONCURRENT=40` **TRO trong sim**: da kiem chung bang cach doi 40 -> 25 va `printDone`
giong het tung byte, tren **dataset DEV 2022-01..2024-06**.

⚠️ **PHAM VI cua ket luan "tro" nay: CHI sim, CHI dataset DEV do.** Tren duong **LIVE** con mot
circuit breaker **theo MAT DO mo lenh, DOC LAP voi `BREAKER_MODE`** — no **VAN BAT** ke ca khi
`BREAKER_MODE=OFF`:

- Noi dat: `MarketBigChangeDetector` (khoi "KILL-SWITCH AN TOAN - KHONG XOA"), goi tu
  `DetectEntrySignal2TradeNormal.createOrderBuyRequest`.
- Ba nguong gio la **HANG SO trong code**, khong con la tham so cau hinh:
  `BURST_BASE=40`, `DENSITY_SUSTAIN=10.0`, `DENSITY_ALPHA=0.6`, `CIRCUIT_DANGER_RATIO=0.7`,
  `CIRCUIT_LOOKBACK_MINUTES=4`.
- Kiem lai bang `grep -rn MAX_CONCURRENT src/main`: chi con 3 cho nhac ten
  (`Cfg.java` whitelist, mot comment trong `MarketBigChangeDetector`, mot comment HPO) —
  tuc `MAX_CONCURRENT` dung nghia la **khong con consumer nao** doc de chan lenh; cai chan lenh
  that o live la ba hang so tren, khong phai `MAX_CONCURRENT`.
- Nhanh live nay tung bi xoa trong dot refactor "xoa tham so tro" 2026-09-03 roi **da khoi phuc**.
  Dung suy tu "MAX_CONCURRENT tro" ra "live khong co gioi han mat do" — hai chuyen khac nhau.

## 8. Param TRO trong C2b (khong xoa, chi bi co khac tat)

`Configs.java` co **121 field**; voi C2b chi khoang **18-20** thuc su tac dong P&L.

| bi tat boi | cac param thanh tro |
|---|---|
| `SELECTOR_ONLY_ENTRY=1` | `MS_UP_*`, `MS_DOWN_*`, `PREDICT_SYMBOL_RATE_UP/DOWN_*`, `DCA_LOSS_BIG_*`, `DCA_TIME_BIG_*` |
| `SELECTOR_RANK_TOPK=8` | tran ung vien tang 1 (`PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX`) |
| off cung nhanh phang (co `OFF_FLAT_HARD` da **xoa** 2026-09-03) | nhanh BIG_UP / SMALL_UP / SMALL_DOWN, tang `BUDGET_DIVIDER_1` |
| `DCA_GRID_WEIGHTS=1,0,0,0` | `DCA_GRID_LEVELS/L1/STEP/LEGS/W_RATIO/SCALAR`, `DCA_TIER_*`, `TS_CARRY_SL_ON_DCA` |
| `BREAKER_MODE=OFF` (chi trong SIM — xem muc 7) — **M2 (2026-09-03): co che breaker trong SIM DA BI XOA (`5f40a90`), `Configs.java:509-512` chi ho tro gia tri `OFF`. Cac param ben phai khong "tro" ma la KHONG CON CONSUMER trong sim.** | `MAX_CONCURRENT_ORDERS`, `DENSITY_*`, `CIRCUIT_*`, `BREAKER_MARGIN_HALT`, `BREAKER_CLUSTER_DD_MAX` |
| `TS_GIVEBACK_MODE=1` | `TS_PROFIT_MULTIPLIER` (5.21847), **va `TS_GAP_CONST`** |
| `TS_GIVEBACK_FLOOR=false` | `TS_MIN_GAP` |
| ~~`ENABLE_SHORT=false` / `CONF_SIZE_MODE=0` / `SIZE_MULT=1.0`~~ **M3 (2026-09-03): ca ba KEY NAY KHONG CON TON TAI trong `src/main`** (`5f40a90` xoa `research/SimulatorMarketLevelInvertedSelector.java` 555 dong + `ShortEntryLifecycleTest` 129 + `ShortOrderMechanismTest` 101 + toan bo `CONF_SIZE_*`/`SIZE_MULT`). Chung khong "bi tat" — chung da bi xoa. `SHORT_*` va `CONF_SIZE_*` gio la ten khong co consumer. | ~~`SHORT_*`, `CONF_SIZE_*`~~ |

Luu y: `AI_DYNAMIC_MAX` **khong** phai tran clamp cua nguong gate (xem muc 0). Voi TOPK=8 no tro
trong duong chon ung vien, nhung van con y nghia neu ai do dat `SELECTOR_RANK_TOPK<=0`.

**Da chet han trong engine (khong chi tro):**
- `TS_DYNAMIC_K` (0.29774) — `calRateMinWithPredReturn15MForTradingStop` da FROZEN bo, chi con dung trong tool HPO.
- `TS_WEAK_MOMENTUM_THRES` — khong xuat hien o dau trong `src/main`.

## 9. Ket qua

**DEV** (2022-01 -> 2024-06, 970 lenh): equity 35,000 -> **60,390** · CAGR **24.48%** ·
maxDD **-13.12%** · Sharpe(quy) 1.99 · underwater 93 ngay · quy duong 8/10 · quy >=+5% 6/10 ·
2022 +11.6 / 2023 +45.4 / 2024H1 +6.3 · khong nam nao am.

**VALIDATION** (2024-07 -> 2025-12, 1,063 lenh, cham lan thu 5): equity -> **47,681** ·
CAGR **23.60%** · maxDD **-7.28%** · Sharpe(quy) 1.33 · underwater **234 ngay** · quy duong 4/6.
⚠️ 2024Q4 (+7,347) + 2025Q1 (+4,133) = **90.5%** toan bo lai; ba quy cuoi cong lai +1.5% trong 9 thang.
⚠️ 2025Q4: nhieu lenh nhat (338, gap 6 lan 2025Q3), lenh dong thoi cao nhat (30), maxDD sau nhat
VAL (-7.3%) — ma PnL **-385**.
⚠️ Stop-loss o VAL dat hon DEV ro ret: **-25%/lenh** vs -19%, cung winrate 85%.

## 10. Cach tai lap
```bash
cp -f configs/sim_dev.properties $RUNDIR/config.properties
TRADING_PROFILE=profiles/c2b.properties \
  WFO_DATA_DIR=$DS WFO_SMART_CACHE=1 SIM_END_DATE=20240630 \
  EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json \
  java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx14g -cp $JAR \
  com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss
```
Kiem cau hinh hieu dung: `java -cp $JAR com.binance.chuyennd.tradecore.DumpConfig`
(phai thay `PROFILE_HASH=1bc17b5075511263`, `CONFIG_HASH=28f7c17882b0b339`).
Kiem cong thuc gate ma phan tich python dang dung:
`python3 research/analysis/gate_cfg.py` (in ra nguon tung tham so + co/khong co tran).
