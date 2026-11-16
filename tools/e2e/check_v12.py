#!/usr/bin/env python3
"""E2E_REPLAY_V12 - BO CHAM (prereg PREREG_E2E_REPLAY_V12 §5, §6). Doc output replay (<runs>/<LUOT>/...) + REF
(<ref>/<LUOT>/ref_*.csv, do ref_v12.py sinh DOC LAP) + fixture. In PASS / FAIL / KHONG XAY RA / KHONG DU MAU / CHUA AP DUNG
cho C1, E1, S1, D1, X1, F1, K1, E2 + bang §6. "KHONG XAY RA" / "KHONG DU MAU" KHONG tinh la PASS.

ERRATA2 (593e7f45) E7: X1 nhan ARM_CUNG_NEN do REF-nhip quyet dinh (xem x1). E8: bao cao N7 (A1 vs khong loc), N8 (key config
khong mac dinh JAR trong result.json), N10 (eq_at REF cache 60 s vs eq_at jar).
ERRATA1 (33633d41): E (|E_REF - E_replay|/E <= 1e-6, C_eff = min(C3_CAPITAL, E) trong S1/D1), D1 tu nhien vao ket luan + dieu
kien thi truong / p15 cho moi leg DCA, X1 moi (TIME_STOP 0 lech phut + gia trong [L,H]; ARM_CUNG_NEN; stopPrice jar dat vs SL REF
<= 2 tick; gia khop san gia chi bao cao; X14_HOAN loai khoi X1), C1 kiem dung danh sach override khai bao (+LIVE_TS_MKT_EXT=0).

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
T1105 = 1793836800000   # 2026-11-05 07:00 +07


def rd(path):
    if not os.path.isfile(path):
        return []
    with open(path) as fh:
        return list(csv.DictReader(fh))


def lane(runs, n):
    d = os.path.join(runs, n)
    res = json.load(open(d + "/result.json")) if os.path.isfile(d + "/result.json") else None
    log = open(d + "/run.log", errors="replace").read() if os.path.isfile(d + "/run.log") else ""
    return dict(dir=d, name=n, res=res, log=log, legs=rd(d + "/legs.csv"), fills=rd(d + "/fills.csv"),
                events=rd(d + "/events.csv"), outcomes=rd(d + "/outcomes.csv"), market=rd(d + "/market.csv"))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


# ------------------------------------------------------------------ C1
BANNERS = {"LIVE-SIZING": r"\[LIVE-SIZING\] LIVE_APPLY_GRID_RATIO=true", "LIVE-DCA-GRID": r"\[LIVE-DCA-GRID\] LIVE_DCA_GRID_ENABLED=true .*applyRatio=true",
           "MINUTE-FIN": r"\[MINUTE-FIN\] BAT", "GATE-RATIO": r"\[GATE-RATIO\] LIVE BAT"}


# prereg ?1 + ERRATA1 E2 (N3): DUNG tap override khai bao (LIVE_GATE_ROLLING_FILE = "duong dan du lieu")
DECL_OVR = {"LIVE_ADAPTER", "C3_CAPITAL", "LIVE_APPLY_GRID_RATIO", "LIVE_DCA_GRID_ENABLED", "C3_EXCLUDE_LEGACY_HELD",
            "LIVE_IS_SHADOW_HOST", "LIVE_GATE_ROLLING_FILE", "LIVE_TS_MKT_EXT"}


def c1(L):
    if L["res"] is None:
        return FAIL, {"loi": "khong co result.json (refused/crash)"}
    jc, ec = L["res"].get("jar_check", {}), L["res"].get("env_check", {})
    nres = sum(1 for v in jc.get("class_resources", {}).values() if v.startswith("jar:file:" + jc.get("jar_path", "?")))
    ban = {k: bool(re.search(p, L["log"])) for k, p in BANNERS.items()}
    det = {"jar_md5": jc.get("jar_md5"), "jar_ok": jc.get("ok"), "classes_from_jar": nres, "banners": ban,
           "missing_names": ec.get("missing_names_not_overridden"), "differ": ec.get("differ_not_overridden"),
           "overrides": ec.get("overrides_declared"),
           "config_properties_replay(E5)": L["res"].get("config_properties_replay"),
           "Cfg_khong_dat_env_mac_dinh_JAR(E5)": L["res"].get("cfg_effective", {}).get("Cfg.asked_khong_dat_env_(mac_dinh_JAR)"),
           "died_symbols_jar": (L["res"].get("market") or {}).get("died_symbols_jar")}
    ov = ec.get("overrides_declared") or {}
    det["override_set_ok"] = set(ov) == DECL_OVR and ov.get("LIVE_TS_MKT_EXT") == "0"
    ok = det["override_set_ok"] and (jc.get("ok") is True and jc.get("jar_md5") == "641803565297d4065d90245e04a00f11" and nres == 10 and all(ban.values())
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


# ------------------------------------------------------------------ S1 + E (ERRATA1 E1/N4)
def p_for(env, cap, flags):
    return R.params(env, cap, flags)


def qty_ok(b, px, step, qty):
    want = (Decimal(repr(b)) / Decimal(repr(px))).to_integral_value(rounding=ROUND_FLOOR) if step <= 0 else \
        ((Decimal(repr(b)) / Decimal(repr(px))) / step).to_integral_value(rounding=ROUND_FLOOR) * step
    return want == Decimal(qty), str(want)


def c3cap(L):
    """C3_CAPITAL cua luot (override khai truoc)."""
    return float(L["res"]["cfg_effective"]["rig.CAPITAL"]) if L["res"] else None


class FX:
    """Fixture (nen giao dich klines.csv.gz + ts_ext.csv) cho mark / gia nen / X14."""

    def __init__(self, fx):
        self.dir = fx
        self.man = json.load(open(fx + "/manifest.json"))
        self.END = self.man["END"]
        self.bars = R.load_bars(fx)
        self.lastc = {s: m[max(t for t in m if t < self.END)][3] for s, m in self.bars.items() if any(t < self.END for t in m)}
        self.tsext = rd(fx + "/ts_ext.csv")

    def raw_bar_fn(self, flat):
        def raw_bar(s, t):
            x = self.bars.get(s, {}).get(t)
            if x is None and flat and t >= self.END and s in self.lastc:
                v = self.lastc[s]
                x = (v, v, v, v)
            return x
        return raw_bar

    def x14_flag(self, day):
        """flag X14 that cua ngay UTC `day` (dong log [TS-EXT] flag cuoi cung cua ngay, uu tien final=true); None = khong co."""
        rows = [x for x in self.tsext if x["day"] == day]
        fin = [x for x in rows if x["final"] == "true"]
        r = (fin or rows)
        return r[-1]["flag"] if r else None


def ref_summary(refdir):
    p = refdir + "/ref_summary.json"
    return json.load(open(p)) if os.path.isfile(p) else {}


def lane_fct_flat(L, refdir):
    """he so S-DCA theo moc cua REF (doc lap) + co gia phang (S-TS) cua luot."""
    st = {k: int(v) for k, v in (ref_summary(refdir).get("sdca_start") or {}).items()}
    flat = bool(((L["res"] or {}).get("injections") or {}).get("flat_ext"))
    return R.sdca_fct(st), flat


def e_rows(L, refdir, fxo):
    """Moi leg SUBMITTED: E_replay (cot eq = cache C3MainEquity ma capital() vua dung) + eq_at jar; [ERRATA3 E10] REF DOC LAP:
    eq_at_REF = cot eq_at cua ref_market.csv tai phut quyet dinh (mo hinh cache 60 s cua REF, khong doc eq_at jar),
    E_REF = ref_v12.equity_at(fills.csv, eq_at_REF) (khop SAN + mark fixture), C_eff_REF = min(C3_CAPITAL, E_REF),
    used_REF = ref_u.csv (gia von vi the dang mo truoc BUY dau cua cid, tu fills.csv), U_REF = used_REF / C_eff_REF;
    U_jar = margin_before / capital (jar). E_REF_tai_eq_at_jar chi BAO CAO."""
    fills = R.load_fills(L["dir"] + "/fills.csv") if os.path.isfile(L["dir"] + "/fills.csv") else []
    fct, flat = lane_fct_flat(L, refdir)
    mark = R.make_mark(fxo.raw_bar_fn(flat), fct)
    C3 = c3cap(L)
    eqat = {int(x["b"]): x.get("eq_at", "") for x in rd(refdir + "/ref_market.csv")}
    ur = {x["cid"]: float(x["used_before_usd"]) for x in rd(refdir + "/ref_u.csv")}
    isint = lambda v: str(v or "").lstrip("-").isdigit()  # noqa: E731
    out = {}
    for x in L["legs"]:
        if x["outcome"] != "SUBMITTED":
            continue
        dec = int(x["decision_ts"])
        at = int(x["eq_at"]) if isint(x.get("eq_at")) else -1
        atr = int(eqat[dec]) if isint(eqat.get(dec)) else -1
        er = R.equity_at(fills, atr, mark, C3) if atr > 0 else None
        ceff = min(C3, er) if er is not None else None
        used = ur.get(x["cid"])
        cap_j, mb = fnum(x.get("capital")), fnum(x.get("margin_before"))
        out[x["cid"]] = dict(eq=fnum(x.get("eq")), at=at, at_ref=atr, e_ref=er, ceff=ceff, dec=dec, used_ref=used,
                             u_ref=(used / ceff if (used is not None and ceff) else None),
                             u_jar=(mb / cap_j if (mb is not None and cap_j) else None),
                             e_ref_tai_eq_at_jar_bao_cao=(R.equity_at(fills, at, mark, C3) if at > 0 else None))
    return out


def u_check(E):
    """[ERRATA3 E10] |U_REF - U_jar| <= 1e-6 cho MOI SUBMIT (thieu U_REF / U_jar => loi)."""
    bad, worst = [], 0.0
    for cid, e in E.items():
        if e.get("u_ref") is None or e.get("u_jar") is None:
            bad.append({"leg": cid, "loi": "thieu U_REF/U_jar", "used_ref": e.get("used_ref")})
            continue
        d = abs(e["u_ref"] - e["u_jar"])
        worst = max(worst, d)
        if d > 1e-6:
            bad.append({"leg": cid, "U_REF": e["u_ref"], "U_jar": e["u_jar"], "abs": d})
    return bad, worst


def e_check(E):
    bad, worst, lag = [], 0.0, collections.Counter()
    for cid, e in E.items():
        lag[(e["at"] - e["dec"]) // 1000 if e["at"] > 0 else None] += 1
        if e["eq"] is None or e["e_ref"] is None:
            bad.append({"leg": cid, "loi": "thieu eq / eq_at REF"})
            continue
        rel = abs(e["e_ref"] - e["eq"]) / abs(e["e_ref"])
        worst = max(worst, rel)
        if rel > 1e-6:
            bad.append({"leg": cid, "E_replay": e["eq"], "E_REF(eq_at_REF)": e["e_ref"], "rel": rel})
        # [ERRATA3 E10] eq_at jar (thoi diem cache equity jar dung khi size) == eq_at REF (mo hinh cache doc lap)
        if e["at"] != e["at_ref"]:
            bad.append({"leg": cid, "loi": "eq_at jar != eq_at REF", "eq_at_jar": e["at"], "eq_at_REF": e["at_ref"]})
    return bad, worst, dict(lag)


def s1(L, env, meta, E, flags="on"):
    bad, n, worst = [], 0, 0.0
    first3 = []
    C3 = c3cap(L)
    ebad, eworst, lag = e_check(E)
    ubad, uworst = u_check(E)
    for x in L["legs"]:
        if x["outcome"] != "SUBMITTED":
            continue
        n += 1
        e = E.get(x["cid"]) or {}
        cap = e.get("ceff") if e.get("ceff") is not None else C3
        b = float(x["budget"])
        used = e.get("used_ref")   # [ERRATA3 E10] U DOC LAP (REF tu fills.csv), KHONG dung margin_before cua jar
        li = int(x["leg_idx"]) if x["leg_idx"] not in ("", None) else 0
        bref = R.budget(p_for(env, cap, flags), used, li) if used is not None else None
        rel = abs(b - float(bref)) / b if bref is not None else 1.0
        worst = max(worst, rel)
        m = meta.get(x["symbol"])
        qok, want = qty_ok(b, float(x["sizing_px"]), m["step"] if m else Decimal(0), x["qty"])
        if rel > 1e-5 or not qok:
            bad.append({"leg": x["cid"], "b": b, "b_ref": float(bref) if bref is not None else None, "rel": rel, "qty": x["qty"],
                        "qty_ref": want, "C_eff_REF": cap, "capital_code": fnum(x["capital"])})
        if len(first3) < 3:
            first3.append((b, used, fnum(x["margin_before"])))
    hv = R.hand_values()
    hv_ok = all(abs(a - e) <= 0.005 * e for a, e in zip(hv, [225.00, 216.56, 208.44]))
    det = {"n_submit": n, "worst_rel_budget": worst, "bad": bad[:20], "n_bad": len(bad), "hand_values_ref": hv, "hand_ok": hv_ok,
           "first3_replay(b,used_REF,margin_before_jar)": first3, "C3_CAPITAL": C3,
           "U(E10)": {"worst_abs": uworst, "n_bad(>1e-6)": len(ubad), "bad": ubad[:10]},
           "E": {"worst_rel": eworst, "n_bad(>1e-6)": len(ebad), "bad": ebad[:10], "eq_at_minus_decision_s": lag,
                 "C_eff_min": min((e["ceff"] for e in E.values() if e["ceff"] is not None), default=None)}}
    if n == 0:
        return NA, det
    return (PASS if not bad and hv_ok and not ebad and not ubad else FAIL), det


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
                c["exit_cid"] = c["sells"][-1][3]
                tstop = any(c["first_ms"] <= t <= c["exit_ms"] for t in ts_ev.get(s, []))
                c["reason"] = "TIME_STOP" if tstop else ("TRAIL" if c["sells"][-1][3].startswith("c3s-") else
                                                         "OTHER:" + c["sells"][-1][3].split("-")[0])
                c["vwap"] = sum(z[0] * z[1] for z in c["buys"]) / sum(z[0] for z in c["buys"])
                out.append(c)
                del cur[s]
    return out, list(cur.values())


def utc_day(ms):
    import datetime as _dt
    return _dt.datetime.fromtimestamp(ms / 1000, _dt.timezone.utc).strftime("%Y-%m-%d")


def x1(L, refdir, meta, fxo):
    """ERRATA1 X1 + ERRATA2 E7: ly do cum 1 leg == REF; TIME_STOP: phut == REF (0 lech) + gia khop trong [L,H] nen do;
    nhan ARM_CUNG_NEN do REF-NHIP quyet dinh (cot nhip_label cua ref_clusters.csv): cum co nhan => |stopPrice jar DAT - SL REF-nhip|
    <= 2 tick VA phut thoat == phut thoat REF-nhip; cum khong nhan => nhu ERRATA1 E4 so voi REF-nen (>= 98 % cung phut, du <= +-1,
    stopPrice <= 2 tick); jar thoat kieu arm-cung-nen (TRAIL_ARM/TRAIL_SL cua symbol trong CHINH phut thoat jar) ma REF-nhip khong
    gan nhan (hoac nguoc lai) => FAIL; X14_HOAN loai khoi X1. Gia khop san gia: BAO CAO. Bao cao rieng cum co nhan: dGia, dPhut
    REF-nhip so voi REF-nen."""
    rep, rep_open = clusters_replay(L, meta)
    ref = {(x["symbol"], int(x["b0"])): x for x in rd(refdir + "/ref_clusters.csv")}
    fct, flat = lane_fct_flat(L, refdir)
    raw = fxo.raw_bar_fn(flat)
    stop_px = {}
    armsl = collections.defaultdict(list)
    for e in L["events"]:
        if e["type"] == "TRAIL_STOP_PLACED":
            m = re.search(r"cid=(\S+)", e["detail"])
            if m:
                stop_px[m.group(1)] = float(e["value"])
        elif e["type"] in ("TRAIL_ARM", "TRAIL_SL"):
            armsl[e["symbol"]].append(int(e["ms"]))
    rows, mism = [], []
    for c in rep:
        k = (c["symbol"], c["b0"])
        f = ref.get(k)
        if f is not None and f["reason"] == "OPEN" and f.get("nhip_label") == "1" and f.get("nhip_reason") not in ("", "OPEN", None):
            f = dict(f, exit_bar=f["nhip_exit_bar"], reason=f["nhip_reason"], exit_px=f["nhip_exit_px"], sl=f["nhip_sl"])
        if f is None or f["reason"] == "OPEN":
            mism.append({"cum": k, "replay": c["reason"], "ref": None if f is None else "OPEN"})
            continue
        if "nhip_label" not in f:
            mism.append({"cum": k, "loi": "ref_clusters.csv thieu cot nhip_* (REF cu, truoc ERRATA2)"})
            continue
        em = c["exit_ms"] // 60000 * 60000
        dm = (em - int(f["exit_bar"])) // 60000
        rr = "TRAIL" if f["reason"].startswith("TRAIL") else f["reason"]
        tick = float(meta[c["symbol"]]["tick"]) if c["symbol"] in meta else 0.0
        is_ts = rr == "TIME_STOP" or c["reason"] == "TIME_STOP"
        flag = fxo.x14_flag(utc_day(int(f["exit_bar"]))) if is_ts else None
        x14 = is_ts and flag == "ON"
        jar_arm = any(em <= t < em + 60000 and t >= c["first_ms"] for t in armsl[c["symbol"]]) and not is_ts
        lab = f["nhip_label"] == "1"
        nb = int(f["nhip_exit_bar"]) if f["nhip_exit_bar"] not in ("", None) else None
        nsl, slnen = fnum(f["nhip_sl"]), fnum(f["sl"])
        dfill = (c["exit_px"] - float(f["exit_px"])) / float(f["exit_px"])
        row = {"cum": k, "legs": c["legs"], "reason": (c["reason"], rr), "dmin": dm, "dfill_bao_cao": dfill, "x14_flag": flag,
               "X14_HOAN": x14, "ARM_CUNG_NEN": lab, "ARM_CUNG_NEN_jar": jar_arm, "nhan_khop": lab == jar_arm,
               "nhip": {"exit_bar": nb, "reason": f["nhip_reason"], "k": f["nhip_k"], "sl": nsl, "ev": f.get("nhip_ev_phut_thoat")}}
        if lab:
            row["dmin_vs_nhip"] = (em - nb) // 60000 if nb is not None else None
            row["nhip_vs_nen"] = {"dphut": (nb - int(f["exit_bar"])) // 60000 if nb is not None else None,
                                  "dsl_tick": (nsl - slnen) / tick if (nsl is not None and slnen is not None and tick > 0) else None,
                                  "dsl_pct": (nsl - slnen) / slnen if (nsl is not None and slnen) else None}
        if c["reason"] == "TRAIL":
            sp = stop_px.get(c["exit_cid"])
            sl = nsl if lab else slnen
            row["stop_dat"], row["sl_ref"], row["sl_ref_nguon"], row["tick"] = sp, sl, ("REF-nhip" if lab else "REF-nen"), tick
            row["px_ok"] = sp is not None and sl is not None and abs(sp - sl) <= 2 * tick + 1e-12
            row["dstop_tick"] = (sp - sl) / tick if (sp is not None and sl is not None and tick > 0) else None
        elif c["reason"] == "TIME_STOP":
            x = raw(c["symbol"], em)
            fv = fct(c["symbol"], em)
            if x is None:
                row["px_ok"] = False
            else:
                lo, hi = x[2] * fv, x[1] * fv
                row["bar_LH"] = (lo, hi)
                row["px_ok"] = lo * (1 - 1e-12) <= c["exit_px"] <= hi * (1 + 1e-12)
        else:
            row["px_ok"] = False
        rows.append(row)
    ref_exited_not_rep = [k for k, f in ref.items() if (f["reason"] != "OPEN" or (f.get("nhip_label") == "1" and f.get("nhip_reason") not in ("", "OPEN", None)))
                          and not any((c["symbol"], c["b0"]) == k for c in rep)]
    ev = [r for r in rows if not r["X14_HOAN"]]
    ts = [r for r in ev if "TIME_STOP" in r["reason"]]
    arm = [r for r in ev if r["ARM_CUNG_NEN"] and r not in ts]
    oth = [r for r in ev if r not in ts and r not in arm]
    same = sum(1 for r in oth if r["dmin"] == 0)
    one = [r for r in ev if r["legs"] == 1]
    lab_bad = [r for r in ev if not r["nhan_khop"]]
    reason_ok = all(r["reason"][0] == r["reason"][1] for r in one) and not mism and not ref_exited_not_rep
    ok_min = (all(r["dmin"] == 0 for r in ts) and all(r.get("dmin_vs_nhip") == 0 for r in arm)
              and (not oth or same >= 0.98 * len(oth)) and all(abs(r["dmin"]) <= 1 for r in oth))
    ok_px = all(r["px_ok"] for r in ev)
    ok_lab = not lab_bad
    kinds = collections.Counter(r["reason"][0] for r in ev)
    dl = [r["dfill_bao_cao"] for r in ev if "TIME_STOP" not in r["reason"]]
    det = {"n_danh_gia": len(ev), "kinds_replay": dict(kinds), "n_TIME_STOP": len(ts),
           "n_ARM_CUNG_NEN(REF-nhip)": len(arm), "n_ARM_CUNG_NEN_jar": sum(1 for r in ev if r["ARM_CUNG_NEN_jar"]),
           "ARM_CUNG_NEN_bao_cao_rieng": [{"cum": r["cum"], "dmin_jar_vs_nhip": r.get("dmin_vs_nhip"), "dmin_jar_vs_nen": r["dmin"],
                                           "nhip_vs_nen": r.get("nhip_vs_nen"), "dstop_tick_vs_nhip": r.get("dstop_tick"),
                                           "dfill": r["dfill_bao_cao"], "ev": r["nhip"]["ev"]} for r in arm],
           "nhan_lech(jar vs REF-nhip)": [{"cum": r["cum"], "jar": r["ARM_CUNG_NEN_jar"], "ref_nhip": r["ARM_CUNG_NEN"],
                                          "dmin": r["dmin"], "nhip": r["nhip"]} for r in lab_bad][:20],
           "khong_nhan_nhip_khac_phut_nen(bao cao)": sum(1 for r in oth if r["nhip"]["exit_bar"] is not None
                                                          and r["nhip"]["exit_bar"] != int(ref[r["cum"]]["exit_bar"])),
           "n_X14_HOAN": len(rows) - len(ev), "con_lai_cung_phut": same, "con_lai_n": len(oth),
           "dmin_lech": [(r["cum"], r["dmin"]) for r in ev if r["dmin"] != 0][:20],
           "px_bad": [r for r in ev if not r["px_ok"]][:20], "dstop_tick_max": max((abs(r["dstop_tick"]) for r in ev
                                                                                     if r.get("dstop_tick") is not None), default=None),
           "gia_khop_san_gia_BAO_CAO": {"mean": sum(dl) / len(dl) if dl else None, "min": min(dl) if dl else None},
           "mismatch": mism[:20], "ref_exited_not_replay": ref_exited_not_rep[:20],
           "reason_diff_1leg": [r for r in one if r["reason"][0] != r["reason"][1]][:20], "open_end_replay": len(rep_open),
           "ok_reason": reason_ok, "ok_phut": ok_min, "ok_gia": ok_px, "ok_nhan": ok_lab}
    good = reason_ok and ok_min and ok_px and ok_lab and len(ev) > 0
    if len(ev) < 10 or kinds.get("TIME_STOP", 0) < 1 or kinds.get("TRAIL", 0) < 1:
        det["danh_gia_tam"] = good
        return NS, det
    return (PASS if good else FAIL), det


# ------------------------------------------------------------------ D1 (ERRATA1: dieu kien thi truong + p15 + C_eff)
def dca_rows(legs):
    return [x for x in legs if x["level"] == "DCA_LEVEL1" and x["outcome"] == "SUBMITTED"]


def ref_market(refdir):
    return {int(x["b"]): x for x in rd(refdir + "/ref_market.csv")}


def dca_leg_checks(x, mref, env, E, C3):
    """1 leg DCA replay: phut co dieu kien thi truong (REF: BIG_DOWN hoac isDcaAlt, universe A1) + p15 >= MIN_MOMENTUM_15M
    (REF) + budget = cong thuc voi C_eff_REF (<= 1e-5) + E (<= 1e-6)."""
    b = int(x["decision_ts"])
    r = mref.get(b)
    P = p_for(env, C3, "on")
    cond = bool(r) and r["big_a1"] != "" and (r["big_a1"] == "1" or r["alt_a1"] == "1")
    p15ok = bool(r) and float(r["p15"]) >= float(P["MOM"])
    e = E.get(x["cid"]) or {}
    cap = e.get("ceff") if e.get("ceff") is not None else C3
    used = e.get("used_ref")   # [ERRATA3 E10] U doc lap
    bref = R.budget(p_for(env, cap, "on"), used, int(x["leg_idx"])) if used is not None else None
    brel = abs(float(x["budget"]) - float(bref)) / float(x["budget"]) if bref is not None else 1.0
    uabs = abs(e["u_ref"] - e["u_jar"]) if (e.get("u_ref") is not None and e.get("u_jar") is not None) else 1.0
    erel = abs(e["e_ref"] - e["eq"]) / abs(e["e_ref"]) if e.get("eq") is not None and e.get("e_ref") is not None else 1.0
    return {"b": b, "sym": x["symbol"], "legIdx": int(x["leg_idx"]), "dieu_kien_tt": cond, "p15_ok": p15ok,
            "tt": None if not r else {"big": r["big_a1"], "alt": r["alt_a1"], "p15": r["p15"], "dip": r["dip"]},
            "budget_rel": brel, "E_rel": erel, "U_abs": uabs, "eq_at_khop": e.get("at") == e.get("at_ref"),
            "ok": cond and p15ok and brel <= 1e-5 and erel <= 1e-6 and uabs <= 1e-6 and e.get("at") == e.get("at_ref")}


def d1_natural(L, refdir, env, E):
    mref = ref_market(refdir)
    C3 = c3cap(L)
    rep = [(int(x["decision_ts"]), x["symbol"], int(x["leg_idx"])) for x in dca_rows(L["legs"])]
    ref = [(int(x["decision_ts"]), x["symbol"], int(x["leg_idx"])) for x in rd(refdir + "/ref_legs.csv")
           if x["level"] == "DCA_LEVEL1" and x["outcome"] == "SUBMITTED"]
    chk = [dca_leg_checks(x, mref, env, E, C3) for x in dca_rows(L["legs"])]
    det = {"replay": rep[:20], "ref": ref[:20], "leg_checks": chk[:20]}
    if not rep and not ref:
        return NA, det
    return (PASS if sorted(rep) == sorted(ref) and all(c["ok"] for c in chk) else FAIL), det


def d1_sdca(L, refdir, env, meta, E):
    if L["res"] is None:
        return FAIL, {"loi": "khong co result.json"}
    inj = L["res"].get("injections", {})
    syms = list((inj.get("sdca_start") or {}).keys())
    refsum = ref_summary(refdir)
    ref_syms = list((refsum.get("sdca_start") or {}).keys())
    reflegs = rd(refdir + "/ref_legs.csv")
    mref = ref_market(refdir)
    C3 = c3cap(L)
    st = int(inj.get("sdca_st", -1))
    design = [st + 3 * 60000, st + 12 * 60000, st + 22 * 60000] if st > 0 else None
    det = {"sdca_replay": inj.get("sdca_start"), "sdca_ref": refsum.get("sdca_start"), "st": st,
           "thiet_ke_phut_DCA(st+3,+12,+22)": design, "dip_ref": (refsum.get("sdca_synth") or {}).get("dip"),
           "p15_zero_ref": (refsum.get("sdca_synth") or {}).get("p15_zero"), "clusters": {}}
    ok = len(syms) >= 2 and sorted(syms) == sorted(ref_syms)
    full = 0
    first_buy = {}
    for f in L["fills"]:
        if f["side"] == "BUY" and f["symbol"] in syms and f["symbol"] not in first_buy:
            first_buy[f["symbol"]] = float(f["price"])
    for s in syms:
        sts = int(inj["sdca_start"][s])
        dl = [x for x in L["legs"] if x["symbol"] == s and x["outcome"] == "SUBMITTED" and x["level"] == "DCA_LEVEL1"
              and int(x["decision_ts"]) >= sts - 60000]
        idx = [int(x["leg_idx"]) for x in dl]
        mins = [int(x["decision_ts"]) for x in dl]
        rmins = [int(x["decision_ts"]) for x in reflegs if x["symbol"] == s and x["level"] == "DCA_LEVEL1" and x["outcome"] == "SUBMITTED"]
        chk = [dca_leg_checks(x, mref, env, E, C3) for x in dl]
        pre = []
        for x in dl:
            li = int(x["leg_idx"])
            fb = first_buy.get(s)
            drop = float(R.F(R.F(float(x["ref_px"])) / R.F(fb)) - R.F(1)) if fb else None
            if drop is None or drop > float(R.LEVELS[li - 1]):
                pre.append((x["decision_ts"], li, drop))
        no5 = len([x for x in L["legs"] if x["symbol"] == s and x["outcome"] == "SUBMITTED" and x["level"] == "DCA_LEVEL1"
                   and int(x["leg_idx"]) >= 4]) == 0
        c_ok = idx == [1, 2, 3] and mins == rmins and all(c["ok"] for c in chk) and not pre and no5
        full += c_ok
        det["clusters"][s] = {"leg_idx": idx, "minutes": mins, "ref_minutes": rmins, "khop_thiet_ke": mins == design,
                              "leg_checks": chk, "leg_before_level": pre, "no_5th": no5, "ok": c_ok}
    ok = ok and full >= 2
    return (PASS if ok else FAIL), det


def mkt_compare(L, refdir):
    """BAO CAO: co dieu kien thi truong moi phut - rig (vong live, ham production) vs REF (cong thuc sim, universe A1)."""
    mref = ref_market(refdir)
    n = nd = 0
    diff = []
    for x in L["market"]:
        b = int(x["b"])
        r = mref.get(b)
        if r is None or r["big_a1"] == "":
            continue
        n += 1
        a = (x["big"], x["alt"])
        bb = (r["big_a1"], r["alt_a1"])
        if a != bb:
            nd += 1
            if len(diff) < 15:
                diff.append({"b": b, "rig(big,alt,down,down15)": (x["big"], x["alt"], x["down"], x["down15"]),
                             "ref": (r["big_a1"], r["alt_a1"], r["down_a1"], r["down15_a1"])})
    return {"phut_so": n, "phut_lech_co": nd, "rig_big": sum(1 for x in L["market"] if x["big"] == "1"),
            "rig_alt": sum(1 for x in L["market"] if x["alt"] == "1"),
            "ref_big": sum(1 for r in mref.values() if r["big_a1"] == "1"), "ref_alt": sum(1 for r in mref.values() if r["alt_a1"] == "1"),
            "lech": diff}


def n8_report(L):
    """ERRATA2 E8/N8: liet ke key config.properties replay (khong co mac dinh JAR) tu result.json + nguon gia tri."""
    res = L["res"] or {}
    cp = res.get("config_properties_replay") or {}
    return {"keys": cp, "n": len(cp), "nhan": dict(collections.Counter(v.split("]")[0] + "]" for v in cp.values())),
            "DIED_SYMBOLS": cp.get("DIED_SYMBOLS"), "died_symbols_jar": (res.get("market") or {}).get("died_symbols_jar"),
            "ghi_chu": "DIED_SYMBOLS khong co trong danh sach trang env 242 (key config.properties, khong phai env) => gia tri 242 "
                       "theo AUDIT_GOLIVE_1116_D #24; A1 xac nhan"}


def n10_report(L, refdir):
    """ERRATA2 E8/N10: eq_at REF (mo hinh cache 60 s, ref_legs.csv) vs eq_at jar (legs.csv) cho leg SUBMITTED cung (phut, symbol, legIdx)."""
    ref = {(x["decision_ts"], x["symbol"], x["leg_idx"]): x.get("eq_at", "") for x in rd(refdir + "/ref_legs.csv")
           if x["outcome"] == "SUBMITTED"}
    n = same = 0
    diff = []
    for x in L["legs"]:
        if x["outcome"] != "SUBMITTED":
            continue
        r = ref.get((x["decision_ts"], x["symbol"], x["leg_idx"] or "0"))
        if r is None:
            continue
        n += 1
        if str(r) == str(x.get("eq_at", "")):
            same += 1
        elif len(diff) < 10:
            diff.append((x["decision_ts"], x["symbol"], r, x.get("eq_at")))
    return {"leg_so": n, "eq_at_trung": same, "lech": diff}


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
# Tap nhan KHAI TRUOC (prereg muc 5 E2 + ERRATA1 / ERRATA3 E9). Nhan ngoai tap => TU CHOI file nhan (E2 FAIL).
E2_LABELS = ("LEGACY-11-05", "JAR-R4Q-FIN2-BIGDOWN-SEL", "JAR-R4Q-FIN2-UNIVERSE-A1", "EXCHANGEINFO")
LABELS_HEADER = ["symbol", "label", "nguon"]


def labels_check(path):
    """[ERRATA3 E9] tools/e2e/labels_1105.csv: header DUNG symbol,label,nguon; moi nhan thuoc E2_LABELS; LEGACY-11-05 phai co
    nguon (dong log chi ra danh sach LEGACY doi trong ngay); symbol khong trung. File thieu / sai => TU CHOI.
    Tra (ok, {symbol: label}, chi_tiet)."""
    import hashlib
    det = {"file": path, "md5": None, "loi": []}
    if not path or not os.path.isfile(path):
        det["loi"].append("khong co file nhan (phai commit TRUOC luot chinh thuc, co the rong)")
        return False, {}, det
    det["md5"] = hashlib.md5(open(path, "rb").read()).hexdigest()
    with open(path) as fh:
        r = csv.reader(fh)
        head = next(r, None)
        rows = [x for x in r if any(z.strip() for z in x)]
    if head != LABELS_HEADER:
        det["loi"].append("header %s != %s" % (head, LABELS_HEADER))
    labels = {}
    for i, x in enumerate(rows, 2):
        if len(x) != 3:
            det["loi"].append("dong %d: %d cot" % (i, len(x)))
            continue
        sym, lab, src = (z.strip() for z in x)
        if not sym:
            det["loi"].append("dong %d: thieu symbol" % i)
        if lab not in E2_LABELS:
            det["loi"].append("dong %d: nhan '%s' KHONG thuoc tap khai truoc %s" % (i, lab, list(E2_LABELS)))
        if lab == "LEGACY-11-05" and not src:
            det["loi"].append("dong %d: LEGACY-11-05 thieu nguon (dong log)" % i)
        if sym in labels:
            det["loi"].append("dong %d: symbol %s trung" % (i, sym))
        labels[sym] = lab
    det["n"] = len(rows)
    return not det["loi"], labels, det


def e2_core(Lold, real, labels):
    """So SUBMIT R-OLD voi SUBMIT dry that (real); nhan da qua labels_check."""
    rep = {(x["symbol"], int(x["decision_ts"])): x for x in Lold["legs"] if x["outcome"] == "SUBMITTED"}
    match, unl = 0, []
    for x in real:
        k = (x["symbol"], int(x["decision_ts"]))
        y = rep.get(k)
        if y is not None and abs(float(y["budget"]) - float(x["budget"])) / float(x["budget"]) <= 1e-4:
            match += 1
        elif labels.get(x["symbol"]) not in E2_LABELS:
            unl.append(("thieu/lech", k))
    realk = {(x["symbol"], int(x["decision_ts"])) for x in real}
    lo, hi = min(k[1] for k in realk), max(k[1] for k in realk)
    for k in rep:
        if lo <= k[1] <= hi and k not in realk and labels.get(k[0]) not in E2_LABELS:
            unl.append(("thua", k))
    det = {"n_real": len(real), "match": match, "unlabeled": unl[:30]}
    return (PASS if match >= 20 and not unl else FAIL), det


def e2(Lold, fx, dry_csv, labels_csv):
    lok, labels, ldet = labels_check(labels_csv)
    man = json.load(open(fx + "/manifest.json"))
    leg = (Lold.get("res") or {}).get("legacy_E9") or {}
    legs = {"jar_n": leg.get("jar_n"), "jar_excludeLegacyHeld": leg.get("jar_excludeLegacyHeld"),
            "jar_file_md5": leg.get("jar_file_md5"),
            "nguon": {k: (leg.get("nguon") or {}).get(k) for k in ("source", "source_md5", "line", "line_ms", "n",
                                                                   "n_doi_trong_cua_so", "doi_trong_cua_so")}}
    if man["START"] != T1105:
        return NAPPLY, {"ly_do": "chi ap dung fixture 11-05 (fixture hien tai START=%s)" % man["START"], "nhan": ldet,
                        "nhan_ok": lok, "legacy_E9": legs}
    if not lok:
        return FAIL, {"loi": "file nhan bi TU CHOI (ERRATA3 E9)", "nhan": ldet}
    if not leg.get("jar_excludeLegacyHeld") or not leg.get("jar_n"):
        return FAIL, {"loi": "R-OLD khong chay voi C3_EXCLUDE_LEGACY_HELD=true + danh sach LEGACY (ERRATA3 E9)", "legacy_E9": legs}
    # prereg muc 5 E2: "log dry that ngay 11-05, 23 SUBMIT 22:52-22:53" => chi SUBMIT co phut quyet dinh < 11-06 07:00 +07
    real = [x for x in rd(dry_csv) if int(x["decision_ts"]) < T1105 + 86400000]
    if not real:
        return FAIL, {"loi": "khong co SUBMIT dry that 11-05 trong %s" % dry_csv}
    st, det = e2_core(Lold, real, labels)
    det["nhan"] = ldet
    det["legacy_E9"] = legs
    return st, det


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
    out = run_checks(a.runs, a.ref, a.fx, a.env, a.dry_1105, a.labels_1105)
    js = json.dumps(out, indent=1, default=str, ensure_ascii=False)
    if a.out:
        open(a.out, "w").write(js)
    for k, v in out.items():
        print("%-28s %s" % (k, v[0]))
    print(js[:30000])


def _md5(p):
    import hashlib
    return hashlib.md5(open(p, "rb").read()).hexdigest() if p and os.path.isfile(p) else None


def run_checks(runs, refroot, fx, envf, dry_1105="", labels_1105=""):
    env = R.load_env(envf)
    meta, _ = R.load_exinfo(fx + "/exinfo.json")
    fxo = FX(fx)
    Ls = {n: lane(runs, n) for n in ["R0", "R0-DRY", "R-OLD", "S-DCA", "FIN-INJ", "R-1000", "R-4000", "S-TS"]}
    rf = lambda n: os.path.join(refroot, n)  # noqa: E731
    E = {n: e_rows(Ls[n], rf(n), fxo) for n in ("R0", "R0-DRY", "S-DCA", "S-TS") if Ls[n]["res"] is not None}
    out = collections.OrderedDict()
    lanes_c1 = FLAG_ON_LANES + (["S-TS"] if Ls["S-TS"]["res"] is not None else [])
    c1s = {n: c1(Ls[n]) for n in lanes_c1 if Ls[n]["res"] is not None or os.path.isdir(Ls[n]["dir"])}
    out["C1"] = (PASS if c1s and all(v[0] == PASS for v in c1s.values()) else FAIL, c1s)
    for n in ("R0", "R0-DRY"):
        out["E1[%s]" % n] = e1(Ls[n], rf(n))
        out["S1[%s]" % n] = s1(Ls[n], env, meta, E.get(n, {}))
        out["K1[%s]" % n] = k1(Ls[n])
    out["D1[tu nhien R0]"] = d1_natural(Ls["R0"], rf("R0"), env, E.get("R0", {}))
    out["D1[S-DCA]"] = d1_sdca(Ls["S-DCA"], rf("S-DCA"), env, meta, E.get("S-DCA", {}))
    out["X1[R0]"] = x1(Ls["R0"], rf("R0"), meta, fxo)
    if Ls["S-TS"]["res"] is not None:
        out["X1[S-TS DEV tong hop]"] = x1(Ls["S-TS"], rf("S-TS"), meta, fxo)
        out["S1[S-TS DEV]"] = s1(Ls["S-TS"], env, meta, E.get("S-TS", {}))
    out["S1[S-DCA]"] = s1(Ls["S-DCA"], env, meta, E.get("S-DCA", {}))
    out["F1[FIN-INJ]"] = f1(Ls["FIN-INJ"], Ls["R0"], rf("FIN-INJ"))
    out["E2[R-OLD]"] = e2(Ls["R-OLD"], fx, dry_1105, labels_1105)
    out["MKT[R0] rig vs REF"] = ("BAO CAO", mkt_compare(Ls["R0"], rf("R0")))
    out["N7 REF universe A1 vs khong loc"] = ("BAO CAO", {n: (ref_summary(rf(n)).get("market") or {}) for n in ("R0", "S-DCA")})
    out["N8 key config khong mac dinh JAR"] = ("BAO CAO", n8_report(Ls["R0"]))
    out["N10 eq_at REF(cache 60 s) vs jar"] = ("BAO CAO", {n: n10_report(Ls[n], rf(n)) for n in ("R0", "S-DCA", "S-TS")
                                                           if Ls[n]["res"] is not None})
    out["R-OLD banners (ky vong TAT)"] = ("BAO CAO", {k: bool(re.search(p, Ls["R-OLD"]["log"])) for k, p in BANNERS.items()})
    out["VON_MICRO_6"] = ("BAO CAO", micro(Ls["R0"], env, meta, Ls["R-1000"], Ls["R-4000"]))
    out["INPUT md5 (ERRATA3 E11)"] = ("BAO CAO", {"env242_file": envf, "env242_md5": _md5(envf),
                                                  "labels_1105": labels_1105, "labels_1105_md5": _md5(labels_1105),
                                                  "result_json_env242_md5": {n: (Ls[n]["res"] or {}).get("env242_file_md5") for n in Ls},
                                                  "result_json_labels_md5": {n: (Ls[n]["res"] or {}).get("labels_1105_md5") for n in Ls}})
    out["errata/khoa"] = ("BAO CAO", {n: {"errata_mo_lai": (Ls[n]["res"] or {}).get("errata_mo_lai"),
                                          "official_lock": (Ls[n]["res"] or {}).get("official_lock")} for n in ("R0",)})
    keys = ["C1", "E1[R0]", "E1[R0-DRY]", "S1[R0]", "S1[R0-DRY]", "D1[S-DCA]", "X1[R0]", "F1[FIN-INJ]", "K1[R0]", "K1[R0-DRY]",
            "E2[R-OLD]"]
    # ERRATA1 E5: D1 tu nhien vao ket luan (co DCA tu nhien => phai PASS; khong co => KHONG XAY RA, S-DCA quyet dinh)
    concl = PASS if (all(out[k][0] == PASS for k in keys) and out["D1[tu nhien R0]"][0] in (PASS, NA)) else FAIL
    out["KET LUAN (iii)"] = (concl, "PASS <=> moi tieu chi PASS + D1 tu nhien PASS/KHONG XAY RA (KHONG DU MAU / CHUA AP DUNG != PASS)")
    return out


if __name__ == "__main__":
    main()
