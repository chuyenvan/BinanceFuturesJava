package com.binance.chuyennd.ai_ml.wfo.budget;

import com.binance.chuyennd.ai_ml.wfo.WFOBacktestEngine;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import io.jenetics.*;
import io.jenetics.engine.*;
import io.jenetics.util.Factory;

public class WFOTier3BudgetRunner {

    public static BotTradingConfig optimize(long start, long end, BotTradingConfig bestRisk) {
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(40, 120),      // numberOrderBudget
                DoubleChromosome.of(0.3, 0.7),     // budgetMarginRatio1
                DoubleChromosome.of(1.2, 2.5)      // budgetDivider1
        );

        Engine<DoubleGene, Float> engine = Engine.builder(gt -> {
                    BotTradingConfig config = bestRisk.clone();
                    config.numberOrderBudget = gt.get(0).gene().intValue();
                    config.budgetMarginRatio1 = gt.get(1).gene().floatValue();
                    config.budgetDivider1 = gt.get(2).gene().floatValue();

                    return WFOBacktestEngine.run(start, end, config);
                }, gtf)
                .maximizing()
                .executor(Runnable::run) // ÉP CHẠY 1 LUỒNG TUẦN TỰ
                .build();

        Genotype<DoubleGene> best = engine.stream().limit(20)
                .collect(EvolutionResult.toBestEvolutionResult()).bestPhenotype().genotype();

        BotTradingConfig res = bestRisk.clone();
        res.numberOrderBudget = best.get(0).gene().intValue();
        res.budgetMarginRatio1 = best.get(1).gene().floatValue();
        res.budgetDivider1 = best.get(2).gene().floatValue();
        return res;
    }
}