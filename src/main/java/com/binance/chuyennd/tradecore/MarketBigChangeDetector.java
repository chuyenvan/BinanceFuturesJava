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

        // 2026-09-03: co OFF_FLAT_HARD da go -> chi con MOT nhanh song la BIG_DOWN
        // (BIG_UP / SMALL_UP / SMALL_DOWN_15M da bi tat cung tu truoc, nay xoa han).
        if (rateDownAvg < Configs.MS_DOWN_BIG_AVG) {
            return MarketLevelChange.BIG_DOWN;
        }



        return null;
    }

    public static boolean isDcaAlt(Float rateDown15MAvg, Float rateDownAvg, Float rateUpAvg) {
        return rateDown15MAvg < Configs.MS_DOWN_BIG_AVG
                || rateDownAvg < Configs.MS_DOWN_BIG_AVG / 3;
    }

    // ================================================================================
    // KILL-SWITCH AN TOAN - KHONG XOA. Breaker MAT DO mo lenh (chong bao / order storm).
    // Chay o duong LIVE (DetectEntrySignal2TradeNormal.createOrderBuyRequest), DOC LAP voi
    // BREAKER_MODE - tuc no VAN BAT ke ca khi BREAKER_MODE=OFF.
    // (2026-09-03: da tung bi xoa ca sim lan live trong dot refactor "xoa tham so tro". C2B_SPEC
    //  muc 7 noi MAX_CONCURRENT=40 "TRO" - dieu do chi duoc chung minh cho SIM tren dataset DEV
    //  (doi 40->25 cho printDone giong het tung byte), KHONG chung minh gi cho live. Da khoi phuc
    //  nhanh live. Ba nguong duoi day gio la HANG SO trong code, khong con la tham so cau hinh.)
    // ================================================================================
    /** BASE cua density-burst limiter: so lenh cho phep mo trong cua so LOOKBACK truoc khi phanh. */
    private static final int BURST_BASE = 40;
    /** Suc chiu dung mat do mo lenh (he so cua duong cong luy thua). */
    private static final float DENSITY_SUSTAIN = 10.0f;
    /** Do cong cua ham kiem soat mat do. */
    private static final float DENSITY_ALPHA = 0.6f;
    /** Ti le lenh "nguy hiem" toi da truoc khi cat cau dao lop 2. */
    private static final float CIRCUIT_DANGER_RATIO = 0.7f;
    /** Cua so nhin lai (phut) de dem mat do mo lenh. */
    private static final int CIRCUIT_LOOKBACK_MINUTES = 4;

    /** Object sieu nhe chua chung du lieu cho ca Test va Prod. */
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

    /** Ham VO danh rieng cho MOI TRUONG PRODUCTION (real trade). */
    public static boolean is50PercentOrderLossProd(
            Collection<OrderTargetInfo> runningOrders,
            long currentTime) {

        List<CircuitOrder> recentOrders = new ArrayList<>();
        long lookbackMillis = CIRCUIT_LOOKBACK_MINUTES * 60000L;

        if (runningOrders != null) {
            for (OrderTargetInfo o : runningOrders) {
                if (currentTime - o.timeStart <= lookbackMillis) {
                    boolean isProfitable = false;
                    // Lenh Prod khong co calTp(), nham tinh lai dua vao Entry va TP/gia hien tai
                    if (o.priceTP != null && o.priceEntry != null) {
                        isProfitable = (o.side == OrderSide.BUY) ? (o.priceTP > o.priceEntry) : (o.priceEntry > o.priceTP);
                    }
                    recentOrders.add(new CircuitOrder(o.timeStart, o.status, o.priceSL != null, isProfitable));
                }
            }
        }

        return evaluateCircuitBreakerCore(recentOrders, currentTime);
    }

    /** LOI cua breaker mat do. */
    private static boolean evaluateCircuitBreakerCore(List<CircuitOrder> recentOrders, long currentTime) {
        if (recentOrders.isEmpty()) return false;

        // Sap xep tu moi nhat -> cu nhat theo timeStart
        recentOrders.sort((o1, o2) -> Long.compare(o2.timeStart, o1.timeStart));

        // ---- LOP 1: mat do theo duong cong luy thua (power law) ----
        int baseBurst = BURST_BASE;
        float sustain = DENSITY_SUSTAIN;
        float alpha = DENSITY_ALPHA;

        int orderCount = 1; // tinh luon lenh dang cho duyet

        for (CircuitOrder order : recentOrders) {
            long diffMillis = currentTime - order.timeStart;
            if (diffMillis < 0) continue;

            int diffMins = (int) (diffMillis / 60000L);
            int checkMins = Math.max(1, diffMins);

            int allowedOrders = (int) (baseBurst + sustain * Math.pow(checkMins, alpha));
            orderCount++;

            if (orderCount > allowedOrders) {
                return true; // vuot mat do -> chan
            }
        }

        // ---- LOP 2: cau dao chong bao (danh gia lai ti le lo thuc su) ----
        int totalOrders = recentOrders.size();

        // Vung mien tru: van cho xa mot luong dan nhat dinh luc bao moi toi
        if (totalOrders < (baseBurst / 2.0)) {
            return false;
        }

        int safeOrders = 0;
        for (CircuitOrder info : recentOrders) {
            // Lenh DA DONG: an toan neu chot loi duong
            boolean isDoneAndProfitable = (info.status == OrderTargetStatus.TAKE_PROFIT_DONE)
                    || (info.status == OrderTargetStatus.STOP_MARKET_DONE && info.isProfitable);

            // Lenh DANG CHAY: an toan neu da doi stop-loss duong
            boolean isRunningAndSafe = (info.status != OrderTargetStatus.TAKE_PROFIT_DONE
                    && info.status != OrderTargetStatus.STOP_LOSS_DONE
                    && info.hasPriceSL);

            if (isDoneAndProfitable || isRunningAndSafe) {
                safeOrders++;
            }
        }

        return (totalOrders - safeOrders > BURST_BASE * CIRCUIT_DANGER_RATIO);
    }
}
