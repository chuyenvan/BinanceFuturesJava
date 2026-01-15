package com.binance.chuyennd.ai_ml.onnx;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Stream;

public class FixedSymbolMapper {
    private static final Logger LOG = LoggerFactory.getLogger(FixedSymbolMapper.class);

    // File lưu trữ mapping cố định: symbol,id
    private static final String MAPPING_FILE = "storage/symbol_mapping.csv";

    private static final Map<String, Short> strToId = new ConcurrentHashMap<>();
    private static final Map<Short, String> idToStr = new ConcurrentHashMap<>();
    private static final AtomicInteger maxId = new AtomicInteger(0);

    static {
        loadMapping();
    }

    private static void loadMapping() {
        File file = new File(MAPPING_FILE);
        if (!file.exists()) {
            try {
                // Tạo thư mục cha nếu chưa có
                if (file.getParentFile() != null) file.getParentFile().mkdirs();
                file.createNewFile();
            } catch (IOException e) {
                LOG.error("Could not create mapping file", e);
            }
            return;
        }

        try (Stream<String> lines = Files.lines(Paths.get(MAPPING_FILE))) {
            lines.forEach(line -> {
                String[] parts = line.split(",");
                if (parts.length == 2) {
                    String sym = parts[0].trim();
                    short id = Short.parseShort(parts[1].trim());
                    strToId.put(sym, id);
                    idToStr.put(id, sym);
                    if (id > maxId.get()) {
                        maxId.set(id);
                    }
                }
            });
            LOG.info("Loaded {} symbols from mapping file.", strToId.size());
        } catch (IOException e) {
            LOG.error("Error loading symbol mapping", e);
        }
    }

    /**
     * Lấy ID cố định. Nếu chưa có thì tạo mới và ghi xuống file ngay lập tức.
     */
    public static synchronized short getId(String symbol) {
        if (strToId.containsKey(symbol)) {
            return strToId.get(symbol);
        }

        int nextVal = maxId.incrementAndGet();
        if (nextVal > Short.MAX_VALUE) {
            throw new RuntimeException("Symbol overflow! More than " + Short.MAX_VALUE + " symbols.");
        }

        short newId = (short) nextVal;
        strToId.put(symbol, newId);
        idToStr.put(newId, symbol);

        // Ghi xuống file (Append mode)
        appendToFile(symbol, newId);

        return newId;
    }

    public static String getSymbol(short id) {
        return idToStr.getOrDefault(id, "UNKNOWN-" + id);
    }

    private static void appendToFile(String symbol, short id) {
        String line = symbol + "," + id + "\n";
        try {
            Files.write(Paths.get(MAPPING_FILE), line.getBytes(), StandardOpenOption.APPEND);
        } catch (IOException e) {
            LOG.error("Failed to append symbol to mapping file: " + symbol, e);
        }
    }
}