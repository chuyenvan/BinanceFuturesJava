/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid.enums;

/**
 *
 * @author pc
 */
public enum PositionSide
{
	BOTH("BOTH"), SHORT("SHORT"), LONG("LONG");

	private final String code;

	PositionSide(String side)
	{
		this.code = side;
	}

	@Override
	public String toString()
	{
		return code;
	}
}