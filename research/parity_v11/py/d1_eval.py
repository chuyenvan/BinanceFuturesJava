#!/usr/bin/env python3
"""PARITY_V11_WINDOW luot D (D+1) — danh gia 1 ngay bang Vision offline vs live 242.
Theo docs/prereg/PREREG_PARITY_V11_WINDOW.md (481701b2): P1-F/P1/P1-m/MD/FUND/NET/S1-I/S1-m/S1-V/GV-I/GV-O/P2/P3/CTL/TSX.
Khong doc/ghi 242. Input: ~/claude_master/parity_v11w/{live,runs/d21,vision}.

argv: stage (gate|fund|s1|p2|p3|ctl|labels)
"""
import glob
import gzip
import io
import json
import os
import re
import sys
import zlib
import datetime as dt

import numpy as np
import pandas as pd
import onnxruntime as ort

W = os.path.expanduser("~/claude_master/parity_v11w")
LIVE, RUN = W + "/live", W + "/runs/d21"
MOD = os.path.expanduser("~/claude_master/parity_1020/raw242/models")
T0, T1 = 1792543980000, 1792627140000
F32 = np.float32
FEATS = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
         "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
         "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown",
         "marketBreadthStrength", "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw",
         "fundingRateAvg24H", "fundingRateTrend", "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
         "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"]
FUND_GATE = ["fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend"]
NONFUND_GATE = [f for f in FEATS if f not in FUND_GATE]
F45 = ["f%d" % i for i in range(45)]
FUND_T1 = ["f%d" % i for i in list(range(17, 26)) + [32]]
OI_T1 = ["f%d" % i for i in range(40, 45)]
DYN_MIN, SCORE_BASE, DYN_MULT, GS = F32(0.26787), F32(0.15), F32(1.28760), F32(1.55)


def f7(t):
    return dt.datetime.utcfromtimestamp(t / 1000 + 7 * 3600).strftime("%m-%d %H:%M")


def read_gz(p):
    raw = b""
    try:
        with gzip.open(p, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                raw += b
    except (EOFError, OSError, zlib.error):
        pass
    if not raw:
        return None
    txt = raw.decode(errors="ignore")
    lines = txt.splitlines()
    if not txt.endswith("\n"):
        lines = lines[:-1]
    if len(lines) < 2:
        return None
    return pd.read_csv(io.StringIO("\n".join(lines)))


def eq(a, b, tol=1e-6):
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    return (np.abs(a - b) <= tol * (1 + np.abs(b))) | (np.isnan(a) & np.isnan(b))


def load_live_gate():
    L = pd.concat([d for d in (read_gz(p) for p in sorted(glob.glob(LIVE + "/dumps/feat_dump_*.csv.gz"))) if d is not None],
                  ignore_index=True)
    L["min"] = (L.ts // 60000) * 60000
    L = L.drop_duplicates("min", keep="last")
    L = L[(L["min"] >= T0) & (L["min"] <= T1)].sort_values("min").reset_index(drop=True)
    return L


def load_bt():
    B = pd.read_csv(RUN + "/out_BT.csv.gz")
    return B[(B["min"] >= T0) & (B["min"] <= T1)].sort_values("min").reset_index(drop=True)


def p15_session():
    return ort.InferenceSession(MOD + "/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx",
                                providers=["CPUExecutionProvider"])


def net_session():
    return ort.InferenceSession(MOD + "/c3_models/g015x26_f15_cut20251231.onnx", providers=["CPUExecutionProvider"])


def s1_session():
    return ort.InferenceSession(MOD + "/c3_models/s1a2x1_cut20251231.onnx", providers=["CPUExecutionProvider"])


def pwin(sess, X):
    nm = sess.get_inputs()[0].name
    outs = [o.name for o in sess.get_outputs()]
    pidx = [i for i, o in enumerate(outs) if "prob" in o.lower()]
    pidx = pidx[0] if pidx else len(outs) - 1
    o = sess.run(None, {nm: np.asarray(X, np.float32)})[pidx]
    if isinstance(o, list):
        return np.array([float(np.float32(d.get(1, d.get("1", np.nan)))) for d in o], dtype=np.float32)
    return np.asarray(o)[:, -1].astype(np.float32)


# ADDENDUM1 (MAJ-1): log loc 10-21 (+07) chi phu toi 10-21 23:59 (+07) = 16:59 UTC; noi them log day du
# 10-22 00:00-07:05 (+07) (owner keo 10-24, zgrep tren full.log* cua 242) de phu het cua so UTC 10-21
# (dong [GATE-RATIO] cua gio 23 UTC in luc 07:01 +07 10-22).
LOGS = [LIVE + "/raw/loglines_1021.gz", LIVE + "/full_1022_0000_0705.log.gz"]
_LOG = []


def loglines(day=None):
    if not _LOG:
        for p in LOGS:
            with gzip.open(p, "rt", errors="ignore") as f:
                _LOG.extend(f.read().splitlines())
    return _LOG


PAT_T = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)")


def lt(s):
    m = PAT_T.match(s)
    if not m:
        return None
    d, mo, y, hh, mi, ss, ms = m.groups()
    return int(dt.datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss),
                           tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000)


# ---------------------------------------------------------------- ADDENDUM1: q theo gio
H = 3600000


def qlog_by_hour():
    """CRIT-1 (audit OC1023): LiveGateRollingRatio.noteCandidate() goi logHour() khi SANG gio => dong
    [GATE-RATIO] in luc gio h+1 (+07 log) la q DA DUNG trong gio UTC h. Map: h = floor(t_log/H)*H - H.
    (ab5bbe44 map sai thanh h = floor(t_log/H)*H.) Tra {h: (q_t9, buffer_log, eval_log, t_log)}."""
    out = {}
    for ln in loglines():
        if "[GATE-RATIO] q_t=" in ln and "q_t9=" in ln:
            t = lt(ln)
            mm = re.search(r"q_t9=([0-9.]+)", ln)
            mb = re.search(r"buffer=(\d+)", ln)
            me = re.search(r"eval=(\d+)", ln)
            if t and mm:
                out[(t // H) * H - H] = (float(mm.group(1)), int(mb.group(1)) if mb else -1,
                                         int(me.group(1)) if me else -1, int(t))
    return out


def restarts():
    return sorted(t for t in (lt(s) for s in loglines() if "MainClass:" in s) if t)


_QR = {}


def q_replay(h):
    """q replay causal (prereg §4 P3) tu gate_ratio_live.bin: q dau gio h tren record ts in [h-90d, h);
    gio co restart: record flush truoc restart (luat restart giu nguyen nhu ab5bbe44).
    Tra (q, m, mode, t_restart)."""
    if not _QR:
        sys.path.insert(0, os.path.expanduser("~/claude_master/1016/grr"))
        import grr_lib
        bts, br, nbad = grr_lib.load(LIVE + "/raw/gate_ratio_live.bin")
        bts = np.asarray(bts, np.int64)
        o = np.argsort(bts, kind="stable")
        _QR.update(sorted_in_file=bool(np.all(np.diff(bts) >= 0)), bts=bts[o], br32=br[o].astype(np.float32),
                   nbad=int(nbad), rs=restarts())
    bts, br32 = _QR["bts"], _QR["br32"]
    PCT = 0.99995083

    def q_at(cut_hi):
        i0 = np.searchsorted(bts, h - 90 * 86400000, "left")
        i1 = np.searchsorted(bts, cut_hi, "left")
        a = br32[i0:i1]
        m = len(a)
        k = min(m - 1, max(0, int(np.floor(PCT * (m - 1)))))
        return float(np.partition(a, k)[k]), m

    rs = [t for t in _QR["rs"] if h <= t < h + H]
    if rs:
        cut = (rs[-1] // 60000) * 60000 - 60000
        q, m = q_at(cut + 1)
        return q, m, "restart", rs[-1]
    q, m = q_at(h)
    return q, m, "normal", None


def gate_tick(t_log):
    """Dong [GATE] in trong phut M+1 (+07 log, giay :06-:40) la quyet dinh cua tick (nen) M:
    tick = floor(t_log/60000)*60000 - 60000. Kiem tren log 10-22 (co dong [MAP] tick=) o stage gv."""
    return (t_log // 60000) * 60000 - 60000


# ---------------------------------------------------------------- stage gate
def stage_gate():
    L, B = load_live_gate(), load_bt()
    J = L.merge(B, on="min", suffixes=("_l", "_b"))
    res = {"n_live_minutes": int(len(L)), "n_bt_minutes": int(len(B)), "n_join": int(len(J)),
           "live_min": f7(int(L["min"].min())), "live_max": f7(int(L["min"].max())),
           "missing_in_live": [f7(int(x)) for x in sorted(set(B["min"]) - set(L["min"]))],
           "missing_in_bt": [f7(int(x)) for x in sorted(set(L["min"]) - set(B["min"]))]}
    okall = np.ones(len(J), bool)
    perf = {}
    for f in NONFUND_GATE:
        o = eq(J[f + "_l"], J[f + "_b"])
        okall &= o
        perf[f] = round(float(o.mean()), 6)
    res["P1F"] = {"ALL30": float(okall.mean()), "n_bad_minutes": int((~okall).sum()),
                  "bad_minutes": [f7(int(x)) for x in J["min"][~okall]],
                  "per_feature_lt_1": {k: v for k, v in perf.items() if v < 1.0}}
    # 3 cot funding: bao cao (luot D khong phan quyet)
    res["FUND3_gate_roundD"] = {f: float(eq(J[f + "_l"], J[f + "_b"]).mean()) for f in FUND_GATE}
    # p15
    sess = p15_session()
    nm = sess.get_inputs()[0].name
    Xoff = J[[f + "_b" for f in FEATS]].astype(np.float32).copy()
    Xoff.columns = FEATS
    for f in FUND_GATE:      # luot D: tiem funding live
        Xoff[f] = J[f + "_l"].astype(np.float32)
    p15off = sess.run(None, {nm: Xoff.values})[0].reshape(-1)
    Xlive = J[[f + "_l" for f in FEATS]].astype(np.float32)
    p15live_onnx = sess.run(None, {nm: Xlive.values})[0].reshape(-1)
    J["p15_off"] = p15off
    rel = np.abs(J.p15_out.values - p15off) / np.abs(p15off)
    res["P1"] = {"n": int(len(J)), "median_rel": float(np.nanmedian(rel)),
                 "frac_le_1e-3": float(np.nanmean(rel <= 1e-3)), "frac_le_1e-4": float(np.nanmean(rel <= 1e-4)),
                 "max_rel": float(np.nanmax(rel)), "n_gt_1e-3": int((rel > 1e-3).sum()),
                 "PASS": bool(np.nanmedian(rel) <= 1e-4 and np.nanmean(rel <= 1e-3) >= 0.98)}
    m = np.abs(p15live_onnx - J.p15_out.values) / np.abs(J.p15_out.values)
    res["P1m"] = {"frac_le_1e-6": float(np.nanmean(m <= 1e-6)), "max_rel": float(np.nanmax(m))}
    res["MD"] = {}
    for lc, bc in (("rateDownAvg", "r_down"), ("rateUpAvg", "r_up"), ("rateDown15MAvg", "r_down15")):
        res["MD"][lc] = float(eq(J[lc], J[bc]).mean())
    # chi tiet phut lech
    bad = J[~okall].copy()
    bad["rel_p15"] = rel[~okall]
    dcols = [f for f in NONFUND_GATE if not eq(J[f + "_l"], J[f + "_b"]).all()]
    bad["min_s"] = bad["min"].map(f7)
    bd = bad[["min_s", "rel_p15"]].copy()
    for f in dcols:
        bd[f + "_live"] = bad[f + "_l"].values
        bd[f + "_bt"] = bad[f + "_b"].values
    res["bad_detail"] = bd.round(6).to_dict("records")
    # nsym (K3)
    res["nsym_bt"] = J[["min", "nsym"]].assign(min=lambda x: x["min"].map(f7)).to_dict("records")
    J.assign(p15_off=p15off, p15_onnx_live=p15live_onnx).to_csv(W + "/work/join_gate.csv.gz", index=False)
    json.dump(res, open(W + "/work/gate_d1.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k not in ("nsym_live", "bad_detail")}, indent=1, default=str))


# ---------------------------------------------------------------- stage fund
def load_live45():
    A = read_gz(LIVE + "/feat45_live.csv.gz")
    Bb = read_gz(LIVE + "/feat45_live_b.csv.gz")
    # ADDENDUM1: 7 file predictionSymbol 10-22 00:00-00:06 (+07) CO tren Oracle (keo 10-23) nhung khong duoc
    # giai ma vao feat45_live_b (bat dau tu 00:07) => giai ma bang Pa1020Feat (py/psym_c_build.sh).
    Cc = read_gz(LIVE + "/feat45_live_c.csv.gz") if os.path.exists(LIVE + "/feat45_live_c.csv.gz") else None
    F = pd.concat([x for x in (A, Bb, Cc) if x is not None], ignore_index=True)
    F = F.drop_duplicates(["ts", "symbol"], keep="last")
    F["min"] = (F.ts // 60000) * 60000
    F = F[(F["min"] >= T0) & (F["min"] <= T1)]
    return F


def stage_fund():
    F = load_live45()
    U = pd.read_csv(RUN + "/fund_BT.csv.gz", dtype={"symbol": str})
    U = U[(U["min"] >= T0) & (U["min"] <= T1)]
    J = U.merge(F, on=["min", "symbol"], suffixes=("_b", "_l"))
    cols = [c for c in F45 if c not in FUND_T1 and c not in OI_T1]
    ok = np.ones(len(J), bool)
    perc = {}
    for c in cols:
        o = eq(J[c + "_l"], J[c + "_b"])
        ok &= o
        if o.mean() < 1:
            perc[c] = round(float(o.mean()), 6)
    J["ok"] = ok
    bym = J.groupby("min").ok.all()
    res = {"rows_bt": int(len(U)), "rows_live": int(len(F)), "rows_join": int(len(J)),
           "bt_rows_missing_in_live": int(len(U) - len(J)),
           "rows_ok_frac": float(ok.mean()), "minutes": int(len(bym)), "minutes_all_ok": float(bym.mean()),
           "feat_lt_1": perc,
           "bad_minutes": [f7(int(x)) for x in bym[~bym].index],
           "rows_by_minute_live": F.groupby("min").size().describe().to_dict()}
    # funding f17-f25,f32: bao cao rieng (luot D: tiem live, khong phan quyet)
    res["fund_feats_match_report_only"] = {c: float(eq(J[c + "_l"], J[c + "_b"]).mean()) for c in FUND_T1}
    # OI f40-44
    res["oi_feats_report_only"] = {c: float(eq(J[c + "_l"], J[c + "_b"]).mean()) for c in OI_T1}
    J.to_csv(W + "/work/join_fund.csv.gz", index=False)
    json.dump(res, open(W + "/work/fund_d1.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:3000])


# ---------------------------------------------------------------- stage net
def stage_net():
    F = pd.read_csv(W + "/work/join_fund.csv.gz", dtype={"symbol": str})
    net = net_session()
    Xl = F[[c + "_l" for c in F45]].values.astype(np.float32)
    Xb = F[[c + "_b" for c in F45[:40]]].values.astype(np.float32)
    for j, c in enumerate(F45[:40]):
        if c in FUND_T1:
            Xb[:, j] = Xl[:, j]
    Xb = np.concatenate([Xb, Xl[:, 40:45]], axis=1)
    pwl, pwb = pwin(net, Xl), pwin(net, Xb)
    d = np.abs(pwl - pwb)
    F["net_l"], F["net_b"] = pwl, pwb
    bym = F.assign(d=d).groupby("min").apply(lambda x: (x.d <= 1e-6 * (1 + np.abs(x.net_b))).all())
    res = {"rows": int(len(F)), "net015_le1e-6": float((d <= 1e-6 * (1 + np.abs(pwb))).mean()),
           "max_absdiff": float(d.max()), "minutes": int(len(bym)), "minutes_all_ok": float(bym.mean()),
           "bad_minutes": [f7(int(x)) for x in bym[~bym].index]}
    F[["min", "symbol", "net_l", "net_b"]].to_csv(W + "/work/net_pw.csv.gz", index=False)
    # net live cho TOAN BO symbol cua predictionSymbol (dung cho gateValue/P2 nhu par_a)
    L = load_live45()
    XL = L[F45].values.astype(np.float32)
    L[["min", "symbol"]].assign(net_l=pwin(net, XL)).to_csv(W + "/work/net_live_all.csv.gz", index=False)
    json.dump(res, open(W + "/work/net_d1.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:2000])


# ---------------------------------------------------------------- helpers S1
LEGACY = set(x.strip() for x in open(LIVE + "/raw/ts_ext_legacy.txt") if x.strip()
             and not x.startswith("#") and "," not in x)


def load_s1():
    fs = sorted(glob.glob(LIVE + "/s1/s1_dump_2026102[12]_*.csv.gz"))
    S = pd.concat([d for d in (read_gz(p) for p in fs) if d is not None], ignore_index=True)
    S = S[(S.ts >= T0) & (S.ts <= T1)].drop_duplicates(["ts", "symbol"], keep="last")
    return S


def load_sel():
    fs = sorted(glob.glob(LIVE + "/dumps/sel_dump_2026102[12]_*.csv.gz"))
    S = pd.concat([d for d in (read_gz(p) for p in fs) if d is not None], ignore_index=True)
    S = S[(S.ts >= T0) & (S.ts <= T1)].drop_duplicates(["ts", "symbol"], keep="last")
    return S


def rank_first(v, asc=True):
    order = sorted(range(len(v)), key=lambda i: ((v[i] if asc else -v[i]), i))
    r = np.empty(len(v), dtype=int)
    for k, i in enumerate(order):
        r[i] = k + 1
    return r


def stage_s1():
    S = load_s1()
    sel = load_sel()
    sess = s1_session()
    nm = sess.get_inputs()[0].name
    X = S[["f%d" % i for i in range(9)]].values.astype(np.float32)
    sc = -sess.run(None, {nm: X})[0].reshape(-1)   # live score = -onnx output (da kiem: corr -1.0, |ratio|=1)
    d = np.abs(sc - S.score.values.astype(np.float32))
    tol = 1e-6 * (1 + np.abs(S.score.values))
    res = {"S1_m": {"rows": int(len(S)), "frac_le_1e-6": float((d <= tol).mean()), "max_abs": float(d.max())}}
    # S1-I
    m = sel.merge(S, on=["ts", "symbol"], suffixes=("_sel", "_s1"))
    res["S1_I_selectorScore_vs_score"] = float(np.nanmax(np.abs(np.abs(m.selectorScore) - np.abs(m.score))))
    ok = 0
    tot = 0
    bad = []
    for ts, g in sel.groupby("ts"):
        sg = S[S.ts == ts]
        if len(sg) == 0:
            continue
        cand = sg[~sg.symbol.isin(LEGACY)].sort_values(["score", "symbol"])
        top = list(cand.symbol.head(24))
        want = list(g.sort_values("rank").symbol)
        tot += 1
        if top == want:
            ok += 1
        else:
            bad.append({"ts": f7(int(ts)), "jaccard": len(set(top) & set(want)) / 24.0,
                        "n": len(want), "rank0": int(g["rank"].min())})
    res["S1_I"] = {"minutes": tot, "exact_order": ok, "frac": ok / max(1, tot), "bad": bad[:20]}
    json.dump(res, open(W + "/work/s1_d1.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:2500])


def stage_gv_p2():
    net = pd.read_csv(W + "/work/net_live_all.csv.gz", dtype={"symbol": str})
    nb = pd.read_csv(W + "/work/net_pw.csv.gz", dtype={"symbol": str})
    nbmap = {(int(a), b): c for a, b, c in zip(nb["min"], nb.symbol, nb.net_b)}
    sel = load_sel()
    s1 = load_s1()[["ts", "symbol", "score"]]
    G = pd.read_csv(W + "/work/join_gate.csv.gz")
    p15off = dict(zip(G["min"].astype(np.int64), G["p15_off"]))
    QL = qlog_by_hour()
    RS = restarts()
    rows = []
    skipped = []
    for ts, g in sel.groupby("ts"):
        sc = s1[s1.ts == ts].set_index("symbol").score
        nw = net[net["min"] == ts].set_index("symbol")
        uni = sorted(s for s in sc.index if s in nw.index)
        if len(uni) < 20:
            skipped.append(f7(int(ts)))
            continue
        rS = rank_first(np.array([sc[s] for s in uni], np.float32), True)
        for tag in ("live", "off"):
            pw = np.array([nw.loc[s, "net_l"] for s in uni], np.float32)
            if tag == "off":
                pw = np.array([nbmap.get((int(ts), s), nw.loc[s, "net_l"]) for s in uni], np.float32)
            pS = rank_first(pw, False)
            byP = np.empty(len(uni), np.float32)
            for i in range(len(uni)):
                byP[pS[i] - 1] = pw[i]
            gv = {s: float(np.float32(1.0) - np.float32(byP[rS[i] - 1])) for i, s in enumerate(uni)}
            for _, rr in g.iterrows():
                rows.append((int(ts), rr.symbol, tag, float(rr.gateValue), float(gv.get(rr.symbol, np.nan)),
                             float(rr.p15), float(rr.selectorScore)))
    Gd = pd.DataFrame(rows, columns=["ts", "symbol", "tag", "gv_live", "gv_calc", "p15", "sscore"])
    res = {"sel_minutes": int(sel.ts.nunique()), "skipped_minutes_no_net_live": skipped}
    for tag, name in (("live", "GV_I"), ("off", "GV_O")):
        x = Gd[Gd.tag == tag]
        res[name] = {"n": int(len(x)), "n_minutes": int(x.ts.nunique()),
                     "frac_le1e-6": float(eq(x.gv_calc, x.gv_live).mean()),
                     "n_diff": int((~eq(x.gv_calc, x.gv_live)).sum()),
                     "bad_minutes": [f7(int(t)) for t in sorted(set(x.ts[~eq(x.gv_calc, x.gv_live)]))][:30]}
    x = Gd[Gd.tag == "live"].merge(Gd[Gd.tag == "off"][["ts", "symbol", "gv_calc"]].rename(columns={"gv_calc": "gv_off"}),
                                   on=["ts", "symbol"], how="left")
    x["h"] = x.ts // H * H

    # ADDENDUM1: q live theo PHUT. Gio co restart tai tr: tick >= phut(tr)-1' do process moi quyet dinh voi q
    # tinh luc restart (= dong [GATE-RATIO] in luc h+1); tick truoc do do process cu quyet dinh voi q dau gio
    # (process cu tat truoc h+1 nen KHONG co dong log) => dung q replay 'normal' cua gio h (danh dau q_src) va
    # kiem bang khoang thr=[..] cua dong [GATE] (xem GATE_LOG.thr_range_match).
    def qlive(ts):
        h = ts // H * H
        rs = [t for t in RS if h <= t < h + H]
        if rs and ts < (rs[-1] // 60000) * 60000 - 60000:
            return q_replay(h)[0], "replay_pre_restart"
        if h in QL:
            return QL[h][0], "log"
        return np.nan, "missing"

    ql = {int(t): qlive(int(t)) for t in x.ts.unique()}
    x["q"] = x.ts.map(lambda t: ql[int(t)][0])
    x["q_src"] = x.ts.map(lambda t: ql[int(t)][1])
    qo = {int(h): q_replay(int(h))[0] for h in x.h.unique()}
    x["q_off"] = x.h.map(qo)          # ADDENDUM1: phia offline dung q REPLAY (prereg §4 P2), khong dung q log
    x["p15_off"] = x.ts.map(p15off)
    need = ["q", "q_off", "p15_off", "gv_off"]
    dmask = x[need].isna().any(axis=1)
    dropped = {f7(int(t)): [c for c in need if x.loc[x.ts == t, c].isna().any()] for t in sorted(set(x.ts[dmask]))}
    x = x[~dmask].reset_index(drop=True)
    fac_l = np.maximum(DYN_MIN, (x.gv_live.astype(np.float32) / SCORE_BASE) * DYN_MULT).astype(np.float32)
    fac_o = np.maximum(DYN_MIN, (x.gv_off.astype(np.float32) / SCORE_BASE) * DYN_MULT).astype(np.float32)
    q_l = x.q.astype(np.float32).values
    q_o = x.q_off.astype(np.float32).values
    thr_l = (q_l * fac_l.values * GS).astype(np.float32)
    thr_o = (q_o * fac_o.values * GS).astype(np.float32)
    x["pass_l"] = ~(x.p15.astype(np.float32).values < thr_l)
    x["pass_o"] = ~(x.p15_off.astype(np.float32).values < thr_o)
    x["thr_l"], x["thr_o"] = thr_l, thr_o
    x["rl"] = x.p15.astype(np.float32).values / thr_l
    x["ro"] = x.p15_off.astype(np.float32).values / thr_o
    fl = x[x.pass_l != x.pass_o]
    ml = np.abs(x.p15 - x.thr_l) / np.abs(x.thr_l)
    mo = np.abs(x.p15_off - x.thr_o) / np.abs(x.thr_o)
    heavy = (ml > 0.01) | (mo > 0.01)
    hv = (x.pass_l != x.pass_o) & heavy
    res["P2"] = {"n_pairs": int(len(x)), "n_minutes": int(x.ts.nunique()), "minutes_dropped": dropped,
                 "q_src_minutes": {k: int(v) for k, v in x.groupby("q_src").ts.nunique().items()},
                 "q_live_eq_q_off_frac": float((x.q == x.q_off).mean()),
                 "n_pass_live": int(x.pass_l.sum()), "n_pass_off": int(x.pass_o.sum()),
                 "n_flip": int(len(fl)), "n_flip_minutes": int(fl.ts.nunique()),
                 "n_flip_heavy": int(hv.sum()),
                 "flip_detail": [{"min": f7(int(x.ts[i])), "symbol": x.symbol[i], "p15": float(x.p15[i]),
                                  "p15_off": float(x.p15_off[i]), "rel_l": float(ml[i]), "rel_o": float(mo[i]),
                                  "thr_l": float(x.thr_l[i]), "thr_o": float(x.thr_o[i]), "heavy": bool(hv[i])}
                                 for i in fl.index[:30]],
                 "max_rq_live": float(x.rl.max()), "max_rq_off": float(x.ro.max()),
                 "n_rq_ge_09_live": int((x.rl >= 0.9).sum()), "n_rq_ge_09_off": int((x.ro >= 0.9).sum()),
                 "n_rq_ge_08_live": int((x.rl >= 0.8).sum()),
                 "PASS": bool(hv.sum() == 0)}
    # [GATE] log: map dong log -> tick (ADDENDUM1: ab5bbe44 map theo phut ghi log, lech 1 phut)
    gl = []
    tick_chk = []
    last_map = None
    for ln in loglines():
        if "[MAP] tick=" in ln:
            mt = re.search(r"\[MAP\] tick=(\d+)", ln)
            last_map = int(mt.group(1)) if mt else None
        elif "[GATE] " in ln and "n_pass=" in ln:
            t = lt(ln)
            mm = re.search(r"thr=\[([^\]]*)\] n_cand=(\d+) n_rej=(\d+) n_pass=(\d+) n_skipfull=(\d+)", ln)
            if t and mm:
                tk = gate_tick(int(t))
                if last_map is not None:
                    tick_chk.append(last_map == tk)
                gl.append((tk, mm.group(1), int(mm.group(4))))
                last_map = None
    gl = pd.DataFrame(gl, columns=["min", "thr_rng", "n_pass_log"]).drop_duplicates("min", keep="last")
    # Khoang thr=[..] cua dong [GATE] in EntryGate.threshold(gv) = base TINH MIN_MOMENTUM_15M (0,008)*fac*scale
    # (DetectEntrySignal2TradeNormal @627e9b34), KHONG phai nguong ratio q_t => chi dung de kiem fac/gv/tick-map.
    x["thr_static"] = (F32(0.008) * fac_l.values * GS).astype(np.float32)
    cmp_pass = x.groupby("ts").agg(pass_calc=("pass_l", "sum"), thr_min=("thr_static", "min"),
                                   thr_max=("thr_static", "max")).reset_index().rename(columns={"ts": "min"})
    mrg = gl.merge(cmp_pass, on="min")

    def rng_ok(r):
        if r.thr_rng.strip() == "-..-":
            return False
        a, b = (float(v) for v in r.thr_rng.split(".."))
        return abs(a - r.thr_min) <= 6e-6 and abs(b - r.thr_max) <= 6e-6

    mrg["thr_ok"] = mrg.apply(rng_ok, axis=1)
    res["GATE_LOG"] = {"n_lines": int(len(gl)), "n_minutes_join": int(len(mrg)),
                       "map_tick_check": {"n_lines_with_MAP": len(tick_chk), "n_tick_eq": int(sum(tick_chk))},
                       "n_match": int((mrg.n_pass_log == mrg.pass_calc).sum()),
                       "sum_log": int(mrg.n_pass_log.sum()), "sum_calc": int(mrg.pass_calc.sum()),
                       "thr_range_match_base0008": int(mrg.thr_ok.sum()),
                       "thr_range_mismatch": mrg[~mrg.thr_ok].assign(min=lambda d: d["min"].map(f7))[
                           ["min", "thr_rng", "thr_min", "thr_max"]].to_dict("records")[:20],
                       "mismatch": mrg[mrg.n_pass_log != mrg.pass_calc].assign(
                           min=lambda d: d["min"].map(f7))[["min", "n_pass_log", "pass_calc"]].to_dict("records")[:20],
                       "gate_lines_not_joined": [f7(int(t)) for t in sorted(set(gl["min"]) - set(mrg["min"]))
                                                 if T0 <= t <= T1]}
    x.to_csv(W + "/work/p2_pairs.csv.gz", index=False)
    json.dump(res, open(W + "/work/gv_p2_d1.json", "w"), indent=1, default=str)
    print(json.dumps(res, indent=1, default=str)[:4000])


def stage_p3():
    QL = qlog_by_hour()
    hours = list(range((T0 // H) * H, (T1 // H) * H + H, H))   # 24 gio UTC cua cua so (00..23 UTC 10-21)
    hu = lambda h: dt.datetime.utcfromtimestamp(h / 1000).strftime("%m-%d %H:%M")
    rows = []
    for h in sorted(QL):
        q_log, buf, ev, tlog = QL[h]
        q, m, mode, tr = q_replay(h)
        rows.append({"h_utc": hu(h), "h": h, "log_at_p07": f7(tlog), "q_log": q_log, "q_rep": q, "m": m,
                     "buffer_log": buf, "eval_log": ev, "m_eq_buf_minus_eval": bool(m == buf - ev),
                     "mode": mode, "restart_p07": f7(tr) if tr else "", "in_window": h in hours})
    Q = pd.DataFrame(rows)
    Q["rel"] = (Q.q_log - Q.q_rep).abs() / Q.q_rep       # ADDENDUM1: bo co match6 (so 9 vs 6 chu so) -> rel
    Qw = Q[Q.in_window]
    have = set(Q.h[Q.in_window])
    res = {"n_hours_expected": len(hours), "n_hours_measured": int(len(Qw)),
           "hours_missing_utc": [hu(h) for h in hours if h not in have],
           "n_rel_gt_1e-6": int((Qw.rel > 1e-6).sum()),
           "max_rel": float(Qw.rel.max()), "med_rel": float(Qw.rel.median()),
           "n_m_eq_buf_minus_eval": int(Qw.m_eq_buf_minus_eval.sum()),
           "restart_hours_utc": Qw[Qw["mode"] == "restart"].h_utc.tolist(),
           "buffer": {"n": int(len(_QR["bts"])), "bad_chunks": _QR["nbad"], "sorted_in_file": _QR["sorted_in_file"],
                      "first": f7(int(_QR["bts"].min())), "last": f7(int(_QR["bts"].max()))},
           "pre_window_lines": Q[~Q.in_window].drop(columns=["h"]).to_dict("records"),
           "mismatch": Qw[Qw.rel > 1e-6].drop(columns=["h"]).to_dict("records")[:30]}
    res["PASS"] = bool(not res["hours_missing_utc"] and res["n_rel_gt_1e-6"] == 0)
    Q.drop(columns=["h"]).to_csv(W + "/work/p3_q.csv", index=False)
    json.dump(res, open(W + "/work/p3_d1.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "pre_window_lines"}, indent=1, default=str)[:3500])


def stage_ctl():
    a = json.load(open(RUN + "/cmp_ctl_gate.json"))
    b = json.load(open(RUN + "/cmp_ctl_fund.json"))
    print(json.dumps({"gate": {k: a[k] for k in ("rows_ref", "rows_new", "rows_both", "only_ref", "rows_bit_nonfund",
                                                  "rows_tol_nonfund", "n_bad_minutes_nonfund", "cols_diff_nonfund")},
                      "fund": {k: b[k] for k in ("rows_ref", "rows_new", "rows_both", "only_ref", "rows_bit_nonfund",
                                                 "rows_tol_nonfund", "n_bad_minutes_nonfund", "cols_diff_nonfund",
                                                 "cols_diff_fund")}}, indent=1))


if __name__ == "__main__":
    os.makedirs(W + "/work", exist_ok=True)
    {"gate": stage_gate, "fund": stage_fund, "net": stage_net, "s1": stage_s1,
     "gv": stage_gv_p2, "p3": stage_p3, "ctl": stage_ctl}[sys.argv[1]]()
