package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.bigchange.market.MarketLevelChange;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.trade.PositionRisk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

public class DcaProcessor {
    public static final Logger LOG = LoggerFactory.getLogger(DcaProcessor.class);

    public static List<String> getDCA(MarketLevelChange levelChange, Long time, Double budget,
                                      Map<String, OrderTargetInfoTest> symbol2OrderRunning, Boolean isTrendBuyWithBtc, Boolean isTrendBuyWithETH) {
        return symbol2OrderRunning.entrySet()
                .stream()
                .filter(entry -> {
                    OrderTargetInfoTest order = entry.getValue();
                    try {
                        // "Giải nén" các thuộc tính từ đối tượng 'order' và truyền vào hàm tiện ích
                        return DcaUtils.shouldDca(
                                order.calMargin(),
                                order.calRateLoss(),
                                order.marketLevelChange,
                                order.timeStart,
                                levelChange,  // Trạng thái thị trường chung
                                time,         // Thời gian hiện tại
                                budget,
                                isTrendBuyWithBtc,
                                isTrendBuyWithETH
                        );
                    } catch (Exception e) {
                        LOG.info("Error when processing DCA for {}", Utils.toJson(order));
                        e.printStackTrace();
                    }
                    return false;
                })
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }

    /**
     * Hàm DCA cho môi trường Production.
     */
    public static List<String> getDCAProduction(MarketLevelChange levelChange, Long time, Double budget,
                                                Map<String, PositionRisk> symbol2OrderRunning, boolean isTrendBuyWithBtc, boolean isTrendBuyWitETH) {

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
                            isTrendBuyWithBtc,
                            isTrendBuyWitETH);
                })
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }
}


