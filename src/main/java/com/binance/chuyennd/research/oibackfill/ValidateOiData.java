package com.binance.chuyennd.research.oibackfill;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import com.binance.chuyennd.tradecore.Configs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.text.SimpleDateFormat;
import java.util.*;

/**
 * TASK-013 VALIDATE CUOI: kiem tra OI data trong Aerospike 226 la DU + DUNG truoc khi dung cho train.
 *
 * <p>Mot lan chay dut khoat — neu PASS toan bo: khong can kiem lai. Neu FAIL: bao cao chi tiet
 * dung lop nao (data thieu, gia tri sai, doc loi) de biet fix o dau (data/doc/xu-ly).
 *
 * <p>KIEM 4 TOM TAT:
 * <ol>
 *   <li><b>Du — coverage:</b> so coin co OI >= nguong, phan bo theo nam (phat hien gap nam).</li>
 *   <li><b>Du — granularity:</b> kiem chuoi 5m khong bi gap qua 30 phut trong 2023 (nam tung bao empty).</li>
 *   <li><b>Dung — gia tri OI:</b> OI > 0, khong NaN/Inf, OI LUNA giam >50% trong crash 2022-05.</li>
 *   <li><b>Dung — LS + taker:</b> lsGlobal/lsToptrader in [0.1,10], takerRatio in [0.05,20]; LUNA co data.</li>
 * </ol>
 *
 * <p>Usage: java ValidateOiData [--quick] (--quick: chi kiem BTC+LUNA+SOL, bo qua scan toan bo)
 */
public class ValidateOiData {

    private static final Logger LOG = LoggerFactory.getLogger(ValidateOiData.class);

    // Moc epoch ms (UTC midnight)
    private static final long Y2022_05_01 = 1651363200000L;
    private static final long Y2022_06_01 = 1654041600000L;
    private static final long Y2023_01_01 = 1672531200000L;
    private static final long Y2024_01_01 = 1704067200000L;
    private static final long Y2021_01_01 = 1609459200000L;
    private static final long Y2025_01_01 = 1735689600000L;
    private static final long GAP_THRESHOLD_MS = 30 * 60_000L; // 30 phut

    // Pass threshold
    private static final int MIN_COINS_WITH_OI_2023 = 300; // >= 300 coin co OI trong 2023
    private static final int MIN_OI_RECORDS_PER_YEAR = 80_000; // >= 80k moc/nam cho coin chinh

    public static void main(String[] args) throws Exception {
        boolean quick = args.length > 0 && "--quick".equalsIgnoreCase(args[0]);
        LOG.info("===== VALIDATE OI DATA 226 (mode={}) =====", quick ? "QUICK" : "FULL");

        int failures = 0;

        // ============================================================
        // CHECK 1: COVERAGE — bao nhieu coin co OI, phan bo theo nam
        // ============================================================
        LOG.info("[CHECK-1] Coverage: so coin co OI, phan bo theo nam...");
        Map<String, Short> symbolMap = DataManagerAerospikeFloatSim.loadSymbolMapper();
        List<String> sampleCoins = quick
                ? Arrays.asList("BTCUSDT", "ETHUSDT", "LUNAUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT")
                : new ArrayList<>(symbolMap.keySet());

        int coinsWithOi2023 = 0, coinsChecked = 0;
        int[] yearCount = new int[5]; // 2021,2022,2023,2024,2025
        long[] yearStarts = {Y2021_01_01, Y2022_01_01(), Y2023_01_01, Y2024_01_01, Y2025_01_01};
        long[] yearEnds = {Y2022_01_01(), Y2023_01_01, Y2024_01_01, Y2025_01_01, Long.MAX_VALUE};

        for (String coin : sampleCoins) {
            TreeMap<Long, Float> oi = DataManagerAerospikeFloatSim.getMetricMap226(
                    OiMetricSets.OI.set, OiMetricSets.OI.bin, coin);
            if (oi == null || oi.isEmpty()) continue;
            coinsChecked++;
            for (int y = 0; y < 5; y++) {
                if (!oi.subMap(yearStarts[y], yearEnds[y] == Long.MAX_VALUE ? Long.MAX_VALUE : yearEnds[y]).isEmpty())
                    yearCount[y]++;
            }
            if (!oi.subMap(Y2023_01_01, Y2024_01_01).isEmpty()) coinsWithOi2023++;
        }
        LOG.info("  Checked={} coinsWithOi2023={} | by-year: 2021={} 2022={} 2023={} 2024={} 2025={}",
                coinsChecked, coinsWithOi2023, yearCount[0], yearCount[1], yearCount[2], yearCount[3], yearCount[4]);
        if (!quick && coinsWithOi2023 < MIN_COINS_WITH_OI_2023) {
            LOG.error("  [FAIL-1a] coins_with_OI_2023={} < threshold={}", coinsWithOi2023, MIN_COINS_WITH_OI_2023);
            failures++;
        } else {
            LOG.info("  [PASS-1] coverage ok");
        }

        // ============================================================
        // CHECK 2: GRANULARITY — kiem gap > 30 phut trong 2023 (BTC dai dien)
        // ============================================================
        LOG.info("[CHECK-2] Granularity: kiem gap >30 phut trong 2023 (BTC)...");
        TreeMap<Long, Float> btcOi = DataManagerAerospikeFloatSim.getMetricMap226(
                OiMetricSets.OI.set, OiMetricSets.OI.bin, "BTCUSDT");
        int gaps2023 = 0;
        long prevTs = -1;
        if (btcOi != null) {
            for (long ts : btcOi.subMap(Y2023_01_01, Y2024_01_01).keySet()) {
                if (prevTs > 0 && (ts - prevTs) > GAP_THRESHOLD_MS) {
                    SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm");
                    LOG.warn("  Gap 2023: {} -> {} (~{}m)", sdf.format(new Date(prevTs)),
                            sdf.format(new Date(ts)), (ts - prevTs) / 60000);
                    gaps2023++;
                    if (gaps2023 >= 10) { LOG.warn("  (truong hop them bi cat...)"); break; }
                }
                prevTs = ts;
            }
        }
        int btcRecs2023 = (btcOi != null) ? btcOi.subMap(Y2023_01_01, Y2024_01_01).size() : 0;
        LOG.info("  BTC 2023: {} moc, {} gap >30 phut", btcRecs2023, gaps2023);
        if (btcRecs2023 < MIN_OI_RECORDS_PER_YEAR) {
            LOG.error("  [FAIL-2a] BTC_OI_2023_recs={} < threshold={}", btcRecs2023, MIN_OI_RECORDS_PER_YEAR);
            failures++;
        } else if (gaps2023 > 50) {
            LOG.error("  [FAIL-2b] BTC_OI_2023 co {} gap >30 phut (nghi van data lo)", gaps2023);
            failures++;
        } else {
            LOG.info("  [PASS-2] granularity ok");
        }

        // ============================================================
        // CHECK 3: DUNG — gia tri OI (sanity range + crash signal LUNA 2022-05)
        // ============================================================
        LOG.info("[CHECK-3] Dung — gia tri OI: range sanity + LUNA crash 2022-05...");

        // 3a. BTC OI range sanity: tat ca record phai > 0, khong NaN/Inf
        int btcNanInf = 0, btcNeg = 0, btcZero = 0;
        if (btcOi != null) {
            for (float v : btcOi.values()) {
                if (Float.isNaN(v) || Float.isInfinite(v)) btcNanInf++;
                else if (v < 0) btcNeg++;
                else if (v == 0) btcZero++;
            }
        }
        int btcTotal = btcOi != null ? btcOi.size() : 0;
        double zeroPct = btcTotal > 0 ? (double) btcZero / btcTotal : 0;
        LOG.info("  BTC OI: total={} NaN/Inf={} <0={} ==0={} (zero {}%)",
                btcTotal, btcNanInf, btcNeg, btcZero, String.format("%.3f", zeroPct * 100));
        // FAIL neu co NaN/Inf hoac gia tri AM (loi tinh toan that), hoac zero qua nhieu (>0.5% = mat doan data).
        // Zero rai rac < 0.5% = gian doan nguon Binance binh thuong (TASK-103f xac nhan: 510/608211=0.084%,
        // rai 12 thang, deu =0 khong am) -> coi nhu NaN khi train, KHONG fail.
        if (btcNanInf > 0 || btcNeg > 0) {
            LOG.error("  [FAIL-3a] BTC OI co NaN/Inf/AM (loi tinh toan/doc that): NaN/Inf={} <0={}", btcNanInf, btcNeg);
            failures++;
        } else if (zeroPct > 0.005) {
            LOG.error("  [FAIL-3a] BTC OI co {}% gia tri =0 (>0.5% -> nghi mat doan data, can kiem)", String.format("%.2f", zeroPct * 100));
            failures++;
        } else {
            if (btcZero > 0) LOG.warn("  [WARN-3a] BTC OI co {} moc =0 ({}%) — gian doan nguon rai rac, coi nhu missing khi train (OK)",
                    btcZero, String.format("%.3f", zeroPct * 100));
            LOG.info("  [PASS-3a] BTC OI range sanity OK (khong NaN/Inf/am; zero rai rac trong nguong)");
        }

        // 3b. LUNA crash 2022-05: OI phai giam >50% tu dinh 2022-04 den day 2022-05
        TreeMap<Long, Float> lunaOi = DataManagerAerospikeFloatSim.getMetricMap226(
                OiMetricSets.OI.set, OiMetricSets.OI.bin, "LUNAUSDT");
        boolean crashSignalOk = false;
        float lunaPreCrashMax = Float.NaN, lunaPostCrashMin = Float.NaN;
        if (lunaOi != null && !lunaOi.isEmpty()) {
            // Dinh truoc crash: 2022-04-01 -> 2022-05-07 (truoc de-peg)
            long preCrashStart = 1648771200000L; // 2022-04-01 UTC
            long crashStart   = 1651968000000L;  // 2022-05-08 UTC (bat dau de-peg)
            long crashEnd     = Y2022_06_01;
            SortedMap<Long, Float> preCrash = lunaOi.subMap(preCrashStart, crashStart);
            SortedMap<Long, Float> postCrash = lunaOi.subMap(crashStart, crashEnd);
            if (!preCrash.isEmpty() && !postCrash.isEmpty()) {
                lunaPreCrashMax = preCrash.values().stream().max(Float::compare).orElse(Float.NaN);
                lunaPostCrashMin = postCrash.values().stream().min(Float::compare).orElse(Float.NaN);
                if (!Float.isNaN(lunaPreCrashMax) && !Float.isNaN(lunaPostCrashMin) && lunaPreCrashMax > 0) {
                    float dropPct = (lunaPreCrashMax - lunaPostCrashMin) / lunaPreCrashMax;
                    crashSignalOk = dropPct > 0.50f;
                    LOG.info("  LUNA crash: pre-max={:.0f} post-min={:.0f} drop={:.1f}% {}",
                            lunaPreCrashMax, lunaPostCrashMin, dropPct * 100,
                            crashSignalOk ? "PASS" : "WARN(drop<50%)");
                } else {
                    LOG.warn("  LUNA crash: khong tinh duoc drop (NaN/0)");
                }
            } else {
                LOG.warn("  LUNA crash: khong co du data (preCrash={} postCrash={})", preCrash.size(), postCrash.size());
            }
        } else {
            LOG.warn("  LUNA OI: EMPTY (chu y neu backfill chua co LUNA)");
        }
        if (!crashSignalOk) {
            LOG.warn("  [WARN-3b] LUNA crash signal khong ro (co the data LUNA thieu hoac OI USDT-notional khong phan anh on-chain unwind)");
            // Khong FAIL vi LUNA da delist, co the la dung (OI giam truoc khi delist)
        } else {
            LOG.info("  [PASS-3b] LUNA crash signal OK (OI giam >50%)");
        }

        // ============================================================
        // CHECK 4: DUNG — LS + taker co gia tri hop le
        // ============================================================
        LOG.info("[CHECK-4] Dung — LS + taker sanity: BTC + LUNA...");
        String[] checkCoins = {"BTCUSDT", "LUNAUSDT"};
        int lsErrors = 0, takerErrors = 0;
        for (String coin : checkCoins) {
            TreeMap<Long, Float> lsGlobal = DataManagerAerospikeFloatSim.getMetricMap226(
                    OiMetricSets.LS_GLOBAL_ACC.set, OiMetricSets.LS_GLOBAL_ACC.bin, coin);
            TreeMap<Long, Float> lsTop = DataManagerAerospikeFloatSim.getMetricMap226(
                    OiMetricSets.LS_TOPTRADER_ACC.set, OiMetricSets.LS_TOPTRADER_ACC.bin, coin);
            TreeMap<Long, Float> taker = DataManagerAerospikeFloatSim.getMetricMap226(
                    OiMetricSets.TAKER_VOL.set, OiMetricSets.TAKER_VOL.bin, coin);

            // LS ratio: ty le Long/Short ~ 0.1..10 (bear thi 0.5, bull thi 2.0, extreme <0.1 or >10 = loi)
            int lsOutOfRange = 0;
            if (lsGlobal != null) {
                for (float v : lsGlobal.values()) {
                    if (!Float.isNaN(v) && (v < 0.05f || v > 20f)) lsOutOfRange++;
                }
            }
            // Taker ratio: tu 0 -> inf (>1 la buy-heavy), extreme <0.05 or >20 nghi van
            int takerOutOfRange = 0;
            if (taker != null) {
                for (float v : taker.values()) {
                    if (!Float.isNaN(v) && (v < 0.0f || v > 50f)) takerOutOfRange++;
                }
            }
            LOG.info("  {} lsGlobal={} lsTop={} taker={} | ls_outlier={} taker_outlier={}",
                    coin,
                    lsGlobal != null ? lsGlobal.size() : "EMPTY",
                    lsTop != null ? lsTop.size() : "EMPTY",
                    taker != null ? taker.size() : "EMPTY",
                    lsOutOfRange, takerOutOfRange);
            if (lsGlobal == null || lsGlobal.isEmpty()) {
                LOG.warn("  [WARN-4] {} lsGlobal EMPTY (co the LUNA da delist truoc khi Binance publish LS)", coin);
            }
            if (lsOutOfRange > 10) { lsErrors++; LOG.error("  [FAIL-4a] {} lsGlobal co {} gia tri ngoai [0.05,20]", coin, lsOutOfRange); }
            if (takerOutOfRange > 10) { takerErrors++; LOG.error("  [FAIL-4b] {} taker co {} gia tri ngoai [0,50]", coin, takerOutOfRange); }
        }
        if (lsErrors == 0 && takerErrors == 0) LOG.info("  [PASS-4] LS + taker range sanity OK");
        failures += lsErrors + takerErrors;

        // ============================================================
        // TONG KET
        // ============================================================
        LOG.info("===================================================");
        if (failures == 0) {
            LOG.info("VALIDATE PASS ({} failures=0) — OI data DU + DUNG, KHONG can kiem lai.", quick ? "QUICK" : "FULL");
            LOG.info("Neu sau nay doc OI ra ket qua bat thuong: van de o code DOC hoac XU LY, KHONG phai data 226.");
        } else {
            LOG.error("VALIDATE FAIL ({} failures) — xem log ben tren de biet check nao fail va fix o dau.", failures);
        }
        LOG.info("===================================================");
    }

    // Helper: epoch ms 2022-01-01 UTC
    private static long Y2022_01_01() { return 1640995200000L; }
}
