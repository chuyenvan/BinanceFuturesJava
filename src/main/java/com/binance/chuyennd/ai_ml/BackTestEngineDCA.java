package com.binance.chuyennd.ai_ml; // Dat cung package

import com.binance.chuyennd.research.BudgetManagerSimple;

public class BackTestEngineDCA {

    private final DcaOptimizationConfig dcaConfig;

    /**
     * Constructor: Nhan 9 tham so tu Jenetics
     */
    public BackTestEngineDCA(
            double rateLossBigDown, double rateLossMediumDown, double rateLossMediumUp,
            double rateLossSmallDown, double rateLossNull, double marginRate_1_5,
            double marginRate_2_0, double marginRate_2_5) {

        // 1. Tao doi tuong Config
        this.dcaConfig = new DcaOptimizationConfig();
        this.dcaConfig.rateLossBigDown = rateLossBigDown;
        this.dcaConfig.rateLossMediumDown = rateLossMediumDown;
        this.dcaConfig.rateLossMediumUp = rateLossMediumUp;
        this.dcaConfig.rateLossSmallDown = rateLossSmallDown;
        this.dcaConfig.rateLossNull = rateLossNull;
        this.dcaConfig.marginRate_1_5 = marginRate_1_5;
        this.dcaConfig.marginRate_2_0 = marginRate_2_0;
        this.dcaConfig.marginRate_2_5 = marginRate_2_5;
    }

    /**
     * Ham nay se duoc Jenetics goi hang nghin lan
     */
    public double run() {
        try {
            // 1. Reset cac Singleton
//            BudgetManagerSimple.resetInstance();
//
//
//            // 2. Khoi tao Simulator voi CONSTRUCTOR MOI
//            SimulatorMarketLevelTicker1MStopLoss test = new SimulatorMarketLevelTicker1MStopLoss(this.dcaConfig);
//
//            // 3. Chay backtest
//            test.initData();
//            test.simulatorWithInitEntry();

        } catch (Exception e) {
            e.printStackTrace();
            return 0.0; // Phat neu co loi
        }

        // 4. Tra ve loi nhuan
        return BudgetManagerSimple.getInstance().balanceCurrent;
    }
}