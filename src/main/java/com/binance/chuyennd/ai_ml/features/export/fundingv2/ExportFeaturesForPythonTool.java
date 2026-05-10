package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;
import java.util.zip.GZIPOutputStream;

public class ExportFeaturesForPythonTool {
    private static final Logger LOG = LoggerFactory.getLogger(ExportFeaturesForPythonTool.class);

    private static class PrepareData {
        long time;
        short id;
        float[] features;

        public PrepareData(long time, short id, float[] features) {
            this.time = time;
            this.id = id;
            this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        String outputDir = "features_export_python/";
        new File(outputDir).mkdirs();

        new ExportFeaturesForPythonTool().startGeneration(outputDir);
    }

    public void startGeneration(String outputDir) throws Exception {
        LOG.info("📥 Đang tải Market Data & Symbol Mapper...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        SimpleDateFormat sdfFull = new SimpleDateFormat("yyyyMMdd-HHmm");
        FundingFeatureExtractorV2 extractor = new FundingFeatureExtractorV2();

        int currentYear = Calendar.getInstance().get(Calendar.YEAR);
        long now = System.currentTimeMillis();

        // 🔄 VÒNG LẶP THEO NĂM
        for (int year = 2021; year <= 2026; year++) {
            String outputFilePath = outputDir + "features_" + year + ".bin.gz";
            File outFile = new File(outputFilePath);

            long startOfYearTs = sdfFull.parse(year + "0101-0000").getTime();
            long endOfYearTs = sdfFull.parse(year + "1231-2359").getTime();

            if (endOfYearTs > now) endOfYearTs = now;
            if (startOfYearTs > now) continue;

            if (outFile.exists() && year < currentYear) {
                LOG.info("⏩ File [{}] đã tồn tại. BỎ QUA NĂM {}!", outFile.getName(), year);
                continue;
            }

            LOG.info("======================================================");
            LOG.info("🚀 BẮT ĐẦU XUẤT MỚI FEATURES CHO NĂM {} TỪ AEROSPIKE...", year);

            // 🔥 ĐÃ TRẢ LẠI WARM-UP CHUẨN 48 TIẾNG (2 NGÀY) TÍNH TỪ ĐẦU NĂM
            long warmupStartTs = startOfYearTs - (48 * 3600000L);

            LOG.info("   - Thời gian Warmup bắt đầu từ: {}", sdfFull.format(new Date(warmupStartTs)));
            LOG.info("   - Thời gian ghi File bắt đầu từ: {}", sdfFull.format(new Date(startOfYearTs)));

            // DỌN DẸP SẠCH SẼ TRƯỚC KHI CHẠY NĂM MỚI
            CoinRankManager.getInstance().resetCache();

            try (DataOutputStream dos = new DataOutputStream(
                    new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(outputFilePath)), 1024 * 1024))) {

                int yearRecordCount = 0;
                List<PrepareData> batch = new ArrayList<>();
                long currentReadTs = warmupStartTs;

                while (currentReadTs <= endOfYearTs) {
                    int minutesToRead = 1440;
                    if (currentReadTs + minutesToRead * Utils.TIME_MINUTE > endOfYearTs) {
                        minutesToRead = (int) ((endOfYearTs - currentReadTs) / Utils.TIME_MINUTE) + 1;
                    }

                    TreeMap<Long, Map<String, KlineObjectSimple>> dailyData =
                            DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentReadTs, minutesToRead);

                    if (dailyData != null && !dailyData.isEmpty()) {
                        for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : dailyData.entrySet()) {
                            long time = timeEntry.getKey();
                            Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                            // 1. Luôn cập nhật lịch sử (Dù là đang Warm-up hay Ghi file)
                            extractor.updateMarketHistory(symbol2Ticker);

                            // 2. CHẶN GHI FILE NẾU ĐANG TRONG GIAI ĐOẠN WARM-UP
                            if (time < startOfYearTs) continue;

                            // 3. Rút trích Feature
                            final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                            // 🔥 CHẠY .stream() TUẦN TỰ ĐỂ AN TOÀN TUYỆT ĐỐI CHO MẢNG HISTORY
                            List<PrepareData> minuteData = symbol2Ticker.keySet().stream()
                                    .map(symbol -> {
                                        try {
                                            Short symId = symbolMap.get(symbol);
                                            KlineObjectSimple ticker = symbol2Ticker.get(symbol);
                                            if (symId == null || ticker == null || !Utils.isTickerAvailable(ticker)) return null;

                                            OrderTargetInfoTest dummyOrder = new OrderTargetInfoTest(
                                                    OrderTargetStatus.REQUEST, ticker.priceClose, null, 1.0f,
                                                    Configs.LEVERAGE_ORDER, symbol, time, time, OrderSide.BUY
                                            );
                                            dummyOrder.lastEntry = ticker.priceClose;

                                            FundingMarketFeatures features = extractor.extractFeatures(
                                                    time, dummyOrder, symbol2Ticker, time2MarketData.get(time), basket);

                                            if (features != null) {
                                                return new PrepareData(time, symId, convertFeaturesToArray(features));
                                            }
                                        } catch (Exception e) {}
                                        return null;
                                    })
                                    .filter(Objects::nonNull)
                                    .collect(Collectors.toList());

                            batch.addAll(minuteData);

                            // 4. Batch ghi file
                            if (batch.size() >= 100000) {
                                for (PrepareData pd : batch) {
                                    dos.writeLong(pd.time);
                                    dos.writeShort(pd.id);
                                    for (float f : pd.features) dos.writeFloat(f);
                                }
                                yearRecordCount += batch.size();
                                batch.clear();
                            }
                        }
                    }

                    currentReadTs += minutesToRead * Utils.TIME_MINUTE;
                    System.out.print(".");
                }

                if (!batch.isEmpty()) {
                    for (PrepareData pd : batch) {
                        dos.writeLong(pd.time);
                        dos.writeShort(pd.id);
                        for (float f : pd.features) dos.writeFloat(f);
                    }
                    yearRecordCount += batch.size();
                    batch.clear();
                }

                LOG.info("\n🎉 HOÀN TẤT NĂM {}! Tổng cộng {} records đã được ghi.", year, yearRecordCount);
            }
        }
        LOG.info("🏁 HOÀN TẤT TOÀN BỘ QUÁ TRÌNH XUẤT FEATURES!");
        System.exit(0);
    }

    private float[] convertFeaturesToArray(FundingMarketFeatures f) {
        return new float[]{
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength,
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock,
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike,
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend
        };
    }
}