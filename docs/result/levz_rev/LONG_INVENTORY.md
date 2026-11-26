# LONG_INVENTORY - danh muc co che he LONG (c3 / v1.2) de doi chieu voi he SHORT LEVZ

Agent ra soat CHI DOC, 2026-11-26. Nguon code: worktree `~/claude_master/w3/c3_ops7` (nhanh `v1.2/ops-micro7`, HEAD fd0a2718) -
viet tat duong dan: `J=src/main/java/com/binance/chuyennd`. Tai lieu: `~/claude_master/vz_e1_wt/docs` (HEAD 442d2e27) + docs cua c3_ops7.
Profile tham chieu: `profiles/g2_flat3.properties` (= B0 "G2+FLAT3" ma DEPLOY242_G2FLAT3_READINESS goi la cau hinh dua len 242) va
`profiles/r4_kg0_k16_f015_g155.properties` (= cau hinh sim A3 cua HO5 / ky vong pilot).

CANH BAO TRUNG THUC (doc truoc):
- KHONG doc env that cua 242 (cam). Gia tri "dang chay" = profile + default trong code + tai lieu ops. Nhung cho tai lieu va profile
  KHAC nhau duoc danh dau [LECH]. Dac biet: K (SELECTOR_RANK_TOPK) = 16 trong g2_flat3 / r4, nhung GOLIVE_SCENARIO goi goi v1.1 la "K24 +
  skipFull + X14" -> K live 16 hay 24: CHUA XAC MINH.
- `LIVE_GATE_ROLLING_MODE=ratio / PCT=0.999950829 / DAYS=90` thay trong script ops/tai lieu (6 lan), khong kiem duoc tren env 242.
- Nhieu co che cua he LONG la MUC CUNG (khong rolling) - xem cot (4). Tien de "he LONG dung rolling moi cho" chi DUNG cho tang
  CHON LENH (gate p15, S1, net015-map) va mot so co trang thai; tang THOAT / DCA / kill-switch / phat hien sap deu la so cung.

Ky hieu cot (5): CO / MOT PHAN / CHUA / KHONG AP DUNG.

## A. Tin hieu / dieu kien vao (crash la gi)

| # | co che | lam gi | tham so that + noi dinh nghia | (4) co dinh / rolling | (5) SHORT LEVZ |
|---|---|---|---|---|---|
| A1 | Nhip quet market-level 1 phut | Moi phut tinh 3 so cap thi truong tu nen 1m: rateDownAvg, rateUpAvg, rateDown15MAvg | `J/trading/DetectEntrySignal2TradeNormal.java:217-356`; cua so 15 nen (`Configs.NUMBER_TICKER_CAL_RATE_CHANGE=15`, `J/tradecore/Configs.java:107`) | Cua so truot 15 phut (max/min gia 15 nen) - nhung chi la cua so do, KHONG chuan hoa | CHUA (SHORT tinh theo gio, khong co tin hieu sap cap thi truong 1m) |
| A2 | Do "sap" cap thi truong | rateDownAvg = TRUNG BINH cua 100 return 1m TE NHAT trong universe (cat 4/5 universe neu it coin) | `J/tradecore/MarketBigChangeDetector.java:167-197`, period=100 (`Detect...:332`) | CAT NGANG thi truong (trung binh N coin te nhat), N CO DINH=100. Co tuy chon chuan hoa N theo ti le universe `BD_FRACTION` (`:171-177`, PREREG_BD_CHAIN) nhung default 0 = TAT, profile khong khai | MOT PHAN (B2 co EWr_n = trung binh deu toan universe, khong phai "N coin te nhat") |
| A3 | Nguong BIG_DOWN | rateDownAvg < -3.157 % => level BIG_DOWN => mo leg market-signal | `Configs.MS_DOWN_BIG_AVG=-0.03157f` (`Configs.java:487`), `getMarketStatus1M` (`MarketBigChangeDetector.java:201-209`); profile khong override | **CO DINH tuyet doi**. Tai lieu RESULT_BD_THRESHOLD_FRAGILITY: "PnL BIG_DOWN dao 2x (8 323 -> 16 254 USD) trong 4 bien the nguong lan can" = nguong cung MONG MANH | KHONG AP DUNG (SHORT khong vao theo sap) |
| A4 | Nguong DCA_ALT (DCA_LEVEL1) | rateDown15MAvg < -3.157 % HOAC rateDownAvg < -1.052 % => leg DCA_LEVEL1 cho coin dang giu | `isDcaAlt` (`MarketBigChangeDetector.java:215-219`), `MS_DOWN_BIG_AVG_DCA=-0.03157f` (`Configs.java:491`) | CO DINH | KHONG AP DUNG |
| A5 | Loai coin "dump rieng / pump" khoi phep do | bo coin co ret 1m < -15 % khi BTC > -0.4 %; bo coin ret 1m > +30 % | `Detect...:287-292`, `MarketBigChangeDetector.java:87-90` | CO DINH | CHUA (SHORT khong loai outlier khoi EW) |
| A6 | Universe cua phep do market-level | c3_live chi tinh market level tren `marketIndexMembers` (da loai TradFi) | `Detect...:269-299` (U3) | cap nhat theo snapshot universe | MOT PHAN (B2 EWr tren universe qv30) |
| A7 | Ung vien selector (duong chinh) | Moi tick 15' S1 xep hang toan pool, lay top-K, moi coin qua gate p15 (muc B) | `Detect...:543-650`, `SELECTOR_RANK_TOPK` | xem C/D | MOT PHAN (SHORT co pool LEV + top-K theo s) |

Ghi chu A: duong vao chinh cua v1.2 la SELECTOR (PREDICT_SYMBOL_TRADE) + leg BIG_DOWN (chon coin theo S1-map, `BigDownSelect`) + DCA.
"Crash-buy" o tang tin hieu thuc chat = gate p15 (du doan return 15' cap thi truong) MO + S1 chon coin "da giam sau" (feature dd_7d, ret_3d...).

## B. Gate thi truong va gate tung lenh

| # | co che | lam gi | tham so that + noi dinh nghia | (4) | (5) SHORT |
|---|---|---|---|---|---|
| B1 | Gate p15 dong (cong thuc goc) | PASS <=> !(p15 < thr), thr = thrBase x max(DYN_MIN, sp/SCORE_BASE x DYN_MULT) x GATE_DYN_SCALE; sp = symbolPred (net015-map) | `J/tradecore/EntryGate.java:184-213`; DYN_MIN 0.26787, SCORE_BASE 0.15, DYN_MULT 1.28760 (hang so `:44-48`); GATE_DYN_SCALE 1.55 (g2_flat3/r4) | Nguong NHAN theo diem coin (thich nghi theo coin) nhung cac he so CO DINH | CHUA |
| B2 | **Gate rolling "deu lenh" (GDV2) tren ti so r** - co che THICH NGHI quan trong nhat | r = p15 / (max(DYN_MIN, sp/0.15x1.2876) x gs); q_t = phan vi PCT cua r trong buffer 90 ngay QUA KHU, tinh lai moi GIO (causal: chi r co ts < gio h); thrBase = q_t => thuc chat PASS <=> r >= q_t | `J/ai_ml/onnx/entry/AIRejectFilter.java:91-129`, `LiveGateRollingRatio.java:80-110, 368-395`, loi `GateRatioBuffer.java` (computeQ: k=floor(pct x (m-1)), warm-up 7 ngay); PCT=0.999950829, DAYS=90 (g2_flat3; LIVE_* trong ops) | **ROLLING 90 ngay, phan vi (quantile) cua CHINH chuoi r cua nguon dang chay**, nap r cua moi ung vien PREDICT (cat ngang + theo thoi gian). Persist qua restart + seed file (md5, lag <= 24h); seed hong => chan vao lenh moi. Muc dich: giu TI LE PASS on dinh qua regime | CHUA (SHORT dung z_min CO DINH 2,5 / 3,0 / 3,5) |
| B3 | San MIN_MOMENTUM_15M | Khi rolling bat: CHI la fallback trong 7 ngay warm-up (khong phai san duoi cua q_t). Van la nguong cho leg sp=null (DCA_LEVEL1). Leg BIG_DOWN c3 BO gate p15 (nhu sim) | `SIM_MIN_MOMENTUM_15M=0.008` (profile); `Configs.java:437` default 0.02284; `Detect...:1305-1316` (BIG_DOWN bo gate) | CO DINH (0.008) | KHONG AP DUNG |
| B4 | Tuy chon gate theo regime BTC 30d / phan vi cuon p15 30 ngay | GATE_REGIME_ADAPTIVE (scale 1.0 vs 1.7 theo uptrend BTC 30d); SIM_GATE_P15_Q (quantile cuon 30 ngay cua p15) | `EntryGate.java:60-86, 186-194` | ROLLING nhung **TAT** (default OFF, profile khong khai) - chi sim | CHUA (B2 co G_BTC7/G_BTC20/G_EW*, dau <= 0, khong rolling) |
| B5 | skipFull (QUOTA bo qua khi so day) | Neu U >= U_MAX thi ung vien PREDICT bi REJECT ma KHONG nap r vao buffer (khong lam lech phan phoi q_t) | `AIRejectFilter.java:105-109`; `Configs.GATE_QUOTA_SKIP_WHEN_FULL` (`Configs.java:163`, default false); GOLIVE goi v1.1 = "K24 + skipFull" [LECH: g2_flat3/r4 khong khai key] | trang thai | KHONG AP DUNG (SHORT khong co buffer) |
| B6 | Gate 2 tang NSEL | buffer THEM rieng cho hang > K | `NselGate.java` | ROLLING nhung **CHI SIM, TAT**; live khai key => nem loi | CHUA |
| B7 | Thu tu kiem tung leg THAT | push mo? -> kill-switch armed -> latch -> universe isBuyable -> so healthy -> reconcile -> LEGACY -> trung coin / DCA due -> AccountModeGuard (one-way, cross, lev 1) -> exchangeInfo -> sizing | `J/c3live/entry/C3LiveEntry.java:207-288` | CO DINH (luat) | MOT PHAN (sim SHORT: 1 vi the / coin, cooldown 72h) |
| B8 | TickWeakBlock | chan ca tick khi chi so yeu nam o duoi quantile cuon WIN ngay | `J/tradecore/TickWeakBlock.java` (quantile cuon `WIN_DAYS`, causal) | ROLLING - **profile khong khai, default chua xac minh** => khong tinh la dang chay | CHUA |
| B9 | Filter thanh khoan / tuoi niem yet / spread o duong vao LONG | - | Khong tim thay filter qv / spread / tuoi niem yet tuong minh trong C3LiveEntry hay isBuyable (chi TradFi / non-ASCII / delist < 7 ngay / EXCLUDE / PREMARKET). Gian tiep: S1 can 14 ngay du lieu gio (WARMUP_HOURS=336, `S1FeatureLive.java:54`), net015 can du 45 feature, map can >= 20 coin | - | SHORT CO (qv30 >= 20M, >= 45 ngay; B2 F_LIQ50, F_AGE90) - o diem nay SHORT CHAT HON LONG |

## C. Model

| # | model | dau vao | nhan | train / retrain | cach dung diem | (4) | (5) SHORT |
|---|---|---|---|---|---|---|---|
| C1 | p15 (gate) | 33 feature cap thi truong (`MarketFeatures`), ONNX TreeEnsembleRegressor 150 cay | cot `label_oldbasket` (`ml/gate/train_gate_fold.py:36`; dinh nghia chi tiet KHONG doc) - du doan return 15' | WFO expanding, cutoff theo QUY (fold_k = 2021-04-01 + 3k thang, purge); live = fold_20 (cut 2026-04-01, md5 8ec99757) DONG BANG | Nguong ROLLING quantile (B2), khong dung diem tuyet doi | model: retrain theo quy trong nghien cuu, live dong bang; nguong: ROLLING | CHUA (SHORT khong co model gate) |
| C2 | S1 (selector, "nguon edge duy nhat da chung minh") | 9 feature: vol_7d, dd_7d, rk_dd_7d, hrs_since_high_7d, ret_3d, rk_ret_3d, ret_14d, ls_global, rk_oi_delta24h | `rel5` = ngu phan vi TRONG TICK cua (g1lite - median_tick(g1lite)); g1lite = maxFav_72h >= 5 % ? maxFav - min(0,5 x maxFav, 8 %) : retEnd_72h | XGBRanker rank:ndcg, WFO 10 fold, purge 72h (`research/pipeline/README.md:67-108`); live s1a2x1_cut20251231 dong bang | XEP HANG (top-K), khong nguong | Feature: **ROLLING 7d/3d/14d cua chinh coin + RANK CAT NGANG (rk_*, pct across coins)**; nhan: **CAT NGANG trong tick** | MOT PHAN: SHORT B3 co model (Ridge/...), feature co "hang phan vi thanh khoan cat ngang", nhung nhan tuyet doi + nguong T20 = phan vi 80 % diem OOF TRAIN (co dinh theo tap train, khong cat ngang trong gio). B3 = KHONG DAT |
| C3 | net015 (P(win)) | 45 feature (cung bo model funding live) | 1 chieu y = (maxFav_4h >= 6 %), khong SL (PREREG_G015REBUILD) [nhan cua ban g015x26_f15 dang chay: chua doc ky] | cut 20251231 dong bang | **QUANTILE-MAP theo hang S1**: P(win) cua ca vu tru trong tick duoc gan lai cho coin theo THU HANG S1, sp = 1 - P(win) (`Detect...:796-830`, `LiveBuildMap.java`) | **CAT NGANG trong tick (rank mapping)** | CHUA |
| C4 | Trailing STRONG/WEAK theo sp | sp <= 0,29 => cap STRONG, nguoc lai WEAK | `TS_PNOPUMP_WEAK_THR` 0,29; `ShadowBookC3.trailRate` (`:356-377`) | CO DINH; o FLAT3 ca hai cap = 3 % => thuc te KHONG tac dung | CHUA |

## D. QUOTA / top-K / xep hang

| # | co che | lam gi | tham so | (4) | (5) SHORT |
|---|---|---|---|---|---|
| D1 | top-K selector | moi tick 15' lay K coin hang S1 tot nhat (`GatePreFilter.runSelector`) | K=16 (g2_flat3 / r4); [LECH] GOLIVE v1.1 noi K24; c3 cu K=8 | CO DINH so luong, xep hang = cat ngang | CO (K_max 3/5/10, xep theo s = min(z_oi, z_f)) |
| D2 | "Quota" ngam qua gate rolling | phan vi 0.99995 cua r trong 90 ngay => so lenh/thoi gian xap xi on dinh ("deu lenh") | B2 | ROLLING | CHUA |
| D3 | skipFull | B5 | | | KHONG AP DUNG |
| D4 | Nhip selector | 15 phut; market-level 1 phut (`MARKET_SCAN_MIN`, `Detect...:158`) | | CO DINH | SHORT theo gio |

## E. Sizing

| # | co che | lam gi | tham so | (4) | (5) SHORT |
|---|---|---|---|---|---|
| E1 | Goc equity compound (B3) | size tinh tren equity hien tai = balance + unrealized (MTM), khong phai von dau | `BudgetManagerSimple.equityNow`, `SIM_FIX_B3=true`; live: von = min(LIVE_C3_PILOT_CAPITAL, totalMarginBalance) cache <= 60s (`C3LiveEquity`) | THICH NGHI theo equity | CO (equity hien tai x 0,60 / K_max) |
| E2 | Ngan sach cum | ladder = equity x F_BASE x DCA_GRID_SCALE, chia theo trong so grid | F_BASE 0,015; SCALE 6,0; WEIGHTS 1,1,1,1 => cum toi da 9 % equity, moi leg 2,25 % | CO DINH (ti le) | MOT PHAN |
| E3 | Throttle theo muc su dung von | managerBudget: leg bi giam theo (1 - U/U_MAX); U >= U_MAX => khong mo | U_MAX 0,60 (`Configs.java:177`); `C3LiveEntry.java:256-262` (V12_CORE ghi "1 - U/U_MAX") | **THICH NGHI theo U (trang thai so)** | CHUA (SHORT: slot co dinh 0,60/K, chi chan khi het tran) |
| E4 | Tran 1 leg | <= 4,5 % equity | `LiveProfileC3.SIZE_CAP_OF_EQUITY=0.045f` (`:57`) | CO DINH | CHUA |
| E5 | Tran tap trung 1 coin | <= 15 % equity | `CONC_CAP_PERCOIN_ENABLED=true, PCT=0.15` | CO DINH | MOT PHAN (1 vi the / coin) |
| E6 | Tier multiplier | TIER_1 (top 20 % theo tong volume 720 nen) x1,2, TIER_2 x1,0, TIER_3 x0,5 (va TIER_3 chan DCA) | `CoinRankManager.java:121-126, 197-230` | XEP HANG CAT NGANG volume - nhung **TIER_FLAT=1** trong g2_flat3/r4/c3 => he so = 1,0 (TAT). Chan DCA TIER_3 trong C3LiveEntry van con (`:243`) - co bi TIER_FLAT tat khong: CHUA XAC MINH | CHUA |
| E7 | Tran so lenh nho nhat / budget toi thieu | budget < minBudget => bo | `C3LiveEntry.java:265` | CO DINH | - |

## F. DCA

| # | co che | lam gi | tham so | (4) | (5) SHORT |
|---|---|---|---|---|---|
| F1 | DCA grid | them leg khi gia <= gia vao DAU x (1 + level) | LEVELS -0,50 / -0,75 / -0,90 (default `Configs.java:217-218`), WEIGHTS 1,1,1,1, `DcaUtils.shouldDcaGrid` (`:32-43`), live `LIVE_DCA_GRID_ENABLED=true` | **CO DINH % tuyet doi**, khong theo bien dong coin | MOT PHAN (B0: +10 % 1 lan; chuong trinh: DCA khong uu tien) |
| F2 | DCA_LEVEL1 theo sap thi truong | A4 | | CO DINH | KHONG AP DUNG |
| F3 | Chan DCA | latch kill-switch chan; C4 cong suat KHONG chan DCA; TIER_3 chan; cum dang treo/dong chan | `C3LiveEntry.java:217-243` | luat | - |

## G. Thoat lenh

| # | co che | lam gi | tham so | (4) | (5) SHORT |
|---|---|---|---|---|---|
| G1 | Arm trailing | khi lai dinh >= 7 % thi dat STOP_MARKET tren san (MARK_PRICE) | `ARM_RATE=0.07f` (`LiveProfileC3.java:51`), `SIM_RATE_PROFIT_STOP_MARKET=0.07` | CO DINH % | CO (B1: arm 3/5/7/10 %) |
| G2 | Gap trailing (FLAT3) | exit = dinh - min(dinh x giveback, cap); g2_flat3: giveback 1,0, cap STRONG = WEAK = 3 % => gap 3 % | `SIM_TS_MAX_GAP=0.03`, `SIM_TS_MAX_GAP_WEAK=0.03`, `TS_GIVEBACK_RATIO=1.0`; dinh do bang high 1m (`TS_PEAK_MODE` default high) | CO DINH % | CO (gap 2/3/5 %) |
| G3 | Ratchet | doi stop lien tuc (dead-zone 1,0); live chi doi khi muc moi cao hon >= 1 tick VA >= 0,1 % | `RATCHET_DEADZONE_MULT_ON=1.0f`; V12_CORE muc 4 | CO DINH | CO |
| G4 | Time-stop | cum CHUA arm sau 168 h => dong | `TIME_STOP_HOURS=168`; `SIM_LOSER_TIME_STOP_HOURS=168` | CO DINH | CO (H 24..720 h) |
| G5 | Hoan time-stop X14 | ngay UTC co co "alt dang sap" => hoan time-stop toi +336 h | `TsMktExt.java` (EXT_HOURS 336); co(D): ALT_EW (trung binh deu log-return 1m moi alt tru BTC/ETH, cat +-0,5) - DD so voi DINH 31 ngay truot <= -30 % (`AltEwIndex.java:12-37`) | **Chi so ROLLING (dinh 31 ngay truot) + nguong CO DINH -30 %** | CHUA (SHORT khong co trang thai thi truong o tang thoat; T1 STATE thoat theo trang thai cua CHINH coin) |
| G6 | Stop loss cung | KHONG co SL cho cum chua arm (thiet ke; 1x long) | GOLIVE_SCENARIO:284 | - | SHORT LUON co SL 15/30/50 % (CO DINH %) |
| G7 | FLATTEN (kill-switch) | dong het reduce-only chia lo <= 5 lenh / 10 s | `C3LiveFlattener`; `LIVE_C3_FLATTEN_MAX_ORDERS` | CO DINH | CHUA (sim) |

## H. Kill-switch / giam sat

| # | co che | dieu kien | hanh dong | (4) | (5) SHORT |
|---|---|---|---|---|---|
| H1 | C1 du lieu | nen BTC moi nhat > 180 s hoac > 10 % symbol thieu | NO_NEW_ENTRY, tu nha sau 30' sach | CO DINH | CHUA (he SHORT chua co live) |
| H2 | C2 truot | truot bat loi > 2,5 % (3 lan / 24h) | latch | CO DINH | - |
| H3 | C3 loi API | >= 5 loi lien tiep | latch | CO DINH | - |
| H4 | C4 cong suat | > 90 vi the hoac U >= 0,60 | NO_NEW_ENTRY (code: latch theo quyet dinh MASTER 10-25; spec ghi tu nha) [LECH tai lieu/code, ghi o V12_CORE 0.3] | CO DINH | - |
| H5 | C5 khong tick | > 5' | NO_NEW_ENTRY | CO DINH | - |
| H6 | C6/A40 | DD MTM <= -40 % tu dinh pilot | dong het + latch | CO DINH | - |
| H7 | Breaker mat do | luy thua: cho phep 40 + 10 x m^0,6 lenh trong m phut (cua so 4'), lop 2: > 28 lenh "nguy hiem" | `MarketBigChangeDetector.java:230-335` (hang so) | CO DINH (cua so truot 4') | - |
| H8 | ConcCapLiveGuard | gioi han BIG_DOWN theo gio | `J/tradecore/ConcCapLiveGuard.java` (cua so 60' tu troi) | cua so truot 60', nguong co dinh | - |
| H9 | Reconcile | lech equity so vs san > 1 % => chan mo moi | V12_CORE C9 | CO DINH | - |
| H10 | Seed gate hong | chan vao lenh moi | `LiveGateRollingRatio.initSeedBranch` | - | - |

## I. Universe

| # | co che | lam gi | tham so | (4) | (5) SHORT |
|---|---|---|---|---|---|
| I1 | SymbolUniverseLive | buyable = perp, loai TradFi (classifier A1), non-ASCII, delist trong 7 ngay (`DELIVERY_GUARD_MS`), index/tong hop (ALLUSDT, BTCDOMUSDT), PREMARKET, EXCLUDE | `J/c3live/universe/SymbolUniverseLive.java:26-55`, REFRESH 15' | cap nhat dinh ky tu exchangeInfo; KHONG co nguong thanh khoan | MOT PHAN (SHORT: qv30 >= 20M TUYET DOI + >= 45 ngay + loai stable/index; khong loai TradFi tuong minh - chua kiem) |
| I2 | Quarantine id trung | `SimpleSymbolMapper.isQuarantined` | `Detect...:281` | - | - |
| I3 | LEGACY | khong vao coin dang giu o tai khoan chinh (tuy C3_EXCLUDE_LEGACY_HELD) | `LiveProfileC3.java:99-104` | - | KHONG AP DUNG |

## J. Phat hien nghien cuu lien quan (chi trich, khong dien giai them)

- RESULT_OI_STUDY (2026-09-23): H1 dOI cross-section NO-GO cho long; decile dOI cao nhat (Q9) te nhat 24h -0,4165 %/lenh nhung so EW (-0,2699 %)
  khong tach ro => "chi dung duoc o phia short/avoid"; H2 OI + gia phan ky NULL; H3 OI overlay len MOM15: thong tin co that (ter0 dOI thap
  +5,0 %, vua qua MDE) nhung KHONG GO de loc coin.
- RESULT_CROWDED_LONG (2026-09-24): crowded-long bang QUANTILE TRUOT (L/S cap thi truong) = KHONG phai tin hieu rui ro (CI chua 0, duoi MDE);
  thuc chat do "bull em"; duoi cua so KHONG tap trung khi ON; cu giam lon nhat 2025-10-10 -19,32 % xay ra khi tin hieu TAT. Dong truc positioning.
- LIQ_PROXY (2026-10-23): NO-GO ca 4 proxy thanh ly (OI roi + gia sap + taker ban) cho entry crash-buy.
- GATE_VZ (2026-10-17): them feature VZ cap thi truong (VA 8 cot, VB + OI/LS 13 cot) vao gate p15: NO-GO ca hai (mean dCAGR +0,68 / +0,39, CI chua 0).
- RESULT_FUNDING_FACTOR (2026-09-22): NO-GO 3 gia thuyet; funding cao la CHI PHI that cho long (D10-D1 net 24h -0,2525 %, CI khong chua 0)
  nhung dau chi dung 54,9 % so phut (< cong 60 %); decile funding thap cho long = NULL.
- RESULT_BD_THRESHOLD_FRAGILITY: edge BIG_DOWN mong manh theo nguong cung (PnL dao 2x qua 4 nguong lan can).
- C3_BASELINE: compound equity (B3) chi doi THANG DO, khong doi tap lenh; ban le STRONG/WEAK = doi median lay duoi, khong phai cai tien.
- Gate rolling GDV2 (ti so r, quantile 90 ngay): DUOC dua vao B0 (g2_flat3) va live - la co che thich nghi duy nhat o tang vao lenh da len production.
- LEVZ tang 1 (RESULT LEVZ.md): NO-GO, 4 nhanh truot C1 (p Holm 0,53-0,79) va C5. LEVZ B3 (commit 442d2e27): sort bang model KHONG DAT
  (WFO 2025 -32,6 %, kem ngau nhien p 0,97).
- Khong tim thay ket qua rieng cho LEVZ B1/B2/T1 trong luot doc nay (chi doc prereg).

---

## (i) Nhung cho he LONG dung ROLLING / THICH NGHI ma he SHORT dang dung muc cung hoac chua co

| # | co che LONG | cua so | chuan hoa theo | SHORT hien tai |
|---|---|---|---|---|
| 1 | Gate rolling ti so r (B2) | 90 ngay, tinh lai moi gio, warm-up 7 ngay, persist | PHAN VI (0,99995) cua chuoi r = diem / he so theo coin, gop moi ung vien (cat ngang x thoi gian) | z_min CO DINH 2,5 / 3,0 / 3,5; B3 T20 = phan vi 80 % diem OOF TAP TRAIN (co dinh theo fold) |
| 2 | Feature S1 | 7d (168h, min_periods 84), 3d, 14d cua chinh coin | rolling max / std chinh coin + RANK pct cat ngang (rk_dd_7d, rk_ret_3d, rk_oi_delta24h) | z-score rolling chinh coin (CO), nhung KHONG co rank cat ngang trong s = min(z_oi, z_f) |
| 3 | Nhan S1 | moi tick 15' | ngu phan vi TRONG TICK cua (g1lite - median tick) | nhan B3 = loi nhuan lenh tuyet doi (net_ex chi tru EW o tang 1) |
| 4 | net015 quantile-map | moi tick | gan P(win) theo thu hang S1 (rank mapping) | CHUA |
| 5 | Do sap cap thi truong | 1 phut / 15 phut | trung binh N coin te nhat (cat ngang); tuy chon N = ti le universe (TAT) | B2 EWr_n trung binh deu, nguong dau <= 0 |
| 6 | X14 ALT_EW drawdown | dinh 31 ngay truot | log-return EW alt, DD so dinh truot | CHUA o tang thoat |
| 7 | Throttle U/U_MAX | trang thai so | margin dang dung / equity | slot co dinh equity x 0,60 / K |
| 8 | Tier theo volume | 720 nen | xep hang volume cat ngang | qv30 >= 20M TUYET DOI (va 50M o B2) - nhung o LONG tier dang TAT |
| 9 | ConcCap BIG_DOWN / breaker mat do | 60' / 4' truot | dem lenh | CHUA (sim SHORT co cooldown 72h / coin) |
| 10 | Retrain model WFO | theo quy, expanding, purge | - | B3 co WFO theo nam |

Nguoc lai, nhung cho LONG CUNG (khong nen dung lam ly do "LONG rolling"): nguong BIG_DOWN -3,157 %, DCA -50/-75/-90 %, arm 7 %, gap 3 %,
time-stop 168h, X14 -30 %, U_MAX 0,60, tran 4,5 % / 15 %, toan bo kill-switch, MIN_MOMENTUM 0,008, DYN_MIN / SCORE_BASE / DYN_MULT, STRONG thr 0,29.

## (ii) Muc cung cua he SHORT (prereg + code)

Code `~/claude_master/w3/levz/code/levz.py` (sig.py cua levz2 import nguyen ban nay):
- `Z_TH = 2.5` (:27) - nguong z cua ca z_oi va z_f (z la rolling, nguong cung).
- `F_MIN = 0.0001` (:28) - san funding TUYET DOI 0,01 %/8h (r8). Ghi chu: day la muc nen co che cua Binance, nhung KHONG theo coin / thi truong.
- `SD_OI_FLOOR = 0.02` (:29) - san sd log-OI; `SD_F_FLOOR = 0.00005` (:30) - san sd funding 0,005 %/8h (PREREG_LEVZ muc 2 dong 29-31).
- `ZR_TH = -2.0` (:31) - xac nhan E1; z_r = r1h / sd (khong tru mean) (`ret_z` :136-144).
- `COOL_H = 72` (:32), `E1_WIN = 24` (:33), `WS = (14, 7)` ngay (:24), `HS = (4, 24, 72)` (:23), `FEE = 0.0014` (:21).
- fund_z: can n >= 0,8 x W / ih (xu ly ky funding 4h/8h - da thich nghi theo chu ky) (:147-169).
- Universe `common.py:92-104`: qv30 (trung binh 30 ngay truoc, rolling mean) >= 20M USD TUYET DOI, niem yet >= 45 ngay.
Prereg:
- PREREG_LEVZ2: z_min {2,5; 3,0; 3,5}; K_max {3,5,10}; SL {15,30,50 %}; H {24,72,168}; trailing 10 %/5 %; DCA +10 % 1 lan; size equity x 0,60 / K;
  phi 0,07 %/chieu; truot SL 0,5 %.
- PREREG_LEVZ_B1: SL {15,30,50 %}; H {24..720}; arm {3,5,7,10 %} x gap {2,3,5 %}; truot SL 0,3 %, trail 0,1 %.
- PREREG_LEVZ_B2: GATE dau <= 0 tren EWr_3/7/14, BTCdev_7/20 (nguong 0 cung, chi so co cua so); FILTER qv30 >= 50M, tuoi >= 90 ngay, r24 < +20 %,
  r24 >= +10 %, f >= 0,0003 (TUYET DOI); BR / BRmed (trung vi - co yeu to tuong doi).
- PREREG_LEVZ_B3: z_min 1,5; f > 0,01 %; T20/T10 = phan vi 80/90 % diem OOF tap train; Ridge alpha 10.
- PREREG_LEVZ_T1: BRK SL {3..20 %}, R {0,5..3}; VOL SL = a x sd log-return gio 168h x sqrt(24), a {1,1,5,2,3}, san 2 %, tran 50 % (=> DA CO
  thoat theo bien dong, MOT PHAN); STATE thoat khi z < z_out {0,1} hoac f <= 0,01 %.

## (iii) De xuat ap dung cho SHORT (chi de xuat, xep theo muc co can cu; chua chay thu)

1. **Gate "deu lenh" kieu GDV2 thay z_min co dinh** (can cu MANH nhat: co che thich nghi duy nhat cua LONG da len production). Diem
   s = min(z_oi, z_f) (hoac ti so s / he so); vao khi s >= phan vi P cua buffer s moi ung vien 90 ngay qua, tinh lai moi gio, causal,
   warm-up 7 ngay, fallback = nguong cung hien tai. P chot truoc bang ti le lenh muc tieu (khong tune theo PnL). Loi ich: so lenh on dinh
   qua regime (2022 gan nhu khong co su kien). Rui ro: buffer cung pha tron het coin; them skipFull (khong nap khi so day) nhu LONG.
2. **San funding tuong doi thay F_MIN = 1e-4 / 3e-4 tuyet doi**: f vuot phan vi cat ngang cua universe tai gio t (vd f >= trung vi
   cat ngang + delta) hoac rank pct cat ngang. Can cu: LONG dung rank cat ngang trong feature (rk_*) va nhan S1; RESULT_FUNDING_FACTOR cho
   thay funding co cau truc cat ngang (D10 vs D1) that. Giu F_MIN la dieu kien co che phu (f > muc nen) neu muon.
3. **San sd (SD_OI_FLOOR 0,02, SD_F_FLOOR 5e-5) suy tu phan phoi cat ngang**: vd san = phan vi 10-20 % cua sd rolling cua universe tai t
   (cung W). Can cu: trung binh - LONG khong co tuong duong truc tiep (DYN_MIN cua LONG cung la hang so). Kiem bang V4 cua LEVZ (ti le dot
   bi san bind).
4. **Nhan / feature cat ngang cho tang SORT (sau B3 khong dat)**: nhan = ngu phan vi TRONG GIO cua loi nhuan short (tru median gio), feature
   them rank pct cat ngang (rk_z_oi, rk_z_f, rk_r24, rk_dOI24h). Can cu: S1 la nguon edge da chung minh cua LONG va dung dung cach nay. Rui ro:
   so ung vien / gio cua SHORT nho (PROGRAM: < 300 / nam => khong lam B3) - phai dem truoc.
5. **Universe thanh khoan theo phan vi**: qv30 >= phan vi X % cat ngang moi ngay thay 20M / 50M USD tuyet doi (so sym 138 -> 611 qua cac nam).
   Can cu: yeu (tier volume cua LONG dang TAT); loi ich chu yeu la on dinh dinh nghia qua thoi gian.
6. **Gate thi truong chuan hoa theo universe thay dau <= 0**: BR (do rong LEV) so voi trung vi / phan vi rolling cua chinh BR (B2 da co BRmed -
   mo rong sang phan vi 90 ngay); EWr_n chia cho do bien dong EW rolling. Can cu: BD_FRACTION + RESULT_BD_THRESHOLD_FRAGILITY cua LONG (nguong
   cung cap thi truong mong manh). Luu y G_EW14 cua SHORT la gia thuyet hau kiem.
7. **Throttle phoi nhiem theo U (1 - U/U_MAX) thay slot co dinh 0,60/K**: can cu trung binh (LONG giu tap lenh on dinh qua compound + throttle);
   tac dong chu yeu len tap trung khi nhieu ung vien cung gio.
8. **Co trang thai thi truong tren chi so EW alt (dinh 31 ngay truot) cho tang thoat**: vd khi alt dang tang manh / squeeze toan thi truong
   (guong X14) thi rut time-stop hoac siet SL. Can cu: X14 duoc dua vao v1.1 sau nghien cuu TSX; voi SHORT chua co bang chung.
9. **Thoat theo bien dong (T1 VOL) da co** - KHONG lay LONG lam can cu: LONG dung arm / gap / DCA theo % CO DINH. Neu T1 VOL thang thi do la
   phat hien rieng cua SHORT.

KHONG tim thay trong code / tai lieu da doc: filter spread o duong vao LONG; filter thanh khoan tuong minh o duong vao LONG; dinh nghia chinh xac
`label_oldbasket` (p15) va nhan cua net015 ban g015x26_f15 dang chay; gia tri env that tren 242 (K, skipFull, LIVE_GATE_ROLLING_*); ket qua
LEVZ B1 / B2 / T1; mac dinh TICK_BLOCK_*; viec TIER_FLAT co tat luon chan DCA TIER_3 o C3LiveEntry khong.
