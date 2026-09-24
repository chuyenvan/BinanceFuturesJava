# BAN DO FIELD CAU HINH — sinh tu ma nguon (tools/gen_config_field_map.py)

**KHONG go tay.** Chay lai sau moi lan doi code.

## ⚠️ Ban do nay chi de DIEU HUONG, KHONG de quyet dinh xoa

Ban dau tien cua script nay co false positive: xep `DCA_GRID_WEIGHTS` va
`TS_PNOPUMP_WEAK_THR` la DEAD — ca hai la LOI cua C2b. Ly do: field dung ben trong
`Configs.java` viet TRAN (khong co tien to `Configs.`), va `AIRejectFilter` nam duoi
`ai_ml/` nhung la ENGINE. Da sua ca hai. Nhung bai hoc giu nguyen:

> Muon xoa mot field: phai chung minh bang **byte-identity** (doi gia tri qua profile
> roi so `printDone.csv`) hoac doc tay tung cho doc. Khong xoa chi vi ban do noi DEAD.

Nhan cung KHONG noi field co REACHABLE duoi mot cau hinh cu the: mot field
`ENGINE_SIM` van co the TRO voi C2b vi bi co khac tat (vd `MAX_CONCURRENT_ORDERS`
chi song khi `BREAKER_MODE != OFF`). Xem `docs/design/C2B_SPEC.md` muc 8.

| nhan | nghia |
|---|---|
| `ENGINE_SIM` | doc trong engine backtest (`research/**`) |
| `ENGINE_LIVE` | doc trong `trading/**` — san giao dich that |
| `SIM+LIVE` | ca hai engine |
| `ENGINE_SHARED` | doc trong file engine dung chung (`TradeUtils`, `AIRejectFilter`, `DcaUtils`...) |
| `SELF_ONLY` | chi dung ben trong `Configs.java` (getter, ham dan xuat) |
| `TOOL_ONLY` / `TOOL+SELF` | chi doc trong `ai_ml/**` tool (HPO/WFO/validation/probe) — khong anh huong engine |
| `DEAD` | khong tim thay cho doc nao |

Tong 78 field. Phan bo: {'OTHER': 15, 'ENGINE_SIM': 23, 'SIM+LIVE': 7, 'ENGINE_SHARED': 15, 'SELF_ONLY': 10, 'TOOL+SELF': 1, 'ENGINE_LIVE': 4, 'TOOL_ONLY': 3}

## SELF_ONLY (10)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `DCA_GRID_L1` | — | 3 |
| `DCA_GRID_LEGS` | — | 2 |
| `DCA_GRID_LEVELS` | — | 4 |
| `DCA_GRID_STEP` | — | 2 |
| `DCA_GRID_WEIGHTS` | — | 3 |
| `DCA_GRID_W_RATIO` | — | 3 |
| `TS_PNOPUMP_WEAK_THR` | — | 4 |
| `TS_PNOPUMP_WEAK_THR_OVR` | — | 2 |
| `configFile` | — | 1 |
| `properties` | — | 20 |

## TOOL_ONLY (3)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `MS_DOWN_SMALL_AVG_OR_15M` | `ai_ml/hpo/kaggle/BenchmarkSpeedTest.java`, `ai_ml/hpo/kaggle/BackTestEngineMarketThresholds.java`, `ai_ml/hpo/master/RunWorkerKaggle.java` | 0 |
| `MS_UP_BIG_THRES` | `ai_ml/hpo/kaggle/BenchmarkSpeedTest.java`, `ai_ml/hpo/kaggle/BackTestEngineMarketThresholds.java`, `ai_ml/hpo/master/RunWorkerKaggle.java` | 0 |
| `MS_UP_SMALL_THRES` | `ai_ml/hpo/kaggle/BenchmarkSpeedTest.java`, `ai_ml/hpo/kaggle/BackTestEngineMarketThresholds.java` | 0 |

## TOOL+SELF (1)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `DCA_GRID_SCALAR` | `ai_ml/wfo/CpcvBatchRunner.java`, `ai_ml/wfo/framework/tasks/CpcvCellTask.java` | 5 |

## ENGINE_LIVE (4)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `FILE_AI_ENTRY_PREDICTIONS` | `aerospike/DataManagerAerospikeFloatSim.java`, `ai_ml/onnx/entry/MergePredictionFiles.java`, `trading/DetectEntrySignal2TradeNormal.java` | 0 |
| `NUMBER_THREAD_ORDER_MANAGER` | `trading/BinanceOrderTradingManager.java`, `trading/DetectEntrySignal2TradeNormal.java` | 1 |
| `NUMBER_TICKER_CAL_RATE_CHANGE` | `ai_ml/validation/data/SurvivorshipFeatureCheck.java`, `ai_ml/features/export/MarketDataInlineGenerator.java`, `trading/DetectEntrySignal2TradeNormal.java` +1 | 0 |
| `PRICE_REALTIME_MAX_AGE_MS` | `trading/DetectEntrySignal2TradeNormal.java` | 0 |

## ENGINE_SIM (23)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `AEROSPIKE_READ_CLUSTER` | `aerospike/DataManagerAerospikeFloatSim.java`, `ai_ml/validation/GoldenBacktest.java`, `ai_ml/validation/data/AerospikeCoverageMap.java` +4 | 8 |
| `APPLY_FUNDING_FEE` | `ai_ml/wfo/CpcvBatchRunner.java`, `ai_ml/wfo/framework/tasks/TrailingStopSweepProbe.java`, `ai_ml/wfo/framework/tasks/CpcvCellTask.java` +3 | 2 |
| `APPLY_SLIPPAGE` | `ai_ml/hpo/TestFitnessV41.java`, `ai_ml/hpo/HPOFitnessCalculatorV4.java`, `ai_ml/hpo/BacktestIntegrityGuard.java` +6 | 0 |
| `BLOCK_INTRABAR_LOOKAHEAD` | `ai_ml/wfo/framework/tasks/TrailingStopSweepProbe.java`, `ai_ml/hpo/BacktestIntegrityGuard.java`, `ai_ml/validation/ablation/market/RunFundingImpact.java` +6 | 0 |
| `COND_EXIT_HOURS` | `research/SimulatorMarketLevelTicker1MStopLoss.java`, `research/OrderTargetInfoTest.java` | 2 |
| `COND_EXIT_MIN_FAV` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 2 |
| `ENTRY_UNIVERSE_DUMP` | `ai_ml/wfo/framework/tasks/EntryUniverseCountProbe.java`, `research/SimulatorMarketLevelTicker1MStopLoss.java` | 0 |
| `FIX_B1` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 0 |
| `FIX_B3` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 0 |
| `FUNDING_MARK_NOTIONAL` | `research/SimulatorMarketLevelTicker1MStopLoss.java`, `research/OrderTargetInfoTest.java` | 1 |
| `FUNDING_SCALE` | `research/OrderTargetInfoTest.java` | 2 |
| `GATE_COUNT_ONLY` | `ai_ml/wfo/framework/tasks/GatePassCountProbe.java`, `ai_ml/wfo/framework/tasks/EntryUniverseCountProbe.java`, `ai_ml/wfo/framework/tasks/StrategyWfoTask.java` +1 | 3 |
| `LOSER_TIME_STOP_HOURS` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 3 |
| `RATE_FEE` | `ai_ml/hpo/TestFitnessV41.java`, `ai_ml/hpo/HPOFitnessCalculatorV4.java`, `ai_ml/hpo/BacktestIntegrityGuard.java` +7 | 3 |
| `SELECTOR_ONLY_ENTRY` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 1 |
| `SIM_FAIL_FAST_ON_DATA_ERROR` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 0 |
| `SLIPPAGE_RATE` | `ai_ml/hpo/TestFitnessV41.java`, `ai_ml/hpo/HPOFitnessCalculatorV4.java`, `ai_ml/hpo/BacktestIntegrityGuard.java` +6 | 2 |
| `TICKER_SOURCE` | `ai_ml/wfo/framework/tasks/CapacityProbe.java`, `ai_ml/wfo/framework/tasks/SurvivalProbe.java`, `ai_ml/wfo/framework/tasks/EntryUniverseCountProbe.java` +7 | 3 |
| `TIME_RUN` | `aerospike/DataMigrator.java`, `ai_ml/hpo/compile/BackTestEngineCombined.java`, `ai_ml/hpo/compile/RunOptimizationCombined.java` +18 | 1 |
| `TS_CAP_STRONG_RANK` | `research/OrderTargetInfoTest.java` | 3 |
| `USE_SMART_CACHE` | `ai_ml/wfo/CpcvBatchRunner.java`, `ai_ml/wfo/framework/WfoWorker.java`, `ai_ml/wfo/framework/tasks/StrategyWfoTask.java` +2 | 2 |
| `WFO_LOG_ENTRIES` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 1 |
| `WRITE_SIM_STORAGE` | `research/SimulatorMarketLevelTicker1MStopLoss.java` | 2 |

## SIM+LIVE (7)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `AI_DYNAMIC_MAX` | `tradecore/EntryGate.java`, `ai_ml/hpo/general/RunOptimizationDynamicFilter.java`, `ai_ml/hpo/general/BackTestEngineDynamicFilter.java` +7 | 1 |
| `LEVERAGE_ORDER` | `tradecore/selector/ShadowBookC3.java`, `aerospike/validate_data/predictsymbol/CheckLabel6Predictions.java`, `ai_ml/validation/ablation/dca/LunaDcaScenario.java` +13 | 0 |
| `NUMBER_ENTRY_EACH_SIGNAL` | `trading/DetectEntrySignal2TradeNormal.java`, `research/SimulatorMarketLevelTicker1MStopLoss.java` | 0 |
| `PREDICT_SYMBOL_RATE_MAX_THRESHOLD` | `tradecore/EntryGate.java`, `ai_ml/wfo/framework/tasks/EntrySourceProbe.java`, `ai_ml/hpo/compile/BackTestEngineCombined.java` +9 | 1 |
| `RATE_PROFIT_STOP_MARKET` | `tradecore/TradeUtils.java`, `ai_ml/wfo/framework/tasks/TrailingStopSweepProbe.java`, `ai_ml/wfo/framework/tasks/MaeDistributionProbe.java` +2 | 3 |
| `SELECTOR_RANK_TOPK` | `ai_ml/wfo/framework/tasks/EntryUniverseCountProbe.java`, `trading/DetectEntrySignal2TradeNormal.java`, `research/SimulatorMarketLevelTicker1MStopLoss.java` | 2 |
| `number_order_budget` | `ai_ml/validation/ablation/dca/LunaDcaScenario.java`, `trading/BudgetManager.java`, `research/BudgetManagerSimple.java` | 2 |

## ENGINE_SHARED (15)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `DCA_GRID_ENABLED` | `tradecore/DcaProcessor.java`, `ai_ml/wfo/CpcvBatchRunner.java`, `ai_ml/wfo/framework/tasks/CpcvCellTask.java` +1 | 0 |
| `DCA_GRID_SCALE` | `tradecore/DcaUtils.java` | 2 |
| `DCA_LOSS_BIG_DOWN` | `tradecore/DcaUtils.java`, `ai_ml/hpo/master/RunWorkerKaggle.java` | 0 |
| `DCA_TIME_BIG_DOWN` | `tradecore/DcaUtils.java`, `ai_ml/hpo/master/RunWorkerKaggle.java` | 0 |
| `FIX_B2` | `tradecore/DcaUtils.java` | 0 |
| `F_BASE` | `tradecore/TradeUtils.java` | 1 |
| `MIN_MOMENTUM_15M` | `tradecore/EntryGate.java`, `ai_ml/wfo/framework/tasks/Mom15SweepProbe.java`, `ai_ml/wfo/framework/tasks/GatePassCountProbe.java` +6 | 2 |
| `MS_DOWN_BIG_AVG` | `tradecore/MarketBigChangeDetector.java`, `ai_ml/wfo/framework/tasks/W13Diagnose.java`, `ai_ml/hpo/kaggle/BenchmarkSpeedTest.java` +2 | 1 |
| `TIER_FLAT` | `tradecore/CoinRankManager.java` | 1 |
| `TS_GIVEBACK_RATIO` | `tradecore/TradeUtils.java` | 4 |
| `TS_MAX_GAP` | `tradecore/TradeUtils.java`, `ai_ml/wfo/framework/tasks/TrailingStopSweepProbe.java` | 2 |
| `TS_MAX_GAP_WEAK` | `tradecore/TradeUtils.java`, `ai_ml/wfo/framework/tasks/TrailingStopSweepProbe.java`, `trading/BinanceOrderTradingManager.java` | 2 |
| `U_MAX` | `tradecore/TradeUtils.java` | 1 |
| `WFO_DISABLE_DCA` | `tradecore/DcaProcessor.java`, `ai_ml/wfo/framework/tasks/MaeDistributionProbe.java` | 1 |
| `WFO_STATIC_RANK` | `tradecore/CoinRankManager.java`, `ai_ml/wfo/framework/ExportCoinTierStatic.java`, `ai_ml/wfo/framework/WfoWorker.java` +2 | 1 |

## OTHER (15)

| field | doc o dau | dung tran trong Configs |
|---|---|---|
| `AEROSPIKE_HOST_242` | `tradecore/selector/S1RankerLive.java`, `aerospike/DataMigrator.java`, `aerospike/DataManagerAerospikeFloatSim.java` +1 | 0 |
| `AEROSPIKE_HOST_ORACLE` | `aerospike/DataManagerAerospikeFloatSim.java` | 0 |
| `AEROSPIKE_NAMESPACE` | `aerospike/validate_data/predictmarket/CheckGapPredictMarket.java`, `aerospike/validate_data/marketobject/MarketObjectGapRepairTool.java`, `aerospike/validate_data/marketobject/CheckGapMarketObject.java` +52 | 4 |
| `AEROSPIKE_NAMESPACE_242` | `tradecore/selector/S1RankerLive.java`, `aerospike/tools/DiagnoseTickerMismatch242VsOracle.java`, `aerospike/tools/CopyAuxSets242To226.java` +2 | 1 |
| `AEROSPIKE_PORT_242` | `tradecore/selector/S1RankerLive.java`, `aerospike/DataMigrator.java`, `aerospike/DataManagerAerospikeFloatSim.java` +1 | 0 |
| `AEROSPIKE_PORT_ORACLE` | `aerospike/DataManagerAerospikeFloatSim.java` | 0 |
| `AI_DYNAMIC_MIN` | `tradecore/EntryGate.java`, `ai_ml/hpo/general/RunOptimizationDynamicFilter.java`, `ai_ml/hpo/general/BackTestEngineDynamicFilter.java` +1 | 2 |
| `AI_DYNAMIC_MULTIPLIER` | `tradecore/EntryGate.java`, `ai_ml/hpo/general/RunOptimizationDynamicFilter.java`, `ai_ml/hpo/general/BackTestEngineDynamicFilter.java` +1 | 2 |
| `PRE_ARM_SL` | `tradecore/PreArmSlUtils.java` | 2 |
| `TICKLOG` | `research/TickDecisionLog.java` | 1 |
| `TICKLOG_DIR` | `research/TickDecisionLog.java` | 0 |
| `TICKLOG_POOL` | `research/TickDecisionLog.java` | 0 |
| `TICKLOG_POS_EVERY_MIN` | `research/TickDecisionLog.java` | 1 |
| `TICKLOG_TAG` | `research/TickDecisionLog.java` | 0 |
| `WFO_FUNDING_PRED_DIR` | `tradecore/BinsProvenance.java` | 0 |
