package com.binance.chuyennd.object;

import java.io.Serializable;

public class MarketDataObject implements Serializable {
    public float rateDownAvg;
    public float rateDown15MAvg;
    public float rateUpAvg;


    public MarketDataObject(Float rateDownAvg, Float rateUpAvg, Float rateDown15MAvg) {
        this.rateDownAvg = rateDownAvg;
        this.rateUpAvg = rateUpAvg;
        this.rateDown15MAvg = rateDown15MAvg;
    }


    public static MarketDataObject decodeMarketDataFromBinary(byte[] data) {
        if (data == null || data.length < 12) return null;
        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.wrap(data);
        // Lưu ý: Thứ tự getFloat phải khớp với thứ tự putFloat lúc encode
        return new MarketDataObject(
                buffer.getFloat(), // rateDownAvg
                buffer.getFloat(), // rateUpAvg
                buffer.getFloat()  // rateDown15MAvg
        );
    }
    public byte[] endCode() {
        // 3 biến float * 4 bytes = 12 bytes
        java.nio.ByteBuffer buffer = java.nio.ByteBuffer.allocate(12);
        buffer.putFloat(rateDownAvg);
        buffer.putFloat(rateUpAvg);
        buffer.putFloat(rateDown15MAvg);
        return buffer.array();
    }

}
