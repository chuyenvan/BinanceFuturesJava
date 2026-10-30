package com.binance.chuyennd.c3live.soak;

import com.binance.chuyennd.c3live.api.ExchangeGateway;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Proxy;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;

/**
 * [V12 R4h] Gateway CHI DOC cho soak user-data stream: CHI cho {@code startUserStream} (POST /fapi/v1/listenKey — san tra
 * listenKey dang hieu luc neu da co, khong vo hieu hoa nguoi khac) va {@code keepAliveUserStream} (PUT — chi gia han).
 * MOI ham khac — dac biet {@code closeUserStream} (DELETE: lam dut stream cua MOI ket noi dung listenKey do) va moi lenh/
 * huy/doi cau hinh — NEM {@link UnsupportedOperationException}, khong cham san.
 */
public final class SoakGuard {

    private static final Logger LOG = LoggerFactory.getLogger(SoakGuard.class);
    static final Set<String> ALLOWED = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "startUserStream", "keepAliveUserStream", "name")));
    static final AtomicLong BLOCKED = new AtomicLong();

    private SoakGuard() {
    }

    public static ExchangeGateway readOnly(ExchangeGateway d) {
        return (ExchangeGateway) Proxy.newProxyInstance(ExchangeGateway.class.getClassLoader(), new Class<?>[]{ExchangeGateway.class},
                (proxy, m, args) -> {
                    String n = m.getName();
                    if (m.getDeclaringClass() == Object.class) {
                        if ("toString".equals(n)) return "SoakGuard[" + d + "]";
                        if ("hashCode".equals(n)) return System.identityHashCode(proxy);
                        if ("equals".equals(n)) return proxy == args[0];
                    }
                    if (!ALLOWED.contains(n)) {
                        BLOCKED.incrementAndGet();
                        LOG.error("[WS-SOAK] CHAN goi '{}' (soak CHI DOC: chi POST/PUT listenKey)", n);
                        throw new UnsupportedOperationException("[WS-SOAK] chi doc: chan " + n);
                    }
                    try {
                        return m.invoke(d, args);
                    } catch (InvocationTargetException e) {
                        throw e.getCause();
                    }
                });
    }

    public static long blockedCount() {
        return BLOCKED.get();
    }
}
