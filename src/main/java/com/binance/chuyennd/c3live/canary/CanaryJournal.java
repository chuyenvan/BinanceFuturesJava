package com.binance.chuyennd.c3live.canary;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.LongSupplier;
import java.util.regex.Pattern;

/**
 * [V12 3] Nhat ky canary dang JSONL ({@code run/canary/canary_<TS>.jsonl}): moi call san (KHONG key / signature / query),
 * ket qua, ma loi, weight, su kien stream (raw, da che listenKey), ket qua tung buoc K. Ghi + flush tung dong (JVM bi kill
 * giua chung van con du lieu). Giu ban sao trong RAM cho test/tinh tieu chi.
 */
public final class CanaryJournal {

    private static final Logger LOG = LoggerFactory.getLogger(CanaryJournal.class);
    private static final Gson GSON = new GsonBuilder().disableHtmlEscaping().create();
    private static final Pattern LISTEN_KEY = Pattern.compile("(\"listenKey\"\\s*:\\s*\")[^\"]*(\")");

    private final File file;
    private final LongSupplier clock;
    private final List<Map<String, Object>> mem = Collections.synchronizedList(new ArrayList<>());
    private Writer out;

    public CanaryJournal(File file, LongSupplier clock) {
        this.file = file;
        this.clock = clock;
        if (file != null) {
            try {
                File p = file.getAbsoluteFile().getParentFile();
                if (p != null && !p.exists() && !p.mkdirs()) throw new IOException("mkdirs " + p);
                out = new OutputStreamWriter(new FileOutputStream(file, true), StandardCharsets.UTF_8);
            } catch (IOException e) {
                LOG.error("[CANARY] khong mo duoc journal {}: {}", file.getPath(), e.toString());
                out = null;
            }
        }
    }

    public File file() {
        return file;
    }

    /** Ghi 1 dong {ts, type, ...fields}. Gia tri String duoc che listenKey. */
    public synchronized Map<String, Object> event(String type, Map<String, ?> fields) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("ts", clock.getAsLong());
        m.put("type", type);
        if (fields != null) {
            for (Map.Entry<String, ?> e : fields.entrySet()) {
                Object v = sanitize(e.getValue());
                m.put(e.getKey(), v instanceof String ? mask((String) v) : v);
            }
        }
        mem.add(m);
        if (out != null) {
            try {
                out.write(GSON.toJson(m));
                out.write('\n');
                out.flush();
            } catch (IOException e) {
                LOG.error("[CANARY] ghi journal loi: {}", e.toString());
            }
        }
        return m;
    }

    /** Tien ich: event(type, k1, v1, k2, v2, ...). */
    public Map<String, Object> ev(String type, Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i + 1 < kv.length; i += 2) m.put(String.valueOf(kv[i]), kv[i + 1]);
        return event(type, m);
    }

    /** Ban sao cac dong da ghi trong JVM nay. */
    public List<Map<String, Object>> entries() {
        synchronized (mem) {
            return new ArrayList<>(mem);
        }
    }

    public synchronized void close() {
        if (out != null) {
            try {
                out.close();
            } catch (IOException ignore) {
                // da dong
            }
            out = null;
        }
    }

    /** So khong huu han (NaN/Inf) => chuoi (JSON chuan khong co NaN); de quy Map/List. */
    @SuppressWarnings("unchecked")
    public static <T> T sanitize(T v) {
        if (v instanceof Double) {
            Double d = (Double) v;
            return d.isNaN() || d.isInfinite() ? (T) String.valueOf(d) : v;
        }
        if (v instanceof Float) {
            Float f = (Float) v;
            return f.isNaN() || f.isInfinite() ? (T) String.valueOf(f) : v;
        }
        if (v instanceof Map) {
            Map<Object, Object> out = new LinkedHashMap<>();
            for (Map.Entry<?, ?> e : ((Map<?, ?>) v).entrySet()) out.put(e.getKey(), sanitize(e.getValue()));
            return (T) out;
        }
        if (v instanceof List) {
            List<Object> out = new ArrayList<>();
            for (Object x : (List<?>) v) out.add(sanitize(x));
            return (T) out;
        }
        return v;
    }

    static String mask(String s) {
        if (s == null || s.indexOf("listenKey") < 0) return s;
        return LISTEN_KEY.matcher(s).replaceAll("$1***$2");
    }

    /** Che chuoi bi mat (listenKey...) chi giu 4 ky tu dau. */
    public static String redact(String secret) {
        if (secret == null) return null;
        return secret.length() <= 4 ? "***" : secret.substring(0, 4) + "***";
    }
}
