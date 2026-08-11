package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
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
        // TASK-037: chạy Kaggle/226 đọc-only (box cần AEROSPIKE_READ_CLUSTER=226, như ExportGateFeatures*). KHÔNG dùng trên box live.
        // TASK-037: PHIÊN BẢN MỚI (v3) — KHÔNG đè data model 21-feature cũ (features_export_python/).
        // args[0] = startDate yyyyMMdd, args[1] = endDate yyyyMMdd, args[2] = outputDir (optional).
        String outputDir = "features_export_python_v3/";

        SimpleDateFormat sdfFull = new SimpleDateFormat("yyyyMMdd HH:mm");
        long targetStartTs = sdfFull.parse("20210101 07:00").getTime();
        long globalEndTs = System.currentTimeMillis();
        if (args.length >= 1 && !args[0].isEmpty()) {
            targetStartTs = sdfFull.parse(args[0] + " 07:00").getTime();
        }
        if (args.length >= 2 && !args[1].isEmpty()) {
            globalEndTs = sdfFull.parse(args[1] + " 07:00").getTime();
        }
        if (args.length >= 3 && !args[2].isEmpty()) {
            outputDir = args[2];
        }
        new File(outputDir).mkdirs();

        new ExportFeaturesForPythonTool().startGeneration(outputDir, targetStartTs, globalEndTs);
        System.exit(0);
    }

    /**
     * Load dữ liệu từ Aerospike rồi gọi overload nhận pre-loaded data.
     * Dùng khi chạy độc lập (main / test). Worker dùng overload bên dưới để tái dùng data.
     */
    public void startGeneration(String outputDir, long targetStartTs, long globalEndTs) throws Exception {
        // [2026-08-04] TASK-112c: nhanh theo Configs.TICKER_SOURCE (CUNG 1 flag voi ticker/lifecycle,
        // khong them config rieng) — file: doc snapshot core_market_data/core_symbol_mapper tu
        // KaggleDataLoader (Kaggle, khong co Aerospike); aerospike (mac dinh): giu hanh vi cu.
        TreeMap<Long, MarketDataObject> time2MarketData;
        Map<String, Short> globalMapper;
        if ("file".equals(Configs.TICKER_SOURCE)) {
            LOG.info("📥 Đang tải Market Data & Symbol Mapper từ file snapshot (TICKER_SOURCE=file)...");
            time2MarketData = KaggleDataLoader.loadMarketData();
            globalMapper = KaggleDataLoader.loadSymbolMapperFile();
            if (time2MarketData == null || globalMapper == null) {
                throw new IllegalStateException("TICKER_SOURCE=file nhung thieu snapshot "
                        + "core_market_data/core_symbol_mapper trong kaggle_data_hpo/ - day len Kaggle truoc.");
            }
        } else {
            LOG.info("📥 Đang tải Market Data & Symbol Mapper...");
            time2MarketData = DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike();
            globalMapper = DataManagerAerospikeFloatSim.loadSymbolMapper();
        }
        startGeneration(outputDir, targetStartTs, globalEndTs,
                time2MarketData, new ConcurrentHashMap<>(globalMapper));
    }

    /**
     * Overload nhận data đã load sẵn — dùng bởi {@link ExportTool1Worker} để tái dùng MarketData
     * giữa các tháng mà không phải load lại từ Aerospike mỗi lần.
     *
     * @param preloadedMarketData  kết quả từ {@code DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike()}
     * @param preloadedSymbolMap   kết quả từ {@code loadSymbolMapper()} bọc trong ConcurrentHashMap
     */
    public void startGeneration(String outputDir, long targetStartTs, long globalEndTs,
            TreeMap<Long, MarketDataObject> preloadedMarketData,
            ConcurrentHashMap<String, Short> preloadedSymbolMap) throws Exception {
        final TreeMap<Long, MarketDataObject> time2MarketData = preloadedMarketData;
        final ConcurrentHashMap<String, Short> symbolMap = preloadedSymbolMap;

        // === RE-EXPORT UNFILTERED (opt-in, TASK unfiltered): mac dinh GIU nguyen hanh vi production.
        //     Bat qua env FF_UNFILTERED=1 -> bo EntrySignalFilter, xuat MOI alt tren luoi 15m (khop funding_label.csv),
        //     co the sub-sample deterministic qua FF_SAMPLE_RATE (0,1]. KHONG doi output production. ===
        final boolean unfiltered = "1".equals(System.getenv("FF_UNFILTERED"));
        // === COUNT-ONLY (TASK do TOP_PCT 2026-08-09): FF_COUNT_ONLY=1 -> chi dem N_t/phut qua nhanh
        //     filtered (bo extractFeatures + KHONG ghi .t1c.gz). Mac dinh tat -> path production khong doi. ===
        final boolean countOnly = "1".equals(System.getenv("FF_COUNT_ONLY"));
        final long[] ntHist = new long[2048];
        long ntTimestamps = 0L;
        long ntCandTotal = 0L;
        // === KEYDUMP (TASK label-filter 2026-08-09): FF_KEYDUMP=1 -> ghi binary key (symId<<32|minuteIdx)
        //     cho moi coin qua selectCoins (khop TUYET DOI voi features vi cung selectCoins + cung warmup). ===
        final boolean keyDump = "1".equals(System.getenv("FF_KEYDUMP"));
        java.io.DataOutputStream keyOut = null;
        long keyDumpCount = 0L;
        if (keyDump) {
            keyOut = new java.io.DataOutputStream(new java.io.BufferedOutputStream(
                    new java.io.FileOutputStream(outputDir + (outputDir.endsWith("/") ? "" : "/") + "keys.bin"), 1 << 20));
        }
        final double sampleRate = parseRate(System.getenv("FF_SAMPLE_RATE"));
        // [2026-08-04 CANONICAL 1m] Luoi grid unfiltered: env FF_GRID_MIN (mac dinh 15, khop hanh vi cu).
        // Dat =1 de xuat Tool1 luoi 1 phut THAT (khop LABEL_STEP_MIN=1 cua ExportFundingLabel) — bat buoc
        // dong bo 2 gia tri nay (Tool1 grid == label step) neu khong join (symbol,ts) exact se rot ~het du lieu.
        final long GRID_15M_MS = Long.parseLong(envOr("FF_GRID_MIN", "15")) * 60_000L;

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

        // [2026-08-07 TASK-251] Sink T1C1 (columnar + quantize int16 + byte-split + delta) thay cho
        // DataOutputStream row-major float32. Đo thật quý 2024Q2 (1.176.470 record): 105.96 → 27.97
        // B/record sau gzip = giảm 3.79 lần quota Kaggle, sai số xấu nhất 0.0038 IQR. Xem Tool1ColSink.
        Tool1ColSink sink = null;
        String currentFilePath = "";
        int fileRecordCount = 0;
        List<PrepareData> batch = new ArrayList<>();

        try {
            // VÒNG LẶP LIÊN TỤC KHÔNG RESET
            while (currentReadTs <= globalEndTs) {
                // 1 ngày/batch (CHUẨN DUY NHẤT). 1440 key/chunk < batch-max-requests=5000 của Aerospike 226
                // → KHÔNG BAO GIỜ vượt ngưỡng (10080 từng tạo chunk 5040 > 5000 → lỗi "Batch max requests
                // exceeded" + mất mảng data). Cộng RETRY ở DataManager (commit 1e8c2f2) chống lỗi transient.
                // Đây là cấu hình ổn định, đã xác nhận: KHÔNG đổi sang giá trị khác.
                int minutesToRead = 1440;
                if (currentReadTs + (long) minutesToRead * Utils.TIME_MINUTE > globalEndTs) {
                    minutesToRead = (int) ((globalEndTs - currentReadTs) / Utils.TIME_MINUTE) + 1;
                }

                if (minutesToRead <= 0) break;

                // [2026-08-04] TASK-112 pattern (giong ExportFundingLabel): TICKER_SOURCE=file cho phep
                // chay TREN KAGGLE doc ticker_*.bin (dataset hpo-ticker-daily), khong can Aerospike/Oracle.
                // minutesToRead <=1440 luon (chi rut ngan o chunk cuoi) va currentReadTs LUON day-aligned
                // (targetStartTs/warmup/+1440p moi buoc deu giu alignment) -> moi lan doc CHI cham 1 file
                // ticker_YYYYMMDD.bin, subMap() cat dung cua so (khop chinh xac hanh vi readDataFromAerospikeCustom).
                TreeMap<Long, Map<String, KlineObjectSimple>> dailyData;
                if ("aerospike".equals(Configs.TICKER_SOURCE)) {
                    dailyData = DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(currentReadTs, minutesToRead);
                } else if ("file".equals(Configs.TICKER_SOURCE)) {
                    TreeMap<Long, Map<String, KlineObjectSimple>> fileDay =
                            KaggleDataLoader.loadDailyTickersStringKey(currentReadTs);
                    if (fileDay == null) {
                        dailyData = new TreeMap<>();
                    } else {
                        if (!fileDay.isEmpty() && fileDay.firstKey() > currentReadTs) {
                            LOG.warn("TICKER_SOURCE=file: currentReadTs={} khong day-aligned voi file ngay "
                                    + "(firstKey={}) - co the mat data dau cua so. Kiem tra targetStartTs.",
                                    currentReadTs, fileDay.firstKey());
                        }
                        long rangeEndExclusive = currentReadTs + (long) minutesToRead * Utils.TIME_MINUTE;
                        dailyData = new TreeMap<>(fileDay.subMap(currentReadTs, rangeEndExclusive));
                    }
                } else {
                    throw new IllegalStateException("Thieu/sai TICKER_SOURCE trong config.properties (hien tai: "
                            + Configs.TICKER_SOURCE + ") - them dong: TICKER_SOURCE=aerospike (doc Aerospike) "
                            + "hoac TICKER_SOURCE=file (doc ticker_*.bin tu Kaggle dataset, khong can Oracle).");
                }

                if (dailyData != null && !dailyData.isEmpty()) {
                    for (Map.Entry<Long, Map<String, KlineObjectSimple>> timeEntry : dailyData.entrySet()) {
                        long time = timeEntry.getKey();
                        Map<String, KlineObjectSimple> symbol2Ticker = timeEntry.getValue();

                        // [QUAN TRỌNG NHẤT]: Luôn nạp State liên tục
                        extractor.updateMarketHistory(symbol2Ticker);
                        final List<String> basket = CoinRankManager.getInstance().getTopCoin(time);

                        // Bỏ qua nếu vẫn đang trong giai đoạn Warmup
                        if (time < targetStartTs) continue;

                        // === COUNT-ONLY: dem N_t = ung vien qua tier1(vol>=2000)+|rate30m|>0 tai phut nay,
                        //     KHONG extract/ghi. History da updateMarketHistory o tren -> getInstance() dung. ===
                        if (countOnly) {
                            int nt = com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter
                                    .countCandidates(symbol2Ticker, com.binance.chuyennd.ai_ml.features.export.HistoryManager.getInstance());
                            if (nt < 0) nt = 0;
                            if (nt >= ntHist.length) nt = ntHist.length - 1;
                            ntHist[nt]++;
                            ntTimestamps++;
                            ntCandTotal += nt;
                            continue;
                        }

                        // === KEYDUMP: ghi key (symId,minute) cho moi coin qua selectCoins, bo extraction. ===
                        if (keyDump) {
                            java.util.Set<String> pfK = com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter
                                    .selectCoins(symbol2Ticker, com.binance.chuyennd.ai_ml.features.export.HistoryManager.getInstance());
                            long minuteIdx = time / 60000L;
                            for (String symK : pfK) {
                                short sidK = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getId(symK);
                                if (sidK < 0) continue; // dung CUNG mapper voi label (khop symId tuyet doi)
                                keyOut.writeLong(((long) (sidK & 0xFFFF) << 32) | (minuteIdx & 0xFFFFFFFFL));
                                keyDumpCount++;
                            }
                            continue;
                        }

                        // KIỂM TRA MỐC CẮT FILE (3 THÁNG)
                        if (time >= chunkEndTs) {
                            if (sink != null) {
                                writeBatch(sink, batch);
                                fileRecordCount += batch.size();
                                batch.clear();
                                sink.close();
                                LOG.info("\n🎉 Đã đóng file: {} (Tổng: {} records)", currentFilePath, fileRecordCount);
                            }

                            // Cập nhật mốc 3 tháng tiếp theo
                            chunkStartTs = chunkEndTs;
                            cal.setTimeInMillis(chunkStartTs);
                            cal.add(Calendar.MONTH, 3);
                            chunkEndTs = cal.getTimeInMillis();
                            sink = null; // Kích hoạt tạo file mới ở dưới
                        }

                        // MỞ FILE MỚI NẾU CẦN
                        if (sink == null) {
                            // ĐUÔI MỚI .t1c.gz (KHÔNG dùng lại .bin.gz): định dạng khác hẳn nên phải phân
                            // biệt được từ tên file — reader Python (ml/lib/tool1_col.py) chọn decoder theo
                            // đuôi, và các job/glob cũ trỏ *.bin.gz sẽ KHÔNG vô tình đọc nhầm file mới.
                            currentFilePath = outputDir + "features_" + sdfFile.format(new Date(chunkStartTs))
                                    + "_to_" + sdfFile.format(new Date(chunkEndTs)) + ".t1c.gz";
                            LOG.info("📂 Đang tạo file mới: {}", currentFilePath);
                            // stepMin = 1: tIdx mã hoá theo PHÚT thật (bất biến, không phụ thuộc FF_GRID_MIN).
                            // Lưới xuất thưa hơn (vd 15m) vẫn đúng vì tIdx chỉ là số phút kể từ baseMs.
                            sink = new Tool1ColSink(currentFilePath, 1);
                            fileRecordCount = 0;
                        }

                        // === ENTRY SIGNAL FILTER (TASK filter 2026-06-18): chi xet coin qua filter CHUNG
                        //     (vol-avg-30m >= 2k + top-10% |rate30m| cross-sectional). Giam ~90% record.
                        //     History da updateMarketHistory(symbol2Ticker) o tren -> getInstance() la dung instance. ===
                        java.util.Set<String> passFilter;
                        if (unfiltered) {
                            if (time % GRID_15M_MS != 0L) continue;            // luoi 15m khop funding_label.csv
                            passFilter = new java.util.HashSet<>();
                            for (java.util.Map.Entry<String, KlineObjectSimple> te : symbol2Ticker.entrySet()) {
                                String sym = te.getKey(); if (!isAlt(sym)) continue;
                                KlineObjectSimple k = te.getValue(); if (k == null || !Utils.isTickerAvailable(k)) continue;
                                Short sid = symbolMap.get(sym); if (sid == null) continue;
                                if (sampleRate < 1.0 && !sampleKeep(sid, time, sampleRate)) continue;
                                passFilter.add(sym);
                            }
                        } else {
                            passFilter = com.binance.chuyennd.ai_ml.features.export.funding.EntrySignalFilter
                                    .selectCoins(symbol2Ticker, com.binance.chuyennd.ai_ml.features.export.HistoryManager.getInstance());
                        }
                        if (passFilter.isEmpty()) continue; // khong coin nao qua filter/sample tai moc nay

                        // === PASS 1: per-coin (parallel) — feature #1..#32; cross-sectional (#33..#35) để NaN ===
                        List<FeatureHolder> rawList = passFilter.parallelStream()
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
                            writeBatch(sink, batch);
                            fileRecordCount += batch.size();
                            batch.clear();
                        }
                    }
                }

                currentReadTs += minutesToRead * Utils.TIME_MINUTE;
                System.out.print(".");
            }

            // DỌN DẸP CUỐI CÙNG (Đóng file cuối cùng đang ghi dở)
            if (sink != null) {
                if (!batch.isEmpty()) {
                    writeBatch(sink, batch);
                    fileRecordCount += batch.size();
                    batch.clear();
                }
                sink.close();
                LOG.info("\n🎉 Đã đóng file cuối: {} (Tổng: {} records)", currentFilePath, fileRecordCount);
            }

        } catch (Exception e) {
            LOG.error("❌ Lỗi trong quá trình xuất feature", e);
        }

        if (keyDump && keyOut != null) {
            try { keyOut.flush(); keyOut.close();
                LOG.info("KEYDUMP: da ghi {} keys -> {}keys.bin", keyDumpCount,
                        outputDir.endsWith("/") ? outputDir : outputDir + "/");
            } catch (java.io.IOException ioe) { LOG.error("KEYDUMP: dong keys.bin loi", ioe); }
        }

        if (countOnly) {
            StringBuilder sb = new StringBuilder();
            sb.append("# FF_COUNT_ONLY N_t histogram (Nt = ung vien qua tier1+|rate30m|>0, TRUOC cat top-pct)\n");
            sb.append("# ntTimestamps=").append(ntTimestamps).append(" ntCandTotal=").append(ntCandTotal).append("\n");
            sb.append("Nt,freq\n");
            for (int i = 0; i < ntHist.length; i++) {
                if (ntHist[i] > 0) sb.append(i).append(",").append(ntHist[i]).append("\n");
            }
            String histPath = outputDir + (outputDir.endsWith("/") ? "" : "/") + "nt_histogram.csv";
            try (java.io.Writer w = new java.io.FileWriter(histPath)) {
                w.write(sb.toString());
                LOG.info("COUNT-ONLY: da ghi histogram -> {}", histPath);
            } catch (java.io.IOException ioe) {
                LOG.error("COUNT-ONLY: ghi histogram loi: {}", histPath, ioe);
            }
            double[] pcts = {0.10, 0.15, 0.20, 0.25, 0.30};
            StringBuilder rep = new StringBuilder("\n===== TOP_PCT: features_count = sum_t ceil(N_t*pct) =====\n");
            rep.append(String.format("ntTimestamps=%d ntCandTotal=%d%n", ntTimestamps, ntCandTotal));
            for (double p : pcts) {
                long total = 0L;
                for (int i = 0; i < ntHist.length; i++) {
                    if (ntHist[i] == 0) continue;
                    total += (long) Math.ceil(i * p) * ntHist[i];
                }
                rep.append(String.format("TOP_PCT=%.2f -> %d records%n", p, total));
            }
            LOG.info(rep.toString());
            System.out.println(rep);
        }

        LOG.info("🏁 HOÀN TẤT TOÀN BỘ QUÁ TRÌNH XUẤT FEATURES!");
    }

    /**
     * [2026-08-07 TASK-251] Đẩy batch vào {@link Tool1ColSink}. Sink tự gom đủ CHUNK_ROWS rồi sort
     * (symId, tIdx) + quantize + delta + byte-split — phía gọi KHÔNG cần đổi thứ tự/gom gì thêm.
     */
    private void writeBatch(Tool1ColSink sink, List<PrepareData> batch) throws IOException {
        for (PrepareData pd : batch) {
            sink.add(pd.time, pd.id, pd.features);
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
                //   (loop-theo-coin RAM-aware), MERGE ở train 039 theo (ts,coin). KHÔNG nằm trong .t1c.gz này.
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

    // === Helpers cho che do UNFILTERED (opt-in). Chi dung khi FF_UNFILTERED=1. ===

    /** Alt-USDT hop le: loai BTC/ETH/BTCDOM, cap _ (index), USDC. Khop dinh nghia rank/basket alt. */
    private static boolean isAlt(String s) {
        return s.endsWith("USDT") && !s.equals("BTCUSDT") && !s.equals("ETHUSDT")
                && !s.contains("_") && !s.contains("USDC") && !s.equals("BTCDOMUSDT");
    }

    /** [2026-08-04] env getter voi default, dung cho FF_GRID_MIN (khong co helper chung trong class nay). */
    private static String envOr(String name, String def) {
        String v = System.getenv(name);
        return (v != null && !v.isEmpty()) ? v : def;
    }

    /** Parse FF_SAMPLE_RATE -> (0,1]; rong/loi/ngoai khoang => 1.0 (giu tat ca). */
    private static double parseRate(String v) {
        if (v == null || v.isEmpty()) return 1.0;
        try {
            double r = Double.parseDouble(v);
            return (r > 0 && r <= 1) ? r : 1.0;
        } catch (Exception e) {
            return 1.0;
        }
    }

    /** Sub-sample deterministic theo (symId, mocGrid15m): hash -> uniform [0,1) < rate thi giu.
     *  On dinh giua cac lan chay (khong phu thuoc thu tu/seed) -> tai lap duoc. */
    private static boolean sampleKeep(short id, long t, double rate) {
        long h = (id & 0xffffL) * 1000003L + (t / (15L * 60_000L));
        h ^= (h >>> 33);
        h *= 0xff51afd7ed558ccdL;
        h ^= (h >>> 33);
        double u = (h >>> 11) * 0x1.0p-53;
        return u < rate;
    }
}