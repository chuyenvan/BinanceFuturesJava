"""REX Buoc 1 (PREREG_REX_S1.md): selector LightGBM walk-forward theo quy. KHONG doc day >= 2026-01-01."""
import json
import logging
import os
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/rex"))
import rex_s0 as R0  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("rex1")
OUT = R0.OUT
HO = pd.Timestamp("2026-01-01")
DEV0, DEV1, VAL0, VAL1 = pd.Timestamp("2022-01-01"), pd.Timestamp("2024-12-31"), pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
PAR = dict(objective="regression", num_leaves=15, min_data_in_leaf=500, learning_rate=0.03, n_estimators=300,
           feature_fraction=0.7, bagging_fraction=0.7, bagging_freq=1, lambda_l2=10.0, verbose=-1, n_jobs=4)
FSETS = {"A": list("abcde"), "B": list("abcdef"), "C": list("abcdefg")}


def feats(fs):
    return ["r_" + c for fam in FSETS[fs] for c in R0.FAM[fam]]


def load():
    P = pd.read_parquet(OUT + "/panel.parquet")
    P = P[P.day < HO].reset_index(drop=True)
    assert P.day.max() < HO
    return P


def walk(P, h, fs):
    X = feats(fs); tgt = f"rk{h}"
    out = []
    for q in pd.period_range("2022Q1", "2025Q4", freq="Q"):
        q0 = q.start_time.normalize(); q1 = q.end_time.normalize()
        tr = P[(P.day >= "2021-03-01") & (P.day <= q0 - pd.Timedelta(days=h + 1)) & P[tgt].notna()]
        te = P[(P.day >= q0) & (P.day <= q1)]
        assert tr.day.max() + pd.Timedelta(days=h) < q0
        pr = np.zeros(len(te))
        for sd in (1, 2, 3):
            m = lgb.LGBMRegressor(random_state=sd, **PAR)
            m.fit(tr[X], tr[tgt] - 0.5)
            pr += m.predict(te[X]) / 3
        out.append(pd.DataFrame({"day": te.day.values, "sym": te.sym.values, "score": pr}))
    return pd.concat(out, ignore_index=True)


def nw_t(x, lag):
    x = np.asarray(x, float); x = x[~np.isnan(x)]; n = len(x); mu = x.mean(); e = x - mu
    v = (e @ e) / n
    for k in range(1, lag + 1):
        v += 2 * (1 - k / (lag + 1)) * (e[k:] @ e[:-k]) / n
    return float(mu / np.sqrt(v / n))


def daily_ic(df, score, y):
    g = df[[ "day", score, y]].dropna()
    g = g.assign(a=g.groupby("day")[score].rank(), b=g.groupby("day")[y].rank())
    return g.groupby("day").apply(lambda z: z.a.corr(z.b) if len(z) >= 20 else np.nan).dropna()


def ic_stats(ic, h, a, b):
    s = ic[(ic.index >= a) & (ic.index <= b)]
    mo = s.groupby(s.index.to_period("M")).mean()
    return {"mean": float(s.mean()), "t_nw": nw_t(s.values, h), "pos_month": float((mo > 0).mean()), "n_days": int(len(s)),
            "by_year": {int(k): round(float(v), 4) for k, v in s.groupby(s.index.year).mean().items()}}


def wide_px():
    D = pd.read_parquet(R0.S.W + "/d1.parquet", columns=["sym", "day", "close", "fund_day"])
    C = D.pivot(index="day", columns="sym", values="close").sort_index()
    FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
    CF = C.ffill()
    RET = (CF / CF.shift(1) - 1).fillna(0.0)          # loi suat close t-1 -> t (sau delist = 0)
    return RET, FD


def portfolio(pred, P, h, RET, FD, k=10, ca=0.001):
    """h tranche: moi ngay t mua top-k bang 1/h von, giu h ngay. Tra ve loi suat ngay t+1 (close t -> t+1)."""
    days = sorted(pred.day.unique())
    top = pred.sort_values("score", ascending=False).groupby("day").head(k)
    W1 = pd.crosstab(top.day, top.sym).astype(float) / k            # trong so EW cua top-k quyet dinh ngay t
    W1 = W1.reindex(index=pd.DatetimeIndex(days), columns=RET.columns, fill_value=0.0)
    W = W1.rolling(h, min_periods=1).sum() / h                         # danh muc giu tu close t
    nxt = RET.shift(-1).reindex(W.index)                               # loi suat t -> t+1
    fn = FD.shift(-1).reindex(W.index)
    gross = (W * nxt).sum(axis=1)
    turn = W.diff().abs().sum(axis=1).fillna(W.iloc[0].abs().sum())
    net = gross - turn * ca - (W * fn).sum(axis=1)
    uni = P.groupby("day").y1.mean().reindex(W.index)
    btc = nxt["BTCUSDT"]
    df = pd.DataFrame({"net": net, "exc": net - uni, "excb": net - btc, "turn": turn})
    df.index = df.index + pd.Timedelta(days=1)                         # gan vao ngay t+1
    return df.dropna()


def sstats(r, a, b):
    s = r[(r.index > a) & (r.index <= b + pd.Timedelta(days=1))]
    if len(s) < 30 or s.std() == 0:
        return {"sh": 0.0}
    eq = (1 + s).cumprod()
    return {"sh": float(s.mean() / s.std() * np.sqrt(365)), "ann": float(s.mean() * 365), "maxdd": float((eq / eq.cummax() - 1).min()),
            "by_year_sh": {int(y): round(float(g.mean() / g.std() * np.sqrt(365)), 2) for y, g in s.groupby(s.index.year) if len(g) > 30}}


def deciles(pred, P, h, a, b):
    j = pred.merge(P[["day", "sym", f"yx{h}"]], on=["day", "sym"])
    j = j[(j.day >= a) & (j.day <= b)].dropna()
    j["dec"] = j.groupby("day").score.transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    return [round(float(v), 5) for v in j.groupby("dec")[f"yx{h}"].mean().values]


def main():
    P = load()
    RET, FD = wide_px()
    res = {"baseline": {}, "variants": {}}
    dev = P[(P.day >= DEV0) & (P.day <= DEV1)]
    allf = feats("C")
    for h in (1, 3, 7):
        rows = []
        for c in allf:
            ic = daily_ic(dev, c, f"y{h}")
            rows.append((c, float(ic.mean()), nw_t(ic.values, h), {int(k): round(float(v), 4) for k, v in ic.groupby(ic.index.year).mean().items()}))
        rows.sort(key=lambda r: -abs(r[1]))
        res["baseline"][h] = rows[:8]
        for r in rows[:8]:
            log.info("BASE h%d %-10s IC %+.4f t %+.2f %s", h, *r)
    preds = {}
    for fs in ("A", "B", "C"):
        for h in (1, 3, 7):
            name = f"{fs}{h}"
            pr = walk(P, h, fs)
            preds[name] = pr
            j = pr.merge(P[["day", "sym", f"y{h}"]], on=["day", "sym"])
            ic = daily_ic(j, "score", f"y{h}")
            pf = portfolio(pr[pr.day <= DEV1], P, h, RET, FD)
            v = {"ic_dev": ic_stats(ic, h, DEV0, DEV1), "dec_dev": deciles(pr, P, h, DEV0, DEV1),
                 "pf_dev": {k: sstats(pf[k], DEV0, DEV1) for k in ("net", "exc", "excb")}, "turn": float(pf.turn.mean())}
            res["variants"][name] = v
            log.info("VAR %s IC %+.4f t %+.2f pos_m %.2f yr %s | top10 exc Sh %+.2f %s | excb %+.2f | net %+.2f | turn %.2f | dec %s", name,
                     v["ic_dev"]["mean"], v["ic_dev"]["t_nw"], v["ic_dev"]["pos_month"], v["ic_dev"]["by_year"],
                     v["pf_dev"]["exc"]["sh"], v["pf_dev"]["exc"].get("by_year_sh"), v["pf_dev"]["excb"]["sh"], v["pf_dev"]["net"]["sh"], v["turn"], v["dec_dev"])
            json.dump(res, open(OUT + "/s1_result.json", "w"), indent=1, default=str)
    win = max(res["variants"], key=lambda k: res["variants"][k]["ic_dev"]["t_nw"])
    h = int(win[1:]); v = res["variants"][win]; pr = preds[win]
    best_base = abs(res["baseline"][h][0][1])
    j = pr.merge(P[["day", "sym", f"y{h}"]], on=["day", "sym"])
    ic = daily_ic(j, "score", f"y{h}")
    pf = portfolio(pr, P, h, RET, FD)
    val = {"ic": ic_stats(ic, h, VAL0, VAL1), "pf": {k: sstats(pf[k], VAL0, VAL1) for k in ("net", "exc", "excb")}, "dec": deciles(pr, P, h, VAL0, VAL1)}
    G = {"G1": v["ic_dev"]["mean"] > 0 and v["ic_dev"]["t_nw"] >= 3,
         "G2": all(v["ic_dev"]["by_year"].get(y, -1) > 0 for y in (2022, 2023, 2024)),
         "G3": v["ic_dev"]["pos_month"] >= 0.65,
         "G4": v["pf_dev"]["exc"]["sh"] >= 1.0 and all(v["pf_dev"]["exc"]["by_year_sh"].get(y, -1) > 0 for y in (2022, 2023, 2024)),
         "G5": val["ic"]["mean"] > 0 and val["ic"]["t_nw"] >= 2 and val["pf"]["exc"].get("ann", -1) > 0}
    res["winner"] = {"name": win, "gates": {k: bool(x) for k, x in G.items()}, "val": val,
                     "model_vs_best_single": float(v["ic_dev"]["mean"] / best_base) if best_base else None,
                     "verdict": "GO" if all(G.values()) else "NO-GO"}
    log.info("WINNER %s | gates %s | VAL IC %+.4f t %+.2f yr %s | VAL top10 exc %s excb %s net %s | dec %s | model/base %.2f | %s", win, res["winner"]["gates"],
             val["ic"]["mean"], val["ic"]["t_nw"], val["ic"]["by_year"], val["pf"]["exc"], val["pf"]["excb"]["sh"], val["pf"]["net"]["sh"], val["dec"],
             res["winner"]["model_vs_best_single"] or 0, res["winner"]["verdict"])
    pr.to_parquet(OUT + "/pred_s1.parquet")
    for k, p in preds.items():
        p.to_parquet(OUT + f"/pred_s1_{k}.parquet")
    pf.to_csv(OUT + "/s1_winner_pf.csv")
    json.dump(res, open(OUT + "/s1_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
