package com.binance.chuyennd.ai_ml.features.export;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.ai_ml.data.SymbolLifecycleManager;
import com.binance.chuyennd.ai_ml.hpo.kaggle.KaggleDataLoader;
import com.binance.chuyennd.object.sw.KlineObjectSimple;
import com.binance.chuyennd.tradecore.Configs;
import com.binance.chuyennd.utils.Utils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.io.FileWriter;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.*;
import java.util.concurrent.Callable;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

/**
 * TASK-024 (ADR-0011 §5.2) — export FUNDING LABEL = PATH THÔ per-coin (KHÔNG ép nhãn 3-lớp ở đây;
 * triple-barrier X/Y + horizon được QUÉT lúc train, KHÔNG re-export).
 *
 * <p>Đây là H1-DATA của funding (tương đương TASK-012 {@link ExportGateReturn} cho gate). Khác gate ở chỗ
 * gate = AGGREGATE (1 dòng/mốc), funding = PER-COIN (selector "coin NÀO sắp bơm").
 *
 * <p><b>Định nghĩa path (cho mỗi {@code (coin, t)}, với τ là các nến 15m thuộc {@code (t, t+H]}):</b>
 * <ul>
 *   <li>{@code maxFav_H}  = max( high(τ)/close(t) − 1 )  — biên thuận lợi cực đại (đỉnh) trong cửa sổ.</li>
 *   <li>{@code maxAdv_H}  = min( low(τ)/close(t)  − 1 )  — biên bất lợi cực đại (đáy) trong cửa sổ.</li>
 *   <li>{@code tHitFav_H} / {@code tHitAdv_H} = OFFSET (phút) từ t tới lúc chạm đỉnh / đáy đó.</li>
 *   <li>{@code retEnd_H}  = close(t+H)/close(t) − 1 — return close-to-close cuối cửa sổ.</li>
 *   <li>{@code nBars_H}   = số nến 15m THỰC CÓ trong (t, t+H] (đủ = H/15m: 16/48/96/288/672/1344/2880). Thiếu ⇒ data gap/coin chết (hoặc anchor gần cuối chuỗi dữ liệu — bình thường với H dài như 7d/14d/30d).</li>
 * </ul>
 * Lưu tại nhiều mốc H = {4h,12h,24h,72h,7d,14d,30d} (= {16,48,96,288,672,1344,2880} bước 15m) để train suy được
 * nhiều horizon mà KHÔNG cần re-export. 3 mốc {7d,14d,30d} (TASK bleed-thesis long-horizon) là ADDITIVE — APPEND
 * cuối, KHÔNG đổi 4 mốc gốc {4h,12h,24h,72h} (thứ tự cột + giá trị cột cũ giữ nguyên, dataset Kaggle cũ vẫn dùng
 * được). Triple-barrier ở train: chạm +X% trước (tHitFav &lt; tHitAdv) / chạm −Y% trước / hết H.
 *
 * <p><b>Look-ahead (ĐÚNG ranh giới H1):</b> LABEL ĐƯỢC nhìn tương lai — path chỉ dùng nến τ &gt; t tới t+H.
 * close(t) lấy từ nến tại t (đã biết tại t). FEATURE (task sau) mới phải ≤ t. Vì là LABEL nên KHÔNG dính
 * luật chống intrabar look-ahead của backtest ({@code BLOCK_INTRABAR_LOOKAHEAD} — luật đó cho KHỚP LỆNH, không cho nhãn).
 *
 * <p><b>Universe (BẮT BUỘC qua lifecycle — KHÔNG đọc DIED_SYMBOLS):</b> tạo anchor tại (coin, t) chỉ khi
 * {@link SymbolLifecycleManager#isAlive(String, long)} (gồm CẢ coin đã chết, trong khoảng [firstSeen, lastSeen]).
 * ⚠️ Phụ thuộc builder TASK-010 đã chạy. Nếu set {@code symbol_lifecycle} rỗng ({@code loadedCount()==0})
 * ⇒ tool DỪNG ngay (BLOCKED), KHÔNG fallback DIED âm thầm.
 *
 * <p><b>Nhịp sample = env LABEL_STEP_MIN phút, mặc định 15</b> (constant {@link #SAMPLE_STEP_MS}; khớp sibling
 * gate TASK-012, đủ mịn cho triple-barrier timing). Path bar cùng nhịp: gộp 1m→step (high=max maxPrice,
 * low=min minPrice, close=close nến 1m cuối bucket) — với STEP_MIN=1 thì bucket=nến 1m gốc (không gộp, không
 * mất thông tin). [2026-08-04] LABEL_STEP_MIN=1 dùng cho canonical WFO (Uni chốt: model live chạy theo phút,
 * lưới 15m cũ chỉ giữ làm baseline/so sánh — xem docs/reports/WFO_DATA_PIPELINE_MASTER.md).
 *
 * <p>Nguồn: ticker {@code kline_1m_opt} (226, đọc-only; box cần {@code AEROSPIKE_READ_CLUSTER=226}). Output {@link #OUT}.
 *
 * <p><b>[2026-08-06] TASK-251 fix #3 — xuất theo file QUÝ (Uni yêu cầu: đĩa Oracle không đủ chứa 1 file
 * khổng lồ + bước merge cuối cần gấp đôi dung lượng file cuối; muốn tách file theo mốc thời gian, đẩy Kaggle
 * xong quý nào xoá local ngay quý đó).</b> Thay vì ghi 1 file {@code outPath} duy nhất, mỗi partition coin
 * (xem {@code LABEL_THREADS}) tự chia output thành nhiều file THEO QUÝ DƯƠNG LỊCH (Jan/Apr/Jul/Oct — khớp quy
 * ước quý đang dùng ở {@code ExportFeaturesForPythonTool}): {@code <outPath-khong-.csv>_YYYYMMDD_to_YYYYMMDD.csv}.
 * Một dòng label (dựa theo {@code tEpoch} = thời điểm TẠO anchor) luôn thuộc ĐÚNG 1 quý — không có overlap/trùng
 * giữa 2 file quý liền kề (khác với việc chia theo NGÀY XỬ LÝ, vì 1 anchor được TẠO ở quý Q có thể mãi tới quý
 * Q+1 mới EMIT ra do phải đợi đủ H_MAX phút nhìn tương lai — file vẫn ghi đúng vào quý Q vì dùng tEpoch tạo anchor,
 * không dùng lúc emit). Mỗi partition-thread ĐÓNG file quý của mình khi vòng lặp ngày đã đi qua
 * {@code quý.end + H_MAX phút} — chỉ để GIẢI PHÓNG RAM (mỗi {@link LabelPbSink} giữ buffer ~20MB), KHÔNG
 * phải để gộp.
 *
 * <p><b>[2026-08-08] FIX RACE GỘP QUÝ — mất 29,37% dữ liệu quý 2024Q4 trên production.</b> Bản trước gộp
 * quý NGAY TRONG LÚC CHẠY, kích hoạt khi bộ đếm "số lần đóng quý Q" chạm {@code nParts}. Hai lỗi:
 * <ol>
 *   <li><b>Đếm LẦN ĐÓNG chứ không đếm PARTITION PHÂN BIỆT.</b> Một partition có thể đóng rồi MỞ LẠI cùng
 *       một quý nhiều lượt (anchor của coin có gap dữ liệu, và toàn bộ anchor của coin chết chỉ được flush
 *       ở CUỐI day-loop, đều mang {@code tEpoch} của quý cũ). Log thật quý 20241001_to_20250101: 9 lần
 *       "đóng file quý" cho 4 partition; "Đã gộp quý" fire ngay sau lần đóng thứ 4 (một lần đóng chỉ
 *       4.321 dòng = lần mở lại), trong khi partition thật sự nặng (11.859.598 dòng) đóng SAU đó 46 phút.
 *       Gộp xong là xoá {@code .partN}, nên mọi dòng ghi tiếp thành file mồ côi: 40.575.661 dòng thật
 *       ⇒ file cuối chỉ 28.660.118.</li>
 *   <li><b>{@code new FileOutputStream(path)} khi mở lại = TRUNCATE</b> ⇒ mất dữ liệu ngay từ khâu GHI,
 *       trước cả lúc gộp. Nay mở lại luôn dùng chế độ APPEND (định dạng là chuỗi chunk tự-mô-tả nên nối
 *       thêm hoàn toàn hợp lệ).</li>
 * </ol>
 * Hệ quả thứ ba của cách đếm cũ: partition nào KHÔNG có dòng nào trong quý Q thì bộ đếm không bao giờ chạm
 * {@code nParts} ⇒ quý Q KHÔNG BAO GIỜ được gộp (3 quý 2025Q3/2025Q4/2026Q1 trong log thật).
 *
 * <p><b>Cách sửa:</b> KHÔNG gộp trong lúc chạy. Toàn bộ việc gộp dồn vào {@link #mergeAllQuarters} chạy SAU
 * khi mọi partition kết thúc — thời điểm DUY NHẤT chắc chắn không còn ai ghi thêm. Vẫn gộp TỪNG QUÝ nên chỉ
 * cần dư ~1–2 quý dung lượng. Sau khi nối byte, BẮT BUỘC đếm lại số dòng thực trong file .pb và đối chiếu
 * với tổng số dòng các partition đã ghi; lệch ⇒ ERROR + exit code 2 + GIỮ {@code .partN}, không im lặng.
 */
public class ExportFundingLabel {

    private static final Logger LOG = LoggerFactory.getLogger(ExportFundingLabel.class);

    /** [2026-08-04 CANONICAL 1m] Nhịp sample anchor + độ rộng 1 nến path — env LABEL_STEP_MIN (mặc định 15,
     *  khớp hành vi cũ). Đặt =1 để sinh label lưới 1 phút thật (yêu cầu Uni: model live chạy theo phút).
     *  Kiến trúc VỐN ĐÃ stream nến 1m gốc (readDataFromAerospike1M) rồi mới gộp bucket SAMPLE_STEP_MS — đổi
     *  step KHÔNG cần viết lại logic finalizeBucket/updateAnchor, chỉ cần scale H_STEPS/H_MAX + 2 chỗ hardcode
     *  "*15" (emit offset-phút, recompute72 validate). Backward-compat: KHÔNG set env -> y hệt hành vi cũ. */
    private static final int STEP_MIN = Integer.parseInt(envOr("LABEL_STEP_MIN", "15"));
    private static final long SAMPLE_STEP_MS = STEP_MIN * 60_000L;
    /** Mốc H tính bằng PHÚT THẬT (bất biến theo step): 4h,12h,24h,72h,7d,14d,30d. Chia STEP_MIN -> số bước.
     *  BẮT BUỘC chia hết (STEP_MIN phải là ước của 240) — throw sớm nếu không, tránh sinh H_STEPS sai lệch âm thầm.
     *  3 mốc cuối {7d,14d,30d} = ADDITIVE (bleed-thesis long-horizon) — APPEND sau 72h, KHÔNG chèn giữa/đổi thứ tự
     *  4 mốc gốc. H_MAX lớn hơn ⇒ cuối chuỗi dữ liệu (coin sống tới "nay" hoặc coin chết) sẽ có nhiều anchor
     *  KHÔNG đủ nến forward cho 7d/14d/30d hơn trước (bình thường) — cơ chế biên GIỮ NGUYÊN: {@link #emit}
     *  snapshot(h, NaN) cho mốc chưa chạm (nBars_H thiếu, retEnd_H rỗng), KHÔNG bao giờ dùng nến tương lai
     *  không tồn tại (không wrap). */
    // [2026-08-06] TASK-251 fix: horizon dai (7d/14d/30d, H_MAX=43200 buoc=30 ngay tren grid 1-phut)
    // khien moi coin giu ~43.200 anchor mo dong thoi (ArrayDeque `active`) -> finalizeBucket() quet
    // O(anchors) moi phut -> qua cham (do thuc te tren Oracle: ~12h20m moi xu ly ~112/2007 ngay,
    // ETA ~9 ngay/full range). gen_funding_wf_predictions.py (script WFO tren Kaggle) CHI doc
    // maxFav_H/nBars_H cho H_LIST=[4h,12h,24h,72h] - 3 moc dai (7d/14d/30d, bleed-thesis) hien
    // KHONG duoc tieu thu. Bat LABEL_HORIZON_SET=short -> chi export 4 moc ngan (H_MAX=4320=72h,
    // ~1/10 anchor-list) cho critical path WFO.
    // [2026-08-06] Uni xac nhan: da search toan repo, KHONG co script/tool nao (Python hay Java)
    // doc 3 cot dai 7d/14d/30d - "bleed-thesis" van chi la du dinh trong comment, chua co job thuc
    // su dung. Theo chi dao "khong dung thi bo" -> DOI DEFAULT sang "short". Muon lam lai bleed-thesis
    // sau nay thi set LABEL_HORIZON_SET=full (van con code, khong xoa han, chi doi default).
    private static final boolean SHORT_HORIZON_ONLY =
            !"full".equalsIgnoreCase(envOr("LABEL_HORIZON_SET", "short"));
    static final int[] H_MINUTES = SHORT_HORIZON_ONLY
            ? new int[]{240, 720, 1440, 4320}
            : new int[]{240, 720, 1440, 4320, 10080, 20160, 43200};
    private static final int[] H_STEPS = computeHSteps();
    private static final String[] H_NAME = SHORT_HORIZON_ONLY
            ? new String[]{"4h", "12h", "24h", "72h"}
            : new String[]{"4h", "12h", "24h", "72h", "7d", "14d", "30d"};
    private static final int H_MAX = H_STEPS[H_STEPS.length - 1];
    private static final String START_DATE = "20210101";
    private static final String OUT = "outputs/funding_label.csv";

    // === [2026-08-09 label-filter] KEYSET: chi tao anchor cho (symId,minute) thuoc keyset lay tu features
    //     (FF_KEYDUMP, cung selectCoins + cung warmup -> khop features TUYET DOI). Bat qua env
    //     LABEL_KEYSET=path1,path2,... (moi file binary big-endian long = (symId<<32)|minuteIdx).
    //     Khong set -> all-coin nhu cu (backward-compat). ===
    private static long[] KEYSET = null;
    private static boolean KEYSET_ON = false;
    private static boolean keysetContains(short symId, long tEpochMs) {
        long key = ((long) (symId & 0xFFFF) << 32) | ((tEpochMs / 60000L) & 0xFFFFFFFFL);
        return java.util.Arrays.binarySearch(KEYSET, key) >= 0;
    }
    private static void loadKeyset(String paths) throws java.io.IOException {
        java.util.List<long[]> chunks = new java.util.ArrayList<>();
        long total = 0;
        for (String p0 : paths.split(",")) {
            String p = p0.trim();
            if (p.isEmpty()) continue;
            java.io.File f = new java.io.File(p);
            long n = f.length() / 8L;
            long[] arr = new long[(int) n];
            try (java.io.DataInputStream in = new java.io.DataInputStream(
                    new java.io.BufferedInputStream(new java.io.FileInputStream(f), 1 << 20))) {
                for (int i = 0; i < n; i++) arr[i] = in.readLong();
            }
            chunks.add(arr);
            total += n;
            LOG.info("KEYSET nap {} keys tu {}", n, p);
        }
        KEYSET = new long[(int) total];
        int off = 0;
        for (long[] c : chunks) { System.arraycopy(c, 0, KEYSET, off, c.length); off += c.length; }
        java.util.Arrays.sort(KEYSET);
        KEYSET_ON = KEYSET.length > 0;
        LOG.info("KEYSET tong {} keys (da sort) -> KEYSET_ON={}", KEYSET.length, KEYSET_ON);
    }

    private static String envOr(String name, String def) {
        String v = System.getenv(name);
        return (v != null && !v.isEmpty()) ? v : def;
    }

    private static int[] computeHSteps() {
        int[] out = new int[H_MINUTES.length];
        for (int i = 0; i < H_MINUTES.length; i++) {
            if (H_MINUTES[i] % STEP_MIN != 0)
                throw new IllegalStateException("LABEL_STEP_MIN=" + STEP_MIN + " khong chia het H=" + H_MINUTES[i]
                        + "phut -> se sinh H_STEPS sai. Chon STEP_MIN la uoc cua 240 (vd 1,3,5,15,20,30,60).");
            out[i] = H_MINUTES[i] / STEP_MIN;
        }
        return out;
    }

    private static final SymbolLifecycleManager LIFECYCLE = SymbolLifecycleManager.getInstance();

    /** Universe = USDT-perp alt (selector chọn alt; loại BTC/ETH = vai market gate, loại BTCDOM/USDC/đa-tài-sản). */
    private static boolean isAlt(String s) {
        return s.endsWith("USDT") && !s.equals("BTCUSDT") && !s.equals("ETHUSDT")
                && !s.contains("_") && !s.contains("USDC") && !s.equals("BTCDOMUSDT");
    }

    /** Trạng thái tích luỹ path của 1 anchor (coin, t). */
    private static final class Anchor {
        final long tStep;          // bucket index = epoch/SAMPLE_STEP_MS của t
        final float closeT;
        float maxFav = -Float.MAX_VALUE;
        float maxAdv = Float.MAX_VALUE;
        int tHitFavStep = 0;       // offset (số bước 15m) tới đỉnh
        int tHitAdvStep = 0;
        int barsSeen = 0;          // số nến THỰC trong cửa sổ tới hiện tại
        // snapshot tại từng H
        final boolean[] snap = new boolean[H_STEPS.length];
        final float[] maxFavH = new float[H_STEPS.length];
        final float[] maxAdvH = new float[H_STEPS.length];
        final int[] tHitFavH = new int[H_STEPS.length];
        final int[] tHitAdvH = new int[H_STEPS.length];
        final float[] retEndH = new float[H_STEPS.length];
        final int[] nBarsH = new int[H_STEPS.length];
        boolean[] retEndSet = new boolean[H_STEPS.length];

        Anchor(long tStep, float closeT) {
            this.tStep = tStep;
            this.closeT = closeT;
        }
    }

    /** Trạng thái streaming per-coin: bucket 15m đang gộp + danh sách anchor đang mở. */
    private static final class CoinState {
        long curBucketIdx = -1;
        float bHi, bLo, bClose;
        final ArrayDeque<Anchor> active = new ArrayDeque<>();
    }

    /** 1 file quý đang mở của 1 partition (giữ writer + đếm dòng để log/kiểm tra). */
    static final class QuarterSink {
        final long qStart, qEnd;
        /** [2026-08-07 TASK-251] Đổi từ FileWriter (CSV) sang protobuf columnar — xem {@link LabelPbSink}. */
        final LabelPbSink w;
        long rows = 0;
        QuarterSink(long qStart, long qEnd, LabelPbSink w) { this.qStart = qStart; this.qEnd = qEnd; this.w = w; }
    }

    /** Ngữ cảnh của 1 partition: outPath gốc, vị trí partition, các file quý ĐANG MỞ của RIÊNG partition này,
     *  + 2 cấu trúc CHIA SẺ giữa mọi partition (closeCounters đếm bao nhiêu partition đã đóng xong quý Q;
     *  mergerPool chạy việc gộp quý ở thread riêng, không chặn worker đang export). */
    static final class PartCtx {
        final String outPath;
        final int partIdx, nParts;
        final Map<Long, QuarterSink> open = new TreeMap<>();
        /** Các quý mà partition NÀY đã từng mở file .partN — mở lại phải APPEND, không được ghi đè. */
        final Set<Long> everOpened = new HashSet<>();
        final QuarterRegistry reg;
        PartCtx(String outPath, int partIdx, int nParts, QuarterRegistry reg) {
            this.outPath = outPath; this.partIdx = partIdx; this.nParts = nParts;
            this.reg = reg;
        }
    }

    /** Sổ ghi CHUNG mọi partition: quý nào đã từng được ghi (qStart -> qEnd) + TỔNG số dòng mà các
     *  partition báo đã ghi vào quý đó. Dùng ở bước gộp-cuối để (1) biết phải gộp những quý nào,
     *  (2) đối chiếu số dòng THỰC trong file .pb sau khi gộp. */
    static final class QuarterRegistry {
        final ConcurrentHashMap<Long, Long> qEndOf = new ConcurrentHashMap<>();
        final ConcurrentHashMap<Long, java.util.concurrent.atomic.LongAdder> rowsOf = new ConcurrentHashMap<>();
        final ExecutorService mergerPool;
        QuarterRegistry(int nThreads) {
            this.mergerPool = Executors.newFixedThreadPool(Math.max(1, Math.min(2, nThreads)));
        }
        void record(long qStart, long qEnd, long rows) {
            qEndOf.put(qStart, qEnd);
            rowsOf.computeIfAbsent(qStart, k -> new java.util.concurrent.atomic.LongAdder()).add(rows);
        }
    }

    public static void main(String[] args) {
        try {

            // ===== GUARD universe: builder TASK-010 phải đã chạy =====
            int nLifecycle = LIFECYCLE.loadedCount();
            if (nLifecycle == 0) {
                LOG.error("⛔ BLOCKED: set Aerospike 'symbol_lifecycle' RỖNG (loadedCount=0) ⇒ builder TASK-010 CHƯA chạy. "
                        + "TASK-024 KHÔNG fallback DIED_SYMBOLS âm thầm. Hãy chạy SymbolLifecycleBuilder trên 226 trước, rồi chạy lại.");
                return;
            }
            LOG.info("✅ Lifecycle nạp {} symbol (universe qua isAlive — gồm coin đã chết).", nLifecycle);

            String startStr = args.length > 0 ? args[0] : START_DATE;
            String endStr   = args.length > 1 ? args[1] : null;
            String outPath  = args.length > 2 ? args[2] : OUT;
            long start = Utils.sdfFile.parse(startStr).getTime() + 7 * Utils.TIME_HOUR;
            long end   = (endStr != null) ? Utils.sdfFile.parse(endStr).getTime() + 7 * Utils.TIME_HOUR
                                          : System.currentTimeMillis();

            // [2026-08-06] TASK-251 toi uu #2: finalizeBucket() la O(anchors dang mo CUA RIENG 1 coin) —
            // hoan toan doc lap giua coin nay voi coin khac (khong doc/ghi cheo state coin khac). Vi vay
            // chia universe alt-coin thanh N partition DISJOINT (hash symbol mod N), moi partition chay
            // 1 THREAD rieng, lap lai NGUYEN VEN cung logic day-loop/finalizeBucket/emit (KHONG doi thuat
            // toan, chi doi PHAM VI coin xu ly) -> giam rui ro sai lech so voi single-thread. Moi thread
            // tu doc Aerospike/Kaggle rieng cho ngay cua no (trung lap I/O giua thread, nhung bottleneck
            // do jstack la CPU tai finalizeBucket() chu khong phai I/O, nen trung lap nay chap nhan duoc).
            // LABEL_THREADS=1 (mac dinh) -> y HET hanh vi don-partition cu.
            int nThreads = Math.max(1, Integer.parseInt(envOr("LABEL_THREADS", "1")));
            String keysetPaths = System.getenv("LABEL_KEYSET");
            if (keysetPaths != null && !keysetPaths.isEmpty()) {
                loadKeyset(keysetPaths);
                LOG.info("🔑 LABEL_KEYSET bat -> label CHI tao anchor cho (symId,ts) thuoc keyset features "
                        + "(khop features 0.10 tuyet doi). isAlt/isAlive gate duoc bo qua trong keyset-mode.");
            }
            boolean noValidate = "1".equals(System.getenv("NO_VALIDATE"));
            if (noValidate) LOG.info("NO_VALIDATE=1 -> bo gom validate (tranh OOM tich luy toan bo anchor — BAT BUOC cho run lon, xem phan ETA_OOM).");
            LOG.info("🏷️ TASK-024 export funding LABEL path-thô per-coin | {} → {} | sample {}m | H={} | H_MAX={} buoc ({} phut) | LABEL_THREADS={} | xuat theo file QUY (xem class-doc)",
                    startStr, (endStr != null ? endStr : "nay"), STEP_MIN, Arrays.toString(H_NAME), H_MAX, H_MAX * STEP_MIN, nThreads);

            boolean useAerospike;
            if ("aerospike".equals(Configs.TICKER_SOURCE)) {
                useAerospike = true;
            } else if ("file".equals(Configs.TICKER_SOURCE)) {
                useAerospike = false;
            } else {
                throw new IllegalStateException("Thieu/sai TICKER_SOURCE trong config.properties (hien tai: "
                        + Configs.TICKER_SOURCE + ") - them dong: TICKER_SOURCE=aerospike (doc Aerospike) "
                        + "hoac TICKER_SOURCE=file (doc ticker_*.bin tu Kaggle dataset, khong can Oracle).");
            }

            // [2026-08-06] TASK-251 fix #3: dem so partition da dong xong 1 quy (key=qStartEpoch) + pool
            // rieng chay viec GOP file quy (khong chan cac worker export). Chia se giua moi partition-thread.
            QuarterRegistry reg = new QuarterRegistry(nThreads);

            long totalEmitted;
            int totalCoins;
            if (nThreads == 1) {
                long[] res = runPartition(start, end, outPath, 1, 0, useAerospike, noValidate, reg);
                totalEmitted = res[0];
                totalCoins = (int) res[1];
            } else {
                ExecutorService pool = Executors.newFixedThreadPool(nThreads);
                List<Future<long[]>> futures = new ArrayList<>();
                for (int p = 0; p < nThreads; p++) {
                    final int partIdx = p;
                    Callable<long[]> task = () -> runPartition(start, end, outPath, nThreads, partIdx, useAerospike, noValidate, reg);
                    futures.add(pool.submit(task));
                }
                pool.shutdown();
                totalEmitted = 0;
                totalCoins = 0;
                for (Future<long[]> f : futures) {
                    long[] r = f.get();   // propagate exception nếu 1 partition lỗi -> FAIL FAST, không âm thầm bỏ qua
                    totalEmitted += r[0];
                    totalCoins += (int) r[1];
                }
            }

            // Moi partition da dong het file quy cua no (closeAllRemaining trong runPartition) truoc khi
            // return o day -> moi task gop quy con thieu deu da duoc submit vao mergerPool. Cho no xong.
            int badQuarters = mergeAllQuarters(outPath, nThreads, reg);
            if (badQuarters > 0) {
                LOG.error("❌ {} quý LỆCH số dòng sau khi gộp — KHÔNG dùng dataset này.", badQuarters);
                System.exit(2);
            }

            LOG.info("✅ Xong toàn bộ: {} dòng emit, {} coin trong universe | {} → {} | dữ liệu chia theo FILE QUÝ " +
                    "(xem log 'Đã gộp quý' để biết từng file, KHÔNG có 1 file {} duy nhất)",
                    totalEmitted, totalCoins, startStr, (endStr != null ? endStr : "nay"), outPath);

            // [2026-08-04] Sidecar metadata: downstream (gen_funding_wf_predictions.py, train_*) doc file nay
            // de biet stepMin THAT (khong doan/hardcode 15). Ten file = <outPath>.meta.json — 1 file DUY NHAT
            // cho ca job (khong chia theo quy, vi cau hinh step/horizon giong nhau cho moi quy).
            try (Writer mw = new OutputStreamWriter(new FileOutputStream(outPath + ".meta.json"), StandardCharsets.UTF_8)) {
                mw.write("{\n");
                mw.write("  \"stepMinutes\": " + STEP_MIN + ",\n");
                mw.write("  \"hStepsMinutes\": " + java.util.Arrays.toString(H_MINUTES) + ",\n");
                mw.write("  \"hNames\": " + java.util.Arrays.toString(H_NAME) + ",\n");
                mw.write("  \"startDate\": \"" + startStr + "\",\n");
                mw.write("  \"endDate\": \"" + (endStr != null ? endStr : "nay") + "\",\n");
                mw.write("  \"emittedRows\": " + totalEmitted + ",\n");
                mw.write("  \"coinCount\": " + totalCoins + ",\n");
                mw.write("  \"labelThreads\": " + nThreads + ",\n");
                mw.write("  \"chunkedByQuarter\": true,\n");
                mw.write("  \"generatedAt\": \"" + new java.util.Date() + "\"\n");
                mw.write("}\n");
            }
            LOG.info("   meta -> {}.meta.json (stepMinutes={})", outPath, STEP_MIN);
        } catch (Exception e) {
            LOG.error("ExportFundingLabel lỗi", e);
            System.exit(1);
        }
        // BẮT BUỘC: DataManagerAerospikeFloatSim giữ ExecutorService non-daemon → main return KHÔNG đủ
        // để JVM thoát (treo). Trên Kaggle = kernel kẹt tới timeout 12h. System.exit để chấm dứt sạch.
        System.exit(0);
    }

    /**
     * Chạy TOÀN BỘ day-loop + finalize + flush cho 1 PARTITION coin (nParts=1,partIdx=0 = full universe,
     * y hệt phạm vi coin xử lý single-thread cũ). Mỗi partition có {@code coins}/{@code Validate}/{@code emitted}
     * RIÊNG (không share state giữa thread). Khác bản cũ: KHÔNG ghi 1 file duy nhất — ghi nhiều file THEO QUÝ
     * (xem {@link PartCtx}/{@link QuarterSink}), tự đóng quý khi đã an toàn (qua {@link #closeQuartersUpTo}) và
     * đóng hết các quý còn treo ở cuối (qua {@link #closeAllRemaining}). Trả về {@code {emittedRows, coinCount}}.
     */
    private static long[] runPartition(long start, long end, String outPath, int nParts, int partIdx,
                                        boolean useAerospike, boolean noValidate,
                                        QuarterRegistry reg) throws Exception {
        Map<String, CoinState> coins = new HashMap<>();
        PartCtx ctx = new PartCtx(outPath, partIdx, nParts, reg);
        Validate v = new Validate(noValidate);
        long[] emitted = {0};
        long days = 0;
        String tag = nParts > 1 ? ("[part" + partIdx + "/" + nParts + "] ") : "";

        for (long day = start; day < end; day += 24L * Utils.TIME_HOUR) {
            TreeMap<Long, Map<String, KlineObjectSimple>> oneDay = useAerospike
                    ? DataManagerAerospikeFloatSim.readDataFromAerospike1M(day)
                    : KaggleDataLoader.loadDailyTickersStringKey(day);
            if (oneDay == null) {
                LOG.warn("{}Thieu file ticker ngay {} (TICKER_SOURCE=file) - bo qua ngay nay.",
                        tag, Utils.sdfFile.format(new java.util.Date(day)));
                continue;
            }
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : oneDay.entrySet()) {
                long epoch = e.getKey();
                long bucketIdx = epoch / SAMPLE_STEP_MS;
                for (Map.Entry<String, KlineObjectSimple> se : e.getValue().entrySet()) {
                    String sym = se.getKey();
                    if (!KEYSET_ON && !isAlt(sym)) continue; // keyset-mode: keyset la nguon quyet dinh, khong pre-loc isAlt
                    if (nParts > 1 && Math.floorMod(sym.hashCode(), nParts) != partIdx) continue;
                    KlineObjectSimple k = se.getValue();
                    if (!Utils.isTickerAvailable(k)) continue;
                    CoinState cs = coins.computeIfAbsent(sym, x -> new CoinState());
                    if (cs.curBucketIdx != bucketIdx) {
                        if (cs.curBucketIdx >= 0) finalizeBucket(cs, sym, ctx, v, emitted);
                        cs.curBucketIdx = bucketIdx;
                        cs.bHi = k.maxPrice;
                        cs.bLo = k.minPrice;
                        cs.bClose = k.priceClose;
                    } else {
                        if (k.maxPrice > cs.bHi) cs.bHi = k.maxPrice;
                        if (k.minPrice < cs.bLo) cs.bLo = k.minPrice;
                        cs.bClose = k.priceClose;
                    }
                }
            }
            // [2026-08-06 fix #3] Sau khi xu ly xong ngay `day`: bat nhung quy da CHAC CHAN khong con
            // anchor nao (tao trong quy do) chua emit — an toan dong file + tinh vao closeCounters.
            closeQuartersUpTo(ctx, day);
            if (++days % 200 == 0)
                LOG.info("{}   ... {} ngày, {}, emitted={}", tag, days, fmtDate(day), emitted[0]);
        }

        // flush: hoàn tất bucket cuối + emit mọi anchor còn mở (coin chết / cuối dữ liệu → H dài có thể thiếu)
        for (Map.Entry<String, CoinState> ce : coins.entrySet()) {
            CoinState cs = ce.getValue();
            if (cs.curBucketIdx >= 0) finalizeBucket(cs, ce.getKey(), ctx, v, emitted);
            for (Anchor a : cs.active) emit(a, ce.getKey(), ctx, v, emitted);
            cs.active.clear();
        }
        // Khong con ngay nao nua -> chac chan khong con anchor nao se tao them -> dong HET quy con mo.
        closeAllRemaining(ctx);
        LOG.info("{}✅ Partition xong: {} dòng emit, {} coin (file quý xem log 'Đã gộp quý')", tag, emitted[0], coins.size());
        if (!noValidate) v.report();
        return new long[]{emitted[0], coins.size()};
    }

    // ================== [2026-08-06 fix #3] CHIA FILE THEO QUÝ ==================

    // [2026-08-06 fix #3b — BUG THẬT phát hiện qua smoke test LABEL_THREADS=4]: KHÔNG dùng chung
    // Utils.sdfFile (1 SimpleDateFormat static duy nhất, KHÔNG thread-safe — Calendar nội bộ bị nhiều
    // thread ghi đè chéo) ở day-loop hot-path (emit() gọi mỗi dòng, hàng triệu lần, từ 4 thread song
    // song) — gây sinh ngày-tháng RÁC ("00010101", "10210101"...) rồi crash parse. Code cũ chỉ gọi
    // Utils.sdfFile ở chỗ HIẾM (log mỗi 200 ngày) nên race gần như không lộ; emit()-mỗi-dòng thì lộ
    // ngay. Dùng ThreadLocal riêng (đúng pattern {@link #FMT} đã có sẵn trong file cho việc NÀY).
    private static final ThreadLocal<SimpleDateFormat> QDATE_FMT = ThreadLocal.withInitial(() -> {
        SimpleDateFormat f = new SimpleDateFormat("yyyyMMdd");
        f.setTimeZone(TimeZone.getTimeZone("GMT+7")); // khop tz pin cung trong Utils.sdfFile
        return f;
    });

    private static String fmtDate(long epoch) {
        return QDATE_FMT.get().format(new Date(epoch));
    }

    /** parse "yyyyMMdd" (tz GMT+7, qua QDATE_FMT riêng-thread) rồi +7h — ĐÚNG quy ước epoch "ngày" mà
     *  main()/day-loop đang dùng cho start/end/day (xem cách {@code start}/{@code end} được tính ở main()). */
    private static long dateStrToEpoch(String yyyymmdd) throws Exception {
        return QDATE_FMT.get().parse(yyyymmdd).getTime() + 7 * Utils.TIME_HOUR;
    }

    /** Quý dương lịch chứa {@code tEpoch} (Jan/Apr/Jul/Oct) — trả về epoch 00:00 ngày đầu quý, CÙNG quy ước
     *  epoch với start/end/day (dùng {@link #fmtDate} để lấy đúng ngày-tháng-năm hiển thị, y hệt cách log
     *  dòng "... ngày" đang làm — ĐÃ xác nhận đúng lịch, không lệch 7h — nhưng KHÔNG dùng Utils.sdfFile
     *  trực tiếp để tránh race, xem comment QDATE_FMT). */
    static long quarterStartEpoch(long tEpoch) throws Exception {
        String ymd = fmtDate(tEpoch);
        int year = Integer.parseInt(ymd.substring(0, 4));
        int month = Integer.parseInt(ymd.substring(4, 6));
        int qMonth = ((month - 1) / 3) * 3 + 1;
        return dateStrToEpoch(String.format("%04d%02d01", year, qMonth));
    }

    /** Epoch 00:00 ngày đầu quý KẾ TIẾP (đúng 3 tháng dương lịch sau {@code qStartEpoch}). */
    static long quarterEndEpoch(long qStartEpoch) throws Exception {
        String ymd = fmtDate(qStartEpoch);
        int year = Integer.parseInt(ymd.substring(0, 4));
        int month = Integer.parseInt(ymd.substring(4, 6));
        int nextMonth = month + 3;
        int nextYear = year;
        if (nextMonth > 12) { nextMonth -= 12; nextYear += 1; }
        return dateStrToEpoch(String.format("%04d%02d01", nextYear, nextMonth));
    }

    /** Chuỗi hậu tố tên file quý, khớp quy ước đang dùng ở ExportFeaturesForPythonTool: "YYYYMMDD_to_YYYYMMDD". */
    static String quarterSuffix(long qStart, long qEnd) throws Exception {
        return fmtDate(qStart) + "_to_" + fmtDate(qEnd);
    }

    private static String baseNoCsv(String outPath) {
        return outPath.endsWith(".csv") ? outPath.substring(0, outPath.length() - 4) : outPath;
    }

    /** [2026-08-07 TASK-251] Đuôi file output. Đổi .csv -> .pb vì nội dung giờ là protobuf columnar
     *  (xem {@link LabelPbSink}); giữ nguyên tên tham số dòng lệnh {@code funding_label_1m.csv} để không
     *  phải sửa lệnh chạy đang dùng — chỉ phần ĐUÔI file quý sinh ra là đổi. */
    private static final String OUT_EXT = ".pb";

    /** Đường dẫn file TẠM của 1 partition cho 1 quý — xoá sau khi gộp. */
    static String quarterPartPath(String outPath, long qStart, long qEnd, int partIdx) throws Exception {
        return baseNoCsv(outPath) + "_" + quarterSuffix(qStart, qEnd) + ".part" + partIdx + OUT_EXT;
    }

    /** Đường dẫn file quý CUỐI CÙNG (sau khi gộp N partition) — đây là file đem push Kaggle. */
    static String quarterFinalPath(String outPath, long qStart, long qEnd) throws Exception {
        return baseNoCsv(outPath) + "_" + quarterSuffix(qStart, qEnd) + OUT_EXT;
    }

    /** Lấy (hoặc mở mới, lazy) writer của quý chứa {@code tEpoch} cho partition này. */
    static QuarterSink sinkFor(PartCtx ctx, long tEpoch) throws Exception {
        long qStart = quarterStartEpoch(tEpoch);
        QuarterSink s = ctx.open.get(qStart);
        if (s == null) {
            long qEnd = quarterEndEpoch(qStart);
            String path = quarterPartPath(ctx.outPath, qStart, qEnd, ctx.partIdx);
            // [2026-08-08 FIX RACE] Partition NÀY đã từng mở quý này rồi ⇒ đây là lần MỞ LẠI (anchor của
            // coin có gap dữ liệu / coin chết emit rất trễ) ⇒ BẮT BUỘC append; truncate thì mất sạch phần
            // đã ghi trước đó. Lần đầu vẫn truncate để không dính rác của run trước bị crash.
            boolean reopen = !ctx.everOpened.add(qStart);
            // baseMs = ĐẦU QUÝ -> t_idx luôn nằm gọn trong 18 bit mà LabelPbSink.flushChunk() dùng để sort.
            LabelPbSink w = new LabelPbSink(path, qStart, STEP_MIN, H_NAME, H_MINUTES, reopen);
            s = new QuarterSink(qStart, qEnd, w);
            ctx.open.put(qStart, s);
            if (reopen)
                LOG.warn("[part{}/{}] MỞ LẠI (append) file quý đã đóng: {} — có anchor đến muộn (coin gap/coin chết). "
                        + "Đây chính là lý do KHÔNG được gộp quý trong lúc job còn chạy.", ctx.partIdx, ctx.nParts, path);
            else
                LOG.info("[part{}/{}] mở file quý mới: {}", ctx.partIdx, ctx.nParts, path);
        }
        return s;
    }

    /** Đóng mọi quý mà partition này CHẮC CHẮN không còn anchor chưa emit (day-loop đã đi qua
     *  quý.end + H_MAX phút — margin đúng bằng cửa sổ nhìn-tương-lai dài nhất, xem H_MAX). */
    static void closeQuartersUpTo(PartCtx ctx, long dayProcessed) throws Exception {
        long marginMs = (long) H_MAX * STEP_MIN * 60_000L;
        Iterator<Map.Entry<Long, QuarterSink>> it = ctx.open.entrySet().iterator();
        while (it.hasNext()) {
            QuarterSink s = it.next().getValue();
            if (dayProcessed >= s.qEnd + marginMs) {
                closeSink(ctx, s);
                it.remove();
            }
        }
    }

    /** Hết ngày để xử lý (day-loop kết thúc, đã flush anchor còn mở) -> đóng HẾT quý còn treo, bất kể margin. */
    static void closeAllRemaining(PartCtx ctx) throws Exception {
        for (QuarterSink s : ctx.open.values()) closeSink(ctx, s);
        ctx.open.clear();
    }

    /** Đóng writer file .partN của 1 quý (giải phóng RAM buffer chunk) và GHI SỔ số dòng đã ghi.
     *
     *  <p><b>[2026-08-08 FIX RACE] TUYỆT ĐỐI KHÔNG gộp quý ở đây.</b> Bản cũ đếm số LẦN ĐÓNG rồi gộp khi
     *  chạm {@code nParts}. Sai 2 tầng: (1) một partition đóng-mở-đóng nhiều lượt cũng làm bộ đếm tăng nên
     *  gộp fire khi partition khác chưa đóng (log production: gộp ngay sau lần đóng thứ 4/9; một partition
     *  11.859.598 dòng đóng SAU khi đã gộp ⇒ mất 29,37% quý 2024Q4); (2) partition nào KHÔNG có dòng nào
     *  trong quý Q thì bộ đếm không bao giờ chạm nParts ⇒ quý Q KHÔNG BAO GIỜ được gộp (3 quý 2025Q3/
     *  2025Q4/2026Q1 trong log thật). Không có mốc nào TRONG LÚC CHẠY là an toàn: anchor của coin có gap
     *  dữ liệu, và toàn bộ anchor của coin chết (chỉ được flush ở CUỐI day-loop), có thể rơi vào BẤT KỲ
     *  quý cũ nào. Vì vậy việc gộp được dời hẳn sang {@link #mergeAllQuarters}, chạy sau khi mọi partition
     *  đã kết thúc. */
    private static void closeSink(PartCtx ctx, QuarterSink s) throws Exception {
        s.w.close();
        LOG.info("[part{}/{}] đóng file quý {} ({} dòng)", ctx.partIdx, ctx.nParts, quarterSuffix(s.qStart, s.qEnd), s.rows);
        ctx.reg.record(s.qStart, s.qEnd, s.rows);
        s.rows = 0;   // đã ghi sổ -> nếu mở lại quý này (append) thì đếm tiếp từ 0, không cộng trùng
    }

    /** Đếm số dòng THỰC trong 1 file .pb (chuỗi LabelChunk writeDelimitedTo) mà KHÔNG dựng object
     *  cho toàn bộ cột: chỉ đọc varint length-prefix rồi quét lấy field 5 (row_count), bỏ qua phần
     *  còn lại. Nhờ vậy kiểm tra được file 40 triệu dòng với vài MB RAM.
     *  Trả về -1 nếu file không tồn tại. */
    static long countRowsInPb(String path) throws Exception {
        java.io.File f = new java.io.File(path);
        if (!f.exists()) return -1;
        long rows = 0;
        try (java.io.InputStream in = new java.io.BufferedInputStream(new java.io.FileInputStream(f), 1 << 20)) {
            com.google.protobuf.CodedInputStream cis = com.google.protobuf.CodedInputStream.newInstance(in);
            cis.setSizeLimit(Integer.MAX_VALUE);
            while (!cis.isAtEnd()) {
                int size = cis.readRawVarint32();
                int oldLimit = cis.pushLimit(size);
                while (true) {
                    int tag = cis.readTag();
                    if (tag == 0) break;
                    if (com.google.protobuf.WireFormat.getTagFieldNumber(tag) == 5
                            && com.google.protobuf.WireFormat.getTagWireType(tag)
                               == com.google.protobuf.WireFormat.WIRETYPE_VARINT) {
                        rows += cis.readUInt32();
                    } else {
                        cis.skipField(tag);
                    }
                }
                cis.popLimit(oldLimit);
            }
        }
        return rows;
    }

    /**
     * [2026-08-08 FIX RACE] Gộp TOÀN BỘ quý — CHỈ được gọi SAU khi MỌI partition đã kết thúc hoàn toàn
     * (day-loop + flush anchor còn mở + {@link #closeAllRemaining}). Đó là thời điểm DUY NHẤT chắc chắn
     * không còn ai ghi thêm vào bất kỳ quý nào (xem giải thích ở {@link #closeSink}).
     *
     * <p>Vẫn giữ được ràng buộc dung lượng ban đầu: gộp TỪNG QUÝ một, mỗi lúc chỉ cần dư ~1–2 quý (không
     * phải gấp đôi cả full-range). Đánh đổi CÓ CHỦ Ý: việc "push Kaggle rồi xoá local từng quý" chỉ bắt
     * đầu được sau khi job xong, thay vì cuốn chiếu trong lúc chạy — vì chính cuốn chiếu đã gây mất 29%.
     *
     * @return số quý LỖI (thiếu dòng / gộp hỏng). 0 = mọi quý khớp chính xác.
     */
    static int mergeAllQuarters(String outPath, int nParts, QuarterRegistry reg) throws Exception {
        List<Long> quarters = new ArrayList<>(reg.qEndOf.keySet());
        Collections.sort(quarters);
        LOG.info("🧩 GỘP CUỐI: {} quý, {} partition (chỉ chạy khi mọi partition đã kết thúc)", quarters.size(), nParts);
        List<Future<Boolean>> futures = new ArrayList<>();
        for (Long qStart : quarters) {
            final long qs = qStart, qe = reg.qEndOf.get(qStart);
            final long expectRows = reg.rowsOf.get(qStart).sum();
            futures.add(reg.mergerPool.submit(() -> mergeQuarter(outPath, qs, qe, nParts, expectRows)));
        }
        reg.mergerPool.shutdown();
        int bad = 0;
        for (Future<Boolean> f : futures) {
            if (!Boolean.TRUE.equals(f.get())) bad++;
        }
        if (!reg.mergerPool.awaitTermination(60, TimeUnit.MINUTES)) {
            LOG.warn("⚠️ mergerPool CHƯA dừng hẳn sau 60 phút.");
        }
        LOG.info("🧩 GỘP CUỐI xong: {}/{} quý OK", quarters.size() - bad, quarters.size());
        return bad;
    }

    /** Gộp các file .partN của 1 quý thành 1 file quý cuối, ĐỐI CHIẾU số dòng thực rồi mới xoá .partN.
     *
     *  <p><b>[2026-08-08] KIỂM TRA HẬU-EXPORT BẮT BUỘC:</b> sau khi nối byte xong, đếm số dòng THỰC trong
     *  file .pb ({@link #countRowsInPb}) và so với {@code expectRows} = tổng số dòng mà các partition đã
     *  báo cho quý này. Lệch ⇒ log ERROR + trả false (job exit code 2) và GIỮ NGUYÊN các file .partN để
     *  còn cứu dữ liệu. Chính khâu này đáng lẽ phải bắt được vụ mất 29% ngay từ lần chạy đầu.
     *
     *  <p>Partition không có dòng nào trong quý ⇒ không có file .partN ⇒ BỎ QUA (bản cũ ném
     *  FileNotFoundException, và tệ hơn là quý đó không bao giờ được gộp).
     *
     *  @return true nếu file quý cuối khớp chính xác {@code expectRows}. */
    private static boolean mergeQuarter(String outPath, long qStart, long qEnd, int nParts, long expectRows) {
        try {
            return mergeQuarter0(outPath, qStart, qEnd, nParts, expectRows);
        } catch (Exception ex) {
            LOG.error("❌ Gộp quý lỗi", ex);
            return false;
        }
    }

    private static boolean mergeQuarter0(String outPath, long qStart, long qEnd, int nParts, long expectRows)
            throws Exception {
        String finalPath = quarterFinalPath(outPath, qStart, qEnd);
        long totalBytes = 0;
        int nPartFiles = 0;
        // [2026-08-07 TASK-251] Với protobuf, mỗi chunk TỰ CHỨA dictionary symbol + metadata của nó, nên
        // gộp = NỐI BYTE thuần: không parse, không remap sym_id, không ghi lại header. Nhanh hơn hẳn bản
        // CSV cũ (phải đọc/ghi lại từng dòng text) và không có nguy cơ hỏng dữ liệu do parse sai.
        try (java.io.OutputStream out = new java.io.BufferedOutputStream(
                new FileOutputStream(finalPath), 1 << 20)) {
            byte[] buf = new byte[1 << 20];
            for (int p = 0; p < nParts; p++) {
                java.io.File pf = new java.io.File(quarterPartPath(outPath, qStart, qEnd, p));
                if (!pf.exists()) continue;      // partition này không có dòng nào trong quý -> bình thường
                nPartFiles++;
                try (java.io.InputStream in = new java.io.BufferedInputStream(
                        new java.io.FileInputStream(pf), 1 << 20)) {
                    int r;
                    while ((r = in.read(buf)) > 0) {
                        out.write(buf, 0, r);
                        totalBytes += r;
                    }
                }
            }
        }
        long actualRows = countRowsInPb(finalPath);
        if (actualRows != expectRows) {
            LOG.error("❌ QUÝ {} LỆCH SỐ DÒNG: file {} có {} dòng, các partition đã ghi {} dòng (thiếu {} = {}%). "
                            + "GIỮ NGUYÊN các file .partN để cứu dữ liệu. KHÔNG dùng dataset này.",
                    quarterSuffix(qStart, qEnd), finalPath, actualRows, expectRows, expectRows - actualRows,
                    expectRows == 0 ? "n/a"
                            : String.format(Locale.US, "%.4f", 100.0 * (expectRows - actualRows) / expectRows));
            return false;
        }
        for (int p = 0; p < nParts; p++) {
            new java.io.File(quarterPartPath(outPath, qStart, qEnd, p)).delete();
        }
        LOG.info("✅ Đã gộp quý {} -> {} ({} bytes protobuf, {} file part, {} dòng ĐÃ ĐỐI CHIẾU KHỚP, "
                        + "SẴN SÀNG push Kaggle rồi xoá local)",
                quarterSuffix(qStart, qEnd), finalPath, totalBytes, nPartFiles, actualRows);
        return true;
    }

    /**
     * Đóng nến 15m hiện tại của coin: feed nó như PATH bar cho mọi anchor đang mở, finalize anchor quá hạn,
     * rồi tạo anchor MỚI tại bucket này (nếu coin còn sống theo lifecycle). Thứ tự đảm bảo anchor mới KHÔNG
     * tự ăn nến của chính nó (path là (t, t+H], không gồm t).
     */
    private static void finalizeBucket(CoinState cs, String sym, PartCtx ctx, Validate v, long[] emitted) throws Exception {
        long b = cs.curBucketIdx;
        float hi = cs.bHi, lo = cs.bLo, close = cs.bClose;
        // 1) feed bucket cho anchor đang mở
        Iterator<Anchor> it = cs.active.iterator();
        while (it.hasNext()) {
            Anchor a = it.next();
            int o = (int) (b - a.tStep);
            if (o < 1) continue;                 // không xảy ra (bucket tăng dần)
            if (o > H_MAX) {                      // hết cửa sổ → emit & gỡ
                emit(a, sym, ctx, v, emitted);
                it.remove();
                continue;
            }
            updateAnchor(a, o, hi, lo, close);
        }
        // 2) tạo anchor mới tại t = b. KEYSET_ON -> CHI tao neu (symId,t) thuoc keyset features (khop 0.10
        //    tuyet doi). Khong keyset -> giu hanh vi cu (all-coin theo lifecycle isAlive).
        long tEpoch = b * SAMPLE_STEP_MS;
        boolean makeAnchor;
        if (KEYSET_ON) {
            short sidA = com.binance.chuyennd.ai_ml.data.SimpleSymbolMapper.getInstance().getId(sym);
            makeAnchor = sidA >= 0 && close > 0 && keysetContains(sidA, tEpoch);
        } else {
            makeAnchor = LIFECYCLE.isAlive(sym, tEpoch) && close > 0;
        }
        if (makeAnchor) {
            cs.active.addLast(new Anchor(b, close));
        }
    }

    /** Cập nhật 1 anchor với 1 nến path tại offset o (bước 15m) trong (t, t+H_MAX]. */
    private static void updateAnchor(Anchor a, int o, float hi, float lo, float close) {
        // (a) xử lý CROSS H mà KHÔNG có nến đúng mốc (gap): snapshot bằng trạng thái TRƯỚC nến này
        //     (retEnd để trống vì không có close đúng mốc t+H)
        for (int h = 0; h < H_STEPS.length; h++) {
            if (!a.snap[h] && o > H_STEPS[h]) snapshot(a, h, Float.NaN);
        }
        // (b) cập nhật running max/min (chỉ trong cửa sổ)
        float favR = hi / a.closeT - 1f;
        float advR = lo / a.closeT - 1f;
        if (favR > a.maxFav) { a.maxFav = favR; a.tHitFavStep = o; }
        if (advR < a.maxAdv) { a.maxAdv = advR; a.tHitAdvStep = o; }
        a.barsSeen++;
        // (c) snapshot tại mốc H ĐÚNG (có nến tại t+H): gồm cả nến này + retEnd close-to-close
        for (int h = 0; h < H_STEPS.length; h++) {
            if (!a.snap[h] && o == H_STEPS[h]) snapshot(a, h, close / a.closeT - 1f);
        }
    }

    /** Chốt snapshot cho mốc H thứ h từ trạng thái running hiện tại. retEnd = NaN ⇒ không có close đúng mốc (gap). */
    private static void snapshot(Anchor a, int h, float retEnd) {
        a.snap[h] = true;
        a.maxFavH[h] = a.maxFav;
        a.maxAdvH[h] = a.maxAdv;
        a.tHitFavH[h] = a.tHitFavStep;
        a.tHitAdvH[h] = a.tHitAdvStep;
        a.nBarsH[h] = a.barsSeen;
        if (!Float.isNaN(retEnd)) { a.retEndH[h] = retEnd; a.retEndSet[h] = true; }
    }

    /** Emit 1 anchor: mốc H nào chưa snapshot (data hết sớm — coin chết/cuối dữ liệu) → chốt incomplete.
     *  [2026-08-06 fix #3] Ghi vào ĐÚNG file quý ứng với tEpoch (thời điểm TẠO anchor), KHÔNG phải lúc emit
     *  (2 thời điểm có thể khác quý — xem class-doc). */
    private static void emit(Anchor a, String sym, PartCtx ctx, Validate v, long[] emitted) throws Exception {
        if (a.barsSeen == 0) return;   // không có nến tương lai nào (anchor sát cuối tuyệt đối) → bỏ, không 0 giả
        for (int h = 0; h < H_STEPS.length; h++) if (!a.snap[h]) snapshot(a, h, Float.NaN);

        long tEpoch = a.tStep * SAMPLE_STEP_MS;
        // [2026-08-07 TASK-251] Trước đây build 1 dòng CSV bằng StringBuilder; giờ đẩy thẳng số vào
        // LabelPbSink (nó lo scale 1e-5, delta giữa horizon, sort trong chunk, nén columnar).
        // tHit* nhân STEP_MIN để ra PHÚT THẬT — giữ nguyên đơn vị như CSV cũ, downstream không phải đổi.
        int nH = H_STEPS.length;
        int[] tHitFavMin = new int[nH];
        int[] tHitAdvMin = new int[nH];
        for (int h = 0; h < nH; h++) {
            tHitFavMin[h] = a.tHitFavH[h] * STEP_MIN;
            tHitAdvMin[h] = a.tHitAdvH[h] * STEP_MIN;
        }
        QuarterSink s = sinkFor(ctx, tEpoch);
        s.w.add(sym, tEpoch, a.maxFavH, a.maxAdvH, tHitFavMin, tHitAdvMin, a.retEndH, a.retEndSet, a.nBarsH);
        s.rows++;
        emitted[0]++;
        v.collect(sym, tEpoch, a);
    }

    private static String header() {
        StringBuilder h = new StringBuilder("tEpochMs,tDate,symbol");
        for (String n : H_NAME)
            h.append(",maxFav_").append(n).append(",maxAdv_").append(n)
             .append(",tHitFav_").append(n).append(",tHitAdv_").append(n)
             .append(",retEnd_").append(n).append(",nBars_").append(n);
        return h.append('\n').toString();
    }

    private static String f(float val) {
        return (Float.isNaN(val) || val == -Float.MAX_VALUE || val == Float.MAX_VALUE)
                ? "" : String.format(Locale.US, "%.6f", val);
    }

    // ================== VALIDATE (chạy sau export trên 226) ==================

    /**
     * Gom thống kê khi emit + recompute độc lập một số anchor. Mọi kiểm tra theo §Validate của TASK-024:
     * (a) phân bố maxFav/maxAdv theo H/năm; (b) tỉ lệ giả-lập chạm +6%/72h; (c) recompute ~5 (coin,t) đường khác;
     * (d) look-ahead inherent (chỉ nến trong (t,t+H]); (e) bắt coin bơm lịch sử (top maxFav_72h); (f) coin die.
     */
    private static final class Validate {
        // ⚠️ FIX khi thêm horizon: H72 PHẢI trỏ đúng "72h" theo TÊN, KHÔNG suy từ length-1
        // (length-1 giờ là mốc dài nhất = 30d sau khi thêm 7d/14d/30d — nếu để length-1 thì
        // toàn bộ validate (b)/(c)/(e)/(f) sẽ âm thầm đổi sang đo 30d thay vì 72h).
        final int H72 = indexOfHorizon("72h");
        // (a) phân bố
        final List<Float>[] favAll = lists();
        final List<Float>[] advAll = lists();
        // (a) theo năm cho maxFav_72h
        final Map<Integer, List<Float>> year2fav72 = new TreeMap<>();
        // (b) hit +6%/72h (chỉ trên nBars_72h đủ)
        long hit6 = 0, complete72 = 0;
        // (e) top pump
        final TreeMap<Float, String> topPump = new TreeMap<>();
        // (f) coin die
        long incomplete72 = 0;
        final Set<String> deadSyms = new TreeSet<>();
        // (c) recompute: bắt vài anchor 72h-đủ để đọc lại đường khác
        final List<long[]> watch = new ArrayList<>();   // {tEpoch, tStep} ; sym ở watchSym
        final List<String> watchSym = new ArrayList<>();
        final List<float[]> watchExp = new ArrayList<>(); // {maxFav72, maxAdv72, retEnd72}

        @SuppressWarnings("unchecked")
        private static List<Float>[] lists() {
            List<Float>[] a = new List[H_STEPS.length];
            for (int i = 0; i < a.length; i++) a[i] = new ArrayList<>();
            return a;
        }

        final boolean disabled;
        Validate(boolean disabled) { this.disabled = disabled; }
        void collect(String sym, long tEpoch, Anchor a) {
            if (disabled) return;
            for (int h = 0; h < H_STEPS.length; h++) {
                if (a.maxFavH[h] != -Float.MAX_VALUE) favAll[h].add(a.maxFavH[h]);
                if (a.maxAdvH[h] != Float.MAX_VALUE) advAll[h].add(a.maxAdvH[h]);
            }
            int y = year(tEpoch);
            if (a.maxFavH[H72] != -Float.MAX_VALUE)
                year2fav72.computeIfAbsent(y, x -> new ArrayList<>()).add(a.maxFavH[H72]);

            boolean full72 = a.nBarsH[H72] >= H_STEPS[H72];
            if (full72) {
                complete72++;
                if (a.maxFavH[H72] >= 0.06f) hit6++;
                // (e) top pump
                if (a.maxFavH[H72] != -Float.MAX_VALUE) {
                    topPump.put(a.maxFavH[H72], sym + "@" + FMT.get().format(new Date(tEpoch)));
                    if (topPump.size() > 20) topPump.remove(topPump.firstKey());
                }
                // (c) bắt 5 anchor đầu đủ-72h để recompute
                if (watch.size() < 5) {
                    watch.add(new long[]{tEpoch, a.tStep});
                    watchSym.add(sym);
                    watchExp.add(new float[]{a.maxFavH[H72], a.maxAdvH[H72], a.retEndSet[H72] ? a.retEndH[H72] : Float.NaN});
                }
            } else {
                incomplete72++;
                if (a.nBarsH[H72] < H_STEPS[H72]) deadSyms.add(sym);
            }
        }

        void report() throws Exception {
            if (disabled) return;
            LOG.info("=== (a) PHÂN BỐ maxFav/maxAdv mỗi H (p1/p5/p50/p95/p99) ===");
            for (int h = 0; h < H_STEPS.length; h++) {
                List<Float> fv = favAll[h], ad = advAll[h];
                Collections.sort(fv); Collections.sort(ad);
                LOG.info("  {} maxFav: n={} p1={} p5={} p50={} p95={} p99={}", H_NAME[h], fv.size(),
                        pc(fv, 1), pc(fv, 5), pc(fv, 50), pc(fv, 95), pc(fv, 99));
                LOG.info("  {} maxAdv: n={} p1={} p5={} p50={} p95={} p99={}", H_NAME[h], ad.size(),
                        pc(ad, 1), pc(ad, 5), pc(ad, 50), pc(ad, 95), pc(ad, 99));
            }
            LOG.info("=== (a') maxFav_72h theo NĂM (p50/p95 | #(≥+6%)) ===");
            for (Map.Entry<Integer, List<Float>> e : year2fav72.entrySet()) {
                List<Float> r = e.getValue(); Collections.sort(r);
                long h6 = r.stream().filter(x -> x >= 0.06f).count();
                LOG.info("  {}: n={} p50={} p95={} #(≥6%)={} ({}%)", e.getKey(), r.size(),
                        pc(r, 50), pc(r, 95), h6, r.isEmpty() ? 0 : String.format(Locale.US, "%.1f", 100.0 * h6 / r.size()));
            }
            LOG.info("=== (b) TỈ LỆ giả-lập chạm +6% trong 72h (trên nBars_72h ĐỦ) = {}/{} = {}% (đối chiếu trực giác label cũ) ===",
                    hit6, complete72, complete72 == 0 ? 0 : String.format(Locale.US, "%.2f", 100.0 * hit6 / complete72));

            LOG.info("=== (c) RECOMPUTE độc lập 72h (đọc lại window 1m→15m đường khác) ===");
            for (int i = 0; i < watch.size(); i++) {
                long tEpoch = watch.get(i)[0];
                String sym = watchSym.get(i);
                float[] exp = watchExp.get(i);
                float[] re = recompute72(sym, tEpoch);
                boolean okF = re != null && Math.abs(re[0] - exp[0]) < 1e-4;
                boolean okA = re != null && Math.abs(re[1] - exp[1]) < 1e-4;
                LOG.info("  {} t={} : maxFav export={} recompute={} {} | maxAdv export={} recompute={} {}",
                        sym, FMT.get().format(new Date(tEpoch)),
                        f(exp[0]), re == null ? "null" : f(re[0]), okF ? "KHỚP✅" : "LỆCH🔴",
                        f(exp[1]), re == null ? "null" : f(re[1]), okA ? "KHỚP✅" : "LỆCH🔴");
            }

            LOG.info("=== (d) LOOK-AHEAD: path chỉ dùng nến (t, t+H]; (coin,t) thiếu data tới t+H giữ nBars thiếu (KHÔNG 0 giả), train lọc. ===");

            LOG.info("=== (e) BẮT COIN BƠM (top-20 maxFav_72h — kỳ vọng đúng đợt bơm lịch sử) ===");
            for (Map.Entry<Float, String> e : topPump.descendingMap().entrySet())
                LOG.info("   maxFav_72h={} : {}", f(e.getKey()), e.getValue());

            LOG.info("=== (f) COIN DIE / data dừng: {} dòng nBars_72h THIẾU; {} coin chạm cảnh thiếu-data ===",
                    incomplete72, deadSyms.size());
            int shown = 0;
            for (String s : deadSyms) {
                LOG.info("   coin thiếu-data tới 72h: {} (status lifecycle={})", s, LIFECYCLE.getStatus(s));
                if (++shown >= 15) break;
            }
        }

        /**
         * Recompute độc lập maxFav/maxAdv_72h bằng ĐƯỜNG KHÁC: đọc lại 1m từ t, gộp 15m, tính trực tiếp.
         * Khớp định nghĩa chính: {@code close(t)} = close nến 1m CUỐI trong bucket t; path = bucket (tBucket, tBucket+288].
         */
        private float[] recompute72(String sym, long tEpoch) throws Exception {
            long tBucket = tEpoch / SAMPLE_STEP_MS;
            int h72Steps = H_STEPS[H72];           // = 288@15m hoac 4320@1m (72h/STEP_MIN) — KHONG dung H_MAX
            int minutes = (h72Steps + 1) * STEP_MIN + 5;   // du bucket t + h72Steps bucket sau (truoc: hardcode *15)
            TreeMap<Long, Map<String, KlineObjectSimple>> win =
                    DataManagerAerospikeFloatSim.readDataFromAerospikeCustom(tEpoch, minutes);
            if (win == null || win.isEmpty()) return null;
            // gộp 15m: idx -> {hi, lo, lastClose, lastTs}; lastClose chốt theo ts lớn nhất trong bucket
            Map<Long, float[]> bucket = new TreeMap<>();
            for (Map.Entry<Long, Map<String, KlineObjectSimple>> e : win.entrySet()) {
                long ep = e.getKey();
                long idx = ep / SAMPLE_STEP_MS;
                if (idx < tBucket || idx > tBucket + h72Steps) continue;
                KlineObjectSimple k = e.getValue().get(sym);
                if (k == null || !Utils.isTickerAvailable(k)) continue;
                float[] b = bucket.computeIfAbsent(idx, x -> new float[]{-Float.MAX_VALUE, Float.MAX_VALUE, 0f, -1f});
                if (k.maxPrice > b[0]) b[0] = k.maxPrice;
                if (k.minPrice < b[1]) b[1] = k.minPrice;
                if (ep > b[3]) { b[3] = ep; b[2] = k.priceClose; }
            }
            float[] bt = bucket.get(tBucket);
            if (bt == null || bt[2] <= 0) return null;
            float closeT = bt[2];
            float maxFav = -Float.MAX_VALUE, maxAdv = Float.MAX_VALUE;
            for (Map.Entry<Long, float[]> e : bucket.entrySet()) {
                if (e.getKey() <= tBucket) continue;   // path chỉ (t, t+H]
                float[] b = e.getValue();
                float favR = b[0] / closeT - 1f, advR = b[1] / closeT - 1f;
                if (favR > maxFav) maxFav = favR;
                if (advR < maxAdv) maxAdv = advR;
            }
            return new float[]{maxFav, maxAdv};
        }
    }

    /** Tìm index của mốc H theo TÊN (vd "72h") trong {@link #H_NAME} — tránh giả định vị trí (length-1 đổi
     *  nghĩa mỗi khi thêm horizon mới ở cuối mảng). */
    private static int indexOfHorizon(String name) {
        for (int i = 0; i < H_NAME.length; i++) if (H_NAME[i].equals(name)) return i;
        throw new IllegalStateException("Không tìm thấy horizon '" + name + "' trong H_NAME");
    }

    private static String pc(List<Float> sorted, int p) {
        if (sorted.isEmpty()) return "-";
        int idx = Math.min(sorted.size() - 1, (int) Math.ceil(p / 100.0 * sorted.size()) - 1);
        if (idx < 0) idx = 0;
        return String.format(Locale.US, "%.4f", sorted.get(idx));
    }

    private static final ThreadLocal<SimpleDateFormat> FMT =
            ThreadLocal.withInitial(() -> new SimpleDateFormat("yyyyMMdd-HHmm")); // GMT+7

    private static int year(long ms) { return Integer.parseInt(new SimpleDateFormat("yyyy").format(new Date(ms))); }
}
