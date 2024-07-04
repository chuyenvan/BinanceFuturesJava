package com.binance.tech.indicators.oscillator;


import com.binance.chuyennd.config.Labels;
import com.binance.tech.indicators.ma.ExponentialMovingAverage;
import com.binance.tech.model.TechCandle;
import com.binance.tech.model.indicators.IndicatorEntry;

/**
 * BBP - Bull Bear Power
 */
public class BullBearPower
{
	public static IndicatorEntry[] calculate(TechCandle[] candles)
	{
		return calculate(candles, 13);
	}

	public static IndicatorEntry[] calculate(TechCandle[] candles, int periods)
	{
		if (candles.length < periods)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		IndicatorEntry[] ema = ExponentialMovingAverage.calculate(candles, periods);

		IndicatorEntry[] uoEntries = new IndicatorEntry[ema.length];

		for (int i = 0; i < ema.length; i++)
		{
			double bullPower = ema[i].getHighPrice() - ema[i].getValue();
			double bearPower = ema[i].getLowPrice() - ema[i].getValue();
			double bbp = bullPower + bearPower;

			uoEntries[i] = new IndicatorEntry(ema[i]);
			uoEntries[i].setValue(bbp);
		}

		return uoEntries;
	}

}
