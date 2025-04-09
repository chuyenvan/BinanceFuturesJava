/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.object.KlineObjectNumber;
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

import java.io.File;
import java.io.IOException;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * @author pc
 */
public class GribCoupleSimulator {

    public static final Logger LOG = LoggerFactory.getLogger(GribCoupleSimulator.class);
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
        GribCoupleSimulator simulator = new GribCoupleSimulator();
        simulator.init();
        simulator.simulatorSpecial();
    }

    private void simulatorSpecial() throws ParseException {

        Map<String, KlineObjectSimple> symbol2FinalTicker = new HashMap<>();
        Long startTime = Utils.sdfFile.parse(TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        Double rateGrid = 0.2;
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
                    if (ticker == null) {
                        continue;
                    }
                    symbol2FinalTicker.put(symbol, ticker);
                    String symbolBuy = symbol + "-" + OrderSide.BUY;
                    String symbolSell = symbol + "-" + OrderSide.SELL;
                    GridObjectTestResearch gridBuy = symbol2GridRunning.get(symbolBuy);
                    GridObjectTestResearch gridSell = symbol2GridRunning.get(symbolSell);

//                    if (gridBuy != null && gridSell != null){
//                        if (gridBuy.calProfit() + gridSell.calProfit() > BudgetManagerSimple.getInstance().getBudgetGrid()/5){
//                            gridBuy.closeGrid(ticker, "Close by profit");
//                            allGridDone.put(gridBuy.tickerStart.startTime.longValue() + allGridDone.size(), gridBuy);
//                            symbol2GridRunning.remove(symbolBuy);
//                            gridSell.closeGrid(ticker, "Close by profit");
//                            allGridDone.put(gridSell.tickerStart.startTime.longValue() + allGridDone.size(), gridSell);
//                            symbol2GridRunning.remove(symbolSell);
//                        }
//                    }
                    if (gridBuy == null) {
                        Double maxPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.BUY, rateGrid);
                        Double minPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.SELL, rateGrid);
                        gridBuy = new GridObjectTestResearch(symbol, OrderSide.BUY, maxPrice, minPrice, ticker);
                        gridBuy.initGrid();
                        symbol2GridRunning.put(symbolBuy, gridBuy);
                    } else {
                        if (gridBuy.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                            gridBuy.updateAllOrderRunning(ticker);
                        }
                        if (gridBuy.status.equals(OrderTargetStatus.FINISHED)) {
//                            gridBuy.exportFile();
                            allGridDone.put(gridBuy.tickerStart.startTime.longValue() + allGridDone.size(), gridBuy);
                            symbol2GridRunning.remove(symbolBuy);
                        }
                    }
                    if (gridSell == null) {
                        Double maxPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.BUY, rateGrid);
                        Double minPrice = Utils.calPriceTarget(symbol, ticker.priceClose, OrderSide.SELL, rateGrid);
                        gridSell = new GridObjectTestResearch(symbol, OrderSide.SELL, maxPrice, minPrice, ticker);
                        gridSell.initGrid();
                        symbol2GridRunning.put(symbolSell, gridSell);
                    } else {
                        if (gridSell.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                            gridSell.updateAllOrderRunning(ticker);
                        }
                        if (gridSell.status.equals(OrderTargetStatus.FINISHED)) {
//                            gridSell.exportFile();
                            allGridDone.put(gridSell.tickerStart.startTime.longValue() + allGridDone.size(), gridSell);
                            symbol2GridRunning.remove(symbolSell);
                        }
                    }
                }
                if (time % Utils.TIME_DAY == 0) {
                    GridBudgetManager.getInstance().updateBalance(time, allGridDone, symbol2GridRunning, true);
                } else {
                    GridBudgetManager.getInstance().updateBalance(time, allGridDone, symbol2GridRunning, false);
                }
//                if (symbol2GridRunning.isEmpty()) {
//                    break;
//                }
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

        File[] symbolFiles = new File(Configs.FOLDER_TICKER_1D).listFiles();
        for (File symbolFile : symbolFiles) {
            String symbol = symbolFile.getName();
            if (Constants.specialSymbol.contains(symbol)) {
                try {
                    List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + symbol);
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
