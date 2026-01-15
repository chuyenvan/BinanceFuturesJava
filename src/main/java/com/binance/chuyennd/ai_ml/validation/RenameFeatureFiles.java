package com.binance.chuyennd.ai_ml.validation;

import java.io.File;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

public class RenameFeatureFiles {
    public static void main(String[] args) {
        // Thư mục gốc chứa các folder con
        File rootDir = new File("C:\\Users\\pc\\Desktop\\data\\prediction");

        if (!rootDir.exists() || !rootDir.isDirectory()) {
            System.out.println("Thư mục prediction không tồn tại hoặc không phải thư mục.");
            return;
        }

        // Duyệt qua các folder con
        for (File subDir : rootDir.listFiles()) {
            if (subDir.isDirectory()) {
                for (File file : subDir.listFiles()) {
                    if (file.isFile()) {
                        String fileName = file.getName();
                        String timestampStr;

                        // Nếu có đuôi .features thì bỏ đi
                        if (fileName.endsWith(".features")) {
                            timestampStr = fileName.replace(".features", "");
                        } else {
                            timestampStr = fileName; // không có đuôi
                        }

                        try {
                            long timestamp = Long.parseLong(timestampStr);

                            // Làm tròn về phút (60.000 ms)
                            long rounded = (timestamp / 60000) * 60000;

                            // Giữ nguyên phần mở rộng nếu có
                            String newName;
                            if (fileName.endsWith(".features")) {
                                newName = rounded + ".features";
                            } else {
                                newName = String.valueOf(rounded);
                            }

                            Path source = file.toPath();
                            Path target = new File(subDir, newName).toPath();

                            // Đổi tên file
                            Files.move(source, target, StandardCopyOption.REPLACE_EXISTING);

                            System.out.println("Đổi: " + fileName + " -> " + newName);
                        } catch (NumberFormatException | IOException e) {
                            System.err.println("Lỗi xử lý file: " + fileName);
                            e.printStackTrace();
                        }
                    }
                }
            }
        }
    }
}