//package com.binance.chuyennd.ai_ml.deepseek;
//
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.io.BufferedReader;
//import java.io.File;
//import java.io.FileReader;
//import java.text.SimpleDateFormat;
//import java.util.*;
//import java.util.stream.Collectors;
//
//public class DataAnalyzer {
//    private static final Logger LOG = LoggerFactory.getLogger(DataAnalyzer.class);
//
//    public static void main(String[] args) {
//        LOG.info("🚀 STARTING COMPREHENSIVE DATA ANALYSIS FOR FULL DATASET (2021+)");
//
//        String dataDir = "storage/training_data_full";
//        List<MarketFeatures> allFeatures = loadAllFeaturesFromDirectory(dataDir);
//
//        if (allFeatures.isEmpty()) {
//            LOG.error("❌ No features found in directory: {}", dataDir);
//            return;
//        }
//
//        LOG.info("✅ Successfully loaded {} total features", allFeatures.size());
//
//        // 1. Phân tích tổng quan
//        analyzeDatasetOverview(allFeatures);
//
//        // 2. Phân tích theo thời gian
//        analyzeTemporalDistribution(allFeatures);
//
//        // 3. Phân tích phân phối features
//        analyzeAllFeatureDistributions(allFeatures);
//
//        // 4. Phân tích tương quan
//        analyzeFeatureCorrelations(allFeatures);
//
//        // 5. Kiểm tra chất lượng dữ liệu
//        performDataQualityAudit(allFeatures);
//
//        // 6. Phân tích regime và market states
//        analyzeMarketRegimes(allFeatures);
//
//        // 7. Tìm vấn đề cụ thể
//        identifySpecificIssues(allFeatures);
//
//        LOG.info("🎉 COMPREHENSIVE DATA ANALYSIS COMPLETED");
//    }
//
//    public static List<MarketFeatures> loadAllFeaturesFromDirectory(String directoryPath) {
//        List<MarketFeatures> allFeatures = new ArrayList<>();
//        File dir = new File(directoryPath);
//
//        if (!dir.exists() || !dir.isDirectory()) {
//            LOG.warn("Directory not found: {}", directoryPath);
//            return allFeatures;
//        }
//
//        File[] files = dir.listFiles((d, name) -> name.startsWith("market_features_") && name.endsWith(".csv"));
//
//        if (files == null || files.length == 0) {
//            LOG.warn("No CSV files found in directory: {}", directoryPath);
//            return allFeatures;
//        }
//
//        LOG.info("Found {} CSV files to process", files.length);
//
//        for (File file : files) {
//            try {
//                List<MarketFeatures> fileFeatures = loadFeaturesFromCSV(file.getAbsolutePath());
//                allFeatures.addAll(fileFeatures);
//                LOG.info("Loaded {} features from {}", fileFeatures.size(), file.getName());
//            } catch (Exception e) {
//                LOG.warn("Failed to load features from {}: {}", file.getName(), e.getMessage());
//            }
//        }
//
//        // Sắp xếp theo timestamp
//        allFeatures.sort(Comparator.comparing(f -> f.timestamp));
//
//        return allFeatures;
//    }
//
//    public static List<MarketFeatures> loadFeaturesFromCSV(String csvFile) {
//        List<MarketFeatures> featuresList = new ArrayList<>();
//
//        try (BufferedReader br = new BufferedReader(new FileReader(csvFile))) {
//            String header = br.readLine();
//            if (header == null) {
//                return featuresList;
//            }
//
//            String line;
//            int lineCount = 0;
//            int errorCount = 0;
//
//            while ((line = br.readLine()) != null) {
//                lineCount++;
//                try {
//                    MarketFeatures features = parseCSVLine(line);
//                    if (features != null) {
//                        featuresList.add(features);
//                    }
//                } catch (Exception e) {
//                    errorCount++;
//                    if (errorCount <= 3) {
//                        LOG.debug("Error parsing line {} in {}: {}", lineCount, csvFile, e.getMessage());
//                    }
//                }
//            }
//
//            if (errorCount > 0) {
//                LOG.debug("File {}: {} features loaded, {} errors", csvFile, featuresList.size(), errorCount);
//            }
//
//        } catch (Exception e) {
//            LOG.warn("Error loading CSV file {}: {}", csvFile, e.getMessage());
//        }
//
//        return featuresList;
//    }
//
//    private static MarketFeatures parseCSVLine(String line) {
//        String[] values = line.split(",");
//        if (values.length < 50) {
//            return null;
//        }
//
//        MarketFeatures features = new MarketFeatures();
//        int index = 0;
//
//        try {
//            // METADATA
//            features.timestamp = Long.parseLong(values[index++]);
//
//            // MOMENTUM & TREND (12 features)
//            features.momentum1M = parseDouble(values[index++]);
//            features.momentum5M = parseDouble(values[index++]);
//            features.momentum15M = parseDouble(values[index++]);
//            features.momentum1H = parseDouble(values[index++]);
//            features.momentum4H = parseDouble(values[index++]);
//            features.momentum24H = parseDouble(values[index++]);
//            features.trendStrengthBTC = parseDouble(values[index++]);
//            features.trendStrengthETH = parseDouble(values[index++]);
//            features.trendDurationBTC = parseDouble(values[index++]);
//            features.trendDurationETH = parseDouble(values[index++]);
//            features.momentumAcceleration = parseDouble(values[index++]);
//            features.trendConsistency = parseDouble(values[index++]);
//
//            // VOLATILITY & RISK (10 features)
//            features.volatility1M = parseDouble(values[index++]);
//            features.volatility15M = parseDouble(values[index++]);
//            features.volatility1H = parseDouble(values[index++]);
//            features.volatility4H = parseDouble(values[index++]);
//            features.volatility24H = parseDouble(values[index++]);
//            features.volatilityTermStructure = parseDouble(values[index++]);
//            features.var95_1H = parseDouble(values[index++]);
//            features.expectedShortfall1H = parseDouble(values[index++]);
//            features.maxDrawdown24H = parseDouble(values[index++]);
//            features.volatilityRegime = parseString(values[index++]);
//
//            // BREADTH & PARTICIPATION (8 features)
//            features.advanceDeclineRatio = parseDouble(values[index++]);
//            features.percentAboveMA20 = parseDouble(values[index++]);
//            features.percentAboveMA50 = parseDouble(values[index++]);
//            features.percentAboveMA200 = parseDouble(values[index++]);
//            features.volumeRatioUpDown = parseDouble(values[index++]);
//            features.volumeConcentration = parseDouble(values[index++]);
//            features.marketBreadthStrength = parseDouble(values[index++]);
//            features.leadershipRotation = parseDouble(values[index++]);
//
//            // STRUCTURE & LIQUIDITY (6 features)
//            features.bidAskSpreadAvg = parseDouble(values[index++]);
//            features.marketDepthBTC = parseDouble(values[index++]);
//            features.marketDepthETH = parseDouble(values[index++]);
//            features.liquidityIndex = parseDouble(values[index++]);
//            features.fundingRatePressure = parseDouble(values[index++]);
//            features.openInterestChange = parseDouble(values[index++]);
//
//            // CROSS-ASSET & MACRO (8 features)
//            features.btcDominance = parseDouble(values[index++]);
//            features.altcoinBeta = parseDouble(values[index++]);
//            features.stablecoinFlow = parseDouble(values[index++]);
//            features.fearGreedIndex = parseDouble(values[index++]);
//            features.termStructure = parseDouble(values[index++]);
//            features.basisRate = parseDouble(values[index++]);
//            features.marketRegime = parseString(values[index++]);
//            features.regimeConfidence = parseDouble(values[index++]);
//
//            // TIME FEATURES (4 features)
//            features.hourOfDay = parseInt(values[index++]);
//            features.dayOfWeek = parseInt(values[index++]);
//            features.weekOfMonth = parseInt(values[index++]);
//            features.monthOfYear = parseInt(values[index++]);
//
//            // LABELS
//            features.regimeLabel = parseString(values[index++]);
//            features.futureReturn1H = parseDouble(values[index++]);
//            features.futureReturn4H = parseDouble(values[index++]);
//            features.futureReturn24H = parseDouble(values[index++]);
//            features.maxDrawdownNext4H = parseDouble(values[index]);
//
//        } catch (Exception e) {
//            return null;
//        }
//
//        return features;
//    }
//
//    private static double parseDouble(String value) {
//        if (value == null || value.trim().isEmpty() || "null".equalsIgnoreCase(value) || "NULL".equalsIgnoreCase(value)) {
//            return 0.0;
//        }
//        try {
//            return Double.parseDouble(value.trim());
//        } catch (NumberFormatException e) {
//            return 0.0;
//        }
//    }
//
//    private static int parseInt(String value) {
//        if (value == null || value.trim().isEmpty()) {
//            return 0;
//        }
//        try {
//            return Integer.parseInt(value.trim());
//        } catch (NumberFormatException e) {
//            return 0;
//        }
//    }
//
//    private static String parseString(String value) {
//        if (value == null || value.trim().isEmpty() || "null".equalsIgnoreCase(value) || "NULL".equalsIgnoreCase(value)) {
//            return "UNKNOWN";
//        }
//        // Remove CSV escaping
//        if (value.startsWith("\"") && value.endsWith("\"")) {
//            value = value.substring(1, value.length() - 1).replace("\"\"", "\"");
//        }
//        return value.trim();
//    }
//
//    // ==================== PHÂN TÍCH TỔNG QUAN ====================
//
//    private static void analyzeDatasetOverview(List<MarketFeatures> features) {
//        LOG.info("\n📊 === DATASET OVERVIEW ===");
//
//        if (features.isEmpty()) return;
//
//        // Thời gian
//        MarketFeatures first = features.get(0);
//        MarketFeatures last = features.get(features.size() - 1);
//
//        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss");
//        LOG.info("Time range: {} to {}",
//                sdf.format(new Date(first.timestamp)),
//                sdf.format(new Date(last.timestamp)));
//
//        long days = (last.timestamp - first.timestamp) / (1000 * 60 * 60 * 24);
//        LOG.info("Total duration: {} days", days);
//        LOG.info("Total samples: {}", features.size());
//        LOG.info("Average samples per day: {}", String.format("%.1f", (double)features.size() / days));
//
//        // Phân bố theo năm
//        Map<Integer, Long> yearDistribution = features.stream()
//                .collect(Collectors.groupingBy(
//                        f -> getYearFromTimestamp(f.timestamp),
//                        Collectors.counting()
//                ));
//
//        LOG.info("Year distribution:");
//        yearDistribution.entrySet().stream()
//                .sorted(Map.Entry.comparingByKey())
//                .forEach(entry ->
//                        LOG.info("  {}: {} samples ({}%)",
//                                entry.getKey(), entry.getValue(),
//                                String.format("%.1f", entry.getValue() * 100.0 / features.size())));
//    }
//
//    private static int getYearFromTimestamp(long timestamp) {
//        Calendar cal = Calendar.getInstance();
//        cal.setTimeInMillis(timestamp);
//        return cal.get(Calendar.YEAR);
//    }
//
//    // ==================== PHÂN TÍCH THỜI GIAN ====================
//
//    private static void analyzeTemporalDistribution(List<MarketFeatures> features) {
//        LOG.info("\n⏰ === TEMPORAL DISTRIBUTION ===");
//
//        // Phân bố theo giờ - FIXED FORMAT
//        Map<Integer, Long> hourDistribution = features.stream()
//                .collect(Collectors.groupingBy(f -> f.hourOfDay, Collectors.counting()));
//
//        LOG.info("Hour of day distribution:");
//        hourDistribution.entrySet().stream()
//                .sorted(Map.Entry.comparingByKey())
//                .forEach(entry ->
//                        LOG.info("  {}:00 - {} samples",
//                                String.format("%02d", entry.getKey()), entry.getValue()));
//
//        // Phân bố theo ngày trong tuần
//        Map<Integer, Long> dayDistribution = features.stream()
//                .collect(Collectors.groupingBy(f -> f.dayOfWeek, Collectors.counting()));
//
//        String[] days = {"", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"};
//        LOG.info("Day of week distribution:");
//        dayDistribution.entrySet().stream()
//                .sorted(Map.Entry.comparingByKey())
//                .forEach(entry ->
//                        LOG.info("  {} - {} samples ({}%)",
//                                days[entry.getKey()], entry.getValue(),
//                                String.format("%.1f", entry.getValue() * 100.0 / features.size())));
//    }
//
//    // ==================== PHÂN TÍCH PHÂN PHỐI FEATURES ====================
//
//    private static void analyzeAllFeatureDistributions(List<MarketFeatures> features) {
//        LOG.info("\n📈 === FEATURE DISTRIBUTIONS ===");
//
//        String[] keyFeatures = {
//                "momentum1M", "momentum15M", "momentum1H",
//                "volatility1H", "volatility24H",
//                "advanceDeclineRatio", "btcDominance",
//                "volumeRatioUpDown", "trendStrengthBTC",
//                "fearGreedIndex", "liquidityIndex"
//        };
//
//        for (String feature : keyFeatures) {
//            analyzeFeatureDistribution(features, feature);
//        }
//    }
//
//    private static void analyzeFeatureDistribution(List<MarketFeatures> features, String featureName) {
//        List<Double> values = features.stream()
//                .map(f -> getFeatureValue(f, featureName))
//                .filter(Objects::nonNull)
//                .filter(v -> Double.isFinite(v))
//                .collect(Collectors.toList());
//
//        if (values.isEmpty()) {
//            LOG.warn("  {}: No valid values", featureName);
//            return;
//        }
//
//        double[] valueArray = values.stream().mapToDouble(Double::doubleValue).toArray();
//        double min = Arrays.stream(valueArray).min().orElse(0);
//        double max = Arrays.stream(valueArray).max().orElse(0);
//        double mean = Arrays.stream(valueArray).average().orElse(0);
//        double stdDev = calculateStdDev(valueArray, mean);
//
//        Arrays.sort(valueArray);
//        double p10 = valueArray[(int) (valueArray.length * 0.10)];
//        double p25 = valueArray[(int) (valueArray.length * 0.25)];
//        double p50 = valueArray[(int) (valueArray.length * 0.50)];
//        double p75 = valueArray[(int) (valueArray.length * 0.75)];
//        double p90 = valueArray[(int) (valueArray.length * 0.90)];
//
//        // FIXED: Sử dụng String.format thay vì {}
//        LOG.info("  {}:", featureName);
//        LOG.info("    Min: {}, Max: {}, Mean: {}, StdDev: {}",
//                formatDouble(min), formatDouble(max), formatDouble(mean), formatDouble(stdDev));
//        LOG.info("    Percentiles - 10th: {}, 25th: {}, 50th: {}, 75th: {}, 90th: {}",
//                formatDouble(p10), formatDouble(p25), formatDouble(p50),
//                formatDouble(p75), formatDouble(p90));
//    }
//
//    private static String formatDouble(double value) {
//        return String.format(Locale.US, "%.6f", value);
//    }
//
//    private static Double getFeatureValue(MarketFeatures feature, String featureName) {
//        switch (featureName) {
//            case "momentum1M": return feature.momentum1M;
//            case "momentum15M": return feature.momentum15M;
//            case "momentum1H": return feature.momentum1H;
//            case "volatility1H": return feature.volatility1H;
//            case "volatility24H": return feature.volatility24H;
//            case "advanceDeclineRatio": return feature.advanceDeclineRatio;
//            case "btcDominance": return feature.btcDominance;
//            case "volumeRatioUpDown": return feature.volumeRatioUpDown;
//            case "trendStrengthBTC": return feature.trendStrengthBTC;
//            case "fearGreedIndex": return feature.fearGreedIndex;
//            case "liquidityIndex": return feature.liquidityIndex;
//            default: return null;
//        }
//    }
//
//    private static double calculateStdDev(double[] values, double mean) {
//        if (values.length <= 1) return 0.0;
//        double variance = Arrays.stream(values)
//                .map(v -> Math.pow(v - mean, 2))
//                .average()
//                .orElse(0);
//        return Math.sqrt(variance);
//    }
//
//    // ==================== PHÂN TÍCH TƯƠNG QUAN ====================
//
//    private static void analyzeFeatureCorrelations(List<MarketFeatures> features) {
//        LOG.info("\n🔗 === FEATURE CORRELATIONS ===");
//
//        if (features.size() < 100) {
//            LOG.info("  Not enough samples for correlation analysis");
//            return;
//        }
//
//        String[][] correlationPairs = {
//                {"momentum15M", "volatility1H"},
//                {"btcDominance", "advanceDeclineRatio"},
//                {"volumeRatioUpDown", "momentum1H"},
//                {"trendStrengthBTC", "momentum1H"},
//                {"fearGreedIndex", "volatility1H"}
//        };
//
//        for (String[] pair : correlationPairs) {
//            double correlation = calculateCorrelation(features, pair[0], pair[1]);
//            // FIXED: Xử lý NaN
//            String correlationStr = Double.isNaN(correlation) ? "NaN (constant values)" : String.format("%.4f", correlation);
//            LOG.info("  {} ↔ {}: {}", pair[0], pair[1], correlationStr);
//        }
//    }
//
//    private static double calculateCorrelation(List<MarketFeatures> features, String feature1, String feature2) {
//        List<Double> values1 = new ArrayList<>();
//        List<Double> values2 = new ArrayList<>();
//
//        for (MarketFeatures feature : features) {
//            Double val1 = getFeatureValue(feature, feature1);
//            Double val2 = getFeatureValue(feature, feature2);
//
//            if (val1 != null && val2 != null && Double.isFinite(val1) && Double.isFinite(val2)) {
//                values1.add(val1);
//                values2.add(val2);
//            }
//        }
//
//        if (values1.size() < 10) return Double.NaN;
//
//        return safePearsonCorrelation(values1, values2);
//    }
//
//    private static double safePearsonCorrelation(List<Double> x, List<Double> y) {
//        double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
//        int n = x.size();
//
//        for (int i = 0; i < n; i++) {
//            sumX += x.get(i);
//            sumY += y.get(i);
//            sumXY += x.get(i) * y.get(i);
//            sumX2 += x.get(i) * x.get(i);
//            sumY2 += y.get(i) * y.get(i);
//        }
//
//        double numerator = n * sumXY - sumX * sumY;
//        double denominator = Math.sqrt((n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY));
//
//        // FIXED: Xử lý division by zero
//        if (denominator == 0) {
//            return Double.NaN;
//        }
//
//        return numerator / denominator;
//    }
//
//    // ==================== KIỂM TRA CHẤT LƯỢNG DỮ LIỆU ====================
//
//    private static void performDataQualityAudit(List<MarketFeatures> features) {
//        LOG.info("\n🔍 === DATA QUALITY AUDIT ===");
//
//        int total = features.size();
//        if (total == 0) return;
//
//        // Đếm các vấn đề chất lượng
//        long zeroMomentum = features.stream().filter(f -> f.momentum1M == 0.0).count();
//        long zeroVolatility = features.stream().filter(f -> f.volatility1H == 0.0).count();
//        long defaultBTCDominance = features.stream().filter(f -> f.btcDominance == 0.45).count();
//        long invalidValues = features.stream().filter(f ->
//                Double.isNaN(f.momentum1M) || Double.isInfinite(f.momentum1M) ||
//                        Double.isNaN(f.volatility1H) || Double.isInfinite(f.volatility1H)
//        ).count();
//
//        // FIXED: Sử dụng String.format
//        LOG.info("Zero momentum1M: {}/{} ({}%)", zeroMomentum, total,
//                String.format("%.1f", zeroMomentum * 100.0 / total));
//        LOG.info("Zero volatility1H: {}/{} ({}%)", zeroVolatility, total,
//                String.format("%.1f", zeroVolatility * 100.0 / total));
//        LOG.info("Default BTC dominance: {}/{} ({}%)", defaultBTCDominance, total,
//                String.format("%.1f", defaultBTCDominance * 100.0 / total));
//        LOG.info("Invalid values: {}/{} ({}%)", invalidValues, total,
//                String.format("%.1f", invalidValues * 100.0 / total));
//
//        // Phân tích regime distribution
//        Map<String, Long> regimeDistribution = features.stream()
//                .collect(Collectors.groupingBy(f -> f.marketRegime, Collectors.counting()));
//
//        LOG.info("Market regime distribution:");
//        regimeDistribution.forEach((regime, count) ->
//                LOG.info("  {}: {} ({}%)", regime, count,
//                        String.format("%.1f", count * 100.0 / total)));
//
//        // Phân tích volatility regime
//        Map<String, Long> volRegimeDistribution = features.stream()
//                .collect(Collectors.groupingBy(f -> f.volatilityRegime, Collectors.counting()));
//
//        LOG.info("Volatility regime distribution:");
//        volRegimeDistribution.forEach((regime, count) ->
//                LOG.info("  {}: {} ({}%)", regime, count,
//                        String.format("%.1f", count * 100.0 / total)));
//    }
//
//    // ==================== PHÂN TÍCH MARKET REGIMES ====================
//
//    private static void analyzeMarketRegimes(List<MarketFeatures> features) {
//        LOG.info("\n🎯 === MARKET REGIME ANALYSIS ===");
//
//        if (features.isEmpty()) return;
//
//        // Phân tích features theo regime
//        Map<String, List<MarketFeatures>> regimeGroups = features.stream()
//                .collect(Collectors.groupingBy(f -> f.marketRegime));
//
//        regimeGroups.forEach((regime, regimeFeatures) -> {
//            if (regimeFeatures.size() > 10) {
//                LOG.info("Regime '{}' ({} samples):", regime, regimeFeatures.size());
//
//                double avgMomentum = regimeFeatures.stream()
//                        .mapToDouble(f -> f.momentum1H)
//                        .average()
//                        .orElse(0);
//
//                double avgVolatility = regimeFeatures.stream()
//                        .mapToDouble(f -> f.volatility1H)
//                        .average()
//                        .orElse(0);
//
//                double avgBtcDominance = regimeFeatures.stream()
//                        .mapToDouble(f -> f.btcDominance)
//                        .average()
//                        .orElse(0);
//
//                LOG.info("  Avg Momentum1H: {}, Avg Volatility1H: {}, Avg BTC Dominance: {}",
//                        formatDouble(avgMomentum), formatDouble(avgVolatility), formatDouble(avgBtcDominance));
//            }
//        });
//
//        // Phân tích extreme events
//        analyzeExtremeEvents(features);
//    }
//
//    private static void analyzeExtremeEvents(List<MarketFeatures> features) {
//        LOG.info("\n⚡ === EXTREME EVENTS ANALYSIS ===");
//
//        // Tìm các sự kiện momentum cực đoan
//        List<MarketFeatures> highMomentum = features.stream()
//                .filter(f -> Math.abs(f.momentum1H) > 0.03)
//                .sorted((f1, f2) -> Double.compare(Math.abs(f2.momentum1H), Math.abs(f1.momentum1H)))
//                .limit(10)
//                .collect(Collectors.toList());
//
//        LOG.info("Top high momentum events (|momentum1H| > 0.03): {} events", highMomentum.size());
//
//        // Tìm các sự kiện volatility cao
//        List<MarketFeatures> highVolatility = features.stream()
//                .filter(f -> f.volatility1H > 0.05)
//                .sorted((f1, f2) -> Double.compare(f2.volatility1H, f1.volatility1H))
//                .limit(10)
//                .collect(Collectors.toList());
//
//        LOG.info("High volatility events (volatility1H > 0.05): {} events", highVolatility.size());
//
//        if (!highVolatility.isEmpty()) {
//            SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm");
//            LOG.info("Sample high volatility events:");
//            highVolatility.stream().limit(3).forEach(f ->
//                    LOG.info("  {}: Volatility = {}, Regime = {}",
//                            sdf.format(new Date(f.timestamp)), formatDouble(f.volatility1H), f.marketRegime));
//        }
//    }
//
//    // ==================== PHÂN TÍCH VẤN ĐỀ CỤ THỂ ====================
//
//    private static void identifySpecificIssues(List<MarketFeatures> features) {
//        LOG.info("\n🔧 === SPECIFIC ISSUES IDENTIFICATION ===");
//
//        // Kiểm tra volatility values
//        List<MarketFeatures> highVolatility = features.stream()
//                .filter(f -> f.volatility1H > 0.1)
//                .collect(Collectors.toList());
//
//        LOG.info("Samples with volatility1H > 0.1: {}", highVolatility.size());
//
//        if (!highVolatility.isEmpty()) {
//            LOG.info("Sample high volatility values:");
//            highVolatility.stream().limit(5).forEach(f ->
//                    LOG.info("  Timestamp: {}, Volatility1H: {}",
//                            new SimpleDateFormat("yyyy-MM-dd HH:mm").format(new Date(f.timestamp)),
//                            formatDouble(f.volatility1H)));
//        }
//
//        // Kiểm tra BTC Dominance range
//        double minBtcDom = features.stream().mapToDouble(f -> f.btcDominance).min().orElse(0);
//        double maxBtcDom = features.stream().mapToDouble(f -> f.btcDominance).max().orElse(0);
//        double avgBtcDom = features.stream().mapToDouble(f -> f.btcDominance).average().orElse(0);
//
//        LOG.info("BTC Dominance - Min: {}, Max: {}, Avg: {}",
//                formatDouble(minBtcDom), formatDouble(maxBtcDom), formatDouble(avgBtcDom));
//
//        // Kiểm tra FearGreedIndex values
//        double minFGI = features.stream().mapToDouble(f -> f.fearGreedIndex).min().orElse(0);
//        double maxFGI = features.stream().mapToDouble(f -> f.fearGreedIndex).max().orElse(0);
//        double avgFGI = features.stream().mapToDouble(f -> f.fearGreedIndex).average().orElse(0);
//
//        LOG.info("FearGreedIndex - Min: {}, Max: {}, Avg: {}", formatDouble(minFGI), formatDouble(maxFGI), formatDouble(avgFGI));
//
//        // Kiểm tra các giá trị bất thường
//        checkAnomalousValues(features);
//
//        // Đề xuất fix
//        LOG.info("\n💡 RECOMMENDED FIXES:");
//
//        // Phân tích thực tế các vấn đề
//        analyzeActualProblems(features);
//    }
//
//    private static void analyzeActualProblems(List<MarketFeatures> features) {
//        // Kiểm tra xem có features nào bị constant không
//        checkConstantFeatures(features);
//
//        // Kiểm tra data quality thực tế
//        checkRealDataQuality(features);
//    }
//
//    private static void checkConstantFeatures(List<MarketFeatures> features) {
//        LOG.info("\n📊 === CONSTANT FEATURES CHECK ===");
//
//        String[] featuresToCheck = {"volatility1H", "fearGreedIndex", "volatility24H"};
//
//        for (String featureName : featuresToCheck) {
//            Set<Double> uniqueValues = features.stream()
//                    .map(f -> getFeatureValue(f, featureName))
//                    .filter(Objects::nonNull)
//                    .collect(Collectors.toSet());
//
//            LOG.info("{} - Unique values: {}", featureName, uniqueValues.size());
//            if (uniqueValues.size() <= 5) {
//                LOG.info("  ⚠️  {} has very few unique values: {}", featureName, uniqueValues);
//            }
//        }
//    }
//
//    private static void checkRealDataQuality(List<MarketFeatures> features) {
//        LOG.info("\n🔎 === REAL DATA QUALITY CHECK ===");
//
//        // Kiểm tra phân bố thực tế của các features quan trọng
//        double volatilityStdDev = features.stream()
//                .mapToDouble(f -> f.volatility1H)
//                .filter(Double::isFinite)
//                .map(v -> Math.abs(v - 0.01)) // Độ lệch so với 0.01
//                .average()
//                .orElse(1.0);
//
//        if (volatilityStdDev < 0.001) {
//            LOG.info("❌ VOLATILITY DATA ISSUE: All volatility1H values are ~0.01 (constant)");
//        }
//
//        double fearGreedStdDev = features.stream()
//                .mapToDouble(f -> f.fearGreedIndex)
//                .filter(Double::isFinite)
//                .map(v -> Math.abs(v - 50.0)) // Độ lệch so với 50.0
//                .average()
//                .orElse(1.0);
//
//        if (fearGreedStdDev < 0.001) {
//            LOG.info("❌ FEAR_GREED DATA ISSUE: All FearGreedIndex values are ~50.0 (constant)");
//        }
//
//        // Kiểm tra regimes
//        Set<String> marketRegimes = features.stream()
//                .map(f -> f.marketRegime)
//                .collect(Collectors.toSet());
//
//        Set<String> volatilityRegimes = features.stream()
//                .map(f -> f.volatilityRegime)
//                .collect(Collectors.toSet());
//
//        LOG.info("Unique Market Regimes: {}", marketRegimes);
//        LOG.info("Unique Volatility Regimes: {}", volatilityRegimes);
//
//        if (marketRegimes.size() <= 2) {
//            LOG.info("❌ MARKET REGIME ISSUE: Only {} market regimes detected", marketRegimes.size());
//        }
//
//        if (volatilityRegimes.size() <= 1) {
//            LOG.info("❌ VOLATILITY REGIME ISSUE: Only {} volatility regime detected", volatilityRegimes.size());
//        }
//    }
//
//    private static void checkAnomalousValues(List<MarketFeatures> features) {
//        LOG.info("\n📋 === ANOMALOUS VALUES CHECK ===");
//
//        // Kiểm tra giá trị momentum bất thường
//        long abnormalMomentum = features.stream()
//                .filter(f -> Math.abs(f.momentum1H) > 0.5)
//                .count();
//        LOG.info("Abnormal momentum1H (> 0.5): {}", abnormalMomentum);
//
//        // Kiểm tra giá trị volatility bất thường
//        long abnormalVolatility = features.stream()
//                .filter(f -> f.volatility1H > 1.0)
//                .count();
//        LOG.info("Abnormal volatility1H (> 1.0): {}", abnormalVolatility);
//
//        // Kiểm tra giá trị BTC dominance bất thường
//        long abnormalBTCDom = features.stream()
//                .filter(f -> f.btcDominance < 0.3 || f.btcDominance > 0.7)
//                .count();
//        LOG.info("Abnormal BTC dominance (<0.3 or >0.7): {}", abnormalBTCDom);
//
//        // Kiểm tra volume ratio
//        long abnormalVolumeRatio = features.stream()
//                .filter(f -> f.volumeRatioUpDown < 0.0 || f.volumeRatioUpDown > 1.0)
//                .count();
//        LOG.info("Abnormal volume ratio (<0 or >1): {}", abnormalVolumeRatio);
//    }
//}