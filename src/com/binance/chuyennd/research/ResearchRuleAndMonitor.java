/*
 * The MIT License
 *
 * Copyright 2023 pc.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */
package com.binance.chuyennd.research;

import com.binance.chuyennd.object.TickerStatistics;

import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.model.enums.OrderSide;
import java.util.List;
import org.apache.commons.lang3.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class ResearchRuleAndMonitor {

    public static final Logger LOG = LoggerFactory.getLogger(ResearchRuleAndMonitor.class);

    public ResearchRuleAndMonitor() {

    }

    public static void main(String[] args) {
        new ResearchRuleAndMonitor().startThreadFindAndChoiseSymbol2Research();
    }

    private void startThreadFindAndChoiseSymbol2Research() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadFindAndChoiseSymbol2Research");
            LOG.info("Start thread find and choise symbol 2 resarch!");
            while (true) {
                try {
                    // get top price increment
                    // get top price decrement
                    getTopPriceChange();
                    Thread.sleep(15 * Utils.TIME_MINUTE);
                } catch (Exception e) {
                    LOG.error("ERROR during find and choise symbol 2 res: {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }

    private void getTopPriceChange() {
        try {
            String allFuturePrices = HttpRequest.getContentFromUrl("https://fapi.binance.com/fapi/v1/ticker/24hr");
            List<Object> futurePrices = Utils.gson.fromJson(allFuturePrices, List.class);
            for (Object futurePrice : futurePrices) {
                TickerStatistics ticker = Utils.gson.fromJson(futurePrice.toString(), TickerStatistics.class);
                if (ticker.getLastPrice().equals(ticker.getHighPrice())) {
                    LOG.info("Symbol price api erorr: {}", ticker.getSymbol());
                } else {
                    // only get pair with usdt
                    if (StringUtils.endsWithIgnoreCase(ticker.getSymbol(), "usdt")) {
                        if (Double.parseDouble(ticker.getPriceChangePercent()) > 5) {
                            ResearchManager.getInstance().addNewOrder(ticker.getSymbol(), OrderSide.BUY, "TopPriceIncrement", Double.valueOf(ticker.getLastPrice()));
                        }
                        if (Double.parseDouble(ticker.getPriceChangePercent()) < -5) {
                            ResearchManager.getInstance().addNewOrder(ticker.getSymbol(), OrderSide.SELL, "TopPriceDecrement", Double.valueOf(ticker.getLastPrice()));
                        }
                    }
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
            LOG.info("Error during get symbol top price change");
        }
    }

}
