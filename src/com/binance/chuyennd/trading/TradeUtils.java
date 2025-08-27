package com.binance.chuyennd.trading;

import com.binance.chuyennd.utils.Configs;

public class TradeUtils {
    public static Double calRateMinWithMaxChange15M(Double maxChange15M) {
        Double rateMin2MoveSl = Configs.RATE_PROFIT_STOP_MARKET;
        if (maxChange15M != null && maxChange15M > 0.006) {
            if (maxChange15M < 0.01) {
                if (rateMin2MoveSl < 0.02) {
                    rateMin2MoveSl = 0.02;
                }
            } else {
                if (maxChange15M < 0.02) {
                    if (rateMin2MoveSl < 0.025) {
                        rateMin2MoveSl = 0.025;
                    }
                } else {
                    if (maxChange15M < 0.03) {
                        if (rateMin2MoveSl < 0.04) {
                            rateMin2MoveSl = 0.04;
                        }
                    } else {
                        if (rateMin2MoveSl < 0.06) {
                            rateMin2MoveSl = 0.06;
                        }
                    }
                }
            }
        } else {
            if (maxChange15M != null && maxChange15M > 0.004) {
                if (rateMin2MoveSl < 0.015) {
                    rateMin2MoveSl = 0.015;
                }
            }
        }
        return rateMin2MoveSl;
    }

}
