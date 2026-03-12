package com.binance.chuyennd.utils;

import java.util.Collection;

public class DoubleArrayUtils
{

	public static int maxIndex(float[] values, int startIndex, int endIndex)
	{
		float value = values[startIndex];
		int index = startIndex;

		for (int i = startIndex; i <= endIndex; i++)
		{
			if (values[i] > value)
			{
				value = values[i];
				index = i;
			}
		}

		return index;
	}

	public static float maxValue(float[] values, int startIndex, int endIndex)
	{
		float value = values[startIndex];

		for (int i = startIndex; i <= endIndex; i++)
		{
			if (values[i] > value)
			{
				value = values[i];
			}
		}

		return value;
	}

	public static int minIndex(float[] values, int startIndex, int endIndex)
	{
		float value = values[startIndex];
		int index = startIndex;

		for (int i = startIndex; i <= endIndex; i++)
		{
			if (values[i] < value)
			{
				value = values[i];
				index = i;
			}
		}

		return index;
	}

	public static float minValue(float[] values, int startIndex, int endIndex)
	{
		float value = values[startIndex];

		for (int i = startIndex; i <= endIndex; i++)
		{
			if (values[i] < value)
			{
				value = values[i];
			}
		}

		return value;
	}

	public static float sum(float[] values, int startIndex, int endIndex)
	{
		float sum = 0;
		for (int i = startIndex; i <= endIndex; i++)
		{
			sum += values[i];
		}
		return sum;
	}

	public static float avg(float[] values, int startIndex, int endIndex)
	{
		float sum = 0;
		for (int i = startIndex; i <= endIndex; i++)
		{
			sum += values[i];
		}
		return sum / (endIndex - startIndex + 1);
	}
	public static float avg(Collection<Float> values)
	{
		float sum = 0;
		for (Float value:values)
		{
			sum += value;
		}
		return sum / (values.size());
	}

	public static float[] slice(float[] values, int startIndex, int endIndex)
	{
		float[] newCandles = new float[endIndex - startIndex + 1];
		for (int i = startIndex; i <= endIndex; i++)
		{
			newCandles[i - startIndex] = values[i];
		}
		return newCandles;
	}

}
