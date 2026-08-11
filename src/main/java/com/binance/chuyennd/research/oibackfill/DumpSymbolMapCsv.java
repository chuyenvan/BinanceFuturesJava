package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedWriter;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * TASK-251 — Xuất TOÀN BỘ {@code symbol_mapper} (Aerospike 226) ra {@code symbol_map.csv} định dạng
 * {@code symId,symbol} (header + 1 dòng/symbol, sort theo symId tăng dần) — ĐÚNG format mà
 * {@code ml/training/gen_funding_wf_predictions.py} kỳ vọng (đọc qua {@code MAP_CSV} rồi
 * {@code merge(m, on="symId")} + {@code dropna(subset=["symbol"])}).
 *
 * <p><b>Vì sao cần tool này (không tái dùng {@code /home/ubuntu/selector_pred_out/symbol_map.csv}
 * cũ, 781 symbol, Jul 8):</b> {@code symbol_mapper} hiện tại đã lớn hơn (863 entry, đo 2026-08-05).
 * Merge trong {@code gen_funding_wf_predictions.py} là LEFT-JOIN theo {@code symId} rồi
 * {@code dropna(subset=["symbol"])} — nếu {@code symbol_map.csv} THIẾU symId nào đang xuất hiện
 * trong Tool1 (`ff_*.bin`) hoặc OI (`oi_percoin_full.bin`), TOÀN BỘ dòng feature của đúng symId đó
 * sẽ bị DROP âm thầm (không log lỗi rõ ràng) — tương đương mất trắng coin đó khỏi dataset train.
 * File cũ (781 symbol) THIẾU ~81 symId mới (coin niêm yết sau Jul 8) → phải regenerate từ
 * {@code symbol_mapper} HIỆN TẠI để đảm bảo phủ đủ 100% symId, không chỉ USDT-pattern (dump TOÀN
 * BỘ map, kể cả 1 entry không khớp {@code ^[A-Z0-9]+USDT$} nếu có — thừa thì vô hại, thiếu mới hại).
 *
 * <p>Đọc-only, KHÔNG ghi gì vào Aerospike. Args: {@code [outPath mac dinh /tmp/symbol_map.csv]}
 */
public class DumpSymbolMapCsv {
    private static final Logger LOG = LoggerFactory.getLogger(DumpSymbolMapCsv.class);

    public static void main(String[] args) {
        String out = args.length > 0 ? args[0] : "/tmp/symbol_map.csv";
        try {
            Map<String, Short> map = DataManagerAerospikeFloatSim.loadSymbolMapper();
            List<Map.Entry<String, Short>> entries = new ArrayList<>(map.entrySet());
            entries.sort((a, b) -> Short.compare(a.getValue(), b.getValue()));
            try (BufferedWriter w = new BufferedWriter(new FileWriter(out))) {
                w.write("symId,symbol");
                w.newLine();
                for (Map.Entry<String, Short> e : entries) {
                    w.write(e.getValue() + "," + e.getKey().trim().toUpperCase());
                    w.newLine();
                }
            }
            LOG.info("✅ Ghi {} symbol (TOÀN BỘ symbol_mapper) -> {} | symId range [{}..{}]",
                    entries.size(), out,
                    entries.isEmpty() ? "-" : entries.get(0).getValue(),
                    entries.isEmpty() ? "-" : entries.get(entries.size() - 1).getValue());
            System.exit(0);
        } catch (Throwable e) {
            LOG.error("❌ DumpSymbolMapCsv FAIL", e);
            System.exit(1);
        }
    }
}
