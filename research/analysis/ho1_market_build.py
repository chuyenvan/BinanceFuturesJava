#!/usr/bin/env python3
"""HO1 B5a — market.bin holdout = market.bin DEV (NGUYEN byte) + doan 2026 tu Aerospike ORACLE set market_data_object.

Cong G-B5m (pre-reg 35d03784 §2.4): tai sinh market.bin DEV tu CHINH nguon (scan market_data_object, last-wins theo
thu tu scan nhu DataManagerAerospikeFloatSim.getAllMarketDataFromAerospike, cat >= HoldoutSeal.SEAL_MS, format
WfoDataset.writeMarket) so md5 4ab691c9. PHAT HIEN 2026-10-08: set co ts TRUNG (nhieu key cung bin time, gia tri
khac) -> exporter Java KHONG tat dinh tren cac phut do. Ket qua cong: PASS (byte) | EXPLAINED (moi ban ghi lech deu la
ts trung co gia tri khac VA gia tri DEV nam trong cac ung vien) | FAIL (lech khong giai thich duoc -> DUNG).
Chi DOC Aerospike Oracle (127.0.0.1:3222, ns test). KHONG cham 242. Market = du lieu tho (khong model).
Usage: python3 ho1_market_build.py
"""
import hashlib
import json
import logging
import os
import struct
import sys
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho1mkt")

HOST, PORT, NS, SET = "127.0.0.1", 3222, "test", "market_data_object"
DEV = "/home/ubuntu/wfo_ds_x1_2021/market.bin"
DEV_MD5 = "4ab691c908fc545c26243e8328d7a0a6"
SEAL_UTC = 1767225600000            # HoldoutSeal.SEAL_MS
END = 1782864000000                 # 2026-07-01 00:00 UTC (= 07:00 +07): het ngay UTC 2026-06-30 (vong lap ngay cua sim)
OUT = "/home/ubuntu/claude_master/1003/ho1/ds"


def md5b(b):
    return hashlib.md5(b).hexdigest()


def scan():
    """-> (last: ts->12B theo thu tu scan last-wins, cand: ts->list cac gia tri)."""
    import aerospike
    c = aerospike.client({"hosts": [(HOST, PORT)]}).connect()
    last, cand = {}, defaultdict(list)
    bad = [0]

    def cb(rec):
        bins = rec[2]
        t, d = bins.get("time"), bins.get("data")
        if t is None or d is None or len(d) < 12:
            bad[0] += 1
            return
        v = bytes(d[:12])
        last[int(t)] = v
        cand[int(t)].append(v)

    q = c.query(NS, SET)
    q.select("time", "data")
    q.foreach(cb, {"total_timeout": 0})
    c.close()
    log.info("scan %s.%s: %d ts, %d record, bo %d", NS, SET, len(last), sum(len(v) for v in cand.values()), bad[0])
    return last, cand


def pack(items):
    return b"".join(struct.pack(">q", k) + v for k, v in items)


def main():
    os.makedirs(OUT, exist_ok=True)
    raw = open(DEV, "rb").read()
    assert md5b(raw) == DEV_MD5
    n_dev = struct.unpack(">i", raw[:4])[0]
    assert 4 + 20 * n_dev == len(raw)
    dd = {struct.unpack(">q", raw[4 + 20 * i:12 + 20 * i])[0]: raw[12 + 20 * i:24 + 20 * i] for i in range(n_dev)}
    last, cand = scan()
    dev = sorted((k, v) for k, v in last.items() if k < SEAL_UTC)
    regen = struct.pack(">i", len(dev)) + pack(dev)
    diff = [k for k, v in dev if dd.get(k) != v]
    unexpl = [k for k in diff if not (len(set(cand[k])) > 1 and dd.get(k) in cand[k])]
    ndup_diff = sum(1 for k, vs in cand.items() if k < SEAL_UTC and len(set(vs)) > 1)
    g = dict(n_regen=len(dev), n_dev=n_dev, ts_set_equal=set(dd) == set(k for k, _ in dev), md5_regen=md5b(regen),
             md5_dev=DEV_MD5, n_val_diff=len(diff), n_unexplained=len(unexpl), n_dev_dup_ts_diffvals=ndup_diff)
    g["verdict"] = "PASS" if g["md5_regen"] == DEV_MD5 else (
        "EXPLAINED" if g["ts_set_equal"] and not unexpl else "FAIL")
    log.info("G-B5m tai sinh market.bin DEV: %s", g)
    meta = dict(prereg="35d03784", G_B5m=g, diff_ts=diff[:50], unexplained_ts=unexpl[:50])
    if g["verdict"] == "FAIL":
        log.error("G-B5m FAIL -> DUNG, khong ghi doan 2026")
        json.dump(meta, open(OUT + "/market_meta.json", "w"), indent=1)
        sys.exit(2)
    h = sorted((k, v) for k, v in last.items() if SEAL_UTC <= k < END)
    amb = [k for k, _ in h if len(set(cand[k])) > 1]
    ts = [k for k, _ in h]
    assert all(t % 60000 == 0 for t in ts) and all(b > a for a, b in zip(ts, ts[1:]))
    new = struct.pack(">i", n_dev + len(h)) + raw[4:] + pack(h)
    p = OUT + "/market.bin"
    open(p, "wb").write(new)
    chk = open(p, "rb").read()
    assert md5b(chk[4:4 + 20 * n_dev]) == md5b(raw[4:])
    day = defaultdict(int)
    for t in ts:
        day[(t + 7 * 3600000) // 86400000] += 1
    meta.update(n_2026=len(h), first=ts[0], last=ts[-1], n_minutes_range=(END - SEAL_UTC) // 60000,
                n_days=len(day), days_lt_1440=sum(1 for v in day.values() if v < 1440),
                ambiguous_2026_ts=amb, md5_dev_records=md5b(raw[4:]), md5=md5b(chk), bytes=len(chk), path=p)
    json.dump(meta, open(OUT + "/market_meta.json", "w"), indent=1)
    log.info("MARKET holdout: %s", {k: v for k, v in meta.items() if k not in ("G_B5m", "diff_ts")})


if __name__ == "__main__":
    main()
