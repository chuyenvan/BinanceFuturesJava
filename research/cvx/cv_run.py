"""CVX tang 1 (PREREG_CVX.md b01558e1). Chay sau cv_data.py. Output ~/claude_master/1016/cvx/cvx_result.json"""
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("cvx")
W = os.path.expanduser("~/claude_master/1016/cvx")
SW = os.path.expanduser("~/claude_master/1016/screen")
E0, E1, C0, C1 = "2021-03-01", "2023-12-31", "2024-01-01", "2026-09-30"
FEE = 0.0005
RES = {}

D = pd.read_parquet(SW + "/d1.parquet")
C = D.pivot(index="day", columns="sym", values="close").sort_index()
Q = D.pivot(index="day", columns="sym", values="qv").reindex(C.index)
FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
CF = C.ffill()
first = C.apply(lambda s: s.first_valid_index())
qv30 = Q.rolling(30, min_periods=20).median()


def st(r, ann):
    r = r.dropna()
    if len(r) < 10 or r.std() == 0:
        return {"sh": 0.0, "ann": 0.0, "maxdd": 0.0, "n": int(len(r))}
    eq = (1 + r).cumprod()
    return {"sh": float(r.mean() / r.std() * np.sqrt(ann)), "ann": float(r.mean() * ann), "maxdd": float((eq / eq.cummax() - 1).min()), "n": int(len(r))}


def split(r, ann):
    return {"E": st(r[(r.index >= E0) & (r.index <= E1)], ann), "C": st(r[(r.index >= C0) & (r.index <= C1)], ann)}


def survive(s):
    e, c = s["E"]["sh"], s["C"]["sh"]
    return bool(e > 0.5 and c > 0.5 and np.sign(e) == np.sign(c) and s["C"]["ann"] > 0)


def ic(x, y):
    j = pd.concat([x, y], axis=1).dropna()
    out = {}
    for tag, a, b in (("E", E0, E1), ("C", C0, C1)):
        k = j[(j.index >= a) & (j.index <= b)]
        out[tag] = [float(spearmanr(k.iloc[:, 0], k.iloc[:, 1])[0]) if len(k) > 30 else None, int(len(k))]
    return out


def daily_ts(pos_d, ret_d, fund_d):
    """pos_d[d] = vi the trong ngay d (quyet dinh o close d-1)."""
    pos_d = pos_d.reindex(ret_d.index).fillna(0.0)
    pnl = pos_d * ret_d - FEE * pos_d.diff().abs().fillna(pos_d.abs()) - pos_d * fund_d
    return pnl


def perp_hourly(sym):
    M = pd.read_parquet(f"{SW}/m1_{sym}.parquet").close
    return M.resample("1h").last()


def cv1(asset):
    bn = pd.read_parquet(f"{W}/bn_spot_1h_{asset}USDT.parquet").close
    cb = pd.read_parquet(f"{W}/cb_1h_{asset}-USD.parquet").close
    H = pd.date_range("2021-01-01", "2026-09-30 23:00", freq="1h")
    bn, cb = bn.reindex(H), cb.reindex(H)
    chk = {"cov_cb": float(cb.notna().mean()), "cov_bn": float(bn.notna().mean())}
    CP = np.log(cb / bn)
    chk["med_abs_cp"] = float(CP.abs().median())
    chk["corr_ret"] = float(np.log(cb).diff().corr(np.log(bn).diff()))
    CPd = CP - CP.rolling(168, min_periods=150).mean()
    px = perp_hourly(asset + "USDT").reindex(H)
    r1 = px.shift(-1) / px - 1                      # gio t -> t+1 (sau moc tin hieu t)
    r4 = px.shift(-4) / px - 1
    fund_h = FD[asset + "USDT"].reindex(H.floor("D")).values / 24.0
    fund_h = pd.Series(fund_h, index=H)
    out = {"check": chk, "IC1h": ic(CPd, r1), "IC4h_nonoverlap": ic(CPd[H.hour % 4 == 3], r4[H.hour % 4 == 3])}
    # CV1a gio
    pos = (CPd > 0).astype(float).where(CPd.notna(), 0.0)
    pnl_h = pos * r1 - FEE * pos.diff().abs().fillna(0.0) - pos * fund_h.shift(-1).fillna(0.0)
    pnl_d = pnl_h.groupby(pnl_h.index.floor("D")).sum()   # gan PnL vao ngay cua gio bat dau giu (xap xi)
    out["CV1a"] = split(pnl_d, 365)
    out["CV1a_turn_per_day"] = float(pos.diff().abs().groupby(pos.index.floor("D")).sum().mean())
    # CV1b ngay
    dm = CPd.groupby(CPd.index.floor("D")).mean()       # trung binh 24 gio cua ngay d (toi close 24:00)
    Cd = C[asset + "USDT"]
    rd = Cd / Cd.shift(1) - 1
    pos_d = (dm > 0).astype(float).where(dm.notna(), 0.0).shift(1)   # tin hieu ngay d-1 -> giu ngay d
    out["CV1b"] = split(daily_ts(pos_d, rd, FD[asset + "USDT"]), 365)
    dd = dm.shift(0)
    out["IC24h_nonoverlap"] = ic(dd, rd.shift(-1))
    out["bh"] = split(rd, 365)
    return out


def cv2():
    U = pd.read_parquet(W + "/upbit_1d.parquet")
    ub = U[U.sym == "BTCUSDT"].set_index("day").close_krw.reindex(C.index)
    bnb = C["BTCUSDT"]
    KP = np.log(ub / bnb)
    chk = {"cov_upbit_btc": float(ub[(ub.index >= "2021-01-01")].notna().mean()),
           "kp_in_range": float(((KP > -0.10) & (KP < 0.25))[KP.notna()].mean())}
    fx_implied = (ub / bnb)
    KPd = KP - KP.shift(1).rolling(30, min_periods=25).median()
    chk["kpd_in_range"] = float(((KPd > -0.10) & (KPd < 0.25))[KPd.notna()].mean())   # Addendum 1: D3 thay the
    rd = bnb / bnb.shift(1) - 1
    out = {"check": chk, "IC1d": ic(KPd, rd.shift(-1))}
    sun = KPd[KPd.index.weekday == 6]
    r7 = bnb.shift(-7) / bnb - 1
    out["IC7d_nonoverlap"] = ic(sun, r7[r7.index.weekday == 6])
    pos_a = (KPd < 0).astype(float).where(KPd.notna(), 0.0).shift(1)
    out["CV2a"] = split(daily_ts(pos_a, rd, FD["BTCUSDT"]), 365)
    # CV2b: Chu nhat quyet, giu 7 ngay Thu Hai..Chu nhat
    sig = (KPd < 0).astype(float).where(KPd.notna(), 0.0)
    wk = sig.where(sig.index.weekday == 6).ffill()      # gia tri cua Chu nhat gan nhat (toi close Chu nhat)
    pos_b = wk.shift(1)                                  # ngay Thu Hai dung tin hieu Chu nhat
    out["CV2b"] = split(daily_ts(pos_b, rd, FD["BTCUSDT"]), 365)
    out["kp_median_by_year"] = {int(k): round(float(v), 4) for k, v in KP.groupby(KP.index.year).median().items()}
    return out, fx_implied


def xs(F, ca=0.001, cb=0.0006, min_n=20, q=10):
    """F: day x sym, feature tai close ngay s. Long decile F THAP (gia thuyet CV3/CV4). Vao close s+1, thoat close s+8."""
    sdays = [d for d in C.index if d.weekday() == 6 and d >= pd.Timestamp("2021-02-28") and d + pd.Timedelta(days=8) <= pd.Timestamp(C1)]
    rows, pL, pS = [], set(), set()
    for s in sdays:
        ent = s + pd.Timedelta(days=1); ex = ent + pd.Timedelta(days=7)
        assert s < ent < ex
        age_ok = first[first <= ent - pd.Timedelta(days=60)].index
        u = qv30.loc[s]; u = u[u >= 20e6].index.intersection(age_ok)
        f = F.loc[s].reindex(u).dropna() if s in F.index else pd.Series(dtype=float)
        f = f[[x for x in f.index if not math.isnan(C.at[ent, x])]]
        if len(f) < min_n:
            continue
        ret = CF.loc[ex, f.index] / C.loc[ent, f.index] - 1
        fs = FD.loc[ent + pd.Timedelta(days=1):ex, f.index].sum()
        n = max(3, len(f) // q)
        lo = list(f.nsmallest(n).index); hi = list(f.nlargest(n).index)
        toL = 1 - len(set(lo) & pL) / n; toS = 1 - len(set(hi) & pS) / n
        pL, pS = set(lo), set(hi)
        rL = ret[lo].mean(); fL = fs[lo].mean()
        rB = CF.at[ex, "BTCUSDT"] / C.at[ent, "BTCUSDT"] - 1
        fB = FD.loc[ent + pd.Timedelta(days=1):ex, "BTCUSDT"].sum()
        h0 = rL - fL - toL * 2 * ca
        loh = h0 - rB + fB - abs(rL - rB) * cb
        ls = h0 - ret[hi].mean() + fs[hi].mean() - toS * 2 * ca
        exc = h0 - ret.mean()
        rows.append((ent, loh, ls, exc, len(f), toL))
    df = pd.DataFrame(rows, columns=["t", "LOH", "LS", "EXC", "n", "to"]).set_index("t")
    return df


def summ_xs(df, F):
    # IC tuan: feature Chu nhat vs loi suat vao->thoat (khong chong)
    o = {"LOH": split(df.LOH, 52), "LS": split(df.LS, 52), "EXC_ref": split(df.EXC, 52), "weeks": int(len(df)),
         "n_min": int(df.n.min()) if len(df) else 0, "n_med": float(df.n.median()) if len(df) else 0, "to": float(df.to.mean()) if len(df) else 0}
    return o


def cv3(fx):
    U = pd.read_parquet(W + "/upbit_1d.parquet")
    U["px"] = U.close_krw * U.fac
    P = U.pivot(index="day", columns="sym", values="px").reindex(C.index)
    T = U.pivot(index="day", columns="sym", values="turnover_krw").reindex(C.index)
    syms = [s for s in P.columns if s in C.columns]
    lr = np.log(P[syms] / C[syms]).sub(np.log(fx), axis=0)          # ln(Up_i/BN_i) - ln(Up_BTC/BN_BTC)
    # Addendum 1: loc ghep sai token (co hoc, theo do hop le du lieu)
    ru = np.log(P[syms]).diff(); rb = np.log(C[syms]).diff()
    bad = [s for s in syms if lr[s].abs().median() > 0.05 or ru[s].corr(rb[s]) < 0.80]
    lr = lr.drop(columns=bad).where(lambda x: x.abs() <= 0.50)
    syms = [s for s in syms if s not in bad]
    RP = lr.rolling(7, min_periods=7).mean()
    tu = T[syms].div(fx, axis=0).where(lr.notna())                    # KRW -> USDT theo ty gia ngam
    A = tu.rolling(7, min_periods=7).sum() / Q[syms].rolling(7, min_periods=7).sum()
    rp_sun = RP[RP.index.weekday == 6]
    chk = {"rp_abs_median": float(lr.abs().stack().median()), "rp_abs_p99": float(lr.abs().stack().quantile(0.99)), "excluded": bad}
    return {"check": chk, "CV3": summ_xs(xs(RP), RP), "CV3b": summ_xs(xs(A), A), "n_sym_upbit": len(syms),
            "rp_sun_obs": int(rp_sun.notna().sum().sum())}


def cv4():
    B = pd.read_parquet(W + "/bybit_funding.parquet")
    BD = B.groupby(["day", "sym"]).rate.sum().unstack().reindex(C.index)
    syms = [s for s in BD.columns if s in C.columns]
    have = BD[syms].notna().astype(float).rolling(7).sum() == 7
    diff = (FD[syms] - BD[syms].fillna(0.0)).rolling(7).sum().where(have)
    j = pd.concat([FD["BTCUSDT"].rename("bn"), BD["BTCUSDT"].rename("by")], axis=1).dropna()
    chk = {"corr_btc_funding": float(j.bn.corr(j.by)), "n_sym": len(syms), "fd_abs_median": float(diff.abs().stack().median())}
    return {"check": chk, "CV4": summ_xs(xs(diff), diff)}


def main():
    res = {"BTC": cv1("BTC"), "ETH_ref": cv1("ETH")}
    c2, fx = cv2()
    res["KIMCHI"] = c2
    res["UPBIT_XS"] = cv3(fx)
    res["FUND_XS"] = cv4()
    ch = res["BTC"]["check"]
    D = {"D1": ch["cov_cb"] >= 0.99 and ch["cov_bn"] >= 0.995,
         "D2": ch["med_abs_cp"] < 0.01 and ch["corr_ret"] > 0.99,
         "D3": c2["check"]["cov_upbit_btc"] >= 0.99 and c2["check"]["kpd_in_range"] >= 0.99,
         "D4": res["FUND_XS"]["check"]["corr_btc_funding"] > 0.7,
         "D5": res["UPBIT_XS"]["CV3"]["weeks"] >= 200 and res["FUND_XS"]["CV4"]["weeks"] >= 200}
    res["data_checks"] = {k: bool(v) for k, v in D.items()}
    tests = {"CV1a": res["BTC"]["CV1a"], "CV1b": res["BTC"]["CV1b"], "CV2a": c2["CV2a"], "CV2b": c2["CV2b"],
             "CV3-LO": res["UPBIT_XS"]["CV3"]["LOH"], "CV3-LS": res["UPBIT_XS"]["CV3"]["LS"],
             "CV3b-LO": res["UPBIT_XS"]["CV3b"]["LOH"], "CV3b-LS": res["UPBIT_XS"]["CV3b"]["LS"],
             "CV4-LO": res["FUND_XS"]["CV4"]["LOH"], "CV4-LS": res["FUND_XS"]["CV4"]["LS"]}
    res["survive"] = {k: survive(v) for k, v in tests.items()}
    for k, v in tests.items():
        log.info("%-8s E Sh %+.2f ann %+.1f%% | C Sh %+.2f ann %+.1f%% maxdd %.2f | song=%s", k, v["E"]["sh"], 100 * v["E"]["ann"],
                 v["C"]["sh"], 100 * v["C"]["ann"], v["C"]["maxdd"], res["survive"][k])
    log.info("DATA %s", res["data_checks"])
    log.info("BTC checks %s | IC1h %s | IC4h %s | IC24h %s | turn/ngay CV1a %.2f | BH %s", ch, res["BTC"]["IC1h"], res["BTC"]["IC4h_nonoverlap"],
             res["BTC"]["IC24h_nonoverlap"], res["BTC"]["CV1a_turn_per_day"], {k: round(v["sh"], 2) for k, v in res["BTC"]["bh"].items()})
    e = res["ETH_ref"]
    log.info("ETH ref CV1a E %+.2f C %+.2f | CV1b E %+.2f C %+.2f | IC24h %s", e["CV1a"]["E"]["sh"], e["CV1a"]["C"]["sh"], e["CV1b"]["E"]["sh"], e["CV1b"]["C"]["sh"], e["IC24h_nonoverlap"])
    log.info("KIMCHI check %s | IC1d %s | IC7d %s | KP median/nam %s", c2["check"], c2["IC1d"], c2["IC7d_nonoverlap"], c2["kp_median_by_year"])
    for k in ("CV3", "CV3b"):
        x = res["UPBIT_XS"][k]
        log.info("%s weeks %d n_min %d n_med %.0f TO %.2f | EXC_ref E %+.2f C %+.2f", k, x["weeks"], x["n_min"], x["n_med"], x["to"], x["EXC_ref"]["E"]["sh"], x["EXC_ref"]["C"]["sh"])
    x = res["FUND_XS"]["CV4"]
    log.info("CV4 weeks %d n_min %d n_med %.0f TO %.2f | EXC_ref E %+.2f C %+.2f | check %s | upbit check %s", x["weeks"], x["n_min"], x["n_med"], x["to"],
             x["EXC_ref"]["E"]["sh"], x["EXC_ref"]["C"]["sh"], res["FUND_XS"]["check"], res["UPBIT_XS"]["check"])
    json.dump(res, open(W + "/cvx_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
