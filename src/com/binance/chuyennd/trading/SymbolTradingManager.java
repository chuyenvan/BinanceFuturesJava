/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.statistic24hr.Volume24hrManager;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.util.HashSet;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class SymbolTradingManager {

    public static final Logger LOG = LoggerFactory.getLogger(SymbolTradingManager.class);
    private static volatile SymbolTradingManager INSTANCE = null;
    public static final Integer MAX_VOLUME_TRADING = Configs.getInt("MAX_VOLUME_TRADING");

    public static SymbolTradingManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SymbolTradingManager();
            INSTANCE.startThreadUpdateSymbol2Trading();
        }
        return INSTANCE;
    }

    private void updateSymbolTrading() {
        try {
            Set<String> symbolsVolumeOverVolumeNotTrade = getAllSymbolVolumeOverVolumeNotTrade();
            Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_TD_ORDER_MANAGER);
            Set<String> symbol2Trade = new HashSet<>();
            symbol2Trade.addAll(RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS));
            symbol2Trade.removeAll(Constants.specialSymbol);
            symbol2Trade.removeAll(symbolsVolumeOverVolumeNotTrade);
            symbol2Trade.removeAll(symbolsTrading);
            String currentTime = String.valueOf(System.currentTimeMillis());
            //delet list old
            RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADING);
            //write new
            LOG.info("Update {} symbols to trading list.", symbol2Trade.size());
            for (String symbol : symbol2Trade) {
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADING, symbol, currentTime);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private Set<String> getAllSymbolVolumeOverVolumeNotTrade() {
        Set<String> syms = new HashSet<>();
        Map<String, Double> sym2Volume = Volume24hrManager.getInstance().symbol2Volume;
        for (Map.Entry<String, Double> entry : sym2Volume.entrySet()) {
            String sym = entry.getKey();
            Double volume = entry.getValue();
            if ((volume / 1000000) >= MAX_VOLUME_TRADING) {
                Double rateChange = Volume24hrManager.getInstance().symbol2RateChange.get(sym);
                if (rateChange != null && rateChange < 0.05) {
                    syms.add(sym);
//                    LOG.info("{} not trade rateChange: {} volume: {}", sym, rateChange, volume);
                }
//                syms.add(sym);
            }
        }
        return syms;
    }

    private void startThreadUpdateSymbol2Trading() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateSymbol2Trading");
            LOG.info("Start ThreadUpdateSymbol2Trading !");
            while (true) {
                try {
                    updateSymbolTrading();
                    Thread.sleep(Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadUpdateSymbol2Trading: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public Set<String> getAllSymbol2TradingSignal() {
        return RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS_TRADING);
    }

    public Set<String> getAllSymbol2TradingVolumini() {
        return RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
    }
}
