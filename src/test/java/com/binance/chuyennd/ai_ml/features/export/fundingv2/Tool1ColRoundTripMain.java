package com.binance.chuyennd.ai_ml.features.export.fundingv2;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedOutputStream;
import java.io.DataOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.util.Random;
import java.util.zip.GZIPOutputStream;

/**
 * TASK-251 — SINH DỮ LIỆU GIẢ LẬP "giống thật" rồi ghi ra CẢ HAI định dạng để kiểm chứng round-trip
 * {@link Tool1ColSink} (T1C1) bằng reader Python {@code ml/lib/tool1_col.py}.
 *
 * <p>Chạy được TRÊN MÁY WINDOWS, KHÔNG cần Oracle/Aerospike/Kaggle:
 * <pre>
 *   mvn -DskipTests package &amp;&amp; mvn -DskipTests test-compile
 *   java -cp "target/binance-java-sdk-*.jar;target/test-classes" \
 *        com.binance.chuyennd.ai_ml.features.export.fundingv2.Tool1ColRoundTripMain &lt;outDir&gt;
 *   python ml/lib/test_tool1_col.py &lt;outDir&gt;
 * </pre>
 *
 * <p>[2026-08-08] Bộ sinh có thêm 3 cột {@link #FATTAIL_COLS} với {@code range/IQR > 2000} để bắt
 * đúng ca mà T1C1 (int16) KHÔNG thể đạt ngưỡng 5e-3 IQR — nếu writer không tự chuyển các cột đó sang
 * int32 (T1C2) thì test round-trip sẽ FAIL ở ngưỡng (a).
 *
 * <p>Ghi 2 file CÙNG dữ liệu:
 * <ul>
 *   <li>{@code rt_features.t1c.gz} — định dạng MỚI (Tool1ColSink)</li>
 *   <li>{@code rt_features_ref.bin.gz} — định dạng CŨ row-major float32 big-endian 170 B/record,
 *       làm THAM CHIẾU giá trị gốc (chính xác bit) và làm mốc so tỉ lệ nén.</li>
 * </ul>
 *
 * <p><b>Vì sao dữ liệu phải "giống thật" mới đo được tỉ lệ nén trung thực:</b> 12/40 cột thật là
 * MARKET-WIDE (btcMomentum*, btcDominance, marketBreadth, basket*, basketFundingAvg) — cùng một mốc t
 * thì MỌI coin có giá trị Y HỆT nhau. Sau khi sort (symbol, t), các cột đó lặp lại nguyên chuỗi cho
 * từng symbol nên gzip nén gần như miễn phí. Sinh 40 cột nhiễu độc lập sẽ ĐÁNH GIÁ THẤP tỉ lệ nén một
 * cách sai lệch. Các cột per-coin thì mô phỏng độ mượt theo cửa sổ lookback thật (15m → 24h).
 */
public final class Tool1ColRoundTripMain {

    private static final Logger LOG = LoggerFactory.getLogger(Tool1ColRoundTripMain.class);

    private static final int N_COLS = 40;
    /** Số symbol. Override {@code -Dt1c.nsym=<x>} (mặc định GIỮ NGUYÊN 120 như bản gốc). */
    private static final int N_SYM = Integer.getInteger("t1c.nsym", 120);
    /** Số mốc phút. Override {@code -Dt1c.nmin=<x>}. 120 × 4200 = 504.000 record (~2.5 chunk).
     *  TASK-251 dùng {@code -Dt1c.nmin=2500} (300.000 record) làm nguồn cho test convert. */
    private static final int N_MIN = Integer.getInteger("t1c.nmin", 4200);
    private static final long BASE_TS = 1_712_000_040_000L;   // đã căn phút
    private static final long SEED = 20260807L;

    /** ~0.06% ô của các cột trong {@link #NAN_COLS} bị NaN (mô phỏng warmup/thiếu data). */
    private static final double NAN_RATE = 6e-4;

    /**
     * Biên độ cú nhảy (đơn vị log) tạo đuôi dày cho cột RATIO. Override bằng
     * {@code -Dt1c.jump=<x>} để chạy stress test.
     *
     * <p><b>Vì sao 2.2 mới là "giống thật":</b> sai số lượng tử hoá của T1C1 là hằng số theo cột,
     * bằng {@code 0.5/scale = range/128000}, nên tỉ số kiểm chứng {@code max|err|/IQR} CHÍNH LÀ
     * {@code (range/IQR)/128000} — không phụ thuộc gì khác. Đo thật trên quý 2024Q2 cho ra 0.0038
     * ⇒ cột tệ nhất của DỮ LIỆU THẬT có {@code range/IQR ≈ 486}. Ngưỡng 5e-3 tương đương
     * {@code range/IQR ≤ 640}. Jump=2.2 sinh ra đuôi trong khoảng đó (≈400–500); jump=3.0 sinh
     * {@code range/IQR ≈ 935} — ĐUÔI DÀY HƠN DỮ LIỆU THẬT GẦN 2 LẦN, tất yếu vượt ngưỡng dù mã hoá
     * hoàn toàn đúng. Giữ 2.2 làm mặc định và ghi rõ ở đây để lần sau không ai tưởng là bug.
     */
    private static final double JUMP_LOG = Double.parseDouble(System.getProperty("t1c.jump", "2.2"));

    /** 12 cột MARKET-WIDE — mọi symbol cùng mốc t có CÙNG giá trị (khớp f0..f5, f12..f16, f18 thật). */
    private static final int[] MARKET_COLS = {0, 1, 2, 3, 4, 5, 12, 13, 14, 15, 16, 18};

    /** 10 cột có NaN rải rác. CỐ Ý gồm cả cột đuôi-dày để ô NaN (q=-32768) nằm cạnh ô cực trị
     *  (q≈+32000) — đúng tình huống mà delta vượt dải int16, chỗ dễ hỏng nhất của mã hoá. */
    private static final int[] NAN_COLS = {9, 11, 22, 26, 27, 30, 32, 33, 34, 37};

    // --- kiểu giá trị của từng cột (mô phỏng, không cần khớp tuyệt đối tên feature thật) ---
    private static final int K_FUNDING = 0;   // ~1e-4, thang đo cực nhỏ
    private static final int K_RSI = 1;       // ~0..100
    private static final int K_RATIO = 2;     // dương, KHÔNG chặn trên, đuôi dày (spike hiếm)
    private static final int K_UNIT = 3;      // rank/percentile ∈ (0,1)
    private static final int K_RET = 4;       // ±5% return
    /**
     * ĐUÔI CỰC DÀY quanh 0 — mô phỏng f20 fundingRateTrend / f24 fundingSum24h / f26 volumeZCoin của
     * dữ liệu THẬT: thân phân bố cực hẹp (IQR ~0.07) nhưng thỉnh thoảng có cú nhảy hàng chục–trăm lần
     * ⇒ {@code range/IQR} tới hàng nghìn. Đây chính là loại cột mà int16 KHÔNG THỂ đạt ngưỡng sai số
     * 5e-3 IQR (đo thật quý 2024Q3: 1.02e-2…1.70e-2) và là lý do T1C2 phải có cột int32.
     */
    private static final int K_FATTAIL = 5;

    /** Các cột đuôi cực dày, đặt đúng chỉ số f20/f24/f26 như dữ liệu thật cho dễ đối chiếu. */
    private static final int[] FATTAIL_COLS = {20, 24, 26};

    private static final int[] KIND = new int[N_COLS];
    private static final int[] WIN = new int[N_COLS];
    private static final boolean[] IS_MARKET = new boolean[N_COLS];
    private static final boolean[] HAS_NAN = new boolean[N_COLS];

    static {
        for (int j = 0; j < N_COLS; j++) {
            KIND[j] = K_RET;
            // Cửa sổ lookback (phút) → độ mượt. Phần lớn feature thật dùng 1h..24h; chỉ nhóm
            // microstructure #36..#40 mới là 5m/15m (nhiễu hơn hẳn).
            WIN[j] = (j >= 35) ? 15 : new int[]{60, 240, 1440, 1440, 240}[j % 5];
        }
        for (int j : new int[]{17, 18, 19, 20, 24, 25}) KIND[j] = K_FUNDING;
        for (int j : new int[]{9, 15}) KIND[j] = K_RSI;
        for (int j : new int[]{11, 22, 26, 27, 30, 36, 37, 39}) KIND[j] = K_RATIO;
        for (int j : new int[]{21, 29, 32, 33, 34, 38}) KIND[j] = K_UNIT;
        for (int j : FATTAIL_COLS) KIND[j] = K_FATTAIL;   // GHI ĐÈ sau cùng: 20/24 vốn FUNDING, 26 vốn RATIO
        for (int j : MARKET_COLS) IS_MARKET[j] = true;
        for (int j : NAN_COLS) HAS_NAN[j] = true;
    }

    private Tool1ColRoundTripMain() {
    }

    public static void main(String[] args) throws Exception {
        String outDir = args.length > 0 ? args[0] : "target/t1c_roundtrip";
        new File(outDir).mkdirs();
        String newPath = outDir + "/rt_features.t1c.gz";
        String refPath = outDir + "/rt_features_ref.bin.gz";

        Random rnd = new Random(SEED);

        // Trạng thái AR(1) chuẩn hoá (kỳ vọng 0, phương sai 1) + phần nhảy (jump) cho cột đuôi dày.
        double[] mktX = new double[N_COLS];
        double[] mktJ = new double[N_COLS];
        double[][] coinX = new double[N_SYM][N_COLS];
        double[][] coinJ = new double[N_SYM][N_COLS];

        double[] phi = new double[N_COLS];
        double[] eps = new double[N_COLS];
        for (int j = 0; j < N_COLS; j++) {
            phi[j] = 1.0 - 1.0 / WIN[j];
            eps[j] = Math.sqrt(1.0 - phi[j] * phi[j]);
        }

        Tool1ColSink sink = new Tool1ColSink(newPath, 1);
        DataOutputStream ref = new DataOutputStream(new BufferedOutputStream(
                new GZIPOutputStream(new FileOutputStream(refPath)), 1 << 20));

        float[] f = new float[N_COLS];
        long nCells = 0, nNan = 0;

        for (int t = 0; t < N_MIN; t++) {
            long ts = BASE_TS + t * 60_000L;
            // cập nhật chuỗi market-wide 1 lần cho cả mốc t
            for (int j : MARKET_COLS) {
                mktX[j] = phi[j] * mktX[j] + eps[j] * rnd.nextGaussian();
                mktJ[j] = stepJump(mktJ[j], KIND[j], rnd);
            }
            for (int s = 0; s < N_SYM; s++) {
                for (int j = 0; j < N_COLS; j++) {
                    double x, jmp;
                    if (IS_MARKET[j]) {
                        x = mktX[j];
                        jmp = mktJ[j];
                    } else {
                        coinX[s][j] = phi[j] * coinX[s][j] + eps[j] * rnd.nextGaussian();
                        coinJ[s][j] = stepJump(coinJ[s][j], KIND[j], rnd);
                        x = coinX[s][j];
                        jmp = coinJ[s][j];
                    }
                    float v = value(KIND[j], x, jmp);
                    if (HAS_NAN[j] && rnd.nextDouble() < NAN_RATE) {
                        v = Float.NaN;
                        nNan++;
                    }
                    f[j] = v;
                    nCells++;
                }
                sink.add(ts, s, f);
                ref.writeLong(ts);
                ref.writeShort((short) s);
                for (int j = 0; j < N_COLS; j++) ref.writeFloat(f[j]);
            }
        }

        sink.close();
        ref.close();

        long nRec = (long) N_SYM * N_MIN;
        long newSize = new File(newPath).length();
        long refSize = new File(refPath).length();
        LOG.info("SINH XONG {} record × {} cột | NaN {} ô ({}% tổng ô)", nRec, N_COLS, nNan,
                String.format("%.4f", 100.0 * nNan / nCells));
        LOG.info("  MỚI  {} = {} bytes ({} B/record)", newPath, newSize,
                String.format("%.2f", newSize / (double) nRec));
        LOG.info("  CŨ   {} = {} bytes ({} B/record)", refPath, refSize,
                String.format("%.2f", refSize / (double) nRec));
        LOG.info("  RAW 170 B/record = {} bytes | tỉ lệ raw/mới = {}x | cũ-gzip/mới = {}x",
                nRec * 170, String.format("%.2f", nRec * 170.0 / newSize),
                String.format("%.2f", refSize / (double) newSize));
    }

    /** Phần "nhảy" hiếm tạo đuôi dày cho cột RATIO: xác suất 1e-4/bước, biên độ ±{@link #JUMP_LOG}
     *  (đơn vị log), tắt dần theo hệ số 0.999. */
    private static double stepJump(double j, int kind, Random rnd) {
        if (kind == K_FATTAIL) {
            // cú nhảy TỨC THỜI (không tắt dần): 1e-4/bước, biên độ 30..120 lần IQR của thân.
            // Sinh ra range/IQR cỡ 3000-4000 > 2000 như yêu cầu kiểm chứng.
            if (rnd.nextDouble() < 1e-4) {
                return (rnd.nextBoolean() ? 1 : -1) * (30.0 + 90.0 * rnd.nextDouble());
            }
            return 0.0;
        }
        if (kind != K_RATIO) return 0.0;
        double v = j * 0.999;
        if (rnd.nextDouble() < 1e-4) v += (rnd.nextBoolean() ? JUMP_LOG : -JUMP_LOG);
        return v;
    }

    private static float value(int kind, double x, double jump) {
        switch (kind) {
            case K_FUNDING:
                return (float) (1e-4 * x);
            case K_RSI:
                return (float) (50.0 + 12.0 * x);
            case K_RATIO:
                return (float) Math.exp(0.9 * x + jump);
            case K_UNIT:
                return (float) (1.0 / (1.0 + Math.exp(-x)));
            case K_FATTAIL:
                return (float) (0.05 * x + jump);
            default:
                return (float) (0.02 * x);
        }
    }
}
