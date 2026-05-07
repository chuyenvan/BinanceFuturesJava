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
            this.time = time; this.id = id; this.features = features;
        }
    }

    public static void main(String[] args) throws Exception {
        System.setProperty("java.util.concurrent.ForkJoinPool.common.parallelism", "8");

        String outputDir = "features_export_python/";
        new File(outputDir).mkdirs();

        new ExportFeaturesForPythonTool().startGeneration(outputDir);
    }

    public void startGeneration(String outputDir) throws Exception {
        LOG.info("📥 Đang tải Market Data & Symbol Mapper...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        SimpleDateFormat sdf = new SimpleDateFormat("yyyyMMdd-HHmm");
        FundingFeatureExtractorV2 extractor = new FundingFeatureExtractorV2();

        int currentYear = Calendar.getInstance().get(Calendar.YEAR);

        for (int year = 2021; year <= 2026; year++) {
            String outputFilePath = outputDir + "features_" + year + ".bin.gz";
            File outFile = new File(outputFilePath);

            // LOGIC BỎ QUA: Nếu file tồn tại VÀ năm đó đã kết thúc (year < currentYear)
            if (outFile.exists() && year < currentYear) {
                LOG.info("⏩ File [{}] đã tồn tại và năm {} đã khép lại. BỎ QUA XUẤT LẠI!", outFile.getName(), year);
                continue;
            }

            LOG.info("======================================================");
            LOG.info("🚀 BẮT ĐẦU XUẤT MỚI FEATURES CHO NĂM {} TỪ AEROSPIKE...", year);

            // Setup thời gian Warm-up (Lùi lại 2 ngày cuối năm trước)
            String warmupStr = (year - 1) + "1229-0000";
            String endStr = year + "1231-2359";
            long startFetchTime = sdf.parse(warmupStr).getTime();
            long endFetchTime = sdf.parse(endStr).getTime();
            long startOfYearTs = sdf.parse(year + "0101-0000").getTime();
            long currentTimeMs = System.currentTimeMillis();

            if (startFetchTime > currentTimeMs) continue; // Tương lai -> Bỏ qua
            if (endFetchTime > currentTimeMs) endFetchTime = currentTimeMs; // Chặn mốc cuối ở hiện tại

            try (DataOutputStream dos = new DataOutputStream(
                    new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(outputFilePath))))) {

                int yearRecordCount = 0;
                List<PrepareData> batch = new ArrayList<>();
                long currentDayTs = startFetchTime;

                // VÒNG LẶP ĐỌC THEO TỪNG NGÀY TỪ AEROSPIKE
                while (currentDayTs <= endFetchTime) {
                    // Đọc 1 ngày data (1440 phút)
                    TreeMap<Long, Map<String, KlineObjectSimple>> dailyData =
                            DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentDayTs, 1440);

                    if (dailyData != null && !dailyData.isEmpty()) {
                        for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : dailyData.entrySet()) {
                            long time = timeEntry.getKey();
                            Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                            // 1. Luôn cập nhật lịch sử (Warm-up)
                            extractor.updateMarketHistory(symbol2Ticker);

                            // 2. Nếu nằm trong giai đoạn Warm-up thì bỏ qua, không tính feature
                            if (time < startOfYearTs) continue;

                            // 3. Rút trích Feature
                            final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);
                            List<PrepareData> minuteData = symbol2Ticker.keySet().parallelStream()
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

                    // Tiến tới ngày tiếp theo
                    currentDayTs += 1440 * Utils.TIME_MINUTE;
                    System.out.print("."); // In dấu chấm để biết tool đang chạy
                }

                // Ghi nốt phần còn sót lại trong rổ batch
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
                // Context (5)
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength,

                // Coin Specific (7) - Đã xóa momentum1M để khớp 100% với model ONNX
                f.momentum15M, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock,

                // Basket (5)
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike,

                // Funding (4)
                f.coinFundingRate, f.fundingRateRaw, f.fundingRateAvg24H, f.fundingRateTrend
        };
    }
}