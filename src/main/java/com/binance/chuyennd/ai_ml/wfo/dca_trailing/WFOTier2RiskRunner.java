package com.binance.chuyennd.ai_ml.wfo.dca_trailing;

import com.binance.chuyennd.ai_ml.wfo.WFOBacktestEngine;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import io.jenetics.*;
import io.jenetics.engine.*;
import io.jenetics.util.DoubleRange;
import io.jenetics.util.Factory;

public class WFOTier2RiskRunner {
    public static BotTradingConfig optimize(long start, long end, BotTradingConfig bestEntry) {
        // Tối ưu 16 tham số chốt lời, dời SL và DCA
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                // --- Nhóm Trailing Stop ---
                DoubleChromosome.of(DoubleRange.of(0.005, 0.03)), // 0: rateProfitStopMarket
                DoubleChromosome.of(DoubleRange.of(0.01, 0.03)),  // 1: tsVolHighThres
                DoubleChromosome.of(DoubleRange.of(0.03, 0.08)),  // 2: tsRateHigh
                DoubleChromosome.of(DoubleRange.of(0.005, 0.015)),// 3: tsVolMedThres
                DoubleChromosome.of(DoubleRange.of(0.02, 0.06)),  // 4: tsRateMed
                DoubleChromosome.of(DoubleRange.of(0.001, 0.005)),// 5: tsVolLowThres
                DoubleChromosome.of(DoubleRange.of(0.005, 0.03)), // 6: tsRateLow

                // --- Nhóm DCA Loss Thresholds ---
                DoubleChromosome.of(DoubleRange.of(-0.10, -0.02)),// 7: dcaRateLossBigDown
                DoubleChromosome.of(DoubleRange.of(-0.15, -0.05)),// 8: dcaRateLossMediumDown
                DoubleChromosome.of(DoubleRange.of(-0.25, -0.10)),// 9: dcaRateLossMediumUp
                DoubleChromosome.of(DoubleRange.of(-0.30, -0.15)),// 10: dcaRateLossSmallDown
                DoubleChromosome.of(DoubleRange.of(-0.50, -0.30)),// 11: dcaRateLossNull

                // --- Nhóm DCA Margin Ratios ---
                DoubleChromosome.of(DoubleRange.of(-0.80, -0.40)),// 12: dcaMarginRate1_5
                DoubleChromosome.of(DoubleRange.of(-0.90, -0.50)),// 13: dcaMarginRate2_0
                DoubleChromosome.of(DoubleRange.of(-0.95, -0.70)),// 14: dcaMarginRate2_5
                DoubleChromosome.of(DoubleRange.of(-0.99, -0.80)) // 15: dcaMarginRate3_0
        );

        Engine<DoubleGene, Float> engine = Engine.builder(gt -> {
                    BotTradingConfig config = bestEntry.clone();

                    config.rateProfitStopMarket = gt.get(0).gene().floatValue();

                    config.dcaRateLossBigDown = gt.get(7).gene().floatValue();
                    config.dcaRateLossMediumDown = gt.get(8).gene().floatValue();
                    config.dcaRateLossMediumUp = gt.get(9).gene().floatValue();
                    config.dcaRateLossSmallDown = gt.get(10).gene().floatValue();
                    config.dcaRateLossNull = gt.get(11).gene().floatValue();

                    config.dcaMarginRate1_5 = gt.get(12).gene().floatValue();
                    config.dcaMarginRate2_0 = gt.get(13).gene().floatValue();
                    config.dcaMarginRate2_5 = gt.get(14).gene().floatValue();
                    config.dcaMarginRate3_0 = gt.get(15).gene().floatValue();

                    return WFOBacktestEngine.run(start, end, config);
                }, gtf)
                .populationSize(10) // THÊM DÒNG NÀY: Chỉ tạo 10 cá thể
                .maximizing()
                .executor(Runnable::run)
                .build();

        Genotype<DoubleGene> best = engine.stream().limit(3)
                .collect(EvolutionResult.toBestEvolutionResult()).bestPhenotype().genotype();

        BotTradingConfig res = bestEntry.clone();
        res.rateProfitStopMarket = best.get(0).gene().floatValue();

        res.dcaRateLossBigDown = best.get(7).gene().floatValue();
        res.dcaRateLossMediumDown = best.get(8).gene().floatValue();
        res.dcaRateLossMediumUp = best.get(9).gene().floatValue();
        res.dcaRateLossSmallDown = best.get(10).gene().floatValue();
        res.dcaRateLossNull = best.get(11).gene().floatValue();

        res.dcaMarginRate1_5 = best.get(12).gene().floatValue();
        res.dcaMarginRate2_0 = best.get(13).gene().floatValue();
        res.dcaMarginRate2_5 = best.get(14).gene().floatValue();
        res.dcaMarginRate3_0 = best.get(15).gene().floatValue();

        return res;
    }
}