/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.redis;

import org.apache.commons.io.FileUtils;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * @author chuyennd
 */
public class RedisConst {

    // redis config
    public static final String REDIS_CONFIG_FILE = "redis.config";
    public static String REDIS_ADDR;
    public static String REDIS_HOST;
    public static String REDIS_PORT;
    public static String REDIS_TIMEOUT;

    static {
        try {
            File configFile = new File(REDIS_CONFIG_FILE);
            List<String> lines = FileUtils.readLines(configFile);
            Map<String, String> map = new HashMap();
            for (String line : lines) {
                if (line.contains("=")) {
                    map.put(line.split("=")[0].trim(), line.split("=")[1].trim());
                }
            }
            REDIS_ADDR = map.get("Redis.Address");
            REDIS_HOST = map.get("Redis.Host");
            REDIS_PORT = map.get("Redis.Port");
            REDIS_TIMEOUT = map.get("Redis.Timeout");
        } catch (Exception e) {
            System.out.println("Do not read redis config file: " + REDIS_CONFIG_FILE);
            System.exit(0);
            e.printStackTrace();
        }

    }
    public static final String REDIS_KEY_EDUCA_TD_POS_MANAGER = "redis.key.educa.td.pos.manager";
    public static final String REDIS_KEY_EDUCA_TD_SYMBOL_TREND = "redis.key.educa.td.symbol.trend";
    public static final String REDIS_KEY_EDUCA_TD_POS_MANAGER_QUEUE = "redis.key.educa.td.pos.manager.queue";
}
