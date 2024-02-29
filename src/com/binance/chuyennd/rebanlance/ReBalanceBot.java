/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.rebanlance;

import com.binance.chuyennd.utils.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class ReBalanceBot {

    public static final Logger LOG = LoggerFactory.getLogger(ReBalanceBot.class);
    public static final Long TIME_REBALANCE = Configs.getLong("TIME_REBALANCE");
    public static final Double TOTAL_BUDGET = Configs.getDouble("TOTAL_BUDGET");
    public static final Double DURATION_MAX_BALANCE = Configs.getDouble("DURATION_MAX_BALANCE");
    public static final Double DURATION_MIN_BALANCE = Configs.getDouble("DURATION_MIN_BALANCE");

    public static void main(String[] args) {
        new ReBalanceBot().start();
    }

    private void initData() {
        
    }

    private void start() {
        initData();
    }
}
