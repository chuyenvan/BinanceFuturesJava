/*
 * Copyright 2023 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.client;

import com.binance.chuyennd.utils.Configs;
import com.binance.client.RequestOptions;
import com.binance.client.SyncRequestClient;
import com.binance.chuyennd.config.PrivateConfig;
import com.binance.client.model.market.ExchangeInfoEntry;
import com.binance.client.model.market.ExchangeInformation;
import com.binance.client.model.market.SymbolPrice;
import com.binance.client.model.trade.AccountBalance;
import com.google.gson.Gson; // Thêm thư viện Gson
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.Serializable;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.text.DecimalFormat;
import java.util.*;

/**
 * @author pc
 */
public class ClientSingleton implements Serializable {

    public static final Logger LOG = LoggerFactory.getLogger(ClientSingleton.class);

    // ĐƯỜNG DẪN FILE ĐỂ ĐỌC/GHI LOCAL
    // Đổi đường dẫn này thành "/kaggle/input/ten-dataset-cua-ban/exchange_info.json" khi chạy trên Kaggle
    public static final String EXCHANGE_INFO_PATH = "/kaggle/input/datasets/chuyendinh/java-dataset/exchange_info.data";
    public SyncRequestClient syncRequestClient;
    public Map<String, Float> symbol2UnitQuantity = new HashMap<>();
    public Map<String, Float> symbol2UnitTrade = new HashMap<>();
    public Map<String, Float> symbol2Notional = new HashMap<>();
    public Map<String, Float> symbol2UnitPrice = new HashMap<>();
    private static volatile ClientSingleton INSTANCE = null;

    public static ClientSingleton getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new ClientSingleton();
            INSTANCE.initClient();
        }
        return INSTANCE;
    }

    public void initClient() {
        File localFile = new File(EXCHANGE_INFO_PATH);
        List<ExchangeInfoEntry> symbols = null;
        Gson gson = new Gson();

        // 1. CỐ GẮNG LOAD TỪ FILE LOCAL (Dùng cho Kaggle)
        if (localFile.exists() && !localFile.isDirectory()) {
            LOG.info("Found local file {}. Loading Exchange Information from file (Offline Mode)...", EXCHANGE_INFO_PATH);
            try {
                String jsonContent = new String(Files.readAllBytes(Paths.get(EXCHANGE_INFO_PATH)));
                ExchangeInformation exchangeInfo = gson.fromJson(jsonContent, ExchangeInformation.class);
                symbols = exchangeInfo.getSymbols();
                LOG.info("Successfully loaded {} symbols from local file.", symbols.size());
            } catch (Exception e) {
                LOG.error("Error reading ExchangeInfo from local file. Will fallback to API.", e);
            }
        }

        // 2. NẾU KHÔNG CÓ FILE, GỌI API BINANCE (Dùng cho VPS)
        if (symbols == null) {
            LOG.info("Local file not found or failed to load. Connecting to Binance API...");
            RequestOptions options = new RequestOptions();
            syncRequestClient = SyncRequestClient.create(PrivateConfig.API_KEY, PrivateConfig.SECRET_KEY, options);
            symbols = syncRequestClient.getExchangeInformation().getSymbols();
            LOG.info("Successfully fetched Exchange Information from Binance API with {} symbols.", symbols.size());
        }

        // 3. PARSE DỮ LIỆU VÀO CACHE MAPS
        for (ExchangeInfoEntry symbol : symbols) {
            Float quantityUnit = getMinQty(symbol);
            if (quantityUnit != null) {
                symbol2UnitQuantity.put(symbol.getSymbol(), quantityUnit);
            }
            Float tickSize = getTickSize(symbol);
            if (tickSize != null) {
                symbol2UnitPrice.put(symbol.getSymbol(), tickSize);
            }
            Float notional = getNotional(symbol);
            if (notional != null) {
                symbol2Notional.put(symbol.getSymbol(), notional);
            }
        }
    }

    /**
     * HÀM MỚI: Dùng để chạy trên VPS 1 lần duy nhất, lấy data từ API và lưu thành file .json
     */
    public void dumpExchangeInfoToFile() {
        LOG.info("Dumping Exchange Information to file {} ...", EXCHANGE_INFO_PATH);
        try {
            RequestOptions options = new RequestOptions();
            SyncRequestClient tempClient = SyncRequestClient.create(PrivateConfig.API_KEY, PrivateConfig.SECRET_KEY, options);
            ExchangeInformation exchangeInfo = tempClient.getExchangeInformation();

            Gson gson = new Gson();
            String json = gson.toJson(exchangeInfo);
            Files.write(Paths.get(EXCHANGE_INFO_PATH), json.getBytes());

            LOG.info("Successfully dumped Exchange Information to local file!");
        } catch (Exception e) {
            LOG.error("Failed to dump Exchange Information", e);
        }
    }

    private Float getMinQty(ExchangeInfoEntry symbol) {
        for (List<Map<String, String>> filters : symbol.getFilters()) {
            for (Map<String, String> filter : filters) {
                if (filter.get("minQty") != null) {
                    return Float.valueOf(filter.get("minQty"));
                }
            }
        }
        return null;
    }

    public Float getNotional(ExchangeInfoEntry symbol) {
        for (List<Map<String, String>> filters : symbol.getFilters()) {
            for (Map<String, String> filter : filters) {
                if (filter.get("notional") != null) {
                    return Float.valueOf(filter.get("notional"));
                }
            }
        }
        return null;
    }

    private Float getTickSize(ExchangeInfoEntry symbol) {
        for (List<Map<String, String>> filters : symbol.getFilters()) {
            for (Map<String, String> filter : filters) {
                if (filter.get("tickSize") != null) {
                    return Float.valueOf(filter.get("tickSize"));
                }
            }
        }
        return null;
    }

    public Float getCurrentPrice(String symbol) {
        if (syncRequestClient == null) return null; // Tránh NullPointer khi chạy offline trên Kaggle
        List<SymbolPrice> datas = syncRequestClient.getSymbolPriceTicker(symbol);
        if (datas != null && !datas.isEmpty()) {
            return datas.get(0).getPrice().floatValue();
        }
        return null;
    }

    public Set<String> getAllSymbol() {
        // Đã sửa lại để lấy từ Local Cache thay vì gọi API (Giúp chạy offline tốt hơn)
        Set<String> symbols = new HashSet<>();
        for (String symbol : symbol2UnitQuantity.keySet()) {
            if (StringUtils.endsWithIgnoreCase(symbol, "usdt")) {
                symbols.add(symbol);
            }
        }
        return symbols;
    }

    public Float normalizeQuantity(String symbol, Float quantity) {
        Float stepSize = symbol2UnitQuantity.get(symbol); // minQty hoặc stepSize
        if (stepSize == null || stepSize <= 0) return quantity;

        try {
            java.math.BigDecimal bdQty = new java.math.BigDecimal(quantity.toString());
            java.math.BigDecimal bdStepSize = new java.math.BigDecimal(stepSize.toString());

            // normalizedQty = floor(qty / stepSize) * stepSize
            java.math.BigDecimal normalized = bdQty.divide(bdStepSize, 0, java.math.RoundingMode.FLOOR)
                    .multiply(bdStepSize);

            int scale = bdStepSize.stripTrailingZeros().scale();
            if (scale < 0) scale = 0;
            normalized = normalized.setScale(scale, java.math.RoundingMode.HALF_UP);

            return normalized.floatValue();
        } catch (Exception e) {
            return Float.valueOf(formatDouble(quantity));
        }
    }

    public Float normalizeQuantityTest(String symbol, Float quantity) {
        Float unitQuantity = symbol2UnitQuantity.get(symbol);
        if (unitQuantity != null) {
            quantity = quantity - (quantity % unitQuantity);
            if (quantity.toString().contains("0000") || quantity.toString().contains("9999")) {
                quantity = Float.valueOf(formatDouble(quantity));
            }
            return quantity;
        } else {
            return Float.valueOf(formatDouble(quantity));
        }
    }

    public Float normalizePrice(String symbol, Float price) {
        Float unitPrice = symbol2UnitPrice.get(symbol);
        if (unitPrice == null || unitPrice <= 0) {
            return price;
        }

        try {
            // Sử dụng BigDecimal để tránh sai số float
            java.math.BigDecimal bdPrice = new java.math.BigDecimal(price.toString());
            java.math.BigDecimal bdTickSize = new java.math.BigDecimal(unitPrice.toString());

            // Quy tắc: Price phải là bội số của tickSize
            // Công thức: normalizedPrice = floor(price / tickSize) * tickSize
            java.math.BigDecimal normalized = bdPrice.divide(bdTickSize, 0, java.math.RoundingMode.FLOOR)
                    .multiply(bdTickSize);

            // Đảm bảo không còn rác sau dấu phẩy bằng cách setScale theo tickSize
            int scale = bdTickSize.stripTrailingZeros().scale();
            if (scale < 0) scale = 0;
            normalized = normalized.setScale(scale, java.math.RoundingMode.HALF_UP);

            return normalized.floatValue();
        } catch (Exception e) {
            LOG.error("Error normalizing price for " + symbol, e);
            return price;
        }
    }

    public Float getMinQuantity(String symbol) {
        return symbol2UnitQuantity.get(symbol);
    }

    public Float getNotional(String symbol) {
        return symbol2Notional.get(symbol);
    }

    public static String formatDouble(Float revenue) {
        String format = "###.";
        Float check = revenue;
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
        // CÁCH SỬ DỤNG TRÊN VPS ĐỂ SINH FILE:
        ClientSingleton.getInstance().dumpExchangeInfoToFile();
    }

    public float getBalance() {
        if (syncRequestClient == null) return 0f; // Tránh NullPointer khi chạy offline
        List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
        for (AccountBalance balanceInfo : balanceInfos) {
            if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {
                float balance = balanceInfo.getBalance().floatValue();
                return balance;
            }
        }
        return 0f;
    }

    public float getBalanceAvalible() {
        if (syncRequestClient == null) return 0f; // Tránh NullPointer khi chạy offline
        List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
        for (AccountBalance balanceInfo : balanceInfos) {
            if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {
                float balance = balanceInfo.getAvailableBalance().floatValue();
                return balance;
            }
        }
        return 0f;
    }

    public float getRateBalanceAvalible() {
        if (syncRequestClient == null) return 0f; // Tránh NullPointer khi chạy offline
        List<AccountBalance> balanceInfos = ClientSingleton.getInstance().syncRequestClient.getBalance();
        for (AccountBalance balanceInfo : balanceInfos) {
            if (StringUtils.equalsIgnoreCase(balanceInfo.getAsset(), "usdt")) {
                return balanceInfo.getAvailableBalance().floatValue() / balanceInfo.getBalance().floatValue();
            }
        }
        return 0f;
    }
}