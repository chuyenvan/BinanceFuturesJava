package com.binance.chuyennd.ai_ml.extractor;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.PrintWriter;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.LinkedBlockingQueue;

/**
 * Lop ghi CSV an toan da luong.
 * DA CAP NHAT: Ho tro che do APPEND (Ghi noi tiep).
 */
public class CsvWriter implements Runnable {

    public static final Logger LOG = LoggerFactory.getLogger(CsvWriter.class);

    private final BlockingQueue<String> queue = new LinkedBlockingQueue<>(1000);
    private final PrintWriter writer;
    private final Thread writerThread;
    private volatile boolean isRunning = true;

    public CsvWriter(String filePath, String header) throws IOException {
        File file = new File(filePath);

        // Kiem tra xem file da ton tai va co du lieu chua
        boolean isFileExistsAndHasData = file.exists() && file.length() > 0;

        // FileWriter(file, true) -> true nghia la APPEND (ghi noi tiep)
        this.writer = new PrintWriter(new FileWriter(file, true));

        // Chi ghi Header neu file moi tinh
        if (!isFileExistsAndHasData) {
            this.writer.println(header);
            this.writer.flush();
        }

        this.writerThread = new Thread(this);
        this.writerThread.start();
    }

    public void writeRow(FeatureRow row) {
        if (row == null) return;
        try {
            queue.put(row.toCsvString());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }

    @Override
    public void run() {
        while (isRunning || !queue.isEmpty()) {
            try {
                String row = queue.take();
                writer.println(row);
                // Flush ngay lap tuc de dam bao du lieu duoc ghi xuong dia
                // (Tranh mat data neu chuong trinh bi kill dot ngot)
                writer.flush();
            } catch (InterruptedException e) {
                if (isRunning) {
                    LOG.warn("CsvWriter bi gian doan.");
                }
            } catch (Exception e) {
                LOG.error("Loi khi ghi CSV row: {}", e.getMessage());
            }
        }
        writer.flush();
        writer.close();
    }

    public void close() {
        isRunning = false;
        writerThread.interrupt();
    }
}