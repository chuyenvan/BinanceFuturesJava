#!/usr/bin/env python3
"""HO2 — PHUONG AN A (pre-reg ADDENDUM-2 §2/§2a, 1682a311 + 2691816d): net015 GOC (ONNX export cua predwf_G015/model_f15_4h,
cut20251001) predict-only. Cong A tren DEV 2025Q4; neu PASS moi predict 2026H1 (chi dem/NaN/ts/sha, KHONG thong ke gia tri 2026).
Usage: python3 ho2_net015_onnx.py <orig_predict_wf_20251001.bin (backup Kaggle predwf-g015x26-gate)>"""
import hashlib
import json
import logging
import os
import subprocess
import sys

import numpy as np

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/pipeline"))
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import g015_net_train as G  # noqa: E402
import ho1_net015_predict as H1  # noqa: E402  (build_rows y het B3 HO1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho2net")
ONNX = "/home/ubuntu/deploy_242_l3/models/g015x26_f15_cut20251001.onnx"
ONNX_SHA = "7921ceaf2405049ddf2c23187264c34d6c95a38125f33c9ef3506f02f4e6dd8b"
ORIG_SHA = "e03f0e58ed35f86929059cc349ceb18121df8b48ba3035293d7e6c9140da283a"
DEV_BIN = "/home/ubuntu/predwf_map_s1a2_x1_2021/predict_wf_20251001.bin"
W = "/home/ubuntu/claude_master/1009/ho26"
OUT26 = W + "/net015_2026A"
DT = H1.DT
BLACK = H1.BLACK


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def predict(X, bs=500_000):
    import onnxruntime as ort
    assert sha256f(ONNX) == ONNX_SHA and ONNX_SHA not in BLACK
    so = ort.SessionOptions()
    so.intra_op_num_threads = 4
    s = ort.InferenceSession(ONNX, so, providers=["CPUExecutionProvider"])
    name = s.get_inputs()[0].name
    out = np.empty(len(X), dtype=np.float32)
    for i in range(0, len(X), bs):
        r = s.run(None, {name: np.ascontiguousarray(X[i:i + bs], dtype=np.float32)})
        prob = r[1]
        if isinstance(prob, list):
            out[i:i + bs] = np.array([d[1] for d in prob], dtype=np.float32)
        else:
            out[i:i + bs] = np.asarray(prob)[:, 1].astype(np.float32)
    return out


def run_map(gdir, outdir, name):
    env = dict(os.environ, X1_CUTS="20251001", X1_G015_DIR=gdir)
    os.makedirs(outdir, exist_ok=True)
    r = subprocess.run([sys.executable, "-u", "x1_build_map.py", name, outdir], cwd=REPO + "/research/pipeline/x1",
                       env=env, capture_output=True, text=True)
    log.info("map %s rc=%d tail=%s", gdir, r.returncode, r.stdout.strip().splitlines()[-2:])
    assert r.returncode == 0 and "MAP_OK" in r.stdout
    return outdir + "/predict_wf_20251001.bin"


def gate_a(orig_path):
    g = dict(onnx=ONNX, onnx_sha256=ONNX_SHA, orig=orig_path)
    g["A0_sha256"] = sha256f(orig_path)
    g["A0"] = g["A0_sha256"] == ORIG_SHA
    lo, hi = G.ms("20251001"), G.ms("20260101")
    X, ts, sym, info = H1.build_rows([os.path.join(G.T1_DIR, "features_20250701*"),
                                      os.path.join(G.T1_DIR, "features_20251001*")], lo, hi)
    m = (ts >= lo) & (ts < hi)
    X, ts, sym = X[m], ts[m], sym[m]
    p = predict(X)
    del X
    g["chunk"] = info
    k = ts * 10000 + sym.astype(np.int64)
    r = np.fromfile(orig_path, dtype=DT)
    kr = r["ts"].astype(np.int64) * 10000 + r["sym"].astype(np.int64)
    assert len(np.unique(k)) == len(k) and len(np.unique(kr)) == len(kr)
    o = np.argsort(k)
    pos = np.searchsorted(k[o], kr)
    pos = np.clip(pos, 0, len(k) - 1)
    hit = k[o][pos] == kr
    g.update(n_new=int(len(k)), n_orig=int(len(kr)), keys_equal=bool(len(k) == len(kr) and hit.all()))
    if not g["keys_equal"]:
        g["A1"] = g["A2"] = g["A2c"] = False
        return g
    pv = p[o][pos]                       # gia tri ONNX theo DUNG thu tu dong file goc
    d = np.abs(pv.astype(np.float64) - r["p0"].astype(np.float64))
    g.update(A1_max_abs=float(d.max()), A1_mean_abs=float(d.mean()), A1_nan_new=int(np.isnan(pv).sum()),
             A1_bit_identical_frac=float((pv.view(np.uint32) == r["p0"].astype(np.float32).view(np.uint32)).mean()))
    g["A1"] = bool(g["A1_max_abs"] <= 1e-6 and g["A1_nan_new"] == 0)
    dev = np.fromfile(DEV_BIN, dtype=DT)
    g["dev_md5"] = hashlib.md5(open(DEV_BIN, "rb").read()).hexdigest()
    # A2c: map tren chinh file goc -> == bins DEV byte
    d_in = W + "/gateA/a2c_in"
    os.makedirs(d_in, exist_ok=True)
    dst = d_in + "/predict_wf_20251001.bin"
    if not os.path.exists(dst):
        os.link(os.path.realpath(orig_path), dst)
    b2c = run_map(d_in, W + "/gateA/a2c_out", "s1a2x1")
    g["A2c_md5"] = hashlib.md5(open(b2c, "rb").read()).hexdigest()
    g["A2c"] = g["A2c_md5"] == g["dev_md5"]
    # A2: gia tri ONNX theo thu tu goc -> map -> so bins DEV
    a2 = r.copy()
    a2["p0"] = pv.astype(np.float32)
    d_in = W + "/gateA/a2_in"
    os.makedirs(d_in, exist_ok=True)
    a2.tofile(d_in + "/predict_wf_20251001.bin")
    b2 = np.fromfile(run_map(d_in, W + "/gateA/a2_out", "s1a2x1"), dtype=DT)
    keq = len(b2) == len(dev) and np.array_equal(b2["ts"], dev["ts"]) and np.array_equal(b2["sym"], dev["sym"])
    g["A2_keys_equal"] = bool(keq)
    if keq:
        dd = np.abs(b2["p0"].astype(np.float64) - dev["p0"].astype(np.float64))
        g["A2_max_abs"] = float(dd.max())
        g["A2_n_gt_1e6"] = int((dd > 1e-6).sum())
        g["A2_bit_identical_frac"] = float((b2["p0"].view(np.uint32) == dev["p0"].view(np.uint32)).mean())
        g["A2_p123_bit_equal"] = bool(all(np.array_equal(b2[c].view(np.uint32), dev[c].view(np.uint32)) for c in ("p1", "p2", "p3")))
        g["A2"] = bool(g["A2_max_abs"] <= 1e-6 and g["A2_p123_bit_equal"])
    else:
        g["A2"] = False
    g["pass"] = bool(g["A0"] and g["A1"] and g["A2c"] and g["A2"])
    log.info("CONG A: %s", g)
    return g


def run_2026():
    """= H1.run_2026 nhung model = ONNX goc. SEAL: chi dem/NaN/khoang ts/sha."""
    X, ts, sym, info = H1.build_rows([os.path.join(G.T1_DIR, "features_20251001*"), os.path.join(G.T1_DIR, "features_2026*")],
                                      G.ms("20260101"), G.ms("20260701"))
    os.makedirs(OUT26, exist_ok=True)
    outs = {}
    for c0, c1 in (("20260101", "20260401"), ("20260401", "20260701")):
        lo, hi = G.ms(c0), G.ms(c1)
        m = (ts >= lo) & (ts < hi)
        p = predict(X[m])
        path = os.path.join(OUT26, "predict_wf_%s.bin" % c0)
        G.write_bin(path, ts[m], sym[m], p)
        tq = ts[m]
        outs[c0] = dict(path=path, n=int(m.sum()), nan=int(np.isnan(p).sum()), ts_min=int(tq.min()), ts_max=int(tq.max()),
                        span_days=int((tq.max() - tq.min()) // 86400000), lo=lo, hi=hi, sha256=sha256f(path),
                        bytes=os.path.getsize(path))
        assert outs[c0]["sha256"] not in BLACK and outs[c0]["span_days"] <= 100 and lo <= tq.min() and tq.max() < hi
        assert outs[c0]["nan"] == 0
        log.info("2026 %s: %s", c0, outs[c0])
    return dict(chunk=info, files=outs)


def main():
    os.makedirs(W + "/gateA", exist_ok=True)
    res = dict(prereg="1682a311+2691816d (ADDENDUM-2)", phuong_an="A")
    res["gate_A"] = gate_a(sys.argv[1])
    json.dump(res, open(W + "/gateA/gateA.json", "w"), indent=1, default=str)
    if not res["gate_A"]["pass"]:
        log.error("CONG A FAIL -> PHUONG AN B (khong predict 2026)")
        sys.exit(2)
    res["pred_2026"] = run_2026()
    json.dump(res, open(W + "/gateA/gateA.json", "w"), indent=1, default=str)
    log.info("XONG HO2 net015 A")


if __name__ == "__main__":
    main()
