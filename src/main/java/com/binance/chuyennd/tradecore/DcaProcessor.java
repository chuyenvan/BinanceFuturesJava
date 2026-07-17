package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketLevelChange;
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


    // Thêm <K> đại diện cho Key (có thể là String hoặc Short)
    public static <K> List<K> getDCA(MarketLevelChange levelChange, Long time, Float budget,
                                     Map<K, OrderTargetInfoTest> symbol2OrderRunning) {
        // ABLATION DCA-OFF (2026-07-16): env WFO_DISABLE_DCA=1 -> tat hoan toan nhoi lenh (do dong gop DCA).
        // Mac dinh (env vang) hanh vi cu NGUYEN VEN. Chi duong sim/backtest dung ham nay.
        if (Configs.WFO_DISABLE_DCA) {
            return java.util.Collections.emptyList();
        }
        return symbol2OrderRunning.entrySet()
                .stream()
                .filter(entry -> {
                    OrderTargetInfoTest order = entry.getValue();
                    try {
                        // Logic lõi giữ nguyên 100%
                        return DcaUtils.shouldDca(
                                order.calMargin(), order.calRateLoss(), order.marketLevelChange,
                                order.timeStart, levelChange, time, budget
                        );
                    } catch (Exception e) {
                        LOG.info("Error when processing DCA");
                    }
                    return false;
                })
                .map(Map.Entry::getKey) // Nếu đầu vào là Map<Short,...> thì nó trả về List<Short>
                .collect(Collectors.toList());
    }


    /**
     * Hàm DCA cho môi trường Production.
     */
    public static List<String> getDCAProduction(MarketLevelChange levelChange, Long time, Float budget,
                                                Map<String, PositionRisk> symbol2OrderRunning) {

        return symbol2OrderRunning.entrySet()
                .stream()
                .filter(entry -> {
                    PositionRisk pos = entry.getValue();
                    if (pos == null){
                        return false;
                    }
                    // "Giải nén" các thuộc tính từ đối tượng 'order' và truyền vào hàm tiện ích
                    return DcaUtils.shouldDca(
                            PositionHelper.callMargin(pos),
                            PositionHelper.calRateLoss(pos),
                            BudgetManager.getInstance().symbol2Level.get(pos.getSymbol()),
                            pos.getUpdateTime(),
                            levelChange,  // Trạng thái thị trường chung
                            time,         // Thời gian hiện tại
                            budget
                    );
                })
                .map(Map.Entry::getKey)
                .collect(Collectors.toList());
    }
}


