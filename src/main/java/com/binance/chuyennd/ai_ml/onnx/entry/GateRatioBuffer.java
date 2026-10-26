package com.binance.chuyennd.ai_ml.onnx.entry;

import java.util.Arrays;

/**
 * LÕI THUẦN của gate rolling "đều lệnh" trên TỈ SỐ r (GDV2) — KHÔNG config, KHÔNG log.
 *
 * <p>Dùng CHUNG cho {@link GateRollingRatio} (sim, key {@code SIM_GATE_ROLLING_*}) và
 * {@link LiveGateRollingRatio} (live, key {@code LIVE_GATE_ROLLING_*}) để q_t và quyết định pass
 * <b>bit-identical</b> giữa hai class (một nguồn sự thật duy nhất). Thuật toán trích NGUYÊN VĂN từ
 * {@code GateRollingRatio} của worktree GDV2 (jar 7368be46…): quantile theo giờ, CAUSAL (q_h chỉ dùng
 * r có ts &lt; h), warm-up 7 ngày, quickselect median-of-3 fallback sort.
 *
 * <p>Vì `r` cần `symbolPred` chỉ có lúc chạy ⇒ buffer được dựng ONLINE (khác GD92 precompute từ
 * predictionMap). Mỗi lần đánh giá ứng viên PREDICT nạp một `(ts, r)`.
 */
final class GateRatioBuffer {

    static final long HOUR = 3600_000L;
    static final long DAY = 86_400_000L;
    static final long WARMUP_MS = 7L * DAY;

    // online buffer (append theo ts tăng; head/tail + compact)
    private long[] tsBuf = new long[1 << 14];
    private float[] rBuf = new float[1 << 14];
    private int head = 0;
    private int tail = 0;
    private long firstTs = Long.MIN_VALUE;

    // quantile theo giờ
    private long lastHour = Long.MIN_VALUE;
    private float currentQ = 0f;
    private long nQuery = 0;
    private long nBeforeFirst = 0;

    private float[] scratchArr;

    /**
     * Lõi: tính (nếu qua giờ mới) q cho giờ của ts, trả q, rồi nạp (ts, r).
     * CAUSAL: q_h chỉ dùng r có ts &lt; h (mẫu hiện tại được nạp SAU khi tính q).
     */
    float addAndQuery(long ts, float r, float pct, int days, float fallbackBase) {
        nQuery++;
        long h = (ts / HOUR) * HOUR;              // mốc giờ
        if (h != lastHour) {
            currentQ = computeQ(h, pct, days, fallbackBase);
            lastHour = h;
        }
        add(ts, r);
        return currentQ;
    }

    /**
     * [NUP-TIER2] Nhu addAndQuery nhung tinh them q2 (pct2) MOT LAN khi qua gio moi, tren CUNG
     * cua so TRUOC-add. out[0]=q1, out[1]=q2 (NaN neu khong phai gio moi).
     * q2 KHONG duoc tinh lai moi ung vien (chi phi O(m) moi gio, khong phai moi candidate).
     */
    float addAndQuery2(long ts, float r, float pct, float pct2, int days, float fallbackBase, float[] out) {
        nQuery++;
        long h = (ts / HOUR) * HOUR;
        if (h != lastHour) {
            currentQ = computeQ(h, pct, days, fallbackBase);
            out[1] = computeQPct(h, pct2, days, fallbackBase);
            lastHour = h;
        } else {
            out[1] = Float.NaN;
        }
        add(ts, r);
        out[0] = currentQ;
        return currentQ;
    }

    /** Phan vi pct tren cua so hien tai (head da duoc computeQ cat cho h). KHONG nap mau. */
    private float computeQPct(long h, float pct, int days, float fallbackBase) {
        int m = tail - head;
        if (firstTs == Long.MIN_VALUE || m == 0 || (h - firstTs) < WARMUP_MS) return fallbackBase;
        int k = Math.min(m - 1, Math.max(0, (int) Math.floor((double) pct * (m - 1))));
        return kthSmallest(head, m, k);
    }

    /** Nạp nhiều (ts, r) (sort ts tăng) — cho warm-up seed / nạp lại file persist. */
    void bulkAdd(long[] ts, float[] r) {
        for (int i = 0; i < ts.length; i++) add(ts[i], r[i]);
    }

    private float computeQ(long h, float pct, int days, float fallbackBase) {
        long cut = h - (long) days * DAY;
        while (head < tail && tsBuf[head] < cut) head++;
        int m = tail - head;
        if (firstTs == Long.MIN_VALUE || m == 0 || (h - firstTs) < WARMUP_MS) {
            nBeforeFirst++;
            return fallbackBase;
        }
        int k = Math.min(m - 1, Math.max(0, (int) Math.floor((double) pct * (m - 1))));
        return kthSmallest(head, m, k);
    }

    /** Phân vị thứ k (0-based) trong rBuf[base, base+m). Dùng quickselect median-of-3, fallback sort. */
    private float kthSmallest(int base, int m, int k) {
        if (m <= 0) return Float.NaN;
        float[] a = scratch(m);
        System.arraycopy(rBuf, base, a, 0, m);
        int lo = 0, hi = m - 1, kk = k, guard = 0;
        while (lo < hi) {
            if (++guard > 256) {                 // chống thoái hoá (không xảy ra trong thực tế)
                Arrays.sort(a, lo, hi + 1);
                return a[kk];
            }
            int mid = (lo + hi) >>> 1;
            if (a[mid] < a[lo]) swap(a, mid, lo);
            if (a[hi] < a[lo]) swap(a, hi, lo);
            if (a[hi] < a[mid]) swap(a, hi, mid);
            float pivot = a[mid];
            swap(a, mid, hi);
            int i = lo, j = hi - 1;
            while (true) {
                while (i <= j && a[i] < pivot) i++;
                while (i <= j && a[j] > pivot) j--;
                if (i >= j) break;
                swap(a, i, j);
                i++; j--;
            }
            swap(a, i, hi);
            if (kk < i) hi = i - 1;
            else if (kk > i) lo = i + 1;
            else return a[i];
        }
        return a[lo];
    }

    /**
     * [NUP-TIER2] Phan vi {@code pct} tren CUNG buffer, CUNG cua so, CUNG gio — chi doc, KHONG nap mau,
     * KHONG di chuyen head/tail. Loai mau CUOI neu no chinh la {@code ts} vua duoc {@code addAndQuery}
     * nap, de q2 tinh tren dung trang thai TRUOC-add nhu q1 cua gate chinh.
     * Warm-up / chua co gio => fallbackBase (giong computeQ).
     */
    float queryPctExcludingLast(long ts, float pct, int days, float fallbackBase) {
        long h = (ts / HOUR) * HOUR;
        if (lastHour == Long.MIN_VALUE || h != lastHour) return fallbackBase;
        int end = tail;
        if (end > head && tsBuf[end - 1] == ts) end--;
        int m = end - head;
        if (firstTs == Long.MIN_VALUE || m == 0 || (h - firstTs) < WARMUP_MS) return fallbackBase;
        int k = Math.min(m - 1, Math.max(0, (int) Math.floor((double) pct * (m - 1))));
        return kthSmallest(head, m, k);
    }

    private float[] scratch(int n) {
        if (scratchArr == null || scratchArr.length < n) scratchArr = new float[n];
        return scratchArr;
    }

    private void add(long ts, float r) {
        if (firstTs == Long.MIN_VALUE) firstTs = ts;
        if (tail == tsBuf.length) {
            grow();
        }
        tsBuf[tail] = ts;
        rBuf[tail] = r;
        tail++;
        compactIfNeeded();
    }

    private void grow() {
        int cap = tsBuf.length << 1;
        tsBuf = Arrays.copyOf(tsBuf, cap);
        rBuf = Arrays.copyOf(rBuf, cap);
    }

    private void compactIfNeeded() {
        if (head > 0 && head * 2 > tail) {
            int n = tail - head;
            System.arraycopy(tsBuf, head, tsBuf, 0, n);
            System.arraycopy(rBuf, head, rBuf, 0, n);
            tail = n;
            head = 0;
        }
    }

    private static void swap(float[] a, int i, int j) {
        float t = a[i]; a[i] = a[j]; a[j] = t;
    }

    int size() {
        return tail - head;
    }

    long firstTs() {
        return firstTs;
    }

    long nQuery() {
        return nQuery;
    }

    long nBeforeFirst() {
        return nBeforeFirst;
    }

    long lastHour() {
        return lastHour;
    }

    float currentQ() {
        return currentQ;
    }

    /** Toàn bộ (ts, r) hiện trong cửa sổ (đã cắt đầu), sort ts tăng — cho persist/compact. */
    long[] tsSnapshot() {
        int n = tail - head;
        long[] out = new long[n];
        System.arraycopy(tsBuf, head, out, 0, n);
        return out;
    }

    float[] rSnapshot() {
        int n = tail - head;
        float[] out = new float[n];
        System.arraycopy(rBuf, head, out, 0, n);
        return out;
    }

    void reset() {
        tsBuf = new long[1 << 14];
        rBuf = new float[1 << 14];
        head = tail = 0;
        firstTs = Long.MIN_VALUE;
        lastHour = Long.MIN_VALUE;
        currentQ = 0f;
        nQuery = nBeforeFirst = 0;
        scratchArr = null;
    }
}
