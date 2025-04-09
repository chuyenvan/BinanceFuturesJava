package com.binance.chuyennd.grid;

import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class AltGridResearchTickerDownloaded {
    public static final Logger LOG = LoggerFactory.getLogger(AltGridResearchTickerDownloaded.class);

    public static ConcurrentHashMap<Long, GridObjectALTResearch> allGridDone = new ConcurrentHashMap<>();

    public static void main(String[] args) throws ParseException {
//        String symbol = "1000BONKUSDT";
//        Set<String> symbols = TickerFuturesHelper.getAllSymbol();
        Set<String> symbols = new HashSet<>();
        symbols.addAll(Constants.specialSymbol);
        symbols.addAll(Constants.stableSymbol);
        symbols.addAll(Constants.btcReverseSymbol);
        for (String symbol : symbols) {
            List<KlineObjectNumber> ticker4Hours = (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + symbol);
            List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_1M + symbol);
            TreeMap<Long, KlineObjectSimple> time2Ticker = new TreeMap<>();
            if (tickers == null){
                continue;
            }
            for (KlineObjectSimple ticker : tickers) {
                time2Ticker.put(ticker.startTime.longValue(), ticker);
            }
            GridObjectALTResearch simulator = null;
            Long startTime = ticker4Hours.get(0).startTime.longValue();
            List<KlineObjectNumber> ticker2Test = new ArrayList<>();
            for (KlineObjectNumber ticker4Hour : ticker4Hours) {
                ticker2Test.add(ticker4Hour);
                if (ticker2Test.size() < 4) {
                    continue;
                }
                if (ticker4Hour.startTime.longValue() <= startTime) {
                    continue;
                }
                if (simulator == null) {
                    simulator = GridDetector.findGridAltSymbol(symbol, ticker2Test);
                }
                if (simulator != null) {
                    LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker4Hour.startTime.longValue()),
                            symbol, ticker4Hour.priceClose);
                    startTime = ticker4Hour.startTime.longValue() + 4 * Utils.TIME_HOUR;
                    KlineObjectSimple ticker = time2Ticker.get(startTime);
                    if (ticker == null){
                        continue;
                    }
                    simulator.tickerStart = ticker;
                    simulator.initGrid();
                    while (true) {
                        startTime += Utils.TIME_MINUTE;
                        ticker = time2Ticker.get(startTime);
                        if (ticker == null){
                            break;
                        }
                        if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                            simulator.updateGridWithMaBtc(ticker);
                        } else {
                            simulator.printResult();
                            allGridDone.put(simulator.tickerStart.startTime.longValue() + allGridDone.size(), simulator);
//                        simulator.exportFile();
                            simulator = null;
                            break;
                        }
                    }
                    if (simulator != null) {
                        simulator.printResult();
//                    simulator.exportFile();
                        simulator = null;
                    }
                }
            }
            Storage.writeObject2File("storage/GridTestDone.data", allGridDone);
        }
    }
}
