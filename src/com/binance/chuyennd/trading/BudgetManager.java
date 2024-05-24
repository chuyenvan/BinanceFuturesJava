/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Set;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.logging.Level;

/**
 * @author pc
 */
public class BudgetManager {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManager.class);
    private static volatile BudgetManager INSTANCE = null;
    public Double RATE_BUDGET_PER_ORDER = Configs.getDouble("RATE_BUDGET_PER_ORDER");
    public AtomicInteger numberOrderBudgetAvailable = new AtomicInteger(0);
    public Double MAX_CAPITAL_RATE = Configs.getDouble("MAX_CAPITAL_RATE");
    public Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public Double BUDGET_PER_ORDER;
//    public Double investing = null;

    public static BudgetManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new BudgetManager();
            INSTANCE.updateBudget();
            INSTANCE.updateAllSymbol();
            INSTANCE.scheduleUpdateInvesting();
            INSTANCE.startThreadUpdateDataByHour();
        }
        return INSTANCE;
    }

    private void updateBudget() {
        try {
            Double balance = ClientSingleton.getInstance().getBalance();
            Double budget = RATE_BUDGET_PER_ORDER * balance;
            BUDGET_PER_ORDER = budget / 100;
            LOG.info("Ba and Bu to t: {} -> {}", balance, BUDGET_PER_ORDER);
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

    public Integer getNumberOrderBudgetAvailable() {
        if (numberOrderBudgetAvailable.get() == 0) {
            updateCounterOrderBudgetAvailable();
        }
        if (numberOrderBudgetAvailable.get() > 0) {
            return numberOrderBudgetAvailable.getAndDecrement();
        } else {
            return 0;
        }
    }

    public String callRateCurrent2Die() {
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        return Utils.formatPercent(umInfo.getMarginBalance().doubleValue()
                / (umInfo.getPositionInitialMargin().doubleValue() * LEVERAGE_ORDER));

    }

    public String getInvesting() {
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        return Utils.formatPercent(umInfo.getPositionInitialMargin().doubleValue()
                / (umInfo.getWalletBalance().doubleValue()));

    }

    public Double getInvesting2Check() {
        try {
            Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
            return umInfo.getPositionInitialMargin().doubleValue() * 100
                    / (umInfo.getWalletBalance().doubleValue());
        } catch (Exception e) {
            e.printStackTrace();
        }
        return MAX_CAPITAL_RATE;
    }

    public Integer getLeverage() {
        return LEVERAGE_ORDER;
    }

    private void scheduleUpdateInvesting() {
        new Thread(() -> {
            Thread.currentThread().setName("updateInvesting");
            LOG.info("Start updateInvesting !");
            while (true) {
                try {
                    updateCounterOrderBudgetAvailable();
                    Thread.sleep(10 * Utils.TIME_MINUTE);
                } catch (InterruptedException ex) {
                    java.util.logging.Logger.getLogger(BudgetManager.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }).start();
    }

    private void updateCounterOrderBudgetAvailable() {
        Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
        Double balanceAvailable = MAX_CAPITAL_RATE * umInfo.getWalletBalance().doubleValue() / 100;
        balanceAvailable -= umInfo.getPositionInitialMargin().doubleValue();
        Double numberOrder = balanceAvailable / BUDGET_PER_ORDER;
        numberOrderBudgetAvailable.set(numberOrder.intValue());
    }

    private void updateAllSymbol() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadupdateAllSymbol");
            LOG.info("Start thread updateAllSymbol !");
            while (true) {
                try {
                    Thread.sleep(Utils.TIME_HOUR);
                    updateListSymbolAll();
                } catch (Exception e) {
                    LOG.error("ERROR during updateAllSymbol: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void updateListSymbolAll() {
        try {
            List<PositionRisk> positions = BinanceFuturesClientSingleton.getInstance().getAllPositionInfos();
            Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS);
            for (PositionRisk position : positions) {
                String symbol = position.getSymbol();
                if (!allSymbols.contains(symbol) && StringUtils.endsWithIgnoreCase(symbol, "usdt")
                        && !Constants.specialSymbol.contains(symbol)) {
                    LOG.info("Add {} new to all symbol!", symbol);
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_ALL_SYMBOLS, symbol, symbol);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) throws InterruptedException {
        BinanceFuturesClientSingleton.getInstance();
        Thread.sleep(1000);
        for (int i = 0; i < 100; i++) {
            System.out.println(BudgetManager.getInstance().getNumberOrderBudgetAvailable());
        }
    }

}
