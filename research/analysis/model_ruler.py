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
import glob
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
K_LIFTS = (8, 12, 16)                      # M2 (AMEND §12.1): phai DEU OK o ca 3 muc
# AMEND §12.2: h in {4h,12h,24h,72h}; DIEM phai lay o DUNG slot horizon cua bins.
# Format 26 B/rec big-endian `>i8 ts, >i2 symId, >f4 p4h,p12h,p24h,p72h` (WfoDataset.java:193)
# => slot 0 = `p`; slot 1/2/3 = `z[:, slot-1]`. Nhan tuong ung `retEnd_<h>` trong label .pb.
H_SLOT = {"4h": 0, "12h": 1, "24h": 2, "72h": 3}
H_COL = {"4h": "retEnd_4h", "12h": "retEnd_12h", "24h": "retEnd_24h", "72h": "retEnd_72h"}
# Do duoc 2026-09-25: MOI bins trong repo (deploy + arm retrain) co `z` = NaN 100%
# (trainer `g015_net_train_add.py:256 write_bin` ghi thang 3 NaN). => h=72h KHONG co diem.
Z_NAN_MEASURED = True
BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p", ">f4"), ("z", ">f4", 3)])
SELF_SEED = 20260905
TZ = "Asia/Ho_Chi_Minh"

# Chỉ số dùng cho LUẬT §5 (chiều TỐT = lớn hơn)
PRIMARY = "lift8"
SECOND = "abs_ic"
RAW_METRICS = ["auc8", "auc8c", "lift8", "lift12", "lift16", "dec_rho_lab",
               # PHU (khong dung cho luat GO)
               "ic", "abs_ic", "prec8", "auc", "pacc", "dec_rho", "dec_mono",
               "gross8", "net8", "net_lift8", "gross_all", "gross_lift8"]
AGG_METRICS = ["ic", "abs_ic", "lift8", "prec8"]
MAIN_METRICS = ["auc8", "lift_any", "dec_rho_lab"]          # M1, M2, M3 (AMEND §12.1)
LIFT_COLS = ["lift8", "lift12", "lift16"]


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

def load_labels(labels_dir, col="retEnd_4h"):
    """Nhan `col` (mac dinh `retEnd_4h`) tu /home/ubuntu/label_15m/*.pb — y het arm44_ruler45.py.

    AMEND §12.2: h in {4h, 72h} => col in {retEnd_4h, retEnd_72h}. Cung quy uoc `notna`.
    """
    import funding_label_pb as FLPB
    smap = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    fs = sorted(f for f in os.listdir(labels_dir)
                if f.startswith("funding_label_") and f.endswith(".pb")
                and f.split("_")[2] < "20260101")
    tl, sl, vl = [], [], []
    for fn in fs:
        d = FLPB.read_label(os.path.join(labels_dir, fn),
                            usecols=["tEpochMs", "symbol", col])
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts = d.tEpochMs.to_numpy(np.int64)[k]
        v = d[col].to_numpy(np.float64)[k]
        ok = np.isfinite(v)
        tl.append(ts[ok]); sl.append(sid.to_numpy()[k][ok].astype(np.int32)); vl.append(v[ok])
        del d
    tl = np.concatenate(tl); sl = np.concatenate(sl); vl = np.concatenate(vl)
    order = np.argsort(tl * 1024 + sl, kind="stable")
    LK = (tl * 1024 + sl)[order]; LV = vl[order]
    LOG.info("    nhan: %d dong (%s notna) tu %d file", len(LK), col, len(fs))
    return LK, LV


def join_labels_per_fold(bins_dir, LK, LV, folds, slot=0):
    """Doc bins tung fold + join nhan -> (ts, p, y, fold) gop. Dung DUNG format bins 26 B/rec.

    AMEND §12.2: `slot` 0 -> cot `p` (4h); 1/2/3 -> `z[:, slot-1]` (12h/24h/72h). Coin co DIEM NaN
    o slot dang chay bi BO (khong bia diem).
    """
    TS, P, Y, F = [], [], [], []
    for f in folds:
        bp = os.path.join(bins_dir, "predict_wf_%s.bin" % f)
        arr = np.fromfile(bp, dtype=BIN_DT)
        ts = arr["ts"].astype(np.int64); sy = arr["sym"].astype(np.int64)
        p = (arr["p"] if slot == 0 else arr["z"][:, slot - 1]).astype(np.float32).astype(np.float64)
        key = ts * 1024 + sy
        ip = np.clip(np.searchsorted(LK, key), 0, len(LK) - 1)
        hit = LK[ip] == key
        y = np.full(len(key), np.nan)
        y[hit] = LV[ip[hit]]
        m = np.isfinite(y) & np.isfinite(p)
        TS.append(ts[m]); P.append(p[m]); Y.append(y[m]); F.append(np.full(int(m.sum()), f))
        del arr
    return (np.concatenate(TS), np.concatenate(P), np.concatenate(Y), np.concatenate(F))


def _decile_block(ts_arr, dec_arr, val_arr, size_index):
    """Do mot nhan `val` theo decile: tra (rho per tick, mono ratio per tick, aux sum/cnt per decile)."""
    md = pd.DataFrame({"ts": ts_arr, "dec": dec_arr, "v": val_arr})
    GM = md.groupby(["ts", "dec"])["v"]
    mdc = GM.mean().unstack("dec").reindex(index=size_index, columns=range(10))
    cntd = GM.size().unstack("dec").reindex(index=size_index, columns=range(10)).fillna(0.0)
    aux = {"sum": (mdc.fillna(0.0).mul(cntd).sum(axis=0)).to_numpy(np.float64),
           "cnt": cntd.sum(axis=0).to_numpy(np.float64)}
    mdv = mdc.to_numpy()
    ok = np.isfinite(mdv)
    ry2v = mdc.rank(axis=1, method="average").to_numpy()
    cnt = ok.sum(axis=1).astype(np.float64)
    dc0 = np.where(ok, np.arange(10, dtype=np.float64), 0.0)
    ry0 = np.where(ok, ry2v, 0.0)
    sxy = (dc0 * ry0).sum(axis=1); sx = dc0.sum(axis=1); sy = ry0.sum(axis=1)
    sxx = (dc0 * dc0).sum(axis=1); syy = (ry0 * ry0).sum(axis=1)
    den = np.sqrt(np.maximum((cnt * sxx - sx ** 2) * (cnt * syy - sy ** 2), 0.0))
    with np.errstate(invalid="ignore", divide="ignore"):
        rho = pd.Series(np.where(den > 0, (cnt * sxy - sx * sy) / den, np.nan), index=size_index)
    dadj = np.diff(mdv, axis=1)
    oka = np.isfinite(dadj)
    mono = np.where(oka, (dadj >= 0).astype(np.float64), 0.0).sum(axis=1)
    denom = oka.sum(axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        mono_r = pd.Series(np.where(denom > 0, mono / denom, np.nan), index=size_index)
    return rho, mono_r, aux


def pooled_deciles(aux):
    """Duong decile GOP (row-weighted): mean(D1..D10), Spearman(D, mean), doc D10-D1."""
    s = np.asarray(aux["sum"], dtype=np.float64)
    c = np.asarray(aux["cnt"], dtype=np.float64)
    with np.errstate(invalid="ignore", divide="ignore"):
        m = np.where(c > 0, s / c, np.nan)
    ok = np.isfinite(m)
    if ok.sum() < 3:
        return {"mean": m.tolist(), "rho": float("nan"), "slope": float("nan")}
    d = np.arange(10, dtype=np.float64)[ok]
    v = m[ok]
    rv = pd.Series(v).rank(method="average").to_numpy()
    from scipy.stats import spearmanr
    rho = float(spearmanr(d, v).statistic)
    return {"mean": m.tolist(), "rho": rho, "slope": float(m[9] - m[0])}


def tick_metrics(ts, p, y, with_pacc=True):
    """Bo chi so THEO TUNG TICK (chi tick >= 2 coin). Tra (DataFrame 1 dong/tick, aux decile).

    AMEND §12: M1 = `auc8` (AUC@top8, cong thuc chot truoc), M2 = `lift8/12/16`, M3 = `dec_rho_lab`
    (per-tick rho tren NHAN TRAIN) + `pooled` (duong decile gop). `y` = retEnd cua horizon dang chay.
    Nhan cho CONG XEP HANG = `yb = (y > 0,015)`; kinh te = `y` (gross) va `y - FEE_RT` (net).
    """
    order = np.argsort(ts, kind="stable")
    ts, p, y = np.asarray(ts)[order], np.asarray(p)[order], np.asarray(y)[order]
    d = pd.DataFrame({"ts": ts.astype(np.int64), "p": p.astype(np.float64),
                      "y": y.astype(np.float64)})
    d["yb"] = (d.y > THR).astype(np.float64)              # NHAN TRAIN (net > 1,5%)
    d["ybn"] = ((d.y - FEE_RT) > THR).astype(np.float64)
    d = d[d.groupby("ts")["p"].transform("size") >= 2].copy()
    D = d

    G0 = d.groupby("ts", sort=True)
    D["_rp"] = G0["p"].rank(method="average")
    D["_ry"] = G0["y"].rank(method="average")
    G1 = D.groupby("ts", sort=True)
    a1 = G1["_rp"].transform("mean"); a2 = G1["_ry"].transform("mean")
    D["_num"] = (D._rp - a1) * (D._ry - a2)
    D["_s1"] = (D._rp - a1) ** 2
    D["_s2"] = (D._ry - a2) ** 2
    D["_srp"] = D._rp * D.yb
    G = D.groupby("ts", sort=True)
    size_s = G.size().astype(np.float64)
    ic = G["_num"].sum() / np.sqrt(G["_s1"].sum() * G["_s2"].sum())
    base_s = G["yb"].mean()
    base_n_s = G["ybn"].mean()
    npos = G["yb"].sum()
    nneg = size_s - npos
    # PHU: AUC whole-tick (Mann-Whitney)
    auc = (G["_srp"].sum() - npos * (npos + 1) / 2.0) / (npos * nneg).replace(0, np.nan)

    # ---- MOT lan sort: top-K cho K = 8/12/16 + co `top-8` (M2) ----
    S = D.sort_values(["ts", "p"], ascending=[True, False], kind="stable")
    cc = S.groupby("ts", sort=True).cumcount().to_numpy()
    tmp = pd.DataFrame({"ts": S.ts.to_numpy(), "yb": S.yb.to_numpy(),
                        "ybn": S.ybn.to_numpy(), "y": S.y.to_numpy(), "cc": cc})
    top8idx = S.index[cc < K_SEL]
    isT = pd.Series(False, index=D.index)
    isT.loc[top8idx] = True
    D["_T8"] = isT.to_numpy()
    prec = {}
    for K in K_LIFTS:
        sub = tmp[tmp.cc < K]
        prec[K] = sub.groupby("ts")["yb"].mean().reindex(size_s.index)
    prec8n = tmp[tmp.cc < K_SEL].groupby("ts")["ybn"].mean().reindex(size_s.index)
    gross8 = tmp[tmp.cc < K_SEL].groupby("ts")["y"].mean().reindex(size_s.index)
    gross_all = G["y"].mean()
    n8 = tmp[tmp.cc < K_SEL].groupby("ts")["yb"].size().reindex(size_s.index)

    # ---- M1: AUC@top8 (pairwise trong tick, chi cap co >= 1 coin trong top-8) ----
    A = D.sort_values(["ts", "p"], kind="stable")
    A["_neg"] = 1.0 - A.yb
    A["_cp"] = A.groupby("ts", sort=True)["yb"].cumsum()
    A["_cn"] = A.groupby("ts", sort=True)["_neg"].cumsum()
    gsize = A.groupby(["ts", "p"], sort=True)["p"].transform("size")
    gpos = A.groupby(["ts", "p"], sort=True)["yb"].transform("sum")
    posle = A.groupby(["ts", "p"], sort=True)["_cp"].transform("max")
    negle = A.groupby(["ts", "p"], sort=True)["_cn"].transform("max")
    postot = A.groupby("ts", sort=True)["yb"].transform("sum")
    # a: so cap (N o DUOI a, tinh 0.5 cho bang diem); b: so cap (P o TREN a)
    nbel = (negle - 0.5 * (gsize - gpos)).reindex(D.index)
    pabv = ((postot - posle) + 0.5 * gpos).reindex(D.index)
    isP = (D.yb == 1.0).to_numpy()
    isTv = D._T8.to_numpy()
    PnT = (isP & isTv).astype(np.float64)
    NnT = (~isP & isTv).astype(np.float64)
    A_sum = pd.Series(nbel.to_numpy() * PnT).groupby(D.ts.to_numpy()).sum()
    B_sum = pd.Series(pabv.to_numpy() * NnT).groupby(D.ts.to_numpy()).sum()
    nPT = pd.Series(PnT).groupby(D.ts.to_numpy()).sum()
    nNT = pd.Series(NnT).groupby(D.ts.to_numpy()).sum()
    den8 = (nPT * nneg + (npos - nPT) * nNT).reindex(size_s.index)
    auc8 = (A_sum.reindex(size_s.index) + B_sum.reindex(size_s.index)) / den8.replace(0, np.nan)
    # M1'-BAN DUNG (`auc8c`): cong thuc o tren CONG cap (pos∈T, neg∈T) **2 lan ở tử** (1 lan qua
    # `nbel` cua pos∈T, 1 lan qua `pabv` cua neg∈T) nhung **1 lan ở mẫu** (`den8`) ⇒ co the > 1 tren
    # du lieu nho (bang chung tong hop o RESULT §10.1). `auc8c` = `auc8` − phan trung: chi tinh cap
    # `(T,T)` MOT lan. MẪU KHÔNG ĐỔI (den8 da dem cap `(T,T)` dung 1 lan).
    _tt = D[D._T8.to_numpy()].sort_values(["ts", "p"], kind="stable").copy()
    _tt["_neg"] = 1.0 - _tt.yb
    _cp = _tt.groupby("ts", sort=True)["yb"].cumsum()
    _cn = _tt.groupby("ts", sort=True)["_neg"].cumsum()
    _gs = _tt.groupby(["ts", "p"], sort=True)["p"].transform("size")
    _gp = _tt.groupby(["ts", "p"], sort=True)["yb"].transform("sum")
    _nbelT = _cn - 0.5 * (_gs - _gp)
    C_TT = (_nbelT * _tt.yb).groupby(_tt.ts).sum().reindex(size_s.index).fillna(0.0)
    auc8c = (A_sum.reindex(size_s.index) + B_sum.reindex(size_s.index) - C_TT) / den8.replace(0, np.nan)
    del _tt, _cp, _cn, _gs, _gp, _nbelT, C_TT
    D.drop(columns=["_num", "_s1", "_s2", "_srp"], inplace=True)

    # ---- M3: decile theo RANK score trong tick, 3 nhan ----
    nsel = D.groupby("ts", sort=True)["p"].transform("size").to_numpy(np.float64)
    dec = np.minimum((D._rp.to_numpy() * 10.0 / (nsel + 1)).astype(int), 9)
    tsa = D.ts.to_numpy()
    rho_y, mono_y, aux_gross = _decile_block(tsa, dec, D.y.to_numpy(), size_s.index)
    rho_l, _, aux_lab = _decile_block(tsa, dec, D.yb.to_numpy(), size_s.index)
    _, _, aux_net = _decile_block(tsa, dec, (D.y - FEE_RT).to_numpy(), size_s.index)

    R = pd.DataFrame({
        "n_coin": size_s, "ic": ic, "auc": auc, "auc8": auc8, "auc8c": auc8c, "n8": n8,
        "prec8": prec[8], "lift8": prec[8] - base_s,
        "lift12": prec[12] - base_s, "lift16": prec[16] - base_s,
        "base": base_s, "base_net": base_n_s, "gross8": gross8, "gross_all": gross_all,
        "net_lift8": prec8n - base_n_s,
        "dec_rho": rho_y, "dec_mono": mono_y, "dec_rho_lab": rho_l,
    })
    R["net8"] = R.gross8 - FEE_RT
    R["gross_lift8"] = R.gross8 - R.gross_all
    R["abs_ic"] = R.ic.abs()
    R = R.reset_index().rename(columns={"index": "ts"})
    R["ts"] = R.ts.astype(np.int64)
    aux = {"gross": aux_gross, "lab": aux_lab, "net": aux_net}
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
    return R.sort_values("ts").reset_index(drop=True), aux


def ruler_raw(bins_dir, labels_dir, folds, self_tests=False, horizon="4h", label_horizon=None):
    """RAW theo TUNG FOLD (streaming) — tranh OOM: khong bao gio giu ca 16 fold cung luc.

    AMEND §12.2: doc DIEM o slot `H_SLOT[horizon]` (khop horizon cua nhan). Tra `(None, None)` khi
    slot do KHONG co diem (toan NaN) — KHONG bia so, KHONG lay slot 4h thay cho 72h.
    `label_horizon` (mac dinh = `horizon`) cho phep do KINH TE CROSS-HORIZON: diem cua horizon
    `horizon` nhung nhan `retEnd_<label_horizon>` — LUON ghi ro, khong duoc goi la "cong 72h".
    """
    t0 = time.time()
    slot = H_SLOT[horizon]
    col = H_COL[label_horizon or horizon]
    probe = np.fromfile(os.path.join(bins_dir, "predict_wf_%s.bin" % folds[0]), dtype=BIN_DT,
                        count=200000)
    pv = (probe["p"] if slot == 0 else probe["z"][:, slot - 1]).astype(np.float64)
    if not np.isfinite(pv).any():
        LOG.info("  !! h=%s: DIEM o slot %d cua `%s` TOAN NaN => KHONG DANH GIA DUOC (khong bia so)",
                 horizon, slot, bins_dir)
        return None, None
    LK, LV = load_labels(labels_dir, col)
    keys = ["self", "shuffled", "unif", "logit"] if self_tests else ["self"]
    parts = {k: [] for k in keys}
    aux = {k: {c: {"sum": np.zeros(10), "cnt": np.zeros(10)} for c in ("gross", "lab", "net")}
           for k in keys}
    rng = np.random.default_rng(SELF_SEED)
    for f in folds:
        ts, p, y, fold = join_labels_per_fold(bins_dir, LK, LV, [f], slot)
        if len(ts) == 0:
            LOG.info("    fold %s: 0 dong (nhan hoac diem NaN) -> BO", f)
            continue
        foldmap = pd.Series(fold).groupby(pd.Series(ts)).first()
        foldmap.index = foldmap.index.astype(np.int64)

        def with_fold(R, _fm=foldmap):
            R["fold"] = R.ts.map(_fm)
            return R

        def acc(key, tt, pp, yy):
            R, ax = tick_metrics(tt, pp, yy)
            for c in ("gross", "lab", "net"):
                aux[key][c]["sum"] += ax[c]["sum"]
                aux[key][c]["cnt"] += ax[c]["cnt"]
            return with_fold(R)

        parts["self"].append(acc("self", ts, p, y))
        if self_tests:
            ps = p.copy()
            b = np.flatnonzero(np.diff(ts)) + 1
            st = np.concatenate(([0], b)); en = np.concatenate((b, [len(ts)]))
            for i in range(len(st)):
                s, e = st[i], en[i]
                ps[s:e] = rng.permutation(ps[s:e])
            parts["shuffled"].append(acc("shuffled", ts, ps, y))
            # T2: bien doi TANG NGHIEM NGAT (quantile->uniform, logit) — phai ra DUNG so cu
            rk = pd.Series(p).groupby(pd.Series(ts)).rank(method="average").to_numpy()
            nn = pd.Series(rk).groupby(pd.Series(ts)).transform("size").to_numpy(np.float64)
            u = np.clip((rk - 0.5) / nn, 1e-7, 1 - 1e-7)
            parts["unif"].append(acc("unif", ts, u, y))
            parts["logit"].append(acc("logit", ts, np.log(u / (1 - u)), y))
            del ps, rk, nn, u
        LOG.info("    fold %s: %d dong, %d tick | %.0fs", f, len(ts), len(parts["self"][-1]),
                 time.time() - t0)
        del ts, p, y, fold
    if not parts["self"]:
        LOG.info("  !! h=%s: KHONG fold nao co du lieu => KHONG DANH GIA DUOC", horizon)
        return None, None
    out = {k: pd.concat(v, ignore_index=True) for k, v in parts.items()}
    LOG.info("  RAW xong %d bien the | %d tick | %.0fs", len(out), len(out["self"]),
             time.time() - t0)
    return out, aux


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

def summarize(df, tag, metrics, inflate=1.0, aux=None):
    y = year_of(df.ts.to_numpy())
    df = df.assign(year=y)
    out = {"tag": tag, "n_tick": int(len(df)), "n_coin_mean": float(df.n_coin.mean()),
           "metrics": {}, "by_fold": {}, "by_year": {}, "drift": {}}
    for m in metrics:
        if m not in df.columns:
            continue
        out["metrics"][m] = ci_mean(df[m].to_numpy(), df.ts.to_numpy(), inflate)
    for m in [x for x in (PRIMARY, "ic", "auc8", "dec_rho_lab") if x in df.columns]:
        out["by_fold"][m] = {str(k): round(float(v), 6) for k, v in
                             df.groupby("fold")[m].mean().items()}
        out["by_year"][m] = {str(k): round(float(v), 6) for k, v in
                             df.groupby("year")[m].mean().items()}
        fl = sorted(df.fold.unique())
        if len(fl) >= 2:
            h = len(fl) // 2
            a = df[df.fold.isin(fl[:h])][m].mean(); bb = df[df.fold.isin(fl[h:])][m].mean()
            out["drift"][m] = round(float(a - bb), 6)
    # M3(a) — duong decile GOP tren 3 nhan (AMEND §12.1)
    if aux:
        out["pooled_deciles"] = {c: pooled_deciles(aux[c]) for c in ("lab", "gross", "net")}
        lab = out["pooled_deciles"]["lab"]
        out["M3a"] = dict(rho=lab["rho"], slope=lab["slope"],
                           pass_="PASS" if (np.isfinite(lab["rho"]) and lab["rho"] > 0.8
                                            and lab["slope"] > 0) else "FAIL")
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
    """LUAT v1 §5 (giu lai lam THAM CHIEU; luat QUYET DINH cua vong nay = `go_rule` §12.3)."""
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


def go_rule(D1, D2, label, cand):
    """LUAT GO (AMEND §12.3): h=4h can >= 2/3 chi so chinh {M1,M2,M3} co Δ>0 NGOAI CI vs CA HAI control.

    D1/D2 = dict delta (vs retrain-control / noise-control). Chi so KHONG TINH DUOC => KHONG tinh la PASS.
    M2 = ca 3 muc K in {8,12,16} phai Δ>0 ngoai CI vs ca hai.
    Tra dict gom tung chi so + so PASS + verdict.
    """
    def out_pos(d, m):
        x = (d or {}).get("metrics", {}).get(m)
        return bool(x and x["out_both"] and x["mean"] > 0), x

    res = {}
    # M1
    a1, x1 = out_pos(D1, "auc8"); a2, x2 = out_pos(D2, "auc8")
    na = (x1 is None) or (x2 is None)
    res["M1_auc8"] = dict(state="NA" if na else ("PASS" if (a1 and a2) else "fail"),
                          d_ctrl1=(x1 or {}).get("mean"), d_ctrl2=(x2 or {}).get("mean"),
                          out1=(x1 or {}).get("out_both"), out2=(x2 or {}).get("out_both"))
    # M2 = ca 3 K
    lvl = {}
    for m in LIFT_COLS:
        b1, y1 = out_pos(D1, m); b2, y2 = out_pos(D2, m)
        if (y1 is None) or (y2 is None):
            lvl[m] = "NA"
        else:
            lvl[m] = "PASS" if (b1 and b2) else "fail"
    any_fail = any(v == "fail" for v in lvl.values())
    all_pass = all(v == "PASS" for v in lvl.values())
    res["M2_liftK"] = dict(state="fail" if any_fail else ("PASS" if all_pass else "NA"), detail=lvl)
    # M3 (phan (b): delta per-tick rho tren nhan train)
    c1, z1 = out_pos(D1, "dec_rho_lab"); c2, z2 = out_pos(D2, "dec_rho_lab")
    nm = (z1 is None) or (z2 is None)
    res["M3_decile_b"] = dict(state="NA" if nm else ("PASS" if (c1 and c2) else "fail"),
                              d_ctrl1=(z1 or {}).get("mean"), d_ctrl2=(z2 or {}).get("mean"))
    # "FAIL HEP" (AMEND §12.4): M2 la chi so DUY NHAT fail VA CHI 1 trong 3 muc K fail ⇒ bao rieng,
    # KHONG tu noi nguong. Tra so cu the cho tung K.
    n_k_fail = sum(1 for v in lvl.values() if v == "fail")
    n_other_fail = sum(1 for k in ("M1_auc8", "M3_decile_b") if res[k]["state"] == "fail")
    res["fail_hep"] = dict(
        flag=bool(res["M2_liftK"]["state"] == "fail" and n_k_fail == 1 and n_other_fail == 0),
        n_K_fail=n_k_fail, K_fail=[m for m in LIFT_COLS if lvl[m] == "fail"],
        state_K=lvl,
        d_K={m: {"d_ctrl1": ((D1 or {}).get("metrics", {}).get(m) or {}).get("mean"),
                 "d_ctrl2": ((D2 or {}).get("metrics", {}).get(m) or {}).get("mean"),
                 "out1": bool(((D1 or {}).get("metrics", {}).get(m) or {}).get("out_both")),
                 "out2": bool(((D2 or {}).get("metrics", {}).get(m) or {}).get("out_both"))}
             for m in LIFT_COLS})
    npass = sum(1 for k in ("M1_auc8", "M2_liftK", "M3_decile_b") if res[k]["state"] == "PASS")
    res["n_pass"] = npass
    res["GO_h4"] = bool(npass >= 2)
    LOG.info("  %-26s M1=%s M2=%s%s M3=%s => %d/3 => h=4h: %s", label,
             res["M1_auc8"]["state"], res["M2_liftK"]["state"],
             " [FAIL HEP: %s]" % res["fail_hep"]["K_fail"] if res["fail_hep"]["flag"] else "",
             res["M3_decile_b"]["state"], npass, "GO" if res["GO_h4"] else "NOT GO")
    if res["M2_liftK"]["state"] != "PASS" and not res["fail_hep"]["flag"]:
        LOG.info("     M2 theo tung K: %s", {m: res["fail_hep"]["d_K"][m] for m in LIFT_COLS})
    return res


# ─────────────────────────────── CLI ───────────────────────────────

def cmd_ruler(a):
    infl = C.inflate(a.k)
    LOG.info("### MODEL RULER — arm `%s` | h=%s (nhan %s) | k=%d inflate(k)=%.6f | tham chieu legacy %.2f",
             a.name, a.horizon, a.label_horizon or a.horizon, a.k, infl, G.LEGACY)
    if a.bins:
        res, aux = ruler_raw(a.bins, a.labels, FOLDS[:a.folds] if a.folds else FOLDS,
                             a.self_tests, a.horizon, a.label_horizon)
        metrics = RAW_METRICS
        tag = a.name
        out = {"name": a.name, "mode": "RAW", "bins": a.bins, "labels": a.labels,
               "k": a.k, "horizon": a.horizon, "folds": FOLDS[:a.folds] if a.folds else FOLDS}
        for key, df in res.items():
            if a.per_tick and key == "self":
                df.to_parquet(a.per_tick, index=False)
                LOG.info("  per-tick -> %s (%d dong)", a.per_tick, len(df))
            out[key] = summarize(df, tag + ("" if key == "self" else "|" + key), metrics, infl,
                                 aux[key] if key == "self" else None)
        if a.self_tests:
            LOG.info("\n[T1/T2] TU-KIEM THUOC (T2 phai = 0.0 tuyet doi)")
            for m in RAW_METRICS:
                v = {k: out[k]["metrics"].get(m, {}).get("mean", float("nan"))
                     for k in ("self", "shuffled", "unif", "logit")}
                if not np.isfinite(v["self"]):
                    continue
                d2 = max(abs(v["self"] - v["unif"]), abs(v["self"] - v["logit"]))
                LOG.info("   %-11s self=%+.6f | shuffle=%+.6f | T2 max|Δ| = %.2e %s",
                         m, v["self"], v["shuffled"], d2, "OK" if d2 < 1e-9 else "*** FAIL ***")
            out["selftest_T2_max_abs_delta"] = float(max(
                abs(out["self"]["metrics"].get(m, {}).get("mean", 0)
                    - out[x]["metrics"].get(m, {}).get("mean", 0))
                for m in RAW_METRICS for x in ("unif", "logit")))
    else:
        d = ruler_agg(a.ticks)
        out = {"name": a.name, "mode": "AGG", "ticks": a.ticks, "k": a.k,
               "horizon": a.horizon}
        if a.per_tick:
            d.to_parquet(a.per_tick, index=False)
        out["self"] = summarize(d, a.name, AGG_METRICS, infl)
    s = out["self"]
    LOG.info("  n_tick=%d | n_coin=%.1f", s["n_tick"], s["n_coin_mean"])
    for m in (AGG_METRICS if a.ticks else RAW_METRICS):
        x = s["metrics"].get(m)
        if x:
            LOG.info("   %-11s = %+.6f  [%+.6f,%+.6f] raw | [%+.6f,%+.6f] x%.6f",
                     m, x["mean"], x["raw"][0], x["raw"][1], x["infl"][0], x["infl"][1], infl)
    if s.get("M3a"):
        LOG.info("   M3(a) decile GOP tren NHAN TRAIN: rho=%+.4f doc=%+.5f => %s",
                 s["M3a"]["rho"], s["M3a"]["slope"], s["M3a"]["pass_"])
    LOG.info("   drift lift8 = %s | auc8 = %s | dec_rho_lab = %s", s["drift"].get("lift8"),
             s["drift"].get("auc8"), s["drift"].get("dec_rho_lab"))
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1, default=str)
        LOG.info("  JSON -> %s", a.out)
    return out


PATHS = {
    "45deploy": ("/home/ubuntu/claudedata/predwf_G015x26", None),
    "A45": (None, "/home/ubuntu/kaggle_sim/out/a44out/A45_perfold_ticks.parquet"),
    "A44": (None, "/home/ubuntu/kaggle_sim/out/a44out/A44_perfold_ticks.parquet"),
    "V0": (None, "/home/ubuntu/claudedata/stage2_featvar_out/stage2/V0_perfold_ticks.parquet"),
    "V1": (None, "/home/ubuntu/claudedata/stage2_featvar_out/stage2/V1_perfold_ticks.parquet"),
    "V5": (None, "/home/ubuntu/claudedata/stage2_featvar_out/stage2/V5_perfold_ticks.parquet"),
}
# AMEND §12.7 (DONG khoang trong G-1 — KHONG bia): bins THO cua 4 arm retrain CO THAT, nam trong
# KERNEL OUTPUT tren Kaggle (`g015p2-stage2-featvar-gpu` -> V0/V1/V5; `g015p2-arm44-gpu` -> A44/A45);
# truoc day kernel chi luu lai per-tick parquet (~30 MB) nen may local KHONG co. Da TAI artifact
# bang `kaggle kernels output` (chi tai file da co san — KHONG train, KHONG sim, KHONG job). Co dir
# thi chay RAW (du M1–M10 + lift@12/16), khong co thi lui ve AGG (M1–M4) nhu cu.
BINS_ARMS = {
    "A45": "/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A45",
    "A44": "/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A44",
    "V0": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V0",
    "V1": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V1",
    "V5": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V5",
}
for _n in list(BINS_ARMS):
    _d = BINS_ARMS[_n]
    if glob.glob(os.path.join(_d, "predict_wf_20220101.bin")):
        PATHS[_n] = (_d, PATHS[_n][1])
LOG.info("### BINS THO cua arm retrain: %s",
         {k: ("CO" if PATHS[k][0] else "KHONG(DUNG AGG)") for k in BINS_ARMS})
TMP = "/tmp/model_ruler_out"


def _aux_path(name, tag_h):
    """Sidecar `aux` decile (sum/cnt theo decile) — M3(a) GOP can no, nen cache phai co no."""
    return os.path.join(TMP, "%s_%s_aux.npz" % (name, tag_h))


def save_aux(path, aux):
    np.savez(path, **{"%s_%s" % (c, f): np.asarray(aux[c][f], dtype=np.float64)
                      for c in aux for f in ("sum", "cnt")})


def load_aux(path):
    z = np.load(path)
    return {c: {"sum": z["%s_sum" % c], "cnt": z["%s_cnt" % c]}
            for c in ("gross", "lab", "net")}


def cmd_validate(a):
    os.makedirs(TMP, exist_ok=True)
    t0 = time.time()
    infl = C.inflate(a.k)
    LOG.info("### VALIDATE THUOC tren 5 arm (pre-reg §7 + AMEND §12) — KHONG train, KHONG sim")
    LOG.info("### h=%s | k=%d (so UNG VIEN cua round: A44, V0) => he so CI = inflate(k) = %.6f"
             "  [tham chieu legacy %.2f] | CM: block-%dh %d rep seed %d",
             a.horizon, a.k, infl, G.LEGACY, C.BLOCK_H, C.NREP, C.SEED)
    if a.horizon == "72h":
        LOG.info("### [§12.7 G-2] DO DUOC 2026-09-25: DIEM 72h KHONG TON TAI o MOI bins (deploy VA")
        LOG.info("###   arm retrain): `z[:,2]` = NaN 100% (trainer `write_bin` ghi thang NaN).")
        LOG.info("###   => slot 72h KHONG DANH GIA DUOC voi artifact hien co (KHONG lay p4h thay 72h).")
    PT, SUM, RAWO, VF, AUX = {}, {}, {}, {}, {}
    for name, (bins, ticks) in PATHS.items():
        if a.horizon == "72h" and not bins:
            LOG.info("  [%s] BO QUA (AGG chi co per-tick 4h — khai bao truoc §12.7 G-2)", name)
            continue
        lh = a.label_horizon or a.horizon
        tag_h = "%s_lab%s" % (a.horizon, lh)
        pt = os.path.join(TMP, "%s_pertick.parquet" % name if tag_h == "4h_lab4h"
                          else "%s_%s_pertick.parquet" % (name, tag_h))
        auxp = _aux_path(name, tag_h)
        paths = [pt, auxp] + ([os.path.join(TMP, "%s_%s_pertick.parquet" % (
                            name, k if tag_h == "4h_lab4h" else "%s_%s" % (tag_h, k)))
                         for k in ("shuffled", "unif", "logit")] if (bins and a.self_tests)
                        else [])
        if a.reuse and all(os.path.exists(p) for p in paths):
            probe = pd.read_parquet(pt)
            if "auc8" in probe.columns and "dec_rho_lab" in probe.columns:
                LOG.info("  [%s] REUSE per-tick cache (%s)", name, pt)
                df = probe; df["ts"] = df.ts.astype(np.int64)
                if "abs_ic" not in df.columns:
                    df["abs_ic"] = df.ic.abs()
                SUM[name] = summarize(df, name, AGG_METRICS, infl)
                PT[name] = df.sort_values("ts").reset_index(drop=True)
                if bins:
                    RAWO[name] = {"self": summarize(df, name, RAW_METRICS, infl,
                                                       load_aux(auxp))}
                    if a.self_tests:
                        for k in ("shuffled", "unif", "logit"):
                            dk = pd.read_parquet(
                                os.path.join(TMP, "%s_%s_pertick.parquet" % (name, k)))
                            dk["ts"] = dk.ts.astype(np.int64)
                            if "abs_ic" not in dk.columns:
                                dk["abs_ic"] = dk.ic.abs()
                            VF[k] = dk.sort_values("ts").reset_index(drop=True)
                            RAWO[name][k] = summarize(dk, "%s|%s" % (name, k), RAW_METRICS, infl)
                LOG.info("  [%s] REUSE | n_tick=%d lift8=%+.6f auc8=%s", name, len(df),
                         df.lift8.mean(), df.auc8.mean() if "auc8" in df else "NA")
                continue
            LOG.info("  [%s] cache CU (thieu auc8/dec_rho_lab) => tinh lai", name)
        if bins:
            res, aux = ruler_raw(bins, a.labels, FOLDS, a.self_tests, a.horizon, a.label_horizon)
            if res is None:
                LOG.info("  [%s] BO QUA — KHONG co DIEM o h=%s (slot bins toan NaN)", name, a.horizon)
                continue
            AUX = aux
            save_aux(auxp, aux["self"])       # `aux` long theo bien the => lay nhanh `self`
            df = res["self"]; df.to_parquet(pt, index=False)
            RAWO[name] = {}
            for k in res:
                RAWO[name][k] = summarize(res[k], name + ("" if k == "self" else "|" + k),
                                          RAW_METRICS, infl, aux[k] if k == "self" else None)
            for k in ("shuffled", "unif", "logit"):
                if k not in res:            # --skip-selftest: chi co bien the `self`
                    continue
                res[k].to_parquet(os.path.join(TMP, "%s_%s_pertick.parquet" % (
                    name, k if tag_h == "4h_lab4h" else "%s_%s" % (tag_h, k))), index=False)
        else:
            df = ruler_agg(ticks); df.to_parquet(pt, index=False)
        PT[name] = df
        SUM[name] = summarize(df, name, AGG_METRICS, infl)
        LOG.info("  [%s] %s | n_tick=%d ic=%+.6f lift8=%+.6f auc8=%s", name,
                 "RAW" if bins else "AGG", len(df), df.ic.mean(), df.lift8.mean(),
                 "%.6f" % df.auc8.mean() if "auc8" in df.columns else "NA(co)")

    if "45deploy" not in PT:
        LOG.info("\n### KHONG arm nao tinh duoc o h=%s => DUNG, khong doc so nao.", a.horizon)
        out = {"k": a.k, "inflate": infl, "horizon": a.horizon, "evaluable": False,
               "reason": "khong co DIEM o slot horizon nay (z NaN) cho MOI arm", "delta": {}}
        if a.out:
            json.dump(out, open(a.out, "w"), indent=1, default=str)
            LOG.info("    JSON -> %s", a.out)
        return out
    # [T3] coverage — chi 5/6 ARM THAT (khong tinh ban bien the cua test)
    ref = PT["45deploy"].ts.to_numpy()
    cov = {k: bool(len(v) == len(ref) and (v.ts.to_numpy() == ref).all()) for k, v in PT.items()}
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

    # [V-A..V-E] delta + verdict  (M = v1 phu + cac cot AMEND khi co)
    M = ["auc8", "auc8c", "lift8", "lift12", "lift16", "dec_rho_lab"] + AGG_METRICS
    D = {}
    pairs = [("A44", "45deploy"), ("A44", "A45"), ("A45", "45deploy"),
             ("V0", "45deploy"), ("V0", "V5"), ("V5", "V0"), ("V1", "V0"), ("V5", "45deploy"),
             ("V5", "V1"), ("V1", "45deploy")]
    LOG.info("\n[DELTA] ghep cap theo tick, CI block-%dh %d rep seed %d (ngoai CI = ngoai CA HAI do rong)",
             C.BLOCK_H, C.NREP, C.SEED)
    for x, b in pairs:
        if x not in PT or b not in PT:
            continue
        d = delta(PT[x], PT[b], M, "%s - %s" % (x, b))
        D["%s_minus_%s" % (x, b)] = d
        bits = []
        for m in M:
            y = d["metrics"].get(m)
            if y:
                bits.append("%s=%+.6f%s" % (m, y["mean"], "*" if y["out_both"] else ""))
        LOG.info("  %-16s %s", "%s - %s" % (x, b), " | ".join(bits))

    # ── LUAT GO (AMEND §12.3) ──
    lh = a.label_horizon or a.horizon
    GO = {}
    if lh != a.horizon:
        LOG.info("\n[GO] BO QUA: day la lan chay KINH TE CROSS-HORIZON (diem h=%s x nhan h=%s)"
                 " => khong ap luat GO (luat GO doi diem DUNG horizon cua nhan).", a.horizon, lh)
    else:
        LOG.info("\n[GO — AMEND §12.3] M1=AUC@top8 · M2=lift@{8,12,16} DEU OK · M3(b)=delta"
                 " decile-rho (nhan train h=%s)", lh)
        for cand, c1, c2 in (("A44", "A45", "45deploy"), ("V0", "V5", "45deploy")):
            if cand not in PT:
                continue
            GO[cand] = go_rule(D.get("%s_minus_%s" % (cand, c1)),
                               D.get("%s_minus_%s" % (cand, c2)),
                               "%s vs {%s, %s}" % (cand, c1, c2), cand)
            GO[cand]["controls"] = [c1, c2]
        if a.horizon == "72h":
            LOG.info("\n[GO dieu kien (ii) h=72h] KHONG DANH GIA DUOC cho A44/V0 (§12.7 G-2)")
            for cand in ("A44", "V0"):
                if cand in GO:
                    GO[cand]["h72_evaluable"] = False
    LOG.info("\n[V-A..V-C] LUAT v1 §5 (THAM CHIEU, giu nguyen dinh nghia cu; * = ngoai CI ca hai do rong)")
    V = {}
    if "A44_minus_45deploy" in D and "A44_minus_A45" in D:
        V["V-A"] = verdict(D["A44_minus_45deploy"], D["A44_minus_A45"],
                           "V-A: A44 vs {45deploy, A45}")
    if "V0_minus_45deploy" in D and "V0_minus_V5" in D:
        V["V-B"] = verdict(D["V0_minus_45deploy"], D["V0_minus_V5"],
                           "V-B: V0 vs {45deploy, V5(noise)}")
    vc = (D.get("V5_minus_V0", {"metrics": {}})["metrics"] or {}).get(PRIMARY)
    V["V-C_as_written"] = dict(
        test="V5(nhieu) co 'thang' V0 ngoai CI khong (dinh nghia TRONG pre-reg §7)",
        noise_beats_real=bool(vc and vc["out_both"] and vc["mean"] > 0), detail=vc)
    vcc = (D.get("V5_minus_V1", {"metrics": {}})["metrics"] or {}).get(PRIMARY)
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
    V["V-D"] = dict(detail=(D.get("A45_minus_45deploy", {"metrics": {}})["metrics"] or {})
                     .get(PRIMARY))
    LOG.info("  V-D: nen nhieu retrain A45-45deploy Δlift8=%+.6f", V["V-D"]["detail"]["mean"])
    V["V-E"] = dict(T1_lift8=selftest.get("T1_lift8"), T2_pass=selftest.get("T2_pass"))
    selfok = bool(selftest.get("T2_pass", False)
                  and abs(selftest.get("T1_lift8", 9)) < 0.005)
    kep_a = V.get("V-A", {}).get("verdict") == "KEEP"
    kep_b = V.get("V-B", {}).get("verdict") == "KEEP"
    repro_lit = bool(kep_a and kep_b and not V["V-C_as_written"]["noise_beats_real"] and selfok)
    repro_fix = bool(kep_a and kep_b and not V["V-C_corrected"]["noise_adds_signal"] and selfok)
    LOG.info("\n=== KET LUAN VALIDATE ===")
    LOG.info("    (1) LUAT GO AMEND §12.3: %s", {k: ("GO" if v["GO_h4"] else "NOT GO")
                                             for k, v in GO.items()})
    LOG.info("    (2) ruler TU NOI LAI `GIU 45`?  nguyen van §7: %s | sau khi sua V-C: %s |"
             " luat GO amend: %s", "CO" if repro_lit else "KHONG",
             "CO" if repro_fix else "KHONG",
             "CO (khong ung vien nao GO)" if GO and not any(v["GO_h4"] for v in GO.values())
             else "KHONG")
    out = {"k": a.k, "inflate": infl, "legacy_reference": G.LEGACY, "horizon": a.horizon,
           "block_h": C.BLOCK_H, "nrep": C.NREP, "seed": C.SEED, "thr": THR,
           "fee_rt": FEE_RT, "k_sel": K_SEL, "k_lifts": list(K_LIFTS),
           "coverage": cov, "summary": SUM, "raw_summary": RAWO, "delta": D,
           "GO": GO, "verdicts_v1": V, "selftest": selftest,
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
    r.add_argument("--horizon", default="4h", choices=["4h", "72h"])
    r.add_argument("--label-horizon", default=None, choices=["4h", "12h", "24h", "72h"],
                   help="mac dinh = --horizon; khac di => KINH TE CROSS-HORIZON (khong ap luat GO)")
    r.add_argument("--folds", type=int, default=0)
    r.add_argument("--self-tests", action="store_true")
    v = sub.add_parser("validate")
    v.add_argument("--labels", default="/home/ubuntu/label_15m")
    v.add_argument("--out"); v.add_argument("--skip-selftest", action="store_true")
    v.add_argument("--k", type=int, default=2,
                   help="so UNG VIEN cua round (mac dinh 2: A44 + V0) => he so CI = inflate(k)")
    v.add_argument("--horizon", default="4h", choices=["4h", "72h"])
    v.add_argument("--label-horizon", default=None, choices=["4h", "12h", "24h", "72h"],
                   help="mac dinh = --horizon; khac di => KINH TE CROSS-HORIZON (khong ap luat GO)")
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
