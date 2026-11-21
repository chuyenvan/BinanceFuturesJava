#!/usr/bin/env python3
"""rt_p15_train.py - wrapper PREREG_RETRAIN_PILOT (c796c7b3) muc 1.1 / 4 / 5.
Chay DUNG byte ml/gate/train_gate_fold.py (kiem md5) bang runpy, lay `model`/`tr`/`df` tu globals -> luu booster JSON,
manifest, parity ORT(ONNX moi) vs booster tren >= 20 000 dong DEV ts < S0 (rng 20261121), va (tuy chon) so voi ONNX tham chieu.
Usage: rt_p15_train.py --tag T --data CSV --cutoff YYYYMMDD --purge-ms N --out DIR [--ref-onnx P] [--expect-md5 M]
       [--assert-max-ts MS]"""
import argparse, hashlib, json, logging, os, runpy, sys, time
import numpy as np
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger("rtp15")
SCRIPT = "/home/ubuntu/claude_master/vz_e1_wt/ml/gate/train_gate_fold.py"
SCRIPT_MD5 = "b41c9159597ceecb254240b789429a98"
S0 = 1767200400000


def h(p, a="md5"):
    x = hashlib.new(a)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            x.update(b)
    return x.hexdigest()


def ort_pred(path, X):
    import onnxruntime as ort
    s = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
    nm = s.get_inputs()[0].name
    return np.asarray(s.run(None, {nm: np.ascontiguousarray(X, dtype=np.float32)})[0], dtype=np.float64).reshape(-1)


def main():
    ap = argparse.ArgumentParser()
    for a in ("--tag", "--data", "--cutoff", "--purge-ms", "--out"):
        ap.add_argument(a, required=True)
    ap.add_argument("--ref-onnx"); ap.add_argument("--expect-md5"); ap.add_argument("--assert-max-ts", type=int); ap.add_argument("--note", default="")
    a = ap.parse_args()
    assert h(SCRIPT) == SCRIPT_MD5, "md5 train_gate_fold.py KHAC"
    os.makedirs(a.out, exist_ok=True)
    L.info("NOTE %s", a.note)
    os.environ.update(DATA=a.data, CUTOFF=a.cutoff, OUT_DIR=a.out, GATE_PURGE_MS=str(int(a.purge_ms)))
    t0 = time.time()
    g = runpy.run_path(SCRIPT, run_name="__main__")
    secs = round(time.time() - t0, 1)
    model, tr, df, V3 = g["model"], g["tr"], g["df"], g["V3FULL"]
    onx = os.path.join(a.out, "Model_Regressor_Return15M.onnx")
    bj = os.path.join(a.out, "booster.json")
    model.get_booster().save_model(bj)
    tr_max = int(tr.timestamp.max())
    if a.assert_max_ts is not None:
        assert tr_max < a.assert_max_ts, ("ASSERT train ts", tr_max, a.assert_max_ts)
    dev = df[df.timestamp < S0]
    rng = np.random.default_rng(20261121)
    idx = np.sort(rng.choice(len(dev), 20000, replace=False))
    X = dev[V3].to_numpy(np.float32)[idx]
    p_b = model.predict(X).astype(np.float64)
    p_o = ort_pred(onx, X)
    d = np.abs(p_b - p_o)
    man = {"note": a.note, "tag": a.tag, "cutoff": a.cutoff, "purge_ms": int(a.purge_ms), "script": SCRIPT, "script_md5": SCRIPT_MD5,
           "data": a.data, "data_md5": h(a.data), "train_rows": int(len(tr)), "train_ts_min": int(tr.timestamp.min()),
           "train_ts_max": tr_max, "assert_max_ts": a.assert_max_ts, "rows_file": int(len(df)),
           "xgb_params": {k: v for k, v in model.get_params().items() if v is not None and not callable(v)},
           "onnx_md5": h(onx), "onnx_sha256": h(onx, "sha256"), "booster_sha256": h(bj, "sha256"), "fit_wall_s": secs,
           "parity_onnx_vs_booster": {"n": int(len(d)), "max_abs": float(d.max()), "pass_1e6": bool(d.max() <= 1e-6)},
           "nan_pred": int(np.isnan(p_o).sum())}
    import xgboost, onnxruntime, onnxmltools
    man["env"] = {"python": sys.version.split()[0], "exe": sys.executable, "xgboost": xgboost.__version__,
                  "onnxruntime": onnxruntime.__version__, "onnxmltools": onnxmltools.__version__}
    if a.expect_md5:
        man["expect_md5"] = a.expect_md5
        man["md5_eq"] = man["onnx_md5"] == a.expect_md5
    if a.ref_onnx:
        p_r = ort_pred(a.ref_onnx, X)
        dr = np.abs(p_r - p_o); dbr = np.abs(p_r - p_b)
        man["ref"] = {"path": a.ref_onnx, "md5": h(a.ref_onnx), "n": int(len(dr)),
                      "max_abs_onnx_new_vs_ref": float(dr.max()), "max_abs_booster_new_vs_ref": float(dbr.max()),
                      "pass_1e6": bool(dbr.max() <= 1e-6 and dr.max() <= 1e-6)}
        try:
            import onnx
            def struct(p):
                m = onnx.load(p); n = [x for x in m.graph.node if "TreeEnsemble" in x.op_type][0]
                at = {x.name: x for x in n.attribute}
                return len(set(at["nodes_treeids"].ints)), len(at["nodes_nodeids"].ints)
            man["ref"]["trees_nodes_new"], man["ref"]["trees_nodes_ref"] = struct(onx), struct(a.ref_onnx)
        except Exception as e:  # mo ta
            man["ref"]["struct_err"] = str(e)[:200]
    json.dump(man, open(os.path.join(a.out, "manifest_rt.json"), "w"), indent=1, default=str)
    L.info("RESULT %s", json.dumps(man, default=str))


if __name__ == "__main__":
    main()
