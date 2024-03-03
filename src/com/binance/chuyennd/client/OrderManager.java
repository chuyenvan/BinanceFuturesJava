/*
/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.client;

import com.binance.chuyennd.object.OrderInfo;
import com.binance.chuyennd.object.PremiumIndex;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.NewOrderRespType;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.trade.Order;
import java.io.File;
import java.util.Date;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class OrderManager {

    public static final Logger LOG = LoggerFactory.getLogger(OrderManager.class);
    public ConcurrentHashMap<String, OrderInfo> allOrder;
    private final String FILE_PATH_ORDER_DATA = "storage/symboldata/order.data";
    private final Integer RATE_LEVEGARE = 5;
    private Double PERCENT_STOP;
    private static volatile OrderManager INSTANCE = null;

    public static OrderManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new OrderManager();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        PERCENT_STOP = Configs.getDouble("PercentStop");
        if (new File(FILE_PATH_ORDER_DATA).exists()) {
            this.allOrder = (ConcurrentHashMap<String, OrderInfo>) Storage.readObjectFromFile(FILE_PATH_ORDER_DATA);
        } else {
            allOrder = new ConcurrentHashMap<>();
        }
    }

    public void startThreadManagerOrder(Map<String, PremiumIndex> currentTickers) {
        if (hadOrderNeedProcess()) {
            new Thread(() -> {
                Thread.currentThread().setName("ThreadProcessAllOrderActive");
                LOG.info("Start thread process all order active: {}", new Date());
                try {
                    for (Map.Entry<String, OrderInfo> entry : allOrder.entrySet()) {
                        OrderInfo val = entry.getValue();
                        if (!val.status.equals(OrderStatusProcess.FINISHED)) {
                            // get price
                            PremiumIndex currentTicker = currentTickers.get(val.symbol);
                            if (currentTicker != null) {
                                if (val.priceBest == null) {
                                    val.priceBest = Double.valueOf(currentTicker.markPrice);
                                }
                                if (val.orderSide.equals(OrderSide.BUY)) {
                                    if (Double.valueOf(currentTicker.markPrice) > val.priceBest) {
                                        val.priceBest = Double.valueOf(currentTicker.markPrice);
                                    } else {
                                        checkAndCloseOrder(val, Double.valueOf(currentTicker.markPrice));
                                    }
                                }
                            }
                        }
                    }
                    Storage.writeObject2File(FILE_PATH_ORDER_DATA, allOrder);
                    Thread.sleep(30 * Utils.TIME_SECOND);
                } catch (Exception e) {
                    LOG.error("ERROR during process order active: {}", e);
                    e.printStackTrace();
                }

            }).start();
        }
    }

    public OrderInfo addNewOrder(String symbol, OrderSide side, Double bubget, Double price) {
        if (allOrder.contains(symbol)) {
            OrderInfo orderInfo = allOrder.get(symbol);
            if (!orderInfo.status.equals(OrderStatusProcess.FINISHED)) {
                LOG.info("Symbol {} had order!", symbol);
                return null;
            } else {
                allOrder.remove(symbol);
            }
        }
        if (totalOrderNewProcess() >= 10) {
            LOG.info("Total order new maximum!", totalOrderNewProcess());
            return null;
        }
        OrderInfo info = new OrderInfo();
        info.symbol = symbol;
        info.orderSide = side;
        info.quantity = bubget * RATE_LEVEGARE / price;
        info.priceEntry = price;
        info.status = OrderStatusProcess.REQUEST;
        info.timeCreated = System.currentTimeMillis();
        try {
            Order respon = createOrder(info);
            if (respon != null) {
                info.status = OrderStatusProcess.NEW;
                info.orderId = respon.getOrderId();
                info.priceEntry = respon.getAvgPrice().doubleValue();
                LOG.info("Create new Order: {}", Utils.gson.toJson(info));
                Utils.sendSms2Telegram("Create new order: " + Utils.gson.toJson(info));
            }
        } catch (Exception e) {
            LOG.info("Error during add order 2 queue manager: {}", Utils.gson.toJson(info));
            e.printStackTrace();
        }
        allOrder.put(symbol, info);
        return info;
    }

    private Order createOrder(OrderInfo info) {
        ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(info.symbol, RATE_LEVEGARE);
        return ClientSingleton.getInstance().syncRequestClient.postOrder(info.symbol, info.orderSide, null, OrderType.MARKET, null,
                info.quantity.toString(), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
    }

    private void closePosition(OrderInfo info) {
        OrderSide orderSideClose = OrderSide.BUY;
        if (info.orderSide.equals(OrderSide.BUY)) {
            orderSideClose = OrderSide.SELL;
        }
        Order respon = ClientSingleton.getInstance().syncRequestClient.postOrder(info.symbol, orderSideClose, null, OrderType.MARKET, null,
                info.quantity.toString(), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT);
        LOG.info("Close order respon: {}", Utils.gson.toJson(respon));
    }

    private int totalOrderNewProcess() {
        Integer counter = 0;
        for (Map.Entry<String, OrderInfo> entry : allOrder.entrySet()) {
            OrderInfo val = entry.getValue();
            if (val.status.equals(OrderStatusProcess.NEW)) {
                counter++;
            }
        }
        return counter;
    }

    private boolean hadOrderNeedProcess() {
        Integer counter = 0;
        for (Map.Entry<String, OrderInfo> entry : allOrder.entrySet()) {
            OrderInfo val = entry.getValue();
            if (!val.status.equals(OrderStatusProcess.FINISHED)) {
                counter++;
            }
        }
        return counter > 0;
    }

    private void checkAndCloseOrder(OrderInfo val, Double currentPrice) {
        // check có lãi mới stop
        boolean isProfitGT0 = false;
        if (val.orderSide.equals(OrderSide.BUY)) {
            isProfitGT0 = val.priceEntry < currentPrice;
        } else {
            isProfitGT0 = val.priceEntry > currentPrice;
        }
        if (isProfitGT0 && Math.abs(val.priceBest - currentPrice) * 100 / val.priceBest > PERCENT_STOP) {
            LOG.info("Stop Order: {} priceStop: {} isProfitGT0:{}", Utils.gson.toJson(val), currentPrice, isProfitGT0);
            closePosition(val);
            val.status = OrderStatusProcess.FINISHED;
            allOrder.put(val.symbol, val);
        }
    }

    public static void main(String[] args) {
        OrderManager.getInstance().closePosition(OrderManager.getInstance().allOrder.get("DODOXUSDT"));
    }
}
