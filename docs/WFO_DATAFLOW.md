# WFO DATAFLOW — Luong du lieu WFO da lam min (chot 2026-07-08)

Tong hop end-to-end cho WFO sau khi lam lai data tu dau (survivorship-correct) + xoa sach pred cu
+ chuyen funding sang doc file bin (bo Aerospike luc chay). NGUON THAM CHIEU de noi tiep session moi.

## 0. NGUYEN TAC
- Chuoi BAT BUOC: ticker goc -> market object -> export feature -> TRAIN -> gen PRED -> WFO.
- WFO chay bang FILE BIN offline (WFO_DATA_DIR), KHONG scanAll Aerospike luc chay.
- Verdict PASS/FAIL do Uni quyet. Claude chay ra so, KHONG tu ket luan.
- Java la source of truth; model mang provenance code+data.

## 1. DATA CORE (Aerospike ns=test tren Oracle 127.0.0.1:3222) — GIU
- kline_1m_opt 2,855,553 (ticker sach: ghost USDCUSDT + duoi-don 10 coin delist da xoa)
- market_data_object 2,854,623 (regen tu ticker sach; key yyyyMMdd-HHmm GMT+7; bin data+time)
- funding_data 741 (crawl fapi HistoricalFundingCrawlerLocal; coin delist co funding)
- open_interest + oi_ls_* + oi_taker_vol (5 set ~17-18k moi; chunk-thang SYMBOL_yyyyMM)
- kline_15m_opt 189k / kline_15m_btceth 126 / kline_4h_btceth 126 (Aggregate15m4hLocal)
- symbol_lifecycle 698 (72 DEAD; FTT/RAY/SC DEAD dung delist)
- symbol_mapper 1 (global_id_map, 781 symbol, BTC=1 ETH=2, gom delist)
- wfo_jobs 17 (state WFO framework, KHONG phai pred, KHONG xoa)
- OI file: /home/ubuntu/java/simulator/features_oi_percoin_v1/oi_percoin_20210101_to_20260624.bin.gz
  (3.15GB, 138M rec, 30B: >i8 ts + >i2 symId + >f4[5])

## 2. HAI NHANH PRED (train + pred da XONG)
### 2a. GATE (Java WFOGateRunner, chay Oracle)
- Train: ml/gate/train_gate_fold.py (MOI NHAT mtime+git 2026-06-23; Uni chot "cai moi nhat theo time thay doi").
  XGBRegressor return, 33 feature V3FULL khoa cung, label_oldbasket -> ONNX Model_Regressor_Return15M.onnx per-fold.
- WFOGateRunner: replay 1 lan -> WFO loop 14 fold expanding (train per-fold) -> predict OOS leak-free -> GHI FILE.
  Venv hardcode /home/ubuntu/envs/xgb-env/bin/python.
- Output: /home/ubuntu/claudedata/wfo_gate_pred.csv (1,795,680 dong; timestamp,predReturn15M,predRisk4H;
  2022-12-31 -> 2026-05-31; 0 NaN). 14 model /home/ubuntu/claudedata/wfo_models/. Validate PASS.
### 2b. SELECTOR (Kaggle, Uni chot train+pred tren Kaggle)
- Nut co chai THAT: merge OI 138M >23GB RAM -> OOM Oracle -> Kaggle 30GB (KHONG phai train cham).
- Dataset Kaggle chuyendinh/funding-selector-wfo-data (ready). LUU Y: Kaggle giai nen .gz -> .bin/.csv.
- Train kernel chuyendinh/selector-wfo-train: PASS manh — LIFT med 4h=2.875/12h=1.966/24h=1.612/72h=1.296;
  100% fold LIFT>1 + IC>0; 13/14 fold. 4 model .ubj -> /home/ubuntu/selector_kaggle_out/.
- Pred kernel chuyendinh/selector-wfo-pred (gen_funding_wf_predictions.py, LEAK-FREE walk-forward, purge 72h):
  16 file predict_wf_*.bin (26B >q h 4f); 3,486,305 rec; 2021-01 -> 2025-12; 0 NaN. -> /home/ubuntu/selector_pred_out/.
- KHONG master-worker cho pred: merge OI chi 1 lan/kernel; chia worker se nhan 5 lan merge (loi bat cap hai).

## 3. XOA PRED CU (Uni chot: pred cu la rac) — 2026-07-08
Da TRUNCATE 4 set (/tmp/TruncateSets.java, nhan ten set qua arg): ai_pred_market_full_basket_v2,
funding_pred_1m_v5, funding_selector_pred_1m_v3wf, ai_pred_market_gate_wfo_smoke2. Con core + 2 pred moi:
- ai_pred_market_gate_wfo (1,795,680) — gate nap tu csv (LoadWfoGatePredTool)
- funding_selector_pred_1m_v2 (323,142 chunk-ngay) — nap ExportSelectorPred1mToAerospike (per-symbol-ngay;
  KHONG dung cho WFO — WFO doc funding tu FILE, xem muc 4).

## 4. HOI TU -> funding.bin (BO Aerospike, Uni chot 2026-07-08)
Van de: WfoDataset.export cu doc funding qua getAllFundingPredictionsPrimitiveFromAerospike() hardcode set cu
funding_pred_1m_v5 (da xoa -> funding=0). Selector pred moi la P(win) 4 horizon per (symbol,ts), khac format.
FIX (da commit): WfoDataset.export them buildFundingFromWfFiles(predDir, horizonIdx):
- Doc THANG 16 file predict_wf_*.bin (bo Aerospike), gom theo ts -> TreeMap<ts, long[]>.
- Moi long = (symId<<32)|floatBits(score), score = 1 - P(win) (DAO DAU khop decodeSelectorMapToPrimitiveArray:
  engine chon score THAP = P(win) CAO).
- Env: WFO_FUNDING_PRED_DIR, WFO_SEL_HORIZON_IDX (0=4h,1=12h,2=24h,3=72h; mac dinh 1=12h). Rong -> fallback Aerospike.
Lenh export:
  WFO_FUNDING_PRED_DIR=/home/ubuntu/selector_pred_out WFO_SEL_HORIZON_IDX=1 WFO_SET_PRED=ai_pred_market_gate_wfo \
  java -Xmx12g -cp binance-futures-backfill.jar com.binance.chuyennd.ai_ml.wfo.framework.ExportWfoDataset /home/ubuntu/claudedata/wfo_dataset

## 5. WFO DATASET (file bin) — /home/ubuntu/claudedata/wfo_dataset/
- market.bin 55MB / 2,774,140 : [count][ts:long][3 float]
- pred.bin 28MB / 1,795,680 (gate) : [count][ts:long][predReturn15M][predRisk4H]
- funding.bin 30MB / 175,226 moc, 3.48M rec (selector 12h) : [count][ts:long][len:int][len x long]
- manifest.txt : md5 3 file + provenance; load() verify md5 fail-fast (chong drift L3)

## 6. WFO RUN (framework file bin — dang chay)
- Coordinator: WfoCoordinator <init|status|report|reset> strategy_window (job -> wfo_jobs set).
- Worker: WfoWorker strategy_window, env WFO_DATA_DIR=/home/ubuntu/claudedata/wfo_dataset WFO_SMART_CACHE=1.
  Load dataset file bin 1 lan (md5 verified), lease tung job, chay StrategyWfoTask.runJob.
- 17 cua so: train 12m + OOS 3m, truot 3m, 20210101..20260601 (OOS 202201->202603). N_samples=30/cua so.
- Nguong pre-register (/home/ubuntu/claudedata/validate_criteria.md):
  WFE median >= 0.5, %OOS-duong >= 70%, maxDD-OOS xau nhat <= 50% (ca 3 — verdict Uni quyet).
- Report: WfoCoordinator report strategy_window -> docs/reports/wfo_strategy_window.md + in VERDICT.
- TRANG THAI ket thuc session 2026-07-08: worker DANG CHAY (job strat-w00), 0/17 cua so xong.
- Probe khac (EntrySource/GateAb/SelectorGateCorr/TailLeak/Mom15Sweep) = chan doan bo tro; CHUA chay phien nay.

## 7. VIEC KE TIEP (session moi)
1. Cho WfoWorker xong 17 cua so: grep -c "DONE job" /home/ubuntu/claudedata/wfo_worker.log.
   Worker tat ma chua du 17 -> chay lai WfoWorker (tu lease job PENDING/stale con lai).
2. WfoCoordinator report strategy_window -> doc WFE median / %OOS-duong / maxDD-OOS -> doi chieu nguong.
   TRINH so cho Uni, KHONG tu ket luan verdict.
3. (Tuy chon) A/B horizon: export lai funding.bin voi WFO_SEL_HORIZON_IDX khac (0/2/3) -> WFO so 4 horizon.
4. (Tuy chon) chay cac probe chan doan.
5. Can nhac xoa han code doc pred cu Aerospike (getAllFundingPredictionsPrimitiveFromAerospike + set v5)
   neu Uni muon don triet de — kiem loadAuto + SimulatorMarketLevelTicker1MStopLoss.initData (A/B) con goi khong.

## 8. FILE/TOOL CHINH (branch module)
- WfoDataset.java (buildFundingFromWfFiles), WFOGateRunner.java, ml/gate/train_gate_fold.py
- LoadWfoGatePredTool.java, research/ExportSelectorPred1mToAerospike.java
- ai_ml/wfo/framework: ExportWfoDataset, WfoCoordinator, WfoWorker, tasks/StrategyWfoTask
- ml/funding_selector/kaggle_kernel_train_selector.py; ml/training/gen_funding_wf_predictions.py
- /tmp/TruncateSets.java (xoa set rac); /tmp/ListSets.java (liet ke set)
- Git trailer: Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>

## 9. GHOST USDC — REVIEW LAI (do truc tiep Oracle 2026-07-08, khong doan)
Boi canh: report 133 (chay 2026-07-07) canh bao 38 ghost *USDCUSDT co ticker that [2026-01-03->02-27],
market lat 2 thang duoi bi meo. DO LAI tren data HIEN TAI (sau khi CleanTickerGhostAndTail da chay):

| Noi | 133 (07-07) | Do hien tai (07-08) | Danh gia |
|---|---|---|---|
| Ghost *USDCUSDT trong TICKER goc | co, [2026-01-03->02-27] | 0 (scan FULL 2,855,553 rec; chi con 1 symbol USDCUSDT 244 rec thua) | SACH |
| Basket market lat 2026-01/02 | "meo do 38 ban sao" | 587 coin, 1 USDC (moc 02-27), 0 USDC (01-15, 02-01) | KHONG phong |
| Market feature 2026-01/02 | meo nhe | rateDown/Up/Down15 binh thuong, cung thang cac thang khac | KHONG lech |
| Ghost trong MAPPER (symbol_mapper) | 38 | 38 (con) | VO HAI — xem duoi |

KET LUAN: report 133 KHONG sai, nhung no chay TRUOC khi CleanTickerGhostAndTail xoa ghost khoi ticker.
Ticker goc hien tai da SACH 38 ghost USDC-margin -> market_data_object regen tu ticker sach cung sach.
- 38 ghost con trong MAPPER = symId lich su (mapper chi tich luy, khong xoa). VO HAI vi: (a) mapper khong
  xoa duoc nhung 38 symId nay KHONG co ticker -> khong vao basket market; (b) market la aggregate theo phut
  tu ticker sach; (c) symbol khong ticker -> khong co label/feature -> khong vao train/pred.
- Con 1 symbol USDCUSDT (244 rec thua, range 2023-04->2026-02-27) trong ticker: tac dong cross-sectional
  len basket 587 coin khong dang ke; neu muon tuyet doi sach chi can them 1 filter USDCUSDT$.

CO CHE BUG (van con trong code, tiem an): DataManagerAerospikeFloatSim.java:940 (readDataFromAerospike1M...)
normalize `endsWith("USDT") ? sym : sym+"USDT"` -> neu ticker goc co key *USDC se noi thanh *USDCUSDT ghost.
Ticker gio sach nen KHONG kich hoat, nhung neu nap lai ticker co USDC-margin thi ghost tai tao (dung nhu
133 canh bao "dumping ha nguon se tai phat").

VIEC NEN LAM (re, va tai nguon — KHONG scrub):
1. Loc `USDCUSDT$` khi export ff feature (1 filter) — chan ca USDCUSDT that lan moi ghost tuong lai.
2. Va bug normalize dong 940 de ghost khong tai tao moi lan doc (du ticker gio sach, bug van tiem an).
CHUA LAM 2 viec tren (cho Uni chot). WFO dang chay tren market/ticker da sach ghost (an toan).

Tools do (Oracle /tmp, read-only): CheckGhost.java (mapper), ScanGhostFull.java (scan full ticker),
CheckUsdcReal.java (range USDCUSDT), CountBasket.java (dem coin+USDC theo moc), CheckMarket.java (market lat).
