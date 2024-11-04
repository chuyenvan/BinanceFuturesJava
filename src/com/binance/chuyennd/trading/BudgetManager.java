/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.trade.Asset;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.HashSet;
import java.util.Set;

/**
 * @author pc
 */
public class BudgetManager {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManager.class);
    private static volatile BudgetManager INSTANCE = null;
    public static Double balanceBasic = Configs.getDouble("CAPITAL_START");


    public Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public Double BUDGET_PER_ORDER;
    public Set<String> symbolLocked = new HashSet<>();
    public Set<String> symbolLoss = new HashSet<>();


    public static BudgetManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BudgetManager();
            INSTANCE.updateBudget();
            INSTANCE.updateAllSymbol();
            INSTANCE.startThreadUpdateDataByHour();
        }
        return INSTANCE;
    }

    private void updateBudget() {
        try {
            Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
            Double balanceCurrent = umInfo.getWalletBalance().doubleValue();
            Double ratePerOrder = (Configs.RATE_BUDGET_LIMIT_A_SIGNAL / Configs.NUMBER_ENTRY_EACH_SIGNAL);
            if (balanceCurrent / 5 > balanceBasic) {
                BUDGET_PER_ORDER = ratePerOrder * (balanceCurrent / 5) / 100;
            } else {
                BUDGET_PER_ORDER = ratePerOrder * balanceBasic / 100;
            }
            LOG.info("Ba and Bu to t: {} -> {} balance init:{}", balanceCurrent, BUDGET_PER_ORDER, balanceBasic);
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void startThreadUpdateDataByHour() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateBudgetByHour");
            LOG.info("Start thread ThreadUpdateBudgetByHour!");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR);
                    updateBudget();
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadUpdateBudgetByHour: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    public Double getBudget() {
        return BUDGET_PER_ORDER;
    }

    public String getInvesting() {
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        return Utils.formatPercent(umInfo.getPositionInitialMargin().doubleValue()
                / (umInfo.getWalletBalance().doubleValue()));

    }

    public Double getPositionInitialMargin() {
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        return umInfo.getPositionInitialMargin().doubleValue();
    }



    public Integer getLeverage(String symbol) {
        if (Constants.specialSymbol.contains(symbol)){
            return Configs.LEVERAGE_ORDER * 2;
        }
        return LEVERAGE_ORDER;
    }


    private void updateAllSymbol() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadUpdateAllSymbol");
            LOG.info("Start thread updateAllSymbol !");
            while (true) {
                try {
                    updateListSymbolAll();
                    Thread.sleep(Utils.TIME_HOUR);
                } catch (Exception e) {
                    LOG.error("ERROR during updateAllSymbol: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void updateListSymbolAll() {
        try {
            Set<String> symbols = TickerFuturesHelper.getAllSymbol();
            Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            for (String symbol : symbols) {
                if (!allSymbols.contains(symbol) && StringUtils.endsWithIgnoreCase(symbol, "usdt")
                        && !Constants.diedSymbol.contains(symbol)) {
                    LOG.info("Add {} new to all symbol!", symbol);
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol, symbol);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Double callRateLossDynamicBuy(Double unProfit, String symbol) {
        Double rateLoss = unProfit * 100;
        Long tradingStopRate = rateLoss.longValue() / 2;
        Integer rateProfit2Shard=  10;
        if (Constants.specialSymbol.contains(symbol)){
            rateProfit2Shard = 6;
        }
        if (rateLoss > rateProfit2Shard) {
            tradingStopRate = rateLoss.longValue() / 3;
            if (rateLoss > 2 * rateProfit2Shard) {
                tradingStopRate = rateLoss.longValue() / 4;
            }else{
                if (rateLoss > 3 * rateProfit2Shard) {
                    tradingStopRate = rateLoss.longValue() / 5;
                }
            }
        }
        if (rateLoss < 0) {
            rateLoss = rateLoss.longValue() - Configs.RATE_STOP_LOSS * 100;
        } else {
            rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        }

        return rateLoss / 100;
    }

    public Double calRateStop(Double rateLoss, String symbol) {
        Double rateStopLoss = Configs.RATE_STOP_LOSS;
        if (Constants.specialSymbol.contains(symbol)){
            rateStopLoss = rateStopLoss * 2;
        }
        Double rateStop;
        if (rateLoss < 0.01) {
            rateStop = -rateLoss + rateStopLoss;
        } else {
            rateStop = -rateLoss / 2;
        }
        return rateStop;
    }

    public static void main(String[] args) throws InterruptedException {
    }


}
