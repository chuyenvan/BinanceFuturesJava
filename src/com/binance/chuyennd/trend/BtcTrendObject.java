package com.binance.chuyennd.trend;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.TrendState;

import java.io.Serializable;

public class BtcTrendObject implements Serializable {
    public TrendState state;
    public KlineObjectNumber ticker;

    public BtcTrendObject(TrendState state, KlineObjectNumber ticker) {
        this.state = state;
        this.ticker = ticker;
    }
}
