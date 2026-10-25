package com.binance.chuyennd.c3live.api;

/**
 * [V12] REGULAR = /fapi/v1/order (MARKET...). ALGO = /fapi/v1/algoOrder (STOP_MARKET dieu kien, theo luat moi cua san:
 * lenh dieu kien di qua Algo Service; orderId = algoId, clientOrderId = clientAlgoId).
 */
public enum OrderKind { REGULAR, ALGO }
