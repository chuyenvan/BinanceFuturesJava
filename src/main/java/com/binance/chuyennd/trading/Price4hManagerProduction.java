package com.binance.chuyennd.trading;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.grid.Price4hManager;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.text.ParseException;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class Price4hManagerProduction {
    public static final Logger LOG = LoggerFactory.getLogger(Price4hManagerProduction.class);
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2Time2PriceMin = new ConcurrentHashMap<>();
    public ConcurrentHashMap<String, TreeMap<Long, Double>> symbol2Time2PriceMax = new ConcurrentHashMap<>();
    public static final String FILE_DATA_PRICE_MAX = "storage/price/max.data";
    public static final String FILE_DATA_PRICE_MIN = "storage/price/min.data";
    private static volatile Price4hManagerProduction INSTANCE = null;

    public static Price4hManagerProduction getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new Price4hManagerProduction();
            INSTANCE.startThreadUpdateData();
            if (new File(FILE_DATA_PRICE_MAX).exists()) {
                INSTANCE.symbol2Time2PriceMax = (ConcurrentHashMap<String, TreeMap<Long, Double>>) Storage.readObjectFromFile(FILE_DATA_PRICE_MAX);
                INSTANCE.symbol2Time2PriceMin = (ConcurrentHashMap<String, TreeMap<Long, Double>>) Storage.readObjectFromFile(FILE_DATA_PRICE_MIN);
            } else {
                INSTANCE.updateAllData();
            }
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws ParseException {
        String symbol = "ASRUSDT";
        Long time = Utils.sdfFileHour.parse("20250726 08:15").getTime();
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

    public Double getPriceMaxIn2D(String symbol, Long time) {
        Map<Long, Double> time2PriceMax = symbol2Time2PriceMax.get(symbol);
        if (time2PriceMax == null) {
            updateForSymbol(symbol);
        }
        time2PriceMax = symbol2Time2PriceMax.get(symbol);
        if (time2PriceMax != null) {
            long lastTime = Utils.get4Hour(time) - 4 * Utils.TIME_HOUR;
            Double maxPrice = time2PriceMax.get(lastTime);
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

    private void startThreadUpdateData() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdatePriceAllSymbol");
            LOG.info("Start thread ThreadUpdatePriceAllSymbol !");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR);
                } catch (Exception e) {
                    e.printStackTrace();
                }
                updateAllData();
            }
        }).start();
    }

    private void updateAllData() {
        try {
            Set<String> allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            allSymbol.removeAll(Constants.diedSymbol);
            for (String symbol : allSymbol) {
                updateForSymbol(symbol);
            }
            Storage.writeObject2File(FILE_DATA_PRICE_MAX, symbol2Time2PriceMax);
            Storage.writeObject2File(FILE_DATA_PRICE_MIN, symbol2Time2PriceMin);
        } catch (Exception e) {
            LOG.error("ERROR during ThreadUpdatePriceAllSymbol: {}", e);
            e.printStackTrace();
        }
    }

    private void updateForSymbol(String symbol) {
        try {
            List<KlineObjectNumber> ticker4Hours = TickerFuturesHelper.getTicker(symbol, Constants.INTERVAL_4H);
            TreeMap<Long, Double> time2PriceMin = new TreeMap<>();
            TreeMap<Long, Double> time2PriceMax = new TreeMap<>();
            if (ticker4Hours == null) {
                return;
            }
            for (KlineObjectNumber ticker : ticker4Hours) {
                time2PriceMin.put(ticker.startTime.longValue(), ticker.minPrice);
                time2PriceMax.put(ticker.startTime.longValue(), ticker.maxPrice);
            }
            symbol2Time2PriceMin.put(symbol, time2PriceMin);
            symbol2Time2PriceMax.put(symbol, time2PriceMax);
        } catch (Exception e) {
            LOG.info("Error get price 4h of sym: {}", symbol);
            e.printStackTrace();
        }
    }


}
