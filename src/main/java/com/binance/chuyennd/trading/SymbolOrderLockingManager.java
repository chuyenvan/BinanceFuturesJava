package com.binance.chuyennd.trading;

import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;

public class SymbolOrderLockingManager {
    public static final Logger LOG = LoggerFactory.getLogger(SymbolOrderLockingManager.class);
    public ConcurrentHashMap<String, Long> symbol2TimeLock;
    public ConcurrentHashMap<String, Long> symbol2TimeLockReduceOnly;
    private static volatile SymbolOrderLockingManager INSTANCE = null;

    public static SymbolOrderLockingManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SymbolOrderLockingManager();
            INSTANCE.symbol2TimeLock = new ConcurrentHashMap<String, Long>();
            INSTANCE.symbol2TimeLockReduceOnly = new ConcurrentHashMap<String, Long>();
        }
        return INSTANCE;
    }

    public static void main(String[] args) throws InterruptedException {
//        String symbol = "BTCUSDT";
//        LOG.info("{}", SymbolOrderLockingManager.getInstance().isLock(symbol, 10));
//        LOG.info("{}", SymbolOrderLockingManager.getInstance().isLock(symbol + "123", 10));
//        SymbolOrderLockingManager.getInstance().addLock(symbol);
//        for (int i = 0; i < 11; i++) {
//            Thread.sleep(2000);
//            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmmss(System.currentTimeMillis()),
//                    SymbolOrderLockingManager.getInstance().isLock(symbol, 10));
//            LOG.info("{} {}", Utils.normalizeDateYYYYMMDDHHmmss(System.currentTimeMillis()),
//                    SymbolOrderLockingManager.getInstance().isLock(symbol + "123", 10));
//        }

    }

    public Boolean isLock(String symbol, int timeLock) {
        Long time = symbol2TimeLock.get(symbol);
        if (time != null && System.currentTimeMillis() - time < timeLock * Utils.TIME_SECOND) {
            return true;
        } else {
            if (time != null) {
                symbol2TimeLock.remove(symbol);
            }
        }
        return false;
    }

    public void addLock(String symbol) {
        symbol2TimeLock.put(symbol, System.currentTimeMillis());
    }

    /**
     * Nhả lock SỚM (trước khi hết TTL) — dùng trong try/finally để mọi đường ra của một tác vụ đều trả lock,
     * tránh kẹt tới hết timeout khi return/exception giữa chừng (audit #9 — updatePositionInfo).
     *
     * @param symbol khóa logic cần nhả (vd {@code "UpdateAllPos"})
     */
    public void removeLock(String symbol) {
        symbol2TimeLock.remove(symbol);
    }

    public void addLockReduceOnly(String symbol) {
        symbol2TimeLockReduceOnly.put(symbol, System.currentTimeMillis());
    }

    public Boolean isLockReduceOnly(String symbol) {
        Long time = symbol2TimeLockReduceOnly.get(symbol);
        if (time != null && System.currentTimeMillis() - time < Utils.TIME_HOUR) {
            return true;
        } else {
            if (time != null) {
                symbol2TimeLockReduceOnly.remove(symbol);
            }
        }
        return false;
    }
}
