package com.binance.chuyennd.object;

import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class ResistanceAndSupport {
    public static final Logger LOG = LoggerFactory.getLogger(ResistanceAndSupport.class);
    public static Double zone = 0.002;
    public static Double rangePrice2Order = 0.01;
    public List<TrendObject> resistances;
    public KlineObjectNumber currentTicker;
    public KlineObjectNumber lastTicker;
    public List<TrendObject> trends;
    public List<TrendObject> supports;
    public TrendObjectDetail trendDetail;
    public OrderSide sideSuggest;

    public ResistanceAndSupport(List<TrendObject> trends, KlineObjectNumber currentTicker) {
        if (trends != null && trends.size() >= 2) {
            Integer sIndex = 0;
            Integer rIndex = 1;
            if (trends.get(trends.size() - 1).status.equals(TrendState.TOP)) {
                sIndex = 1;
                rIndex = 0;
            }
            int size = trends.size() - 1;
            this.trends = trends;
            this.currentTicker = currentTicker;
            resistances = new ArrayList<>();
            supports = new ArrayList<>();
            for (int i = 0; i < size / 2; i++) {
                resistances.add(trends.get(size - rIndex - 2 * i));
                supports.add(trends.get(size - sIndex - 2 * i));
            }
        }
    }

    public void printData() {
        if (this.supports != null) {
            StringBuilder builder = new StringBuilder();
            for (int i = 0; i < trends.size() / 2 - 1; i++) {
                builder.append("R").append(i + 1).append(" ").append(Utils.normalizeDateYYYYMMDDHHmm(resistances.get(i).kline.startTime.longValue()));
                builder.append(" ").append(resistances.get(i).kline.maxPrice).append("\n");
            }
            for (int i = 0; i < trends.size() / 2 - 1; i++) {
                builder.append("S").append(i + 1).append(" ").append(Utils.normalizeDateYYYYMMDDHHmm(supports.get(i).kline.startTime.longValue()));
                builder.append(" ").append(supports.get(i).kline.minPrice).append("\n");

            }
            System.out.println(builder);
        }
    }

    public void detectTrend(Double ratePeriod) {
        TrendObject r1 = resistances.get(0);
        TrendObject r2 = resistances.get(1);
        TrendObject r3 = resistances.get(2);
        TrendObject r4 = resistances.get(3);
        TrendObject r5 = resistances.get(4);
        TrendObject s1 = supports.get(0);
        TrendObject s2 = supports.get(1);
        TrendObject s3 = supports.get(2);
        TrendObject s4 = supports.get(3);
        TrendObject s5 = supports.get(4);
        TrendObject rMax1 = getMaxByNumber(resistances, 1, 5);
        TrendObject rMax2 = getMaxByNumber(resistances, 2, 5);
        TrendObject sMin1 = getMinByNumber(supports, 1, 5);
        TrendObject sMin2 = getMinByNumber(supports, 2, 5);


        // check theo cặp r cuối cùng
        trendDetail = new TrendObjectDetail(TrendState.SIDEWAY, new ArrayList<>());
        if (trends.size() > 0) {
            for (int i = 0; i < 2; i++) {
                trendDetail.topBottonObjects.add(trends.get(trends.size() - 1 - i));
                trendDetail.updatePriceRange(trends.get(trends.size() - 1 - i));
            }
            if (r1.getMaxPrice() > r2.getMaxPrice()
                    && s1.getMinPrice() > s2.getMinPrice()) {
                trendDetail.status = TrendState.TREND_UP;
            }
//            if (currentTicker.maxPrice >= rMax1.getMaxPrice()
//                    // đỉnh sau lớn hơn đỉnh trươc và giá lớn hơn đỉnh trước
//                    || (rMax1.kline.startTime > rMax2.kline.startTime && currentTicker.priceClose >= rMax2.getMaxPrice())
//                    // đáy sau cao hơn đáy trước và giá lớn hơn đáy sau
////                    || (s1.getMinPrice() > s2.getMinPrice() && currentTicker.priceClose >= s2.getMinPrice())
//            ) {
//                trendDetail.status = TrendState.TREND_UP;
//            } else {
//                if (currentTicker.minPrice <= sMin1.getMinPrice()
//                        // đỉnh sau thấp hơn đỉnh trước và giá thấp hơn đỉnh sau
//                        || (rMax1.kline.startTime < rMax2.kline.startTime && currentTicker.priceClose <= rMax2.getMaxPrice())
//                        // đáy sau thấp hơn đáy trước và giá thấp hơn đáy trước
//                        || (sMin1.kline.startTime > sMin2.kline.startTime && currentTicker.priceClose <= sMin1.getMinPrice())
//                ) {
//                    trendDetail.status = TrendState.TREND_DOWN;
//                }
//            }
            switch (trendDetail.status) {
                case TREND_UP:
                    for (int i = 2; i < trends.size(); i++) {
                        TrendObject trend = trends.get(trends.size() - 1 - i);
                        if (trendDetail.topBottonObjects.get(trendDetail.topBottonObjects.size() - 1).kline.maxPrice > trend.kline.maxPrice) {
                            trendDetail.topBottonObjects.add(trend);
                            trendDetail.updatePriceRange(trend);
                        } else {
                            break;
                        }
                    }
                    break;
                case TREND_DOWN:
                    for (int i = 2; i < trends.size(); i++) {
                        TrendObject trend = trends.get(trends.size() - 1 - i);
                        if (trendDetail.topBottonObjects.get(trendDetail.topBottonObjects.size() - 1).kline.minPrice < trend.kline.minPrice) {
                            trendDetail.topBottonObjects.add(trend);
                            trendDetail.updatePriceRange(trend);
                        } else {
                            break;
                        }
                    }
                    break;
                case SIDEWAY:
                    for (int i = 2; i < trends.size(); i++) {
                        TrendObject trend = trends.get(trends.size() - 1 - i);
                        Double rateChange = Utils.rateOf2Double(trends.get(trends.size() - 1).kline.maxPrice, trend.kline.minPrice);
                        if (trend.status.equals(TrendState.TOP)) {
                            rateChange = Utils.rateOf2Double(trend.kline.maxPrice, trends.get(trends.size() - 1).kline.minPrice);
                        }
                        if (rateChange < ratePeriod &&
                                (trend.kline.maxPrice <= trendDetail.maxPrice * (1 + zone)
                                        || trend.kline.minPrice > trendDetail.minPrice * (1 - zone))) {
                            trendDetail.topBottonObjects.add(trend);
                            trendDetail.updatePriceRange(trend);
                        } else {
                            break;
                        }
                    }
                    break;

            }
            // sideway -> buy ở đáy nếu sw sau khi tăng -> trend đầu sw là top
            // sideway -> sell ở đỉnh nếu sw sau khi giảm -> trend đầu sw là bottom
            // trend_up -> buy dưới đỉnh tính theo giá đóng 2%
            // trend_down -> sel ở đỉnh trên đáy 2%

            switch (trendDetail.status) {
                case TREND_UP:
                    if (
//                            currentTicker.priceClose * (1 + rangePrice2Order) < trendDetail.maxPrice
//                            && r1.kline.maxPrice > r2.kline.maxPrice
//                            && s1.kline.minPrice > s2.kline.minPrice
                            lastTicker != null
                                    && currentTicker.priceClose > s1.getMinPrice()
                                    && currentTicker.totalUsdt / lastTicker.totalUsdt < 2
                                    && Utils.rateOf2Double(currentTicker.priceClose, currentTicker.priceOpen) < -0.01
//                            && (r3.kline.minPrice > r2.kline.minPrice || s3.kline.minPrice > s2.kline.minPrice)
                    ) {
                        sideSuggest = OrderSide.BUY;
                        LOG.info("{} {} entry:{} target:{} s1Min:{}", sideSuggest, Utils.normalizeDateYYYYMMDDHHmm(currentTicker.startTime.longValue()),
                                currentTicker.priceClose, currentTicker.priceClose * 1.007, s1.getMinPrice());
                    }
                    break;
//            case TREND_DOWN:
//                if (currentTicker.priceClose * (1 - rangePrice2Order) > trendDetail.minPrice) {
//                    sideSuggest = OrderSide.SELL;
//                }
//                break;
//                case SIDEWAY:
//                    if (trends.get(trends.size() - 1).status.equals(TrendState.TOP)) {
//                        if (currentTicker.priceClose * (1 + 2 * rangePrice2Order) < trendDetail.maxPrice
//                                && currentTicker.priceClose < trendDetail.minPrice * (1 + rangePrice2Order)
//                                && currentTicker.minPrice >= trendDetail.minPrice
//                                && currentTicker.priceClose > currentTicker.priceOpen) {
//                            sideSuggest = OrderSide.BUY;
//                        }
//                    } else {
//                        if (currentTicker.priceClose * (1 - rangePrice2Order) > trendDetail.minPrice) {
//                            sideSuggest = OrderSide.SELL;
//                        }
//                    }
//                    break;
            }
        }
    }

    public TrendObject getMaxByNumber(List<TrendObject> objects, int maxNumber, int period) {
        TrendObject max1 = null;
        TrendObject max2 = null;
        for (int i = 0; i < period; i++) {
            TrendObject ob = objects.get(i);
            if (max1 == null || max1.kline.maxPrice < ob.kline.maxPrice) {
                max1 = ob;
            }
        }
        for (int i = 0; i < period; i++) {
            TrendObject ob = objects.get(i);
            if (max1 == ob) {
                continue;
            }
            if (max2 == null || max2.kline.maxPrice < ob.kline.maxPrice) {
                max2 = ob;
            }
        }
        if (maxNumber == 1) {
            return max1;
        } else {
            return max2;
        }
    }

    public TrendObject getMinByNumber(List<TrendObject> objects, int maxNumber, int period) {
        TrendObject min1 = null;
        TrendObject min2 = null;
        for (int i = 0; i < period; i++) {
            TrendObject ob = objects.get(i);
            if (min1 == null || min1.kline.minPrice > ob.kline.minPrice) {
                min1 = ob;
            }
        }
        for (int i = 0; i < period; i++) {
            TrendObject ob = objects.get(i);
            if (min1 == ob) {
                continue;
            }
            if (min2 == null || min2.kline.minPrice > ob.kline.minPrice) {
                min2 = ob;
            }
        }
        if (maxNumber == 1) {
            return min1;
        } else {
            return min2;
        }
    }

    public String printTrend() {
        StringBuilder sb = new StringBuilder();
        sb.append(trendDetail.status).append(" min: ").append(trendDetail.minPrice).append(" max: ").append(trendDetail.maxPrice).append("\n");
        for (int i = 0; i < trendDetail.topBottonObjects.size(); i++) {
            TrendObject trend = trendDetail.topBottonObjects.get(i);
            sb.append(trend.status).append(" ");
            sb.append(Utils.normalizeDateYYYYMMDDHHmm(trend.kline.startTime.longValue())).append(" ");
            sb.append(trend.kline.minPrice).append(" -> ").append(trend.kline.maxPrice).append("\n");
        }
        return sb.toString();
    }

    public Double getStopLoss() {
        if (sideSuggest == null) {
            return null;
        }
        if (sideSuggest.equals(OrderSide.SELL)) {
            return resistances.get(0).getKline().maxPrice * 1.01;
        } else {
            return supports.get(0).getKline().minPrice * 0.99;
        }
    }

    public void setLastTicker(KlineObjectNumber lastTicker) {
        this.lastTicker = lastTicker;
    }
}
