/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.redis;

import com.binance.chuyennd.position.manager.PositionHelper;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.trade.Order;
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
    
    public static final String REDIS_KEY_EDUCA_SYMBOL_TIME_LOCK = "redis.key.educa.symbol.time.lock";
    
    public static final String REDIS_KEY_EDUCA_TD_POS_MANAGER = "redis.key.educa.td.pos.manager";
    public static final String REDIS_KEY_EDUCA_TD_POS_MANAGER_VOLUME = "redis.key.educa.td.pos.manager.volume";
    public static final String REDIS_KEY_EDUCA_TD_POS_TIME_MANAGER = "redis.key.educa.td.pos.time.manager";
    public static final String REDIS_KEY_EDUCA_TD_POS_PROFIT_MANAGER = "redis.key.educa.td.pos.profit.manager";
    public static final String REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER = "redis.key.educa.td.order.dca.manager";
    public static final String REDIS_KEY_EDUCA_TD_SYMBOL_TREND = "redis.key.educa.td.symbol.trend";
    public static final String REDIS_KEY_EDUCA_TD_POS_MANAGER_QUEUE = "redis.key.educa.td.pos.manager.queue";
    
    public static final String REDIS_KEY_EDUCA_TD_ORDER_MANAGER = "redis.key.educa.td.order.manager";
    public static final String REDIS_KEY_EDUCA_TD_ORDER_MANAGER_QUEUE = "redis.key.educa.td.order.manager.queue";
    
    public static final String REDIS_KEY_EDUCA_TD_SIGNAL_ORDER_MANAGER = "redis.key.educa.td.signal.order.manager";
    public static final String REDIS_KEY_EDUCA_TD_SIGNAL_ORDER_MANAGER_QUEUE = "redis.key.educa.td.signal.order.manager.queue";
    
    // btc bigchange trading
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_POS_MANAGER= "redis.key.educa.btcbigchangetd.pos.manager";
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_TP_MANAGER = "redis.key.educa.btcbigchangetd.order.tp.manager";
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_ORDER_SL_MANAGER = "redis.key.educa.btcbigchangetd.order.sl.manager";
    public static final String REDIS_KEY_EDUCA_BTCBIGCHANGETD_SYMBOLS4TRADE = "redis.key.educa.btcbigchangetd.symbol4trade";

    public static void main(String[] args) {
        String symbol = "ETHUSDT";
        Order order = new PositionHelper().readOrderInfo(symbol, 8389765629333329753L);
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, symbol, Utils.toJson(order));
        String json = RedisHelper.getInstance().readJsonData(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_DCA_MANAGER, symbol);
        Order orderInfo = Utils.gson.fromJson(json, Order.class);
        System.out.println(orderInfo.getPrice().doubleValue());
    }
}
