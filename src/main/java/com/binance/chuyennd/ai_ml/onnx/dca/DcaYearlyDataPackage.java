package com.binance.chuyennd.ai_ml.onnx.dca;

import java.io.Serializable;
import java.util.HashMap;
import java.util.Map;
import java.util.TreeMap;

/**
 * Gói dữ liệu "All-in-One" cho 1 năm.
 * Chứa cả dữ liệu dự báo và bảng mapping để đảm bảo tính nhất quán tuyệt đối.
 */
public class DcaYearlyDataPackage implements Serializable {
    private static final long serialVersionUID = 1L;

    // Bảng Mapping riêng của file này (Ví dụ: "BTC" -> 1, "ETH" -> 2)
    public Map<String, Short> symbolToIdMap;

    // Dữ liệu chính: Time -> (SymbolID -> [Risk, Reward, Pump, Dump])
    public TreeMap<Long, HashMap<Short, float[]>> predictions;

    public DcaYearlyDataPackage(Map<String, Short> symbolToIdMap, TreeMap<Long, HashMap<Short, float[]>> predictions) {
        this.symbolToIdMap = symbolToIdMap;
        this.predictions = predictions;
    }
}