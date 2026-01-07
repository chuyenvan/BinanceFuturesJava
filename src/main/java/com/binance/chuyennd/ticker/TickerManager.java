package com.binance.chuyennd.ticker;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataFinalProto;
import com.binance.chuyennd.research.ExportMarketData2File;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.market.FundingRate;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.File;
import java.text.ParseException;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/**
 * @author pc
 */
public class TickerManager {

    public static final Logger LOG = LoggerFactory.getLogger(TickerManager.class);
    public ExecutorService executorService = Executors.newFixedThreadPool(2);

    public static void main(String[] args) throws ParseException {
        new TickerManager().startThreadUpdateTicker1MSimple();
    }

    private void startThreadUpdateTicker1MSimple() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateTicker");
//            if (!new File(Configs.FOLDER_FUNDING_FEE + Constants.SYMBOL_PAIR_BTC).exists()) {
//                startUpdateFundingFee();
//            }
            LOG.info("Start thread ThreadUpdateTicker!");

            ExportMarketData2File exporter = new ExportMarketData2File();
            while (true) {
                try {
                    if (Utils.getCurrentHour() == 4
                            || Utils.getCurrentHour() == 11
                            || Utils.getCurrentHour() == 18) {
                        updateFullTicker1M(Constants.SYMBOL_PAIR_BTC);
                        updateFullTicker1M(Constants.SYMBOL_PAIR_ETH);
                        startUpdateTicker1mSimple(); // ĐÃ SỬA: lưu vào Aerospike
                        exporter.exportMarketEntries();
                        exporter.exportBtcTrendReverse();
                    }

                    if (Utils.getCurrentHour() == 16) {
                        startResetTicker1DAnd4HSimple();
                        startUpdateFundingFee();
                        startResetTicker15mSimple();
                    }
                    Thread.sleep(Utils.TIME_HOUR);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadUpdateTicker: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public static void updateFullTicker1M(String symbol) {
        try {

            String fileName = Configs.FOLDER_TICKER_1M + symbol;
            List<KlineObjectSimple> tickers = null;
            if (new File(fileName).exists()) {
                try {
                    tickers = (List<KlineObjectSimple>) StorageSnappy.readObjectFromFile(fileName);
                    Long startTime = tickers.get(tickers.size() - 1).startTime.longValue();
                    tickers.remove(tickers.size() - 1);
                    while (true) {
//                    LOG.info("Get data: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                        tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
                                Constants.INTERVAL_1M, startTime));
                        startTime = startTime + 500 * Utils.TIME_MINUTE;
                        if (startTime > System.currentTimeMillis()) {
                            break;
                        }
                    }
                } catch (Exception e) {
                    tickers = null;
                    e.printStackTrace();
                }
            }
            if (tickers == null) {
                tickers = new ArrayList<>();
                try {
                    Long startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
                    while (true) {
                        LOG.info("Get data: {}", Utils.normalizeDateYYYYMMDDHHmm(startTime));
                        tickers.addAll(TickerFuturesHelper.getTickerSimpleWithStartTime(symbol,
                                Constants.INTERVAL_1M, startTime));
                        startTime = startTime + 500 * Utils.TIME_MINUTE;
                        if (startTime > System.currentTimeMillis()) {
                            break;
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            StorageSnappy.writeObject2File(fileName, tickers);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startResetTicker15mSimple() {
        try {
            try {
                LOG.info("Start get all ticker 15M: {}", Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                Set<String> symbols = TickerFuturesHelper.getAllSymbol();
                symbols.removeAll(Constants.diedSymbol);
                symbols.add(Constants.SYMBOL_PAIR_BTC);
                symbols.add("ETHUSDT");
                Long startTime = 1672506000000L;
                for (String symbol : symbols) {
                    if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
                        startTime = Utils.sdfFile.parse(Configs.TIME_RUN).getTime() + 7 * Utils.TIME_HOUR;
                    }
                    Long finalStartTime = startTime;
                    executorService.execute(() -> updateDataBySymbolSimple(symbol, Constants.INTERVAL_15M, finalStartTime));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker15m: {}", e);
            e.printStackTrace();
        }
    }

    // PHƯƠNG THỨC MỚI: Lưu dữ liệu 1M vào Aerospike
    private void startUpdateTicker1mSimple() {
        try {
            Set<String> symbols = TickerFuturesHelper.getAllSymbol();
            symbols.removeAll(Constants.diedSymbol);
            symbols.add(Constants.SYMBOL_PAIR_BTC);
            symbols.add(Constants.SYMBOL_PAIR_ETH);

            Long time = Utils.getStartTimeDayAgo(0) + 7 * Utils.TIME_HOUR;
            Long timeEnd2Get = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();

            while (true) {
                if (time < timeEnd2Get) {
                    break;
                }

                LOG.info("Start get data ticker 1m for date: {}", Utils.normalizeDateYYYYMMDDHHmm(time));

                try {
                    TreeMap<Long, Map<String, KlineObjectSimple>> time2Tickers = DataManagerAerospikeFloatSim.readDataFromAerospike1M(time);
                    if (time2Tickers.size() >= 1440) {
                        break;
                    }
                    TreeMap<Long, Map<String, KlineObjectSimple>> time2SymbolAndKline = getAllTicker1MBuyDate(time, symbols);
                    if (time2SymbolAndKline != null && !time2SymbolAndKline.isEmpty()) {
                        LOG.info("Write {} records to Aerospike for date: {}", time2SymbolAndKline.size(), Utils.normalizeDateYYYYMMDDHHmm(time));
                        // LƯU VÀO AEROSPIKE THAY VÌ FILE
                        saveToAerospike(time2SymbolAndKline);
                    }
                } catch (Exception e) {
                    LOG.info("Error get data for date: {}", Utils.normalizeDateYYYYMMDDHHmm(time));
                    e.printStackTrace();
                }
                time = time - Utils.TIME_DAY;
            }

        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker1m: {}", e);
            e.printStackTrace();
        }
    }

    // Thay thế toàn bộ hàm saveToAerospike cũ bằng hàm này
    private void saveToAerospike(TreeMap<Long, Map<String, KlineObjectSimple>> time2SymbolAndKline) {
        try {
            SimpleDateFormat keyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");

            for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : time2SymbolAndKline.entrySet()) {
                Long timestamp = entry.getKey();
                Map<String, KlineObjectSimple> symbolData = entry.getValue();

                // --- 1. CHUYỂN ĐỔI SANG PROTOBUF TỐI ƯU (MinuteDataFinal) ---
                MinuteDataFinalProto.MinuteDataFinal.Builder finalBuilder = MinuteDataFinalProto.MinuteDataFinal.newBuilder();

                for (Map.Entry<String, KlineObjectSimple> item : symbolData.entrySet()) {
                    String symbol = item.getKey();
                    KlineObjectSimple kline = item.getValue();

                    // Xử lý Symbol: Cắt "USDT" nếu cần (để tiết kiệm không gian như DataMigrator)
                    // Hoặc giữ nguyên nếu bạn muốn (nhưng nên thống nhất với DataMigrator)
                    // Ví dụ: Giữ nguyên tên đầy đủ để an toàn
                    String storedSymbol = symbol;

                    MinuteDataFinalProto.KlineObjectOptimized.Builder klineOpt = MinuteDataFinalProto.KlineObjectOptimized.newBuilder();
                    // Ép kiểu Double -> Float
                    klineOpt.setPriceOpen(kline.priceOpen.floatValue());
                    klineOpt.setMaxPrice(kline.maxPrice.floatValue());
                    klineOpt.setMinPrice(kline.minPrice.floatValue());
                    klineOpt.setPriceClose(kline.priceClose.floatValue());
                    klineOpt.setTotalUsdt(kline.totalUsdt.floatValue());

                    // KHÔNG setStartTime (đã bỏ để tối ưu)

                    finalBuilder.putTickers(storedSymbol, klineOpt.build());
                }

                MinuteDataFinalProto.MinuteDataFinal finalData = finalBuilder.build();

                // --- 2. NÉN DỮ LIỆU ---
                byte[] protoAsBytes = finalData.toByteArray();
                byte[] compressedData = Snappy.compress(protoAsBytes);

                // --- 3. GHI VÀO AEROSPIKE (Set: kline_1m_opt) ---
                String keyString = keyFormat.format(new Date(timestamp));

                // Gọi hàm ghi đè (cần update hàm này trong DataManagerAerospike hoặc gọi trực tiếp Client ở đây)
                // Để đơn giản, ta tái sử dụng hàm writeDataToAerospike nhưng truyền tên SET mới
//                DataManagerAerospikeFloatSim.writeMinuteBatch(keyString, compressedData);
            }
            LOG.info("Successfully saved {} records to Aerospike (Optimized Set)", time2SymbolAndKline.size());
        } catch (Exception e) {
            LOG.error("Error saving to Aerospike: {}", e.getMessage());
            e.printStackTrace();
        }
    }

    public void startResetTicker1DAnd4HSimple() {
        try {
            try {
                Set<String> symbols = new HashSet<>();
                symbols.addAll(TickerFuturesHelper.getAllSymbol());
                Long startTime;
                startTime = Utils.sdfFile.parse("20190101").getTime() + 7 * Utils.TIME_HOUR;
                for (String symbol : symbols) {
                    Long finalStartTime = startTime;
                    executorService.execute(() -> updateDataBySymbolSimple(symbol, Constants.INTERVAL_1D, finalStartTime));
                    executorService.execute(() -> updateDataBySymbolSimple(symbol, Constants.INTERVAL_4H, finalStartTime));
                }
            } catch (Exception e) {
                e.printStackTrace();
            }
        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker15m: {}", e);
            e.printStackTrace();
        }
    }


    public void startUpdateFundingFee() {
        try {
            Set<String> symbols = TickerFuturesHelper.getAllSymbol();
            symbols.removeAll(Constants.diedSymbol);
            Long timeStart = Utils.sdfFile.parse(Configs.TIME_RUN).getTime();
            for (String symbol : symbols) {
                updateFundingFeeBySymbol(symbol, timeStart);
                Thread.sleep(5000);
            }
        } catch (Exception e) {
            LOG.error("ERROR during UpdateTicker15m: {}", e);
            e.printStackTrace();
        }
    }

    public void updateFundingFeeBySymbol(String symbol, Long timeStart) {
//        String fileData = Configs.FOLDER_FUNDING_FEE + symbol;
//        File file = new File(fileData);
//        Long time = timeStart;
//        TreeMap<Long, FundingRate> time2FundingRate = new TreeMap<>();
//        if (file.exists()) {
//            try {
//                time2FundingRate = (TreeMap<Long, FundingRate>) Storage.readObjectFromFile(fileData);
//                if (time2FundingRate != null && time2FundingRate.size() > 0) {
//                    time = time2FundingRate.lastKey() + Utils.TIME_HOUR;
//                }
//            } catch (Exception e) {
//                e.printStackTrace();
//            }
//        }
//        try {
//            if (time2FundingRate == null) {
//                time2FundingRate = new TreeMap<>();
//            }
////            LOG.info("Start get funding fee for: {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time));
//            while (true) {
//                if (time + Utils.TIME_HOUR > System.currentTimeMillis()) {
//                    break;
//                }
//                try {
//                    TreeMap<Long, FundingRate> time2Rate = TickerFuturesHelper.getFundingFeeWithStartTime(symbol, time);
//                    if (time2Rate == null
//                            || time2Rate.isEmpty()) {
//                        break;
//                    } else {
//                        time2FundingRate.putAll(time2Rate);
//                        time = time2Rate.lastKey() + Utils.TIME_HOUR;
//                    }
//                } catch (Exception e) {
//                    LOG.info("Error get funding rate for : {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time));
//                    e.printStackTrace();
//                    break;
//                }
//                Thread.sleep(300);
//            }
////            LOG.info("Write funding fee for: {} {} {}", symbol, time2FundingRate.size(), Utils.normalizeDateYYYYMMDDHHmm(time));
//            Storage.writeObject2File(fileData, time2FundingRate);
//        } catch (Exception e) {
//            LOG.info("Error get funding rate for : {} {}", symbol, Utils.normalizeDateYYYYMMDDHHmm(time));
//            e.printStackTrace();
//        }
    }

    private TreeMap<Long, Map<String, KlineObjectSimple>> getAllTicker1MBuyDate(Long time, Set<String> symbols) {
        TreeMap<Long, Map<String, KlineObjectSimple>> time2SymbolAndKline = new TreeMap<>();
        Long startTime = time;
        while (true) {
            for (String symbol : symbols) {
                try {
                    List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M, startTime);
                    for (KlineObjectSimple ticker : tickers) {
                        if (ticker.startTime.longValue() < time + Utils.TIME_DAY) {
                            Map<String, KlineObjectSimple> symbol2Ticker = time2SymbolAndKline.get(ticker.startTime.longValue());
                            if (symbol2Ticker == null) {
                                symbol2Ticker = new HashMap<>();
                                time2SymbolAndKline.put(ticker.startTime.longValue(), symbol2Ticker);
                            }
                            symbol2Ticker.put(symbol, ticker);
                        }
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            startTime = startTime + 500 * Utils.TIME_MINUTE;
            if (startTime - Utils.TIME_DAY > time) {
                break;
            }
        }
        return time2SymbolAndKline;
    }

    public void updateDataBySymbolSimple(String symbol, String interval, Long startTime) {
        try {
//            LOG.info("Process: {}/{}", counter, total);
//            LOG.info("Start get ticker symbol: {} {} {}", symbol, interval, Utils.normalizeDateYYYYMMDDHHmm(startTime));
            String fileName = null;
            switch (interval) {
                case Constants.INTERVAL_1D:
                    fileName = Configs.FOLDER_TICKER_1D;
                    break;
                case Constants.INTERVAL_4H:
                    fileName = Configs.FOLDER_TICKER_4HOUR;
                    break;
                case Constants.INTERVAL_1H:
                    fileName = Configs.FOLDER_TICKER_HOUR;
                    break;
                case Constants.INTERVAL_15M:
                    fileName = Configs.FOLDER_TICKER_15M;
                    break;
                case Constants.INTERVAL_1M:
                    fileName = Configs.FOLDER_TICKER_1M;
                    break;
            }
            fileName = fileName + symbol;
            List<KlineObjectNumber> tickers = null;
            if (new File(fileName).exists()) {
                try {
                    tickers = (List<KlineObjectNumber>) Storage.readObjectFromFile(fileName);
                    startTime = tickers.get(tickers.size() - 1).startTime.longValue();
                    tickers.remove(tickers.size() - 1);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            if (tickers == null) {
                tickers = new ArrayList<>();
            }
            tickers.addAll(TickerFuturesHelper.getTickerWithStartTimeFull(symbol, interval, startTime));
//            tickers = TickerFuturesHelper.updateIndicator(tickers);
//            LOG.info("Write ticker of {} {} {} to file: {}", symbol, interval, tickers.size(), fileName);
            Storage.writeObject2File(fileName, tickers);
//            LOG.info("Finish get ticker symbol: {} {}", symbol, interval);

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

}
