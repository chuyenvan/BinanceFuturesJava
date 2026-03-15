package com.binance.chuyennd.ai_ml.wfo.budget;

import com.binance.chuyennd.ai_ml.wfo.WFOBacktestEngine;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import io.jenetics.*;
import io.jenetics.engine.*;
import io.jenetics.util.DoubleRange;
import io.jenetics.util.Factory;

public class WFOTier3BudgetRunner {

    public static BotTradingConfig optimize(long start, long end, BotTradingConfig bestRisk) {
        // Tối ưu 5 tham số quản trị vốn (Budget)
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(DoubleRange.of(30, 150)),  // 0: numberOrderBudget
                DoubleChromosome.of(DoubleRange.of(0.3, 0.6)), // 1: budgetMarginRatio1
                DoubleChromosome.of(DoubleRange.of(1.2, 2.5)), // 2: budgetDivider1
                DoubleChromosome.of(DoubleRange.of(0.6, 0.9)), // 3: budgetMarginRatio2
                DoubleChromosome.of(DoubleRange.of(1.2, 3.0))  // 4: budgetDivider2
        );

        Engine<DoubleGene, Float> engine = Engine.builder(gt -> {
                    BotTradingConfig config = bestRisk.clone();
                    config.numberOrderBudget = gt.get(0).gene().intValue(); // Chú ý ép kiểu int cho số lệnh
                    config.budgetMarginRatio1 = gt.get(1).gene().floatValue();
                    config.budgetDivider1 = gt.get(2).gene().floatValue();
                    config.budgetMarginRatio2 = gt.get(3).gene().floatValue();
                    config.budgetDivider2 = gt.get(4).gene().floatValue();

                    return WFOBacktestEngine.run(start, end, config);
                }, gtf)
                .populationSize(10) // THÊM DÒNG NÀY: Chỉ tạo 10 cá thể
                .maximizing()
                .executor(Runnable::run)
                .build();

        Genotype<DoubleGene> best = engine.stream().limit(3)
                .collect(EvolutionResult.toBestEvolutionResult()).bestPhenotype().genotype();

        BotTradingConfig res = bestRisk.clone();
        res.numberOrderBudget = best.get(0).gene().intValue();
        res.budgetMarginRatio1 = best.get(1).gene().floatValue();
        res.budgetDivider1 = best.get(2).gene().floatValue();
        res.budgetMarginRatio2 = best.get(3).gene().floatValue();
        res.budgetDivider2 = best.get(4).gene().floatValue();

        return res;
    }
}