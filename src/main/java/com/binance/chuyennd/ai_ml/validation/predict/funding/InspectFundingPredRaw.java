package com.binance.chuyennd.ai_ml.validation.predict.funding;

import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.ScanPolicy;
import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.nio.ByteBuffer;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * XÁC MINH pred[0] LÀ LỚP NÀO — đọc raw funding pred, in ĐỦ 5 prob (không chỉ pred[0]).
 *
 * Lý do: nhánh EARLY (lá chắn chính, 96.5% reject) dùng symbolPred = pred[0]. Phải chắc pred[0]
 * là P(fail) chứ không phải lớp khác. Suy luận code có thể sót (ONNX đổi thứ tự ngầm) => đọc số thật.
 *
 * Đối chiếu phân bố label6 lúc train: [fail≈34%, 72H≈16%, 24H≈29%, 4H≈19%, 15M≈1.6%].
 *   - Nếu prob[0] TB ~0.30-0.40, dao động rộng  => prob[0] = P(fail). pred[0] ĐÚNG là P(fail). ✅
 *   - Nếu prob[0] TB ~0.01-0.02                  => prob[0] = P(lớp 15M). CHIỀU LẬT. 🔴 báo động.
 *   - So vector prob TB với phân bố lớp trên để biết từng vị trí ứng lớp nào.
 *
 * Chạy trên 226. Chỉ đọc.
 */
public class InspectFundingPredRaw {

    private static final Logger LOG = LoggerFactory.getLogger(InspectFundingPredRaw.class);
    private static final int SAMPLE_LIMIT = 2000;   // số record lấy mẫu
    private static final int PRINT_FIRST = 10;      // in chi tiết vài record đầu

    public static void main(String[] args) {
        new InspectFundingPredRaw().run();
    }

    public void run() {
        AtomicInteger seen = new AtomicInteger(0);
        AtomicInteger printed = new AtomicInteger(0);

        // tổng theo từng vị trí prob (tối đa 5) + đếm để tính trung bình
        double[] sum = new double[8];
        long[] cnt = new long[8];
        int[] maxLen = {0};

        try {
            ScanPolicy sp = new ScanPolicy();
            sp.concurrentNodes = true;

            DataManagerAerospikeFloatSim.getClient226().scanAll(sp,
                    Configs.AEROSPIKE_NAMESPACE,
                    Configs.AEROSPIKE_SET_NAME_FUNDING_PRED,
                    (Key key, Record record) -> {
                        if (seen.get() >= SAMPLE_LIMIT) return;
                        try {
                            byte[] compressed = (byte[]) record.getValue("data");
                            if (compressed == null) return;
                            byte[] raw = Snappy.uncompress(compressed);
                            ByteBuffer buf = ByteBuffer.wrap(raw);

                            int mapSize = buf.getInt();
                            for (int i = 0; i < mapSize; i++) {
                                short symbolId = buf.getShort();
                                int arrLen = buf.getInt();
                                float[] probs = new float[arrLen];
                                for (int j = 0; j < arrLen; j++) probs[j] = buf.getFloat();

                                if (arrLen > maxLen[0]) maxLen[0] = arrLen;
                                for (int j = 0; j < arrLen && j < sum.length; j++) {
                                    sum[j] += probs[j];
                                    cnt[j]++;
                                }
                                seen.incrementAndGet();

                                if (printed.get() < PRINT_FIRST) {
                                    StringBuilder sb = new StringBuilder();
                                    float s = 0;
                                    for (int j = 0; j < arrLen; j++) {
                                        sb.append(String.format("%.4f ", probs[j]));
                                        s += probs[j];
                                    }
                                    LOG.info("   sym={} len={} probs=[{}] tổng={}",
                                            symbolId, arrLen, sb.toString().trim(), String.format("%.4f", s));
                                    printed.incrementAndGet();
                                }
                            }
                        } catch (Exception e) {
                            // bỏ record lỗi
                        }
                    }, "data");
        } catch (Exception e) {
            LOG.error("Scan lỗi", e);
        }

        LOG.info("================ TRUNG BÌNH TỪNG VỊ TRÍ PROB (n={} entry, len={}) ================",
                seen.get(), maxLen[0]);
        for (int j = 0; j < maxLen[0] && j < sum.length; j++) {
            double avg = cnt[j] > 0 ? sum[j] / cnt[j] : 0;
            LOG.info("   prob[{}] TB = {}", j, String.format("%.4f", avg));
        }
        LOG.info("📌 Đối chiếu phân bố lớp train [fail~34%, 72H~16%, 24H~29%, 4H~19%, 15M~1.6%]:");
        LOG.info("   - prob[0] TB ~0.30-0.40 => prob[0]=P(fail), symbolPred ĐÚNG là P(fail). ✅");
        LOG.info("   - prob[0] TB ~0.01-0.02 => prob[0]=P(15M), CHIỀU LẬT — filter EARLY sai ngược. 🔴");
        LOG.info("   - Vị trí nào TB ~0.015 chính là lớp 15M (hiếm nhất) => suy ra thứ tự lớp thực tế.");
    }
}