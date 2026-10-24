"""FEE0_RESCORE: S1/S7/S8 (BTC, ETH) - V1 (tai lap tang 1) + C_M0/C_M1(W5/15/30)/C_M2. Usage: f0_run.py v1 | s"""
import json, logging, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f0_common as F  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("f0")
DAYS = pd.date_range("2021-01-02", "2026-09-30", freq="D")
SIGN8 = {"BTC": -1, "ETH": -1}  # sign_from_E trong screen_result.json (a9fa0f46)


def trades(a, T):
    """trade list tu dinh nghia goc sw_run.py (cung phep tinh thoi gian). T = USDT 1m (tin hieu S8)."""
    rows = []
    for d in DAYS:
        t21, t23 = d + pd.Timedelta(hours=21), d + pd.Timedelta(hours=23)
        rows.append(("S1", F.ms(t21), F.ms(t23), 1, F.ms(t23.floor("D"))))
        et = pd.Timestamp(d.date()).tz_localize("America/New_York")
        if et.weekday() == 4:
            def u(h, m=0, base=et):
                return (base + pd.Timedelta(hours=h, minutes=m)).tz_convert("UTC").tz_localize(None)
            t_in, t_out = u(16), u(10, 0, et + pd.Timedelta(days=3))
            rows.append(("S7", F.ms(t_in), F.ms(t_out), 1, F.ms(t_out.floor("D"))))
    hh = (T.ts // 3_600_000) % 24; mm = (T.ts // F.MIN) % 60
    B = T[(mm == 0) & (hh % 4 == 0)]
    imb = (2 * B.tbv - B.vol) / B.vol
    ok = np.isfinite(imb) & (imb != 0)
    B, imb = B[ok], imb[ok]
    for t, v in zip(B.ts.to_numpy(np.int64), imb.to_numpy()):
        rows.append(("S8", t + F.MIN, t + 4 * 3_600_000, int(SIGN8[a] * np.sign(v)), (t // F.DAY) * F.DAY))
    return pd.DataFrame(rows, columns=["sig", "t_in", "t_out", "side", "day"])


def v1():
    """tai lap so tang 1: chi USDT-M, phi taker 0,05 % / maker 0,02 % moi chieu, funding chi S7 (nhu goc)."""
    ref = json.load(open(F.SCR + "/screen_result.json"))
    out = {}
    for a in ("BTC", "ETH"):
        T = F.load_usdt_m1(a)
        X = T[["ts", "high", "low", "close"]]
        fts, fr = F.load_funding(a + "USDT", None, None)
        tr = trades(a, T)
        A = F.px_at(X, tr.t_in.to_numpy()); Bp = F.px_at(X, tr.t_out.to_numpy())
        okp = np.isfinite(A) & np.isfinite(Bp)
        g = tr.side.to_numpy() * (Bp / A - 1)
        fu = tr.side.to_numpy() * F.fund_sum(fts, fr, tr.t_in.to_numpy(np.int64), tr.t_out.to_numpy(np.int64))
        for fee, tag in ((0.0005, "taker"), (0.0002, "maker")):
            for s in ("S1", "S7", "S8"):
                m = (tr.sig == s).to_numpy() & okp
                r = g[m] - 2 * fee - (fu[m] if s == "S7" else 0.0)
                o = F.split(F.daily(tr.day.to_numpy()[m], r, DAYS))
                key = f"{a}_{s}_{tag}"
                out[key] = {"E": round(o["E"]["sharpe"], 4), "C": round(o["C"]["sharpe"], 4), "n": int(m.sum())}
                if tag == "taker":
                    rr = ref["TS_" + a + "USDT"][s]
                    out[key]["ref_E"] = round(rr["E"]["sharpe"], 4); out[key]["ref_C"] = round(rr["C"]["sharpe"], 4); out[key]["ref_n"] = rr["n_trades"]
                log.info("V1 %s %s", key, out[key])
    json.dump(out, open(F.WK + "/v1.json", "w"), indent=1)


def s_family():
    res, D = {}, {}
    v4 = []
    for a in ("BTC", "ETH"):
        X, T, t_usdc = F.exec_frame(a)
        fts, fr = F.load_funding(a + "USDT", a + "USDC", t_usdc)
        hs = F.HS[a + "USDC"]
        tr = trades(a, T)
        log.info("%s exec frame %d bars, usdc from %s, hs %.4f bps, trades %s", a, len(X), pd.to_datetime(t_usdc, unit="ms"), hs * 1e4, tr.sig.value_counts().to_dict())
        for s in ("S1", "S7", "S8"):
            t = tr[tr.sig == s].reset_index(drop=True)
            c = F.costs(t, X, fts, fr, hs)
            key = f"{s}_{a}"; res[key] = {}
            per = {"E": (t.t_in >= F.ms(F.E0)) & (t.t_in < F.ms("2024-01-01")), "C": (t.t_in >= F.ms(F.C0)) & (t.t_in < F.ms("2026-10-01"))}
            for mdl in ("gross", "M0", "M1_W5", "M1_W15", "M1_W30", "M2"):
                dser = F.daily(t.day.to_numpy(), c[mdl], DAYS)
                D[f"{key}|{mdl}"] = dser
                res[key][mdl] = F.split(dser)
            for w in (5, 15, 30):
                res[key][f"fill_W{w}"] = {p: float(c[f"fill_W{w}"][m.to_numpy()].mean()) for p, m in per.items()}
            res[key]["n_trades"] = {p: int(m.sum()) for p, m in per.items()}
            res[key]["fund_mean_bps"] = float(np.nanmean(c["fund"]) * 1e4)
            res[key]["gross_mean_bps"] = {p: float(np.nanmean(c["gross"][m.to_numpy()]) * 1e4) for p, m in per.items()}
            res[key]["frac_exec_usdc_C"] = float((t.t_in[per["C"]] >= t_usdc).mean())
            if s in ("S1", "S7") and a == "BTC":
                rng = np.random.default_rng(20261024)
                for k in rng.choice(np.where(per["C"].to_numpy())[0], 3 if s == "S1" else 2, replace=False):
                    v4.append({"sig": key, "t_in": int(t.t_in[k]), "t_out": int(t.t_out[k]), "side": int(t.side[k]),
                               "fill_W15": bool(c["fill_W15"][k]), "r_M1": None if np.isnan(c["M1_W15"][k]) else float(c["M1_W15"][k])})
            log.info("%s M1 E %+.2f C %+.2f | M2 E %+.2f C %+.2f | M0 E %+.2f C %+.2f | fill15 %s", key,
                     res[key]["M1_W15"]["E"]["sharpe"], res[key]["M1_W15"]["C"]["sharpe"], res[key]["M2"]["E"]["sharpe"], res[key]["M2"]["C"]["sharpe"],
                     res[key]["M0"]["E"]["sharpe"], res[key]["M0"]["C"]["sharpe"], res[key]["fill_W15"])
    pd.DataFrame(D).to_parquet(F.WK + "/s_daily.parquet")
    json.dump(res, open(F.WK + "/s_res.json", "w"), indent=1)
    json.dump(v4, open(F.WK + "/v4_pick.json", "w"), indent=1)


if __name__ == "__main__":
    {"v1": v1, "s": s_family}[sys.argv[1]]()
