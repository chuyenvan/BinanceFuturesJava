# architecture — Bức tranh lớn codebase (tham chiếu khi định vị code)

> Đọc cùng [CORE](CORE.md) + [rules/code](rules/code.md). App dưới `com.binance.chuyennd.*`.
> `com.binance.client.*` = Binance REST/websocket client vendored — coi như thư viện, sửa chủ yếu ở `chuyennd`.

## Luồng dữ liệu
Binance → ingestors → Aerospike/Redis → feature extraction → ONNX inference → signal/trade decisions,
kèm vòng offline backtest + HPO tune chính các tham số `Configs` mà live dùng.

## Bản đồ package
- **Storage** — `aerospike/DataManagerAerospikeFloatSim` = kho market-data chính (binary float-packed). `utils/Storage`/`StorageProto`/`StorageSnappy` = kho file (Snappy/protobuf). `redis/` (Jedis cluster) = order queue live + messaging. Proto ở `src/main/proto/`.
- **AI/ML** (`ai_ml/`) — ONNX qua `onnxruntime` (`ai_ml/onnx/`: entry-signal + funding classifier; model ở `../storage/ai_ml*/`). `ai_ml/features/` trích feature. `ExportFeaturesForPythonTool` + `python/` cầu nối train Python. `ai_ml/data/` cache backtest (`HPOSmartCache`, `CompactDayData`).
- **HPO** (`ai_ml/hpo/`) — Jenetics GA evolve `Configs`. Master/worker: `hpo/master/RunHpoMaster_Distributed` đẩy population vào queue set (`hpo_queue_<CONFIG_VERSION>`), đọc kết quả từ cache set (`hpo_results_<CONFIG_VERSION>`); `RunWorkerKaggle` tiêu thụ. `ai_ml/wfo/` walk-forward.
- **Trade core** (`tradecore/`) — logic giao dịch THUẦN dùng chung live+backtest: `MarketBigChangeDetector`, `DcaProcessor`/`DcaUtils`, `CoinRankManager`, `TradeUtils`, `Configs`.
- **Trading** (`trading/`) — execution live: `DetectEntrySignal2TradeNormal`, `BinanceOrderTradingManager`, `BudgetManager`, `SymbolOrderLockingManager`, `trading/monitor/`.
- **Data validation** (`aerospike/validate_data/`, `ai_ml/validation/`, `websocket/checkdata/`) — tool đứng riêng phát hiện gap, sửa data, so production-vs-backtest.

## 2 process live (sống lâu, mỗi cái một main)
- `websocket/BinanceDataIngestor.main()` — stream funding+ticker vào Aerospike; có watchdog tự restart.
- `trading/BinanceOrderTradingManager.main()` — wire `DetectEntrySignal2TradeNormal().start()` + order manager; tự re-exec qua `Utils.reset(...)`, ghi PID qua `Utils.writePid2File()` (`APP_PID_DIR`/`APP_MAIN_CLASS` từ `daemon.sh` ngoài repo).
- ⛔ Deploy/restart 2 process này = NGƯỜI tay (xem [CORE](CORE.md)).
