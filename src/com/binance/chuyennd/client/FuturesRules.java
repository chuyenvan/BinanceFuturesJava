/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.client;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;

import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * @author pc
 */
public class FuturesRules {

    public static final Logger LOG = LoggerFactory.getLogger(FuturesRules.class);
    private static volatile FuturesRules INSTANCE = null;

    public static FuturesRules getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new FuturesRules();
            INSTANCE.startThreadUpdateLocked();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws InterruptedException {

//        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
//        Thread.sleep(5000);
//        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
//        Thread.sleep(5000);
//        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
//        Thread.sleep(5000);
//        LOG.info("Lock list: {}", FuturesRules.getInstance().getSymsLocked());
        FuturesRules.getInstance().updateListLocked();
        System.out.println(FuturesRules.getInstance().getSymsLocked());
    }

    public FuturesRules() {
    }

    private void startThreadUpdateLocked() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateLocked");
            LOG.info("Start thread ThreadUpdateLocked!");
            while (true) {
                try {
                    Thread.sleep(15 * Utils.TIME_HOUR);
                    updateListLocked();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadRemoveTL: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public Set<String> getSymsLocked() {
        return RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_SYMBOL_TIME_LOCK);
    }

    private void updateListLocked() {
        try {
            Set<String> listLocked = BinanceFuturesClientSingleton.getInstance().getAllSymbolLock();
            RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_BINANCE_SYMBOL_TIME_LOCK);
            if (!listLocked.isEmpty()) {
                LOG.info("Update list lock to redis: {}", Utils.toJson(listLocked));
                for (String symbol : listLocked) {
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_SYMBOL_TIME_LOCK, symbol, symbol);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
