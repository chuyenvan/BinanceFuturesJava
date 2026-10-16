package com.binance.chuyennd.tradecore;

/**
 * [BURST-COOLDOWN 2026-10-16] docs/prereg/PREREG_BURST_COOLDOWN.md — ngat mach sau dot lon cua selector.
 *
 * <p>Dem so chan PREDICT_SYMBOL_TRADE THUC SU mo trong cung mot phut. Khi dem cham {@code n} trong phut m
 * ⇒ cooldown toi het phut m + {@code minutes}. Trong cooldown, chan PREDICT o phut KHAC phut kich hoat bi chan
 * ({@link #blocks(long)} = true); cac chan con lai cua chinh phut kich hoat van duoc mo.
 *
 * <p>{@code n <= 0} hoac {@code minutes <= 0} ⇒ tat: {@link #blocks(long)} luon false, {@link #recordOpen(long)}
 * khong lam gi ⇒ byte-identical.
 */
public final class BurstCooldown {
    private static final long MIN_MS = 60_000L;

    private final int n;
    private final long cooldownMs;
    private long curMinute = Long.MIN_VALUE;
    private int count;
    private long untilMs = Long.MIN_VALUE;
    private long triggers;
    private long blocked;

    public BurstCooldown(int n, int minutes) {
        this.n = n;
        this.cooldownMs = minutes > 0 ? minutes * MIN_MS : 0L;
    }

    public static BurstCooldown off() {
        return new BurstCooldown(0, 0);
    }

    public static BurstCooldown fromConfigs() {
        return new BurstCooldown(Configs.BURST_COOLDOWN_N, Configs.BURST_COOLDOWN_MIN);
    }

    public boolean enabled() {
        return n > 0 && cooldownMs > 0;
    }

    /** true = chan PREDICT moi tai thoi diem {@code tMs} bi chan (va duoc dem). */
    public boolean blocks(long tMs) {
        if (!enabled()) return false;
        long m = Math.floorDiv(tMs, MIN_MS);
        if (m == curMinute) return false;
        if (tMs < untilMs) {
            blocked++;
            return true;
        }
        return false;
    }

    /** Ghi nhan mot chan PREDICT da THUC SU mo tai {@code tMs}. */
    public void recordOpen(long tMs) {
        if (!enabled()) return;
        long m = Math.floorDiv(tMs, MIN_MS);
        if (m != curMinute) {
            curMinute = m;
            count = 0;
        }
        count++;
        if (count == n) {
            untilMs = (m + 1) * MIN_MS + cooldownMs;
            triggers++;
        }
    }

    public long triggers() {
        return triggers;
    }

    public long blocked() {
        return blocked;
    }

    public long untilMs() {
        return untilMs;
    }

    public int n() {
        return n;
    }

    public long minutes() {
        return cooldownMs / MIN_MS;
    }
}
