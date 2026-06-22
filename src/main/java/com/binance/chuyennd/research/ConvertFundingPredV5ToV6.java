package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * Chuyển funding pred set CŨ (per-phút, 2.8M record, ~5.4GB) -> set MỚI theo cấu trúc chunk-tháng
 * (key SYMBOL_yyyyMM, bin Snappy Map&lt;ts,float&gt;, dùng writeMetricMap226) để gọn dung lượng.
 *
 * <p>v5 format: key yyyyMMdd-HHmm (per-phút), bin "data" = Snappy(binary map symbolId-&gt;pred[0]).
 * Đọc toàn bộ bằng getAllFundingPredictionsPrimitiveFromAerospike() -> TreeMap&lt;ts, long[]&gt;
 * (mỗi long = symbolId&lt;&lt;32 | floatBits của pred[0]). Gom theo symbol -> ghi 1 bin "p" vào v6.
 *
 * <p>Args: [outSet=funding_pred_1m_v6] [mapCsv=/home/chuyennd/java/simulator/predict/symbol_map.csv]
 * Chạy TRÊN 226 (đọc+ghi 226). READ v5 / WRITE v6 — KHÔNG đụng v5.
 */
public class ConvertFundingPredV5ToV6 {

    static final Logger LOG = LoggerFactory.getLogger(ConvertFundingPredV5ToV6.class);
    static final String BIN = "p";

    public static void main(String[] args) throws Exception {
        String outSet = args.length > 0 ? args[0] : "funding_pred_1m_v6";
        String mapCsv = args.length > 1 ? args[1] : "/home/chuyennd/java/simulator/predict/symbol_map.csv";

        // symId -> symbol
        Map<Integer, String> id2sym = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(mapCsv))) {
            String line;
            boolean first = true;
            while ((line = br.readLine()) != null) {
                if (first) { first = false; if (line.startsWith("symId")) continue; }
                String[] p = line.split(",");
                if (p.length >= 2) id2sym.put(Integer.parseInt(p[0].trim()), p[1].trim());
            }
        }
        LOG.info("Loaded map: {} symId", id2sym.size());

        // đọc TOÀN BỘ v5 (scanAll)
        TreeMap<Long, long[]> all = DataManagerAerospikeFloatSim.getAllFundingPredictionsPrimitiveFromAerospike();
        LOG.info("v5 doc xong: {} moc-phut", all.size());

        // RAM: giu 'all' (~2.8M moc x long[] ~ 3-4GB voi 11g OK). KHONG gom toan bo bySym cung luc
        // (420M diem x TreeMap boxing ~ 20GB -> OOM). Thay vao do: tap hop symId co mat truoc,
        // roi XU LY TUNG SYMBOL: duyet 'all' lay rieng diem cua symbol do -> ghi -> giai phong.
        java.util.Set<Integer> symIds = new java.util.HashSet<>();
        for (long[] arr : all.values())
            for (long enc : arr) symIds.add((int) (enc >> 32));
        LOG.info("Co {} symId trong v5", symIds.size());

        int err = 0, done = 0;
        long totalPoints = 0, noMap = 0;
        for (int symId : symIds) {
            String sym = id2sym.get(symId);
            if (sym == null) { noMap++; continue; }
            TreeMap<Long, Float> m = new TreeMap<>();
            for (Map.Entry<Long, long[]> e : all.entrySet()) {
                long ts = e.getKey();
                for (long enc : e.getValue()) {
                    if ((int) (enc >> 32) == symId) {
                        m.put(ts, Float.intBitsToFloat((int) (enc & 0xFFFFFFFFL)));
                        break; // moi moc-phut chi 1 entry/symbol
                    }
                }
            }
            if (m.isEmpty()) continue;
            totalPoints += m.size();
            err += DataManagerAerospikeFloatSim.writeMetricMap226(outSet, BIN, sym, m);
            if (++done % 25 == 0) LOG.info("  ghi {}/{} symbol | {} diem cong don...", done, symIds.size(), totalPoints);
        }
        LOG.info("DONE convert v5 -> {} | {} symbol | {} diem | {} symId-khong-map | {} chunk-loi",
                outSet, done, totalPoints, noMap, err);
    }
}
