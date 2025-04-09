package com.binance.chuyennd.grid;

import com.binance.chuyennd.bigchange.market.MarketBigChangeDetectorTest;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class RunAllGridMarket {
    public static final Logger LOG = LoggerFactory.getLogger(RunAllGridMarket.class);

    public static void main(String[] args) throws ParseException {
        String symbol = "XRPUSDT";
        ConcurrentHashMap<Long, GridObjectTestResearch> allGridDone = new ConcurrentHashMap<>();
        Map<Long, GridObjectTestResearch> time2GridRunning = new HashMap<>();

        List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
        Map<Long, MarketDataObject> time2MarketData = (Map<Long, MarketDataObject>)
                Storage.readObjectFromFile("storage/market_data/time2market.data");


        for (KlineObjectSimple ticker : tickers) {
            long time = ticker.startTime.longValue();
            // update grid running
            List<Long> timeGridDones = new ArrayList<>();
            for (Long timeGrid : time2GridRunning.keySet()) {
                GridObjectTestResearch grid = time2GridRunning.get(timeGrid);
                if (grid.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                    if (ticker.startTime.longValue() <= grid.tickerStart.startTime.longValue()) {
                        continue;
                    }
                    grid.updateAllOrderRunning(ticker);
                } else {
                    allGridDone.put(grid.tickerStart.startTime.longValue() + allGridDone.size(), grid);
                    timeGridDones.add(timeGrid);
                }
            }
            for (Long timeGrid : timeGridDones) {
                time2GridRunning.remove(timeGrid);
            }
            MarketDataObject marketData = time2MarketData.get(time);
            if (marketData != null ) {//&& time2GridRunning.size() < 50
                MarketLevelChange levelChange = MarketBigChangeDetectorTest.getMarketStatusSimple(marketData.rateDownAvg,
                        marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg, marketData.rateUp15MAvg,
                        marketData.rateBtcDown15M);
                if (levelChange != null) {
                    if (levelChange.equals(MarketLevelChange.TINY_UP)) {
                        continue;
                    }
                    if (levelChange.equals(MarketLevelChange.TINY_DOWN)) {
                        if (marketData.rateDownAvg > -0.007) {
                            continue;
                        }
                    }
                    GridObjectTestResearch grid = new GridObjectTestResearch(symbol, OrderSide.BUY,
                            ticker.priceClose * 1.2, ticker.priceClose * 0.8, ticker, BudgetManagerSimple.getInstance().getBudgetGrid());
                    grid.levelChange = levelChange;
//                    marketData.rateDown2Symbols.clear();
//                    marketData.rate2Max.clear();
//                    marketData.symbol2PriceMax15M.clear();
//                    grid.marketData = marketData;
//                    LOG.info("Create grid: {} {} {}", symbol, levelChange, Utils.normalizeDateYYYYMMDDHHmm(time));
                    grid.initGrid();
                    time2GridRunning.put(time, grid);
                }
            }
            if (time % Utils.TIME_DAY == 0) {
                LOG.info("Process done: {} {} orders {} dones.", Utils.normalizeDateYYYYMMDD(time), time2GridRunning.size(), allGridDone.size());
            }
        }
        for (GridObjectTestResearch grid : time2GridRunning.values()) {
            if (grid != null) {
                grid.closeGrid(tickers.get(tickers.size() - 1), "Close by end time");
                allGridDone.put(grid.tickerStart.startTime.longValue() + allGridDone.size(), grid);
                grid.printResult();
            }
        }
        Storage.writeObject2File("storage/Grid" + "-" + symbol + "-" + "Done.data", allGridDone);
    }
}
