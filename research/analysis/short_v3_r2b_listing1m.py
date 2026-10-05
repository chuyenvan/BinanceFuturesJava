#!/usr/bin/env python3
"""short_v3_r2b_listing1m.py — R2b (LISTING chuan SL 1m-high) cua PROGRAM_SHORT_V3 ADDENDUM 1.

Pre-reg: docs/prereg/PREREG_SHORT_V3_R2B.md @ 54f64e07 (KHOA). Tap lenh, D0/D1, excess, CI: tai dung nguyen
short_v3_r2_listing.py (import, khong sua). Doc 1m: fetch() cua short_v3_r2_slcheck.py (Aerospike test.kline_1m_opt).
Chuan do: SL +15% kiem tren HIGH 1m, fill tai muc (open >= muc => fill open) + truot 0,2% (nhu R2), exit thoi gian tai
close 1m cuoi cua cua so 168h. Che do '1h' (tat 1m) phai tai lap R2 (+4,41 D0) — sanity SA.
Out: docs/result/RESULT_SHORT_V3_R2B.json ; bang markdown -> ~/claude_master/1002/r2b_tables.md
"""
import json, logging, math, sys, time
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import short_v3_r2_listing as R
import short_v3_r2_slcheck as SC

log = logging.getLogger("r2b")
MIN = 60000
NM = R.HOLD * 60
REPO = R.REPO
OUT_JSON = REPO + "/docs/result/RESULT_SHORT_V3_R2B.json"
OUT_MD = "/home/ubuntu/claude_master/1002/r2b_tables.md"
R2_JSON = REPO + "/docs/result/RESULT_SHORT_V3_R2.json"
PREREG = "docs/prereg/PREREG_SHORT_V3_R2B.md@54f64e07"
G5_THR = -0.005


def sim(r, C, j, t_start, fund, O, Hh, Cc, i, mode):
    """Mot lenh SHORT. mode '1h' = quy uoc R2 (SL tren close 1h, lo co dinh 15,2%); '1m' = chuan R2b."""
    P0 = float(r.P0); t0 = int(r.t0); k0 = int(r.k0)
    lvl = (1 + R.SL_X) * P0
    W = C[k0 + 1:k0 + R.HOLD + 1, j].astype(np.float64)
    fin = np.isfinite(W)
    pend = W[np.where(fin)[0][-1]] if fin.any() else P0
    h1 = np.where(fin & (W >= lvl))[0]
    out = dict(m=None, src=None, gap=False, open_m=None, high_m=None)
    if mode == "1h":
        if len(h1):
            sl, loss, t_exit, out["src"] = True, R.SL_LOSS, t0 + (int(h1[0]) + 1) * R.H, "1h"
        else:
            sl, t_exit, ret, out["src"] = False, t0 + R.HOLD * R.H, pend / P0 - 1, "c1h"
    else:
        hm = np.where(np.nan_to_num(Hh[i], nan=-np.inf) >= lvl)[0]
        t1m = t0 + (int(hm[0]) + 1) * MIN if len(hm) else math.inf
        t1h = t0 + (int(h1[0]) + 1) * R.H if len(h1) else math.inf
        if len(hm) and t1m <= t1h:
            m = int(hm[0]); o = float(O[i, m])
            gap = bool(np.isfinite(o) and o >= lvl)
            fill = o if gap else lvl
            sl, loss, t_exit = True, fill / P0 - 1 + R.SLIP, t1m
            out.update(m=m, src="1m", gap=gap, open_m=o, high_m=float(Hh[i, m]), fill=fill)
        elif len(h1):
            fill = float(W[int(h1[0])])
            sl, loss, t_exit = True, fill / P0 - 1 + R.SLIP, t1h
            out.update(src="1h_fallback", fill=fill)
        else:
            sl, t_exit = False, t0 + R.HOLD * R.H
            c = Cc[i]; fc = np.where(np.isfinite(c))[0]
            if np.isfinite(c[NM - 1]):
                px, out["src"] = float(c[NM - 1]), "c1m_last"
            elif len(fc):
                px, out["src"] = float(c[fc[-1]]), "c1m_ffill"
            else:
                px, out["src"] = pend, "c1h"
            ret = px / P0 - 1
            out["exit_rel_vs_1h"] = abs(px / pend - 1)
    _, _, f, _, _ = fund.window(r.sym, t0, int(t_exit))
    net = (-loss if sl else -ret) - R.FEE + f
    out.update(sl=sl, net=float(net), fund=float(f), loss=float(loss) if sl else None, t_exit=int(t_exit),
               sl1h=bool(len(h1)), t1h=int(t0 + (int(h1[0]) + 1) * R.H) if len(h1) else None)
    return out


def drop_top(v, frac=0.10):
    v = np.sort(np.asarray(v, float))[::-1]
    k = int(math.ceil(frac * len(v)))
    rest = v[k:]
    return dict(n_drop=k, mean=float(rest.mean()), median=float(np.median(rest)))


def arm_stats(df, col_net, col_sl, col_fund):
    g = df.copy()
    g["pnl"] = g[col_net]; g["sl"] = g[col_sl]; g["fund"] = g[col_fund]
    a = dict(all=R.summ(g), by_year={str(y): R.summ(g[g.year == y], year=y) for y in R.YEARS},
             drop_top10=drop_top(g.pnl.to_numpy()))
    x = a["all"]
    yp = [a["by_year"][str(y)].get("mean") for y in R.YEARS]
    G1 = bool(x["mean"] > 0 and x["ci_raw"][0] > 0 and x["ci_infl"][0] > 0)
    G2n = int(sum(1 for v in yp if v is not None and v > 0))
    G5v = a["drop_top10"]["mean"]
    a["GO"] = dict(G1=G1, G1_detail=dict(mean=x["mean"], ci_raw_lo=x["ci_raw"][0], ci_infl_lo=x["ci_infl"][0]),
                   G2=G2n >= 3, G2_years_pos=G2n, G3=bool(x["n"] >= 120), G3_n=x["n"],
                   G4=bool(x["excess_mean"] > 0), G4_excess=x["excess_mean"], G5=bool(G5v > G5_THR), G5_drop10_mean=G5v)
    a["GO"]["PASS"] = bool(G1 and a["GO"]["G2"] and a["GO"]["G3"] and a["GO"]["G4"] and a["GO"]["G5"])
    return a


def parse_sanity(idx, C, n2j, t_start, O, Hh, Cc):
    """SC: close phut cuoi moi gio vs CLOSES_1H; high >= max(open, close); ti le phut thieu (nhu slcheck)."""
    rel = []; viol = 0; tot = 0
    for (s, t0), i in idx.items():
        k0 = (t0 - t_start) // R.H; j = n2j[s]
        c1 = Cc[i, 59::60].astype(float); ch = C[k0 + 1:k0 + R.HOLD + 1, j].astype(float)
        ok = np.isfinite(c1) & np.isfinite(ch)
        rel.append(np.abs(c1[ok] / ch[ok] - 1))
        f = np.isfinite(Hh[i]) & np.isfinite(O[i]) & np.isfinite(Cc[i])
        viol += int((Hh[i][f] < np.maximum(O[i][f], Cc[i][f]) - 1e-9).sum()); tot += int(f.sum())
    rel = np.concatenate(rel)
    return dict(n_uniq=len(idx), frac_min_nan=float(np.isnan(Hh).mean()), n_hour_pairs=int(len(rel)),
                close_rel_med=float(np.median(rel)), close_frac_gt_1e4=float((rel > 1e-4).mean()),
                high_viol_frac=float(viol / max(tot, 1)))


def decomp(df):
    """Phan ra Delta mean (1m - 1h) theo nhom SL."""
    N = len(df); out = {}
    grp = {"sweep_1m_only": df.sl1m & ~df.sl1h_, "both_SL": df.sl1m & df.sl1h_,
           "none_SL": ~df.sl1m & ~df.sl1h_, "sl1h_only": ~df.sl1m & df.sl1h_}
    for k, m in grp.items():
        g = df[m]
        out[k] = dict(n=int(len(g)), net1h_mean=float(g.net1h.mean()) if len(g) else None,
                      net1m_mean=float(g.net1m.mean()) if len(g) else None,
                      contrib=float((g.net1m - g.net1h).sum() / N))
    out["total_delta"] = float((df.net1m - df.net1h).mean())
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t00 = time.time()
    C, names, t_start, finfo = R.load_hourly()
    fund = R.Fund()
    L, gap, S1, ucols, fl, lastc = R.find_listings(C, names, t_start, {})
    D, excl = R.build_arms(C, names, t_start, L, ucols, fund)
    n2j = {n: j for j, n in enumerate(names)}
    uniq = sorted({(r.sym, int(r.t0)) for arm in D for r in D[arm].itertuples()}, key=lambda x: x[1])
    O, Hh, Cc, miss = SC.fetch(uniq)
    idx = {u: i for i, u in enumerate(uniq)}
    res = dict(prereg=PREREG, params=dict(fee=R.FEE, sl=R.SL_X, slip=R.SLIP, hold_h=R.HOLD, infl=R.INFL, nrep=R.NREP,
                                          seed=R.SEED, g5_thr=G5_THR),
               sanity=dict(file=finfo, S1_excluded={k: len(v) for k, v in excl.items()},
                           n_trades={a: int(len(D[a])) for a in D}, rec_miss=miss))
    sc = parse_sanity(idx, C, n2j, t_start, O, Hh, Cc)
    log.info("SC parse %s", sc)
    assert sc["close_frac_gt_1e4"] < 0.01 and sc["high_viol_frac"] < 0.001, "SC FAIL: 1m parse sai"
    r2 = json.load(open(R2_JSON))
    r2pnl = {(t["sym"], int(t["t0"])): float(t["pnl"]) for t in r2["trades_D0"]}
    res["strategy"] = {}; res["strategy_1h"] = {}; res["decomp"] = {}
    SA, SCx, trades = {}, {}, {}
    for arm, df in D.items():
        rows = []
        for r in df.itertuples():
            i = idx[(r.sym, int(r.t0))]; j = n2j[r.sym]
            a1 = sim(r, C, j, t_start, fund, O, Hh, Cc, i, "1h")
            am = sim(r, C, j, t_start, fund, O, Hh, Cc, i, "1m")
            rows.append(dict(net1h=a1["net"], sl1h_=a1["sl"], fund1h=a1["fund"], net1m=am["net"], sl1m=am["sl"],
                             fund1m=am["fund"], src=am["src"], m=am["m"], gap=am["gap"], loss1m=am["loss"],
                             fill=am.get("fill"), open_m=am["open_m"], high_m=am["high_m"], t_exit1m=am["t_exit"],
                             t1h=am["t1h"], exit_rel=am.get("exit_rel_vs_1h")))
        X = pd.concat([df.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
        # SA: tai lap R2
        sa = dict(mean_1h=float(X.net1h.mean()), max_abs_vs_build_arms=float((X.net1h - X.pnl).abs().max()))
        if arm == "D0":
            dd = [abs(v - r2pnl[(s, int(t))]) for s, t, v in zip(X.sym, X.t0, X.net1h) if (s, int(t)) in r2pnl]
            sa.update(n_match_r2json=len(dd), max_abs_vs_r2json=float(max(dd)) if dd else None)
        SA[arm] = sa
        # SC (tiep): nhat quan 1h => 1m
        late = X[X.sl1h_ & (X.src == "1m") & (X.t_exit1m > X.t1h.fillna(0))]
        SCx[arm] = dict(src_counts={k: int(v) for k, v in X.src.value_counts().items()}, n_gap_fill=int(X.gap.sum()),
                        n_sl1h_not_sl1m=int((X.sl1h_ & ~X.sl1m).sum()), n_sl1m_later_than_1h=int(len(late)),
                        n_exit_rel_gt_1e4=int((X.exit_rel.fillna(0) > 1e-4).sum()),
                        sl_loss_mean=float(X.loss1m.dropna().mean()), sl_loss_p90=float(np.percentile(X.loss1m.dropna(), 90)),
                        sl_loss_max=float(X.loss1m.dropna().max()))
        res["strategy"][arm] = arm_stats(X, "net1m", "sl1m", "fund1m")
        res["strategy_1h"][arm] = arm_stats(X, "net1h", "sl1h_", "fund1h")
        res["decomp"][arm] = decomp(X)
        trades[arm] = X
        log.info("%s 1m mean %.4f 1h mean %.4f SA %s SC %s", arm, X.net1m.mean(), X.net1h.mean(), sa, SCx[arm])
    for arm in D:
        SA[arm]["r2_mean"] = float(r2["strategy"][arm]["all"]["mean"])
        SA[arm]["PASS"] = bool(abs(SA[arm]["mean_1h"] - SA[arm]["r2_mean"]) <= 0.0005 and SA[arm]["max_abs_vs_build_arms"] < 1e-9)
    assert all(SA[a]["PASS"] for a in SA), "SA FAIL: khong tai lap R2 1h %s" % SA
    # SB: 10 lenh SL-1m mau (D0)
    X = trades["D0"]; sl = X[X.src == "1m"].reset_index(drop=True)
    rng = np.random.default_rng(R.SEED)
    pick = sorted(rng.choice(len(sl), size=min(10, len(sl)), replace=False), key=lambda k: sl.t0.iloc[k])
    SB = []
    for k in pick:
        t = sl.iloc[k]; i = idx[(t.sym, int(t.t0))]; m = int(t.m); lvl = (1 + R.SL_X) * float(t.P0)
        prev = float(np.nanmax(Hh[i, :m])) if m > 0 and np.isfinite(Hh[i, :m]).any() else None
        kh = m // 60
        SB.append(dict(sym=t.sym, t0=str(pd.Timestamp(int(t.t0), unit="ms")), P0=float(t.P0), lvl=lvl,
                       sl_min_open_utc=str(pd.Timestamp(int(t.t0) + m * MIN, unit="ms")), m=m,
                       open=float(O[i, m]), high=float(Hh[i, m]), prev_max_high=prev, fill=float(t.fill), gap=bool(t.gap),
                       close1h_of_hour=float(C[int(t.k0) + 1 + kh, n2j[t.sym]]), sl1h=bool(t.sl1h_),
                       net1m=float(t.net1m), net1h=float(t.net1h)))
        log.info("SB %s", SB[-1])
    sd = {a: dict(r2_posthoc_mean=float(r2["posthoc_SL1m"][a]["mean_1m"]), r2b_mean=float(trades[a].net1m.mean()),
                  r2_posthoc_sl=float(r2["posthoc_SL1m"][a]["sl_rate_1m"]), r2b_sl=float(trades[a].sl1m.mean())) for a in D}
    res["sanity"].update(SA=SA, SB_samples=SB, SC_parse=sc, SC_consistency=SCx, SD_vs_r2_posthoc=sd)
    res["verdict"] = "GO" if any(a["GO"]["PASS"] for a in res["strategy"].values()) else "NO-GO"
    keep = ["sym", "D0", "t0", "P0", "year", "fallback", "ret7", "excess", "net1h", "sl1h_", "net1m", "sl1m", "fund1m",
            "src", "m", "gap", "loss1m"]
    res["trades"] = {a: trades[a][keep].round(6).to_dict("records") for a in D}
    md = write_md(res)
    open(OUT_MD, "w").write(md)
    json.dump(res, open(OUT_JSON, "w"), indent=1, ensure_ascii=False, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    log.info("WROTE %s + %s (%.0fs) verdict %s", OUT_JSON, OUT_MD, time.time() - t00, res["verdict"])
    print(md)


def write_md(res):
    pc, ci_s = R.pc, R.ci_s
    L = ["## Chiến lược — chuẩn SL 1m-high (net %/lệnh sau phí 0,112 + funding exact)", "",
         "| nhánh | n | net mean | net med | CI raw | CI inflate ×1,18 | win% | SL-rate | min | p5 | funding mean | excess mean/med | excess CI raw | bỏ top10% mean/med |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm, a in res["strategy"].items():
        x = a["all"]; d = a["drop_top10"]
        L.append("| %s | %d | **%s** | %s | %s | %s | %.1f | %.1f | %s | %s | %s | %s / %s | %s | %s / %s |" % (
            arm, x["n"], pc(x["mean"]), pc(x["median"]), ci_s(x["ci_raw"]), ci_s(x["ci_infl"]), 100 * x["win"], 100 * x["sl_rate"],
            pc(x["min"]), pc(x["p5"]), pc(x["fund_mean"], 3), pc(x["excess_mean"]), pc(x["excess_med"]), ci_s(x["excess_ci_raw"]),
            pc(d["mean"]), pc(d["median"])))
    L += ["", "## Theo năm (năm của t0, chuẩn 1m)", "", "| nhánh | năm | n | net mean | net med | CI raw | SL-rate | funding | excess |",
          "|---|---|---|---|---|---|---|---|---|"]
    for arm, a in res["strategy"].items():
        for y, b in a["by_year"].items():
            if not b.get("n"):
                L.append("| %s | %s | 0 | — | — | — | — | — | — |" % (arm, y)); continue
            L.append("| %s | %s | %d | %s | %s | %s | %.1f | %s | %s |" % (arm, y, b["n"], pc(b["mean"]), pc(b["median"]), ci_s(b["ci_raw"]),
                                                                       100 * b["sl_rate"], pc(b["fund_mean"], 3), pc(b["excess_mean"])))
    L += ["", "## Luật GO (G1–G5, chuẩn 1m)", "",
          "| nhánh | G1 (mean>0, lo raw>0, lo infl>0) | G2 (≥3/4 năm) | G3 (n≥120) | G4 (excess>0) | G5 (bỏ top10% > −0,5%) | PASS |",
          "|---|---|---|---|---|---|---|"]
    for arm, a in res["strategy"].items():
        g = a["GO"]
        L.append("| %s | %s (%s; %s; %s) | %s (%d/4) | %s (%d) | %s (%s) | %s (%s) | **%s** |" % (
            arm, g["G1"], pc(g["G1_detail"]["mean"]), pc(g["G1_detail"]["ci_raw_lo"]), pc(g["G1_detail"]["ci_infl_lo"]),
            g["G2"], g["G2_years_pos"], g["G3"], g["G3_n"], g["G4"], pc(g["G4_excess"]), g["G5"], pc(g["G5_drop10_mean"]), g["PASS"]))
    L += ["", "**VERDICT: %s**" % res["verdict"]]
    L += ["", "## So với R2 1h (cùng code, chế độ tắt 1m) — phần \"SL-convexity\" đã mất", "",
          "| nhánh | chuẩn | net mean | net med | CI raw | CI infl | SL-rate | năm dương | bỏ top10% mean |", "|---|---|---|---|---|---|---|---|---|"]
    for arm in res["strategy"]:
        for lab, key in (("1h (R2)", "strategy_1h"), ("1m (R2b)", "strategy")):
            a = res[key][arm]; x = a["all"]
            L.append("| %s | %s | %s | %s | %s | %s | %.1f | %d/4 | %s |" % (arm, lab, pc(x["mean"]), pc(x["median"]), ci_s(x["ci_raw"]),
                                                                          ci_s(x["ci_infl"]), 100 * x["sl_rate"], a["GO"]["G2_years_pos"],
                                                                          pc(a["drop_top10"]["mean"])))
    L += ["", "Phân rã Δmean (1m − 1h) theo nhóm lệnh:", "", "| nhánh | nhóm | n | net 1h mean | net 1m mean | đóng góp vào Δmean |", "|---|---|---|---|---|---|"]
    for arm, dd in res["decomp"].items():
        for k in ("sweep_1m_only", "both_SL", "none_SL", "sl1h_only"):
            v = dd[k]
            L.append("| %s | %s | %d | %s | %s | %s |" % (arm, k, v["n"], pc(v["net1h_mean"]), pc(v["net1m_mean"]), pc(v["contrib"])))
        L.append("| %s | **tổng Δ** | | | | **%s** |" % (arm, pc(dd["total_delta"])))
    L += ["", "## SB — 10 lệnh SL-1m mẫu (D0, seed 20260905)", "",
          "| sym | t0 | P0 | mức SL | phút SL (open UTC) | open | high | max high trước | fill | close 1h giờ đó | SL 1h? | net 1m | net 1h |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s in res["sanity"]["SB_samples"]:
        L.append("| %s | %s | %.6g | %.6g | %s | %.6g | %.6g | %s | %.6g | %.6g | %s | %s | %s |" % (
            s["sym"], s["t0"][:16], s["P0"], s["lvl"], s["sl_min_open_utc"][:16], s["open"], s["high"],
            "—" if s["prev_max_high"] is None else "%.6g" % s["prev_max_high"], s["fill"], s["close1h_of_hour"], s["sl1h"],
            pc(s["net1m"]), pc(s["net1h"])))
    return "\n".join(L)


if __name__ == "__main__":
    main()
