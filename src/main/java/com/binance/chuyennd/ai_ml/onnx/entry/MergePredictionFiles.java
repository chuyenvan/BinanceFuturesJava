package com.binance.chuyennd.ai_ml.onnx.entry;

import com.binance.chuyennd.ai_ml.onnx.AiPredictionData;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.StorageSnappy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.util.Calendar;
import java.util.TreeMap;

public class MergePredictionFiles {
    private static final Logger LOG = LoggerFactory.getLogger(MergePredictionFiles.class);

    // Tên file đầu ra cuối cùng (file tổng)
    private static final String FINAL_OUTPUT_FILE = Configs.FILE_AI_ENTRY_PREDICTIONS + "_FULL";

    public static void main(String[] args) {
        new MergePredictionFiles().mergeAllYears();
    }

    public void mergeAllYears() {
        try {
            LOG.info("🔄 STARTING MERGE PROCESS...");

            // Map tổng chứa toàn bộ dữ liệu từ trước đến nay
            TreeMap<Long, AiPredictionData> masterMap = new TreeMap<>();

            // Bắt đầu từ năm 2021 (hoặc năm bắt đầu dữ liệu của bạn)
            int startYear = 2021;
            int currentYear = Calendar.getInstance().get(Calendar.YEAR);

            int totalFilesLoaded = 0;

            // Vòng lặp quét từ năm bắt đầu đến năm hiện tại
            for (int year = startYear; year <= currentYear; year++) {
                String fileName = Configs.FILE_AI_ENTRY_PREDICTIONS + "_" + year;
                File file = new File(fileName);

                if (file.exists()) {
                    LOG.info("📖 Reading file: {}", fileName);
                    try {
                        // Đọc file năm đó
                        TreeMap<Long, AiPredictionData> yearData =
                                (TreeMap<Long, AiPredictionData>) StorageSnappy.readObjectFromFile(fileName);

                        if (yearData != null && !yearData.isEmpty()) {
                            int sizeBefore = masterMap.size();

                            // Gộp vào map tổng
                            masterMap.putAll(yearData);

                            int sizeAfter = masterMap.size();
                            LOG.info("   ✅ Loaded {} records. Total records so far: {}", (sizeAfter - sizeBefore), sizeAfter);
                            totalFilesLoaded++;
                        } else {
                            LOG.warn("   ⚠️ File {} is empty or null.", fileName);
                        }
                    } catch (Exception e) {
                        LOG.error("   ❌ Error reading file " + fileName, e);
                    }
                } else {
                    LOG.info("   ℹ️ File {} not found. Skipping...", fileName);
                }
            }

            if (masterMap.isEmpty()) {
                LOG.error("❌ No data loaded from any files. Aborting save.");
                return;
            }

            // Lưu file tổng
            LOG.info("💾 SAVING MASTER FILE...");
            LOG.info("   Path: {}", FINAL_OUTPUT_FILE);
            LOG.info("   Total Records: {}", masterMap.size());

            StorageSnappy.writeObject2File(FINAL_OUTPUT_FILE, masterMap);

            LOG.info("🎉 MERGE COMPLETE! Successfully combined {} files.", totalFilesLoaded);

        } catch (Exception e) {
            LOG.error("Fatal Error during merge", e);
        }
    }
}