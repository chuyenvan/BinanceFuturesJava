package com.binance.chuyennd.ai_ml.features.export.gate;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * TASK-121 — Self-test main-based (repo KHÔNG dùng JUnit; theo pattern Task029ConcurrencyCheck…).
 * Chỉ test PARSE + CHUNK + validate header + idempotent-dedup; Aerospike được STUB bằng {@link RecordingSink}
 * nên KHÔNG cần kết nối gì. Chạy:
 * <pre>java -cp target/classes com.binance.chuyennd.ai_ml.features.export.gate.LoadWfoGatePredToolTest</pre>
 * In "PASS x/y", exit 0 nếu toàn bộ PASS, ngược lại exit 1.
 */
public class LoadWfoGatePredToolTest {

    static int pass = 0, total = 0;

    /** Sink giả: ghi lại kích thước từng batch để kiểm chunk logic (thay Aerospike). */
    static class RecordingSink implements LoadWfoGatePredTool.BatchSink {
        final List<Integer> batchSizes = new ArrayList<>();
        int totalRecords = 0;
        String lastSet;
        @Override public void write(String setName, Map<Long, AiPredictionData> batch) {
            lastSet = setName;
            batchSizes.add(batch.size());
            totalRecords += batch.size();
        }
    }

    public static void main(String[] args) throws Exception {
        // 1) validateHeader — đúng
        check("header đúng không ném", () -> {
            LoadWfoGatePredTool.validateHeader("timestamp,predReturn15M,predRisk4H");
            return true;
        });
        // 2) validateHeader — sai → ném
        check("header sai phải ném", () -> throwsEx(() ->
                LoadWfoGatePredTool.validateHeader("ts,a,b")));
        // 3) validateHeader — có BOM vẫn chấp nhận
        check("header có BOM chấp nhận", () -> {
            LoadWfoGatePredTool.validateHeader("﻿timestamp,predReturn15M,predRisk4H");
            return true;
        });
        // 4) parseLine — đúng
        check("parseLine đúng giá trị", () -> {
            AiPredictionData d = LoadWfoGatePredTool.parseLine("1609459200000,0.01234567,-0.05000000");
            return d.timestamp == 1609459200000L
                    && Math.abs(d.predReturn15M - 0.01234567f) < 1e-7
                    && Math.abs(d.predRisk4H - (-0.05f)) < 1e-6;
        });
        // 5) parseLine — thiếu cột → ném
        check("parseLine thiếu cột ném", () -> throwsEx(() ->
                LoadWfoGatePredTool.parseLine("123,0.1")));
        // 6) parseLine — ts<=0 → ném
        check("parseLine ts<=0 ném", () -> throwsEx(() ->
                LoadWfoGatePredTool.parseLine("0,0.1,0.2")));
        // 7) parseLine — số sai → ném
        check("parseLine số sai ném", () -> throwsEx(() ->
                LoadWfoGatePredTool.parseLine("123,abc,0.2")));

        // 8) chunk logic: 10 dòng, chunk=4 → batch [4,4,2], total=10
        File csv = writeCsv(10, false);
        RecordingSink sink = new RecordingSink();
        long tot = LoadWfoGatePredTool.load(csv, "test_set", 4, sink);
        check("chunk total=10", () -> tot == 10);
        check("chunk batches = [4,4,2]", () -> sink.batchSizes.equals(java.util.Arrays.asList(4, 4, 2)));
        check("sink nhận đúng setName", () -> "test_set".equals(sink.lastSet));

        // 9) idempotent-dedup: cùng timestamp trong 1 batch → collapse (map key=ts)
        File dup = writeCsvWithDup();
        RecordingSink sink2 = new RecordingSink();
        long totDup = LoadWfoGatePredTool.load(dup, "s", 100, sink2);
        // 3 dòng nhưng 2 dòng cùng ts → map còn 2 record
        check("dedup: đọc 3 dòng nhưng ghi 2 record", () -> totDup == 3 && sink2.totalRecords == 2);

        // 10) dòng trống bị bỏ qua
        File blank = writeCsvWithBlankLine();
        RecordingSink sink3 = new RecordingSink();
        long totBlank = LoadWfoGatePredTool.load(blank, "s", 100, sink3);
        check("bỏ qua dòng trống (2 record)", () -> totBlank == 2 && sink3.totalRecords == 2);

        // 11) dòng hỏng → ném (exit 1 ở main thật)
        File bad = writeCsvBadRow();
        check("dòng hỏng phải ném", () -> throwsEx(() ->
                LoadWfoGatePredTool.load(bad, "s", 100, new RecordingSink())));

        System.out.printf("%n==== LoadWfoGatePredToolTest: PASS %d/%d ====%n", pass, total);
        System.exit(pass == total ? 0 : 1);
    }

    // ===== helpers =====
    interface Body { boolean run() throws Exception; }
    interface Act { void run() throws Exception; }

    static void check(String name, Body b) {
        total++;
        try {
            if (b.run()) { pass++; System.out.println("✅ " + name); }
            else System.out.println("❌ " + name + " (assert false)");
        } catch (Exception e) {
            System.out.println("❌ " + name + " (exception: " + e.getMessage() + ")");
        }
    }

    static boolean throwsEx(Act a) {
        try { a.run(); return false; } catch (Exception e) { return true; }
    }

    static File writeCsv(int rows, boolean unused) throws Exception {
        File f = File.createTempFile("wfo_gate_pred_test", ".csv");
        f.deleteOnExit();
        try (BufferedWriter w = new BufferedWriter(new FileWriter(f))) {
            w.write(LoadWfoGatePredTool.EXPECTED_HEADER); w.newLine();
            long base = 1609459200000L; // 2021-01-01
            for (int i = 0; i < rows; i++) {
                w.write((base + i * 60_000L) + ",0.0001" + i + ",-0.0002" + i);
                w.newLine();
            }
        }
        return f;
    }

    static File writeCsvWithDup() throws Exception {
        File f = File.createTempFile("wfo_gate_pred_dup", ".csv");
        f.deleteOnExit();
        try (BufferedWriter w = new BufferedWriter(new FileWriter(f))) {
            w.write(LoadWfoGatePredTool.EXPECTED_HEADER); w.newLine();
            w.write("1609459200000,0.01,-0.01"); w.newLine();
            w.write("1609459260000,0.02,-0.02"); w.newLine();
            w.write("1609459200000,0.99,-0.99"); w.newLine(); // cùng ts dòng 1 → ghi đè
        }
        return f;
    }

    static File writeCsvWithBlankLine() throws Exception {
        File f = File.createTempFile("wfo_gate_pred_blank", ".csv");
        f.deleteOnExit();
        try (BufferedWriter w = new BufferedWriter(new FileWriter(f))) {
            w.write(LoadWfoGatePredTool.EXPECTED_HEADER); w.newLine();
            w.write("1609459200000,0.01,-0.01"); w.newLine();
            w.write(""); w.newLine();
            w.write("1609459260000,0.02,-0.02"); w.newLine();
        }
        return f;
    }

    static File writeCsvBadRow() throws Exception {
        File f = File.createTempFile("wfo_gate_pred_bad", ".csv");
        f.deleteOnExit();
        try (BufferedWriter w = new BufferedWriter(new FileWriter(f))) {
            w.write(LoadWfoGatePredTool.EXPECTED_HEADER); w.newLine();
            w.write("1609459200000,0.01,-0.01"); w.newLine();
            w.write("khong-phai-so,0.02,-0.02"); w.newLine();
        }
        return f;
    }
}
