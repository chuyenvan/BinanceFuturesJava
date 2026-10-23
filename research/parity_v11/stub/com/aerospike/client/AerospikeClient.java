package com.aerospike.client;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * STUB FAIL-CLOSED cho harness offline (docs/prereg/PREREG_PARITY_V11_WINDOW.md §1, §6 R0).
 * Dat TRUOC jar tren classpath => moi `new AerospikeClient(...)` (242, Oracle, 226, bat ky host) dung JVM ngay bang
 * Runtime.halt(97) — khong exception (tranh bi catch(Exception) nuot), khong mo socket.
 * Chi dung cho research/parity_v11; KHONG BAO GIO dong goi vao jar app.
 */
public class AerospikeClient {
    private static final Logger LOG = LoggerFactory.getLogger(AerospikeClient.class);
    public static final int EXIT_CODE = 97;

    public AerospikeClient(String hostname, int port) {
        trip("AerospikeClient(" + hostname + "," + port + ")");
    }

    public AerospikeClient(com.aerospike.client.policy.ClientPolicy policy, String hostname, int port) {
        trip("AerospikeClient(policy," + hostname + "," + port + ")");
    }

    public AerospikeClient(com.aerospike.client.policy.ClientPolicy policy, Host... hosts) {
        StringBuilder sb = new StringBuilder();
        if (hosts != null) for (Host h : hosts) sb.append(h).append(' ');
        trip("AerospikeClient(policy,hosts=" + sb.toString().trim() + ")");
    }

    static void trip(String what) {
        LOG.error("[HARNESS-OFFLINE-VIOLATION] tao Aerospike client bi CHAN: {} => halt({})", what, EXIT_CODE,
                new IllegalStateException("stack"));
        System.err.println("[HARNESS-OFFLINE-VIOLATION] " + what);
        System.err.flush();
        Runtime.getRuntime().halt(EXIT_CODE);
    }
}
