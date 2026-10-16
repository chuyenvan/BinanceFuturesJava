package com.binance.chuyennd.ai_ml.onnx.entry;

import java.io.*;
import java.util.*;

/** Cong cu 1 lan (KHONG thuoc app): dung/ghep file persist gate theo dung dinh dang GateRatioPersist.
 *  csv2bin <in.csv ts,r> <out.bin>
 *  merge <base.bin> <live.bin> <skipFirstN> <minTsKeep> <out.bin>  : base + live[skipFirstN..] (ts>=minTsKeep)
 *  stat <file.bin> : n, firstTs, lastTs, q(pct) */
public final class GrrFix {
    static final float PCT = 0.999950829f;

    public static void main(String[] a) throws Exception {
        switch (a[0]) {
            case "csv2bin": {
                List<long[]> rows = new ArrayList<>();
                List<Float> rs = new ArrayList<>();
                try (BufferedReader br = new BufferedReader(new FileReader(a[1]))) {
                    String line = br.readLine();
                    while ((line = br.readLine()) != null) {
                        String[] p = line.split(",");
                        rows.add(new long[]{Long.parseLong(p[0])});
                        rs.add(Float.parseFloat(p[1]));
                    }
                }
                long[] ts = new long[rows.size()];
                float[] r = new float[rs.size()];
                for (int i = 0; i < ts.length; i++) { ts[i] = rows.get(i)[0]; r[i] = rs.get(i); }
                GateRatioPersist.writeFresh(a[2], ts, r);
                stat(a[2]);
                break;
            }
            case "merge": {
                GateRatioPersist.Records b = GateRatioPersist.load(a[1], Long.MIN_VALUE);
                GateRatioPersist.Records l = GateRatioPersist.load(a[2], Long.MIN_VALUE);
                if (b.droppedChunks > 0 || l.droppedChunks > 0) throw new IllegalStateException("chunk hong: base=" + b.droppedChunks + " live=" + l.droppedChunks);
                int skip = Integer.parseInt(a[3]);
                long minKeep = Long.parseLong(a[4]);
                long lastBase = b.ts[b.ts.length - 1];
                int n = 0, bad = 0;
                for (int i = skip; i < l.ts.length; i++) { if (l.ts[i] >= minKeep) n++; else bad++; }
                if (bad > 0) throw new IllegalStateException(bad + " record live sau skip co ts < minKeep -> sai skipFirstN");
                long[] ts = Arrays.copyOf(b.ts, b.ts.length + n);
                float[] r = Arrays.copyOf(b.r, b.r.length + n);
                int k = b.ts.length;
                for (int i = skip; i < l.ts.length; i++) { ts[k] = l.ts[i]; r[k] = l.r[i]; k++; }
                for (int i = 1; i < ts.length; i++) if (ts[i] < ts[i - 1]) throw new IllegalStateException("ts khong tang tai " + i);
                System.out.println("live n=" + l.ts.length + " skip=" + skip + " keep=" + n + " lastBase=" + lastBase);
                GateRatioPersist.writeFresh(a[5], ts, r);
                stat(a[5]);
                break;
            }
            case "stat": stat(a[1]); break;
            default: throw new IllegalArgumentException(a[0]);
        }
    }

    static void stat(String p) throws Exception {
        GateRatioPersist.Records x = GateRatioPersist.load(p, Long.MIN_VALUE);
        float[] s = x.r.clone();
        Arrays.sort(s);
        int m = s.length;
        int k = Math.min(m - 1, Math.max(0, (int) Math.floor((double) PCT * (m - 1))));
        System.out.printf("%s n=%d dropped=%d first=%d last=%d q=%.6f%n", p, m, x.droppedChunks, x.ts[0], x.ts[m - 1], s[k]);
    }
}
