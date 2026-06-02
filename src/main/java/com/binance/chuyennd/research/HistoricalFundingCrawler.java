package com.binance.chuyennd.research;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.*;

public class HistoricalFundingCrawler {
    private static final Logger LOG = LoggerFactory.getLogger(HistoricalFundingCrawler.class);

    public static void main(String[] args) {
        LOG.info("🚀 BẮT ĐẦU CÀO LỊCH SỬ FUNDING RATE TỪ 2021 ĐẾN NAY...");

        try {
            // Mốc bắt đầu: 01/01/2021
            long globalStart = Utils.sdfFile.parse("20210101").getTime();
            long globalEnd = System.currentTimeMillis();

            // Lấy danh sách Coin từ Redis
            List<String> symbols = new ArrayList<>();
            for (String s : RedisHelper.getInstance().readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS)) {
                String upperS = s.toUpperCase();
                if (!Constants.diedSymbol.contains(upperS) && StringUtils.endsWithIgnoreCase(upperS, "USDT") && upperS.matches("^[A-Z0-9]+$")) {
                    symbols.add(upperS);
                }
            }
            LOG.info("🎯 Tìm thấy {} symbols để cào lịch sử.", symbols.size());

            int count = 0;
            for (String symbol : symbols) {
                count++;
                Map<Long, Float> historicalRates = new TreeMap<>();
                long currentStart = globalStart;

                while (currentStart < globalEnd) {
                    try {
                        String url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=" + symbol +
                                "&startTime=" + currentStart + "&limit=1000";

                        String response = HttpRequest.getContentFromUrl(url, 5000);

                        if (StringUtils.isNotBlank(response) && response.startsWith("[")) {
                            JSONArray array = new JSONArray(response);
                            if (array.length() == 0) {
                                break; // Hết dữ liệu của coin này
                            }

                            for (int i = 0; i < array.length(); i++) {
                                JSONObject obj = array.getJSONObject(i);
                                long fundingTime = obj.getLong("fundingTime");
                                float fundingRate = obj.getFloat("fundingRate");

                                historicalRates.put(fundingTime, fundingRate);
                                currentStart = fundingTime + 1; // Nhích lên 1ms để cào trang tiếp theo
                            }
                        } else {
                            LOG.warn("⚠️ API báo lỗi hoặc hết data cho {}: {}", symbol, response);
                            break;
                        }

                        Thread.sleep(200); // Ngủ tránh Rate Limit

                    } catch (Exception e) {
                        LOG.error("❌ Lỗi cào Funding cho {}: {}", symbol, e.getMessage());
                        Thread.sleep(2000);
                    }
                }

                // Ghi vào Aerospike
                if (!historicalRates.isEmpty()) {
                    DataManagerAerospikeFloatSim.writeFundingMap(symbol, historicalRates);
                    LOG.info("✅ [{}/{}] Đã cào và lưu {} record Funding cho {}", count, symbols.size(), historicalRates.size(), symbol);
                } else {
                    LOG.info("⏩ [{}/{}] {} không có dữ liệu Funding.", count, symbols.size(), symbol);
                }
            }

            LOG.info("🎉 HOÀN TẤT CÀO LỊCH SỬ FUNDING FEE!");

        } catch (Exception e) {
            LOG.error("Lỗi Fatal: ", e);
        }
    }
}