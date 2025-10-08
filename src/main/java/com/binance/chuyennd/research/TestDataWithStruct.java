package com.binance.chuyennd.research;

import com.binance.chuyennd.bigchange.data.DataManager;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public class TestDataWithStruct {
    public static final Logger LOG = LoggerFactory.getLogger(TestDataWithStruct.class);

    public static void main(String[] args) {
        changeDataObjectOld2ObjectList();
    }

    private static void changeDataObjectOld2ObjectList() {
        try {
            long startTime = Utils.sdfFile.parse("20250901").getTime();
            for (int i = 0; i < 30; i++) {
                long timeFle = startTime + i * Utils.TIME_DAY + 7 * Utils.TIME_HOUR;
                TreeMap<Long, List<List<Object>>> time2TickersObject = new TreeMap<>();
                LOG.info("Clone file: {}", Configs.FOLDER_TICKER_1M_SNAPPY_FILE + timeFle);
                TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManager.readDataFromFile1M(timeFle);
                for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2Tickers.entrySet()) {
                    Long time = entry.getKey();
                    Map<String, KlineObjectSimple> symbol2Ticker = entry.getValue();
                    List<List<Object>> symbol2Objects = new ArrayList<>();
                    for (String symbol : symbol2Ticker.keySet()) {
                        KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                        List<Object> symbol2Object = new ArrayList<>();
                        symbol2Object.add(symbol);
                        symbol2Object.add(ticker.startTime);
                        symbol2Object.add(ticker.priceOpen);
                        symbol2Object.add(ticker.maxPrice);
                        symbol2Object.add(ticker.minPrice);
                        symbol2Object.add(ticker.priceClose);
                        symbol2Object.add(ticker.totalUsdt);
                        symbol2Objects.add(symbol2Object);
                    }
                    time2TickersObject.put(time, symbol2Objects);
                }
                StorageSnappy.writeObject2File("../storage/ticker/ticker1m-snappy-objects/" + timeFle, time2TickersObject);
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
