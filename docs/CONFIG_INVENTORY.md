# BAN KIEM KE CAU HINH — sinh tu ma nguon boi tools/gen_config_inventory.sh

Sinh luc: 2026-09-03 11:43 UTC · commit `19b976d`

> KHONG go tay file nay. Chay lai script sau moi lan doi cau hinh.

## 1. Key ma code THUC SU doc tu config.properties

| key | doc o dau |
|---|---|
| `AEROSPIKE_HOST` | chuyennd/tradecore/Configs.java:387:    public static final String AEROSPIKE_HOST_242 = Co |
| `AEROSPIKE_HOST_226` | chuyennd/tradecore/Configs.java:390:    // Tên hằng đổi 226→ORACLE (2026-08-04, re |
| `AEROSPIKE_NAMESPACE` | chuyennd/tradecore/Configs.java:395:    public static final String AEROSPIKE_NAMESPACE = C |
| `AEROSPIKE_NAMESPACE_242` | chuyennd/tradecore/Configs.java:406:    public static final String AEROSPIKE_NAMESPACE_242 |
| `AEROSPIKE_PORT` | chuyennd/tradecore/Configs.java:388:    public static final int AEROSPIKE_PORT_242 = Confi |
| `AEROSPIKE_PORT_226` | chuyennd/tradecore/Configs.java:393:    public static final int AEROSPIKE_PORT_ORACLE = Co |
| `AEROSPIKE_READ_CLUSTER` | chuyennd/tradecore/Configs.java:69:    public static String AEROSPIKE_READ_CLUSTER = prope |
| `CAPITAL_START` | chuyennd/tradecore/Configs.java:413:        String v = Cfg.get("CAPITAL_START"); |
| `DIED_SYMBOLS` | client/constant/Constants.java:59:        String symbols = Configs.getString("DIED_SYMBOLS |
| `FILE_AI_PREDICTIONS` | chuyennd/tradecore/Configs.java:385:    public static final String FILE_AI_ENTRY_PREDICTIO |
| `NUMBER_ORDER_BUDGET` | chuyennd/tradecore/Configs.java:149:    public static Integer number_order_budget = Cfg.ge |
| `NUMBER_THREAD_ORDER_MANAGER` | chuyennd/tradecore/Configs.java:108:    public static final Integer NUMBER_THREAD_ORDER_MA |
| `SPECIAL_SYMBOLS` | client/constant/Constants.java:66:        symbols = Configs.getString("SPECIAL_SYMBOLS"); |
| `TICKER_SOURCE` | chuyennd/tradecore/Configs.java:70:    public static String TICKER_SOURCE = properties.get |
| `TIME_RUN` | chuyennd/tradecore/Configs.java:81:    public static String TIME_RUN = Configs.getString(" |
| `TS_GIVEBACK_RATIO` | chuyennd/tradecore/Configs.java:173:    public static float TS_GIVEBACK_RATIO = Cfg.get("T |
| `USE_SMART_CACHE` | chuyennd/tradecore/Configs.java:76:    public static boolean USE_SMART_CACHE = properties. |
| `WFO_STATIC_RANK` | chuyennd/tradecore/Configs.java:80:    public static boolean WFO_STATIC_RANK = properties. |
| `WRITE_SIM_STORAGE` | chuyennd/tradecore/Configs.java:73:    public static boolean WRITE_SIM_STORAGE = propertie |

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

- `NUMBER_ORDER_BUDGET`
- `TS_GIVEBACK_RATIO`
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

- `NUMBER_ORDER_BUDGET`
- `TS_GIVEBACK_RATIO`
- `USE_SMART_CACHE`
- `WFO_STATIC_RANK`

## 3. Tham so giao dich doc qua cong Cfg (env hoac TRADING_PROFILE)

- `CAPITAL_START`
- `CONFIG_STRICT`
- `DCA_GRID_ENABLED`
- `DCA_GRID_LEVELS`
- `DCA_GRID_SCALAR`
- `DCA_GRID_SCALE`
- `DCA_GRID_WEIGHTS`
- `GATE_AB_LABELS`
- `NUMBER_ORDER_BUDGET`
- `OI_STALE_HALT`
- `OI_STALE_HALT_MS`
- `SELECTOR_ONLY_ENTRY`
- `SELECTOR_RANK_TOPK`
- `SEL_BACKTEST_HORIZON_IDX`
- `SEL_BACKTEST_SET`
- `SHADOW_NO_PUSH`
- `SIM_AI_DYNAMIC_MAX`
- `SIM_AI_DYNAMIC_MIN`
- `SIM_AI_DYNAMIC_MULTIPLIER`
- `SIM_APPLY_FUNDING`
- `SIM_BREAKER_MODE`
- `SIM_ENTRY_UNIVERSE_DUMP`
- `SIM_FAIL_FAST_ON_DATA_ERROR`
- `SIM_FUNDING_MARK`
- `SIM_FUNDING_SCALE`
- `SIM_F_BASE`
- `SIM_GATE_COUNT_ONLY`
- `SIM_LOSER_TIME_STOP_HOURS`
- `SIM_MIN_MOMENTUM_15M`
- `SIM_MS_DOWN_BIG_AVG`
- `SIM_PREDICT_SYMBOL_RATE_MAX`
- `SIM_RATE_FEE`
- `SIM_RATE_PROFIT_STOP_MARKET`
- `SIM_SLIPPAGE_RATE`
- `SIM_TS_GIVEBACK`
- `SIM_TS_MAX_GAP`
- `SIM_TS_MAX_GAP_WEAK`
- `SIM_TS_PNOPUMP_WEAK_THR`
- `SIM_U_MAX`
- `TIER_FLAT`
- `TS_GIVEBACK_RATIO`
- `TS_PNOPUMP_WEAK_THR`
- `WFO_DISABLE_DCA`
- `WFO_FUNDING_PRED_DIR`
- `WFO_LOG_ENTRIES`

## 4. Kiem tra cong Cfg

```
check_cfg_gateway: OK — khong co tham so giao dich nao lach cong Cfg.
```
