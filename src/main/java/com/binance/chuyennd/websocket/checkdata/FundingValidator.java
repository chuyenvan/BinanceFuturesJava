package com.binance.chuyennd.websocket.checkdata;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.*;
import java.util.stream.Collectors;

public class FundingValidator {
    private static final Logger LOG = LoggerFactory.getLogger(FundingValidator.class);
    public static final String URL_PREMIUM_INDEX = "https://fapi.binance.com/fapi/v1/premiumIndex";

    public static void main(String[] args) {
        FundingValidator validator = new FundingValidator();
        // 1. Đối soát dữ liệu
        validator.validateFunding(200);
// 2. Đối soát ngẫu nhiên 10 file từ storage vs Aerospike (Code mới)
        String storagePath = "../storage/funding_fee/";
        validator.validateRandomFiles(storagePath, 10);

        // 3. In mẫu dữ liệu
        validator.printSampleHistoricalFunding(5);
    }

    public void validateFunding(int limit) {
        LOG.info("🚀 BẮT ĐẦU ĐỐI SOÁT FUNDING RATE (CHỈ CẶP USDT)");

        List<String> allSymbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> s.toUpperCase().endsWith("USDT"))
                .filter(s -> !Constants.diedSymbol.contains(s.toUpperCase()))
                .filter(s -> s.toUpperCase().matches("^[A-Z0-9]+$"))
                .limit(limit)
                .collect(Collectors.toList());

        Map<String, Float> apiFundingRates = new HashMap<>();
        try {
            String response = HttpRequest.getContentFromUrl(URL_PREMIUM_INDEX);
            List<Map<String, Object>> objects = Utils.gson.fromJson(response, List.class);

            for (Map<String, Object> data : objects) {
                String symbol = data.get("symbol").toString().toUpperCase();
                if (symbol.endsWith("USDT")) {
                    float lastFundingRate = Float.parseFloat(data.get("lastFundingRate").toString());
                    apiFundingRates.put(symbol, lastFundingRate);
                }
            }
        } catch (Exception e) {
            LOG.error("❌ Lỗi gọi API premiumIndex: {}", e.getMessage());
            return;
        }

        int totalMatches = 0;
        int totalChecks = 0;

        for (String symbol : allSymbols) {
            String upperS = symbol.toUpperCase();
            Float apiRate = apiFundingRates.get(upperS);
            if (apiRate == null) continue;

            Map<Long, Float> asFundingMap = DataManagerAerospikeFloatSim.getFundingMap(upperS);

            if (asFundingMap != null && !asFundingMap.isEmpty()) {
                totalChecks++;
                Long latestTs = Collections.max(asFundingMap.keySet());
                Float asRate = asFundingMap.get(latestTs);

                boolean isMatch = Math.abs(apiRate - asRate) < 0.00000001;
                if (isMatch) totalMatches++;
                else {
                    LOG.warn("[{}] ❌ Lệch: API={} | AS={} (Kỳ: {})",
                            upperS, apiRate, asRate, Utils.normalizeDateYYYYMMDDHHmm(latestTs));
                }
            }
        }
        LOG.info("📊 TỔNG KẾT: Khớp {}/{} mã USDT ({}%)",
                totalMatches, totalChecks, String.format("%.2f", (totalChecks > 0 ? (totalMatches * 100.0 / totalChecks) : 0)));
    }

    /**
     * In toàn bộ lịch sử Funding đang có trong Aerospike của N mã bất kỳ
     */
    public void printSampleHistoricalFunding(int sampleLimit) {
        LOG.info("📂 IN MẪU DỮ LIỆU LỊCH SỬ FUNDING TRONG AEROSPIKE");

        List<String> symbols = RedisHelper.getInstance()
                .readAllId(RedisConst.REDIS_KEY_BINANCE_ALL_SYMBOLS).stream()
                .filter(s -> s.toUpperCase().endsWith("USDT"))
                .limit(sampleLimit)
                .collect(Collectors.toList());

        for (String symbol : symbols) {
            String upperS = symbol.toUpperCase();
            Map<Long, Float> asFundingMap = DataManagerAerospikeFloatSim.getFundingMap(upperS);

            LOG.info("--------------------------------------------------");
            LOG.info("📝 Symbol: {} (Số kỳ ghi nhận: {})", upperS, asFundingMap.size());

            if (asFundingMap.isEmpty()) {
                LOG.warn("   ⚠️ Không có dữ liệu.");
                continue;
            }

            // Sắp xếp theo thời gian tăng dần để in
            TreeMap<Long, Float> sortedMap = new TreeMap<>(asFundingMap);

            LOG.info("   [🕒 {}] Rate: {}", Utils.normalizeDateYYYYMMDDHHmm(sortedMap.firstKey()),
                    String.format("%.8f", sortedMap.firstEntry().getValue()));

        }
        LOG.info("--------------------------------------------------");
    }

    /**
     * Đối soát ngẫu nhiên dữ liệu giữa File System và Aerospike
     *
     * @param folderPath  Đường dẫn thư mục chứa file .data
     * @param randomCount Số lượng file muốn chọn ngẫu nhiên để kiểm tra
     */
    public void validateRandomFiles(String folderPath, int randomCount) {
        LOG.info("🚀 BẮT ĐẦU ĐỐI SOÁT NGẪU NHIÊN: FILE SYSTEM vs AEROSPIKE");
        File folder = new File(folderPath);
        if (!folder.exists() || !folder.isDirectory()) {
            LOG.error("❌ Thư mục không tồn tại: {}", folderPath);
            return;
        }

        File[] allFiles = folder.listFiles();
        if (allFiles == null || allFiles.length == 0) {
            LOG.warn("⚠️ Không có file nào để kiểm tra.");
            return;
        }

        // Lấy danh sách file và xáo trộn để chọn ngẫu nhiên
        List<File> fileList = new ArrayList<>(Arrays.asList(allFiles));
        Collections.shuffle(fileList);
        List<File> targetFiles = fileList.stream().limit(randomCount).collect(Collectors.toList());

        int totalFilesChecked = 0;
        int filesMatch = 0;

        for (File file : targetFiles) {
            try {
                String symbol = file.getName().toUpperCase();

                // 1. Đọc dữ liệu từ File (Dữ liệu gốc)
                Object rawData = com.binance.chuyennd.utils.Storage.readObjectFromFile(file.getAbsolutePath());
                if (!(rawData instanceof TreeMap)) continue;

                TreeMap<Long, com.binance.client.model.market.FundingRate> fileData =
                        (TreeMap<Long, com.binance.client.model.market.FundingRate>) rawData;

                // 2. Đọc dữ liệu từ Aerospike
                Map<Long, Float> asData = DataManagerAerospikeFloatSim.getFundingMap(symbol);

                totalFilesChecked++;
                LOG.info("--------------------------------------------------");
                LOG.info("📄 Kiểm tra Symbol: {} (File: {} records | AS: {} records)",
                        symbol, fileData.size(), asData.size());

                if (asData.isEmpty()) {
                    LOG.error("   ❌ Thất bại: Aerospike không có dữ liệu cho {}", symbol);
                    continue;
                }

                // 3. Đối soát từng mốc thời gian
                boolean isAllMatch = true;
                int matchInFileCount = 0;

                for (Map.Entry<Long, com.binance.client.model.market.FundingRate> entry : fileData.entrySet()) {
                    Long ts = entry.getKey();
                    Float fileRate = entry.getValue().getFundingRate().floatValue();
                    Float asRate = asData.get(ts);

                    if (asRate == null) {
                        LOG.warn("   ⚠️ Thiếu mốc TS {} trong AS", Utils.normalizeDateYYYYMMDDHHmm(ts));
                        isAllMatch = false;
                    } else if (Math.abs(fileRate - asRate) > 0.00000001) {
                        LOG.error("   ❌ Sai lệch tại {}: File={} | AS={}",
                                Utils.normalizeDateYYYYMMDDHHmm(ts), fileRate, asRate);
                        isAllMatch = false;
                    } else {
                        matchInFileCount++;
                    }
                }

                if (isAllMatch && fileData.size() <= asData.size()) {
                    filesMatch++;
                    LOG.info("   ✅ Khớp hoàn toàn {}/{} mốc thời gian.", matchInFileCount, fileData.size());
                } else {
                    LOG.warn("   ⚠️ Khớp {}/{} mốc thời gian (Có sự sai khác về số lượng hoặc giá trị).",
                            matchInFileCount, fileData.size());
                }

            } catch (Exception e) {
                LOG.error("❌ Lỗi khi xử lý file {}: {}", file.getName(), e.getMessage());
            }
        }

        LOG.info("==================================================");
        LOG.info("📊 TỔNG KẾT ĐỐI SOÁT FILE: Khớp {}/{} file ngẫu nhiên.", filesMatch, totalFilesChecked);
    }
}