package com.binance.tech.indicators.volume;


import com.binance.chuyennd.config.Labels;
import com.binance.tech.model.TechCandle;
import com.binance.tech.model.indicators.IndicatorEntry;

/**
 * A/D - Accumulation / Distribution
 */
public class AccumulationDistribution
{

	public static IndicatorEntry[] calculate(TechCandle[] candles)
	{
		if (candles.length < 2)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		IndicatorEntry[] entries = new IndicatorEntry[candles.length];

		for (int i = 0; i < candles.length; i++)
		{
			TechCandle curr = candles[i];

			double mfm = ( (curr.getClosePrice() - curr.getLowPrice()) - (curr.getHighPrice() - curr.getClosePrice()) ) / ( curr.getHighPrice() - curr.getLowPrice() );
			double mfv = mfm * curr.getVolume();
			double ad = i > 0 ? entries[i - 1].getValue() + mfv : mfv;

			entries[i] = new IndicatorEntry(curr);
			entries[i].setValue(ad);
		}

		return entries;
	}

}
