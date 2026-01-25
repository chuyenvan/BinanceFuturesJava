package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;

public class RunDcaDataCollection {
    private static final Logger LOG = LoggerFactory.getLogger(RunDcaDataCollection.class);
    private final Random rand = new Random();

    // Map lưu thời gian lấy mẫu gần nhất để cooldown
    private final Map<String, Long> symbolLastSampledTime = new HashMap<>();

    // Extractor dùng để check Volatility trước khi quyết định lưu
    private final DcaFeatureExtractor preCheckExtractor = new DcaFeatureExtractor();

    public static void main(String[] args) throws Exception {
        // Init Funding Manager
        try {
            FundingFeeManager.getInstance();
            LOG.info("✅ FundingFeeManager Initialized!");
        } catch (Exception e) {
            LOG.error("❌ Failed to init FundingFeeManager", e);
            return;
        }
        new RunDcaDataCollection().run();
    }

    // Cache data để lookup tương lai (tối ưu tốc độ đọc đĩa)
    private final Map<Long, TreeMap<Long, Map<String, KlineObjectSimple>>> dataCache = new HashMap<>();

    public void run() throws Exception {
        // Folder lưu data tinh gọn (Clean Data)
        DcaDataCollectionManager manager = new DcaDataCollectionManager("storage/training_data_dca");

        LOG.info("🚀 Loading Market Rates...");
        TreeMap<Long, MarketRateChange> time2Rate = loadMarketRateData();
        LOG.info("🚀 Loading Market Rates Done {}", time2Rate.size());

        long startTime = Utils.sdfFile.parse("20210101").getTime();
        long warmUpTime = startTime - Utils.TIME_DAY; // Load trước 1 ngày để warm-up indicator
        long endTime = System.currentTimeMillis();
        long currentTime = warmUpTime;

        while (currentTime <= endTime) {
            try {
                long t0 = System.currentTimeMillis();

                // 1. Lấy Data Hôm Nay (T)
                if (!dataCache.containsKey(currentTime)) {
                    LOG.info("📥 Loading data for day: {}", Utils.normalizeDateYYYYMMDD(currentTime));
                    TreeMap<Long, Map<String, KlineObjectSimple>> d = DataManagerAerospikeFloatSim.readDataFromAerospike1M(currentTime);
                    if (d != null) dataCache.put(currentTime, d);
                }
                TreeMap<Long, Map<String, KlineObjectSimple>> dataDay0 = dataCache.get(currentTime);

                // 2. Chuẩn bị Lookup Data (T, T+1, T+2, T+3) cho Labeling
                TreeMap<Long, Map<String, KlineObjectSimple>> lookupData = new TreeMap<>();
                if (dataDay0 != null) lookupData.putAll(dataDay0);

                // Load trước các ngày tương lai
                for (int i = 1; i <= 3; i++) {
                    long nextDay = currentTime + ((long) i * Utils.TIME_DAY);
                    if (nextDay > endTime) break;

                    if (!dataCache.containsKey(nextDay)) {
                        TreeMap<Long, Map<String, KlineObjectSimple>> dNext = DataManagerAerospikeFloatSim.readDataFromAerospike1M(nextDay);
                        if (dNext != null) dataCache.put(nextDay, dNext);
                    }
                    TreeMap<Long, Map<String, KlineObjectSimple>> dNextCache = dataCache.get(nextDay);
                    if (dNextCache != null) {
                        lookupData.putAll(dNextCache);
                    }
                }

                // 3. XÓA DATA CŨ (Giải phóng RAM)
                long prevDay = currentTime - Utils.TIME_DAY;
                dataCache.remove(prevDay);

                long tLoad = System.currentTimeMillis();

                // 4. Xử lý dữ liệu
                if (dataDay0 != null) {
                    processDay(dataDay0, lookupData, time2Rate, manager, currentTime >= startTime);
                }

                long tProcess = System.currentTimeMillis();

                // 5. Export & Log
                if (currentTime >= startTime) {
                    manager.exportData(); // Ghi ra file csv
                    LOG.info("✅ Day {} done. Load: {}ms, Process: {}ms. Count: {}",
                            Utils.normalizeDateYYYYMMDD(currentTime),
                            (tLoad - t0), (tProcess - tLoad),
                            manager.getCollectedCount());
                } else {
                    LOG.info("🔥 Warm-up day {} done.", Utils.normalizeDateYYYYMMDD(currentTime));
                }

            } catch (Exception e) {
                LOG.error("Error processing day " + currentTime, e);
            }
            currentTime += Utils.TIME_DAY;
        }
    }

    private void processDay(TreeMap<Long, Map<String, KlineObjectSimple>> dayData,
                            TreeMap<Long, Map<String, KlineObjectSimple>> lookupData,
                            TreeMap<Long, MarketRateChange> rateData,
                            DcaDataCollectionManager manager,
                            boolean isCollecting) {

        int counter = 0;
        int totalMinutes = dayData.size();

        for (Map.Entry<Long, Map<String, KlineObjectSimple>> entry : dayData.entrySet()) {
            Long timestamp = entry.getKey();
            Map<String, KlineObjectSimple> snapshot = entry.getValue();

            // Cập nhật lịch sử (Quan trọng: Phải làm tuần tự)
            manager.updateHistory(snapshot);
            // Đồng bộ lịch sử sang preCheckExtractor để dùng tính volatility
            preCheckExtractor.updateMarketHistory(snapshot);

            counter++;
            // Log nhịp tim mỗi 4 giờ
            if (counter % 240 == 0) {
                LOG.info("   ⏳ Processing... {}/{} mins. Data collected: {}", counter, totalMinutes, manager.getCollectedCount());
            }

            if (!isCollecting) continue;

            MarketRateChange rate = rateData != null ? rateData.get(timestamp) : null;

            // 🔥 TẠO LỆNH GIẢ LẬP (Đã lọc Volatility)
            List<OrderTargetInfoTest> simulatedOrders = generateQualitySimulatedOrders(timestamp, snapshot);

            for (OrderTargetInfoTest order : simulatedOrders) {
                manager.processSimulatedOrder(timestamp, order, rate, snapshot, lookupData);
            }
        }
    }

    // 🔥 HÀM QUAN TRỌNG NHẤT: CHỈ LẤY MẪU CHẤT LƯỢNG
    private List<OrderTargetInfoTest> generateQualitySimulatedOrders(long currentTs, Map<String, KlineObjectSimple> snapshot) {
        List<String> candidates = new ArrayList<>();

        // Cooldown: Mỗi coin chỉ lấy mẫu tối đa 1 lần mỗi 45 phút (dày hơn chút để bắt được biến động)
        long cooldownMillis = 45 * 60 * 1000L;

        for (Map.Entry<String, KlineObjectSimple> entry : snapshot.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple kline = entry.getValue();

            // 1. Lọc thanh khoản rác: Volume < 10k USDT -> Bỏ qua
            if (kline.totalUsdt < 10000) continue;

            // 2. Check Cooldown
            Long lastTime = symbolLastSampledTime.get(symbol);
            if (lastTime != null && (currentTs - lastTime) < cooldownMillis) continue;

            // 3. 🔥 LỌC BIẾN ĐỘNG (Volatility Filter) 🔥
            // Chúng ta chỉ cần data khi thị trường có biến động để train AI.
            // Data đi ngang (Sideway) làm nhiễu mô hình và tốn dung lượng.
            if (isVolatilitySignificant(symbol, kline)) {
                candidates.add(symbol);
            }
        }

        // Random Shuffle để không bị thiên kiến
        Collections.shuffle(candidates);

        // Lấy tối đa 10 coin mỗi phút (Tăng số lượng vì đã lọc chất lượng)
        // Với việc lọc Volatility, số lượng candidate thực tế sẽ ít, nên lấy 10 là an toàn.
        int maxCoinsToPick = 10;
        List<String> selectedSymbols = candidates.subList(0, Math.min(candidates.size(), maxCoinsToPick));

        List<OrderTargetInfoTest> orders = new ArrayList<>();

        for (String symbol : selectedSymbols) {
            KlineObjectSimple currentKline = snapshot.get(symbol);
            symbolLastSampledTime.put(symbol, currentTs);

            // Sinh trạng thái ngẫu nhiên: Giả sử đang bị lỗ (Drawdown)
            // Logic này tạo ra các tình huống "Cần về bờ" để AI học cách xử lý
            double drawdownPercent = generateWeightedDrawdown();

            // Tính giá Entry giả định dựa trên giá hiện tại và mức lỗ giả định
            // Entry = Current / (1 - Loss%)
            double assumedEntryPrice = currentKline.priceClose / (1.0 - drawdownPercent);

            // Thời gian Entry giả định (chỉ mang tính tương đối cho feature time-based)
            long assumedStartTime = currentTs - (long) (drawdownPercent * 100 * 3600 * 1000);

            OrderTargetInfoTest order = new OrderTargetInfoTest(
                    null, assumedEntryPrice, null, 100.0, 10, symbol,
                    assumedStartTime, currentTs, OrderSide.BUY
            );
            order.lastPrice = currentKline.priceClose;
            orders.add(order);
        }
        return orders;
    }

    // Hàm check biến động sử dụng Extractor có sẵn
    private boolean isVolatilitySignificant(String symbol, KlineObjectSimple kline) {
        // Dùng reflection hoặc public method tạm để tính nhanh
        // Ở đây ta tính thủ công nhanh dựa trên Range nến hiện tại so với giá
        // Hoặc tốt nhất là gọi method calculateVolatilityShock nếu có thể access

        // Cách đơn giản nhưng hiệu quả: Range nến (High - Low) / Close
        double rangePercent = (kline.maxPrice - kline.minPrice) / kline.priceClose;

        // Nếu nến hiện tại dao động > 0.3% -> Có biến động (Coin rác thường dao động mạnh)
        // Hoặc kiểm tra Volume đột biến
        if (rangePercent > 0.003) return true;

        return false;
    }

    private double generateWeightedDrawdown() {
        double r = rand.nextDouble();
        // Mô phỏng các mức lỗ phổ biến của dân DCA
        if (r < 0.2) return 0.05 + rand.nextDouble() * 0.15; // Lỗ nhẹ 5-20%
        else if (r < 0.7) return 0.20 + rand.nextDouble() * 0.30; // Lỗ trung bình 20-50% (Vùng này cần học kỹ)
        else return 0.50 + rand.nextDouble() * 0.40; // Đu đỉnh chia đôi 50-90%
    }

    private TreeMap<Long, MarketRateChange> loadMarketRateData() throws Exception {
        if (!new File(Configs.FILE_ENTRY_MARKET_LEVEL).exists()) return new TreeMap<>();
        return (TreeMap<Long, MarketRateChange>) StorageSnappy.readObjectFromFile(Configs.FILE_ENTRY_MARKET_LEVEL);
    }
}