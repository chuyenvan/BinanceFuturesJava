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
        // TASK-037: chạy Kaggle/226 đọc-only → getReadClient()→226 (như ExportGateFeatures*). KHÔNG dùng trên box live.
        Configs.IS_KAGGLE_MODE = true;
        // TASK-037: PHIÊN BẢN MỚI (v3) — KHÔNG đè data model 21-feature cũ (features_export_python/).
        String outputDir = "features_export_python_v3/";
        new File(outputDir).mkdirs();

        // CHIA NĂM cho Kaggle (per-minute × all-coin × 5 năm quá lớn cho 1 kernel):
        //   args[0] = ngày bắt đầu ghi (yyyyMMdd, GMT+7 07:00), args[1] = ngày kết thúc (yyyyMMdd, loại trừ).
        //   Không truyền → mặc định 2021-01-01 → hiện tại (full).
        SimpleDateFormat sdfFull = new SimpleDateFormat("yyyyMMdd HH:mm");
        long targetStartTs = sdfFull.parse("20210101 07:00").getTime();
        long globalEndTs = System.currentTimeMillis();
        if (args.length >= 1 && !args[0].isEmpty()) {
            targetStartTs = sdfFull.parse(args[0] + " 07:00").getTime();
        }
        if (args.length >= 2 && !args[1].isEmpty()) {
            globalEndTs = sdfFull.parse(args[1] + " 07:00").getTime();
        }

        new ExportFeaturesForPythonTool().startGeneration(outputDir, targetStartTs, globalEndTs);
    }

    public void startGeneration(String outputDir, long targetStartTs, long globalEndTs) throws Exception {
        LOG.info("📥 Đang tải Market Data & Symbol Mapper...");
        TreeMap<Long, MarketDataObject> time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
        Map<String, Short> globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        final ConcurrentHashMap<String, Short> symbolMap = new ConcurrentHashMap<>(globalMapper);

        SimpleDateFormat sdfFull = new SimpleDateFormat("yyyyMMdd HH:mm");
        SimpleDateFormat sdfFile = new SimpleDateFormat("yyyyMMdd");
        FundingDataCollectionManager.FundingFeatureExtractorV2 extractor = new FundingDataCollectionManager.FundingFeatureExtractorV2();

        // 1. CÀI ĐẶT CÁC MỐC THỜI GIAN (truyền từ main; warmup 48h trước mốc ghi — đủ vì mọi
        //    feature dùng lookback ≤24h, riêng funding-sâu dùng full TreeMap headMap(t) nên đúng từ mọi mốc bắt đầu).
        long warmupStartTs = targetStartTs - (48 * 3600000L); // Warmup 48h

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
                // TASK-100 perf: 7 ngay/batch thay vi 1 ngay/batch — giam round-trip Aerospike qua mang
                // (benchmark Kaggle: bottleneck = network latency, khong phai CPU; ~7x it round-trip)
                int minutesToRead = 10080;
                if (currentReadTs + (long) minutesToRead * Utils.TIME_MINUTE > globalEndTs) {
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

                        // === PASS 1: per-coin (parallel) — feature #1..#32; cross-sectional (#33..#35) để NaN ===
                        List<FeatureHolder> rawList = symbol2Ticker.keySet().parallelStream()
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

                                        if (features != null) return new FeatureHolder(symId, features);
                                    } catch (Exception e) {
                                        LOG.warn("PASS1 trích feature lỗi symbol={} ts={}: {}", symbol, time, e.toString());
                                    }
                                    return null;
                                })
                                .filter(Objects::nonNull)
                                .collect(Collectors.toList());

                        // === PASS 2: cross-sectional rank giữa các coin CÙNG mốc t (single-thread, chỉ coin có data tại t) ===
                        applyCrossSectional(rawList);
                        for (FeatureHolder h : rawList) {
                            batch.add(new PrepareData(time, h.id, convertFeaturesToArray(h.f)));
                        }

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

    /**
     * Mảng feature theo thứ tự KHÓA (xem docs/reports/037.md). #1..#21 GIỮ NGUYÊN (khớp model
     * 21-feature đang LIVE); #22..#35 APPEND-ONLY (TASK-037). 039/inference-v2 phải đọc đúng thứ tự này.
     */
    private float[] convertFeaturesToArray(FundingMarketFeatures f) {
        return new float[]{
                // --- #1..#21: GIỮ NGUYÊN (append-only — KHÔNG đổi) ---
                f.btcMomentum1H, f.btcMomentum4H, f.btcMomentum24H, f.btcDominance, f.marketBreadthStrength,
                f.rateDown15MAvg, f.momentum1H, f.momentum4H, f.momentum24H, f.rsi1H, f.distFromLow24H, f.volatilityShock,
                f.basketMomentum15M, f.basketMomentum1H, f.basketMomentum24H, f.basketRsi14, f.basketVolSpike,
                f.coinFundingRate, f.basketFundingAvg, f.fundingRateAvg24H, f.fundingRateTrend,
                // --- #22..#26: funding sâu per-coin ---
                f.fundingPercentileCoin, f.fundingZCoin, f.fundingPersistence, f.fundingSum24h, f.fundingAbs,
                // --- #27..#28: volume per-coin ---
                f.volumeZCoin, f.volumeTrend,
                // --- #29..#32: cấu trúc giá per-coin ---
                f.distFromHigh24H, f.rangePosition24H, f.atrSqueeze, f.relStrengthBtc24H,
                // --- #33..#35: cross-sectional (cùng mốc t) ---
                f.fundingRankCS, f.volumeZRankCS, f.momentumRankCS,
                // --- #36..#40: microstructure 1m per-coin (TASK-038 phần B) ---
                f.ret15m, f.rvol15m, f.volumeZ5m, f.closePosRange15m, f.wickRatio15m
                // #41..#45 OI/LS/taker per-coin: TASK-038 phần A — xuất TOOL RIÊNG ExportFundingOiPerCoin
                //   (loop-theo-coin RAM-aware), MERGE ở train 039 theo (ts,coin). KHÔNG nằm trong .bin.gz này.
        };
    }

    /** Gom (symId, features) sau PASS 1 để PASS 2 tính cross-sectional rank cùng mốc. */
    private static class FeatureHolder {
        final short id;
        final FundingMarketFeatures f;

        FeatureHolder(short id, FundingMarketFeatures f) {
            this.id = id;
            this.f = f;
        }
    }

    /**
     * PASS 2 — cross-sectional: với mỗi mốc t, xếp rank-percentile coinFundingRate / volumeZCoin /
     * momentum24H GIỮA các coin có data tại t (#33..#35). Giá trị NaN (warmup) bị loại khỏi rank và
     * nhận rank = NaN. KHÔNG look-ahead (chỉ coin cùng mốc, không dùng coin mốc khác).
     *
     * @param list danh sách holder của 1 mốc t (đã lọc coin có ticker hợp lệ)
     */
    private void applyCrossSectional(List<FeatureHolder> list) {
        int m = list.size();
        if (m == 0) return;
        float[] funding = new float[m];
        float[] volz = new float[m];
        float[] mom = new float[m];
        for (int i = 0; i < m; i++) {
            FundingMarketFeatures f = list.get(i).f;
            funding[i] = f.coinFundingRate; // luôn có giá trị (0 nếu thiếu funding) → rank toàn coin
            volz[i] = f.volumeZCoin;        // NaN khi warmup → loại khỏi rank
            mom[i] = f.momentum24H;
        }
        float[] fundingRank = percentileRanks(funding);
        float[] volzRank = percentileRanks(volz);
        float[] momRank = percentileRanks(mom);
        for (int i = 0; i < m; i++) {
            FundingMarketFeatures f = list.get(i).f;
            f.fundingRankCS = fundingRank[i];
            f.volumeZRankCS = volzRank[i];
            f.momentumRankCS = momRank[i];
        }
    }

    /**
     * Rank-percentile (midrank) ∈ [0,1] cho từng phần tử so với các phần tử KHÔNG-NaN cùng mảng.
     * NaN giữ nguyên NaN. Nếu &lt;2 giá trị hợp lệ → tất cả NaN (rank vô nghĩa).
     */
    private static float[] percentileRanks(float[] vals) {
        int m = vals.length;
        float[] out = new float[m];
        int validCount = 0;
        for (float v : vals) if (!Float.isNaN(v)) validCount++;
        if (validCount <= 1) {
            Arrays.fill(out, Float.NaN);
            return out;
        }
        float[] sorted = new float[validCount];
        int k = 0;
        for (float v : vals) if (!Float.isNaN(v)) sorted[k++] = v;
        Arrays.sort(sorted);
        for (int i = 0; i < m; i++) {
            float v = vals[i];
            if (Float.isNaN(v)) {
                out[i] = Float.NaN;
                continue;
            }
            int less = lowerBound(sorted, v);
            int equal = upperBound(sorted, v) - less;
            out[i] = (float) ((less + 0.5 * equal) / validCount);
        }
        return out;
    }

    /** Số phần tử &lt; key trong mảng đã sort tăng dần. */
    private static int lowerBound(float[] a, float key) {
        int lo = 0, hi = a.length;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] < key) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }

    /** Số phần tử ≤ key trong mảng đã sort tăng dần. */
    private static int upperBound(float[] a, float key) {
        int lo = 0, hi = a.length;
        while (lo < hi) {
            int mid = (lo + hi) >>> 1;
            if (a[mid] <= key) lo = mid + 1;
            else hi = mid;
        }
        return lo;
    }
}