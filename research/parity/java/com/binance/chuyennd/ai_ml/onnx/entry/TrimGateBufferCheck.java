package com.binance.chuyennd.ai_ml.onnx.entry;

/**
 * TAM (ngoai src/main, KHONG commit vao src): nap file GRR1 bang CHINH code live
 * GateRatioPersist.load + GateRatioBuffer.bulkAdd/addAndQuery (cung package => goi duoc lop package-private)
 * va in n, firstTs, lastTs, q tai moc gio hEval — de so voi research/parity/trim_gate_buffer.py.
 * Usage: java -cp out:jar com.binance.chuyennd.ai_ml.onnx.entry.TrimGateBufferCheck FILE PCT DAYS HEVAL_MS
 */
public final class TrimGateBufferCheck {
    public static void main(String[] a) throws Exception {
        String path = a[0];
        float pct = Float.parseFloat(a[1]);
        int days = Integer.parseInt(a[2]);
        long hEval = Long.parseLong(a[3]);
        long minTs = hEval - (long) days * GateRatioBuffer.DAY;   // = now - days*DAY trong loadPersistedAndSeed
        GateRatioPersist.Records rec = GateRatioPersist.load(path, minTs);
        GateRatioBuffer b = new GateRatioBuffer();
        b.bulkAdd(rec.ts, rec.r);
        int sizeBefore = b.size();
        float q = b.addAndQuery(hEval, 0f, pct, days, 0.008f);   // q tinh TRUOC khi nap mau gia (causal)
        System.out.println("JAVA file=" + path + " n=" + rec.ts.length + " size=" + sizeBefore
                + " firstTs=" + b.firstTs() + " lastTs=" + (rec.ts.length > 0 ? rec.ts[rec.ts.length - 1] : -1)
                + " hEval=" + hEval + " q=" + q + " qbits=" + Float.floatToIntBits(q)
                + " fallback=" + (b.nBeforeFirst() > 0));
    }
}
