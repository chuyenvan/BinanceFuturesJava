package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Optional;

/**
 * [V12 Q1b] Tai khoan con (GET /fapi/v3/account). totalMarginBalance (Multi-Assets: gom BFUSD quy doi) la nguon equity
 * cho sizing min(PILOT_CAPITAL, totalMarginBalance) va kill-switch DD.
 */
public final class AccountSnapshot {
    private final BigDecimal totalMarginBalance;
    private final BigDecimal totalWalletBalance;
    private final BigDecimal availableBalance;
    private final BigDecimal totalUnrealizedProfit;
    private final List<AssetBalance> assets;
    private final long timeMs;
    /** [2d MAJ-2b] {@code positions} cua /fapi/v3/account; null = khong biet (ban cai khong tra). */
    private final List<PositionInfo> positions;

    public AccountSnapshot(BigDecimal totalMarginBalance, BigDecimal totalWalletBalance, BigDecimal availableBalance,
                           BigDecimal totalUnrealizedProfit, List<AssetBalance> assets, long timeMs) {
        this(totalMarginBalance, totalWalletBalance, availableBalance, totalUnrealizedProfit, assets, timeMs, null);
    }

    public AccountSnapshot(BigDecimal totalMarginBalance, BigDecimal totalWalletBalance, BigDecimal availableBalance,
                           BigDecimal totalUnrealizedProfit, List<AssetBalance> assets, long timeMs,
                           List<PositionInfo> positions) {
        this.positions = positions == null ? null : Collections.unmodifiableList(new ArrayList<>(positions));
        this.totalMarginBalance = totalMarginBalance;
        this.totalWalletBalance = totalWalletBalance;
        this.availableBalance = availableBalance;
        this.totalUnrealizedProfit = totalUnrealizedProfit;
        this.assets = assets == null ? Collections.emptyList() : Collections.unmodifiableList(new ArrayList<>(assets));
        this.timeMs = timeMs;
    }

    public BigDecimal getTotalMarginBalance() { return totalMarginBalance; }
    public BigDecimal getTotalWalletBalance() { return totalWalletBalance; }
    public BigDecimal getAvailableBalance() { return availableBalance; }
    public BigDecimal getTotalUnrealizedProfit() { return totalUnrealizedProfit; }
    public List<AssetBalance> getAssets() { return assets; }
    /** Thoi diem client nhan snapshot (gio server da dong bo neu co). */
    public long getTimeMs() { return timeMs; }
    /** [2d] vi the theo /fapi/v3/account; null = khong biet. */
    public List<PositionInfo> getPositions() { return positions; }

    public Optional<AssetBalance> asset(String name) {
        for (AssetBalance a : assets) if (a.getAsset() != null && a.getAsset().equals(name)) return Optional.of(a);
        return Optional.empty();
    }

    @Override
    public String toString() {
        return "AccountSnapshot{tmb=" + totalMarginBalance + " twb=" + totalWalletBalance + " avail=" + availableBalance
                + " upnl=" + totalUnrealizedProfit + " assets=" + assets.size() + "}";
    }
}
