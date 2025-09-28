package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.client.model.trade.PositionRisk;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class DcaProcessor {

    public static List<String> getDCA(MarketLevelChange levelChange, Long time, Double budget,
                                      Map<String, OrderTargetInfoTest> symbol2OrderRunning, Boolean isTrendBuyWithETH) {
        return symbol2OrderRunning.entrySet()
                .stream()
                .filter(entry -> {
                    OrderTargetInfoTest order = entry.getValue();
                    // "Giải nén" các thuộc tính từ đối tượng 'order' và truyền vào hàm tiện ích
                    return DcaUtils.shouldDca(
                            order.calMargin(),
                            order.calRateLoss(),
                            order.marketLevelChange,
                            order.timeStart,
                            levelChange,  // Trạng thái thị trường chung
                            time,         // Thời gian hiện tại
                            budget,
                            isTrendBuyWithETH
                    );
                })
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }

    /**
     * Hàm DCA cho môi trường Production.
     */
    public static List<String> getDCAProduction(MarketLevelChange levelChange, Long time, Double budget,
                                                Map<String, PositionRisk> symbol2OrderRunning, boolean isTrendBuyWitETH) {

        return symbol2OrderRunning.entrySet()
                .stream()
                .filter(entry -> {
                    PositionRisk pos = entry.getValue();
                    // "Giải nén" các thuộc tính từ đối tượng 'order' và truyền vào hàm tiện ích
                    return DcaUtils.shouldDca(
                            PositionHelper.callMargin(pos),
                            PositionHelper.calRateLoss(pos),
                            BudgetManager.getInstance().symbol2Level.get(pos.getSymbol()),
                            pos.getUpdateTime(),
                            levelChange,  // Trạng thái thị trường chung
                            time,         // Thời gian hiện tại
                            budget,
                            isTrendBuyWitETH);
                })
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }
}


