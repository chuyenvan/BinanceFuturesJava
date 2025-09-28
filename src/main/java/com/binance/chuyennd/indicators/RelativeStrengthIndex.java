package com.binance.chuyennd.indicators;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.RsiEntry;
import com.binance.chuyennd.utils.DoubleArrayUtils;

import java.util.List;

public class RelativeStrengthIndex {
    public static RsiEntry[] calculateRSI(List<KlineObjectNumber> candles, int periods) {
        RsiEntry[] rsiEntries;

        rsiEntries = new RsiEntry[candles.size() - periods];
        int idx = 0;

        double[] change = new double[candles.size()];
        double[] gain = new double[candles.size()];
        double[] loss = new double[candles.size()];
        double avgGain;
        double avgLoss;

        for (int i = 1; i < candles.size(); i++) {
            change[i] = candles.get(i).priceClose - candles.get(i - 1).priceClose;

            if (change[i] > 0)
                gain[i] = change[i];
            else if (change[i] < 0)
                loss[i] = change[i] * -1;

            if (i >= periods) {
                if (i == periods) {
                    avgGain = DoubleArrayUtils.avg(gain, 1, periods);
                    avgLoss = DoubleArrayUtils.avg(loss, 1, periods);
                } else {
                    avgGain = (rsiEntries[idx - 1].getAvgGain() * (periods - 1) + gain[i]) / periods;
                    avgLoss = (rsiEntries[idx - 1].getAvgLoss() * (periods - 1) + loss[i]) / periods;
                }
                double rs = avgGain / avgLoss;
                double rsi = 100 - (100 / (1 + rs));

                rsiEntries[idx] = new RsiEntry(candles.get(i));
                rsiEntries[idx].setChange(change[i]);
                rsiEntries[idx].setGain(gain[i]);
                rsiEntries[idx].setLoss(loss[i]);
                rsiEntries[idx].setAvgGain(avgGain);
                rsiEntries[idx].setAvgLoss(avgLoss);
                rsiEntries[idx].setRs(rs);
                rsiEntries[idx].setRsi(rsi);

                idx++;
            }

        }

        return rsiEntries;
    }

    public static Boolean isRsiSignalBuy(List<KlineObjectNumber> tickers, int index) {
        // tim điểm rsi lên 45 trước đó đã giảm dưới 30
        KlineObjectNumber ticker = tickers.get(index);
        int period = 40;
        if (ticker.rsi >= period
//                && ticker.histogram > 0
        ) {
            for (int i = index - 1; i >= 0; i--) {
                if (tickers.get(i).rsi != null && tickers.get(i).rsi >= period) {
                    return false;
                }
                if (tickers.get(i).rsi != null && tickers.get(i).rsi <= 25) {
                    return true;
                }
            }
        }
        return false;
    }

}
