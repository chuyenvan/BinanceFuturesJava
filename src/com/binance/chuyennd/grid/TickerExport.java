package com.binance.chuyennd.grid;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

public class TickerExport {
    public static final Logger LOG = LoggerFactory.getLogger(TickerExport.class);

    public static void main(String[] args) throws ParseException {
        for (String symbol : Constants.specialSymbol) {
            List<KlineObjectSimple> tickers = (List<KlineObjectSimple>) Storage.readObjectFromFile(
                    Configs.FOLDER_TICKER_1M + symbol);
            LOG.info("export ticker:{} {}", symbol, tickers.size());
            Map<Integer, List<KlineObjectSimple>> year2Tickers = new HashMap<>();
            for (KlineObjectSimple ticker : tickers) {
                int year = Utils.getYear(ticker.startTime.longValue());
                List<KlineObjectSimple> tickerOfYear = year2Tickers.get(year);
                if (tickerOfYear == null) {
                    tickerOfYear = new ArrayList<>();
                }
                tickerOfYear.add(ticker);
                year2Tickers.put(year, tickerOfYear);
            }
            for (Map.Entry<Integer, List<KlineObjectSimple>> entry : year2Tickers.entrySet()) {
                Integer key = entry.getKey();
                List<KlineObjectSimple> values = entry.getValue();
                LOG.info("Write ticker 2 file:{} {} {}", symbol, key, values.size());
                Storage.writeObject2File("storage/ticker1M/" + symbol + "-" + key, values);
            }
        }
    }
}
