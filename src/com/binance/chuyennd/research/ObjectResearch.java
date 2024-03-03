/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.client.OrderStatusProcess;
import com.binance.client.model.enums.OrderSide;
import java.io.Serializable;

/**
 *
 * @author pc
 */
public class ObjectResearch implements Serializable {

    public String symbol;
    public Double priceOrder;
    public Double lastPrice;
    public Double priceClose;
    public Double bestPriceByOrder;
    public OrderStatusProcess statusProcess;
    public String researchName;
    public OrderSide side;
    public Long timeCreate;

    @Override
    public String toString() {
        StringBuilder builder = new StringBuilder();
        builder.append(symbol).append(",");
        builder.append(priceOrder).append(",");
        builder.append(lastPrice).append(",");
        builder.append(timeCreate).append(",");
        return builder.toString();
    }

    public void updateLastPrice(double lastPrice) {
        this.lastPrice = lastPrice;
        if (this.side.equals(OrderSide.BUY)) {
            if (this.bestPriceByOrder < this.lastPrice) {
                this.bestPriceByOrder = this.lastPrice;
            }
        } else {
            if (this.bestPriceByOrder > this.lastPrice) {
                this.bestPriceByOrder = this.lastPrice;
            }
        }
        // check to close position
        checkAndClosePosition();
    }

    private void checkAndClosePosition() {
        Double rate;
        if (this.side.equals(OrderSide.BUY)) {
            rate = (lastPrice - priceOrder) * 100 / priceOrder;
        } else {
            rate = (priceOrder - lastPrice) * 100 / priceOrder;
        }
        if (rate > 2) {
            // close position
            statusProcess = OrderStatusProcess.FINISHED;
            priceClose = lastPrice;
        }
    }
}
