package com.binance.chuyennd.c3live.e2e.replay;

import ch.qos.logback.classic.Level;
import ch.qos.logback.classic.LoggerContext;
import ch.qos.logback.classic.spi.ILoggingEvent;
import ch.qos.logback.core.AppenderBase;
import org.slf4j.ILoggerFactory;
import org.slf4j.LoggerFactory;

import java.util.ArrayList;
import java.util.List;

/** [E2E_REPLAY X7] Dem log ERROR (logback) tu goi c3live / ops trong luc replay; giam nhieu INFO cua com.binance xuong WARN. */
final class LogCapture extends AppenderBase<ILoggingEvent> {

    private final List<String> errs = new ArrayList<>();
    private final List<String> otherErrs = new ArrayList<>();
    private int n;
    private int nOther;
    private ch.qos.logback.classic.Logger root;
    private Level prevBinance;
    private ch.qos.logback.classic.Logger binance;

    static LogCapture attach() {
        ILoggerFactory f = LoggerFactory.getILoggerFactory();
        if (!(f instanceof LoggerContext)) return null;
        LoggerContext ctx = (LoggerContext) f;
        LogCapture c = new LogCapture();
        c.setContext(ctx);
        c.setName("e2e-capture");
        c.start();
        c.root = ctx.getLogger(org.slf4j.Logger.ROOT_LOGGER_NAME);
        c.root.addAppender(c);
        c.binance = ctx.getLogger("com.binance");
        c.prevBinance = c.binance.getLevel();
        c.binance.setLevel(Level.WARN);
        return c;
    }

    void detach() {
        if (root != null) root.detachAppender(this);
        if (binance != null) binance.setLevel(prevBinance);
        stop();
    }

    @Override
    protected synchronized void append(ILoggingEvent e) {
        if (!e.getLevel().isGreaterOrEqual(Level.ERROR)) return;
        String ln = e.getLoggerName();
        String msg = ln + ": " + e.getFormattedMessage();
        if (ln.startsWith("com.binance.chuyennd.c3live") || ln.startsWith("com.binance.chuyennd.ops")) {
            n++;
            if (errs.size() < 60) errs.add(msg);
        } else {
            nOther++;
            if (otherErrs.size() < 30) otherErrs.add(msg);
        }
    }

    synchronized int errorCount() {
        return n;
    }

    synchronized List<String> errors() {
        List<String> l = new ArrayList<>(errs);
        if (nOther > 0) l.add("(ngoai c3live/ops: " + nOther + ") " + otherErrs);
        return l;
    }

    String kind() {
        return "logback";
    }
}
