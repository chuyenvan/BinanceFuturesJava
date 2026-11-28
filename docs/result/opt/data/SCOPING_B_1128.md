# SCOPING_B_1128 - su that cho prereg ADD1 (PROGRAM_OPT muc B). Agent khao sat CHI DOC, 2026-11-28.
Nguon code SIM = commit a8690d46 (jar sim-jar-tsx cc0f9d11, ~/claude_master/tsx/code_sha.txt). CANH BAO: worktree vz_e1_wt (nhanh
research/vz-e1, HEAD 07e98ab4) KHONG chua code TSX (grep LOSER_TS_EXT = 0) => doc Java bang `git show a8690d46:<file>`.
Viet tat: SIM=research/SimulatorMarketLevelTicker1MStopLoss.java, OTI=research/OrderTargetInfoTest.java, CFG=tradecore/Configs.java,
TU=tradecore/TradeUtils.java (tat ca duoi src/main/java/com/binance/chuyennd, tai a8690d46). Live = ~/claude_master/w3/c3_ops7 (fd0a2718).

## Q1 Tham so thoat / DCA (baseline r1-a3 = /home/ubuntu/kaggle_sim/out/r1-a3-*/prof_run.properties + result.json overrides)
| bien | baseline | y nghia (code) |
|---|---|---|
| SIM_RATE_PROFIT_STOP_MARKET | 0.07 | arm khi HIGH 1m >= priceEntry*(1.07); priceEntry = VWAP cac leg (mergeOrder SIM:1199-1212). SIM:1098-1111, TU:107-113 |
| TS_GIVEBACK_RATIO / SIM_TS_MAX_GAP / _WEAK | 1.0 / 0.03 / 0.03 | SL = VWAP*(1+r), r = round_0.005(peak - min(peak*1.0, 0.03)); peak = (HIGH nen hien tai/VWAP - 1); TU:52-58 trailFromCap, OTI:372-383. Arm 7% => SL +4% |
| ratchet | lien tuc | OTI:246-268: SL chi tang, > VWAP; minPrice reset = close nen khi doi SL |
| khop stop | LOW nen SAU <= SL | OTI:203-240: BLOCK_INTRABAR_LOOKAHEAD=true (CFG:122) => nen arm khong khop; nen sau: low<=SL => gia = min(SL, OPEN). Status STOP_MARKET_DONE (SL>VWAP luon) |
| SIM_LOSER_TIME_STOP_HOURS | 168 | cum CHUA arm, tu leg DAU (clusterFirstLegTime), dong tai min(open,close), status STOP_LOSS_DONE. SIM:1042-1060 |
| SIM_LOSER_TS_EXT_HOURS / _DAYS | 336 / 42 dai ngay (flags.json) | hoan time-stop toi 168+336h trong khi ngay UTC (floorDiv(ms,86400000)) cua TICK thuoc tap ngay; SIM:1045-1047, CFG:166-167, 922-933 |
| SIM_PRE_ARM_SL / HARD SL / TP | 0 / tat / 0 | KHONG co trong baseline (0 dong log PREARM_SL/HARD SL theo A1_F2B_RESULT muc 2) |
| DCA_GRID_LEVELS (default) | -0.50,-0.75,-0.90 | tu GIA LEG DAU (firstEntryPrice), dung lastPrice=close; CFG:208-209, DcaUtils.shouldDcaGrid. Toi da 3 leg DCA (4 leg/cum) |
| DCA_GRID_WEIGHTS / SCALE / SIM_F_BASE | 1,1,1,1 / 6.0 / 0.015 | leg = equity*0.015*throttle/4*1*6 = 2.25%*throttle (TU:125-143, DcaUtils.gridLegWeightRatio FIX_B2); throttle = 1-U/0.60; U>=0.60 => khong mo (ca DCA) |
| TIER_FLAT | (ten co, gia tri khong in) | TIER_3 chan DCA SIM:1432-1436 |
| SELECTOR_RANK_TOPK / GATE_QUOTA_SKIP_WHEN_FULL | 24 / true | override result.json |
Cong thuc MASTER b=min(0.045C;0.0225C(1-U/0.6))xtier: o SIM khong co tran 0.045 (vo hieu vi 0.0225<0.045); tran 4.5% chi o live (LiveProfileC3:57).
DCA o SIM KHONG phai luoi gia thu dong: chi xet o tick co tin hieu thi truong (getMarketStatus1M != null, SIM:336-367) hoac isDcaAlt
(SIM:397-404); sau DCA cum moi: priceSL=null (arm reset), VWAP moi, time-stop van neo leg dau. Ledger c0s42: 60 leg DCA, entry/first =
-0.50..-0.90; nam 2022:32, 2024:1, 2025:27.
Live (c3_ops7 c3live/exit/TrailingStopManager.java:33-40,200-240): peak theo gia lay mau ~10s (khong phai HIGH 1m), STOP_MARKET tren san
workingType MARK_PRICE, VWAP = avgEntryF, ARM 0.07 / TIME_STOP 168 (LiveProfileC3.java:51-53), X14 qua LIVE_TS_MKT_EXT; DCA live qua
C3LiveHook.dcaDue (shouldDcaGrid). Lech D1/D2/D8 (OWNER_DECISION_PILOT_1121_ADD6:12). K live 16 hay 24: CHUA XAC MINH (cam doc env 242).

## Q2 DEV 4 seed vs r1-a3
prof_run.properties md5 GIONG HET (dc468e3f) 6/6; overrides giong (K24, skipFull, X14 336h); profile r4_kg0_k16_f015_g155, jar cc0f9d11,
2021-07-01..2025-12-30, von 35000. Khac DUY NHAT: model gate p15 (pred_md5_used: c0s* = 4 lan train lai model PROD; r1-a3 A1 = template,
S7 = b737fb6d) + snapshot mapper ho5. => cung co che thoat, GOP duoc cho phan tich trailing/DCA, NHUNG khong doc lap (cung su kien thi
truong, cung cau hinh): la kiem do ben theo nhieu model, khong phai lap lai.

## Q3 printDone.csv (ca hai bo, header TraceOrderDone.printOrderTestDone)
1 dong / LEG. sym (bo USDT), side BUY, entry (gia leg), tp (= gia THOAT cum), profit % leg = 100*(tp/entry-1), status, start/end
'YYYYMMDD HH:MM' UTC+7 (llv/levz_an da audit; tru 7h ra UTC), time_start_format, level (PREDICT_SYMBOL_TRADE | BIG_DOWN | DCA_LEVEL1),
maxmin15m (rateChange), lastentry, volume (quote vol nen vao), quantity, margin (=entry*qty, lev 1), pnl USDT = qty*(tp-entry)
- fee 0.000982*notional - slip 2*0.000067 - funding, time_order = gio giu (floor, leg), funding (CA CUM gan vao leg dau), dow/up/dow15m
(rateDownAvg/rateUpAvg/rateDown15MAvg luc vao), pred15m (p15), risk4h, symbolPred (sp).
CUM dung = (sym, end): closeOrder chep cung end/tp/status cho moi leg (SIM:1127-1160). Kiem: 0 cum >1 gia thoat, 0 chong lan thuc su,
256 "cham" (cum moi mo dung phut cum cu dong). llv.py:72-99 noi ca chuoi cham => clusters.parquet GOP SAI ~7.5% (c0s42 3146 vs 3402).
Ly do thoat: STOP_MARKET_DONE = trailing; STOP_LOSS_DONE = time-stop (time_order leg dau 168 = thuong; 169-504 = da hoan X14).
| ledger | cum | 1/2/3/4 leg | cum co DCA | TRAIL | TIME-STOP (168 / X14 169-504) |
|---|---|---|---|---|---|
| c0s42 | 3402 | 3352/41/8/1 | 50 | 2872 | 530 (385/143) |
| c0s7 | 3521 | 3467/45/8/1 | 54 | 2970 | 551 (414/135) |
| c0s123 | 3516 | 3473/33/9/1 | 43 | 2985 | 531 (394/135) |
| c0s13 | 3392 | 3342/41/8/1 | 50 | 2894 | 498 (357/139) |
| r1a3-a1 | 3559 | 3506/44/8/1 | 53 | 3003 | 556 (405/149) |
| r1a3-s7 | 3491 | 3443/40/7/1 | 48 | 2923 | 568 (413/153) |
(moi bo con 2 cum time-stop "khac"; khong cum mo cuoi ky.)

## Q4 Duong gia
close1m.npy: [631 sym x 2 148 480 phut] float32, CLOSE ffill, 2021-12-01..2025-12-31 UTC (common_b1.py:16-21; nguon
res1109/r1_s1/kl/kline1m-*.parquet chi cot ts,sym,close). Cum du duong [vao .. thoat+168h] khong gap: 82.8-83.8% moi bo; thieu chu yeu do
vao < 2021-12-01: 15.0-16.0% (528-543 cum); 4-5 cum sym khong co (BLUEBIRD, DEFI, FOOTBALL); 35-41 cum co gap. Tu 2022: 98.5-98.6% du.
Nguon 1m khac: ~/claude_master/gvz/k2021/kline1m-2021-01..12.parquet (OHLCV day du, Vision) => lap duoc 2021-07..11; OHLC 1m 2022-2025:
KHONG TIM THAY tren Oracle (kl chi close; ticker_*.bin.gz cua sim KHONG con o /home/ubuntu/java/simulator/kaggle_data_hpo/daily; chi co
tren dataset Kaggle TICKER_DS). /home/ubuntu/exitfit/bars.pkl = OHLC chi cho cum T170 cu.

## Q5 Tai lap thoat
Phai mo phong: thu tu trong 1 nen (SIM:1000-1111): update minPrice=min(.,LOW), maePeak -> [PRE_ARM_SL off] -> time-stop (chua arm, neo leg
dau, X14 theo ngay UTC cua tick) -> arm neu HIGH>=VWAP*1.07 (dat SL, KHONG khop nen nay) -> da arm: khop neu minPrice<=SL tai min(SL,OPEN),
roi moi ratchet theo HIGH nen; lam tron 0.005; normalizePrice tick (FLOOR); float32; DCA: cum moi, arm reset, minPrice=close; gia vao = CLOSE
nen. Can HIGH/LOW/OPEN => close-only KHONG tai lap dung (arm/peak lech xuong, stop kich muon). Co san: w3/add24_wt/research/exitfit/
exit_engine.py + parity.py: parity PASS tren T170 (1089 leg: status 100%, phut 100%, gia 99.82%; RESULT_EXIT_FIT.md:59-71) nhung hang so
T170 (fee 0.002, giveback 0.5, cap 0.08) + can OHLC ticker sim. Do kho: TRUNG BINH neu co OHLC (doi hang so + them X14 + DCA path), CAO/
khong trung thuc neu chi close.

## Q6 X14
Java KHONG doc flags.json: doc property SIM_LOSER_TS_EXT_DAYS (chuoi yyyyMMdd-yyyyMMdd, ngay UTC) + _HOURS. Tac dung DUY NHAT: hoan
time-stop cum chua arm (khong chan vao lenh, khong dong vi the, khong doi arm/gap/DCA). r1_a3_driver.py:36-37 nap
~/claude_master/tsx/flags.json["ranges"] (luat: tsx_flags.py, ALT_EW DD 31 ngay <= -30%, flag d+1) vao OV; f2b_driver.py:66,150-153 bo/giu
X14_KEYS. Doi danh sach ngay = chi doi chuoi override (khong sua Java/jar). Chan vao lenh theo ngay: KHONG co co che sach. Gan nhat:
SIM_GATE_REGIME_ADAPTIVE + SIM_REGIME_FILE (RegimeSchedule, scale gate theo ngay UTC, GateRollingRatio.java:117) - nhung scale vao r va
vao BUFFER q_t 90 ngay, BIG_DOWN bo gate, can ship file => khong phai loc sach. Doi arm/gap/DCA theo ngay/co: KHONG co (SL_ADAPT_* theo
selRank, TS_LADDER theo dinh) => phai sua Java.

## Q7 Thong tin luc vao
Trong printDone: pred15m (p15), symbolPred (sp), dow/up/dow15m, level (BIG_DOWN), volume. r tinh lai duoc cho leg PREDICT
(r = p15/(max(0.26787, sp/0.15*1.2876)*1.55)); q_t, so ung vien/gio, ung vien bi tu choi: KHONG luu (log chi co 3 dong [GATE-RATIO] tong
ket, logs/full.log r1-a3-a1). TickDecisionLog (TICKLOG) tat trong baseline.

## Q8 Sai / can dinh nghia lai
1. B3 DCA: chi 43-54 cum co DCA / bo (1.3-1.5%), muc -50/-75/-90% tu leg dau, don vao vai dot 2022 + 10/2025; cac bo trung su kien =>
   chia tam phan vi trang thai ~15 cum/o: KHONG du luc. Chi lam mo ta, hoac doi cau hoi (luoi DCA nong hon) = phai sim.
2. "Cung dau tren hai bo" khong phai lap lai doc lap (Q2).
3. Khong dung llv clusters.parquet (gop sai); khoa cum = (sym, end).
4. B2 MFE/giveback phai do tren VWAP, peak = HIGH 1m; close1m lam lech he thong; 2021-07..11 khong co trong close1m (dung gvz/k2021).
5. "Muc NGAY ... co che co ngay giong X14": X14 khong chan vao lenh; can code Java moi hoac chi uoc tren ledger (khong phan hoi danh muc).
6. Replay Python khong co phan hoi: U/throttle, skipFull -> buffer q_t, vao lai cung coin.

## Ket luan
(a) Trailing/DCA theo cum tu duong gia: kha thi cho MO TA (MFE/MAE/thoi gian) 2022-2025 voi close1m (~98.5% cum) neu ghi ro lech close;
    counterfactual (arm,gap) chi trung thuc voi OHLC 1m (gvz/k2021 cho 2021; 2022-2025 phai lay ticker sim tu Kaggle) + engine exitfit
    sua hang so + calib parity voi ledger baseline truoc. DCA: khong du mau.
(b) Sim Java "loc theo ngay": doi ngay X14 = san (chi time-stop). Chan vao lenh theo ngay: CHUA co => them Java (vd SIM_ENTRY_BLOCK_DAYS,
    chan createOrder leg mo cum moi, khong nap r khi chan, default off byte-identical) + jar moi + cong parity.
(c) Doi tham so theo trang thai: sua Java, mau nhu X14: tap ngay + armRate/gap/DCA levels thay the ap tai SIM:1098 (armRate), OTI:372
    (trailRate), DcaUtils.shouldDcaGrid; chot truoc neo = ngay leg dau hay ngay tick; ~40-80 dong + test + parity OFF.
