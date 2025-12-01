package com.binance.chuyennd.ai_ml.extractor;

import java.util.Locale;

/**
 * Phien ban V18: Rut gon con 22 features (9 Market + 13 Symbol)
 */
public class FeatureRow {

    // === NHOM 1: MARKET & CONTEXT (9) ===
    public double btc_rate_change_15m;
    public double isTrendBuyWithBTC;
    public double isTrendBuyWithETH;
    public double market_rate_down_avg_15m;
    public double top_symbols_down_15m_count;
    public double hour_of_day_sin;
    public double hour_of_day_cos;
    public double day_of_week_sin;
    public double day_of_week_cos;

    // === NHOM 2: SYMBOL SPECIFIC (13) ===
    public double sym_rate_change_5m;
    public double sym_rate_change_15m;
    public double sym_rate_change_60m;
    public double sym_rate_vs_high_30m;
    public double sym_rate_vs_btc_15m;
    public double sym_rate_vs_eth_15m; // NEW
    public double sym_rsi_14_1m;
    public double sym_macd_hist_1m;
    public double sym_bb_width_20_1m;
    public double sym_bb_position_20_1m; // NEW
    public double sym_atr_14_1m_percent;
    public double sym_volume_1m_vs_sma_60m; // NEW
    public double sym_5m_candle_wick_ratio; // NEW

    // === LABELS (3) ===
    public double pnl_final;
    public double max_drawdown;
    public double time_to_profit;

    // === DEBUG INFO (2) ===
    public String debug_date;
    public String debug_symbol;
    public double debug_entry;         // <-- THEM DONG NAY
    public double debug_price_to_profit; // <-- THEM DONG NAY

    public String toCsvString() {
        return String.format(Locale.US,
                // Format (22 features + 3 labels + 4 debug)

                // Nhom 1 (9)
                "%.6f,%.1f,%.1f,%.6f,%.0f,%.6f,%.6f,%.6f,%.6f," +

                        // Nhom 2 (13)
                        "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," +
                        "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," +

                        "%.4f,%.4f,%.0f," + // Labels

                        // === SUA DONG NAY (4 cot debug) ===
                        "%s,%s,%.8f,%.8f",

                // === Variables (Nhom 1) ===
                btc_rate_change_15m,
                isTrendBuyWithBTC, isTrendBuyWithETH,
                market_rate_down_avg_15m, top_symbols_down_15m_count,
                hour_of_day_sin, hour_of_day_cos, day_of_week_sin, day_of_week_cos,

                // === Variables (Nhom 2) ===
                sym_rate_change_5m, sym_rate_change_15m, sym_rate_change_60m,
                sym_rate_vs_high_30m, sym_rate_vs_btc_15m, sym_rate_vs_eth_15m,
                sym_rsi_14_1m, sym_macd_hist_1m,
                sym_bb_width_20_1m, sym_bb_position_20_1m,
                sym_atr_14_1m_percent,
                sym_volume_1m_vs_sma_60m, sym_5m_candle_wick_ratio,

                // === Variables (Labels) ===
                pnl_final, max_drawdown, time_to_profit,

                // === Variables (Debug) (SUA LAI) ===
                debug_date, debug_symbol,
                debug_entry, debug_price_to_profit
        );
    }
}