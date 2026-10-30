package com.binance.chuyennd.c3live.api;

import java.math.BigDecimal;

/**
 * [V12 R4 R4] 1 dong lich su thu nhap tai khoan (GET /fapi/v1/income) — dung cho funding c3 THEO SYMBOL (stream
 * ACCOUNT_UPDATE FUNDING_FEE cua tai khoan cross chi co tong so du, khong theo symbol). Bat bien.
 */
public final class IncomeRecord {

    private final String symbol;
    private final String incomeType;
    private final BigDecimal income;
    private final String asset;
    private final long timeMs;
    private final String tranId;

    public IncomeRecord(String symbol, String incomeType, BigDecimal income, String asset, long timeMs, String tranId) {
        this.symbol = symbol;
        this.incomeType = incomeType;
        this.income = income;
        this.asset = asset;
        this.timeMs = timeMs;
        this.tranId = tranId;
    }

    public String getSymbol() { return symbol; }
    public String getIncomeType() { return incomeType; }
    public BigDecimal getIncome() { return income; }
    public String getAsset() { return asset; }
    public long getTimeMs() { return timeMs; }
    public String getTranId() { return tranId; }

    @Override
    public String toString() {
        return symbol + "/" + incomeType + "/" + income + " " + asset + "/" + timeMs + "/" + tranId;
    }
}
