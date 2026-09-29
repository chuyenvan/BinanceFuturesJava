package com.binance.chuyennd.aerospike;

import org.junit.Test;

import java.util.Arrays;
import java.util.Calendar;
import java.util.List;
import java.util.TimeZone;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

/**
 * [B4-SPEED] Bang chung cho {@code monthsBetween(fromTs,toTs)}: chi liet ke chunk-thang phủ khoảng
 * cần đọc (24h) thay vì toàn bộ 202001..nay (~81 tháng) => IO giảm ~40x, kết quả tailMap(24h) y hệt.
 */
public class MonthsBetweenTest {

    private static final TimeZone TZ = TimeZone.getTimeZone("GMT+7");

    private static long ts(int y, int m, int d, int h) {
        Calendar c = Calendar.getInstance(TZ);
        c.clear();
        c.set(y, m - 1, d, h, 0, 0);
        c.set(Calendar.MILLISECOND, 0);
        return c.getTimeInMillis();
    }

    @Test
    public void cungThang_traMotThang() {
        List<String> r = DataManagerAerospikeFloatSim.monthsBetween(ts(2026, 9, 15, 0), ts(2026, 9, 29, 0));
        assertEquals(Arrays.asList("202609"), r);
    }

    @Test
    public void khacThang_traHaiThang() {
        List<String> r = DataManagerAerospikeFloatSim.monthsBetween(ts(2026, 8, 20, 0), ts(2026, 9, 5, 0));
        assertEquals(Arrays.asList("202608", "202609"), r);
    }

    @Test
    public void xaNhau_traDayDuCacThangTangDan() {
        List<String> r = DataManagerAerospikeFloatSim.monthsBetween(ts(2026, 7, 1, 0), ts(2026, 9, 1, 0));
        assertEquals(Arrays.asList("202607", "202608", "202609"), r);
    }

    @Test
    public void cuaSo24hVatQuaRanhGioiThang_phaiBaoCaThangTruoc() {
        // truong hop QUAN TRONG: now roi vao ngay 1 dau thang => 24h truoc nam thang truoc.
        List<String> r = DataManagerAerospikeFloatSim.monthsBetween(ts(2026, 8, 31, 0), ts(2026, 9, 1, 0));
        assertEquals(Arrays.asList("202608", "202609"), r);
    }

    @Test
    public void fromThangSauToThangTruoc_traRong() {
        List<String> r = DataManagerAerospikeFloatSim.monthsBetween(ts(2026, 10, 1, 0), ts(2026, 9, 1, 0));
        assertTrue("from thang sau to thang truoc => rong", r.isEmpty());
    }
}
