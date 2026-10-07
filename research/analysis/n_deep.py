#!/usr/bin/env python3
"""N_DEEP (2026-10-08): dao sau "tang so lenh quanh K24" — frontier 3 seed + on dinh + giai phau lenh them.

CHI PHAN TICH output Kaggle co san (~/kaggle_sim/out): 0 sim, 0 Kaggle, 0 Java, 0 cham 242/shadow, 0 sua file claw.
Mo ta + chan doan, KHONG co luat GO; moi so la "chi bao cao". D3/D4 la in-sample (thien lech chon loc).
Thuoc = gkf_rescore.py (1f9e0e2f): MTM phut phi legacy as-is, cua so 2022+; stress COST_TRUTH post-hoc: chan vao nen 1m
quyet dinh (lag 0) co close/open-1 <= -1% => PnL - pen x notional, entry x (1+pen) cho MTM; 3 muc pen 0.90/1.675/2.67 %/chan.
Ghep lenh D3: (sym, phut vao UTC +-1), 1-1, uu tien khop dung phut. Ngay "trong" = nen khong co chan vao nao trong +-24h.
ROI/lenh = 100 x pnl / notional (notional = qty x entry = margin trong printDone); stress tru 100 x pen o chan sap.
Hang S1 (PREDICT): join bins deploy+moc21 nhu s1k24_driver.step0 (khop symbolPred); BIG_DOWN/DCA khong kiem duoc hang.
Usage: python3 research/analysis/n_deep.py [--workers 3] [--stage parity|all]
"""
import argparse
import itertools
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import gkf_rescore as G  # noqa: E402

R, N = G.R, G.N
log = logging.getLogger("n_deep")
D = "/home/ubuntu/claude_master/1008/ndeep"
JSON_OUT = REPO + "/docs/audit/N_DEEP_20261008.json"
MD_OUT = D + "/tables.md"
G.BAR_CACHE, G.MTM_CACHE = D + "/bar.json", D + "/mtm.json"
OLD_MTM = ["/home/ubuntu/claude_master/1007/gkfscore/mtm.json", "/home/ubuntu/claude_master/1007/k32c/mtm.json"]
ALIAS = {"gkf-nen": "gqsf-a1", "gkf2-l2k32-s7": "k32c-s7", "gkf2-l2k32-s21": "k32c-s21"}
JARS = {"20d412e8": "shadow2", "0944841c": "gqsf"}
SEEDS = ["S42", "S7", "S21"]
PRED = {"S42": None, "S7": "b737fb6d64d198c14654ea9c92510b36", "S21": "0b541d2259b31cf2794160e0aeafa3ff"}
NEN = {"S42": "gqsf-a1", "S7": "gqsf-s7", "S21": "gqsf-s21"}
# arm -> (K, pct, {seed: tag})
ARMS = {
    "NEN": (24, "0.999950829", NEN),
    "A_1k16": (16, "0.999922492", {"S42": "gkf-1k-k16", "S7": "gkf2-1k16-s7", "S21": "gkf2-1k16-s21"}),
    "B_1k24": (24, "0.999939977", {"S42": "gkf-1k-k24", "S7": "gkf2-1k24-s7", "S21": "gkf2-1k24-s21"}),
    "C_l2k16": (16, "0.999880000", {"S42": "gkf-l2-k16", "S7": "gkf2-l2k16-s7", "S21": "gkf2-l2k16-s21"}),
    "D_l2k32": (32, "0.999915000", {"S42": "gkf-l2-k32", "S7": "k32c-s7", "S21": "k32c-s21"}),
}
REFS = {
    "R_K16on": (16, "0.999950829", {"S42": "gqsf16-a1", "S7": "gqsf16-s7", "S21": "gqsf16-s21"}),
    "R_l2k24": (24, "0.999895000", {"S42": "gkf-l2-k24"}),
    "R_l2k24b": (24, "0.999870000", {"S42": "gkf-l2-k24b"}),
}
DUPS = {"k32c-s7": "gkf2-l2k32-s7", "k32c-s21": "gkf2-l2k32-s21"}   # md5 phai trung
MAIN = [a for a in ARMS if a != "NEN"]
PENS = {"#L": 0.0090, "#S": 0.01675, "#H": 0.0267}     # CI COST_TRUTH: 0.90 / 1.675 / 2.67 %/chan
W0 = pd.Timestamp("2021-12-31")
YEARS = [2022, 2023, 2024, 2025]
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"


def fm(x, nd=2, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = ("%+." if sign else "%.") + str(nd) + "f"
    return (s % x).replace(".", ",")


def all_runs():
    """[(arm, seed, tag, K, pct)] cho ARMS + REFS."""
    out = []
    for a, (K, pct, m) in list(ARMS.items()) + list(REFS.items()):
        for s, t in m.items():
            out.append((a, s, t, K, pct))
    return out


def parity():
    res = {}
    for a, s, t, K, pct in all_runs():
        rj, pr, txt = N.result_json(t), N.prof_run(t), G.logtxt(t)
        f32 = "%.8f" % float(np.float32(float(pct)))
        gl, vl, vb = G.gate_line(txt), G.vline(txt), G.vline(G.logtxt(NEN[s]))
        pm = rj.get("pred_md5_used")
        chk = dict(jar=str(rj.get("jar_sha256"))[:8] in JARS, ok=rj.get("ok") is True,
                   date_last=rj.get("date_last") == "20251230", mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk=pr.get("SELECTOR_RANK_TOPK") == str(K) and ("SELECTOR_RANK_TOPK=%d " % K) in txt,
                   pct=pr.get("SIM_GATE_ROLLING_PCT") == pct and ("BAT: mode=ratio pct=" + f32 + " ") in txt,
                   skipfull=pr.get("GATE_QUOTA_SKIP_WHEN_FULL") == "true" and "[GATE-QUOTA] SKIP_WHEN_FULL=ON" in txt,
                   b0ov=all(pr.get(k) == str(v) for k, v in N.B0OV.items() if k != "SIM_GATE_ROLLING_PCT"),
                   pred_vline=vl is not None and vl == vb,
                   pred_md5=(PRED[s] is None and pm in (None, "None")) or pm == PRED[s])
        res[t] = dict(arm=a, seed=s, ok=bool(all(chk.values())), checks=chk, md5=R.md5_of(t), n=rj.get("n_trades"),
                      eq=rj.get("equity_final"), jar=str(rj.get("jar_sha256"))[:8], pred=str(pm)[:8],
                      gate_pass=gl["pass_all"], skipFull=gl["skipFull"])
        log.info("PARITY %-9s %-4s %-15s %s md5=%s n=%s eq=%s jar=%s pred=%s pass=%s skipFull=%s fail=%s", a, s, t,
                 "PASS" if res[t]["ok"] else "*** VOID ***", res[t]["md5"][:8], res[t]["n"], res[t]["eq"],
                 res[t]["jar"], res[t]["pred"], gl["pass_all"], gl["skipFull"], [k for k, v in chk.items() if not v])
    for t, u in DUPS.items():
        m2 = R.md5_of(u)
        res["_dup_" + t] = dict(other=u, md5_other=m2, same=m2 == res[t]["md5"])
        log.info("DUP %s vs %s md5 %s", t, u, "TRUNG" if m2 == res[t]["md5"] else "*** LECH ***")
    return res


def stress(d, msk, pen):
    s = d.copy()
    s["pen"] = np.where(msk, pen * s["notional"].to_numpy(float), 0.0)
    s["pnl"] = s["pnl"] - s["pen"]
    s["entry"] = s["entry"] * np.where(msk, 1.0 + pen, 1.0)
    return s


def seed_cache(md5):
    """lay MTM da tinh o gkfscore/k32c khi md5 + khoa stress khop (khoa cung dinh dang gkf_rescore)."""
    raw = json.load(open(G.MTM_CACHE)) if os.path.exists(G.MTM_CACHE) else {}
    for p in OLD_MTM:
        if not os.path.exists(p):
            continue
        for k, v in json.load(open(p)).items():
            t, sfx = (k.split("#", 1) + [""])[:2]
            t = ALIAS.get(t, t)
            nk = t + ("#" + sfx if sfx else "")
            if nk not in raw and t in md5:
                raw[nk] = v
    return raw


def stab(e, eb=None):
    """D2 tu equity NGAY (b+unP luc Update 07:00 local) cua so 2022+: return ngay MTM."""
    e = e[e.index >= W0].astype(float)
    r = e.pct_change().dropna()
    mo = e.resample("ME").last()
    mo = pd.concat([e.iloc[:1], mo]).pct_change().dropna()
    dd = 100 * (e / e.cummax() - 1)
    out = dict(sd_d=float(100 * r.std()), mean_d=float(100 * r.mean()), sharpe=float(r.mean() / r.std() * np.sqrt(365)),
               worst_m=float(100 * mo.min()), pos_m=float(100 * (mo > 0).mean()), pos_d=float(100 * (r > 0).mean()),
               ulcer=float(np.sqrt((dd ** 2).mean())), worst_d=float(100 * r.min()), n_m=int(len(mo)))
    if eb is not None:
        rb = eb[eb.index >= W0].astype(float).pct_change().dropna()
        j = r.index.intersection(rb.index)
        out["corr_nen"] = float(np.corrcoef(r[j], rb[j])[0, 1])
    return out


def match(a, b):
    """1-1 theo (sym, phut vao UTC): luot 1 khop dung phut, luot 2 +-1 phut. Tra (ia_matched, ib_matched, pairs)."""
    am, bm = G.umin(a), G.umin(b)
    pool = {}
    for j, (s, m) in enumerate(zip(b["sym"], bm)):
        pool.setdefault((s, int(m)), []).append(j)
    ma, mb = np.full(len(a), -1), np.zeros(len(b), bool)
    for dm in (0, -1, 1):
        for i, (s, m) in enumerate(zip(a["sym"], am)):
            if ma[i] >= 0:
                continue
            lst = pool.get((s, int(m) + dm))
            if lst:
                j = lst.pop(0)
                ma[i], mb[j] = j, True
    return ma, mb


def near(ts, ref, h=24):
    """True neu co phan tu ref trong +-h gio quanh moi ts."""
    r = np.sort(ref.to_numpy())
    t = ts.to_numpy()
    lo = np.searchsorted(r, t - np.timedelta64(h, "h"), side="left")
    hi = np.searchsorted(r, t + np.timedelta64(h, "h"), side="right")
    return hi > lo


def legtype(lv):
    lv = lv.astype(str).str.strip()
    return np.where(lv == "PREDICT_SYMBOL_TRADE", "PRED", np.where(lv == "BIG_DOWN", "BIGD", "DCA"))


def rank_bands(legs, tags):
    """hang S1 luc vao cho chan PREDICT (0-based) -> dai 1-16 / 17-24 / 25-32; chan khac = NA."""
    import s1k24_driver as S
    symmap = pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv").set_index("symbol")["symId"]
    IDX = S.bins_index([S.DEPLOY, S.MOC21])
    out, jm = {}, {}
    for t in tags:
        d = legs[t]
        x = pd.DataFrame(dict(sym=d["sym"].to_numpy(), symbolPred=pd.to_numeric(d["symbolPred"], errors="coerce").to_numpy(),
                              ms=((d["ts"] - pd.Timedelta(hours=7)).astype("datetime64[ns]").astype("int64") // 10 ** 6).to_numpy()))
        x, j = S.join_rank(x, IDX, symmap)
        pr = legtype(d["level"]) == "PRED"
        rk = x["rank"].to_numpy()
        b = np.where(rk < 0, "NA", np.where(rk < 16, "1-16", np.where(rk < 24, "17-24", "25-32")))
        out[t] = np.where(pr, b, "NA")
        j.update(pred_match=float(x["sp_match"].to_numpy()[pr].mean()), pred_rank_max=int(rk[pr].max()),
                 pred_na=int((b[pr] == "NA").sum()))
        jm[t] = j
        log.info("RANK %-15s %s", t, j)
    del IDX
    return out, jm


def stats(g):
    n = len(g)
    if not n:
        return dict(n=0)
    return dict(n=int(n), pnl_b=float(g["pnl_b"].sum()), pnl_s=float(g["pnl_s"].sum()), roi_b=float(g["roi_b"].mean()),
                roi_s=float(g["roi_s"].mean()), win_b=float(100 * (g["pnl_b"] > 0).mean()),
                win_s=float(100 * (g["pnl_s"] > 0).mean()), crash=float(100 * g["crash"].mean()))


def frame(d, msk, bandv, other, pen):
    """bang chan (cua so entry 2022-25) voi thuoc tinh D3."""
    n = d["notional"].to_numpy(float)
    f = pd.DataFrame(dict(ts=d["ts"].to_numpy(), year=d["ts"].dt.year.to_numpy(), crash=msk, leg=legtype(d["level"]),
                          band=bandv, empty=~near(d["ts"], other["ts"]), pnl_b=d["pnl"].to_numpy(float)))
    f["pnl_s"] = f["pnl_b"] - pen * n * msk
    f["roi_b"] = 100 * f["pnl_b"] / n
    f["roi_s"] = f["roi_b"] - 100 * pen * msk
    return f


def anatomy(a, b, ma, mb, msk_a, msk_b, band_a, band_b, pen):
    fa = frame(a, msk_a, band_a, b, pen)
    fb = frame(b, msk_b, band_b, a, pen)
    fa["grp"] = np.where(ma >= 0, "CHUNG", "MOI")
    fb["grp"] = np.where(mb, "CHUNG", "MAT")
    lt_a, lt_b = legtype(a["level"]), legtype(b["level"])
    mism = int((lt_a[ma >= 0] != lt_b[ma[ma >= 0]]).sum())
    w = lambda f: f[(f["ts"] >= np.datetime64("2022-01-01")) & (f["ts"] < np.datetime64("2026-01-01"))]
    return w(fa), w(fb), mism


def breakdown(f):
    out = dict(all=stats(f))
    for dim in ("crash", "empty", "band", "leg", "year"):
        out[dim] = {str(k): stats(g) for k, g in f.groupby(dim)}
    out["crash_empty"] = {"%s|%s" % k: stats(g) for k, g in f.groupby(["crash", "empty"])}
    return out


DIMS = dict(crash=[True, False], empty=[True, False], band=["1-16", "17-24", "25-32", "NA"], leg=["PRED", "BIGD", "DCA"])


def subset_search(moi, mat):
    """beat_mat (thuoc chat hon, them sau khi thay ROI_S MOI > 0 gan nhu moi tap con): ROI_S tap con > ROI_S MAT cung seed
    o CA 3 seed va ROI_S gop > ROI_S MAT gop cung nam o >= 3/4 nam (MAT = lenh nen bi chen ra = chi phi co hoi).
    moi: {seed: frame MOI}. Moi bo loc (moi chieu 'any' hoac 1 gia tri; co dinh truoc khi do). Ben = ROI stress > 0
    o CA 3 seed (n >= 20/seed) va ROI stress gop 3 seed > 0 o >= 3/4 nam (nam n >= 10). strict = them >= 3/4 nam TUNG seed."""
    res, k = [], 0
    for combo in itertools.product(*[[None] + v for v in DIMS.values()]):
        if all(c is None for c in combo):
            continue
        k += 1
        sub = {}
        for s, f in moi.items():
            m = np.ones(len(f), bool)
            for dim, c in zip(DIMS, combo):
                if c is not None:
                    m &= (f[dim] == c).to_numpy()
            sub[s] = f[m]
        if min(len(g) for g in sub.values()) < 20:
            continue
        roi = {s: float(g["roi_s"].mean()) for s, g in sub.items()}
        allg = pd.concat(sub.values())
        yr = {int(y): float(g["roi_s"].mean()) for y, g in allg.groupby("year") if len(g) >= 10}
        ny = sum(yr.get(y, -1) > 0 for y in YEARS)
        strict = all(sum((g[g["year"] == y]["roi_s"].mean() > 0) if (g["year"] == y).sum() >= 5 else False
                         for y in YEARS) >= 3 for g in sub.values())
        mroi = {s: float(mat[s]["roi_s"].mean()) for s in sub}
        mall = pd.concat(mat.values())
        myr = {int(y): float(g["roi_s"].mean()) for y, g in mall.groupby("year")}
        nby = sum(yr.get(y, -99) > myr.get(y, 99) for y in YEARS)
        beat = bool(all(roi[s] > mroi[s] for s in sub) and nby >= 3)
        name = ",".join("%s=%s" % (dim, c) for dim, c in zip(DIMS, combo) if c is not None)
        res.append(dict(filter=name, n_per_year=float(np.mean([len(g) for g in sub.values()]) / 4.0),
                        roi_s=roi, roi_s_yr=yr, pos_years=int(ny), robust=bool(all(v > 0 for v in roi.values()) and ny >= 3),
                        strict=bool(strict), beat_mat=beat, mat_roi_s=mroi, mat_roi_s_yr=myr, beat_years=int(nby),
                        pnl_s=float(np.mean([g["pnl_s"].sum() for g in sub.values()])),
                        pnl_b=float(np.mean([g["pnl_b"].sum() for g in sub.values()])),
                        roi_b=float(np.mean([g["roi_b"].mean() for g in sub.values()]))))
    return res, k


def load_all(par, workers):
    tags = [t for _, _, t, _, _ in all_runs() if par[t]["ok"]]
    legs = {t: R.load_legs(t) for t in tags}
    daily = {t: R.load_daily(t) for t in tags}
    bar = G.load_bars(legs, workers)
    conv, msk = {}, {}
    for t in tags:
        conv[t] = G.match_conv(legs[t], bar)
        assert conv[t][0]["match"] >= conv[t][1]["match"], ("lag 0 khong thang", t, conv[t])
        m, br, hit = G.crash_mask(legs[t], bar, 0)
        assert not np.isnan(br).any(), ("thieu nen", t, int(np.isnan(br).sum()))
        msk[t] = m
        log.info("CRASH %-15s n=%d crash=%d (%.2f%%) match_lag0=%.4f", t, len(m), m.sum(), 100 * m.mean(),
                 conv[t][0]["rate"])
    del bar
    keys = []
    for a, s, t, _, _ in all_runs():
        if t not in legs:
            continue
        keys.append(t)
        for sfx, pen in PENS.items():
            if a in ARMS or sfx == "#S":
                legs[t + sfx] = stress(legs[t], msk[t], pen)
                daily[t + sfx] = G.stress_daily(daily[t], legs[t + sfx])
                keys.append(t + sfx)
    return tags, legs, daily, msk, conv, keys


def mtm_metrics(par, legs, daily, keys, workers):
    md5 = {t: par[t]["md5"] for t in par if not t.startswith("_")}
    pen_of = {"": None, "#L": PENS["#L"], "#S": PENS["#S"], "#H": PENS["#H"]}

    def km(k):
        t, _, sfx = k.partition("#")
        p = pen_of["#" + sfx if sfx else ""]
        return md5[t] + ("#S%.5f:lag0" % p if p is not None else "")
    raw = seed_cache(md5)
    miss = {k: legs[k] for k in keys if raw.get(k, {}).get("md5") != km(k)}
    log.info("MTM cache hit %d/%d; can tinh %d: %s", len(keys) - len(miss), len(keys), len(miss), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=workers, chunk=30)
        for k, v in new.items():
            v["md5"] = km(k)
            raw[k] = v
    raw = {k: v for k, v in raw.items() if k in keys}
    json.dump(raw, open(G.MTM_CACHE, "w"))
    return {k: G.metrics(k, k.split("#")[0], legs[k], daily[k], raw[k]["legacy"]) for k in keys}


def selfcheck(M):
    """tai tao so da cong bo: k32_confirm.json (nen 3 seed + D 3 seed) va AUDIT_GKF_PHASE1 (A/B/C seed 42)."""
    flds = ("cagr22", "calmar22", "dd_mtm22", "uw_mtm22", "n_per_year", "sum_pnl_2022_25")
    k32 = json.load(open(REPO + "/docs/result/k32_confirm.json"))["metrics"]
    au = json.load(open(REPO + "/docs/audit/AUDIT_GKF_PHASE1_20261007.json"))["metrics"]
    refs = [(k, k32[k]) for k in k32 if k in M]
    refs += [(k + sfx, au[k + sfx]) for k in ("gkf-1k-k16", "gkf-1k-k24", "gkf-l2-k16", "gkf-l2-k24", "gkf-l2-k24b")
             for sfx in ("", "#S") if k + sfx in au and k + sfx in M]
    bad = [(k, f, M[k][f], r[f]) for k, r in refs for f in flds
           if f in r and abs(M[k][f] - r[f]) > 1e-6 * max(1.0, abs(r[f]))]
    log.info("TU KIEM: %d khoa x %d truong, lech %d %s", len(refs), len(flds), len(bad), bad[:6])
    assert not bad, "TU KIEM LECH -> DUNG"
    return dict(n_keys=len(refs), keys=[k for k, _ in refs], bad=bad)


def msd(v):
    v = [x for x in v if x is not None and np.isfinite(x)]
    if not v:
        return dict(mean=None, sd=None, npos=0, n=0)
    return dict(mean=float(np.mean(v)), sd=float(np.std(v, ddof=1)) if len(v) > 1 else 0.0,
                npos=int(sum(x > 0 for x in v)), n=len(v), vals=[float(x) for x in v])


def d1_d2(M, daily, tagmap):
    """tagmap: {arm: {seed: tag}} (chi run hop le). Tra rows (arm, seed, sfx) + delta vs NEN."""
    rows, delta = {}, {}
    for a, m in tagmap.items():
        for s, t in m.items():
            for sfx in ("", "#L", "#S", "#H"):
                k = t + sfx
                if k not in M:
                    continue
                x = M[k]
                kb = NEN[s] + sfx
                st = stab(daily[k]["equity"], daily[kb]["equity"] if kb in daily and a != "NEN" else None)
                ddb = M[kb]["dd_mtm22"] if kb in M else None
                st["iso_cagr22"] = x["cagr22"] * abs(ddb) / abs(x["dd_mtm22"]) if ddb else None
                st["cagr_ulcer"] = x["cagr22"] / st["ulcer"]
                rows["%s|%s|%s" % (a, s, sfx or "b")] = dict(
                    tag=t, n_per_year=x["n_per_year"], cagr22=x["cagr22"], dd22=x["dd_mtm22"], cal22=x["calmar22"],
                    uw22=x["uw_mtm22"], pnl2225=x["sum_pnl_2022_25"], yret=x["yret"], top10=x["top10_share"], **st)
    keys = ("n_per_year", "cagr22", "dd22", "cal22", "uw22", "pnl2225", "sd_d", "sharpe", "worst_m", "pos_m", "pos_d",
            "ulcer", "top10", "iso_cagr22", "cagr_ulcer")
    for a in tagmap:
        if a == "NEN":
            continue
        for sfx in ("b", "#L", "#S", "#H"):
            pr = [(rows.get("%s|%s|%s" % (a, s, sfx)), rows.get("NEN|%s|%s" % (s, sfx))) for s in SEEDS]
            pr = [(x, y) for x, y in pr if x and y]
            if not pr:
                continue
            dl = {f: msd([x[f] - y[f] for x, y in pr if x[f] is not None and y[f] is not None]) for f in keys}
            dl["cal_ratio"] = msd([x["cal22"] / y["cal22"] for x, y in pr])
            dl["yret"] = {yy: msd([x["yret"][yy] - y["yret"][yy] for x, y in pr]) for yy in YEARS}
            dl["corr_nen"] = msd([x.get("corr_nen") for x, _ in pr])
            dl["seeds"] = [x["tag"] for x, _ in pr]
            delta["%s|%s" % (a, sfx)] = dl
    return rows, delta


def mech_est(tot_a, tot_b, moi, mat, drop_mask):
    """uoc luong khi BO cac chan MOI drop_mask. lo = MAT van mat het (chi tru chan bo);
    mid = lo + n_bo x chi phi chen/ chan MOI (= ΣPnL_S MAT / n MOI cung seed, gia dinh ti le);
    hi = khong chen gi ca (nen + chan MOI giu lai). Tat ca in-sample, khong mo phong lai duong di."""
    drop = moi[drop_mask]
    keep = moi[~drop_mask]
    cost_s = float(mat["pnl_s"].sum()) / max(1, len(moi))
    cost_b = float(mat["pnl_b"].sum()) / max(1, len(moi))
    lo_s = tot_a["pnl_s"] - drop["pnl_s"].sum() - tot_b["pnl_s"]
    lo_b = tot_a["pnl_b"] - drop["pnl_b"].sum() - tot_b["pnl_b"]
    return dict(n_per_year=(tot_a["n"] - len(drop)) / 4.0, n_drop=int(len(drop)), dpnl_s=float(lo_s), dpnl_b=float(lo_b),
                dpnl_s_mid=float(lo_s + len(drop) * cost_s), dpnl_b_mid=float(lo_b + len(drop) * cost_b),
                dpnl_s_hi=float(keep["pnl_s"].sum()), n_per_year_hi=(tot_b["n"] + len(keep)) / 4.0, cost_s=cost_s)


MECH = {  # co dinh truoc khi do: bo chan MOI thoa dieu kien "drop"
    "M1_moi_khong_sap": lambda f: f["crash"],
    "M2_moi_chi_ngay_trong": lambda f: ~f["empty"],
    "M3_moi_trong_va_khong_sap": lambda f: f["crash"] | ~f["empty"],
}


def d3_d4(legs, msk, bands, tagmap):
    pen = PENS["#S"]
    out, moi_all, mat_all = {}, {}, {}
    for a in MAIN:
        moi_all[a] = {}
        for s, t in tagmap.get(a, {}).items():
            b = NEN[s]
            if b not in legs:
                continue
            ma, mb = match(legs[t], legs[b])
            fa, fb, mism = anatomy(legs[t], legs[b], ma, mb, msk[t], msk[b], bands[t], bands[b], pen)
            moi, mat, chung = fa[fa.grp == "MOI"], fb[fb.grp == "MAT"], fa[fa.grp == "CHUNG"]
            moi_all[a][s], mat_all.setdefault(a, {})[s] = moi, mat
            tot_a, tot_b = stats(fa), stats(fb)
            mech = {nm: mech_est(tot_a, tot_b, moi, mat, fn(moi).to_numpy()) for nm, fn in MECH.items()}
            out["%s|%s" % (a, s)] = dict(
                arm=t, nen=b, n_arm=int(len(legs[t])), n_nen=int(len(legs[b])), match_leg_mismatch=mism,
                exact_share=None, tot_arm=tot_a, tot_nen=tot_b, CHUNG=stats(chung), MOI=breakdown(moi),
                MAT=breakdown(mat), dpnl_s_raw=tot_a["pnl_s"] - tot_b["pnl_s"], dpnl_b_raw=tot_a["pnl_b"] - tot_b["pnl_b"],
                mech=mech)
            log.info("D3 %-8s %-4s CHUNG %d MOI %d (pnl_s %+.0f roi_s %+.2f) MAT %d (pnl_s %+.0f roi_s %+.2f) mism %d",
                     a, s, len(chung), len(moi), moi["pnl_s"].sum(), moi["roi_s"].mean(), len(mat), mat["pnl_s"].sum(),
                     mat["roi_s"].mean(), mism)
    ss = {}
    for a in MAIN:
        if len(moi_all[a]) == 3:
            res, k = subset_search(moi_all[a], mat_all[a])
            ss[a] = dict(k_filters=k, robust=sorted([r for r in res if r["robust"]], key=lambda r: -r["n_per_year"]),
                         beat=sorted([r for r in res if r["beat_mat"]], key=lambda r: -r["n_per_year"]), n_eval=len(res))
            log.info("SUBSET %s vuot MAT: %s", a, [(r["filter"], round(r["n_per_year"])) for r in ss[a]["beat"]][:8])
            log.info("SUBSET %s k=%d danh gia %d robust %d strict %d", a, k, len(res), len(ss[a]["robust"]),
                     sum(r["strict"] for r in ss[a]["robust"]))
    return out, ss, moi_all, mat_all


def mech4(out, moi_all, mat_all, ss):
    """M4 = chi giu tap con MOI 'vuot MAT' (neu khong co: 'ben') co n/nam lon nhat (chon SAU khi nhin => in-sample thuan)."""
    for a, v in ss.items():
        lst = v["beat"] or v["robust"]
        if not lst:
            continue
        flt = lst[0]["filter"]
        cond = [c.split("=", 1) for c in flt.split(",")]
        for s, moi in moi_all[a].items():
            keep = np.ones(len(moi), bool)
            for dim, val in cond:
                keep &= (moi[dim].astype(str) == val).to_numpy()
            o = out["%s|%s" % (a, s)]
            o["mech"]["M4_chi_giu[" + flt + "]"] = mech_est(o["tot_arm"], o["tot_nen"], moi, mat_all[a][s], ~keep)


def ms(d, nd=2, sign=True):
    if not d or d.get("mean") is None:
        return "—"
    return "%s±%s (%d/%d)" % (fm(d["mean"], nd, sign), fm(d["sd"], nd), d["npos"], d["n"])


def cell(lst, nd=2):
    """per-seed stats -> 'n/nam · ΣPnL_s k · ROI_b → ROI_s [min..max ROI_s] · win_s'."""
    lst = [x for x in lst if x and x.get("n")]
    if not lst:
        return "—"
    rs = [x["roi_s"] for x in lst]
    return "%s · %s · %s→%s [%s..%s] · %s" % (
        fm(np.mean([x["n"] for x in lst]) / 4.0, 0), fm(np.mean([x["pnl_s"] for x in lst]) / 1000, 1),
        fm(np.mean([x["roi_b"] for x in lst]), nd), fm(np.mean(rs), nd), fm(min(rs), nd), fm(max(rs), nd),
        fm(np.mean([x["win_s"] for x in lst]), 0))


def tables(par, rows, delta, d3, ss, tagmap):
    L = ["### T1. Parity", "| arm | seed | run | md5 | n | eq | jar | pred | gate pass | skipFull | parity |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a, s, t, _, _ in all_runs():
        p = par[t]
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            a, s, t, p["md5"][:8], p["n"], p["eq"], p["jar"], p["pred"], p["gate_pass"], p["skipFull"],
            "PASS" if p["ok"] else "VOID " + ",".join(k for k, v in p["checks"].items() if not v)))
    L += ["", "### T2. Từng run (MTM phút, cửa sổ 2022+; b = base, S = stress 1,675; L/H = 0,90/2,67)",
          "| arm | seed | n/năm | CAGR22 b→S | maxDD22 b→S | Calmar22 b→S | Cal22 L/H | UW22 b→S | ΣPnL22–25 k b→S |",
          "|---|---|---|---|---|---|---|---|---|"]
    for a, m in tagmap.items():
        for s in m:
            b, S_, Lo, Hi = (rows.get("%s|%s|%s" % (a, s, x)) for x in ("b", "#S", "#L", "#H"))
            if not b:
                continue
            L.append("| %s | %s | %s | %s→%s | %s→%s | %s→%s | %s/%s | %s→%s | %s→%s |" % (
                a, s, fm(b["n_per_year"], 0), fm(b["cagr22"]), fm(S_["cagr22"]), fm(b["dd22"]), fm(S_["dd22"]),
                fm(b["cal22"], 3), fm(S_["cal22"], 3), fm(Lo["cal22"], 3) if Lo else "—", fm(Hi["cal22"], 3) if Hi else "—",
                fm(b["uw22"], 0), fm(S_["uw22"], 0), fm(b["pnl2225"] / 1000, 1), fm(S_["pnl2225"] / 1000, 1)))
    return L



def tables2(rows, delta):
    L = ["", "### T3. Δ ghép cặp theo seed vs NỀN: mean±sd (số seed Δ>0 / số seed)",
         "| arm | phí | Δn/năm | ΔCAGR22 | ΔmaxDD22 | Cal×nền | ΔUW22 | ΔΣPnL22–25 k | ΔROI 2022 / 2023 / 2024 / 2025 |",
         "|---|---|---|---|---|---|---|---|---|"]
    for k, d in delta.items():
        a, sfx = k.split("|")
        pk = dict(d["pnl2225"])
        pk.update({x: (v / 1000 if v is not None else None) for x, v in pk.items() if x in ("mean", "sd")})
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            a, {"b": "base", "#L": "0,90", "#S": "1,675", "#H": "2,67"}[sfx], ms(d["n_per_year"], 0), ms(d["cagr22"]),
            ms(d["dd22"]), ms(d["cal_ratio"], 3, False), ms(d["uw22"], 0), ms(pk, 1),
            " / ".join(ms(d["yret"][y], 1) for y in YEARS)))
    L += ["", "### T4. D2 ổn định (mean 3 seed; return NGÀY MTM = equity b+unP 07:00, cửa sổ 2022+)",
          "| arm | phí | sd ngày % | Sharpe ngày×√365 | tháng tệ % | tháng+ % | ngày+ % | Ulcer | UW22 | maxDD22 | top10 ngày % | corr nền | iso-risk CAGR22 | CAGR/Ulcer |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    arms = []
    for k in rows:
        a = k.split("|")[0]
        if a not in arms:
            arms.append(a)
    for a in arms:
        for sfx in ("b", "#S"):
            rr = [rows[k] for k in rows if k.split("|")[0] == a and k.split("|")[2] == sfx]
            if not rr:
                continue
            mv = lambda f, nd=2: fm(np.mean([x[f] for x in rr if x.get(f) is not None]), nd) if any(
                x.get(f) is not None for x in rr) else "—"
            L.append("| %s (%d seed) | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                a, len(rr), "base" if sfx == "b" else "1,675", mv("sd_d", 3), mv("sharpe"), mv("worst_m"), mv("pos_m", 1),
                mv("pos_d", 1), mv("ulcer"), mv("uw22", 0), mv("dd22"), mv("top10", 1), mv("corr_nen", 3),
                mv("iso_cagr22"), mv("cagr_ulcer")))
    L += ["", "Δ vs NỀN theo seed (mean±sd, số seed Δ>0): iso-risk CAGR22 / Sharpe / Ulcer / CAGR÷Ulcer / tháng tệ",
          "| arm | phí | Δiso-risk CAGR22 | ΔSharpe | ΔUlcer | ΔCAGR÷Ulcer | Δtháng tệ | Δsd ngày |", "|---|---|---|---|---|---|---|---|"]
    for k, d in delta.items():
        a, sfx = k.split("|")
        if sfx in ("b", "#S"):
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                a, "base" if sfx == "b" else "1,675", ms(d["iso_cagr22"]), ms(d["sharpe"], 3), ms(d["ulcer"]),
                ms(d["cagr_ulcer"], 3), ms(d["worst_m"]), ms(d["sd_d"], 3)))
    return L



def tables3(d3, ss):
    L = ["", "### T5. D3 giải phẫu (entry 2022–25, stress 1,675). Ô = n/năm · ΣPnL_S k · ROI_b→ROI_S % [min..max ROI_S 3 seed] · win_S %",
         "| arm | nhóm | tất cả | nến sập | không sập | ngày trống | ngày có nền | sập∧trống | không sập∧trống |",
         "|---|---|---|---|---|---|---|---|---|"]
    for a in MAIN:
        per = [d3[k] for k in d3 if k.startswith(a + "|")]
        if not per:
            continue
        L.append("| %s | CHUNG | %s | | | | | | |" % (a, cell([p["CHUNG"] for p in per])))
        for g in ("MOI", "MAT"):
            c = lambda dim, key: cell([p[g][dim].get(key) for p in per])
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                a, g, cell([p[g]["all"] for p in per]), c("crash", "True"), c("crash", "False"), c("empty", "True"),
                c("empty", "False"), c("crash_empty", "True|True"), c("crash_empty", "False|True")))
    L += ["", "MẤT: 'ngày trống' = ARM không có chân vào trong ±24h quanh lệnh nền bị mất.", "",
          "### T6. D3 MỚI theo hạng S1 / leg / năm (cùng định dạng ô)",
          "| arm | 1–16 | 17–24 | 25–32 | PRED | BIG_DOWN | DCA | 2022 | 2023 | 2024 | 2025 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in MAIN:
        per = [d3[k] for k in d3 if k.startswith(a + "|")]
        if not per:
            continue
        c = lambda dim, key: cell([p["MOI"][dim].get(key) for p in per])
        L.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            a, c("band", "1-16"), c("band", "17-24"), c("band", "25-32"), c("leg", "PRED"), c("leg", "BIGD"),
            c("leg", "DCA"), c("year", "2022"), c("year", "2023"), c("year", "2024"), c("year", "2025")))
    L += ["", "### T7. Tập con MỚI 'bền' (ROI_S>0 cả 3 seed, n≥20/seed; ROI_S gộp >0 ở ≥3/4 năm) — top 6 theo n/năm",
          "| arm | k bộ lọc | bộ lọc | n/năm | ΣPnL_S k (mean seed) | ROI_b | ROI_S 3 seed | ROI_S 22/23/24/25 | strict |",
          "|---|---|---|---|---|---|---|---|---|"]
    for a, v in ss.items():
        L.append("| %s | %d | → số tập 'bền' %d / đánh giá %d (n≥20/seed); 'vượt MẤT' %d | | | | | | |" % (
            a, v["k_filters"], len(v["robust"]), v["n_eval"], len(v["beat"])))
        for r in v["robust"][:4]:
            L.append("| %s | %d | %s | %s | %s | %s | %s | %s | %s |" % (
                a, v["k_filters"], r["filter"], fm(r["n_per_year"], 0), fm(r["pnl_s"] / 1000, 1), fm(r["roi_b"]),
                "/".join(fm(x) for x in r["roi_s"].values()), "/".join(fm(r["roi_s_yr"].get(y)) for y in YEARS),
                "✓" if r["strict"] else "✗"))
    L += ["", "### T7b. Tập con MỚI 'vượt MẤT' (ROI_S > ROI_S MẤT cùng seed ở cả 3 seed; ROI_S gộp > MẤT gộp ở ≥3/4 năm) — top 8 theo n/năm",
          "| arm | bộ lọc | n/năm | ΣPnL_S k | ROI_S 3 seed | ROI_S MẤT 3 seed | ROI_S 22/23/24/25 | MẤT 22/23/24/25 |", "|---|---|---|---|---|---|---|---|"]
    for a, v in ss.items():
        if not v["beat"]:
            L.append("| %s | (không có) | | | | | | |" % a)
        for r in v["beat"][:8]:
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                a, r["filter"], fm(r["n_per_year"], 0), fm(r["pnl_s"] / 1000, 1), "/".join(fm(x) for x in r["roi_s"].values()),
                "/".join(fm(x) for x in r["mat_roi_s"].values()), "/".join(fm(r["roi_s_yr"].get(y)) for y in YEARS),
                "/".join(fm(r["mat_roi_s_yr"].get(y)) for y in YEARS)))
    L += ["", "### T8. D4 ước lượng cơ chế (in-sample, cộng/trừ chân MỚI, giữ nguyên đường đi; ΔPnL vs NỀN cùng seed, entry 22–25)",
          "lo = MẤT vẫn mất hết; mid = lo + n_bỏ × (ΣPnL_S MẤT / n MỚI) (giả định tỉ lệ chèn); hi = NỀN + chân MỚI giữ lại, không chèn.",
          "| arm | cơ chế | n/năm (lo) | n/năm (hi) | ΔPnL_S k lo mean±sd (seed>0) | mid | hi | ΔPnL_b k lo / mid | n bỏ/năm |",
          "|---|---|---|---|---|---|---|---|---|"]
    for a in MAIN:
        per = [d3[k] for k in d3 if k.startswith(a + "|")]
        if not per:
            continue
        L.append("| %s | (arm thô) | %s | | %s | | | %s | 0 |" % (a, fm(np.mean([p["tot_arm"]["n"] for p in per]) / 4, 0),
                 ms(msd([p["dpnl_s_raw"] / 1000 for p in per]), 1), fm(np.mean([p["dpnl_b_raw"] for p in per]) / 1000, 1)))
        for nm in per[0]["mech"]:
            mm = [p["mech"][nm] for p in per if nm in p["mech"]]
            L.append("| %s | %s | %s | %s | %s | %s | %s | %s / %s | %s |" % (
                a, nm, fm(np.mean([x["n_per_year"] for x in mm]), 0), fm(np.mean([x["n_per_year_hi"] for x in mm]), 0),
                ms(msd([x["dpnl_s"] / 1000 for x in mm]), 1), ms(msd([x["dpnl_s_mid"] / 1000 for x in mm]), 1),
                ms(msd([x["dpnl_s_hi"] / 1000 for x in mm]), 1), fm(np.mean([x["dpnl_b"] for x in mm]) / 1000, 1),
                fm(np.mean([x["dpnl_b_mid"] for x in mm]) / 1000, 1), fm(np.mean([x["n_drop"] for x in mm]) / 4, 0)))
    return L



def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--stage", default="all", choices=["parity", "all"])
    a = ap.parse_args()
    os.makedirs(D, exist_ok=True)
    par = parity()
    void = [t for t in par if not t.startswith("_") and not par[t]["ok"]]
    log.info("VOID: %s", void)
    assert all(v["same"] for k, v in par.items() if k.startswith("_dup_")), "DUP md5 lech"
    assert all(par[t]["ok"] for t in NEN.values()), "NEN VOID -> DUNG"
    if a.stage == "parity":
        return
    tags, legs, daily, msk, conv, keys = load_all(par, a.workers)
    M = mtm_metrics(par, legs, daily, keys, a.workers)
    sc = selfcheck(M)
    tagmap = {arm: {s: t for s, t in m.items() if t in tags} for arm, (_, _, m) in list(ARMS.items()) + list(REFS.items())}
    rows, delta = d1_d2(M, daily, tagmap)
    main_tags = [t for arm in ARMS for t in tagmap[arm].values()]
    bands, rj = rank_bands(legs, main_tags)
    d3, ss, moi_all, mat_all = d3_d4(legs, msk, bands, tagmap)
    mech4(d3, moi_all, mat_all, ss)
    js = dict(title="N_DEEP_20261008", script="research/analysis/n_deep.py", ruler="gkf_rescore.py (1f9e0e2f)",
              note="mo ta + chan doan, khong luat GO; D3/D4 in-sample", pens=PENS, parity=par, void=void,
              crash_lag_conv=conv, selfcheck=sc, rank_join=rj, rows=rows, delta=delta, d3=d3, subsets=ss,
              crash_share={t: float(msk[t].mean()) for t in tags})
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=G.jd)
    L = tables(par, rows, delta, d3, ss, tagmap) + tables2(rows, delta) + tables3(d3, ss)
    with open(MD_OUT, "w") as fo:
        fo.write("\n".join(L) + "\n")
    log.info("OUT %s %s", JSON_OUT, MD_OUT)


if __name__ == "__main__":
    main()
