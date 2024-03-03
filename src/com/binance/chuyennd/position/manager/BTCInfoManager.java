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
package com.binance.chuyennd.position.manager;

import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendObject;
import com.binance.chuyennd.object.TrendObjectDetail;
import com.binance.chuyennd.object.TrendState;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import java.util.List;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BTCInfoManager {

    public static final Logger LOG = LoggerFactory.getLogger(BTCInfoManager.class);

    private Double MAX_PRICE = null;
    private Double MIN_PRICE = null;
    private final Integer NUMBER_DAY_CHECK_TREND = 60;
    private OrderSide trendSide = null;

    public static OrderSide getLongTrendBtc() {
        try {
            String trend = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_SYMBOL_TREND, Constants.SYMBOL_PAIR_BTC);
            if (StringUtils.equals(trend, OrderSide.BUY.toString())) {
                return OrderSide.BUY;
            }
            if (StringUtils.equals(trend, OrderSide.SELL.toString())) {
                return OrderSide.SELL;
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null;
    }

    private void updateTrendWithPrice(Double currentPirce) {
        double totalChange = MAX_PRICE - MIN_PRICE;
        double currentChange = MAX_PRICE - currentPirce;
        double rateChange = (totalChange - currentChange) / totalChange;
        trendSide = null;
        if (rateChange <= 0.3) {
            trendSide = OrderSide.SELL;
        }
        if (rateChange >= 0.7) {
            trendSide = OrderSide.BUY;
        }
        LOG.info("Current price: {} max: {} min: {} trend: {}", currentPirce, MAX_PRICE, MIN_PRICE, trendSide);
        String trendSideStr = "";
        if (trendSide != null) {
            trendSideStr = trendSide.toString();
        }
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_SYMBOL_TREND, Constants.SYMBOL_PAIR_BTC, trendSideStr);
    }

    private void updateTrendWithPriceNew() {
        try {
            // if BTC by day > 5% -> trend ưith day else trend with chart day
            KlineObjectNumber ticker = TickerFuturesHelper.getLastTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1D);
            String trendSideStr = "BUY";
            if (Math.abs(Utils.rateOf2Double(ticker.minPrice, ticker.maxPrice)) > 0.05) {
                if (ticker.priceClose < ticker.priceOpen) {
                    trendSideStr = "SELL";
                }
                LOG.info("Open: {} Close: {} current:{} trend: {}", ticker.priceOpen,
                        ticker.priceClose, ClientSingleton.getInstance().getCurrentPrice(Constants.SYMBOL_PAIR_BTC), trendSideStr);
            } else {
                List<TrendObject> trends = TickerFuturesHelper.extractTopBottomObjectInTicker(TickerFuturesHelper.getTicker(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1D), 0.01);
                List<TrendObjectDetail> trendDetails = TickerFuturesHelper.detectTrendByKline(trends, 0.02);

                for (int i = 0; i < trendDetails.size(); i++) {
                    TrendObjectDetail trend = trendDetails.get(trendDetails.size() - i - 1);
                    if (!trend.status.equals(TrendState.SIDEWAY)) {
                        if (trend.status.equals(TrendState.TREND_DOWN)) {
                            trendSideStr = "SELL";
                        }
                        break;
                    }
                }
                LOG.info("Open: {} Close: {} current:{} trend: {}", trends.get(trends.size() - 1).getKline().priceOpen,
                        trends.get(trends.size() - 1).getKline().priceClose, ClientSingleton.getInstance().getCurrentPrice(Constants.SYMBOL_PAIR_BTC), trendSideStr);
            }
            RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_SYMBOL_TREND, Constants.SYMBOL_PAIR_BTC, trendSideStr);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void startThreadUpdateTrend() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateTrend");
            LOG.info("Start ThreadUpdateTrend BTC!");
            while (true) {
                try {
                    updateTrendWithPriceNew();
                    Thread.sleep(2 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadUpdateTrend: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public static void main(String[] args) {
//        for (int i = 0; i < 10; i++) {
//            Double currentPrice = BTCInfoManager.getInstance().MIN_PRICE + i * (BTCInfoManager.getInstance().MAX_PRICE - BTCInfoManager.getInstance().MIN_PRICE) / 10;
//            BTCInfoManager.getInstance().updateTrendWithPrice(currentPrice);
//        }
new BTCInfoManager().startThreadUpdateTrend();
//        System.out.println(BTCInfoManager.getLongTrendBtc());
    }
}
