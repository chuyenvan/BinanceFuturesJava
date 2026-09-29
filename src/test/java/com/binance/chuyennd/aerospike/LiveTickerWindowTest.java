package com.binance.chuyennd.aerospike;

import com.binance.chuyennd.utils.Utils;
import org.junit.Test;

import static org.junit.Assert.assertEquals;

/** [B6-SPEED-V3] Unit test cửa sổ phút của {@link LiveTickerWindow} (thuần tính toán, không cần Aerospike). */
public class LiveTickerWindowTest {

    @Test
    public void windowEndsAtLastCompleteMinute() {
        // now = 12:15:08.123 GMT+7 → cửa sổ 1000' kết thúc tại phút 12:14:00.
        long now = System.currentTimeMillis();
        long floor = now - (now % Utils.TIME_MINUTE);
        long[] w = LiveTickerWindow.windowBounds(now, 1000);
        assertEquals(floor - Utils.TIME_MINUTE, w[1]);                       // endMinute = floor(now)-1'
        assertEquals(w[1] - 999L * Utils.TIME_MINUTE, w[0]);                 // startMinute = endMinute - 999'
    }

    @Test
    public void windowSizeMatchesMinutesToRead() {
        long now = System.currentTimeMillis() + 123_456L;                    // offset sub-phút bất kỳ
        for (int m : new int[]{1, 15, 1000, 2000}) {
            long[] w = LiveTickerWindow.windowBounds(now, m);
            assertEquals((long) (m - 1) * Utils.TIME_MINUTE, w[1] - w[0]);
        }
    }

    @Test
    public void windowIndependentOfSubMinuteOffset() {
        // offset sub-phút của now KHÔNG làm dịch cửa sổ phút (cùng floor → cùng [start,end]).
        long base = (System.currentTimeMillis() / Utils.TIME_MINUTE) * Utils.TIME_MINUTE;
        long[] a = LiveTickerWindow.windowBounds(base + 1L, 1000);
        long[] b = LiveTickerWindow.windowBounds(base + 59_999L, 1000);
        assertEquals(a[0], b[0]);
        assertEquals(a[1], b[1]);
    }
}
