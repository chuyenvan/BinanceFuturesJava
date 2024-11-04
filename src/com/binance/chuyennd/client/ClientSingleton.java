/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.client;

import com.binance.client.RequestOptions;
import com.binance.client.SyncRequestClient;
import com.binance.client.examples.constants.PrivateConfig;
import com.binance.client.model.market.ExchangeInfoEntry;
import com.binance.client.model.market.ExchangeInformation;
import com.binance.client.model.market.SymbolPrice;
import com.binance.client.model.trade.AccountBalance;
import java.text.DecimalFormat;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class ClientSingleton {

    public static final Logger LOG = LoggerFactory.getLogger(ClientSingleton.class);
    public SyncRequestClient syncRequestClient;
    public Map<String, Double> symbol2UnitQuantity = new HashMap<>();
    public Map<String, Double> symbol2Notional = new HashMap<>();
    public Map<String, Double> symbol2UnitPrice = new HashMap<>();
    private static volatile ClientSingleton INSTANCE = null;

    public static ClientSingleton getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new ClientSingleton();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    private void initClient() {
        RequestOptions options = new RequestOptions();
        syncRequestClient = SyncRequestClient.create(PrivateConfig.API_KEY, PrivateConfig.SECRET_KEY,
                options);
        for (ExchangeInfoEntry symbol : ClientSingleton.getInstance().syncRequestClient.getExchangeInformation().getSymbols()) {
            Double quantityUnit = getMinQty(symbol);
            if (quantityUnit != null) {
                symbol2UnitQuantity.put(symbol.getSymbol(), quantityUnit);
            }
            Double tickSize = getTickSize(symbol);
            if (tickSize != null) {
                symbol2UnitPrice.put(symbol.getSymbol(), tickSize);
            }
            Double notional = getNotional(symbol);
            if (notional != null){
                symbol2Notional.put(symbol.getSymbol(), notional);
            }
        }
    }

    private Double getMinQty(ExchangeInfoEntry symbol) {
        for (List<Map<String, String>> filters : symbol.getFilters()) {
            for (Map<String, String> filter : filters) {
                if (filter.get("minQty") != null) {
                    return Double.valueOf(filter.get("minQty"));
                }
            }
        }
        return null;
    }
    private Double getNotional(ExchangeInfoEntry symbol) {
        for (List<Map<String, String>> filters : symbol.getFilters()) {
            for (Map<String, String> filter : filters) {
                if (filter.get("notional") != null) {
                    return Double.valueOf(filter.get("notional"));
                }
            }
        }
        return null;
    }


    private Double getTickSize(ExchangeInfoEntry symbol) {
        for (List<Map<String, String>> filters : symbol.getFilters()) {
            for (Map<String, String> filter : filters) {
                if (filter.get("tickSize") != null) {
                    return Double.valueOf(filter.get("tickSize"));
                }
            }
        }
        return null;
    }

    public Double getCurrentPrice(String symbol) {
        List<SymbolPrice> datas = syncRequestClient.getSymbolPriceTicker(symbol);
        if (datas != null && !datas.isEmpty()) {
            return datas.get(0).getPrice().doubleValue();
        }
        return null;
    }

    public Set<String> getAllSymbol() {
        Set<String> symbols = new HashSet<>();
        ExchangeInformation exchangeInfo = syncRequestClient.getExchangeInformation();
        for (ExchangeInfoEntry symbol : exchangeInfo.getSymbols()) {
            if (StringUtils.endsWithIgnoreCase(symbol.getSymbol(), "usdt")) {
                symbols.add(symbol.getSymbol());
            }
        }
        return symbols;
    }

    public Double normalizeQuantity(String symbol, Double quantity) {
        Double unitQuantity = symbol2UnitQuantity.get(symbol);
        if (unitQuantity != null) {
            quantity = quantity - (quantity % unitQuantity);
            if (quantity.toString().contains("0000") || quantity.toString().contains("9999")) {
                quantity = Double.valueOf(formatDouble(quantity));
            }
            return quantity;
        } else {
            return Double.valueOf(formatDouble(quantity));
        }
    }

    public Double normalizePrice(String symbol, Double price) {
        Double unitPrice = symbol2UnitPrice.get(symbol);
        if (unitPrice != null) {
            price = price - (price % unitPrice);
            if (price.toString().contains("0000") || price.toString().contains("9999")) {
                price = Double.valueOf(formatDouble(price));
            }
            return price;
        } else {
            return Double.valueOf(formatDouble(price));
        }
    }

    public Double getMinQuantity(String symbol) {
        return symbol2UnitQuantity.get(symbol);
    }
    public Double getNotional(String symbol) {
        return symbol2Notional.get(symbol);
    }

    public static String formatDouble(Double revenue) {
        String format = "###.";
        Double check = revenue;
        int counter = 0;
        for (int i = 0; i < 10; i++) {
            if (check > 10000) {
                break;
            }
            check *= 10;
            format += "#";
            counter++;
        }
        if (counter == 0) {
            format = format.substring(0, format.length() - 1);
        }
        DecimalFormat formatter = new DecimalFormat(format);
        return formatter.format(revenue);
    }

    public static void main(String[] args) {
//        System.out.println(Utils.calPriceTarget("WOOUSDT", 0.37745, OrderSide.BUY, 0.005));
//        Double entry = 0.6715;
//        Double target = Utils.calPriceTarget("STORJUSDT", entry, OrderSide.BUY, 0.005);
//        Double rate = Utils.rateOf2Double(target, entry);
//        System.out.println(target + " -> " + rate);
//        
//        System.out.println(ClientSingleton.getInstance().getCurrentPrice("CVCUSDT"));
//        System.out.println(ClientSingleton.getInstance().getBalanceAvalible());
        System.out.println(ClientSingleton.getInstance().getRateBalanceAvalible());
    }

    public double getBalance() {
        List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
        for (AccountBalance balanceInfo : balanceInfos) {
            if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {
                double balance = balanceInfo.getBalance().doubleValue();
                return balance;
            }
        }
        return 0d;
    }

    public double getBalanceAvalible() {
        List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
        for (AccountBalance balanceInfo : balanceInfos) {
            if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {
                double balance = balanceInfo.getAvailableBalance().doubleValue();
                return balance;
            }
        }
        return 0d;
    }
    public double getRateBalanceAvalible() {
        List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
        for (AccountBalance balanceInfo : balanceInfos) {
            if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {                
                return balanceInfo.getAvailableBalance().doubleValue()/balanceInfo.getBalance().doubleValue();
            }
        }
        return 0d;
    }
}
