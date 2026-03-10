package com.binance.chuyennd.ai_ml.wfo.dca_trailing;

import com.binance.chuyennd.ai_ml.wfo.WFOBacktestEngine;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import io.jenetics.*;
import io.jenetics.engine.*;
import io.jenetics.util.Factory;

public class WFOTier2RiskRunner {
    public static BotTradingConfig optimize(long start, long end, BotTradingConfig bestEntry) {
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(0.008, 0.025), // rateProfitStopMarket [cite: 809]
                DoubleChromosome.of(0.04, 0.08),    // tsRateHigh [cite: 809]
                DoubleChromosome.of(-0.15, -0.05)   // dcaRateLossBigDown [cite: 810]
        );

        Engine<DoubleGene, Double> engine = Engine.builder(gt -> {
            BotTradingConfig config = bestEntry.clone();
            config.rateProfitStopMarket = gt.get(0).gene().doubleValue();
            config.tsRateHigh = gt.get(1).gene().doubleValue();
            config.dcaRateLossBigDown = gt.get(2).gene().doubleValue();
            return WFOBacktestEngine.run(start, end, config);
        }, gtf).maximizing().build();

        Genotype<DoubleGene> best = engine.stream().limit(25)
                .collect(EvolutionResult.toBestEvolutionResult()).bestPhenotype().genotype();

        BotTradingConfig res = bestEntry.clone();
        res.rateProfitStopMarket = best.get(0).gene().doubleValue();
        res.tsRateHigh = best.get(1).gene().doubleValue();
        res.dcaRateLossBigDown = best.get(2).gene().doubleValue();
        return res;
    }
}