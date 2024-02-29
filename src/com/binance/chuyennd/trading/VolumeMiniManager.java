/*
 * Copyright 2024 pc.
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
package com.binance.chuyennd.trading;

import com.educa.mail.funcs.BreadFunctions;
import com.binance.chuyennd.bigchange.btctd.BreadDetectObject;
import com.binance.chuyennd.funcs.ClientSingleton;
import com.binance.chuyennd.funcs.PriceManager;
import com.binance.chuyennd.funcs.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import java.util.Date;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class VolumeMiniManager {

    public static final Logger LOG = LoggerFactory.getLogger(VolumeMiniManager.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public Set<? extends String> allSymbol;
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public Double VOLUME_MINI = Configs.getDouble("VOLUME_MINI");
    public Double RATE_CHANGE_MIN_2TRADING = Configs.getDouble("RATE_CHANGE_MIN_2TRADING");
    public Double RATE_TARGET_VOLUME_MINI = Configs.getDouble("RATE_TARGET_VOLUME_MINI");    

    public static void main(String[] args) throws InterruptedException {

//        new VolumeMiniManager().detectBySymbol("BTCUSDT");
//        LOG.info("Done check!");
//        new VolumeMiniManager().fixbug();
//        new VolumeMiniManager().testFunction();
//        new VolumeMiniManager().buildReport();
    }

    public void start() throws InterruptedException {
        initData();
        startThreadAltDetectBigChangeAndVolumeMini();       
    }

      

    public void startThreadAltDetectBigChangeAndVolumeMini() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadAltDetectBigChangeVolumeMini");
            LOG.info("Start thread ThreadAltDetectBigChangeVolumeMini rate:{} volume max:{} target: {}",
                    RATE_CHANGE_MIN_2TRADING, VOLUME_MINI, RATE_TARGET_VOLUME_MINI);
            while (true) {                

                if (isTimeTrade() && BudgetManager.getInstance().getBudget() > 0) {
                    try {
                        LOG.info("Start detect symbol is volume mini! {}", new Date());
                        for (String symbol : allSymbol) {
                            executorService.execute(() -> detectBySymbol(symbol));
                        }
                    } catch (Exception e) {
                        LOG.error("ERROR during ThreadAltDetectBigChangeVolumeMini: {}", e);
                        e.printStackTrace();
                    }
                }
                try {
                    Thread.sleep(Utils.TIME_SECOND);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(VolumeMiniManager.class.getName()).log(Level.SEVERE, null, ex);
                }

            }
        }).start();
    }

   

    public boolean isTimeTrade() {
        return Utils.getCurrentMinute() % 15 == 14 && Utils.getCurrentSecond() == 57;
    }

    private void initData() throws InterruptedException {
        allSymbol = TickerFuturesHelper.getAllSymbol();
        allSymbol.removeAll(Constants.specialSymbol);
        ClientSingleton.getInstance();
        PriceManager.getInstance();        
    }

    private void detectBySymbol(String symbol) {
        try {
            KlineObjectNumber ticker = TickerFuturesHelper.getLastTicker(symbol, Constants.INTERVAL_15M);
            if (ticker == null) {
                return;
            }
            BreadDetectObject breadData = BreadFunctions.calBreadDataAlt(ticker, RATE_BREAD_MIN_2TRADE);
            if (breadData.orderSide != null
                    && breadData.orderSide.equals(OrderSide.BUY)
                    && PriceManager.getInstance().isAvalible2Trade(symbol, ticker.minPrice, breadData.orderSide)
                    && breadData.totalRate >= RATE_CHANGE_MIN_2TRADING
                    && ticker.totalUsdt <= VOLUME_MINI * 1000000) {
                LOG.info("Big:{} {} {} rate:{} volume: {}", symbol, new Date(ticker.startTime.longValue()),
                        breadData.orderSide, breadData.totalRate, ticker.totalUsdt);

                Double priceEntry = ticker.priceClose;
                Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, breadData.orderSide, RATE_TARGET_VOLUME_MINI);
                Double quantity = Utils.calQuantity(BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().getLeverage(), priceEntry, symbol);
                if (quantity != null && quantity != 0) {
                    OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                            priceTarget, quantity, BudgetManager.getInstance().getLeverage(), symbol, ticker.startTime.longValue(),
                            ticker.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_VOLUME_MINI);
                    RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
                } else {
                    LOG.info("{} {} quantity false", symbol, quantity);
                }
            }
        } catch (Exception e) {
            LOG.info("Error detect bvm:{}", symbol);
            e.printStackTrace();
        }
    } 

}
