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
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

public class AltGridResearchDownloadNew {
    public static final Logger LOG = LoggerFactory.getLogger(AltGridResearchDownloadNew.class);
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
            GridObjectALTResearch simulator = null;
            List<KlineObjectNumber> ticker2Test = new ArrayList<>();
            Long startTime = ticker4Hours.get(0).startTime.longValue();
            for (KlineObjectNumber ticker4Hour : ticker4Hours) {
                ticker2Test.add(ticker4Hour);
                if (ticker2Test.size() < 4) {
                    continue;
                }
                if (ticker4Hour.startTime.longValue() <= startTime){
                    continue;
                }
                if (simulator == null) {
                    simulator = GridDetector.findGridAltSymbol(symbol, ticker2Test);
                }
                if (simulator != null) {
                    LOG.info("Time create grid: {} {} {}", Utils.normalizeDateYYYYMMDDHHmm(ticker4Hour.startTime.longValue()),
                            symbol, ticker4Hour.priceClose);
                    List<KlineObjectSimple> tickers = new ArrayList<>();
                    for (int i = 0; i < 30; i++) {
                        long time = ticker4Hour.startTime.longValue() + 4 * Utils.TIME_HOUR + i * 500 * Utils.TIME_MINUTE;
                        tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
                                Constants.INTERVAL_1M, time));
                        if (time > System.currentTimeMillis()) {
                            break;
                        }
                    }
                    if (tickers.isEmpty()) {
                        break;
                    }
                    simulator.tickerStart = tickers.get(0);
                    simulator.initGrid();
                    for (KlineObjectSimple ticker : tickers) {
                        if (simulator.status.equals(OrderTargetStatus.POSITION_RUNNING)) {
                            simulator.updateGridWithMaBtc(ticker);
                        } else {
                            simulator.printResult();
                            allGridDone.put(simulator.tickerStart.startTime.longValue() + allGridDone.size(), simulator);
                            startTime = simulator.endTime;
//                        simulator.exportFile();
                            simulator = null;
                            break;
                        }
                    }
                    if (simulator != null) {
                        simulator.printResult();
                        startTime = simulator.endTime;
//                    simulator.exportFile();
                        simulator = null;
                    }
                }
            }
            Storage.writeObject2File("storage/GridTest-" + symbol + ".data", allGridDone);
        }
    }
}
