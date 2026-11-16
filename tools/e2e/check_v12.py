#!/usr/bin/env python3
"""E2E_REPLAY_V12 - BO CHAM (prereg PREREG_E2E_REPLAY_V12 §5, §6). Doc output replay (<runs>/<LUOT>/...) + REF
(<ref>/<LUOT>/ref_*.csv, do ref_v12.py sinh DOC LAP) + fixture. In PASS / FAIL / KHONG XAY RA / KHONG DU MAU / CHUA AP DUNG
cho C1, E1, S1, D1, X1, F1, K1, E2 + bang §6. "KHONG XAY RA" / "KHONG DU MAU" KHONG tinh la PASS.

argv: --runs DIR --ref DIR --fx DIR --env FILE [--out FILE] [--dry-1105 CSV --labels-1105 CSV]
"""
import argparse
import collections
import csv
import json
import os
import re
import sys
from decimal import Decimal, ROUND_FLOOR

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_v12 as R  # noqa: E402  (chi dung ham DAC TA budget/load_env/load_exinfo, khong goi Java)

PASS, FAIL, NA, NS, NAPPLY = "PASS", "FAIL", "KHONG XAY RA", "KHONG DU MAU", "CHUA AP DUNG"
FLAG_ON_LANES = ["R0", "R0-DRY", "S-DCA", "FIN-INJ", "R-1000", "R-4000"]
T1105 = 1794268800000   # 2026-11-05 07:00 +07


def rd(path):
    if not os.path.isfile(path):
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh))


def lane(runs, n):
    d = os.path.join(runs, n)
    res = json.load(open(d + "/result.json")) if os.path.isfile(d + "/result.json") else None
    log = open(d + "/run.log", errors="replace").read() if os.path.isfile(d + "/run.log") else ""
    return dict(dir=d, res=res, log=log, legs=rd(d + "/legs.csv"), fills=rd(d + "/fills.csv"), events=rd(d + "/events.csv"),
                outcomes=rd(d + "/outcomes.csv"))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ C1
BANNERS = {"LIVE-SIZING": r"\[LIVE-SIZING\] LIVE_APPLY_GRID_RATIO=true", "LIVE-DCA-GRID": r"\[LIVE-DCA-GRID\] LIVE_DCA_GRID_ENABLED=true .*applyRatio=true",
           "MINUTE-FIN": r"\[MINUTE-FIN\] BAT", "GATE-RATIO": r"\[GATE-RATIO\] LIVE BAT"}


def c1(L):
    if L["res"] is None:
        return FAIL, {"loi": "khong co result.json (refused/crash)"}
    jc, ec = L["res"].get("jar_check", {}), L["res"].get("env_check", {})
    nres = sum(1 for v in jc.get("class_resources", {}).values() if v.startswith("jar:file:" + jc.get("jar_path", "?")))
    ban = {k: bool(re.search(p, L["log"])) for k, p in BANNERS.items()}
    det = {"jar_md5": jc.get("jar_md5"), "jar_ok": jc.get("ok"), "classes_from_jar": nres, "banners": ban,
           "missing_names": ec.get("missing_names_not_overridden"), "differ": ec.get("differ_not_overridden"),
           "overrides": ec.get("overrides_declared")}
    ok = (jc.get("ok") is True and jc.get("jar_md5") == "641803565297d4065d90245e04a00f11" and nres == 10 and all(ban.values())
          and not ec.get("missing_names_not_overridden") and not ec.get("differ_not_overridden"))
    return (PASS if ok else FAIL), det


# ------------------------------------------------------------------ E1
def e1(L, refdir):
    rep = [(int(x["decision_ts"]), x["symbol"]) for x in L["legs"] if x["level"] == "PREDICT_SYMBOL_TRADE"]
    ref = [(int(x["decision_ts"]), x["symbol"]) for x in rd(refdir + "/ref_legs.csv")
           if x["level"] == "PREDICT_SYMBOL_TRADE" and x["outcome"] != "FIN_EXCL"]
    det = {"n_replay": len(rep), "n_ref": len(ref)}
    if rep != ref:
        sr, sf = set(rep), set(ref)
        det["only_replay"] = sorted(sr - sf)[:20]
        det["only_ref"] = sorted(sf - sr)[:20]
        first = next((i for i, (a, b) in enumerate(zip(rep, ref)) if a != b), min(len(rep), len(ref)))
        det["first_diff_idx"] = first
        return FAIL, det
    if len(rep) < 20:
        return NS, det
    return PASS, det


# ------------------------------------------------------------------ S1
def p_for(env, cap, flags):
    return R.params(env, cap, flags)


def qty_ok(b, px, step, qty):
    want = (Decimal(repr(b)) / Decimal(repr(px))).to_integral_value(rounding=ROUND_FLOOR) if step <= 0 else \
        ((Decimal(repr(b)) / Decimal(repr(px))) / step).to_integral_value(rounding=ROUND_FLOOR) * step
    return want == Decimal(qty), str(want)


def s1(L, env, meta, flags="on"):
    bad, n, worst = [], 0, 0.0
    first3 = []
    for x in L["legs"]:
        if x["outcome"] != "SUBMITTED":
            continue
        n += 1
        cap, used, b = float(x["capital"]), float(x["margin_before"]), float(x["budget"])
        li = int(x["leg_idx"]) if x["leg_idx"] not in ("", None) else 0
        P = p_for(env, cap, flags)
        bref = R.budget(P, used, li)
        rel = abs(b - float(bref)) / b if bref is not None else 1.0
        worst = max(worst, rel)
        m = meta.get(x["symbol"])
        qok, want = qty_ok(b, float(x["sizing_px"]), m["step"] if m else Decimal(0), x["qty"])
        if rel > 1e-5 or not qok:
            bad.append({"leg": x["cid"], "b": b, "b_ref": float(bref) if bref is not None else None, "rel": rel, "qty": x["qty"],
                        "qty_ref": want})
        if len(first3) < 3:
            first3.append((b, used))
    hv = R.hand_values()
    hv_ok = all(abs(a - e) <= 0.005 * e for a, e in zip(hv, [225.00, 216.56, 208.44]))
    det = {"n_submit": n, "worst_rel": worst, "bad": bad[:20], "n_bad": len(bad), "hand_values_ref": hv, "hand_ok": hv_ok,
           "first3_replay(b,used)": first3}
    if n == 0:
        return NA, det
    return (PASS if not bad and hv_ok else FAIL), det


# ------------------------------------------------------------------ cum (replay) tu fills + events
def clusters_replay(L, meta):
    cid2dec = {x["cid"]: int(x["decision_ts"]) for x in L["legs"] if x["cid"]}
    ts_ev = collections.defaultdict(list)
    for e in L["events"]:
        if e["type"] == "TRAIL_TIME_STOP":
            ts_ev[e["symbol"]].append(int(e["ms"]))
    pos, cur, out = collections.defaultdict(float), {}, []
    for f in L["fills"]:
        s, q, px, ms = f["symbol"], float(f["qty"]), float(f["price"]), int(f["ms"])
        if f["side"] == "BUY":
            if s not in cur:
                cur[s] = dict(symbol=s, b0=cid2dec.get(f["cid"]), first_ms=ms, buys=[], sells=[], legs=0)
            cur[s]["buys"].append((q, px))
            cur[s]["legs"] += 1
            pos[s] += q
        else:
            c = cur.get(s)
            if c is None:
                continue
            c["sells"].append((q, px, ms, f["cid"]))
            pos[s] -= q
            if pos[s] <= 1e-12:
                pos[s] = 0.0
                sq = sum(z[0] for z in c["sells"])
                c["exit_px"] = sum(z[0] * z[1] for z in c["sells"]) / sq
                c["exit_ms"] = c["sells"][-1][2]
                tstop = any(c["first_ms"] <= t <= c["exit_ms"] for t in ts_ev.get(s, []))
                c["reason"] = "TIME_STOP" if tstop else ("TRAIL" if c["sells"][-1][3].startswith("c3s-") else
                                                         "OTHER:" + c["sells"][-1][3].split("-")[0])
                c["vwap"] = sum(z[0] * z[1] for z in c["buys"]) / sum(z[0] for z in c["buys"])
                out.append(c)
                del cur[s]
    return out, list(cur.values())


def x1(L, refdir, meta):
    rep, rep_open = clusters_replay(L, meta)
    ref = {(x["symbol"], int(x["b0"])): x for x in rd(refdir + "/ref_clusters.csv")}
    rows, dl, mism = [], [], []
    same_min = pm1 = 0
    for c in rep:
        k = (c["symbol"], c["b0"])
        f = ref.get(k)
        if f is None or f["reason"] == "OPEN":
            mism.append({"cum": k, "replay": c["reason"], "ref": None if f is None else "OPEN"})
            continue
        em = c["exit_ms"] // 60000 * 60000
        dm = (em - int(f["exit_bar"])) // 60000
        same_min += dm == 0
        pm1 += abs(dm) == 1
        d = (c["exit_px"] - float(f["exit_px"])) / float(f["exit_px"])
        dl.append(d)
        tick = float(meta[c["symbol"]]["tick"]) if c["symbol"] in meta else 0.0
        rr = "TRAIL" if f["reason"].startswith("TRAIL") else f["reason"]
        rows.append({"cum": k, "legs": c["legs"], "reason": (c["reason"], rr), "dmin": dm, "dpx": d,
                     "px_ok": d >= -0.015 or abs(c["exit_px"] - float(f["exit_px"])) <= 2 * tick + 1e-12})
    ref_exited_not_rep = [k for k, f in ref.items() if f["reason"] != "OPEN" and not any((c["symbol"], c["b0"]) == k for c in rep)]
    n = len(rows)
    one = [r for r in rows if r["legs"] == 1]
    reason_ok = all(r["reason"][0] == r["reason"][1] for r in one) and not mism and not ref_exited_not_rep
    kinds = collections.Counter(r["reason"][0] for r in rows)
    mean = sum(dl) / len(dl) if dl else None
    det = {"n_exited_matched": n, "kinds_replay": dict(kinds), "same_minute": same_min, "pm1": pm1,
           "mean_dpx": mean, "min_dpx": min(dl) if dl else None, "mismatch": mism[:20], "ref_exited_not_replay": ref_exited_not_rep[:20],
           "reason_diff_1leg": [r for r in one if r["reason"][0] != r["reason"][1]][:20],
           "px_bad": [r for r in rows if not r["px_ok"]][:20], "open_end_replay": len(rep_open)}
    if n < 10 or kinds.get("TIME_STOP", 0) < 1 or kinds.get("TRAIL", 0) < 1:
        # van danh gia de lo loi som, nhung ket luan = KHONG DU MAU
        det["danh_gia_tam"] = _x1_ok(rows, n, same_min, pm1, mean, reason_ok)
        return NS, det
    return (PASS if _x1_ok(rows, n, same_min, pm1, mean, reason_ok) else FAIL), det


def _x1_ok(rows, n, same_min, pm1, mean, reason_ok):
    if n == 0:
        return False
    return (reason_ok and same_min >= 0.98 * n and same_min + pm1 == n and mean is not None and -0.008 <= mean <= 0
            and all(r["px_ok"] for r in rows))


# ------------------------------------------------------------------ D1
def dca_rows(legs):
    return [x for x in legs if x["level"] == "DCA_LEVEL1" and x["outcome"] == "SUBMITTED"]


def d1_natural(L, refdir):
    rep = [(int(x["decision_ts"]), x["symbol"], int(x["leg_idx"])) for x in dca_rows(L["legs"])]
    ref = [(int(x["decision_ts"]), x["symbol"], int(x["leg_idx"])) for x in rd(refdir + "/ref_legs.csv")
           if x["level"] == "DCA_LEVEL1" and x["outcome"] == "SUBMITTED"]
    det = {"replay": rep[:20], "ref": ref[:20]}
    if not rep and not ref:
        return NA, det
    return (PASS if sorted(rep) == sorted(ref) else FAIL), det


def d1_sdca(L, refdir, env, meta):
    if L["res"] is None:
        return FAIL, {"loi": "khong co result.json"}
    inj = L["res"].get("injections", {})
    syms = list((inj.get("sdca_start") or {}).keys())
    refsum = json.load(open(refdir + "/ref_summary.json")) if os.path.isfile(refdir + "/ref_summary.json") else {}
    ref_syms = list((refsum.get("sdca_start") or {}).keys())
    reflegs = rd(refdir + "/ref_legs.csv")
    det = {"sdca_replay": inj.get("sdca_start"), "sdca_ref": refsum.get("sdca_start"), "clusters": {}}
    ok = len(syms) >= 2 and sorted(syms) == sorted(ref_syms)
    full = 0
    first_buy = {}
    for f in L["fills"]:
        if f["side"] == "BUY" and f["symbol"] in syms and f["symbol"] not in first_buy:
            first_buy[f["symbol"]] = float(f["price"])
    for s in syms:
        st = int(inj["sdca_start"][s])
        rows = [x for x in L["legs"] if x["symbol"] == s and x["outcome"] == "SUBMITTED" and int(x["decision_ts"]) >= st - 60000]
        dl = [x for x in rows if x["level"] == "DCA_LEVEL1"]
        idx = [int(x["leg_idx"]) for x in dl]
        mins = [int(x["decision_ts"]) for x in dl]
        rmins = [int(x["decision_ts"]) for x in reflegs if x["symbol"] == s and x["level"] == "DCA_LEVEL1" and x["outcome"] == "SUBMITTED"]
        P = p_for(env, float(dl[0]["capital"]) if dl else 10000.0, "on")
        bud_ok = all(abs(float(x["budget"]) - float(R.budget(P, float(x["margin_before"]), int(x["leg_idx"])))) / float(x["budget"]) <= 1e-5
                     for x in dl)
        pre = []
        for x in dl:
            li = int(x["leg_idx"])
            fb = first_buy.get(s)
            drop = float(R.F(R.F(float(x["ref_px"])) / R.F(fb)) - R.F(1)) if fb else None
            if drop is None or drop > float(R.LEVELS[li - 1]):
                pre.append((x["decision_ts"], li, drop))
        no5 = len([x for x in L["legs"] if x["symbol"] == s and x["outcome"] == "SUBMITTED" and x["level"] == "DCA_LEVEL1"
                   and int(x["leg_idx"]) >= 4]) == 0
        c_ok = idx == [1, 2, 3] and mins == rmins and bud_ok and not pre and no5
        full += c_ok
        det["clusters"][s] = {"leg_idx": idx, "minutes": mins, "ref_minutes": rmins, "budget_ok": bud_ok, "leg_before_level": pre,
                              "no_5th": no5, "ok": c_ok}
    ok = ok and full >= 2
    return (PASS if ok else FAIL), det


# ------------------------------------------------------------------ F1
def f1(Lf, L0, refdir):
    if Lf["res"] is None:
        return FAIL, {"loi": "khong co result.json"}
    inj = Lf["res"].get("injections", {})
    s, b = inj.get("fin_inj_symbol"), inj.get("fin_inj_bar")
    if not s:
        return NA, {"loi": "khong co leg PASS sau moc tiem"}
    b = int(b)
    sub = [x for x in Lf["legs"] if x["symbol"] == s and int(x["decision_ts"]) == b and x["outcome"] == "SUBMITTED"]
    ocx = [x for x in Lf["outcomes"] if x["symbol"] == s and int(x["decision_ts"]) == b and x["outcome"] == "FIN_EXCL"]
    logx = bool(re.search(r"\[MINUTE-FIN-EXCL\][^\n]*" + re.escape(s), Lf["log"]))
    other_f = sorted((x["symbol"], x["outcome"]) for x in Lf["legs"] if int(x["decision_ts"]) == b and x["level"] == "PREDICT_SYMBOL_TRADE")
    other_0 = sorted((x["symbol"], x["outcome"]) for x in L0["legs"] if int(x["decision_ts"]) == b and x["level"] == "PREDICT_SYMBOL_TRADE"
                     and x["symbol"] != s)
    in_r0 = any(x["symbol"] == s and int(x["decision_ts"]) == b for x in L0["legs"])
    refs = json.load(open(refdir + "/ref_summary.json")).get("fin_inj") if os.path.isfile(refdir + "/ref_summary.json") else None
    det = {"symbol": s, "bar": b, "submitted": len(sub), "fin_excl_outcome": len(ocx), "log_line": logx, "others_fininj": other_f,
           "others_r0": other_0, "symbol_had_leg_in_r0": in_r0, "ref_fin_inj": refs}
    ok = not sub and ocx and logx and other_f == other_0 and in_r0
    return (PASS if ok else FAIL), det


# ------------------------------------------------------------------ K1
def k1(L):
    err = [ln for ln in L["log"].splitlines() if re.search(r"\sERROR\s", ln)]
    latch = [e for e in L["events"] if e["type"] == "KS_LATCH" and "[]" not in e["detail"]]
    khan = [ln for ln in L["log"].splitlines() if "KHAN" in ln]
    alerts = open(L["dir"] + "/alerts.txt", errors="replace").read() if os.path.isfile(L["dir"] + "/alerts.txt") else ""
    khan += [ln for ln in alerts.splitlines() if "KHAN" in ln]
    det = {"error_lines": len(err), "error_sample": err[:10], "latch": latch[:10], "khan": khan[:10]}
    if L["res"] is None:
        return FAIL, det
    return (PASS if not err and not latch and not khan else FAIL), det


# ------------------------------------------------------------------ E2
def e2(Lold, fx, dry_csv, labels_csv):
    man = json.load(open(fx + "/manifest.json"))
    if man["START"] != T1105:
        return NAPPLY, {"ly_do": "chi ap dung fixture 11-05 (fixture hien tai START=%s)" % man["START"]}
    real = rd(dry_csv)
    labels = {x["symbol"]: x["label"] for x in rd(labels_csv)}
    allowed = {"LEGACY-11-05", "JAR-R4Q-FIN2-BIGDOWN-SEL", "JAR-R4Q-FIN2-UNIVERSE-A1", "EXCHANGEINFO"}
    rep = {(x["symbol"], int(x["decision_ts"])): x for x in Lold["legs"] if x["outcome"] == "SUBMITTED"}
    match, unl = 0, []
    for x in real:
        k = (x["symbol"], int(x["decision_ts"]))
        y = rep.get(k)
        if y is not None and abs(float(y["budget"]) - float(x["budget"])) / float(x["budget"]) <= 1e-4:
            match += 1
        elif labels.get(x["symbol"]) not in allowed:
            unl.append(("thieu/lech", k))
    realk = {(x["symbol"], int(x["decision_ts"])) for x in real}
    lo, hi = min(k[1] for k in realk), max(k[1] for k in realk)
    for k in rep:
        if lo <= k[1] <= hi and k not in realk and labels.get(k[0]) not in allowed:
            unl.append(("thua", k))
    det = {"n_real": len(real), "match": match, "unlabeled": unl[:30]}
    return (PASS if match >= 20 and not unl else FAIL), det


# ------------------------------------------------------------------ §6
def micro(L0, env, meta, L1000, L4000):
    n = fail = 0
    for x in L0["legs"]:
        if x["outcome"] != "SUBMITTED":
            continue
        n += 1
        P = p_for(env, 1000.0, "on")
        u = float(x["margin_before"]) / float(x["capital"])
        b = R.budget(P, u * 1000.0, int(x["leg_idx"]) if x["leg_idx"] else 0)
        if b is None or float(b) < R.MIN_BUDGET:
            fail += 1
            continue
        m = meta.get(x["symbol"])
        px = float(x["sizing_px"])
        q = R.floor_to(float(b) / px, m["step"]) if m else Decimal(0)
        if m is None or q <= 0 or q < m["minq"] or Decimal(repr(float(q) * px)) < m["mn"]:
            fail += 1
    frac = (n - fail) / n if n else None

    def cnt(L):
        return dict(collections.Counter(x["outcome"] for x in L["legs"])) if L and L["legs"] else None
    return {"R0_legs": n, "fail_at_1000(BUDGET_SMALL|min_notional)": fail, "frac_ok_1000": frac,
            "quyet_dinh": None if frac is None else ("micro = 1 000" if frac >= 0.90 else "micro = 4 000"),
            "R-1000_outcomes": cnt(L1000), "R-4000_outcomes": cnt(L4000)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--fx", required=True)
    ap.add_argument("--env", required=True)
    ap.add_argument("--out", default=None)
    ap.add_argument("--dry-1105", default="")
    ap.add_argument("--labels-1105", default="")
    a = ap.parse_args()
    env = R.load_env(a.env)
    meta, _ = R.load_exinfo(a.fx + "/exinfo.json")
    Ls = {n: lane(a.runs, n) for n in ["R0", "R0-DRY", "R-OLD", "S-DCA", "FIN-INJ", "R-1000", "R-4000"]}
    out = collections.OrderedDict()
    c1s = {n: c1(Ls[n]) for n in FLAG_ON_LANES if Ls[n]["res"] is not None or os.path.isdir(Ls[n]["dir"])}
    out["C1"] = (PASS if c1s and all(v[0] == PASS for v in c1s.values()) else FAIL, c1s)
    for n in ("R0", "R0-DRY"):
        out["E1[%s]" % n] = e1(Ls[n], os.path.join(a.ref, n))
        out["S1[%s]" % n] = s1(Ls[n], env, meta)
        out["K1[%s]" % n] = k1(Ls[n])
    out["D1[tu nhien R0]"] = d1_natural(Ls["R0"], os.path.join(a.ref, "R0"))
    out["D1[S-DCA]"] = d1_sdca(Ls["S-DCA"], os.path.join(a.ref, "S-DCA"), env, meta)
    out["X1[R0]"] = x1(Ls["R0"], os.path.join(a.ref, "R0"), meta)
    out["F1[FIN-INJ]"] = f1(Ls["FIN-INJ"], Ls["R0"], os.path.join(a.ref, "FIN-INJ"))
    out["E2[R-OLD]"] = e2(Ls["R-OLD"], a.fx, a.dry_1105, a.labels_1105)
    out["R-OLD banners (ky vong TAT)"] = ("BAO CAO", {k: bool(re.search(p, Ls["R-OLD"]["log"])) for k, p in BANNERS.items()})
    out["§6 von micro"] = ("BAO CAO", micro(Ls["R0"], env, meta, Ls["R-1000"], Ls["R-4000"]))
    keys = ["C1", "E1[R0]", "E1[R0-DRY]", "S1[R0]", "S1[R0-DRY]", "D1[S-DCA]", "X1[R0]", "F1[FIN-INJ]", "K1[R0]", "K1[R0-DRY]", "E2[R-OLD]"]
    concl = PASS if all(out[k][0] == PASS for k in keys) else FAIL
    out["KET LUAN (iii)"] = (concl, "PASS <=> moi tieu chi PASS (KHONG XAY RA / KHONG DU MAU / CHUA AP DUNG != PASS)")
    js = json.dumps(out, indent=1, default=str, ensure_ascii=False)
    if a.out:
        open(a.out, "w").write(js)
    for k, v in out.items():
        print("%-28s %s" % (k, v[0]))
    print(js[:20000])


if __name__ == "__main__":
    main()
