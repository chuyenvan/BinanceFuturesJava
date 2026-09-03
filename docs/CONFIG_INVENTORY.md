# BAN KIEM KE CAU HINH — sinh tu ma nguon boi tools/gen_config_inventory.sh

Sinh luc: 2026-09-03 03:08 UTC · commit `cb073af`

> KHONG go tay file nay. Chay lai script sau moi lan doi cau hinh.

## 1. Key ma code THUC SU doc tu config.properties

| key | doc o dau |
|---|---|
| `AEROSPIKE_HOST` | chuyennd/tradecore/Configs.java:659:    public static final String AEROSPIKE_HOST_242 = Co |
| `AEROSPIKE_HOST_226` | chuyennd/tradecore/Configs.java:662:    // Tên hằng đổi 226→ORACLE (2026-08-04, re |
| `AEROSPIKE_NAMESPACE` | chuyennd/tradecore/Configs.java:667:    public static final String AEROSPIKE_NAMESPACE = C |
| `AEROSPIKE_NAMESPACE_242` | chuyennd/tradecore/Configs.java:678:    public static final String AEROSPIKE_NAMESPACE_242 |
| `AEROSPIKE_PORT` | chuyennd/tradecore/Configs.java:660:    public static final int AEROSPIKE_PORT_242 = Confi |
| `AEROSPIKE_PORT_226` | chuyennd/tradecore/Configs.java:665:    public static final int AEROSPIKE_PORT_ORACLE = Co |
| `AEROSPIKE_READ_CLUSTER` | chuyennd/tradecore/Configs.java:89:    public static String AEROSPIKE_READ_CLUSTER = prope |
| `CAPITAL_START` | chuyennd/tradecore/Configs.java:685:        String v = Cfg.get("CAPITAL_START"); |
| `DIED_SYMBOLS` | client/constant/Constants.java:59:        String symbols = Configs.getString("DIED_SYMBOLS |
| `DISABLE_PREDICT_SYMBOL` | chuyennd/tradecore/Configs.java:521:            Cfg.get("DISABLE_PREDICT_SYMBOL") != null  |
| `FILE_AI_PREDICTIONS` | chuyennd/tradecore/Configs.java:657:    public static final String FILE_AI_ENTRY_PREDICTIO |
| `HARD_STOP_LOSS_RATE` | chuyennd/tradecore/Configs.java:258:    public static float HARD_STOP_LOSS_RATE = Cfg.get( |
| `NUMBER_ORDER_BUDGET` | chuyennd/tradecore/Configs.java:170:    public static Integer number_order_budget = Cfg.ge |
| `NUMBER_THREAD_ORDER_MANAGER` | chuyennd/tradecore/Configs.java:128:    public static final Integer NUMBER_THREAD_ORDER_MA |
| `SPECIAL_SYMBOLS` | client/constant/Constants.java:66:        symbols = Configs.getString("SPECIAL_SYMBOLS"); |
| `TICKER_SOURCE` | chuyennd/tradecore/Configs.java:90:    public static String TICKER_SOURCE = properties.get |
| `TIME_RUN` | chuyennd/tradecore/Configs.java:101:    public static String TIME_RUN = Configs.getString( |
| `TIME_STOP_HOURS` | chuyennd/tradecore/Configs.java:269:    public static int TIME_STOP_HOURS = Cfg.get("TIME_ |
| `TS_GIVEBACK_RATIO` | chuyennd/tradecore/Configs.java:282:    public static float TS_GIVEBACK_RATIO = Cfg.get("T |
| `TS_MIN_GAP` | chuyennd/tradecore/Configs.java:481:    public static float TS_MIN_GAP = Cfg.get("TS_MIN_G |
| `USE_SMART_CACHE` | chuyennd/tradecore/Configs.java:96:    public static boolean USE_SMART_CACHE = properties. |
| `WFO_STATIC_RANK` | chuyennd/tradecore/Configs.java:100:    public static boolean WFO_STATIC_RANK = properties |
| `WRITE_SIM_STORAGE` | chuyennd/tradecore/Configs.java:93:    public static boolean WRITE_SIM_STORAGE = propertie |

## 2. `config.properties` — doi chieu

| key | gia tri | trang thai |
|---|---|---|
| `AEROSPIKE_HOST` | 103.157.218.242 | active |
| `AEROSPIKE_HOST_226` | 103.157.218.226 | active |
| `AEROSPIKE_NAMESPACE` | ticker | active |
| `AEROSPIKE_NAMESPACE_242` | ticker | active |
| `AEROSPIKE_PORT` | 3222 | active |
| `AEROSPIKE_PORT_226` | 3222 | active |
| `AEROSPIKE_READ_CLUSTER` | 226 | active |
| `CAPITAL_START` | 35000 | active |
| `DIED_SYMBOLS` | BTCDOM,USDC | active |
| `FILE_AI_PREDICTIONS` | ../storage/ai_ml/ai_predictions.data_v3_FULL | active |
| `NUMBER_THREAD_ORDER_MANAGER` | 2 | active |
| `SPECIAL_SYMBOLS` | BNB,ETH,XRP,ADA | active |
| `TICKER_SOURCE` | aerospike | active |
| `TIME_RUN` | 20210101 | active |

Key code doc nhung file nay KHONG khai bao (chay bang default hardcode):

- `DISABLE_PREDICT_SYMBOL`
- `HARD_STOP_LOSS_RATE`
- `NUMBER_ORDER_BUDGET`
- `TIME_STOP_HOURS`
- `TS_GIVEBACK_RATIO`
- `TS_MIN_GAP`
- `USE_SMART_CACHE`
- `WFO_STATIC_RANK`
- `WRITE_SIM_STORAGE`

## 2. `configs/sim_dev.properties` — doi chieu

| key | gia tri | trang thai |
|---|---|---|
| `AEROSPIKE_HOST` | 103.157.218.242 | active |
| `AEROSPIKE_HOST_226` | 127.0.0.1 | active |
| `AEROSPIKE_NAMESPACE` | test | active |
| `AEROSPIKE_NAMESPACE_242` | ticker | active |
| `AEROSPIKE_PORT` | 3222 | active |
| `AEROSPIKE_PORT_226` | 3222 | active |
| `AEROSPIKE_READ_CLUSTER` | 226 | active |
| `CAPITAL_START` | 35000 | active |
| `DIED_SYMBOLS` | BTCDOM,USDC | active |
| `FILE_AI_PREDICTIONS` | ../storage/ai_ml/ai_predictions.data_v3_FULL | active |
| `NUMBER_THREAD_ORDER_MANAGER` | 2 | active |
| `SPECIAL_SYMBOLS` | BNB,ETH,XRP,ADA | active |
| `TICKER_SOURCE` | aerospike | active |
| `TIME_RUN` | 20220101 | active |
| `WRITE_SIM_STORAGE` | true | active |

Key code doc nhung file nay KHONG khai bao (chay bang default hardcode):

- `DISABLE_PREDICT_SYMBOL`
- `HARD_STOP_LOSS_RATE`
- `NUMBER_ORDER_BUDGET`
- `TIME_STOP_HOURS`
- `TS_GIVEBACK_RATIO`
- `TS_MIN_GAP`
- `USE_SMART_CACHE`
- `WFO_STATIC_RANK`

## 3. Tham so giao dich doc qua cong Cfg (env hoac TRADING_PROFILE)

- `ABLATION_MODE`
- `CAPITAL_START`
- `CONFIG_STRICT`
- `CONF_SIZE_FMAX`
- `CONF_SIZE_FMIN`
- `CONF_SIZE_HI`
- `CONF_SIZE_LO`
- `CONF_SIZE_MODE`
- `DCA_GRID_ENABLED`
- `DCA_GRID_LEVELS`
- `DCA_GRID_SCALAR`
- `DCA_GRID_SCALE`
- `DCA_GRID_WEIGHTS`
- `DCA_TIER_MARGIN_CAPS`
- `DCA_TIER_MARGIN_ENABLED`
- `DISABLE_PREDICT_SYMBOL`
- `ENABLE_SHORT`
- `GATE_AB_LABELS`
- `HARD_STOP_LOSS_RATE`
- `LIVE_ENTRY_GRID_MIN`
- `LIVE_LOSER_TIME_STOP_HOURS`
- `LIVE_LOSER_TS_BUFFER`
- `MAX_CONCURRENT`
- `NUMBER_ORDER_BUDGET`
- `SELECTOR_INVERT`
- `SELECTOR_OFFSET`
- `SELECTOR_ONLY_ENTRY`
- `SELECTOR_RANK_OFFSET`
- `SELECTOR_RANK_TOPK`
- `SELECTOR_SCORE_MAX`
- `SELECTOR_TOPN`
- `SEL_BACKTEST_HORIZON_IDX`
- `SEL_BACKTEST_SET`
- `SHORT_SL_PCT`
- `SHORT_TIME_STOP_HOURS`
- `SIM_AI_DYNAMIC_MIN`
- `SIM_APPLY_FUNDING`
- `SIM_BREAKER_MARGIN_HALT`
- `SIM_BREAKER_MODE`
- `SIM_ENTRY_UNIVERSE_DUMP`
- `SIM_FAIL_FAST_ON_DATA_ERROR`
- `SIM_FUNDING_MARK`
- `SIM_FUNDING_SCALE`
- `SIM_GATE_COUNT_ONLY`
- `SIM_GATE_MARKET_OFF`
- `SIM_GATE_ROLLING_DAYS`
- `SIM_GATE_ROLLING_PCT`
- `SIM_HARD_SL_PCT`
- `SIM_LOSER_TIME_STOP_HOURS`
- `SIM_MIN_MOMENTUM_15M`
- `SIM_MS_DOWN_BIG_AVG`
- `SIM_OFF_FLAT_HARD`
- `SIM_PREDICT_SYMBOL_RATE_MAX`
- `SIM_RATE_FEE`
- `SIM_RATE_PROFIT_STOP_MARKET`
- `SIM_SELECTOR_MAX_STALE_MIN`
- `SIM_SLIPPAGE_RATE`
- `SIM_TRAIL_PER_SYMBOL`
- `SIM_TREAT_ZERO_VOL_AS_DELIST`
- `SIM_TS_GIVEBACK`
- `SIM_TS_PROFIT_MULTIPLIER`
- `SIZE_MULT`
- `TIER_FLAT`
- `TIME_STOP_HOURS`
- `TRAIL_PEAK_MODE`
- `TS_CARRY_SL_ON_DCA`
- `TS_GAP_CONST`
- `TS_GIVEBACK_FLOOR`
- `TS_GIVEBACK_RATIO`
- `TS_LIVE_MIN_LOCK`
- `TS_MIN_GAP`
- `TS_PNOPUMP_WEAK_THR`
- `TS_PRED_GAP`
- `TS_RATCHET_DECOUPLED`
- `WFO_DISABLE_DCA`
- `WFO_LOG_ENTRIES`

## 4. Kiem tra cong Cfg

```
check_cfg_gateway: OK — khong co tham so giao dich nao lach cong Cfg.
```
