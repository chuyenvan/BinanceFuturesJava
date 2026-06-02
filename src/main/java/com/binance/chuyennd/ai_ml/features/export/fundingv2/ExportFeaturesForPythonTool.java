package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingDataCollectionManager;
import com.binance.chuyennd.ai_ml.features.export.funding.FundingMarketFeatures;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.tradecore.CoinRankManager;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
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

        SimpleDateFormat sdfFull = new SimpleDateFormat("yyyyMMdd HH:mm");
        SimpleDateFormat sdfFile = new SimpleDateFormat("yyyyMMdd");
        FundingDataCollectionManager.FundingFeatureExtractorV2 extractor = new FundingDataCollectionManager.FundingFeatureExtractorV2();

        // 1. CÀI ĐẶT CÁC MỐC THỜI GIAN THEO YÊU CẦU
        long targetStartTs = sdfFull.parse("20210101 07:00").getTime();
        long warmupStartTs = targetStartTs - (48 * 3600000L); // Warmup 48h
        long globalEndTs = System.currentTimeMillis(); // Kéo đến hiện tại

        LOG.info("======================================================");
        LOG.info("🚀 BẮT ĐẦU XUẤT FEATURES (LIÊN TỤC KHÔNG RESET STATE)");
        LOG.info("   - Thời gian Warmup: {}", sdfFull.format(new Date(warmupStartTs)));
        LOG.info("   - Thời gian bắt đầu ghi File: {}", sdfFull.format(new Date(targetStartTs)));
        LOG.info("   - Thời gian kết thúc (Hiện tại): {}", sdfFull.format(new Date(globalEndTs)));
        LOG.info("======================================================");

        long currentReadTs = warmupStartTs;

        // Quản lý chia file 3 tháng/lần
        long chunkStartTs = targetStartTs;
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(chunkStartTs);
        cal.add(Calendar.MONTH, 3);
        long chunkEndTs = cal.getTimeInMillis();

        DataOutputStream dos = null;
        String currentFilePath = "";
        int fileRecordCount = 0;
        List<PrepareData> batch = new ArrayList<>();

        try {
            // VÒNG LẶP LIÊN TỤC KHÔNG RESET
            while (currentReadTs <= globalEndTs) {
                int minutesToRead = 1440;
                if (currentReadTs + minutesToRead * Utils.TIME_MINUTE > globalEndTs) {
                    minutesToRead = (int) ((globalEndTs - currentReadTs) / Utils.TIME_MINUTE) + 1;
                }

                if (minutesToRead <= 0) break;

                TreeMap<Long, Map<String, KlineObjectSimple>> dailyData =
                        DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentReadTs, minutesToRead);

                if (dailyData != null && !dailyData.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : dailyData.entrySet()) {
                        long time = timeEntry.getKey();
                        Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                        // [QUAN TRỌNG NHẤT]: Luôn nạp State liên tục
                        extractor.updateMarketHistory(symbol2Ticker);
                        final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                        // Bỏ qua nếu vẫn đang trong giai đoạn Warmup
                        if (time < targetStartTs) continue;

                        // KIỂM TRA MỐC CẮT FILE (3 THÁNG)
                        if (time >= chunkEndTs) {
                            if (dos != null) {
                                writeBatch(dos, batch);
                                fileRecordCount += batch.size();
                                batch.clear();
                                dos.close();
                                LOG.info("\n🎉 Đã đóng file: {} (Tổng: {} records)", currentFilePath, fileRecordCount);
                            }

                            // Cập nhật mốc 3 tháng tiếp theo
                            chunkStartTs = chunkEndTs;
                            cal.setTimeInMillis(chunkStartTs);
                            cal.add(Calendar.MONTH, 3);
                            chunkEndTs = cal.getTimeInMillis();
                            dos = null; // Kích hoạt tạo file mới ở dưới
                        }

                        // MỞ FILE MỚI NẾU CẦN
                        if (dos == null) {
                            currentFilePath = outputDir + "features_" + sdfFile.format(new Date(chunkStartTs))
                                    + "_to_" + sdfFile.format(new Date(chunkEndTs)) + ".bin.gz";
                            LOG.info("📂 Đang tạo file mới: {}", currentFilePath);
                            dos = new DataOutputStream(new BufferedOutputStream(new GZIPOutputStream(new FileOutputStream(currentFilePath)), 1024 * 1024));
                            fileRecordCount = 0;
                        }

                        // TRÍCH XUẤT FEATURE BẰNG SINGLE THREAD (stream)
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

                        // FLUSH XUỐNG FILE KHI BATCH ĐẦY ĐỂ TRÁNH TRÀN RAM
                        if (batch.size() >= 100000) {
                            writeBatch(dos, batch);
                            fileRecordCount += batch.size();
                            batch.clear();
                        }
                    }
                }

                currentReadTs += minutesToRead * Utils.TIME_MINUTE;
                System.out.print(".");
            }

            // DỌN DẸP CUỐI CÙNG (Đóng file cuối cùng đang ghi dở)
            if (dos != null) {
                if (!batch.isEmpty()) {
                    writeBatch(dos, batch);
                    fileRecordCount += batch.size();
                    batch.clear();
                }
                dos.close();
                LOG.info("\n🎉 Đã đóng file cuối: {} (Tổng: {} records)", currentFilePath, fileRecordCount);
            }

        } catch (Exception e) {
            LOG.error("❌ Lỗi trong quá trình xuất feature", e);
        }

        LOG.info("🏁 HOÀN TẤT TOÀN BỘ QUÁ TRÌNH XUẤT FEATURES!");
        System.exit(0);
    }

    private void writeBatch(DataOutputStream dos, List<PrepareData> batch) throws IOException {
        for (PrepareData pd : batch) {
            dos.writeLong(pd.time);
            dos.writeShort(pd.id);
            for (float f : pd.features) dos.writeFloat(f);
        }
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