package com.binance.chuyennd.ai_ml.features.export.gate;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;

/**
 * TASK-251 — Đo coverage THẬT của set gate {@code ai_pred_market_gate_wfo} (tầng 7,
 * `WFO_DATA_PIPELINE_MASTER.md` Cảnh báo #5: "Gate coverage 2023+ CHƯA được đo lại"). Read-only,
 * KHÔNG ghi gì — tái dùng {@link DataManagerAerospikeFloatSim#getAllMarketAiPredictionsFromAerospikeSet}
 * (đúng cơ chế đọc mà {@code WfoDataset}/A1PredCoverageValidator dùng, không tự dựng lại).
 *
 * <p>In: tổng số record, ts min/max, #record theo THÁNG (yyyyMM, GMT+7) — để nhìn thẳng khoảng nào
 * đang RỖNG hoặc thấp bất thường (so median), đúng ý nghĩa check A1 nhưng không cần full
 * PreflightContext/ExpectedRanges (nhẹ hơn, chạy trực tiếp bằng 1 lệnh).
 *
 * <p>Args: {@code [setName mac dinh ai_pred_market_gate_wfo]}
 */
public class DiagnoseGateCoverage {
    private static final Logger LOG = LoggerFactory.getLogger(DiagnoseGateCoverage.class);

    public static void main(String[] args) {
        String setName = args.length > 0 ? args[0] : "ai_pred_market_gate_wfo";
        try {
            LOG.info("🔎 Đo coverage set={} (clientOracle, đọc-only)...", setName);
            TreeMap<Long, AiPredictionData> all = DataManagerAerospikeFloatSim.getAllMarketAiPredictionsFromAerospikeSet(setName);
            if (all.isEmpty()) {
                LOG.warn("⚠️ Set {} RỖNG — 0 record.", setName);
                System.exit(0);
            }
            SimpleDateFormat sdfMin = new SimpleDateFormat("yyyy-MM-dd HH:mm");
            sdfMin.setTimeZone(TimeZone.getTimeZone("GMT+7"));
            SimpleDateFormat monthFmt = new SimpleDateFormat("yyyyMM");
            monthFmt.setTimeZone(TimeZone.getTimeZone("GMT+7"));

            TreeMap<String, Long> byMonth = new TreeMap<>();
            for (Long ts : all.keySet()) {
                byMonth.merge(monthFmt.format(new java.util.Date(ts)), 1L, Long::sum);
            }
            LOG.info("✅ TỔNG record={} | ts min={} | ts max={} | #tháng có data={}",
                    all.size(), sdfMin.format(all.firstKey()), sdfMin.format(all.lastKey()), byMonth.size());
            LOG.info("📅 Chi tiết theo tháng (yyyyMM=count):");
            for (Map.Entry<String, Long> e : byMonth.entrySet()) {
                LOG.info("   {} = {}", e.getKey(), e.getValue());
            }
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ DiagnoseGateCoverage FAIL", e);
            System.exit(1);
        }
    }
}
