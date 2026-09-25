#!/usr/bin/env python3
"""model_ruler.py — THƯỚC ĐÁNH GIÁ **MODEL** (ranker), TÁCH KHỎI thước HỆ THỐNG (sim).

Pre-reg: `docs/prereg/PREREG_MODEL_RULER.md` (commit cc22253). Read-only:
**KHÔNG train, KHÔNG sim, KHÔNG chạm ONNX/LIVE.** Chỉ đọc artifact ĐÃ CÓ.

Ý tưởng: SIM trả lời "model này có làm HỆ THỐNG tốt hơn trong HIỆN TRẠNG không" (bị thiên kiến theo
hiện trạng + theo scale score ⇒ phải re-calibrate gate). Thước này trả lời câu hỏi KHÁC, độc lập:
**"tập feature mới có phải RANKER tốt hơn không"** — và nó BẤT BIẾN với mọi biến đổi tăng nghiêm ngặt
của score (T2), tức là nó đo THỨ TỰ, không đo calibration.

Hai chế độ:
  **RAW** (`--bins DIR --labels DIR`): đủ bộ chỉ số M1–M10 (thêm AUC / pairwise / decile / gross-net).
  **AGG** (`--ticks FILE`): chỉ M1–M4 — dùng lại per-tick parquet kernel đã xuất (không giữ bins thô).

Chỉ số (định nghĩa y pre-reg §2):
  M1 rank-IC · M2 |rank-IC| · M3 lift@8 (K=8) · M4 precision@8 · M5 AUC within-tick ·
  M6 pairwise accuracy `P(s_A>s_B | y_A>y_B)` · M7 decile monotonicity · M8 gross@8 · M9 net@8
  (net = gross − fee 2×0.002 − slip 2×0.003 = 0.008; **CHƯA** trừ funding — xem pre-reg §2) ·
  M10 net_lift@8 · M11 drift (first-8-fold − last-8-fold) · M12 bảng theo fold / theo năm.

Usage:
  python3 model_ruler.py ruler --name 45deploy --bins /home/ubuntu/claudedata/predwf_G015x26 \
      [--labels /home/ubuntu/label_15m] [--self-tests] [--out J] [--per-tick P] [--folds N]
  python3 model_ruler.py ruler --name A44 --ticks <parquet> [--out J] [--per-tick P]
  python3 model_ruler.py validate [--out J] [--skip-selftest]
"""
import argparse
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import c3_rates as C                       # noqa: E402  (BLOCK_H/NREP/SEED/inflate — KHONG bia)
import stage2_score as S2                  # noqa: E402  (block_boot_mean — dung lai, khong viet lai)
import gd92xexit_score as G                # noqa: E402  (LEGACY = 1.21, hang so co san)

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("model_ruler")

FOLDS = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401", "20230701",
         "20231001", "20240101", "20240401", "20240701", "20241001", "20250101", "20250401",
         "20250701", "20251001"]
THR = 0.015
# Chi phi round-trip THEO CODE (khong theo comment): Configs.java RATE_FEE = 0.002f
# (comment ghi ro 'da sua thanh 2 chan') + SLIPPAGE_RATE = 0.003f ap 2 chan (x2)
# => 0.002 + 2*0.003 = 0.008 (khop pre-reg §2 M9 'fee 0,002 + slip 0,003x2 = 0,008').
# LUU Y: dong comment o Configs.java:164 ('2*RATE_FEE + 2*SLIPPAGE_RATE') cong nham thanh 0.010;
# cong thuc THAT trong HPOFitnessCalculatorV4 la RATE_FEE + 2*SLIPPAGE_RATE.
FEE_RT = 0.002 + 2 * 0.003      # = 0.008 round-trip
K_SEL = 8                                  # K selector
BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4"), ("z", ">f4", 3)])
SELF_SEED = 20260905
TZ = "Asia/Ho_Chi_Minh"

# Chỉ số dùng cho LUẬT §5 (chiều TỐT = lớn hơn)
PRIMARY = "lift8"
SECOND = "abs_ic"
RAW_METRICS = ["ic", "abs_ic", "lift8", "prec8", "auc", "pacc", "dec_rho", "dec_mono",
               "gross8", "net8", "net_lift8",
               # MO TA THEM (them SAU pre-reg, KHONG dung trong luat §5): moc so sanh gross cua tick
               "gross_all", "gross_lift8"]
AGG_METRICS = ["ic", "abs_ic", "lift8", "prec8"]


# ─────────────────────────────── tiện ích ───────────────────────────────

def year_of(ts_ms):
    return pd.to_datetime(pd.Series(np.asarray(ts_ms)), unit="ms", utc=True) \
             .dt.tz_convert(TZ).dt.year.to_numpy()


def ci_mean(v, ts, inflate=1.0):
    """CI block-72h cua TRUNG BINH, do rong quyet dinh = legacy 1.21 (pre-reg §3)."""
    v = np.asarray(v, dtype=np.float64)
    ts = np.asarray(ts, dtype=np.int64)
    m = np.isfinite(v)
    if m.sum() == 0:
        return dict(mean=float("nan"), raw=[float("nan")] * 2, infl=[float("nan")] * 2)
    lo, hi = S2.block_boot_mean(v[m], ts[m])
    mu = float(v[m].mean())
    return dict(mean=mu, raw=[lo, hi],
                infl=[mu - (mu - lo) * G.LEGACY, mu + (hi - mu) * G.LEGACY],
                honest_infl=[mu - (mu - lo) * inflate, mu + (hi - mu) * inflate],
                n=int(m.sum()))


def decide(ci):
    """Ngoai CI = ngoai CA HAI do rong (pre-reg §3). Tra (out_raw, out_legacy, out_both, huong)."""
    o1 = ci["raw"][0] > 0 or ci["raw"][1] < 0
    o2 = ci["infl"][0] > 0 or ci["infl"][1] < 0
    if not (o1 and o2):
        return o1, o2, False, 0
    return o1, o2, True, (1 if ci["mean"] > 0 else -1)


# ─────────────────────────── RAW: dựng per-tick ───────────────────────────

def load_labels(labels_dir):
    """Nhan `retEnd_4h` (GROSS) tu /home/ubuntu/label_15m/*.pb — y het arm44_ruler45.py."""
    import funding_label_pb as FLPB
    smap = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    fs = sorted(f for f in os.listdir(labels_dir)
                if f.startswith("funding_label_") and f.endswith(".pb")
                and f.split("_")[2] < "20260101")
    tl, sl, vl = [], [], []
    for fn in fs:
        d = FLPB.read_label(os.path.join(labels_dir, fn),
                            usecols=["tEpochMs", "symbol", "retEnd_4h"])
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts = d.tEpochMs.to_numpy(np.int64)[k]
        v = d.retEnd_4h.to_numpy(np.float64)[k]
        ok = np.isfinite(v)
        tl.append(ts[ok]); sl.append(sid.to_numpy()[k][ok].astype(np.int32)); vl.append(v[ok])
        del d
    tl = np.concatenate(tl); sl = np.concatenate(sl); vl = np.concatenate(vl)
    order = np.argsort(tl * 1024 + sl, kind="stable")
    LK = (tl * 1024 + sl)[order]; LV = vl[order]
    LOG.info("    nhan: %d dong (retEnd_4h notna) tu %d file", len(LK), len(fs))
    return LK, LV


def join_labels_per_fold(bins_dir, LK, LV, folds):
    """Doc bins tung fold + join nhan -> (ts, p, y, fold) gop. Dung DUNG format bins 26 B/rec."""
    TS, P, Y, F = [], [], [], []
    for f in folds:
        bp = os.path.join(bins_dir, "predict_wf_%s.bin" % f)
        arr = np.fromfile(bp, dtype=BIN_DT)
        ts = arr["ts"].astype(np.int64); sy = arr["sym"].astype(np.int64)
        p = arr["p"].astype(np.float32).astype(np.float64)
        key = ts * 1024 + sy
        ip = np.clip(np.searchsorted(LK, key), 0, len(LK) - 1)
        hit = LK[ip] == key
        y = np.full(len(key), np.nan)
        y[hit] = LV[ip[hit]]
        m = np.isfinite(y)
        TS.append(ts[m]); P.append(p[m]); Y.append(y[m]); F.append(np.full(int(m.sum()), f))
        del arr
    return (np.concatenate(TS), np.concatenate(P), np.concatenate(Y), np.concatenate(F))


def tick_metrics(ts, p, y, with_pacc=True):
    """Bo chi so M1–M10 THEO TUNG TICK (chi tick >= 2 coin). Tra DataFrame 1 dong/tick.

    Moi dai luong theo tick deu la Series CHUNG index (ts) => khong lech hang.
    """
    order = np.argsort(ts, kind="stable")
    ts, p, y = np.asarray(ts)[order], np.asarray(p)[order], np.asarray(y)[order]
    d = pd.DataFrame({"ts": ts, "p": p, "y": y})
    d["yb"] = (d.y > THR).astype(np.float64)
    d["ybn"] = ((d.y - FEE_RT) > THR).astype(np.float64)
    d = d[d.groupby("ts")["p"].transform("size") >= 2].copy()

    G0 = d.groupby("ts", sort=True)
    D = d
    D["_rp"] = G0["p"].rank(method="average")
    D["_ry"] = G0["y"].rank(method="average")
    G1 = D.groupby("ts", sort=True)
    D["_num"] = (D._rp - G1["_rp"].transform("mean")) * (D._ry - G1["_ry"].transform("mean"))
    D["_s1"] = (D._rp - G1["_rp"].transform("mean")) ** 2
    D["_s2"] = (D._ry - G1["_ry"].transform("mean")) ** 2
    D["_srp"] = D._rp * D.yb
    G = D.groupby("ts", sort=True)
    size_s = G.size().astype(np.float64)
    ic = G["_num"].sum() / np.sqrt(G["_s1"].sum() * G["_s2"].sum())
    base_s = G["yb"].mean()
    base_n_s = G["ybn"].mean()
    npos = G["yb"].sum()
    nneg = size_s - npos
    # M5 AUC within-tick = Mann-Whitney `P(score_pos > score_neg)`, dong hang tinh 0.5
    auc = (G["_srp"].sum() - npos * (npos + 1) / 2.0) / (npos * nneg).replace(0, np.nan)

    top = D.sort_values(["ts", "p"], ascending=[True, False]).groupby("ts").head(K_SEL)
    TG = top.groupby("ts", sort=True)
    prec8 = TG["yb"].mean().reindex(size_s.index)
    prec8n = TG["ybn"].mean().reindex(size_s.index)
    gross8 = TG["y"].mean().reindex(size_s.index)
    gross_all = G["y"].mean()                       # MO TA: mean y cua TOAN tick (moc so sanh)
    n8 = TG.size().reindex(size_s.index)

    # M7 decile: 10 decile theo RANK score trong tick (khong theo gia tri tho)
    nsel = D.groupby("ts", sort=True)["p"].transform("size").to_numpy(np.float64)
    dec = np.minimum((D._rp.to_numpy() * 10.0 / (nsel + 1)).astype(int), 9)
    md = pd.DataFrame({"ts": D.ts.to_numpy(), "dec": dec, "y": D.y.to_numpy()})
    md = md.groupby(["ts", "dec"])["y"].mean().unstack("dec").reindex(
        index=size_s.index, columns=range(10))
    D.drop(columns=["_num", "_s1", "_s2", "_srp"], inplace=True)   # giam dinh OOM
    ry2 = md.rank(axis=1, method="average")
    mdv = md.to_numpy(); ry2v = ry2.to_numpy()
    ok = np.isfinite(mdv)
    cnt = ok.sum(axis=1).astype(np.float64)
    dc0 = np.where(ok, np.arange(10, dtype=np.float64), 0.0)
    ry0 = np.where(ok, ry2v, 0.0)
    sxy = (dc0 * ry0).sum(axis=1); sx = dc0.sum(axis=1); sy2 = ry0.sum(axis=1)
    sxx = (dc0 * dc0).sum(axis=1); syy = (ry0 * ry0).sum(axis=1)
    den = np.sqrt(np.maximum((cnt * sxx - sx ** 2) * (cnt * syy - sy2 ** 2), 0.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        dec_rho = np.where(den > 0, (cnt * sxy - sx * sy2) / den, np.nan)
    dadj = np.diff(mdv, axis=1)
    oka = np.isfinite(dadj)
    mono = np.where(oka, (dadj >= 0).astype(np.float64), 0.0).sum(axis=1)
    denom = oka.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        dec_mono = np.where(denom > 0, mono / denom, np.nan)

    R = pd.DataFrame({
        "n_coin": size_s, "ic": ic, "auc": auc, "n8": n8,
        "prec8": prec8, "base": base_s, "base_net": base_n_s, "gross8": gross8,
        "gross_all": gross_all,
        "net_lift8": prec8n - base_n_s, "dec_rho": dec_rho, "dec_mono": dec_mono,
    })
    R["lift8"] = R.prec8 - R.base
    R["net8"] = R.gross8 - FEE_RT
    R["gross_lift8"] = R.gross8 - R.gross_all
    R["abs_ic"] = R.ic.abs()
    R = R.reset_index().rename(columns={"index": "ts"})
    R["ts"] = R.ts.astype(np.int64)
    if with_pacc:
        from scipy.stats import kendalltau
        pv = d.p.to_numpy(); yv = d.y.to_numpy(); tsv = d.ts.to_numpy()
        b = np.flatnonzero(np.diff(tsv)) + 1
        st = np.concatenate(([0], b)); en = np.concatenate((b, [len(tsv)]))
        pac = np.full(len(st), np.nan)
        for i in range(len(st)):
            s, e = st[i], en[i]
            t = kendalltau(pv[s:e], yv[s:e], nan_policy="omit").statistic
            if np.isfinite(t):
                pac[i] = 0.5 + 0.5 * float(t)       # P(s_A>s_B | y_A>y_B), dong hang = 0.5
        R["pacc"] = pac
    return R.sort_values("ts").reset_index(drop=True)


def ruler_raw(bins_dir, labels_dir, folds, self_tests=False):
    """RAW theo TUNG FOLD (streaming) — tranh OOM: khong bao gio giu ca 16 fold cung luc."""
    t0 = time.time()
    LK, LV = load_labels(labels_dir)
    keys = ["self", "shuffled", "unif", "logit"] if self_tests else ["self"]
    parts = {k: [] for k in keys}
    rng = np.random.default_rng(SELF_SEED)
    for f in folds:
        ts, p, y, fold = join_labels_per_fold(bins_dir, LK, LV, [f])
        foldmap = pd.Series(fold).groupby(pd.Series(ts)).first()
        foldmap.index = foldmap.index.astype(np.int64)

        def with_fold(R, _fm=foldmap):
            R["fold"] = R.ts.map(_fm)
            return R

        parts["self"].append(with_fold(tick_metrics(ts, p, y)))
        if self_tests:
            ps = p.copy()
            b = np.flatnonzero(np.diff(ts)) + 1
            st = np.concatenate(([0], b)); en = np.concatenate((b, [len(ts)]))
            for i in range(len(st)):
                s, e = st[i], en[i]
                ps[s:e] = rng.permutation(ps[s:e])
            parts["shuffled"].append(with_fold(tick_metrics(ts, ps, y)))
            # T2: bien doi TANG NGHIEM NGAT (quantile->uniform, logit) — phai ra DUNG so cu
            rk = pd.Series(p).groupby(pd.Series(ts)).rank(method="average").to_numpy()
            nn = pd.Series(rk).groupby(pd.Series(ts)).transform("size").to_numpy(np.float64)
            u = np.clip((rk - 0.5) / nn, 1e-7, 1 - 1e-7)
            parts["unif"].append(with_fold(tick_metrics(ts, u, y)))
            parts["logit"].append(with_fold(tick_metrics(ts, np.log(u / (1 - u)), y)))
            del ps, rk, nn, u
        LOG.info("    fold %s: %d dong, %d tick | %.0fs", f, len(ts), len(parts["self"][-1]),
                 time.time() - t0)
        del ts, p, y, fold
    out = {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}
    LOG.info("  RAW xong %d bien the | %d tick | %.0fs", len(out), len(out["self"]),
             time.time() - t0)
    return out


def ruler_agg(ticks_file):
    """AGG: doc per-tick parquet kernel da xuat. Chap nhan `prec8` hoac `t8` (ten cot kernel)."""
    d = pd.read_parquet(ticks_file)
    d["ts"] = d.ts.astype(np.int64)
    if "prec8" not in d.columns:
        if "t8" in d.columns:
            d["prec8"] = d["t8"].astype(np.float64)
        elif "base" in d.columns and "lift8" in d.columns:
            d["prec8"] = d["base"] + d["lift8"]
    need = {"ts", "ic", "lift8", "prec8", "base", "n_coin", "n8"}
    miss = need - set(d.columns)
    if miss:
        raise SystemExit("thieu cot %s trong %s" % (sorted(miss), ticks_file))
    d["abs_ic"] = d.ic.abs()
    if "fold" not in d.columns:
        d["fold"] = "?"
    return d.sort_values("ts").reset_index(drop=True)


# ─────────────────────────── tóm tắt + delta ───────────────────────────

def summarize(df, tag, metrics, inflate=1.0):
    y = year_of(df.ts.to_numpy())
    df = df.assign(year=y)
    out = {"tag": tag, "n_tick": int(len(df)), "n_coin_mean": float(df.n_coin.mean()),
           "metrics": {}, "by_fold": {}, "by_year": {}, "drift": {}}
    for m in metrics:
        if m not in df.columns:
            continue
        out["metrics"][m] = ci_mean(df[m].to_numpy(), df.ts.to_numpy(), inflate)
    for m in (PRIMARY, "ic") if "ic" in df.columns else (PRIMARY,):
        if m not in df.columns:
            continue
        out["by_fold"][m] = {str(k): round(float(v), 6) for k, v in
                             df.groupby("fold")[m].mean().items()}
        out["by_year"][m] = {str(k): round(float(v), 6) for k, v in
                             df.groupby("year")[m].mean().items()}
        fl = sorted(df.fold.unique())
        if len(fl) >= 2:
            h = len(fl) // 2
            a = df[df.fold.isin(fl[:h])][m].mean(); bb = df[df.fold.isin(fl[h:])][m].mean()
            out["drift"][m] = round(float(a - bb), 6)
    return out


def delta(dfa, dfb, metrics, tag):
    """Δ ghép cặp THEO TICK (chỉ tick chung), CI block-72h. a - b."""
    A = dfa.set_index("ts"); B = dfb.set_index("ts")
    idx = A.index.intersection(B.index)
    res = {"tag": tag, "n_tick_common": int(len(idx)), "metrics": {}}
    for m in metrics:
        if m not in A.columns or m not in B.columns:
            continue
        dl = (A.loc[idx, m] - B.loc[idx, m]).astype(np.float64)
        ci = ci_mean(dl.to_numpy(), dl.index.to_numpy())
        o1, o2, both, dirn = decide(ci)
        res["metrics"][m] = dict(mean=ci["mean"], raw=ci["raw"], infl=ci["infl"],
                                 out_raw=bool(o1), out_both=bool(both), direction=dirn)
    return res


def verdict(cand_vs_ctrl1, cand_vs_ctrl2, label):
    """LUAT §5: DOI DUOC MOC khi dPrimary > 0 NGOAI CI vs CA HAI VA d|IC| khong bat loi ngoai CI."""
    def fav(d, m, want_pos=True):
        x = d["metrics"].get(m)
        if not x or not x["out_both"]:
            return False
        return x["mean"] > 0 if want_pos else True

    def bad(d, m):
        x = d["metrics"].get(m)
        return bool(x and x["out_both"] and x["mean"] < 0)

    p1 = fav(cand_vs_ctrl1, PRIMARY); p2 = fav(cand_vs_ctrl2, PRIMARY)
    s1 = bad(cand_vs_ctrl1, SECOND); s2 = bad(cand_vs_ctrl2, SECOND)
    change = bool(p1 and p2 and not s1 and not s2)
    detail = dict(lift8_gt_ctrl1=bool(p1), lift8_gt_ctrl2=bool(p2),
                  ic_worse_ctrl1=bool(s1), ic_worse_ctrl2=bool(s2))
    LOG.info("  %-28s => %s  %s", label, "DOI DUOC MOC" if change else "KEEP (NULL)", detail)
    return dict(verdict="CHANGE" if change else "KEEP", detail=detail)


# ─────────────────────────────── CLI ───────────────────────────────

def cmd_ruler(a):
    infl = C.inflate(1) if a.k == 1 else C.inflate(a.k)
    LOG.info("### MODEL RULER — arm `%s` | k=%d inflate=%.6f (=CI goc) | do rong quyet dinh = legacy %.2f",
             a.name, a.k, infl, G.LEGACY)
    if a.bins:
        res = ruler_raw(a.bins, a.labels, FOLDS[:a.folds] if a.folds else FOLDS, a.self_tests)
        metrics = RAW_METRICS
        tag = a.name
        out = {"name": a.name, "mode": "RAW", "bins": a.bins, "labels": a.labels,
               "k": a.k, "folds": FOLDS[:a.folds] if a.folds else FOLDS}
        for key, df in res.items():
            if a.per_tick and key == "self":
                df.to_parquet(a.per_tick, index=False)
                LOG.info("  per-tick -> %s (%d dong)", a.per_tick, len(df))
            out[key] = summarize(df, tag + ("" if key == "self" else "|" + key), metrics, infl)
        if a.self_tests:
            LOG.info("\n[T1/T2] TU-KIEM THUOC")
            for m in RAW_METRICS:
                v = {k: out[k]["metrics"].get(m, {}).get("mean", float("nan"))
                     for k in ("self", "shuffled", "unif", "logit")}
                d2 = max(abs(v["self"] - v["unif"]), abs(v["self"] - v["logit"]))
                LOG.info("   %-9s self=%+.6f | shuffle=%+.6f | T2 max|Δ| = %.2e %s",
                         m, v["self"], v["shuffled"], d2, "OK" if d2 < 1e-9 else "*** FAIL ***")
            out["selftest_T2_max_abs_delta"] = float(max(
                abs(out["self"]["metrics"].get(m, {}).get("mean", 0)
                    - out[x]["metrics"].get(m, {}).get("mean", 0))
                for m in RAW_METRICS for x in ("unif", "logit")))
    else:
        d = ruler_agg(a.ticks)
        out = {"name": a.name, "mode": "AGG", "ticks": a.ticks, "k": a.k}
        if a.per_tick:
            d.to_parquet(a.per_tick, index=False)
        out["self"] = summarize(d, a.name, AGG_METRICS, infl)
    s = out["self"]
    LOG.info("  n_tick=%d | n_coin=%.1f", s["n_tick"], s["n_coin_mean"])
    for m in (AGG_METRICS if a.ticks else RAW_METRICS):
        x = s["metrics"].get(m)
        if x:
            LOG.info("   %-9s = %+.6f  [%+.6f,%+.6f] raw | [%+.6f,%+.6f] legacy1.21",
                     m, x["mean"], x["raw"][0], x["raw"][1], x["infl"][0], x["infl"][1])
    LOG.info("   drift lift8 = %s | ic = %s", s["drift"].get("lift8"), s["drift"].get("ic"))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1, default=str)
        LOG.info("  JSON -> %s", a.out)
        if a.per_tick:
            LOG.info("  (per-tick parquet de tinh delta: %s)", a.per_tick)
    return out


PATHS = {
    "45deploy": ("/home/ubuntu/claudedata/predwf_G015x26", None),
    "A45": (None, "/home/ubuntu/kaggle_sim/out/a44out/A45_perfold_ticks.parquet"),
    "A44": (None, "/home/ubuntu/kaggle_sim/out/a44out/A44_perfold_ticks.parquet"),
    "V0": (None, "/home/ubuntu/claudedata/stage2_featvar_out/stage2/V0_perfold_ticks.parquet"),
    "V1": (None, "/home/ubuntu/claudedata/stage2_featvar_out/stage2/V1_perfold_ticks.parquet"),
    "V5": (None, "/home/ubuntu/claudedata/stage2_featvar_out/stage2/V5_perfold_ticks.parquet"),
}
TMP = "/tmp/model_ruler_out"


def cmd_validate(a):
    os.makedirs(TMP, exist_ok=True)
    t0 = time.time()
    LOG.info("### VALIDATE THUOC tren 5 arm (pre-reg §7) — KHONG train, KHONG sim")
    PT, SUM, RAWO, VF = {}, {}, {}, {}
    for name, (bins, ticks) in PATHS.items():
        pt = os.path.join(TMP, "%s_pertick.parquet" % name)
        paths = [pt] + ([os.path.join(TMP, "%s_%s_pertick.parquet" % (name, k))
                         for k in ("shuffled", "unif", "logit")] if bins else [])
        if a.reuse and all(os.path.exists(p) for p in paths):
            LOG.info("  [%s] REUSE per-tick cache (%s)", name, pt)
            df = pd.read_parquet(pt); df["ts"] = df.ts.astype(np.int64)
            if "abs_ic" not in df.columns:
                df["abs_ic"] = df.ic.abs()
            SUM[name] = summarize(df, name, AGG_METRICS, 1.0)
            PT[name] = df.sort_values("ts").reset_index(drop=True)
            if bins:
                RAWO[name] = {"self": summarize(df, name, RAW_METRICS, 1.0)}
                for k in ("shuffled", "unif", "logit"):
                    dk = pd.read_parquet(os.path.join(TMP, "%s_%s_pertick.parquet" % (name, k)))
                    dk["ts"] = dk.ts.astype(np.int64)
                    if "abs_ic" not in dk.columns:
                        dk["abs_ic"] = dk.ic.abs()
                    VF[k] = dk.sort_values("ts").reset_index(drop=True)
                    RAWO[name][k] = summarize(dk, "%s|%s" % (name, k), RAW_METRICS, 1.0)
            LOG.info("  [%s] REUSE | n_tick=%d ic=%+.6f lift8=%+.6f", name, len(df),
                     df.ic.mean(), df.lift8.mean())
            continue
        if bins:
            res = ruler_raw(bins, a.labels, FOLDS, a.self_tests)
            df = res["self"]; df.to_parquet(pt, index=False)
            RAWO[name] = {k: summarize(res[k], name + ("" if k == "self" else "|" + k),
                                       RAW_METRICS, 1.0) for k in res}
            for k in ("shuffled", "unif", "logit"):
                res[k].to_parquet(
                    os.path.join(TMP, "%s_%s_pertick.parquet" % (name, k)), index=False)
        else:
            df = ruler_agg(ticks); df.to_parquet(pt, index=False)
        PT[name] = df
        SUM[name] = summarize(df, name, AGG_METRICS, 1.0)
        LOG.info("  [%s] %s | n_tick=%d ic=%+.6f lift8=%+.6f", name,
                 "RAW" if bins else "AGG", len(df), df.ic.mean(), df.lift8.mean())

    # [T3] coverage — chi 5/6 ARM THAT (khong tinh ban bien the cua test)
    ref = PT["45deploy"].ts.to_numpy()
    cov = {k: bool(len(v) == len(ref) and (v.ts.to_numpy() == ref).all())
           for k, v in PT.items() if k in PATHS}
    LOG.info("\n[T3] COVERAGE / PROVENANCE (ts khop 45deploy): %s", cov)

    # [T1/T2] tu-kiem
    selftest = {}
    if a.self_tests:
        s = RAWO["45deploy"]
        LOG.info("\n[T1/T2] TU-KIEM THUOC")
        for m in RAW_METRICS:
            v = {k: s[k]["metrics"].get(m, {}).get("mean", float("nan"))
                 for k in ("self", "shuffled", "unif", "logit")}
            if not np.isfinite(v["self"]) or not np.isfinite(v["unif"]):
                continue
            d2 = max(abs(v["self"] - v["unif"]), abs(v["self"] - v["logit"]))
            LOG.info("   %-9s self=%+.6f shuffle=%+.6f | T2 max|Δ|=%.2e %s",
                     m, v["self"], v["shuffled"], d2, "OK" if d2 < 1e-9 else "*** FAIL ***")
        t2 = max(abs(s["self"]["metrics"].get(m, {}).get("mean", 0.0)
                     - s[x]["metrics"].get(m, {}).get("mean", 0.0))
                 for m in RAW_METRICS if m in s["self"]["metrics"]
                 and all(m in s[x]["metrics"] for x in ("unif", "logit"))
                 for x in ("unif", "logit"))
        if not VF:
            VF["shuffled"] = res["shuffled"]
        dsh = delta(VF["shuffled"], PT["45deploy"], AGG_METRICS, "shuffled - 45deploy")
        selftest = {"T2_max_abs_delta": float(t2),
                    "T2_pass": bool(t2 < 1e-9),
                    "T1_lift8": s["shuffled"]["metrics"]["lift8"]["mean"],
                    "T1_ic": s["shuffled"]["metrics"]["ic"]["mean"],
                    "T1_delta_vs_deploy": dsh}
        LOG.info("   T2 PASS=%s (max|Δ|=%.2e) | T1: lift8_shuffled=%+.6f ic_shuffled=%+.6f",
                 selftest["T2_pass"], t2, selftest["T1_lift8"], selftest["T1_ic"])

    # [V-A..V-E] delta + verdict
    M = AGG_METRICS
    D = {}
    pairs = [("A44", "45deploy"), ("A44", "A45"), ("A45", "45deploy"),
             ("V0", "45deploy"), ("V0", "V5"), ("V5", "V0"), ("V1", "V0"), ("V5", "45deploy"),
             ("V5", "V1"), ("V1", "45deploy")]
    LOG.info("\n[DELTA] ghep cap theo tick, CI block-%dh %d rep seed %d (ngoai CI = ngoai CA HAI do rong)",
             C.BLOCK_H, C.NREP, C.SEED)
    for x, b in pairs:
        d = delta(PT[x], PT[b], M, "%s - %s" % (x, b))
        D["%s_minus_%s" % (x, b)] = d
        bits = []
        for m in M:
            y = d["metrics"].get(m)
            if y:
                bits.append("%s=%+.6f%s" % (m, y["mean"], "*" if y["out_both"] else ""))
        LOG.info("  %-16s %s", "%s - %s" % (x, b), " | ".join(bits))

    LOG.info("\n[V-A..V-C] LUAT §5 (CHI so chinh = %s; phu = %s; * = ngoai CI ca hai do rong)",
             PRIMARY, SECOND)
    V = {}
    V["V-A"] = verdict(D["A44_minus_45deploy"], D["A44_minus_A45"], "V-A: A44 vs {45deploy, A45}")
    V["V-B"] = verdict(D["V0_minus_45deploy"], D["V0_minus_V5"], "V-B: V0 vs {45deploy, V5(noise)}")
    vc = D["V5_minus_V0"]["metrics"].get(PRIMARY)
    V["V-C_as_written"] = dict(
        test="V5(nhieu) co 'thang' V0 ngoai CI khong (dinh nghia TRONG pre-reg §7)",
        noise_beats_real=bool(vc and vc["out_both"] and vc["mean"] > 0), detail=vc)
    vcc = D["V5_minus_V1"]["metrics"].get(PRIMARY)
    V["V-C_corrected"] = dict(
        test="BUOC NHIEU THUAN (V5 - V1): cot nhieu co them gi khong?",
        noise_adds_signal=bool(vcc and vcc["out_both"] and vcc["mean"] > 0), detail=vcc)
    LOG.info("  V-C (NGUYEN VAN pre-reg §7): V5>V0 ngoai CI? %s (Δlift8=%+.6f)",
             "CO *** BAY OFI ***" if V["V-C_as_written"]["noise_beats_real"] else "KHONG (PASS)",
             vc["mean"] if vc else float("nan"))
    LOG.info("  V-C' (SUA — V5 ⊇ V1 ⊇ V0 nen 'V5>V0' KHONG phai phep kiem bay OFI): "
             "buoc nhieu thuan V5-V1 co them tin hieu? %s (Δlift8=%+.6f)",
             "CO *** BAY OFI ***" if V["V-C_corrected"]["noise_adds_signal"] else "KHONG (PASS)",
             vcc["mean"] if vcc else float("nan"))
    V["V-D"] = dict(detail=D["A45_minus_45deploy"]["metrics"].get(PRIMARY))
    LOG.info("  V-D: nen nhieu retrain A45-45deploy Δlift8=%+.6f", V["V-D"]["detail"]["mean"])
    V["V-E"] = dict(T1_lift8=selftest.get("T1_lift8"), T2_pass=selftest.get("T2_pass"))
    selfok = bool(selftest.get("T2_pass", False)
                  and abs(selftest.get("T1_lift8", 9)) < 0.005)
    kep_a = V["V-A"]["verdict"] == "KEEP"; kep_b = V["V-B"]["verdict"] == "KEEP"
    repro_lit = bool(kep_a and kep_b and not V["V-C_as_written"]["noise_beats_real"] and selfok)
    repro_fix = bool(kep_a and kep_b and not V["V-C_corrected"]["noise_adds_signal"] and selfok)
    LOG.info("\n=== KET LUAN VALIDATE: ruler TU NOI LAI duoc `GIU 45`? ===")
    LOG.info("    NGUYEN VAN pre-reg §7 (dung V-C nhu da viet): %s", "CO" if repro_lit else "KHONG")
    LOG.info("    SAU KHI SUA V-C (V5-V1, khai bao ro trong result): %s",
             "CO" if repro_fix else "KHONG")
    LOG.info("    V-A=%s V-B=%s V-C=%s V-C'=%s V-E(T1/T2)=%s", V["V-A"]["verdict"],
             V["V-B"]["verdict"],
             "PASS" if not V["V-C_as_written"]["noise_beats_real"] else "FAIL",
             "PASS" if not V["V-C_corrected"]["noise_adds_signal"] else "FAIL", selfok)
    LOG.info("    (V-A KEEP = ruler NOI LAI duoc quyet dinh cua vong ARM44: A44 KHONG phai ranker tot hon)")
    out = {"k": 1, "inflate": C.inflate(1), "legacy": G.LEGACY, "block_h": C.BLOCK_H,
           "nrep": C.NREP, "seed": C.SEED, "thr": THR, "fee_rt": FEE_RT, "k_sel": K_SEL,
           "coverage": cov, "summary": SUM, "raw_summary": RAWO, "delta": D,
           "verdicts": V, "selftest": selftest,
           "reproduces_KEEP45_as_written": bool(repro_lit),
           "reproduces_KEEP45_after_VC_fix": bool(repro_fix)}
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1, default=str)
        LOG.info("    JSON -> %s | %.0fs", a.out, time.time() - t0)
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("ruler")
    r.add_argument("--name", required=True)
    r.add_argument("--bins"); r.add_argument("--ticks")
    r.add_argument("--labels", default="/home/ubuntu/label_15m")
    r.add_argument("--out"); r.add_argument("--per-tick")
    r.add_argument("--k", type=int, default=1)
    r.add_argument("--folds", type=int, default=0)
    r.add_argument("--self-tests", action="store_true")
    v = sub.add_parser("validate")
    v.add_argument("--labels", default="/home/ubuntu/label_15m")
    v.add_argument("--out"); v.add_argument("--skip-selftest", action="store_true")
    v.add_argument("--reuse", action="store_true",
                   help="dung lai per-tick cache trong %s (KHONG tinh lai)" % TMP)
    a = ap.parse_args()
    if a.cmd == "ruler":
        cmd_ruler(a)
    else:
        a.self_tests = not a.skip_selftest
        cmd_validate(a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
