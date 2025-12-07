package com.binance.chuyennd.ai_ml.hpo;

import com.binance.chuyennd.ai_ml.onnx.AIRejectFilter;
import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.bigchange.market.MarketDataObject;
import com.binance.chuyennd.object.MarketRateChange;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.research.SimulatorMarketLevelTicker1MStopLoss;

import java.util.Calendar;
import java.util.Map;
import java.util.TreeMap;
import java.util.concurrent.ConcurrentHashMap;

public class BackTestEngineAI {

    // Constructor nhận các tham số gen từ Jenetics
    public AIRejectFilter aiRejectFilter = new AIRejectFilter();

    public BackTestEngineAI(double risk, double minRet1H, double highRet,
                            double minMom15M, double minTrend4H, double deadTrend24H) {

        // Bơm tham số vào bộ lọc AI (Class AIRejectFilter phải bỏ final các biến này)
        aiRejectFilter.setConfig(risk, minRet1H, highRet, minMom15M, minTrend4H, deadTrend24H);
    }

    public double run(TreeMap<Long, MarketDataObject> time2MarketData,
                      TreeMap<Long, MarketRateChange> time2MarketRateChange,
                      TreeMap<Long, Double> time2BtcReverse,
                      ConcurrentHashMap<String, Map<Long, Boolean>> symbol2TrendData,
                      TreeMap<Long, AiPredictionData> predictionMap) {
        try {
            // 1. Reset Singleton BudgetManager
            BudgetManagerSimple.resetInstance();

            // 2. Khởi tạo Simulator
            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss();

            // 3. Inject dữ liệu Cache (bao gồm cả dữ liệu AI Prediction)
            test.initDataReady(time2MarketData, time2MarketRateChange, time2BtcReverse, symbol2TrendData,
                    predictionMap, aiRejectFilter);

            // 4. Chạy Simulation
            test.simulatorWithInitEntry();

            // 5. Tính toán lợi nhuận mục tiêu
            // TÙY CHỌN: Trả về Lợi nhuận Năm Nay hoặc Tổng Lợi Nhuận
            return calculateCurrentYearProfit(test);

        } catch (Exception e) {
            e.printStackTrace();
            return -10000.0; // Phạt nặng nếu lỗi
        }
    }

    // Hàm phụ trợ tính lợi nhuận riêng năm hiện tại
    private double calculateCurrentYearProfit(SimulatorMarketLevelTicker1MStopLoss simulator) {
        double currentYearProfit = 0;
        Calendar cal = Calendar.getInstance();
        int currentYear = cal.get(Calendar.YEAR);

        for (OrderTargetInfoTest order : simulator.allOrderDone.values()) {
            cal.setTimeInMillis(order.timeUpdate);
            if (cal.get(Calendar.YEAR) == currentYear) {
                currentYearProfit += order.calTp();
            }
        }
        return currentYearProfit;
    }
}