/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.object;

import com.binance.client.model.enums.OrderSide;
import java.io.Serializable;

/**
 *
 * @author pc
 */
public class PremiumIndex implements Serializable {

    public String symbol;
    public String markPrice;
    public String indexPrice;
    public String estimatedSettlePrice;
    public String lastFundingRate;
    public String interestRate;
    public Long nextFundingTime;
    public Long time;
    public OrderSide side;

    @Override
    public String toString() {
        StringBuilder builder = new StringBuilder();
        builder.append(symbol).append(",");
        builder.append(markPrice).append(",");
        builder.append(indexPrice).append(",");
        builder.append(estimatedSettlePrice).append(",");
        builder.append(lastFundingRate).append(",");
        builder.append(interestRate).append(",");
        builder.append(nextFundingTime).append(",");
        builder.append(time).append(",");
        return builder.toString();
    }
}
