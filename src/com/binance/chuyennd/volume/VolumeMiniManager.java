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
package com.binance.chuyennd.volume;

import com.binance.chuyennd.bigchange.statistic.BreadDetectObject;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.indicators.SimpleMovingAverage;
import com.binance.chuyennd.indicators.SimpleMovingAverage1DManager;
import com.binance.chuyennd.movingaverage.MAStatus;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.signal.tradingview.SymbolTradingManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import com.educa.chuyennd.funcs.BreadProductFunctions;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.Date;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.logging.Level;

/**
 * @author pc
 */
public class VolumeMiniManager {

    public static final Logger LOG = LoggerFactory.getLogger(VolumeMiniManager.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(Configs.getInt("NUMBER_THREAD_ORDER_MANAGER"));
    public Set<? extends String> allSymbol;
    public final Double RATE_MA_MAX = Configs.getDouble("RATE_MA_MAX");
    public Double RATE_BREAD_MIN_2TRADE = Configs.getDouble("RATE_BREAD_MIN_2TRADE");
    public Double RATE_TARGET = Configs.getDouble("RATE_TARGET");


    public static void main(String[] args) throws InterruptedException, ParseException {
//        prinAllTop();
        Long time = Utils.sdfFileHour.parse("20240508 13:00").getTime();
//        new VolumeMiniManager().detectBySymbolTest("RLCUSDT", time);
        new VolumeMiniManager().detectBySymbol("QNTUSDT");
        System.out.println("Finish Detect!");
//        LOG.info("Done check!");
//        new VolumeMiniManager().fixbug();
//        new VolumeMiniManager().testFunction();
//        new VolumeMiniManager().buildReport();
    }

    private static void prinAllTop() {
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
            MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(System.currentTimeMillis(), symbol);
            if (maStatus != null && maStatus.equals(MAStatus.TOP)){
                LOG.info("TOP: {} {}",symbol, SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, System.currentTimeMillis()));
            }
        }
    }

    public void start() throws InterruptedException, ParseException {
        initData();
        startThreadAltDetectBigChangeAndVolumeMini();
    }

    public void startThreadAltDetectBigChangeAndVolumeMini() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadAltDetectBigChangeVolumeMini");
            LOG.info("Start thread ThreadAltDetectBigChangeVolumeMini  target: {}", RATE_TARGET);
            while (true) {

                if (isTimeTrade() && BudgetManager.getInstance().getBudget() > 0) {
                    try {
                        LOG.info("Start detect symbol is volume mini! {}", new Date());
//                        Set<String> symbols2Detect = getAllSymbolVolumeOverVolume2Trade();
//                        symbols2Detect.removeAll(Constants.specialSymbol);
                        for (String symbol : SymbolTradingManager.getInstance().getAllSymbol2TradingVolumeMini()) {
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

    private void initData() throws InterruptedException, ParseException {

        allSymbol = TickerFuturesHelper.getAllSymbol();
        allSymbol.removeAll(Constants.diedSymbol);
        SimpleMovingAverage1DManager.getInstance();
        ClientSingleton.getInstance();
    }
    private void detectBySymbolTest(String symbol, Long time) {
        try {
            KlineObjectNumber ticker = TickerFuturesHelper.getTickersByTime(symbol, Constants.INTERVAL_15M, time);
            BreadDetectObject breadData = BreadProductFunctions.calBreadDataAlt(ticker, RATE_BREAD_MIN_2TRADE);

            MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(Utils.getDate(ticker.startTime.longValue()), symbol);
            Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(ticker.startTime.longValue()));
            Double rateMa = Utils.rateOf2Double(ticker.priceClose, maValue);
            Double rateChange = BreadProductFunctions.getRateChangeWithVolume(ticker.totalUsdt / 1000000);

            if (rateChange == null) {
                LOG.info("Error rateChange with ticker: {} {}", symbol, Utils.toJson(ticker));
                return;
            }
            if (breadData.orderSide != null
                    && breadData.orderSide.equals(OrderSide.BUY)
                    && maStatus != null && maStatus.equals(MAStatus.TOP)
//                    && btcMaStatus != null && !btcMaStatus.equals(MAStatus.UNDER)
                    && rateMa <= RATE_MA_MAX
                    && breadData.totalRate >= rateChange) {
                // end new

                LOG.info("Big:{} {} {} rate:{} volume: {}", symbol, new Date(ticker.startTime.longValue()),
                        breadData.orderSide, breadData.totalRate, ticker.totalUsdt);

                Double priceEntry = ticker.priceClose;
                Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, breadData.orderSide, RATE_TARGET);
                Double quantity = Utils.calQuantity(BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().getLeverage(symbol), priceEntry, symbol);
                if (quantity != null && quantity != 0) {
                    OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, ticker.priceClose,
                            priceTarget, quantity, BudgetManager.getInstance().getLeverage(symbol), symbol, ticker.startTime.longValue(),
                            ticker.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_VOLUME_MINI);
//                    RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
                } else {
                    LOG.info("{} {} quantity false", symbol, quantity);
                }
            }
        } catch (Exception e) {
            LOG.info("Error detect bvm:{}", symbol);
            e.printStackTrace();
        }
    }
    private void detectBySymbol(String symbol) {
        try {
            List<KlineObjectNumber> tickers = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_15M);
            IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(tickers, 20);
            KlineObjectNumber lastTicker = tickers.get(tickers.size() - 1);
            Double rateSma20 = Utils.rateOf2Double(lastTicker.priceClose, smaEntries[smaEntries.length - 1].getValue()) ;

//            KlineObjectNumber ticker = TickerFuturesHelper.getLastTicker(symbol, Constants.INTERVAL_15M);
            BreadDetectObject breadData = BreadProductFunctions.calBreadDataAlt(lastTicker, RATE_BREAD_MIN_2TRADE);

            MAStatus maStatus = SimpleMovingAverage1DManager.getInstance().getMaStatus(Utils.getDate(lastTicker.startTime.longValue()), symbol);
            Double maValue = SimpleMovingAverage1DManager.getInstance().getMaValue(symbol, Utils.getDate(lastTicker.startTime.longValue()));
            Double rateMa = Utils.rateOf2Double(lastTicker.priceClose, maValue);
            Double rateChange = BreadProductFunctions.getRateChangeWithVolume(lastTicker.totalUsdt / 1000000);

            if (rateChange == null) {
                LOG.info("Error rateChange with ticker: {} {}", symbol, Utils.toJson(lastTicker));
                return;
            }
            if (breadData.orderSide != null
                    && maStatus != null && maStatus.equals(MAStatus.TOP)
//                    && btcMaStatus != null && !btcMaStatus.equals(MAStatus.UNDER)
                    && rateSma20 < 0
                    && rateMa <= RATE_MA_MAX
                    && breadData.orderSide.equals(OrderSide.BUY)
                    && breadData.totalRate >= rateChange) {
                // end new

                LOG.info("Big:{} {} {} rate:{} volume: {}", symbol, new Date(lastTicker.startTime.longValue()),
                        breadData.orderSide, breadData.totalRate, lastTicker.totalUsdt);

                Double priceEntry = lastTicker.priceClose;
                Double priceTarget = Utils.calPriceTarget(symbol, priceEntry, breadData.orderSide, RATE_TARGET);
                Double quantity = Utils.calQuantity(BudgetManager.getInstance().getBudget(), BudgetManager.getInstance().getLeverage(symbol), priceEntry, symbol);
                if (quantity != null && quantity != 0) {
                    OrderTargetInfo orderTrade = new OrderTargetInfo(OrderTargetStatus.REQUEST, lastTicker.priceClose,
                            priceTarget, quantity, BudgetManager.getInstance().getLeverage(symbol), symbol, lastTicker.startTime.longValue(),
                            lastTicker.startTime.longValue(), breadData.orderSide, Constants.TRADING_TYPE_VOLUME_MINI);
//                    RedisHelper.getInstance().get().rpush(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE, Utils.toJson(orderTrade));
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
