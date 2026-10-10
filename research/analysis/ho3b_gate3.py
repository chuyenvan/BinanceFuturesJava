#!/usr/bin/env python3
"""HO3b cong 3 (ADDENDUM-4 §4a, 62c0cd67): OI dung lai (Vision) -> feature OI -> net015 p0 + S1 -> bins H1, so HO26.
OI ghep = file ghim ts < SEAL7 + ban dung lai ts >= SEAL7. --mode pinned = DOI CHUNG (chi file ghim) phai tai hien HO26
(net015 bit, bins byte) => chung minh duong ong; --mode rebuilt = cong that. Chi in dem/ty le; KHONG in gia tri.
Usage: ho3b_gate3.py --mode pinned|rebuilt --out DIR"""
import argparse, glob, hashlib, json, logging, os, struct, subprocess, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R + "/research/pipeline"); sys.path.insert(0, R + "/research/analysis")
import g015_net_train as G  # noqa: E402
import ho1_net015_predict as HN  # noqa: E402
import ho2_net015_onnx as H2  # noqa: E402
import ho1_featv2_window as FW  # noqa: E402
import ho1_s1_2026 as S1  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho3b_g3")
SEAL7 = 1767200400000
H = 3600000
ODT = G.OI_DT
PIN = G.OI_FILE
RB = "/home/ubuntu/claude_master/1003/ho3b/oi_rebuild"
HO26_NET = "/home/ubuntu/claude_master/1009/ho26/net015_2026A"
HO26_BINS = "/home/ubuntu/claude_master/1009/ho26/bins2026A"
C26 = "/home/ubuntu/claude_master/1003/ho1/s1/CLOSES_1H_2026v2.bin"
MODE = None
_RBA = None


def rebuilt():
    global _RBA
    if _RBA is None:
        fs = sorted(glob.glob(RB + "/*.bin"))
        _RBA = np.concatenate([np.fromfile(f, dtype=ODT) for f in fs])
        log.info("rebuilt OI: %d file, %d dong", len(fs), len(_RBA))
    return _RBA


def read_pin(lo, hi, hourly=False, step=10_000_000):
    n = os.path.getsize(PIN) // ODT.itemsize
    parts = []
    for k in range(0, n, step):
        c = np.fromfile(PIN, dtype=ODT, count=min(step, n - k), offset=k * ODT.itemsize)
        t = c["ts"].astype(np.int64)
        m = (t >= lo) & (t < hi)
        if hourly:
            m &= (t % H == 0)
        parts.append(c[m].copy())
    return np.concatenate(parts)


def read_oi_comb(lo, hi):
    """thay HN.read_oi: OI ghep theo MODE."""
    if MODE == "pinned":
        return read_pin(lo, hi)
    a = read_pin(lo, min(hi, SEAL7)) if lo < SEAL7 else np.zeros(0, ODT)
    r = rebuilt()
    t = r["ts"].astype(np.int64)
    b = r[(t >= max(lo, SEAL7)) & (t < hi)]
    return np.concatenate([a, b])


def comb_hourly_file(path):
    lo, hi = FW.T_START - 3 * H, FW.T_END + 1
    a = read_oi_comb(lo, hi)
    a = a[a["ts"].astype(np.int64) % H == 0]
    a.astype(ODT).tofile(path)   # FIX: np.concatenate tra ve native-endian; file OI la big-endian
    log.info("OI gio ghep -> %s %d dong", path, len(a))


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def stage_feat_s1(out):
    """feat_v2 cua so (OI ghep) -> G-B4a 2025Q4 -> S1 predict-only tren pool HO26 (khong doi)."""
    hp = out + "/oi_hourly.bin"
    comb_hourly_file(hp)
    FW.OI = hp
    P = FW.closes(C26)
    long = FW.features(P)
    g = FW.gate(long)
    os.remove(hp)
    F = long[["ts", "sym"] + S1.KEEP].copy()
    F["sym"] = F.sym.astype(np.int64)
    raw = open(S1.PRED42, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + 16 * n], dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("r", ">f4")]))
    ts = a["ts"].astype(np.int64)
    m = (ts >= S1.SEAL7) & (ts < S1.END7) & (ts % S1.Q == 0)
    open_ts = ts[m][a["p15"][m].astype(np.float32) >= np.float32(0.008)]
    files = sorted(glob.glob(S1.LBDIR + "/funding_label_2026*.pb"))
    A = S1.avail_pool(open_ts, files)
    assert S1.sha256f(S1.M1231) == S1.M1231_SHA
    S, cov = S1.score(S1.M1231, A, F)
    sp = out + "/pred_s1.parquet"
    S[["ts", "sym", "score"]].to_parquet(sp, index=False)
    return dict(G_B4a=g, pool_rows=int(len(A)), s1_rows=int(len(S)), feat_cov=cov, pred=sp, pred_sha256=sha256f(sp))


def stage_net(out):
    HN.read_oi = read_oi_comb
    X, ts, sym, info = HN.build_rows([os.path.join(G.T1_DIR, "features_20251001*"), os.path.join(G.T1_DIR, "features_2026*")],
                                     G.ms("20260101"), G.ms("20260701"))
    nd = out + "/net015"
    os.makedirs(nd, exist_ok=True)
    res = dict(chunk=info)
    for c0, c1 in (("20260101", "20260401"), ("20260401", "20260701")):
        lo, hi = G.ms(c0), G.ms(c1)
        m = (ts >= lo) & (ts < hi)
        p = H2.predict(X[m])
        path = os.path.join(nd, "predict_wf_%s.bin" % c0)
        G.write_bin(path, ts[m], sym[m], p)
        res[c0] = dict(n=int(m.sum()), nan=int(np.isnan(p).sum()), sha256=sha256f(path))
    del X
    return res


def stage_map(out, name):
    lk = "/home/ubuntu/ledger/pred_%s.parquet" % name
    if os.path.lexists(lk):
        os.remove(lk)
    os.symlink(out + "/pred_s1.parquet", lk)
    env = dict(os.environ, X1_CUTS="20260101 20260401", X1_G015_DIR=out + "/net015")
    r = subprocess.run([sys.executable, "-u", "x1_build_map.py", name, out + "/bins"], cwd=R + "/research/pipeline/x1",
                       env=env, capture_output=True, text=True)
    os.remove(lk)
    assert r.returncode == 0 and "MAP_OK" in r.stdout, r.stdout[-500:] + r.stderr[-500:]
    return dict(map_tail=r.stdout.strip().splitlines()[-1])


def keyed(path):
    a = np.fromfile(path, dtype=HN.DT)
    k = a["ts"].astype(np.int64) * 10000 + a["sym"].astype(np.int64)
    o = np.argsort(k, kind="stable")
    return k[o], a[o]


def compare(out):
    from scipy.stats import spearmanr
    res = {}
    K1, K2, A1, A2 = [], [], [], []
    for c0 in ("20260101", "20260401"):
        k1, a1 = keyed(out + "/net015/predict_wf_%s.bin" % c0)
        k2, a2 = keyed(HO26_NET + "/predict_wf_%s.bin" % c0)
        K1.append(k1); K2.append(k2); A1.append(a1); A2.append(a2)
    k1, k2, a1, a2 = np.concatenate(K1), np.concatenate(K2), np.concatenate(A1), np.concatenate(A2)
    K = k1
    keq = bool(len(k1) == len(k2) and np.array_equal(k1, k2))
    p1, p2 = a1["p0"].astype(np.float64), a2["p0"].astype(np.float64)
    res["net015"] = dict(n=int(len(k1)), n_ho26=int(len(k2)), keys_equal=keq)
    if keq:
        d = np.abs(p1 - p2)
        res["net015"].update(spearman=float(spearmanr(p1, p2).correlation), frac_le_1e3=float((d <= 1e-3).mean()),
                             bit_equal_frac=float((a1["p0"].view(np.uint32) == a2["p0"].view(np.uint32)).mean()))
    BK1, BK2, B1, B2 = [], [], [], []
    for c0 in ("20260101", "20260401"):
        k1, b1 = keyed(out + "/bins/predict_wf_%s.bin" % c0)
        k2, b2 = keyed(HO26_BINS + "/predict_wf_%s.bin" % c0)
        BK1.append(k1); BK2.append(k2); B1.append(b1); B2.append(b2)
    k1, k2, b1, b2 = np.concatenate(BK1), np.concatenate(BK2), np.concatenate(B1), np.concatenate(B2)
    bkeq = bool(len(k1) == len(k2) and np.array_equal(k1, k2))
    res["bins"] = dict(n=int(len(k1)), n_ho26=int(len(k2)), keys_equal=bkeq)
    if bkeq:
        ok = np.ones(len(k1), bool)
        for c in ("p0", "p1", "p2", "p3"):
            x, y = b1[c].astype(np.float64), b2[c].astype(np.float64)
            ok &= (np.abs(x - y) <= 1e-6) | (np.isnan(x) & np.isnan(y))
        res["bins"].update(cell_eq_frac=float(ok.mean()),
                           byte_equal={c0: hashlib.md5(open(out + "/bins/predict_wf_%s.bin" % c0, "rb").read()).hexdigest()
                                       == hashlib.md5(open(HO26_BINS + "/predict_wf_%s.bin" % c0, "rb").read()).hexdigest()
                                       for c0 in ("20260101", "20260401")})
    # mo ta theo thang (+07), KHONG vao cong
    try:
        mo = lambda k: pd.to_datetime(k // 10000, unit="ms", utc=True).tz_convert("Asia/Ho_Chi_Minh").strftime("%Y-%m")
        if keq:
            mm = np.asarray(mo(K))
            res["net015"]["by_month"] = {m: dict(n=int((mm == m).sum()), frac_le_1e3=float((np.abs(p1 - p2)[mm == m] <= 1e-3).mean()),
                                                 spearman=float(spearmanr(p1[mm == m], p2[mm == m]).correlation)) for m in sorted(set(mm))}
        if bkeq:
            mb = np.asarray(mo(k1))
            res["bins"]["by_month"] = {m: float(ok[mb == m].mean()) for m in sorted(set(mb))}
    except Exception as e:  # noqa: BLE001
        res["by_month_error"] = repr(e)[:200]
    n3 = res["net015"]
    res["PASS"] = bool(n3["keys_equal"] and bkeq and n3.get("spearman", 0) >= 0.99 and n3.get("frac_le_1e3", 0) >= 0.99
                       and res["bins"].get("cell_eq_frac", 0) >= 0.99)
    return res


def main():
    global MODE
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["pinned", "rebuilt"], required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    MODE = a.mode
    os.makedirs(a.out, exist_ok=True)
    res = dict(prereg="ADDENDUM-4 §4a 62c0cd67", mode=MODE)
    res["feat_s1"] = stage_feat_s1(a.out)
    json.dump(res, open(a.out + "/gate3.json", "w"), indent=1, default=str)
    res["net015"] = stage_net(a.out)
    json.dump(res, open(a.out + "/gate3.json", "w"), indent=1, default=str)
    res["map"] = stage_map(a.out, "ho3bg3" + MODE[0])
    res["compare"] = compare(a.out)
    json.dump(res, open(a.out + "/gate3.json", "w"), indent=1, default=str)
    log.info("GATE3 %s %s", MODE, json.dumps(res["compare"]))
    # don dia (Oracle con ~1.5G): giu json + pred_s1; xoa bins/net015 sau khi da so
    for d in ("net015", "bins"):
        for f in glob.glob(os.path.join(a.out, d, "*.bin")):
            res.setdefault("cleaned_sha256", {})[d + "/" + os.path.basename(f)] = sha256f(f)
            os.remove(f)
    json.dump(res, open(a.out + "/gate3.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
