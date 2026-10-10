#!/usr/bin/env python3
"""HO3b B3: net015 Q3 = ONNX goc 7921ceaf (phuong an A, ADDENDUM-3 §4) predict-only fold [20260701, 20261001) +07.
build_rows HO1 (Tool1 + OI merge_asof 2h + symbol_map); Tool1 = file HO26 Q2 (phu 07-01 00:00..06:59) + file Q3 exporter Java;
OI = file ghim ts < 2026-07-01 00:00 +07 + dung lai Vision ts >= (ADDENDUM-4 §4a). Chi dem/NaN/khoang ts/sha.
Usage: ho3b_net015_q3.py <tool1_q3_file> <out_dir>"""
import glob, hashlib, json, logging, os, sys
import numpy as np
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/pipeline"); sys.path.insert(0, R + "/research/analysis")
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import g015_net_train as G  # noqa: E402
import ho1_net015_predict as HN  # noqa: E402
import ho2_net015_onnx as H2  # noqa: E402
import ho3b_gate3 as G3  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho3b_nq3")
SEALQ3 = 1782838800000            # 2026-07-01 00:00 +07


def main():
    t1q3, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    G3.SEAL7 = SEALQ3
    G3.MODE = "rebuilt"
    HN.read_oi = G3.read_oi_comb
    lo, hi = G.ms("20260701"), G.ms("20261001")
    assert lo == SEALQ3, (lo, SEALQ3)
    X, ts, sym, info = HN.build_rows([os.path.join(G.T1_DIR, "features_20260401_to_20260701*"), t1q3], lo, hi)
    m = (ts >= lo) & (ts < hi)
    p = H2.predict(X[m])
    path = os.path.join(out, "predict_wf_20260701.bin")
    G.write_bin(path, ts[m], sym[m], p)
    tq = ts[m]
    res = dict(chunk=info, n=int(m.sum()), nan=int(np.isnan(p).sum()), ts_min=int(tq.min()), ts_max=int(tq.max()),
               span_days=int((tq.max() - tq.min()) // 86400000), lo=lo, hi=hi, sha256=G3.sha256f(path),
               onnx_sha256=H2.ONNX_SHA, n_ticks=int(len(np.unique(tq))))
    assert res["nan"] == 0 and res["span_days"] <= 100 and lo <= res["ts_min"] and res["ts_max"] < hi
    json.dump(res, open(os.path.join(out, "net015_q3.json"), "w"), indent=1, default=str)
    log.info("NET015 Q3 %s", res)


if __name__ == "__main__":
    main()
