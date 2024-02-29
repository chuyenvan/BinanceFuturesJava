/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid.enums;

/**
 *
 * @author pc
 */
public enum GridOrderStatus
{
	NEW("NEW"), 
        WAIT_SELL("SHORT"),
        WAIT_BUY("SHORT"),
        DONE("LONG");

	private final String code;

	GridOrderStatus(String side)
	{
		this.code = side;
	}

	@Override
	public String toString()
	{
		return code;
	}
}