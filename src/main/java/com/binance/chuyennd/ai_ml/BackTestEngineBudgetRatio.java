package com.binance.chuyennd.ai_ml;

import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;
import com.binance.chuyennd.utils.Configs;

import java.io.IOException;
import java.text.ParseException;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class BackTestEngineBudgetRatio {

    public BackTestEngineBudgetRatio(
            double budgetRatio1, double budgetDivider1,
            double budgetRatio2, double budgetDivider2) {

        // Gán các giá trị mới cho mỗi lần chạy
        Configs.BUDGET_MARGIN_RATIO_1 = budgetRatio1;
        Configs.BUDGET_DIVIDER_1 = budgetDivider1;
        Configs.BUDGET_MARGIN_RATIO_2 = budgetRatio2;
        Configs.BUDGET_DIVIDER_2 = budgetDivider2;
    }

    public static void main(String[] args) throws IOException, ParseException {
        SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();
        test.initData();
        test.simulatorWithInitEntry();
    }

    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, MarketRateChange> time2MarketRateChange,
                      TreeMap<Long, Double> time2BtcReverse) {
        try {
            // 1. Reset Singleton về trạng thái ban đầu
            BudgetManagerSimple.resetInstance();

            // 2. Khởi tạo Simulator
            //    Nó sẽ TỰ ĐỘNG đọc các giá trị Configs mới mà chúng ta vừa gán
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            // 3. Chạy backtest
            //    (Lưu ý: test.initData() có thể làm chậm quá trình.
            //     Nếu có thể, hãy tối ưu để chỉ chạy 1 lần)
//            test.initData();
            test.initDataReady(time2MarketData, time2MarketRateChange, time2BtcReverse,
                    null, null);
            test.simulatorWithInitEntry();

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0; // Trả về 0 nếu có lỗi
        }

        // 4. Trả về lợi nhuận
        return BudgetManagerSimple.getInstance().balanceCurrent;
    }
}
