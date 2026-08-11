package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.util.Map;
import java.util.TreeSet;

/**
 * TASK-251 — Xuất universe symbol từ {@code symbol_mapper} (Aerospike 226, đã verify khớp 242 trong
 * phiên 2026-08-05, 863 symbol) ra file text 1-symbol-1-dòng, dùng làm {@code symfile=} input cho
 * {@link com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFundingOiPerCoin} (đọc-only,
 * KHÔNG ghi gì vào Aerospike).
 *
 * <p>Args: {@code [outPath mac dinh /tmp/oisyms.txt]}
 */
public class DumpSymbolUniverse {
    private static final Logger LOG = LoggerFactory.getLogger(DumpSymbolUniverse.class);

    public static void main(String[] args) {
        String out = args.length > 0 ? args[0] : "/tmp/oisyms.txt";
        try {
            Map<String, Short> map = DataManagerAerospikeFloatSim.loadSymbolMapper();
            TreeSet<String> symbols = new TreeSet<>();
            for (String s : map.keySet()) {
                String up = s.trim().toUpperCase();
                if (up.matches("^[A-Z0-9]+USDT$")) symbols.add(up);
            }
            try (BufferedWriter w = new BufferedWriter(new FileWriter(out))) {
                for (String s : symbols) {
                    w.write(s);
                    w.newLine();
                }
            }
            LOG.info("✅ Ghi {} symbol (từ symbol_mapper, tổng map size={}) -> {}", symbols.size(), map.size(), out);
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ DumpSymbolUniverse FAIL", e);
            System.exit(1);
        }
    }
}
