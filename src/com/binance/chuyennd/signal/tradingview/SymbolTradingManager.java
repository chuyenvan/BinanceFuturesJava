/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.signal.tradingview;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import java.util.HashSet;
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
            Set<String> symbolsTrading = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_RUNNING);
            Set<String> symbol2Trade = new HashSet<>();
            Set<String> allSymbol = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            symbol2Trade.addAll(allSymbol);
            symbol2Trade.removeAll(Constants.diedSymbol);
            symbol2Trade.removeAll(symbolsVolumeOverVolumeNotTrade);
            symbol2Trade.removeAll(symbolsTrading);
            String currentTime = String.valueOf(System.currentTimeMillis());
            //delet list old
            RedisHelper.getInstance().get().del(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_CHECKING);
            //write new
            LOG.info("Update {} symbols to trading list. all:{} not:{} running:{}", symbol2Trade.size(), allSymbol.size(),
                    symbolsVolumeOverVolumeNotTrade.size(), symbolsTrading.size()
            );
            for (String symbol : symbol2Trade) {
                RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_CHECKING, symbol, currentTime);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private Set<String> getAllSymbolVolumeOverVolumeNotTrade() {
        Set<String> syms = new HashSet<>();
//        Map<String, Double> sym2Volume = Volume24hrManager.getInstance().symbol2Volume;
//        for (Map.Entry<String, Double> entry : sym2Volume.entrySet()) {
//            String sym = entry.getKey();
//            Double volume = entry.getValue();
//            if ((volume / 1000000) >= MAX_VOLUME_TRADING) {
//                Double rateChangeWithOpen = Volume24hrManager.getInstance().symbol2RateChangeWithOpen.get(sym);
////                LOG.info("{} Open: {} last: {} high:{} rate: {}", sym,
////                        Volume24hrManager.getInstance().symbol2OpenPrice.get(sym),
////                        Volume24hrManager.getInstance().symbol2LastPrice.get(sym),
////                        Volume24hrManager.getInstance().symbol2MaxPrice.get(sym),
////                        rateChangeWithOpen);
//                // > max volume -> down > 5% or 24h tăng < 5%
//                if (rateChangeWithOpen != null && rateChangeWithOpen < 0.05) {
//                    syms.add(sym);
////                    LOG.info("{} not trade rateChange: {} volume: {}", sym, rateChange, volume);
//                }
//                syms.add(sym);
//            }
//        }
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
        return RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS_CHECKING);
    }

    public Set<String> getAllSymbol2TradingVolumeMini() {
        return RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
    }

    public static void main(String[] args) {
        SymbolTradingManager.getInstance().updateSymbolTrading();
    }
}
