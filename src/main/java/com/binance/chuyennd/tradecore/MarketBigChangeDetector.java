package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.MarketDataObject15M;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.enums.OrderSide;
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

    public static MarketDataObject15M calMarketData(Map<String, KlineObjectSimple> symbol2Ticker, Map<String, Float> symbol2PriceMax,
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
        MarketDataObject15M result = new MarketDataObject15M(rateChangeDownAvg, rateChangeUpAvg, rateChangeDown15MAvg);
        result.rateDown4HAvg = rateChangeDown15MAvg.floatValue();


        return result;
    }

    // Thêm <K> vào hàm getTopSymbol
    public static <K> Set<K> getTopSymbol(int period,
                                          Map<K, KlineObjectSimple> symbol2FinalTicker,
                                          Set<K> symbolLocked,
                                          TreeMap<Float, K> predict2Symbol) {
        Set<K> symbols = new HashSet<>();
        if (predict2Symbol != null && !predict2Symbol.isEmpty()) {
            for (Map.Entry<Float, K> entry : predict2Symbol.entrySet()) {
                K symbolKey = entry.getValue(); // Có thể là String hoặc Short

                if (symbolLocked != null && symbolLocked.contains(symbolKey)) {
                    continue;
                }

                KlineObjectSimple ticker = symbol2FinalTicker.get(symbolKey);
                if (ticker != null) {
                    symbols.add(symbolKey);
                }
                if (symbols.size() >= period) {
                    break;
                }
            }
        }
        return symbols;
    }

    public static Set<Short> getTopSymbolArray(int period,
                                               KlineObjectSimple[] symbol2FinalTicker,
                                               Set<Short> symbolLocked,
                                               TreeMap<Float, Short> predict2Symbol) {
        Set<Short> symbols = new HashSet<>();
        if (predict2Symbol != null && !predict2Symbol.isEmpty()) {
            for (Map.Entry<Float, Short> entry : predict2Symbol.entrySet()) {
                Short symbolKey = entry.getValue(); // Có thể là String hoặc Short

                if (symbolLocked != null && symbolLocked.contains(symbolKey)) {
                    continue;
                }

                KlineObjectSimple ticker = symbol2FinalTicker[symbolKey];
                if (ticker != null) {
                    symbols.add(symbolKey);
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

    /**
     * @param predReturn15M: Giá trị AI dự báo (Ví dụ: 0.015)
     * @param k_down:        Tham số HPO 1 (Ví dụ: 0.8)
     * @param k_up:          Tham số HPO 2 (Ví dụ: 1.0)
     */
    public static MarketLevelChange getMarketStatus1MDynamic(Float rateDownAvg, Float rateUpAvg,
                                                             Float rateDown15MAvg, Float predReturn15M,
                                                             float k_down, float k_up) {

        // 1. Lấy Volatility động từ AI
        // Lấy giá trị tuyệt đối để làm baseline. Đặt đáy 0.5% (0.005) để tránh lúc AI dự báo Vol = 0 gây lỗi chia
        float v = (predReturn15M != null && Math.abs(predReturn15M) > 0.005f) ? Math.abs(predReturn15M) : 0.005f;

        // 2. TỰ ĐỘNG SINH CÁC NGƯỠNG (Ép 12 param thành logic nội suy)
        // Hệ số phân bậc: Nhỏ (x1) -> Vừa (x2) -> Lớn (x3)
        float dynDownSmall = -(v * k_down);         // Vd: -0.01
        float dynDownMed = -(v * k_down * 2.0f);  // Vd: -0.02
        float dynDownBig = -(v * k_down * 3.0f);  // Vd: -0.03

        float dynUpSmall = (v * k_up);            // Vd: 0.01
        float dynUpMed = (v * k_up * 2.0f);     // Vd: 0.02
        float dynUpBig = (v * k_up * 3.0f);     // Vd: 0.03

        // 3. Logic bắt Tín hiệu

        // 3.1 BIG UP / DOWN
        if (rateUpAvg > dynUpBig) return MarketLevelChange.BIG_UP;
        if (rateDownAvg < dynDownBig) return MarketLevelChange.BIG_DOWN;

        // 3.2 MEDIUM UP / DOWN
        if (rateUpAvg > dynUpMed) return MarketLevelChange.MEDIUM_UP;

        // Gộp chung điều kiện Medium: Avg sập hoặc 15M sập mạnh
        if (rateDownAvg < dynDownMed || rateDown15MAvg < (dynDownMed * 1.5f)) {
            return MarketLevelChange.MEDIUM_DOWN;
        }

        // 3.3 SMALL UP / DOWN
        if (rateUpAvg > dynUpSmall && rateDownAvg > 0) return MarketLevelChange.SMALL_UP;
        if (rateDownAvg < dynDownSmall && rateUpAvg < 0 && rateDown15MAvg < dynDownSmall) {
            return MarketLevelChange.SMALL_DOWN;
        }

        // 3.4 15M ONLY (Đánh bắt gãy khung ngắn)
        if (rateDown15MAvg < dynDownMed) return MarketLevelChange.MEDIUM_DOWN_15M;
        if (rateDown15MAvg < dynDownSmall) return MarketLevelChange.SMALL_DOWN_15M;

        return null;
    }

    /**
     * MÔ HÌNH GEOMETRIC PROGRESSION (CẤP SỐ NHÂN)
     * Giải quyết bài toán Fat Tails và giảm số lượng tham số cho HPO.
     */
    public static MarketLevelChange getMarketStatus1MGeometric(
            Float rateDownAvg, Float rateUpAvg, Float rateDown15MAvg,
            float baseDown, float ratioDown,
            float baseUp, float ratioUp) {

        // --- CHIỀU DOWN (Tính bằng số âm) ---
        // Ví dụ: baseDown = 0.005 (0.5%), ratioDown = 2.0
        // Small = -0.005 | Med = -0.010 | Big = -0.020
        float downSmall = -baseDown;
        float downMed = downSmall * ratioDown;
        float downBig = downMed * ratioDown;

        // 15M Threshold (Khung ngắn giật râu mạnh hơn, nhân hệ số giãn 1.5)
        float down15mSmall = downSmall * 1.5f;
        float down15mMed = downMed * 1.5f;

        // --- CHIỀU UP (Tính bằng số dương) ---
        float upSmall = baseUp;
        float upMed = upSmall * ratioUp;
        float upBig = upMed * ratioUp;

        // --- LOGIC PHÂN LOẠI THỊ TRƯỜNG (Ưu tiên check mốc Lớn nhất trước) ---

        // 1. BIG (Bão bùng / Thiên nga đen)
        if (rateDownAvg < downBig) return MarketLevelChange.BIG_DOWN;
        if (rateUpAvg > upBig) return MarketLevelChange.BIG_UP;

        // 2. MEDIUM (Sóng vừa)
        if (rateDownAvg < downMed) return MarketLevelChange.MEDIUM_DOWN;
        if (rateDown15MAvg < down15mMed) return MarketLevelChange.MEDIUM_DOWN_15M;
        if (rateUpAvg > upMed) return MarketLevelChange.MEDIUM_UP;

        // 3. SMALL (Sóng lăn tăn)
        if (rateDownAvg < downSmall && rateUpAvg < 0 && rateDown15MAvg < down15mSmall) {
            return MarketLevelChange.SMALL_DOWN;
        }
        if (rateUpAvg > upSmall && rateDownAvg > 0) {
            return MarketLevelChange.SMALL_UP;
        }

        // 4. 15M ONLY (Rớt mạnh khung ngắn nhưng Avg tổng chưa rớt)
        if (rateDown15MAvg < down15mSmall) return MarketLevelChange.SMALL_DOWN_15M;

        return null;
    }

    public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg,
                                                      Float rateDown15MAvg) {

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
        if (rateDownAvg < Configs.MS_DOWN_MED_AVG) {
            return MarketLevelChange.MEDIUM_DOWN;
        }

        // 3. SMALL UP / DOWN
        if (rateUpAvg > Configs.MS_UP_SMALL_THRES && rateDownAvg > 0) {
            return MarketLevelChange.SMALL_UP;
        }
        if (rateDownAvg < Configs.MS_DOWN_SMALL_AVG) {
            return MarketLevelChange.SMALL_DOWN;
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

    public static boolean is50PercentOrderLoss(
            Collection<OrderTargetInfoTest> runningOrders,
            long currentTime) {

        List<CircuitOrder> recentOrders = new ArrayList<>();
        long lookbackMillis = 240 * 60000L; // Soi 4 tiếng quay đầu

        if (runningOrders != null) {
            for (OrderTargetInfoTest o : runningOrders) {
                if (currentTime - o.timeStart <= lookbackMillis) {
                    recentOrders.add(new CircuitOrder(o.timeStart, o.status, o.priceSL != null, false)); // Lệnh đang chạy thì chưa chốt lãi
                }
            }
        }
        return evaluateCircuitBreakerCore(recentOrders, currentTime);
    }

    // 1. Tạo một Object siêu nhẹ để chứa chung dữ liệu cho cả Test và Prod
    public static class CircuitOrder {
        public long timeStart;
        public OrderTargetStatus status;
        public boolean hasPriceSL;
        public boolean isProfitable;

        public CircuitOrder(long timeStart, OrderTargetStatus status, boolean hasPriceSL, boolean isProfitable) {
            this.timeStart = timeStart;
            this.status = status;
            this.hasPriceSL = hasPriceSL;
            this.isProfitable = isProfitable;
        }
    }

    /**
     * 2. Hàm VỎ (Wrapper) dành riêng cho MÔI TRƯỜNG PRODUCTION (Real Trade)
     */
    public static boolean is50PercentOrderLossProd(
            Collection<OrderTargetInfo> runningOrders,
            long currentTime) {

        List<CircuitOrder> recentOrders = new ArrayList<>();
        long lookbackMillis = 240 * 60000L;

        if (runningOrders != null) {
            for (OrderTargetInfo o : runningOrders) {
                if (currentTime - o.timeStart <= lookbackMillis) {
                    boolean isProfitable = false;
                    // Lệnh Prod không có calTp(), ta nhẩm tính Lãi dựa vào Entry và TP/Giá hiện tại
                    if (o.priceTP != null && o.priceEntry != null) {
                        isProfitable = (o.side == OrderSide.BUY) ? (o.priceTP > o.priceEntry) : (o.priceEntry > o.priceTP);
                    }
                    recentOrders.add(new CircuitOrder(o.timeStart, o.status, o.priceSL != null, isProfitable));
                }
            }
        }

        return evaluateCircuitBreakerCore(recentOrders, currentTime);
    }

    /**
     * 3. HÀM LÕI (CORE LOGIC) CHUNG CHO CẢ 2 MÔI TRƯỜNG
     */
    private static boolean evaluateCircuitBreakerCore(List<CircuitOrder> recentOrders, long currentTime) {
        if (recentOrders.isEmpty()) return false;

        // Sắp xếp từ mới nhất -> cũ nhất theo timeStart
        recentOrders.sort((o1, o2) -> Long.compare(o2.timeStart, o1.timeStart));

        // =========================================================================
        // LỚP 1: KIỂM TRA MẬT ĐỘ THEO ĐƯỜNG CONG LŨY THỪA (POWER LAW)
        // =========================================================================
        int baseBurst = Configs.MAX_CONCURRENT_ORDERS;
        float sustain = Configs.DENSITY_SUSTAIN;
        float alpha = Configs.DENSITY_ALPHA;

        int orderCount = 1; // Tính luôn lệnh đang chờ duyệt

        for (CircuitOrder order : recentOrders) {
            long diffMillis = currentTime - order.timeStart;
            if (diffMillis < 0) continue;

            int diffMins = (int) (diffMillis / 60000L);
            int checkMins = Math.max(1, diffMins);

            int allowedOrders = (int) (baseBurst + sustain * Math.pow(checkMins, alpha));
            orderCount++;

            if (orderCount > allowedOrders) {
                return true; // Vượt mật độ -> Chặn
            }
        }

        // =========================================================================
        // LỚP 2: CẦU DAO CHỐNG BÃO (ĐÁNH GIÁ LẠI TỶ LỆ LỖ THỰC SỰ)
        // =========================================================================
        int totalOrders = recentOrders.size();

        // Vùng miễn trừ: Vẫn cho phép xả một lượng đạn nhất định lúc bão mới tới
        if (totalOrders < (baseBurst / 2.0)) {
            return false;
        }

        int safeOrders = 0;
        for (CircuitOrder info : recentOrders) {
            // Lệnh ĐÃ ĐÓNG: Được tính là an toàn nếu chốt lời dương
            boolean isDoneAndProfitable = (info.status == OrderTargetStatus.TAKE_PROFIT_DONE)
                    || (info.status == OrderTargetStatus.STOP_MARKET_DONE && info.isProfitable);

            // Lệnh ĐANG CHẠY: Được tính là an toàn nếu đã dời Stoploss dương
            boolean isRunningAndSafe = (info.status != OrderTargetStatus.TAKE_PROFIT_DONE
                    && info.status != OrderTargetStatus.STOP_LOSS_DONE
                    && info.hasPriceSL);

            if (isDoneAndProfitable || isRunningAndSafe) {
                safeOrders++;
            }
        }

        return (totalOrders - safeOrders > Configs.MAX_CONCURRENT_ORDERS * 0.7);
    }

    public static com.binance.chuyennd.object.MarketDataObject15M calMarketData15M(
            Map<Short, com.binance.chuyennd.object.sw.KlineObjectSimple> symbol2Ticker,
            Map<Short, Float> symbol2PriceMax,
            Map<Short, Float> symbol2MinPrice) {

        TreeMap<Float, Short> rateDown2Symbols = new TreeMap<>();
        TreeMap<Float, Short> rateMin2Symbols = new TreeMap<>();
        TreeMap<Float, Short> rateMax2Symbols = new TreeMap<>();
        TreeMap<Float, Short> rateUp2Symbols = new TreeMap<>();

        // Lấy ID của BTCUSDT một lần duy nhất
        short btcId = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getId(com.binance.client.constant.Constants.SYMBOL_PAIR_BTC);
        com.binance.chuyennd.object.sw.KlineObjectSimple btcTicker = symbol2Ticker.get(btcId);
        Float rateChangeBtc = (btcTicker != null) ? com.binance.chuyennd.utils.Utils.rateOf2Double(btcTicker.priceClose, btcTicker.priceOpen) : 0f;

        for (Map.Entry<Short, com.binance.chuyennd.object.sw.KlineObjectSimple> entry : symbol2Ticker.entrySet()) {
            short symId = entry.getKey();
            // Optional: Bác có thể cache diedSymbol thành Set<Short> để filter O(1) chỗ này

            com.binance.chuyennd.object.sw.KlineObjectSimple ticker = entry.getValue();
            Float rateChange = com.binance.chuyennd.utils.Utils.rateOf2Double(ticker.priceClose, ticker.priceOpen).floatValue();

            if (rateChangeBtc > -0.004 && rateChange < -0.15) continue;
            if (rateChange > 0.3) continue;

            rateDown2Symbols.put(rateChange, symId);
            rateUp2Symbols.put(-rateChange, symId);

            Float maxPrice = symbol2PriceMax.get(symId);
            if (maxPrice != null) {
                rateMax2Symbols.put(com.binance.chuyennd.utils.Utils.rateOf2Double(ticker.priceClose, maxPrice).floatValue(), symId);
            }

            Float minPrice = symbol2MinPrice.get(symId);
            if (minPrice != null) {
                rateMin2Symbols.put(-com.binance.chuyennd.utils.Utils.rateOf2Double(ticker.priceClose, minPrice).floatValue(), symId);
            }
        }

        // Hàm calRateChangeAvg của bác có thể ép kiểu Float qua String, nhưng ở đây tính AVG thì key (Float) là đủ rồi
        Float rateChangeDownAvg = calRateChangeAvgShort(rateDown2Symbols, 100);
        Float rateChangeUpAvg = -calRateChangeAvgShort(rateUp2Symbols, 100);
        Float rateChangeDown4HAvg = calRateChangeAvgShort(rateMax2Symbols, 100);

        return new com.binance.chuyennd.object.MarketDataObject15M(rateChangeDownAvg, rateChangeUpAvg, rateChangeDown4HAvg);
    }

    // Viết thêm hàm nhỏ này để nó nhận TreeMap<Float, Short>
    public static Float calRateChangeAvgShort(TreeMap<Float, Short> rateLoss2Symbols, Integer period) {
        Float total = 0f; int counter = 0;
        if (period > rateLoss2Symbols.size() * 4 / 5) period = rateLoss2Symbols.size() * 4 / 5;
        for (Map.Entry<Float, Short> entry : rateLoss2Symbols.entrySet()) {
            counter++; total += entry.getKey();
            if (period != null && counter >= period) break;
        }
        return rateLoss2Symbols.isEmpty() ? 0f : total / counter;
    }
}


