/*
 * Copyright 2024 pc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package com.binance.chuyennd.mongo;

import com.binance.chuyennd.object.KlineObjectNumber;
import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.binance.client.constant.Constants;
import com.mongodb.MongoClient;
import com.mongodb.MongoClientURI;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoCursor;
import com.mongodb.client.MongoDatabase;

import java.util.*;

import org.bson.Document;
import org.bson.conversions.Bson;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import static com.mongodb.client.model.Filters.*;

/**
 * @author pc
 */
public class TickerMongoHelper {

    public static final Logger LOG = LoggerFactory.getLogger(TickerMongoHelper.class);

    public MongoClientURI uri;
    MongoClient client;
    MongoDatabase db;
    MongoCollection<Document> ticker_log_15m;
    MongoCollection<Document> ticker_log_1h;
    MongoCollection<Document> ticker_log_4h;
    MongoCollection<Document> ticker_log_1d;
    MongoCollection<Document> ticker_statistic;
    MongoCollection<Document> ticker_statistic_bak;


    private static volatile TickerMongoHelper INSTANCE = null;

    public static TickerMongoHelper getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new TickerMongoHelper(false);
        }
        return INSTANCE;
    }

    public TickerMongoHelper(boolean lock) {
        try {
            initDB();
        } catch (Exception e) {
            e.printStackTrace();
            System.exit(0);
        }
    }

    private void initDB() {
        String mongoInfo = Configs.getString("mongo_edu");
        uri = new MongoClientURI(mongoInfo);
        client = new MongoClient(uri);

        db = client.getDatabase("zalo_data");
        ticker_log_15m = db.getCollection("ticker_log_15m");
        ticker_log_1h = db.getCollection("ticker_log_1h");
        ticker_log_4h = db.getCollection("ticker_log_4h");
        ticker_log_1d = db.getCollection("ticker_log_1d");
        ticker_statistic = db.getCollection("ticker_statistic");
        ticker_statistic_bak = db.getCollection("ticker_statistic_bak");

    }


    public boolean insertTicker15m(Document doc) {
        try {
            if (doc != null) {
                ticker_log_15m.insertOne(doc);
                return true;
            }
        } catch (Exception e) {
            LOG.error("Error on insert ticker ", e);
        }
        return false;
    }

    public boolean insertTicker1h(Document doc) {
        try {
            if (doc != null) {
                ticker_log_1h.insertOne(doc);
                return true;
            }
        } catch (Exception e) {
            LOG.error("Error on insert ticker ", e);
        }
        return false;
    }

    public boolean insertTicker4h(Document doc) {
        try {
            if (doc != null) {
                ticker_log_4h.insertOne(doc);
                return true;
            }
        } catch (Exception e) {
            LOG.error("Error on insert ticker ", e);
        }
        return false;
    }

    public boolean insertTicker1d(Document doc) {
        try {
            if (doc != null) {
                ticker_log_1d.insertOne(doc);
                return true;
            }
        } catch (Exception e) {
            LOG.error("Error on insert ticker ", e);
        }
        return false;
    }

    public boolean insertTickerStatistic(Document doc) {
        try {
            if (doc != null) {
                ticker_statistic.insertOne(doc);
                return true;
            }
        } catch (Exception e) {
            LOG.error("Error on insert ticker ", e);
        }
        return false;
    }


    public MongoCursor<Document> getAllTickerByDate(long date) {
        Bson filter = eq("date", date);
        return ticker_log_15m.find(filter).iterator();
    }

    public MongoCursor<Document> getAllTickerStatisticByHourNumber(Integer hour) {
        Bson filter = eq("hour", hour);
        return ticker_statistic.find(filter).iterator();
    }

    public MongoCursor<Document> getAllTickerStatisticByHourNumberBak(Integer hour) {
        Bson filter = eq("hour", hour);
        return ticker_statistic_bak.find(filter).iterator();
    }

    public MongoCursor<Document> getTicker15m(long date, String sym) {
        Bson filter = and(eq("date", date), eq("sym", sym));
        return ticker_log_15m.find(filter).iterator();
    }

    public TreeMap<Long, Map<String, KlineObjectNumber>> getDataFromDb(Long startTime) {
        MongoCursor<Document> docs = TickerMongoHelper.getInstance().getAllTickerByDate(startTime);
        TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers = new TreeMap<>();
        while (docs.hasNext()) {
            Document doc = docs.next();
            String symbol = doc.getString("sym");
            List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().extractDetails(doc);
            for (KlineObjectNumber ticker : tickers) {
                Map<String, KlineObjectNumber> symbol2Ticker = time2Tickers.get(ticker.startTime.longValue());
                if (symbol2Ticker == null) {
                    symbol2Ticker = new HashMap<>();
                    time2Tickers.put(ticker.startTime.longValue(), symbol2Ticker);
                }
                symbol2Ticker.put(symbol, ticker);
            }
        }
        return time2Tickers;
    }

    public TreeMap<Long, Map<String, KlineObjectNumber>> getDataFromDb(Long startTime, String symbol) {
        MongoCursor<Document> docs = TickerMongoHelper.getInstance().getTicker15m(startTime, symbol);
        TreeMap<Long, Map<String, KlineObjectNumber>> time2Tickers = new TreeMap<>();
        while (docs.hasNext()) {
            Document doc = docs.next();
            List<KlineObjectNumber> tickers = TickerMongoHelper.getInstance().extractDetails(doc);
            for (KlineObjectNumber ticker : tickers) {
                Map<String, KlineObjectNumber> symbol2Ticker = time2Tickers.get(ticker.startTime.longValue());
                if (symbol2Ticker == null) {
                    symbol2Ticker = new HashMap<>();
                    time2Tickers.put(ticker.startTime.longValue(), symbol2Ticker);
                }
                symbol2Ticker.put(symbol, ticker);
            }
        }
        return time2Tickers;
    }


    public List<KlineObjectNumber> getTicker15mBySymbol(String symbol) {
        MongoCursor<Document> docs = getAllTicker15mBySymbol(symbol);
        List<KlineObjectNumber> tickers = new ArrayList<>();
        while (docs.hasNext()) {
            Document doc = docs.next();
            try {
                tickers.addAll(extractDetails(doc));
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return tickers;
    }

    public List<KlineObjectNumber> getTicker1HourBySymbol(String symbol) {
        MongoCursor<Document> docs = getAllTicker1HourBySymbol(symbol);
        List<KlineObjectNumber> tickers = new ArrayList<>();
        while (docs.hasNext()) {
            Document doc = docs.next();
            try {
                tickers.addAll(extractDetails(doc));
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return tickers;
    }

    public List<KlineObjectNumber> getTicker4HourBySymbol(String symbol) {
        MongoCursor<Document> docs = getAllTicker4HourBySymbol(symbol);
        List<KlineObjectNumber> tickers = new ArrayList<>();
        while (docs.hasNext()) {
            Document doc = docs.next();
            try {
                tickers.addAll(extractDetails(doc));
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return tickers;
    }

    public List<KlineObjectNumber> getTicker1dBySymbol(String symbol) {
        MongoCursor<Document> docs = getAllTicker1dBySymbol(symbol);
        List<KlineObjectNumber> tickers = new ArrayList<>();
        while (docs.hasNext()) {
            Document doc = docs.next();
            try {
                tickers.addAll(extractDetails(doc));
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
        return tickers;
    }

    public List<KlineObjectNumber> extractDetails(Document doc) {
        List<KlineObjectNumber> tickers = new ArrayList<>();
        try {
            List<Document> details = doc.get("details", List.class);
            for (Document detail : details) {
                tickers.add(Utils.gson.fromJson(detail.toJson(), KlineObjectNumber.class));
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return tickers;
    }


    public MongoCursor<Document> getAllTicker15mBySymbol(String sym) {
        Bson filterSort = eq("date", 1);
        Bson filter = eq("sym", sym);
        return ticker_log_15m.find(filter).sort(filterSort).iterator();
    }

    public MongoCursor<Document> getAllTicker1HourBySymbol(String sym) {
        Bson filterSort = eq("date", 1);
        Bson filter = eq("sym", sym);
        return ticker_log_1h.find(filter).sort(filterSort).iterator();
    }

    public MongoCursor<Document> getAllTicker4HourBySymbol(String sym) {
        Bson filterSort = eq("date", 1);
        Bson filter = eq("sym", sym);
        return ticker_log_4h.find(filter).sort(filterSort).iterator();
    }
    public MongoCursor<Document> getAllTicker1dBySymbol(String sym) {
        Bson filterSort = eq("date", 1);
        Bson filter = eq("sym", sym);
        return ticker_log_1d.find(filter).sort(filterSort).iterator();
    }


    public Long getLastDateTicker15mBySymbol(String symbol) {
        Bson filter = eq("sym", symbol);
        Bson filterSort = eq("date", -1);
        MongoCursor<Document> cursor = ticker_log_15m.find(filter).sort(filterSort).iterator();
        while (cursor.hasNext()) {
            Document record = cursor.next();
            return record.getLong("date");
        }
        return 0l;
    }


    public Long getFirstDateTickerBySymbol(String symbol) {
        Bson filter = eq("sym", symbol);
        Bson filterSort = eq("date", 1);
        MongoCursor<Document> cursor = ticker_log_15m.find(filter).sort(filterSort).iterator();
        while (cursor.hasNext()) {
            Document record = cursor.next();
            return record.getLong("date");
        }
        return 0l;
    }


    public void deleteTicker15m(String symbol, Long date) {
        Bson query = and(eq("sym", symbol), eq("date", date));
        ticker_log_15m.deleteMany(query);
    }

    public void deleteTicker15m(String symbol) {
        Bson query = eq("sym", symbol);
        ticker_log_15m.deleteMany(query);
    }

    public void deleteTicker1h(String symbol) {
        Bson query = eq("sym", symbol);
        ticker_log_1h.deleteMany(query);
    }

    public void deleteTicker4h(String symbol) {
        Bson query = eq("sym", symbol);
        ticker_log_4h.deleteMany(query);
    }


    public Set<String> getAllSymbol15m() {
        Set<String> result = new HashSet<>();
        MongoCursor<String> cursor = ticker_log_15m.distinct("sym", null, String.class).iterator();
        while (cursor.hasNext()) {
            String record = cursor.next();
            result.add(record);
        }
        return result;
    }

    public static void main(String[] args) {

    }

}
