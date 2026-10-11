#!/usr/bin/env python3
"""HO4-P1 (ADDENDUM-6 af6d6c94) chuoi Python ha nguon — chay TRONG kernel Kaggle (cache Oracle <= 500 MB).
Mode det (lat DEV S, P3-DET + P3-DEV) | y26 (2026, S4). Dau vao: output kernel exporter/OI (kernel_sources), dataset code
`ho4p1-code` (module repo + model dong bang), funding-oi-percoin (OI ghim), ho26-pred-s*, sim-ho26a-bundle (+ DEV refs cho det).
KHONG in gia tri/phan phoi 2026: chi dem/khoang ts/NaN/md5. Usage (trong kernel): ho4p1_chain.py <cfg.json>"""
import glob, gzip, hashlib, json, logging, os, shutil, struct, subprocess, sys, time
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho4p1ch")
CFG = json.load(open(sys.argv[1]))
IN, WORK = "/kaggle/input", os.environ.get("HO4P1_WORK", "/kaggle/working")
OUT = WORK + "/out"
CODE = CFG["code_dir"]
os.makedirs(OUT, exist_ok=True)
H, Q = 3600000, 900000
RES = dict(mode=CFG["mode"], tag=CFG["tag"], prereg="ADDENDUM-6 af6d6c94", steps={})


def save():
    json.dump(RES, open(WORK + "/result.json", "w"), indent=1, default=str)


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sha256f(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def find(pat, src):
    """file trong /kaggle/input co duong dan chua '/<src>/' (dataset hoac kernel output); ca ban .gz va ban da giai nen."""
    c = sorted(p for p in glob.glob(IN + "/**/" + pat, recursive=True) if ("/" + src + "/") in p and os.path.isfile(p))
    return c


def one(pat, src):
    c = find(pat, src)
    assert len(c) >= 1, ("MISSING", pat, src)
    return c[0]


# ---------------- moi truong module ----------------
os.environ["OI_FILE"] = "/tmp/oi_comb.bin"
os.environ["MAP_CSV"] = CODE + "/symbol_map_863.csv"
os.environ["SEL1M_CODE"] = CODE
os.makedirs("/home/ubuntu/ledger", exist_ok=True)
if not os.path.lexists("/home/ubuntu/sel1m_code"):
    os.symlink(CODE, "/home/ubuntu/sel1m_code")
sys.path.insert(0, CODE)
import g015_net_train as G  # noqa: E402
import ho1_net015_predict as HN  # noqa: E402
import ho2_net015_onnx as H2  # noqa: E402
import ho1_featv2_window as FW  # noqa: E402
import ho1_s1_2026 as S1  # noqa: E402
H2.ONNX = CODE + "/g015x26_f15_cut20251001.onnx"
S1.MAP = CODE + "/symbol_map_781.csv"
assert G.OI_FILE == "/tmp/oi_comb.bin" and G.MAP_CSV == CODE + "/symbol_map_863.csv"
V3 = json.load(open(CODE + "/v3full.json"))
_m863 = pd.read_csv(CODE + "/symbol_map_863.csv")
_cnt = _m863.groupby("symId").symbol.nunique()
DUP_IDS = {int(i) for i in _cnt[_cnt > 1].index}   # §6.2a (ADDENDUM-6): id dung chung boi 2 symbol trong mapper -> loai
RES["dup_ids"] = {int(i): sorted(_m863[_m863.symId == i].symbol) for i in sorted(DUP_IDS)}
assert len(V3) == 33
ODT = G.OI_DT
DT = HN.DT
REC = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])
MDT = np.dtype([("ts", ">i8"), ("v", "V12")])
CDT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
SHA = CFG["model_sha"]
for nm, sh in SHA.items():
    assert sha256f(CODE + "/" + nm) == sh, ("SHA model", nm)
RES["model_sha_ok"] = True


def gz_or_raw(p):
    return gzip.open(p, "rb").read() if p.endswith(".gz") else open(p, "rb").read()


# ---------------- OI ghep: ghim ts < CUT + dung lai ts >= CUT ----------------
def build_oi(lo, cut, hi):
    pin = one("oi_percoin_full.bin", "funding-oi-percoin")
    assert sha256f(pin) == CFG["pin_sha"], "OI ghim sha"
    n = os.path.getsize(pin) // ODT.itemsize
    parts = []
    for k in range(0, n, 10_000_000):
        c = np.fromfile(pin, dtype=ODT, count=min(10_000_000, n - k), offset=k * ODT.itemsize)
        t = c["ts"].astype(np.int64)
        parts.append(c[(t >= lo) & (t < cut)].copy())
    a = np.concatenate(parts); del parts
    rp = one("oi_rebuilt.bin*", CFG["oi_src"])
    raw = gz_or_raw(rp)
    RES["steps"]["oi_rebuilt_md5_raw"] = hashlib.md5(raw).hexdigest()
    r = np.frombuffer(raw, dtype=ODT)
    t = r["ts"].astype(np.int64)
    b = r[(t >= cut) & (t < hi)]
    out = np.concatenate([a, b]).astype(ODT)
    out.tofile(G.OI_FILE)
    RES["steps"]["oi"] = dict(pin_rows=int(len(a)), rebuilt_rows=int(len(b)), lo=lo, cut=cut, hi=hi, md5=md5f(G.OI_FILE))
    log.info("OI ghep %s", RES["steps"]["oi"])
    del raw, r, a, b, out


# ---------------- store gate ----------------
def load_gate(path, lo, hi):
    d = pd.read_csv(path, usecols=["timestamp"] + V3, dtype={c: np.float32 for c in V3})
    d["timestamp"] = d["timestamp"].astype(np.int64)
    d = d[(d.timestamp >= lo) & (d.timestamp < hi)].drop_duplicates("timestamp", keep="last")
    return d.sort_values("timestamp").reset_index(drop=True)


def p15_of(model, X):
    import xgboost as xgb
    b = xgb.Booster()
    b.load_model(model)
    return b.predict(xgb.DMatrix(X)).astype(np.float32)


def read_pred(p):
    raw = open(p, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    assert 4 + 16 * n == len(raw)
    return raw, np.frombuffer(raw[4:], dtype=REC)


def write_pred(path, pre_bytes, ts, p15, suf_bytes=b""):
    b = np.zeros(len(ts), dtype=REC)
    b["ts"] = ts; b["p15"] = p15.astype(">f4"); b["risk"] = np.float32(0.0)
    n = (len(pre_bytes) + len(suf_bytes)) // 16 + len(ts)
    with open(path, "wb") as f:
        f.write(struct.pack(">i", n)); f.write(pre_bytes); f.write(b.tobytes()); f.write(suf_bytes)
    a = read_pred(path)[1]["ts"].astype(np.int64)
    assert (np.diff(a) > 0).all(), "pred ts khong tang"
    return md5f(path)


def read_market(p):
    with open(p, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        return np.frombuffer(f.read(20 * n), dtype=MDT)


def write_market(path, parts):
    out = np.concatenate(parts).astype(MDT)
    t = out["ts"].astype(np.int64)
    assert (np.diff(t) > 0).all(), "market ts khong tang"
    with open(path, "wb") as f:
        f.write(struct.pack(">i", len(out))); f.write(out.tobytes())
    v = np.frombuffer(out["v"].tobytes(), dtype=">f4").reshape(-1, 3)
    return dict(n=int(len(out)), md5=md5f(path), nan=int(np.isnan(v.astype(np.float64)).sum()))


# ---------------- net015: Tool1 + OI (= HN.build_rows; nguon Tool1 co cua so thoi gian rieng de khong trung khoa) ----------------
def rows_t1(sources, lo, hi):
    """sources = [(file, t_from, t_to)] — dong Tool1 cua file chi lay ts in [t_from, t_to) ∩ [lo, hi)."""
    smap = pd.read_csv(G.MAP_CSV)
    aa = []
    for p, a0, a1 in sources:
        x = G.read_tool1(p, grid_ms=G.GRID_MS)
        xt = x["ts"].astype(np.int64)
        aa.append(x[(xt >= max(lo, a0)) & (xt < min(hi, a1))].copy())
        del x, xt
    a = np.concatenate(aa); del aa
    dmask = np.isin(a["sym"].astype(np.int64), np.array(sorted(DUP_IDS), np.int64))
    n_dup_rows = int(dmask.sum())
    a = a[~dmask]                                   # §6.2a: symId mapper mo ho (2 symbol/1 id) -> loai
    k = a["ts"].astype(np.int64) * 10000 + a["sym"].astype(np.int64)
    assert len(np.unique(k)) == len(k), "trung khoa (ts,sym) Tool1"
    aoc = HN.read_oi(lo - G.OI_TOL, hi)
    t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32), "ridx": np.arange(len(a), dtype=np.int64)})
    o = pd.DataFrame({"ts": aoc["ts"].astype(np.int64), "symId": aoc["sym"].astype(np.int32)})
    O = np.asarray(aoc["oi"], dtype=np.float32)
    for j, nm in enumerate(G.OI_NAMES):
        o[nm] = O[:, j]
    del aoc, O
    t = t.sort_values("ts", kind="stable").reset_index(drop=True)
    o = o.sort_values(["ts", "symId"], kind="stable").reset_index(drop=True)
    mg = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=G.OI_TOL)
    del t, o
    mg = mg.merge(smap, on="symId", how="left").dropna(subset=["symbol"])
    mg = mg.sort_values(["ts", "symId"], kind="stable").reset_index(drop=True)
    X = np.empty((len(mg), G.NF), dtype=np.float32)
    X[:, :40] = a["f"][mg["ridx"].to_numpy()]
    X[:, 40:] = mg[G.OI_NAMES].to_numpy(np.float32)
    ts, sym = mg["ts"].to_numpy(np.int64), mg["symId"].to_numpy(np.int32)
    info = dict(n_tool1=int(len(a)), n_rows=int(len(mg)), n_drop_dup_id_rows=n_dup_rows, oi_nan_rows=int(np.isnan(X[:, 40:]).all(axis=1).sum()),
                ts_min=int(ts.min()), ts_max=int(ts.max()))
    del a, mg
    return X, ts, sym, info


def net015_fold(sources, lo, hi, path):
    X, ts, sym, info = rows_t1(sources, lo, hi)
    p = H2.predict(X); del X
    G.write_bin(path, ts, sym, p)
    info.update(nan=int(np.isnan(p).sum()), md5=md5f(path), sha256=sha256f(path), lo=lo, hi=hi)
    assert info["nan"] == 0 and lo <= info["ts_min"] and info["ts_max"] < hi
    return info


# ---------------- feat_v2 KEEP9 ----------------
def closes_frame(c_new, dev_part):
    """dev_part=True: CLOSES DEV ghim (duoi cat san) <= ts max DEV + Vision 1m sau do (§6.5); False: chi Vision 1m (det)."""
    b = c_new
    if dev_part:
        a = np.fromfile(CODE + "/closes_dev_tail.bin", dtype=CDT)
        dmax = int(a["ts"].astype(np.int64).max())
        b = b[b["ts"].astype(np.int64) > dmax]
        src = [a, b]
    else:
        src = [b]
    df = pd.concat([pd.DataFrame({"ts": x["ts"].astype(np.int64), "sym": x["sym"].astype(np.int32), "c": x["c"].astype(np.float64)}) for x in src])
    df = df[(df.ts >= FW.T_START) & (df.ts <= FW.T_END)]
    P = df.pivot(index="ts", columns="sym", values="c").sort_index()
    hours = pd.Index(np.arange(P.index.min(), P.index.max() + H, H))
    return P.reindex(hours)


def featv2(c_new, dev_part, t_start, t_end, keep_from, path):
    FW.T_START, FW.T_END, FW.KEEP_FROM = t_start, t_end, keep_from
    FW.OI = G.OI_FILE
    FW.DEV_UNI.clear(); FW.DEV_UNI.update(json.load(open(CODE + "/dev_uni.json")))
    P = closes_frame(c_new, dev_part)
    long = FW.features(P)
    long.to_parquet(path, index=False)
    return long, dict(n=int(len(long)), md5=md5f(path), ts_min=int(long.ts.min()), ts_max=int(long.ts.max()))


def closes_merge(parts):
    """parts = [(file, t_from, t_to)] -> mang CDT ghep, sap (ts, sym) — gio dong ts thuoc [t_from, t_to)."""
    out = []
    for p, a0, a1 in parts:
        c = np.fromfile(p, dtype=CDT)
        t = c["ts"].astype(np.int64)
        out.append(c[(t >= a0) & (t < a1)])
    c = np.concatenate(out)
    k = c["ts"].astype(np.int64) * 10000 + c["sym"].astype(np.int64)
    assert len(np.unique(k)) == len(k)
    return c


# ---------------- pool + S1 + bins ----------------
def open_ticks(ts, p15, lo, hi):
    m = (ts >= lo) & (ts < hi) & (ts % Q == 0)
    return ts[m][p15[m].astype(np.float32) >= np.float32(0.008)]


def pool_s1(ts42, p42, quarters, F, s1_model, name):
    """quarters = [(lo, hi, [label files])] — tick cua quy chi dung nhan cua kernel quy do."""
    A = []
    for lo, hi, files in quarters:
        A.append(S1.avail_pool(open_ticks(ts42, p42, lo, hi), files))
    A = pd.concat(A).drop_duplicates(["ts", "sym"]).sort_values(["ts", "sym"]).reset_index(drop=True)
    S, cov = S1.score(s1_model, A, F)
    S = S[["ts", "sym", "score"]].sort_values(["ts", "sym"]).reset_index(drop=True)
    p = "/home/ubuntu/ledger/pred_%s.parquet" % name
    S.to_parquet(p, index=False)
    shutil.copyfile(p, OUT + "/s1_%s.parquet" % name)
    return dict(pool=int(len(A)), ticks=int(A.ts.nunique()), feat_cov=cov, nan_score=int(S.score.isna().sum()),
                md5=md5f(OUT + "/s1_%s.parquet" % name))


def bins(name, cuts, gdir, bdir):
    env = dict(os.environ, X1_CUTS=" ".join(cuts), X1_G015_DIR=gdir)
    os.makedirs(bdir, exist_ok=True)
    r = subprocess.run([sys.executable, "-u", CODE + "/x1_build_map.py", name, bdir], cwd=CODE, env=env, capture_output=True, text=True)
    assert r.returncode == 0 and "MAP_OK" in r.stdout, r.stdout[-800:] + r.stderr[-800:]
    out = {}
    for c in cuts:
        p = bdir + "/predict_wf_%s.bin" % c
        a = np.fromfile(p, dtype=DT)
        t = a["ts"].astype(np.int64)
        out[c] = dict(n=int(len(a)), md5=md5f(p), nan_p0=int(np.isnan(a["p0"].astype(np.float64)).sum()),
                      ts_min=int(t.min()), ts_max=int(t.max()), ts_nondecr=bool((np.diff(t) >= 0).all()))
    return out


def drop_syms(path, ids):
    a = np.fromfile(path, dtype=DT)
    m = ~np.isin(a["sym"].astype(np.int64), np.array(sorted(ids), np.int64))
    a[m].astype(DT).tofile(path)
    return dict(n_before=int(len(a)), n_dropped=int((~m).sum()), md5=md5f(path))


def manifest():
    man = {}
    for p in sorted(glob.glob(OUT + "/**/*", recursive=True)):
        if os.path.isfile(p) and not p.endswith("MANIFEST.json"):
            man[os.path.relpath(p, OUT)] = dict(md5=md5f(p), bytes=os.path.getsize(p))
    json.dump(man, open(OUT + "/MANIFEST.json", "w"), indent=0, sort_keys=True)
    RES["manifest"] = man
    save()


def mkd(p):
    os.makedirs(p, exist_ok=True)
    return p


def ms_utc(d):
    return int(pd.Timestamp(d, tz="UTC").value // 10**6)


# ---------------- mode det: lat DEV S (P3-DET) ----------------
def run_det():
    S_LO, S_HI, Q4 = 1751302800000, 1767200400000, 1759251600000
    U_Q4 = ms_utc("2025-10-01")                      # ranh file Tool1/nhan quy UTC
    src = CFG["det_src"]
    t0 = time.time()
    build_oi(ms_utc("2025-05-15"), S_LO, S_HI + 86400000)
    st = load_gate(one("gate_dev.csv*", src), S_LO, S_HI)
    ts = st.timestamp.to_numpy(np.int64)
    p42 = p15_of(CODE + "/gate_s42_cut20260101p15.json", st[V3].to_numpy(np.float32))
    raw, a = read_pred(one("pred.bin", "ho26-pred-s42"))
    pt = a["ts"].astype(np.int64)
    npre = int(np.searchsorted(pt, S_LO))
    RES["steps"]["gate_p15"] = dict(rows=int(len(st)), ts_min=int(ts.min()), ts_max=int(ts.max()), nan=int(np.isnan(p42).sum()),
                                    pred_md5=write_pred(mkd(OUT + "/pred_det_s42") + "/pred.bin", raw[4:4 + 16 * npre], ts, p42), n_pre=npre)
    save()
    base = read_market(one("market.bin", "sim-ho26a-bundle"))
    bt = base["ts"].astype(np.int64)
    new = read_market(one("market_rebuilt.bin", src))
    nt = new["ts"].astype(np.int64)
    RES["steps"]["market"] = write_market(OUT + "/market.bin", [base[bt < S_LO], new[(nt >= S_LO) & (nt < S_HI)], base[bt >= S_HI]])
    save()
    t1a, t1b = find("t1a/*.t1c*", src), find("t1b/*.t1c*", src)
    srcs = [(p, 0, U_Q4) for p in t1a] + [(p, U_Q4, 1 << 62) for p in t1b]
    os.makedirs(OUT + "/net015", exist_ok=True)
    RES["steps"]["net015"] = {c: net015_fold(srcs, lo, hi, OUT + "/net015/predict_wf_%s.bin" % c)
                              for c, lo, hi in (("20250701", S_LO, Q4), ("20251001", Q4, S_HI))}
    save()
    cl = closes_merge([(one("CLOSES_1H_vision1m.bin", src), 0, 1 << 62)])
    F, RES["steps"]["featv2"] = featv2(cl, False, ms_utc("2025-06-01"), ms_utc("2026-01-01"), S_LO - 24 * H, OUT + "/feat_v2.parquet")
    F = F[["ts", "sym"] + S1.KEEP].copy(); F["sym"] = F.sym.astype(np.int64)
    save()
    quarters = [(S_LO, Q4, find("laba/*.pb", src)), (Q4, S_HI, find("labb/*.pb", src))]
    RES["steps"]["s1"] = pool_s1(ts, p42, quarters, F, CODE + "/s1a2x1_cut20251001.json", "ho4p1det")
    save()
    RES["steps"]["bins"] = bins("ho4p1det", ["20250701", "20251001"], OUT + "/net015", OUT + "/bins")
    RES["secs"] = round(time.time() - t0)
    manifest()
    log.info("CHAIN_DET_DONE %s", json.dumps({k: (v.get("md5") if isinstance(v, dict) else None) for k, v in RES["steps"].items()}))


# ---------------- mode y26: 2026 (S4) ----------------
def run_y26():
    SEAL, A1, A2, END = 1767200400000, 1774976400000, 1782838800000, 1790787600000
    U1, U2 = ms_utc("2026-04-01"), ms_utc("2026-07-01")
    QS = CFG["q_src"]                                   # {"q1": slug, "q2": slug, "q3": slug}
    QB = [("q1", SEAL, A1), ("q2", A1, A2), ("q3", A2, END)]
    t0 = time.time()
    build_oi(ms_utc("2025-11-01"), SEAL, END + 3 * 86400000)
    # store gate ghep theo quy
    st = pd.concat([load_gate(one("gate.csv*", QS[q]), lo, hi) for q, lo, hi in QB]).reset_index(drop=True)
    ts = st.timestamp.to_numpy(np.int64)
    assert (np.diff(ts) > 0).all()
    X = st[V3].to_numpy(np.float32)
    RES["steps"]["gate"] = dict(rows=int(len(st)), ts_min=int(ts.min()), ts_max=int(ts.max()),
                                rows_q={q: int(((ts >= lo) & (ts < hi)).sum()) for q, lo, hi in QB},
                                nan_cells=int(np.isnan(X).sum()))
    preds = {}
    for s in CFG["seeds"]:
        p = p15_of(CODE + "/gate_s%d_cut20260101p15.json" % s, X)
        raw, a = read_pred(one("pred.bin", "ho26-pred-s%d" % s))
        pt = a["ts"].astype(np.int64)
        npre = int(np.searchsorted(pt, SEAL))
        pre = raw[4:4 + 16 * npre]
        md = write_pred(mkd(OUT + "/pred_s%d" % s) + "/pred.bin", pre, ts, p)
        preds[str(s)] = dict(md5=md, n_dev=npre, md5_dev_records=hashlib.md5(pre).hexdigest(), n_2026=int(len(ts)),
                             nan_2026=int(np.isnan(p).sum()))
        if s == 42:
            p42 = p
    RES["steps"]["pred"] = preds
    del X
    save()
    base = read_market(one("market.bin", "sim-ho26a-bundle"))
    bt = base["ts"].astype(np.int64)
    parts = [base[bt < SEAL]]
    for q, lo, hi in QB:
        m = read_market(one("market_rebuilt.bin", QS[q]))
        mt = m["ts"].astype(np.int64)
        parts.append(m[(mt >= lo) & (mt < hi)])
    RES["steps"]["market"] = write_market(OUT + "/market.bin", parts)
    RES["steps"]["market"]["n_dev"] = int((bt < SEAL).sum())
    RES["steps"]["market"]["md5_dev_records"] = hashlib.md5(base[bt < SEAL].tobytes()).hexdigest()
    save()
    tq = {q: find("t1/*.t1c*", QS[q]) for q in QS}
    folds = (("20260101", SEAL, A1, [(p, 0, 1 << 62) for p in tq["q1"]]),
             ("20260401", A1, A2, [(p, 0, U1) for p in tq["q1"]] + [(p, U1, 1 << 62) for p in tq["q2"]]),
             ("20260701", A2, END, [(p, 0, U2) for p in tq["q2"]] + [(p, U2, 1 << 62) for p in tq["q3"]]))
    os.makedirs(OUT + "/net015", exist_ok=True)
    RES["steps"]["net015"] = {c: net015_fold(srcs, lo, hi, OUT + "/net015/predict_wf_%s.bin" % c) for c, lo, hi, srcs in folds}
    save()
    cl = closes_merge([(one("CLOSES_1H_vision1m.bin", QS["q1"]), 0, A1), (one("CLOSES_1H_vision1m.bin", QS["q2"]), A1, A2),
                       (one("CLOSES_1H_vision1m.bin", QS["q3"]), A2, 1 << 62)])
    F, RES["steps"]["featv2"] = featv2(cl, True, ms_utc("2025-11-15"), ms_utc("2026-10-01"), SEAL - 24 * H, OUT + "/feat_v2_26.parquet")
    F = F[["ts", "sym"] + S1.KEEP].copy(); F["sym"] = F.sym.astype(np.int64)
    save()
    quarters = [(lo, hi, find("lab/*.pb", QS[q])) for q, lo, hi in QB]
    RES["steps"]["s1"] = pool_s1(ts, p42, quarters, F, CODE + "/s1a2x1_cut20251231.json", "ho4p1y26")
    save()
    cuts = ["20260101", "20260401", "20260701"]
    RES["steps"]["bins_raw"] = bins("ho4p1y26", cuts, OUT + "/net015", OUT + "/bins")
    # loai khoi giao dich: symbol co kline trong quy nhung khong co funding Vision (§6.2-3)
    mp = pd.read_csv(CODE + "/symbol_map_863.csv")
    s2i = dict(zip(mp.symbol, mp.symId))
    nof = set()
    for q in QS:
        nof |= set(json.load(open(one("universe_excl.json", QS[q])))["no_funding_vision"])
    ids = {int(s2i[s]) for s in nof if s in s2i} | DUP_IDS
    RES["steps"]["excl_no_funding"] = dict(symbols=sorted(nof), ids=sorted(ids))
    RES["steps"]["bins"] = {c: drop_syms(OUT + "/bins/predict_wf_%s.bin" % c, ids) for c in cuts}
    RES["secs"] = round(time.time() - t0)
    manifest()
    log.info("CHAIN_Y26_DONE secs=%s", RES["secs"])


if __name__ == "__main__":
    {"det": run_det, "y26": run_y26}[CFG["mode"]]()
