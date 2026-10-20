#!/usr/bin/env python3
"""T_OOS (PREREG_T_OOS): kiem ngoai mau bo loc T (BTC sleeve: ve 0 khi close ngay <= thr x dinh close P ngay; vao lai khi
close ngay > max close R ngay truoc do) tren BTCUSDT spot 2018-01-01..2019-12-31, so voi B&H. Logic trang thai T = BAN SAO
DUNG tung dong cua bb_core.simulate (docs/result/btc_base/bb_core.py dong 374-386): dinh gom ngay hien tai (dc[j-(P-1):j+1]),
max vao lai KHONG gom ngay hien tai (dc[j-R:j]), cua so mo rong max(0, .) khi chua du lich su, 1 chuyen trang thai toi da/ngay,
trang thai khoi tao ON, quyet dinh + khop tai close ngay UTC (nen 23:59 = close kline 1d).
Usage: python3 t_oos.py --data clean.csv --out outdir [--dev]"""
import argparse
import json
import logging
import sys

import numpy as np
import pandas as pd

log = logging.getLogger("toos")
COST = 0.0010 + 0.0005            # phi spot + truot, moi chieu
BASE = dict(thr=0.70, P=180, R=30)
GRID_THR = [0.65, 0.70, 0.75]
GRID_P = [120, 180, 240]
GRID_R = [20, 30, 40]
T0_DATE = "2017-12-31"            # close ngay nay = moc bat dau (equity = 1,0), cua so cham 2018-01-01..2019-12-31
END_DATE = "2019-12-31"
SUB_T0_DATE = "2018-02-13"        # close ngay nay = moc bat dau cua so phu (bat dau 2018-02-14)
SEAL_DATE = "2020-01-01"          # du lieu tu moc nay tro di la niem phong: cam


# ------------------------------------------------------------------------------------------------ logic T (ban sao bb_core)
def t_states(dc, days, thr=0.70, P=180, R=30, init_on=True):
    """dc: close ngay (mang); days: danh sach chi so ngay quyet dinh (tang dan). Tra (state sau quyet dinh moi ngay, switches)."""
    on = init_on
    st = np.zeros(len(days), bool)
    sw = []
    for n, j in enumerate(days):
        pc = dc[j]
        if on:
            if pc <= thr * dc[max(0, j - (P - 1)):j + 1].max():
                on = False
                sw.append((n, "OFF"))
        else:
            if j >= 1 and pc > dc[max(0, j - R):j].max():
                on = True
                sw.append((n, "ON"))
        st[n] = on
    return st, sw


def run_equity(dc, days, st, cost=COST):
    """Von 1,0 USDT tai close days[0]. ON -> 100 % BTC (mua het tien, phi tren notional); OFF -> USDT lai 0. Khong thanh ly cuoi ky."""
    cash, q, entry_cash, entry_n = 1.0, 0.0, None, None
    eq = np.zeros(len(days))
    trades, episodes = [], []
    for n, j in enumerate(days):
        p = dc[j]
        if st[n] and q == 0.0:
            notional = cash / (1.0 + cost)
            q = notional / p
            entry_cash, entry_n = cash, n
            cash = 0.0
            trades.append((n, "BUY", float(p)))
        elif (not st[n]) and q > 0.0:
            cash = q * p * (1.0 - cost)
            episodes.append(dict(entry_n=entry_n, exit_n=n, ret=cash / entry_cash - 1.0, open=False))
            q = 0.0
            trades.append((n, "SELL", float(p)))
        eq[n] = cash + q * p
    if q > 0.0:
        episodes.append(dict(entry_n=entry_n, exit_n=None, ret=eq[-1] / entry_cash - 1.0, open=True))
    return eq, trades, episodes


def bh_equity(dc, days, cost=COST):
    q = (1.0 / (1.0 + cost)) / dc[days[0]]
    return q * dc[np.asarray(days)]


def metrics(s, steps, date_of):
    """s: chuoi equity bat dau = 1,0 (diem 0 = moc tham chieu). maxDD tren close ngay."""
    s = np.asarray(s, float)
    peak = np.maximum.accumulate(s)
    dd = s / peak - 1.0
    it = int(np.argmin(dd))
    ip = int(np.argmax(s[:it + 1]))
    cagr = float(s[-1] ** (365.0 / steps) - 1.0) if s[-1] > 0 else -1.0
    return dict(total=float(s[-1] / s[0] - 1.0), cagr=cagr, maxdd=float(dd[it]), peak_date=str(date_of(ip)),
                trough_date=str(date_of(it)), steps=int(steps))


def primary_series(eq):
    return np.concatenate([[1.0], eq])


def evaluate(dc, days, dates, thr, P, R, st_override=None):
    """1 o tham so: T vs B&H tren cua so days (chi so ngay); tra dict + chi tiet."""
    if st_override is None:
        st, sw = t_states(dc, days, thr, P, R, True)
    else:
        st = st_override
        sw = [(n, "ON" if st[n] else "OFF") for n in range(1, len(st)) if st[n] != st[n - 1]]
    eq, trades, eps = run_equity(dc, days, st)
    bh = bh_equity(dc, days)
    steps = len(days) - 1

    def dof(k):
        return dates[days[max(k - 1, 0)]]
    mt = metrics(primary_series(eq), steps, dof)
    mb = metrics(primary_series(bh), steps, dof)
    c1 = abs(mt["maxdd"]) <= 0.6 * abs(mb["maxdd"])
    c2 = mt["total"] >= mb["total"]
    c3 = mt["maxdd"] >= -0.40
    return dict(T=mt, BH=mb, c1=bool(c1), c2=bool(c2), c3=bool(c3), switches=len(sw), off_days=int((~st).sum()),
                eq=eq, bh=bh, st=st, trades=trades, episodes=eps)


def ep_rows(res, days, dates):
    out = []
    for e in res["episodes"]:
        out.append(dict(entry=str(dates[days[e["entry_n"]]]), exit=(str(dates[days[e["exit_n"]]]) if e["exit_n"] is not None else None),
                        ret=float(e["ret"]), open=bool(e["open"])))
    return out


def trade_rows(res, days, dates):
    return [dict(date=str(dates[days[n]]), action=a, price=p) for n, a, p in res["trades"]]


# ------------------------------------------------------------------------------------------------ du lieu
def load_clean(path):
    d = pd.read_csv(path)
    d["date"] = pd.to_datetime(d["date"]).dt.date
    d = d.sort_values("date").reset_index(drop=True)
    assert d["date"].is_unique, "ngay trung"
    assert str(d["date"].max()) < SEAL_DATE, "V2: co du lieu >= 2020-01-01"
    full = pd.date_range(d["date"].min(), d["date"].max(), freq="D").date
    assert len(full) == len(d) and all(a == b for a, b in zip(full, d["date"])), "thieu ngay sau khi lam day"
    return list(d["date"]), d["close"].to_numpy(float)


def short(m):
    return "%+.1f%% / CAGR %+.1f%% / DD %.1f%%" % (100 * m["total"], 100 * m["cagr"], 100 * m["maxdd"])


# ------------------------------------------------------------------------------------------------ kiem look-ahead
def lookahead_check(dc, days, params, cuts, tag):
    """Quyet dinh ngay d chi dung close <= d: (a) cat du lieu sau moc; (b) thay gia sau moc bang random walk; state + equity <= moc khong doi."""
    st_full, _ = t_states(dc, days, **params)
    eq_full, _, _ = run_equity(dc, days, st_full)
    out = []
    for jc in cuts:
        nd = [i for i, j in enumerate(days) if j <= jc]
        n = len(nd)
        d_cut = dc[:jc + 1]
        st_a, _ = t_states(d_cut, days[:n], **params)
        rng = np.random.default_rng(1)
        d_scr = dc.copy()
        d_scr[jc + 1:] = dc[jc] * np.exp(np.cumsum(rng.normal(0, 0.03, len(dc) - jc - 1)))
        st_b, _ = t_states(d_scr, days, **params)
        eq_b, _, _ = run_equity(d_scr, days, st_b)
        ok_a = bool(np.array_equal(st_a, st_full[:n]))
        ok_b = bool(np.array_equal(st_b[:n], st_full[:n]) and np.allclose(eq_b[:n], eq_full[:n], rtol=0, atol=1e-12))
        out.append(dict(tag=tag, cut_idx=int(jc), n_days=n, truncate_ok=ok_a, scramble_ok=ok_b))
        log.info("V3 %s cut=%d n=%d truncate=%s scramble=%s", tag, jc, n, ok_a, ok_b)
    return out


# ------------------------------------------------------------------------------------------------ DEV (V1 + so sanh nhat quan)
def dev_block(res_json):
    sys.path.insert(0, "/home/ubuntu/claude_master/btc_base")
    import bb_core as C  # noqa: E402  (tai dung load_px cua BTC_BASE)
    P = C.load_px("D")
    a0 = C.WIN["D"]["a0"]
    nm = C.WIN["D"]["a1"] - a0
    di, dc = P["daily_btc_idx"], P["daily_btc"]
    days = [j for j, k in enumerate(di) if 0 <= int(k) < nm]
    # V2: lich su close ngay dung trong DEV bat dau 2021-01-01 (px_btceth.npz) -> khong co 2020
    first_close = pd.Timestamp((a0 + int(di[0])) * 60000, unit="ms")
    assert first_close >= pd.Timestamp(SEAL_DATE), "DEV co du lieu < 2021?"
    dates_all = [pd.Timestamp((a0 + int(k)) * 60000, unit="ms").date() for k in di]
    assert str(dates_all[0]) >= "2021-01-01"
    res = evaluate(dc, days, dates_all, **{"thr": 0.70, "P": 180, "R": 30})
    v1 = dict(off_days=res["off_days"], switches=res["switches"], expect_off=475, expect_switches=41,
              ok=bool(res["off_days"] == 475 and res["switches"] == 41), n_days=len(days),
              first_day=str(dates_all[days[0]]), last_day=str(dates_all[days[-1]]), hist_first=str(dates_all[0]))
    log.info("V1 DEV: %s", v1)
    la = lookahead_check(dc, days, dict(thr=0.70, P=180, R=30), [days[len(days) // 3], days[2 * len(days) // 3]], "DEV")
    return dict(v1=v1, T=res["T"], BH=res["BH"], c1=res["c1"], c2=res["c2"], c3=res["c3"], switches=res["switches"],
                off_days=res["off_days"], episodes=ep_rows(res, days, dates_all), trades=trade_rows(res, days, dates_all),
                lookahead=la)


# ------------------------------------------------------------------------------------------------ chinh
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dev", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    dates, dc = load_clean(a.data)
    idx = {str(d): i for i, d in enumerate(dates)}
    j0, j1 = idx[T0_DATE], idx[END_DATE]
    days = list(range(j0, j1 + 1))
    log.info("data %s..%s n=%d ; cua so cham: t0=%s .. %s (%d buoc)", dates[0], dates[-1], len(dates), T0_DATE, END_DATE, len(days) - 1)
    out = dict(cost_per_side=COST, n_days_total=len(dates), first=str(dates[0]), last=str(dates[-1]))

    # --- chinh
    prim = evaluate(dc, days, dates, **BASE)
    out["primary"] = dict(T=prim["T"], BH=prim["BH"], c1=prim["c1"], c2=prim["c2"], c3=prim["c3"], switches=prim["switches"],
                          off_days=prim["off_days"], episodes=ep_rows(prim, days, dates), trades=trade_rows(prim, days, dates),
                          dd_ratio=abs(prim["T"]["maxdd"]) / abs(prim["BH"]["maxdd"]))
    log.info("PRIMARY T  : %s ; sw=%d off=%d", short(prim["T"]), prim["switches"], prim["off_days"])
    log.info("PRIMARY B&H: %s", short(prim["BH"]))
    log.info("C1=%s C2=%s C3=%s", prim["c1"], prim["c2"], prim["c3"])

    # --- luoi 27 o
    grid = []
    for thr in GRID_THR:
        for P in GRID_P:
            for R in GRID_R:
                r = evaluate(dc, days, dates, thr, P, R)
                grid.append(dict(thr=thr, P=P, R=R, T_total=r["T"]["total"], T_maxdd=r["T"]["maxdd"], BH_total=r["BH"]["total"],
                                 BH_maxdd=r["BH"]["maxdd"], c1=r["c1"], c2=r["c2"], c3=r["c3"], both=bool(r["c1"] and r["c2"]),
                                 switches=r["switches"], off_days=r["off_days"]))
    n_both = sum(g["both"] for g in grid)
    cond_sub = n_both >= 19            # >= 70 % cua 27 o (ceil(18,9) = 19)
    out["grid"] = grid
    out["grid_summary"] = dict(n_cells=len(grid), n_c1c2=n_both, n_c1=sum(g["c1"] for g in grid), n_c2=sum(g["c2"] for g in grid),
                               n_c3=sum(g["c3"] for g in grid), threshold_cells=19, cond_sub=bool(cond_sub))
    centre = [g for g in grid if (g["thr"], g["P"], g["R"]) == (0.70, 180, 30)][0]
    assert centre["T_total"] == prim["T"]["total"] and centre["T_maxdd"] == prim["T"]["maxdd"], "o trung tam != T chinh"
    log.info("GRID: %d/27 o dat C1&C2 (can >= 19)", n_both)

    verdict = bool(prim["c1"] and prim["c2"] and prim["c3"] and cond_sub)
    out["verdict"] = "PASS (khong bi bac bo)" if verdict else "FAIL"
    log.info("VERDICT: %s", out["verdict"])

    # --- bao cao phu (khong tham gia verdict)
    sub = {}
    n0 = idx[SUB_T0_DATE] - j0
    s_t = prim["eq"][n0:] / prim["eq"][n0]
    s_b = prim["bh"][n0:] / prim["bh"][n0]
    dof = lambda k: dates[days[n0 + k]]  # noqa: E731
    mt, mb = metrics(s_t, len(s_t) - 1, dof), metrics(s_b, len(s_b) - 1, dof)
    sub["from_2018_02_14"] = dict(T=mt, BH=mb, c1=bool(abs(mt["maxdd"]) <= 0.6 * abs(mb["maxdd"])), c2=bool(mt["total"] >= mb["total"]),
                                  c3=bool(mt["maxdd"] >= -0.40), state_on_at_start=bool(prim["st"][n0]),
                                  note="lat cat tu duong primary, rebase tai close 2018-02-13; vi the T giu nguyen vi the thua ke")
    # warm-start: may trang thai chay lien tuc tu 2017-08-17 (ON khoi tao tai ngay dau du lieu), do tu t0 nhu primary
    st_w, sw_w = t_states(dc, list(range(0, j1 + 1)), **BASE)
    rw = evaluate(dc, days, dates, 0.70, 180, 30, st_override=st_w[j0:])
    sub["warm_start"] = dict(T=rw["T"], BH=rw["BH"], c1=rw["c1"], c2=rw["c2"], c3=rw["c3"], switches=rw["switches"],
                             off_days=rw["off_days"], state_at_t0="ON" if st_w[j0] else "OFF",
                             switches_before_t0=int(sum(1 for n, _ in sw_w if n < j0)),
                             trades=trade_rows(rw, days, dates), episodes=ep_rows(rw, days, dates))
    out["secondary"] = sub
    log.info("SUB 2018-02-14: T %s | BH %s", short(mt), short(mb))
    log.info("SUB warm-start: T %s | state_t0=%s", short(rw["T"]), sub["warm_start"]["state_at_t0"])

    # --- V3 look-ahead tren OOS
    cuts = [idx["2018-04-30"], idx["2018-12-31"], idx["2019-06-30"]]
    out["v3"] = lookahead_check(dc, days, BASE, cuts, "OOS")
    out["v2"] = dict(max_date=str(dates[-1]), sealed_from=SEAL_DATE, ok=bool(str(dates[-1]) < SEAL_DATE))

    if a.dev:
        out["dev"] = dev_block(out)
        d = out["dev"]
        log.info("DEV T  : %s ; sw=%d off=%d", short(d["T"]), d["switches"], d["off_days"])
        log.info("DEV B&H: %s", short(d["BH"]))
    with open(a.out.rstrip("/") + "/t_oos_res.json", "w") as f:
        json.dump(out, f, indent=1, default=str)
    log.info("DONE")


if __name__ == "__main__":
    main()
