package com.binance.chuyennd.ai_ml.features.export.funding;

import java.io.Serializable;

public class FundingMarketFeatures implements Serializable {
    // --- TRỤC THỜI GIAN (KHÔNG phải feature train; chỉ để split theo thời gian + purge gap) ---
    public long timestamp;
    public String symbol;

    // --- GROUP 1: MARKET CONTEXT ---
    public float btcMomentum1H;
    public float btcMomentum4H;
    public float btcMomentum24H;
    public float btcDominance;
    public float marketBreadthStrength;

    // --- GROUP 2: MARKET-RATEDOWN + COIN SPECIFIC ---
    public float rateDownAvg;    // market-MDO rateDownAvg (cũ: momentum1M — nhãn coin SAI, thực là market)
    public float rateDown15MAvg; // market-MDO rateDown15MAvg (cũ: momentum15M — nhãn coin SAI, thực là market)
    public float momentum1H;
    public float momentum4H;
    public float momentum24H;
    public float rsi1H;
    public float distFromLow24H;
    public float volatilityShock;

    // --- GROUP 3: BASKET SPECIFIC ---
    public float basketMomentum15M;
    public float basketMomentum1H;
    public float basketMomentum24H;
    public float basketRsi14;
    public float basketVolSpike;

    // --- GROUP 4: FUNDING FEE ---
    public float coinFundingRate;
    public float basketFundingAvg;
    public float fundingRateAvg24H;
    public float fundingRateTrend;

    // =====================================================================
    // --- TASK-037 (F3): FEATURE MỚI — APPEND-ONLY (#22..#35) ---
    // Thứ tự KHÓA (xem docs/reports/037.md): KHÔNG chèn giữa, KHÔNG đổi 21 feature cũ.
    // Giá trị KHÔNG tính được (warmup/thiếu data) = Float.NaN (KHÔNG fill-0).
    // =====================================================================
    // A. Funding sâu per-coin (expanding ≤t từ lịch sử funding riêng coin, no-leak)
    public float fundingPercentileCoin; // #22 percentile của funding hiện tại trong lịch sử coin (≤t)
    public float fundingZCoin;          // #23 (funding − mean_lichsu)/std_lichsu (≤t)
    public float fundingPersistence;    // #24 số kỳ funding liên tiếp CÙNG DẤU (run-length, gồm kỳ hiện tại)
    public float fundingSum24h;         // #25 tổng funding các kỳ settle trong 24h gần (t-24h, t]
    public float fundingAbs;            // #26 |funding hiện tại|
    // B. Volume per-coin
    public float volumeZCoin;           // #27 (volume nến hiện tại − mean20)/std20
    public float volumeTrend;           // #28 avgVol ngắn(5) / avgVol dài(60)
    // C. Cấu trúc giá per-coin (từ kline ≤t)
    public float distFromHigh24H;       // #29 (high24h − close)/high24h
    public float rangePosition24H;      // #30 (close − low24h)/(high24h − low24h) ∈ [0,1]
    public float atrSqueeze;            // #31 ATR ngắn(14)/ATR dài(100); <1 = nén
    public float relStrengthBtc24H;     // #32 return_coin_24h − return_btc_24h
    // D. Cross-sectional (so coin CÙNG mốc t — tính ở PASS 2 trong export tool)
    public float fundingRankCS;         // #33 rank-percentile coinFundingRate cross-coin
    public float volumeZRankCS;         // #34 rank-percentile volumeZCoin cross-coin
    public float momentumRankCS;        // #35 rank-percentile momentum24H cross-coin

    // =====================================================================
    // --- TASK-038 (F4): APPEND-ONLY (#36..#45). Thứ tự KHÓA (xem docs/reports/038.md).
    //     NaN khi thiếu data (KHÔNG fill-0). KHÔNG đổi #1..#35.
    // =====================================================================
    // E. Microstructure 1m per-coin (tổng hợp từ nến 1m ≤t)
    public float ret15m;            // #36 return 15 phút gần
    public float rvol15m;           // #37 std của return 1m trong 15 nến gần (sôi động tức thời)
    public float volumeZ5m;         // #38 volume 5m gần / nền (sumVol5 / (avgVol20*5))
    public float closePosRange15m;  // #39 (close − low15)/(high15 − low15) ∈ [0,1]
    public float wickRatio15m;      // #40 bấc trên trung bình 15 nến (rejection)
    // F. OI/LS/taker per-coin (đọc 5 set metrics 013; set ở PASS export, KHÔNG ở extractor)
    public float oiDelta24hCoin;    // #41 Δ% OI coin vs t-24h
    public float oiZCoin;           // #42 z-score OI hiện tại vs lịch sử coin (expanding ≤t)
    public float lsGlobalCoin;      // #43 long/short global accounts của coin
    public float lsToptraderCoin;   // #44 long/short top-trader của coin
    public float takerBuyRatioCoin; // #45 taker buy/(buy+sell) của coin

    // --- LABELS (TARGET) ---
    // 0: Fail, 1: 72H, 2: 24H, 3: 4H, 4: 15M
    public int label6;   // Target 6%
    public int label40;  // Target 40%
}