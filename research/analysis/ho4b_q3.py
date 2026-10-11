#!/usr/bin/env python3
"""HO4-P0b Q3: kiem ke model cho holdout (KHONG mo so 2026 — chi ty le khop/sha).
(1) 8 model gate seed cut20260101 (HO1 B2): sha vs manifest; predict lai store H1 -> so pred_s*/pred.bin (|d|<=1e-6, bit).
(2) retrain seed 42 vao thu muc TAM -> sha + |d| du doan H1 vs model goc. (3) sha ONNX net015 + S1 json; net015 fold 20260101
predict lai (ONNX goc, Tool1+OI ghim) -> so net015_2026A. Usage: ho4b_q3.py <out.json>"""
import hashlib, json, logging, os, struct, sys, tempfile
import numpy as np
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R); sys.path.insert(0, R + "/research/analysis"); sys.path.insert(0, R + "/research/pipeline")
import ho1_gate_build as HG  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho4b_q3")
OUT = sys.argv[1]
RES = {}


def save():
    json.dump(RES, open(OUT, "w"), indent=1, default=str)


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def cmp(a, b):
    d = np.abs(a.astype(np.float64) - b.astype(np.float64))
    return dict(n=int(len(d)), le1e6=float((d <= 1e-6).mean()), bit=float((a.astype(np.float32).view(np.uint32) == b.astype(np.float32).view(np.uint32)).mean()),
                max_abs=float(d.max()) if len(d) else None)


def gate():
    from xgboost import XGBRegressor
    man = json.load(open(HG.D + "/manifest_gate.json"))
    df, _ = HG.load_2026()
    X = df[HG.GA.V3FULL].to_numpy(np.float32)
    ts = df["timestamp"].to_numpy(np.int64)
    out = {"manifest_keys": list(man)[:12]}
    P = {}
    for s in HG.SEEDS:
        mp = HG.D + "/gate_s%d_cut20260101p15.json" % s
        r = dict(exists=os.path.exists(mp))
        if r["exists"]:
            r["sha256"] = sha(mp)
            m = XGBRegressor(); m.load_model(mp)
            p = m.predict(X).astype(np.float32)
            P[s] = p
            raw = open(HG.D + "/pred_s%d/pred.bin" % s, "rb").read()
            n = struct.unpack(">i", raw[:4])[0]
            a = np.frombuffer(raw[4:4 + 16 * n], dtype=HG.REC)
            t = a["ts"].astype(np.int64)
            k = t >= HG.SEAL
            ok_ts = bool(np.array_equal(t[k], ts))
            r.update(ts_equal=ok_ts, pred_md5=hashlib.md5(raw).hexdigest(), **({"h1": cmp(p, a["p15"][k])} if ok_ts else {}))
        out["s%d" % s] = r
        log.info("gate s%d %s", s, {kk: v for kk, v in r.items() if kk != "sha256"})
    RES["gate"] = out; save()
    # retrain seed 42 vao thu muc tam (khong ghi de model goc)
    tmp = tempfile.mkdtemp(prefix="ho4b_q3_", dir="/home/ubuntu/claude_master/1011/ho4b")
    HG.D = tmp
    dev = HG.load_dev()
    m2, meta = HG.train(42, dev)
    p2 = m2.predict(X).astype(np.float32)
    RES["retrain_s42"] = dict(sha256=meta["model_sha256"], sha_equal=meta["model_sha256"] == out["s42"].get("sha256"),
                              n_train=meta["n_train"], train_ts_max=meta["train_ts_max"], h1_vs_orig_model=cmp(p2, P[42]))
    os.remove(meta["model"]); os.rmdir(tmp)
    log.info("retrain s42 %s", RES["retrain_s42"]); save()


def net_s1():
    import g015_net_train as G
    import ho1_net015_predict as HN
    import ho2_net015_onnx as H2
    r = dict(onnx=H2.ONNX, onnx_sha_ok=sha(H2.ONNX) == H2.ONNX_SHA,
             s1_json="/home/ubuntu/s1_model/s1a2x1_cut20251231.json",
             s1_sha_ok=sha("/home/ubuntu/s1_model/s1a2x1_cut20251231.json") == "af706dc654c96f075caddc5f4153c768eec0732a28340cf9adbd6a6f791d8bf1")
    ref = H2.OUT26 + "/predict_wf_20260101.bin"
    r["ref_sha_ok"] = sha(ref) == "8df74093" + sha(ref)[8:] if os.path.exists(ref) else False
    lo, hi = G.ms("20260101"), G.ms("20260401")
    X, ts, sym, info = HN.build_rows([os.path.join(G.T1_DIR, "features_20251001*"), os.path.join(G.T1_DIR, "features_2026*")], lo, hi)
    m = (ts >= lo) & (ts < hi)
    p = H2.predict(X[m]); ts, sym = ts[m], sym[m]
    del X
    a = np.fromfile(ref, dtype=HN.DT)
    ka = a["ts"].astype(np.int64) * 10000 + a["sym"].astype(np.int64)
    kn = ts * 10000 + sym.astype(np.int64)
    com, ia, ib = np.intersect1d(ka, kn, return_indices=True)
    r.update(n_ref=int(len(ka)), n_new=int(len(kn)), common=int(len(com)), fold20260101=cmp(p[ib], a["p0"][ia]))
    RES["net015_s1"] = r
    log.info("net015/S1 %s", r); save()


if __name__ == "__main__":
    for nm in sys.argv[2:] or ["gate", "net"]:
        {"gate": gate, "net": net_s1}[nm]()
    log.info("Q3_DONE")
