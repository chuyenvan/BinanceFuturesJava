package com.binance.chuyennd.aerospike;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Info;

import java.util.HashMap;
import java.util.Map;

public class AerospikeCheckData {
    public static void main(String[] args) {
        Map<String, AerospikeClient> clients = new HashMap<>();
        clients.put("oracle", new AerospikeClient("161.118.212.3", 3222));
//        clients.put("242", new AerospikeClient("103.157.218.242", 3222));


        for (Map.Entry<String, AerospikeClient> entry : clients.entrySet()) {


            AerospikeClient client = entry.getValue();
            String host = entry.getKey();
            try {

                String namespace = "test";
                // truncate toàn bộ set
//                client.truncate(null, namespace, "kline_1m_opt", null);
//                client.truncate(null, namespace, "funding_pred_1m_v5", null);


                // Lấy thống kê namespace
                String nsResponse = Info.request(client.getNodes()[0], "namespace/" + namespace);
                System.out.println("=== Namespace Stats ===");
                printStatInMB(nsResponse, "memory-size");
                printStatInMB(nsResponse, "index_used_bytes");
                printStatInMB(nsResponse, "data_total_bytes");
                printStatInMB(nsResponse, "data_used_bytes");

                System.out.println("=== Set Stats (MB/GB) ===");
                String setsResponse = Info.request(client.getNodes()[0], "sets/" + namespace);


                String[] sets = setsResponse.split(";");
                for (String setStat : sets) {
                    if (setStat.contains("set=")) {
                        String[] fields = setStat.split(":");
                        String setName = "";
                        long objects = 0;
                        long memBytes = 0;
                        long devBytes = 0;

                        for (String f : fields) {
                            if (f.startsWith("set=")) setName = f.split("=")[1];
                            if (f.startsWith("objects=")) objects = Long.parseLong(f.split("=")[1]);
                            if (f.startsWith("memory_data_bytes=")) memBytes = Long.parseLong(f.split("=")[1]);
                            if (f.startsWith("data_used_bytes=")) devBytes = Long.parseLong(f.split("=")[1]);
                        }
                        if (objects == 0 ) continue;

                        System.out.printf("Set: %s %s%n", host, setName);
                        System.out.printf("  Objects: %d%n", objects);
                        System.out.printf("  Memory Used: %s%n", formatSize(memBytes));
                        System.out.printf("  Device Used: %s%n%n", formatSize(devBytes));
                    }
                }

            } finally {
                client.close();
            }
        }
    }

    // Hàm tiện ích để parse và in dung lượng theo MB/GB
    private static void printStatInMB(String response, String key) {
        for (String stat : response.split(";"))     {
            if (stat.startsWith(key)) {
                String[] kv = stat.split("=");
                if (kv.length == 2) {
                    long bytes = Long.parseLong(kv[1]);
                    System.out.println(key + " = " + formatSize(bytes));
                }
            }
        }
    }

    private static String formatSize(long size) {
        float kb = (float) size / 1024;
        float mb = kb / 1024;
        float gb = mb / 1024;
        if (gb >= 1) {
            return String.format("%.2f GB", gb);
        } else if (mb >= 1) {
            return String.format("%.2f MB", mb);
        } else {
            return String.format("%.2f KB", kb);
        }
    }
}