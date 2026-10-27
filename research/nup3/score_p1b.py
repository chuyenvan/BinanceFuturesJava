#!/usr/bin/env python3
"""NUP3b Pha 1 — cham theo PREREG_NUP3B.md (9b49f7a9, sha c544278c) + ADDENDUM_TECH (dd9a92fe).
Thuoc do/luat = PREREG_NUP3 §5-6 + dien giai MASTER (nhu NUP3 P1); equity tu 2021-07 GOM 2021H2 (ADDENDUM (c)), khong niem phong.
Ky cham DEV 2022-25, gan theo gio dong +07. S1x: so nen != B0 -> MTM rieng; x B0 = B0 cung seed.
Stage: check | map | mtm | score"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/nup3")
import score_p1 as P  # noqa: E402

M, Q, R = P.M, P.Q, P.R
KS = P.KS
WK = "/home/ubuntu/claude_master/nup3b_p1_wk"
OUTD = P.OUTD
ARMS = ["s0b", "s1b", "s1x"]
SIZE = {"s0b": 0.525, "s1b": 0.574, "s1x": 0.574}
SARM = {"s0b": "V0", "s1b": "V1", "s1x": "V1"}
SEEDS = P.SEEDS
JAR = "8aba4090bd39ec45853df68d5b5538d6c3edd324aba20285bfb875ad7396e676"
H7MS = 7 * 3600 * 1000


def tag(a, s):
    return "nup3b-%s-%s" % (a, s) + ("r" if (a, s) == ("s0b", "s99") else "")


def md5b(b):
    return hashlib.md5(b).hexdigest()


def books(t):
    hdr, base, slv = P.split_run(t)
    return hdr, base, slv


def stage_check():
    V = {}
    b0m = {s: md5b(open(KS + "tsx-x14-%s/storage/printDone.csv" % s, "rb").read()) for s in SEEDS}
    for a in ARMS:
        for s in SEEDS:
            t = tag(a, s)
            hdr, base, slv = books(t)
            rj = json.load(open(KS + t + "/result.json"))
            sm = json.load(open(KS + t + "/storage/sleeve_summary.json"))
            ov = rj["overrides"]
            mb = md5b(hdr + b"".join(base))
            v = dict(md5_base=mb, md5_b0=b0m[s], inv=mb == b0m[s], n_base_rows=len(base), n_sleeve_rows=len(slv),
                     rows_ok=len(slv) == sm["printdone_sleeve_rows"], ok=rj["ok"], jar_ok=rj["jar_sha256"] == JAR,
                     cfg_ok=bool(sm["arm"] == SARM[a] and abs(sm["size_mult"] - SIZE[a]) < 1e-6
                                 and float(ov["SLEEVE_SIZE_MULT"]) == SIZE[a] and ov["SLEEVE_ARM"] == SARM[a]
                                 and (str(ov.get("BASE_SKIP_SLEEVE_SYMBOLS", "false")).lower() == "true") == (a == "s1x")
                                 and sm["base_skip_sleeve_symbols"] == (a == "s1x")),
                     n_trades_ok=rj["n_trades"] == len(base) + len(slv),
                     sim={k: sm[k] for k in sm if k not in ("sleeve_profit", "sleeve_fee", "comb_maxdd_mtm_low_usd",
                                                             "comb_maxdd_mtm_low_pct", "comb_maxdd_t")})
            if a == "s1x":
                v["s1x_ok"] = bool(sm["overlap_base_opens_sleeve_sym"] == 0 and sm["base_skip_backstop"] == 0)
                v["inv"] = None
            V[t] = v
            print(t, v["inv"], v["n_base_rows"], v["n_sleeve_rows"], v["rows_ok"], v["ok"], v["jar_ok"], v["cfg_ok"], v["n_trades_ok"],
                  v.get("s1x_ok"))
    allok = all((v["inv"] is True or (v["inv"] is None and v["s1x_ok"])) and v["rows_ok"] and v["ok"] and v["jar_ok"] and v["cfg_ok"]
                and v["n_trades_ok"] for v in V.values())
    json.dump(dict(runs=V, ALL_OK=allok), open(WK + "/check.json", "w"), indent=1)
    print("CHECK ALL_OK", allok)
    assert allok


def sleeve_t0_by_minute(t):
    hdr, _, slv = books(t)
    d = P.parse(hdr + b"".join(slv), "S")[0]
    c = P.clusters(d)
    return c, d


def stage_map():
    """sid -> sym tu chinh du lieu run: dong OPEN cua sleeve_cand.csv (ts_ms, sid) vs cum sleeve mo cung phut (+07)."""
    cand = {}
    stats = {}
    for a in ARMS:
        for s in SEEDS:
            t = tag(a, s)
            c, _ = sleeve_t0_by_minute(t)
            by_min = c.groupby("t0")["sym"].apply(set).to_dict()
            sc = pd.read_csv(KS + t + "/storage/sleeve_cand.csv")
            op = sc[sc.decision.astype(str).str.strip() == "OPEN"]
            best = None
            for off in (0, 60000):
                hit = 0
                for ts, sid in zip(op.ts_ms.to_numpy(np.int64), op.sid.to_numpy(np.int64)):
                    k = pd.Timestamp(int(ts + H7MS + off), unit="ms")
                    hit += k in by_min
                if best is None or hit > best[1]:
                    best = (off, hit)
            off = best[0]
            stats[t] = dict(n_open=len(op), off_ms=off, minute_hit=best[1], n_cl=len(c))
            for ts, sid in zip(op.ts_ms.to_numpy(np.int64), op.sid.to_numpy(np.int64)):
                k = pd.Timestamp(int(ts + H7MS + off), unit="ms")
                if k in by_min:
                    cur = cand.get(int(sid))
                    cand[int(sid)] = set(by_min[k]) if cur is None else (cur & by_min[k] if cur & by_min[k] else cur | {"__CONFLICT__"})
    # loai tru lan truyen
    mp = {}
    changed = True
    while changed:
        changed = False
        used = set(mp.values())
        for sid, ss in cand.items():
            if sid in mp:
                continue
            r = {x for x in ss if x not in used and x != "__CONFLICT__"}
            if len(r) == 1:
                mp[sid] = r.pop()
                changed = True
    amb = {sid: sorted(ss) for sid, ss in cand.items() if sid not in mp}
    inv = {}
    for k, v in mp.items():
        inv.setdefault(v, []).append(k)
    dup = {k: v for k, v in inv.items() if len(v) > 1}
    json.dump(dict(map={str(k): v for k, v in mp.items()}, ambiguous={str(k): v for k, v in amb.items()}, dup=dup, stats=stats),
              open(WK + "/sidmap.json", "w"), indent=1)
    print("mapped", len(mp), "ambiguous", len(amb), "dup", len(dup))
    print(json.dumps(stats))
    assert not dup


def stage_mtm():
    FR = {}
    for a in ARMS:
        for s in SEEDS:
            t = tag(a, s)
            hdr, base, slv = books(t)
            for bk, lines in (("S", slv), ("B", base)):
                if bk == "B" and a != "s1x":
                    continue
                d = P.parse(hdr + b"".join(lines), bk)[0]
                FR[t + "#" + bk] = d[["sym", "quantity", "entry", "margin", "pnl", "ts", "te", "notional"]].copy()
    o_ll = R.load_legs
    R.load_legs = lambda t: FR[t].copy() if t in FR else o_ll(t)
    b0 = ["tsx-x14-" + s for s in SEEDS]
    out, miss = M.build(b0 + sorted(FR), None)
    print("missing", miss)
    assert all(v == 0 for v in miss.values()), miss
    np.savez(WK + "/eq.npz", **{k.replace("#", "__"): v for k, v in out.items()})
    json.dump(dict(missing=miss), open(WK + "/mtm.json", "w"), indent=1)


def skip_join(t, s, cB0, cSl):
    """S1x: ghep log BASE-SKIP-SLEEVE (1 dong / cum sleeve, lan chan dau) voi printDone B0 cung seed."""
    mp = {int(k): v for k, v in json.load(open(WK + "/sidmap.json"))["map"].items()}
    rows = []
    with open(KS + t + "/logs/full.log", errors="replace") as f:
        for ln in f:
            if "BASE-SKIP-SLEEVE" not in ln:
                continue
            kv = dict(x.split("=", 1) for x in ln.strip().split("BASE-SKIP-SLEEVE", 1)[1].split())
            rows.append((int(kv["sid"]), int(kv["tMs"]), kv["lvl"], int(kv["sleeveT0"])))
    L = pd.DataFrame(rows, columns=["sid", "tms", "lvl", "st0ms"])
    L["sym"] = L.sid.map(mp)
    L["t"] = pd.to_datetime(L.tms + H7MS, unit="ms")
    L["st0"] = pd.to_datetime(L.st0ms + H7MS, unit="ms")
    # sid chua map duy nhat: lay sym cua cum sleeve mo dung phut sleeveT0, tru sym da gan cho sid khac
    amb = {int(k): set(v) for k, v in json.load(open(WK + "/sidmap.json"))["ambiguous"].items()}
    used = set(mp.values())
    by_t0 = cSl.groupby("t0")["sym"].apply(set).to_dict()
    nfb = 0
    for i in L.index[L.sym.isna()]:
        c = by_t0.get(L.at[i, "st0"], set()) - used
        if L.at[i, "sid"] in amb:
            c = c & amb[L.at[i, "sid"]] if c & amb[L.at[i, "sid"]] else c
        if len(c) == 1:
            L.at[i, "sym"] = c.pop()
            nfb += 1
    # cum sleeve tuong ung (sym, t0)
    cs = cSl.set_index(["sym", "t0"])
    key = list(zip(L.sym, L.st0))
    L["s_found"] = [k in cs.index for k in key]
    L["s_te"] = [cs.loc[k, "te"] if k in cs.index else pd.NaT for k in key]
    if isinstance(L["s_te"].iloc[0], pd.Series):
        raise RuntimeError("dup sleeve cluster key")
    b = cB0[["sym", "t0", "te", "pnl", "ei", "si"]].copy()
    bx = b.set_index(["sym", "t0"])
    # (A) dung phut chan dau tien == t0 cum B0 cung symbol
    A = [(sy, tt) for sy, tt in zip(L.sym, L.t) if (sy, tt) in bx.index]
    A = sorted(set(A))
    # (B) cum B0 mo (t0) trong cua so giu cua cum sleeve S1x co log: st0 < t0_B0 <= te_sleeve
    g = {}
    for sy, a0, e0 in zip(L.sym, L.st0, L.s_te):
        g.setdefault(sy, []).append((a0, e0))
    Bset = []
    for sy, t0 in zip(b.sym, b.t0):
        for a0, e0 in g.get(sy, ()):
            if a0 < t0 <= e0:
                Bset.append((sy, t0))
                break
    Bset = sorted(set(Bset))
    # moi cum sleeve S1x (khong chi co log): cua so giu
    g2 = {}
    for sy, a0, e0 in zip(cSl.sym, cSl.t0, cSl.te):
        g2.setdefault(sy, []).append((a0, e0))
    Cset = sorted({(sy, t0) for sy, t0 in zip(b.sym, b.t0) if any(a0 < t0 <= e0 for a0, e0 in g2.get(sy, ()))})

    def summ(keys):
        k = bx.loc[keys] if keys else bx.iloc[:0]
        dev = k[(k.ei >= P.I0) & (k.ei < P.I1)]
        return dict(n_all=len(k), n_dev=len(dev), n_dev_open=int(((k.si >= P.I0) & (k.si < P.I1)).sum()),
                    pnl_dev=float(dev.pnl.sum()), pnl_all=float(k.pnl.sum()))
    return dict(n_log=len(L), n_log_mapped=int(L.sym.notna().sum()), n_log_fallback=nfb, n_log_sleeve_found=int(L.s_found.sum()),
                lvl=L.lvl.value_counts().to_dict(), A_exact_first_skip=summ(A), B_window_logged=summ(Bset),
                C_window_all_sleeve=summ(Cset))


def stage_score():
    z = np.load(WK + "/eq.npz")
    chk = json.load(open(WK + "/check.json"))["runs"]
    rows, years, quarts, extra = [], [], [], {}
    V = dict(quarter_sum={}, sim_cross={}, flat={})
    B = {}
    BS = pd.read_csv(P.REPO + "/docs/result/golive_quarterly/quarterly_x14_by_seed.csv")
    for s in SEEDS:
        dB = P.load_b0(s)
        eqB = P.dev_full(z["tsx-x14-" + s])
        cb = P.core(dB, eqB)
        r = BS[(BS.phase == "DEV") & (BS.seed.str.lower() == s) & (BS.period == "DEV_2022_25")].iloc[0]
        assert cb["n_cl"] == int(r.n_cl) and abs(cb["pnl"] - r.pnl) < 1e-3 and abs(cb["dd"] - r.dd_cum) < 0.005
        B[s] = dict(d=dB, eq=eqB, bal=P.realized_bal(dB, P.NDEV), core=cb)
    for a in ARMS:
        for s in SEEDS:
            t = tag(a, s)
            hdr, base, slv = books(t)
            dS = P.parse(hdr + b"".join(slv), "S")[0]
            eqS = P.dev_full(z[t + "__S"])
            if a == "s1x":
                dBa = P.parse(hdr + b"".join(base), "B")[0]
                eqBa = P.dev_full(z[t + "__B"])
            else:
                dBa, eqBa = B[s]["d"], B[s]["eq"]
            balBa, balS = P.realized_bal(dBa, P.NDEV), P.realized_bal(dS, P.NDEV)
            dP = pd.concat([dBa, dS], ignore_index=True)
            eqP, balP = eqBa + eqS - P.CAP0, balBa + balS - P.CAP0
            cp, cs, cba = P.core(dP, eqP), P.core(dS, eqS), P.core(dBa, eqBa)
            cb = B[s]["core"]
            xp = P.expo(dP, cp["c"], eqP, balP)
            eqPf = P.month_fix(dBa, eqBa)[0] + P.month_fix(dS, eqS)[0] - P.CAP0
            sm = chk[t]["sim"]
            full = slice(0, P.I1)
            V["sim_cross"][t] = dict(u_mark=[float(xp["um"][full].max()), sm["u_total_max"]],
                                     u_marg=[float(xp["ug"][full].max()), sm["u_total_margin_max"]],
                                     npos=[int(xp["npos"][full].max()), sm["max_pos_total"]])
            flat = xp["npos"] < 0.5
            V["flat"][t] = dict(pipeline=float(np.abs((eqP - balP)[flat & (np.arange(P.NDEV) >= P.I0 - 1)]).max()),
                                fixed=float(np.abs((eqPf - balP)[flat & (np.arange(P.NDEV) >= P.I0 - 1)]).max()))
            cS_all = P.clusters(dS)
            ne = P.neff(cs["K"], cba["c"], cba["K"])
            ov, nbw = P.overlap(cba["c"], cS_all)
            sl_open = dS[(dS["si"] >= P.I0) & (dS["si"] < P.I1)]
            n_rej = int((xp["ug"][sl_open["si"].to_numpy()] > 1.0).sum())
            V["quarter_sum"][t] = dict(port=sum(cp["q"].values()) - cp["pnl"], sleeve=sum(cs["q"].values()) - cs["pnl"],
                                       years=sum(cp["yr"][y]["pnl"] for y in P.YEARS) - cp["pnl"])
            row = dict(tag=t, arm=a, seed=s, size=SIZE[a],
                       P_n_cl=cp["n_cl"], P_ncl_y=cp["n_cl"] / 4, B0_n_cl=cb["n_cl"], r_ncl=cp["n_cl"] / cb["n_cl"],
                       P_pnl=cp["pnl"], B0_pnl=cb["pnl"], r_pnl=cp["pnl"] / cb["pnl"],
                       P_stress=cp["stress"], B0_stress=cb["stress"], r_stress=cp["stress"] / cb["stress"],
                       P_cagr=cp["cagr"], B0_cagr=cb["cagr"], P_dd=cp["dd"], P_dd_fix=Q.ddx(eqPf[P.I0 - 1:P.I1]), B0_dd=cb["dd"],
                       P_dd_full=Q.ddx(eqP[0:P.I1]), P_calmar=cp["calmar"], B0_calmar=cb["calmar"],
                       P_u_mark_max=xp["u_mark_max"], P_u_marg_max=xp["u_marg_max"], P_u_marg_gt1_min=xp["u_marg_gt1_min"],
                       P_npos_max=xp["npos_max"], S_legs_open_dev=len(sl_open), S_legs_marg_gt1=n_rej,
                       S_pct_legs_marg_gt1=100 * n_rej / len(sl_open),
                       base_n_cl=cba["n_cl"], base_pnl=cba["pnl"], base_r_ncl=cba["n_cl"] / cb["n_cl"], base_r_pnl=cba["pnl"] / cb["pnl"],
                       base_dd=cba["dd"],
                       S_n_cl=cs["n_cl"], S_ncl_y=cs["n_cl"] / 4, S_n_leg=cs["n_leg"], S_pnl=cs["pnl"], S_stress=cs["stress"],
                       S_notional=float(cs["L"]["notional"].sum()),
                       S_roi_leg=100 * cs["pnl"] / float(cs["L"]["notional"].sum()),
                       S_roi_stress=100 * cs["stress"] / float(cs["L"]["notional"].sum()),
                       S_years_stress_pos=int(sum(cs["yr"][y]["stress"] > 0 for y in P.YEARS)),
                       S_pnl_2021H2=float(dS.loc[dS["ei"] < P.I0, "pnl"].sum()),
                       overlap=ov, base_cl_open_dev=nbw, pct_overlap=100 * ov / nbw,
                       sim_overlap_full=sm["overlap_base_opens_sleeve_sym"], sim_not_opened=sm["not_opened"],
                       sim_opened=sm["opened"], sim_cand=sm["cand"],
                       **{"S_" + k: v for k, v in ne.items()})
            for y in P.YEARS:
                row["r_ncl_%d" % y] = cp["yr"][y]["n_cl"] / cb["yr"][y]["n_cl"]
                years.append(dict(tag=t, arm=a, seed=s, year=y, P_n_cl=cp["yr"][y]["n_cl"], B0_n_cl=cb["yr"][y]["n_cl"],
                                  r_ncl=cp["yr"][y]["n_cl"] / cb["yr"][y]["n_cl"], P_pnl=cp["yr"][y]["pnl"], B0_pnl=cb["yr"][y]["pnl"],
                                  base_n_cl=cba["yr"][y]["n_cl"], base_pnl=cba["yr"][y]["pnl"],
                                  S_n_cl=cs["yr"][y]["n_cl"], S_pnl=cs["yr"][y]["pnl"], S_stress=cs["yr"][y]["stress"]))
            for qn in cp["q"]:
                quarts.append(dict(tag=t, arm=a, seed=s, quarter=qn, P_pnl=cp["q"][qn], S_pnl=cs["q"][qn], base_pnl=cba["q"][qn]))
            if a == "s1x":
                sj = skip_join(t, s, cb["c"], cS_all)
                extra[t] = sj
                for k in ("A_exact_first_skip", "B_window_logged", "C_window_all_sleeve"):
                    row["skip_%s_n_dev" % k[0]] = sj[k]["n_dev"]
                    row["skip_%s_pnl_dev" % k[0]] = sj[k]["pnl_dev"]
                row["skip_n_log"] = sj["n_log"]
                row["skip_log_ok"] = bool(sj["n_log_mapped"] == sj["n_log"] == sj["n_log_sleeve_found"])
            rows.append(row)
            print(t, "done")
    Rn, Y = pd.DataFrame(rows), pd.DataFrame(years)
    Rn.to_csv(OUTD + "/p1b_runs.csv", index=False)
    Y.to_csv(OUTD + "/p1b_years.csv", index=False)
    pd.DataFrame(quarts).to_csv(OUTD + "/p1b_quarters.csv", index=False)
    arms = []
    for a in ARMS:
        g, gy = Rn[Rn.arm == a], Y[Y.arm == a]
        med = lambda c: float(g[c].median())  # noqa: E731
        yr_r = {y: float(gy[gy.year == y].r_ncl.median()) for y in P.YEARS}
        yr_s = {y: float(gy[gy.year == y].S_stress.median()) for y in P.YEARS}
        o = dict(arm=a, size=SIZE[a], P_ncl_y=med("P_ncl_y"), r_ncl=med("r_ncl"), **{"r_ncl_%d" % y: yr_r[y] for y in P.YEARS},
                 P_pnl=med("P_pnl"), r_pnl=med("r_pnl"), P_stress=med("P_stress"), r_stress=med("r_stress"),
                 P_cagr=med("P_cagr"), P_dd_med=med("P_dd"), P_dd_worst=float(g.P_dd.min()), P_dd_fix_med=med("P_dd_fix"),
                 P_dd_full_med=med("P_dd_full"), P_calmar=med("P_calmar"),
                 P_u_mark_max_med=med("P_u_mark_max"), P_u_mark_max_worst=float(g.P_u_mark_max.max()),
                 P_u_marg_max_med=med("P_u_marg_max"), P_u_marg_max_worst=float(g.P_u_marg_max.max()),
                 P_npos_max=int(g.P_npos_max.max()), S_legs_marg_gt1_med=med("S_legs_marg_gt1"),
                 S_legs_marg_gt1_max=int(g.S_legs_marg_gt1.max()), S_pct_legs_marg_gt1_max=float(g.S_pct_legs_marg_gt1.max()),
                 base_r_ncl=med("base_r_ncl"), base_r_pnl=med("base_r_pnl"), base_dd_med=med("base_dd"),
                 S_ncl_y=med("S_ncl_y"), S_roi_leg=med("S_roi_leg"), S_roi_stress=med("S_roi_stress"), S_pnl=med("S_pnl"),
                 S_stress=med("S_stress"), **{"S_stress_%d" % y: yr_s[y] for y in P.YEARS},
                 S_years_stress_pos_med=int(sum(yr_s[y] > 0 for y in P.YEARS)), S_seeds_stress_pos=int((g.S_stress > 0).sum()),
                 overlap_med=med("overlap"), pct_overlap_med=med("pct_overlap"),
                 S_ep_y=med("S_ep_y"), S_ep_nonov_y=med("S_ep_nonov_y"), S_pct_ep_nonov=med("S_pct_ep_nonov"),
                 S_days_y=med("S_days_y"), S_pct_days_nob0=med("S_pct_days_nob0"), S_corr_daily=med("S_corr_daily"),
                 S_top10_day_pct=med("S_top10_day_pct"), S_pnl_2021H2_med=med("S_pnl_2021H2"))
        o["G1"] = bool(o["r_ncl"] >= 1.30 and all(yr_r[y] >= 1.15 for y in P.YEARS))
        o["G2"] = bool(o["r_pnl"] >= 1.00 and o["S_years_stress_pos_med"] >= 3 and o["S_seeds_stress_pos"] >= 3)
        o["G3"] = bool(o["P_dd_med"] >= -32 and o["P_dd_worst"] >= -36 and o["P_u_mark_max_worst"] <= 1.0)
        o["PASS_P1"] = bool(o["G1"] and o["G2"] and o["G3"])
        o["iso_dd_dev_pp"] = o["P_dd_med"] - (-30.0)
        o["iso_dd_holds"] = bool(abs(o["iso_dd_dev_pp"]) <= 3.0)
        if a == "s1x":
            for k in ("A", "B", "C"):
                o["skip_%s_n_dev_med" % k] = med("skip_%s_n_dev" % k)
                o["skip_%s_pnl_dev_med" % k] = med("skip_%s_pnl_dev" % k)
        arms.append(o)
    A = pd.DataFrame(arms)
    A.to_csv(OUTD + "/p1b_arms.csv", index=False)
    V["quarter_sum_ok"] = bool(all(abs(v) < 1e-6 for x in V["quarter_sum"].values() for v in x.values()))
    V["sim_cross_maxdiff"] = dict(u_mark=max(abs(x["u_mark"][0] - x["u_mark"][1]) for x in V["sim_cross"].values()),
                                  u_marg=max(abs(x["u_marg"][0] - x["u_marg"][1]) for x in V["sim_cross"].values()),
                                  npos=max(abs(x["npos"][0] - x["npos"][1]) for x in V["sim_cross"].values()))
    V["mtm"] = json.load(open(WK + "/mtm.json"))
    V["mtm_missing_ok"] = bool(all(v == 0 for v in V["mtm"]["missing"].values()))
    V["s1x_skip"] = extra
    V["sidmap"] = {k: v for k, v in json.load(open(WK + "/sidmap.json")).items() if k != "map"}
    json.dump(V, open(OUTD + "/p1b_validate.json", "w"), indent=1, default=str)
    pd.set_option("display.width", 250)
    print(A.T.to_string())
    print(Rn.drop(columns=["tag"]).T.to_string())
    print(json.dumps({k: V[k] for k in ("quarter_sum_ok", "sim_cross_maxdiff", "mtm_missing_ok")}))
    print("flat", V["flat"])
    print(json.dumps(extra, default=str))
    print(Y.pivot_table(index=["arm", "seed"], columns="year", values="S_stress").round(0).to_string())


if __name__ == "__main__":
    os.makedirs(WK, exist_ok=True)
    {"check": stage_check, "map": stage_map, "mtm": stage_mtm, "score": stage_score}[sys.argv[1]]()
