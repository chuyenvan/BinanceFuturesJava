package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.ai_ml.features.export.HistoryManager;
import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.CoinTier;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.ParseException;
import java.util.*;

public class MarketBigChangeDetector {
    public static final Logger LOG = LoggerFactory.getLogger(MarketBigChangeDetector.class);

    public static void main(String[] args) throws ParseException {
        try {
//            Long startTime = Utils.sdfFileHour.parse("20250831 19:23").getTime();
//
//            List<KlineObjectNumber> btcTickers = TickerFuturesHelper.getTickerWithStartTime(Constants.SYMBOL_PAIR_BTC, Constants.INTERVAL_1M,
//                    startTime - 360 * Utils.TIME_MINUTE);
//            while (true) {
//                if (btcTickers.get(btcTickers.size() - 1).startTime.longValue() > startTime) {
//                    btcTickers.remove(btcTickers.size() - 1);
//                } else {
//                    break;
//                }
//            }
//
//            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(0).startTime.longValue()),
//                    Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
//
//            System.out.println(MarketBigChangeDetector.isBtcTrendReverse(btcTickers));

//            btcTickers.remove(btcTickers.size() - 1);
//            if (MarketBigChangeDetector.isBtcTrendReverse(btcTickers)) {
//                // check last time not btc trend reverse -> btc trend reverse
//                String finalTimeTrendReverse = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
//                        MarketLevelChange.BTC_TREND_REVERSE.toString());
//                if (finalTimeTrendReverse == null || Long.parseLong(finalTimeTrendReverse) < btcTickers.get(btcTickers.size() - 1).startTime.longValue()) {
//                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_MARKET_LEVEL_FINAL,
//                            MarketLevelChange.BTC_TREND_REVERSE.toString(), String.valueOf(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
//                    LOG.info("Fixbug btc trend reverse error {} ",
//                            Utils.normalizeDateYYYYMMDDHHmm(btcTickers.get(btcTickers.size() - 1).startTime.longValue()));
//                }
//            }
            Long start = Utils.sdfFileHour.parse("20250830 23:11").getTime();
            for (int i = 0; i < 100; i++) {
                Long startTime = start - Utils.TIME_MINUTE * i;
                String symbol = "MUSDT";
//                List<KlineObjectNumber> tickerProds = TickerFuturesHelper.getTickerWithStartTime(symbol, Constants.INTERVAL_1M,
//                        startTime - 60 * Utils.TIME_MINUTE);
                List<KlineObjectSimple> tickers = TickerFuturesHelper.getTickerSimpleWithStartTime(symbol, Constants.INTERVAL_1M,
                        startTime - 60 * Utils.TIME_MINUTE);
                while (true) {
                    if (tickers.get(tickers.size() - 1).startTime.longValue() > startTime) {
                        tickers.remove(tickers.size() - 1);
                    } else {
                        break;
                    }

                }

            }

        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static MarketDataObject calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, Float> symbol2PriceMax,
                                                 Map<String, Float> symbol2MinPrice) {
        TreeMap<Float, String> rateDown2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateMin2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateMax2Symbols = new TreeMap<>();
        TreeMap<Float, String> rateUp2Symbols = new TreeMap<>();
        KlineObjectSimple btcTicker = symbol2Ticker.get(Constants.SYMBOL_PAIR_BTC);
        Float rateChangeBtc;
        if (btcTicker == null) {
            rateChangeBtc = 0f;
        } else {
            rateChangeBtc = Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen);
        }
        for (Map.Entry<String, KlineObjectSimple> entry1 : symbol2Ticker.entrySet()) {
            String symbol = entry1.getKey();
            if (Constants.diedSymbol.contains(symbol)) {
                continue;
            }
            KlineObjectSimple ticker = entry1.getValue();
            Float rateChange = Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen).floatValue();
            // pass symbol big dump(delist/waring/monitor...)
            if (rateChangeBtc > -0.004 && rateChange < -0.15) {
                continue;
            }
            if (rateChange > 0.3) {
                continue;
            }
            rateDown2Symbols.put(rateChange, symbol);
            rateUp2Symbols.put(-rateChange, symbol);
            Float maxPrice = symbol2PriceMax.get(symbol);
            if (maxPrice != null) {
                rateMax2Symbols.put(Utils.rateOf2Double(ticker.priceClose, maxPrice).floatValue(), symbol);
            }
            Float minPrice = symbol2MinPrice.get(symbol);
            if (minPrice != null) {
                rateMin2Symbols.put(-Utils.rateOf2Double(ticker.priceClose, minPrice).floatValue(), symbol);
            }
        }
        Float rateChangeDownAvg = MarketBigChangeDetector.calRateChangeAvg(rateDown2Symbols, 100);
        Float rateChangeUpAvg = -MarketBigChangeDetector.calRateChangeAvg(rateUp2Symbols, 100);
        Float rateChangeDown15MAvg = MarketBigChangeDetector.calRateChangeAvg(rateMax2Symbols, 100);

//        List<String> symbolsTopDown = MarketBigChangeDetectorTest.getTopSymbolSimple(rateDown2Symbols,
//                Configs.NUMBER_ENTRY_EACH_SIGNAL, null);
        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, rateChangeDown15MAvg);
        result.rateBtc = rateChangeBtc.floatValue();
        result.rateDown15MAvg = rateChangeDown15MAvg.floatValue();


        return result;
    }

    public static Set<String> getTopSymbol(int period, Map<String,
            KlineObjectSimple> symbol2FinalTicker, Set<String> symbolLocked, TreeMap<Float, String> predict2Symbol) {
        Set<String> symbols = new HashSet<>();
        if (predict2Symbol != null && !predict2Symbol.isEmpty()) {
            for (Map.Entry<Float, String> entry : predict2Symbol.entrySet()) {
                String symbol = entry.getValue();
                if (symbolLocked != null && symbolLocked.contains(symbol)) {
//                LOG.info("Not trade {} because symbol locking: {}",
//                        symbol, Utils.normalizeDateYYYYMMDDHHmm(System.currentTimeMillis()));
                    continue;
                }
                KlineObjectSimple ticker = symbol2FinalTicker.get(symbol);
                if (ticker != null) {
                    symbols.add(symbol);
                }
                if (symbols.size() >= period) {
                    break;
                }
            }

        }
        return symbols;
    }


    public static Float calRateChangeAvg(TreeMap<Float, String> rateLoss2Symbols, Integer period) {
        Float total = 0f;
        int counter = 0;
        if (period > rateLoss2Symbols.size() * 4 / 5) {
            period = rateLoss2Symbols.size() * 4 / 5;
        }
        for (Map.Entry<Float, String> entry : rateLoss2Symbols.entrySet()) {
            Float key = entry.getKey();
            counter++;
            total += key;
            if (period != null && counter >= period) {
                break;
            }
        }
        if (rateLoss2Symbols.isEmpty()) {
            return 0f;
        }
        return total / counter;
    }


    public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg,
                                                      Float btcRateChange, Float rateDown15MAvg) {

        // 1. BIG UP / BIG DOWN
        if (rateUpAvg > Configs.MS_UP_BIG_THRES) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) {
            return MarketLevelChange.BIG_DOWN;
        }

        // 2. MEDIUM UP / DOWN
        if (rateUpAvg > Configs.MS_UP_MED_THRES) {
            return MarketLevelChange.MEDIUM_UP;
        }
        // Logic Medium Down phức tạp (AVG < X HOẶC (AVG < Y VÀ 15M < Z))
        if (rateDownAvg < Configs.MS_DOWN_MED_AVG ||
                (rateDownAvg < Configs.MS_DOWN_MED_AVG_CMB
                        && rateDown15MAvg < Configs.MS_DOWN_MED_15M_CMB
                )
        ) {
            return MarketLevelChange.MEDIUM_DOWN;
        }

        // 3. SMALL UP / DOWN
        if (rateUpAvg > Configs.MS_UP_SMALL_THRES && rateDownAvg > 0) {
            return MarketLevelChange.SMALL_UP;
        }
        if (rateDownAvg < Configs.MS_DOWN_SMALL_AVG && rateUpAvg < 0
                && rateDown15MAvg < Configs.MS_DOWN_SMALL_15M
        ) {
            return MarketLevelChange.SMALL_DOWN;
        }

        // 4. RIÊNG BIỆT THEO 15M (Trường hợp Avg không giảm mạnh nhưng 15M sập)
        if (rateDown15MAvg < Configs.MS_DOWN_15M_MED_ONLY) {
            return MarketLevelChange.MEDIUM_DOWN_15M;
        }
        if (rateDown15MAvg < Configs.MS_DOWN_15M_SMALL_ONLY) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }

        return null;
    }

    public static boolean isDcaAlt(Float rateDown15MAvg,
                                   Float rateDownAvg,
                                   Float rateUpAvg) {
        return rateDown15MAvg < -0.035
                || rateUpAvg > 0.012
                || rateDownAvg < -0.012;
    }


    public static boolean is50PercentOrderLoss(Map<String, OrderTargetInfoTest> symbolTradeInLastest, long currentTime) {
        if (symbolTradeInLastest == null || symbolTradeInLastest.isEmpty()) {
            return false;
        }

        List<OrderTargetInfoTest> recentOrders = new ArrayList<>(symbolTradeInLastest.values());
        recentOrders.sort((o1, o2) -> Long.compare(o2.timeStart, o1.timeStart));

        // =========================================================================
        // LỚP 1: KIỂM TRA MẬT ĐỘ THEO "TOKEN BUCKET" (CHUẨN INSIGHT THỰC CHIẾN)
        // =========================================================================
        int baseBurst = Configs.MAX_CONCURRENT_ORDERS; // Sức nổ (VD: 30)
        float recoveryRate = Configs.RECOVERY_RATE_PER_MIN; // CHỈ SỐ DUY NHẤT ĐỂ HPO DÒ TÌM

        int orderCount = 1; // Tính luôn lệnh đang chờ duyệt

        for (OrderTargetInfoTest order : recentOrders) {
            if (order == null) continue;

            long diffMillis = currentTime - order.timeStart;
            if (diffMillis < 0) continue;

            int diffMins = (int) (diffMillis / 60000L);

            // Quá 4H (240p) thì bỏ qua, không tính làm áp lực nữa
            if (diffMins > 240) break;

            // CÔNG THỨC: 10 phút đầu giữ nguyên Base Burst. Sau 10 phút cộng thêm Recovery Rate
            float extraOrders = Math.max(0, diffMins - 10) * recoveryRate;
            int allowedOrders = baseBurst + (int) extraOrders;

            orderCount++;

            // Chặn ngay nếu vượt ngưỡng động tại bất kỳ thời điểm nào trong quá khứ
            if (orderCount > allowedOrders) {
                return true;
            }
        }

        // =========================================================================
        // LỚP 2: CẦU DAO CHỐNG BÃO (Dựa trên tỷ lệ lỗ)
        // =========================================================================
        int totalOrders = recentOrders.size();

        // Cho phép bot xả đạn đủ một nửa sức nổ rồi mới check cầu dao
        if (totalOrders < (baseBurst / 2.0)) {
            return false;
        }

        int safeOrders = 0;
        for (OrderTargetInfoTest info : recentOrders) {
            if (info != null && info.priceSL != null) {
                safeOrders++; // Lệnh đã dời SL là lệnh an toàn
            }
        }

        return safeOrders < (totalOrders / 2.0);
    }
    public static Map<String, CoinTier> rankCoinsByVolume(Set<String> activeSymbols, HistoryManager historyManager) {
        Map<String, CoinTier> symbolTiers = new HashMap<>();
        List<Map.Entry<String, Float>> volumeList = new ArrayList<>();

        // 1. Tính tổng Volume 24H (1440 phút) để xếp hạng độ uy tín
        int lookbackMins = 1440;

        for (String symbol : activeSymbols) {
            // Sử dụng hàm có sẵn của HistoryManager để lấy tổng Volume
            float vol = historyManager.getSumVolume(symbol, lookbackMins);
            volumeList.add(new AbstractMap.SimpleEntry<>(symbol, vol));
        }

        // 2. Sắp xếp giảm dần theo Volume (Thằng to nhất lên đầu)
        volumeList.sort((a, b) -> b.getValue().compareTo(a.getValue()));

        int totalCoins = volumeList.size();
        if (totalCoins == 0) return symbolTiers;

        // 3. Chia mốc 20% - 60% - 20%
        int top20Index = (int) (totalCoins * 0.20);
        int bottom20Index = (int) (totalCoins * 0.80);

        for (int i = 0; i < totalCoins; i++) {
            String symbol = volumeList.get(i).getKey();

            if (i < top20Index) {
                symbolTiers.put(symbol, CoinTier.TIER_1_BLUECHIP);
            } else if (i >= bottom20Index) {
                symbolTiers.put(symbol, CoinTier.TIER_3_SHITCOIN);
            } else {
                symbolTiers.put(symbol, CoinTier.TIER_2_MIDCAP);
            }
        }

        return symbolTiers;
    }
}


