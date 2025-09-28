/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.redis;

import org.apache.commons.lang.StringUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.JedisCluster;

import java.util.*;

/**
 * @author chuyennd
 */
public class RedisHelper {

    public static final Logger LOG = LoggerFactory.getLogger(RedisHelper.class);

    private static volatile RedisHelper INSTANCE = null;

    public static RedisHelper getInstance() {
        if (INSTANCE == null) {
            RedisDriver redis = new RedisDriver();
            redis.setRedisAddress(RedisConst.REDIS_ADDRESS);
            redis.setRedisTimeout(Integer.parseInt(RedisConst.REDIS_TIMEOUT));
            redis.setup();
            INSTANCE = new RedisHelper();
        }
        return INSTANCE;
    }

    public JedisCluster get() {
        return RedisDriver.getInstance().get();
    }

    public void setTimeToLive(String key, int second) {
        get().expire(key, second);
    }

    public void writeJsonData(String key, String id, String json) {
        try {
            if (StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(id) && StringUtils.isNotEmpty(json)) {
                JedisCluster jedis = RedisDriver.getInstance().get();
                jedis.hset(key, id, json);
            }
        } catch (Exception e) {
            LOG.error("Error during write Json: {}:{}", key, id);
            e.printStackTrace();
        }
    }

    public void addList(String key, String member) {
        try {
            if (StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(member)) {
                JedisCluster jedis = RedisDriver.getInstance().get();
                jedis.sadd(key, member);
            }
        } catch (Exception e) {
            LOG.error("Error during add list: {}:{}", key, key);
            e.printStackTrace();
        }
    }

    public void removeList(String key, String member) {
        try {
            if (StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(member)) {
                JedisCluster jedis = RedisDriver.getInstance().get();
                jedis.srem(key, member);
            }
        } catch (Exception e) {
            LOG.error("Error during remove list: {}:{}", key, key);
            e.printStackTrace();
        }
    }

    public void set(String key, String value, int expireTime) {
        try {
            JedisCluster jedis = RedisDriver.getInstance().get();
            jedis.set(key, value);
            jedis.expire(key, expireTime);
        } catch (Exception e) {
            LOG.error("(set) ERROR, key: {}, data: {}, expireTime: {}", key, value, expireTime, e);
        }
    }

    public void delJsonData(String key, String id) {
        try {
            JedisCluster jedis = RedisDriver.getInstance().get();
            jedis.hdel(key, id);

        } catch (Exception e) {
            LOG.error("Error during write Json: {}:{}", key, id);
            e.printStackTrace();
        }
    }

    public Set<String> smembers(String key) {
        if (key == null) {
            return new HashSet<>();
        }

        JedisCluster jedis = RedisDriver.getInstance().get();
        return jedis.smembers(key);
    }

    public String readJsonData(String key, String id) {
        String result = null;
        try {
            if (StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(id)) {
//                LOG.info("Get json id:{} key:{}", id, key);
                JedisCluster jedis = RedisDriver.getInstance().get();
                result = jedis.hget(key, id);
            }
        } catch (Exception e) {
            LOG.error("Error during get Json: {}, {}", key, id);
            e.printStackTrace();
        }
        return result;
    }

    public Set<String> readAllId(String key) {
        Set<String> result = new HashSet();
        try {
            if (StringUtils.isNotEmpty(key)) {
//                LOG.info("Get json all id from key:{}", key);
                JedisCluster jedis = RedisDriver.getInstance().get();
                result.addAll(jedis.hgetAll(key).keySet());
                return result;
            }
        } catch (Exception e) {
            LOG.error("Error during get all id from key:{}", key);
            e.printStackTrace();
        }
        return result;
    }

    public void lpushJsonData(String key, String json) {
        try {
            if (StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(json)) {
                JedisCluster jedis = RedisDriver.getInstance().get();
                jedis.lpush(key, json);
            }
        } catch (Exception e) {
            LOG.error("Error during lpush json: {}", key);
            e.printStackTrace();
        }
    }

    public void rpushDataQueue(String key, String json) {
        try {
            if (StringUtils.isNotEmpty(key) && StringUtils.isNotEmpty(json)) {
                JedisCluster jedis = RedisDriver.getInstance().get();
                Long result = jedis.rpush(key, json);
                if (result == null) {
                    throw new Exception();
                }
            }
        } catch (Exception e) {
            LOG.error("Error during write Json: {}:{}", key, json);
            e.printStackTrace();
        }
    }

    public List<String> blpopDataQueue(String key) {
        List<String> queueData = new LinkedList<>();
        try {
            if (StringUtils.isNotEmpty(key)) {
                JedisCluster jedis = RedisDriver.getInstance().get();
//                queueData = jedis.lrange(key, 0, -1);
                queueData = jedis.blpop(0, key);
            }
        } catch (Exception e) {
            LOG.error("Error during write Json: {}", key);
            e.printStackTrace();
        }
        return queueData;
    }

    public Map<String, String> hgetAll(String key) {
        JedisCluster jedis = RedisDriver.getInstance().get();
        return jedis.hgetAll(key);
    }

    public List<String> lrange(String key, Long start, Long stop) {
        JedisCluster jedis = RedisDriver.getInstance().get();
        return jedis.lrange(key, start, stop);
    }

    public void hdel(String key, String username) {
        JedisCluster jedis = RedisDriver.getInstance().get();
        jedis.hdel(key, username);
    }

    public static void main(String[] args) {
//        RedisHelper.getInstance().writeJsonData("chuyennd", "123", "1");
//        System.out.println(RedisHelper.getInstance().readJsonData("chuyennd", "123"));

//        for (int i = 0; i < 10; i++) {
//            String member = String.valueOf(i);
//            RedisHelper.getInstance().addList(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING, member);
//            RedisHelper.getInstance().addList(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING, member);
//        }
//
//        System.out.println(RedisHelper.getInstance().smembers(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING));
//        for (int i = 0; i < 10; i++) {
//            String member = String.valueOf(i);
//            RedisHelper.getInstance().removeList(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING, member);
//            System.out.println(RedisHelper.getInstance().smembers(RedisConst.REDIS_KEY_SET_ALL_SYMBOL_POS_RUNNING));
//        }
    }
}
