package com.binance.chuyennd.bigchange.data;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.KlineArchiveProto;
import com.binance.chuyennd.proto.KlineProto;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageProto;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class DataManager {
    public static final Logger LOG = LoggerFactory.getLogger(DataManager.class);

    private static volatile DataManager INSTANCE = null;
    public ConcurrentHashMap<String, Map<String, Map<Long, KlineObjectNumber>>> interval2Symbol2TimeAndTicker;
    public ConcurrentHashMap<String, Map<String, List<KlineObjectNumber>>> interval2Symbol2Tickers;

    public static DataManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new DataManager();
            try {
                Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
                INSTANCE.initData(startTime);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return INSTANCE;
    }


    public static TreeMap<Long, Map<String, KlineObjectSimple>> readDataFromFile1M(long startTime) {
        String fileName = Configs.FOLDER_TICKER_1M_PROTOBUF_SNAPPY_FILE + startTime + ".pb";
        File dataFile = new File(fileName);
        if (!dataFile.exists()) {
            LOG.warn("Protobuf data file does not exist: {}", fileName);
            return null;
        }

        KlineArchiveProto.KlineArchive archive = StorageProto.readProtoWithSnappy(fileName);
        if (archive == null) {
            LOG.error("Failed to read or parse Protobuf file: {}", fileName);
            return null;
        }

        return convertProtoArchiveToOldStructure(archive);
    }


    public static TreeMap<Long, Map<String, KlineObjectSimple>> convertProtoArchiveToOldStructure(KlineArchiveProto.KlineArchive archive) {
        TreeMap<Long, Map<String, KlineObjectSimple>> time2SymbolAndKline = new TreeMap<>();
        if (archive == null) {
            return null;
        }

        Map<String, KlineArchiveProto.SymbolKlines> symbolKlinesMap = archive.getSymbolKlinesMap();

        for (Map.Entry<String, KlineArchiveProto.SymbolKlines> symbolEntry : symbolKlinesMap.entrySet()) {
            String symbol = symbolEntry.getKey();
            Map<Long, KlineProto.KlineObjectSimpleProto> timeToKlineProtoMap = symbolEntry.getValue().getTimeToKlineMap();

            for (Map.Entry<Long, KlineProto.KlineObjectSimpleProto> timeEntry : timeToKlineProtoMap.entrySet()) {
                Long time = timeEntry.getKey();
                KlineObjectSimple simpleKline = convertKlineProtoToSimple(timeEntry.getValue());
                time2SymbolAndKline.computeIfAbsent(time, k -> new HashMap<>()).put(symbol, simpleKline);
            }
        }
        return time2SymbolAndKline;
    }

    public static KlineObjectSimple convertKlineProtoToSimple(KlineProto.KlineObjectSimpleProto protoKline) {
        KlineObjectSimple simpleKline = new KlineObjectSimple();
        simpleKline.startTime = (double) protoKline.getStartTime();
        simpleKline.priceOpen = (double) protoKline.getPriceOpen();
        simpleKline.maxPrice = (double) protoKline.getMaxPrice();
        simpleKline.minPrice = (double) protoKline.getMinPrice();
        simpleKline.priceClose = (double) protoKline.getPriceClose();
        simpleKline.totalUsdt = (double) protoKline.getTotalUsdt();
        return simpleKline;
    }


    private void initData(Long startTime) {
        String fileData = Configs.FILE_DATA_LOADED + startTime;
        if (new File(fileData).exists()) {
            interval2Symbol2Tickers = (ConcurrentHashMap<String, Map<String, List<KlineObjectNumber>>>) Storage.readObjectFromFile(fileData);
        } else {
            interval2Symbol2Tickers = new ConcurrentHashMap<>();
            interval2Symbol2Tickers.put(Constants.INTERVAL_1H, getData(Constants.INTERVAL_1H, startTime));
            interval2Symbol2Tickers.put(Constants.INTERVAL_4H, getData(Constants.INTERVAL_4H, startTime));
            interval2Symbol2Tickers.put(Constants.INTERVAL_1D, getData(Constants.INTERVAL_1D, startTime));
            Storage.writeObject2File(fileData, interval2Symbol2Tickers);
        }
        interval2Symbol2TimeAndTicker = new ConcurrentHashMap<>();
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1H, traceData(interval2Symbol2Tickers.get(Constants.INTERVAL_1H)));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_4H, traceData(interval2Symbol2Tickers.get(Constants.INTERVAL_4H)));
        interval2Symbol2TimeAndTicker.put(Constants.INTERVAL_1D, traceData(interval2Symbol2Tickers.get(Constants.INTERVAL_1D)));
    }

    private Map<String, Map<Long, KlineObjectNumber>> traceData(Map<String, List<KlineObjectNumber>> symbol2Tickers) {
        Map<String, Map<Long, KlineObjectNumber>> results = new HashMap<>();
        for (Map.Entry<String, List<KlineObjectNumber>> entry : symbol2Tickers.entrySet()) {
            String symbol = entry.getKey();
            List<KlineObjectNumber> tickers = entry.getValue();
            Map<Long, KlineObjectNumber> time2Ticker = new HashMap<>();
            for (KlineObjectNumber ticker : tickers) {
                time2Ticker.put(ticker.startTime.longValue(), ticker);
            }
            results.put(symbol, time2Ticker);
        }
        return results;
    }

    private Map<String, List<KlineObjectNumber>> getData(String interval, Long startTime) {
        Map<String, List<KlineObjectNumber>> results = new HashMap<>();
        String folderData = null;
        switch (interval) {
            case Constants.INTERVAL_1H:
                folderData = Configs.FOLDER_TICKER_HOUR;
                break;
            case Constants.INTERVAL_4H:
                folderData = Configs.FOLDER_TICKER_4HOUR;
                break;
            case Constants.INTERVAL_1D:
                folderData = Configs.FOLDER_TICKER_1D;
                break;
        }
        if (folderData != null) {
            File[] symbolFiles = new File(folderData).listFiles();
            for (File symbolFile : symbolFiles) {
                String symbol = symbolFile.getName();
                if (!StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                    continue;
                }
                List<KlineObjectNumber> tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(symbolFile.getPath());
                results.put(symbol, tickers);
            }
        }
        return results;
    }




}
