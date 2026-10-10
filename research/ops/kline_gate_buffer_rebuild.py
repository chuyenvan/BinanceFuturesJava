#!/usr/bin/env python3
"""KFIX F6 — dung lai buffer gate rolling (GRR1, run/gate_ratio_live.bin) tu nen 1m DA SUA. Chay tren ORACLE, KHONG ghi 242.

r_k = p15 / (max(DYN_MIN, sp_k/SCORE_BASE*DYN_MULT) * GS)  (LiveGateRollingRatio.threshold, float32), k < K.
- p15: ONNX fold_20 (= model live) tren 33 feature gate (port devexport_202609, kline_242_div.stage_gate) tinh tu nen:
  --arm 242 (doc Aerospike 242 — SAU backfill la nen chuan) hoac --arm vis (gia tri thay bang Vision monthly, de kiem qua khu).
- sp_k: --sp cache:DIR = thong ke thu tu pwin cua tick LIVE (build_gate_buffer_k24.py extract tu storage 242/shadow),
        --sp bins = selector HO26 sim (bins2026Ax, ffill <= 15') — chi dung de kiem qua khu.
Stage:
  feat  --arm 242|vis --lo YYYYMMDD --hi YYYYMMDD --wd DIR        -> DIR/kdiv_gate_<arm>_<lo>_<hi>.csv.gz (warm-up 48h noi bo)
  build --feat GLOB --sp cache:DIR|bins --k K --now YYYYMMDD-HHMM --out OUT.bin [--ref REF.bin] [--json J]
  check --bin OUT.bin [--ref REF.bin] --now YYYYMMDD-HHMM
Quy trinh live: docs/runbooks/KLINE_FIX_242.md muc B (sau backfill: feat --arm 242 cho [now-92d, now], build K16 live /
  K cua tung shadow, check vs file dang chay, MASTER chep vao run/ trong lan restart co ke hoach).
"""
import argparse, datetime as dt, glob, json, logging, os, sys
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kline_gate_buffer_rebuild")
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "research", "analysis"))
sys.path.insert(0, os.path.join(REPO, "research", "parity"))
TZ7 = dt.timezone(dt.timedelta(hours=7))
MN, HOUR, DAY = 60000, 3600000, 86400000


def p7(s):
    return int(dt.datetime.strptime(s, "%Y%m%d-%H%M" if "-" in s else "%Y%m%d").replace(tzinfo=TZ7).timestamp() * 1000)


def f7(ms):
    return dt.datetime.fromtimestamp(ms / 1000, TZ7).strftime("%Y-%m-%d %H:%M")


def stage_feat(a):
    import kline_242_div as kd
    os.makedirs(a.wd, exist_ok=True)
    kd.WD = a.wd
    kd.stage_gate(argparse.Namespace(arm=a.arm, lo=a.lo, hi=a.hi))


def p15_from_feat(pattern):
    import onnxruntime as ort
    import kline_242_div as kd
    sess = ort.InferenceSession(kd.MODEL, providers=["CPUExecutionProvider"])
    df, p = kd.load_feat(pattern, sess)
    return df["ts"].to_numpy(np.int64), p.astype(np.float32)


def r_from_bins(ts, p15, k):
    """Nhu kline_242_div.gate_eval: sp HO26 ffill <= 15', r cho k hang dau co sp."""
    import kline_242_div as kd
    T15, SP = kd.load_bins()
    fi = np.searchsorted(T15, ts, "right") - 1
    okm = (fi >= 0) & (ts - T15[np.maximum(fi, 0)] <= 15 * MN)
    sp = np.where(okm[:, None], SP[np.maximum(fi, 0)][:, :k], np.nan).astype(np.float32)
    valid = ~np.isnan(sp)
    fac = np.maximum(kd.DYN_MIN, (sp / kd.SCORE_BASE * kd.DYN_MULT).astype(np.float32)).astype(np.float32)
    r = (p15[:, None] / (fac * kd.GS).astype(np.float32)).astype(np.float32)
    rows = np.nonzero(valid)
    return ts[rows[0]], r[valid]


def r_from_cache(cache, fts, fp15, k, rep):
    """Tick live (cache) + p15 tinh lai tu nen da sua (khop phut, chon do lech phut tot nhat trong {-1,0,+1})."""
    import build_gate_buffer_k24 as BG
    ts, p15_live, n, pw = BG.load_cache(cache)
    tmin = ts // MN * MN
    best = None
    for off in (-MN, 0, MN):
        j = np.searchsorted(fts, tmin + off)
        ok = (j < len(fts)) & (fts[np.minimum(j, len(fts) - 1)] == tmin + off)
        if ok.sum() == 0:
            continue
        rel = np.abs(fp15[j[ok]] / p15_live[ok] - 1)
        cand = (float(np.median(rel)), off, ok, j)
        rep.setdefault("align", []).append({"off_min": off // MN, "matched": int(ok.sum()), "rel_p50": cand[0],
                                            "rel_le_1e-3_pct": float(100 * np.mean(rel <= 1e-3))})
        if best is None or cand[0] < best[0]:
            best = cand
    if best is None:
        raise SystemExit("khong khop duoc tick live nao voi feature")
    _, off, ok, j = best
    rep["align_chosen_off_min"] = off // MN
    rep["ticks_live"], rep["ticks_matched"] = int(len(ts)), int(ok.sum())
    p15c = p15_live.copy()
    p15c[ok] = fp15[j[ok]]
    keep = ok
    tk, rk, _ = BG.recon(ts[keep], p15c[keep], n[keep], pw[keep], k)
    return tk, rk


def qtrace(ts, r, hours):
    import gate_arm_check as GAC
    out = {}
    for h in hours:
        q, m = GAC.q_at(ts, r, h, float(np.float32(0.999950829)), 90)
        out[h] = (q if h - int(ts.min()) >= GAC.WARMUP else 0.008, m)
    return out


def stage_build(a):
    import build_gate_buffer_k24 as BG
    import gate_arm_check as GAC
    now = p7(a.now)
    rep = {"now": f7(now), "k": a.k, "sp": a.sp, "feat": a.feat}
    fts, fp15 = p15_from_feat(a.feat)
    rep["feat_minutes"] = int(len(fts))
    if a.sp == "bins":
        tk, rk = r_from_bins(fts, fp15, a.k)
    elif a.sp.startswith("cache:"):
        tk, rk = r_from_cache(a.sp[6:], fts, fp15, a.k, rep)
    else:
        raise SystemExit("--sp cache:DIR | bins")
    keep = (tk >= now - 90 * DAY) & (tk < now)
    tk, rk = tk[keep], rk[keep]
    o = np.argsort(tk, kind="stable")
    tk, rk = tk[o], rk[o]
    BG.write_grr1(a.out, tk, rk)
    bts, br = GAC.read_grr1(a.out)
    assert np.array_equal(bts, tk) and np.array_equal(br, rk), "doc lai GRR1 lech"
    rep["out"] = a.out
    rep["analyse"] = GAC.analyse(a.out, now_ms=now)
    if a.ref:
        rep.update(compare(a.out, a.ref, now))
    log.info("BUILD %s", json.dumps(rep, default=str))
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=1, default=str)


def compare(path, ref, now):
    """q theo gio (moi 6h, 30 ngay cuoi) cua buffer moi vs buffer tham chieu + analyse ca hai."""
    import gate_arm_check as GAC
    a_ts, a_r = GAC.read_grr1(path)
    b_ts, b_r = GAC.read_grr1(ref)
    hrs = [((now // HOUR) - i) * HOUR for i in range(0, 30 * 24, 6)]
    qa, qb = qtrace(a_ts, a_r, hrs), qtrace(b_ts, b_r, hrs)
    rat = [qa[h][0] / qb[h][0] for h in hrs if qa[h][0] and qb[h][0]]
    return {"ref": ref, "ref_analyse": GAC.analyse(ref, now_ms=now),
            "q_ratio_new_over_ref_30d_6h": {"n": len(rat), "p1": float(np.quantile(rat, .01)) if rat else None,
                                            "p50": float(np.median(rat)) if rat else None,
                                            "p99": float(np.quantile(rat, .99)) if rat else None}}


def stage_check(a):
    import gate_arm_check as GAC
    now = p7(a.now)
    rep = {"bin": a.bin, "analyse": GAC.analyse(a.bin, now_ms=now)}
    if a.ref:
        rep.update(compare(a.bin, a.ref, now))
    log.info("CHECK %s", json.dumps(rep, default=str))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=["feat", "build", "check"])
    ap.add_argument("--arm", choices=["242", "vis"], default="242")
    ap.add_argument("--lo")
    ap.add_argument("--hi")
    ap.add_argument("--wd", default=os.path.expanduser("~/claude_master/1010/kfix_gate"))
    ap.add_argument("--feat")
    ap.add_argument("--sp", default="bins")
    ap.add_argument("--k", type=int, default=16)
    ap.add_argument("--now", default=dt.datetime.now(TZ7).strftime("%Y%m%d-%H%M"))
    ap.add_argument("--out")
    ap.add_argument("--ref")
    ap.add_argument("--bin")
    ap.add_argument("--json")
    a = ap.parse_args()
    {"feat": stage_feat, "build": stage_build, "check": stage_check}[a.stage](a)


if __name__ == "__main__":
    main()
