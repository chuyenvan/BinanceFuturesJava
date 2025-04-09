/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class GribSimulatorWithAnOrder {

    public static final Logger LOG = LoggerFactory.getLogger(GribSimulatorWithAnOrder.class);
    public final String FILE_STORAGE_ORDER_DONE = "storage/GridSimulator.data";
    public String TIME_RUN = Configs.getString("TIME_RUN");
    public ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone = new ConcurrentHashMap<>();
    //get data
    public TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = new TreeMap<>();
    public ConcurrentHashMap<String, GridObjectTestResearch> symbol2GridRunning = new ConcurrentHashMap();
    public Map<String, List<KlineObjectNumber>> symbol2Ticker1Ds = new HashMap<>();
    public Double priceRange = null;

    // strategy dat mua va ban 3 lenh tren 3 lenh duoi lenh khop dat lenh moi theo gia moi
    // create order limit
    // update order limit

    public static void main(String[] args) throws ParseException, IOException {
        GribSimulatorWithAnOrder simulator = new GribSimulatorWithAnOrder();
//        for (int i = 0; i < 2; i++) {
//            GridConfigs.GRID_RATE_TRADE = 0.04 + i * 0.01;
//            for (String symbol : Constants.btcReverseSymbol) {
//                try {
//                    Constants.specialSymbol.clear();
//                    Constants.specialSymbol.add(symbol);
////                    LOG.info("special: {} {}",symbol, Constants.specialSymbol);
//                    simulator.init();
//                    simulator.simulatorSpecial();
//                } catch (Exception e) {
//                    e.printStackTrace();
//                }
//            }
//        }
        simulator.init();
        simulator.simulatorSpecial();
    }

    private void simulatorSpecial() throws ParseException {

        Map<String, KlineObjectSimple> symbol2FinalTicker = new HashMap<>();
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
//        Map<Long, MarketDataObject> time2MarketData = (Map<Long, MarketDataObject>)
//                Storage.readObjectFromFile("storage/market_data/time2market.data");
        try {
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                Long time = entry.getKey();
                if (time < startTime) {
                    continue;
                }
                Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
                    String symbol = entry1.getKey();
                    if (!Constants.specialSymbol.contains(symbol)) {
                        continue;
                    }
                    KlineObjectSimple ticker = entry1.getValue();
                    if (ticker == null){
                        continue;
                    }
                    symbol2FinalTicker.put(symbol, ticker);
                    GridObjectTestResearch grid = symbol2GridRunning.get(symbol);
                    if (grid == null) {
                        List<KlineObjectNumber> ticker15Ms = symbol2Ticker1Ds.get(symbol);
                        Map<String, KlineObjectSimple> ticker4hAgo = time2Tickers.get(time - 4 * Utils.TIME_HOUR);
                        List<Double> rateTimeAgo = new ArrayList<>();
                        rateTimeAgo.add(Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen));
                        Double rate4h = null;
                        if (ticker4hAgo != null && ticker4hAgo.get(symbol) != null) {
                            rate4h = Utils.rateOf2Double(ticker.priceClose, ticker4hAgo.get(symbol).priceOpen);
                            rateTimeAgo.add(rate4h);
                        } else {
                            rateTimeAgo.add(null);
                        }

                        if (ticker15Ms != null) {
                            Double differenceMa20AndMa60 = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC
                                    , ticker.startTime.longValue());
                            Double difference4HMa20AndMa60 = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC
                                    , ticker.startTime.longValue());
                            grid = GridDetector.findGridSpecialSymbol(symbol, ticker, time, ticker15Ms, differenceMa20AndMa60, difference4HMa20AndMa60, rate4h);
                            if (grid != null) {
                                grid.datas = rateTimeAgo;
                                grid.initGridOnlyAnOrder();
                                symbol2GridRunning.put(symbol, grid);
                            }
                        }
                    } else {
                        if (grid.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                            grid.updateOrderUnique(ticker);
                        }
                        if (grid.status.equals(OrderTargetStatus.FINISHED)) {
                            allGridDone.put(grid.tickerStart.startTime.longValue() + allGridDone.size(), grid);
//                            grid.printResult();
                            symbol2GridRunning.remove(symbol);
                        }
                    }

                }
                if (time % Utils.TIME_DAY == 0) {
                    GridBudgetManager.getInstance().updateBalance(time, allGridDone, symbol2GridRunning, true);
                } else {
                    GridBudgetManager.getInstance().updateBalance(time, allGridDone, symbol2GridRunning, false);
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }


        for (String symbol : symbol2GridRunning.keySet()) {
            GridObjectTestResearch grid = symbol2GridRunning.get(symbol);
            if (grid != null && symbol2FinalTicker.get(symbol) != null) {
                grid.closeGrid(symbol2FinalTicker.get(symbol), "Close by end time");
                allGridDone.put(grid.tickerStart.startTime.longValue() + allGridDone.size(), grid);
                grid.printResult();
            }

        }
        if (allGridDone.size() > 0) {
            GridBudgetManager.getInstance().updateBalance(System.currentTimeMillis(), allGridDone, symbol2GridRunning, true);
//            Storage.writeObject2File("storage/GridTest" + Constants.specialSymbol + "-" + GridConfigs.GRID_RATE_TRADE + ".data", allGridDone);
            Storage.writeObject2File("storage/GridTestDone.data", allGridDone);
            Storage.writeObject2File("storage/BalanceIndex.data", GridBudgetManager.getInstance().balanceIndex);
        }
    }

    private void init() {
//        Constants.specialSymbol.addAll(Constants.btcReverseSymbol);
        File[] symbolFiles = new File(Configs.FOLDER_TICKER_1D).listFiles();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (Constants.specialSymbol.contains(symbol)) {
                try {
//                    List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
                    List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1D + symbol);
                    if (tickers == null) {
                        continue;
                    }
                    symbol2Ticker1Ds.put(symbol, tickers);
                    LOG.info("{} {} {}", symbol, Utils.normalizeDateYYYYMMDD(tickers.get(0).startTime.longValue()),
                            Utils.normalizeDateYYYYMMDD(tickers.get(tickers.size() - 1).startTime.longValue()));
                    List<KlineObjectSimple> ticker1Ms = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
                    if (ticker1Ms == null) {
                        continue;
                    }
                    for (KlineObjectSimple ticker : ticker1Ms) {
                        Map<String, KlineObjectSimple> ticker1MofSymbol = time2Tickers.get(ticker.startTime.longValue());
                        if (ticker1MofSymbol == null) {
                            ticker1MofSymbol = new HashMap<>();
                        }
                        ticker1MofSymbol.put(symbol, ticker);
                        time2Tickers.put(ticker.startTime.longValue(), ticker1MofSymbol);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }

    }


}
