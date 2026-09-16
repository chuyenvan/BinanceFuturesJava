package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.object.MarketLevelChange;
import com.binance.chuyennd.helper.PositionHelper;
import com.binance.chuyennd.research.BudgetManagerSimple;
import com.binance.chuyennd.research.OrderTargetInfoTest;
import com.binance.chuyennd.trading.BudgetManager;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.trade.PositionRisk;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
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
        List<Map.Entry<K, OrderTargetInfoTest>> candidates = symbol2OrderRunning.entrySet()
                .stream()
                .filter(entry -> {
                    OrderTargetInfoTest order = entry.getValue();
                    try {
                        // DCA GRID (2026-08-01): grid co ke hoach, do tren firstEntryPrice + tran so leg.
                        // Mac dinh DCA_GRID_ENABLED=false -> chay logic cu NGUYEN VEN (byte-identical).
                        if (Configs.DCA_GRID_ENABLED) {
                            return DcaUtils.shouldDcaGrid(
                                    order.firstEntryPrice != null ? order.firstEntryPrice : order.priceEntry,
                                    order.lastPrice, order.legCount);
                        }
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
                .collect(Collectors.toList());

        // DCA ROUND CAP (2026-09-16) docs/PREREG_DCA_ROUND_CAP.md — tran tong margin moi moi luot.
        //   Mac dinh OFF => tra ve keys theo dung thu tu stream cu (byte-identical).
        if (Configs.DCA_ROUND_CAP_ENABLED && "drop".equals(Configs.DCA_RANK_MODE)) {
            return capByDrop(candidates, time);
        }
        return candidates.stream().map(Map.Entry::getKey).collect(Collectors.toList());
    }

    // ===== DCA ROUND CAP (2026-09-16) — trang thai per-tick, xuyen 2 call-site cung tick =====
    private static long capTickMillis = Long.MIN_VALUE;
    private static float capUsedThisTick = 0f;
    private static boolean capModeLogged = false;
    public static int capRounds = 0;        // so luot DCA co cap chay (>=1 ung vien)
    public static int capRoundsCut = 0;     // so luot bi cat (>=1 ung vien bi bo)
    public static int capLegsCut = 0;       // so leg (ung vien) bi cat

    /** Reset dem cho moi run sim (goi o Simulator.initDataReady). */
    public static void resetRoundCapStats() {
        capTickMillis = Long.MIN_VALUE;
        capUsedThisTick = 0f;
        capModeLogged = false;
        capRounds = 0;
        capRoundsCut = 0;
        capLegsCut = 0;
    }

    /** Xep hang drop tang dan (rot sau nhat truoc) + cong don margin moi toi tran PCT x equity.
     *  Chi cat (bo) ung vien khi tong vuot tran; GIU NGUYEN thu tu GOC cua cac ung vien duoc giu
     *  (khong reorder khi khong cat => byte-identical voi parity khi cap khong binding). */
    private static <K> List<K> capByDrop(List<Map.Entry<K, OrderTargetInfoTest>> candidates, Long time) {
        long t = time != null ? time.longValue() : Long.MIN_VALUE;
        if (t != capTickMillis) {   // tick moi => reset budget luot (xuyen 2 call-site cung tick)
            capTickMillis = t;
            capUsedThisTick = 0f;
        }
        if (candidates.isEmpty()) {
            return java.util.Collections.emptyList();
        }

        // xep hang drop tang dan (rot sau nhat truoc) — chi de QUYET DINH ai bi cat
        List<Map.Entry<K, OrderTargetInfoTest>> ranked = new ArrayList<>(candidates);
        ranked.sort(Comparator.comparingDouble(e ->
                (double) DcaUtils.dcaGridDrop(
                        e.getValue().firstEntryPrice != null ? e.getValue().firstEntryPrice : e.getValue().priceEntry,
                        e.getValue().lastPrice)));

        BudgetManagerSimple bm = BudgetManagerSimple.getInstance();
        float balanceBasic = Configs.FIX_B3 ? bm.equityNow() : bm.balanceBasic;
        Float mb = TradeUtils.managerBudget(BudgetManagerSimple.getInstance().getBudget(),
                bm.marginRunning, balanceBasic, MarketLevelChange.DCA_LEVEL1);
        float capValue = Configs.DCA_ROUND_CAP_PCT * balanceBasic;

        // duyet tu sau nhat (drop nho nhat truoc), cong don margin; bo (cat) khi vuot tran / het bac
        Set<K> cutKeys = new HashSet<>();
        for (Map.Entry<K, OrderTargetInfoTest> e : ranked) {
            OrderTargetInfoTest o = e.getValue();
            float tier = tierMultiplierOf(e.getKey());
            float m = DcaUtils.dcaGridLegMargin(mb, tier, o.legCount);
            if (m <= 0f || capUsedThisTick + m > capValue) {   // het bac grid / u>=U_MAX / tran 10%
                cutKeys.add(e.getKey());
            } else {
                capUsedThisTick += m;
            }
        }

        // giu thu tu GOC (byte-identical khi khong cat), chi bo cac key bi cat
        List<K> kept = new ArrayList<>();
        for (Map.Entry<K, OrderTargetInfoTest> e : candidates) {
            if (!cutKeys.contains(e.getKey())) kept.add(e.getKey());
        }

        int cut = cutKeys.size();
        capRounds++;
        if (cut > 0) {
            capRoundsCut++;
            capLegsCut += cut;
        }
        if (!capModeLogged) {
            capModeLogged = true;
            LOG.info("[DCA-CAP] MODE rank={} capPct={}", Configs.DCA_RANK_MODE, Configs.DCA_ROUND_CAP_PCT);
        }
        if (cut > 0) {
            LOG.info("[DCA-CAP] t={} nCand={} kept={} cut={} cap={} eq={}",
                    time, candidates.size(), kept.size(), cut, capValue, balanceBasic);
        }
        return kept;
    }

    private static float tierMultiplierOf(Object key) {
        if (key instanceof Number) {
            return CoinRankManager.getInstance().getBudgetMultiplier(((Number) key).shortValue());
        }
        return 1f;
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


