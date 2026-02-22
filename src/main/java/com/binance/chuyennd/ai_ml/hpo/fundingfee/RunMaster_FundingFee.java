package com.binance.chuyennd.ai_ml.hpo.fundingfee;

import com.binance.chuyennd.ai_ml.hpo.distributed.DistributedQueueManager;
import io.jenetics.*;
import io.jenetics.engine.Engine;
import io.jenetics.engine.EvolutionResult;
import io.jenetics.util.Factory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicLong;

public class RunMaster_FundingFee {
    private static final Logger LOG = LoggerFactory.getLogger(RunMaster_FundingFee.class);

    private static final int POPULATION_SIZE = 50;
    private static final int GENERATIONS = 100;
    private static final AtomicLong testCounter = new AtomicLong(0);

    public static void main(String[] args) {
        LOG.info("=== 👑 MASTER NODE: KHỞI TẠO JENETICS VÀ PHÂN PHỐI TASK ===");

        Factory<Genotype<DoubleGene>> gtf = Genotype.of(
                DoubleChromosome.of(-0.04, -0.015),
                DoubleChromosome.of(-0.05, -0.02),
                DoubleChromosome.of(0.004, 0.012),
                DoubleChromosome.of(-0.012, -0.004),
                DoubleChromosome.of(0.1, 0.5)
        );

        Engine<DoubleGene, Double> engine = Engine.builder(RunMaster_FundingFee::evalAndPushToQueue, gtf)
                .populationSize(POPULATION_SIZE)
                .survivorsSelector(new TournamentSelector<>(3))
                .offspringSelector(new RouletteWheelSelector<>())
                .alterers(new Mutator<>(0.2), new MeanAlterer<>(0.6))
                // 🔥 QUAN TRỌNG: Mở 100 luồng để Master có thể đẩy đồng loạt 50 Task vào Queue và chờ cùng lúc
                .executor(Executors.newFixedThreadPool(POPULATION_SIZE * 2))
                .build();

        EvolutionResult<DoubleGene, Double> bestResult = engine.stream()
                .limit(GENERATIONS)
                .peek(result -> LOG.info(">>> 🏆 Gen {} Xong! Best PnL: {}", result.generation(), result.bestFitness()))
                .collect(EvolutionResult.toBestEvolutionResult());

        LOG.info("🎉 TỐI ƯU HÓA HOÀN TẤT. Lợi nhuận MAX: {}", bestResult.bestFitness());
    }

    private static Double evalAndPushToQueue(Genotype<DoubleGene> gt) {
        long c = testCounter.incrementAndGet();

        double pMinTrade = gt.get(0).gene().doubleValue();
        double pMinFull = gt.get(1).gene().doubleValue();
        double pUpAvg = gt.get(2).gene().doubleValue();
        double pDownAvg = gt.get(3).gene().doubleValue();
        double pFundingPred = gt.get(4).gene().doubleValue();

        if (pMinFull > pMinTrade) return -10000.0;

        // Tạo Genome Key và Chuỗi Params
        String genomeKey = String.format(java.util.Locale.US, "G_%.5f_%.5f_%.5f_%.5f_%.5f",
                pMinTrade, pMinFull, pUpAvg, pDownAvg, pFundingPred);
        String paramsStr = String.format(java.util.Locale.US, "%.5f,%.5f,%.5f,%.5f,%.5f",
                pMinTrade, pMinFull, pUpAvg, pDownAvg, pFundingPred);

        // Đẩy vào Queue
        DistributedQueueManager.pushTask(genomeKey, paramsStr);
        LOG.info("📦 Đã đẩy Task #{} lên Queue: {}", c, genomeKey);

        // Chờ Worker báo cáo kết quả
        Double score = DistributedQueueManager.waitForResult(genomeKey);
        LOG.info("✅ Nhận kết quả Task #{}: Score = {}", c, score);

        return score;
    }
}