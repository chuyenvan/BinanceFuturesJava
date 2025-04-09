/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.client.model.enums.OrderSide;

import java.util.ArrayList;
import java.util.Collection;

/**
 * @author pc
 */
public class GridOrder extends OrderTargetInfoTest {
    public GridOrder(OrderTargetStatus status, Double priceEntry,
                     Double priceTP, Double quantity, Integer leverage, String symbol,
                     long timeStart, long timeUpdate, OrderSide side) {
        this.status = status;
        this.priceEntry = priceEntry;
        this.priceTP = priceTP;
        this.quantity = quantity;
        this.leverage = leverage;
        this.symbol = symbol;
        this.timeStart = timeStart;
        this.timeUpdate = timeUpdate;
        this.side = side;
    }

    public static void main(String[] args) {
        GridOrder order = new GridOrder(OrderTargetStatus.REQUEST, 1.0, null, 1.0,
                4, "BTCUSDT", System.currentTimeMillis(), System.currentTimeMillis(), OrderSide.SELL);
        LOG.info("{}", order.symbol);
        order.updateTPSL();
        Collection<OrderTargetInfoTest> orders = new ArrayList<>();
        orders.add(order);
        BudgetManagerSimple.getInstance().updateInvesting(orders);
    }

}
