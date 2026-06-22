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
 * TASK-039c (nạp Aerospike, biến thể PER-PHÚT): đẩy funding-selector predict MỖI PHÚT của tập đã
 * filter vào set {@code funding_selector_pred_1m} theo cấu trúc CHUNK-NGÀY (key SYMBOL_yyyyMMdd).
 *
 * <p>KHÁC {@link ExportSelectorPredToAerospike} (set 15m, chunk-tháng): per-phút dày ~15x →
 * chunk-tháng vỡ "Record too big" → BẮT BUỘC chunk-NGÀY ({@code writeMetricMapDay226}). Xem
 * docs/DATA_CHUNKING_STANDARD.md.
 *
 * <p>Đọc record 26B big-endian {@code >q h 4f} (ts:long, symId:short, p4h..p72h:float), gom PER-FILE
 * theo symbol → ghi 4 bin (p4h/p12h/p24h/p72h). NaN bỏ qua. Chạy TRÊN 226.
 *
 * <p>{@code java -cp jar ...ExportSelectorPred1mToAerospike [predDir] [mapCsv] [set] [smoke]}
 */
public class ExportSelectorPred1mToAerospike {

    static final Logger LOG = LoggerFactory.getLogger(ExportSelectorPred1mToAerospike.class);
    static final String[] BINS = {"p4h", "p12h", "p24h", "p72h"};
    static final int REC = 26;

    public static void main(String[] args) throws Exception {
        String predDir = args.length > 0 ? args[0] : "/home/chuyennd/java/simulator/predict_1m";
        String mapCsv = args.length > 1 ? args[1] : predDir + "/symbol_map.csv";
        String set = args.length > 2 ? args[2] : "funding_selector_pred_1m";
        boolean smoke = args.length > 3 && args[3].equalsIgnoreCase("smoke");

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
        LOG.info("Loaded map: {} symId | set dich={} (chunk-NGAY)", id2sym.size(), set);

        File[] files = new File(predDir).listFiles((d, n) -> n.startsWith("predict_") && n.endsWith(".bin"));
        if (files == null || files.length == 0) {
            LOG.error("Khong thay predict_*.bin trong {}", predDir);
            return;
        }
        Arrays.sort(files);
        if (smoke) files = new File[]{files[0]};
        LOG.info("Se nap {} file -> set {}", files.length, set);

        long totalRec = 0;
        int totalErr = 0;
        for (File f : files) {
            byte[] buf = Files.readAllBytes(f.toPath());
            if (buf.length % REC != 0) {
                LOG.error("{}: size {} khong chia het {}", f.getName(), buf.length, REC);
                continue;
            }
            Map<String, TreeMap<Long, Float>[]> bySym = new HashMap<>();
            ByteBuffer bb = ByteBuffer.wrap(buf); // BIG_ENDIAN - khop numpy '>'
            int n = buf.length / REC;
            long nrec = 0, nskip = 0;
            for (int i = 0; i < n; i++) {
                long ts = bb.getLong();
                short sid = bb.getShort();
                float[] ps = {bb.getFloat(), bb.getFloat(), bb.getFloat(), bb.getFloat()};
                String sym = id2sym.get((int) sid);
                if (sym == null) { nskip++; continue; }
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
                        err += DataManagerAerospikeFloatSim.writeMetricMapDay226(set, BINS[h], e.getKey(), e.getValue()[h]);
                syms++;
            }
            totalRec += nrec;
            totalErr += err;
            LOG.info("{}: {} rec | {} symbol ghi | {} skip(no-map) | {} chunk-loi",
                    f.getName(), nrec, syms, nskip, err);
            if (smoke) { LOG.info("SMOKE 1 file xong - kiem Aerospike roi chay full"); break; }
        }
        LOG.info("DONE nap -> set {} (chunk-NGAY) | tong {} rec | {} chunk-loi", set, totalRec, totalErr);
    }
}
