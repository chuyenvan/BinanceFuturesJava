package com.binance.chuyennd.ai_ml.extractor;

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

public class DataContext {

    public static final Logger LOG = LoggerFactory.getLogger(DataContext.class);

    // Du lieu goc (4 nguon)
    public static TreeMap<Long, KlineObjectSimple> ALL_BTC_DATA;
    public static TreeMap<Long, KlineObjectSimple> ALL_ETH_DATA;
    public static TreeMap<Long, MarketDataObject> CACHED_time2MarketData;
    public static ConcurrentHashMap<String, Map<Long, Boolean>> CACHED_symbol2TrendData;

    // Du lieu truy xuat nhanh (bang index)
    public static List<Long> ALL_TIMESTAMPS_LIST;
    public static Map<Long, Integer> TIMESTAMP_TO_INDEX_MAP;
    public static List<KlineObjectSimple> ALL_BTC_KLINES_LIST;
    public static List<Double> ALL_BTC_CLOSE_PRICES_LIST;
    public static List<KlineObjectSimple> ALL_ETH_KLINES_LIST;
    public static List<Double> ALL_ETH_CLOSE_PRICES_LIST;

    public static void loadAllStaticData() throws Exception {
        LOG.info("Bat dau tai du lieu vao DataContext...");

        CACHED_symbol2TrendData = (ConcurrentHashMap<String, Map<Long, Boolean>>) StorageSnappy.readObjectFromFile(Configs.FILE_TREND_BY_TIME);
        LOG.info("Tai xong Trend data.");

        CACHED_time2MarketData = (TreeMap<Long, MarketDataObject>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
        LOG.info("Tai xong Market data.");

        ALL_BTC_DATA = loadKlinesFromFile(Constants.SYMBOL_PAIR_BTC);
        LOG.info("Tai xong BTC data: {} phut", ALL_BTC_DATA.size());

        ALL_ETH_DATA = loadKlinesFromFile(Constants.SYMBOL_PAIR_ETH);
        LOG.info("Tai xong ETH data: {} phut", ALL_ETH_DATA.size());

        ALL_TIMESTAMPS_LIST = new ArrayList<>(ALL_BTC_DATA.keySet());
        TIMESTAMP_TO_INDEX_MAP = new HashMap<>();
        for(int i = 0; i < ALL_TIMESTAMPS_LIST.size(); i++) {
            TIMESTAMP_TO_INDEX_MAP.put(ALL_TIMESTAMPS_LIST.get(i), i);
        }

        ALL_BTC_KLINES_LIST = new ArrayList<>(ALL_BTC_DATA.values());
        ALL_BTC_CLOSE_PRICES_LIST = ALL_BTC_KLINES_LIST.stream().map(k -> k.priceClose).collect(Collectors.toList());

        ALL_ETH_KLINES_LIST = syncKlinesWithTimestamps(ALL_ETH_DATA);
        ALL_ETH_CLOSE_PRICES_LIST = ALL_ETH_KLINES_LIST.stream().map(k -> k.priceClose).collect(Collectors.toList());

        LOG.info("Da dong bo hoa (sync) du lieu BTC va ETH.");
    }

    public static int getTimestampIndex(long timestamp) {
        return TIMESTAMP_TO_INDEX_MAP.getOrDefault(timestamp, -1);
    }

    private static TreeMap<Long, KlineObjectSimple> loadKlinesFromFile(String symbol) throws Exception {
        String filePath = Configs.FOLDER_TICKER_1M + symbol;
        @SuppressWarnings("unchecked")
        List<KlineObjectSimple> ticker1Ms = (List<KlineObjectSimple>) StorageSnappy.readObjectFromFile(filePath);
        if (ticker1Ms == null || ticker1Ms.isEmpty()) throw new RuntimeException("File Kline bi trong: " + filePath);
        TreeMap<Long, KlineObjectSimple> dataMap = new TreeMap<>();
        for (KlineObjectSimple kline : ticker1Ms) {
            dataMap.put(kline.startTime.longValue(), kline);
        }
        return dataMap;
    }

    private static List<KlineObjectSimple> syncKlinesWithTimestamps(TreeMap<Long, KlineObjectSimple> klineMap) {
        List<KlineObjectSimple> syncedList = new ArrayList<>(ALL_TIMESTAMPS_LIST.size());
        KlineObjectSimple lastKnownKline = klineMap.firstEntry().getValue();
        for(Long ts : ALL_TIMESTAMPS_LIST) {
            KlineObjectSimple kline = klineMap.get(ts);
            if (kline != null) {
                lastKnownKline = kline;
            }
            syncedList.add(lastKnownKline);
        }
        return syncedList;
    }
}