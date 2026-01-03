package com.binance.chuyennd.websocket;

public class BinanceDataIngestor {
    public static void main(String[] args) {
        new FundingIngestor2Aerospike().start();
        new TickerIngestor2Aerospike().start();
    }
}
