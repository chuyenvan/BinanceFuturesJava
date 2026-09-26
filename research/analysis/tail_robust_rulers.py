#!/usr/bin/env python3
"""tail_robust_rulers.py — PREREG_TAIL_ROBUST_RULERS (commit 4660529).

BỘ THƯỚC "KHÔNG-ĐUÔI" (17 thước, pre-reg §5) + LÀM MỊN LẠI CI (§6), trên pool P32
(`label_b_pnl.parquet`, `y = gross` luật thoát) cho 10 đối tượng (§3).

Read-only: KHÔNG train, KHÔNG sim, KHÔNG chạm 242/ONNX/LIVE. DEV only (<= 2025-12-31).
CI: bootstrap theo KHỐI tick, PAIRED (mọi đối tượng dùng cùng ma trận block-index/seed/cấu hình).
Mọi đối tượng bị ép về **cùng tập tick** (giao các tick có điểm đủ) để Δ là ghép cặp thật.

  python3 tail_robust_rulers.py --stage level   --pool p32
  python3 tail_robust_rulers.py --stage report  --pool p32
  python3 tail_robust_rulers.py --stage level   --pool ext --tag ext \
      --objects ofi_candidate,ofi_baseline_fresh,ofi_noise,45deploy,S1
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import model_ruler as MR                                  # noqa: E402
import c3_rates as C                                      # noqa: E402

TMP = "/tmp/trr"
POOL_P32 = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
POOL_EXT = "/home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext.parquet"
K = 8
F_DEC = 0.006
FEES = [0.0, 0.004, 0.006, 0.008]
H = 3600000
S0, CAP = 0.02, 70.0
BLOCKS = [24, 72, 168]
NREPS = [2000, 5000]
SEEDS = [20260905, 20260907, 20260911]
K_RULER, K_OBJ = 17, 10
MAIN = (72, 2000, 20260905)
QUANT_CFGS = [(72, 2000, 20260905), (24, 2000, 20260905), (168, 2000, 20260905),
              (72, 5000, 20260905), (72, 2000, 20260907), (72, 2000, 20260911)]
RULERS = ["wmean_p1p99", "wmean_p5p95", "tmean_1", "tmean_5", "median", "sign_frac",
          "tf_1", "tf_5", "tf_10", "conc_1", "conc_5", "hhi_gain", "ic_wmean", "ic_med",
          "loss_mean", "wl_ratio", "max_loss"]
EXTRA = ["p25", "p75", "net_tick", "gross8", "ic_raw", "e_mean", "d_mean"]
CAPM = ["A_mean", "B95", "Bmax"]
BINS = {
    "45deploy": "/home/ubuntu/claudedata/predwf_G015x26",
    "A44": "/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A44",
    "A45": "/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A45",
    "V1": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V1",
    "V5": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V5",
    "MRA4": "/tmp/mrbins/MRA4",
    "MRB8": "/tmp/mrbins/MRB8",
    "MRB32": "/tmp/mrbins/MRB32",
}
PREDS = {
    "S1": "/home/ubuntu/ledger/pred_s1a2x1.parquet",
    "ofi_candidate": "/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_ofi_candidate_v2.parquet",
    "ofi_baseline_fresh": "/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_baseline_fresh.parquet",
    "ofi_noise": "/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_ofi_noise_v2.parquet",
}
OBJECTS = list(BINS) + list(PREDS)
# ⚠️ CHIEU DIEM KHAC NHAU GIUA 2 NGUON (do duoc, khong doan):
#   - bins (`p`): corr(score, rank cua pool) ~ -0,32 => DIEM CAO = TOT (chuan model_ruler)
#   - `pred_s1a2x1.parquet` + `pred_ofi_*_v2.parquet`: score = -pred (xem
#     `research/pipeline/x1/kaggle_ofi_v3/ofi_train_eval_v3.py:150,177`) => DIEM THAP = TOT
#   => phai DOI DAU cho nhom nay, neu khong se chon nham top-8 = 8 coin XAU NHAT cua pool.
ORIENT = {o: -1 for o in PREDS}
PAIRS = [("A45", "45deploy"), ("V5", "V1"),
         ("A44", "45deploy"), ("A44", "V1"), ("A45", "V1"),
         ("MRA4", "45deploy"), ("MRA4", "A45"), ("MRA4", "V1"),
         ("MRB8", "45deploy"), ("MRB8", "A45"), ("MRB8", "V1"),
         ("MRB32", "45deploy"), ("MRB32", "A45"), ("MRB32", "V1"),
         ("MRB8", "V5"), ("MRB32", "V5"),
         ("S1", "45deploy"), ("S1", "V1"),
         ("ofi_candidate", "45deploy"), ("ofi_candidate", "V1"),
         ("ofi_candidate", "ofi_baseline_fresh"), ("ofi_candidate", "ofi_noise"),
         ("ofi_baseline_fresh", "45deploy"), ("ofi_baseline_fresh", "V1"),
         ("ofi_noise", "45deploy"), ("ofi_noise", "V1")]


def log(*a):
    print(*a, flush=True)


def cfg_id(b, n, s):
    return "%d_%d_%d" % (b, n, s)


# ─────────────────────────── nạp pool + điểm ───────────────────────────

def load_pool(path, mode):
    cols = ["ts", "symId", "gross", "exit_ts"] + (["rank"] if mode == "p32" else [])
    d = pd.read_parquet(path, columns=cols)
    d = d.sort_values(["ts", "rank"] if mode == "p32" else ["ts", "symId"],
                      kind="stable").reset_index(drop=True)
    ts = d.ts.to_numpy(np.int64)
    return dict(ts=ts, sym=d.symId.to_numpy(np.int64), gross=d.gross.to_numpy(np.float64),
                exit_ts=d.exit_ts.to_numpy(np.int64), tick=np.searchsorted(np.unique(ts), ts),
                ticks=np.unique(ts), mode=mode)


def score_vec(P, obj):
    key = P["ts"] * 1024 + P["sym"]
    order = np.argsort(key, kind="stable")
    ks = key[order]
    S = np.full(len(key), np.nan)
    t0 = time.time()
    if obj in BINS:
        for f in MR.FOLDS:
            bp = os.path.join(BINS[obj], "predict_wf_%s.bin" % f)
            if not os.path.exists(bp):
                continue
            arr = np.fromfile(bp, dtype=MR.BIN_DT)
            k = arr["ts"].astype(np.int64) * 1024 + arr["sym"].astype(np.int64)
            v = arr["p"].astype(np.float64)
            ip = np.clip(np.searchsorted(ks, k), 0, len(ks) - 1)
            hit = ks[ip] == k
            S[order[ip[hit]]] = v[hit]
            del arr, k, v
    else:
        d = pd.read_parquet(PREDS[obj], columns=["ts", "sym", "score"])
        k = d.ts.to_numpy(np.int64) * 1024 + d.sym.to_numpy(np.int64)
        ip = np.clip(np.searchsorted(ks, k), 0, len(ks) - 1)
        hit = ks[ip] == k
        S[order[ip[hit]]] = d.score.to_numpy(np.float64)[hit]
        del d, k
    log("    [score] %-34s phu=%.2f%% | %.0fs" % (obj,
        100 * np.isfinite(S).mean(), time.time() - t0))
    return S


def stage_scores(P, tag, objs):
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(TMP, "scores_%s.npz" % tag)
    if os.path.exists(out):
        z = np.load(out)
        if all(o in z.files and z[o].shape[0] == len(P["gross"]) for o in objs):
            return {o: z[o] for o in objs}
    SC = {}
    for o in objs:
        SC[o] = score_vec(P, o)
    np.savez_compressed(out, **{o: SC[o] for o in objs})
    log("  ### score -> %s (%.1f MB)" % (out, os.path.getsize(out) / 1e6))
    return SC


def common_ticks(P, SC, objs):
    """Giao cac tick co DIEM DU cho MOI doi tuong (de Δ la ghep cap that)."""
    nt = len(P["ticks"])
    if P["mode"] == "p32":
        m = np.ones(nt, bool)
        for o in objs:
            m &= np.isfinite(SC[o].reshape(nt, -1)).all(1)
    else:
        tot = np.bincount(P["tick"], minlength=nt)
        m = np.ones(nt, bool)
        for o in objs:
            f = np.isfinite(SC[o])
            m &= (np.bincount(P["tick"][f], minlength=nt) == tot)
    log("  ### tick dung chung: %d / %d (bo %d)" % (m.sum(), nt, nt - m.sum()))
    return P["ticks"][m]


def subset_pool(P, ticks):
    m = np.isin(P["ts"], ticks)
    ts = P["ts"][m]
    t2 = np.unique(ts)
    return dict(ts=ts, sym=P["sym"][m], gross=P["gross"][m], exit_ts=P["exit_ts"][m],
                tick=np.searchsorted(t2, ts), ticks=t2, mode=P["mode"])


# ─────────────────── chọn top-K theo tick ───────────────────

def select_topk(P, S, k=K):
    nt = len(P["ticks"])
    if P["mode"] == "p32":
        Sm = S.reshape(nt, -1)
        order = np.argsort(-Sm, axis=1, kind="stable")[:, :k]
        fi = (np.repeat(np.arange(nt), k) * Sm.shape[1] + order.reshape(-1))
    else:
        cnt = np.bincount(P["tick"], minlength=nt)
        o = np.lexsort((-S, P["tick"]))
        starts = np.repeat(np.cumsum(cnt) - cnt, cnt)[o]
        cc = np.arange(len(o)) - starts
        fi = np.sort(o[cc < k])
    return dict(tick=P["tick"][fi], gross=P["gross"][fi], score=S[fi], exit_ts=P["exit_ts"][fi],
                sym=P["sym"][fi], ticks=P["ticks"], nt=nt)


def tick_ic(ti, score, y, nt):
    d = pd.DataFrame({"t": ti, "s": score, "y": y})
    rs = d.groupby("t")["s"].rank(method="average")
    ry = d.groupby("t")["y"].rank(method="average")
    d["rs"], d["ry"] = rs, ry
    g = d.groupby("t")
    a = g["rs"].transform("mean"); b = g["ry"].transform("mean")
    d["a"] = (d.rs - a) * (d.ry - b); d["b"] = (d.rs - a) ** 2; d["c"] = (d.ry - b) ** 2
    G = d.groupby("t")
    ic = (G["a"].sum() / np.sqrt(G["b"].sum() * G["c"].sum()).replace(0, np.nan)) \
        .reindex(range(nt)).to_numpy(np.float64)
    return ic


def tick_agg(SEL, f, nt):
    ti = SEL["tick"]; net = SEL["gross"] - f; sc = SEL["score"]
    A = {}

    def bs(v, name):
        A[name] = np.bincount(ti, weights=np.asarray(v, np.float64), minlength=nt)
    A["CNT"] = np.bincount(ti, minlength=nt).astype(np.float64)
    bs(net, "SN")
    bs((net > 0).astype(np.float64), "SPOS")
    bs(np.where(net > 0, net, 0.0), "WW")
    A["WN"] = np.bincount(ti[net > 0], minlength=nt).astype(np.float64)
    bs(np.where(net < 0, -net, 0.0), "LL")
    A["LN"] = np.bincount(ti[net < 0], minlength=nt).astype(np.float64)
    g = np.maximum(net, 0.0)
    bs(g, "G1"); bs(g * g, "G2")
    mn = np.full(nt, np.inf)
    np.minimum.at(mn, ti, net)
    A["MINN"] = np.where(np.isfinite(mn), mn, 0.0)
    q = np.percentile(net, [1, 5, 90, 95, 99])
    bs(np.clip(net, q[0], q[4]), "W1S")
    bs(np.clip(net, q[1], q[3]), "W5S")
    for nm, a, b in (("T1", q[0], q[4]), ("T5", q[1], q[3])):
        m = (net >= a) & (net <= b)
        bs(np.where(m, net, 0.0), nm + "S")
        A[nm + "C"] = np.bincount(ti[m], minlength=nt).astype(np.float64)
    N = len(net)
    rk = np.argsort(np.argsort(net, kind="stable"), kind="stable")
    for pct, nm in ((1, "F1"), (5, "F5"), (10, "F10")):
        keep = rk < N - int(np.ceil(pct / 100.0 * N))
        bs(np.where(keep, net, 0.0), nm + "S")
        A[nm + "C"] = np.bincount(ti[keep], minlength=nt).astype(np.float64)
    bs(np.where(rk >= N - int(np.ceil(0.01 * N)), net, 0.0), "C1NUM")
    bs(np.where(rk >= N - int(np.ceil(0.05 * N)), net, 0.0), "C5NUM")
    icw = tick_ic(ti, sc, np.clip(net, q[0], q[4]), nt)
    A["IC"] = np.where(np.isfinite(icw), icw, 0.0)
    A["NTIC"] = np.isfinite(icw).astype(np.float64)
    A["_ic"] = icw
    A["_icraw"] = tick_ic(ti, sc, net, nt)
    # exposure e_t (leg dang mo) + d_t (coin PHAN BIET dang mo) — cho bang TIEN/tran 70%
    a = ti.astype(np.int64); b = np.searchsorted(SEL["ticks"], SEL["exit_ts"], "left")
    ca = np.bincount(a, minlength=nt + 1)[:nt]
    cb = np.bincount(np.clip(b, 0, nt), minlength=nt + 1)[:nt]
    A["E"] = (np.cumsum(ca) - np.cumsum(cb)).astype(np.float64)
    c = np.clip(b, 0, nt) - a
    tot = int(c.sum())
    if tot > 0:
        tri = np.repeat(np.arange(len(a)), c)
        base = np.repeat(a, c) + np.arange(tot) - np.repeat(np.cumsum(c) - c, c)
        A["D"] = (pd.DataFrame({"t": base.astype(np.int32), "s": SEL["sym"][tri].astype(np.int32)})
                  .drop_duplicates().groupby("t").size().reindex(range(nt), fill_value=0)
                  .to_numpy(np.float64))
    else:
        A["D"] = np.zeros(nt)
    A["_netsort"] = np.sort(net)
    A["_q"] = q
    return A, net, ti


POINT = {
    "wmean_p1p99": lambda A: A["W1S"].sum() / A["CNT"].sum(),
    "wmean_p5p95": lambda A: A["W5S"].sum() / A["CNT"].sum(),
    "tmean_1": lambda A: A["T1S"].sum() / A["T1C"].sum(),
    "tmean_5": lambda A: A["T5S"].sum() / A["T5C"].sum(),
    "tf_1": lambda A: A["F1S"].sum() / A["F1C"].sum(),
    "tf_5": lambda A: A["F5S"].sum() / A["F5C"].sum(),
    "tf_10": lambda A: A["F10S"].sum() / A["F10C"].sum(),
    "sign_frac": lambda A: A["SPOS"].sum() / A["CNT"].sum(),
    "conc_1": lambda A: A["C1NUM"].sum() / A["SN"].sum(),
    "conc_5": lambda A: A["C5NUM"].sum() / A["SN"].sum(),
    "hhi_gain": lambda A: A["G2"].sum() / A["G1"].sum() ** 2,
    "ic_wmean": lambda A: A["IC"].sum() / A["NTIC"].sum(),
    "loss_mean": lambda A: -A["LL"].sum() / A["LN"].sum(),
    "wl_ratio": lambda A: (A["WW"].sum() / A["WN"].sum()) / (A["LL"].sum() / A["LN"].sum()),
    "max_loss": lambda A: A["MINN"].sum() / A["NTIC"].sum(),
    "net_tick": lambda A: A["SN"].sum() / A["CNT"].size,
    "gross8": lambda A: (A["SN"].sum() + F_DEC * A["CNT"].sum()) / A["CNT"].sum(),
    "e_mean": lambda A: A["E"].mean(),
    "d_mean": lambda A: A["D"].mean(),
}


# ─────────────────────────── bootstrap ───────────────────────────

def blk_inv(ticks, block_h):
    return np.unique(ticks // (block_h * H), return_inverse=True)[1]


def boot(Xb, BI):
    return Xb[BI].sum(1)


def wquant(sorted_v, wsum_cum, target):
    idx = (wsum_cum < target).sum(1)
    return sorted_v[np.clip(idx, 0, len(sorted_v) - 1)]


def stage_level(P, SC, objs, tag):
    nt = len(P["ticks"])
    inv, nb, BI = {}, {}, {}
    for b in BLOCKS:
        inv[b] = blk_inv(P["ticks"], b)
        nb[b] = int(inv[b].max()) + 1
        for n in NREPS:
            for s in SEEDS:
                BI[(b, n, s)] = np.random.default_rng(s).integers(0, nb[b], (n, nb[b]))
    CFGS = [cfg_id(b, n, s) for b in BLOCKS for n in NREPS for s in SEEDS]
    for o in objs:
        t0 = time.time()
        SEL = select_topk(P, SC[o])
        A, net, ti = tick_agg(SEL, F_DEC, nt)
        R, point = {}, {k: float(POINT[k](A)) for k in POINT}
        point["median"] = float(np.median(net))
        point["p25"] = float(np.percentile(net, 25))
        point["p75"] = float(np.percentile(net, 75))
        ic = A["_ic"]; m = np.isfinite(ic)
        point["ic_med"] = float(np.median(ic[m]))
        point["ic_raw"] = float(np.median(A["_icraw"][np.isfinite(A["_icraw"])]))
        point["nan_ticks_leg"] = 0
        point["n_leg"] = int(len(net))
        point["d_p95"] = float(np.percentile(A["D"], 95))
        point["d_max"] = float(A["D"].max())
        point["q1"], point["q99"] = float(A["_q"][0]), float(A["_q"][4])
        for cid in CFGS:
            b, n, s = (int(x) for x in cid.split("_"))
            BIx = BI[(b, n, s)]
            _ib = inv[b]

            def Xt(name):
                return np.bincount(_ib, weights=A[name], minlength=nb[b])

            def Bp(name):
                return boot(Xt(name), BIx)

            Bt = Bp

            cnt = Bp("CNT"); sn = Bp("SN")
            v = {}
            v["wmean_p1p99"] = Bp("W1S") / cnt
            v["wmean_p5p95"] = Bp("W5S") / cnt
            v["tmean_1"] = Bp("T1S") / Bp("T1C")
            v["tmean_5"] = Bp("T5S") / Bp("T5C")
            v["tf_1"] = Bp("F1S") / Bp("F1C")
            v["tf_5"] = Bp("F5S") / Bp("F5C")
            v["tf_10"] = Bp("F10S") / Bp("F10C")
            v["sign_frac"] = Bp("SPOS") / cnt
            v["conc_1"] = Bp("C1NUM") / sn
            v["conc_5"] = Bp("C5NUM") / sn
            g1 = Bp("G1"); g2 = Bp("G2")
            v["hhi_gain"] = g2 / (g1 * g1)
            v["ic_wmean"] = Bt("IC") / Bt("NTIC")
            v["loss_mean"] = -Bp("LL") / Bp("LN")
            v["wl_ratio"] = (Bp("WW") / Bp("WN")) / (Bp("LL") / Bp("LN"))
            v["max_loss"] = Bt("MINN") / Bt("NTIC")
            v["net_tick"] = sn
            v["gross8"] = (sn + F_DEC * cnt) / cnt
            v["e_mean"] = Bt("E") / Bt("NTIC")
            v["d_mean"] = Bt("D") / Bt("NTIC")
            # ic_med (theo tick): weighted-quantile tren IC da sort
            o2 = np.argsort(np.where(m, ic, np.inf), kind="stable")
            icsort = np.where(m, ic, 0.0)[o2]
            nrep = n
            out = np.empty(nrep)
            CH = max(1, int(2e7 // nt))
            for c0 in range(0, nrep, CH):
                wb = np.stack([np.bincount(BIx[r], minlength=nb[b]) for r in range(c0, min(nrep, c0 + CH))]).astype(np.float32)
                cw = np.cumsum(wb[:, _ib][:, o2], axis=1, dtype=np.float32)
                out[c0:c0 + cw.shape[0]] = wquant(icsort, cw, 0.5 * cw[:, -1:])
            v["ic_med"] = out
            # p25/p75/median chi o 6 cau hinh da khai bao (pre-reg §6)
            if (b, n, s) in QUANT_CFGS:
                nleg = len(net)
                outs = np.full((3, nrep), np.nan)
                CH2 = max(1, int(1.2e7 // nleg))
                for c0 in range(0, nrep, CH2):
                    wb = np.stack([np.bincount(BIx[r], minlength=nb[b])
                                   for r in range(c0, min(nrep, c0 + CH2))]).astype(np.float32)
                    cw = np.cumsum(wb[:, _ib[ti]], axis=1, dtype=np.float32)
                    tot = cw[:, -1:]
                    for j, p in enumerate((0.5, 0.25, 0.75)):
                        outs[j, c0:c0 + cw.shape[0]] = wquant(A["_netsort"], cw, p * tot)
                v["median"], v["p25"], v["p75"] = outs[0], outs[1], outs[2]
            R[cid] = {k: np.asarray(v[k], np.float32) for k in v}
        json.dump(point, open(os.path.join(TMP, "point_%s_%s.json" % (tag, o)), "w"), indent=1)
        np.savez_compressed(os.path.join(TMP, "reps_%s_%s.npz" % (tag, o)), **R)
        log("  ### %-20s n_leg=%d point_median=%+.5f tf5=%+.5f conc1=%.3f | %.0fs" % (
            o, len(net), point["median"], point["tf_5"], point["conc_1"], time.time() - t0))
        del A, net, SEL


# ─────────────────────────── báo cáo ───────────────────────────

def ci_sum(v, point, infl):
    lo, hi = np.percentile(v, 2.5), np.percentile(v, 97.5)
    ilo, ihi = point - (point - lo) * infl, point + (hi - point) * infl
    out_r = bool(lo > 0 or hi < 0); out_i = bool(ilo > 0 or ihi < 0)
    wid = (hi - lo) / abs(point) if abs(point) > 1e-12 else float("inf")
    return {"point": round(float(point), 8), "raw": [round(float(lo), 8), round(float(hi), 8)],
            "infl": [round(float(ilo), 8), round(float(ihi), 8)],
            "out_raw": out_r, "out_infl": out_i, "out": bool(out_r and out_i),
            "width_rel": round(float(wid), 4),
            "width": round(float(hi - lo), 8), "dir": int(np.sign(point))}


def stage_report(P, tag, objs, outfile):
    NT = len(P["ticks"])
    rep = {}
    pts = {}
    for o in objs:
        z = np.load(os.path.join(TMP, "reps_%s_%s.npz" % (tag, o)), allow_pickle=True)
        rep[o] = {k: (z[k].item() if z[k].dtype == object else z[k])
                  for k in z.files if k != "point"}
        # net_tick luu dang TONG theo khoi -> chuan hoa ve TRUNG BINH/tick (Σ tick trong 1 rep = nt)
        for cid, dd in rep[o].items():
            if isinstance(dd, dict) and "net_tick" in dd:
                dd["net_tick"] = (np.asarray(dd["net_tick"], np.float64) / NT).astype(np.float32)
        pts[o] = json.load(open(os.path.join(TMP, "point_%s_%s.json" % (tag, o)))) \
            if os.path.exists(os.path.join(TMP, "point_%s_%s.json" % (tag, o))) \
            else json.loads(str(np.asarray(z["point"]).item()))
    infl17, infl10 = C.inflate(K_RULER), C.inflate(K_OBJ)
    res = {"k_ruler": K_RULER, "k_obj": K_OBJ, "inflate_k17": infl17, "inflate_k10": infl10,
           "f": F_DEC, "K": K, "fees": FEES, "cap": CAP, "s0": S0,
           "n_tick": len(P["ticks"]), "objs": objs, "level": {}, "delta": {}, "rule": {},
           "quant_cfgs": [cfg_id(*c) for c in QUANT_CFGS]}
    for o in objs:
        res["level"][o] = {"point": pts[o], "metrics": {}}
        for r in RULERS + EXTRA:
            cells = {}
            for cid, m in rep[o].items():
                if r not in m:
                    continue
                if not np.isfinite(m[r]).any():
                    continue
                cells[cid] = ci_sum(m[r], pts[o].get(r, float("nan")), infl17)
            if cells:
                res["level"][o]["metrics"][r] = cells
    for (A_, B_) in PAIRS:
        if A_ not in rep or B_ not in rep:
            continue
        key = "%s-%s" % (A_, B_)
        res["delta"][key] = {"point": {}, "metrics": {}}
        for r in RULERS + EXTRA:
            cells = {}
            for cid in rep[A_]:
                if r not in rep[A_][cid] or r not in rep[B_][cid]:
                    continue
                va, vb = rep[A_][cid][r], rep[B_][cid][r]
                if not (np.isfinite(va).any() and np.isfinite(vb).any()):
                    continue
                d = va - vb
                pt = pts[A_].get(r, float("nan")) - pts[B_].get(r, float("nan"))
                cells[cid] = ci_sum(d, pt, infl17)
            if cells:
                res["delta"][key]["metrics"][r] = cells
                res["delta"][key]["point"][r] = round(
                    pts[A_].get(r, float("nan")) - pts[B_].get(r, float("nan")), 8)
    # LUAT D1/D2
    for (A_, B_) in PAIRS:
        key = "%s-%s" % (A_, B_)
        if key not in res["delta"]:
            continue
        rec = {}
        for r in RULERS:
            c = res["delta"][key]["metrics"].get(r, {}).get(cfg_id(*MAIN))
            if c is None:
                continue
            rec[r] = {"d": c["point"], "out": c["out"], "dir": c["dir"],
                      "width_rel": c["width_rel"]}
        res["rule"][key] = rec
    # D1: doi tuong X co alpha khong-duoi?
    d1 = {}
    for o in objs:
        if o in ("45deploy", "V1"):
            continue
        ok = []
        ra = res["rule"].get("%s-45deploy" % o, {})
        rb = res["rule"].get("%s-V1" % o, {})
        for r in RULERS:
            a, b = ra.get(r), rb.get(r)
            if a and b and a["out"] and b["out"] and a["dir"] == b["dir"] and a["dir"] != 0:
                ok.append(r)
        d1[o] = {"thuoc_dat": ok, "n": len(ok), "qua_D1": len(ok) >= 2}
    # D2: hieu chuan THUOC bang 2 doi chung bat buoc
    d2 = {}
    for r in RULERS:
        hits = []
        for key in ("A45-45deploy", "V5-V1"):
            c = res["rule"].get(key, {}).get(r)
            if c and c["out"]:
                hits.append(key)
        d2[r] = {"doi_chung_ngoai_CI": hits, "phan_giai_duoc": len(hits) == 0}
    res["D1"] = d1
    res["D2"] = d2
    # bang TIEN: net/tick + tran 70% (3 cach) x 4 muc phi (chi o cau hinh CHINH)
    fee_tab = {}
    cid = cfg_id(*MAIN)
    for o in objs:
        m = rep[o][cid]["net_tick"].astype(np.float64)
        pt = pts[o]["net_tick"]
        gm = 100 * S0 * pts[o]["d_mean"]
        gp = 100 * S0 * pts[o]["d_p95"]
        gx = 100 * S0 * pts[o]["d_max"]
        rec = {"d_mean": round(pts[o]["d_mean"], 3), "d_p95": round(pts[o]["d_p95"], 1),
               "d_max": int(pts[o]["d_max"]), "gross_anchor": {"mean": round(gm, 2),
               "p95": round(gp, 2), "max": round(gx, 2)}, "fees": {}}
        sz = {"A_mean": CAP / gm, "B95": CAP / gp, "Bmax": CAP / gx}
        rec["size"] = {k: round(v, 4) for k, v in sz.items()}
        for f in FEES:
            ptk = pt - (f - F_DEC) * K
            mf = m - (f - F_DEC) * K
            e = {"net_tick": ci_sum(mf, ptk, infl17)}
            for meth in CAPM:
                e["sized_" + meth] = ci_sum(2.0 * sz[meth] * mf,
                                            2.0 * sz[meth] * ptk, infl17)
            rec["fees"]["%.3f" % f] = e
        fee_tab[o] = rec
    res["money"] = fee_tab
    json.dump(res, open(outfile, "w"), indent=1, default=str)
    log("### JSON -> %s (%.1f KB)" % (outfile, os.path.getsize(outfile) / 1e3))
    return res


def rnd(o, nd=6):
    if isinstance(o, float):
        return None if o != o else round(o, nd)
    if isinstance(o, dict):
        return {k: rnd(v, nd) for k, v in o.items()}
    if isinstance(o, list):
        return [rnd(v, nd) for v in o]
    return o


def stage_publish(outs, dst, extra=None):
    """Gop rep_*.json (da tinh) -> 1 JSON gon cho repo."""
    J = {"note": "PREREG_TAIL_ROBUST_RULERS; xem docs/result/RESULT_TAIL_ROBUST_RULERS.md",
         "runs": {}}
    for name, p in outs.items():
        j = json.load(open(p))
        J["runs"][name] = {"n_tick": j["n_tick"], "objs": j["objs"], "k_ruler": j["k_ruler"],
                           "k_obj": j["k_obj"],
                           "inflate": {k: j[k] for k in ("inflate_k17", "inflate_k10")},
                           "f": j["f"], "K": j["K"], "fees": j["fees"], "cap": j.get("cap"),
                           "D1": j["D1"], "D2": j["D2"], "money": j["money"],
                           "level": j["level"], "delta": j["delta"],
                           "quant_cfgs": j["quant_cfgs"]}
    if extra:
        J["validity"] = extra
    with open(dst, "w") as fh:
        json.dump(rnd(J), fh, separators=(",", ":"), default=str)
    log("### PUBLISH %s (%.0f KB)" % (dst, os.path.getsize(dst) / 1e3))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="level")
    ap.add_argument("--pool", default="p32")
    ap.add_argument("--tag", default="")
    ap.add_argument("--objects", default="")
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    tag = a.tag or a.pool
    os.makedirs(TMP, exist_ok=True)
    if a.pool == "p32":
        P = load_pool(POOL_P32, "p32")
    else:
        # B2 = pool MO RONG = P32 ∪ tap coin MOI (nhu RESULT_OFI_MONEY §1), KHONG chi file `_ext`
        A_ = pd.read_parquet(POOL_P32, columns=["ts", "symId", "gross", "exit_ts"],)
        B_ = pd.read_parquet(POOL_EXT, columns=["ts", "symId", "gross", "exit_ts"])
        U = pd.concat([A_, B_], ignore_index=True).drop_duplicates(["ts", "symId"], keep="first")
        tmp = os.path.join(TMP, "pool_ext_union.parquet")
        U.to_parquet(tmp, index=False)
        B = load_pool(tmp, "ext")
        log("  ### pool_ext union: P32=%d + NEW=%d -> %d dong | %d tick" % (
            len(A_), len(B_), len(U), len(B["ticks"])))
        del A_, B_, U
        P = B
    objs = [x for x in a.objects.split(",") if x] or (OBJECTS if a.pool == "p32"
                                                     else ["ofi_candidate", "ofi_baseline_fresh",
                                                           "ofi_noise", "45deploy", "S1"])
    log("### pool=%s rows=%d tick=%d | objs=%d" % (a.pool, len(P["gross"]), len(P["ticks"]), len(objs)))
    SC = stage_scores(P, "pool_" + a.pool, objs)
    for o in objs:                      # chuan hoa CHIEU: diem CAO = TOT cho MOI doi tuong
        SC[o] = SC[o] * ORIENT.get(o, 1)
    tk = common_ticks(P, SC, objs)
    if len(tk) < len(P["ticks"]):
        m = np.isin(P["ts"], tk)
        SC = {o: SC[o][m] for o in objs}
        P = subset_pool(P, tk)
        log("  ### pool sau loc: %d dong | %d tick" % (len(P["gross"]), len(P["ticks"])))
    if a.stage == "level":
        stage_level(P, SC, objs, tag)
    elif a.stage == "publish":
        src = {"p32": "/tmp/trr/rep_full.json", "p32mrb": "/tmp/trr/rep_mrb.json",
               "pool_ext_B2": "/tmp/trr/rep_ext.json"}
        src = {k: v for k, v in src.items() if os.path.exists(v)}
        stage_publish(src, a.out or "docs/result/tail_robust_rulers.json",
                      extra=(json.load(open("/tmp/trr/validate.json"))
                             if os.path.exists("/tmp/trr/validate.json") else None))
    else:
        out = a.out or ("docs/result/tail_robust_rulers.json" if a.pool == "p32"
                        else "docs/result/tail_robust_rulers_ext.json")
        stage_report(P, tag, objs, out)


if __name__ == "__main__":
    main()
