package com.binance.chuyennd.ai_ml.data;

import com.binance.chuyennd.object.sw.KlineObjectSimple;
import org.junit.After;
import org.junit.Test;

import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;

import static org.junit.Assert.*;

/**
 * TASK-142 (rework compact-lossless) — RAM-cache ticker theo ngày (đường TICKER_SOURCE=file). Test CƠ CHẾ
 * cache thuần (không cần file .bin.gz thật): tráo loader giả qua {@link HPOSmartCache#setFileLoaderForTest}
 * rồi kiểm:
 * <ul>
 *   <li>cache HIT: gọi 2 lần cùng ngày → loader chỉ chạy 1 lần; map dựng lại từ nén có GIÁ TRỊ Y HỆT
 *       (KHÔNG còn assert identity vì bản nén tạo object mới mỗi lần — đây là chủ đích của rework).</li>
 *   <li>totalUsdt GIỮ nguyên (khác CompactDayData LOSSY) + startTime = ĐÚNG map key (lossless).</li>
 *   <li>clearFileCache / clearCache → nạp lại (loader chạy lại), fileCachedDays về 0.</li>
 *   <li>ngày miss (loader trả null) KHÔNG được cache (giữ FAIL-FAST đường cũ).</li>
 * </ul>
 */
public class HPOSmartCacheFileCacheTest {

    @After
    public void tearDown() {
        // trả loader mặc định + xóa cache để không rò trạng thái sang test khác
        HPOSmartCache.setFileLoaderForTest(null);
        HPOSmartCache.clearCache();
    }

    private static TreeMap<Long, KlineObjectSimple[]> fakeDay(long dayTs) {
        TreeMap<Long, KlineObjectSimple[]> m = new TreeMap<>();
        KlineObjectSimple[] minute = new KlineObjectSimple[1000];
        KlineObjectSimple k = new KlineObjectSimple();
        k.startTime = dayTs;
        k.priceOpen = 1f; k.maxPrice = 2f; k.minPrice = 0.5f; k.priceClose = 1.5f;
        k.totalUsdt = 12345f;   // 🔑 field CompactDayData sẽ mất — bản compact-lossless PHẢI giữ nguyên
        minute[7] = k;
        m.put(dayTs, minute);
        return m;
    }

    @Test
    public void cacheHitGiuGiaTriVaLoaderChayMotLan() {
        AtomicInteger calls = new AtomicInteger(0);
        final long day = 1_700_000_000_000L;
        HPOSmartCache.setFileLoaderForTest(d -> { calls.incrementAndGet(); return fakeDay(d); });

        TreeMap<Long, KlineObjectSimple[]> first = HPOSmartCache.getDataShortFromFile(day);
        TreeMap<Long, KlineObjectSimple[]> second = HPOSmartCache.getDataShortFromFile(day);

        assertEquals("loader chi duoc goi 1 lan (lan 2 la cache HIT)", 1, calls.get());
        assertEquals(1, HPOSmartCache.fileCachedDays());

        KlineObjectSimple k1 = first.get(day)[7];
        KlineObjectSimple k2 = second.get(day)[7];
        assertNotNull(k1);
        assertNotNull(k2);
        // Bang GIA TRI tren MOI field (khong con assert identity vi nen -> dung lai object moi)
        assertEquals("startTime = dung map key (lossless)", day, (long) k2.startTime);
        assertEquals(k1.startTime, k2.startTime);
        assertEquals(1f, k2.priceOpen, 0f);
        assertEquals(2f, k2.maxPrice, 0f);
        assertEquals(0.5f, k2.minPrice, 0f);
        assertEquals(1.5f, k2.priceClose, 0f);
        assertEquals("totalUsdt GIU nguyen (khong bi nen mat nhu CompactDayData)",
                12345f, k2.totalUsdt, 0f);
    }

    @Test
    public void phutVangCoinLaNull() {
        final long day = 1_700_000_000_000L;
        HPOSmartCache.setFileLoaderForTest(d -> fakeDay(d));

        TreeMap<Long, KlineObjectSimple[]> got = HPOSmartCache.getDataShortFromFile(day);
        // fakeDay chi set coin id=7; moi id khac phai la null (sentinel NaN KHONG duoc bien thanh object)
        assertNull("coin vang phai la null", got.get(day)[0]);
        assertNull("coin vang phai la null", got.get(day)[500]);
        assertNotNull("coin co du lieu phai co object", got.get(day)[7]);
    }

    @Test
    public void clearFileCacheThiNapLai() {
        AtomicInteger calls = new AtomicInteger(0);
        final long day = 1_700_000_000_000L;
        HPOSmartCache.setFileLoaderForTest(d -> { calls.incrementAndGet(); return fakeDay(d); });

        HPOSmartCache.getDataShortFromFile(day);
        assertEquals(1, calls.get());
        HPOSmartCache.clearFileCache();
        assertEquals(0, HPOSmartCache.fileCachedDays());
        HPOSmartCache.getDataShortFromFile(day);
        assertEquals("sau clear -> cache miss -> loader chay lai", 2, calls.get());

        // clearCache() tong cung phai xoa FILE_STORE
        HPOSmartCache.clearCache();
        assertEquals(0, HPOSmartCache.fileCachedDays());
    }

    @Test
    public void ngayMissKhongDuocCache() {
        AtomicInteger calls = new AtomicInteger(0);
        final long day = 1_700_000_000_000L;
        HPOSmartCache.setFileLoaderForTest(d -> { calls.incrementAndGet(); return null; });

        assertNull("loader tra null -> tra null (giu FAIL-FAST)", HPOSmartCache.getDataShortFromFile(day));
        assertEquals("miss khong duoc cache", 0, HPOSmartCache.fileCachedDays());
        HPOSmartCache.getDataShortFromFile(day);
        assertEquals("moi lan miss deu goi loader lai (khong cache null)", 2, calls.get());
    }
}
