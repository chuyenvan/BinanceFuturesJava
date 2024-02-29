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

import com.binance.chuyennd.utils.Configs;
import com.binance.chuyennd.utils.Utils;
import com.mongodb.MongoClient;
import com.mongodb.MongoClientURI;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoCursor;
import com.mongodb.client.MongoDatabase;
import static com.mongodb.client.model.Filters.eq;
import static com.mongodb.client.model.Filters.ne;
import static com.mongodb.client.model.Filters.and;
import com.mongodb.client.model.UpdateOptions;
import java.util.List;
import org.bson.Document;
import org.bson.conversions.Bson;
import org.bson.types.ObjectId;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class TickerMongoHelper {

    public static final Logger LOG = LoggerFactory.getLogger(TickerMongoHelper.class);

    public MongoClientURI uri;
    MongoClient client;
    MongoDatabase db;
    MongoCollection<Document> ticker_log;

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
        ticker_log = db.getCollection("ticker_log");

    }

    public boolean insertTicker(Document doc) {
        try {
            if (doc != null) {
                ticker_log.insertOne(doc);
                return true;
            }
        } catch (Exception e) {
            LOG.error("Error on insert ticker ", e);
        }
        return false;
    }

    public MongoCursor<Document> getAllTickerByHour(long hour) {
        Bson filter = eq("hour", hour);
        return ticker_log.find(filter).iterator();
    }

    public MongoCursor<Document> getTicker(long hour, String sym) {
        Bson filter = and(eq("hour", hour), eq("sym", sym));
        return ticker_log.find(filter).iterator();
    }

    public MongoCursor<Document> getAllTickerBySymbol(String sym) {
        Bson filter = eq("sym", sym);
        return ticker_log.find(filter).iterator();
    }

    public Long getLastHourTickerBySymbol(String symbol) {
        Bson filter = eq("sym", symbol);
        Bson filterSort = eq("hour", -1);
        MongoCursor<Document> cursor = ticker_log.find(filter).sort(filterSort).iterator();
        while (cursor.hasNext()) {
            Document record = cursor.next();
            return record.getLong("hour");
        }
        return 0l;
    }
    public Long getFirstHourTickerBySymbol(String symbol) {
        Bson filter = eq("sym", symbol);
        Bson filterSort = eq("hour", 1);
        MongoCursor<Document> cursor = ticker_log.find(filter).sort(filterSort).iterator();
        while (cursor.hasNext()) {
            Document record = cursor.next();
            return record.getLong("hour");
        }
        return 0l;
    }

    public void deleteTicker(String symbol, Long lastHourUpdate) {
        Bson query = and(eq("sym", symbol), eq("hour", lastHourUpdate));
        ticker_log.deleteMany(query);
    }

}
