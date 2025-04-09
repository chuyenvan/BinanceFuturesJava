package com.binance.chuyennd.client;

import com.binance.client.RequestOptions;
import com.binance.client.SubscriptionClient;
import com.binance.client.SyncRequestClient;
import com.binance.client.examples.constants.PrivateConfig;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.market.Candlestick;

import java.net.URI;
import java.net.URISyntaxException;


public class CandleStream {
    public static void main(String[] args) {
        startCandlestickEventStreaming();
    }
    public static void startCandlestickEventStreaming() {
        try {
            // open websocket
//            final WebsocketClientEndpoint clientEndPoint = new WebsocketClientEndpoint(new URI("wss://stream.binance.com:9443/ws/btcusdt@kline_1m"));
            final WebsocketClientEndpoint clientEndPoint = new WebsocketClientEndpoint(new URI("wss://data-stream.binance.vision/stream?streams=btcusdt@trade&timeUnit=MICROSECOND"));

            // add listener
            clientEndPoint.addMessageHandler(new WebsocketClientEndpoint.MessageHandler() {
                public void handleMessage(String message) {
                    System.out.println(message);
                }
            });

            // send message to websocket
            clientEndPoint.sendMessage("{'event':'addChannel','channel':'ok_btccny_ticker'}");

            // wait 5 seconds for messages from websocket
            Thread.sleep(5000);

        } catch (InterruptedException ex) {
            System.err.println("InterruptedException exception: " + ex.getMessage());
        } catch (URISyntaxException ex) {
            System.err.println("URISyntaxException exception: " + ex.getMessage());
        }
    }
}
