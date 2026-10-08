#!/usr/bin/env python3
"""NSEL_JD (2026-10-08): kiem khop noi J-D vong NSEL (PREREG_NSEL 9986c929 §3) -- CHI phan tich output co san.

0 sim, 0 Kaggle, 0 Java, 0 cham 242/shadow. KHONG mo nsel-nen-* / nsel-m1-* / nsel-m2-* (assert ten run).
Luat (chot o pre-reg, khong doi): M0 (2 tang, khong CORE_ADD, khong F1, penalty 0) seed 42/7/21 vs D
(gkf-l2-k32 / gkf2-l2k32-s7 / -s21):
  (a) n/nam 2022-25 (chan printDone, moi loai, theo nam entry): ti le M0/D trong [0,90; 1,10] ca 3 seed;
  (b) J3 M0 vs nen cung seed (gqsf-a1/s7/s21): ti le chan MAT (cua so entry 2022-25, khop 1-1 tol 1 khoa sym)
      co nguyen nhan '2_giu_symbol' >= 80% ca 3 seed. Dinh nghia + thu tu code = nsel_p0_data (0c68609c), IMPORT
      truc tiep (load/logscan/attach/match/Book/j3/eqh), khong viet lai.
  Gate offline (nguyen nhan 4/5, SAU 'giu symbol') cua M0: chay 2 bien the -- (i) bang gate rong (4+5 gop thanh
  '5_offline_khong_thay_o'), (ii) bang gate cua D cung seed (chi khi md5 printDone M0 == D: cung duong arm).
  Ti le '2_giu_symbol' KHONG phu thuoc gate (gate xet sau) -> 2 bien the phai cho cung so (tu kiem).
Bao cao them (khong vao luat): parity (jar/override/pred md5/[NSEL] on=/counter cuoi run), phan ra chan theo tang
  tu NSEL_LEG, core_on_held_by_add_would, Jaccard tap chan M0 vs D (khop 1-1 tol 1 khoa sym).
Cache moi: ~/claude_master/1008/nsel/jd_cache/ (eqh M0 tai lap bang P.eqh, cung px_hour.npz va so gio nhu D).
Usage: python3 research/analysis/nsel_jd.py
"""
import hashlib
import json
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import nsel_p0_data as P  # noqa: E402

log = logging.getLogger("nsel_jd")
OUT, W = P.OUT, P.W
JDW = W + "/jd_cache"
JSON_OUT = REPO + "/docs/result/NSEL_JD_20261008.json"
MD_OUT = REPO + "/docs/result/NSEL_JD_20261008.md"
SEEDS, NEN, YEARS = P.SEEDS, P.NEN, P.YEARS
M0 = {"S42": "nsel-m0-s42", "S7": "nsel-m0-s7", "S21": "nsel-m0-s21"}
D = P.ARMS["D"][2]
K_D = P.ARMS["D"][0]                 # 32 = K_THEM = pool topK cua M0 = K arm D (luat topK cua j3)
JAR_M0 = "b7c89f09"
N_LO, N_HI, HOLD_MIN = 0.90, 1.10, 80.0
FORBID = ("nsel-nen-", "nsel-m1-", "nsel-m2-")
EXP_OV = dict(SIM_GATE_ROLLING_MODE="ratio", SIM_GATE_ROLLING_DAYS=90, SIM_GATE_ROLLING_PCT=0.999950829,
              TS_GIVEBACK_RATIO=1.0, SIM_TS_MAX_GAP=0.03, SIM_TS_MAX_GAP_WEAK=0.03, SELECTOR_RANK_TOPK=24,
              GATE_QUOTA_SKIP_WHEN_FULL="true", NSEL_ADD_ENABLED="true", NSEL_ADD_TOPK=32,
              SIM_NSEL_ADD_ROLLING_PCT=0.999915, SIM_NSEL_ADD_ROLLING_DAYS=90)
RX_ON = re.compile(r"\[NSEL\] on=.*$")
RX_BAT = re.compile(r"\[NSEL\] BAT tang THEM: (.*?) \*\*\*")
RX_LEG = re.compile(r"NSEL_LEG sym=(\S+?)USDT tOpen=\S+ \S+ tMs=(\d+) type=(\S+) tier=(\d+) rank=(\S+)")
LTMAP = {"PREDICT_SYMBOL_TRADE": "PRED", "BIG_DOWN": "BIGD"}
GCOLS = ["has", "col", "lock", "full", "would_run", "P_run", "in_run", "would_b", "P_b", "in_b"]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def same_val(a, b):
    try:
        return abs(float(a) - float(b)) < 1e-12
    except (TypeError, ValueError):
        return str(a).strip().lower() == str(b).strip().lower()


def simlog(tag):
    """log kernel (sim-<tag>.log, JSON stream): overrides, PRED_MD5_USED, pred_ds."""
    ov = pm = pds = None
    with open(OUT + tag + "/sim-%s.log" % tag, errors="ignore") as f:
        for ln in f:
            try:
                s = json.loads(ln.strip().lstrip("[,").rstrip("]"))["data"]
            except Exception:
                continue
            m = re.search(r"overrides=(\{.*\})", s)
            if m and ov is None:
                ov = json.loads(m.group(1))
            m = re.search(r"PRED_MD5_USED=([0-9a-f]{32})", s)
            if m:
                pm = m.group(1)
            m = re.search(r"pred_ds=(\S+)", s)
            if m:
                pds = m.group(1)
    return ov, pm, pds


def fullscan(tag):
    """full.log M0: NSEL_LEG (sym, phut UTC, type, tier, rank), dong [NSEL] on= cuoi, dong BAT, dong CRASH-PENALTY."""
    legs, on, bat, cp = [], None, None, []
    with open(OUT + tag + "/logs/full.log", errors="ignore") as f:
        for ln in f:
            m = RX_LEG.search(ln)
            if m:
                legs.append((m.group(1), int(m.group(2)) // 60000, m.group(3), int(m.group(4)), m.group(5)))
                continue
            m = RX_ON.search(ln)
            if m:
                on = m.group(0).strip()
            m = RX_BAT.search(ln)
            if m:
                bat = m.group(1)
            if "CRASH-PENALTY" in ln or "CRASH_ENTRY_PENALTY" in ln:
                cp.append(ln.strip()[-200:])
    return pd.DataFrame(legs, columns=["sym", "m0", "type", "tier", "rank"]), on, bat, cp


def parse_on(s):
    """'[NSEL] on=true k=v ... legs={A:B=n, ...}' -> (kv, legs)."""
    if not s:
        return {}, {}
    head, _, tail = s.partition(" legs=")
    kv = dict(re.findall(r"(\w+)=([^\s{]+)", head))
    lg = {k: int(v) for k, v in re.findall(r"([A-Z_0-9]+:[A-Z]+)=(\d+)", tail)}
    return kv, lg


def nyear(d):
    c = d["year"].value_counts()
    return {int(y): int(c.get(y, 0)) for y in YEARS}


def tier_join(d, legs, lg):
    """gan tang cho chan printDone tu NSEL_LEG (khop (sym, m0, loai)); ten tang xac dinh bang counter legs=."""
    lg2 = legs.assign(lt=legs["type"].map(LTMAP).fillna("DCA"))
    k = lg2.drop_duplicates(["sym", "m0", "lt"])
    x = d[["sym", "m0", "lt"]].merge(k[["sym", "m0", "lt", "tier"]], on=["sym", "m0", "lt"], how="left")
    pr = lg2[lg2["lt"] == "PRED"]
    name = {}
    for t, c in pr["tier"].value_counts().items():
        hit = [kk.split(":")[1] for kk, v in lg.items() if kk.startswith("PREDICT_SYMBOL_TRADE:") and v == c]
        name[int(t)] = hit[0] if len(hit) == 1 else "tier%d" % t
    for t in lg2["tier"].unique():
        name.setdefault(int(t), "tier%d" % t)
    lab = x["tier"].map(lambda v: name.get(int(v), "?") if np.isfinite(v) else "NA").to_numpy()
    meta = dict(n_leg_log=int(len(legs)), n_leg_dupkey=int(len(lg2) - len(k)), join_rate=float(np.mean(lab != "NA")),
                tier_name={str(a): b for a, b in name.items()},
                pred_tier_counts={str(int(a)): int(b) for a, b in pr["tier"].value_counts().items()})
    return lab, meta


def hold_tier(mm, a, lab):
    """MAT '2_giu_symbol' (cua so 22-25): cum arm dang giu coin luc nen vao (cung cach hold_detail) -> tang leg0 cum do."""
    h = mm[(mm["cause"] == "2_giu_symbol") & P.win(mm)]
    l0 = a["leg0"].to_numpy()
    t0 = pd.Series(lab[l0], index=a.loc[l0, "pid"].to_numpy())
    x = h[["sym", "m0"]].reset_index().merge(a[["sym", "m0", "m1", "pid"]], on="sym", suffixes=("", "_a"))
    x = x[(x["m0_a"] <= x["m0"]) & (x["m1"] > x["m0"])].sort_values("m0_a").drop_duplicates("index", keep="last")
    v = pd.Series(t0.reindex(x["pid"]).to_numpy()).value_counts()
    return dict(n_hold=int(len(h)), n_found=int(len(x)), leg0_tier={str(k): int(c) for k, c in v.items()})


def null_gate():
    return pd.DataFrame({c: pd.Series(dtype=object) for c in GCOLS}).rename_axis("row")


def jcause(r):
    c = r["cause"]
    tot = r["total"]["n"]
    g = c.get("2_giu_symbol", {}).get("n", 0)
    g2 = g + c.get("2_giu_symbol_khac_cum", {}).get("n", 0)
    return dict(n_mat=tot, n_hold=g, hold_pct=100.0 * g / max(1, tot), hold_incl_dca_pct=100.0 * g2 / max(1, tot),
                cause={k: dict(n=v["n"], share=v["share"], pnl_s=v["pnl_s"], roi_s=v["roi_s"]) for k, v in c.items()},
                sum_ok=r["check"]["sum_ok"], hold_detail=r.get("hold_detail"))


def load_all():
    tags = list(M0.values()) + list(D.values()) + list(NEN.values())
    for t in tags:
        assert not t.startswith(FORBID), t
    bar = json.load(open(P.NDEEP_BAR))["bar"]
    L, SEL, PAR, LEGS = {}, {}, {}, {}
    for t in tags:
        d, meta = P.load(t)
        sel, _, _ = P.logscan(t)
        am = P.attach(d, sel, bar)
        L[t], SEL[t] = d, sel
        rj = json.load(open(OUT + t + "/result.json"))
        ov, pm, pds = simlog(t)
        PAR[t] = dict(md5_printDone=md5f(OUT + t + "/storage/printDone.csv"), jar=rj["jar_sha256"], n_trades=rj["n_trades"],
                      n=meta["n"], n_raw=meta["n_raw"], equity_final=rj["equity_final"], date_last=rj["date_last"],
                      overrides=ov, pred_md5=pm, pred_ds=pds, attach=am, n_selrank=int(len(sel)))
        if t in M0.values():
            legs, on, bat, cp = fullscan(t)
            kv, lg = parse_on(on)
            LEGS[t] = legs
            PAR[t].update(nsel_on_line=on, nsel_bat=bat, crash_penalty_lines=cp[-3:], n_crash_penalty_lines=len(cp),
                          nsel_kv=kv, nsel_legs=lg, n_nsel_leg=int(len(legs)))
        log.info("LOAD %-16s n=%d md5=%s jar=%s pred=%s sel=%d", t, meta["n"], PAR[t]["md5_printDone"][:8],
                 PAR[t]["jar"][:8], pm, len(sel))
    del bar
    return L, SEL, PAR, LEGS


def parity(PAR):
    """1. parity 3 run M0: jar, override, pred md5 (== nen/D cung seed), [NSEL] on=, counter cuoi run."""
    out, ok = {}, True
    ov0 = PAR[M0["S42"]]["overrides"] or {}
    for s in SEEDS:
        p = PAR[M0[s]]
        ov = p["overrides"] or {}
        kv, lg = p["nsel_kv"], p["nsel_legs"]
        c = dict(jar=p["jar"].startswith(JAR_M0),
                 ov_expected=set(ov) == set(EXP_OV) and all(same_val(ov[k], v) for k, v in EXP_OV.items()),
                 ov_same_s42=set(ov) == set(ov0) and all(same_val(ov[k], ov0[k]) for k in ov0),
                 no_coreadd_f1_pen_key=not any(("CORE_ADD" in k) or ("F1" in k) or ("PENALTY" in k) for k in ov),
                 pred_eq_nen=p["pred_md5"] == PAR[NEN[s]]["pred_md5"] and p["pred_ds"] == PAR[NEN[s]]["pred_ds"],
                 pred_eq_D=p["pred_md5"] == PAR[D[s]]["pred_md5"] and p["pred_ds"] == PAR[D[s]]["pred_ds"],
                 on_true=kv.get("on") == "true",
                 bat_coreadd_false=bool(p["nsel_bat"]) and "CORE_ADD=false" in p["nsel_bat"] and "F1=NaN" in p["nsel_bat"],
                 counter_coreadd_off=kv.get("core_add_on") == "false" and kv.get("core_add_done") == "0"
                 and kv.get("core_add_attempt") == "0" and kv.get("add_rej_f1") == "0",
                 counter_legs_eq_n=sum(lg.values()) == p["n"] == p["n_trades"],
                 counter_add_eq_legs=int(kv.get("add_leg_done", -1)) == lg.get("PREDICT_SYMBOL_TRADE:ADD", -2)
                 == int(kv.get("add_pass", -3)),
                 counter_core_eq_legs=int(kv.get("core_pass", -1)) == lg.get("PREDICT_SYMBOL_TRADE:CORE", -2),
                 nsel_leg_eq_n=p["n_nsel_leg"] == p["n"],
                 date_last=p["date_last"] == "20251230")
        out[s] = dict(checks=c, ok=all(c.values()), jar=p["jar"], pred_md5=p["pred_md5"], pred_ds=p["pred_ds"],
                      overrides=ov, nsel_bat=p["nsel_bat"], nsel_kv=kv, nsel_legs=lg,
                      crash_penalty_lines=p["crash_penalty_lines"], n_crash_penalty_lines=p["n_crash_penalty_lines"])
        ok &= out[s]["ok"]
    return out, bool(ok)


def eqh_m0(L):
    """tai lap equity moc gio cho M0 bang P.eqh (cung px_hour.npz, cung so gio nhu eqh D) vao jd_cache/."""
    os.makedirs(JDW, exist_ok=True)
    px = dict(np.load(W + "/px_hour.npz"))
    out = {}
    for s in SEEDS:
        t = M0[s]
        zd = np.load(W + "/eqh_%s.npz" % D[s])
        nH = len(zd["eq"])
        miss_sym = sorted(set(L[t]["sym"]) - set(px))
        P.W = JDW
        try:
            P.eqh(t, L[t], px, nH)
        finally:
            P.W = W
        z = np.load(JDW + "/eqh_%s.npz" % t)
        out[s] = dict(nH=nH, miss_sym=miss_sym, miss=int(z["miss"]),
                      maxabs_eq_vs_D=float(np.max(np.abs(z["eq"] - zd["eq"]))),
                      maxabs_mg_vs_D=float(np.max(np.abs(z["mg"] - zd["mg"]))))
        log.info("EQH-JD %s %s", t, out[s])
    del px
    return out


def book_m0(t, d):
    P.W = JDW
    try:
        return P.Book(t, d)
    finally:
        P.W = W


def run_j(L, SEL, PAR, LEGS):
    ref = json.load(open(REPO + "/docs/audit/NSEL_P0_DATA_20261008.json"))["j3"]
    NY, J3, X = {}, {}, {}
    for s in SEEDS:
        b, m, dd = L[NEN[s]], L[M0[s]], L[D[s]]
        ny_m, ny_d, ny_b = nyear(m), nyear(dd), nyear(b)
        sm, sd_ = sum(ny_m.values()), sum(ny_d.values())
        NY[s] = dict(M0=ny_m, D=ny_d, NEN=ny_b, M0_per_year=sm / 4.0, D_per_year=sd_ / 4.0, NEN_per_year=sum(ny_b.values()) / 4.0,
                     ratio=sm / sd_, ratio_year={y: ny_m[y] / max(1, ny_d[y]) for y in YEARS},
                     pass_=bool(N_LO <= sm / sd_ <= N_HI))
        same_path = PAR[M0[s]]["md5_printDone"] == PAR[D[s]]["md5_printDone"]
        # J3 M0 (i) gate rong; (ii) gate D (chi khi cung duong arm)
        b2a, a2b, _, _ = P.match(b, m, 1, False)
        bk = book_m0(M0[s], m)
        r0, mm = P.j3(b, m, b2a, bk, null_gate(), K_D, a2b)
        rD = None
        if same_path:
            rD, _ = P.j3(b, m, b2a, bk, P.gtab(D[s], NEN[s]), K_D, a2b)
        # J3 D tinh lai (tu kiem vs NSEL_P0_DATA json)
        b2d, d2b, _, _ = P.match(b, dd, 1, False)
        rd, _ = P.j3(b, dd, b2d, P.Book(D[s], dd), P.gtab(D[s], NEN[s]), K_D, d2b)
        refd = ref["D|%s" % s]["cause"].get("2_giu_symbol", {}).get("n")
        J3[s] = dict(M0=jcause(r0), M0_gateD=jcause(rD) if rD else None, D=jcause(rd), D_ref_p0_n_hold=refd,
                     D_ref_p0_n_mat=ref["D|%s" % s]["total"]["n"], same_path=same_path)
        J3[s]["selfcheck"] = dict(
            gate_indep=(rD is None) or (J3[s]["M0_gateD"]["n_hold"] == J3[s]["M0"]["n_hold"]),
            D_vs_p0=(J3[s]["D"]["n_hold"] == refd) and (J3[s]["D"]["n_mat"] == J3[s]["D_ref_p0_n_mat"]))
        J3[s]["pass_"] = bool(J3[s]["M0"]["hold_pct"] >= HOLD_MIN)
        X[s] = extras(s, m, dd, mm, PAR, SEL, LEGS)
        log.info("SEED %s NY %.3f J3 M0 %.2f%% D %.2f%% self %s", s, NY[s]["ratio"], J3[s]["M0"]["hold_pct"],
                 J3[s]["D"]["hold_pct"], J3[s]["selfcheck"])
    return NY, J3, X


def extras(s, m, dd, mm, PAR, SEL, LEGS):
    t = M0[s]
    kv = PAR[t]["nsel_kv"]
    lab, tmeta = tier_join(m, LEGS[t], PAR[t]["nsel_legs"])
    w = P.win(m)
    tb = pd.crosstab(m.loc[w, "lt"], pd.Series(lab[w], index=m.index[w], name="tier"))
    ty = pd.crosstab(m.loc[w & (m["lt"] == "PRED"), "year"], pd.Series(lab[w & (m["lt"] == "PRED").to_numpy()],
                     index=m.index[w & (m["lt"] == "PRED")], name="tier"))
    jac = {}
    for nm, msk_d, msk_m in (("all", np.ones(len(dd), bool), np.ones(len(m), bool)), ("w2225", P.win(dd), P.win(m))):
        d2m, m2d, _, _ = P.match(dd[msk_d].reset_index(drop=True), m[msk_m].reset_index(drop=True), 1, False)
        ch = int((d2m >= 0).sum())
        jac[nm] = dict(n_D=int(msk_d.sum()), n_M0=int(msk_m.sum()), chung=ch,
                       jaccard=ch / max(1, msk_d.sum() + msk_m.sum() - ch))
    sa = SEL[t].sort_values(["m0", "sym", "rank"]).reset_index(drop=True)
    sb = SEL[D[s]].sort_values(["m0", "sym", "rank"]).reset_index(drop=True)
    return dict(tier_meta=tmeta, legs_w2225_lt_x_tier={k: {kk: int(vv) for kk, vv in r.items()} for k, r in tb.to_dict("index").items()},
                pred_w2225_year_x_tier={int(k): {kk: int(vv) for kk, vv in r.items()} for k, r in ty.to_dict("index").items()},
                hold_mat_leg0_tier=hold_tier(mm, m, lab),
                core_on_held_would=int(kv.get("core_on_held_would", -1)),
                core_on_held_by_add_would=int(kv.get("core_on_held_by_add_would", -1)),
                core_pass=int(kv.get("core_pass", -1)), add_pass=int(kv.get("add_pass", -1)),
                add_bookfull=int(kv.get("add_bookfull", -1)), jaccard=jac,
                selrank_identical_D=bool(len(sa) == len(sb) and sa.equals(sb)),
                md5_eq_D=PAR[t]["md5_printDone"] == PAR[D[s]]["md5_printDone"])


def jd(o):
    if isinstance(o, (set, tuple)):
        return list(o)
    return P.jd(o)


def main():
    L, SEL, PAR, LEGS = load_all()
    PA, par_ok = parity(PAR)
    EQ = eqh_m0(L)
    NY, J3, X = run_j(L, SEL, PAR, LEGS)
    n_pass = all(NY[s]["pass_"] for s in SEEDS)
    h_pass = all(J3[s]["pass_"] for s in SEEDS)
    self_ok = all(all(J3[s]["selfcheck"].values()) for s in SEEDS) and all(J3[s]["M0"]["sum_ok"] for s in SEEDS)
    verdict = "PASS" if (n_pass and h_pass) else "FAIL"
    js = dict(title="NSEL_JD 2026-10-08", script="research/analysis/nsel_jd.py", prereg="docs/prereg/PREREG_NSEL.md 9986c929 §3 J-D",
              rule=dict(n_ratio=[N_LO, N_HI], hold_min_pct=HOLD_MIN, window="entry 2022-01-01..2025-12-31",
                        match="1-1 tol 1 phut khoa sym (nsel_p0_data.match)", cause="nsel_p0_data.j3 '2_giu_symbol'", topK=K_D),
              runs=dict(M0=M0, D=D, NEN=NEN), parity=PA, parity_ok=par_ok, eqh_m0=EQ,
              run_md5={t: PAR[t]["md5_printDone"] for t in PAR}, run_n={t: PAR[t]["n"] for t in PAR},
              attach={t: PAR[t]["attach"] for t in PAR},
              n_year=NY, n_pass=n_pass, j3=J3, hold_pass=h_pass, selfcheck_ok=self_ok, extras=X, verdict=verdict)
    os.makedirs(os.path.dirname(JSON_OUT), exist_ok=True)
    json.dump(js, open(JSON_OUT, "w"), default=jd, indent=1, ensure_ascii=False)
    log.info("ghi %s verdict %s (n %s, hold %s, parity %s, self %s)", JSON_OUT, verdict, n_pass, h_pass, par_ok, self_ok)
    write_md(js)


def f2(x, n=2):
    return "—" if x is None else ("%." + str(n) + "f") % x


def write_md(js):
    o = ["# NSEL J-D — M0 ≈ D (2026-10-08)", "",
         "Khớp nối J-D của PREREG_NSEL (9986c929 §3). Chỉ phân tích output Kaggle có sẵn: 0 sim, 0 Kaggle, 0 Java, 0 chạm 242/shadow; "
         "không mở nsel-nen-*/nsel-m1-*/nsel-m2-*. Script `research/analysis/nsel_jd.py` (import trực tiếp `nsel_p0_data` 0c68609c: "
         "load/logscan/attach/match/Book/j3/eqh). JSON `docs/result/NSEL_JD_20261008.json`.", "",
         "Luật (chốt trước): M0 seed 42/7/21 vs D (gkf-l2-k32 / gkf2-l2k32-s7 / -s21): (a) n/năm 2022–25 (chân printDone, mọi loại, "
         "theo năm entry) tỉ lệ M0/D ∈ [0,90; 1,10] cả 3 seed; (b) J3 M0 vs nền cùng seed (gqsf-a1/s7/s21): % chân MẤT (cửa sổ entry "
         "2022–25, khớp 1-1 tol 1 phút khoá sym) có nguyên nhân `2_giu_symbol` (thứ tự code nsel_p0_data.j3, topK = 32) ≥ 80% cả 3 seed.", "",
         "## Kết luận: J-D **%s** (n/năm %s, giữ symbol %s; parity %s; tự kiểm %s)" % (
             js["verdict"], "PASS" if js["n_pass"] else "FAIL", "PASS" if js["hold_pass"] else "FAIL",
             "OK" if js["parity_ok"] else "LỆCH", "OK" if js["selfcheck_ok"] else "LỆCH"), ""]
    o += ["## 1. Parity 3 run M0", "",
          "| seed | jar | pred md5 (pred_ds) | override = kỳ vọng / = s42 | không key CORE_ADD/F1/PENALTY | [NSEL] on / BAT | counter core/add/BD/DCA | n printDone = counter = NSEL_LEG | checks |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in SEEDS:
        p = js["parity"][s]
        c, lg = p["checks"], p["nsel_legs"]
        o.append("| %s | %s | %s (%s) | %s / %s | %s | on=%s · %s | %s/%s/%s/%s | %s | %s |" % (
            s, p["jar"][:8], (p["pred_md5"] or "")[:8] or "bundle mặc định", p["pred_ds"] or "—", c["ov_expected"], c["ov_same_s42"],
            c["no_coreadd_f1_pen_key"], p["nsel_kv"].get("on"), p["nsel_bat"], lg.get("PREDICT_SYMBOL_TRADE:CORE"),
            lg.get("PREDICT_SYMBOL_TRADE:ADD"), lg.get("BIG_DOWN:CORE"), lg.get("DCA_LEVEL1:CORE"),
            c["counter_legs_eq_n"] and c["nsel_leg_eq_n"], "PASS" if p["ok"] else "FAIL " + ",".join(k for k, v in c.items() if not v)))
    o += ["", "pred md5 M0 = nền = D cùng seed: " + ", ".join("%s %s/%s" % (s, js["parity"][s]["checks"]["pred_eq_nen"],
          js["parity"][s]["checks"]["pred_eq_D"]) for s in SEEDS) + ". Dòng CRASH-PENALTY trong full.log M0: " +
          ", ".join("%s %d" % (s, js["parity"][s]["n_crash_penalty_lines"]) for s in SEEDS) + ".", ""]
    return write_md2(js, o)


def write_md2(js, o):
    o += ["## 2. n/năm 2022–25 (chân, mọi loại)", "",
          "| seed | M0 n 2022/23/24/25 | D n 2022/23/24/25 | n/năm M0 | n/năm D | M0/D | M0/D theo năm | nền n/năm | [0,90;1,10] |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in SEEDS:
        r = js["n_year"][s]
        o.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            s, "/".join(str(r["M0"][y]) for y in YEARS), "/".join(str(r["D"][y]) for y in YEARS), f2(r["M0_per_year"], 1),
            f2(r["D_per_year"], 1), f2(r["ratio"], 4), "/".join(f2(r["ratio_year"][y], 3) for y in YEARS),
            f2(r["NEN_per_year"], 1), "PASS" if r["pass_"] else "FAIL"))
    o += ["", "## 3. J3 — chân nền MẤT do giữ symbol (cửa sổ entry 2022–25)", "",
          "| seed | MẤT M0 | giữ symbol M0 n (%) | +DCA khác cụm % | MẤT D | giữ symbol D n (%) | D theo NSEL_P0 (n giữ/MẤT) | tự kiểm gate-độc-lập / D=P0 | ≥80% |",
          "|---|---|---|---|---|---|---|---|---|"]
    for s in SEEDS:
        r = js["j3"][s]
        m, d = r["M0"], r["D"]
        o.append("| %s | %d | %d (%s) | %s | %d | %d (%s) | %s/%s | %s / %s | %s |" % (
            s, m["n_mat"], m["n_hold"], f2(m["hold_pct"]), f2(m["hold_incl_dca_pct"]), d["n_mat"], d["n_hold"], f2(d["hold_pct"]),
            r["D_ref_p0_n_hold"], r["D_ref_p0_n_mat"], r["selfcheck"]["gate_indep"], r["selfcheck"]["D_vs_p0"],
            "PASS" if r["pass_"] else "FAIL"))
    causes = sorted({c for s in SEEDS for c in js["j3"][s]["M0"]["cause"]})
    o += ["", "Nguyên nhân MẤT M0 (độc quyền, thứ tự code; gate rỗng ⇒ 4+5 gộp vào `5_offline_khong_thay_o`): n (%) · ΣPnL_S k · ROI_S %", "",
          "| nguyên nhân | S42 | S7 | S21 |", "|---|---|---|---|"]
    for c in causes:
        row = []
        for s in SEEDS:
            x = js["j3"][s]["M0"]["cause"].get(c)
            row.append("%d (%s) · %s · %s" % (x["n"], f2(x["share"], 1), f2(x["pnl_s"] / 1000, 1), f2(x["roi_s"])) if x else "0")
        o.append("| %s | %s |" % (c, " | ".join(row)))
    return write_md3(js, o)


def write_md3(js, o):
    X = js["extras"]
    o += ["", "## 4. Báo cáo thêm (không vào luật)", "",
          "| seed | chân 22–25 PRED LÕI/THÊM · BD · DCA | join NSEL_LEG | MẤT giữ-symbol: leg0 cụm M0 đang giữ LÕI/THÊM | core_on_held_by_add_would / core_on_held_would | add_bookfull | Jaccard M0∩D toàn run / 22–25 | md5 = D / SELRANK = D |",
          "|---|---|---|---|---|---|---|---|"]
    for s in SEEDS:
        x = X[s]
        t = x["legs_w2225_lt_x_tier"]
        ht = x["hold_mat_leg0_tier"]["leg0_tier"]
        o.append("| %s | %s/%s · %s · %s | %s | %s/%s (tìm %d/%d) | %d / %d | %d | %s / %s | %s / %s |" % (
            s, t.get("PRED", {}).get("CORE", 0), t.get("PRED", {}).get("ADD", 0), sum(t.get("BIGD", {}).values()),
            sum(t.get("DCA", {}).values()), f2(100 * x["tier_meta"]["join_rate"], 2), ht.get("CORE", 0), ht.get("ADD", 0),
            x["hold_mat_leg0_tier"]["n_found"], x["hold_mat_leg0_tier"]["n_hold"], x["core_on_held_by_add_would"],
            x["core_on_held_would"], x["add_bookfull"], f2(x["jaccard"]["all"]["jaccard"], 4), f2(x["jaccard"]["w2225"]["jaccard"], 4),
            x["md5_eq_D"], x["selrank_identical_D"]))
    o += ["", "PRED 22–25 theo năm (LÕI/THÊM): " + "; ".join("%s " % s + ", ".join(
        "%d %s/%s" % (y, v.get("CORE", 0), v.get("ADD", 0)) for y, v in sorted(X[s]["pred_w2225_year_x_tier"].items())) for s in SEEDS),
          "", "core_on_held_by_add_would / core_on_held_would = counter Java theo lượt ứng viên-phút (không phải số chân, không khử trùng "
          "lặp theo cụm); chỉ là cận trên thô cho phạm vi CORE_ADD ở M1. Tầng gán từ NSEL_LEG (tier) khớp (sym, phút, loại); "
          "tên LÕI/THÊM xác định bằng counter legs= cuối run.", ""]
    same = all(X[s]["md5_eq_D"] for s in SEEDS)
    o += ["## 5. Ghi chú", ""]
    if same:
        o += ["- printDone M0 **trùng byte** D cả 3 seed (md5 %s). Tỉ lệ n = 1,0000 và J3 M0 = J3 D là hệ quả trực tiếp; "
              "SELRANK cũng trùng. Nghĩa là trên đường thực tế, mọi chân tầng LÕI đều là chân D đã có (tầng THÊM = gate D: cùng quần thể "
              "hạng ≤ 32 khi sổ không đầy, pct 0,999915, DAYS 90) — tầng LÕI không sinh chân nào ngoài D. Đúng kỳ vọng thiết kế "
              "(M0 = LÕI ∪ THÊM, THÊM ≡ D), không phải dấu hiệu lỗi: NSEL_LEG/counter cho thấy 2 tầng thực sự chạy (LÕI/THÊM tách rõ)." %
              ", ".join(js["run_md5"][M0[s]][:8] for s in SEEDS),
              "- Hệ quả (chỉ ghi nhận, không đổi luật): khác biệt M1 vs M0 sẽ đến hoàn toàn từ CORE_ADD.", ""]
    if js["verdict"] == "FAIL":
        o += ["- FAIL ⇒ dừng theo pre-reg; chẩn đoán xem mục 2–4 (tầng nào sinh/mất chân so với D).", ""]
    with open(MD_OUT, "w") as f:
        f.write("\n".join(o) + "\n")
    log.info("ghi %s", MD_OUT)


if __name__ == "__main__":
    main()
