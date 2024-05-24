package com.binance.chuyennd.indicators;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.utils.Point;
import com.binance.chuyennd.utils.PolylineSlope;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

public class MACDTradingController {
    public static final Logger LOG = LoggerFactory.getLogger(MACDTradingController.class);

    public static boolean isMacdTrendBuy(List<KlineObjectNumber> tickers, int i) {
        // 4 histogram cuối tăng, đang âm
        // trước ít nhất 5 đỉnh âm giảm dần và 5 đỉnh dương giảm dần
        int periodAm = 5;
        // find cut down
        if (i < 11) {
            return false;
        }
        if (tickers.get(i - 11).histogram == null) {
            return false;
        }

        // 1. n histogram cuối tăng, đang âm
//        KlineObjectNumber last2Ticker = tickers.get(i - 2);
        KlineObjectNumber lastTicker = tickers.get(i - 1);
        KlineObjectNumber currentTicker = tickers.get(i);
        if (currentTicker.histogram > 0
                || currentTicker.histogram < lastTicker.histogram
//                || lastTicker.histogram < last2Ticker.histogram
        ) {
            return false;
        }
        // 2. n đỉnh giảm dần
        int soluongHistogramLienkeGiamLientiep = 0;
        for (int j = 1; j < periodAm + 1; j++) {
            if (tickers.get(i - j).histogram < tickers.get(i - j - 1).histogram) {
                soluongHistogramLienkeGiamLientiep++;
            } else {
                break;
            }
        }
        if (soluongHistogramLienkeGiamLientiep >= periodAm) {
            return true;
        }

        return false;
    }

    public static boolean isSignalCutMacdFirst(List<KlineObjectNumber> tickers, int i) {
        // trước ít nhất 5 đỉnh âm giảm dần và 5 đỉnh dương giảm dần
//        int period =1;
        // find cut down
        if (i < 20) {
            return false;
        }
        KlineObjectNumber lastTicker = tickers.get(i - 1);
        KlineObjectNumber currentTicker = tickers.get(i);
        // get macd Min
        Double histogramMax = null;
        for (int j = 1; j < 20; j++) {
            KlineObjectNumber ticker = tickers.get(i - j);
            if (ticker.histogram != null) {
                if (histogramMax == null || histogramMax < Math.abs(ticker.histogram)) {
                    histogramMax = Math.abs(ticker.histogram);
                }
            }
        }
//        Double maxPrice = null;
        if (lastTicker.signal != null
                && currentTicker.histogram > -0.08 * histogramMax
                && lastTicker.signal > lastTicker.macd
//                && currentTicker.signal < 0
                && currentTicker.macd < 0
        ) {
//            int counterMacdAm = 0;
//            // tìm điểm macd cắt xuống và đếm số ticker đã cắt > period và signal luôn nhỏ hơn trước đó
//            for (int j = 1; j < 20; j++) {
//                KlineObjectNumber ticker = tickers.get(i - j);
//                if (ticker.signal > 0) {
//                    break;
//                }
////                if (maxPrice == null || maxPrice < ticker.priceClose) {
////                    maxPrice = ticker.priceClose;
////                }
//                if (ticker.signal > ticker.macd) {
//                    counterMacdAm++;
//                } else {
//                    return false;
//                }
//            }
//            if (counterMacdAm >= period
////                    && Utils.rateOf2Double(maxPrice, currentTicker.priceClose) > 0.01
//            ) {
            return true;
//            }
        }

        return false;
    }

    public static boolean isTradingStatus(List<KlineObjectNumber> tickers, int i, Double target, int numberHour) {
        int startCheck = i;
        Double priceTP = tickers.get(i).priceClose * (1 + target);
        for (int j = startCheck + 1; j < tickers.size(); j++) {
            if ((tickers.get(j).startTime.longValue() - tickers.get(i).startTime.longValue())
                    > numberHour * Utils.TIME_HOUR) {
                break;
            }
            if (j < tickers.size()) {
                KlineObjectNumber ticker = tickers.get(j);
                if (ticker.maxPrice > priceTP && ticker.minPrice < priceTP) {
                    return true;
                }
            }
        }
        return false;
    }

    public static boolean isMacdTrendBuyNew(List<KlineObjectNumber> tickers, int i) {
        // 4 histogram cuối tăng, đang âm
        // trước ít nhất 5 đỉnh âm giảm dần và 5 đỉnh dương giảm dần
        int periodAm = 4;
        int periodDuong = 10;
        // find cut down
        if (i < 11) {
            return false;
        }
        if (tickers.get(i - 11).histogram == null) {
            return false;
        }

        // 1. n histogram cuối tăng, đang âm
        KlineObjectNumber lastTicker = tickers.get(i - 1);
        KlineObjectNumber currentTicker = tickers.get(i);
        if (currentTicker.histogram > 0 || currentTicker.histogram < lastTicker.histogram) {
            return false;
        }
        // 2. n đỉnh âm giảm dần
        int soluongHistogramLienkeGiamLientiep = 0;
        for (int j = 1; j < periodAm + 1; j++) {
            if (tickers.get(i - j).histogram < tickers.get(i - j - 1).histogram
                    && tickers.get(i - j).histogram < 0) {
                soluongHistogramLienkeGiamLientiep++;
            } else {
                break;
            }
        }
        if (soluongHistogramLienkeGiamLientiep < periodAm) {
            return false;
        }
        // 3. check số lượng đỉnh dương trước đó giảm liên tiếp cách đỉnh âm ko quá 15 đỉnh
        Integer indexHistogramDuongDauTien = null;
        for (int j = 0; j < 10; j++) {
            if (tickers.get(i - j).histogram > 0) {
                indexHistogramDuongDauTien = i - j;
                break;
            }
        }
        if (indexHistogramDuongDauTien == null) {
            return false;
        }
        int soluongHistogramDuongGiamLienTiep = 0;
        for (int j = 0; j < periodDuong; j++) {
            if (tickers.get(indexHistogramDuongDauTien - j).histogram > 0) {
                soluongHistogramDuongGiamLienTiep++;
            } else {
                break;
            }
        }
        if (soluongHistogramDuongGiamLienTiep >= periodDuong) {
//            Double histogramMax = null;
//            Double histogramMin = null;
//            for (int j = 0; j < periodDuong + periodAm; j++) {
//                if (histogramMax == null || tickers.get(i - j).histogram > histogramMax) {
//                    histogramMax = tickers.get(i - j).histogram;
//                }
//                if (histogramMin == null || tickers.get(i - j).histogram < histogramMin) {
//                    histogramMin = tickers.get(i - j).histogram;
//                }
//            }
//            LOG.info("check: {} Max: {} Min: {} rate:{}", Utils.normalizeDateYYYYMMDDHHmm(tickers.get(i).startTime.longValue()),
//                    histogramMax, histogramMin, histogramMax / histogramMin);
            return true;
        }
        return false;
    }

    public static Double slopeHistogram(List<KlineObjectNumber> tickers, int start, int end) {
        List<Point> points = new ArrayList<>();
        for (int i = start; i < end; i++) {
            points.add(new Point(tickers.get(start).histogram * (i + 1), tickers.get(i).histogram));
        }
        return PolylineSlope.calculateSlopesAvg(points);
    }

    public static Double rateChangeWithMax(List<KlineObjectNumber> tickers, int start, int end) {
        Double maxPrice = null;
        for (int i = start; i < end; i++) {
            if (maxPrice == null || maxPrice < tickers.get(i).priceClose) {
                maxPrice = tickers.get(i).priceClose;
            }
        }
        return Utils.rateOf2Double(maxPrice, tickers.get(end).priceClose);
    }

    public static boolean isMacdTrendBuyNew1h(List<KlineObjectNumber> tickers, int i) {
        // 4 histogram cuối tăng, đang âm
        // trước ít nhất 5 đỉnh âm giảm dần và 5 đỉnh dương giảm dần
        int periodAm = 3;
        // find cut down
        if (i < 11) {
            return false;
        }
        if (tickers.get(i - 11).histogram == null) {
            return false;
        }
        KlineObjectNumber lastTicker = tickers.get(i - 1);
        KlineObjectNumber currentTicker = tickers.get(i);
        // 0. cả signal và macd phải dương
//        if (currentTicker.signal < 0 || currentTicker.macd < 0){
//            return false;
//        }

        // 1. n histogram cuối tăng, đang âm
//        KlineObjectNumber last2Ticker = tickers.get(i - 2);
        if (currentTicker.histogram > 0
                || currentTicker.histogram < lastTicker.histogram
//                || lastTicker.histogram < last2Ticker.histogram
        ) {
            return false;
        }
        // 2. n đỉnh giảm dần
        int soluongHistogramLienkeGiamLientiep = 0;
        for (int j = 1; j < periodAm + 1; j++) {
            if (tickers.get(i - j).histogram < tickers.get(i - j - 1).histogram) {
                soluongHistogramLienkeGiamLientiep++;
            } else {
                break;
            }
        }
        if (soluongHistogramLienkeGiamLientiep >= periodAm) {
            return true;
        }

        return false;
    }

    public static boolean isMacdTamGiacCan(List<KlineObjectNumber> tickers, int indexCheckPoint) {
        // đỉnh cuối dương -> các đáy thấp hơn đỉnh(đỉnh là histogram đáy)
        // trước ít nhất 5 đỉnh âm giảm dần và periodMin đỉnh dương giảm dần
        // check trong 30 ticker gần nhất
        int period = 30;
        int periodMin = 5;
        // 0. cả signal và macd phải dương
        KlineObjectNumber currentTicker = tickers.get(indexCheckPoint);
        KlineObjectNumber lastTicker = tickers.get(indexCheckPoint - 1);
        if (currentTicker.histogram < 0 || lastTicker.histogram > 0) {
            return false;
        }
//        // 1. tìm đáy
//        int indexHistogramMin = 0;
//        Double histogramMin = null;
//        for (int j = 1; j < period + 1; j++) {
//            if (histogramMin == null || histogramMin > tickers.get(indexCheckPoint - j).histogram){
//                histogramMin = tickers.get(indexCheckPoint - j).histogram;
//                indexHistogramMin = indexCheckPoint - j;
//            }else{
//                break;
//            }
//
//        }
//        if (indexHistogramMin == 0) {
//            return false;
//        }else{
//        // 2. check 2 cạnh đáy ít nhất periodMin đỉnh giảm liên tiếp
//            //  check đáy tới checkpoint
//            if (indexCheckPoint - indexHistogramMin < periodMin){
//                return false;
//            }else{
//                for (int i = indexHistogramMin; i < indexCheckPoint; i++) {
//                    if (tickers.get(i).histogram > tickers.get(i +1).histogram){
//                        return false;
//                    }
//                }
//            }
//            // check cạnh đối diện
//            for (int i = indexHistogramMin - periodMin + 1; i < indexHistogramMin ; i++) {
//                if (tickers.get(i).histogram < tickers.get(i +1).histogram){
//                    return false;
//                }
//            }
//        }
        return true;
    }

    public static boolean isMacdStopTrendBuy(List<KlineObjectNumber> tickers, int i, Long startTime) {
        // histogram down period session || 2 session histogram -
        int periods = 5;
        boolean isSessonDown = true;
        int counterHistogram = 0;
        //
        if (tickers.get(i - periods).startTime.longValue() <= startTime) {
            return false;
        }
        for (int j = 0; j < periods; j++) {
            KlineObjectNumber lastTicker = tickers.get(i - j - 1);
            KlineObjectNumber ticker = tickers.get(i - j);

            if (ticker.histogram < 0) {
                counterHistogram++;
            }
            if (ticker.histogram > lastTicker.histogram) {
                isSessonDown = false;
            }
        }
        if (isSessonDown || counterHistogram > 2) {
            return true;
        }
        return false;
    }

    public static boolean isMacdStopTrendBuyNew(List<KlineObjectNumber> tickers, int i, Long startTime) {
        // histogram down period session || 2 session histogram -
        int periods = 5;
        boolean isSessonDown = true;
        int counterHistogram = 0;
        //
        if (tickers.get(i - periods).startTime.longValue() <= startTime) {
            return false;
        }
        for (int j = 0; j < periods; j++) {
            KlineObjectNumber lastTicker = tickers.get(i - j - 1);
            KlineObjectNumber ticker = tickers.get(i - j);

            if (ticker.histogram < 0) {
                counterHistogram++;
            }
            if (ticker.histogram > lastTicker.histogram) {
                isSessonDown = false;
            }
        }
        if (isSessonDown || counterHistogram > 2) {
            return true;
        }
        return false;
    }

}
