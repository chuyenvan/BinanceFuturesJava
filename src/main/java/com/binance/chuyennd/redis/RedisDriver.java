/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package com.binance.chuyennd.redis;

import java.io.IOException;
import java.util.HashSet;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import redis.clients.jedis.HostAndPort;
import redis.clients.jedis.JedisCluster;

/**
 *
 * @author Chuyennd2
 */
public class RedisDriver {

    public static final Logger LOG = LoggerFactory.getLogger(RedisDriver.class);
    private static volatile RedisDriver INSTANCE = null;
    private JedisCluster jedisCluster;
    private String redisAddress;
    private int redisTimeout;

    private RedisDriver(JedisCluster jedisCluster) {
        this.jedisCluster = jedisCluster;
    }

    public RedisDriver() {
    }

    public synchronized RedisDriver setup() {
        if (INSTANCE == null) {
            LOG.info("Start connect Redis: " + redisAddress);
            Set<HostAndPort> hostAndPortNodes = new HashSet();
            String[] hostAndPorts = redisAddress.split(",");
            for (String hostAndPort : hostAndPorts) {
                String[] parts = hostAndPort.split(":");
                String host = parts[0];
                int port = Integer.parseInt(parts[1].trim());
                hostAndPortNodes.add(new HostAndPort(host, port));
            }
            INSTANCE = new RedisDriver(new JedisCluster(hostAndPortNodes, redisTimeout));
        }
        return INSTANCE;
    }

    public static synchronized RedisDriver getInstance() {
        if (INSTANCE == null) {
            INSTANCE = new RedisDriver().setup();
        }
        return INSTANCE;
    }

    public JedisCluster get() {
        return INSTANCE.jedisCluster;
    }

    public void setRedisAddress(String dress) {
        redisAddress = dress;
    }

    public void setRedisTimeout(int timeout) {
        redisTimeout = timeout;
    }

    public String getRedisAddress() {
        return redisAddress;
    }

    public int getRedisTimeout() {
        return redisTimeout;
    }

    public static void main(String[] args) throws InterruptedException, IOException {
        RedisDriver redis = new RedisDriver();
        redis.setRedisAddress("103.216.120.125:30001,103.216.120.125:30002,103.216.120.125:30003,103.216.120.126:30001,103.216.120.126:30002,103.216.120.126:30003");
        redis.setRedisTimeout(3000);
        redis.setup();
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_GAME, "bai1dang1",
//                FileUtils.readFileToString(new File("E:\\educa_deploy\\baitap\\Educa-baitap\\baitap1-dang1\\js\\bai1.json")));
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_GAME, "bai1dang5",
//                FileUtils.readFileToString(new File("E:\\educa_deploy\\baitap\\Educa-baitap\\baitap1-dang5\\js\\bai3.json")));
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_GAME, "bai2dang1",
//                FileUtils.readFileToString(new File("E:\\educa_deploy\\baitap\\Educa-baitap\\baitap2-dang1\\js\\bai2.json")));
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_GAME, "bai6dang1",
//                FileUtils.readFileToString(new File("E:\\educa_deploy\\baitap\\Educa-baitap\\baitap6-dang1\\js\\bai6.json")));
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_GAME, "game1",
//                FileUtils.readFileToString(new File("E:\\educa_deploy\\baitap\\game(22-3)\\game1\\js\\game1.json")));
//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_EXERCISE, "gamedemo",
//                FileUtils.readFileToString(new File("E:\\educa_deploy\\nodejs\\service\\bai28.json")));

//        RedisHelper.getInstance().writeJsonData(RedisConst.REDIS_KEY_EDUCA_EXERCISE, "18",
//                FileUtils.readFileToString(new File("C:\\Users\\chuyennd\\AppData\\Local\\Packages\\Microsoft.SkypeApp_kzf8qxf38zg5c\\LocalState\\Downloads\\bai1.json")));
        System.out.println(redis.get().hget("redis.key.educa.userinfo", "1"));
    }
}
