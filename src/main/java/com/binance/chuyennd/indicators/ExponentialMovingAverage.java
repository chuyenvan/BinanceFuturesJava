package com.binance.chuyennd.indicators;


import com.binance.chuyennd.config.Labels;
import com.binance.chuyennd.object.IndicatorEntry;
import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.utils.DoubleArrayUtils;

import java.util.List;

/**
 * EMA - Exponential Moving Average
 */
public class ExponentialMovingAverage
{
	
	public static double[] calculate(double[] values, int periods)
	{
		if (values.length < periods)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		int len = values.length - periods + 1;
		double[] emaEntries = new double[len];

		double smoothing = 2d / (periods + 1);

		for (int i = 0; i < len; i++)
		{
			if (i == 0)
			{
				double[] slice = DoubleArrayUtils.slice(values, 0, periods - 1);
				double[] smaEntries = SimpleMovingAverage.calculate(slice, periods);
				double smaEntry = smaEntries[smaEntries.length - 1];
				emaEntries[i] = smaEntry;
			}
			else
			{
				emaEntries[i] = values[i + periods - 1] * smoothing + emaEntries[i - 1] * (1 - smoothing);
			}
		}

		return emaEntries;
	}

	public static IndicatorEntry[] calculate(List<KlineObjectNumber> candles, int periods)
	{
		if (candles.size() < periods)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		int len = candles.size() - periods + 1;
		IndicatorEntry[] emaEntries = new IndicatorEntry[len];

		double smoothing = 2d / (periods + 1);

		for (int i = 0; i < len; i++)
		{
			emaEntries[i] = new IndicatorEntry(candles.get(i + periods - 1));

			if (i == 0)
			{
				IndicatorEntry[] smaEntries = SimpleMovingAverage.calculate(candles, periods);
				double smaEntry = smaEntries[smaEntries.length - 1].getValue();
				emaEntries[i].setValue(smaEntry);
			}
			else
			{
				double emaEntry = candles.get(i + periods - 1).getDefaultPrice() * smoothing + emaEntries[i - 1].getValue() * (1 - smoothing);
				emaEntries[i].setValue(emaEntry);
			}
		}

		return emaEntries;
	}
	public static IndicatorEntry[] calculateSimple(List<KlineObjectSimple> candles, int periods)
	{
		if (candles.size() < periods)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		int len = candles.size() - periods + 1;
		IndicatorEntry[] emaEntries = new IndicatorEntry[len];

		double smoothing = 2d / (periods + 1);

		for (int i = 0; i < len; i++)
		{
			emaEntries[i] = new IndicatorEntry(candles.get(i + periods - 1));

			if (i == 0)
			{
				IndicatorEntry[] smaEntries = SimpleMovingAverage.calculateSimple(candles, periods);
				double smaEntry = smaEntries[smaEntries.length - 1].getValue();
				emaEntries[i].setValue(smaEntry);
			}
			else
			{
				double emaEntry = candles.get(i + periods - 1).getDefaultPrice() * smoothing + emaEntries[i - 1].getValue() * (1 - smoothing);
				emaEntries[i].setValue(emaEntry);
			}
		}

		return emaEntries;
	}

}
