/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import java.io.File;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.apache.commons.io.FileUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class MoveSystem {

    public static final Logger LOG = LoggerFactory.getLogger(MoveSystem.class);
    public static final String FILE_STORAGE_ORDER_RUNNING = "storage/databak/orderrunning.data";

    public static void main(String[] args) {
//        moveData2Storage();

        moveData2Redis();
    }

    private static void moveData2Storage() {
        importDataRedis2Storage();
    }

    private static Map<String, OrderTargetInfo> readFromRedis() {
        Map<String, OrderTargetInfo> sym2Order = new HashMap<>();
        for (String symbol : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER)) {
            try {
                OrderTargetInfo orderInfo = Utils.gson.fromJson(RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol),
                        OrderTargetInfo.class);
                sym2Order.put(symbol, orderInfo);
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return sym2Order;
    }

    private static void writeStorage(Map<String, OrderTargetInfo> sym2Order) {
        try {
            List<String> lines = new ArrayList<>();
            for (Map.Entry<String, OrderTargetInfo> entry : sym2Order.entrySet()) {
                OrderTargetInfo orderInfo = entry.getValue();
                lines.add(Utils.toJson(orderInfo));
            }
            FileUtils.writeLines(new File(FILE_STORAGE_ORDER_RUNNING), lines);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void importDataRedis2Storage() {
        Map<String, OrderTargetInfo> sym2Order = readFromRedis();
        writeStorage(sym2Order);
    }

    private static void moveData2Redis() {
        Map<String, OrderTargetInfo> sym2Order = readFromStorage();
        for (Map.Entry<String, OrderTargetInfo> entry : sym2Order.entrySet()) {
            String symbol = entry.getKey();
            OrderTargetInfo orderInfo = entry.getValue();
            if (orderInfo != null) {
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER, symbol, Utils.toJson(orderInfo));
            }
        }
    }

    private static Map<String, OrderTargetInfo> readFromStorage() {
        Map<String, OrderTargetInfo> sym2Order = new HashMap();
        try {
            List<String> lines = FileUtils.readLines(new File(FILE_STORAGE_ORDER_RUNNING));
            for (String line : lines) {
                try {
                    OrderTargetInfo orderInfo = Utils.gson.fromJson(line, OrderTargetInfo.class);
                    if (orderInfo != null) {
                        sym2Order.put(orderInfo.symbol, orderInfo);
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }

        } catch (Exception e) {
            e.printStackTrace();
        }
        return sym2Order;
    }
}
