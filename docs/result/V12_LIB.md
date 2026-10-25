# V12_LIB — thư viện c3_live độc lập (C2, C4, C5, C13, C14, P0-U1..U4)

Branch `v1.2/lib` từ `16de49a6` (worktree `~/claude_master/v12/lib`). Agent: v12lib (Claude Opus). Ngày 2026-10-25.
Phạm vi: CHỈ package mới `com.binance.chuyennd.c3live.*` — **chưa nối** vào `DetectEntrySignal2TradeNormal`, `BinanceOrderTradingManager`,
`ShadowBookC3`, `KillSwitchEngine`, `AIRejectFilter`, `LiveGateRollingRatio`, `LiveFeaturePipeline` (vòng 2). Không cờ nào cần vì chưa có đường gọi.

## 1. Commit
| commit | nội dung |
|---|---|
| `53f39ef8` | **c3live.api** (commit đầu, cho vòng 2): `ExchangeGateway`, DTO bất biến, `ErrorKind`, `GatewayException`, `ExchangeInfoParser`, `ClientOrderIds`; test `MockExchangeGateway` |
| `3e3765e2` | C14 `c3live.log.OrderAuditLog` |
| `06a08f88` | C13 `c3live.rate.RateGuard` |
| `f613d288` | C2 `c3live.client.C3LiveClient` (+ `C3LiveKeys`, `C3LiveClientConfig`, `HmacSigner`, `ErrorMapper`, `C3LiveKeyException`) |
| `e293c695` | C4 `c3live.filters.SymbolRules` + fixture exchangeInfo tay |
| `48fbaadb` | C5 `c3live.guard.AccountModeGuard` |
| `4cb54bd4` | P0-U1..U4 `c3live.universe.SymbolUniverseLive` (+ `TradFiClassifier`, `UniverseDiff`) |
| (commit này) | `docs/plan/GOLIVE_DECISIONS_Q1.md`, `docs/result/V12_LIB.md` |

## 2. Việc × tiêu chí × test
| mã | tiêu chí (GOLIVE_SCENARIO §2 / task) | kết quả | test |
|---|---|---|---|
| api | interface chung 3 bản cài Live/Dry/Mock; lỗi → enum 7 loại | xong | `ApiTypesTest` 3 |
| C2 | key từ `LIVE_C3_KEYS_FILE` (mặc định `/root/.config/c3live/keys.env`), quyền **đúng 600** + owner (mặc định root), không symlink, thư mục cha không ghi được bởi group/other; sai ⇒ `C3LiveKeyException`, **không tạo client**; HMAC-SHA256; java.net.http; timeout; recvWindow; đồng bộ giờ server (10′ + khi -1021); mọi lỗi → `ErrorKind`; không log key/secret/signature/query/listenKey; không dùng `PrivateConfig`/`ClientSingleton`/`BinanceFuturesClientSingleton` | xong | `C3LiveClientTest` 14: vector HMAC 2 bộ docs Binance; ký đúng (kiểm độc lập bằng javax.crypto) trên mock `HttpServer` JDK (repo không có MockWebServer); symbol non-ASCII percent-encode UTF-8 + ký đúng; map -2015/-1022→AUTH, -1021→OTHER+resync, -2019→INSUFFICIENT_MARGIN, -1013/-4164/-1111→FILTER, 429/418→RATE_LIMIT + chặn RateGuard theo Retry-After, -2011/-2013→UNKNOWN_ORDER, 5xx/-1007/timeout lệnh→TIMEOUT_UNKNOWN_STATE (notExecuted=false); 7 ca file key sai; mọi log/audit/exception quét không chứa key/secret/signature. `NoSecretInClassesTest` 1: lớp c3live không có chuỗi ≥32 ký tự [A-Za-z0-9] |
| C4 | bước `MARKET_LOT_SIZE.stepSize` (fallback LOT_SIZE), `minNotional`, `maxQty`; không đạt ⇒ bỏ leg + lý do, **không nới budget, không ép BTC 0.002**; stop long làm tròn XUỐNG theo tick; nạp lại 6 h | xong | `SymbolRulesTest` 7 (1 skip: dump thật chưa có): bất biến độc lập trên mọi symbol TRADING × 40 cặp giá/budget ngẫu nhiên: qty chia hết step, qty·price ≤ budget, budget − qty·price < step·price, ≥ minNotional, min/maxQty |
| C5 | multiAssets==true (KHÔNG tự đổi, chỉ báo+chặn), dual==false, CROSSED, leverage==1; sai ⇒ đặt lại 1 lần, vẫn sai ⇒ chặn symbol/toàn bộ + cảnh báo | xong | `AccountModeGuardTest` 7: 4 trạng thái sai × (sửa được / vẫn sai, đặt lại đúng 1 lần) + fail-closed khi lỗi đọc + cache (đợt 24 symbol = 1 lần kiểm toàn cục) |
| C13 | ngân sách weight/1m, lệnh/10s, lệnh/1m từ `exchangeInfo.rateLimits`, ≤ 50 %; hết ⇒ chờ có hạn hoặc RATE_LIMIT; header `X-MBX-USED-WEIGHT-1M`; 429/418 back-off | xong | `RateGuardTest` 7: đợt **24 leg + 80 dời stop** (392 call, 208 lệnh tính cả huỷ) ⇒ max cửa sổ trượt (đo độc lập): weight/1m ≤ 1200, lệnh/10s ≤ 150, lệnh/1m ≤ 600 (= 50 % 2400/300/1200), 0 RATE_LIMIT, xong < 30 s giả lập |
| U1 | nguồn exchangeInfo, TRADING ∧ PERPETUAL ∧ USDT, refresh 15′, `diff()` | xong | `SymbolUniverseLiveTest` 6 |
| U2 (dữ liệu) | `deliveryDate < now + 7 ngày` ⇒ `isBuyable=false` | xong | +3 ngày bị chặn, +8 ngày mua được, ngày sau bị chặn |
| U3 | loại TradFi khỏi universe mua + `marketIndexMembers()` | xong (**phân loại CHƯA XÁC MINH**) | 4 luật (danh sách / contractType TRADIFI* / underlyingType ∉ {COIN, INDEX} / underlyingSubType TradFi…) |
| U4 | non-ASCII: giữ trong U nếu TRADING, xử lý UTF-8 không regex; mặc định không mua (`LIVE_C3_ALLOW_NONASCII=0`) + lý do | xong | `whyNotBuyable = NON_ASCII`; cờ 1 ⇒ mua được + vào market index |
| UNIVERSE_EXCLUDE | thay DIED; cảnh báo khi symbol EXCLUDE (không `:intentional`) vẫn TRADING (POWR, MDT) | xong | alerter 1 lần, không lặp khi tập không đổi |
| C14 | 1 dòng `[C3-LIVE-ORDER]` 12 cột cố định qua SLF4J, không key | xong | `OrderAuditLogTest` 2 + dòng audit thật trong `C3LiveClientTest` |

## 3. Validation
- `mvn -o -q package -DskipTests=false`: **EXIT 0**; toàn repo **458 test, 0 fail, 0 error, 2 skip** (1 skip mới = test dump exchangeInfo thật chưa có).
- Test mới c3live: **47** (46 pass + 1 skip có chủ đích).
- **Bytecode lớp cũ**: sha256 toàn bộ `target/classes/**/*.class` trước (base `16de49a6`, 738 lớp) và sau: **738/738 lớp cũ giống hệt, 0 lớp đổi**; thêm 45 lớp `c3live`. `git diff --name-only 16de49a6 HEAD` ngoài c3live/docs: **0 file**.
- Lớp c3live trong jar shaded: 45; quét `[A-Za-z0-9]{32,}`: **0**. Không `System.out/err`, `printStackTrace`; không import `chuyennd.config`/`chuyennd.client`/`com.binance.client`.
- `PrivateConfig.java` chỉ chép để biên dịch (gitignored, không commit, không in).

## 4. CHƯA XÁC MINH / chưa làm
1. **Trường phân loại TradFi thật** — Oracle chưa có dump exchangeInfo đầy đủ (`exchange_info_pin.json` chỉ có symbol/status/filters rút gọn). Fixture tay giả định `contractType=TRADIFI_PERPETUAL`, `underlyingType=EQUITY`, `underlyingSubType=["TradFi"]`. Cần owner chạy `bash ~/claude_master/deploy/dump_exchangeinfo.sh` ⇒ chạy lại `SymbolRulesTest.invariantsOnRealDumpIfPresent` + đối chiếu tập TradFi với danh sách proxy SYMLIFE (113 symbol, `live_low_activity_1023.csv`). Trong lúc chờ: fallback `UNIVERSE_TRADFI_LIST`.
2. **Algo API** (`/fapi/v1/algoOrder`, `/fapi/v1/openAlgoOrders`, huỷ/tra theo `clientAlgoId`) dựa trên code LEGACY (`SyncRequestImpl`) + tài liệu nhớ; mã lỗi khi algo order không tồn tại chưa xác minh ⇒ `queryStop` có thể ném OTHER thay vì empty (an toàn: không kết luận "không có"). Xác minh ở canary bước (4).
3. Weight endpoint (`W_*` trong `C3LiveClient`), format `/fapi/v1/symbolConfig`, `/fapi/v3/account`, `/fapi/v3/positionRisk` — theo tài liệu, chưa thấy response thật (canary bước 1).
4. Giới hạn rate mặc định 2400/300/1200 khi chưa nạp exchangeInfo.
5. Chưa nối vào đường lệnh/sổ (C1, C3, C6–C9, C12) — vòng 2.

## 5. Rủi ro / điểm mở cho vòng 2
- **IP weight chung LEGACY (242)**: RateGuard dùng max(đếm nội bộ, header sàn) ⇒ khi LEGACY + c3_live ≥ 50 % IP, c3_live **tự nhường** tới phút sau (chờ ≤ `LIVE_C3_RATE_MAX_WAIT_MS`, mặc định 2 s, quá ⇒ RATE_LIMIT). Nếu LEGACY thường xuyên > 1200/phút, c3_live có thể bị đói — theo dõi WARN `[C3-RATE]`.
- `newStopMarket(sym, side, stop, cid, ro)` 5 tham số = **closePosition=true** (sàn cấm gửi kèm reduceOnly). Q1a nói "reduce-only": C6 chọn 1 trong 2 — bản 6 tham số (qty + reduceOnly=true) phải dời/đặt lại stop sau mỗi DCA; closePosition tự theo vị thế. MASTER quyết.
- `workingType` mặc định `CONTRACT_PRICE` (giá khớp cuối ≈ close sim); `MARK_PRICE` qua `LIVE_C3_STOP_WORKING_TYPE`.
- `maxQty` vượt ⇒ BỎ leg (không cắt nhỏ). `minNotional` so với giá ref (close 1m) — sàn so giá khớp; có tham số đệm `minNotionalMargin` (mặc định 1, không đệm).
- Huỷ lệnh tính vào ngân sách lệnh (bảo thủ, `LIVE_C3_CANCEL_COUNTS_AS_ORDER=1`).
- Key owner mặc định `root` (`LIVE_C3_KEYS_OWNER`): JVM trên 242 phải chạy bằng root (CHƯA XÁC MINH user chạy app).
- Symbol non-ASCII KHÔNG được đưa thẳng vào clientOrderId (luật sàn `^[.A-Z:/a-z0-9_-]{1,36}$`) ⇒ C3 dùng `ClientOrderIds.symbolToken(sym)`; client từ chối cid sai trước khi gửi.
- Universe: `deliveryDate == 0` ⇒ không mua (fail-closed); snapshot cũ > 60′ ⇒ không mua; `isAlive` (quản lý vị thế) tách khỏi `isTradable`/`isBuyable` để vị thế TradFi/EXCLUDE cũ vẫn đóng được.
- Pre-market (nếu sàn dùng `underlyingType` khác COIN/INDEX) bị coi là TradFi ⇒ không mua (bảo thủ).

## 6. Biến môi trường mới (đều chỉ dùng trong c3live, chưa có đường gọi)
`LIVE_C3_KEYS_FILE`, `LIVE_C3_KEYS_OWNER`, `LIVE_C3_BASE_URL`, `LIVE_C3_RECV_WINDOW_MS`, `LIVE_C3_HTTP_CONNECT_TIMEOUT_MS`, `LIVE_C3_HTTP_TIMEOUT_MS`,
`LIVE_C3_TIME_SYNC_MS`, `LIVE_C3_STOP_WORKING_TYPE`, `LIVE_C3_RATE_MAX_WAIT_MS`, `LIVE_C3_CANCEL_COUNTS_AS_ORDER`, `UNIVERSE_EXCLUDE`
(mặc định `BTCDOMUSDT:intentional,USDCUSDT:intentional`), `LIVE_C3_ALLOW_NONASCII` (0), `UNIVERSE_TRADFI_LIST`, `UNIVERSE_CRYPTO_UNDERLYING_TYPES`,
`UNIVERSE_TRADFI_SUBTYPES`, `UNIVERSE_MAX_STALE_MS`.

## 7. File (tất cả MỚI)
- `src/main/java/com/binance/chuyennd/c3live/api/` — `AccountSnapshot, AssetBalance, ClientOrderIds, ErrorKind, ExchangeGateway, ExchangeInfo, ExchangeInfoParser, GatewayException, OrderInfo, OrderKind, OrderStatus, PositionInfo, RateLimitSpec, Side, SymbolConfig, SymbolMeta`
- `.../c3live/client/` — `C3LiveClient, C3LiveClientConfig, C3LiveKeys, C3LiveKeyException, ErrorMapper, HmacSigner`
- `.../c3live/filters/SymbolRules`, `.../c3live/guard/AccountModeGuard`, `.../c3live/rate/RateGuard`, `.../c3live/log/OrderAuditLog`,
  `.../c3live/universe/` — `SymbolUniverseLive, TradFiClassifier, UniverseDiff`
- test: `src/test/java/com/binance/chuyennd/c3live/{api/ApiTypesTest, client/C3LiveClientTest, client/NoSecretInClassesTest, filters/SymbolRulesTest, guard/AccountModeGuardTest, log/OrderAuditLogTest, rate/RateGuardTest, universe/SymbolUniverseLiveTest, mock/MockExchangeGateway}`
- `src/test/resources/c3live/exchangeInfo_fixture_manual.json` (fixture tay, CHƯA XÁC MINH)
- `docs/plan/GOLIVE_DECISIONS_Q1.md`, `docs/result/V12_LIB.md`

## 8. API công khai (chữ ký Java) cho vòng 2
```java
// c3live.api
public interface ExchangeGateway {
  String name(); long serverTime(); ExchangeInfo exchangeInfo();
  OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String clientOrderId, boolean reduceOnly);
  default OrderInfo newStopMarket(String symbol, Side side, BigDecimal stopPrice, String clientOrderId, boolean reduceOnly); // closePosition=true
  OrderInfo newStopMarket(String symbol, Side side, BigDecimal qtyOrNull, BigDecimal stopPrice, String clientOrderId, boolean reduceOnly);
  OrderInfo cancelOrder(String symbol, String clientOrderId);      OrderInfo cancelStop(String symbol, String clientAlgoId);
  Optional<OrderInfo> queryOrder(String symbol, String clientOrderId); Optional<OrderInfo> queryStop(String symbol, String clientAlgoId);
  List<OrderInfo> openOrders(String symbolOrNull); List<OrderInfo> openStops(String symbolOrNull);
  List<PositionInfo> positions(); AccountSnapshot account();
  boolean multiAssetsMargin(); boolean dualSidePosition(); void setDualSidePosition(boolean dual);
  SymbolConfig symbolConfig(String symbol); int setLeverage(String symbol, int leverage); void setMarginType(String symbol, String marginType);
  String startUserStream(); void keepAliveUserStream(String listenKey); void closeUserStream(String listenKey);
}
public enum ErrorKind { RATE_LIMIT, INSUFFICIENT_MARGIN, FILTER, UNKNOWN_ORDER, TIMEOUT_UNKNOWN_STATE, AUTH, OTHER }
public class GatewayException extends RuntimeException { ErrorKind getKind(); int getHttpStatus(); int getExchangeCode(); boolean isDefinitelyNotExecuted(); long getRetryAfterMs(); }
public enum Side { BUY, SELL }  public enum OrderKind { REGULAR, ALGO }
public enum OrderStatus { NEW, PARTIALLY_FILLED, FILLED, CANCELED, REJECTED, EXPIRED, EXPIRED_IN_MATCH, TRIGGERING, TRIGGERED, FINISHED, UNKNOWN; boolean isFinal(); }
public final class OrderInfo { getKind/getSymbol/getOrderId/getClientOrderId/getSide/getType/getStatus/getRawStatus/getOrigQty/getExecutedQty/getAvgPrice/getStopPrice/isReduceOnly/isClosePosition/getUpdateTimeMs; static Builder builder(); Builder toBuilder(); }
public final class PositionInfo { getSymbol/getPositionSide/getPositionAmt/getEntryPrice/getMarkPrice/getUnrealizedProfit/getNotional/getUpdateTimeMs/isFlat }
public final class AccountSnapshot { getTotalMarginBalance/getTotalWalletBalance/getAvailableBalance/getTotalUnrealizedProfit/getAssets/getTimeMs; Optional<AssetBalance> asset(String) }
public final class SymbolConfig { CROSSED, ISOLATED; getSymbol/getMarginType/getLeverage/isCrossed }
public final class ExchangeInfo { getServerTime/getRateLimits/getSymbols; Optional<SymbolMeta> symbol(String); Optional<RateLimitSpec> rateLimit(String type, long windowMs) }
public final class SymbolMeta { getSymbol/getStatus/getContractType/getQuoteAsset/getUnderlyingType/getUnderlyingSubType/getOnboardDate/getDeliveryDate/getTickSize/getStepSize/getMinQty/getMaxQty/getMarketStepSize/getMarketMinQty/getMarketMaxQty/getMinNotional ... }
public final class ExchangeInfoParser { static ExchangeInfo parse(String json); static ExchangeInfo parseFile(Path p) throws IOException; }
public final class ClientOrderIds { MAX_LEN=36; static boolean isValid(String id); static String symbolToken(String symbol); }

// c3live.client
public final class C3LiveClient implements ExchangeGateway {
  static C3LiveClient create(C3LiveClientConfig cfg, RateGuard rate) throws C3LiveKeyException; // cach DUY NHAT cho production
  RateGuard rateGuard(); long syncTime(); long timeOffsetMs(); long timeSyncCount(); }
public final class C3LiveClientConfig { static C3LiveClientConfig fromEnv(); static C3LiveClientConfig fromEnv(Function<String,String> env); static Builder builder(); ... }
public final class C3LiveKeys { DEFAULT_PATH, DEFAULT_OWNER; static C3LiveKeys load(Path path, String expectedOwner) throws C3LiveKeyException; }
public class C3LiveKeyException extends Exception
public final class ErrorMapper { static ErrorKind kindFor(int httpStatus, int code); static boolean definitelyNotExecuted(ErrorKind k); }
public final class HmacSigner { HmacSigner(byte[] secret); String sign(String payload); static String hmacSha256Hex(byte[] secret, String payload); }

// c3live.filters
public final class SymbolRules {
  SymbolRules(ExchangeInfo ei, long nowMs); SymbolRules(ExchangeInfo ei, long nowMs, BigDecimal minNotionalMargin);
  void load(ExchangeInfo ei, long nowMs); boolean refreshIfDue(long nowMs, Supplier<ExchangeInfo> source); // 6h
  Sizing sizeMarketBuy(String symbol, BigDecimal budgetUsdt, BigDecimal refPrice);
  Sizing checkQty(String symbol, BigDecimal qty, BigDecimal refPrice, boolean market, boolean reduceOnly);
  BigDecimal roundQtyDown(String symbol, BigDecimal qty, boolean market); BigDecimal roundPrice(String symbol, BigDecimal price, RoundingMode mode);
  BigDecimal roundStopPriceForLong(String symbol, BigDecimal stop); boolean isPriceInRange(String symbol, BigDecimal price);
  BigDecimal tickSize(String symbol); Optional<SymbolMeta> meta(String symbol);
  enum SkipReason { UNKNOWN_SYMBOL, NOT_TRADING, NO_FILTER, BAD_INPUT, QTY_ZERO, BELOW_MIN_QTY, ABOVE_MAX_QTY, BELOW_MIN_NOTIONAL, OVER_BUDGET }
  static final class Sizing { boolean isOk(); BigDecimal getQty(); BigDecimal getNotional(); SkipReason getReason(); String getDetail(); } }

// c3live.guard
public final class AccountModeGuard {
  AccountModeGuard(ExchangeGateway gw, Consumer<String> alerter);
  AccountModeGuard(ExchangeGateway gw, int expectedLeverage, Consumer<String> alerter, LongSupplier clock, long globalTtlMs);
  Result checkGlobal(); Result checkSymbol(String symbol); boolean isGlobalBlocked(); boolean isSymbolCleared(String symbol);
  Set<String> blockedSymbols(); void resetSymbol(String symbol);
  static final class Result { boolean isOk(); String getScope(); List<String> getProblems(); List<String> getActions(); } }

// c3live.rate
public final class RateGuard {
  RateGuard(Limits limits, double fraction /*<=0.5*/, long maxWaitMs, Clock clock); static RateGuard defaults();
  void updateLimits(Limits l); void acquire(int weight, int orders); void acquire(int weight, int orders, long maxWait);
  void onHeaders(Integer usedWeight1m, Integer orderCount10s, Integer orderCount1m); void onSuccess(); long onRateLimited(int httpStatus, long retryAfterMs);
  long blockedUntilMs(); int budgetWeight1m(); int budgetOrders10s(); int budgetOrders1m(); long peakWeight1m(); long peakOrders10s(); long peakOrders1m();
  static final class Limits { Limits(int weight1m, int orders10s, int orders1m, boolean fromExchange); static Limits binanceDefault(); static Limits fromExchangeInfo(ExchangeInfo ei); }
  interface Clock { long nowMs(); void sleepMs(long ms) throws InterruptedException; } }

// c3live.log
public final class OrderAuditLog { LIVE_TAG="[C3-LIVE-ORDER]", DRY_TAG="[LIVE-DRY]";
  OrderAuditLog(String tag); OrderAuditLog(String tag, Consumer<String> sink); static OrderAuditLog live(); static OrderAuditLog dry();
  String record(Entry e); static String format(String tag, Entry e);
  static final class Entry { static Entry of(long ts); clientOrderId/orderId/symbol/side/type/qty/price/status/latencyMs/errCode/reason (fluent) } }

// c3live.universe
public final class SymbolUniverseLive {
  SymbolUniverseLive(Config cfg, Supplier<ExchangeInfo> source, Consumer<String> alerter);
  UniverseDiff refresh(long nowMs); UniverseDiff refreshIfDue(long nowMs) /*15'*/; UniverseDiff apply(ExchangeInfo ei, long nowMs);
  boolean isAlive(String sym); boolean isTradable(String sym); boolean isBuyable(String sym, long nowMs); Optional<String> whyNotBuyable(String sym, long nowMs);
  Set<String> marketIndexMembers(); Set<String> tradableSymbols(); Optional<TradFiClassifier.Verdict> classification(String sym);
  Optional<Reason> notTradableReason(String sym); UniverseDiff diff(); static boolean isAsciiSymbol(String s);
  static final class Config { static Config fromEnv(Function<String,String> env); static Config defaults(); } }
public final class TradFiClassifier { TradFiClassifier(Set<String> cryptoUnderlying, Set<String> tradfiTags, Set<String> explicitList); static TradFiClassifier defaults(); Verdict classify(SymbolMeta m); }
// test: com.binance.chuyennd.c3live.mock.MockExchangeGateway (src/test) — sàn giả lập trong bộ nhớ, tiêm lỗi failNext(method, ex), đếm calls(method)
```
