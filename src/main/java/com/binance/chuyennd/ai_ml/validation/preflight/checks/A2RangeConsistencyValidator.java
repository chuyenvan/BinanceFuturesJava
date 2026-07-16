package com.binance.chuyennd.ai_ml.validation.preflight.checks;

import com.binance.chuyennd.ai_ml.validation.preflight.CheckId;
import com.binance.chuyennd.ai_ml.validation.preflight.DataValidator;
import com.binance.chuyennd.ai_ml.validation.preflight.PreflightContext;
import com.binance.chuyennd.ai_ml.validation.preflight.ValidationResult;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedInputStream;
import java.io.DataInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.util.ArrayList;
import java.util.Calendar;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * A2 — Chặn "lệch RANGE giữa các nguồn" (market tới 2026-05 nhưng pred chỉ tới 2025-10 → cửa sổ WFO cuối
 * thiếu pred; {@code DATA_VALIDATION_FRAMEWORK §2 A2}).
 *
 * <p><b>Cơ chế:</b> tính [min,max] ts của từng nguồn WFO thực dùng (đọc file bin trong {@code ctx.wfoDataDir()}:
 * {@code market.bin} / {@code pred.bin}=gate / {@code funding.bin}=selector) → GIAO = [max(min), min(max)] →
 * kiểm GIAO có phủ TRỌN mọi cửa sổ WFO không. Cửa sổ nào [trainStart, oosEnd] không nằm gọn trong giao ⇒ FAIL
 * (A2 = BLOCK).</p>
 *
 * <p><b>WRAP {@code ValidateMarketPredictConsistency}:</b> tool cũ đối soát GIÁ TRỊ pred (recompute vs Aerospike)
 * — thuộc loại B2, KHÔNG tính range. Phần range là GAP (roadmap ghi A2 = WRAP+GAP); ở đây tự tính min/max ts từ
 * bin dataset (nguồn WFO thật) — chính xác hơn suy từ tool giá-trị. {@code market.bin/pred.bin/funding.bin} là
 * 3 khối WFO nạp; {@code selector} = {@code funding} trong dataflow hiện tại (WFO_DATAFLOW §4).</p>
 *
 * <p><b>Cửa sổ WFO</b> tái dựng ĐÚNG {@code StrategyWfoTask.buildWindows} (DATA_START=20210101, DATA_END=20260601,
 * train 12m + OOS 3m, trượt 3m, mốc +7h). So số cửa sổ dựng được với {@code ctx.expected().expectedFolds()}.</p>
 *
 * <p><b>TODO-verify-trên-data-thật:</b> (1) giữ hằng {@link #DATA_START}/{@link #DATA_END}/{@link #TRAIN_MONTHS}/
 * {@link #OOS_MONTHS} ĐỒNG BỘ với {@code StrategyWfoTask} (nếu task đổi env WFO_TRAIN_MONTHS/OOS_MONTHS thì A2 đọc
 * cùng env); (2) xác nhận {@code selector==funding} còn đúng nếu tách selector khỏi funding; (3) train cũng cần
 * pred phủ (replay warmup) — check dùng [trainStart, oosEnd]; nếu chỉ cần OOS, đổi biên.</p>
 */
public final class A2RangeConsistencyValidator implements DataValidator {

    private static final Logger LOG = LoggerFactory.getLogger(A2RangeConsistencyValidator.class);

    // Đồng bộ StrategyWfoTask (khớp WFORunner).
    private static final String DATA_START = "20210101";
    private static final String DATA_END = "20260601";
    private static final int TRAIN_MONTHS = 12;
    private static final int OOS_MONTHS = 3;

    private static final String F_MARKET = "market.bin";
    private static final String F_PRED = "pred.bin";
    private static final String F_FUNDING = "funding.bin";
    private static final int MAX_LIST = 30;

    @Override
    public CheckId id() {
        return CheckId.A2;
    }

    /**
     * Tính giao range 3 nguồn, kiểm phủ mọi cửa sổ WFO.
     *
     * @param ctx cần {@link PreflightContext#wfoDataDir()} có 3 file bin
     * @return FAIL (BLOCK) nếu giao không phủ cửa sổ nào; PASS kèm metrics
     * @throws IllegalStateException nếu thiếu wfoDataDir / file bin (lỗi hạ tầng → NEEDS_HUMAN)
     * @throws Exception nếu lỗi đọc bin
     */
    @Override
    public ValidationResult validate(PreflightContext ctx) throws Exception {
        String dir = ctx.wfoDataDir();
        if (dir == null || dir.trim().isEmpty()) {
            throw new IllegalStateException("A2: thieu wfoDataDir (WFO_DATA_DIR) — khong doc duoc bin dataset.");
        }
        long[] mkt = rangeMarketOrPred(new File(dir, F_MARKET), 3);   // market: ts + 3 float
        long[] gate = rangeMarketOrPred(new File(dir, F_PRED), 2);    // gate pred: ts + 2 float
        long[] fnd = rangeFunding(new File(dir, F_FUNDING));          // funding: ts + [len]+len*long

        long lo = Math.max(mkt[0], Math.max(gate[0], fnd[0]));
        long hi = Math.min(mkt[1], Math.min(gate[1], fnd[1]));

        Map<String, Object> metrics = new LinkedHashMap<>();
        metrics.put("market", human(mkt));
        metrics.put("gate", human(gate));
        metrics.put("funding", human(fnd));
        metrics.put("intersection", (lo <= hi)
                ? Utils.normalizeDateYYYYMMDD(lo) + " -> " + Utils.normalizeDateYYYYMMDD(hi)
                : "RONG (lo>hi)");

        List<long[]> windows = buildWindows();
        int expectedFolds = ctx.expected().expectedFolds();
        metrics.put("windowsBuilt", windows.size());
        metrics.put("expectedFolds", expectedFolds);

        if (lo > hi) {
            return ValidationResult.fail(id(),
                    "Giao range 3 nguon RONG (khong co khoang thoi gian phu chung) — lech range nghiem trong.",
                    metrics);
        }

        List<String> uncovered = new ArrayList<>();
        for (int i = 0; i < windows.size(); i++) {
            long[] w = windows.get(i); // {trainStart, trainEnd, oosStart, oosEnd}
            long need0 = w[0], need1 = w[3];
            if (need0 < lo || need1 > hi) {
                if (uncovered.size() < MAX_LIST) {
                    uncovered.add("w" + i + "[" + Utils.normalizeDateYYYYMMDD(need0) + ".."
                            + Utils.normalizeDateYYYYMMDD(need1) + "]");
                }
            }
        }
        metrics.put("windowsCovered", windows.size() - uncovered.size());
        metrics.put("windowsUncovered", uncovered);

        if (windows.size() != expectedFolds) {
            metrics.put("warnFoldMismatch",
                    "so cua so dung duoc (" + windows.size() + ") != expectedFolds (" + expectedFolds + ")");
        }

        if (!uncovered.isEmpty()) {
            return ValidationResult.fail(id(),
                    uncovered.size() + "/" + windows.size() + " cua so WFO khong duoc giao range phu tron: "
                            + uncovered, metrics);
        }
        return ValidationResult.pass(id(),
                "Giao range 3 nguon phu tron " + windows.size() + " cua so WFO.", metrics);
    }

    /** Đọc min/max ts của file dạng [count][ts:long][nFloat float] (market/pred). */
    private long[] rangeMarketOrPred(File f, int nFloat) throws Exception {
        if (!f.isFile()) throw new IllegalStateException("A2: thieu file " + f.getAbsolutePath());
        long min = Long.MAX_VALUE, max = Long.MIN_VALUE;
        int skip = nFloat * 4;
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
            int n = in.readInt();
            for (int i = 0; i < n; i++) {
                long ts = in.readLong();
                if (ts < min) min = ts;
                if (ts > max) max = ts;
                skipFully(in, skip);
            }
        }
        if (min == Long.MAX_VALUE) throw new IllegalStateException("A2: " + f.getName() + " rong (0 record).");
        return new long[]{min, max};
    }

    /** Đọc min/max ts của funding.bin dạng [count][ts:long][len:int][len x long]. */
    private long[] rangeFunding(File f) throws Exception {
        if (!f.isFile()) throw new IllegalStateException("A2: thieu file " + f.getAbsolutePath());
        long min = Long.MAX_VALUE, max = Long.MIN_VALUE;
        try (DataInputStream in = new DataInputStream(new BufferedInputStream(new FileInputStream(f), 1 << 20))) {
            int n = in.readInt();
            for (int i = 0; i < n; i++) {
                long ts = in.readLong();
                if (ts < min) min = ts;
                if (ts > max) max = ts;
                int len = in.readInt();
                skipFully(in, (long) len * 8);
            }
        }
        if (min == Long.MAX_VALUE) throw new IllegalStateException("A2: " + f.getName() + " rong (0 moc).");
        return new long[]{min, max};
    }

    private static void skipFully(DataInputStream in, long n) throws java.io.IOException {
        long remain = n;
        while (remain > 0) {
            long s = in.skip(remain);
            if (s <= 0) { // skip co the tra 0 o cuoi buffer; doc byte de ep tien
                if (in.read() < 0) throw new java.io.EOFException("A2: het file khi skip");
                remain--;
            } else {
                remain -= s;
            }
        }
    }

    /** Tái dựng cửa sổ WFO ĐÚNG {@code StrategyWfoTask.buildWindows}. Trả {trainStart,trainEnd,oosStart,oosEnd}. */
    private List<long[]> buildWindows() throws Exception {
        long dataStart = Utils.sdfFile.parse(DATA_START).getTime() + 7 * Utils.TIME_HOUR;
        long dataEnd = Utils.sdfFile.parse(DATA_END).getTime() + 7 * Utils.TIME_HOUR;
        List<long[]> wins = new ArrayList<>();
        Calendar cal = Calendar.getInstance();
        cal.setTimeInMillis(dataStart);
        cal.add(Calendar.MONTH, TRAIN_MONTHS);
        while (true) {
            long oosStart = cal.getTimeInMillis();
            Calendar oe = (Calendar) cal.clone();
            oe.add(Calendar.MONTH, OOS_MONTHS);
            long oosEnd = oe.getTimeInMillis();
            if (oosEnd > dataEnd) break;
            Calendar ts = (Calendar) cal.clone();
            ts.add(Calendar.MONTH, -TRAIN_MONTHS);
            wins.add(new long[]{ts.getTimeInMillis(), oosStart - Utils.TIME_MINUTE, oosStart, oosEnd - Utils.TIME_MINUTE});
            cal.add(Calendar.MONTH, OOS_MONTHS);
        }
        return wins;
    }

    private static String human(long[] range) {
        return Utils.normalizeDateYYYYMMDD(range[0]) + " -> " + Utils.normalizeDateYYYYMMDD(range[1]);
    }
}
