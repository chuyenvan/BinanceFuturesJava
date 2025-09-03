package com.binance.chuyennd.grid;


import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Storage;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Class Singleton: Tự động khởi tạo và quản lý "Chế độ Thị trường".
 * Sửa đổi để tự động nạp dữ liệu lịch sử BTC trong lần gọi getInstance() đầu tiên.
 */
public class MarketRegimeManager {
    public static final Logger LOG = LoggerFactory.getLogger(MarketRegimeManager.class);
    private static volatile MarketRegimeManager instance;
    public final TreeMap<Long, TechnicalAnalysisUtils.MarketRegime> time2Regime = new TreeMap<>();
    private static final long FOUR_HOURS_MS = 4 * 60 * 60 * 1000L;
    private boolean isInitialized = false;

    private MarketRegimeManager() {
        // Private constructor
    }

    // === PHƯƠNG THỨC GET INSTANCE ĐÃ ĐƯỢC CẬP NHẬT ===
    public static MarketRegimeManager getInstance() {
        if (instance == null) {
            synchronized (MarketRegimeManager.class) {
                if (instance == null) {
                    instance = new MarketRegimeManager();
                    instance.init(); // Tự động gọi init()
                }
            }
        }
        return instance;
    }

    // === PHƯƠNG THỨC INIT MỚI, TỰ ĐỘNG NẠP DỮ LIỆU ===
    private void init() {
        if (isInitialized) {
            return;
        }
        LOG.info("Bắt đầu khởi tạo và tính toán MarketRegimeManager từ file...");

        // Lấy dữ liệu lịch sử 1 phút của BTC từ file storage
        // **LƯU Ý:** Bạn cần đảm bảo Configs.FOLDER_TICKER_1M_FILE đã đúng
        String btcDataPath = Configs.FOLDER_TICKER_1M_FILE + "BTCUSDT.data";
        TreeMap<Long, KlineObjectSimple> btcHistoricalData = (TreeMap<Long, KlineObjectSimple>) Storage.readObjectFromFile(btcDataPath);

        if (btcHistoricalData == null || btcHistoricalData.isEmpty()) {
            LOG.info("Không tìm thấy hoặc không đọc được file dữ liệu BTC tại: " + btcDataPath);
            return;
        }

        // Gọi hàm xử lý dữ liệu (logic không đổi)
        processData(btcHistoricalData);

        this.isInitialized = true;
        LOG.info("Khởi tạo MarketRegimeManager thành công. Có " + time2Regime.size() + " điểm dữ liệu.");
    }

    // === HÀM XỬ LÝ DỮ LIỆU (TÁCH RA TỪ INIT CŨ) ===
    private void processData(TreeMap<Long, KlineObjectSimple> btcHistoricalData) {
        List<KlineObjectSimple> btc1mTickers = new ArrayList<>(btcHistoricalData.values());
        List<KlineObjectSimple> btc4hTickers = new ArrayList<>();

        // 1. Xây dựng lại dữ liệu nến 4 giờ
        for (KlineObjectSimple btc1mTicker : btc1mTickers) {
            if ((btc1mTicker.startTime.longValue() + 60000) % FOUR_HOURS_MS == 0) {
                btc4hTickers.add(btc1mTicker);
            }
        }

        if (btc4hTickers.size() < 200) { // Cần ít nhất 200 nến 4h
            LOG.info("Không đủ dữ liệu BTC để tính toán SMA 200 trên biểu đồ 4 giờ.");
            return;
        }

        // 2. Tính toán SMA và xác định Chế độ
        final int SMA50_PERIOD = 50;
        final int SMA200_PERIOD = 200;

        for (int i = SMA200_PERIOD; i < btc4hTickers.size(); i++) {
            List<KlineObjectSimple> sublist = btc4hTickers.subList(0, i + 1);
            double currentPrice = sublist.get(sublist.size() - 1).priceClose;

            double sma50 = TechnicalAnalysisUtils.calculateSMA(sublist, SMA50_PERIOD);
            double sma200 = TechnicalAnalysisUtils.calculateSMA(sublist, SMA200_PERIOD);

            TechnicalAnalysisUtils.MarketRegime regime = TechnicalAnalysisUtils.MarketRegime.NEUTRAL;
            if (sma50 > 0 && sma200 > 0) {
                if (currentPrice > sma50 && sma50 > sma200) {
                    regime = TechnicalAnalysisUtils.MarketRegime.BULLISH;
                } else if (currentPrice < sma50 && sma50 < sma200) {
                    regime = TechnicalAnalysisUtils.MarketRegime.BEARISH;
                }
            }
            time2Regime.put(btc4hTickers.get(i).startTime.longValue(), regime);
        }
    }

    /**
     * Lấy Chế độ Thị trường tại một thời điểm cụ thể.
     */
    public TechnicalAnalysisUtils.MarketRegime getRegimeByTime(long currentTimeMillis) {
        if (!isInitialized || time2Regime.isEmpty()) {
            return TechnicalAnalysisUtils.MarketRegime.NEUTRAL;
        }
        Map.Entry<Long, TechnicalAnalysisUtils.MarketRegime> entry = time2Regime.floorEntry(Utils.get4Hour(currentTimeMillis));
        return (entry != null) ? entry.getValue() : TechnicalAnalysisUtils.MarketRegime.NEUTRAL;
    }
}