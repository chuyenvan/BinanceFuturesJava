/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.client;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class FuturesRules {

    public static final Logger LOG = LoggerFactory.getLogger(FuturesRules.class);
    private static volatile FuturesRules INSTANCE = null;
//    public static final Long TIME_RULE = 10 * Utils.TIME_MINUTE;

    public static FuturesRules getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new FuturesRules();
            INSTANCE.startThreadRemoveLock();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws InterruptedException {

        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
        Thread.sleep(5000);
        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
        Thread.sleep(5000);
        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
        Thread.sleep(5000);
        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
    }

    public FuturesRules() {
    }

    private void startThreadRemoveLock() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadRemoveTL");
            LOG.info("Start thread ThreadRemoveTL!");
            while (true) {
                try {
                    Thread.sleep(10 * Utils.TIME_SECOND);
                    checkAndUnlockTradingRule();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadRemoveTL: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void checkAndUnlockTradingRule() {

        for (Map.Entry<String, String> entry : RedisHelper.getInstance().get().hgetAll(RedisConst.REDIS_KEY_EDUCA_SYMBOL_TIME_LOCK).entrySet()) {
            String symbol = entry.getKey();
            String timelock = entry.getValue();
            long timeLockLong = Long.parseLong(timelock);
            if (calTimeLock(timeLockLong) < System.currentTimeMillis()) {
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_EDUCA_SYMBOL_TIME_LOCK, symbol);
            }
        }

    }

    public void addLock(String sym, Long time) {
        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_SYMBOL_TIME_LOCK, sym, time.toString());
    }

    public long calTimeLock(long currentTime) {
        return currentTime + (10 - Utils.getCurrentMinute(currentTime) % 10) * Utils.TIME_MINUTE;
    }

    public Set<String> getSymsLocked() {
        return RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_SYMBOL_TIME_LOCK);
    }
}
