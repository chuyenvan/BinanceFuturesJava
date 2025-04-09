/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.client.TickerFuturesHelper;
import com.binance.chuyennd.position.manager.PositionHelper;
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

import java.util.*;

/**
 * @author pc
 */
public class BudgetManager {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManager.class);
    private static volatile BudgetManager INSTANCE = null;
    public static Double balanceBasic = Configs.getDouble("CAPITAL_START");


    public Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public Double BUDGET_PER_ORDER = 0d;
    public Double marginRunning = 0d;
    public Double balance = 0d;
    public Double slMax = 0d;
    public Map<String, Double> symbol2Margin = new HashMap<>();
    public Map<String, PositionRisk> symbol2Pos = new HashMap<>();
    public Set<String> marginBig = new HashSet<>();
    public Set<String> symbolSell = new HashSet<>();
    public Set<String> symbolBuy = new HashSet<>();
    public Map<String, MarketLevelChange> symbol2Level = new HashMap<>();


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
//            if (balanceCurrent / 5 > balanceBasic) {
//                BUDGET_PER_ORDER = ratePerOrder * (balanceCurrent / 5) / 100;
//            } else {
            BUDGET_PER_ORDER = ratePerOrder * balanceBasic / 100;
//            }
            LOG.info("Ba and Bu to t: {} -> {} balance init:{} marginRunning:{}", balanceCurrent, BUDGET_PER_ORDER, balanceBasic, marginRunning);
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
        return BUDGET_PER_ORDER / 2;
    }

    public Double getBudgetSell() {
        return BUDGET_PER_ORDER / 8;
    }


    public Double calMarginRunning(List<PositionRisk> positions) {
        Double margin = 0d;
        for (PositionRisk pos : positions) {
            if (pos.getPositionAmt().doubleValue() > 0) {
                margin += PositionHelper.callMargin(pos);
            }
        }
        return margin;
    }


    public Double getBudgetGrid() {
        return balanceBasic / (Constants.specialSymbol.size() * 10);
    }

    public Integer getLeverage() {
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

    public Set<String> getSymbolRunning(MarketLevelChange level) {
        Set<String> hashSet = new HashSet<>();
        for (String symbol : symbol2Level.keySet()) {
            if (level.equals(symbol2Level.get(symbol))) {
                hashSet.add(symbol);
            }
        }
        return hashSet;
    }

    private void updateListSymbolAll() {
        try {
            Set<String> symbols = TickerFuturesHelper.getAllSymbol();
            Set<String> allSymbols = RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS);
            for (String symbol : symbols) {
                if (!allSymbols.contains(symbol) && StringUtils.endsWithIgnoreCase(symbol, "usdt")
                        && !Constants.diedSymbol.contains(symbol)) {
                    LOG.info("Add {} new to all symbol!", symbol);
                    ClientSingleton.getInstance().initClient();
                    ClientSingleton.getInstance().syncRequestClient.changeInitialLeverage(symbol, BudgetManager.getInstance().getLeverage());
                    RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS, symbol, symbol);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Double calRateMin2MoveSL(MarketLevelChange marketLevelChange, Double priceEntry, Double maxPrice15M) {
        Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
        try {
            if (marginRunning != null
                    && marginRunning < 40 * BUDGET_PER_ORDER
                    && priceEntry != null
                    && maxPrice15M != null) {
                double rateMaxTarget = 0.01;
                if (marketLevelChange.equals(MarketLevelChange.BIG_DOWN)
                        || marketLevelChange.equals(MarketLevelChange.BIG_UP)
                        || marketLevelChange.equals(MarketLevelChange.MEDIUM_DOWN)
                        || marketLevelChange.equals(MarketLevelChange.MEDIUM_UP)
                        || marketLevelChange.equals(MarketLevelChange.SMALL_DOWN)
                        || marketLevelChange.equals(MarketLevelChange.SMALL_UP)
                ) {
                    rateMaxTarget = 0.08;
                }
                Double rateChangeNew = Utils.rateOf2Double(maxPrice15M, priceEntry) / 2;
                if (rateChangeNew > rateMin2MoveSl) {
                    rateMin2MoveSl = rateChangeNew;
                    if (rateChangeNew > rateMaxTarget) {
                        rateMin2MoveSl = rateMaxTarget;
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return rateMin2MoveSl;
    }

    public Double callRateLossDynamicBuy(Double unProfit, Double rateSLMin) {
        Double rateLoss = unProfit * 1000;
        Double rateStopLoss = Configs.RATE_STOP_LOSS_ALT;
//        if (Constants.specialSymbol.contains(symbol) || Constants.stableSymbol.contains(symbol)) {
//            rateStopLoss = Configs.RATE_STOP_LOSS_SPECIAL;
//        }
        Long tradingStopRate;
        if (rateLoss < 60) {
            tradingStopRate = rateLoss.longValue() / 2;
            if (tradingStopRate > 5) {
                tradingStopRate -= 2;
            }
        } else {
            tradingStopRate = 30l;
        }
        if (rateLoss < rateSLMin * 1000) {
            rateLoss = rateLoss.longValue() - rateStopLoss * 1000;
        } else {
            rateLoss = rateLoss.longValue() - tradingStopRate.doubleValue();
        }

        return rateLoss / 1000;
    }

    public void removeSymbolNotPos(Set<String> symbols) {
        Set<String> hashSet = new HashSet<>();
        for (String symbol : symbol2Level.keySet()) {
            if (!symbols.contains(symbol)) {
                hashSet.add(symbol);
            }
        }
        if (!hashSet.isEmpty()) {
            LOG.info("Remove symbol trade success: {}", hashSet);
            for (String symbol : hashSet) {
                symbol2Level.remove(symbol);
            }
        }
    }
}
