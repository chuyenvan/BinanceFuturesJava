package com.binance.chuyennd.ai_ml.validation.data;

import com.binance.chuyennd.aerospike.DataManagerAerospikeFloatSim;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;import java.util.zip.GZIPInputStream;

/**
 * TASK (2026-07-10) — CarryEdgeProbe v3: PnL THAT cua book carry cross-sectional dollar-neutral.
 * READ-ONLY. Do quyet dinh: carry (funding, ~0.05%/ky) co song noi PRICE PnL (~vai %/ky) khong?
 *
 * Moi ky 8h slot:
 *   - SHORT top-K coin funding DUONG cao nhat: PnL = +funding_nhan - retFwd (short lo khi gia len)
 *   - LONG bottom-K coin funding AM sau nhat:  PnL = +funding_nhan + retFwd (long lai khi gia len)
 *   - Dollar-neutral: book net price = mean(retLong) - mean(retShort). Neu coin funding cao van pump
 *     -> retShort duong -> chan short lo -> co the nuot carry. DAY la phep thu that.
 * retFwd = retEnd_12h tu funding_label.csv (proxy price move ~ 1.5 ky; horizon mismatch chap nhan cho test huong).
 * Net = funding_gross + price_pnl - fee*turnover. Cong don theo quy.
 *
 * Env: CARRY_TOPK(5) CARRY_MIN_COINS(20) RATE_FEE(0.0004) RATE_CAP(0.03)
 *      LABEL_CSV(/home/ubuntu/kaggle_selector_ds/funding_label.csv.gz)
 */
public class CarryEdgeProbe {
    private static final Logger LOG = LoggerFactory.getLogger(CarryEdgeProbe.class);

    public static void main(String[] args) throws Exception {
        int topK = Integer.parseInt(System.getenv().getOrDefault("CARRY_TOPK", "5"));
        int minCoins = Integer.parseInt(System.getenv().getOrDefault("CARRY_MIN_COINS", "20"));
        double fee = Double.parseDouble(System.getenv().getOrDefault("RATE_FEE", "0.0004"));
        double rateCap = Double.parseDouble(System.getenv().getOrDefault("RATE_CAP", "0.03"));
        String labelCsv = System.getenv().getOrDefault("LABEL_CSV", "/home/ubuntu/kaggle_selector_ds/funding_label.csv.gz");

        LOG.info("v3 START topK={} minCoins={} fee={} rateCap={}", topK, minCoins, fee, rateCap);

        // 1) funding_label.csv -> per symbol TreeMap<ts, retEnd_12h>
        Map<String, TreeMap<Long, Float>> ret = new HashMap<>();
        int rows = 0;
        try (BufferedReader br = new BufferedReader(new InputStreamReader(
                new GZIPInputStream(new java.io.FileInputStream(labelCsv))))) {
            String line = br.readLine(); // header
            while ((line = br.readLine()) != null) {
                String[] p = line.split(",");
                if (p.length < 15) continue;
                try {
                    long ts = Long.parseLong(p[0]);
                    String sym = p[2];
                    String r = p[13]; // retEnd_12h
                    if (r.isEmpty() || r.equals("NaN")) continue;
                    ret.computeIfAbsent(sym, k -> new TreeMap<>()).put(ts, Float.parseFloat(r));
                    rows++;
                } catch (Exception ignored) {}
            }
        }
        LOG.info("label: {} rows, {} symbol co retEnd_12h", rows, ret.size());

        // 2) funding_data
        Map<String, TreeMap<Long, Float>> all = DataManagerAerospikeFloatSim.getAllFundingMap();
        LOG.info("funding_data: {} symbol", all.size());

        // 3) ts slot -> list [symbol, rate]
        TreeMap<Long, List<Object[]>> ts2 = new TreeMap<>();
        for (Map.Entry<String, TreeMap<Long, Float>> e : all.entrySet()) {
            for (Map.Entry<Long, Float> r : e.getValue().entrySet()) {
                if (r.getValue() == null || r.getValue().isNaN()) continue;
                if (Math.abs(r.getValue()) > rateCap) continue;
                long slot = (r.getKey() / 28800000L) * 28800000L;
                ts2.computeIfAbsent(slot, k -> new ArrayList<>()).add(new Object[]{e.getKey(), r.getValue()});
            }
        }
        LOG.info("so ky (8h): {}", ts2.size());

        TreeMap<String, double[]> quarter = new TreeMap<>(); // [fundingGross, pricePnl, net, nP, turnover, matched]
        Set<String> prevLegs = new HashSet<>();
        for (Map.Entry<Long, List<Object[]>> e : ts2.entrySet()) {
            List<Object[]> rs = e.getValue();
            if (rs.size() < minCoins) continue;
            rs.sort((a, b) -> Float.compare((Float) a[1], (Float) b[1]));
            int n = rs.size();
            int k = Math.min(topK, n / 2);
            long slot = e.getKey();

            double fundingGross = 0, priceLong = 0, priceShort = 0;
            int nLong = 0, nShort = 0;
            Set<String> legs = new HashSet<>();
            for (int i = 0; i < k; i++) {
                String symL = (String) rs.get(i)[0];          // funding am nhat -> LONG
                String symS = (String) rs.get(n - 1 - i)[0];  // funding duong nhat -> SHORT
                fundingGross += Math.abs((Float) rs.get(i)[1]) + Math.abs((Float) rs.get(n - 1 - i)[1]);
                Float rL = fwd(ret.get(symL), slot);
                Float rS = fwd(ret.get(symS), slot);
                if (rL != null) { priceLong += rL; nLong++; }
                if (rS != null) { priceShort += rS; nShort++; }
                legs.add("L:" + symL); legs.add("S:" + symS);
            }
            double fundingPerLeg = fundingGross / (2 * k);
            // price PnL dollar-neutral per leg = (mean long ret) - (mean short ret), /? scale per-leg
            double pLong = nLong > 0 ? priceLong / nLong : 0;
            double pShort = nShort > 0 ? priceShort / nShort : 0;
            double pricePnl = (pLong - pShort) / 2.0; // trung binh 2 chan, dollar-neutral

            int churned = 0; for (String lg : legs) if (!prevLegs.contains(lg)) churned++;
            double turnover = legs.isEmpty() ? 0 : (double) churned / legs.size();
            double net = fundingPerLeg + pricePnl - (2 * fee) * turnover;
            prevLegs = legs;

            String qk = qKey(slot);
            double[] a = quarter.computeIfAbsent(qk, x -> new double[6]);
            a[0] += fundingPerLeg; a[1] += pricePnl; a[2] += net; a[3] += 1; a[4] += turnover;
            a[5] += (nLong + nShort);
        }

        LOG.info("=== PnL THAT (funding + price) THEO QUY, dollar-neutral ===");
        LOG.info(String.format("%-8s %7s %11s %11s %11s %8s", "quy", "so_ky", "funding%", "price%", "NET%", "turn"));
        for (Map.Entry<String, double[]> e : quarter.entrySet()) {
            double[] a = e.getValue(); int nP = (int) a[3];
            LOG.info(String.format("%-8s %7d %11.3f %11.3f %11.3f %8.2f",
                    e.getKey(), nP, a[0] * 100, a[1] * 100, a[2] * 100, nP > 0 ? a[4] / nP : 0));
        }
        LOG.info("DONE. NET% = funding + price - fee. price% la KEY: neu am manh -> carry bi price nuot.");
    }

    private static Float fwd(TreeMap<Long, Float> m, long slot) {
        if (m == null) return null;
        Map.Entry<Long, Float> e = m.floorEntry(slot + 900000L); // nearest <= slot+15m
        if (e == null) return null;
        if (Math.abs(e.getKey() - slot) > 6 * 3600000L) return null; // qua xa -> bo
        return e.getValue();
    }

    private static String qKey(long ms) {
        long t = ms + 7 * 3600000L;
        java.time.LocalDate d = java.time.Instant.ofEpochMilli(t).atZone(java.time.ZoneOffset.UTC).toLocalDate();
        int q = (d.getMonthValue() - 1) / 3 + 1;
        return d.getYear() + "Q" + q;
    }
}
