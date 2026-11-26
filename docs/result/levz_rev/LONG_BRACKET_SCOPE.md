# LONG_BRACKET_SCOPE - khao sat cong lam "LONG vao lenh co SL + TP theo ti le R, khong DCA" bang simulator hien co

Agent CHI DOC, 2026-11-26. Code: `~/claude_master/w3/c3_ops7` (v1.2/ops-micro7). Tai lieu: `~/claude_master/vz_e1_wt/docs`.
Viet tat: `SIM=src/main/java/com/binance/chuyennd/research/SimulatorMarketLevelTicker1MStopLoss.java` (1 959 dong),
`CFG=src/main/java/com/binance/chuyennd/tradecore/Configs.java`.

## 0. RUI RO / PHAT HIEN QUAN TRONG NHAT (doc truoc)
1. **Ho nay DA DUOC DO MOT LAN**: `docs/result/RESULT_FAMILY2_TP_SL.md` (2026-09-27, prereg PREREG_FAMILY2_TP_SL + AMENDMENT):
   "TP nho + SL nho, KHONG DCA -> 0/4 PASS". N1 TP 2 % / SL -1 %, N2 TP 1 % / SL -1 %, N3 TP 3 % / SL -1,5 % (DCA OFF), N4 = N1 + time-stop 24h.
   Ca 4: equity 35 000 -> 11 111..12 465, CAGR -20,5..-22,9 %, maxDD -64..-68 %; win% sup, TSloss% tang ngoai CI theo huong XAU.
   N4 == N1 tung byte (moi cum da bi TP/SL dong truoc 24h). Ly giai cua tai lieu: chi phi khu hoi ~0,6-0,8 % + SL -1/-1,5 % => lo deu;
   bo trailing => mat nguon PnL duy nhat (duoi thang). => Vung SL nho (<= 1,5 %) / TP nho (<= 3 %) da DONG. CHUA do: SL rong
   (5..20 %), R >= 1 voi SL rong, SL/TP theo bien dong. Prereg moi phai neu ro day la mo rong FAMILY2, khong lap lai.
2. **Bay sizing khi tat DCA**: `TradeUtils.managerBudget` chia cho TONG trong so grid (`dcaGridTotalWeight`, `CFG:326-334`).
   Neu chi dat `DCA_GRID_ENABLED=false` ma giu `DCA_GRID_WEIGHTS=1,1,1,1` => leg = equity x F_BASE x throttle / 4 = 0,375 % equity
   (nho 6 lan so voi 2,25 % hien tai) va DCA_GRID_SCALE KHONG con duoc nhan. Cach dung da co tien le: `DCA_GRID_WEIGHTS=1,0,0,0`
   (profile c3; C3_BASELINE do n_DCA = 0) + env `WFO_DISABLE_DCA=1` (FAMILY2 da dung, tat DcaProcessor.getDCA).
3. **Sim khac live o co che stop** (R-LIVE, `docs/result/add24_rlive_ow2/MASTER_CONCLUSION_RLIVE_1124.md:14-15`): lech nhat quan D1
   (live kich stop theo MARK price, sim theo gia LAST/nen), D2 (live lay mau 10 s, sim dung HIGH nen 1m), D8 (gia vao = gia khop).
   SL chat lam cac lech nay LON hon (nhieu lenh thoat gan muc stop). Duong LIVE c3 hien KHONG co SL truoc arm / TP / time-stop cho
   kieu bracket (c3live/exit chi co arm + trailing + time-stop 168h + X14) => muon live phai viet code live rieng (khong thuoc khao sat nay).

## 1. Simulator va duong thoat lenh
- Engine: `SIM` (`simulatorWithInitEntry`, IntegrityGuard cam o dau). Vong lap PHUT: moi phut moi symbol dang giu goi
  `startUpdateOldOrderTrading` (`SIM:267`, dinh nghia `SIM:1121-1240`). Thu tu trong 1 nen 1m:
  PRE_ARM_SL -> LOSER_TIME_STOP -> COND_EXIT -> TP -> arm/trailing (`OrderTargetInfoTest.updateStatusNew/updateTPSL`).
  Cung nen ca SL va TP => SL thang (quy uoc X2).
- Do phan giai: nen 1 PHUT. SL: `bar.low <= stop` => thoat tai min(stop, open, close) (`PreArmSlUtils.java`, khong bao gio tot hon stop).
  TP: `bar.close >= TP` => thoat DUNG muc TP (bo qua rau nen; khong truot). Arm: `peakPrice` = HIGH 1m (TS_PEAK_MODE mac dinh high).
  Time-stop: thoat tai min(open, close). Muc SL/TP do tren `firstEntryPrice` (gia leg DAU).
- Bang owner muon:

| # | muon | trang thai | key / file:dong | ghi chu |
|---|---|---|---|---|
| a | tat DCA | CHI CAU HINH | `DCA_GRID_WEIGHTS=1,0,0,0` (grid ratio leg>=1 = 0 => khong mo, `SIM:1641-1655`) + env `WFO_DISABLE_DCA=1` (`CFG:366-368`, `DcaProcessor.java:28-30`; key INFRA => qua `kaggle_sim.submit(extra_env=...)`) | KHONG dung `DCA_GRID_ENABLED=false` (bay muc 0.2) |
| b | SL co dinh % | CHI CAU HINH | `SIM_PRE_ARM_SL` (am, vd -0.08) `CFG:521`, parse `CFG:945`; logic `SIM:1126-1151` | chi ap cum CHUA arm; voi TP_ONLY khong bao gio arm => ap moi lenh. Co them `SIM_SL_ADAPT_HARDSL*` (theo selRank, `CFG:648-653`) |
| c | TP co dinh % | CHI CAU HINH | `SIM_TAKE_PROFIT_RATE` (`CFG:197`, `:946`), `SIM_TAKE_PROFIT_ONLY=true` bo arm/trailing (`CFG:199`, `:947`); logic `SIM:1189-1216` | da qua cong parity byte-identical khi OFF (FAMILY2 muc 2) |
| d | SL/TP theo bien dong coin | PHAI SUA CODE | khong co key. Gan nhat: `VolTargetSizing` (vol 7d chinh coin, chi cho SIZE), `SL_ADAPT_*` (theo hang, khong theo vol) | uoc: ham thuan trong tradecore (vd `VolBracket.levels(vol, a, R)`) ~30-40 dong + field vol luc vao tren `OrderTargetInfoTest` ~5 + noi vao 2 cho SIM (PRE_ARM_SL, TP) ~15-25 + Configs ~10-15 + unit test ~60 => ~70-100 dong main + test; cong parity OFF byte-identical; rebuild jar STUB + dataset jar |
| e | time-stop ngan hon | CHI CAU HINH | `SIM_LOSER_TIME_STOP_HOURS` (`CFG:508`, `:942`; `SIM:1153-1172`) - chi cum chua arm (voi TP_ONLY = moi cum); `SIM_COND_EXIT_HOURS/_MIN_FAV` (`CFG:509-514`) | thoat tai min(open, close) |

## 2. Sizing / QUOTA co phu thuoc DCA khong (su that tu code)
- `TradeUtils.managerBudget` (`TradeUtils.java:125-143`): U = margin/equity; U >= U_MAX(0,60) => null; throttle = clamp(1 - U/0,6);
  budget = equity x F_BASE x throttle / dcaGridTotalWeight(). Sim nhan tiep tier (TIER_FLAT=1 => 1,0), [VolTarget/Pacing TAT],
  roi `gridLegWeightRatio` = w x SCALE (fix B2) => leg = equity x F_BASE x SCALE x w/total x throttle. g2_flat3: 0,015 x 6 / 4 = 2,25 %;
  tran 4,5 % (live `LiveProfileC3.SIZE_CAP_OF_EQUITY`; sim = equity x F_BASE x SCALE theo C3_BASELINE). Cong thuc MASTER
  b = min(0,045C ; 0,0225C(1-U/0,6)) x tier KHOP code (tier = 1).
- Bo DCA voi WEIGHTS=1,0,0,0: leg = equity x F_BASE x SCALE x throttle => phai chon lai F_BASE x SCALE (giu 2,25 % hay dung 9 %
  "suat ca cum" cu, hay 4,5 % tran). Phan von truoc day "de danh cho 3 leg DCA" (3/4 suat cum) thanh von nhan roi.
- QUOTA: top-K selector (K=16, `SELECTOR_RANK_TOPK`) moi tick 15' + 1 vi the / coin + U_MAX + CONC_PERCOIN 15 %. SL chat => cum dong
  nhanh => coin duoc phep vao lai som hon, U thap hon, skipFull (neu bat) hiem kich hon. FAMILY2: gross TB/MAX 3 % / 33 % => so khong bao gio day.
- Cau hoi mo cho MASTER: (1) size theo RUI RO (risk/lenh = size x SL co dinh, vd 0,5 % equity) hay giu size theo von? Voi SL thay doi
  (d hoac luoi SL) size co dinh lam rui ro/lenh doi theo SL - so sanh giua cac o luoi bi lan. (2) Throttle 1-U/0,6 vo nghia khi U luon
  thap - giu hay bo? (3) Gate rolling GDV2 (`LIVE/SIM_GATE_ROLLING_*`) nap r tu moi ung vien; doi kieu thoat lam doi U => doi skipFull =>
  doi phan phoi buffer => doi so lenh: can tach "hieu ung thoat" khoi "hieu ung so lenh" trong prereg. (4) Leg BIG_DOWN (bo gate p15) co giu
  trong kieu bracket khong.

## 3. Duong chay sim tren Kaggle fleet
- API: `tools/kaggle_sim.py` - `submit(tag, profile, overrides, bundle_ds=, jar_ds=, extra_env=, ...)` (`:417-451`), `wait` (`:465`, timeout
  13h), `fetch` (`:491`), `free_slots()` (`:90`). Runbook `docs/runbooks/KAGGLE_SIM.md`.
- Du lieu: bundle `chuyendinh/sim-c2b-bundle` (jar + config + profiles + market/pred/funding bin + bins S1) hoac bundle 48 thang qua
  `bundle_ds`; ticker qua TICKER_DS (TICKER_SOURCE=file). Jar doi code => dataset jar rieng `jar_ds` (log `JAR_SHA256`). Jar KHONG chua key:
  tai lieu goi "jar STUB" (vd FAMILY2 jar `sim-jar-tpsl` d45f2f86; r1-a3 jar `cc0f9d11`; HO5 prereg: "Kaggle chi dung jar STUB").
  Luu y: jar cc0f9d11 (r1-a3) CO cac key TP/PRE_ARM_SL khong - CHUA XAC MINH (kiem bang 1 run smoke: log `TAKEPROFIT` / `PREARM_SL`).
- Thoi gian do that: r1-a3 (r4_kg0_k16_f015_g155, 2021-07-01 -> 2025-12-30, 3 622 lenh) `secs=2381` (~40 phut/kernel) + ~1,5 phut
  queue/mount; 8 seed. 5 slot CPU dung chung CA account; 12h hard kill; kernel BAT BUOC internet (symbol mapper doc Aerospike Oracle,
  guard N >= 800); `System.exit` bat buoc; Kaggle ~1,29x cham hon Oracle; chi phi 0 (CPU).
  Uoc: 1 cau hinh x 8 seed = 8 kernel ~ 2 dot ~ 1,5 h; luoi 30 cau hinh x 1 seed ~ 6 dot ~ 4,5 h; x 8 seed ~ 36 h.
- Luat (trich): AGENT_RUNBOOK ?0: DEV = 2022-01-01..2025-12-31; prereg + commit TRUOC khi chay; equity khong phai tieu chi (RATE + CI
  block-72h); so sanh CUNG ha tang (Kaggle vs Kaggle); **Sim MOI = Kaggle, Oracle KHONG chay sim** (shadow live); khong push.
  ce-buttons: cam SSH inline quote phuc tap - dung `ce.cmd <nut>` / script; dispatch job dai la hanh dong CUOI turn; CLAUDE.md:
  "cam bash driver ad-hoc khi nut/pipeline co san". KAGGLE_RULES: dem slot truoc khi push, dung khi FREE = 0, test 1 kernel truoc khi
  push fleet (?6), jar rebuild khi HEAD doi (?5). rules/backtest: commit truoc khi chay, khong chay working-tree ban.
  Luat "cam agent mvn package": KHONG tim thay trong rules/* da doc (build-env chi mo ta mvn); chi co trong brief cua MASTER.
- Cong bat buoc cho moi lan doi code: key OFF => printDone md5 trung moc (vd KEEPLEG0 `99e42b75`), nhu FAMILY2 muc 2.

## 4. Phuong an re: mo phong lai phan thoat bang Python tu ledger
- `~/claude_master/w3/p15_stab/s2/k/c0s42/storage/printDone.csv` (3 462 dong). Cot: sym, side, entry, tp(= gia thoat), profit(%), status,
  start, time_start_format, end, level, maxmin15m, lastentry, volume, quantity, margin, pnl, time_order(gio giu), funding, dow, up, dow15m,
  pred15m, risk4h, symbolPred. MOT DONG / LEG (leg DCA la dong rieng, level DCA_LEVEL1); khong co id cum, khong co dinh/MAE.
- Du thong tin de replay thoat: CO (sym, gio vao phut, gia vao, level de bo leg DCA). Can them nen 1m OHLC: bundle ticker Kaggle co
  OHLC; tren Oracle `~/vz_e1/raw/kline1m-*` CHI co close (LEVZ ghi), `/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin` co high/low nhung 1h.
  Dung close-only se danh gia SL lac quan (sim dung LOW).
- Sai lech so voi sim that (khong co phan hoi danh muc): (1) tap lenh vao co dinh = tap cua cau hinh goc (co DCA, so day hon) - thieu cac
  lan vao lai cung coin sau khi TP/SL dong som (luat "dang giu" o goc chan); (2) size/compound/U/throttle khong tinh lai; (3) gate rolling +
  skipFull doi theo U => doi tap ung vien; (4) funding phai tinh lai theo thoi gian giu moi.
- Cach do sai lech MIEN PHI: FAMILY2 da co printDone Java cho N1..N4 (`~/kaggle_sim/out/tp-n*`, tag trong result json) va nen N0 `cd-sel15`:
  replay N1..N3 bang Python tren ledger N0 roi so tung lenh chung (ly do/gia/gio thoat) + so lenh + PnL/lenh voi ban Java. Them 1 cau hinh
  SL rong (moi) chay ca hai cach de do o vung quan tam.

## 5. Bang phuong an

| phuong an | cong DEV | cong chay | do tin cay | rui ro |
|---|---|---|---|---|
| P1 Java sim Kaggle, CHI CAU HINH (a,b,c,e): luoi SL rong x R x H | prereg + smoke/parity 1 kernel: ~0,5 ngay | ~40 phut/kernel; 30 cau hinh x 1 seed ~4,5 h; x8 seed ~1,5 ngay | CAO (cung engine baseline; quan he voi live: lech D1/D2 o SL chat) | bay sizing (muc 0.2); da tung FAIL o SL nho; nhieu cau hinh => phai inflate CI |
| P2 Python replay ledger (screen) | ~1-1,5 ngay (reader ledger + OHLC 1m + engine + calib FAMILY2) | phut | TRUNG BINH (khong phan hoi danh muc; ung vien co dinh) | ket luan sai neu dung lam bang chung; chi de cat luoi |
| P3 SL/TP theo bien dong (d) trong Java | ~1-2 ngay (code ~70-100 dong + test + parity + jar STUB + dataset) | nhu P1 | CAO sau parity | sua code sim => phai giu "mot bo nao", Javadoc, byte-identical OFF |
| P4 Lam ca live | ngoai pham vi | - | - | c3live chua co SL truoc arm / TP; MARK vs LAST |

## 6. De xuat (khong chay thu)
1. Viet prereg MO RONG FAMILY2 (khong lap vung SL <= 1,5 %): luoi SL {5, 8, 12, 15, 20 %} x R {0,5; 1; 1,5; 2; 3} x H {72, 168 h} = 50 o,
   DCA tat dung cach (WEIGHTS=1,0,0,0 + WFO_DISABLE_DCA=1), chot TRUOC quy tac size (de xuat: size theo rui ro co dinh moi lenh) va do
   rieng so lenh / skipFull.
2. Chay P2 truoc de cat luoi (calib bang FAMILY2 N1..N3 - neu sai lech PnL/lenh > nguong chot truoc thi bo P2), roi P1 tren <= 10 o
   con lai x 8 seed tren Kaggle, so voi moc Kaggle cung jar.
3. (d) chi lam sau khi P1 cho thay co o SL rong duong; cong thuc vol chot truoc (vd vol 168h nhu T1 SHORT).
4. Smoke 1 kernel xac nhan jar dang dung co key TP/PRE_ARM_SL (log TAKEPROFIT/PREARM_SL) truoc khi push fleet.
