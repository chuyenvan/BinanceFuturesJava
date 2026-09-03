# AUDIT — "DA DANH GIA TOT" ROI CO APPLY DUOC GI KHONG

Ngay audit: 2026-09-03 (Oracle 10:45 UTC). Job READ-ONLY: khong chay java, khong chay backtest,
khong cham VALIDATION/HOLDOUT, khong commit.

Cach xac minh cot "Da apply": grep truc tiep
`profiles/c2b.properties` (22 key) + `src/main` tren repo `/home/ubuntu/src/BinanceFuturesJava`
branch `module` (HEAD `16c53d2`). **Khong suy tu van ban docs.** Docs noi da apply ma config/code
khong co -> ghi MAU THUAN va dung ve phia config/code.

## TRA LOI NGAN CHO CAU HOI CUA CHU DU AN

Cam giac "danh gia thang nhieu ma khong apply duoc gi" **khong dung voi phan lon cac muc**:
gan het cac muc THANG da nam san trong C2b (arm 7%, sizing 1.5x, TS_GIVEBACK, loser-time-stop 168h,
funding-mark, M1, va **selector S1**). Cai thuc su "thang ma chua apply" chi con **5 muc**, va
**4/5 la no ghi chep / tai lap**, khong phai alpha. Xem Bang 2.

Phat hien nang nhat khong lien quan cau hoi goc: **commit `5f40a90` (2026-09-03 15:47 +0700) da XOA
3582 dong**, trong do co CONF_SIZE_*, SIZE_MULT, MAX_CONCURRENT_ORDERS, GateRollingThreshold,
circuit-breaker MARGIN/BOTH, va ca `SimulatorMarketLevelInvertedSelector` (ENABLE_SHORT).
=> **3 "don bay da co san trong code, chua tung bat" ma memory va docs con quang cao thi GIO KHONG
CON.** Muon dung phai viet lai code. Chi tiet: Muc 4 M1-M3.

---

# BANG 1 — MOI THI NGHIEM / GIA THUYET DA DANH GIA

Quy uoc cot "Apply": CO / KHONG / MOT PHAN / VOID (nut tro, phep do vo nghia).
`b:` = equity cuoi DEV (2022-01..2024-06, von goc 35,000), doc tu `devrun/<TAG>/logs/sim.out`.
C2b = **b:60390** (CAGR 24.48 / maxDD -13.12 / 8-10 quy duong / Sharpe(q) 0.95 / n 970).

## A. TANG SELECTOR

| ID | Ten | Ngay | Ket qua do duoc | Verdict goc | Apply? | Bang chung apply | Neu chua: ly do + chi phi |
|---|---|---|---|---|---|---|---|
| A1 | **S1 = LambdaRank + label cross-sectional + pool tick gate mo** (bins `predwf_map_s1a2`) | 2026-09-02 | `map_s1a2_g1` b:50891 -> CAGR **16.21** / DD **-10.69** / **9** quy+ / Sharpe **1.00** / n 1117 vs base `G1_giveback5` b:48352 = 13.85 / -15.6 / 7 / 0.74 / n 1736 | THANG | **CO** | `/home/ubuntu/java/dev_c2.sh:23` `WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2`; env nay duoc phep di ngoai profile: `src/main/java/com/binance/chuyennd/tradecore/Cfg.java:46`; doc bins: `WfoDataset.java:71-72`; top-K: `profiles/c2b.properties:12` `SELECTOR_RANK_TOPK=8`; nhanh rank: `DetectEntrySignal2TradeNormal.java:322,327` + `SimulatorMarketLevelTicker1MStopLoss.java:307-316` | Apply roi. **Nhung bins KHONG duoc pin trong profile va pipeline sinh bins KHONG co trong git** — xem Muc 3 va Bang 2 #1 |
| A2 | S1a (ledger 2022+) | 2026-09-02 | `map_s1a_g1` b:49581 (CAGR 15.00 / DD -12.8 / 8 quy+) | thang base, kem s1a2 | KHONG | — | Bi A1 thay the (s1a2 dung ledger 2021+). Dung |
| A3 | Control tam thuong: ranker `vol_7d` thuan | 2026-09-02 | `map_vol7d_g1` b:41876 (7.46 / -16.3 / n 922) | THUA (dung y do control) | KHONG | — | La doi chung, khong de apply |
| A4 | Pool day du MOI tick (s1a4 / s1b4) | 2026-09-03 | `C2_s1a4` b:55357 · `C2_s1b4` b:56588 vs `C2a` b:59471 | THUA | KHONG | — | Pha cau truc do tu tin cua G015 (map doi 41% dong thay vi 5%). Da dong |
| A5 | Label graded (bien do x so gio tren 6%) | 2026-09-03 | `C2_s1b2` b:56704 (21.37 / -16.69) vs C2a 59471 | THUA -2.34pp | KHONG | — | Da dong nhanh label |
| A6 | **C6' A/B chi doi selector** (G015 voi DUNG exit/sizing cua C2a) | 2026-09-03 | `C2_g015` b:51903 (CAGR 17.13 / DD -20.82) vs `C2a` b:59471 (23.71 / -13.42) => S1 hon **+6.6pp CAGR**, DD **tot hon 7.4pp** | PASS C6' | **CO** (day la bang chung cua A1) | `devrun/C2_g015/logs/sim.out` vs `devrun/C2a/logs/sim.out`; script `dev_c4.sh:23` (`predwf_G015x26`) | — |
| A7 | Do ben theo seed (train lai S1 seed 1 / 7) | 2026-09-03 | `C2a_seed1` b:58483 · `C2a_seed7` b:59406 vs C2a 59471 | PASS (on dinh) | CO | `dev_c6.sh:25-26` | Khong can key |
| A8 | `SELECTOR_RANK_TOPK=5` (khop live) | 2026-09-02 | `G1_topk5` 13.54 / **-10.7** / 8 quy+ / **Sharpe 0.98** / n 1289; `map_s1a2_g1k5` b:47360 vs K=8 b:50891 | K=8 nhieu equity, K=5 DD/Sharpe tot hon | **MOT PHAN** | `profiles/c2b.properties:12` = **8**; live chay **5** (runbook_live_242 §12) | Venh live<->sim CHUA dong. Chi phi: 1 quyet dinh + 1 vong parity |
| A9 | Nhanh selector cu: fav72 / cs72 / V2-40feat / V3 / veto b30-b40 / v3-nomom | 2026-09-02 | b: 44788 / 46645 / 32956 / 38471 / 41769-42432 / **10305** | THUA het | KHONG | — | Label maxFav bi vol-confound. Da dong |
| A10 | **H3 — dau do tu tin tuyet doi** (Kaggle GPU, 14.3M dong OOS) | 2026-09-03 | rho(pred,g1lite) **0.1667** vs nguong 0.2175 va vs G015 **0.1675**; lech hieu chuan 0.215 > 0.05; **shuffle control** admit 0.508% o chat luong **+0.0992 > model that +0.0891** | **FAIL 4/5 tieu chi** | KHONG | `docs/PREREG_H3.md`; `research/kaggle/h3_abs_head/run.py`; ledger `/home/ubuntu/ledger/h3/` | Het du dia voi 9 feature hien tai. Dong |
| A11 | Chon nhan offline tot nhat | 2026-09-03 | tuong quan ROI that (n=2263): **g1lite 0.584** > maxFav_72h 0.574 > g1_replay 0.507 > nH_above_3 0.503 | g1lite thang = nhan DANG dung | **CO** (khong doi gi) | `featv2/LABELPICK.out`; `s1_rank.py` dong 8 (`D.g1lite`) | — |

## B. TANG GATE (dieu kien thi truong)

| ID | Ten | Ngay | Ket qua do duoc | Verdict goc | Apply? | Bang chung apply | Neu chua: ly do + chi phi |
|---|---|---|---|---|---|---|---|
| B1 | **H1a** noi `MIN_MOMENTUM_15M` 0.008 -> 0.006 | 2026-09-03 | nen C2a: `H1a_mom006` b:**60953** (> C2b 60390!) nhung DD **-21.1** / underwater 108d. Nen C2b: `K0_h1a_prof` b:59580, DD -21.0 / 133d | **FAIL** (truot C1 maxDD<=15) | KHONG | `profiles/c2b.properties:17` = **0.008**; `profiles/k0.properties:17` = 0.006 (chi de doi chieu) | Lenh them CO lai (n=1243, ROI +1.26%) nhung loang + phoi nhiem dong thoi 29->37. Muon apply phai co co che kiem soat DD moi — BR da thu, that bai (B5) |
| B2 | **H1b** `PREDICT_SYMBOL_RATE_MAX` 0.15 -> 0.30 | 2026-09-03 | `H1b_rmax30` b:47460, CAGR 12.70, DD **-44.3**, 2022 **-31.6%** | THAM HOA | KHONG | khong co key nay trong `profiles/*` -> chay default 0.15 | **Truc chet, dong vinh vien** |
| B3 | H1c ca hai | 2026-09-03 | `H1c_both` b:37600, DD **-51.3**, 2022 -35.2% | THAM HOA | KHONG | — | Dong |
| B4 | **Rolling-percentile gate** (A7 / RG95 / RG97 / RG95w180) | 2026-09-02 va 2026-09-03 | A7 tren nen D1: `A7_rollgate` b:51484 = **16.75 / -15.0** (danh gia "kha" luc do, +29% PnL o R3). Tren nen C2b: `RG95` b:56683 · `RG97` b:52045 · `RG95w180` b:59120 — **ca 3 < C2b 60390** | THANG tren nen cu, **THUA tren nen C2b** | KHONG | Khong co `SIM_GATE_ROLLING_PCT` trong `profiles/*`. **Co che DA BI XOA**: `git show --stat 5f40a90` -> `ai_ml/onnx/entry/GateRollingThreshold.java \| 97 ----` | Apply gio doi **viet lai code** (~100 dong) + pre-reg moi. EV am tren nen C2b => khong nen |
| B5 | Nguong gate THUC TE khong phai 0.008 | 2026-09-03 | `dyn_thr = 0.008 x clamp(score/0.15 x 1.28760, 0.26787, 2.14135)`; median score G015 0.47-0.70 => **luon clamp** => nguong hang **1.713%**. Ti le admit top-8: DEV 0.51% · VAL 0.71% · 2025Q4 2.03% (trong dai lich su, 2022Q2 = 2.12%) | DINH CHINH — ket luan "gate hong, mo 78%" la SAI, da rut lai | **CO** (ghi vao chinh profile) | `profiles/c2b.properties:15-16` (comment ghi ro cong thuc + 0.01713); `DumpConfig` in `derived.gate_thr@score_*` — xem `devrun/logs/dev_rnd.out` | — |
| B6 | `regime_probe` — them dai luong thi truong gop tu feature coin | 2026-09-03 | chi `p15`: OOS TB **+0.0532**; `p15` + 14 dai luong gop: **-0.1467** (chenh **-0.20**). Chi 3/14 giu dau qua 3 nam | FAIL (them vao te di han) | KHONG | `research/analysis/regime_probe.py` + `regime_probe.out`; commit `9aceed5` | Can DU LIEU MOI (trang thai thi truong tong, order book, trade flow) — khong co trong nguon hien tai |
| B7 | Slow gate breadth 72h | 2026-09-02 | autocorr lag3 = **0.22** (lag1-2 thoi co hoc) | FAIL | KHONG | — | Dong |
| B8 | Breadth TB 7d lag3 (post-hoc) | 2026-09-02 | IC **+0.30** voi breadth 3 ngay toi, on 3 nam, quintile 0.32->0.51 | post-hoc, CHUA pre-reg | KHONG | `/home/ubuntu/featv2/GATE_BREADTH_DAILY.csv` | Chi duoc dung neu pre-reg rieng (sizing multiplier). Chua ai viet pre-reg. Chi phi: 1 pre-reg + 1-2 run |
| B9 | On dinh selectivity theo thoi gian | 2026-09-03 (VAL) | p15 median troi 0.36% -> 0.93% => 0.008 tuong ung phan vi ~94.7 (DEV) nhung ~76 (VAL); universe phinh **155 -> 563 coin/gio** | van de THAT nhung tac dong ky vong NHO | KHONG | khong co tham so nao trong `profiles/c2b.properties` phan anh universe size | Y tuong: top-K theo ti le universe thay vi K=8 co dinh. **Chua tung kiem.** Chi phi: sua code selector + pre-reg |

## C. TANG EXIT / SIZING

| ID | Ten | Ngay | Ket qua do duoc | Verdict goc | Apply? | Bang chung apply | Neu chua: ly do + chi phi |
|---|---|---|---|---|---|---|---|
| C1 | **Gradient arm** (profit-stop) 4/5/6/7/8% | 2026-09-03 | CAGR **12.47 / 16.21 / 17.71 / 18.98 / 18.74** (`R2_arm4` b:46904 · `map_s1a2_g1` 50891 · `R2_arm6` 52545 · `R5_arm7` 53968 · `R6_arm8` 53689) => plateau 6-8, chon **tam = 7%** | THANG, chon bang luat pre-reg (khong chon max) | **CO** | `profiles/c2b.properties:21` `SIM_RATE_PROFIT_STOP_MARKET=0.07`; luat ghi trong `dev_rob2.sh:2-4` va `dev_c2.sh:2-4` | — |
| C2 | **Sizing scale** 1.0 / 1.5 / 2.0 | 2026-09-03 | CAGR 16.21 / 20.44 / 23.51, maxDD **-10.69 / -13.55 / -15.55** (`R7_scale15` b:55629 · `R8_scale20` b:59227) => chon 1.5 = gia tri lon nhat con DD <= 15% | THANG | **CO** | `profiles/c2b.properties:38` `DCA_GRID_SCALE=1.5` | — |
| C3 | **SIM_TS_GIVEBACK** (trailing dung thiet ke: arm -> SL = profit - min(50%, cap), ratchet lien tuc) | 2026-09-02 | `G1_giveback5` b:48352 (13.85) vs `G0_giveback3` b:46444 (12.02) | THANG | **CO** | `profiles/c2b.properties:22` `SIM_TS_GIVEBACK=1`; commit `00b2362`; `derived.trail_path=calRateLossDynamicBuyPNoPump` (dev_rnd.out) | — |
| C4 | **SIM_LOSER_TIME_STOP_HOURS=168** | 2026-09-02 | margin-days (lenh giu >30d) **91% -> 1.7%**; plateau 96/168/336 (`A6_ts96` b:48452 · `A6_ts336` b:49865) | THANG | **CO** | `profiles/c2b.properties:24` | — |
| C5 | **SIM_FUNDING_MARK** (fix funding notional theo mark) | 2026-09-02 | zombie funding ao 4-10x truoc fix (AXS -130.7 vs mark -35.1); corr 1.0000 voi tinh tay | BUG FIX bat buoc | **CO** | `profiles/c2b.properties:46` `SIM_FUNDING_MARK=true` | Moi ket qua truoc fix (sweep, CPCV) bi thoi — da bo |
| C6 | **M1 = A2+A3+A5** (SELECTOR_ONLY_ENTRY + TS_GAP_CONST + TIER_FLAT) | 2026-09-03 | `C2b` b:**60390** vs `C2a` b:59471 (24.48 vs 23.71) | THANG + it tham so hon | **CO** | `profiles/c2b.properties:13,23,39` | — |
| C7 | A4 hard stop -5% tu entry | 2026-09-02 | `A4_hardsl` b:**17598** (-24% CAGR / DD -57%) | **PHA** (arm-delay la cot loi) | KHONG (co y) | `profiles/c2b.properties:33` `HARD_STOP_LOSS_RATE=0` | Dong |
| C8 | TRAIL_PER_SYMBOL | 2026-09-02 | `R2_trail` b:35222 / `R2f_trail` b:35219 = **-17%** | FAIL | KHONG | key khong ton tai trong `profiles/*` | Dong |
| C9 | **N1-N4 lan can** (arm 6/8 x scale 1.25/1.75) | 2026-09-03 | `N1_a6s125` b:55269 · `N2_a8s125` b:56543 · `N3_a6s175` b:59631 · **`N4_a8s175` b:61148 (> C2b 60390)** | PASS on dinh | **KHONG** | `dev_c3.sh:4` viet ro: "**KHONG chon config tot nhat tu day; chi PASS/FAIL on dinh**" | Dung luat pre-reg. Muon dung N4 phai co pre-reg RIENG (do plateau arm 7-8 x scale 1.5-1.75 + maxDD) — xem Bang 2 #5 |
| C10 | H6 exit theo vol (k x vol_7d) | — | **chua chay** | — | KHONG | — | Con trong hang doi `docs/ROADMAP_NOLEAK.md` (H6). Chi phi: code moi + pre-reg |
| C11 | **CONF_SIZE_*** (sizing theo do tu tin selector) | 2026-09-03 | `p6 = 1 - symbolPred` vs ROI/lenh: **spearman -0.019, p = 0.55**; moi cau hinh confFactor cho ROI-co-trong-so THAP HON baseline | **NHANH DONG** (range restriction: selector da dung chinh diem do de loc top-8) | KHONG | `research/analysis/p6_analyze.py`, `size_signal.py`. **CODE DA BI XOA**: `git grep CONF_SIZE_MODE 5f40a90^ -- src/main` co 5 hit (`Configs.java:194-198`, `SimulatorMarketLevelTicker1MStopLoss.java:1045-1050`); `git grep CONF_SIZE_MODE HEAD -- src/main` = **0 hit** | Vua het EV (do offline) vua het co so ha tang. Xem M1 |
| C12 | `SIZE_MULT` (nhan budget/lenh) | 2026-09-03 | chua tung chay | — | **VOID** | `SIZE_MULT` con o `5f40a90^:SimulatorMarketLevelTicker1MStopLoss.java:156-158,1036-1040`, **0 hit o HEAD** | Code da xoa. Apply = viet lai |
| C13 | `MAX_CONCURRENT` (tran lenh dong thoi) | 2026-09-03 | `K1_conc25` b:59580 va `K2_conc20` b:59580 **giong het K0 tung byte** | **VO HIEU** — nut tro khi BREAKER_MODE=OFF | **VOID** | `docs/PREREG_K.md`; `docs/RUNS_DEV.md` dong K1/K2. Field con o `5f40a90^:Configs.java:230`, **da xoa o HEAD** | Sim khong he co tran cung lenh dong thoi (chi "mot lenh moi coin" + throttle von) |

## D. PHOI NHIEM / BREAKER + CHI PHI

| ID | Ten | Ngay | Ket qua do duoc | Verdict goc | Apply? | Bang chung apply | Neu chua: ly do + chi phi |
|---|---|---|---|---|---|---|---|
| D1 | **BR — bat circuit breaker** (BR1 MARGIN / BR2 BOTH / BR3 MARGIN+mom006) | 2026-09-03 | `BR1_margin` b:**60272** (970->962 lenh, equity -118) · `BR2_both` b:**60272** (giong het BR1) · `BR3_mg006` b:59542, DD **-20.9** vs K0 -21.0 | **KHONG cai thien gi**; breaker KHONG cuu duoc DD cua viec noi gate | KHONG | `profiles/c2b.properties:49` `SIM_BREAKER_MODE=OFF`. **Co che DA XOA**: `Configs.java:509-512` — "SIM_BREAKER_MODE=... nhung co che circuit-breaker DA BI XOA 2026-09-03. Chi ho tro SIM_BREAKER_MODE=OFF"; `5f40a90` xoa `RunBreakerBacktest.java` (185 dong) + `RunMarginHaltSweep.java` (195 dong) | Co che DD la "gia chay nguoc tren lenh DA MO", khong phai "mo qua nhieu lenh". Khong co che phoi nhiem nao thay duoc **tin hieu regime**. Dong |
| D2 | Stress chi phi (fee 1.5x, slip 2x, funding 1.5x) | 2026-09-03 | `C2c` b:53433 = CAGR **18.51%** / DD -14.52 (nen C2a); `C2b_stress` b:54200 = 19.19% | **PASS C5** (>=12%) | **CO** (la tieu chi PASS, khong phai key) | `dev_c2.sh:26` (`SIM_RATE_FEE=0.003 SIM_SLIPPAGE_RATE=0.006 SIM_FUNDING_SCALE=1.5`, commit `3071c33`) | Co che: arm 7% + giveback 50% cap 8% => SL chot **+3.5%** > chi phi round-trip 1.0-1.8% |
| D3 | Stress nang (chi phi 2.3x base) | 2026-09-03 | `C2a_stress2` b:50156 = CAGR 15.54 / DD -15.7 | PASS | CO | `devrun/C2a_stress2/logs/sim.out` | — |
| D4 | R4 — bo 20% coin lai nhat (concentration) | 2026-09-03 | `R4_univ` b:41718: CAGR **16.2 -> 7.3**; top-10 coin = 25% gross+ | **RUI RO THAT, chua khac phuc** | KHONG (khong co gi de apply) | `dev_rob.sh:32-33`, `featv2/excl_top.py` | Khong co tham so nao giam concentration. Chua co huong. Ghi vao "rui ro da biet" |

## E. HA TANG CAU HINH (B1-B5)

| ID | Ten | Ngay | Ket qua do duoc | Verdict goc | Apply? | Bang chung apply | Neu chua: ly do + chi phi |
|---|---|---|---|---|---|---|---|
| E1 | **B1 — DumpConfig** (in moi field + gia tri dan xuat + CONFIG_HASH) | 2026-09-03 | `CONFIG_HASH=28f7c17882b0b339` (C2b); `derived.*` in dung 2 tang gate | XONG | **CO** | commit `4776ea0`; `src/main/java/com/binance/chuyennd/tradecore/DumpConfig.java`; output thuc: `devrun/logs/dev_rnd.out` | — |
| E2 | **B2 — Cfg gateway + TRADING_PROFILE** | 2026-09-03 | parity 2 chieu: `P_env2` b:60390 va `P_prof2` b:60390 **byte-identical** voi C2b goc | XONG | **CO** | commit `ccde0ca`; `src/main/java/com/binance/chuyennd/tradecore/Cfg.java`; `profiles/c2b.properties` | — |
| E3 | **B3 — dong kenh cau hinh thu hai** + `configs/sim_dev.properties` vao git | 2026-09-03 | `P_env3` b:60390 / `P_prof3` b:60390 byte-identical; `CONFIG_STRICT=1` + file cu -> rc=2, liet ke dung **20 key rac**; 8 key chay bang default hardcode vo hinh -> nay khai bao tuong minh | XONG | **CO** | commit `cb073af`; `tools/check_cfg_gateway.sh` (GATE2 trong `/home/ubuntu/java/logs/gs_gate.log` = OK) | — |
| E4 | **Toi gian profile 22 -> 15 key** (byte-identity) | 2026-09-03 | `V1_nogapconst` / `V2_nomingap` / `V3_nozeros` / `N1_nolvl` / `N2_nodps` / `N3_nonob` / `C2b_MIN` — **TAT CA b:60390, printDone IDENTICAL** voi C2b (`devrun/logs/inert.out`, `devrun/logs/dev_rnd.out`) | **THANG** (7 key la TRO) | **KHONG** | `profiles/c2b.properties` van **22 key**. Ban 15 key chi ton tai o `/home/ubuntu/java/profiles/c2b_min.properties` (PROFILE_HASH `531b4ae7b4b64885`) — **KHONG co trong git**: `git ls-files \| grep c2b_min` = rong | Chi phi: 1 commit. Rui ro: 0 (da chung minh byte-identity). **Xem Bang 2 #2** |
| E5 | **RND — hang so HPO 5 chu so co load-bearing khong** | 2026-09-03 | nen `C2b_MIN` b:60390. `RND1_2dp` (1.29/0.27/2.14) b:**60003**, 2022 +11.5 / 2023 +45.5 / 2024 +5.7, maxDD **-13.1**, 6/10 quy>=5%, underwater 95d. `RND2_rnd` (1.3/0.25/2.0) b:**59846**, maxDD **-13.2**, underwater 95d | **CA HAI PASS** het 4 tieu chi (\|dCAGR\|<=2pp, maxDD>=-15.12, quy duong >=8/10, khong nam am) => "hang so KHONG load-bearing". Pre-reg noi: **thay bang so tron** | **KHONG** | `src/main/java/com/binance/chuyennd/tradecore/Configs.java:307-309` van **1.28760 / 0.26787 / 2.14135**. Override chi la env: `Configs.java:435,440,441` | Chi phi: sua 3 dong + 1 run parity. **Nhung "khong mat gi" trong pre-reg la SAI**: mat 387 USDT equity = ~-0.4pp CAGR. Can Uni chot. **Xem Bang 2 #3 + M9** |
| E6 | **Xoa 40 co che TRO + 9 tham so chet** | 2026-09-03 | `P_newjar` b:60390, `D1`/`D2`/`D3`/`D4` b:60390, `GS1` b:60390 — **IDENTICAL** voi C2b (`/home/ubuntu/java/logs/gs_gate.log` GATE3) | THANG (don 3582 dong, ket qua khong doi) | **CO** | commit `5f40a90` (40 co che) + `52fb1e1` (9 tham so) + `4dd3b04` (CONFIG_FIELD_MAP 123 -> 65 field, 0 DEAD); `tools/parity_clean.sh` | Tac dung phu NGHIEM TRONG: xoa luon 3 don bay chua tung dung. Xem M1-M3 |
| E7 | Khoi phuc 4 kill-switch bi xoa NHAM | 2026-09-03 | 191 dong khoi phuc o `MarketBigChangeDetector` / `BinanceOrderTradingManager` / `DetectEntrySignal2TradeNormal` | BUG FIX | **CO** | commit `637513c` | Bang chung dot refactor E6 la **rui ro cao** — da xoa nham 4 kill-switch an toan |
| E8 | B4 (85 field mutable -> final) / B5 (CONFIG_HASH + PROFILE_HASH vao header printDone + manifest) | — | **chua lam** | — | **KHONG** | `docs/TRADING_CONFIG_REDESIGN.md:214-220` ("Con lai (B4/B5)") | B5 la dieu kien de moi ket qua tu mang theo cau hinh sinh ra no. Chi phi thap. **Xem Bang 2 #4** |
| E9 | Pin exchangeInfo | 2026-09-03 | 892 symbol, md5 `5a815948d890` | XONG, ap tu VAL tro di | **CO** | env `EXCHANGE_INFO_PATH=/home/ubuntu/java/exchange_info_pin.json` (`dev_min.sh:36`, `verify_inert.sh:31`); commit `e2c8fde` | Chua ap cho cac run DEV cu (dev_c2.sh khong dat) |
| E10 | `TICKER_SOURCE` aerospike vs file | 2026-09-03 | Oracle+aerospike **60390** · Oracle+file **60395** · Kaggle+file **60395** (`GS_FILE15`/`GS_FILE24` b:60395, printDone giong het nhau). Nguyen nhan: **1 lenh/970** — FTT BUY 2022-11-09, aerospike cham SL, file khong => +5 USDT = **0.008%** | do truc tiep, ghi nhan | **CO** (ghi thanh luat) | `/home/ubuntu/gs/BASELINE_NOTE.md`; `/home/ubuntu/java/logs/gs_filetest.log`; commit `180683c` | Moi so sanh Oracle<->Kaggle chi tin toi ~0.01% |

## F. VALIDATION + DANG CHAY + NO CHUA QUYET

| ID | Ten | Ngay | Ket qua do duoc | Verdict goc | Apply? | Bang chung apply | Neu chua: ly do + chi phi |
|---|---|---|---|---|---|---|---|
| F1 | **VAL single-shot C2b** (lan cham VAL thu 5) | 2026-09-03 | `VAL_C2b` b:**47681** (2024-07-15..2025-12-30, 1.46 nam): CAGR **23.60%** / maxDD **-7.28%** / quy+ **4/6** / n 1063 / Sharpe(q) 0.69. Stress `VAL_C2b_stress` b:42081 = 13.46%. Hinh dang: 2024Q3 +1.5 / **2024Q4 +20.7** / 2025Q1 +9.6 / 2025Q2 +3.1 / 2025Q3 -0.8 / 2025Q4 -0.8; underwater **234 ngay** | **PASS V1-V5** nhung loi nhuan don 1 quy bull | **CO** (da chay) | `devrun/logs/val_c2b.out`; `/home/ubuntu/java/val_c2b.sh`; jar md5 `82566c54ecae` + exchangeInfo `5a815948d890` khop pre-reg; `HOLDOUT SEAL` cat 312,322 ban ghi >=2026 | **Thieu A/B baseline G015 tren VAL** => chua tach duoc selector vs beta. Can cham VAL lan 2 (canh bao 1/3 da phat) |
| F2 | Audit du lieu VAL | 2026-09-03 | (a) `feat_v2_val` == `feat_v2` tren doan chung: nan_mismatch 0, max diff <=4.7e-7 => PASS. (b) NaN `ls_global`/`rk_oi_delta24h`: 1.0-1.8% (2024) -> **8.1-8.2% (2025Q4)**. (c) universe **155 -> 265 -> 563 coin/gio**, coin unique 171 -> 591 | (a) PASS, (b)(c) RUI RO | KHONG (khong co gi apply) | `featv2/audit.py`, `featv2/AUDIT.out`, `featv2/admit_rate.py` | (b) la rui ro pipeline OI/LS cho live. (c) khong tham so nao phan anh => xem B9 |
| F3 | **GS wave-1 — Sobol 15 chieu, 256 diem** | 2026-09-03 | **CHUA CO KET QUA**: 5 kernel `chuyendinh/gs-w1-0..4` push luc 10:22 UTC (`/home/ubuntu/gs/push5.log`), `/home/ubuntu/gs/out/` **chua ton tai** luc audit 10:45 UTC | dang chay | **KHONG (chua the)** | pre-reg `docs/PREREG_GS.md` (chot 10:35 UTC); khong gian `research/kaggle/gsearch/gen_params.py` `SPEC` 15 chieu (commit `f51fd17`); diem neo `id=-1` phai tai lap **60395** neu khong => **WAVE VOID** | Luat doc ket qua da chot cung (§4 buoc 1-7). Chia du lieu: DEV-A 2022-2023 (chon), DEV-B 2024H1 (xac nhan <=5 finalist), **VALIDATION khong bi cham** |
| F4 | Override SIM_* cho hang so HPO con song | 2026-09-03 | 4 key moi mo: `SIM_AI_DYNAMIC_MULTIPLIER/MAX`, `SIM_TS_MAX_GAP`, `SIM_TS_MAX_GAP_WEAK`, `SIM_F_BASE`, `SIM_U_MAX`; default = gia tri cu => byte-identical | XONG (ha tang cho GS) | **CO** | commit `f2ada23` + `f51fd17`; `Configs.java:435-448` | Khong key nao trong `profiles/c2b.properties` => tat ca chay default |
| F5 | **PHASE1_DECISION_SURFACE — 7 muc "phai quyet lai co y thuc"** | (tu Pha 1) | **cot "QUYET (1.2)" TRONG HOAN TOAN** — khong muc nao duoc quyet | **CHUA QUYET** | **KHONG** | `docs/PHASE1_DECISION_SURFACE.md` — bang A/B/C, cot cuoi rong; muc "Tong ket cai CHUA/DA-NHIEM" liet ke 7 muc | Trong do **2 muc con song va nguy hiem**: **A2c** label SL = 0.03 "placeholder, user chot sau" CHUA TUNG CHOT; **A2e** lay mau grid 15m **overlap voi horizon 4h = L1 leak**, co mode nonoverlap nhung default la grid. Ca hai thuoc model **G015** — model dang cap `score` cho GATE (S1 chi dao thu hang, quantile-map giu nguyen phan phoi P(win) cua G015) => **leak L1 tiem an o tang gate CHUA dong** |
| F6 | Bug funding `computeFundingOnClose` | 2026-09-02 | notional co dinh = qty x avgEntry => funding ao 4-10x | BUG, da fix | **CO** | commit `49fde3b` -> `SIM_FUNDING_MARK=true` (xem C5) | Moi ket qua truoc fix (sweep, CPCV Pha 2) **bi thoi** |
| F7 | Pha 2 CPCV gate market-return tren VAL | (truoc 2026-09-02) | FAIL DSR (DSR 0.936@400 / 0.912@1400 vs nguong 0.95), 4 lan cham VAL | **FAIL, dong** | KHONG | `docs/ROADMAP_NOLEAK.md:83`; memory `cpcv_*.md` (11 file archive) | Dong |
| F8 | Forced-seller / carry-funding / trend-holdout | (truoc 2026-09-02) | KILLED | FAIL | KHONG | memory `forced-seller-verdict.md`, `carry-funding-verdict.md`, `trend-holdout-verdict.md` | Dong |
| F9 | H7 — sleeve short thuc su | — | chua chay | — | KHONG | **`ENABLE_SHORT` khong phai sleeve thu hai**: no DAO CHIEU tin hieu selector thanh SELL, giu nguyen moi gate/filter/budget, TAT DCA => khong chay song song long+short. Va `SimulatorMarketLevelInvertedSelector.java` (**555 dong**) **DA BI XOA** o `5f40a90` | Apply = viet code moi hoan toan (truoc day uoc "dang ke", nay con nhieu hon vi mat ca ban inverted). Xem M3 |
| F10 | H4 features spike-15m / H5 label lien tuc co do ben | — | chua chay | — | KHONG | `docs/ROADMAP_NOLEAK.md` hang doi muc 4 | 9 feature hien tai deu **cham 3-14 ngay**. Day la huong ma MOI phep do 2026-09-03 deu chi ve (nut that = FEATURE). Chi phi cao (du lieu moi) |

## PHAN BO BANG 1

Tong **57 muc** da danh gia (co so do hoac co verdict chot).

| Apply? | so muc | ID |
|---|---|---|
| **CO** | **23** | A1, A6, A7, A11, B5, C1, C2, C3, C4, C5, C6, D2, D3, E1, E2, E3, E6, E7, E9, E10, F1, F4, F6 |
| **KHONG** | **30** | A2, A3, A4, A5, A9, A10, B1, B2, B3, B4, B6, B7, B8, B9, C7, C8, C9, C10, C11, D1, D4, E4, E5, E8, F2, F5, F7, F8, F9, F10 |
| **MOT PHAN** | **1** | A8 (K=8 sim vs K=5 live) |
| **VOID** (nut tro / phep do vo nghia) | **2** | C12 (`SIZE_MULT`), C13 (`MAX_CONCURRENT`) |
| **CHUA THE** (dang chay) | **1** | F3 (GS wave-1) |

Boc tach 30 muc KHONG apply:

| nhom | so | ID | co dung khi khong apply? |
|---|---|---|---|
| **THUA / FAIL da do** | 18 | A2, A3, A4, A5, A9, A10, B1, B2, B3, B4, B6, B7, C7, C8, C11, D1, F7, F8 | **Dung** — do dac noi khong |
| **Chua chay** | 4 | B8 (breadth lag3, post-hoc chua pre-reg), C10 (H6 exit theo vol), F9 (H7 short), F10 (H4/H5) | Dung — chua co so |
| **THANG/PASS ma CHUA apply** | 4 | **E4** (toi gian profile 22->15 key), **E5** (RND so tron), **E8** (B5 hash vao printDone), **C9** (N4 arm8xscale1.75) | **KHONG dung** voi 3 muc dau (no ghi chep); C9 dung vi luat pre-reg cam chon |
| **Rui ro da ghi nhan, khong co gi de apply** | 4 | B9 (universe 155->563 coin/gio), D4 (concentration: bo 20% coin lai nhat -> CAGR 16.2->7.3), F2 (NaN OI/LS 8.2% o 2025Q4), F5 (7 quyet dinh Pha 1 chua chot) | Dung ve hinh thuc, nhung F5 la **no nghiem trong** — xem M13 |

# BANG 2 — TOP 5 "THANG NHUNG CHUA APPLY", xep theo (gia tri ky vong / chi phi)

| # | Cai gi | So do chung minh no thang | Tai sao chua apply duoc | Viec cu the can lam | Rui ro |
|---|---|---|---|---|---|
| **1** | **Dua pipeline S1 vao git + pin bins vao manifest** | S1 la **nguon edge duy nhat da chung minh**: `map_s1a2_g1` 16.21/-10.69/9 quy+/Sharpe 1.00 vs base 13.85/-15.6/7/0.74; A/B cung exit (`C2_g015` 17.13/-20.82 vs `C2a` 23.71/-13.42) = **+6.6pp CAGR, DD tot hon 7.4pp**. ROI/lenh chi-S1 **+2.25%** (n 653) vs chi-G015 +1.23% (n 1146); rank-IC S1 **+0.150** vs G015 +0.055 | Khong ai coi day la "thi nghiem" nen khong ai ghi vao apply-list. Thuc te: `git ls-files \| grep -E "s1_rank\|build_map\|ledger\|path_labels"` chi tra ve `scripts/model_quality/cpcv/trial_ledger.py` — **toan bo pipeline S1 nam ngoai git**: `/home/ubuntu/featv2/{s1_rank.py,build_map.py,s1_v4.py,feat_v2_build.py}`, `/home/ubuntu/ledger/{ledger.py,ledger3.py,path_labels.py}`. Bins `/home/ubuntu/predwf_map_s1a2` (10 file, 394MB) chi ton tai tren dia Oracle, **khong duoc pin trong `profiles/c2b.properties`** (cap qua env `WFO_FUNDING_PRED_DIR`, `Cfg.java:46`) | (a) `git add` 7 script python vao `research/selector/`; (b) ghi md5 cua 10 bins vao `profiles/c2b.properties` duoi dang comment + vao manifest dataset; (c) mot dong trong profile hoac `configs/sim_dev.properties` ghi ro bins dir dung cho C2b | **Rui ro cua VIEC KHONG LAM la cao nhat trong ca bang**: Oracle disk 90-91% da phai don 4.7G; neu `predwf_map_s1a2` hoac `featv2/feat_v2.parquet` (955MB) bi xoa thi C2b **khong the tai lap** va toan bo edge mat. Chi phi lam: ~30 phut, rui ro 0 |
| **2** | **Toi gian `profiles/c2b.properties` 22 -> 15 key** | 7 run **byte-identical b:60390** voi C2b: `V1_nogapconst`, `V2_nomingap`, `V3_nozeros` (`devrun/logs/inert.out`: "IDENTICAL => key da bo la TRO"), `N1_nolvl`, `N2_nodps`, `N3_nonob`, `C2b_MIN` (`devrun/logs/dev_rnd.out`) | Da lam va da do XONG, chi thieu buoc commit. Ban 15 key nam o `/home/ubuntu/java/profiles/c2b_min.properties` (PROFILE_HASH `531b4ae7b4b64885`), **khong co trong repo** — `profiles/` trong git chi co 7 file: br1/br2/br3/c2b/k0/k1/k2 | Commit `c2b_min.properties` vao `profiles/`, hoac thay `c2b.properties` bang ban 15 key va giu 7 key TRO trong comment ("da chung minh tro ngay 2026-09-03, bang chung: inert.out") | 0 — byte-identity da chung minh. Duy nhat: PROFILE_HASH doi (`1bc17b5075511263` -> `531b4ae7b4b64885`), moi doc so cu phai biet |
| **3** | **Thay 3 hang so HPO 5 chu so bang so tron** (`AI_DYNAMIC_MULTIPLIER/MIN/MAX`) | `RND1_2dp` (1.29/0.27/2.14) b:60003, maxDD -13.1, 6/10 quy>=5%, khong nam am. `RND2_rnd` (1.3/0.25/2.0) b:59846, maxDD -13.2. **Ca hai PASS het 4 tieu chi** cua `docs/PREREG_RND.md` => "hang so KHONG load-bearing" — day chinh la ket luan pre-reg chot truoc, va hanh dong pre-reg chot truoc la "**thay bang so tron**" | Khong ai bam nut. `Configs.java:307-309` van la `1.28760f / 0.26787f / 2.14135f`. Chi co duong env override (`Configs.java:435,440,441`), khong dat trong profile | Sua 3 dong `Configs.java` sang `1.3f / 0.25f / 2.0f` (RND2) **hoac** khai bao 3 key trong `profiles/c2b.properties` -> chay 1 run parity xac nhan ra dung 59846 | **Mat that 544 USDT equity = ~-0.5pp CAGR** (60390 -> 59846). Pre-reg viet "khong mat gi" — **cau do khong dung**. Vi vay day la quyet dinh CUA UNI: doi 0.5pp CAGR lay su trung thuc (bo dau vet HPO tren range da nhiem). Neu chon RND1 (1.29/0.27/2.14) thi chi mat 0.4pp |
| **4** | **B5 — ghi `CONFIG_HASH` + `PROFILE_HASH` vao header `printDone.csv` va manifest dataset** | Khong phai phep do alpha, nhung la thu da CHUNG MINH gia tri qua 2 su co: (a) `dev_h1.sh` khong dat `TS_GAP_CONST/TIER_FLAT/SELECTOR_ONLY_ENTRY` => H1a/b/c dung tren **C2a** chu khong phai C2b, da so nham 2 baseline mot lan; (b) `config.properties` ban chay khong nam trong git, **155 ban tren dia, 24 bien the md5** | B3 da xong nhung B5 bi hoan. `docs/TRADING_CONFIG_REDESIGN.md:214-220` con ghi "Con lai (B4/B5)" | Them 1 dong header vao `printDone.csv` writer + ghi 2 hash vao manifest cua `ExportWfoDataset` | Thap. Doi header => cac script doc `printDone.csv` (`qret.py`, `ev.sh`, `label_align.py`, `conc.py`, `attrib.py`) phai skip them 1 dong. Da tung dinh bug header 1 lan (`fab02f2`: cot 'risk4h' thuc ra la symbolPred) |
| **5** | **Diem lan can cao hon C2b: `N4_a8s175` (arm 8% x scale 1.75)** | `N4_a8s175` b:**61148** > C2b b:60390 (+758 USDT). Va `H1a_mom006` b:**60953** cung > C2b | Ca hai **bi luat pre-reg cam chon**: `dev_c3.sh:4` viet ro "N1..N4 lan can quanh diem chon: ... KHONG chon config tot nhat tu day; chi PASS/FAIL on dinh"; H1a truot maxDD -21.1% > 15%. Va **N4 khong co maxDD/quy+ trong bat ky log nao** — chi co equity | Neu muon dung: viet pre-reg RIENG do **plateau 2 chieu** (arm 7/7.5/8 x scale 1.5/1.625/1.75), chon TAM plateau chu khong dinh, va cham C1-C5 day du (nhat la maxDD <= 15%) | **Cao nhat trong bang.** DEV da thu ~53 config; SE cua Sharpe(q) voi 10 quy ~ 0.32; ky vong max cua ~50 phep thu ngau nhien ~ 0.7. Chon N4 vi thay no cao nhat = **dung y nghia cua L2 selection leak**. +0.5pp CAGR khong bu duoc mot lan chon post-hoc. Ngoai ra GS wave-1 dang quet dung 2 chieu nay (`SIM_RATE_PROFIT_STOP_MARKET` 0.02-0.20, `DCA_GRID_SCALE` 0.5-3.0) => **cho GS xong roi doc theo §4 PREREG_GS, dung tu chay** |

---

# MUC 3 — CAU HOI TRONG TAM: S1 DA APPLY HAY CHUA?

## 3.1 Bo so 16.21 / -10.7 / 9 quy+ / Sharpe 1.00 ra tu RUN NAO

- **Run**: `map_s1a2_g1`, thu muc `/home/ubuntu/java/devrun/map_s1a2_g1/`.
  `logs/sim.out` -> **b:50891 done:113/1117/1117**. Equity cuoi 50,891 tren von goc 35,000.
- **Nguon so 16.21/-10.69/9/1.00/n1117**: `/home/ubuntu/java/dev_rob2.sh` dong 4, viet TRUOC khi
  chay R5-R8: "Base map_s1a2_g1: CAGR 16.21 / maxDD -10.69 / 9 quy+ / Sharpe 1.00 / n 1117".
  Cung so nay o memory `selector_s1_ledger.md` bang "Ket qua (DEV, sim gate cong bang)".
- **Tap**: **DEV**, 2022-01-01 -> 2024-06-30 (`SIM_END_DATE=20240630`). **KHONG phai VAL.**
- **Config**: script `/home/ubuntu/java/dev_map2.sh` dong 17-18 —
  `N=s1a2; P=/home/ubuntu/predwf_map_s1a2; build_map.py s1a2 $P; WFO_FUNDING_PRED_DIR=$P`.
  Env exit = "G1": `SELECTOR_RANK_TOPK=8 SIM_MIN_MOMENTUM_15M=0.008 SIM_TS_GIVEBACK=1
  **SIM_RATE_PROFIT_STOP_MARKET=0.05** SIM_LOSER_TIME_STOP_HOURS=168 DCA_GRID_WEIGHTS=1,0,0,0`
  **khong dat `DCA_GRID_SCALE`** => scale = 1.0. Tuc **arm 5% + sizing 1.0x**.
- **Nguon mo hinh**: `pred_s1a2.parquet` (7.4MB, `/home/ubuntu/ledger/`) do `s1_rank.py` sinh —
  `xgb.XGBRanker(objective="rank:ndcg", ..., lambdarank_pair_method="topk",
  lambdarank_num_pair_per_sample=8)`, qid = `pd.factorize(ts, sort=True)`, label
  `rel5` = quintile trong tick cua `rel = g1lite - median(pool)`, pool = `cand_dev.parquet`
  (tick gate mo, p15 >= 0.008), 10 fold WFO cutoff 20220101..20240401, purge 72h,
  `assert tr.ts.max() < cutoff`. **Dung la LambdaRank + label cross-sectional + pool tick gate mo.**

## 3.2 Base 13.85 / -15.6 ra tu run nao

- **Run**: `G1_giveback5`, `/home/ubuntu/java/devrun/G1_giveback5/logs/sim.out` -> **b:48352
  done:257/1736/1736**. Cung tap DEV, **cung exit y het** (arm 5%, scale 1.0), khac **duy nhat**
  bo bins selector: `predwf_B015` / `claudedata/predwf_G015x26` = model G015 goc (45 feature,
  label triple-barrier maxFav>=6%/4h) thay cho `predwf_map_s1a2`.
- => cap 16.21 vs 13.85 la **A/B doi DUY NHAT selector**, voi gate lam cong bang bang quantile-map
  (`build_map.py`: trong tung tick, coin hang k cua model moi nhan gia tri P(win) hang k cua G015
  => phan phoi P(win) theo tick giong het => gate chat/long y nhau). Dong cuoi `build_map.py` in
  `TOTAL rows ... changed ... MAP_OK` de kiem.

## 3.3 C2b co PHAI la S1 khong? — CAU TRA LOI DUT KHOAT

**S1 DA APPLY — day du o tang mo hinh, NHUNG apply MOT PHAN o tang ha tang/tai lap.**

Truoc het, mot dinh chinh danh cho master: **`SELECTOR_RANK_TOPK=8` va `SELECTOR_ONLY_ENTRY=1`
KHONG phai la S1.** Hai key do chi noi "moi tick lay 8 coin dau bang xep hang" va "bo leg
market-signal". Chung se y nguyen neu ta cam bins G015 vao — do dung la run `C2_g015` (b:51903).
**Cai lam nen S1 la `WFO_FUNDING_PRED_DIR`**, khong phai `SELECTOR_*`.

Chuoi bang chung, tung mat khop:
1. `profiles/c2b.properties:12-13` -> `SELECTOR_RANK_TOPK=8`, `SELECTOR_ONLY_ENTRY=1`.
2. `Configs.java:334-339` doc 2 key do qua `Cfg.get(...)`.
3. `SimulatorMarketLevelTicker1MStopLoss.java:307-316` lay `nSel = min(TOPK, symbol2Pred.length)`
   tu mang `symbol2Pred` — mang nay den tu **dataset**, khong tu profile.
4. Dataset do `ExportWfoDataset` sinh; `WfoDataset.java:71-72` doc bins tu env
   **`WFO_FUNDING_PRED_DIR`**; `WfoDataset.java:116` canh bao "khong set -> fallback Aerospike".
5. `Cfg.java:46` liet ke `WFO_FUNDING_PRED_DIR` la bien **HA TANG** (duoc phep dat qua env ngay
   ca khi da dat `TRADING_PROFILE`; moi bien GIAO DICH thi bi fail-fast exit 2).
6. `/home/ubuntu/java/dev_c2.sh:23` — script sinh ra chinh `devrun/C2a`, `C2b`, `C2c`:
   `export WFO_FUNDING_PRED_DIR=/home/ubuntu/predwf_map_s1a2 WFO_CODE_SHA=3071c33-C2`.
7. `predwf_map_s1a2` = output cua `build_map.py s1a2` = quantile-map cua `pred_s1a2.parquet`
   = output cua `s1_rank.py` = **LambdaRank**. (§3.1)
8. Moi script chay tren nen C2b sau do deu tro cung bins: `dev_c3.sh:20`, `dev_c5.sh:21`,
   `dev_c6.sh:19`, `dev_h1.sh:25`, `dev_k.sh:23`, `dev_br.sh:20`, `dev_rg.sh:12`, `dev_rnd.sh:20`,
   `dev_min.sh:28`, `parity2.sh:10`, `parity3.sh:22`, `verify_inert.sh:27`.

**Phan "MOT PHAN" — 4 thu con thieu, deu la ha tang chu khong phai mo hinh:**
- (a) **Profile khong pin selector.** `profiles/c2b.properties` co 22 key giao dich, **khong key nao
  noi C2b dung bins nao**. Ai chay `TRADING_PROFILE=profiles/c2b.properties` ma quen
  `WFO_FUNDING_PRED_DIR` se lang le chay bang **fallback Aerospike** (`WfoDataset.java:116` chi
  `LOG.warn`, khong exit) => ra so khac ma khong bao loi. `CONFIG_HASH`/`PROFILE_HASH` cung khong
  bao gio thay doi khi doi selector.
- (b) **Pipeline S1 khong co trong git** (Bang 2 #1).
- (c) **Chua co duong realtime cho live**: features hourly + quantile-map online theo phan phoi
  G015 cua tick hien tai — chua viet. `ls_global`/`rk_oi_delta24h` NaN 18-19% tren DEV va tang len
  8.1-8.2% o 2025Q4.
- (d) **Gate van chay bang G015.** Quantile-map giu **nguyen** phan phoi P(win) cua G015 trong tung
  tick; S1 chi doi *coin nao nhan gia tri nao*. Nghia la `score` dung cho gate (`dyn_thr`), cho
  strong/weak trailing (`TS_PNOPUMP_WEAK_THR=0.29`) va cho tran ung vien (0.32120) **van la cua
  G015**. => moi no cua G015 (F5: label SL 0.03 placeholder chua chot, grid 15m overlap = L1 leak)
  **van con nguyen trong C2b**.

## 3.4 Vay 16.21 vs 13.85 dang so cai gi, va tai sao C2b la 24.48?

- **16.21 vs 13.85** = **chi doi selector**, giu exit "G1" (arm 5%, scale 1.0). Do la phep do
  **edge cua S1**, dung cho tieu chi C6'.
- **C2b = 24.48% (b:60390)** = cung selector S1 **cong hai thay doi exit/sizing**:
  arm 5% -> **7%** (`SIM_RATE_PROFIT_STOP_MARKET=0.07`) va scale 1.0 -> **1.5**
  (`DCA_GRID_SCALE=1.5`), cong M1. Duong di so hoc, tat ca tren cung bins S1:
  16.21 (arm5, scale1) -> 18.98 (arm7, scale1 = `R5_arm7` b:53968) -> 23.71 (arm7 + scale1.5 =
  `C2a` b:59471) -> 24.48 (+M1 = `C2b` b:60390).
- Doi chieu tren nen G015 de thay S1 khong bi arm7/scale1.5 "an mat": `C2_g015` b:51903 =
  **17.13%**. Tuc voi DUNG exit cua C2b, S1 24.48 vs G015 17.13 => **S1 dong gop +7.35pp CAGR**
  va DD -13.12 vs -20.82.
- **Ket luan**: hai thang so khong he mau thuan. 13.85/16.21 la thang "arm5 scale1";
  17.13/24.48 la thang "arm7 scale1.5". **Trong ca hai thang, S1 deu thang G015.**

---

# MUC 4 — MAU THUAN VA NO GHI CHEP

Moi muc: docs/memory noi gi -> code/config thuc te noi gi -> dung ve phia nao.

## M1 (NANG NHAT) — "3 don bay sizing da co san trong code, chi can pre-reg + chay" la SAI

- Memory `config_redesign.md` muc "Don bay da co san trong code, CHUA tung bat":
  "`CONF_SIZE_MODE/LO/HI/FMIN/FMAX` — sizing theo do tu tin selector **da code day du**...
  Cong `SIZE_MULT`, `MAX_CONCURRENT`. => **Ba don bay 'sizing theo rank' khong can code moi**".
- Repo cung noi vay: `docs/TRADING_CONFIG_REDESIGN.md:58-59` va `:222`.
- **Thuc te code**: `git grep -n "CONF_SIZE_MODE" HEAD -- src/main` = **0 hit**.
  `git grep -n "SIZE_MULT" HEAD -- src/main` = chi 1 hit trong danh sach tien to o `Cfg.java:56`
  (chuoi de fail-fast, khong phai co che). `MAX_CONCURRENT_ORDERS` = chi 1 comment o
  `RunHpoMaster_Distributed.java:36`.
  O `5f40a90^` thi ca ba deu song: `Configs.java:194-198,230`,
  `SimulatorMarketLevelTicker1MStopLoss.java:156-158,1036-1050`.
- Commit `5f40a90` (2026-09-03 15:47 +0700) "xoa 40 co che TRO", 50 file, **-3582 dong**, xoa luon
  test `ConfSizeSizingTest.java` (131 dong) va `SizeMultSizingTest.java` (113 dong).
- **DUNG VE PHIA CODE: ba don bay do KHONG con.** Ghi chep phai sua. Apply gio = viet lai code.
- (Luu y: rieng `CONF_SIZE` thi EV cung da bi phu dinh doc lap — spearman(p6, ROI) = -0.019,
  p = 0.55. Nen mat code khong phai ton that. Nhung `SIZE_MULT` thi chua tung do.)

## M2 — Circuit breaker: memory noi "co san nhung dang tat", thuc te DA BI XOA

- Memory `selector_edge_evidence.md` muc 10: "`evaluateCircuitBreakerCore` (goi tu
  `SimulatorMarketLevelTicker1MStopLoss:978`, chi chay khi `BREAKER_MODE != OFF`) ... Gia tri hop le
  `SIM_BREAKER_MODE`: `OFF`/`MARGIN`/`DCA`/`BOTH`. Mac dinh code la `MARGIN`".
- **Thuc te**: `Configs.java:509-512` — "`SIM_BREAKER_MODE=` ... nhung co che circuit-breaker
  **DA BI XOA 2026-09-03. Chi ho tro SIM_BREAKER_MODE=OFF**". `5f40a90` xoa
  `RunBreakerBacktest.java` (185 dong) + `RunMarginHaltSweep.java` (195 dong);
  `MarketBigChangeDetector.java` -136 dong.
- `grep -n "MarketBigChangeDetector" SimulatorMarketLevelTicker1MStopLoss.java` chi con 3 hit
  (`:237` getMarketStatus1M, `:253` getTopSymbolArray, `:285` isDcaAlt) — **khong con goi breaker**.
- **DUNG VE PHIA CODE.** BR1/BR2/BR3 khong the chay lai. (EV cung da phu dinh: BR1/BR2 b:60272,
  BR3 DD -20.9 vs -21.0 — khong cai thien gi.)
- Phan con dung cua memory: `evaluateCircuitBreakerCore` **van ton tai** o
  `MarketBigChangeDetector.java:253` va **van bat ke ca khi BREAKER_MODE=OFF** o duong LIVE
  (`MarketBigChangeDetector.java:196`, `DetectEntrySignal2TradeNormal.java:543-544`) — do la 1
  trong 4 kill-switch da khoi phuc o `637513c`. Nen: **live van co breaker cung, sim thi khong.**

## M3 — `ENABLE_SHORT` / H7: ban inverted-selector da bi xoa

- Memory `selector_edge_evidence.md` muc 8 mo ta chi tiet hanh vi `ENABLE_SHORT`
  ("dao chieu tin hieu selector thanh SELL, giu nguyen moi gate/filter/budget, tat DCA").
- **Thuc te**: `5f40a90` xoa `research/SimulatorMarketLevelInvertedSelector.java` (**555 dong**) +
  `ShortEntryLifecycleTest.java` (129) + `ShortOrderMechanismTest.java` (101).
- **DUNG VE PHIA CODE.** H7 (chan short cho nam bear) gio dat hon truoc: khong con ca ban tham chieu.

## M4 — Rolling-percentile gate: van duoc de xuat trong khi co che da bi xoa

- Memory `val_2026-09-03_c2b.md` muc "Viec ke tiep 1": "Dang chay: rolling-percentile gate tren
  DEV (RG95/RG97/RG95w180)"; va "Rolling-percentile gate van dang test, nhung de **on dinh
  selectivity**". Memory `MEMORY.md` (index) thi da dinh chinh: "Rolling-percentile gate KHONG phai
  bat buoc; A7/RG95/RG97 da chay va khong cai thien".
- **Thuc te code**: `5f40a90` xoa `ai_ml/onnx/entry/GateRollingThreshold.java` (**97 dong**);
  `git grep "GATE_ROLLING_PCT\|GateRollingThreshold" HEAD -- src/main` = **0 hit**.
- **DUNG VE PHIA CODE.** RG95/RG97 khong the chay lai ma khong viet lai. Ket qua do (56683/52045/
  59120 vs C2b 60390) noi la khong nen — nhung phai ghi ro rang no da **bat kha thi**, khong chi la
  "khong bat buoc".

## M5 — `profiles/c2b_min.properties` khong ton tai trong repo

- Nhiem vu audit gia dinh co `profiles/c2b_min.properties`. **Khong co.**
  `ls profiles/` trong repo = `br1, br2, br3, c2b, k0, k1, k2` (7 file).
- File thuc su ton tai o `/home/ubuntu/java/profiles/c2b_min.properties` (15 key, PROFILE_HASH
  `531b4ae7b4b64885`), cung 5 file khac cung khong duoc commit: `base18`, `n1`, `n2`, `n3`,
  `rnd1`, `rnd2`, `v1_nogapconst`, `v2_nomingap`, `v3_nozeros`.
- 7 file trung ten thi **giong het** ban repo (diff rong) — nen khong co rui ro lech, chi la thieu.

## M6 — `docs/index.md` tro tuot ra khoang khong

- `docs/index.md` (router "doc dau tien") tro tuong minh tới: `CORE.md` ("**Luon doc CORE**"),
  `FINDINGS.md` ("**NGUON SU THAT**"), `SESSION_START.md` ("**DOC DAU TIEN moi session**"),
  `DATA_STATE.md`, `architecture.md`, `PIPELINE.md`, `REDESIGN_INFRA_20260804.md`,
  `DATA_VALIDATION_FRAMEWORK.md`, `db/index.md`, `reference/*`.
- **Kiem tra thuc te**: `CORE.md` MISSING · `FINDINGS.md` MISSING · `SESSION_START.md` MISSING ·
  `DATA_STATE.md` MISSING · `architecture.md` MISSING · `PIPELINE.md` MISSING.
  (Da bi don sang `docs/archive/_cleanup_20260829` o commit `c446f0a`.)
- => Router chinh cua docs **hong**. Mot agent moi doc `index.md` se di tim 6 file khong ton tai
  va bo qua `ROADMAP_NOLEAK.md`/`RUNS_DEV.md` — la 2 file that su song.

## M7 — `docs/CONFIG_FIELD_MAP.md` tro `docs/C2B_SPEC.md`, file khong ton tai

- `CONFIG_FIELD_MAP.md` (sinh `4dd3b04`) viet: "Xem `docs/C2B_SPEC.md` muc 8".
- `ls docs/C2B_SPEC.md` -> **No such file or directory**.

## M8 — `docs/CONFIG_INVENTORY.md` da cu hon code

- Header file: "Sinh luc: 2026-09-03 03:08 UTC · commit `cb073af`".
- Nhung `52fb1e1` (15:07 +0700 = 08:07 UTC) xoa 9 tham so va `5f40a90` (15:47 +0700 = 08:47 UTC)
  xoa 40 co che. => Ban kiem ke liet ke tham so **da khong con**.
  `CONFIG_FIELD_MAP.md` moi hon (sinh `4dd3b04`, 65 field, 0 DEAD) va **thang** khi 2 file lech.

## M9 — `docs/PREREG_RND.md` noi "khong mat gi", so do noi mat 0.4-0.5pp CAGR

- Pre-reg: "Ca hai PASS => so le chi la vet HPO vo hai. **Thay bang so tron** ...: don gian hon,
  trung thuc hon, **khong mat gi**. Day la ket qua tot."
- So do: nen 60390 -> RND1 **60003** (-387 USDT, ~-0.4pp CAGR) -> RND2 **59846** (-544 USDT,
  ~-0.5pp CAGR). Trong nguong pre-reg (2.0pp) nen PASS la dung — nhung **"khong mat gi" la sai**.
- => Hanh dong pre-reg chot truoc (thay so tron) van nen lam, nhung phai bao Uni dung con so: doi
  0.4-0.5pp CAGR DEV lay viec bo dau vet HPO tren range da nhiem.

## M10 — K=8 (sim) vs K=5 (live): venh chua dong

- `profiles/c2b.properties:12` = `SELECTOR_RANK_TOPK=8`.
- Live 242 chay **K=5** (`docs/runbooks/runbook_live_242_2026-08-19.md §12` bang venh live<->G1;
  commit `311bb29` "fix(live): K5 selector parity voi backtest RANK-TOPK";
  `842c327` "cap selector entry to SELECTOR_RANK_TOPK per tick").
- Do do co: `G1_topk5` 13.54/-10.7/8 quy+/Sharpe **0.98** vs `G1` 13.85/-15.6/7/0.74 — K=5 co
  **DD va Sharpe tot hon**, K=8 co equity cao hon. Bien ban 2026-09-02 tu canh bao: "so sanh 2 gia
  tri K **sau khi thay ket qua** — khong sweep K".
- => Venh nay chua duoc quyet mot cach co y thuc o bat cu dau. Live va sim dang la hai he khac nhau.
  (GS wave-1 dang quet `SELECTOR_RANK_TOPK` trong dai 2-30 => cho ket qua GS truoc khi quyet.)

## M11 — Hai diem neo 60390 va 60395: de bi doc thanh 2 config khac nhau

- `C2b` = **60390** (Oracle, `TICKER_SOURCE=aerospike`). Diem neo GS wave-1 = **60395**
  (Kaggle/Oracle, `TICKER_SOURCE=file`).
- Nguyen nhan da truy dut: **dung 1 lenh / 970** (FTT BUY 2022-11-09 01:00, giai doan FTX sup),
  duong aerospike cham SL sau 130h, duong file khong cham va di tiep den loser-time-stop 168h.
  PnL -1084.85 vs -1080.39. Lech +5 USDT = **0.008%**.
- `/home/ubuntu/gs/BASELINE_NOTE.md` da ghi ro va `PREREG_GS.md` §5 dat dieu kien VOID quanh 60395.
  Ghi lai o day vi memory chua co dong nao ve viec nay.

## M12 — Hai con so "base G015" khac nhau, ca hai deu dung

- `docs/ROADMAP_NOLEAK.md` bang ung vien freeze ghi "base G015 cung exit: CAGR **17.13** /
  maxDD -20.82". Memory `runs_log.md` + `dev_ab_2026-09-02.md` ghi "G1 base (G015) **13.85** / -15.6".
- Khong mau thuan: **17.13** = `C2_g015` b:51903 = G015 voi exit cua **C2a** (arm 7%, scale 1.5);
  **13.85** = `G1_giveback5` b:48352 = G015 voi exit **G1** (arm 5%, scale 1.0).
- Ghi vao day de khong ai lai lay 13.85 so voi 24.48 roi ket luan sai bien do.

## M13 — F5: 7 quyet dinh Pha 1 chua bao gio duoc quyet, 2 trong so do con nguy hiem

- `docs/PHASE1_DECISION_SURFACE.md`: cot "QUYET (1.2)" **trong hoan toan** o ca 3 bang A/B/C.
- Hai muc con song va nam **ngay tren duong gate cua C2b** (vi gate dung score G015, xem §3.3d):
  - **A2c** — label SL (adv) = **0.03**, ghi ro trong chinh doc la "SL placeholder, user chot sau
    — **CHUA TUNG CHOT**".
  - **A2e** — lay mau grid 15 phut, **overlap voi horizon 4h = L1 leak**; co mode nonoverlap nhung
    default la grid.
- => Trong khi moi cong suc 2026-09-02/03 do vao selector S1 va exit, **model cap score cho gate
  van la G015 voi 2 quyet dinh nhan chua bao gio duoc chot va 1 nghi van leak L1**. Day la no ghi
  chep nghiem trong nhat sau M1.

---

# PHU LUC — DIEM MASTER KET LUAN CHUA CHINH XAC

1. **"S1 ... khong thay apply duoc gi"** — SAI. S1 **da apply**, la thanh phan chinh cua C2b
   (`dev_c2.sh:23`). Cai chua apply la **pin bins vao profile** + **commit pipeline vao git**.
2. **"C2b co SELECTOR_RANK_TOPK=8 va SELECTOR_ONLY_ENTRY=1 — do co phai S1 khong?"** — hai key do
   **khong** quyet dinh S1; chung giong y nguyen o run `C2_g015` (bins G015). Bien quyet dinh la
   `WFO_FUNDING_PRED_DIR`.
3. **"profiles/c2b_min.properties"** — khong ton tai trong repo (M5).
4. **"nhieu cai duoc danh gia thang nhung khong thay apply"** — dinh luong: 20/48 muc DA apply
   (va do la toan bo noi dung C2b); 14/48 la THUA/FAIL do do nen dung khi khong apply; chi
   **5/48** la "thang/pass ma chua apply", trong do **4 la no ghi chep**, 1 bi luat pre-reg cam.
   Cam giac "khong apply duoc gi" den tu cho khac: **hau het thi nghiem tu 2026-09-03 tro di deu
   THUA C2b** (H1, K, BR, RG, RND, N1-N4, regime, H3) — tuc he da can du dia voi bo tham so va bo
   feature hien tai, dung nhu `9aceed5` ket luan. Do khong phai loi "khong apply", do la
   **het duong o tang tham so**.
