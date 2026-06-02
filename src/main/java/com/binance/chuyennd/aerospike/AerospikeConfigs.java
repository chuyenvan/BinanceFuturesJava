package com.binance.chuyennd.aerospike;

import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.proto.MinuteDataProto;

import java.text.SimpleDateFormat;
import java.util.Map;
import java.util.TimeZone;

public class AerospikeConfigs {
    public static final SimpleDateFormat keyFormat = new SimpleDateFormat("yyyyMMdd-HHmm");
    public static final WritePolicy writePolicy = new WritePolicy();

    // 🕐 Lớp 1: pin tz GMT+7 cho key formatter Aerospike — không phụ thuộc tz mặc định JVM.
    static {
        keyFormat.setTimeZone(TimeZone.getTimeZone("GMT+7"));
    }

    public static byte[] convertMapToProtoBytes(Map<String, KlineObjectSimple> javaMap) {
        // ... (Ham nay giu nguyen nhu cu) ...
        MinuteDataProto.MinuteData.Builder minuteBuilder = MinuteDataProto.MinuteData.newBuilder();
        for (Map.Entry<String, KlineObjectSimple> entry : javaMap.entrySet()) {
            String symbol = entry.getKey();
            KlineObjectSimple javaTicker = entry.getValue();
            MinuteDataProto.KlineObjectSimpleProto.Builder protoTickerBuilder = MinuteDataProto.KlineObjectSimpleProto.newBuilder()
                    .setStartTime(javaTicker.startTime)
                    .setPriceOpen(javaTicker.priceOpen)
                    .setMaxPrice(javaTicker.maxPrice)
                    .setMinPrice(javaTicker.minPrice)
                    .setPriceClose(javaTicker.priceClose)
                    .setTotalUsdt(javaTicker.totalUsdt);
            minuteBuilder.putTickers(symbol, protoTickerBuilder.build());
        }
        return minuteBuilder.build().toByteArray();
    }
}
