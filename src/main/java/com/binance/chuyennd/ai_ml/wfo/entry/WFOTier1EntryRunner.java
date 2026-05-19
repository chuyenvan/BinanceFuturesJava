package com.binance.chuyennd.ai_ml.wfo.entry;

import com.binance.chuyennd.ai_ml.wfo.WFOBacktestEngine;
import com.binance.chuyennd.tradecore.BotTradingConfig;
import io.jenetics.*;
import io.jenetics.engine.*;
import io.jenetics.util.DoubleRange;
import io.jenetics.util.Factory;

public class WFOTier1EntryRunner {
    public static BotTradingConfig optimize(long start, long end, BotTradingConfig base) {
        // Tối ưu 12 tham số liên quan đến tín hiệu vào lệnh và ngưỡng AI
        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                // --- Nhóm AI Filter (NỚI LỎNG) ---
                DoubleChromosome.of(DoubleRange.of(0.1, 0.5)),      // 0: maxThreshold
                DoubleChromosome.of(DoubleRange.of(-0.06, -0.005)), // 1: down15m (Cho phép sập nhẹ 0.5% cũng vào)
                DoubleChromosome.of(DoubleRange.of(0.001, 0.02)),   // 2: upAvg
                DoubleChromosome.of(DoubleRange.of(-0.03, -0.001)), // 3: downAvg

                // --- Nhóm Market Thresholds (NỚI LỎNG) ---
                DoubleChromosome.of(DoubleRange.of(0.010, 0.04)),   // 4: msUpBigThres
                DoubleChromosome.of(DoubleRange.of(-0.06, -0.005)), // 5: msDownBigAvg (Cho phép sập 0.5% tính là Big)
                DoubleChromosome.of(DoubleRange.of(0.005, 0.02)),   // 6: msUpMedThres
                DoubleChromosome.of(DoubleRange.of(-0.04, -0.003)), // 7: msDownMedAvg
                DoubleChromosome.of(DoubleRange.of(0.001, 0.01)),   // 8: msUpSmallThres
                DoubleChromosome.of(DoubleRange.of(-0.03, -0.001)), // 9: msDownSmallAvg
                DoubleChromosome.of(DoubleRange.of(-0.10, -0.02)),  // 10: msDown15mMedOnly
                DoubleChromosome.of(DoubleRange.of(-0.05, -0.005))  // 11: msDown15mSmallOnly
        );

        Engine<DoubleGene, Float> engine = Engine.builder(gt -> {
                    BotTradingConfig config = base.clone();
                    config.aiPredictRateMaxThreshold = gt.get(0).gene().floatValue();
                    config.aiPredictRateDown15m = gt.get(1).gene().floatValue();
                    config.aiPredictRateUpAvg = gt.get(2).gene().floatValue();
                    config.aiPredictRateDownAvg = gt.get(3).gene().floatValue();

                    config.msUpBigThres = gt.get(4).gene().floatValue();
                    config.msDownBigAvg = gt.get(5).gene().floatValue();
                    config.msUpMedThres = gt.get(6).gene().floatValue();
                    config.msDownMedAvg = gt.get(7).gene().floatValue();
                    config.msUpSmallThres = gt.get(8).gene().floatValue();
                    config.msDownSmallAvg = gt.get(9).gene().floatValue();
                    config.msDown15mSmallOnly = gt.get(11).gene().floatValue();

                    return WFOBacktestEngine.run(start, end, config);
                }, gtf)
                .populationSize(10) // THÊM DÒNG NÀY: Chỉ tạo 10 cá thể
                .maximizing()
                .executor(Runnable::run)
                .build();

        Genotype<DoubleGene> best = engine.stream().limit(3) // Khuyên dùng limit cao hơn vì không gian tìm kiếm lớn
                .collect(EvolutionResult.toBestEvolutionResult()).bestPhenotype().genotype();

        BotTradingConfig res = base.clone();
        res.aiPredictRateMaxThreshold = best.get(0).gene().floatValue();
        res.aiPredictRateDown15m = best.get(1).gene().floatValue();
        res.aiPredictRateUpAvg = best.get(2).gene().floatValue();
        res.aiPredictRateDownAvg = best.get(3).gene().floatValue();
        res.msUpBigThres = best.get(4).gene().floatValue();
        res.msDownBigAvg = best.get(5).gene().floatValue();
        res.msUpMedThres = best.get(6).gene().floatValue();
        res.msDownMedAvg = best.get(7).gene().floatValue();
        res.msUpSmallThres = best.get(8).gene().floatValue();
        res.msDownSmallAvg = best.get(9).gene().floatValue();
        res.msDown15mSmallOnly = best.get(11).gene().floatValue();
        return res;
    }
}