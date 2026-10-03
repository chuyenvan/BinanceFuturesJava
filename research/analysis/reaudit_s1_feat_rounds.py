#!/usr/bin/env python3
"""REAUDIT_S1_FEATURE_ROUNDS (2026-10-03) — cham lai cac vong feature/label S1 bang thuoc §9 A-20261003.
CHI doc artifact co san: 0 train, 0 sim, 0 Kaggle, 0 Java. DEV <= 2025.

Phan A  oi12   : MTM ngay ghep cap X1_GS_T170_OI12_2021 vs X1_GS_T170_2021 (devrun Oracle, sim.out), block-10d
                 NREP 2000 seed 20260905 (dung SAD.daily_boot), DeltaCAGR/maxDD/Calmar + DeltaPnL theo nam.
Phan B  geom   : (i) G vs CTRL voi k=1 (luat moi: GN la doi chung, khong phai lever) + k=2 (pre-reg);
                 (ii) POST-HOC thong tin: 4 run co GEOM {G42,G7,GN42,GN7} vs 4 seed CTRL {K42,S7,S13,S21}.
Phan C  offline: FEATGRP/HPO/BAG (pred ~/s1hpo, CPU seed 42) Delta edge5 CONFIRM vs baseline VA vs trung binh
                 5 cot nhieu (noise_0..4 = "doi seed tuong duong"), + san seed CONFIRM tu CTRL K42/S7/S13/S21.
Usage: python3 reaudit_s1_feat_rounds.py oi12|geom|offline|all  -> docs/audit/reaudit_s1_feat_rounds.json
"""
import json, os, sys
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import selector_ablation_driver as SAD  # noqa: E402
import reset_rule_score as R  # noqa: E402

OUT = os.path.join(REPO, "docs/audit/reaudit_s1_feat_rounds.json")
DEV = "/home/ubuntu/java/devrun"
YRS = ("2021", "2022", "2023", "2024", "2025")


def infl(k):
    return 1.0 if k <= 1 else float(np.sqrt(2 * np.log(k)))


def ci(obs_d, arr, k=1):
    a = arr[np.isfinite(arr)]
    lo, hi = np.percentile(a, [2.5, 97.5])
    f = infl(k)
    return dict(d=float(obs_d), ci_raw=[float(lo), float(hi)],
                ci_infl=[float(obs_d - (obs_d - lo) * f), float(obs_d + (hi - obs_d) * f)], k=k,
                out_raw=bool(lo > 0 or hi < 0), out_infl=bool(obs_d - (obs_d - lo) * f > 0 or obs_d + (hi - obs_d) * f < 0))


def daily_from_simout(path):
    rows = []
    with open(path, errors="ignore") as fh:
        for line in fh:
            m = R.RX_DAILY.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)), int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "b", "unP"]).drop_duplicates("d", keep="last")
    e["t"] = pd.to_datetime(e["d"], format="%Y%m%d")
    e = e.set_index("t").sort_index()
    return (e["b"] + e["unP"]).astype(float)


def legs_pnl_year(path):
    d = pd.read_csv(path, on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d["pnl"] = pd.to_numeric(d["pnl"], errors="coerce")
    d = d.dropna(subset=["pnl"])
    y = d["start"].astype(str).str[:4]
    return d, {k: float(v) for k, v in d.groupby(y).pnl.sum().items()}


def year_ret(eq):
    out = {}
    for y in sorted(set(eq.index.year)):
        s = eq[eq.index.year == y]
        prev = eq[eq.index < s.index[0]]
        e0 = prev.iloc[-1] if len(prev) else s.iloc[0]
        out[str(y)] = float(100 * (s.iloc[-1] / e0 - 1))
    return out


def boot(eqs, base):
    e2 = {("P0" if k == base else k): v for k, v in eqs.items()}
    obs, bs = SAD.daily_boot(e2)
    obs[base], bs[base] = obs.pop("P0"), bs.pop("P0")
    return obs, bs


# ----------------------------------------------------------------------------------------------- A. OI12
def part_oi12():
    tags = {"BASE": "X1_GS_T170_2021", "OI12": "X1_GS_T170_OI12_2021"}
    res = {"tags": tags, "note": "nen T170 (gate nguong co dinh scale 1,70, chi phi cu) — KHONG phai chuoi B0; 1 seed/arm"}
    eq = {k: daily_from_simout(os.path.join(DEV, t, "logs/sim.out")) for k, t in tags.items()}
    for k in eq:
        res.setdefault("n_days", {})[k] = int(len(eq[k]))
        res.setdefault("eq_last", {})[k] = float(eq[k].iloc[-1])
    pnl = {}
    for k, t in tags.items():
        d, py = legs_pnl_year(os.path.join(DEV, t, "storage/printDone.csv"))
        pnl[k] = dict(n=int(len(d)), sum_pnl=float(d.pnl.sum()), by_year=py,
                      win=float(100 * (pd.to_numeric(d.profit, errors="coerce") > 0).mean()))
    res["legs"] = pnl
    res["dpnl_year"] = {y: pnl["OI12"]["by_year"].get(y, 0.0) - pnl["BASE"]["by_year"].get(y, 0.0) for y in YRS}
    for wname, w0 in (("full_2021H2_2025", "2021-06-30"), ("w2022_2025", "2021-12-31")):
        e = {k: v[v.index >= pd.Timestamp(w0)] for k, v in eq.items()}
        obs, bs = boot(e, "BASE")
        con = {m: ci(obs["OI12"][m] - obs["BASE"][m], bs["OI12"][m] - bs["BASE"][m], k=1)
               for m in ("cagr", "mdd", "calmar", "sharpe")}
        res[wname] = dict(obs={k: {m: float(v[m]) for m in ("cagr", "mdd", "calmar", "sharpe")} for k, v in obs.items()},
                          delta=con, yr_ret={k: year_ret(v) for k, v in e.items()})
        print("OI12", wname, {m: (round(c["d"], 3), [round(z, 3) for z in c["ci_raw"]]) for m, c in con.items()})
    yr = res["full_2021H2_2025"]["yr_ret"]
    res["dret_year"] = {y: yr["OI12"].get(y, np.nan) - yr["BASE"].get(y, np.nan) for y in YRS}
    print("OI12 dret_year", res["dret_year"], "dpnl_year", res["dpnl_year"])
    return res


# ----------------------------------------------------------------------------------------------- B. GEOM
def part_geom():
    tags = {"G42": "geom-g42", "G7": "geom-g7", "GN42": "geom-gn42", "GN7": "geom-gn7",
            "K42": "s1rn-k42", "S7": "s1rn-s7", "S13": "s1rn-s13", "S21": "s1rn-s21", "B0": "selab-p0"}
    W0 = pd.Timestamp("2021-12-31")
    eq = {}
    for k, t in tags.items():
        d = R.load_daily(t)["equity"].astype(float)
        eq[k] = d[d.index >= W0]
    obs, bs = boot(eq, "B0")
    mets = ("cagr", "mdd", "calmar", "sharpe")
    fam = {"G": ["G42", "G7"], "CTRL": ["K42", "S7"], "GEO4": ["G42", "G7", "GN42", "GN7"],
           "CTRL4": ["K42", "S7", "S13", "S21"], "GN": ["GN42", "GN7"]}
    for f, mem in fam.items():
        obs[f] = {m: float(np.mean([obs[x][m] for x in mem])) for m in mets}
        bs[f] = {m: np.mean([bs[x][m] for x in mem], axis=0) for m in mets}
    res = {"tags": tags, "window": "2022-01-01..2025-12-30 (equity ngay tu 2021-12-31)",
           "obs": {k: {m: float(v[m]) for m in mets} for k, v in obs.items()}}
    pairs = [("G", "CTRL", 1), ("G", "CTRL", 2), ("GEO4", "CTRL4", 1), ("GEO4", "B0", 1), ("G", "B0", 1),
             ("CTRL4", "B0", 1), ("CTRL", "CTRL4", 1)]
    res["contrasts"] = {}
    for a, b, k in pairs:
        key = "%s-%s_k%d" % (a, b, k)
        res["contrasts"][key] = {m: ci(obs[a][m] - obs[b][m], bs[a][m] - bs[b][m], k=k) for m in mets}
        c = res["contrasts"][key]
        print("GEOM", key, {m: (round(c[m]["d"], 3), [round(z, 3) for z in c[m]["ci_infl"]]) for m in ("cagr", "calmar")})
    yr = {k: year_ret(v) for k, v in eq.items()}
    for f, mem in fam.items():
        yr[f] = {y: float(np.mean([yr[x][y] for x in mem])) for y in ("2022", "2023", "2024", "2025")}
    res["yr_ret"] = yr
    res["dret_year"] = {"G-CTRL": {y: yr["G"][y] - yr["CTRL"][y] for y in ("2022", "2023", "2024", "2025")},
                        "GEO4-CTRL4": {y: yr["GEO4"][y] - yr["CTRL4"][y] for y in ("2022", "2023", "2024", "2025")}}
    res["seed_sd_cagr"] = {f: float(np.std([obs[x]["cagr"] for x in fam[f]], ddof=1)) for f in ("GEO4", "CTRL4")}
    print("GEOM dret_year", res["dret_year"], "seed_sd", res["seed_sd_cagr"])
    return res


# ----------------------------------------------------------------------------------------------- C. OFFLINE
S1H = "/home/ubuntu/s1hpo"
CAND = {"H1": "pred_p1_H1", "H2": "pred_p1_H2", "H3": "pred_p1_H3", "H4": "pred_p1_H4", "H5": "pred_p1_H5",
        "H6": "pred_p1_H6", "BAG5": "pred_p2_bag5", "G1": "pred_p3_G1", "G2": "pred_p3_G2", "G3": "pred_p3_G3"}
NOISE = {"n0": "pred_p3_noise", "n1": "pred_noisecal_noise_1", "n2": "pred_noisecal_noise_2",
         "n3": "pred_noisecal_noise_3", "n4": "pred_noisecal_noise_4"}
KFAM = {"H1": 6, "H2": 6, "H3": 6, "H4": 6, "H5": 6, "H6": 6, "BAG5": 1, "G1": 3, "G2": 3, "G3": 3}


def edge5(df, col):
    rk = df.groupby("ts")[col].rank(method="first")
    top = df.g1lite.where(rk <= 5)
    return 100 * (top.groupby(df.ts).mean() - df.g1lite.groupby(df.ts).mean())


def part_offline():
    import s1_hpo_bag_featgrp as HBF
    B = pd.read_parquet(S1H + "/pred_baseline18.parquet", columns=["ts", "sym", "g1lite", "score", "fold"])
    B = B.rename(columns={"score": "base"})
    for k, f in list(CAND.items()) + list(NOISE.items()):
        P = pd.read_parquet("%s/%s.parquet" % (S1H, f))
        P = P[["ts", "sym", "score"]].rename(columns={"score": k})
        n0 = len(B)
        B = B.merge(P, on=["ts", "sym"], how="inner")
        assert len(B) == n0, (k, n0, len(B))
    E = {k: edge5(B, k) for k in ["base"] + list(CAND) + list(NOISE)}
    fold = B.groupby("ts").fold.first()
    yr = pd.Series(pd.to_datetime(fold.index, unit="ms").year, index=fold.index)
    conf = fold >= 10
    NM = pd.concat([E[k] for k in NOISE], axis=1).mean(axis=1)
    res = {"n_rows": int(len(B)), "n_ticks": int(len(fold)), "noise": {}, "cand": {}}
    for k in NOISE:
        d = (E[k] - E["base"])[conf]
        res["noise"][k] = dict(confirm_mean=float(d.mean()))
    nz = np.array([res["noise"][k]["confirm_mean"] for k in NOISE])
    res["noise_summary"] = dict(mean=float(nz.mean()), sd=float(nz.std(ddof=1)))
    print("OFF noise CONFIRM d_edge5 vs base:", np.round(nz, 3), "mean %.3f sd %.3f" % (nz.mean(), nz.std(ddof=1)))
    for k in CAND:
        d_b = (E[k] - E["base"])[conf]
        d_n = (E[k] - NM)[conf]
        cb = HBF.block_ci_diff(d_b, k=KFAM[k])
        cn = HBF.block_ci_diff(d_n, k=KFAM[k])
        cn1 = HBF.block_ci_diff(d_n, k=1)
        byy = {int(y): float((E[k] - NM)[yr == y].mean()) for y in sorted(set(yr))}
        res["cand"][k] = dict(k=KFAM[k], vs_base=cb, vs_noise_mean=cn, vs_noise_mean_k1=cn1,
                              z_vs_noise_dist=float((d_b.mean() - nz.mean()) / nz.std(ddof=1)), by_year_vs_noise=byy)
        print("OFF %-5s CONF vs base %+.3f [%+.3f;%+.3f] | vs noiseMean %+.3f [%+.3f;%+.3f] (k=%d) raw [%+.3f;%+.3f] | z %.2f"
              % (k, cb["mean"], cb["lo"], cb["hi"], cn["mean"], cn["lo"], cn["hi"], KFAM[k], cn1["lo"], cn1["hi"],
                 res["cand"][k]["z_vs_noise_dist"]), {y: round(v, 2) for y, v in byy.items()})
    # san seed CONFIRM (2024-25) tu CTRL GPU seeds (16 fold 2022+), so voi ORIG (deploy = seed 42 CPU)
    L = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet", columns=["ts", "sym", "g1lite"])
    O = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2x1.parquet", columns=["ts", "sym", "score"]).rename(
        columns={"score": "ORIG"})
    O = O.merge(L, on=["ts", "sym"], how="left")
    for s in ("K42", "S7", "S13", "S21"):
        P = pd.read_parquet("/home/ubuntu/claude_master/1003/s1rn/kout/pred_%s.parquet" % s, columns=["ts", "sym", "score"])
        O = O.merge(P.rename(columns={"score": s}), on=["ts", "sym"], how="inner")
    t24 = int(pd.Timestamp("2024-01-01").value // 10 ** 6)
    sd = {}
    for s in ("ORIG", "K42", "S7", "S13", "S21"):
        e = edge5(O, s)
        sd[s] = dict(all=float(e.mean()), confirm_2024_25=float(e[e.index >= t24].mean()))
    seeds = np.array([sd[s]["confirm_2024_25"] for s in ("K42", "S7", "S13", "S21")])
    res["seed_floor"] = dict(per_arm=sd, ctrl_confirm_mean=float(seeds.mean()), ctrl_confirm_sd=float(seeds.std(ddof=1)),
                             orig_minus_ctrl_confirm=float(sd["ORIG"]["confirm_2024_25"] - seeds.mean()))
    print("OFF seed floor", json.dumps(res["seed_floor"]))
    return res


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    js = json.load(open(OUT)) if os.path.exists(OUT) else {}
    js.update(dict(script="research/analysis/reaudit_s1_feat_rounds.py", nrep=SAD.NREP, seed=SAD.SEED,
                   block_days=SAD.BLOCK_D, offline_block_h=72, offline_seed=20260919))
    if what in ("oi12", "all"):
        js["oi12"] = part_oi12()
    if what in ("geom", "all"):
        js["geom"] = part_geom()
    if what in ("offline", "all"):
        js["offline"] = part_offline()
    json.dump(js, open(OUT, "w"), indent=1, default=float)
    print("JSON ->", OUT)


if __name__ == "__main__":
    main()


# ----------------------------------------------------------------------------------------------- D. cap devrun bat ky
def part_devpair(base_tag, arm_tag):
    """MTM ngay ghep cap 2 devrun Oracle (cung cach OI12). Dung cho 5MGRID (X1_C3_FULL_PARITY vs X1_C3_5M)."""
    eq = {"BASE": daily_from_simout(os.path.join(DEV, base_tag, "logs/sim.out")),
          "ARM": daily_from_simout(os.path.join(DEV, arm_tag, "logs/sim.out"))}
    w0 = max(v.index[0] for v in eq.values())
    eq = {k: v[v.index >= w0] for k, v in eq.items()}
    obs, bs = boot(eq, "BASE")
    con = {m: ci(obs["ARM"][m] - obs["BASE"][m], bs["ARM"][m] - bs["BASE"][m], k=1) for m in ("cagr", "mdd", "calmar")}
    yr = {k: year_ret(v) for k, v in eq.items()}
    out = dict(base=base_tag, arm=arm_tag, w0=str(w0.date()),
               obs={k: {m: float(v[m]) for m in ("cagr", "mdd", "calmar")} for k, v in obs.items()}, delta=con,
               dret_year={y: yr["ARM"].get(y, np.nan) - yr["BASE"].get(y, np.nan) for y in YRS})
    print("DEVPAIR", arm_tag, "vs", base_tag, {m: (round(c["d"], 3), [round(z, 3) for z in c["ci_raw"]]) for m, c in con.items()},
          {y: round(v, 2) for y, v in out["dret_year"].items()})
    return out


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "devpair":
    js = json.load(open(OUT))
    js.setdefault("devpair", {})["%s__vs__%s" % (sys.argv[3], sys.argv[2])] = part_devpair(sys.argv[2], sys.argv[3])
    json.dump(js, open(OUT, "w"), indent=1, default=float)
    print("JSON ->", OUT)
