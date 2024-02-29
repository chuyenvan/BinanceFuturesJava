/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.grid.enums.PositionSide;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 *
 * @author pc
 */
public class GridPosition {

    public Double symbol;
    public Double startPrice;
    public Double closePrice;
    public Double avgPrice;
    public Double minPrice;
    public Double maxPrice;
    public List<Double> listPrice = new ArrayList<>();
    public Double quantity;
    public PositionSide positionSide;
    public Double sumProfit;
    public Integer gridNumber;
    public Double distance;
    public Map<Double, GridOrder> price2GridOrder = new HashMap<>();
    public List<GridOrder> orderHistories; 

    void startGridManager() {
        initData();
    }

    private void initData() {
        
    }
}
