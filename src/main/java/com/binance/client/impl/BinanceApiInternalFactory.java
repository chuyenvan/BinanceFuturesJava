package com.binance.client.impl;

import com.binance.chuyennd.config.PrivateConfig;
import com.binance.client.RequestOptions;
import com.binance.client.SubscriptionClient;
import com.binance.client.SubscriptionOptions;
import com.binance.client.SyncRequestClient;

import java.net.URI;

public final class BinanceApiInternalFactory {

    private static final BinanceApiInternalFactory instance = new BinanceApiInternalFactory();

    public static BinanceApiInternalFactory getInstance() {
        return instance;
    }

    private BinanceApiInternalFactory() {
    }

    public SyncRequestClient createSyncRequestClient(String apiKey, String secretKey, RequestOptions options) {
        RequestOptions requestOptions = new RequestOptions(options);
        return new SyncRequestImpl(apiKey, secretKey, requestOptions);
    }

    public SubscriptionClient createSubscriptionClient(SubscriptionOptions options) {
        SubscriptionOptions subscriptionOptions = new SubscriptionOptions(options);
        RequestOptions requestOptions = new RequestOptions();
        try {
            String host = new URI(options.getUri()).getHost();
            requestOptions.setUrl("https://" + host);
        } catch (Exception e) {

        }
        SubscriptionClient webSocketStreamClient = new WebSocketStreamClientImpl(subscriptionOptions);
        return webSocketStreamClient;
    }

}
