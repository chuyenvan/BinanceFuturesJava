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
package com.binance.chuyennd.bigchange.btctd;

import com.binance.chuyennd.funcs.TickerHelper;
import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.SubscriptionClient;
import com.binance.client.model.enums.CandlestickInterval;
import com.binance.client.model.enums.OrderSide;
import com.binance.client.model.event.CandlestickEvent;
import java.util.Collection;
import java.util.Date;
import java.util.concurrent.atomic.AtomicBoolean;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BtcBreadBigChange2T {

    public static final Logger LOG = LoggerFactory.getLogger(BtcBreadBigChange2T.class);
    public Double RATE_2TRADING = Configs.getDouble("Rate2Trading");
    public Double BTC_BREAD_BIGCHANE = Configs.getDouble("BTCBreadBigChange");
    public AtomicBoolean isTrading = new AtomicBoolean(false);

    public static void main(String[] args) {
        new BtcBreadBigChange2T().startThreadDetectBreadBigChange2Trade();
//        new BtcBreadBigChange2T().startThreadTradingAlt(OrderSide.BUY);
    }

    public void startThreadDetectBreadBigChange2Trade() {
        SubscriptionClient client = SubscriptionClient.create();
        client.subscribeCandlestickEvent("btcusdt", CandlestickInterval.ONE_MINUTE, ((event) -> {
//            Long startTime = System.currentTimeMillis();
            process(event);
//            Long endTime = System.currentTimeMillis();
//            LOG.info("{} {}", startTime - event.getEventTime(), endTime - startTime);

        }), null);
    }

    private void process(CandlestickEvent event) {
        try {
            Double beardAbove = 0d;
            Double beardBelow = 0d;
            Double rateChange = null;

            if (event.getClose().doubleValue() > event.getOpen().doubleValue()) {
                beardAbove = event.getHigh().doubleValue() - event.getClose().doubleValue();
                beardBelow = event.getOpen().doubleValue() - event.getLow().doubleValue();
                rateChange = Utils.rateOf2Double(event.getClose().doubleValue(), event.getOpen().doubleValue());
            } else {
                beardAbove = event.getHigh().doubleValue() - event.getOpen().doubleValue();
                beardBelow = event.getClose().doubleValue() - event.getLow().doubleValue();
                rateChange = Utils.rateOf2Double(event.getOpen().doubleValue(), event.getClose().doubleValue());
            }
            double rateChangeAbove = beardAbove / event.getLow().doubleValue();
            double rateChangeBelow = beardBelow / event.getLow().doubleValue();
            OrderSide side = null;
            if (rateChangeAbove > BTC_BREAD_BIGCHANE) {
                LOG.info("bread above: {} {}", rateChangeAbove, new Date());
                side = OrderSide.SELL;
            } else {
                if (rateChangeBelow > BTC_BREAD_BIGCHANE) {
                    side = OrderSide.BUY;
                    LOG.info("bread below: {} {}", rateChangeBelow, new Date());
                }
            }
//            LOG.info("{} {} bread above:{} bread below:{} rateChange:{}", new Date(event.getStartTime()), side, rateChangeAbove, rateChangeBelow, rateChange);
            if (side != null && rateChange >= RATE_2TRADING && !isTrading.get()) {
                LOG.info("{} {} bread above:{} bread below:{} rateChange:{}", new Date(event.getStartTime()), side, rateChangeAbove, rateChangeBelow, rateChange);
                isTrading.set(true);
                startThreadTradingAlt(side);
            }

        } catch (Exception e) {
        }

    }

    public void startThreadTradingAlt(OrderSide orderSide) {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadTradingAltBreadBtcBigChan");
            LOG.info("Start ThreadTradingAltBreadBtcBigChan !");
            try {
                Collection<? extends String> allSymbol = TickerHelper.getAllSymbol();
                for (String symbol : allSymbol) {
                    boolean result = PositionHelper.getInstance().addOrderByTarget(symbol, orderSide);
                    if (!result) {
                        LOG.info("Break because balance not enough!");
                        break;
                    }
                }
                isTrading.set(false);
            } catch (Exception e) {
                LOG.error("ERROR during ThreadTradingAltBreadBtcBigChan: {}", e);
                e.printStackTrace();
            }

        }).start();
    }

}
