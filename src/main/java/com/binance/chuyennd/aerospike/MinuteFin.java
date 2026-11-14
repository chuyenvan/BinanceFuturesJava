package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.xerial.snappy.Snappy;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.Collection;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;

/**
 * [FIN 2026-11-14, phuong an A] Bin "fin" cua record phut {@code ticker.kline_1m_opt} (key yyyyMMdd-HHmm).
 *
 * <p>fin = tap symbol (TEN NGAN, cung key cua map bin "data", vd "BTC") ma nen phut do trong bin "data" la BAN CHOT:
 * WS kline x=true (ban cuoi cua san) hoac REST da settle (nen dong &gt;= KLINE_SETTLE_MIN_AGE_SEC). Ingestor ghi bin "fin"
 * CUNG MOT lenh put voi bin "data" (nguyen tu, trong khoa stripe cua phut) va cap nhat lai khi nen chot ve muon (fin lon dan
 * toi khi het state WS ~10'). Ban nan (phut dang mo) va REST som (+2/+4 s, co the chua settle) KHONG vao fin (ghi de mot
 * symbol bang ban chua chot =&gt; go symbol do khoi fin). Reader cu chi doc bin "data" =&gt; khong anh huong.
 *
 * <p>Ma hoa: Snappy(UTF-8("v1:" + ten ngan sap xep tang dan, ngan cach ',')); tap rong = "v1:".
 */
public final class MinuteFin {
    public static final String BIN = "fin";
    static final String V1 = "v1:";

    private MinuteFin() {
    }

    public static byte[] encode(Collection<String> shortSyms) throws IOException {
        StringBuilder sb = new StringBuilder(V1);
        boolean first = true;
        for (String s : new TreeSet<>(shortSyms)) {
            if (s == null || s.isEmpty()) continue;
            if (s.indexOf(',') >= 0) throw new IllegalArgumentException("symbol chua dau phay: " + s);
            if (!first) sb.append(',');
            sb.append(s);
            first = false;
        }
        return Snappy.compress(sb.toString().getBytes(StandardCharsets.UTF_8));
    }

    /** null =&gt; null (record khong co bin fin). Sai phien ban / hong =&gt; IOException. */
    public static Set<String> decode(byte[] b) throws IOException {
        if (b == null) return null;
        String s = new String(Snappy.uncompress(b), StandardCharsets.UTF_8);
        if (!s.startsWith(V1)) throw new IOException("bin fin sai phien ban");
        Set<String> out = new TreeSet<>();
        String body = s.substring(V1.length());
        if (body.isEmpty()) return out;
        for (String x : body.split(",")) {
            if (!x.isEmpty()) out.add(x);
        }
        return out;
    }

    /**
     * Thuan (ingestor): fin sau 1 lan ghi = finOld - (newKeys ngoai finalSyms) + (finalSyms co nen trong data sau ghi).
     * {@code finOld} null = record chua co bin fin.
     */
    public static Set<String> merge(Set<String> finOld, Collection<String> newKeys, Collection<String> finalSyms,
                                    Set<String> dataKeysAfter) {
        Set<String> fin = new TreeSet<>();
        if (finOld != null) fin.addAll(finOld);
        Set<String> fs = finalSyms == null ? java.util.Collections.<String>emptySet() : new java.util.HashSet<>(finalSyms);
        if (newKeys != null) {
            for (String s : newKeys) {
                if (!fs.contains(s)) fin.remove(s);
            }
        }
        for (String s : fs) {
            if (dataKeysAfter.contains(s)) fin.add(s);
        }
        return fin;
    }

    /** Ten ngan -&gt; ten day du (cung quy uoc convertProtoMapToJavaMap: them "USDT" neu chua co). */
    public static String fullSym(String shortSym) {
        return shortSym.endsWith("USDT") ? shortSym : shortSym + "USDT";
    }

    /** Ket qua doc NGUYEN TU 1 record phut (bin data + fin) phia live. */
    public static final class Read {
        /** Nen phut (ten day du); null khi record vang / khong co bin data / loi doc. */
        public final Map<String, KlineObjectSimple> data;
        /** Tap fin (ten DAY DU); null =&gt; record KHONG co bin fin (ingestor cu) hoac record vang / loi. */
        public final Set<String> fin;
        public final boolean found;
        public final boolean error;
        /** So o (symbol) cua cache bi ghi de khi merge ban doc nay (LiveTickerWindow dien). */
        public int overwritten;

        public Read(Map<String, KlineObjectSimple> data, Set<String> fin, boolean found, boolean error) {
            this.data = data;
            this.fin = fin;
            this.found = found;
            this.error = error;
        }

        public static Read missing() {
            return new Read(null, null, false, false);
        }

        public static Read failed() {
            return new Read(null, null, false, true);
        }
    }
}
