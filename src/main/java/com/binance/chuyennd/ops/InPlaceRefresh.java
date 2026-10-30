package com.binance.chuyennd.ops;

import com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper;
import com.binance.chuyennd.tradecore.Cfg;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * [V12 R4g] Lam moi TAI CHO cho process strategy/trade (thay cho restart JVM 12h, mac dinh TAT o c3_live/c3_shadow).
 * Kiem ke day du nhung gi restart tung "vo tinh" lam moi: docs/c3live/ROUND4G.md §1. Chi 1 muc can lam moi o day:
 * <ul>
 *   <li>symbol mapper ({@link SimpleSymbolMapper#refreshFromStore()}): id do process KHAC (collectData / tool) cap sau
 *       khi JVM nay init — truoc day chi duoc nap lai khi restart. Chu ky {@code LIVE_MAPPER_REFRESH_MIN} (mac dinh 10,
 *       0 = tat; getSymbol truot (id la) van tu lam moi &lt;= 1 lan/phut).</li>
 * </ul>
 * Cac muc khac da tu lam moi (exchangeInfo R7/UNIVERSE_A1 theo mtime, TS-EXT scheduler, funding hourly, LEGACY reconcile
 * moi tick, user-data stream keepAlive/reconnect) hoac la ngan sach (LIVE_FEAT_DUMP: nay tinh theo ngay UTC khi reset TAT).
 * Ingestor (collectData) KHONG goi lop nay.
 */
public final class InPlaceRefresh {

    private static final Logger LOG = LoggerFactory.getLogger(InPlaceRefresh.class);
    public static final String KEY_MAPPER_MIN = "LIVE_MAPPER_REFRESH_MIN";
    public static final int DEFAULT_MAPPER_MIN = 10;
    private static volatile ScheduledExecutorService ex;

    private InPlaceRefresh() {
    }

    /** Gia tri thuan: null/rong/sai/am => mac dinh 10; 0 = tat; tran 1440. */
    static int parseMinutes(String raw) {
        if (raw == null || raw.trim().isEmpty()) return DEFAULT_MAPPER_MIN;
        try {
            int v = Integer.parseInt(raw.trim());
            return v < 0 ? DEFAULT_MAPPER_MIN : Math.min(v, 1440);
        } catch (NumberFormatException e) {
            return DEFAULT_MAPPER_MIN;
        }
    }

    public static synchronized void start() {
        if (ex != null) return;
        int min = parseMinutes(Cfg.get(KEY_MAPPER_MIN));
        LOG.info("[OPS-REFRESH] lam moi tai cho: mapper moi {} phut (0=tat); reset dinh ky={}h (nguon={})", min,
                OpsConfig.periodicResetHours(), OpsConfig.periodicResetSource());
        if (min <= 0) return;
        ex = Executors.newSingleThreadScheduledExecutor(r -> {
            Thread t = new Thread(r, "OPS-REFRESH");
            t.setDaemon(true);
            return t;
        });
        ex.scheduleWithFixedDelay(InPlaceRefresh::refreshMapper, min, min, TimeUnit.MINUTES);
    }

    static void refreshMapper() {
        try {
            int n = SimpleSymbolMapper.getInstance().refreshFromStore();
            if (n > 0) LOG.info("[OPS-REFRESH] mapper them {} symbol tu store", n);
        } catch (Throwable t) {
            LOG.warn("[OPS-REFRESH] lam moi mapper loi (bo qua nhip nay): {}", t.toString());
        }
    }
}
