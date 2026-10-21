#!/usr/bin/env python3
"""TSX_V2 Phase A2/A3 (MO TA, khong chon): tran tren oracle + ho so hoi phuc. Chi DEV, nguon = run X14 8 seed.
Dinh nghia (co dinh TRUOC khi tinh, dung lai o prereg B2):
  mark = tick dau tien tuoi > 168h; P_mark = min(open, close) nen mark; F = gia leg dau.
  loss = 1 - P_mark / F (lo gia coin tu leg dau; = lo cum khi 1 leg); mkt = 1 - exp(EW(mark) - EW(t0)) (ALT_EW giam cung ky,
  EW = cumsum log-ret 1m edge_attr/index.npz, lay phut <= t); rho = loss / mkt (mkt <= 0 -> rho = +inf; loss <= 0 -> rho = 0).
  H504 = giu (hoan) MOI ngay toi 504h, arm/trailing nhu sim; oracle = max(PnL cat tai tick bat ky trong [mark, min(thoat H504, 504h+1')],
  PnL thoat H504). Sau thoi diem thoat cua run X14 khong biet leg DCA -> dong bang.
"""
import json
import logging
import sys

import numpy as np
import pandas as pd

import common as CM
import engine as EN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("A")
OUTD = CM.D + "/out"


def ew_at(ts, L, t_ms):
    i = np.searchsorted(ts, t_ms, side="right") - 1
    return L[np.clip(i, 0, len(L) - 1)]


def main():
    C, keys, arr, fund = CM.load_all()
    tk = CM.ticks()
    nof = CM.nofund_syms(C)
    W = CM.Wins(keys, arr, fund, tk, True, nof)
    eod = CM.ew_eod()
    days, ok = CM.base_flags_check(eod)
    assert ok
    dset = CM.dayints(days)
    dd30 = CM.dd_series(eod, 30)
    eps = CM.episodes(eod)
    ets, eL = CM.ew_minute()
    X = C[C["arm"] == "X14"].reset_index(drop=True)
    rows = []
    for r in X.itertuples():
        w = W.get(r.wid)
        rx = EN.replay(w, r.legs, dayset=dset, cap_j=CM.CAP504)
        rp = EN.replay(w, r.legs)
        rh = EN.replay(w, r.legs, all_days=True, cap_j=CM.CAP504, want_path=True)
        mi = rx["mark_i"]
        mark_ms = r.t0_ms + int(w.vj[mi]) * 60000
        mday = pd.Timestamp(mark_ms // 86400000 * 86400000, unit="ms")
        pm = float(w.cut_px[mi])
        F = r.legs[0][1]
        loss = 1 - pm / F
        mkt = 1 - np.exp(ew_at(ets, eL, mark_ms) - ew_at(ets, eL, r.t0_ms))
        rho = 0.0 if loss <= 0 else (np.inf if mkt <= 0 else loss / mkt)
        spd7 = float(ew_at(ets, eL, mark_ms) - ew_at(ets, eL, mark_ms - 7 * 86400000))
        o = dict(seed=r.seed, sym=r.sym, te=r.te, t0=r.t0, wid=r.wid, n=r.n, st=r.st, pnl_src=r.pnl,
                 pnl_x14=rx["pnl"], st_x14=rx["st"], j_x14=rx["j"], pnl_cut=rp["pnl"], pnl_h504=rh["pnl"], st_h504=rh["st"],
                 j_h504=rh["j"], open_h504=rh["open"], armed_pre=rx["armed_pre"], deferred=rx["deferred"],
                 mark_day=mday, on=bool(np.isin(mark_ms // 86400000, dset)), dd_prev=float(dd30.get(mday - pd.Timedelta(days=1), np.nan)),
                 loss=loss, mkt=float(mkt), rho=float(rho), spd7=spd7, notional=sum(e * q for _, e, q in r.legs))
        if not rx["armed_pre"]:
            ex = rh["ex_i"] if rh["ex_i"] is not None else len(w.vj) - 1
            i504 = int(np.searchsorted(w.vj, CM.CAP504 + 1, side="right")) - 1
            iend = min(ex - 1 if rh["ex_i"] is not None else ex, i504)
            idx, val = EN.cut_values(w, r.legs if True else r.legs, rh, mi, max(iend, mi))
            # leg DCA sau thoi diem thoat X14 khong biet -> legs cua cum la tat ca leg (deu < thoat X14)
            best_cut = float(val.max()) if len(val) else -np.inf
            bi = int(idx[int(np.argmax(val))]) if len(val) else mi
            cands = [best_cut]
            if np.isfinite(rh["pnl"]) and rh["j"] <= CM.CAP504 + 1 + 0:
                cands.append(rh["pnl"])
            orc = max(cands)
            if orc == rh["pnl"] and rh["pnl"] > best_cut:
                tb = (rh["j"] - EN.MARK) / 60.0
            else:
                tb = (int(w.vj[bi]) - EN.MARK) / 60.0
            o.update(oracle=orc, t_best_h=tb, v_mark=float(val[0]) if len(val) else np.nan)
        rows.append(o)
    A = pd.DataFrame(rows)
    A["year"] = A["mark_day"].dt.year
    A["ep"] = [next((i for i, (a, b) in enumerate(eps) if a <= d <= b), -1) for d in A["mark_day"]]
    A["ep_lab"] = [("%s..%s" % (eps[e][0].strftime("%Y-%m-%d"), eps[e][1].strftime("%Y-%m-%d"))) if e >= 0 else "-" for e in A["ep"]]
    A.to_pickle(CM.D + "/cache/phaseA.pkl")
    chk = dict(n=int(len(A)), x14_vs_src_maxabs=float((A["pnl_x14"] - A["pnl_src"]).abs().max()),
               vmark_vs_cut_maxabs=float((A["v_mark"] - A["pnl_cut"]).abs().max()), open_h504=int(A["open_h504"].sum()))
    log.info("kiem noi bo: %s", chk)
    ns = len(CM.SEEDS)
    J = dict(check=chk, episodes=[(a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")) for a, b in eps])
    D = A[A["deferred"]].copy()
    D["d_orc_x14"] = D["oracle"] - D["pnl_x14"]
    D["d_orc_cut"] = D["oracle"] - D["pnl_cut"]
    D["d_x14_cut"] = D["pnl_x14"] - D["pnl_cut"]
    D["d_h504_x14"] = D["pnl_h504"] - D["pnl_x14"]
    B = A[(~A["armed_pre"]) & (~A["deferred"])].copy()
    B["d_h504_cut"] = B["pnl_h504"] - B["pnl_cut"]
    B["d_orc_cut"] = B["oracle"] - B["pnl_cut"]
    B["near"] = (B["dd_prev"] > -0.30) & (B["dd_prev"] <= -0.27)

    def per_seed(df, col):
        return float(df[col].sum() / ns)

    J["A2a"] = dict(n_per_seed=len(D) / ns, x14_direct=per_seed(D, "d_x14_cut"), oracle_vs_x14=per_seed(D, "d_orc_x14"),
                    oracle_vs_cut=per_seed(D, "d_orc_cut"), h504_vs_x14=per_seed(D, "d_h504_x14"),
                    by_year={int(y): dict(n=len(g) / ns, x14_direct=per_seed(g, "d_x14_cut"), oracle_vs_x14=per_seed(g, "d_orc_x14"))
                             for y, g in D.groupby("year")},
                    by_ep={l: dict(n=len(g) / ns, x14_direct=per_seed(g, "d_x14_cut"), oracle_vs_x14=per_seed(g, "d_orc_x14"),
                                   h504_vs_x14=per_seed(g, "d_h504_x14")) for l, g in D.groupby("ep_lab")})
    J["A2b"] = dict(n_per_seed=len(B) / ns, h504_vs_cut=per_seed(B, "d_h504_cut"), oracle_vs_cut=per_seed(B, "d_orc_cut"),
                    near=dict(n=float(B["near"].sum() / ns), h504_vs_cut=per_seed(B[B["near"]], "d_h504_cut"),
                              oracle_vs_cut=per_seed(B[B["near"]], "d_orc_cut")),
                    by_year={int(y): dict(n=len(g) / ns, h504_vs_cut=per_seed(g, "d_h504_cut"), oracle_vs_cut=per_seed(g, "d_orc_cut"))
                             for y, g in B.groupby("year")},
                    by_ep={l: dict(n=len(g) / ns, h504_vs_cut=per_seed(g, "d_h504_cut"), oracle_vs_cut=per_seed(g, "d_orc_cut"))
                           for l, g in B[B["ep"] >= 0].groupby("ep_lab")},
                    open_h504=int(B["open_h504"].sum()))
    bins = [-np.inf, 1.0, 3.0, np.inf]
    labs = ["beta (rho<=1)", "trung gian (1<rho<=3)", "idio (rho>3 hoac ALT_EW khong giam)"]
    for df in (D, B):
        df["typ"] = pd.cut(df["rho"], bins, labels=labs)
    J["A2c"] = dict(deferred={str(t): dict(n=len(g) / ns, x14_direct=per_seed(g, "d_x14_cut"), oracle_vs_x14=per_seed(g, "d_orc_x14"),
                                           oracle_vs_cut=per_seed(g, "d_orc_cut")) for t, g in D.groupby("typ", observed=True)},
                    offday={str(t): dict(n=len(g) / ns, h504_vs_cut=per_seed(g, "d_h504_cut"), oracle_vs_cut=per_seed(g, "d_orc_cut"))
                            for t, g in B.groupby("typ", observed=True)})
    # A3 ho so thoi gian hoi (cum hoan)
    q = D["t_best_h"].quantile([0.1, 0.25, 0.5, 0.75, 0.9]).to_dict()
    hb = pd.cut(D["t_best_h"], [-0.01, 24, 72, 168, 336.1], labels=["0-24h", "24-72h", "72-168h", "168-336h"])
    J["A3"] = dict(t_best_q={str(k): float(v) for k, v in q.items()},
                   t_best_hist={str(k): float(v / ns) for k, v in hb.value_counts().sort_index().items()},
                   gain_by_tbest={str(k): per_seed(g, "d_orc_cut") for k, g in D.groupby(hb, observed=True)},
                   best_at_mark_frac=float((D["t_best_h"] <= 1 / 60 + 1e-9).mean()),
                   spearman={c: dict(t_best=float(D["t_best_h"].corr(D[c], method="spearman")),
                                     orc_gain=float(D["d_orc_cut"].corr(D[c], method="spearman")),
                                     x14_direct=float(D["d_x14_cut"].corr(D[c], method="spearman")))
                             for c in ("dd_prev", "spd7", "rho", "loss")})
    for c, edges in (("dd_prev", None), ("spd7", None), ("rho", None)):
        v = D[c].replace(np.inf, np.nan)
        tq = pd.qcut(v.rank(method="first"), 3, labels=["T1 thap", "T2", "T3 cao"])
        J["A3"]["tert_" + c] = {str(k): dict(range=[float(v[tq == k].min()), float(v[tq == k].max())], n=float((tq == k).sum() / ns),
                                             t_best_med=float(D.loc[tq == k, "t_best_h"].median()),
                                             orc_gain=per_seed(D[tq == k], "d_orc_cut"), x14_direct=per_seed(D[tq == k], "d_x14_cut"))
                                for k in tq.cat.categories}
        J["A3"]["tert_" + c]["inf_or_nan"] = float(v.isna().sum() / ns)
    json.dump(J, open(OUTD + "/phaseA.json", "w"), indent=1, default=str)
    cols = ["seed", "sym", "t0", "te", "mark_day", "on", "deferred", "armed_pre", "n", "pnl_x14", "pnl_cut", "pnl_h504", "oracle",
            "t_best_h", "loss", "mkt", "rho", "spd7", "dd_prev", "ep_lab", "st_x14", "st_h504", "notional"]
    A[cols].to_csv(OUTD + "/phaseA_clusters.csv", index=False)
    log.info("A2a %s", {k: v for k, v in J["A2a"].items() if k not in ("by_ep",)})
    log.info("A2b %s", {k: v for k, v in J["A2b"].items() if k not in ("by_ep",)})
    log.info("A2c %s", J["A2c"])
    log.info("A3 %s", J["A3"])
    log.info("XONG phase A")


if __name__ == "__main__":
    main()
