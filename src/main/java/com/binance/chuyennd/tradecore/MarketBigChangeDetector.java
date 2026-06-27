package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.helper.TickerFuturesHelper;
import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetInfo;
import com.binance.chuyennd.trading.OrderTargetStatus;
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

        MarketDataObject result = new MarketDataObject(rateChangeDownAvg, rateChangeUpAvg, rateChangeDown15MAvg);
        result.rateDown15MAvg = rateChangeDown15MAvg.floatValue();


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
     * MÔ HÌNH GEOMETRIC PROGRESSION (CẤP SỐ NHÂN)
     * Giải quyết bài toán Fat Tails và giảm số lượng tham số cho HPO.
     */

    public static MarketLevelChange getMarketStatus1M(Float rateDownAvg, Float rateUpAvg,
                                                      Float rateDown15MAvg) {

        // 1. BIG UP / BIG DOWN
        // [OFF-CỨNG] MS_UP_BIG_THRES thuộc cụm phẳng → bỏ nhánh BIG_UP (kéo theo DCA BIG_UP + DCA_LOSS_BIG_UP chết).
        if (!Configs.OFF_FLAT_HARD && rateUpAvg > Configs.MS_UP_BIG_THRES) {
            return MarketLevelChange.BIG_UP;
        }
        if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) {
            return MarketLevelChange.BIG_DOWN;
        }

        // 3. SMALL UP / DOWN
        // [OFF-CỨNG] MS_UP_SMALL_THRES thuộc cụm phẳng → bỏ nhánh SMALL_UP.
        if (!Configs.OFF_FLAT_HARD && rateUpAvg > Configs.MS_UP_SMALL_THRES) {
            return MarketLevelChange.SMALL_UP;
        }

        // [OFF-CỨNG] MS_DOWN_SMALL_AVG_OR_15M thuộc cụm phẳng → bỏ nhánh SMALL_DOWN_15M.
        if (!Configs.OFF_FLAT_HARD && (rateDownAvg < Configs.MS_DOWN_SMALL_AVG_OR_15M
                || rateDown15MAvg < Configs.MS_DOWN_SMALL_AVG_OR_15M)) {
            return MarketLevelChange.SMALL_DOWN_15M;
        }

        return null;
    }

    public static boolean isDcaAlt(Float rateDown15MAvg, Float rateDownAvg, Float rateUpAvg) {
        return rateDown15MAvg < Configs.MS_DOWN_BIG_AVG
                || rateDownAvg < Configs.MS_DOWN_BIG_AVG / 3;
    }

    public static boolean is50PercentOrderLoss(
            Collection<OrderTargetInfoTest> runningOrders,
            long currentTime) {

        List<CircuitOrder> recentOrders = new ArrayList<>();
        long lookbackMillis = Configs.CIRCUIT_LOOKBACK_MINUTES * 60000L;

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
        long lookbackMillis = Configs.CIRCUIT_LOOKBACK_MINUTES * 60000L;

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

        return (totalOrders - safeOrders > Configs.MAX_CONCURRENT_ORDERS * Configs.CIRCUIT_DANGER_RATIO);
    }

}


