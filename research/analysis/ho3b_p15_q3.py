#!/usr/bin/env python3
"""HO3b B3: p15 Q3 cho 8 seed = model gate HO1 B2 (cut 2026-01-01 +07, KHONG retrain; ADDENDUM-3 §4) predict tren store
gate Q3 (exporter Java goc, chi cot timestamp + 33 V3FULL, KHONG doc nhan). pred.bin = ban ghi pred HO26 seed do NGUYEN byte
+ ban ghi Q3 ts in [2026-07-01, 2026-10-01) +07 (predRisk4H = 0f). Chi dem/NaN/md5. Usage: ho3b_p15_q3.py <store_q3.csv.gz> <out_dir>"""
import hashlib, json, logging, os, struct, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho3b_p15")
TZ = "Asia/Ho_Chi_Minh"
Q0 = pd.Timestamp("2026-07-01", tz=TZ).value // 10**6
Q1 = pd.Timestamp("2026-10-01", tz=TZ).value // 10**6
HO1 = "/home/ubuntu/claude_master/1003/ho1/gate"
PREDS = json.load(open("/home/ubuntu/claude_master/1009/ho26/kaggle/stage_manifest.json"))["preds"]
REC = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]


def main():
    store, out = sys.argv[1], sys.argv[2]
    use = ["timestamp"] + GA.V3FULL
    assert not any(c.startswith("label") for c in use)
    df = pd.read_csv(store, usecols=use, dtype={c: np.float32 for c in GA.V3FULL})
    df["timestamp"] = df["timestamp"].astype(np.int64)
    df = df[(df.timestamp >= Q0) & (df.timestamp < Q1)].sort_values("timestamp").reset_index(drop=True)
    assert df.timestamp.is_unique
    X = df[GA.V3FULL].to_numpy(np.float32)
    ts = df.timestamp.to_numpy(np.int64)
    info = dict(n_q3=int(len(df)), n_minutes=int((Q1 - Q0) // 60000), ts_first=int(ts[0]), ts_last=int(ts[-1]),
                nan_by_feat={c: int(df[c].isna().sum()) for c in GA.V3FULL if df[c].isna().any()})
    log.info("STORE Q3 %s", info)
    from xgboost import XGBRegressor
    res = dict(store=store, store_md5=hashlib.md5(open(store, "rb").read()).hexdigest(), info=info, seeds={})
    for s in SEEDS:
        src = HO1 + "/pred_s%d/pred.bin" % s
        raw = open(src, "rb").read()
        assert hashlib.md5(raw).hexdigest() == PREDS[str(s)], ("md5 pred HO26", s)
        n = struct.unpack(">i", raw[:4])[0]
        a = np.frombuffer(raw[4:], dtype=REC, count=n)
        assert int(a["ts"][-1]) < Q0 and ts[0] > int(a["ts"][-1])
        m = XGBRegressor(); m.load_model(HO1 + "/gate_s%d_cut20260101p15.json" % s)
        p = m.predict(X).astype(np.float32)
        assert np.isfinite(p).all()
        b = np.zeros(len(ts), dtype=REC); b["ts"] = ts; b["p15"] = p; b["risk"] = np.float32(0)
        d = os.path.join(out, "pred_s%d" % s); os.makedirs(d, exist_ok=True)
        with open(d + "/pred.bin", "wb") as f:
            f.write(struct.pack(">i", n + len(ts))); f.write(raw[4:]); f.write(b.tobytes())
        chk = open(d + "/pred.bin", "rb").read()
        assert chk[4:4 + 16 * n] == raw[4:]
        res["seeds"][str(s)] = dict(md5=hashlib.md5(chk).hexdigest(), n=n + len(ts), n_ho26=n, n_q3=int(len(ts)),
                                    md5_prefix_ho26_records=hashlib.md5(raw[4:]).hexdigest())
        log.info("seed %d %s", s, res["seeds"][str(s)])
    json.dump(res, open(os.path.join(out, "p15_q3.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
