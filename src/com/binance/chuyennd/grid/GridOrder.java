/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.grid.enums.GridOrderStatus;
import com.binance.client.model.trade.Order;

/**
 *
 * @author pc
 */
public class GridOrder {

    public Double priceStart;
    public Double priceEnd;
    public Double quantity;
    public Order orderStart;
    public Order orderEnd;
    public GridOrderStatus status;
}
