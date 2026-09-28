#!/usr/bin/env python3
"""P5 — cham lai 4 vong (EXIT_STRUCT/SHAPE1/FAMILY2/SIZE_COUNT) tren output CO SAN.
- 4 thuo chuan + rao (a)/(b')/q* : DUNG y dinh nghia ofi_reorient_rulers.point() (net = pnl USDT)
- 5 rate: BAN CU (pnl USDT, = size_count_score.rates -> loi #31) va BAN CHUAN (profit %)
- rao cu appetite latest 40/250/-20/0 nam am : maxDD/UW chuoi NGAY + uoc MTM phut
KHONG chay sim. Offline. Output nho.
"""
import os, re, json
import numpy as np, pandas as pd

OUT = "/home/ubuntu/kaggle_sim/out"
DD_MTM_SHIFT = 8.7
ROUNDS = {
    "EXIT_STRUCT": [("A0", "cd-sel15"), ("A1", "xs-a1"), ("A2", "xs-a2"), ("A3", "xs-a3")],
    "SHAPE1": [("S0", "cd-sel15"), ("S1", "sh1-s1-sl05"), ("S2", "sh1-s2-sl03k16"),
               ("S3", "sh1-s3-ts8"), ("S4", "sh1-s4-sl03")],
    "FAMILY2": [("N0", "cd-sel15"), ("N1", "tp-n1"), ("N2", "tp-n2"),
                ("N3", "tp-n3"), ("N4", "tp-n4")],
    "SIZE_COUNT": [("B0", "cd-sel15"), ("B1", "sc-b1"), ("B2", "sc-b2"),
                   ("B3", "sc-b3"), ("B4", "sc-b4")],
}
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")


def equity(tag):
    rows = []
    with open(f"{OUT}/{tag}/logs/sim.out", errors="ignore") as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "eq"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d")["eq"].sort_index()


def dd_uw_by_year(s):
    out = {}
    for y, sy in s.groupby(s.index.year):
        dd = float((sy / sy.cummax() - 1).min() * 100)
        u = sy < sy.cummax()
        um = int(u.groupby((~u).cumsum()).sum().max()) if len(u) else 0
        qe = sy.resample("QE").last()
        q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
        qr = (qe.values / q0.values - 1) * 100
        ry = (sy.iloc[-1] / sy.iloc[0] - 1) * 100
        out[int(y)] = (dd, um, float(qr.min()), float(ry))
    return out


def dd_uw_full(s):
    dd = float((s / s.cummax() - 1).min() * 100)
    u = s < s.cummax()
    um = int(u.groupby((~u).cumsum()).sum().max()) if len(u) else 0
    qe = s.resample("QE").last()
    q0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), qe]).iloc[:-1]
    qr = (qe.values / q0.values - 1) * 100
    ye = s.resample("YE").last()
    y0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), ye]).iloc[:-1]
    yr = dict(zip((str(p.year) for p in ye.index.to_period("Y")),
                  (ye.values / y0.values - 1) * 100))
    neg = [int(y) for y, v in yr.items() if v < 0]
    return dd, um, float(qr.min()), neg


def load(tag):
    d = pd.read_csv(f"{OUT}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("profit", "margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["status"] = d["status"].astype(str).str.strip()
    d["sym"] = d["sym"].astype(str).str.strip()
    return d.dropna(subset=["pnl", "profit"])


def rates(d, col):
    p = d[col]
    sm = p[d.status == "STOP_MARKET_DONE"]
    sl = p[d.status == "STOP_LOSS_DONE"]
    return {
        "n": float(len(d)),
        "win%": float(100.0 * (p > 0).mean()),
        "TSloss%": float(100.0 * (d.status == "STOP_LOSS_DONE").mean()),
        "mp_sm": float(sm.mean()) if len(sm) else float("nan"),
        "mp_sl": float(sl.mean()) if len(sl) else float("nan"),
        "meanP": float(p.mean()),
        "mMargin": float(d.margin.mean()),
    }


def point(d):
    """Dung y ofi_reorient_rulers.point() voi net = pnl."""
    net = d.pnl.to_numpy(dtype=float)
    n = len(net)
    tot = float(net.sum())
    o = np.sort(net)[::-1]
    k1 = max(1, int(np.ceil(0.01 * n)))
    k5 = max(1, int(np.ceil(0.05 * n)))
    k10 = max(1, int(np.ceil(0.10 * n)))

    def tail(x):
        k = max(1, int(np.ceil(x / 100.0 * n)))
        return float(o[k:].sum())

    win = net[net > 0]; los = net[net < 0]
    pcs = d.groupby("sym").pnl.sum()
    rec = {
        "share_top1_pct": float(o[:k1].sum() / tot * 100) if tot else float("nan"),
        "bottom_half_sum": tail(50),
        "median_leg": float(np.median(net)),
        "sign_pct": float(100.0 * (net > 0).mean()),
        "tf_5": float(o[k5:].mean()),
        "tf_10": float(o[k10:].mean()),
        "asym": float(los.mean() / win.mean()) if len(los) and len(win) and win.mean() else float("nan"),
        "wl_ratio": float(win.mean() / -los.mean()) if len(los) and len(win) else float("nan"),
        "loss_mean": float(-los.mean()) if len(los) else float("nan"),
        "conc_5": float(o[:k5].sum() / tot) if tot else float("nan"),
        "max_loss_leg": float(net.min()),
        "conc1coin_pnlshare_pct": float(100.0 * pcs.max() / tot) if tot else float("nan"),
        "SumPnL": tot,
    }
    rec["pass_a"] = bool(tot > 0 and rec["share_top1_pct"] <= 15.0)
    rec["pass_b50"] = bool(rec["bottom_half_sum"] > 0)
    rec["q_breakeven_pct"] = None
    for q in np.arange(0.5, 95.55, 0.5):
        if tail(q) <= 0:
            rec["q_breakeven_pct"] = float(round(q, 2)); break
    return rec


def clean(m):
    out = {}
    for k, v in m.items():
        if isinstance(v, (bool, np.bool_)): out[k] = bool(v)
        elif isinstance(v, (float, np.floating)): out[k] = (None if not np.isfinite(v) else round(float(v), 4))
        elif isinstance(v, (int, np.integer)): out[k] = int(v)
        else: out[k] = v
    return out


def main():
    res = {}
    for rnd, arms in ROUNDS.items():
        res[rnd] = {}
        for name, tag in arms:
            d = load(tag)
            r_new = rates(d, "profit")
            r_old = rates(d, "pnl")
            pt = point(d)
            yy = dd_uw_by_year(equity(tag))
            eq = equity(tag)
            fdd, fuw, fq, fneg = dd_uw_full(eq)
            m = {"tag": tag}
            m.update({f"rateNEW_{k}": v for k, v in r_new.items()})
            m.update({f"rateOLD_{k}": v for k, v in r_old.items()})
            m.update(pt)
            m["maxDD_day"] = fdd
            m["maxDD_min_est"] = fdd - DD_MTM_SHIFT
            m["UW_day"] = fuw
            m["UW_year"] = max(v[1] for v in yy.values())
            m["maxDD_year"] = min(v[0] for v in yy.values())
            m["qmin"] = fq
            m["neg_years"] = fneg
            CONC_OK = True  # conc 1 coin: lay tu doc da cong bo (moi arm <=15%), KHONG bind
            m["rao_latest_day"] = bool(m["maxDD_day"] >= -40 and m["maxDD_year"] >= -40
                                       and m["UW_day"] <= 250 and m["UW_year"] <= 250
                                       and m["qmin"] >= -20 and not m["neg_years"]
                                       and CONC_OK)
            m["rao_latest_min"] = bool((m["maxDD_year"] - DD_MTM_SHIFT) >= -40
                                       and m["UW_day"] <= 250 and m["UW_year"] <= 250
                                       and m["qmin"] >= -20 and not m["neg_years"]
                                       and CONC_OK)
            m["both_ab"] = bool(m["pass_a"] and m["pass_b50"])
            res[rnd][name] = clean(m)
    json.dump(res, open("/tmp/recheck_p5.json", "w"), indent=1)
    for rnd, arms in res.items():
        print(f"\n=== {rnd} ===")
        for nm, m in arms.items():
            print("%-3s n=%-5d ratesNEW win%%=%6.2f TSloss%%=%6.2f mP|SM=%7.3f mP|SL=%7.3f mMargin=%8.1f"
                  % (nm, m["rateNEW_n"], m["rateNEW_win%"], m["rateNEW_TSloss%"],
                     m["rateNEW_mp_sm"] or 0, m["rateNEW_mp_sl"] or 0, m["rateNEW_mMargin"]))
            print("     ratesOLD win%%=%6.2f TSloss%%=%6.2f mP|SM=%8.3f mP|SL=%8.3f mMargin=%8.1f"
                  % (m["rateOLD_win%"], m["rateOLD_TSloss%"], m["rateOLD_mp_sm"] or 0,
                     m["rateOLD_mp_sl"] or 0, m["rateOLD_mMargin"]))
            print("     (a)%%top1=%7.2f(b)TF50=%9.0f wl=%6.3f loss_mean=%8.1f tf_5=%8.4f conc_5=%6.3f "
                  "coinPNL%%=%5.2f q*=%s" % (m["share_top1_pct"], m["bottom_half_sum"], m["wl_ratio"],
                                          m["loss_mean"], m["tf_5"], m["conc_5"], m["conc1coin_pnlshare_pct"],
                                          m["q_breakeven_pct"]))
            print("     maxDDday=%7.2f maxDDmin~=%7.2f UW=%5d qmin=%7.2f negY=%s | "
                  "RAO_day=%s RAO_min=%s (a)=%s (b')=%s BOTH=%s"
                  % (m["maxDD_day"], m["maxDD_min_est"], m["UW_day"], m["qmin"],
                     m["neg_years"] or "-", "PASS" if m["rao_latest_day"] else "FAIL",
                     "PASS" if m["rao_latest_min"] else "FAIL",
                     "PASS" if m["pass_a"] else "FAIL",
                     "PASS" if m["pass_b50"] else "FAIL",
                     "PASS" if m["both_ab"] else "FAIL"))


if __name__ == "__main__":
    main()
