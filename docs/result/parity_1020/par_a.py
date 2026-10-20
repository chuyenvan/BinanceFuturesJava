#!/usr/bin/env python3
"""PARITY 1020 — phan A: market rates (1), p15 (2), gate r/q_t + flip (3), P3 q_t log vs replay.
Audit-only. Doc: raw242/dumps (feat_dump, sel_dump 242), devexport_1016_1020_md.csv.gz (offline, cung du lieu 242),
raw242/gate_ratio_live.bin (buffer 242, copy doc), raw242/loglines.gz (log 242 da loc)."""
import glob, gzip, io, json, re, sys, zlib, datetime as dt
import numpy as np, pandas as pd, onnxruntime as ort
sys.path.insert(0, "/home/ubuntu/claude_master/1016/grr")
import grr_lib  # noqa: E402

W = "/home/ubuntu/claude_master/parity_1020"
H = 3600000
T0 = 1792148400000          # nen 2026-10-16 18:00 +07 (quyet dinh 18:01) = bat dau cua so
FEATS = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
         "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
         "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown",
         "marketBreadthStrength", "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw",
         "fundingRateAvg24H", "fundingRateTrend", "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
         "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"]
F32 = np.float32
DYN_MIN, SCORE_BASE, DYN_MULT, GS = F32(0.26787), F32(0.15), F32(1.28760), F32(1.55)
PCT = float(F32(0.999950829))


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
    try:
        return pd.read_csv(io.StringIO("\n".join(lines)))
    except Exception:
        return None


def stats(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    a, b = a[m], b[m]
    d = np.abs(a - b)
    tol = 1e-6 * (1 + np.abs(b))
    rel = d / (np.abs(b) + 1e-12)
    return dict(n=int(m.sum()), frac_match_1e6=float((d <= tol).mean()), med_abs=float(np.median(d)),
                p99_abs=float(np.quantile(d, .99)), max_abs=float(d.max()), med_rel=float(np.median(rel)),
                p99_rel=float(np.quantile(rel, .99)), corr=float(np.corrcoef(a, b)[0, 1]) if len(a) > 2 else None,
                spearman=float(pd.Series(a).rank().corr(pd.Series(b).rank())) if len(a) > 2 else None)


res = {}
# ---------------- live feat_dump ----------------
L = pd.concat([d for d in (read_gz(p) for p in sorted(glob.glob(W + "/raw242/dumps/feat_dump_*.csv.gz"))) if d is not None],
              ignore_index=True)
L["min"] = (L.ts // 60000) * 60000
L = L.drop_duplicates("min", keep="last")
L = L[L["min"] >= T0]
E = pd.read_csv(W + "/devexport_1016_1020_md.csv.gz")
E["min"] = E.ts.astype("int64")
best = None
for off in (-60000, 0, 60000):
    J = L.merge(E.assign(min=E["min"] + off), on="min", suffixes=("_l", "_e"))
    ok = int((np.abs(J["momentum24H_l"] - J["momentum24H_e"]) <= 1e-6 * (1 + np.abs(J["momentum24H_e"]))).sum())
    if best is None or ok > best[1]:
        best = (off, ok, J)
off, _, J = best
res["align"] = dict(offset_ms=off, n_live=int(len(L)), n_off=int((E["min"] >= T0).sum()), n_joined=int(len(J)),
                    live_min=f7(L["min"].min()), live_max=f7(L["min"].max()))
lm = set(L["min"]); em = set(E["min"] + off)
res["align"]["live_not_off"] = sorted(f7(x) for x in lm - em)[:30]
res["align"]["n_live_not_off"] = len(lm - em)
res["align"]["n_off_not_live"] = len({x for x in em if x >= T0 and x <= L["min"].max()} - lm)
res["align"]["off_not_live_sample"] = sorted(f7(x) for x in em - lm if T0 <= x <= L["min"].max())[:30]
print("ALIGN", json.dumps(res["align"])[:1500])

# (1) market rates
res["rates"] = {}
for lc, ec in [("rateDownAvg", "o_rateDownAvg"), ("rateUpAvg", "o_rateUpAvg"), ("rateDown15MAvg", "o_rateDown15MAvg")]:
    res["rates"][lc] = stats(J[lc], J[ec])
    print("RATE", lc, json.dumps(res["rates"][lc]))
# feature-level (tom tat)
res["features"] = {f: stats(J[f + "_l"], J[f + "_e"]) for f in FEATS}
for f in FEATS:
    s = res["features"][f]
    print("FEAT %-24s match=%.4f med_rel=%.2e p99_rel=%.2e max_abs=%.3g sp=%.5f" % (f, s["frac_match_1e6"], s["med_rel"], s["p99_rel"], s["max_abs"], s["spearman"] or 0))

# (2) p15
sess = ort.InferenceSession(W + "/raw242/models/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx", providers=["CPUExecutionProvider"])
nm = sess.get_inputs()[0].name
J["p15_off"] = sess.run(None, {nm: J[[f + "_e" for f in FEATS]].astype(np.float32).values})[0].reshape(-1)
J["p15_ort_live"] = sess.run(None, {nm: J[[f + "_l" for f in FEATS]].astype(np.float32).values})[0].reshape(-1)
res["p15_model_on_live_feat"] = stats(J.p15_ort_live, J.p15_out)
res["p15"] = stats(J.p15_out, J.p15_off)
rel = (J.p15_out - J.p15_off).abs() / J.p15_off.abs().clip(lower=1e-12)
J["p15_rel"] = rel
res["P1"] = dict(n=int(len(J)), med_rel=float(rel.median()), frac_le_1e3=float((rel <= 1e-3).mean()),
                 frac_le_1e4=float((rel <= 1e-4).mean()), n_gt_1e3=int((rel > 1e-3).sum()),
                 PASS=bool(rel.median() <= 1e-4 and (rel <= 1e-3).mean() >= 0.98))
print("P15 model-on-live", json.dumps(res["p15_model_on_live_feat"]))
print("P15 live vs off", json.dumps(res["p15"]))
print("P1", json.dumps(res["P1"]))
bf = ["advanceDeclineRatio", "percentAboveMA20", "marketBreadthStrength", "basketMomentum15M", "momentum15M", "momentum1M"]
bad = J[rel > 1e-3].copy()
bad["min_s"] = bad["min"].map(f7)
cols = ["min_s", "p15_out", "p15_off", "p15_rel"] + sum([[f + "_l", f + "_e"] for f in bf], [])
res["P1_bad_minutes"] = bad.sort_values("p15_rel", ascending=False)[cols].head(60).round(6).to_dict("records")
# phut lech theo gio-trong-phut / theo phut-trong-gio
bad["mm"] = ((bad["min"] // 60000) % 60)
res["P1_bad_by_minute_of_hour"] = bad["mm"].value_counts().sort_index().to_dict()
# feature nao lech o phut xau
fl = {}
for f in FEATS:
    a, b = bad[f + "_l"].astype(float), bad[f + "_e"].astype(float)
    fl[f] = float(((a - b).abs() > 1e-6 * (1 + b.abs())).mean()) if len(bad) else 0.0
res["P1_bad_feature_mismatch_frac"] = dict(sorted(fl.items(), key=lambda x: -x[1])[:12])
print("P1 bad by feature", res["P1_bad_feature_mismatch_frac"])
J[["min", "p15_out", "p15_off", "p15_rel", "rateDownAvg", "o_rateDownAvg", "rateUpAvg", "o_rateUpAvg",
   "rateDown15MAvg", "o_rateDown15MAvg"]].to_csv(W + "/out_minute_p15_rates.csv.gz", index=False)

# ---------------- (3) gate ----------------
S = pd.concat([d for d in (read_gz(p) for p in sorted(glob.glob(W + "/raw242/dumps/sel_dump_*.csv.gz"))) if d is not None],
              ignore_index=True)
S = S.drop_duplicates(["ts", "symbol"], keep="last")
S = S[S.ts >= T0].copy()
res["sel"] = dict(rows=int(len(S)), minutes=int(S.ts.nunique()), rows_per_min=S.groupby("ts").size().value_counts().to_dict())
# p15 sel_dump vs feat_dump (noi bo)
pm = S.groupby("ts").p15.first().rename("p15_sel").reset_index().rename(columns={"ts": "min"})
K = pm.merge(J[["min", "p15_out", "p15_off"]], on="min", how="left")
res["sel_vs_featdump_p15"] = stats(K.p15_sel, K.p15_out)
print("SEL p15 vs feat_dump", json.dumps(res["sel_vs_featdump_p15"]))
gv = S.gateValue.astype(np.float32).values
fac = np.maximum(DYN_MIN, (gv / SCORE_BASE) * DYN_MULT).astype(np.float32)
S["fac"] = fac
S["r_live"] = (S.p15.astype(np.float32).values / (fac * GS)).astype(np.float32)
S = S.merge(J[["min", "p15_off"]].rename(columns={"min": "ts"}), on="ts", how="left")
S["r_off"] = (S.p15_off.astype(np.float32).values / (fac * GS)).astype(np.float32)

# buffer + replay q
bts, br, nbad = grr_lib.load(W + "/raw242/gate_ratio_live.bin")
br32 = br.astype(np.float32)
res["buffer"] = dict(n=int(len(bts)), bad_chunks=int(nbad), first=f7(int(bts.min())), last=f7(int(bts.max())),
                     sorted=bool(np.all(np.diff(bts) >= 0)))
print("BUFFER", res["buffer"])
# r cua sel_dump co trong buffer? (cung ts, cung r float32)
bdf = pd.DataFrame({"ts": bts, "r": br32})
bwin = bdf[bdf.ts >= T0]
cnt_b = bwin.groupby("ts").size()
res["buffer_records_per_min_in_window"] = cnt_b.value_counts().head(8).to_dict()
key_b = set(zip(bwin.ts.values.tolist(), bwin.r.values.view(np.int32).tolist()))
S["in_buf"] = [(t, r) in key_b for t, r in zip(S.ts.values.tolist(), S.r_live.values.astype(np.float32).view(np.int32).tolist())]
res["sel_r_in_buffer_frac"] = float(S.in_buf.mean())
print("sel r in buffer exact frac", res["sel_r_in_buffer_frac"])
# restart (MainClass) tu log
lines = gzip.open(W + "/raw242/loglines.gz", "rt", errors="ignore").read().splitlines()
pat_t = re.compile(r"^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d+)")


def lt(s):
    m = pat_t.match(s)
    if not m:
        return None
    d, mo, y, hh, mi, ss, ms = m.groups()
    return int(dt.datetime(int(y), int(mo), int(d), int(hh), int(mi), int(ss), tzinfo=dt.timezone(dt.timedelta(hours=7))).timestamp() * 1000)


restarts = sorted(t for t in (lt(s) for s in lines if "MainClass:" in s) if t and t >= T0 - 2 * H)
res["restarts"] = [f7(t) for t in restarts]
gr = []
for s in lines:
    if "[GATE-RATIO] q_t=" in s:
        t = lt(s)
        m = re.search(r"q_t=([0-9.]+) buffer=(\d+) eval=(\d+) pass=(\d+)", s)
        if t and m and t >= T0:
            gr.append(dict(tlog=t, q_log=float(m.group(1)), buf=int(m.group(2)), ev=int(m.group(3)), ps=int(m.group(4))))
G = pd.DataFrame(gr)
G["h"] = (G.tlog // H) * H - H


def q_at(cut_hi, h):
    lo = h - 90 * 86400000
    i0 = np.searchsorted(bts, lo, "left"); i1 = np.searchsorted(bts, cut_hi, "left")
    a = br32[i0:i1]
    m = len(a)
    k = min(m - 1, max(0, int(np.floor(PCT * (m - 1)))))
    return float(np.partition(a, k)[k]), m


rows = []
hours = sorted(set((S.ts // H * H).tolist()))
for h in hours:
    rs = [t for t in restarts if h <= t < h + H]
    if rs:
        # sau restart: computeQ tai tick dau sau restart, buffer = moi record da flush truoc restart
        tr = rs[-1]
        cut = (tr // 60000) * 60000 - 60000   # record ts (nen) < nen cua tick dau sau restart
        q, m = q_at(cut + 1, h)
        mode = "restart"
    else:
        q, m = q_at(h, h)
        mode = "normal"
    rows.append(dict(h=h, q_rep=q, m_rep=m, mode=mode))
Q = pd.DataFrame(rows)
QG = Q.merge(G, on="h", how="left")
QG["q_rep6"] = QG.q_rep.round(6)
QG["abs_d"] = (QG.q_log - QG.q_rep).abs()
QG["rel_d"] = QG.abs_d / QG.q_rep
QG["match6"] = (QG.q_log - QG.q_rep6).abs() < 5e-13
lg = QG.dropna(subset=["q_log"])
res["P3"] = dict(n_hours=int(len(Q)), n_with_log=int(len(lg)), n_match_6dp=int(lg.match6.sum()),
                 max_rel=float(lg.rel_d.max()), med_rel=float(lg.rel_d.median()),
                 n_rel_gt_1e6=int((lg.rel_d > 1e-6).sum()),
                 note="log in %.6f => do phan giai tuong doi ~7e-5; tieu chi 1e-6 chi kiem duoc o muc khop 6 chu so",
                 q_first=float(Q.q_rep.iloc[0]), q_last=float(Q.q_rep.iloc[-1]),
                 mismatch=lg[~lg.match6][["h", "q_log", "q_rep", "m_rep", "buf", "mode"]].assign(h=lambda x: x.h.map(f7)).head(30).to_dict("records"))
print("P3", json.dumps({k: v for k, v in res["P3"].items() if k != "mismatch"}))
print("P3 mismatch", res["P3"]["mismatch"][:10])
# q dung cho tung phut: q_rep cua gio
S["h"] = S.ts // H * H
S = S.merge(Q[["h", "q_rep"]], on="h", how="left")
S["thr"] = (S.q_rep.astype(np.float32) * S.fac.astype(np.float32) * GS).astype(np.float32)
S["pass_live"] = ~(S.p15.astype(np.float32) < S.thr)
S["pass_off"] = ~(S.p15_off.astype(np.float32) < S.thr)
S["rq_live"] = S.r_live / S.q_rep
S["rq_off"] = S.r_off / S.q_rep
fl = S[S.pass_live != S.pass_off].copy()
ml = (fl.p15 - fl.thr).abs() / fl.thr
mo = (fl.p15_off - fl.thr).abs() / fl.thr
res["gate"] = dict(n_pairs=int(len(S)), n_pairs_no_off=int(S.p15_off.isna().sum()), n_pass_live=int(S.pass_live.sum()),
                   n_pass_off=int(S.pass_off.sum()), n_flip_pairs=int(len(fl)), n_flip_minutes=int(fl.ts.nunique()),
                   n_flip_heavy_either=int(((ml > .01) | (mo > .01)).sum()), n_flip_heavy_both=int(((ml > .01) & (mo > .01)).sum()),
                   max_rq_live=float(S.rq_live.max()), max_rq_off=float(S.rq_off.max()),
                   t_max_rq_live=f7(int(S.loc[S.rq_live.idxmax(), "ts"])), t_max_rq_off=f7(int(S.loc[S.rq_off.idxmax(), "ts"])),
                   rq_live_ge_09=int((S.rq_live >= .9).sum()), rq_off_ge_09=int((S.rq_off >= .9).sum()))
res["gate"]["r_stats"] = stats(S.r_live, S.r_off)
res["P2"] = dict(n_heavy=res["gate"]["n_flip_heavy_either"], PASS=res["gate"]["n_flip_heavy_either"] == 0)
print("GATE", json.dumps(res["gate"]))
# GATE log n_pass vs replay
gp = re.compile(r"\[GATE\] .*n_cand=(\d+) n_rej=(\d+) n_pass=(\d+) n_skipfull=(\d+) u=([0-9.]+)")
gl = []
for s in lines:
    if "[GATE] " in s and "n_pass=" in s:
        t = lt(s); m = gp.search(s)
        if t and m and t >= T0:
            gl.append(dict(t=t, n_cand=int(m.group(1)), n_pass=int(m.group(3)), n_skip=int(m.group(4)), u=float(m.group(5))))
GL = pd.DataFrame(gl)
res["gate_log"] = dict(n_lines=int(len(GL)), sum_pass=int(GL.n_pass.sum()), sum_skip=int(GL.n_skip.sum()),
                       u_max=float(GL.u.max()), n_cand_dist=GL.n_cand.value_counts().head(5).to_dict())
print("GATE log", res["gate_log"])
S.to_csv(W + "/out_sel_gate.csv.gz", index=False)
json.dump(res, open(W + "/par_a.json", "w"), indent=1, default=str)
print("JSON ->", W + "/par_a.json")
