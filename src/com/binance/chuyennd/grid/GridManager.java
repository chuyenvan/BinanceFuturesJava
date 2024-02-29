/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.binance.chuyennd.grid;

import com.binance.chuyennd.redis.RedisConst;
import com.binance.chuyennd.redis.RedisHelper;
import com.binance.chuyennd.utils.Utils;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 *
 * @author pc
 */
public class GridManager {
    public static final Logger LOG = LoggerFactory.getLogger(GridManager.class);
    public static void main(String[] args) {
        new GridManager().startThreadListenAndProcessGridOrder();
    }

    private void startThreadListenAndProcessGridOrder() {
        new Thread(() -> {
            Thread.currentThread().setName("ThreadListenAndProcessGridOrder");
            LOG.info("Start ListenAndProcessGridOrder !");
             while (true) {
                List<String> data;
                try {
                    data = RedisHelper.getInstance().get().blpop(0, RedisConst.REDIS_KEY_EDUCA_TD_GRID_MANAGER_QUEUE);
                    LOG.info("Queue listen grid to manager received : {} ", data.toString());
                    String json = data.get(1);
                    try {
                       GridPosition gridPos = Utils.gson.fromJson(json, GridPosition.class);
                       gridPos.startGridManager();
                    } catch (Exception e) {
                        e.printStackTrace();
                    }
                } catch (Exception e) {
                    LOG.error("ERROR during ThreadListenQueuePosition2Manager {}", e);
                    e.printStackTrace();
                }
            }
        }).start();
    }
}
