package com.binance.chuyennd.ai_ml.features.export.dca;

import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.FundingFeeManager;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class DcaFeatureExtractor {
    private static final Logger LOG = LoggerFactory.getLogger(DcaFeatureExtractor.class);
    private final HistoryManager historyManager = new HistoryManager();

    public void updateMarketHistory(Map<String, KlineObjectSimple> snapshot) {
        historyManager.updateHistory(snapshot);
    }

    // Wrapper để Manager gọi tìm Basket
    public List<String> identifyTargetBasket(long currentTimestamp) {
        return historyManager.findPotentialLosers(currentTimestamp);
    }

    public DcaMarketFeatures extractFeatures(long currentTimestamp, OrderTargetInfoTest order,
                                             MarketRateChange marketRate,
                                             Map<String, KlineObjectSimple> currentSnapshot,
                                             double dcaImpactRatio,
                                             List<String> targetBasket) { // Đã BỎ tham số fundingMap

        KlineObjectSimple kline = currentSnapshot.get(order.symbol);
        KlineObjectSimple btcKline = currentSnapshot.get("BTCUSDT");

        if (kline == null) return null;

        DcaMarketFeatures f = new DcaMarketFeatures();

        // 1. POSITION CONTEXT
        f.dcaImpactRatio = dcaImpactRatio;
        f.currentDrawdown = (order.priceEntry - kline.priceClose) / order.priceEntry;

        Double price1Hago = historyManager.getPriceAt(order.symbol, currentTimestamp - 3600000);
        if (price1Hago != null && price1Hago > 0) {
            f.lossVelocity1H = (kline.priceClose - price1Hago) / price1Hago;
        } else {
            f.lossVelocity1H = -f.currentDrawdown;
        }

        // 2. MACRO BTC
        double rateBtc = 0.0;
        double rateBtc1H = 0.0;
        if (btcKline != null) {
            Double btcPrice24h = historyManager.getPriceAt("BTCUSDT", currentTimestamp - 24 * 3600000);
            if (btcPrice24h != null && btcPrice24h > 0) rateBtc = (btcKline.priceClose - btcPrice24h) / btcPrice24h;

            Double btcPrice1h = historyManager.getPriceAt("BTCUSDT", currentTimestamp - 3600000);
            if (btcPrice1h != null && btcPrice1h > 0) rateBtc1H = (btcKline.priceClose - btcPrice1h) / btcPrice1h;
        }
        f.btcMomentum1H = rateBtc1H;
        f.btcMomentum24H = rateBtc;

        // 3. RELATIVE STRENGTH & MARKET CONTEXT
        Double coinPrice24h = historyManager.getPriceAt(order.symbol, currentTimestamp - 24 * 3600000);
        double coinRate24H = (coinPrice24h != null && coinPrice24h > 0) ? (kline.priceClose - coinPrice24h) / coinPrice24h : 0.0;

        f.instantAlpha = coinRate24H - rateBtc;
        f.recoveryElasticity = calculateElasticity(order.symbol, kline);
        f.dangerIndex = (f.lossVelocity1H * 50) + (f.instantAlpha * 50);

        f.crashVelocity = marketRate != null ? marketRate.rateDown15MAvg : 0.0;
        f.globalRateDownAvg = marketRate != null ? marketRate.rateDownAvg : 0.0;

        // 4. TECHNICALS
        f.rsi1H = historyManager.getRsi14(order.symbol);
        f.distFromLow24H = calculateDistFromLow24H(order.symbol, kline);
        f.maxRateChange60M = historyManager.getMaxRateChange(order.symbol, 60);

        f.volumeSpike = calculateVolumeSpike(order.symbol, kline);
        f.volumeAnomaly = f.volumeSpike;
        f.volatilityShock = calculateVolatilityShock(order.symbol, kline);

        // 5. BASKET SPECIFIC
        if (targetBasket == null || targetBasket.isEmpty()) targetBasket = Collections.singletonList(order.symbol);
        extractBasketTechnicalFeatures(f, targetBasket);

        // 6. FUNDING (Logic Clone 100% từ Entry)
        extractBasketFundingFeatures(f, targetBasket, currentTimestamp);

        // 7. TIME
        extractTimeFeatures(f, currentTimestamp);

        return f;
    }

    // --- LOGIC CLONE: BASKET FUNDING (QUAN TRỌNG) ---
    private void extractBasketFundingFeatures(DcaMarketFeatures features, List<String> basket, long currentTime) {
        try {
            double totalCurrentFunding = 0;
            double totalAvg24H = 0;
            int validCount = 0;

            for (String symbol : basket) {
                // Gọi trực tiếp Singleton giống bên Entry
                Double currentFunding = FundingFeeManager.getInstance().getNearestFundingFee(symbol, currentTime);

                if (currentFunding != null) {
                    totalCurrentFunding += currentFunding;

                    double sum24h = 0;
                    int count24h = 0;
                    // Loop 24h back (0, 4, 8... 24)
                    for (int i = 0; i <= 24; i += 4) {
                        long pastTime = currentTime - (i * 3600 * 1000L);
                        Double past = FundingFeeManager.getInstance().getNearestFundingFee(symbol, pastTime);
                        if (past != null) {
                            sum24h += past;
                            count24h++;
                        }
                    }

                    if (count24h > 0) totalAvg24H += (sum24h / count24h);
                    else totalAvg24H += currentFunding;

                    validCount++;
                }
            }

            if (validCount > 0) {
                features.fundingRateRaw = totalCurrentFunding / validCount;
                features.fundingRateAvg24H = totalAvg24H / validCount;
            } else {
                features.fundingRateRaw = 0.0;
                features.fundingRateAvg24H = 0.0;
            }
            // Trend = Hiện tại - Trung bình 24h (Đang âm thêm hay dương lên?)
            features.fundingRateTrend = features.fundingRateRaw - features.fundingRateAvg24H;

        } catch (Exception e) {
            // Fallback an toàn
            features.fundingRateRaw = 0.0;
            features.fundingRateAvg24H = 0.0;
            features.fundingRateTrend = 0.0;
        }
    }

    private void extractBasketTechnicalFeatures(DcaMarketFeatures features, List<String> basket) {
        double sumRsi = 0, sumMom15m = 0, sumMom1h = 0, sumVolSpike = 0;
        int count = 0;

        for (String symbol : basket) {
            Double rsi = historyManager.getRsi14(symbol);
            if (rsi != null) {
                sumRsi += rsi;
                sumMom15m += calculateReturn(symbol, 15);
                sumMom1h += calculateReturn(symbol, 60);

                List<KlineObjectSimple> h = historyManager.getHistory(symbol);
                if (h != null && !h.isEmpty()) {
                    KlineObjectSimple current = h.get(h.size() - 1);
                    double avgVol = historyManager.getAverageVolume(symbol, 20);
                    if (avgVol > 0) sumVolSpike += current.totalUsdt / avgVol;
                    else sumVolSpike += 1.0;
                }
                count++;
            }
        }

        if (count > 0) {
            features.basketRsi14 = sumRsi / count;
            features.basketMomentum15M = sumMom15m / count;
            features.basketMomentum1H = sumMom1h / count;
            features.basketVolSpike = sumVolSpike / count;
        } else {
            features.basketRsi14 = features.rsi1H;
            features.basketMomentum15M = 0.0;
            features.basketMomentum1H = features.lossVelocity1H;
            features.basketVolSpike = features.volumeSpike;
        }
    }

    private void extractTimeFeatures(DcaMarketFeatures features, long timestamp) {
        Calendar c = Calendar.getInstance();
        c.setTimeInMillis(timestamp);
        features.hourOfDay = c.get(Calendar.HOUR_OF_DAY);
        features.dayOfWeek = c.get(Calendar.DAY_OF_WEEK);
        features.weekOfMonth = c.get(Calendar.WEEK_OF_MONTH);
        features.monthOfYear = c.get(Calendar.MONTH) + 1;
    }

    // Helpers
    private double calculateReturn(String symbol, int minutes) {
        List<KlineObjectSimple> h = historyManager.getHistory(symbol);
        if (h == null || h.isEmpty()) return 0.0;
        KlineObjectSimple current = h.get(h.size() - 1);
        long pastTime = current.startTime.longValue() - (minutes * 60000L);
        Double pastPrice = historyManager.getPriceAt(symbol, pastTime);
        if (pastPrice != null && pastPrice > 0) {
            return (current.priceClose - pastPrice) / pastPrice;
        }
        return 0.0;
    }

    private double calculateElasticity(String symbol, KlineObjectSimple kline) {
        Double ma20 = historyManager.getMa(symbol, 20);
        return (ma20 != null && ma20 > 0) ? (kline.priceClose - ma20) / ma20 : 0.0;
    }

    private double calculateDistFromLow24H(String symbol, KlineObjectSimple kline) {
        Double low24 = historyManager.getLow24H(symbol);
        return (low24 != null && low24 > 0) ? (kline.priceClose - low24) / low24 : 0.0;
    }

    private double calculateVolumeSpike(String symbol, KlineObjectSimple kline) {
        double avgVol = historyManager.getAverageVolume(symbol, 20);
        return (avgVol > 0) ? kline.totalUsdt / avgVol : 1.0;
    }

    private double calculateVolatilityShock(String symbol, KlineObjectSimple kline) {
        double avgRange = historyManager.getAverageRange(symbol, 20);
        double currentRange = kline.maxPrice - kline.minPrice;
        return (avgRange > 0) ? currentRange / avgRange : 1.0;
    }
}