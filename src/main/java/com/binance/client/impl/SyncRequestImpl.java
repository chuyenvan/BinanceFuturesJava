// File: com/binance/client/impl/SyncRequestImpl.java
package com.binance.client.impl;

import com.binance.client.RequestOptions;
import com.binance.client.SyncRequestClient;
import com.binance.client.impl.utils.JsonWrapper;
import com.binance.client.impl.utils.JsonWrapperArray;
import com.binance.client.model.enums.*;
import com.binance.client.model.market.ExchangeInfoEntry;
import com.binance.client.model.market.ExchangeInformation;
import com.binance.client.model.market.Trade;
import com.binance.client.model.trade.Order;
import com.binance.connector.futures.client.utils.SignatureGenerator;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;

import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class SyncRequestImpl implements SyncRequestClient {

    private final String apiKey;
    private final String secretKey;
    private final String BASE_URL = "https://fapi.binance.com";

    public SyncRequestImpl(String apiKey, String secretKey, RequestOptions options) {
        this.apiKey = apiKey;
        this.secretKey = secretKey;
    }

    private <T> RestApiRequest<T> createRequest(String method, String endpoint, Map<String, String> params, Class<T> clazz) {
        RestApiRequest<T> apiRequest = new RestApiRequest<>();
        params.put("timestamp", String.valueOf(System.currentTimeMillis()));
        params.put("recvWindow", "10000");

        StringBuilder queryString = new StringBuilder();
        for (Map.Entry<String, String> entry : params.entrySet()) {
            if (queryString.length() > 0) queryString.append("&");
            queryString.append(entry.getKey()).append("=").append(entry.getValue());
        }

        String signature = SignatureGenerator.getSignature(queryString.toString(), secretKey);
        queryString.append("&signature=").append(signature);

        String fullUrl = BASE_URL + endpoint + "?" + queryString.toString();

        // Log URL để debug nếu cần
        // System.out.println("REQUEST: " + fullUrl);

        Request.Builder builder = new Request.Builder()
                .url(fullUrl)
                .addHeader("X-MBX-APIKEY", apiKey)
                .addHeader("Content-Type", "application/json");

        if ("POST".equals(method)) {
            builder.post(RequestBody.create(MediaType.parse("application/x-www-form-urlencoded"), ""));
        } else if ("DELETE".equals(method)) {
            builder.delete(); // <--- Bắt buộc phải có dòng này thì mới HỦY được
        } else {
            builder.get();
        }

        apiRequest.request = builder.build();

        apiRequest.jsonParser = (JsonWrapper json) -> {
            if (clazz.getSimpleName().equals("ExchangeInformation")) {
                ExchangeInformation info = new ExchangeInformation();
                List<ExchangeInfoEntry> symbolListRes = new LinkedList<>();
                if (json.containKey("symbols")) {
                    JsonWrapperArray symbolArray = json.getJsonArray("symbols");
                    symbolArray.forEach(symbolJson -> {
                        ExchangeInfoEntry symbol = new ExchangeInfoEntry();
                        symbol.setSymbol(symbolJson.getString("symbol"));
                        symbol.setStatus(symbolJson.getString("status"));
                        if (symbolJson.containKey("filters")) {
                            List<Map<String, String>> filters = new LinkedList<>();
                            JsonWrapperArray filtersArray = symbolJson.getJsonArray("filters");
                            filtersArray.forEach(f -> {
                                Map<String, String> map = new java.util.HashMap<>();
                                map.put("filterType", f.getString("filterType"));
                                if (f.containKey("minQty")) map.put("minQty", f.getString("minQty"));
                                if (f.containKey("tickSize")) map.put("tickSize", f.getString("tickSize"));
                                if (f.containKey("notional")) map.put("notional", f.getString("notional"));
                                filters.add(map);
                            });
                            List<List<Map<String, String>>> wrapper = new LinkedList<>();
                            wrapper.add(filters);
                            symbol.setFilters(wrapper);
                        }
                        symbolListRes.add(symbol);
                    });
                }
                info.setSymbols(symbolListRes);
                return (T) info;
            }
            if (clazz.getSimpleName().equals("Order")) {
                Order order = new Order();
                if (json.containKey("orderId")) order.setOrderId(json.getLong("orderId"));
                if (json.containKey("algoId")) order.setOrderId(json.getLong("algoId"));
                if (json.containKey("symbol")) order.setSymbol(json.getString("symbol"));
                if (json.containKey("status")) order.setStatus(json.getString("status"));
                return (T) order;
            }
            return null;
        };
        return apiRequest;
    }

    @Override
    public ExchangeInformation getExchangeInformation() {
        RestApiRequest<ExchangeInformation> request = createRequest("GET", "/fapi/v1/exchangeInfo", new TreeMap<>(), ExchangeInformation.class);
        return RestApiInvoker.callSync(request);
    }

    //    // --- SỬA HÀM NÀY ĐỂ GỌI ALGO API CHUẨN ---
//    @Override
//    public Order postAlgoOrder(String symbol, OrderSide side, OrderType orderType, String quantity,
//                               String stopPrice, String reduceOnly) {
//        Map<String, String> params = new TreeMap<>();
//        params.put("symbol", symbol);
//        params.put("side", side.toString());
//
//        // QUAN TRỌNG:
//        // algoType phải là "STOP" (thay vì STOP_MARKET)
//        // type sẽ là "MARKET" để chỉ định đây là Stop Market
//        params.put("algoType", "CONDITIONAL");
//        params.put("type", "STOP_MARKET");
//
//        params.put("triggerprice", stopPrice);
//
//        if (quantity != null) params.put("quantity", quantity);
//        if (reduceOnly != null) params.put("reduceOnly", reduceOnly);
//
//        // Gọi vào endpoint Algo
//        RestApiRequest<Order> request = createRequest("POST", "/fapi/v1/algoOrder", params, Order.class);
//        return RestApiInvoker.callSync(request);
//    }
// --- SỬA HÀM NÀY ĐỂ GỌI ALGO API CHUẨN ---
    @Override
    public Order postAlgoOrder(String symbol, OrderSide side, OrderType orderType, String quantity,
                               String stopPrice, String reduceOnly) {
        Map<String, String> params = new TreeMap<>();
        params.put("symbol", symbol);
        params.put("side", side.toString());

        // 1. Khai báo hệ Algo theo luật mới Binance
        params.put("algoType", "CONDITIONAL");
        params.put("type", orderType.toString()); // STOP_MARKET

        // 2. 🔥 SỬA LỖI CHẾT NGƯỜI: Binance bắt buộc dùng 'triggerPrice' (Chữ P viết hoa)
        // Code cũ của bạn dùng 'triggerprice' (p viết thường) nên Algo Engine không hiểu và âm thầm vứt lệnh đi!
        params.put("triggerPrice", stopPrice);

        // 3. 🔥 MẸO QUANT ĐỂ HIỆN LÊN APP (TAB POSITION TP/SL)
        // Khi muốn cắt lỗ, dùng closePosition=true là chuẩn nhất.
        // Binance quy định: Đã dùng closePosition thì CẤM gửi quantity và reduceOnly lên.
        if (reduceOnly != null && reduceOnly.equals("true")) {
            params.put("closePosition", "true");
        } else {
            if (quantity != null) params.put("quantity", quantity);
            if (reduceOnly != null) params.put("reduceOnly", reduceOnly);
        }

        RestApiRequest<Order> request = createRequest("POST", "/fapi/v1/algoOrder", params, Order.class);

        // 4. 🔥 TỰ ĐỘNG BÙ ĐẮP DỮ LIỆU BỊ THIẾU ĐỂ LOG KHÔNG CÒN NULL
        request.jsonParser = (json) -> {
            Order order = new Order();

            if (json.containKey("algoId")) order.setOrderId(json.getLong("algoId"));
            if (json.containKey("clientAlgoId")) order.setClientOrderId(json.getString("clientAlgoId"));

            // Tự nhét lại các tham số đầu vào để Java theo dõi được trạng thái
            order.setSymbol(symbol);
            order.setSide(side.toString());
            order.setType(orderType.toString());
            order.setStopPrice(new java.math.BigDecimal(stopPrice));

            if (json.containKey("msg") && json.getString("msg").equalsIgnoreCase("success")) {
                order.setStatus("NEW");
            } else if (json.containKey("status")) {
                order.setStatus(json.getString("status"));
            }
            return order;
        };

        return RestApiInvoker.callSync(request);
    }

    // Hàm postOrder thường (vẫn giữ lại cho lệnh Market/Limit thông thường)
    @Override
    public Order postOrder(String symbol, OrderSide side, PositionSide positionSide, OrderType orderType,
                           TimeInForce timeInForce, String quantity, String price, String reduceOnly,
                           String newClientOrderId, String stopPrice, String closePosition, String activationPrice,
                           String callbackRate, WorkingType workingType, String priceProtect, NewOrderRespType newOrderRespType) {

        Map<String, String> params = new TreeMap<>();
        params.put("symbol", symbol);
        params.put("side", side.toString());
        params.put("type", orderType.toString());

        if (quantity != null) params.put("quantity", quantity);
        if (price != null) params.put("price", price);
        if (stopPrice != null) params.put("stopPrice", stopPrice);
        if (reduceOnly != null) params.put("reduceOnly", reduceOnly);
        if (workingType != null) params.put("workingType", workingType.toString());
        if (timeInForce != null) params.put("timeInForce", timeInForce.toString());
        if (newClientOrderId != null) params.put("newClientOrderId", newClientOrderId);
        if (positionSide != null) params.put("positionSide", positionSide.toString());

        RestApiRequest<Order> request = createRequest("POST", "/fapi/v1/order", params, Order.class);
        return RestApiInvoker.callSync(request);
    }


    // --- CÁC HÀM STUB ---
    @Override
    public com.binance.client.model.market.OrderBook getOrderBook(String symbol, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<Trade> getRecentTrades(String symbol, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<Trade> getOldTrades(String symbol, Integer limit, Long fromId) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.AggregateTrade> getAggregateTrades(String symbol, Long fromId, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.Candlestick> getCandlestick(String symbol, CandlestickInterval interval, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.Candlestick> getContinuousCandlesticks(String pair, ContractType contractType, CandlestickInterval interval, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.Candlestick> getIndexPriceCandlesticks(String pair, CandlestickInterval interval, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.Candlestick> getMarkPriceCandlesticks(String pair, CandlestickInterval interval, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.MarkPrice> getMarkPrice(String symbol) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.FundingRate> getFundingRate(String symbol, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.PriceChangeTicker> get24hrTickerPriceChange(String symbol) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.SymbolPrice> getSymbolPriceTicker(String symbol) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.SymbolOrderBook> getSymbolOrderBookTicker(String symbol) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.LiquidationOrder> getLiquidationOrders(String symbol, AutoCloseType type, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<Object> postBatchOrders(String batchOrders) {
        return null;
    }

    @Override
    public Order cancelOrder(String symbol, Long orderId, String origClientOrderId) {
        return null;
    }

    @Override
    public com.binance.client.model.ResponseResult cancelAllOpenOrder(String symbol) {
        return null;
    }

    @Override
    public java.util.List<Object> batchCancelOrders(String symbol, String orderIdList, String origClientOrderIdList) {
        return null;
    }

    @Override
    public com.binance.client.model.ResponseResult changePositionSide(String dual) {
        return null;
    }

    @Override
    public com.binance.client.model.ResponseResult changeMarginType(String symbolName, MarginType marginType) {
        return null;
    }

    @Override
    public com.alibaba.fastjson.JSONObject addIsolatedPositionMargin(String symbolName, int type, String amount, PositionSide positionSide) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.trade.WalletDeltaLog> getPositionMarginHistory(String symbolName, int type, long startTime, long endTime, int limit) {
        return null;
    }

    @Override
    public com.alibaba.fastjson.JSONObject getPositionSide() {
        return null;
    }

    @Override
    public Order getOrder(String symbol, Long orderId, String origClientOrderId) {
        return null;
    }

    @Override
    public Order getOpenOrder(String symbol, Long orderId, String origClientOrderId) {
        return null;
    }

    @Override
    public java.util.List<Order> getOpenOrders(String symbol) {
        return null;
    }

    @Override
    public java.util.List<Order> getAllOrders(String symbol, Long orderId, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.trade.AccountBalance> getBalance() {
        return null;
    }

    @Override
    public com.binance.client.model.trade.AccountInformation getAccountInformation() {
        return null;
    }

    @Override
    public com.binance.client.model.trade.Leverage changeInitialLeverage(String symbol, Integer leverage) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.trade.PositionRisk> getPositionRisk(String symbol) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.trade.MyTrade> getAccountTrades(String symbol, Long startTime, Long endTime, Long fromId, Integer limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.trade.Income> getIncomeHistory(String symbol, IncomeType incomeType, Long startTime, Long endTime, Integer limit) {
        return null;
    }

    @Override
    public String startUserDataStream() {
        return null;
    }

    @Override
    public String keepUserDataStream(String listenKey) {
        return null;
    }

    @Override
    public String closeUserDataStream(String listenKey) {
        return null;
    }

    @Override
    public com.binance.client.model.market.OpenInterest getOpenInterest(String symbol) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.OpenInterestStat> getOpenInterestStat(String symbol, PeriodType period, Long startTime, Long endTime, Long limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.CommonLongShortRatio> getTopTraderAccountRatio(String symbol, PeriodType period, Long startTime, Long endTime, Long limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.CommonLongShortRatio> getTopTraderPositionRatio(String symbol, PeriodType period, Long startTime, Long endTime, Long limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.CommonLongShortRatio> getGlobalAccountRatio(String symbol, PeriodType period, Long startTime, Long endTime, Long limit) {
        return null;
    }

    @Override
    public java.util.List<com.binance.client.model.market.TakerLongShortStat> getTakerLongShortRatio(String symbol, PeriodType period, Long startTime, Long endTime, Long limit) {
        return null;
    }

    @Override
    public com.alibaba.fastjson.JSONObject autoCancelAllOrders(String symbol, Long countdownTime) {
        return null;
    }


    @Override
    public List<Order> getOpenAlgoOrders(String symbol) {
        // 1. Chuẩn bị tham số
        Map<String, String> params = new TreeMap<>();
        if (symbol != null) {
            params.put("symbol", symbol);
        }
        params.put("algoType", "CONDITIONAL"); // Bắt buộc
        params.put("timestamp", String.valueOf(System.currentTimeMillis()));
        params.put("recvWindow", "10000");

        // 2. Tạo Query String & Signature
        StringBuilder queryString = new StringBuilder();
        for (Map.Entry<String, String> entry : params.entrySet()) {
            if (queryString.length() > 0) queryString.append("&");
            queryString.append(entry.getKey()).append("=").append(entry.getValue());
        }
        String signature = SignatureGenerator.getSignature(queryString.toString(), secretKey);

        // --- FIX 1: Endpoint chuẩn theo tài liệu là /fapi/v1/openAlgoOrders ---
        String fullUrl = BASE_URL + "/fapi/v1/openAlgoOrders?" + queryString.toString() + "&signature=" + signature;

        // 3. Tạo Request
        OkHttpClient client = new OkHttpClient();
        Request request = new Request.Builder()
                .url(fullUrl)
                .addHeader("X-MBX-APIKEY", apiKey)
                .addHeader("Content-Type", "application/json")
                .get()
                .build();

        try {
            // 4. Gọi API
            String response = client.newCall(request).execute().body().string();
            // System.out.println("ALGO ORDERS JSON: " + response); // Debug xem JSON trả về

            // --- FIX 2: Parse Mảng JSON trực tiếp (Root Array) ---
            List<Order> orderList = new LinkedList<>();

            // Kiểm tra nếu response bắt đầu bằng '[' tức là mảng
            if (response.trim().startsWith("[")) {
                com.alibaba.fastjson.JSONArray array = com.alibaba.fastjson.JSON.parseArray(response);

                for (int i = 0; i < array.size(); i++) {
                    com.alibaba.fastjson.JSONObject obj = array.getJSONObject(i);
                    Order order = new Order();

                    // Map các trường theo tài liệu mới
                    // Lưu ý: ID của Algo Order là "algoId", không phải "orderId"
                    if (obj.containsKey("algoId")) order.setOrderId(obj.getLong("algoId"));
                    if (obj.containsKey("symbol")) order.setSymbol(obj.getString("symbol"));

                    // Lấy Trigger Price (Stop Price)
                    if (obj.containsKey("triggerPrice")) order.setStopPrice(obj.getBigDecimal("triggerPrice"));
                        // Hoặc fallback sang stopPrice cũ nếu có
                    else if (obj.containsKey("stopPrice")) order.setStopPrice(obj.getBigDecimal("stopPrice"));

                    if (obj.containsKey("side")) order.setSide(obj.getString("side"));
                    if (obj.containsKey("orderType")) order.setType(obj.getString("orderType")); // Ví dụ: TAKE_PROFIT
                    if (obj.containsKey("reduceOnly")) order.setReduceOnly(obj.getBoolean("reduceOnly"));
                    if (obj.containsKey("clientAlgoId")) order.setClientOrderId(obj.getString("clientAlgoId"));

                    // Map thêm status
                    if (obj.containsKey("algoStatus")) order.setStatus(obj.getString("algoStatus"));

                    orderList.add(order);
                }
            } else {
                // Trường hợp API trả về lỗi hoặc Object rỗng
                // System.err.println("Response is not an array: " + response);
            }
            return orderList;

        } catch (Exception e) {
            e.printStackTrace();
        }
        return new LinkedList<>();
    }
    // File: com/binance/client/impl/SyncRequestImpl.java

    @Override
    public Order cancelAlgoOrder(Long algoId, String clientAlgoId) {
        // 1. Chuẩn bị tham số
        Map<String, String> params = new TreeMap<>();
        if (algoId != null) {
            params.put("algoId", algoId.toString());
        }
        if (clientAlgoId != null) {
            params.put("clientAlgoId", clientAlgoId);
        }
        params.put("timestamp", String.valueOf(System.currentTimeMillis()));
        params.put("recvWindow", "10000");

        // 2. Gọi hàm tạo Request (Method DELETE)
        // Endpoint chuẩn: /fapi/v1/algoOrder
        RestApiRequest<Order> request = createRequest("DELETE", "/fapi/v1/algoOrder", params, Order.class);

        // 3. Cập nhật lại Parser riêng cho hàm hủy này (Vì cấu trúc trả về hơi khác)
        request.jsonParser = (JsonWrapper json) -> {
            Order order = new Order();
            // Response mẫu: {"algoId": 2146760, "clientAlgoId": "...", "code": "200", "msg": "success"}
            if (json.containKey("algoId")) {
                order.setOrderId(json.getLong("algoId")); // Map algoId -> orderId
            }
            if (json.containKey("clientAlgoId")) {
                order.setClientOrderId(json.getString("clientAlgoId"));
            }
            if (json.containKey("msg")) {
                order.setStatus(json.getString("msg")); // Lưu message success vào status
            }
            return order;
        };

        return RestApiInvoker.callSync(request);
    }
}