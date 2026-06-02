package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.tradecore.MarketBigChangeDetector;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Sinh {@link MarketDataObject} ON-THE-FLY trong lúc export training data, dùng ĐÚNG
 * {@link MarketBigChangeDetector#calMarketData} như live + ExportMarketData2File (một bộ não),
 * kèm GUARD CHẤT LƯỢNG: trả {@code null} khi dữ liệu phút đó không đáng tin => caller KHÔNG
 * xuất sample phút đó.
 *
 * <p>Lý do gen inline: bỏ phụ thuộc ngầm vào set Aerospike "market_data_object" (có thể thiếu/cũ,
 * tạo lỗ hổng không ngẫu nhiên làm lệch phân phối tập train). Vì dùng cùng {@code calMarketData}
 * nên giá trị khớp cả serve lẫn bản precomputed — không gây train/serve skew.
 *
 * <p>Buffer trượt per-symbol PHẢI được nuôi TUẦN TỰ theo thời gian: gọi {@link #update} đúng
 * MỘT lần cho MỖI phút theo thứ tự thời gian (kể cả phút sẽ bị bỏ), để cửa sổ 15m chính xác.
 */
public class MarketDataInlineGenerator {

    private static final Logger LOG = LoggerFactory.getLogger(MarketDataInlineGenerator.class);

    /** Số nến tính max/min cho rate 15M — khớp ExportMarketData2File & live. */
    private static final int WINDOW = Configs.NUMBER_TICKER_CAL_RATE_CHANGE;
    /** Dưới mức symbol khả dụng này coi như GAP DATA, không tin được trung bình thị trường. */
    public static final int MIN_SYMBOLS = 50;

    private final Map<String, List<KlineObjectSimple>> symbol2LastTickers = new HashMap<>();

    private long emitted = 0, droppedCold = 0, droppedGap = 0, droppedDegenerate = 0;

    /**
     * Nuôi buffer trượt và tính + VALIDATE MarketDataObject cho phút hiện tại.
     *
     * @param snapshot map symbol -> ticker 1M của phút hiện tại
     * @return MarketDataObject hợp lệ; hoặc {@code null} nếu phút này phải bỏ (cửa sổ lạnh,
     *         gap data, thiếu BTC, hoặc giá trị degenerate/NaN/Inf)
     */
    public MarketDataObject update(Map<String, KlineObjectSimple> snapshot) {
        if (snapshot == null || snapshot.isEmpty()) {
            droppedGap++;
            return null;
        }

        Map<String, Float> symbol2MaxPrice = new HashMap<>();
        Map<String, Float> symbol2MinPrice = new HashMap<>();
        int validSymbols = 0;
        int warmSymbols = 0;

        for (Map.Entry<String, KlineObjectSimple> e : snapshot.entrySet()) {
            String symbol = e.getKey();
            if (Constants.diedSymbol.contains(symbol)) continue;
            KlineObjectSimple ticker = e.getValue();
            if (!Utils.isTickerAvailable(ticker)) continue;

            List<KlineObjectSimple> tickers = symbol2LastTickers.computeIfAbsent(symbol, k -> new ArrayList<>());
            tickers.add(ticker);
            if (tickers.size() > 100) {
                for (int i = 0; i < 5; i++) tickers.remove(0);
            }
            validSymbols++;

            Float priceMax = null, priceMin = null;
            for (int i = 0; i < WINDOW; i++) {
                int index = tickers.size() - i - 1;
                if (index >= 0) {
                    KlineObjectSimple kline = tickers.get(index);
                    priceMax = (priceMax == null) ? kline.maxPrice : Math.max(priceMax, kline.maxPrice);
                    priceMin = (priceMin == null) ? kline.minPrice : Math.min(priceMin, kline.minPrice);
                }
            }
            if (tickers.size() >= WINDOW) warmSymbols++;
            symbol2MaxPrice.put(symbol, priceMax);
            symbol2MinPrice.put(symbol, priceMin);
        }

        // GUARD 1: gap data — quá ít symbol khả dụng.
        if (validSymbols < MIN_SYMBOLS) {
            droppedGap++;
            return null;
        }
        // GUARD 2: thiếu BTC (mỏ neo thị trường) => trung bình không đáng tin.
        if (!snapshot.containsKey(Constants.SYMBOL_PAIR_BTC)) {
            droppedGap++;
            return null;
        }
        // GUARD 3: cửa sổ LẠNH — đa số symbol chưa đủ WINDOW nến warm-up (đầu range / sau gap dài).
        if (warmSymbols < MIN_SYMBOLS) {
            droppedCold++;
            return null;
        }

        MarketDataObject md = MarketBigChangeDetector.calMarketData(snapshot, symbol2MaxPrice, symbol2MinPrice);

        // GUARD 4: degenerate / NaN / Inf.
        if (md == null
                || bad(md.rateDownAvg) || bad(md.rateUpAvg) || bad(md.rateDown15MAvg)
                || (md.rateDownAvg == 0f && md.rateUpAvg == 0f && md.rateDown15MAvg == 0f)) {
            droppedDegenerate++;
            return null;
        }

        emitted++;
        return md;
    }

    private static boolean bad(float v) {
        return Float.isNaN(v) || Float.isInfinite(v);
    }

    /** Báo cáo số phút xuất / bị bỏ theo từng lý do (gọi định kỳ để theo dõi coverage). */
    public String report() {
        long dropped = droppedCold + droppedGap + droppedDegenerate;
        return String.format("MarketData gen: emitted=%d, dropped=%d [cold=%d, gap=%d, degenerate=%d]",
                emitted, dropped, droppedCold, droppedGap, droppedDegenerate);
    }
}
