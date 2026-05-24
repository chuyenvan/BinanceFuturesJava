package com.binance.chuyennd.object;

import java.io.Serializable;
import java.nio.ByteBuffer;

public class MarketDataObject15M implements Serializable {
    public float rateDownAvg;
    public float rateUpAvg;
    public float rateDown4HAvg; // Đổi từ 15M sang 4H

    public MarketDataObject15M(Float rateDownAvg, Float rateUpAvg, Float rateDown4HAvg) {
        this.rateDownAvg = rateDownAvg;
        this.rateUpAvg = rateUpAvg;
        this.rateDown4HAvg = rateDown4HAvg;
    }

    public static MarketDataObject15M decodeMarketDataFromBinary(byte[] data) {
        if (data == null || data.length < 12) return null;
        ByteBuffer buffer = ByteBuffer.wrap(data);
        return new MarketDataObject15M(
                buffer.getFloat(), // rateDownAvg
                buffer.getFloat(), // rateUpAvg
                buffer.getFloat()  // rateDown4HAvg
        );
    }

    public byte[] endCode() {
        ByteBuffer buffer = ByteBuffer.allocate(12);
        buffer.putFloat(rateDownAvg);
        buffer.putFloat(rateUpAvg);
        buffer.putFloat(rateDown4HAvg);
        return buffer.array();
    }
}