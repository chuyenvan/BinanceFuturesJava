#!/usr/bin/env python3
"""Nhan K' (docs/prereg/PREREG_PARITY_V11_WINDOW_ADDENDUM1.md, fea9fb97) cho moi (phut, nguon) lech cua ngay PV_DAY.
  K3' : drop-one CHUNG MINH (OFF-BT chay lai tren U_D \\ S_M; S1-V xep hang lai bo S_M) => lech bien mat
  K1' : bang chung log/manifest NEU TEN chinh symbol gay lech (reread/overwritten/rewritten) trong [M-1440', M+10']
  K6  : hoan doi hang S1-V giua 2 ung vien ke nhau, |dv| <= 1e-6*max|v|, top-24 trung tap (mo ta, khong tinh K5)
  K2  : giu nhu prereg goc (lay tu labels_<tag>.json)
  K5  : phut co >= 1 nguon khong mang nhan nao trong K1'/K2/K3'/K4/K6
argv: plan | eval     (giua 2 buoc: python3 py/day_harness.py drop WORK/kprime_groups.json)
Doc WORK/labels_<tag>.json, join/net/s1v cua ngay, RUN_drop/g<k>/. Khong doc 242.
"""
import io
import json
import os
import re
import sys
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import day_eval as E  # noqa: E402
from day_s1v import rank_pct  # noqa: E402

C = E.C
WORK, TAG, RUN = C["WORK"], C["tag"], C["RUN"]
VIS, MIN = C["VIS"], 60000
T0, T1 = C["T0"], C["T1"]
DAY_D, DAY_PREV = C["day"], C["day_prev"]
f7 = E.f7


def ms(s):
    import datetime as dt
    return int(dt.datetime.strptime("2026-" + s + " +0700", "%Y-%m-%d %H:%M %z").timestamp() * 1000)


def vis_times(day, sym):
    p = "%s/%s/%s.zip" % (VIS, day, sym)
    if not os.path.exists(p):
        return None
    with zipfile.ZipFile(p) as z:
        raw = z.read(z.namelist()[0]).decode()
    first = raw.split("\n", 1)[0]
    d = pd.read_csv(io.StringIO(raw), header=0 if first.startswith("open_time") else None, usecols=[0])
    return np.asarray(d.iloc[:, 0].values, np.int64)


def membership_marks():
    """Moc doi thanh vien U cho D-1 va D: niem yet = nen Vision dau tien; huy niem yet = nen Vision cuoi."""
    days = sorted(os.listdir(VIS))
    if C["layout"] == "legacy-d1":
        syms = {d: set(f[:-4] for f in os.listdir(VIS + "/" + d) if f.endswith(".zip")) for d in days}
    else:
        UALL = set()
        for p in C["tsx_univ"]:
            UALL |= {x.strip() for x in open(p) if x.strip()}
        syms = {d: set(f[:-4] for f in os.listdir(VIS + "/" + d) if f.endswith(".zip")) & UALL for d in days}
        syms[DAY_D] = {x.strip() for x in open(C["U"]) if x.strip()}
    marks = []
    for d in (DAY_PREV, DAY_D):
        dprev = days[days.index(d) - 1]
        for s in sorted(syms[d] - syms[dprev]):
            marks.append({"symbol": s, "kind": "list", "day": d, "t": int(vis_times(d, s).min())})
        for s in sorted(syms[dprev] - syms[d]):
            marks.append({"symbol": s, "kind": "delist", "day": d, "t": int(vis_times(dprev, s).max())})
    for m in marks:
        m["p07"] = f7(m["t"])
    return marks


def bad_minutes():
    lab = json.load(open(WORK + "/labels_%s.json" % TAG))
    return lab, [(ms(r["min"]), r) for r in lab["bad_minutes"]]


def plan():
    lab, bad = bad_minutes()
    marks = membership_marks()
    groups, mg = {}, {}
    for t, r in bad:
        S = tuple(sorted({m["symbol"] for m in marks if t - 1440 * MIN <= m["t"] <= t}))
        if S:
            groups.setdefault(S, len(groups))
            mg[r["min"]] = groups[S]
    out = {"marks": marks, "groups": [{"k": k, "drop": list(S), "n_minutes": sum(1 for v in mg.values() if v == k)}
                                      for S, k in groups.items()], "minute_group": mg}
    json.dump(out, open(WORK + "/kprime_groups.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k != "minute_group"}, indent=1))


def k6_rows(g):
    """g = cac dong s1v_rows cua 1 gio. Tra (tat ca dong lech la K6?, chi tiet)."""
    eq = E.eq
    if len(g) == 0:
        return False, {}
    top_c = set(g.sort_values(["score_calc", "symbol"]).symbol.head(24))
    top_l = set(g.sort_values(["score_live", "symbol"]).symbol.head(24))
    top_same = top_c == top_l
    bad_feat = {}
    for i in range(7):
        m = ~eq(g["c%d" % i], g["l%d" % i])
        for s in g.symbol[m]:
            bad_feat.setdefault(s, set()).add(i)
    bad_score = set(g.symbol[~eq(g.score_calc, g.score_live)])
    G = g.set_index("symbol")
    expl, det = {}, []
    for s, cols in bad_feat.items():
        ok = True
        for c in cols:
            if c not in (2, 5):
                ok = False
                break
            v = 1 if c == 2 else 4
            n = int(np.sum(~np.isnan(g["c%d" % v].values)))
            lc, cc = G.loc[s, "l%d" % c], G.loc[s, "c%d" % c]
            # |dhang| = 1/n; dung sai nhu eq() vi hang live in float32 (sai so ~1e-8, >> 1e-6/n)
            if not (n > 0 and abs(abs(lc - cc) - 1.0 / n) <= 1e-6 * (1 + abs(lc))):
                ok = False
                break
            part = g[(g.symbol != s) & eq(g["l%d" % c], cc) & eq(g["c%d" % c], lc)]
            hit = None
            for s2 in part.symbol:
                for side in ("l", "c"):
                    a, b = float(G.loc[s, "%s%d" % (side, v)]), float(G.loc[s2, "%s%d" % (side, v)])
                    if abs(a - b) <= 1e-6 * max(abs(a), abs(b)):
                        hit = (s2, side, a, b)
                        break
                if hit:
                    break
            if not hit:
                ok = False
                break
            det.append({"symbol": s, "col": "f%d" % c, "partner": hit[0], "side": hit[1], "v": hit[2], "v_partner": hit[3]})
        expl[s] = ok
    all_ok = top_same and all(expl.values()) and all(expl.get(s, False) for s in bad_score)
    return all_ok, {"top24_same_set": top_same, "rows_bad": len(set(bad_feat) | bad_score),
                    "rows_k6": sum(1 for v in expl.values() if v), "swaps": det[:6],
                    "score_only_rows": sorted(bad_score - set(bad_feat))[:6]}


def s1v_k5_class(g):
    """MO TA (khong phai nhan): phan loai dong S1-V lech KHONG dat K6 theo dinh nghia da chot.
    tie_split: chi cot rank lech, |dhang| = 0,5/n va co doi tac ke ma 1 phia hoa hang, |dv| <= 1e-6*max|v|
    score_only: moi feature khop dung sai nhung score lech; other: con lai."""
    eq = E.eq
    G = g.set_index("symbol")
    out = {"tie_split": 0, "score_only": 0, "other": 0}
    bad_feat = {}
    for i in range(7):
        m = ~eq(g["c%d" % i], g["l%d" % i])
        for s in g.symbol[m]:
            bad_feat.setdefault(s, set()).add(i)
    for s in set(g.symbol[~eq(g.score_calc, g.score_live)]) - set(bad_feat):
        out["score_only"] += 1
    for s, cols in bad_feat.items():
        cls = "tie_split"
        for c in cols:
            if c not in (2, 5):
                cls = "other"
                break
            v = 1 if c == 2 else 4
            n = int(np.sum(~np.isnan(g["c%d" % v].values)))
            lc, cc = G.loc[s, "l%d" % c], G.loc[s, "c%d" % c]
            if abs(abs(lc - cc) - 0.5 / n) > 1e-6 * (1 + abs(lc)):
                cls = "other"
                break
            part = g[(g.symbol != s) & (eq(g["c%d" % c], cc) | eq(g["l%d" % c], lc))]
            if not any(abs(float(G.loc[s, "%s%d" % (sd, v)]) - float(G.loc[s2, "%s%d" % (sd, v)])) <=
                       1e-6 * max(abs(float(G.loc[s, "%s%d" % (sd, v)])), abs(float(G.loc[s2, "%s%d" % (sd, v)])))
                       for s2 in part.symbol for sd in ("l", "c")):
                cls = "other"
                break
        out[cls] += 1
    return out


def k1p_evidence():
    """Dong log NEU TEN symbol + tu khoa reread/overwrit/rewrit/ghi de. Dong chi co bo dem khong tinh."""
    ev = []
    pk = re.compile(r"(reread|overwrit|rewrit|ghi de|ghi đè|doc lai)", re.I)
    ps = re.compile(r"\b([A-Z0-9]{2,}USDT)\b")
    for ln in E.loglines():
        if pk.search(ln):
            syms = ps.findall(ln)
            if syms:
                t = E.lt(ln)
                for s in syms:
                    ev.append((t, s, ln[:200]))
    return ev


_DEV = {}


def deviating_symbols(src, t, SV):
    """Symbol lech cu the cua nguon (chi FUND/NET/S1-V xac dinh duoc symbol; P1-F/MD/P1/GV-O la muc thi truong)."""
    if src == "S1V":
        g = SV[SV.ts == t]
        ok = E.eq(g.score_calc, g.score_live)
        for i in range(7):
            ok &= E.eq(g["c%d" % i], g["l%d" % i])
        return set(g.symbol[~ok])
    if "jf" not in _DEV:
        _DEV["jf"] = pd.read_csv(WORK + "/join_fund.csv.gz", usecols=["min", "symbol", "ok"], dtype={"symbol": str})
        _DEV["nb"] = pd.read_csv(WORK + "/net_pw.csv.gz", dtype={"symbol": str})
    if src == "FUND":
        x = _DEV["jf"]
        return set(x.symbol[(x["min"] == t) & (~x.ok.astype(bool))])
    x = _DEV["nb"]
    x = x[x["min"] == t]
    return set(x.symbol[np.abs(x.net_l - x.net_b) > 1e-6 * (1 + np.abs(x.net_b))])


def eval_():
    lab, bad = bad_minutes()
    gp = json.load(open(WORK + "/kprime_groups.json"))
    mg = gp["minute_group"]
    SV = pd.read_csv(WORK + "/s1v_rows.csv.gz")
    sess = E.s1_session()
    nm = sess.get_inputs()[0].name
    F = E.load_live45()
    sel = E.load_sel()
    s1 = E.load_s1()[["ts", "symbol", "score"]]
    netlive = pd.read_csv(WORK + "/net_live_all.csv.gz", dtype={"symbol": str})
    ev = k1p_evidence()
    # ---- K3' theo nhom drop
    k3p = {}
    for g in gp["groups"]:
        k, G = g["k"], set(g["drop"])
        mins = sorted(ms(m) for m, kk in mg.items() if kk == k)
        d = RUN + "_drop/g%d" % k
        chk = {t: {} for t in mins}
        if not os.path.exists(d + "/out_BT.csv.gz"):
            for t in mins:
                chk[t]["_err"] = "thieu drop run"
            k3p.update(chk)
            continue
        Bd = E.load_bt(d + "/out_BT.csv.gz")
        L, J = E.gate_join(Bd)
        J = J[J["min"].isin(mins)].reset_index(drop=True)
        if len(J):
            J["p15_off"] = E.p15_off_of(J)
        Ud = pd.read_csv(d + "/fund_BT.csv.gz", dtype={"symbol": str})
        Ud = Ud[Ud["min"].isin(mins)]
        Jf, _ = E.fund_join(Ud, F[F["min"].isin(mins)])
        if len(Jf):
            pwl, pwb = E.net_pair(Jf)
            Jf["net_l"], Jf["net_b"] = pwl, pwb
        for t in mins:
            r = J[J["min"] == t]
            if len(r):
                r = r.iloc[0]
                chk[t]["P1F"] = bool(all(E.eq([r[f + "_l"]], [r[f + "_b"]])[0] for f in E.NONFUND_GATE))
                chk[t]["MD"] = bool(all(E.eq([r[a]], [r[b]])[0] for a, b in
                                        (("rateDownAvg", "r_down"), ("rateUpAvg", "r_up"), ("rateDown15MAvg", "r_down15"))))
                chk[t]["P1"] = bool(abs(r.p15_out - r.p15_off) / abs(r.p15_off) <= 1e-3)
            x = Jf[Jf["min"] == t]
            if len(x):
                chk[t]["FUND"] = bool(x.ok.all())
                chk[t]["NET"] = bool((np.abs(x.net_l - x.net_b) <= 1e-6 * (1 + np.abs(x.net_b))).all())
                nbmap = {(int(a), b): c for a, b, c in zip(x["min"], x.symbol, x.net_b)}
                Gd, _ = E.gv_rows(sel[sel.ts == t], s1[s1.ts == t], netlive[netlive["min"] == t], nbmap)
                o = Gd[Gd.tag == "off"]
                chk[t]["GV_O"] = bool(len(o) > 0 and E.eq(o.gv_calc, o.gv_live).all())
            sv = SV[(SV.ts == t) & (~SV.symbol.isin(G))].copy()
            if len(sv):
                sv["c2"] = rank_pct(sv.c1.values)
                sv["c5"] = rank_pct(sv.c4.values)
                X = sv[["c%d" % i for i in range(7)] + ["f7", "f8"]].values.astype(np.float32)
                sv["score_calc"] = (-sess.run(None, {nm: X})[0].reshape(-1)).astype(np.float32)
                ok = E.eq(sv.score_calc, sv.score_live)
                for i in range(7):
                    ok &= E.eq(sv["c%d" % i], sv["l%d" % i])
                chk[t]["S1V"] = bool(ok.all())
        k3p.update(chk)
    # ---- gan nhan
    out_rows, cnt, cnt_ms = [], {}, {}
    for t, r in bad:
        srcs = r["sources"]
        k2 = [x for x in r["labels"] if x.startswith("K2")]
        per = {}
        k6d = None
        for s in srcs:
            labs = list(k2)
            if k3p.get(t, {}).get(s) is True:
                labs.append("K3'")
            if s == "S1V":
                ok6, k6d = k6_rows(SV[SV.ts == t])
                if ok6:
                    labs.append("K6")
            if ev and s in ("FUND", "NET", "S1V"):
                dev = deviating_symbols(s, t, SV)
                if any(t - 1440 * MIN <= (te or 0) <= t + 10 * MIN and sym in dev for te, sym, _ in ev):
                    labs.append("K1'")
            per[s] = sorted(set(labs))
            for x in per[s]:
                cnt_ms[x] = cnt_ms.get(x, 0) + 1
        k5 = any(not v for v in per.values())
        mlabs = sorted(set(sum(per.values(), [])))
        for x in mlabs:
            cnt[x] = cnt.get(x, 0) + 1
        if k5:
            cnt["K5"] = cnt.get("K5", 0) + 1
        s1c = s1v_k5_class(SV[SV.ts == t]) if ("S1V" in per and not per["S1V"]) else None
        out_rows.append({"min": r["min"], "sources": srcs, "per_source": per, "K5": k5, "old_labels": r["labels"],
                         "S_M_group": mg.get(r["min"]), "k3p_check": k3p.get(t), "k6_detail": k6d,
                         "s1v_k5_class": s1c})
    res = {"addendum": "PREREG_PARITY_V11_WINDOW_ADDENDUM1 (fea9fb97)", "day": DAY_D, "n_bad_minutes": len(out_rows),
           "minutes_with_label": cnt, "minute_source_pairs_with_label": cnt_ms,
           "n_minute_source_pairs": sum(len(r["sources"]) for r in out_rows),
           "K5_minutes": [r["min"] for r in out_rows if r["K5"]],
           "K5_by_source": {s: sum(1 for r in out_rows if r["K5"] and not r["per_source"].get(s, [1])) for s in
                            ("P1F", "P1", "MD", "FUND", "NET", "GV_O", "S1V")},
           "K5_nonS1V_minutes": [r["min"] for r in out_rows if r["K5"] and any(not v for s, v in r["per_source"].items()
                                                                                 if s != "S1V")],
           "S1V_K5_minutes_by_class_desc": {
               c: sum(1 for r in out_rows if r["s1v_k5_class"] and set(k for k, v in r["s1v_k5_class"].items() if v) == {c})
               for c in ("tie_split", "score_only", "other")},
           "S1V_K5_minutes_mixed_class": sum(1 for r in out_rows if r["s1v_k5_class"] and
                                             sum(1 for v in r["s1v_k5_class"].values() if v) > 1),
           "membership_marks": gp["marks"], "drop_groups": gp["groups"],
           "k1p_evidence_lines": len(ev), "k1p_evidence_first": [(f7(a) if a else None, b, c) for a, b, c in ev[:5]],
           "old_K1_minutes_count_based": sum(1 for r in out_rows if "K1" in r["old_labels"]),
           "rows": out_rows}
    json.dump(res, open(WORK + "/kprime_%s.json" % TAG, "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in res.items() if k != "rows"}, indent=1, default=str)[:5000])
    for r in out_rows:
        if r["K5"] and r["sources"] != ["S1V"]:
            print(r["min"], r["sources"], r["per_source"])


if __name__ == "__main__":
    {"plan": plan, "eval": eval_}[sys.argv[1]]()
