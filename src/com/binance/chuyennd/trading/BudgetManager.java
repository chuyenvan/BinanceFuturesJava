/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.trading;

import com.binance.chuyennd.funcs.*;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class BudgetManager {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManager.class);
    private static volatile BudgetManager INSTANCE = null;
    public Double RATE_BUDGET_PER_ORDER = Configs.getDouble("RATE_BUDGET_PER_ORDER");
    public Integer LEVERAGE_ORDER = Configs.getInt("LEVERAGE_ORDER");
    public Double BUDGET_PER_ORDER;

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
            Double balance = ClientSingleton.getInstance().getBalance();
            if (balance < 200) {
                LOG.info("Not t because b avalible not enough! avalible: {}", ClientSingleton.getInstance().getBalanceAvalible());
                BUDGET_PER_ORDER = 0.0;
            } else {
                Double budget = RATE_BUDGET_PER_ORDER * balance;
                BUDGET_PER_ORDER = budget / 100;
                if (BUDGET_PER_ORDER < 7.5) {
                    BUDGET_PER_ORDER = 7.5;
                }
                LOG.info("Ba and Bu to t: {} -> {}", balance, BUDGET_PER_ORDER);
            }
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

    Double getBudget() {
        return BUDGET_PER_ORDER;
    }

    Integer getLeverage() {
        return LEVERAGE_ORDER;
    }

}
