package com.binance.chuyennd.ai_ml.validation.data;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Bin;
import com.aerospike.client.Key;
import com.aerospike.client.Record;
import com.aerospike.client.policy.RecordExistsAction;
import com.aerospike.client.policy.WritePolicy;
import com.binance.chuyennd.utils.HttpRequest;
import com.binance.chuyennd.utils.Utils;
import com.google.gson.Gson;
import com.google.gson.reflect.TypeToken;
import org.apache.commons.lang.StringUtils;
import org.json.JSONArray;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xerial.snappy.Snappy;

import java.lang.reflect.Type;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;

/**
 * TASK-136 - Crawl funding rate lich su (2021->nay) tu fapi.binance.com, ghi set funding_data Oracle LOCAL.
 * DOC LAP HistoricalFundingCrawler goc (lay symbol tu Redis + ghi writeFundingMap=getClient242 -> ghi 242).
 * Ban nay: symbol tu universe file (781, co coin delist), ghi THANG AerospikeClient local (bin f_data Snappy(gson)).
 * Merge voi record cu (guard chong mat lich su). Args: [symfile] [host] [port] [ns]
 */
public class HistoricalFundingCrawlerLocal {
    private static final Logger LOG = LoggerFactory.getLogger(HistoricalFundingCrawlerLocal.class);
    private static final String SET = "funding_data";
    private static final Gson GSON = new Gson();
    private static final Type MAP_TYPE = new TypeToken<TreeMap<Long, Float>>() {}.getType();

    public static void main(String[] args) throws Exception {
        String symfile = args.length >= 1 ? args[0] : "/tmp/oisyms.txt";
        String host = args.length >= 2 ? args[1] : "127.0.0.1";
        int port = args.length >= 3 ? Integer.parseInt(args[2]) : 3222;
        String ns = args.length >= 4 ? args[3] : "test";
        LOG.info("CRAWL FUNDING -> {}:{} ns={} set={} | symfile={}", host, port, ns, SET, symfile);
        if (!"127.0.0.1".equals(host) && !"localhost".equals(host)) LOG.warn("host KHONG localhost ({})!", host);

        List<String> symbols = new ArrayList<>();
        for (String line : Files.readAllLines(Paths.get(symfile))) {
            String s = line.trim().toUpperCase();
            if (s.matches("^[A-Z0-9]+USDT$")) symbols.add(s);
        }
        LOG.info("🎯 {} symbol tu universe file.", symbols.size());

        long globalStart = Utils.sdfFile.parse("20210101").getTime();
        long globalEnd = System.currentTimeMillis();

        WritePolicy wp = new WritePolicy();
        wp.expiration = 0; wp.sendKey = true; wp.recordExistsAction = RecordExistsAction.UPDATE;

        int count = 0, withData = 0;
        try (AerospikeClient client = new AerospikeClient(host, port)) {
            for (String symbol : symbols) {
                count++;
                TreeMap<Long, Float> rates = new TreeMap<>();
                long currentStart = globalStart;
                while (currentStart < globalEnd) {
                    try {
                        String url = "https://fapi.binance.com/fapi/v1/fundingRate?symbol=" + symbol
                                + "&startTime=" + currentStart + "&limit=1000";
                        String resp = HttpRequest.getContentFromUrl(url, 5000);
                        if (StringUtils.isNotBlank(resp) && resp.startsWith("[")) {
                            JSONArray arr = new JSONArray(resp);
                            if (arr.length() == 0) break;
                            for (int i = 0; i < arr.length(); i++) {
                                JSONObject o = arr.getJSONObject(i);
                                long ft = o.getLong("fundingTime");
                                rates.put(ft, (float) o.getDouble("fundingRate"));
                                currentStart = ft + 1;
                            }
                            if (arr.length() < 1000) break; // trang cuoi
                        } else break;
                        Thread.sleep(150);
                    } catch (Exception e) {
                        LOG.warn("  loi {} @ {}: {}", symbol, currentStart, e.getMessage());
                        Thread.sleep(1500);
                    }
                }
                if (rates.isEmpty()) { if (count % 50 == 0) LOG.info("  [{}/{}] {} khong co funding", count, symbols.size(), symbol); continue; }
                // merge record cu (guard)
                Key key = new Key(ns, SET, symbol);
                TreeMap<Long, Float> finalMap = new TreeMap<>();
                try {
                    Record old = client.get(null, key);
                    if (old != null && old.getValue("f_data") != null) {
                        byte[] b = (byte[]) old.getValue("f_data");
                        if (b.length > 0) {
                            TreeMap<Long, Float> ex = GSON.fromJson(new String(Snappy.uncompress(b), "UTF-8"), MAP_TYPE);
                            if (ex != null) finalMap.putAll(ex);
                        }
                    }
                } catch (Exception ignore) {}
                finalMap.putAll(rates);
                byte[] comp = Snappy.compress(GSON.toJson(finalMap).getBytes("UTF-8"));
                client.put(wp, key, new Bin("f_data", comp));
                withData++;
                if (count % 25 == 0 || count <= 5)
                    LOG.info("  [{}/{}] {}: {} record funding", count, symbols.size(), symbol, finalMap.size());
            }
            // verify coin delist
            for (String c : new String[]{"LUNAUSDT","FTTUSDT","BTCUSDT"}) {
                Record r = client.get(null, new Key(ns, SET, c));
                int n = 0;
                if (r != null && r.getValue("f_data") != null) {
                    TreeMap<Long, Float> m = GSON.fromJson(new String(Snappy.uncompress((byte[]) r.getValue("f_data")), "UTF-8"), MAP_TYPE);
                    n = m == null ? 0 : m.size();
                }
                LOG.info("VERIFY {}: {} record funding", c, n);
            }
        }
        LOG.info("🎉 HET CRAWL FUNDING: {}/{} symbol co data.", withData, symbols.size());
        System.exit(0);
    }
}
