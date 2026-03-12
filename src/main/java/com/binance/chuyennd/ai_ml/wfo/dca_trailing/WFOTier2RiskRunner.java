package com.binance.chuyennd.ai_ml.wfo.dca_trailing;

import com.binance.chuyennd.ai_ml.wfo.WFOBacktestEngine;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import io.jenetics.*;
import io.jenetics.engine.*;
import io.jenetics.util.Factory;

public class WFOTier2RiskRunner {
    public static BotTradingConfig optimize(long start, long end, BotTradingConfig bestEntry) {
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(0.008, 0.025), // rateProfitStopMarket
                DoubleChromosome.of(0.04, 0.08),    // tsRateHigh
                DoubleChromosome.of(-0.15, -0.05)   // dcaRateLossBigDown
        );

        Engine<DoubleGene, Float> engine = Engine.builder(gt -> {
                    BotTradingConfig config = bestEntry.clone();
                    config.rateProfitStopMarket = gt.get(0).gene().floatValue();
                    config.tsRateHigh = gt.get(1).gene().floatValue();
                    config.dcaRateLossBigDown = gt.get(2).gene().floatValue();
                    return WFOBacktestEngine.run(start, end, config);
                }, gtf)
                .maximizing()
                .executor(Runnable::run) // ÉP CHẠY 1 LUỒNG TUẦN TỰ
                .build();

        Genotype<DoubleGene> best = engine.stream().limit(25)
                .collect(EvolutionResult.toBestEvolutionResult()).bestPhenotype().genotype();

        BotTradingConfig res = bestEntry.clone();
        res.rateProfitStopMarket = best.get(0).gene().floatValue();
        res.tsRateHigh = best.get(1).gene().floatValue();
        res.dcaRateLossBigDown = best.get(2).gene().floatValue();
        return res;
    }
}