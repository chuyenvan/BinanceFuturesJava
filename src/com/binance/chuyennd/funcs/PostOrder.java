/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.funcs;

import com.binance.chuyennd.utils.Utils;
import com.binance.client.RequestOptions;
import com.binance.client.SubscriptionClient;
import com.binance.client.SyncRequestClient;
import com.binance.client.examples.constants.PrivateConfig;
import com.binance.client.model.enums.MarginType;
import com.binance.client.model.enums.NewOrderRespType;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.enums.OrderType;
import com.binance.client.model.enums.TimeInForce;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class PostOrder {

    public static final Logger LOG = LoggerFactory.getLogger(PostOrder.class);
    static int INCREASE_MARGIN_TYPE = 1;
    static int DECREASE_MARGIN_TYPE = 2;

    public static void main(String[] args) {

//        System.out.println(ClientSingleton.getInstance().syncRequestClient.changeMarginType("BTCUSDT", MarginType.ISOLATED));
                RequestOptions options = new RequestOptions();
                SyncRequestClient syncRequestClient = SyncRequestClient.create(PrivateConfig.API_KEY, PrivateConfig.SECRET_KEY,
                        options);
                System.out.println(syncRequestClient.getOpenOrders("ETHUSDT"));
        //        System.out.println(syncRequestClient.getOpenOrders("FRONTUSDT"));
        //        System.out.println(syncRequestClient.getPositionRisk("STORJUSDT"));
        ////        System.out.println(syncRequestClient.getPositionRisk("BTCUSDT"));
        //        System.out.println(syncRequestClient.getOrderBook("BTCUSDT", 100));
        //receiveUserData();
        //        String symbol = "BTCUSDT";
        //        Double quantity = 0.001;
        //        Double price = 27000.0;
        //        Double stopPrice = 26000.0;
        //        newOrder(symbol, OrderSide.BUY, quantity, price);
        //        setStopLossOrTakeProfit(symbol, OrderSide.SELL, quantity.toString(), stopPrice.toString());
        //        System.out.println(syncRequestClient.postOrder("BTCUSDT", OrderSide.SELL, PositionSide.BOTH, OrderType.LIMIT, TimeInForce.GTC,
        //                "1", "1", null, null, null, null));
        // place dual position side order.
        // Switch between dual or both position side, call: com.binance.client.examples.trade.ChangePositionSide
        //        newOrder("TOMOUSDT", OrderSide.BUY, 141.555062898212421, 1.37409231);
        //        newOrder("TRBUSDT", OrderSide.BUY, 04.415025445688392, 48.18981633);
        //        takeProfit("BTCUSDT", OrderSide.SELL, "0.001", "27000");
        //        stopLoss("BTCUSDT", OrderSide.SELL, "0.001", "27000");
        //        System.out.println(Utils.normalQuantity2Api(34521.4464486062));
        //        closePosition("MAGICUSDT", OrderSide.BUY, 735.0556434365623);
        //
    }

    private static void closePosition(String symbol, OrderSide orderSide, Double quantity) {
        OrderSide orderSideClose = OrderSide.BUY;
        if (orderSide.equals(OrderSide.BUY)) {
            orderSideClose = OrderSide.SELL;
        }
        System.out.println(ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, orderSideClose, null, OrderType.LIMIT, null,
                Utils.normalQuantity2Api(quantity), null, null, null, null, null, null, null, null, null, NewOrderRespType.RESULT));

    }

    private static void newOrder(String symbol, OrderSide orderSide, Double quantity, Double price, Integer leverage) {
        System.out.println(Utils.normalQuantity2Api(quantity) + " " + Utils.normalPrice2Api(price));
        ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, leverage);
        System.out.println(ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, orderSide, null, OrderType.LIMIT, TimeInForce.GTC,
                Utils.normalQuantity2Api(quantity), Utils.normalPrice2Api(price), null, null, null, null, null, null, null, null, NewOrderRespType.RESULT));

    }

    private static void takeProfit(String symbol, OrderSide side, String quantity, String stopPrice) {
        ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.TAKE_PROFIT, TimeInForce.GTC,
                quantity, stopPrice, null, null, stopPrice, null, null, null, null, null, NewOrderRespType.RESULT);
    }

    private static void stopLoss(String symbol, OrderSide side, String quantity, String stopPrice) {
        ClientSingleton.getInstance().syncRequestClient.postOrder(symbol, side, null, OrderType.STOP_MARKET, TimeInForce.GTC,
                quantity, null, null, null, stopPrice, null, null, null, null, null, NewOrderRespType.RESULT);
    }

    private static void receiveUserData() {
        RequestOptions options = new RequestOptions();
        SyncRequestClient syncRequestClient = SyncRequestClient.create(PrivateConfig.API_KEY, PrivateConfig.SECRET_KEY,
                options);

        // Start user data stream
        String listenKey = syncRequestClient.startUserDataStream();
        System.out.println("listenKey: " + listenKey);

        // Keep user data stream
//        syncRequestClient.keepUserDataStream(listenKey);
        // Close user data stream
//        syncRequestClient.closeUserDataStream(listenKey);
        SubscriptionClient client = SubscriptionClient.create();

        client.subscribeUserDataEvent(listenKey, ((event) -> {
            System.out.println(event);
        }), null);

    }

}
