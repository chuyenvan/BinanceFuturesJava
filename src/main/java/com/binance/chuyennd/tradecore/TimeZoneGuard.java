package com.binance.chuyennd.tradecore;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.TimeZone;

/**
 * Bảo vệ múi giờ toàn hệ thống.
 *
 * <p>Hệ thống CHUẨN HOÁ về <b>GMT+7</b>: key Aerospike dạng {@code yyyyMMdd-HHmm} mã hoá GIỜ TƯỜNG
 * GMT+7 (dữ liệu lịch sử được ghi bởi máy GMT+7). Nếu JVM chạy ở múi giờ khác (vd VPS Oracle = UTC),
 * {@link SimpleDateFormat} trần sẽ format/parse LỆCH GIỜ ⇒ key trỏ sai phút ⇒ HỎNG DATA âm thầm.
 *
 * <ul>
 *   <li>{@link #enforceGmt7()} — Lớp 0: ép tz mặc định JVM = GMT+7. Gọi CÀNG SỚM CÀNG TỐT
 *       (đặt ở đầu static-init {@link Configs}) để mọi SimpleDateFormat trần hành xử y hệt trên mọi OS.</li>
 *   <li>{@link #assertGmt7()} — Lớp 2: fail-fast. Sai tz hoặc round-trip key lệch ⇒ log + {@code System.exit}
 *       ⇒ VPS provision sai tz CHẾT NGAY lúc start, không kịp xuất/ghi data lỗi.</li>
 * </ul>
 */
public final class TimeZoneGuard {

    public static final String SYSTEM_TZ_ID = "GMT+7";
    public static final TimeZone SYSTEM_TZ = TimeZone.getTimeZone(SYSTEM_TZ_ID);
    private static final int OFFSET_MS = 7 * 60 * 60 * 1000;

    private TimeZoneGuard() {
    }

    /** Lớp 0: ép timezone mặc định JVM về GMT+7. */
    public static void enforceGmt7() {
        TimeZone.setDefault(SYSTEM_TZ);
    }

    /**
     * Lớp 2: kiểm timezone mặc định JVM == GMT+7 và round-trip timestamp↔key đúng phút.
     * Sai ⇒ in lỗi to và {@link System#exit(int)} để chặn chạy tiếp với data sẽ bị lệch giờ.
     */
    public static void assertGmt7() {
        TimeZone def = TimeZone.getDefault();
        boolean okOffset = def.getRawOffset() == OFFSET_MS && def.getDSTSavings() == 0;

        boolean okRoundTrip;
        try {
            // KHÔNG set tz cho fmt: cố ý test CHÍNH tz mặc định JVM hiện tại.
            SimpleDateFormat fmt = new SimpleDateFormat("yyyyMMdd-HHmm");
            // 1609434000000 = 2021-01-01 00:00 GMT+7 (tức 2020-12-31 17:00 UTC) ⇒ key kỳ vọng "20210101-0000".
            long sample = 1609434000000L;
            String key = fmt.format(new Date(sample));
            long back = fmt.parse(key).getTime();
            okRoundTrip = "20210101-0000".equals(key) && back == sample;
        } catch (Exception e) {
            okRoundTrip = false;
        }

        if (!okOffset || !okRoundTrip) {
            System.err.println("⛔ TIMEZONE GUARD FAIL: default tz = " + def.getID()
                    + " offset(h)=" + (def.getRawOffset() / 3600000.0)
                    + " | hệ thống YÊU CẦU GMT+7. SimpleDateFormat sẽ key Aerospike LỆCH GIỜ ⇒ HỎNG DATA."
                    + " Sửa tz máy, hoặc chạy với -Duser.timezone=GMT+07:00.");
            System.exit(1);
        }
    }
}
