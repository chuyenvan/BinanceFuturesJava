/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.client.BinanceFuturesClientSingleton;
import com.binance.chuyennd.client.ClientSingleton;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.chuyennd.websocket.ListenAllTicker;
import com.binance.client.constant.Constants;
import com.binance.client.model.market.ExchangeInfoEntry;
import com.binance.client.model.trade.Asset;
import com.binance.client.model.trade.PositionRisk;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.math.BigDecimal;
import java.util.*;

/**
 * @author pc
 */
public class BudgetManager {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManager.class);
    private static volatile BudgetManager INSTANCE = null;
    public static Double balanceBasic = Configs.getDouble("CAPITAL_START");


    public Double BUDGET_PER_ORDER = 0d;

    public Double marginRunning = 0d;
    public Double balance = 0d;
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
            INSTANCE.startThreadUpdateDataByHour();
        }
        return INSTANCE;
    }

    private void updateBudget() {
        try {
            Asset umInfo = BinanceFuturesClientSingleton.getInstance().getAccountUMInfo();
            Double balanceCurrent = umInfo.getWalletBalance().doubleValue();
            BUDGET_PER_ORDER = balanceBasic / Configs.number_order_budget;
            long time = new File("target/binance-java-sdk-1.2.4.jar").lastModified();
            LOG.info("Ba and Bu {}: {} -> {} balance init:{} marginRunning:{} ", Utils.normalizeDateYYYYMMDDHHmm(time),
                    balanceCurrent, BUDGET_PER_ORDER, balanceBasic, marginRunning);
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

    public Double calMarginRunning(Collection<PositionRisk> positions) {
        Double margin = 0d;
        for (PositionRisk pos : positions) {
            if (pos.getPositionAmt().compareTo(new BigDecimal("0")) != 0) {
                margin += PositionHelper.callMargin(pos);
            }
        }
        return margin;
    }





    private Set<String> getAllSymbol() {
        Set<String> symbolActive = new HashSet<>();
        for (ExchangeInfoEntry symbol : ClientSingleton.getInstance().syncRequestClient.getExchangeInformation().getSymbols()) {
            if (StringUtils.endsWithIgnoreCase(symbol.getSymbol(), "usdt")
                    && symbol.getStatus().contains("TRADING")) {
                symbolActive.add(symbol.getSymbol());
            }
        }
        return symbolActive;
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
                RedisHelper.getInstance().delJsonData(RedisConst.REDIS_KEY_SYMBOL_2_ORDER_INFO, symbol);
                symbol2Level.remove(symbol);
            }
        }
    }

    public void addMarginRunning(Double budget) {
        if (marginRunning != null && budget != null) {
            marginRunning += budget;
        }
    }
}
