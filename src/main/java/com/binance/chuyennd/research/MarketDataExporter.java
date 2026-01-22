package com.binance.chuyennd.research; // Hoặc package phù hợp với project của bạn

import com.binance.chuyennd.object.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectOutputStream;
import java.util.Map;
import java.util.TreeMap;

/**
 * Class mới chuyên trách việc xuất dữ liệu thị trường (Refactored)
 */
public class MarketDataExporter {

    private static final Logger LOG = LoggerFactory.getLogger(MarketDataExporter.class);

    /**
     * Hàm gộp dữ liệu và xuất ra file duy nhất.
     *
     * @param rateChangesMap Map chứa thông tin rateDown, rateUp, rate15m (Time -> MarketRateChange)
     * @param oldDataMap Map chứa thông tin rateBtc, rate2Max cũ (Time -> MarketDataObject cũ)
     * @param btcReversionMap Map chứa trạng thái hồi của BTC (Time -> Double)
     * @param outputFilePath Đường dẫn file output (Configs.FILE_ENTRY_MARKET_LEVEL)
     */
    public void exportMarketEntries(
            TreeMap<Long, MarketRateChange> rateChangesMap,
            TreeMap<Long, MarketDataObject> oldDataMap,
            TreeMap<Long, Double> btcReversionMap,
            String outputFilePath) {

        LOG.info("🔄 Starting merge market data...");
        TreeMap<Long, MarketDataObject> mergedDataMap = new TreeMap<>();

        // 1. Duyệt qua tất cả các mốc thời gian có trong rateChangesMap (làm mốc chính)
        for (Map.Entry<Long, MarketRateChange> entry : rateChangesMap.entrySet()) {
            Long time = entry.getKey();
            MarketRateChange rateChange = entry.getValue();

            // 2. Lấy dữ liệu tương ứng từ các nguồn khác
            MarketDataObject oldObj = oldDataMap.get(time);
            Double btcRev = btcReversionMap.get(time);

            // Xử lý null safety nếu dữ liệu ở map khác không đồng bộ
            Float rateBtc = (oldObj != null) ? oldObj.rateBtc : null;
            TreeMap<Float, Short> rate2Max = (oldObj != null) ? oldObj.rate2Max : null;

            // 3. Tạo đối tượng MarketDataObject mới đã gộp đủ thông tin
            MarketDataObject newObj = new MarketDataObject(
                    rateChange.rateDownAvg,
                    rateChange.rateDown15MAvg,
                    rateChange.rateUpAvg,
                    rateBtc,
                    btcRev,
                    rate2Max
            );

            mergedDataMap.put(time, newObj);
        }

        LOG.info("✅ Merged complete. Total entries: {}", mergedDataMap.size());

        // 4. Ghi ra file (Sử dụng ObjectOutputStream tiêu chuẩn)
        saveToFile(mergedDataMap, outputFilePath);
    }

    private void saveToFile(TreeMap<Long, MarketDataObject> data, String filePath) {
        LOG.info("💾 Saving data to file: {}", filePath);
        try (FileOutputStream fileOut = new FileOutputStream(filePath);
             ObjectOutputStream objectOut = new ObjectOutputStream(fileOut)) {

            objectOut.writeObject(data);
            LOG.info("✅ Export successful!");

        } catch (IOException e) {
            LOG.error("❌ Error saving market data entries: ", e);
        }
    }
}