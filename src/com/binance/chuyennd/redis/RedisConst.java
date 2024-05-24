/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.redis;

import com.binance.chuyennd.utils.Configs;
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
    // grid
    public static final String REDIS_KEY_EDUCA_TD_GRID_MANAGER_QUEUE = "redis.key.educa.td.grid.manager.queue";
    public static final String REDIS_KEY_EDUCA_TEST = "redis.key.educa.test.queue";
    
    public static final String REDIS_KEY_EDUCA_SYMBOL_TIME_LOCK = "redis.key.educa.symbol.time.lock";
    public static final String REDIS_KEY_EDUCA_ALL_SYMBOLS= "redis.key.educa.all.symbols";
    public static final String REDIS_KEY_EDUCA_MOVING_AVERAGE_DETAILS= "redis.key.educa.moving.average.details";
    public static final String REDIS_KEY_EDUCA_ALL_SYMBOLS_CHECKING= "redis.key.educa.all.symbols.trading";
    public static final String REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADINGVIEW_FAIL= "redis.key.educa.all.symbols.tradingview.fail";
    
    public static final String REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING = "redis.key.set.td.pos.running";
    
//    public static final String REDIS_KEY_EDUCA_TD_ORDER_MANAGER = "redis.key.educa.td.order.manager";
//    public static final String REDIS_KEY_EDUCA_TD_ORDER_MANAGER_NEW = "redis.key.educa.td.order.manager.new";
//    public static String REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER = "redis.key.educa.test.td.order.manager.new";
    public static String REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER = Configs.getString("REDIS_KEY_EDUCA_TEST_TD_POS_MANAGER");

    public static final String REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE = "redis.key.educa.td.order.manager.queue";
    
    public static final String REDIS_KEY_BINANCE_ORDER_DCA_QUEUES = "redis.key.binance.order.dca.queues";
    
    public static final String REDIS_KEY_EDUCA_TD_SIGNAL_ORDER_MANAGER = "redis.key.educa.td.signal.order.manager";
    public static final String REDIS_KEY_EDUCA_TD_SIGNAL_ORDER_MANAGER_QUEUE = "redis.key.educa.td.signal.order.manager.queue";
    
    // btc bigchange trading
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_POS_MANAGER= "redis.key.educa.btcbigchangetd.pos.manager";
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_TP_MANAGER = "redis.key.educa.btcbigchangetd.order.tp.manager";
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_SL_MANAGER = "redis.key.educa.btcbigchangetd.order.sl.manager";
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE = "redis.key.educa.btcbigchangetd.symbol4trade";


}
