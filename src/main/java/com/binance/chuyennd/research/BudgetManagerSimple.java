package com.binance.chuyennd.research;

import com.binance.chuyennd.trading.OrderTargetStatus;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * @author pc
 */
public class BudgetManagerSimple {

    public static final Logger LOG = LoggerFactory.getLogger(BudgetManagerSimple.class);

    public BalanceIndex balanceIndex = new BalanceIndex();

    public Float BUDGET_PER_ORDER;

    public Map<Long, Float> time2Balance = new HashMap<>();
    public Float unProfit = 0f;

    public Float profitLossMax = 0f;
    public Float totalFee = 0f;
    public Float totalFundingFee = 0f;
    public Float balanceBasic = Configs.capitalStart();
    public Float balanceCurrent = balanceBasic;
    public AtomicInteger counterOrderCreated = new AtomicInteger(0);

    public Float profit = 0f;
    public Integer maxOrderRunning = 0;
    public Float fee = 0f;
    public int totalSL = 0;

    private static volatile BudgetManagerSimple INSTANCE = null;
    public Float marginRunning = 0f;

    // 🔴 maxDD CHÍNH THỨC: đáy unrealized danh mục THẬT, lấy MỖI TICK theo bar.low (xem Simulator).
    //    Ghi thẳng vào balanceIndex.unProfitMin (single source) — THAY cho writer cũ Σ profitMin/minPrice
    //    (nông + lấy mẫu theo giờ). Fitness HPO V3 đọc unProfitMin nên giờ phạt DD theo đáy THẬT.
    public Float trueUnrealizedMin = 0f;
    public Long timeTrueUnrealizedMin;
    public TreeMap<Integer, Float> year2TrueUnrealizedMin = new TreeMap<>();

    // 🟡 TASK-119 — maxDD MARK-TO-MARKET + MARGIN_CALL (REPORT-ONLY, chạy SONG SONG, KHÔNG vào fitness/verdict).
    //    Khác maxDD cũ (unProfitMin neo 0 unrealized): equity_mtm = vốn + realized(net) + unrealized@bar.low,
    //    maxDD_mtm đo drawdown TỪ ĐỈNH chạy → bắt phần realized đã tích luỹ rồi trả lại (martingale gom lãi
    //    nhỏ rồi crash). MARGIN_CALL theo Binance USDⓈ-M cross: thanh lý khi marginBalance(=equity_mtm) ≤
    //    maintenanceMargin. Giả định proxy v1: MMR phẳng 0.5% (bậc thấp alt), maintAmount=0, notional@bar.low.
    //    Xoá cụm này ⇒ hành vi cũ y hệt (không nhánh quyết định nào đọc). Xem tasks/119.
    public static final float MAINT_MARGIN_RATE = 0.005f;  // proxy MMR Binance cross 1x (giả định, ghi ở task)
    public Float equityPeakMtm = null;   // đỉnh equity_mtm chạy (null tới tick đầu có vị thế)
    public Float maxDDMtm = 0f;          // max drawdown equity_mtm (abs USD, ≥0)
    public Long timeMaxDDMtm;
    public Float minEquityMtm = null;    // equity_mtm thấp nhất từng thấy (abs USD)
    public boolean marginCallHit = false;
    public Long timeMarginCall;

    // 🟢 PER-QUÝ MARK-TO-MARKET (TASK-110): đo hiệu suất từng quý ĐÚNG cách — equity = realized + unrealized
    //    snapshot mỗi tick theo quý. Tránh sai lệch "lệch quý": lệnh mở Q1 lỗ-tạm rồi chốt-lời Q2, nếu chỉ
    //    quy PnL theo timeUpdate (đóng) thì Q1 giấu lỗ, Q2 phồng lãi. Mark-to-market: lỗ-tạm hạ equity Q1
    //    (âm vào Q1), chốt-lời nâng equity Q2 (dương Q2) — đúng "trừ âm cuối quý, cộng khi sang quý".
    //    quarterKey = year*10 + quarter(1..4). equityLast = equity điểm cuối cùng thấy trong quý;
    //    equityMin = đáy equity trong quý (cho maxDD per-quý thật). Hiệu suất quý = equityLast[q] - equityLast[q-1].
    public TreeMap<Integer, Float> quarter2EquityLast = new TreeMap<>();
    public TreeMap<Integer, Float> quarter2EquityMin = new TreeMap<>();
    public TreeMap<Integer, Float> quarter2EquityMax = new TreeMap<>();
    public TreeMap<Integer, Long> quarter2LastTime = new TreeMap<>();

    static int quarterKeyOf(long time) {
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(time);
        int year = cal.get(Calendar.YEAR);
        int month0 = cal.get(Calendar.MONTH);   // 0-based: 0=Jan .. 11=Dec
        int q = month0 / 3 + 1;                  // Q1=0..2, Q2=3..5, Q3=6..8, Q4=9..11
        return year * 10 + q;
    }

    private static final ThreadLocal<BudgetManagerSimple> threadLocalInstance = ThreadLocal.withInitial(BudgetManagerSimple::new);

    public static BudgetManagerSimple getInstance() {
        return threadLocalInstance.get();
    }

    public static void resetInstance() {
        threadLocalInstance.remove();
    }

    /**
     * Cập nhật đáy unrealized THẬT của danh mục (đo lường, không quyết định). Gọi MỖI TICK từ Simulator.
     *
     * @param unrealizedAtLow tổng unrealized danh mục tính theo bar.low của từng cụm đang chạy (âm = lỗ)
     * @param time            mốc phút hiện tại (GMT+7) — để gom đáy theo năm
     */
    public void updateTrueUnrealizedMin(float unrealizedAtLow, long time) {
        if (unrealizedAtLow < trueUnrealizedMin) {
            trueUnrealizedMin = unrealizedAtLow;
            timeTrueUnrealizedMin = time;
            // 🔴 maxDD CHÍNH THỨC = đáy unrealized THẬT (per-tick, bar.low). Ghi thẳng vào unProfitMin để
            //    fitness HPO (HPOFitnessCalculatorV3) + mọi report đọc đúng DD thật. ĐÂY là single source —
            //    writer cũ (Σ profitMin/minPrice) trong BalanceIndex.updateIndex đã gỡ.
            balanceIndex.unProfitMin = trueUnrealizedMin;
            balanceIndex.timeUnProfitMin = time;
        }
        int year = Utils.getYear(time);
        Float yMin = year2TrueUnrealizedMin.get(year);
        if (yMin == null || yMin > unrealizedAtLow) {
            year2TrueUnrealizedMin.put(year, unrealizedAtLow);
        }
    }

    /**
     * TASK-119 (REPORT-ONLY) — cập nhật maxDD mark-to-market + cờ MARGIN_CALL. Gọi MỖI TICK từ Simulator
     * NGAY SAU {@link #updateTrueUnrealizedMin} (cùng cadence + cùng mark bar.low). KHÔNG vào fitness/verdict.
     *
     * @param unrealizedAtLow tổng unrealized danh mục @bar.low (âm=lỗ) — CHÍNH số truyền cho maxDD cũ
     * @param notionalAtLow   tổng notional @bar.low = Σ qty·bar.minPrice (cho maintenance margin)
     * @param time            mốc phút (GMT+7)
     */
    public void updateEquityMtm(float unrealizedAtLow, float notionalAtLow, long time) {
        float equity = balanceBasic + profit + unrealizedAtLow;   // realized NET (profit) + unrealized@low

        if (equityPeakMtm == null || equity > equityPeakMtm) {
            equityPeakMtm = equity;
        }
        float dd = equityPeakMtm - equity;   // ≥0
        if (dd > maxDDMtm) {
            maxDDMtm = dd;
            timeMaxDDMtm = time;
        }
        if (minEquityMtm == null || equity < minEquityMtm) {
            minEquityMtm = equity;
        }
        // MARGIN_CALL (Binance cross): equity_mtm ≤ maintenanceMargin ≈ MMR·notional (maintAmount=0, bậc thấp).
        if (equity <= MAINT_MARGIN_RATE * notionalAtLow) {
            if (!marginCallHit) {
                marginCallHit = true;
                timeMarginCall = time;
            }
        }
    }

    public void updateBudget() {
        try {
            BUDGET_PER_ORDER = balanceBasic / Configs.number_order_budget;
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public Float getBudget() {
        if (BUDGET_PER_ORDER == null || BUDGET_PER_ORDER == 0.0f) updateBudget();
        return BUDGET_PER_ORDER;
    }

    public void updatePnl(OrderTargetInfoTest orderInfo) {
        if (orderInfo != null) {
            if (orderInfo.status.equals(OrderTargetStatus.STOP_LOSS_DONE)) {
                totalSL++;
            }
            fee += calFee(orderInfo);
            totalFundingFee += orderInfo.calFundingFee();
            profit += orderInfo.calTp();
        }
    }

    // 🔥 HÀM MỚI: TƯƠNG THÍCH VỚI ARRAY SIÊU TỐC TỪ SIMULATOR
    public void updateBalance(Long timeUpdate, TreeMap<Long, OrderTargetInfoTest> allOrderDone,
                              Set<Short> activeIds, OrderTargetInfoTest[] orderRunning,
                              List<OrderTargetInfoTest>[] symbol2OrdersEntry, boolean isPrintBalance) {
        Float balance = balanceBasic;
        totalFee = fee;
        balance = balance + profit;
        balanceCurrent = balance;

        // Trích xuất list đang chạy
        List<OrderTargetInfoTest> runningList = new ArrayList<>(activeIds.size());
        for (short id : activeIds) {
            if (orderRunning[id] != null) runningList.add(orderRunning[id]);
        }

        unProfit = calUnrealizedProfit(runningList);
        profitLossMax = calProfitLossMax(runningList);

        // 🟢 PER-QUÝ MARK-TO-MARKET (TASK-110): equity = balanceBasic + realized(profit) + unrealized(unProfit).
        //    Snapshot MỖI TICK (ngoài if isPrintBalance — phải liên tục). equityLast = giá trị tick muộn nhất
        //    trong quý → hiệu suất quý = equityLast[q] - equityLast[q-1] (tự xử lý lệnh xuyên quý). equityMin/Max
        //    = đáy/đỉnh equity trong quý → maxDD per-quý thật (đáy trong quý so đầu quý).
        float equity = balance + unProfit;   // balance đã = balanceBasic + profit
        int qk = quarterKeyOf(timeUpdate);
        Long lastT = quarter2LastTime.get(qk);
        if (lastT == null || timeUpdate >= lastT) {
            quarter2EquityLast.put(qk, equity);
            quarter2LastTime.put(qk, timeUpdate);
        }
        Float qMin = quarter2EquityMin.get(qk);
        if (qMin == null || equity < qMin) quarter2EquityMin.put(qk, equity);
        Float qMax = quarter2EquityMax.get(qk);
        if (qMax == null || equity > qMax) quarter2EquityMax.put(qk, equity);

        Float positionMarginReal = marginRunning;

        // Truyền thẳng Set và Mảng sang BalanceIndex
        balanceIndex.updateIndex(balanceBasic, marginRunning, positionMarginReal, timeUpdate, profitLossMax,
                profitLossMax, activeIds, symbol2OrdersEntry, orderRunning, unProfit);

        if (isPrintBalance) {
            time2Balance.put(timeUpdate, balance);
            Float balanceYesterday = time2Balance.get(timeUpdate - Utils.TIME_DAY);
            Float profitOfDate = 0f;
            if (balanceYesterday != null) {
                profitOfDate = balance - balanceYesterday;
            }

            Float marginMaxDate = balanceIndex.date2MarginMax.get(Utils.getDate(timeUpdate - Utils.TIME_MINUTE));
            if (marginMaxDate == null) marginMaxDate = 0f;

            Float marginMaxMonth = balanceIndex.month2MarginMax.get(Utils.getMonth(timeUpdate - Utils.TIME_DAY));
            if (marginMaxMonth == null) marginMaxMonth = 0f;

            Float unProfitDate = balanceIndex.date2ProfitMin.get(Utils.getDate(timeUpdate - Utils.TIME_MINUTE));
            if (unProfitDate == null) unProfitDate = 0f;

            Float unProfitMonth = balanceIndex.month2ProfitMin.get(Utils.getMonth(timeUpdate - Utils.TIME_DAY));
            if (unProfitMonth == null) unProfitMonth = 0f;

            LOG.info("Update {} => b:{} pD:{}\tm:{}\tmax:{}\t{}\t" +
                            "unP:{}\tunPMin:{}\t{}\t{}\t{}%\tdone:{}/{}/{} run:{}/{} f:{}",
                    Utils.normalizeDateYYYYMMDDHHmm(timeUpdate), Utils.formatLog(balance.longValue(), 5),
                    Utils.formatLog(profitOfDate.longValue(), 4),
                    Utils.formatLog(marginRunning.longValue(), 4),
                    Utils.formatLog(marginMaxDate.longValue(), 5),
                    Utils.formatLog(marginMaxMonth.longValue(), 5),
                    Utils.formatLog(unProfit.longValue(), 5),
                    Utils.formatLog(balanceIndex.unProfitMin.longValue(), 5),
                    Utils.formatLog(unProfitDate.longValue(), 5),
                    Utils.formatLog(unProfitMonth.longValue(), 5),
                    Utils.formatPercentNew(balanceIndex.unProfitMin / balanceBasic),
                    totalSL, allOrderDone.size(), counterOrderCreated.get(),
                    counterOrderRunning(activeIds, symbol2OrdersEntry), maxOrderRunning, totalFundingFee.longValue());
        }
    }

    // Đếm lệnh bằng Set và Array
    private Integer counterOrderRunning(Set<Short> activeIds, List<OrderTargetInfoTest>[] symbol2OrdersEntry) {
        int counter = 0;
        for (short id : activeIds) {
            if (symbol2OrdersEntry[id] != null) {
                counter += symbol2OrdersEntry[id].size();
            }
        }
        return counter;
    }

    private Float calFee(OrderTargetInfoTest orderInfo) {
        return orderInfo.quantity * orderInfo.priceEntry * Configs.RATE_FEE;
    }

    public Float calUnrealizedProfitMin(Collection<OrderTargetInfoTest> orderInfos) {
        Float result = 0f;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            result += orderInfo.profitMin;
        }
        return result;
    }

    public Float calUnrealizedProfit(Collection<OrderTargetInfoTest> orderInfos) {
        Float result = 0f;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            result += orderInfo.calProfit();
        }
        return result;
    }

    public Float calProfitLossMax(Collection<OrderTargetInfoTest> orderInfos) {
        Float result = 0f;
        for (OrderTargetInfoTest orderInfo : orderInfos) {
            result += orderInfo.profitMin;
        }
        return result;
    }

    public Float calPositionMargin(Collection<OrderTargetInfoTest> values) {
        Float totalMargin = 0f;
        if (values != null) {
            for (OrderTargetInfoTest orderInfo : values) {
                totalMargin += orderInfo.calMargin();
            }
        }
        return totalMargin;
    }

    public Float calPositionMarginReal(Collection<OrderTargetInfoTest> values) {
        Float totalMargin = 0f;
        if (values != null) {
            for (OrderTargetInfoTest orderInfo : values) {
                totalMargin += orderInfo.calMargin() - orderInfo.calProfit();
            }
        }
        return totalMargin;
    }

    public void updateMaxOrderRunning(Integer counterOrderRunning) {
        if (maxOrderRunning < counterOrderRunning) {
            maxOrderRunning = counterOrderRunning;
        }
    }
}