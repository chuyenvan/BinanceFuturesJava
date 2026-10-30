package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;
import java.util.List;
import java.util.Optional;

/**
 * [V12] Cong giao tiep san DUY NHAT cua duong c3_live (tai khoan con). 3 ban cai:
 * <ul>
 *   <li>Live: {@code c3live.client.C3LiveClient} (REST ky HMAC, key tu file root-only, qua RateGuard).</li>
 *   <li>Dry: (vong 2) di het size/round/clientOrderId, ghi [LIVE-DRY], KHONG gui.</li>
 *   <li>Mock: test (src/test .../c3live/mock/MockExchangeGateway).</li>
 * </ul>
 * Quy uoc chung:
 * <ul>
 *   <li>Moi loi -> {@link GatewayException} voi {@link ErrorKind}; khong tra null.</li>
 *   <li>qty / gia: BigDecimal DA lam tron theo filter (xem c3live.filters.SymbolRules); ban cai KHONG tu lam tron lai.</li>
 *   <li>One-way mode: khong gui positionSide.</li>
 *   <li>Lenh dieu kien (STOP_MARKET) di Algo API (/fapi/v1/algoOrder): orderId = algoId, clientOrderId = clientAlgoId.</li>
 * </ul>
 */
public interface ExchangeGateway {

    /** "live" | "dry" | "mock" ... (cho log). */
    String name();

    /** Gio server (ms). */
    long serverTime();

    /** GET /fapi/v1/exchangeInfo (public). */
    ExchangeInfo exchangeInfo();

    /**
     * Lenh MARKET (newOrderRespType=RESULT). Timeout -> TIMEOUT_UNKNOWN_STATE: phai {@link #queryOrder} theo clientOrderId
     * truoc khi gui lai.
     */
    OrderInfo newMarketOrder(String symbol, Side side, BigDecimal qty, String clientOrderId, boolean reduceOnly);

    /**
     * STOP_MARKET dong TOAN BO vi the (closePosition=true; tham so reduceOnly bi bo qua vi san cam gui kem closePosition).
     */
    default OrderInfo newStopMarket(String symbol, Side side, BigDecimal stopPrice, String clientOrderId, boolean reduceOnly) {
        return newStopMarket(symbol, side, null, stopPrice, clientOrderId, reduceOnly);
    }

    /**
     * STOP_MARKET (Algo API, algoType=CONDITIONAL). qty == null -> closePosition=true; qty != null -> quantity + reduceOnly.
     * stopPrice = triggerPrice da lam tron theo tick (stop ban cua long: lam tron XUONG).
     */
    OrderInfo newStopMarket(String symbol, Side side, BigDecimal qty, BigDecimal stopPrice, String clientOrderId,
                            boolean reduceOnly);

    /** Huy lenh thuong theo origClientOrderId. Khong ton tai -> UNKNOWN_ORDER. */
    OrderInfo cancelOrder(String symbol, String clientOrderId);

    /** Huy lenh algo (stop) theo clientAlgoId. Khong ton tai -> UNKNOWN_ORDER. */
    OrderInfo cancelStop(String symbol, String clientAlgoId);

    /**
     * Tra lenh thuong theo origClientOrderId. San noi khong ton tai (-2013) -> Optional.empty().
     * Khong chac chan (timeout) -> NEM TIMEOUT_UNKNOWN_STATE (khong bao gio tra empty khi chua biet).
     */
    Optional<OrderInfo> queryOrder(String symbol, String clientOrderId);

    /**
     * [3h] Tra lenh thuong theo orderId (vd actualOrderId cua stop algo da kich). Khong ton tai -> empty. Mac dinh: khong ho tro
     * (nem UnsupportedOperationException => nguoi goi coi la KHONG doc duoc).
     */
    default Optional<OrderInfo> queryOrderById(String symbol, long orderId) {
        throw new UnsupportedOperationException("queryOrderById khong ho tro boi " + name());
    }

    /**
     * [3j R2(c)] Cac khop THAT cua 1 lenh thuong theo orderId (GET /fapi/v1/userTrades). Nguon gia thu 3 khi ACK
     * MARKET khong co avgPrice va queryOrder chua tra gia. Khong doc duoc => nem GatewayException; khong co khop => list rong.
     * Mac dinh: khong ho tro (nem UnsupportedOperationException => nguoi goi coi la KHONG doc duoc).
     */
    default List<TradeFill> userTrades(String symbol, long orderId) {
        throw new UnsupportedOperationException("userTrades khong ho tro boi " + name());
    }

    /** Nhu {@link #queryOrder} cho lenh algo (clientAlgoId). */
    Optional<OrderInfo> queryStop(String symbol, String clientAlgoId);

    /** Lenh thuong dang mo; symbol null = moi symbol (weight cao). */
    List<OrderInfo> openOrders(String symbolOrNull);

    /** Lenh algo (stop) dang mo; symbol null = moi symbol. */
    List<OrderInfo> openStops(String symbolOrNull);

    /** Vi the khac 0 (va ca vi the 0 neu san tra ve). */
    List<PositionInfo> positions();

    /** Tai khoan: totalMarginBalance / totalWalletBalance / availableBalance / assets. */
    AccountSnapshot account();

    /** GET /fapi/v1/multiAssetsMargin. */
    boolean multiAssetsMargin();

    /** GET /fapi/v1/positionSide/dual (true = hedge mode). */
    boolean dualSidePosition();

    /** POST /fapi/v1/positionSide/dual (chi duoc khi khong co vi the / lenh mo). "Khong can doi" coi la thanh cong. */
    void setDualSidePosition(boolean dualSidePosition);

    /** GET /fapi/v1/symbolConfig?symbol= : marginType + leverage. */
    SymbolConfig symbolConfig(String symbol);

    /**
     * [V12 2c MIN-5] GET /fapi/v1/symbolConfig KHONG kem symbol = cau hinh MOI symbol (1 call) — de nap san luc start /
     * moi gio. CHUA XAC MINH san tra du moi symbol (symbol vang => AccountModeGuard kiem rieng o leg dau). Ban cai khong
     * ho tro => UnsupportedOperationException.
     */
    default java.util.List<SymbolConfig> symbolConfigs() {
        throw new UnsupportedOperationException("symbolConfigs");
    }

    /** POST /fapi/v1/leverage. Tra leverage san xac nhan. */
    int setLeverage(String symbol, int leverage);

    /** POST /fapi/v1/marginType (CROSSED|ISOLATED). "Khong can doi" (-4046) coi la thanh cong. */
    void setMarginType(String symbol, String marginType);

    /**
     * [V12 3] GET /fapi/v1/ticker/24hr (public; symbol null = moi symbol, weight 40; co symbol = weight 1). Chi cong cu canary
     * dung (luat chon symbol + gia tham chieu cho tran notional). Ban cai khong ho tro => UnsupportedOperationException.
     */
    default List<Ticker24h> tickers24h(String symbolOrNull) {
        throw new UnsupportedOperationException("tickers24h");
    }

    /** POST /fapi/v1/listenKey (user-data stream cua TAI KHOAN CON). */
    String startUserStream();

    /** PUT /fapi/v1/listenKey. */
    void keepAliveUserStream(String listenKey);

    /** DELETE /fapi/v1/listenKey. */
    void closeUserStream(String listenKey);

    /**
     * [V12 R4 R4] GET /fapi/v1/income (CHI DOC, weight 30): lich su thu nhap theo symbol (vd FUNDING_FEE) tu startTime, toi da
     * limit dong. Dung tinh funding c3 theo symbol tren tai khoan chinh. Mac dinh: khong ho tro.
     */
    default List<IncomeRecord> income(String incomeType, long startTimeMs, int limit) {
        throw new UnsupportedOperationException("income khong ho tro boi " + name());
    }
}
