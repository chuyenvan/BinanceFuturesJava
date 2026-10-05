#!/usr/bin/env python3
"""SELECTOR_ABLATION — sinh file DIEM selector thay the (bins predict_wf_*.bin) cho B0 (G2+FLAT3).

Pre-reg: docs/prereg/PREREG_SELECTOR_ABLATION.md. KHONG sua .java. Sim doc diem selector tu funding.bin, dung lai
tu 18 file bins `predict_wf_*.bin` (26 B/rec big-endian `>q h 4f`: ts, symId, p4h,p12h,p24h,p72h; Java dung
`symbolPred = 1 - p0`, lay K phan tu symbolPred THAP nhat = p0 CAO nhat). Moi arm CHI doi coin nao nhan gia tri nao
trong CUNG moc ts: giu nguyen tap (ts,symId), thu tu record, va MULTISET bo-4 gia tri cua moi ts
(=> admission/nguong gate theo multiset giu nguyen, G5).
  P0  = bins goc (khong bien doi) -> phai ra sha 407e2aba..., sim parity md5 650c386f.
  R<s>= hoan vi ngau nhien bo-4 gia tri giua cac symbol TRONG CUNG ts (np.random.default_rng(s), s=42/7/13,
        file sort ten).
  L   = gan p0 giam dan (kem 3 gia tri cung dong) cho symbol theo quoteVol 24h giam dan (the: symId tang dan);
        quoteVol 24h = tong quoteVol 1m cac gio UTC tron [F-24h, F) voi F = floor_gio(ts) <= ts (CAUSAL).
Dong NaN p0 (Java bo) giu nguyen vi tri, khong tham gia hoan vi.

Lenh (Oracle):
  qv     [--workers 3]          Aerospike test.kline_1m_opt -> quoteVol GIO UTC theo symbol (CACHE/qvh/YYYYMM.parquet)
  liq                            -> CACHE/liq/liqrank_<fold>.npy (int16, hang thanh khoan trong ts, 0 = lon nhat)
                                    + CACHE/liq/qv24_<fold>.npy (float64, chi de sanity)
  gen    --arm A --out DIR [--src DIR ...] [--liq DIR]   sinh 18 file + in sha256
  sanity                          kiem: cung tap ts x sym, multiset moi ts giu nguyen, seed khac => thu tu khac, L causal
Ham `gen_arm(...)` duoc kernel Kaggle goi lai y nguyen (helper nhung base64) — sha phai trung ban Oracle.
"""
import argparse
import glob
import hashlib
import json
import logging
import os
import sys
import time

import numpy as np

log = logging.getLogger("sel_abl")
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
PCOLS = ("p0", "p1", "p2", "p3")
H = 3600000
SEEDS = {"R42": 42, "R7": 7, "R13": 13}
ARMS = ("P0", "R42", "R7", "R13", "L")
CACHE = "/home/ubuntu/claude_master/1003/sa"
SRC = ["/home/ubuntu/predwf_map_s1a2_x1", "/home/ubuntu/kaggle_sim/s3moc21"]
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
SHA_P0 = "407e2abab3053a39a51dcb9f331d063b3e67196bf608ae061aee444cd2841ca5"
H0_MS = 1625011200000          # 2021-06-30 00:00 UTC = gio dau cua luoi quoteVol gio
H0_MS = 1624838400000          # 2021-06-28 00:00 UTC (ghi de dong tren: luoi bat dau som hon tick dau >= 24h)


def sha256_concat(paths):
    h = hashlib.sha256()
    for p in paths:
        with open(p, "rb") as f:
            for b in iter(lambda: f.read(1 << 22), b""):
                h.update(b)
    return h.hexdigest()


def src_files(src_dirs):
    fs = []
    for d in src_dirs:
        fs += glob.glob(os.path.join(d, "predict_wf_*.bin"))
    fs = sorted(fs, key=os.path.basename)
    names = [os.path.basename(f) for f in fs]
    if len(fs) != 18 or len(set(names)) != 18:
        raise SystemExit("SA_FAIL: can dung 18 file bins khac ten, co %d (%s)" % (len(fs), names))
    return fs


def read_rec(path):
    return np.fromfile(path, dtype=REC)


def permute_rows(a, src, dst):
    """Gan bo-4 gia tri cua dong src[i] cho dong dst[i]; ts/sym/thu tu record giu nguyen."""
    out = a.copy()
    for c in PCOLS:
        v = a[c]
        nv = v.copy()
        nv[dst] = v[src]
        out[c] = nv
    return out


def transform(a, arm, rng=None, liqrank=None):
    """Tra ve mang record moi cho 1 file. CHI hoan vi trong CUNG ts, chi tren dong p0 khong NaN."""
    if arm == "P0":
        return a
    ts = a["ts"].astype(np.int64)
    p0 = a["p0"].astype(np.float64)
    ok = np.isfinite(p0)
    idx = np.arange(len(a))
    # dong NaN: dat khoa ts rieng (-1 - idx) de khong bao gio tron vao nhom that
    key = np.where(ok, ts, -1 - idx)
    if arm in SEEDS:
        u = rng.random(len(a))                       # luon rut du n so (ke ca dong NaN) => tat dinh theo file
        src = np.lexsort((u, key))                   # trong moi ts: thu tu NGAU NHIEN
        dst = np.lexsort((idx, key))                 # trong moi ts: thu tu record
    elif arm == "L":
        src = np.lexsort((idx, -p0, key))            # trong moi ts: p0 GIAM dan (the: thu tu record)
        dst = np.lexsort((a["sym"].astype(np.int64), liqrank.astype(np.int64), key))  # thanh khoan giam dan
    else:
        raise SystemExit("SA_FAIL arm %s" % arm)
    return permute_rows(a, src, dst)


def gen_arm(arm, files, out_dir, liq_dir=None):
    """Sinh 18 file cho arm vao out_dir. Tra (sha256_concat, list path)."""
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(SEEDS[arm]) if arm in SEEDS else None
    outs = []
    for f in files:
        nm = os.path.basename(f)
        a = read_rec(f)
        lr = None
        if arm == "L":
            lr = np.load(os.path.join(liq_dir, "liqrank_%s.npy" % nm[len("predict_wf_"):-4]))
            if len(lr) != len(a):
                raise SystemExit("SA_FAIL liqrank len %s %d != %d" % (nm, len(lr), len(a)))
        b = transform(a, arm, rng=rng, liqrank=lr)
        o = os.path.join(out_dir, nm)
        b.tofile(o)
        outs.append(o)
    sha = sha256_concat(outs)
    log.info("GEN arm=%s files=%d sha256=%s -> %s", arm, len(outs), sha, out_dir)
    return sha, outs


# ───────────────────────── stage qv: Aerospike 1m -> quoteVol GIO UTC ─────────────────────────
def _qv_month(ym):
    import aerospike
    import cramjam
    import pandas as pd
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from short_state_0sim import parse_all_min      # {sym_bytes: (close, quoteVol_1m)}
    fp = os.path.join(CACHE, "qvh", "%s.parquet" % ym)
    if os.path.exists(fp):
        return ym, -1, 0.0
    t0 = time.time()
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    mo = pd.Period(ym, freq="M")
    acc, nmin = {}, {}
    nrec_tot = 0
    for d in pd.date_range(mo.start_time, mo.end_time.normalize(), freq="D"):
        base = d + pd.Timedelta(hours=7)                 # key GMT+7 = phut MO; 00:00 UTC -> 07:00
        keys = [("test", "kline_1m_opt", (base + pd.Timedelta(minutes=k)).strftime("%Y%m%d-%H%M"))
                for k in range(1440)]
        recs = cli.batch_read(keys).batch_records
        for k, rr in enumerate(recs):
            if rr.result != 0 or rr.record is None:
                continue
            b = rr.record[2]
            if not b or "data" not in b:
                continue
            kstr = rr.key[2] if (rr.key is not None and len(rr.key) > 2) else None
            if kstr is not None and kstr != keys[k][2]:
                raise SystemExit("SA_FAIL thu tu batch_read lech %s vs %s" % (kstr, keys[k][2]))
            nrec_tot += 1
            hour_ms = int((d + pd.Timedelta(minutes=k)).value // 10**6) // H * H
            for s, (_c, v) in parse_all_min(bytes(dec(b["data"]))).items():
                kk = (hour_ms, s)
                acc[kk] = acc.get(kk, 0.0) + float(v)
                nmin[kk] = nmin.get(kk, 0) + 1
    cli.close()
    rows = [(h_, s.decode(), q, nmin[(h_, s)]) for (h_, s), q in acc.items()]
    df = pd.DataFrame(rows, columns=["hour_ms", "sym", "qv", "nmin"])
    df.to_parquet(fp, index=False)
    return ym, nrec_tot, time.time() - t0


def stage_qv(workers):
    import pandas as pd
    from multiprocessing import Pool
    os.makedirs(os.path.join(CACHE, "qvh"), exist_ok=True)
    months = [p.strftime("%Y%m") for p in pd.period_range("2021-06", "2025-12", freq="M")]
    with Pool(workers) as pool:
        for ym, nrec, secs in pool.imap_unordered(_qv_month, months):
            log.info("qv %s phut_co_du_lieu=%d %.0fs", ym, nrec, secs)


def load_hourly():
    """-> (C cumsum [nh+1, nsym] float64, sym2col dict, nh). Hang k = gio H0 + k*H."""
    import pandas as pd
    fs = sorted(glob.glob(os.path.join(CACHE, "qvh", "*.parquet")))
    q = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    syms = sorted(q["sym"].unique())
    s2c = {s: i for i, s in enumerate(syms)}
    hmax = int(q["hour_ms"].max())
    nh = (hmax - H0_MS) // H + 1
    M = np.zeros((nh, len(syms)), dtype=np.float64)
    k = ((q["hour_ms"].to_numpy(np.int64) - H0_MS) // H)
    keep = k >= 0
    np.add.at(M, (k[keep], q["sym"].map(s2c).to_numpy()[keep]), q["qv"].to_numpy(float)[keep])
    C = np.vstack([np.zeros((1, len(syms))), np.cumsum(M, axis=0)])
    log.info("hourly qv: %d gio x %d sym, %d file thang, hour_max=%s", nh, len(syms), len(fs),
             pd.to_datetime(hmax, unit="ms"))
    return C, s2c, nh


# ───────────────────────── stage liq: hang thanh khoan trong ts (CAUSAL) ─────────────────────────
def qv24_for(ts, sym, C, s2c, id2name):
    """quoteVol cac gio tron [F-24h, F), F = floor_gio(ts). Tra (qv24, k_end) ; k_end = chi so gio F (exclusive)."""
    F = (ts // H) * H
    kF = (F - H0_MS) // H                       # so gio truoc F ke tu H0 => C[kF] = tong gio < F
    if (kF - 24 < 0).any():
        raise SystemExit("SA_FAIL: co tick ma cua so 24h truoc H0")
    if (kF > C.shape[0] - 1).any():
        raise SystemExit("SA_FAIL: co tick vuot luoi qv (thieu thang)")
    us, inv = np.unique(sym, return_inverse=True)
    col = np.array([s2c.get(id2name.get(int(s), ""), -1) for s in us], dtype=np.int64)
    c = col[inv]
    q = np.zeros(len(ts), dtype=np.float64)
    m = c >= 0
    q[m] = C[kF[m], c[m]] - C[kF[m] - 24, c[m]]
    return q, kF


def rank_in_ts(ts, sym, qv):
    """hang 0..n-1 trong moi ts theo qv GIAM dan, the: symId TANG dan."""
    o = np.lexsort((sym.astype(np.int64), -qv, ts))
    tso = ts[o]
    start = np.r_[0, np.flatnonzero(np.diff(tso)) + 1]
    grp_start = np.repeat(start, np.diff(np.r_[start, len(tso)]))
    r = np.empty(len(ts), dtype=np.int64)
    r[o] = np.arange(len(ts)) - grp_start
    return r


def stage_liq():
    import pandas as pd
    C, s2c, nh = load_hourly()
    mp = pd.read_csv(MAP)
    id2name = dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))
    os.makedirs(os.path.join(CACHE, "liq"), exist_ok=True)
    cov = {}
    for f in src_files(SRC):
        nm = os.path.basename(f)[len("predict_wf_"):-4]
        a = read_rec(f)
        ts = a["ts"].astype(np.int64)
        sym = a["sym"].astype(np.int64)
        q, kF = qv24_for(ts, sym, C, s2c, id2name)
        r = rank_in_ts(ts, sym, q)
        if r.max() > 32767:
            raise SystemExit("SA_FAIL rank > int16")
        np.save(os.path.join(CACHE, "liq", "liqrank_%s.npy" % nm), r.astype(np.int16))
        np.save(os.path.join(CACHE, "liq", "qv24_%s.npy" % nm), q)
        cov[nm] = dict(n=int(len(a)), frac_qv_pos=float((q > 0).mean()),
                       frac_unmapped=float(np.mean([id2name.get(int(s)) is None for s in np.unique(sym)])),
                       max_window_end_minus_ts_min=float(((kF * H + H0_MS) - ts).max() / 60000.0))
        log.info("liq %s n=%d qv>0=%.4f", nm, len(a), cov[nm]["frac_qv_pos"])
    json.dump(cov, open(os.path.join(CACHE, "liq", "coverage.json"), "w"), indent=1)


# ───────────────────────── sanity ─────────────────────────
def _spearman_in_ts(ts, x, y):
    """trung binh Spearman trong ts (nhom >= 5 dong)."""
    import pandas as pd
    d = pd.DataFrame({"ts": ts, "x": x, "y": y})
    d["rx"] = d.groupby("ts")["x"].rank()
    d["ry"] = d.groupby("ts")["y"].rank()
    g = d.groupby("ts")
    n = g.size()
    c = g.apply(lambda z: np.corrcoef(z.rx, z.ry)[0, 1] if len(z) >= 5 and z.rx.std() > 0 and z.ry.std() > 0 else np.nan)
    c = c[n >= 5]
    return float(np.nanmean(c)), int(c.notna().sum())


def stage_sanity(out_root, sample_files=("20220101", "20240701", "20251001")):
    """Kiem tren file da sinh o out_root/<arm>/ (gen truoc). Ghi CACHE/sanity.json."""
    import pandas as pd
    res = {"arms": {}, "checks": {}}
    files = src_files(SRC)
    res["sha_src"] = sha256_concat(files)
    res["checks"]["src_sha_eq_P0"] = res["sha_src"] == SHA_P0
    ok_all = True
    for arm in ARMS:
        d = os.path.join(out_root, arm)
        outs = sorted(glob.glob(os.path.join(d, "predict_wf_*.bin")))
        r = dict(sha=sha256_concat(outs), files=len(outs), per_file={})
        for f in files:
            nm = os.path.basename(f)
            a, b = read_rec(f), read_rec(os.path.join(d, nm))
            same_keys = bool(len(a) == len(b) and np.array_equal(a["ts"], b["ts"]) and np.array_equal(a["sym"], b["sym"]))
            # multiset bo-4 gia tri trong ts: sort (ts, p0, p1, p2, p3) cua 2 ben phai bang nhau tung byte
            def srt(x):
                o = np.lexsort((x["p3"], x["p2"], x["p1"], x["p0"], x["ts"]))
                y = x[o]
                return b"".join(y[c].tobytes() for c in ("ts", "p0", "p1", "p2", "p3"))
            same_ms = srt(a) == srt(b)
            nan_same = bool(np.array_equal(np.isnan(a["p0"].astype(float)), np.isnan(b["p0"].astype(float))))
            frac_changed = float(np.mean(a["p0"] != b["p0"]))
            pf = dict(n=int(len(a)), same_keys=same_keys, same_multiset=bool(same_ms), nan_pos_same=nan_same,
                      n_nan=int(np.isnan(a["p0"].astype(float)).sum()), frac_p0_changed=frac_changed)
            if nm[11:19] in sample_files:
                pf["spearman_vs_P0"], pf["n_ts"] = _spearman_in_ts(a["ts"].astype(np.int64),
                                                                   a["p0"].astype(float), b["p0"].astype(float))
            r["per_file"][nm] = pf
            ok_all &= same_keys and bool(same_ms) and nan_same
        res["arms"][arm] = r
        log.info("SANITY %s sha=%s files=%d", arm, r["sha"][:16], r["files"])
    res["checks"]["all_same_keys_multiset_nan"] = bool(ok_all)
    res["checks"]["P0_identity"] = res["arms"]["P0"]["sha"] == SHA_P0
    # seed khac => thu tu khac
    RP = (("R42", "R7"), ("R42", "R13"), ("R7", "R13"))
    for x, y in RP:
        nm = "predict_wf_20240701.bin"
        a = read_rec(os.path.join(out_root, x, nm))
        b = read_rec(os.path.join(out_root, y, nm))
        res["checks"]["diff_%s_%s_frac_p0" % (x, y)] = float(np.mean(a["p0"] != b["p0"]))
    res["checks"]["seeds_differ"] = all(res["checks"]["diff_%s_%s_frac_p0" % p] > 0.5
                                        for p in RP)
    res["checks"]["sha_distinct"] = len({res["arms"][k]["sha"] for k in ARMS}) == len(ARMS)
    # L: causal + tai tinh doc lap 30 dong ngau nhien tu parquet gio
    res["L_causal"] = _check_L_causal()
    res["checks"]["L_causal_recompute_ok"] = res["L_causal"]["ok"]
    res["L_coverage"] = json.load(open(os.path.join(CACHE, "liq", "coverage.json")))
    res["checks"]["L_order_follows_liq"] = _check_L_order(out_root)
    json.dump(res, open(os.path.join(CACHE, "sanity.json"), "w"), indent=1)
    log.info("SANITY checks %s", json.dumps(res["checks"]))
    return res


def _check_L_causal(nsamp=30, seed=7):
    import pandas as pd
    mp = pd.read_csv(MAP)
    id2name = dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))
    rng = np.random.default_rng(seed)
    files = src_files(SRC)
    out, ok = [], True
    for i in range(nsamp):
        f = files[int(rng.integers(0, len(files)))]
        nm = os.path.basename(f)[len("predict_wf_"):-4]
        a = read_rec(f)
        j = int(rng.integers(0, len(a)))
        ts, sid = int(a["ts"][j]), int(a["sym"][j])
        q24 = float(np.load(os.path.join(CACHE, "liq", "qv24_%s.npy" % nm))[j])
        F = ts // H * H
        lo, hi = F - 24 * H, F
        name = id2name.get(sid, "")
        tot, hmax = 0.0, None
        for ym in sorted({pd.Timestamp(lo, unit="ms").strftime("%Y%m"), pd.Timestamp(hi - 1, unit="ms").strftime("%Y%m")}):
            q = pd.read_parquet(os.path.join(CACHE, "qvh", "%s.parquet" % ym))
            q = q[(q.sym == name) & (q.hour_ms >= lo) & (q.hour_ms < hi)]
            tot += float(q.qv.sum())
            if len(q):
                hmax = max(hmax or 0, int(q.hour_ms.max()))
        good = abs(tot - q24) <= 1e-6 * max(1.0, abs(tot)) and (hmax is None or hmax + H <= ts)
        ok &= good
        out.append(dict(file=nm, ts=ts, sym=name, qv24_arr=q24, qv24_recompute=tot,
                        last_hour_end_minus_ts_min=None if hmax is None else (hmax + H - ts) / 60000.0, ok=bool(good)))
    return dict(ok=bool(ok), samples=out)


def _check_L_order(out_root):
    """Trong moi ts cua 1 file mau: p0 cua arm L phai GIAM (khong tang) theo hang thanh khoan."""
    nm = "20240701"
    b = read_rec(os.path.join(out_root, "L", "predict_wf_%s.bin" % nm))
    lr = np.load(os.path.join(CACHE, "liq", "liqrank_%s.npy" % nm)).astype(np.int64)
    ts = b["ts"].astype(np.int64)
    p0 = b["p0"].astype(np.float64)
    o = np.lexsort((lr, ts))
    same = np.diff(ts[o]) == 0
    return bool(np.all(np.diff(p0[o])[same] <= 0))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["qv", "liq", "gen", "sanity"])
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--arm", choices=ARMS)
    ap.add_argument("--out", default=os.path.join(CACHE, "bins"))
    ap.add_argument("--src", action="append", default=None)
    ap.add_argument("--liq", default=os.path.join(CACHE, "liq"))
    a = ap.parse_args()
    if a.cmd == "qv":
        stage_qv(a.workers)
    elif a.cmd == "liq":
        stage_liq()
    elif a.cmd == "gen":
        arms = [a.arm] if a.arm else list(ARMS)
        shas = {}
        for arm in arms:
            shas[arm] = gen_arm(arm, src_files(a.src or SRC), os.path.join(a.out, arm), a.liq)[0]
        json.dump(shas, open(os.path.join(a.out, "sha256.json"), "w"), indent=1)
    else:
        stage_sanity(a.out)


if __name__ == "__main__":
    main()
