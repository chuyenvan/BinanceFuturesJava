#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bar_a_calibration.py — docs/prereg/PREREG_BAR_A_CALIBRATION.md (commit 71e3d2b).

HIEU CHINH RAO (a) `share top-1 % <= 15 %` — LOC HUU ICH hay KHONG THE DAT?

  * Don vi: U1 = CAP LENH (1 leg = 1 lenh/vi the). KHONG dung cap ngay.
  * Thu thap `share top-1/5/25 %` tren MOI doi tuong da do co PnL cap lenh:
        G-A book      (rulers_unit.json, 5 doi tuong, U1)
        G-B tick-score(tail_robust_rulers.json, 10 doi tuong, pool tick = 1 co hoi vao lenh)
        G-C arm sim   (gross_asymmap.json, 461 run ledger cap lenh; + TAIL50 8 bien the)
        G-D           (exit/shape/family2/size_count, 4 arm moi vong)
  * CI block-72h (anchor 2021-07-01, 2000 rep, seed 20260905, inflate(k=8)).
  * PASS_a(T), PASS_b'(25) [bo top-25 % leg => con duong], PASS_both(T).
  * Tra loi (1) co doi tuong nao PASS_a(15) + PnL duong ben (CI ngoai 0)?  (2) muc nao dat duoc?
    (3) danh doi voi (b')?  (4) ket luan + de xuat muc.

Thuan Python offline, 0 train/0 sim, DEV<=2025-12-31, khong cham 2026, khong cham 242/ONNX/LIVE.
Usage:  python3 bar_a_calibration.py --json docs/result/bar_a_calibration.json
"""
import argparse
import json
import math
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import size_count_score as S          # legs(), tail()
import c3_rates as C                  # inflate()

ROOT = "/home/ubuntu/src/BinanceFuturesJava"
RES = os.path.join(ROOT, "docs/result")
ASYMMAP = os.path.join(RES, "gross_asymmap.json")
RULERS = os.path.join(RES, "rulers_unit.json")
TAILRB = os.path.join(RES, "tail_robust_rulers.json")
TAIL50 = os.path.join(RES, "TAIL50_RULER_REDUNDANCY.json")
EXITST = os.path.join(RES, "RESULT_EXIT_STRUCT.json")
SHAPE1 = os.path.join(RES, "shape1_early_cut.json")
FAM2 = os.path.join(RES, "family2_tp_sl.json")
SCNT = os.path.join(RES, "size_count_score.json")

SEED, NREP = 20260905, 2000
BLOCK_H, K = 72, 8
END_DEV = "20251231"
THRESH = [15, 25, 50, 100]


def inflate(k):
    return C.inflate(k)


# --------------------------------- legs -----------------------------------
def legs_of(base):
    """Tra ve (pnl[], blk2[]) cap lenh tu 1 run dir (printDone.csv)."""
    d = S.legs(base)
    d = d.dropna(subset=["pnl"]).copy()
    p = d["pnl"].to_numpy(float)
    blk = d["blk2"].to_numpy(int) if "blk2" in d.columns else (d["blk"].to_numpy(int))
    return p, blk


def share_metrics(p):
    """n, sum, share_top1/5/25, drop25, winrate, asym, median, q_star (cung dinh nghia prereg)."""
    p = np.asarray(p, float)
    p = p[np.isfinite(p)]
    n = len(p)
    out = dict(n=int(n))
    if n == 0:
        return out
    s = np.sort(p)[::-1]
    tot = float(s.sum())
    out["sum_pnl"] = tot
    k1 = max(1, int(math.ceil(0.01 * n)))
    k5 = max(1, int(math.ceil(0.05 * n)))
    k25 = max(1, int(math.ceil(0.25 * n)))
    out["share_top1"] = float(100.0 * s[:k1].sum() / tot) if tot != 0 else float("nan")
    out["share_top5"] = float(100.0 * s[:k5].sum() / tot) if tot != 0 else float("nan")
    out["share_top25"] = float(100.0 * s[:k25].sum() / tot) if tot != 0 else float("nan")
    out["drop25"] = float(s[k25:].sum())
    out["median"] = float(np.median(p))
    out["winrate"] = float((p > 0).mean())
    pos, neg = p[p > 0], p[p < 0]
    out["asym"] = float(abs(neg.mean()) / pos.mean()) if len(pos) and len(neg) else float("nan")
    csum = np.cumsum(s)
    ks = np.where(csum >= tot)[0]
    out["q_star"] = float(100.0 * (ks[0] + 1) / n) if len(ks) else float("nan")
    return out


# --------------------------- block bootstrap ------------------------------
def _boot(p, blk, fn, nrep=NREP, seed=SEED, k=K):
    """Bootstrap theo khoi 72h; tra (obs, lo, hi) da no rong inflate(k)."""
    obs = fn(p)
    u, inv = np.unique(blk, return_inverse=True)
    groups = [p[inv == i] for i in range(len(u))]
    nb = len(u)
    if nb < 2:
        return float(obs), float("nan"), float("nan")
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(nrep):
        pick = rng.integers(0, nb, nb)
        x = np.concatenate([groups[i] for i in pick])
        v = fn(x)
        if v == v and np.isfinite(v):
            draws.append(v)
    arr = np.asarray(draws, float)
    if len(arr) == 0:
        return float(obs), float("nan"), float("nan")
    lo, hi = np.percentile(arr, [2.5, 97.5])
    c = (lo + hi) / 2.0
    w = inflate(k)
    return float(obs), float(c - (c - lo) * w), float(c + (hi - c) * w)


def stat_share(p):
    p = p[np.isfinite(p)]
    n = len(p)
    if n == 0:
        return float("nan")
    s = np.sort(p)[::-1]
    tot = s.sum()
    if tot == 0:
        return float("nan")
    k1 = max(1, int(math.ceil(0.01 * n)))
    return float(100.0 * s[:k1].sum() / tot)


def stat_drop25(p):
    p = p[np.isfinite(p)]
    n = len(p)
    if n == 0:
        return float("nan")
    s = np.sort(p)[::-1]
    k25 = max(1, int(math.ceil(0.25 * n)))
    return float(s[k25:].sum())


def stat_sum(p):
    p = p[np.isfinite(p)]
    return float(p.sum()) if len(p) else float("nan")


def full_object(base, source, name, unit="lenh"):
    try:
        p, blk = legs_of(base)
    except Exception as e:
        return dict(source=source, name=name, unit=unit, err="legs:%s" % e)
    if len(p) == 0:
        return dict(source=source, name=name, unit=unit, err="empty")
    m = share_metrics(p)
    m.update(source=source, name=name, unit=unit)
    o, lo, hi = _boot(p, blk, stat_share)
    m["ci_share_top1"] = [round(lo, 3), round(hi, 3)]
    o2, lo2, hi2 = _boot(p, blk, stat_drop25)
    m["ci_drop25"] = [round(lo2, 3), round(hi2, 3)]
    o3, lo3, hi3 = _boot(p, blk, stat_sum)
    m["ci_sum"] = [round(lo3, 3), round(hi3, 3)]
    # freq (leg/nam)
    try:
        d = S.legs(base)
        yrs = (d["t_end"].max() - d["ts"].min()).days / 365.25
        m["freq_per_yr"] = round(len(p) / yrs, 1) if yrs > 0 else None
        m["d_last"] = d["t_end"].max().strftime("%Y%m%d")
    except Exception:
        pass
    return m


# -------------------------------- main ------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(RES, "bar_a_calibration.json"))
    a = ap.parse_args()
    t0 = time.time()
    objs = []          # moi doi tuong (dict)

    # ---- G-A: book U1 ----
    ru = json.load(open(RULERS))
    book = []
    for name, o in ru["objects"].items():
        u = o.get("U1", {})
        if not u:
            continue
        tot = u["sum"]
        tf25 = u["tf25"]
        top25 = 100.0 * (tot - tf25) / tot if tot else float("nan")
        book.append(dict(
            source="G-A book(U1)", name=name, unit="vi the(coin-ngay)", n=u["n"],
            sum_pnl=tot, share_top1=u["share_top1_pct"], share_top5=u["conc_5_pct"],
            share_top25=top25, drop25=tf25, median=u["median"], winrate=u["winrate"],
            asym=u["asym"], side="gop",
            ci_share_top1=[u["ci"]["share_top1_pct"]["ci_infl_lo"], u["ci"]["share_top1_pct"]["ci_infl_hi"]],
            ci_drop25=[u["ci"]["tf25"]["ci_infl_lo"], u["ci"]["tf25"]["ci_infl_hi"]],
            ci_sum=None))
    objs += book

    # ---- G-B: tick-score (pool) ----
    tr = json.load(open(TAILRB))
    gb = []
    for pool in ("p32", "pool_ext_B2"):
        for name, lv in tr["runs"].get(pool, {}).get("level", {}).items():
            pt = lv.get("point", {})
            c1 = pt.get("conc_1")
            if c1 is None:
                continue
            met = lv.get("metrics", {}).get("conc_1", {}).get("72_2000_20260905", {})
            raw = met.get("raw"); infl_ = met.get("infl")
            gb.append(dict(
                source="G-B tick-score(%s)" % pool, name=name, unit="tick(co hoi vao lenh)",
                n=None, sum_pnl=None, share_top1=100.0 * c1,
                share_top5=100.0 * pt.get("conc_5") if pt.get("conc_5") is not None else None,
                share_top25=None, drop25=None,
                ci_share_top1=[100.0 * raw[0], 100.0 * raw[1]] if raw else None,
                ci_share_top1_infl=[100.0 * infl_[0], 100.0 * infl_[1]] if infl_ else None))
    # dedup: p32 and ext overlap -> keep both (chi bao, khong tinh vao POP)
    objs += gb

    # ---- G-C: arm sim (asymmap population) ----
    am = json.load(open(ASYMMAP))
    pop = [r for r in am if r.get("top1_share") is not None and r.get("sum_pnl") is not None]
    for r in pop:
        objs.append(dict(source="G-C arm(ledger)", name=r["tag"], unit="lenh",
                         n=r["n"], sum_pnl=r["sum_pnl"], share_top1=r["top1_share"],
                         share_top5=r.get("conc_5"), share_top25=None, drop25=r.get("TF50"),
                         median=r.get("median"), winrate=(r.get("sign_pct", float("nan")) / 100.0
                                                           if r.get("sign_pct") is not None else None),
                         asym=r.get("asym")))

    # ---- G-D: exit/shape/family2/size_count ----
    gd = []
    ex = json.load(open(EXITST))["rao"]
    for name, v in ex.items():
        gd.append(dict(source="G-D exit_struct", name=name, unit="lenh", n=v["n"],
                       sum_pnl=v["sum_pnl"], share_top1=v["share_top1_pct"],
                       share_top5=None, share_top25=None, drop25=v["tf50"],
                       median=v["median_leg"], winrate=v["sign_pct"] / 100.0))
    for f, tag in ((SHAPE1, "G-D shape1"), (FAM2, "G-D family2"), (SCNT, "G-D size_count")):
        try:
            dd = json.load(open(f))
            arms = dd.get("arms", {})
            for name, v in arms.items():
                gd.append(dict(source=tag, name=name, unit="lenh", n=v.get("n"),
                               sum_pnl=v.get("sum_pnl"),
                               share_top1=v.get("top1_share"),
                               median=v.get("median"), winrate=(v.get("sign_pct", float("nan")) / 100.0
                                                                 if v.get("sign_pct") is not None else None)))
        except Exception as e:
            gd.append(dict(source=tag, err=str(e)))
    objs += gd

    # ---- recompute TOAN BO arm pop: share top1/5/25 + drop25 + CI block ----
    print("recompute all %d arm runs..." % len(pop), flush=True)
    cand = []
    for i, r in enumerate(pop):
        base = os.path.join(r["root"], r["tag"])
        o = full_object(base, "G-C arm(ledger)", r["tag"])
        if "err" not in o:
            o["share_top1_asymmap"] = r.get("top1_share")
            if o.get("share_top1") is not None and o.get("ci_share_top1"):
                o["robust_a15"] = bool(o["ci_share_top1"][1] <= 15)
                o["robust_b25"] = bool(o["ci_drop25"][0] > 0) if o.get("ci_drop25") else None
        cand.append(o)
        if (i + 1) % 50 == 0:
            print("  %d/%d (%.0fs)" % (i + 1, len(pop), time.time() - t0), flush=True)
    # them vai ten goi cu the de doi chieu (neu chua co)
    named_extra = ["gr-kg0-q995", "gr-kg0-q998", "gr-kg0-q999", "gr-kg0-q998-15m",
                   "cd-sel15-q999", "cd-sel15-q998", "cd-sel15", "selcut-cut"]
    have = {c["name"] for c in cand}
    for t in named_extra:
        if t in have:
            continue
        base = os.path.join("/home/ubuntu/kaggle_sim/out", t)
        if os.path.exists(os.path.join(base, "storage", "printDone.csv")):
            cand.append(full_object(base, "G-C arm(ledger)", t))

    # ---- phan bo ----
    def dist(vals):
        v = np.asarray([x for x in vals if x is not None and np.isfinite(x)], float)
        if len(v) == 0:
            return {}
        q = np.percentile(v, [0, 25, 50, 75, 100])
        return dict(n=len(v), min=float(q[0]), p25=float(q[1]), median=float(q[2]),
                    p75=float(q[3]), max=float(q[4]),
                    le15=int((v <= 15).sum()), le25=int((v <= 25).sum()),
                    le50=int((v <= 50).sum()), le100=int((v <= 100).sum()))

    ok = [c for c in cand if "err" not in c and c.get("share_top1") is not None]
    pop_shares = [c["share_top1"] for c in ok]
    book_shares = [b["share_top1"] for b in book]
    gb_shares = [g["share_top1"] for g in gb]
    gd_shares = [g.get("share_top1") for g in gd]

    dist_out = dict(
        POP_arm461=dist(pop_shares),
        POP_valid_pos=dist([r["top1_share"] for r in pop if r.get("sum_pnl", 0) > 0]),
        BOOK_U1=dist(book_shares),
        SCORE_OBJ=dist(gb_shares),
        G_D=dist(gd_shares),
    )

    # ---- PASS_a / PASS_b' / PASS_both tren TOAN BO arm pop (share tai lap) ----
    valid = [c for c in ok if c.get("sum_pnl", 0) > 0]
    cand_pass = {}
    for T in THRESH:
        pa = [c for c in valid if c["share_top1"] <= T]
        pb = [c for c in pa if c.get("drop25") is not None and c["drop25"] > 0]
        ra = [c for c in pa if c.get("robust_a15")]
        rb = [c for c in pb if c.get("robust_b25")]
        cand_pass["T%d" % T] = dict(
            valid=len(valid), pass_a=len(pa), pass_b=len(pb),
            pass_both_robust=len(rb),
            names_a=[c["name"] for c in pa], names_b=[c["name"] for c in pb],
            names_robust_a15=[c["name"] for c in ra], names_robust_both=[c["name"] for c in rb])
    pop_pass = {k: dict(valid=v["valid"], pass_a=v["pass_a"]) for k, v in cand_pass.items()}

    # doi chieu tai lap vs asymmap (share_top1)
    diffs = []
    for c in ok:
        if c.get("share_top1_asymmap") is not None and c.get("share_top1") is not None:
            diffs.append(abs(c["share_top1"] - c["share_top1_asymmap"]))
    repro = dict(n=len(diffs), max_abs_diff=float(np.max(diffs)) if diffs else None)

    out = dict(
        prereg="docs/prereg/PREREG_BAR_A_CALIBRATION.md", commit_prereg="71e3d2b",
        repro_vs_asymmap=repro,
        seed=SEED, nrep=NREP, block_h=BLOCK_H, k=K, inflate=inflate(K),
        n_pop=len(pop), n_cand_recomputed=len(cand), n_repro=len(diffs),
        distribution=dist_out, pop_pass=pop_pass, cand_pass=cand_pass,
        book=book, score_obj=gb, cand=cand, g_d=gd,
        objects=objs,
    )
    os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
    json.dump(out, open(a.json, "w"), indent=0, default=str)
    print("wrote %s  n_pop=%d n_cand=%d  (%.0fs)" % (a.json, len(pop), len(cand), time.time() - t0))
    # in tom tat
    for kk, v in dist_out.items():
        print("DIST", kk, v)
    print("POP PASS", pop_pass)
    for T, v in cand_pass.items():
        print("CAND", T, "pass_a=%d pass_b=%d" % (v["pass_a"], v["pass_b"]), v["names_a"][:8])


if __name__ == "__main__":
    main()
