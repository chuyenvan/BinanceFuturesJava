package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.entry.RunGeneratePredictions;
import com.binance.chuyennd.ai_ml.onnx.funding.GenerateFundingPredictionsTool;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class DataUpdaterManager {
    private static final Logger LOG = LoggerFactory.getLogger(DataUpdaterManager.class);

    public static void main(String[] args) {
        // Có thể gọi trực tiếp class này để force update theo time mong muốn
        Long targetTime = null;
        if (args.length > 0) {
            try {
                targetTime = Utils.sdfFile.parse(args[0]).getTime();
            } catch (Exception e) {
                LOG.error("❌ Lỗi format thời gian đầu vào (Expected yyyyMMdd).", e);
            }
        }

        new DataUpdaterManager().checkAndUpdateData(targetTime);
    }

    /**
     * Hàm kiểm tra và update dữ liệu.
     *
     * @param forceStartTime Nếu truyền vào, sẽ force update từ thời điểm này.
     *                       Nếu truyền null, sẽ tự dò lastMarketDataTime từ DB.
     */
    public void checkAndUpdateData(Long forceStartTime) {
        LOG.info("======================================================");
        LOG.info("🔄 BẮT ĐẦU TIẾN TRÌNH CẬP NHẬT DỮ LIỆU ĐỒNG BỘ...");
        LOG.info("======================================================");

        Long timeToRun = forceStartTime;

        if (timeToRun == null) {
            LOG.info("🔍 Đang kiểm tra Metadata của Market Data để làm mốc chuẩn...");
            long lastMarketDataTime = DataManagerAerospikeFloatSim.getLastTimestampFromSet(DataManagerAerospikeFloatSim.AEROSPIKE_SET_NAME_MARKET_DATA);

            if (lastMarketDataTime == 0L || lastMarketDataTime < System.currentTimeMillis() - Utils.TIME_DAY) {
                String lastTimeStr = (lastMarketDataTime == 0L) ? "NULL" : Utils.normalizeDateYYYYMMDDHHmm(lastMarketDataTime);
                LOG.info("⚠️ Dữ liệu cần cập nhật (Last: {}). Bắt đầu chạy bù cả 3 loại dữ liệu...", lastTimeStr);
                timeToRun = (lastMarketDataTime == 0L) ? null : lastMarketDataTime;
            } else {
                LOG.info("✅ Dữ liệu đã up-to-date (Last: {}). Bỏ qua tiến trình update.", Utils.normalizeDateYYYYMMDDHHmm(lastMarketDataTime));
                return; // Thoát nếu không cần update
            }
        } else {
            LOG.info("⚠️ Force Update được kích hoạt từ mốc: {}", Utils.normalizeDateYYYYMMDDHHmm(timeToRun));
        }

        try {
            // 1.1 Chạy bù Market Data
            LOG.info("▶️ 1/3: Kích hoạt ExportMarketData2File...");
            new ExportMarketData2Aerospike().exportMarketEntries(timeToRun);

            // 1.2 Chạy bù AI Prediction (Entry)
            LOG.info("▶️ 2/3: Kích hoạt RunGeneratePredictions...");
            new RunGeneratePredictions().generateAndSave(timeToRun);

            // 1.3 Chạy bù Funding Prediction
            LOG.info("▶️ 3/3: Kích hoạt GenerateFundingPredictionsTool...");
            new GenerateFundingPredictionsTool().startGeneration(timeToRun, System.currentTimeMillis());

            LOG.info("🎉 HOÀN TẤT QUÁ TRÌNH CẬP NHẬT DỮ LIỆU!");

        } catch (Exception e) {
            LOG.error("❌ Lỗi nghiêm trọng trong quá trình cập nhật dữ liệu: " + e.getMessage(), e);
            throw new RuntimeException("Cập nhật dữ liệu thất bại", e);
        }
    }
}