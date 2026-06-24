package com.binance.chuyennd.ai_ml.onnx.funding;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.io.FileWriter;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Map;

/**
 * TASK-109 — Export set selector Java (4 cột P(win)) ra CSV để VALIDATE so Python predict_*.bin.
 * Đọc set SEL_SET tại từng phút trong [start,end), giải mã float[4], ghi CSV: ts,symId,p4h,p12h,p24h,p72h.
 * Chạy: java -cp jar SelectorExportSetTool <setName> <startYYYYMMdd> <endYYYYMMdd> <outCsv>
 */
public class SelectorExportSetTool {
    private static final Logger LOG = LoggerFactory.getLogger(SelectorExportSetTool.class);

    public static void main(String[] args) throws Exception {
        Configs.IS_KAGGLE_MODE = true;   // đọc 226
        String setName = args[0];
        long start = Utils.sdfFile.parse(args[1]).getTime() + 7 * Utils.TIME_HOUR;
        long end = Utils.sdfFile.parse(args[2]).getTime() + 7 * Utils.TIME_HOUR;
        String outCsv = args[3];

        SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
        int rows = 0;
        try (FileWriter fw = new FileWriter(outCsv)) {
            fw.write("ts,symId,p4h,p12h,p24h,p72h\n");
            for (long t = start; t < end; t += Utils.TIME_MINUTE) {
                String keyStr = fmt.format(new Date(t));
                Key key = new Key(Configs.AEROSPIKE_NAMESPACE, setName, keyStr);
                Record rec = DataManagerAerospikeFloatSim.getClient226().get(null, key);
                if (rec == null) continue;
                byte[] compressed = (byte[]) rec.getValue("data");
                if (compressed == null) continue;
                byte[] raw = Snappy.uncompress(compressed);
                Map<Short, float[]> map = DataManagerAerospikeFloatSim.decodeFundingMapFromBinary(raw);
                for (Map.Entry<Short, float[]> e : map.entrySet()) {
                    float[] p = e.getValue();
                    if (p.length < 4) continue;
                    fw.write(t + "," + e.getKey() + "," + p[0] + "," + p[1] + "," + p[2] + "," + p[3] + "\n");
                    rows++;
                }
            }
        }
        LOG.info("✅ Export {} rows từ set {} [{}->{}] -> {}", rows, setName, args[1], args[2], outCsv);
        System.exit(0);
    }
}
