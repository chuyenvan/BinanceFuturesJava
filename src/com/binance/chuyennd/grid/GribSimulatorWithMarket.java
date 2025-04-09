/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.bigchange.statistic.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class GribSimulatorWithMarket {

    public static final Logger LOG = LoggerFactory.getLogger(GribSimulatorWithMarket.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/GridSimulator.data";
    public String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, GridObjectTestResearch> symbol2GridRunning = new ConcurrentHashMap();

    public Double priceRange = null;

    // strategy dat mua va ban 3 lenh tren 3 lenh duoi lenh khop dat lenh moi theo gia moi
    // create order limit
    // update order limit

    public static void main(String[] args) throws ParseException, IOException {
        GribSimulatorWithMarket simulator = new GribSimulatorWithMarket();
//        simulator.simulator();
        simulator.simulatorSpecial();
    }

    private void simulatorSpecial() throws ParseException {
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Map<Long, MarketDataObject> time2MarketData = (Map<Long, MarketDataObject>)
                Storage.readObjectFromFile("../storage/market_data/time2market.data");
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                LOG.info("Read file ticker: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));

                time2Tickers = DataManager.readDataFromFile1M(startTime);
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();

                        Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                        if (!symbol2GridRunning.isEmpty()) {
                            for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                                String symbol = entry1.getKey();
                                KlineObjectSimple ticker = entry1.getValue();
                                GridObjectTestResearch grid = symbol2GridRunning.get(symbol);
                                if (grid != null) {
                                    if (grid.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                                        grid.updateAllOrderRunning(ticker);
                                    }
                                    if (grid.status.equals(OrderTargetStatus.FINISHED)) {
                                        allGridDone.put(grid.tickerStart.startTime.longValue() + allGridDone.size(), grid);
                                        grid.printResult();
                                        symbol2GridRunning.remove(symbol);
                                    }
                                }
                            }
                        }
                        MarketDataObject marketData = time2MarketData.get(time);
                        if (marketData != null && symbol2GridRunning.size() < 100) {
                            MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                                    marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
                                    marketData.rateBtcDown15M);
                            if (levelChange != null) {
                                LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(time), levelChange);
                                int numberGridActive = 3;
                                if (levelChange.equals(MarketLevelChange.TINY_UP)) {
                                    numberGridActive = 0;
                                }
                                if (levelChange.equals(MarketLevelChange.TINY_DOWN)) {
                                    if (marketData.rateDownAvg > -0.007) {
                                        numberGridActive = 0;
                                    } else {
                                        Double differenceMa20AndMa60 = SimpleMovingAverageWeekManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                                        if (differenceMa20AndMa60 != null && differenceMa20AndMa60 < 0) {
//                                            numberGridActive = 0;
                                        } else {
                                            numberGridActive = 1;
                                        }
                                    }
                                }
                                if (levelChange.equals(MarketLevelChange.SMALL_UP)
                                        || levelChange.equals(MarketLevelChange.SMALL_DOWN)) {
                                    Double differenceMa20AndMa60 = SimpleMovingAverageWeekManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
                                    if (differenceMa20AndMa60 != null
                                            && differenceMa20AndMa60 < 0
                                            && levelChange.equals(MarketLevelChange.SMALL_DOWN)) {
//                                        numberGridActive = 0;
                                    } else {
                                        numberGridActive = 2;
                                    }
                                }
                                int counter = 0;
                                if (numberGridActive > 0) {
//                                    List<String> symbolTop = getTop20(marketData.rate2Max);
                                    for (String symbol : marketData.rate2Max.values()) {
                                        KlineObjectSimple ticker = entry.getValue().get(symbol);
                                        if (ticker == null) {
                                            continue;
                                        }
                                        if (symbol2GridRunning.containsKey(symbol)) {
                                            continue;
                                        }
//                                        if (!Constants.specialSymbol.contains(symbol)) {
//                                            continue;
//                                        }
//                                    Double differenceMa20AndMa60 = SimpleMovingAverageDayManager.getInstance()
//                                            .getDifferenceMa10AndMa60(symbol, ticker.startTime.longValue());
//                                    Double differenceMa4Hour20AndMa60 = SimpleMovingAverage4hManager.getInstance()
//                                            .getDifferenceMa10AndMa60(symbol, ticker.startTime.longValue());
//                                    if (differenceMa20AndMa60 != null || differenceMa4Hour20AndMa60 > 0) {
                                        GridObjectTestResearch grid = new GridObjectTestResearch(symbol, OrderSide.BUY,
                                                ticker.priceClose * 1.3, ticker.priceClose * 0.9, ticker,
                                                BudgetManagerSimple.getInstance().getBudgetGrid());
                                        grid.levelChange = levelChange;
//                                        marketData.rateDown2Symbols.clear();
//                                        marketData.rate2Max.clear();
//                                        marketData.symbol2PriceMax15M.clear();
//                                        grid.marketData = marketData;
                                        LOG.info("Create grid: {} {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time), levelChange);
                                        if (levelChange.equals(MarketLevelChange.TINY_UP)
//                                                || levelChange.equals(MarketLevelChange.TINY_DOWN)
//                                                || levelChange.equals(MarketLevelChange.SMALL_DOWN)
//                                                || levelChange.equals(MarketLevelChange.SMALL_UP)
//                                                || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                                        ) {
//                                            Double differenceMa20AndMa60 = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(symbol
//                                                    , ticker.startTime.longValue());
//                                            Double difference4hMa20AndMa60 = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(symbol
//                                                    , ticker.startTime.longValue());
//                                            if ((differenceMa20AndMa60 != null && differenceMa20AndMa60 > 0) ||
//                                                    (difference4hMa20AndMa60 != null && difference4hMa20AndMa60 > 0)) {
//                                                grid.initGrid();
//                                                symbol2GridRunning.put(symbol, grid);
//                                                counter++;
//                                            }
                                        } else {
                                            grid.initGrid();
                                            symbol2GridRunning.put(symbol, grid);
                                            counter++;

                                        }
                                        if (counter > numberGridActive) {
                                            break;
                                        }

//                                    }
                                    }
                                }
                            }
                        }
                        if (time % Utils.TIME_DAY == 0) {
                            GridBudgetManager.getInstance().updateBalance(time, allGridDone, symbol2GridRunning, true);
                        } else {
                            GridBudgetManager.getInstance().updateBalance(time, allGridDone, symbol2GridRunning, false);
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
            Long finalStartTime1 = startTime;
            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        Storage.writeObject2File("storage/GridTestDone.data", allGridDone);
    }

    private List<String> getTop20(TreeMap<Double, String> rate2Max) {
        List<String> symbols = new ArrayList<>();
        for (Map.Entry<Double, String> entry : rate2Max.entrySet()) {
            String symbol = entry.getValue();
            symbols.add(symbol);
            if (symbols.size() >= 30) {
                break;
            }
        }
        return symbols;
    }

    private List<String> getSymbolGrid(TreeMap<Double, String> rate2Max) {
        List<String> symbols = new ArrayList<>();
//        Set<String> hashSet = new HashSet<>();
//        hashSet.addAll(Constants.specialSymbol);
//        hashSet.addAll(Constants.stableSymbol);
//        hashSet.addAll(Constants.btcReverseSymbol);
        for (Map.Entry<Double, String> entry : rate2Max.descendingMap().entrySet()) {
            String symbol = entry.getValue();
            if (symbol2GridRunning.containsKey(symbol)) {
                continue;
            }
//            if (hashSet.contains(symbol)){
            symbols.add(symbol);
//            }
        }
        return symbols;
    }


    private GridObjectTest createGrid(String symbol, KlineObjectSimple ticker) {
        Double maxPrice = ticker.priceClose * 1.2;
        Double minPrice = ticker.priceClose * 0.8;
        Double top = maxPrice * (1 + 0.01);
        Double bottom = minPrice * (1 - 0.01);
        Double range = Utils.rateOf2Double(maxPrice, minPrice) * 100;
        GridObjectTest simulator = new GridObjectTest(symbol, OrderSide.BUY, maxPrice, minPrice, top, bottom, range.intValue(), ticker);
        return simulator;

    }

}
