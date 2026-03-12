package com.binance.chuyennd.aerospike;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.Host;
import com.aerospike.client.Info;

import com.aerospike.client.AerospikeClient;
import com.aerospike.client.cluster.Node;

public class AerospikeInfo {
    public static void main(String[] args) {
        AerospikeClient client = new AerospikeClient("172.25.80.187", 3000);

        try {
            Node node = client.getNodes()[0];

            String nsInfo = Info.request(node, "namespace/educa");
            String[] parts = nsInfo.split(";");

            long deviceDataBytes = 0;
            int deviceAvailablePct = -1;

            for (String part : parts) {
                if (part.startsWith("device_data_bytes=")) {
                    deviceDataBytes = Long.parseLong(part.split("=")[1]);
                }
                if (part.startsWith("device_available_pct=")) {
                    deviceAvailablePct = Integer.parseInt(part.split("=")[1]);
                }
            }

            if (deviceAvailablePct >= 0) {
                float usedPct = 100 - deviceAvailablePct;
                float totalBytes = deviceDataBytes / (usedPct / 100.0f);
                System.out.printf("Namespace educa đang dùng %.2f%% dung lượng\n", usedPct);
                System.out.printf("Tổng dung lượng cấu hình: %.2f GB\n", totalBytes / (1024.0*1024*1024));
            }

        } finally {
            client.close();
        }
    }

}