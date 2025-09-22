package com.binance.chuyennd.trading;

import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.concurrent.ConcurrentHashMap;

public class SymbolOrderLockingManager {
    public static final Logger LOG = LoggerFactory.getLogger(SymbolOrderLockingManager.class);
    public ConcurrentHashMap<String, Long> symbol2TimeLock;
    private static volatile SymbolOrderLockingManager INSTANCE = null;

    public static SymbolOrderLockingManager getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new SymbolOrderLockingManager();
            INSTANCE.symbol2TimeLock = new ConcurrentHashMap<String, Long>();
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
}
