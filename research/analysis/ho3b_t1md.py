#!/usr/bin/env python3
"""HO3b §4b-bis (mo ta, KHONG vao cong 4): Tool1 cot #6 (index 5) = rateDown15MAvg cua market data -> thay bang md inline
Kernel A (khong co md tai ts -> 0, ngu nghia Java) tren H1, ONNX 7921ceaf predict, so p0 vs net015_2026A (thuoc cong 3)
va bins (x1_build_map voi S1 HO26 pred_ho26s1) o trung. Khong luong tu hoa int16 (xap xi). Chi dem/ty le.
Usage: ho3b_t1md.py <kernelA_market.bin> <out_dir>"""
import json, logging, os, struct, subprocess, sys
import numpy as np
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/pipeline"); sys.path.insert(0, R + "/research/analysis")
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import g015_net_train as G  # noqa: E402
import ho1_net015_predict as HN  # noqa: E402
import ho2_net015_onnx as H2  # noqa: E402
import ho3b_gate3 as G3  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho3b_t1md")


def main():
    ka, out = sys.argv[1], sys.argv[2]
    os.makedirs(out + "/net015", exist_ok=True)
    raw = open(ka, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:], dtype=np.dtype([("ts", ">i8"), ("v", ">f4", 3)]), count=n)
    mt, m15 = a["ts"].astype(np.int64), a["v"][:, 2].astype(np.float32)
    G3.MODE = "pinned"
    HN.read_oi = G3.read_oi_comb
    X, ts, sym, info = HN.build_rows([os.path.join(G.T1_DIR, "features_20251001*"), os.path.join(G.T1_DIR, "features_2026*")],
                                     G.ms("20260101"), G.ms("20260701"))
    j = np.searchsorted(mt, ts)
    jj = np.clip(j, 0, len(mt) - 1)
    hit = mt[jj] == ts
    X[:, 5] = np.where(hit, m15[jj], np.float32(0))
    res = dict(rows=int(len(ts)), md_hit=int(hit.sum()), md_miss=int((~hit).sum()))
    for c0, c1 in (("20260101", "20260401"), ("20260401", "20260701")):
        lo, hi = G.ms(c0), G.ms(c1)
        m = (ts >= lo) & (ts < hi)
        p = H2.predict(X[m])
        G.write_bin(os.path.join(out, "net015", "predict_wf_%s.bin" % c0), ts[m], sym[m], p)
    del X
    lk = "/home/ubuntu/ledger/pred_ho3bt1md.parquet"
    if os.path.lexists(lk):
        os.remove(lk)
    os.symlink("/home/ubuntu/claude_master/1003/ho1/s1/pred_ho26s1v2.parquet", lk)
    env = dict(os.environ, X1_CUTS="20260101 20260401", X1_G015_DIR=out + "/net015")
    r = subprocess.run([sys.executable, "-u", "x1_build_map.py", "ho3bt1md", out + "/bins"], cwd=R + "/research/pipeline/x1",
                       env=env, capture_output=True, text=True)
    os.remove(lk)
    assert r.returncode == 0 and "MAP_OK" in r.stdout
    res["compare"] = G3.compare(out)
    for d in ("net015", "bins"):
        for f in os.listdir(os.path.join(out, d)):
            if f.endswith(".bin"):
                os.remove(os.path.join(out, d, f))
    json.dump(res, open(out + "/t1md.json", "w"), indent=1, default=str)
    log.info("T1MD %s", json.dumps(res, default=str))


if __name__ == "__main__":
    main()
