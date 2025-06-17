package com.binance.chuyennd.grid;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.ticker.TickerManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.ObjectInputFilter;
import java.text.ParseException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

public class Price4hManager {
    public static final Logger LOG = LoggerFactory.getLogger(Price4hManager.class);
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2Time2PriceMin = new ConcurrentHashMap<>();
    public Double priceMin;
    public Double priceMax;
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2Time2PriceMax = new ConcurrentHashMap<>();
    private static volatile Price4hManager INSTANCE = null;

    public static Price4hManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new Price4hManager();
            INSTANCE.startThreadUpdateData();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws ParseException {
        long startTime = Utils.sdfFile.parse("20190101").getTime() + 7 * Utils.TIME_HOUR;
        new TickerManager().updateDataBySymbolSimple("UNFIUSDT", Constants.INTERVAL_4H, startTime);

        String symbol = "BTCUSDT";
        Long time = Utils.sdfFileHour.parse("20250208 23:45").getTime();
        System.out.println(Price4hManager.getInstance().getPriceMinIn2D(symbol, time));
        System.out.println(Price4hManager.getInstance().getPriceMaxIn2D(symbol, time));
    }

    public Double getPriceMinIn2D(String symbol, Long time) {
        Map<Long, Double> time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin == null) {
            updateForSymbol(symbol);
        }
        time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin != null) {
            long lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR;
            Double minPrice = time2PriceMin.get(lastTime);
            if (minPrice == null) {
                return null;
            }
            for (int i = 2; i < 30; i++) {
                lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR * i;
//                LOG.info("time4h manager: {} {}",Utils.normalizeDateYYYYMMDDHHmm(lastTime), Utils.normalizeDateYYYYMMDDHHmm(time));
                if (time2PriceMin.get(lastTime) != null) {
                    minPrice = Math.min(minPrice, time2PriceMin.get(lastTime));
                }
            }
            return minPrice;
        }
        return null;
    }

    public Double getPriceMinBeforeIn2D(String symbol, Long time) {
        Map<Long, Double> time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin == null) {
            updateForSymbol(symbol);
        }
        time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin != null) {
            long lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR;
            Double minPrice = time2PriceMin.get(lastTime);
            if (minPrice == null) {
                return null;
            }
            for (int i = 2; i < 12; i++) {
                lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR * i;
//                LOG.info("time4h manager: {} {}",Utils.normalizeDateYYYYMMDDHHmm(lastTime), Utils.normalizeDateYYYYMMDDHHmm(time));
                if (time2PriceMin.get(lastTime) != null) {
                    minPrice = Math.min(minPrice, time2PriceMin.get(lastTime));
                }
            }
            return minPrice;
        }
        return null;
    }

    public Double getPriceMaxIn2D(String symbol, Long time) {
        Map<Long, Double> time2PriceMax = symbol2Time2PriceMax.get(symbol);
        if (time2PriceMax == null) {
            updateForSymbol(symbol);
        }
        time2PriceMax = symbol2Time2PriceMax.get(symbol);
        if (time2PriceMax != null) {
            long lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR;
            Double maxPrice = time2PriceMax.get(lastTime);
            if (maxPrice == null) {
                return null;
            }
            for (int i = 2; i < 20; i++) {
                lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR * i;
                if (time2PriceMax.get(lastTime) != null) {
                    maxPrice = Math.max(maxPrice, time2PriceMax.get(lastTime));
                }
            }
            return maxPrice;
        }
        return null;
    }

    public Double getPriceMinIn7D(String symbol, Long time) {
        Map<Long, Double> time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin == null) {
            updateForSymbol(symbol);
        }
        time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin != null) {
            long lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR;
            Double minPrice = time2PriceMin.get(lastTime);
            if (minPrice == null) {
                return null;
            }
            for (int i = 2; i < 43; i++) {
                lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR * i;
//                LOG.info("time4h manager: {} {}",Utils.normalizeDateYYYYMMDDHHmm(lastTime), Utils.normalizeDateYYYYMMDDHHmm(time));
                if (time2PriceMin.get(lastTime) != null) {
                    minPrice = Math.min(minPrice, time2PriceMin.get(lastTime));
                }
            }
            return minPrice;
        }
        return null;
    }

    public Double getPriceMin(String symbol) {
        Map<Long, Double> time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin == null) {
            updateForSymbol(symbol);
        }
        return priceMin;
    }

    public Double getPriceMax(String symbol) {
        Map<Long, Double> time2PriceMin = symbol2Time2PriceMin.get(symbol);
        if (time2PriceMin == null) {
            updateForSymbol(symbol);
        }
        return priceMax;
    }

    private void startThreadUpdateData() {
        File folder = new File(Configs.FOLDER_TICKER_4HOUR);
        Set<String> hashSet = new HashSet<>();
        for (File file : folder.listFiles()) {
            hashSet.add(file.getName());
        }
        for (String symbol : hashSet) {
            updateForSymbol(symbol);
        }
    }

    private void updateForSymbol(String symbol) {
        try {
            List<KlineObjectNumber> ticker4Hours =
                    (List<KlineObjectNumber>) Storage.readObjectFromFile(Configs.FOLDER_TICKER_4HOUR + symbol);
            TreeMap<Long, Double> time2PriceMin = new TreeMap<>();
            TreeMap<Long, Double> time2PriceMax = new TreeMap<>();
            if (ticker4Hours == null) {
                return;
            }
            for (KlineObjectNumber ticker : ticker4Hours) {
                time2PriceMin.put(ticker.startTime.longValue(), ticker.minPrice);
                time2PriceMax.put(ticker.startTime.longValue(), ticker.maxPrice);
                priceMin = Utils.minPrice(ticker, priceMin);
                priceMax = Utils.maxPrice(ticker, priceMax);
            }
            symbol2Time2PriceMin.put(symbol, time2PriceMin);
            symbol2Time2PriceMax.put(symbol, time2PriceMax);
        } catch (Exception e) {
            LOG.info("Error get price 4h of sym: {}", symbol);
            e.printStackTrace();
        }
    }


}
