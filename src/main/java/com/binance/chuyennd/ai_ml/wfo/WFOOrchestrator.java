//package com.binance.chuyennd.ai_ml.wfo;
//
//import com.binance.chuyennd.ai_ml.wfo.entry.WFOTier1EntryRunner;
//import com.binance.chuyennd.ai_ml.wfo.dca_trailing.WFOTier2RiskRunner;
//import com.binance.chuyennd.ai_ml.wfo.budget.WFOTier3BudgetRunner;
//import com.binance.chuyennd.tradecore.BotTradingConfig;
//import com.binance.chuyennd.utils.Utils;
//import org.slf4j.Logger;
//import org.slf4j.LoggerFactory;
//
//import java.io.FileWriter;
//import java.io.PrintWriter;
//
//public class WFOOrchestrator {
//    private static final Logger LOG = LoggerFactory.getLogger(WFOOrchestrator.class);
//
//    public void startProcess(long startTs, long endTs) {
//        long isStep = 180 * Utils.TIME_DAY; // IS: 3 tháng huấn luyện
//        long oosStep = 60 * Utils.TIME_DAY; // OOS: 1 tháng thực chiến giả định
//
//        // 1. TÍNH TOÁN TỔNG SỐ VÒNG (WINDOWS) ĐỂ TÍNH PHẦN TRĂM TIẾN ĐỘ
//        long tempCurrent = startTs;
//        int totalWindows = 0;
//        while (tempCurrent + isStep + oosStep <= endTs) {
//            totalWindows++;
//            tempCurrent += oosStep;
//        }
//
//        LOG.info("=========================================================");
//        LOG.info("🎯 HỆ THỐNG WFO SẼ CHẠY TỔNG CỘNG: {} CỬA SỔ (WINDOWS)", totalWindows);
//        LOG.info("=========================================================");
//
//        long current = startTs;
//        int currentWindow = 0;
//        BotTradingConfig rollingConfig = new BotTradingConfig();
//
//        while (current + isStep + oosStep <= endTs) {
//            currentWindow++;
//            long trainEnd = current + isStep;
//            long testEnd = trainEnd + oosStep;
//
//            // Tính % tiến độ
//            double progressPct = ((double) currentWindow / totalWindows) * 100.0;
//
//            LOG.info("⏳ [TIẾN ĐỘ: {}%] ĐANG XỬ LÝ WINDOW {}/{} (Train: {} -> Test: {})",
//                    String.format("%.1f", progressPct), currentWindow, totalWindows,
//                    Utils.normalizeDateYYYYMMDD(trainEnd), Utils.normalizeDateYYYYMMDD(testEnd));
//
//            // Chuyền đuốc qua 3 tầng tối ưu
//            LOG.info("   -> Chạy Tier 1 (Entry/AI)...");
//            BotTradingConfig bestEntry = WFOTier1EntryRunner.optimize(current, trainEnd, rollingConfig);
//
//            LOG.info("   -> Chạy Tier 2 (Risk/Trailing/DCA)...");
//            BotTradingConfig bestRisk = WFOTier2RiskRunner.optimize(current, trainEnd, bestEntry);
//
//            LOG.info("   -> Chạy Tier 3 (Budget/Position Sizing)...");
//            BotTradingConfig finalIS = WFOTier3BudgetRunner.optimize(current, trainEnd, bestRisk);
//
//            // Bước chốt: Kiểm chứng OOS trên tập dữ liệu tương lai gần
//            float oosScore = WFOBacktestEngine.run(trainEnd, testEnd, finalIS);
//
//            // 2. IN LOG KẾT QUẢ REAL-TIME RÕ RÀNG ĐỂ NGƯỜI DÙNG XEM NGAY
//            LOG.info("=========================================================");
//            LOG.info("🏆 KẾT QUẢ TẠM THỜI WINDOW {}/{} ({} -> {})", currentWindow, totalWindows, Utils.normalizeDateYYYYMMDD(trainEnd), Utils.normalizeDateYYYYMMDD(testEnd));
//            LOG.info("💰 ĐIỂM THỰC CHIẾN (OOS SCORE): {}", oosScore);
//            LOG.info("⚙️ THAM SỐ GỢI Ý ĐỂ TEST NGAY:");
//            LOG.info("   - Lọc AI (Threshold/15m/Up/Down): [{}, {}, {}, {}]", finalIS.aiPredictRateMaxThreshold, finalIS.aiPredictRateDown15m, finalIS.aiPredictRateUpAvg, finalIS.aiPredictRateDownAvg);
//            LOG.info("   - Risk Base: {}", finalIS.rateProfitStopMarket);
//            LOG.info("   - Budget (Orders/Ratio1/Div1): [{}, {}, {}]", finalIS.numberOrderBudget, finalIS.budgetMarginRatio1, finalIS.budgetDivider1);
//            LOG.info("=========================================================");
//
//            // 3. TỰ ĐỘNG XUẤT RA FILE (CHỈ XUẤT NẾU LÃI OOS > 0 ĐỂ LỌC RÁC)
//            if (oosScore > 0) {
//                exportProductionConfig(finalIS, testEnd, oosScore);
//            }
//
//            // Trượt cửa sổ và dùng tham số mới làm gốc cho kỳ sau
//            current += oosStep;
//            rollingConfig = finalIS;
//        }
//
//        LOG.info("🎉 HỆ THỐNG WFO ĐÃ HOÀN TẤT 100% QUÁ TRÌNH TỐI ƯU!");
//    }
//
//    /**
//     * Tự động lưu cấu hình ra file để mang đi trade thực tế ngay lập tức
//     */
//    private void exportProductionConfig(BotTradingConfig config, long validDate, float score) {
//        String fileName = "wfo_production_params_" + Utils.normalizeDateYYYYMMDD(validDate) + ".properties";
//        try (PrintWriter writer = new PrintWriter(new FileWriter(fileName))) {
//            writer.println("# AI GENERATED CONFIG FOR PRODUCTION");
//            writer.println("# Valid tested date: " + Utils.normalizeDateYYYYMMDD(validDate));
//            writer.println("# OOS Score (Profit Velocity): " + score);
//
//            // AI
//            writer.println("aiPredictRateMaxThreshold=" + config.aiPredictRateMaxThreshold);
//            writer.println("aiPredictRateDown15m=" + config.aiPredictRateDown15m);
//            writer.println("aiPredictRateUpAvg=" + config.aiPredictRateUpAvg);
//            writer.println("aiPredictRateDownAvg=" + config.aiPredictRateDownAvg);
//
//            // Risk
//            writer.println("rateProfitStopMarket=" + config.rateProfitStopMarket);
//
//            // Budget
//            writer.println("numberOrderBudget=" + config.numberOrderBudget);
//            writer.println("budgetMarginRatio1=" + config.budgetMarginRatio1);
//            writer.println("budgetDivider1=" + config.budgetDivider1);
//            writer.println("budgetMarginRatio2=" + config.budgetMarginRatio2);
//            writer.println("budgetDivider2=" + config.budgetDivider2);
//
//            LOG.info("💾 Đã tự động xuất file cấu hình: {}", fileName);
//        } catch (Exception e) {
//            LOG.error("❌ Lỗi xuất file config: {}", e.getMessage());
//        }
//    }
//}