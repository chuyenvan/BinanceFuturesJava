#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dung OFFLINE buffer gate rolling (GRR1, run/gate_ratio_live.bin) cho shadow #2 K24 (phuong an G2).

Nguon (CHI DOC, ban sao keo tu 242 ve Oracle): storage/data/predictionSymbol/<day>/<ts>.features
(FundingMarketFeatures 45 feature, da qua PASS-2 CS + OI — dung mang vua cho vao model) va
storage/data/prediction/<day>/<ts> (PredictionResult.return15M = p15).

Cong thuc (khop live C3, DetectEntrySignal2TradeNormal.buildValueMap + LiveBuildMap.assign + LiveGateRollingRatio.threshold):
  pwin = net015(45 feature) tren toan uni; LiveBuildMap gan pwin giam dan theo hang S1 => coin hang k nhan
  pwin_(k) (thong ke thu tu k, giam dan) => sp_k = f32(1 - pwin_(k)) KHONG phu thuoc danh tinh S1.
  r_k = p15 / (max(DYN_MIN, sp_k / SCORE_BASE * DYN_MULT) * GATE_DYN_SCALE), k = 1..K (float32 nhu Java).
Sai khac khai ro: (1) coin LEGACY bi skip (khong dem hang) va coin S1=NaN (ngoai uni) KHONG tai tao duoc
  => tap hang co the lech 1; (2) tick live bo (S1 chua san sang / uni<20) chi bo duoc khi uni<20.
  Muc lech do bang lenh `validate` (K16 tai tao vs buffer K16 that cua 242, cung tick).

KET QUA 2026-10-05: tu 2026-10-01 13:00 (sau deploy G2+FLAT3 242) 99,7% tick 242 = top-16 tai tao bo 0..3
  hang (legacy) voi sai so < 1e-6; q(0.99995) cung tick: 242 = tai tao K16 (trung bit). Truoc deploy, buffer 242 chua
  r cua cau hinh cu (r lon hon ~6x) => KHONG dung de so.
KHONG ghi vao shadow: chi ghi --out (mac dinh ~/claude_master/1005/shadow2/buffer_k24.bin).
Usage:
  python3 build_gate_buffer_k24.py extract --data D --model M [--cache C] [--workers 3]
  python3 build_gate_buffer_k24.py validate --cache C --ref242 gate_ratio_live_k16.bin [--json J]
  python3 build_gate_buffer_k24.py build --cache C --k 24 --out OUT.bin [--ref242 BIN] [--json J]
"""
import argparse
import datetime as dt
import glob
import json
import logging
import os
import struct
import sys
import zlib
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_arm_check as GAC  # noqa: E402  read_grr1 / q_at (mirror GateRatioPersist / GateRatioBuffer)

LOG = logging.getLogger("build_gate_buffer_k24")
TZ = dt.timezone(dt.timedelta(hours=7))
DAY, HOUR = 86_400_000, 3_600_000
# EntryGate (src/main/java/.../tradecore/EntryGate.java:44-48) + env 242/shadow SIM_GATE_DYN_SCALE=1.55
DYN_MIN, SCORE_BASE, DYN_MULT = np.float32(0.26787), np.float32(0.15), np.float32(1.28760)
GS = np.float32(1.55)
PCT, DAYS = 0.999950829, 90
MAGIC = 0x47525231
TOPN = 40   # luu toi da 40 thong ke thu tu pwin moi tick (du cho K<=40)
FIELDS = ("btcMomentum1H btcMomentum4H btcMomentum24H btcDominance marketBreadthStrength rateDown15MAvg momentum1H "
          "momentum4H momentum24H rsi1H distFromLow24H volatilityShock basketMomentum15M basketMomentum1H "
          "basketMomentum24H basketRsi14 basketVolSpike coinFundingRate basketFundingAvg fundingRateAvg24H "
          "fundingRateTrend fundingPercentileCoin fundingZCoin fundingPersistence fundingSum24h fundingAbs volumeZCoin "
          "volumeTrend distFromHigh24H rangePosition24H atrSqueeze relStrengthBtc24H fundingRankCS volumeZRankCS "
          "momentumRankCS ret15m rvol15m volumeZ5m closePosRange15m wickRatio15m oiDelta24hCoin oiZCoin lsGlobalCoin "
          "lsToptraderCoin takerBuyRatioCoin").split()   # = FundingOnnxInferenceManager.extractFeaturesToArray
assert len(FIELDS) == 45


def load_snappy_obj(path):
    """StorageSnappy.writeObject2File: ObjectOutputStream(byte[] Snappy(ObjectOutputStream(obj)))."""
    import cramjam
    import javaobj
    obj = javaobj.loads(open(path, "rb").read())
    raw = bytes((x & 0xFF) for x in obj)
    return javaobj.loads(cramjam.snappy.decompress_raw(raw))


def fmt(t):
    return dt.datetime.fromtimestamp(t / 1000, TZ).strftime("%Y-%m-%d %H:%M")


_SESS = None


def _sess(model):
    global _SESS
    if _SESS is None:
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.intra_op_num_threads = 1
        _SESS = ort.InferenceSession(model, so)
    return _SESS


def extract_day(args):
    """Mot ngay -> cache npz: ts, p15 (f32), n_uni, pw_top (TOPN pwin giam dan, NaN pad), status."""
    data, day, model, cache = args
    out = os.path.join(cache, day + ".npz")
    if os.path.exists(out):
        return day, "cached"
    sess = _sess(model)
    iname = sess.get_inputs()[0].name
    oidx = [o.name for o in sess.get_outputs()].index("probabilities")
    files = sorted(glob.glob(os.path.join(data, "predictionSymbol", day, "*.features")))
    ts_l, p15_l, n_l, pw_l = [], [], [], []
    miss_p15 = bad = 0
    for f in files:
        ts = int(os.path.basename(f).split(".")[0])
        pf = os.path.join(data, "prediction", day, str(ts))
        if not os.path.exists(pf):
            miss_p15 += 1
            continue
        try:
            p15 = np.float32(float(load_snappy_obj(pf).return15M))
            m = load_snappy_obj(f)
            syms = sorted(str(k) for k in m.keys())
            byk = {str(k): v for k, v in m.items()}
            X = np.array([[float(getattr(byk[s], fn)) for fn in FIELDS] for s in syms], dtype=np.float32)
        except Exception:
            bad += 1
            continue
        n = X.shape[0]
        pw = np.full(TOPN, np.nan, dtype=np.float32)
        if n > 0:
            p = sess.run(None, {iname: X})[oidx][:, -1].astype(np.float32)   # lop 1 = win (Net015ValueLive.pwin)
            if np.isnan(p).any():
                n = -n   # buildValueMap: NaN => bo tick
            else:
                s = np.sort(p)[::-1][:TOPN]
                pw[:len(s)] = s
        ts_l.append(ts)
        p15_l.append(p15)
        n_l.append(n)
        pw_l.append(pw)
    np.savez_compressed(out, ts=np.array(ts_l, dtype=np.int64), p15=np.array(p15_l, dtype=np.float32),
                        n=np.array(n_l, dtype=np.int32), pw=np.array(pw_l, dtype=np.float32).reshape(-1, TOPN))
    return day, "ticks=%d miss_p15=%d bad=%d" % (len(ts_l), miss_p15, bad)


def cmd_extract(a):
    days = sorted(os.path.basename(d) for d in glob.glob(os.path.join(a.data, "predictionSymbol", "*")))
    os.makedirs(a.cache, exist_ok=True)
    jobs = [(a.data, d, a.model, a.cache) for d in days]
    with Pool(a.workers) as pool:
        for day, st in pool.imap_unordered(extract_day, jobs):
            LOG.info("extract %s %s", day, st)
    return 0


def load_cache(cache):
    parts = [np.load(f) for f in sorted(glob.glob(os.path.join(cache, "*.npz")))]
    ts = np.concatenate([p["ts"] for p in parts])
    o = np.argsort(ts, kind="stable")
    return (ts[o], np.concatenate([p["p15"] for p in parts])[o], np.concatenate([p["n"] for p in parts])[o],
            np.concatenate([p["pw"] for p in parts])[o])


def recon(ts, p15, n, pw, k):
    """(ts_rec, r_rec, tick_idx) cho K hang dau; bo tick uni<20 / NaN (n<20). Float32 nhu Java."""
    ok = n >= 20
    kk = np.minimum(k, np.where(ok, n, 0))
    sp = np.float32(1.0) - pw[:, :k]                                  # f32(1 - pwin_(j))
    factor = np.maximum(DYN_MIN, (sp / SCORE_BASE) * DYN_MULT)
    r = p15[:, None] / (factor * GS)
    mask = np.arange(k)[None, :] < kk[:, None]
    rows = np.nonzero(mask)
    return ts[rows[0]], r[mask].astype(np.float32), rows[0]


def cmd_validate(a, ts=None, p15=None, n=None, pw=None):
    """K16 tai tao vs buffer K16 THAT cua 242 (cung tick). Moi tick: tap r cua 242 (sort) phai = top-(16+d) hang
    tai tao bo d hang (d = 0..3: coin LEGACY bi skip, khong dem hang) voi sai so tuong doi < 1e-6 (nhieu ULP float32)."""
    import itertools
    if ts is None:
        ts, p15, n, pw = load_cache(a.cache)
    rts, rr = GAC.read_grr1(a.ref242)
    cut = a.ref_from or 0
    keep = rts >= cut
    rts, rr = rts[keep], rr[keep]
    t16, r16, _ = recon(ts, p15, n, pw, 16)
    t24, r24, _ = recon(ts, p15, n, pw, 24)
    ref_ticks = np.unique(rts)
    have = set(int(t) for t in np.unique(t24))
    cat = {"missing_in_recon": 0, "unexplained": 0}
    for t in ref_ticks:
        if int(t) not in have:
            cat["missing_in_recon"] += 1
            continue
        Rs = np.sort(rr[rts == t])
        Q = r24[t24 == t]
        got = None
        for d in range(4):
            for drop in itertools.combinations(range(16 + d), d):
                c = np.sort(np.delete(Q[:16 + d], list(drop)))
                if len(c) == len(Rs) and (np.abs(Rs - c) / np.abs(c)).max() < 1e-6:
                    got = d
                    break
            if got is not None:
                break
        k = "unexplained" if got is None else "drop%d" % got
        cat[k] = cat.get(k, 0) + 1
    lo, hi = int(ref_ticks.min()), int(ref_ticks.max())
    sel16 = np.isin(t16, ref_ticks)
    sel24 = np.isin(t24, ref_ticks)
    q = lambda v: float(np.sort(v)[int(np.floor(PCT * (len(v) - 1)))])
    expl = sum(v for k, v in cat.items() if k.startswith("drop"))
    res = {"ref_from": fmt(cut) if cut else "-", "ref_n": int(len(rts)), "ref_ticks": int(len(ref_ticks)),
           "ref_first": fmt(lo), "ref_last": fmt(hi), "categories": cat,
           "explained_frac": expl / max(1, len(ref_ticks)),
           "q_same_ticks": {"ref242": q(rr), "recon16": q(r16[sel16]), "recon24": q(r24[sel24]),
                            "n_ref": int(len(rr)), "n_recon16": int(sel16.sum())}}
    LOG.info("VALIDATE K16 recon vs 242: %s", json.dumps(res))
    return res


def write_grr1(path, ts, r):
    """= GateRatioPersist.writeFresh: 1 chunk MAGIC|LEN|CRC32|Snappy(ts>i8|r>f4 ...)."""
    import snappy
    raw = np.empty(len(ts), dtype=np.dtype([("ts", ">i8"), ("r", ">f4")]))
    raw["ts"] = ts
    raw["r"] = r
    comp = snappy.compress(raw.tobytes())
    with open(path, "wb") as f:
        f.write(struct.pack(">iiI", MAGIC, len(comp), zlib.crc32(comp) & 0xffffffff))
        f.write(comp)


def qinfo(ts, r, now_ms):
    first = int(ts.min())
    h = (now_ms // HOUR) * HOUR
    q, m = GAC.q_at(ts, r, h, PCT, DAYS)
    return {"n": int(len(ts)), "first": fmt(first), "last": fmt(int(ts.max())), "days": round((int(ts.max()) - first) / DAY, 2),
            "armed": bool(h - first >= GAC.WARMUP), "q_raw": q, "m": m,
            "q_t": q if h - first >= GAC.WARMUP else 0.008}


def cmd_build(a):
    ts, p15, n, pw = load_cache(a.cache)
    now_ms = a.now or int(dt.datetime.now(TZ).timestamp() * 1000)
    out = {"now": fmt(now_ms), "pct": PCT, "days": DAYS, "k": a.k, "ticks_cache": int(len(ts)),
           "ticks_bad_uni": int((n < 20).sum())}
    tk, rk, _ = recon(ts, p15, n, pw, a.k)
    keep = (tk >= now_ms - DAYS * DAY) & (tk < now_ms)
    tk, rk = tk[keep], rk[keep]
    write_grr1(a.out, tk, rk)
    bts, br = GAC.read_grr1(a.out)
    assert np.array_equal(bts, tk) and np.array_equal(br, rk), "doc lai GRR1 lech"
    out["out"] = a.out
    out["k%d" % a.k] = qinfo(bts, br, now_ms)
    t16, r16, _ = recon(ts, p15, n, pw, 16)
    keep16 = (t16 >= now_ms - DAYS * DAY) & (t16 < now_ms)
    out["k16_recon"] = qinfo(t16[keep16], r16[keep16], now_ms)
    if a.ref242:
        rts, rr = GAC.read_grr1(a.ref242)
        out["k16_242"] = qinfo(rts, rr, now_ms)
        ref_from0 = a.ref_from
        a.ref_from = None
        out["validate_all"] = cmd_validate(a, ts, p15, n, pw)
        a.ref_from = ref_from0
        if a.ref_from:
            out["validate_from"] = cmd_validate(a, ts, p15, n, pw)
    # q_t theo gio 7 ngay cuoi (ca hai ban tai tao, cung cua so) => ti so K/K16
    hrs = [((now_ms // HOUR) - i) * HOUR for i in range(0, 7 * 24, 6)]
    ratios = []
    for h in hrs:
        qa, _ = GAC.q_at(bts, br, h, PCT, DAYS)
        qb, _ = GAC.q_at(t16[keep16], r16[keep16], h, PCT, DAYS)
        if qa and qb and h - int(bts.min()) >= GAC.WARMUP:
            ratios.append(qa / qb)
    out["q_ratio_k_over_k16_7d"] = {"n": len(ratios), "median": float(np.median(ratios)) if ratios else None,
                                    "min": float(min(ratios)) if ratios else None, "max": float(max(ratios)) if ratios else None}
    LOG.info("BUILD %s", json.dumps(out))
    if a.json:
        json.dump(out, open(a.json, "w"), indent=1, default=str)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["extract", "validate", "build"])
    ap.add_argument("--data")
    ap.add_argument("--model")
    ap.add_argument("--cache", default=os.path.expanduser("~/claude_master/1005/shadow2/cache_k24"))
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--ref242")
    ap.add_argument("--k", type=int, default=24)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/1005/shadow2/buffer_k24.bin"))
    ap.add_argument("--now", type=int, default=None, help="epoch ms (mac dinh: bay gio)")
    ap.add_argument("--ref-from", type=int, default=None, dest="ref_from",
                    help="epoch ms: chi so tick 242 tu moc nay (vd sau deploy G2+FLAT3 242 2026-10-01)")
    ap.add_argument("--json")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    assert "/shadow_c3" not in os.path.abspath(a.out) and "/v_t_m" not in a.out, "KHONG ghi vao thu muc shadow/242"
    return {"extract": cmd_extract, "validate": cmd_validate, "build": cmd_build}[a.cmd](a) and 0


if __name__ == "__main__":
    sys.exit(main())
