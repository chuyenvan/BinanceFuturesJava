package com.binance.chuyennd.ai_ml.extractor;

import java.util.Locale;

public class FeatureRow {

    // === NHOM 1: BTC TRIGGER (9) ===
    public double btc_rate_change_1m;
    public double btc_rate_change_5m;
    public double btc_rate_change_15m;
    public double btc_rate_vs_high_15m;
    public double btc_rate_vs_high_30m;
    public double btc_rate_vs_high_60m;
    public double btc_rate_vs_low_15m;
    public double btc_volume_1m_vs_sma_60m;
    public double btc_5m_candle_wick_ratio;

    // === NHOM 2: MACRO TREND (2) ===
    public double isTrendBuyWithBTC;
    public double isTrendBuyWithETH;

    // === NHOM 3: BTC MOMENTUM (6) ===
    public double btc_rsi_14_1m;
    public double btc_macd_hist_1m;
    public double btc_bb_width_20_1m;
    public double eth_rsi_14_1m;
    public double eth_macd_hist_1m;
    public double eth_bb_width_20_1m;

    // === NHOM 4: MARKET CONTEXT (5) ===
    public double market_rate_down_avg_1m;
    public double market_rate_down_avg_15m;
    public double market_rate_up_avg_1m;
    public double corr_btc_eth_1h;
    public double top_symbols_down_15m_count;

    // === NHOM 5: TIME (4) ===
    public double hour_of_day_sin;
    public double hour_of_day_cos;
    public double day_of_week_sin;
    public double day_of_week_cos;

    // === NHOM 6: SYMBOL SPECIFIC (9) ===
    // (Da xoa sym_volume_vs_sma_60m)
    public double sym_rate_change_1m;
    public double sym_rate_change_5m;
    public double sym_rate_change_15m;
    public double sym_rate_vs_high_30m;
    public double sym_rate_vs_btc_15m;
    public double sym_rsi_14_1m;
    public double sym_macd_hist_1m;
    public double sym_bb_width_20_1m;
    public double sym_atr_14_1m_percent;

    // === LABELS (3) ===
    public double pnl_final;
    public double max_drawdown;
    public double time_to_profit;

    // === DEBUG INFO (2) ===
    public String debug_date;
    public String debug_symbol;

    public String toCsvString() {
        return String.format(Locale.US,
                // Format (35 features + 3 labels + 2 debug)
                "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," + // Nhom 1
                        "%.1f,%.1f," + // Nhom 2
                        "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," + // Nhom 3
                        "%.6f,%.6f,%.6f,%.6f,%.0f," + // Nhom 4
                        "%.6f,%.6f,%.6f,%.6f," + // Nhom 5
                        "%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f,%.6f," + // Nhom 6 (9 features)
                        "%.4f,%.4f,%.0f," + // Labels
                        "%s,%s", // Debug Info

                // Variables
                btc_rate_change_1m, btc_rate_change_5m, btc_rate_change_15m,
                btc_rate_vs_high_15m, btc_rate_vs_high_30m, btc_rate_vs_high_60m, btc_rate_vs_low_15m,
                btc_volume_1m_vs_sma_60m, btc_5m_candle_wick_ratio,

                isTrendBuyWithBTC, isTrendBuyWithETH,

                btc_rsi_14_1m, btc_macd_hist_1m, btc_bb_width_20_1m,
                eth_rsi_14_1m, eth_macd_hist_1m, eth_bb_width_20_1m,

                market_rate_down_avg_1m, market_rate_down_avg_15m, market_rate_up_avg_1m,
                corr_btc_eth_1h, top_symbols_down_15m_count,

                hour_of_day_sin, hour_of_day_cos, day_of_week_sin, day_of_week_cos,

                // Nhom 6
                sym_rate_change_1m, sym_rate_change_5m, sym_rate_change_15m,
                sym_rate_vs_high_30m, sym_rate_vs_btc_15m,
                sym_rsi_14_1m, sym_macd_hist_1m, sym_bb_width_20_1m,
                sym_atr_14_1m_percent,

                pnl_final, max_drawdown, time_to_profit,

                debug_date, debug_symbol
        );
    }
}