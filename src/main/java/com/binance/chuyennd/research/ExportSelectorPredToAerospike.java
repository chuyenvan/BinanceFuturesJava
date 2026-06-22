package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileReader;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * TASK-039c (nạp Aerospike): đẩy funding-selector predict SET vào Aerospike 226, SET MỚI
 * {@code funding_selector_pred_v1}. Đọc 66 file {@code predict_YYYYMM.bin} (record 26B big-endian
 * {@code >q h 4f} = ts:long, symId:short, p4h,p12h,p24h,p72h:float) → gom theo symbol → ghi 4 bin
 * (p4h/p12h/p24h/p72h) qua {@link DataManagerAerospikeFloatSim#writeMetricMap226} (key SYMBOL_yyyyMM,
 * Snappy Map&lt;ts,float&gt;, merge-guard sẵn có).
 *
 * <p>Gom PER-FILE (1 tháng) để RAM nhỏ. NaN (OI thiếu) bị bỏ qua. symId→symbol từ symbol_map.csv.
 * Reader backtest đọc set mới là việc tích hợp RIÊNG — tool này chỉ NẠP.
 *
 * <p>Chạy TRÊN 226 (file predict ở đó, writeMetricMap226 ghi client 226):
 * {@code java -cp jar com.binance.chuyennd.research.ExportSelectorPredToAerospike [predDir] [mapCsv] [smoke]}
 */
public class ExportSelectorPredToAerospike {

    static final Logger LOG = LoggerFactory.getLogger(ExportSelectorPredToAerospike.class);
    static final String SET = "funding_selector_pred_v1";
    static final String[] BINS = {"p4h", "p12h", "p24h", "p72h"};
    static final int REC = 26;

    public static void main(String[] args) throws Exception {
        String predDir = args.length > 0 ? args[0] : "/home/chuyennd/java/simulator/predict";
        String mapCsv = args.length > 1 ? args[1] : predDir + "/symbol_map.csv";
        boolean smoke = args.length > 2 && args[2].equalsIgnoreCase("smoke");

        Map<Integer, String> id2sym = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(mapCsv))) {
            String line;
            boolean first = true;
            while ((line = br.readLine()) != null) {
                if (first) {
                    first = false;
                    if (line.startsWith("symId")) continue;
                }
                String[] p = line.split(",");
                if (p.length >= 2) id2sym.put(Integer.parseInt(p[0].trim()), p[1].trim());
            }
        }
        LOG.info("Loaded map: {} symId", id2sym.size());

        File[] files = new File(predDir).listFiles((d, n) -> n.startsWith("predict_") && n.endsWith(".bin"));
        if (files == null || files.length == 0) {
            LOG.error("Khong thay predict_*.bin trong {}", predDir);
            return;
        }
        Arrays.sort(files);
        if (smoke) files = new File[]{files[0]};
        LOG.info("Se nap {} file -> set {}", files.length, SET);

        long totalRec = 0;
        int totalErr = 0;
        for (File f : files) {
            byte[] buf = Files.readAllBytes(f.toPath());
            if (buf.length % REC != 0) {
                LOG.error("{}: size {} khong chia het {}", f.getName(), buf.length, REC);
                continue;
            }
            Map<String, TreeMap<Long, Float>[]> bySym = new HashMap<>();
            ByteBuffer bb = ByteBuffer.wrap(buf); // BIG_ENDIAN mac dinh - khop numpy '>'
            int n = buf.length / REC;
            long nrec = 0, nskip = 0;
            for (int i = 0; i < n; i++) {
                long ts = bb.getLong();
                short sid = bb.getShort();
                float[] ps = {bb.getFloat(), bb.getFloat(), bb.getFloat(), bb.getFloat()};
                String sym = id2sym.get((int) sid);
                if (sym == null) {
                    nskip++;
                    continue;
                }
                TreeMap<Long, Float>[] arr = bySym.get(sym);
                if (arr == null) {
                    @SuppressWarnings("unchecked")
                    TreeMap<Long, Float>[] a = new TreeMap[]{new TreeMap<>(), new TreeMap<>(), new TreeMap<>(), new TreeMap<>()};
                    arr = a;
                    bySym.put(sym, arr);
                }
                for (int h = 0; h < 4; h++) if (!Float.isNaN(ps[h])) arr[h].put(ts, ps[h]);
                nrec++;
            }
            int err = 0, syms = 0;
            for (Map.Entry<String, TreeMap<Long, Float>[]> e : bySym.entrySet()) {
                for (int h = 0; h < 4; h++)
                    if (!e.getValue()[h].isEmpty())
                        err += DataManagerAerospikeFloatSim.writeMetricMap226(SET, BINS[h], e.getKey(), e.getValue()[h]);
                syms++;
            }
            totalRec += nrec;
            totalErr += err;
            LOG.info("{}: {} rec | {} symbol ghi | {} skip(no-map) | {} chunk-loi",
                    f.getName(), nrec, syms, nskip, err);
            if (smoke) {
                LOG.info("SMOKE 1 file xong - kiem Aerospike roi chay full");
                break;
            }
        }
        LOG.info("DONE nap -> set {} | tong {} rec | {} chunk-loi", SET, totalRec, totalErr);
    }
}
