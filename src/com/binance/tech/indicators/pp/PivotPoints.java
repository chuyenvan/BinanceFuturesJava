package com.binance.tech.indicators.pp;


import com.binance.chuyennd.config.Labels;
import com.binance.tech.model.TechCandle;
import com.binance.tech.model.pp.PivotPointsEntry;
import com.binance.tech.util.CandleUtils;

public abstract class PivotPoints
{

	public PivotPointsEntry calculate(TechCandle[] candles, int periods)
	{
		if (candles.length < periods)
		{
			throw new IllegalArgumentException(Labels.NOT_ENOUGH_VALUES);
		}

		return calculate(CandleUtils.mergeCandles(candles, candles.length - periods, candles.length - 1));
	}

	public PivotPointsEntry calculate(TechCandle candle)
	{
		// System.out.println("-> " + candle);
		return calculate(candle.getOpenPrice(), candle.getHighPrice(), candle.getLowPrice(), candle.getClosePrice());
	}

	abstract PivotPointsEntry calculate(double open, double high, double low, double close);

}
