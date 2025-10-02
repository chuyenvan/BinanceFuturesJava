package com.binance.chuyennd.tradecore;

import com.binance.chuyennd.grid.SimpleMovingAverage4hManager;
import com.binance.chuyennd.grid.SimpleMovingAverageDayManager;
import com.binance.chuyennd.trading.SimpleMovingAverage4hManagerProduction;
import com.binance.chuyennd.trading.SimpleMovingAverageDayManagerProduction;
import com.binance.client.constant.Constants;

public class TrendDetector {

    public static Boolean isTrendBTC(Long time) {
        Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        if ((maDif1d != null && maDif1d > 0)
                || (maDif4h != null && maDif4h > 0)

        ) {
            return true;
        }
        return false;
    }

    public static Boolean isTrendETH(Long time) {
        Double maDif1d = SimpleMovingAverageDayManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_ETH, time);
        Double maDif4h = SimpleMovingAverage4hManager.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_ETH, time);
        if ((maDif1d != null && maDif1d > 0)
                || (maDif4h != null && maDif4h > 0)
        ) {
            return true;
        }
        return false;
    }

    public static boolean isETHTrendBuyProduction(Long time) {
        Double maDif1d = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_ETH, time);
        Double maDif4h = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_ETH, time);
        if ((maDif1d != null && maDif1d > 0)
                || (maDif4h != null && maDif4h > 0)) {
            return true;
        }
        return false;
    }

    public static boolean isBtcTrendBuyProduction( long time) {
        Double maDif1d = SimpleMovingAverageDayManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        Double maDif4h = SimpleMovingAverage4hManagerProduction.getInstance().getDifferenceMa10AndMa60(Constants.SYMBOL_PAIR_BTC, time);
        if ((maDif1d != null && maDif1d > 0)
                || (maDif4h != null && maDif4h > 0)
                ) {
            return true;
        }
        return false;

    }
}
