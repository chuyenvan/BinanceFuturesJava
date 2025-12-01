/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.ai_ml.extractor;

import com.binance.chuyennd.aerospike.DataManagerAerospike;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.ExportMarketData2File;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.tradecore.TradeUtils;
import com.binance.chuyennd.tradecore.TrendDetector;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
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
public class ExportDataEntries {

    public static final Logger LOG = LoggerFactory.getLogger(ExportDataEntries.class);

    public String currentMonth = null;

    public TreeMap<Long, OrderTargetInfoTest> allOrderDone;
    public ConcurrentHashMap<String, Map<Long, Boolean>> symbol2TrendData;

    public TreeMap<Long, MarketDataObject> time2MarketData;
    public TreeMap<Long, MarketRateChange> time2MarketRateChange;

    public TreeMap<Long, Double> time2BtcReverse;
    public TreeMap<Long, Set<String>> time2Symbol2Trade = new TreeMap<>();
    public TreeMap<Long, Set<String>> time2Symbol2TradeBtcReverse = new TreeMap<>();


    /**
     * CONSTRUCTOR MAC DINH: De chay binh thuong
     * (Tao mot config DCA mac dinh)
     */


    public static void main(String[] args) throws ParseException, IOException, InterruptedException {
        ExportDataEntries test = new ExportDataEntries();
        test.initData();
        test.simulatorWithInitEntry();
    }

    public void simulatorWithInitEntry(String... inputs) throws ParseException {
        Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
        TreeMap<Long, Double> time2RateDown15MAvg = new TreeMap<>();
        Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();
        //get data
        while (true) {
            TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers;
            try {
                time2Tickers = DataManagerAerospike.readDataFromAerospike1M(startTime);
                if (time2Tickers == null) {
                    LOG.info("File data error or not found for time: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                }
                LOG.info("Total entries: {}", time2Symbol2Trade.size());
                if (time2Tickers != null) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                        Long time = entry.getKey();

                        Boolean isTrendBuyWithBtc = getTrendBySymbol(Constants.SYMBOL_PAIR_BTC, time);
                        Boolean isTrendBuyWithETH = getTrendBySymbol(Constants.SYMBOL_PAIR_ETH, time);
                        try {
                            Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                            for (String symbol : symbol2Ticker.keySet()) {
                                KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                if (!Utils.isTickerAvailable(ticker)) {
                                    continue;
                                }
                                List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                if (tickers == null) {
                                    tickers = new ArrayList<>();
                                    symbol2LastTickers.put(symbol, tickers);
                                }
                                tickers.add(ticker);
                                int sizeRemove = 205;

                                if (tickers.size() > sizeRemove) {
                                    for (int i = 0; i < 5; i++) {
                                        tickers.remove(0);
                                    }
                                }
                            }

                            MarketRateChange marketRateChange = time2MarketRateChange.get(time);
                            MarketDataObject marketData;
                            marketData = time2MarketData.get(time);
                            Set<String> symbolLocked = new HashSet<>();
                            MarketLevelChange levelChange = null;
                            Map<String, Double> symbol2PriceMax15M = new HashMap<>();

                            if (marketData != null) {
                                TreeMap<Double, String> rate2Max = new TreeMap<>();
                                rate2Max.putAll(marketData.rate2Max);
                                double predictedReturn = 0;
                                levelChange = MarketBigChangeDetector.getMarketStatus1M(marketData.rateDownAvg,
                                        marketData.rateUpAvg, marketData.rateBtc, marketData.rateDown15MAvg);
                                symbol2PriceMax15M.putAll(marketData.symbol2PriceMax15M);

                                // buy signal new
                                if (levelChange != null) {
                                    Integer numberOrder = Configs.NUMBER_ENTRY_EACH_SIGNAL;
                                    // tang so luong lenh lay du lieu
                                    numberOrder = numberOrder * 3;
                                    if (levelChange.equals(MarketLevelChange.SMALL_DOWN)
                                            || levelChange.equals(MarketLevelChange.SMALL_UP)
                                            || levelChange.equals(MarketLevelChange.MEDIUM_DOWN_15M)
                                            || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)
                                    ) {
                                        numberOrder = numberOrder / 2;
                                    }
                                    Set<String> symbol2BUY = new HashSet<>();
                                    symbol2BUY.addAll(MarketBigChangeDetector.getTopSymbol(rate2Max, numberOrder, symbol2Ticker, symbolLocked));
                                    symbol2BUY.addAll(MarketBigChangeDetector.addSpecialSymbol(symbol2Ticker, symbol2BUY,
                                            isTrendBuyWithETH, new HashSet<>()));
                                    // check create order new
                                    for (String symbol : symbol2BUY) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                        // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                        if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                            continue; // Bỏ qua nếu có rủi ro
                                        }
                                        addEntries(symbol, ticker, levelChange, isTrendBuyWithBtc);
                                    }
                                }
                            }


                            if (marketRateChange != null) {
                                time2RateDown15MAvg.put(time, marketRateChange.rateDown15MAvg);
                                while (time2RateDown15MAvg.size() > Configs.NUMBER_RATE_DOWN_HISTORY_TRADE) {
                                    time2RateDown15MAvg.remove(time2RateDown15MAvg.firstKey());
                                }
                                Double minRate15Min60M = Collections.min(time2RateDown15MAvg.values());
                                Set<String> symbolCanTradeMass = new HashSet<>();
                                Set<String> symbolHadTrade = new HashSet<>();
                                // funding level 1
                                if (MarketBigChangeDetector.isFundingFeeTrade(marketRateChange.rateDown15MAvg - 0.003,// ha dieu kien noi long lay them du lieu
                                        marketRateChange.rateDownAvg, marketRateChange.rateUpAvg, minRate15Min60M, isTrendBuyWithETH)
                                ) {
                                    Set<String> symbolFundingBuy = FundingFeeManager.getInstance().getFundingBuyNew(time);
                                    Set<String> symbolBuyFundingFee = new HashSet<>();
                                    symbolBuyFundingFee.addAll(symbolFundingBuy);
                                    for (String symbol : symbolBuyFundingFee) {
                                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                        if (!Utils.isTickerAvailable(ticker)) {
                                            continue;
                                        }
                                        List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);

                                        Double priceMax15M = getMax15M(tickers);
                                        Double rateTicker = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen);

                                        Double rateMax15M = 0.0;
                                        if (priceMax15M != null) {
                                            rateMax15M = Utils.rateOf2Double(ticker.priceClose, priceMax15M);
                                        }
                                        if (MarketBigChangeDetector.isRateChangeAvailable2Trade(rateTicker, rateMax15M, isTrendBuyWithETH)) {
                                            // ================== GỌI HÀM LỌC DUY NHẤT ==================
                                            if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                                continue; // Bỏ qua nếu có rủi ro
                                            }
                                            symbolCanTradeMass.add(symbol);
                                            addEntries(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY, isTrendBuyWithBtc);
                                        } else {
                                            if (MarketBigChangeDetector.isRateChangeAvailable2TradeMass(rateTicker, rateMax15M, isTrendBuyWithETH)) {
                                                symbolCanTradeMass.add(symbol);
                                                symbolHadTrade.add(symbol);
                                            }
                                        }
                                    }
                                    if (symbolCanTradeMass.size() > 4) {
                                        symbolCanTradeMass.removeAll(symbolHadTrade);
                                        for (String symbol : symbolCanTradeMass) {
                                            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                            if (!Utils.isTickerAvailable(ticker)) {
                                                continue;
                                            }
                                            List<KlineObjectSimple> tickers = symbol2LastTickers.get(symbol);
                                            if (TradeUtils.shouldAvoidEntry(symbol, tickers, isTrendBuyWithETH)) {
                                                continue; // Bỏ qua nếu có rủi ro
                                            }
                                            addEntries(symbol, ticker, MarketLevelChange.FUNDING_FEE_BUY, isTrendBuyWithBtc);
                                        }
                                    }
                                }
                            }

                            // BTC trend reverse
                            Double rateBtcTrendReverse = time2BtcReverse.get(time);
                            if (rateBtcTrendReverse != null && rateBtcTrendReverse >= Configs.BTC_TREND_REVERSE_RATE_MIN_TRADE) {
                                Set<String> hashSet = new HashSet<>();
                                hashSet.addAll(Constants.specialSymbol);
                                time2Symbol2TradeBtcReverse.put(time, hashSet);
                            }


                        } catch (Exception e) {
                            e.printStackTrace();
                        }
                    }
                }
            } catch (Exception e) {
                e.printStackTrace();
            }

            startTime += Utils.TIME_DAY;
            if (startTime > System.currentTimeMillis()) {
                break;
            }
        }
        StorageSnappy.writeObject2File(Configs.ENTRIES_DATA_FILE, time2Symbol2Trade);


    }

    private Boolean getTrendBySymbol(String symbol, Long time) {
        Map<Long, Boolean> trendData = symbol2TrendData.get(symbol);
        if (trendData == null) {
            trendData = new HashMap<>();
            symbol2TrendData.put(symbol, trendData);
        }
        if (trendData.containsKey(time)) {
            return trendData.get(time);
        } else {
            Boolean trend = false;
            switch (symbol) {
                case Constants.SYMBOL_PAIR_BTC:
                    trend = TrendDetector.isTrendBTC(time);
                    break;
                case Constants.SYMBOL_PAIR_ETH:
                    trend = TrendDetector.isTrendETH(time);
                    break;
            }
            trendData.put(time, trend);
            return trend;
        }
    }

    private void logByProcessTime(Long startTimeRun, String msg, Long time) {
        long duration = (System.currentTimeMillis() - startTimeRun);
        if (duration > 100) {
            LOG.info("{} {} {}", Utils.normalizeDateYYYYMMDDHHmm(time), msg, duration);
        }
    }


    private Double getMax15M(List<KlineObjectSimple> tickers) {
        Double priceMax15M = null;
        for (int i = 0; i < Configs.NUMBER_TICKER_CAL_RATE_CHANGE; i++) {
            int index = tickers.size() - i - 1;
            if (index >= 0) {
                KlineObjectSimple kline = tickers.get(index);
                if (priceMax15M == null) {
                    priceMax15M = kline.maxPrice;
                }
                priceMax15M = Math.max(priceMax15M, kline.maxPrice);
            }
        }
        return priceMax15M;
    }


    public void initData() throws IOException, ParseException {
        // clear Data Old
        BudgetManagerSimple.getInstance().resetInstance();
        allOrderDone = new TreeMap<>();

        if (!new File(Configs.FILE_MARKET_RATE_CHANGE).exists()) {
            new ExportMarketData2File().exportMarketEntries();
        }
        if (!new File(Configs.FILE_ENTRY_BTC_REVERSE).exists()) {
            new ExportMarketData2File().exportBtcTrendReverse();
        }
        time2MarketRateChange = (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_MARKET_RATE_CHANGE);
        time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        time2BtcReverse = (TreeMap<Long, Double>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_BTC_REVERSE);

        if (new File(Configs.FILE_TREND_BY_TIME).exists()) {
            symbol2TrendData = (ConcurrentHashMap<String, Map<Long, Boolean>>) StorageSnappy.readObjectFromFile(Configs.FILE_TREND_BY_TIME);
        } else {
            symbol2TrendData = new ConcurrentHashMap<>();
        }
    }


    public void addEntries(String symbol, KlineObjectSimple ticker, MarketLevelChange levelChange,
                           Boolean isTrendBuyWithBtc) {
        if (levelChange.equals(MarketLevelChange.SMALL_UP)
                || levelChange.equals(MarketLevelChange.SMALL_DOWN_15M)) {
            if (!isTrendBuyWithBtc) {
                return;
            }
        }
        Set<String> symbolEntries = time2Symbol2Trade.get(ticker.startTime.longValue());
        if (symbolEntries == null) {
            symbolEntries = new HashSet<>();
            time2Symbol2Trade.put(ticker.startTime.longValue(), symbolEntries);
        }
        symbolEntries.add(symbol);
    }

}
