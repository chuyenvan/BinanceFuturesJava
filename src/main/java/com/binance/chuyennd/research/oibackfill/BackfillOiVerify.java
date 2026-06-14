package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.Map;
import java.util.TimeZone;
import java.util.TreeMap;

/**
 * TASK-013 — VERIFY cho TEST NHỎ ở GATE: đọc lại 226 5 set của vài symbol, đưa SỐ vào report:
 * <ul>
 *   <li>#record mỗi set + ts-range (đầu/cuối) + 3 mẫu giá trị.</li>
 *   <li>DEDUP/GRID: mọi ts có chia hết 5m không (chuẩn-mốc đúng, không còn create_time trùng/lệch).</li>
 *   <li>RECOMPUTE OI vs API openInterestHist (B1 đã 0% — đưa lại số): max diff % tại các ts trùng.</li>
 * </ul>
 * Đọc-only. Mặc định symbol BTCUSDT,LUNAUSDT (1 sống + 1 delist). {@code System.exit(0)} cuối main.
 */
public class BackfillOiVerify {

    private static final Logger LOG = LoggerFactory.getLogger(BackfillOiVerify.class);
    private static final String OI_HIST = "https://fapi.binance.com/futures/data/openInterestHist";

    public static void main(String[] args) {
        Configs.IS_KAGGLE_MODE = true;
        String[] symbols = (args != null && args.length > 0)
                ? String.join(",", args).split("[,\\s]+")
                : new String[]{"BTCUSDT", "LUNAUSDT"};
        try {
            for (String symbol : symbols) {
                if (symbol.trim().isEmpty()) continue;
                verifyOne(symbol.trim().toUpperCase());
            }
        } catch (Exception e) {
            LOG.error("❌ Verify lỗi: ", e);
            System.exit(1);
        }
        System.exit(0);
    }

    private static void verifyOne(String symbol) {
        LOG.info("======================== VERIFY {} ========================", symbol);
        SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm");
        sdf.setTimeZone(TimeZone.getTimeZone("UTC"));

        TreeMap<Long, Float> oiMap = null;
        for (int i = 0; i < OiMetricSets.ALL.length; i++) {
            OiMetricSets.Metric m = OiMetricSets.ALL[i];
            TreeMap<Long, Float> map = DataManagerAerospikeFloatSim.getMetricMap226(m.set, m.bin, symbol);
            if (m == OiMetricSets.OI) oiMap = map;

            if (map.isEmpty()) {
                LOG.warn("   set={} : RỖNG", m.set);
                continue;
            }
            // grid check
            int offGrid = 0;
            for (Long ts : map.keySet()) if (ts % OiMetricSets.STEP_MS != 0) offGrid++;

            StringBuilder samples = new StringBuilder();
            int c = 0;
            for (Map.Entry<Long, Float> e : map.entrySet()) {
                if (c++ >= 3) break;
                samples.append(String.format("[%s=%.4f] ", sdf.format(e.getKey()), e.getValue()));
            }
            LOG.info("   set={} | #rec={} | range[{} .. {}] | offGrid5m={} | mẫu: {}",
                    m.set, map.size(), sdf.format(map.firstKey()), sdf.format(map.lastKey()), offGrid, samples);
        }

        // RECOMPUTE OI vs API (chỉ symbol còn sống mới có API; delist sẽ rỗng → bỏ qua có log).
        recomputeOiVsApi(symbol, oiMap);
    }

    private static void recomputeOiVsApi(String symbol, TreeMap<Long, Float> oiMap) {
        if (oiMap == null || oiMap.isEmpty()) {
            LOG.warn("   RECOMPUTE: open_interest 226 RỖNG → bỏ qua.");
            return;
        }
        try {
            String url = OI_HIST + "?symbol=" + symbol + "&period=5m&limit=30";
            byte[] b = VisionMetricsClient.httpBytes(url);
            if (b == null) {
                LOG.warn("   RECOMPUTE: API trả 404 cho {} (delist?) → bỏ qua.", symbol);
                return;
            }
            JSONArray arr = new JSONArray(new String(b, "UTF-8"));
            int matched = 0;
            double maxDiffPct = 0;
            for (int i = 0; i < arr.length(); i++) {
                JSONObject o = arr.getJSONObject(i);
                long ts = OiMetricSets.normalize5m(o.getLong("timestamp"));
                double apiVal = o.getDouble("sumOpenInterestValue");
                Float stored = oiMap.get(ts);
                if (stored == null) continue;
                matched++;
                double diff = apiVal == 0 ? 0 : Math.abs(stored - apiVal) / apiVal * 100.0;
                if (diff > maxDiffPct) maxDiffPct = diff;
            }
            LOG.info("   RECOMPUTE OI vs API: matched={}/{} mốc | maxDiff={}%",
                    matched, arr.length(), String.format("%.4f", maxDiffPct));
            if (matched == 0) {
                LOG.warn("   ⚠️ Không có mốc trùng (backfill chưa tới hiện tại, hoặc forward chưa chạy) — bình thường với history-only.");
            }
        } catch (Exception e) {
            LOG.warn("   RECOMPUTE lỗi: {}", e.getMessage());
        }
    }
}
