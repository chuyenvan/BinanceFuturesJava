package com.binance.chuyennd.ai_ml.dl4j; // Dat package cua ban

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.TechnicalAnalysisUtils;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;

import java.io.File;
import java.io.FileWriter;
import java.io.PrintWriter;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import java.util.stream.Collectors;

/**
 * Lop nay tao file CSV bang cach mo phong day du logic trade (DCA + Trading Stop)
 * cho tung diem du lieu de tao ra "Super-Label"
 * PHIEN BAN 5: Mo phong (Simulation)
 */
public class FeatureExtractor_BtcReverse {

    // --- Cau hinh ---
    private static final String CSV_FILE_PATH = "storage/ai_ml/dl4j/btc_reverse_dataset_v5_sim.csv";

    // Loc dau vao: Chi lay mau neu gia giam 1% so voi dinh 30 phut
    private static final double ENTRY_FILTER_THRESHOLD = -0.005;

    // Giai doan "lam nong" de tinh TA
    private static final int WARMUP_PERIOD = 200;

    // Mo phong trong bao lau (7 ngay)
    private static final int SIMULATION_PERIOD_MINUTES = 7 * 24 * 60; // 10,080 phut

    // Cau hinh chi bao TA
    private static final int RSI_PERIOD = 14;
    private static final int ATR_PERIOD = 14;
    private static final int BB_PERIOD = 20;
    private static final int MACD_FAST = 12;
    private static final int MACD_SLOW = 26;
    private static final int MACD_SIGNAL = 9;

    // Cache du lieu Trend (BTC/ETH)
    private static ConcurrentHashMap<String, Map<Long, Boolean>> CACHED_symbol2TrendData;

    // Cache toan bo 5 nam du lieu BTC
    private static TreeMap<Long, KlineObjectSimple> ALL_BTC_DATA;

    // Gia lap cac tham so tu he thong
    private static final double HYPOTHETICAL_BUDGET_PER_ORDER = 20.0;
    private static final int LEVERAGE = 10;
    // (Gia dinh la Trend = True trong suot qua trinh mo phong label)
    private static final boolean SIMULATED_TREND = true;

    public static void main(String[] args) {

        System.out.println("Bat dau tao file dataset V5 (Simulation)...");

        try {
            // 1. Tai du lieu Trend
            System.out.println("Dang tai du lieu Trend...");
            CACHED_symbol2TrendData = (ConcurrentHashMap<String, Map<Long, Boolean>>) StorageSnappy.readObjectFromFile(Configs.FILE_TREND_BY_TIME);

            // 2. Tai TOAN BO 5 nam du lieu BTC vao RAM (TU FILE SNAPPY)
            System.out.println("Dang tai toan bo 5 nam du lieu BTC tu file Snappy vao RAM...");
            ALL_BTC_DATA = loadAllBtcDataFromFile();
            System.out.println("Tai thanh cong " + ALL_BTC_DATA.size() + " phut du lieu BTC.");

            // 3. Tao thu muc (neu chua co)
            setupCsvFile();

        } catch (Exception e) {
            e.printStackTrace();
            return;
        }

        // 4. Bat dau xu ly va ghi file
        try (PrintWriter writer = new PrintWriter(new FileWriter(CSV_FILE_PATH))) {

            // Ghi Header (11 features + 1 label)
            writer.println(
                    "btc_rate_vs_15m_high,btc_rate_vs_30m_high,btc_rate_vs_60m_high," +
                            "btc_rate_change_1m,btc_rate_change_5m," +
                            "isTrendBuyWithETH,isTrendBuyWithBTC," +
                            "rsi_14,bb_width_20,atr_14,macd_hist," +
                            "label"
            );

            List<Long> allTimestamps = new ArrayList<>(ALL_BTC_DATA.keySet());
            List<KlineObjectSimple> allKlines = new ArrayList<>(ALL_BTC_DATA.values());
            List<Double> allClosePrices = allKlines.stream()
                    .map(k -> k.priceClose)
                    .collect(Collectors.toList());

            int rowsWritten = 0;
            System.out.println("Bat dau quet du lieu va tinh toan features/labels...");
            System.out.println("(Qua trinh nay se RAT CHAM do phai mo phong 7 ngay cho moi dong)...");

            // Chung ta phai tru di SIMULATION_PERIOD_MINUTES o cuoi
            for (int i = WARMUP_PERIOD; i < allTimestamps.size() - SIMULATION_PERIOD_MINUTES; i++) {

                long currentTimestamp = allTimestamps.get(i);

                // (Them log theo doi ngay ban yeu cau)
                if (i % 1440 == 0) { // In ra moi ngay 1 lan
                    System.out.println("--- Dang xu ly ngay: " + Utils.normalizeDateYYYYMMDD(currentTimestamp) + " ---");
                }

                List<KlineObjectSimple> historyKlines = allKlines.subList(i - WARMUP_PERIOD, i + 1);

                // --- BUOC D: TINH TOAN FEATURES (CAU HOI) ---
                Map<String, Double> features = calculateFeatures(
                        historyKlines,
                        allClosePrices.subList(i - WARMUP_PERIOD, i + 1),
                        currentTimestamp
                );

                if (features == null) continue;

                // --- BUOC D (Bo sung): LOC DU LIEU ---
                if (features.get("btc_rate_vs_30m_high") > ENTRY_FILTER_THRESHOLD) {
                    continue;
                }

                // --- BUOC E: TINH TOAN "SUPER-LABEL" (MO PHONG) ---
                int label = calculateSimulatedLabel(allKlines, i);

                // --- BUOC F: GHI RA FILE CSV ---
                writer.printf("%.6f,%.6f,%.6f,%.6f,%.6f,%.1f,%.1f,%.6f,%.6f,%.6f,%.6f,%d%n",
                        features.get("btc_rate_vs_15m_high"),
                        features.get("btc_rate_vs_30m_high"),
                        features.get("btc_rate_vs_60m_high"),
                        features.get("btc_rate_change_1m"),
                        features.get("btc_rate_change_5m"),
                        features.get("isTrendBuyWithETH"),
                        features.get("isTrendBuyWithBTC"),
                        features.get("rsi_14"),
                        features.get("bb_width_20"),
                        features.get("atr_14"),
                        features.get("macd_hist"),
                        label);
                rowsWritten++;
            }

            System.out.println("\n--- HOAN TAT TAO FILE DATASET: " + CSV_FILE_PATH + " ---");
            System.out.println("Tong so dong (vi du) da ghi: " + rowsWritten);

        } catch (Exception e) {
            System.err.println("Gap loi nghiem trong khi tao file CSV:");
            e.printStackTrace();
        }
    }

    /**
     * Ham ho tro: Tinh toan "Super-Label" bang cach mo phong
     */
    private static int calculateSimulatedLabel(List<KlineObjectSimple> allKlines, int currentIndex) {

        // 1. Khoi tao Vi the (Position)
        SimulatedPosition pos = new SimulatedPosition(allKlines.get(currentIndex).priceClose);

        // 2. Chay vong lap mo phong 7 ngay (10,080 phut)
        for (int i = 1; i <= SIMULATION_PERIOD_MINUTES; i++) {

            KlineObjectSimple currentTicker = allKlines.get(currentIndex + i);

            // 2a. Cap nhat gia (min/max)
            pos.updatePrice(currentTicker);

            // 2b. Kiem tra xem Trading Stop (da dat) co bi cham khong
            if (pos.isStopped(currentTicker)) {
                return pos.getLabel(); // Tra ve 1 (Thang) hoac 0 (Thua)
            }

            // 2c. Kiem tra xem co nen dat Trading Stop moi khong
            // (Lay lich su 90 phut tinh den thoi diem 'i' nay)
            List<KlineObjectSimple> historyForStop = allKlines.subList(
                    (currentIndex + i) - 90, // 90 phut qua khu
                    (currentIndex + i) + 1  // Den phut hien tai
            );
            pos.checkAndSetTradingStop(historyForStop);

            // 2d. Kiem tra xem co nen DCA khong
            // (Logic giong het MarketBigChangeDetector.isDcaWithBtcReverse)
            if (pos.checkDcaCondition(currentTicker, SIMULATED_TREND)) {
                pos.executeDca(currentTicker.priceClose);
            }
        }

        // 3. Neu het 7 ngay ma khong bi stop
        return pos.getFinalLabel(); // Tra ve 1 (Thang) hoac 0 (Thua) dua tren PnL
    }

    // === CÁC HÀM SAO CHÉP TỪ LOGIC GỐC (TradeUtils, MarketBigChangeDetector) ===

    /**
     * (Logic tu TradeUtils.java)
     * Tinh toan muc % toi thieu de bat dau dat Trading Stop
     */
    private static double simulate_calRateMinWithMaxChange60MForTradingStop(double maxChange90M, boolean isTrendBuyWithETH) {
        Double rateMin2MoveSl = 0.016; // Configs.RATE_PROFIT_STOP_MARKET (Gia su 1.6%)
        if (isTrendBuyWithETH) {
            if (maxChange90M >= 0.01) {
                rateMin2MoveSl = 0.03;
            } else if (maxChange90M >= 0.006) {
                rateMin2MoveSl = 0.02;
            } else if (maxChange90M >= 0.004) {
                rateMin2MoveSl = 0.016;
            }
        } else {
            if (maxChange90M >= 0.02) {
                rateMin2MoveSl = 0.015;
            } else if (maxChange90M >= 0.01) {
                rateMin2MoveSl = 0.012;
            }
        }
        return rateMin2MoveSl;
    }

    /**
     * (Logic tu TradeUtils.java)
     * Tinh toan vi tri dat Stop Loss dong (sau khi da kich hoat)
     */
    private static double simulate_calRateLossDynamicBuy(double unProfit, double maxChange90M) {
        double rateLoss = unProfit * 200;
        long tradingStopRate;
        long maxRateTradingStop = 16L;
        if (maxChange90M < 0.004) {
            maxRateTradingStop = 6L;
        }
        if (rateLoss < maxRateTradingStop * 2) {
            tradingStopRate = (long) (rateLoss / 2);
        } else {
            tradingStopRate = maxRateTradingStop;
        }
        rateLoss = (long) rateLoss - tradingStopRate;
        return rateLoss / 200.0;
    }

    /**
     * (Logic tu MarketBigChangeDetector.java)
     * Kiem tra xem co nen DCA hay khong
     */
    private static boolean simulate_isDcaWithBtcReverse(double rateLoss, double budget, double marginOfSym,
                                                        double priceClose, double lastEntry, boolean isTrendBuyWithETH) {
        int marginRatioLevel1 = 2;
        int marginRatioLevel2 = 4;
        if (marginOfSym > marginRatioLevel1 * budget) {
            if (marginOfSym > marginRatioLevel2 * budget) {
                if (Utils.rateOf2Double(priceClose, lastEntry) < -0.1) {
                    return true;
                }
            } else {
                if (rateLoss < -0.05 || rateLoss > 0.02) {
                    return true;
                }
            }
        } else {
            if (rateLoss < -0.03 || rateLoss > 0.02) {
                return true;
            }
        }
        return false;
    }

    /**
     * Ham ho tro: Tinh max rate 90m (cho logic Trading Stop)
     */
    private static double simulate_getMaxRateIn90M(List<KlineObjectSimple> tickers_90m) {
        double maxRateChangeIn90M = 0d;
        for (KlineObjectSimple tickerCheck : tickers_90m) {
            double rate = Utils.rateOf2Double(tickerCheck.maxPrice, tickerCheck.minPrice);
            if (rate > maxRateChangeIn90M) {
                maxRateChangeIn90M = rate;
            }
        }
        return maxRateChangeIn90M;
    }

    // === CÁC HÀM CŨ (Giu nguyen tu V4) ===

    // loadAllBtcDataFromFile()
    // calculateFeatures()
    // findMaxPrice()
    // getTrend()
    // setupCsvFile()
    // calculateEMA()
    // calculateSMA()
    // calculateMACD()

    // (Toi se bo qua viec dan (paste) lai cac ham da co o tren de tiet kiem khong gian)
    // (Ban chi can giu nguyen cac ham do tu code V4)

    // === LOP NOI (INNER CLASS) DE QUAN LY MO PHONG ===

    private static class SimulatedPosition {
        double avgEntryPrice;
        double totalQuantity;
        double lastEntryPrice;

        double priceSL; // 0.0 nghia la chua dat
        double maxPriceInPosition; // Max price ke tu entry/dca cuoi cung
        double minPriceInPosition; // Min price ke tu entry/dca cuoi cung

        SimulatedPosition(double initialPrice) {
            this.avgEntryPrice = initialPrice;
            this.lastEntryPrice = initialPrice;
            this.totalQuantity = (HYPOTHETICAL_BUDGET_PER_ORDER * LEVERAGE) / initialPrice;
            this.priceSL = 0.0;
            this.maxPriceInPosition = initialPrice;
            this.minPriceInPosition = initialPrice;
        }

        void updatePrice(KlineObjectSimple ticker) {
            this.maxPriceInPosition = Math.max(this.maxPriceInPosition, ticker.maxPrice);
            this.minPriceInPosition = Math.min(this.minPriceInPosition, ticker.minPrice);
        }

        boolean isStopped(KlineObjectSimple ticker) {
            return this.priceSL > 0.0 && ticker.minPrice <= this.priceSL;
        }

        int getLabel() {
            return (this.priceSL > this.avgEntryPrice) ? 1 : 0; // Thang (Trailing) hay Thua (StopLoss)
        }

        int getFinalLabel() {
            double lastPrice = this.minPriceInPosition; // Gia su dong o gia cuoi
            return (lastPrice > this.avgEntryPrice) ? 1 : 0; // Thang hay Thua khi het 7 ngay
        }

        void checkAndSetTradingStop(List<KlineObjectSimple> history_90m) {
            if (this.priceSL > 0.0) return; // Da dat SL roi, khong can kiem tra nua

            double maxChange90M = simulate_getMaxRateIn90M(history_90m);
            double rateLossMax = (this.maxPriceInPosition - this.avgEntryPrice) / this.avgEntryPrice;
            double rateMin2MoveSl = simulate_calRateMinWithMaxChange60MForTradingStop(maxChange90M, SIMULATED_TREND);

            if (rateLossMax > rateMin2MoveSl) {
                double rateStop = simulate_calRateLossDynamicBuy(rateLossMax, maxChange90M);
                this.priceSL = this.avgEntryPrice * (1.0 + rateStop);
                // Reset minPrice de lan sau check SL chinh xac
                this.minPriceInPosition = this.maxPriceInPosition;
            }
        }

        boolean checkDcaCondition(KlineObjectSimple ticker, boolean isTrend) {
            double rateLoss = (ticker.priceClose - this.avgEntryPrice) / this.avgEntryPrice;
            double marginOfSym = (this.avgEntryPrice * this.totalQuantity) / LEVERAGE;

            return simulate_isDcaWithBtcReverse(
                    rateLoss,
                    HYPOTHETICAL_BUDGET_PER_ORDER,
                    marginOfSym,
                    ticker.priceClose,
                    this.lastEntryPrice,
                    isTrend
            );
        }

        void executeDca(double price) {
            // Tinh toan lai vi the
            double newQuantity = (HYPOTHETICAL_BUDGET_PER_ORDER * LEVERAGE) / price;
            double newTotalCost = (this.avgEntryPrice * this.totalQuantity) + (price * newQuantity);

            this.totalQuantity += newQuantity;
            this.avgEntryPrice = newTotalCost / this.totalQuantity;
            this.lastEntryPrice = price;

            // Reset lai cac chi so theo doi
            this.priceSL = 0.0;
            this.maxPriceInPosition = price;
            this.minPriceInPosition = price;

            // System.out.println("--- DA THUC HIEN DCA ---");
        }
    }

    /**
     * Ham ho tro: Tai toan bo du lieu BTC tu 1 file Snappy duy nhat
     * (THAY THE ham doc Aerospike)
     */
    private static TreeMap<Long, KlineObjectSimple> loadAllBtcDataFromFile() throws Exception {

        String btcFilePath = Configs.FOLDER_TICKER_1M + Constants.SYMBOL_PAIR_BTC;
        System.out.println("Dang doc file BTC tu: " + btcFilePath);

        @SuppressWarnings("unchecked") // Can thiet cho viec ep kieu
        List<KlineObjectSimple> ticker1Ms =
                (List<KlineObjectSimple>) StorageSnappy.readObjectFromFile(btcFilePath);

        if (ticker1Ms == null || ticker1Ms.isEmpty()) {
            throw new RuntimeException("Khong the tai file BTC hoac file bi trong: " + btcFilePath);
        }

        TreeMap<Long, KlineObjectSimple> btcDataMap = new TreeMap<>();
        for (KlineObjectSimple kline : ticker1Ms) {
            // Dam bao chuyen doi startTime (Double) sang Long
            btcDataMap.put(kline.startTime.longValue(), kline);
        }

        return btcDataMap;
    }

    /**
     * Ham ho tro: Tinh toan 11 features
     * (Giu nguyen)
     */
    public static Map<String, Double> calculateFeatures(List<KlineObjectSimple> klines, List<Double> closePrices, long timestamp) {
        Map<String, Double> features = new HashMap<>();

        KlineObjectSimple lastKline = klines.get(klines.size() - 1);
        double currentPrice = lastKline.priceClose;

        // --- 7 Features Cu ---
        double high_15m = findMaxPrice(klines.subList(Math.max(0, klines.size() - 15), klines.size()));
        double high_30m = findMaxPrice(klines.subList(Math.max(0, klines.size() - 30), klines.size()));
        double high_60m = findMaxPrice(klines.subList(Math.max(0, klines.size() - 60), klines.size()));

        KlineObjectSimple kline_5m_ago = klines.get(klines.size() - 6);

        features.put("btc_rate_vs_15m_high", (currentPrice - high_15m) / high_15m);
        features.put("btc_rate_vs_30m_high", (currentPrice - high_30m) / high_30m);
        features.put("btc_rate_vs_60m_high", (currentPrice - high_60m) / high_60m);
        features.put("btc_rate_change_1m", Utils.rateOf2Double(lastKline.priceClose, lastKline.priceOpen));
        features.put("btc_rate_change_5m", Utils.rateOf2Double(currentPrice, kline_5m_ago.priceClose));
        features.put("isTrendBuyWithETH", getTrend(Constants.SYMBOL_PAIR_ETH, timestamp) ? 1.0 : 0.0);
        features.put("isTrendBuyWithBTC", getTrend(Constants.SYMBOL_PAIR_BTC, timestamp) ? 1.0 : 0.0);

        // --- 4 Features Moi (TA) ---
        features.put("rsi_14", TechnicalAnalysisUtils.calculateRSI(klines, RSI_PERIOD));
        features.put("atr_14", TechnicalAnalysisUtils.calculateATR(klines, ATR_PERIOD));

        Map<String, Double> bb_bands = TechnicalAnalysisUtils.calculateBollingerBands(klines, BB_PERIOD, 2.0);
        if (bb_bands == null) return null;
        double bb_width = (bb_bands.get("UPPER") - bb_bands.get("LOWER")) / bb_bands.get("MIDDLE");
        features.put("bb_width_20", bb_width);

        Map<String, Double> macd = calculateMACD(closePrices, MACD_FAST, MACD_SLOW, MACD_SIGNAL);
        if (macd == null) return null;
        features.put("macd_hist", macd.get("hist"));

        return features;
    }
    // --- Cac ham ho tro khac (Giu nguyen) ---

    private static double findMaxPrice(List<KlineObjectSimple> klines) {
        double maxPrice = 0;
        for (KlineObjectSimple kline : klines) {
            if (kline.maxPrice > maxPrice) {
                maxPrice = kline.maxPrice;
            }
        }
        return maxPrice;
    }

    private static boolean getTrend(String symbol, Long time) {
        if (CACHED_symbol2TrendData == null || !CACHED_symbol2TrendData.containsKey(symbol)) {
            return false;
        }
        long timeKey = Utils.getDate(time);
        Boolean trend = CACHED_symbol2TrendData.get(symbol).get(timeKey);
        return trend != null && trend;
    }

    private static void setupCsvFile() throws java.io.IOException {
        File csvFile = new File(CSV_FILE_PATH);
        File parentDir = csvFile.getParentFile();
        if (parentDir != null && !parentDir.exists()) {
            System.out.println("Dang tao thu muc (directory) bi thieu: " + parentDir.getAbsolutePath());
            if (!parentDir.mkdirs()) {
                throw new java.io.IOException("Khong the tao thu muc: " + parentDir.getAbsolutePath());
            }
        }
    }

    // --- LOGIC TINH MACD (Giu nguyen) ---

    private static double calculateEMA(List<Double> prices, int period, double previousEMA) {
        double multiplier = 2.0 / (period + 1);
        double currentPrice = prices.get(prices.size() - 1);
        return (currentPrice - previousEMA) * multiplier + previousEMA;
    }

    private static double calculateSMA(List<Double> prices, int period) {
        double sum = 0;
        List<Double> sublist = prices.subList(prices.size() - period, prices.size());
        for (double price : sublist) {
            sum += price;
        }
        return sum / period;
    }

    private static Map<String, Double> calculateMACD(List<Double> closePrices, int fast, int slow, int signal) {
        if (closePrices.size() < (slow + signal)) {
            return null; // Khong du du lieu
        }

        List<Double> emaFastList = new ArrayList<>();
        List<Double> emaSlowList = new ArrayList<>();
        List<Double> macdList = new ArrayList<>();
        List<Double> signalList = new ArrayList<>();

        double firstEmaFast = calculateSMA(closePrices.subList(0, fast), fast);
        double firstEmaSlow = calculateSMA(closePrices.subList(0, slow), slow);
        emaFastList.add(firstEmaFast);
        emaSlowList.add(firstEmaSlow);

        for (int i = fast; i < closePrices.size(); i++) {
            List<Double> subPricesFast = closePrices.subList(0, i + 1);
            List<Double> subPricesSlow = closePrices.subList(0, i + 1);

            if (i >= slow) {
                double emaSlow = calculateEMA(subPricesSlow, slow, emaSlowList.get(emaSlowList.size() - 1));
                emaSlowList.add(emaSlow);
            }
            double emaFast = calculateEMA(subPricesFast, fast, emaFastList.get(emaFastList.size() - 1));
            emaFastList.add(emaFast);

            if (i >= (slow - 1)) {
                macdList.add(emaFastList.get(emaFastList.size() - 1) - emaSlowList.get(emaSlowList.size() - 1));
            }
        }

        if (macdList.size() < signal) return null;
        double firstSignal = calculateSMA(macdList.subList(0, signal), signal);
        signalList.add(firstSignal);

        for (int i = signal; i < macdList.size(); i++) {
            List<Double> subMacd = macdList.subList(0, i + 1);
            double emaSignal = calculateEMA(subMacd, signal, signalList.get(signalList.size() - 1));
            signalList.add(emaSignal);
        }

        double macdValue = macdList.get(macdList.size() - 1);
        double signalValue = signalList.get(signalList.size() - 1);
        double histValue = macdValue - signalValue;

        Map<String, Double> result = new HashMap<>();
        result.put("macd", macdValue);
        result.put("signal", signalValue);
        result.put("hist", histValue);
        return result;
    }
}