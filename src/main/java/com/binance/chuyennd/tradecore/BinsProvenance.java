package com.binance.chuyennd.tradecore;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Arrays;

/**
 * VET TRUY NGUYEN BINS SELECTOR (2026-09-03).
 *
 * <p>Ly do ton tai: bins selector (<code>predict_wf_*.bin</code> trong
 * <code>WFO_FUNDING_PRED_DIR</code>) la BIEN QUYET DINH cua edge S1 nhung nam NGOAI git
 * (394 MB) va truoc day khong he xuat hien trong <code>CONFIG_HASH</code> hay log run nao.
 * Doi bins = doi hoan toan ket qua backtest ma khong dau vet nao thay doi.
 *
 * <p>Lop nay tinh sha256 tren NOI DUNG cua toan bo <code>predict_wf_*.bin</code> (sort theo
 * ten file, noi tiep nhau) de moi run TU KHAI dung bo bins nao. Doi chieu voi
 * <code>research/pipeline/BINS_MANIFEST.md</code>.
 *
 * <p>KHONG dua hash nay vao <code>CONFIG_HASH</code>: hash doi hoi bins co mat tren dia, ma
 * node Kaggle chi nhan dataset da build (khong co bins). Duong dan bins thi CO trong
 * <code>CONFIG_HASH</code> (qua {@code Configs.WFO_FUNDING_PRED_DIR}).
 */
public final class BinsProvenance {

    private static final Logger LOG = LoggerFactory.getLogger(BinsProvenance.class);

    /** Tien to + duoi cua file bins selector — khop {@code WfoDataset.buildFundingFromWfFiles}. */
    private static final String PREFIX = "predict_wf_";
    private static final String SUFFIX = ".bin";

    private BinsProvenance() { }

    /** @return danh sach file bins da sort theo ten, hoac mang rong neu dir khong dung. */
    public static File[] listBins(String dir) {
        if (dir == null || dir.trim().isEmpty()) return new File[0];
        File d = new File(dir.trim());
        if (!d.isDirectory()) return new File[0];
        File[] fs = d.listFiles((p, name) -> name.startsWith(PREFIX) && name.endsWith(SUFFIX));
        if (fs == null) return new File[0];
        Arrays.sort(fs);
        return fs;
    }

    /**
     * sha256 tren noi dung noi tiep cua moi {@code predict_wf_*.bin} (sort theo ten).
     *
     * @param dir thu muc bins
     * @return 64 ky tu hex
     * @throws IOException khi dir rong / khong ton tai / khong co file bins nao
     */
    public static String sha256(String dir) throws IOException {
        File[] fs = listBins(dir);
        if (fs.length == 0)
            throw new IOException("BINS SELECTOR trong: '" + dir + "' khong co " + PREFIX + "*"
                    + SUFFIX + ". Lay lai tu Kaggle dataset chuyendinh/predwf-map-s1a2-bins roi"
                    + " doi chieu sha256 theo research/pipeline/BINS_MANIFEST.md.");
        MessageDigest md;
        try {
            md = MessageDigest.getInstance("SHA-256");
        } catch (Exception e) {
            throw new IOException("Khong khoi tao duoc SHA-256", e);
        }
        byte[] buf = new byte[1 << 20];
        for (File f : fs) {
            try (InputStream in = Files.newInputStream(f.toPath())) {
                int n;
                while ((n = in.read(buf)) > 0) md.update(buf, 0, n);
            }
        }
        StringBuilder hex = new StringBuilder(64);
        for (byte b : md.digest()) hex.append(String.format("%02x", b));
        return hex.toString();
    }

    /** Tong so byte cua cac file bins (0 neu khong co). */
    public static long totalBytes(String dir) {
        long t = 0;
        for (File f : listBins(dir)) t += f.length();
        return t;
    }

    /**
     * In mot dong khai bao bins cho run hien tai (SLF4J, khong dung System.out).
     *
     * <p>KHONG throw: day la duong BAO CAO (DumpConfig / khoi dong sim). Cho fail cung nam o
     * {@code WfoDataset.export} — cho bins THUC SU duoc tieu thu. Khi bins khong doc duoc, ham
     * nay log muc ERROR de khong ai doc luot qua duoc.
     *
     * @param dir gia tri hieu dung cua WFO_FUNDING_PRED_DIR
     */
    public static void logDeclaration(String dir) {
        if (dir == null || dir.trim().isEmpty()) {
            LOG.error("bins.dir=<KHONG KHAI BAO> -> run nay KHONG khai duoc dung bo bins selector"
                    + " nao. Khai bao WFO_FUNDING_PRED_DIR trong profile giao dich"
                    + " (vi du profiles/c2b.properties).");
            return;
        }
        File[] fs = listBins(dir);
        if (fs.length == 0) {
            LOG.error("bins.dir={} bins.files=0 -> thu muc KHONG ton tai hoac khong co {}*{} tren"
                    + " node nay. Neu day la node chi nhan dataset da build thi doi chieu"
                    + " binsSha256 trong manifest.txt cua dataset.", dir, PREFIX, SUFFIX);
            return;
        }
        try {
            String h = sha256(dir);
            LOG.info("bins.dir={} bins.files={} bins.bytes={} bins.sha256_16={} bins.sha256={}",
                    dir, fs.length, totalBytes(dir), h.substring(0, 16), h);
        } catch (IOException e) {
            LOG.error("bins.dir={} bins.files={} -> KHONG tinh duoc sha256: {}",
                    dir, fs.length, e.getMessage());
        }
    }
}
