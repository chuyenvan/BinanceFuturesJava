package com.binance.chuyennd.indicators;


import com.binance.chuyennd.config.Labels;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.CandleUtils;
import com.binance.chuyennd.utils.DoubleArrayUtils;

import java.util.List;

/**
 * SMA - Simple Moving Average
 */
public class SimpleMovingAverage
{

	public static double[] calculate(double[] values, int periods)
	{
		if (values.length < periods)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		int len = values.length - periods + 1;
		double[] results = new double[len];

		for (int i = 0; i < len; i++)
		{
			results[i] = DoubleArrayUtils.avg(values, i, i + periods - 1);
		}

		return results;
	}
	public static IndicatorEntry[] calculate(List<KlineObjectNumber> candles, int periods)
	{
		if (candles.size() < periods)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		int len = candles.size() - periods + 1;
		IndicatorEntry[] smaEntries = new IndicatorEntry[len];

		for (int i = 0; i < len; i++)
		{
			smaEntries[i] = new IndicatorEntry(candles.get(i + periods - 1));
			smaEntries[i].setValue(CandleUtils.avgPrice(candles, i, i + periods - 1));
		}

		return smaEntries;
	}

}
