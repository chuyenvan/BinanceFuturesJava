package com.binance.chuyennd.ai_ml.wfo.entry;

import com.binance.chuyennd.ai_ml.wfo.WFOBacktestEngine;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import io.jenetics.*;
import io.jenetics.engine.*;
import io.jenetics.util.Factory;

public class WFOTier1EntryRunner {
    public static BotTradingConfig optimize(long start, long end, BotTradingConfig base) {
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(-0.04, -0.015), // msDownSmallAvg [cite: 950]
                DoubleChromosome.of(0.004, 0.02),   // msUpSmallThres [cite: 950]
                DoubleChromosome.of(0.1, 0.4)        // aiPredictRateMaxThreshold [cite: 808]
        );

        Engine<DoubleGene, Double> engine = Engine.builder(gt -> {
            BotTradingConfig config = base.clone();
            config.msDownSmallAvg = gt.get(0).gene().doubleValue();
            config.msUpSmallThres = gt.get(1).gene().doubleValue();
            config.aiPredictRateMaxThreshold = gt.get(2).gene().doubleValue();
            return WFOBacktestEngine.run(start, end, config);
        }, gtf).maximizing().build();

        Genotype<DoubleGene> best = engine.stream().limit(30)
                .collect(EvolutionResult.toBestEvolutionResult()).bestPhenotype().genotype();

        BotTradingConfig res = base.clone();
        res.msDownSmallAvg = best.get(0).gene().doubleValue();
        res.msUpSmallThres = best.get(1).gene().doubleValue();
        res.aiPredictRateMaxThreshold = best.get(2).gene().doubleValue();
        return res;
    }
}