package com.binance.chuyennd.trading.grid;

import com.binance.client.model.trade.Order;

public class GridOrderProd {
    public Double price;
    public Order orderBuy;
    public Order orderSell;
    public GridOrderProd(Double price) {
        this.price = price;
        this.orderBuy = null;
        this.orderSell = null;
    }
}
