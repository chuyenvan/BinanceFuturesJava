#!/usr/bin/env python3
"""HO3b cong 4 (ADDENDUM-4 §4b, 62c0cd67): dung market.bin + pred.bin s42 cho 2 kernel kinh te H1.
 market.bin = ban ghi HO26 ts < SEAL7 (byte) + MOI phut Kernel A (Java inline) trong [SEAL7, ts cuoi HO26].
 3 feature gate (momentum1M/15M/Acc) H1 tu md inline (khong co md => 0; Acc = f32(m5) - f32(m15)); p15 s42 = model HO1 B2.
 Kiem: predict lai X goc == p15 H1 cua pred HO26 s42 (bit). Chi dem/md5; KHONG in gia tri.
Usage: ho3b_mk_build.py <kernelA_market.bin> <outdir> [upload]"""
import hashlib, json, logging, os, struct, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_mk")
TZ = "Asia/Ho_Chi_Minh"
SEAL7 = pd.Timestamp("2026-01-01", tz=TZ).value // 10**6
END7 = pd.Timestamp("2026-07-01", tz=TZ).value // 10**6
MKT26, MKT26_MD5 = "/home/ubuntu/claude_master/1003/ho1/ds/market.bin", "34e33678105275b3620d1c92c3510172"
PRED26, PRED26_MD5 = "/home/ubuntu/claude_master/1003/ho1/gate/pred_s42/pred.bin", "22f69456381d9d1abd1592382c3b0319"
MODEL42 = "/home/ubuntu/claude_master/1003/ho1/gate/gate_s42_cut20260101p15.json"
MDT = np.dtype([("ts", ">i8"), ("v", ">f4", 3)])
REC = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def rd_market(p):
    raw = open(p, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    assert len(raw) == 4 + 20 * n
    return np.frombuffer(raw[4:], dtype=MDT, count=n), raw


def build_market(ka, out):
    assert md5f(MKT26) == MKT26_MD5
    old, raw = rd_market(MKT26)
    new, _ = rd_market(ka)
    ot, nt = old["ts"].astype(np.int64), new["ts"].astype(np.int64)
    assert (np.diff(ot) > 0).all() and (np.diff(nt) > 0).all()
    k = int(np.searchsorted(ot, SEAL7))
    last = int(ot[-1])
    sel = new[(nt >= SEAL7) & (nt <= last)]
    n = k + len(sel)
    with open(out, "wb") as f:
        f.write(struct.pack(">i", n))
        f.write(raw[4:4 + 20 * k])
        f.write(sel.tobytes())
    chk = open(out, "rb").read()
    assert hashlib.md5(chk[4:4 + 20 * k]).hexdigest() == hashlib.md5(raw[4:4 + 20 * k]).hexdigest()
    oh = set(ot[k:].tolist())
    nh = set(sel["ts"].astype(np.int64).tolist())
    info = dict(n_total=n, n_dev=k, n_h1_ho26=len(oh), n_h1_inline=len(nh), inline_only=len(nh - oh),
                ho26_only=len(oh - nh), ka_rows=int(len(new)), ka_first=int(nt[0]), ka_last=int(nt[-1]), last_ho26=last,
                md5=hashlib.md5(chk).hexdigest(), bytes=len(chk), md5_dev_prefix=hashlib.md5(raw[4:4 + 20 * k]).hexdigest())
    log.info("MARKET %s", info)
    return {int(t): (np.float32(v[0]), np.float32(v[2])) for t, v in zip(sel["ts"], sel["v"])}, info


def load_h1():
    use = ["timestamp"] + GA.V3FULL
    df = pd.read_csv(GA.STORE, usecols=use, dtype={c: np.float32 for c in GA.V3FULL})
    df["timestamp"] = df["timestamp"].astype(np.int64)
    df = df[(df["timestamp"] >= SEAL7) & (df["timestamp"] < END7)].sort_values("timestamp").reset_index(drop=True)
    assert df["timestamp"].is_unique
    return df


def build_pred(md, outp):
    from xgboost import XGBRegressor
    assert md5f(PRED26) == PRED26_MD5
    raw = open(PRED26, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:], dtype=REC, count=n)
    ts = a["ts"].astype(np.int64)
    k = int(np.searchsorted(ts, SEAL7))
    df = load_h1()
    t26 = df["timestamp"].to_numpy(np.int64)
    assert np.array_equal(t26, ts[k:]), "tap ts H1 store != pred HO26"
    m = XGBRegressor()
    m.load_model(MODEL42)
    X = df[GA.V3FULL].to_numpy(np.float32)
    p0 = m.predict(X).astype(np.float32)
    rep = bool(np.array_equal(p0.view(np.uint32), a["p15"][k:].astype(np.float32).view(np.uint32)))
    log.info("TAI HIEN p15 H1 HO26 s42 (bit): %s", rep)
    assert rep, "khong tai hien duoc p15 HO26 -> DUNG"
    i1, i15, i5, ia = (GA.V3FULL.index(c) for c in ("momentum1M", "momentum15M", "momentum5M", "momentumAcceleration"))
    hit = np.array([t in md for t in t26])
    m1 = np.array([md[t][0] if t in md else np.float32(0) for t in t26], dtype=np.float32)
    m15 = np.array([md[t][1] if t in md else np.float32(0) for t in t26], dtype=np.float32)
    X2 = X.copy()
    X2[:, i1], X2[:, i15] = m1, m15
    X2[:, ia] = (X2[:, i5].astype(np.float32) - m15).astype(np.float32)
    p1 = m.predict(X2).astype(np.float32)
    assert np.isfinite(p1).all()
    b = a.copy()
    b["p15"][k:] = p1.astype(">f4")
    with open(outp, "wb") as f:
        f.write(raw[:4]); f.write(b.tobytes())
    chk = open(outp, "rb").read()
    assert chk[:4 + 16 * k] == raw[:4 + 16 * k] and len(chk) == len(raw)
    info = dict(n=n, n_dev=k, n_h1=int(len(t26)), h1_md_hit=int(hit.sum()), h1_md_miss=int((~hit).sum()),
                rows_m1_changed=int((X2[:, i1] != X[:, i1]).sum()), rows_p15_changed=int((p1 != p0).sum()),
                md5=hashlib.md5(chk).hexdigest(), reproduce_ho26_bit=rep, model=MODEL42)
    log.info("PRED %s", info)
    return info


def upload(folder, name, fname):
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    json.dump({"title": name, "id": "chuyendinh/" + name, "licenses": [{"name": "CC0-1.0"}]},
              open(os.path.join(folder, "dataset-metadata.json"), "w"))
    r = a.dataset_create_new(folder, public=False, quiet=True, dir_mode="skip")
    log.info("UPLOAD %s -> %s", name, getattr(r, "url", r))


def main():
    ka, out = sys.argv[1], sys.argv[2]
    dm, dp = os.path.join(out, "ds_mkt"), os.path.join(out, "ds_pred")
    os.makedirs(dm, exist_ok=True); os.makedirs(dp, exist_ok=True)
    md, mi = build_market(ka, os.path.join(dm, "market.bin"))
    pi = build_pred(md, os.path.join(dp, "pred.bin"))
    res = dict(prereg="ADDENDUM-4 §4b 62c0cd67", kernel_a_market=ka, kernel_a_md5=md5f(ka), market=mi, pred=pi)
    json.dump(res, open(os.path.join(out, "mk_build.json"), "w"), indent=1)
    if len(sys.argv) > 3 and sys.argv[3] == "upload":
        upload(dm, "ho3b-mkt-h1", "market.bin")
        upload(dp, "ho3b-pred-mk-s42", "pred.bin")


if __name__ == "__main__":
    main()
