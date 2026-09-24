#!/usr/bin/env python3
"""BLACKSWAN_2510 — stress THIEN NGA DEN quanh 2025-10-10/11 (alt cascade).

Thuc thi DUNG docs/prereg/PREREG_BLACKSWAN_2510.md (commit ffece1f, chot TRUOC khi do).

THUAN PYTHON OFFLINE tren artifact DA CO + du lieu 1m. KHONG Java tren Oracle, KHONG claude-run,
KHONG push, DEV only (moi leg end <= 2025-12-31), KHONG doc 2026.

  VIEC A: 1m 2025-10-08..13 -> BTC/ETH vs phan bo ALT (p1..p99, worst20) theo NGAY va theo GIO,
          gio cao diem + phut BTC cham day.
  VIEC B: artifact that — leg dang mo trong W, max drop equity W, % lai bi xoa, %lai 2025 truoc/sau.
  VIEC C: stress chi phi x2/x5/x10 tren leg trong W; 1 coin ve -90/-100% (co/khong conc cap 0.15).
  VIEC D: 1-2 leg lon nhat lech -> dPnL/dCAGR/dmaxDD + nguong X* xoa sach lai 1 nam / toan ky.

Usage: python3 blackswan_2510.py [--json /home/ubuntu/blackswan/blackswan.json]
"""
import argparse
import gzip
import heapq
import json
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jbin  # noqa: E402  (thuan Python, doc ticker bin)

OUTDIR = "/home/ubuntu/blackswan"
TICKER = "/home/ubuntu/kaggle_data_hpo"
KOUT = "/home/ubuntu/kaggle_sim/out"
DEVRUN = "/home/ubuntu/java/devrun"

CAP0 = 35000.0
COST = 0.008          # cost/leg = 0.008 * margin (do TRUOC tren 4 nen, xem PREREG §6)
TZ_SHIFT_H = 7        # printDone GMT+7 -> UTC

W_START = pd.Timestamp("2025-10-09 00:00")
W_END = pd.Timestamp("2025-10-13 23:59")
E_DAY = pd.Timestamp("2025-10-10")
DAYS = ["20251008", "20251009", "20251010", "20251011", "20251012", "20251013"]
W_DAYS = ["20251009", "20251010", "20251011", "20251012", "20251013"]

RUNS = {
    "T170": os.path.join(KOUT, "t170-x1-2021"),
    "KEEPLEG0": os.path.join(DEVRUN, "FG_KEEPLEG0"),
    "T100": os.path.join(KOUT, "hn-t100"),
    "GD92": os.path.join(KOUT, "hn-g92"),
}
CC_TIGHT = os.path.join(DEVRUN, "CC_TIGHT_T170")

MAJORS = {"BTC", "ETH"}
STABLE = {"USDC", "USDT", "DAI", "FDUSD", "TUSD", "BUSD", "EUR", "USDP", "USDE", "USD1", "PYUSD"}

os.makedirs(OUTDIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(os.path.join(OUTDIR, "blackswan.log"), "w"),
              logging.StreamHandler()])
L = logging.getLogger("blackswan")

REPORT = []
R = {}


def say(s=""):
    REPORT.append(str(s))
    L.info(s)


RX_EQ = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?\tunP:\s*(-?\d+)")
RX_EQM = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?\tunP:\s*(-?\d+).*?\tunPMin:\s*(-?\d+)")
PEAK_EXP = pd.Timestamp("2025-10-10 21:22")   # dinh exposure (local 10-11 04:22 = UTC 10-10 21:22)


# ---------------------------------------------------------------- artifact helpers
def paths(base):
    return (os.path.join(base, "storage", "printDone.csv"),
            os.path.join(base, "logs", "sim.out"))


def legs(base):
    pdone, _ = paths(base)
    d = pd.read_csv(pdone, on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("profit", "margin", "pnl", "entry", "quantity", "funding"):
        if c in d.columns:
            d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "margin"]).copy()
    d["sym"] = d["sym"].str.strip()
    d["ts"] = pd.to_datetime(d["start"].astype(str), format="%Y%m%d %H:%M", errors="coerce") \
        - pd.Timedelta(hours=TZ_SHIFT_H)     # GMT+7 -> UTC
    d["te"] = pd.to_datetime(d["end"].astype(str), format="%Y%m%d %H:%M", errors="coerce") \
        - pd.Timedelta(hours=TZ_SHIFT_H)
    d = d.dropna(subset=["ts", "te"]).reset_index(drop=True)
    return d


def equity(base):
    _, sout = paths(base)
    rows = []
    with open(sout, errors="ignore") as fh:
        for line in fh:
            m = RX_EQ.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity.astype(float)


def maxdd(s):
    s = s.astype(float)
    return float((s / s.cummax() - 1).min() * 100.0)


def intraday(base):
    """THAM KHAO (exploratory, ngoai pre-reg): b+unPMin theo ngay — can duoi moc-to-market trong ngay.

    Tra DataFrame index=ngay, cot b/unP/unPMin/low (low = b+unPMin).
    """
    _, sout = paths(base)
    rows = []
    with open(sout, errors="ignore") as fh:
        for line in fh:
            m = RX_EQM.search(line)
            if m:
                b, u, um = int(m.group(2)), int(m.group(3)), int(m.group(4))
                rows.append((m.group(1), b, u, um, b + um))
    f = pd.DataFrame(rows, columns=["d", "b", "unP", "unPMin", "low"])
    f = f.drop_duplicates("d", keep="last")
    f["d"] = pd.to_datetime(f.d, format="%Y%m%d")
    return f.set_index("d")


def cagr(eq_end, years):
    return float((eq_end / CAP0) ** (1.0 / years) - 1.0) * 100.0


# ---------------------------------------------------------------- sweep: concurrent margin
def sweep(d):
    """Quet start/end tren moc PHUT -> (times, margin_hi, margin_lo)."""
    st = d["ts"].values.astype("datetime64[m]").astype(np.int64)
    en = d["te"].values.astype("datetime64[m]").astype(np.int64)
    mg = d["margin"].values.astype(float)
    o = np.argsort(st, kind="mergesort")
    st, mg_st = st[o], mg[o]
    o2 = np.argsort(en, kind="mergesort")
    en, mg_en = en[o2], mg[o2]
    times = np.unique(np.concatenate([st, en]))
    cs, ce = np.cumsum(mg_st), np.cumsum(mg_en)
    i_st = np.searchsorted(st, times, side="right")
    i_en = np.searchsorted(en, times, side="left")
    hi = np.where(i_st > 0, cs[np.maximum(i_st - 1, 0)], 0.0) \
        - np.where(i_en > 0, ce[np.maximum(i_en - 1, 0)], 0.0)
    i_en2 = np.searchsorted(en, times, side="right")
    lo = np.where(i_st > 0, cs[np.maximum(i_st - 1, 0)], 0.0) \
        - np.where(i_en2 > 0, ce[np.maximum(i_en2 - 1, 0)], 0.0)
    return times, hi, lo


def eq_at(eqday, times):
    idx = pd.DatetimeIndex(times.astype("datetime64[m]"))
    return eqday.reindex(idx, method="ffill").to_numpy()


def coin_exposure(d, eqday):
    """max_t (margin 1 coin / equity(t)) * 100 + thoi diem + margin tuyet doi."""
    best = (0.0, None, None, 0.0)
    for sym, g in d.groupby("sym"):
        t, hi, _ = sweep(g)
        if len(t) == 0:
            continue
        e = eq_at(eqday, t)
        r = hi / np.where((e > 0) & np.isfinite(e), e, np.nan)
        if not np.isfinite(r).any():
            continue
        j = int(np.nanargmax(r))
        if np.isfinite(r[j]) and r[j] * 100 > best[0]:
            best = (float(r[j] * 100), str(sym),
                    pd.Timestamp(int(t[j]), unit="m").strftime("%Y-%m-%d %H:%M"),
                    float(hi[j]))
    return best


def conc_replay(d, eqday, pct):
    """Replay offline: chan HAN leg moi neu (margin_coin + margin_leg)/equity > pct.

    XAP XI (equity moc NGAY, khong phai moc phut) — khong phai sim. Tra (n_leg, sum_pnl, block, sub).
    """
    n0, s0 = int(d.shape[0]), float(d["pnl"].sum())
    if not (0 < pct < 1):
        return n0, s0, 0, d
    dd = d.sort_values(["ts", "te"], kind="mergesort")
    heaps = {}             # sym -> heap (end_ns, margin) cac leg DANG MO
    open_mg = {}           # sym -> margin dang mo
    kept = []
    blk = 0
    for _, row in dd.iterrows():
        t = row["ts"]
        sym = row["sym"]
        # het han: bo cac leg da dong (te <= t) cua CHINH coin nay
        h = heaps.get(sym)
        cur = open_mg.get(sym, 0.0)
        if h:
            tn = t.value
            while h and h[0][0] <= tn:
                cur -= heapq.heappop(h)[1]
        open_mg[sym] = cur
        e_now = eqday.reindex([t], method="ffill")
        e_now = float(e_now.iloc[0]) if len(e_now) else np.nan
        if np.isfinite(e_now) and e_now > 0 and (cur + row["margin"]) / e_now > pct:
            blk += 1
            continue
        open_mg[sym] = cur + row["margin"]
        heapq.heappush(heaps.setdefault(sym, []), (row["te"].value, float(row["margin"])))
        kept.append(row)
    sub = pd.DataFrame(kept) if kept else d.iloc[0:0]
    return len(sub), float(sub["pnl"].sum()) if len(sub) else 0.0, blk, sub


# ---------------------------------------------------------------- VIEC A
def load_1m():
    """Tra (DatetimeIndex phut UTC, symbols list, close matrix n_min x n_sym)."""
    cache = os.path.join(OUTDIR, "m1_W.npz")
    if os.path.exists(cache):
        z = np.load(cache, allow_pickle=False)
        idx = pd.DatetimeIndex(pd.to_datetime(z["t"], unit="ms"))
        return idx, [str(s) for s in z["syms"]], z["M"]
    syms = None
    times = []
    rows = []
    for day in DAYS:
        p = os.path.join(TICKER, "ticker_%s.bin.gz" % day)
        with gzip.open(p, "rb") as f:
            b = f.read()
        for k, v in jbin.iter_minutes(b):
            if syms is None:
                syms = sorted(v.keys())
                sidx = {s: i for i, s in enumerate(syms)}
            arr = np.full(len(syms), np.nan)
            for s, tup in v.items():
                j = sidx.get(s)
                if j is not None:
                    c = tup[3]
                    arr[j] = c if c and c > 0 else np.nan
            times.append(k)
            rows.append(arr)
    M = np.vstack(rows)
    idx = pd.DatetimeIndex(pd.to_datetime(np.array(times), unit="ms"))
    np.savez_compressed(cache, t=np.array(times, dtype=np.int64),
                        syms=np.array([str(s) for s in syms]), M=M.astype(np.float32))
    return idx, syms, M


def alt_mask(syms):
    keep = []
    for s in syms:
        if not s.endswith("USDT"):
            keep.append(False)
            continue
        base = s[:-4]
        if base in MAJORS or base in STABLE:
            keep.append(False)
        else:
            keep.append(True)
    return np.array(keep)


def pct(r):
    r = r[np.isfinite(r)]
    if len(r) == 0:
        return {}
    q = np.percentile(r * 100, [1, 10, 50, 90, 99])
    return dict(n=int(len(r)), p1=float(q[0]), p10=float(q[1]), p50=float(q[2]),
                p90=float(q[3]), p99=float(q[4]), mean=float(r.mean() * 100))


def vc_a(say):
    say("=" * 78)
    say("VIEC A — XAC NHAN SU KIEN bang du lieu 1m (UTC)")
    idx, syms, M = load_1m()
    say("1m: %d phut x %d symbol (%s .. %s) — file ticker_%s..%s" %
        (M.shape[0], M.shape[1], idx[0], idx[-1], DAYS[0], DAYS[-1]))
    ser = pd.DataFrame(M, index=idx, columns=syms)
    am = alt_mask(syms)
    alts = [s for s, k in zip(syms, am) if k]
    say("ALT universe: %d symbol (tru BTC/ETH + stablecoin)" % len(alts))

    # --- daily returns
    day_close = {}
    for d in DAYS:
        last_min = ser.loc[d + " 23:59"]
        day_close[d] = last_min
    dc = pd.DataFrame(day_close)                      # index=sym, col=day
    # dr[sym, i] = close(W_DAYS[i]) / close(DAYS[i]) - 1  (DAYS[0] = 20251008 = ngay NEO)
    dr = (dc[W_DAYS].values / dc[DAYS[:len(W_DAYS)]].values) - 1.0

    say("")
    say("A1. TONG QUAN NGAY (UTC). r = close(23:59 d)/close(23:59 d-1) - 1")
    say("    | ngay | BTC%  | ETH%  | ALT p1 | ALT p10 | ALT p50 | ALT p90 | ALT p99 | ALT<0% | n_alt |")
    rowsA1 = []
    for i, d in enumerate(W_DAYS):
        ral = dr[am, i]
        base = W_DAYS[i - 1] if i else DAYS[0]        # ngay neo: 20251008 cho 20251009
        bt = dc.loc["BTCUSDT", d] / dc.loc["BTCUSDT", base] - 1
        et = dc.loc["ETHUSDT", d] / dc.loc["ETHUSDT", base] - 1
        p = pct(ral)
        frac_neg = float(np.mean(ral[np.isfinite(ral)] < 0) * 100)
        rowsA1.append(dict(day=d, btc=float(bt * 100), eth=float(et * 100), alt=p,
                           frac_neg=frac_neg))
        say("    | %s | %6.2f | %6.2f | %6.2f | %7.2f | %7.2f | %7.2f | %7.2f | %5.1f%% | %5d |"
            % (d, bt * 100, et * 100, p["p1"], p["p10"], p["p50"], p["p90"], p["p99"],
               frac_neg, p["n"]))
    R["A1_daily"] = rowsA1

    # --- hourly returns; worst hour
    hr = ser.resample("1h").last()
    hr_ret = hr.pct_change()
    hr_ret = hr_ret.loc[(hr_ret.index >= pd.Timestamp("2025-10-08 01:00")) &
                        (hr_ret.index <= pd.Timestamp("2025-10-13 23:00"))]
    say("")
    say("A2. GIO XAU NHAT trong W (ALT p1 thap nhat) — top 8 gio:")
    rowsH = []
    for t, row in hr_ret.iterrows():
        ra = row.values[am]
        p = pct(ra)
        if not p:
            continue
        rowsH.append((t, p, row["BTCUSDT"], row["ETHUSDT"]))
    rowsH.sort(key=lambda x: x[1]["p1"])
    say("    | gio UTC | BTC% | ETH% | ALT p1 | p10 | p50 | p90 | p99 |")
    for t, p, b, e in rowsH[:8]:
        say("    | %s | %6.2f | %6.2f | %6.2f | %6.2f | %6.2f | %6.2f | %6.2f |"
            % (t.strftime("%m-%d %H:%M"), b * 100, e * 100, p["p1"], p["p10"], p["p50"],
               p["p90"], p["p99"]))
    R["A2_worst_hours"] = [
        dict(hour=t.strftime("%Y-%m-%d %H:%M"), btc=float(b * 100), eth=float(e * 100), **p)
        for t, p, b, e in rowsH[:8]]

    # --- phut: BTC cham day + drop 1 phut lon nhat
    w = ser.loc["2025-10-09":"2025-10-13"]
    bt = w["BTCUSDT"].dropna()
    tmin = bt.idxmin()
    drop1 = (bt / bt.shift(1) - 1).dropna()
    t1 = drop1.idxmin()
    say("")
    say("A3. PHUT: BTC day %s (close %.0f, tu dinh W %s = %+.2f%%) | drop 1 phut lon nhat %s (%+.2f%%)"
        % (tmin, bt.min(), bt.loc[:tmin].idxmax(),
           (bt.min() / bt.loc[:tmin].max() - 1) * 100, t1, drop1.min() * 100))
    # phut ALT sap manh nhat (p10 cua ret 1 phut)
    mr = w.pct_change()
    amv = mr.values[:, am]
    with np.errstate(invalid="ignore"):
        p10m = np.nanpercentile(amv, 10, axis=1)
    talt = pd.Timestamp(w.index[int(np.nanargmin(p10m))])
    say("A3b. Phut ALT sap manh nhat (p10 ret 1m thap nhat): %s (p10 = %.2f%%)"
        % (talt, float(np.nanmin(p10m)) * 100))
    R["A3"] = dict(btc_low=str(tmin), btc_low_px=float(bt.min()),
                   btc_low_dd_pct=float((bt.min() / bt.loc[:tmin].max() - 1) * 100),
                   btc_worst_1m=str(t1), btc_worst_1m_pct=float(drop1.min() * 100),
                   alt_worst_minute=str(talt), alt_worst_minute_p10=float(np.nanmin(p10m) * 100))

    # --- sap bao nhieu: close cuoi W / close dau W
    p0 = dc.loc[:, DAYS[1]]      # close 2025-10-09 23:59
    p1 = dc.loc[:, W_DAYS[-1]]   # close 2025-10-13 23:59
    wr = (p1 / p0 - 1).dropna()
    wa = wr[[s for s in wr.index if s[:-4] not in MAJORS and s[:-4] not in STABLE]]
    p = pct(wa.values)
    say("")
    say("A4. SAP BAO NHIEU (close 10-13 vs close 10-09, UTC). BTC %.2f%% ETH %.2f%%; ALT: n=%d "
        "p1=%.2f p10=%.2f p50=%.2f p90=%.2f p99=%.2f"
        % ((p1["BTCUSDT"] / p0["BTCUSDT"] - 1) * 100, (p1["ETHUSDT"] / p0["ETHUSDT"] - 1) * 100,
           p["n"], p["p1"], p["p10"], p["p50"], p["p90"], p["p99"]))
    w20 = wa.sort_values().head(20)
    say("    worst-20 ALT (ca cua so): " +
        ", ".join("%s %.1f%%" % (s[:-4], v * 100) for s, v in w20.items()))
    R["A4"] = dict(btc_pct=float((p1["BTCUSDT"] / p0["BTCUSDT"] - 1) * 100),
                   eth_pct=float((p1["ETHUSDT"] / p0["ETHUSDT"] - 1) * 100), alt=p,
                   worst20={s[:-4]: float(v * 100) for s, v in w20.items()})
    # worst-20 trong NGAY su kien E
    ie = W_DAYS.index("20251010")
    re_ = pd.Series(dr[:, ie], index=syms)
    rea = re_[[s for s in syms if s[:-4] not in MAJORS and s[:-4] not in STABLE]].dropna()
    w20e = rea.sort_values().head(20)
    say("    worst-20 ALT (rieng ngay 2025-10-10): " +
        ", ".join("%s %.1f%%" % (s[:-4], v * 100) for s, v in w20e.items()))
    # max intra-window drawdown per coin (peak->trough)
    dn = w / w.cummax() - 1
    ddm = dn.min()
    da = ddm[[s for s in ddm.index if s[:-4] not in MAJORS and s[:-4] not in STABLE]].dropna()
    pdq = np.nanpercentile(da.values * 100, [1, 10, 50, 90, 99])
    say("    drawdown TRONG W (peak->trough, phan tram) ALT: p1=%.2f p10=%.2f p50=%.2f p90=%.2f p99=%.2f (worst %.1f%%)"
        % (pdq[0], pdq[1], pdq[2], pdq[3], pdq[4], da.min() * 100))
    say("    worst-20 ALT drawdown trong W: " +
        ", ".join("%s %.1f%%" % (s[:-4], v * 100) for s, v in da.sort_values().head(20).items()))
    R["A4b"] = dict(worst20_E={s[:-4]: float(v * 100) for s, v in w20e.items()},
                    dd=pct(da.values), dd_worst20={s[:-4]: float(v * 100)
                                                   for s, v in da.sort_values().head(20).items()})
    ser.to_pickle(os.path.join(OUTDIR, "m1_close_W.pkl")) if False else None
    return idx, syms, M


# ---------------------------------------------------------------- VIEC B..D
def vc_bcd(say, idx, syms, M):
    ser = pd.DataFrame(M, index=idx, columns=syms)

    for tag, base in RUNS.items():
        d = legs(base)
        e = equity(base)
        years = (e.index[-1] - pd.Timestamp("2021-07-01")).days / 365.25
        eq_end = float(e.iloc[-1])
        say("")
        say("#" * 78)
        say("NEN %s — n=%d leg, eq_end=%.0f, CAGR=%.2f%% (%.2f nam), maxDD toan ky=%.2f%%"
            % (tag, len(d), eq_end, cagr(eq_end, years), years, maxdd(e)))
        win = d[(d["ts"] <= W_END) & (d["te"] >= W_START)].copy()
        inw = d[(d["te"] >= W_START) & (d["te"] <= W_END)].copy()
        say("VIEC B. Leg DANG MO trong W: %d | leg DONG trong W: %d | Σpnl dong trong W = %.0f USDT"
            % (len(win), len(inw), inw["pnl"].sum()))
        top = win.sort_values("margin", ascending=False).head(10)
        say("    top-10 leg theo margin dang mo trong W (sym, margin, pnl, start->end UTC):")
        for _, r in top.iterrows():
            say("      %-12s m=%9.0f pnl=%9.0f  %s -> %s" %
                (r["sym"], r["margin"], r["pnl"], r["ts"].strftime("%m-%d %H:%M"),
                 r["te"].strftime("%m-%d %H:%M")))
        ce = coin_exposure(win, e)
        say("    coin nang nhat trong W: %s — max margin 1 coin = %.0f USDT = %.2f%% equity @ %s"
            % (ce[1], ce[3], ce[0], ce[2]))
        ceall = coin_exposure(d, e)
        say("    (doi chieu TOAN KY: %s %.2f%% equity @ %s, margin %.0f)"
            % (ceall[1], ceall[0], ceall[2], ceall[3]))

        # --- max drop equity trong W + % lai bi xoa
        wq = e[(e.index >= W_START) & (e.index <= W_END)]
        pe = e[(e.index >= W_START - pd.Timedelta(days=1)) & (e.index <= W_END + pd.Timedelta(days=2))]
        drop = float((wq / wq.cummax() - 1).min() * 100) if len(wq) else float("nan")
        # neo tu cuoi T9 (truoc W)
        pre = e[e.index < W_START]
        anchor = float(pre.iloc[-1]) if len(pre) else float("nan")
        post = e[e.index > W_END]
        postv = float(post.iloc[0]) if len(post) else float("nan")
        lai_truoc = anchor - CAP0
        lai_sau = postv - CAP0
        xoa = (lai_truoc - lai_sau) / lai_truoc * 100 if lai_truoc else float("nan")
        say("    equity: %s (truoc W)=%.0f -> %s (sau W)=%.0f | W low=%.0f (%.2f%% tu dinh W)"
            % (pre.index[-1].date(), anchor, (post.index[0].date() if len(post) else "-"),
               postv, float(wq.min()), drop))
        say("    lai luy ke (eq-35000): truoc=%.0f -> sau=%.0f ⇒ BI XOA %.1f%%"
            % (lai_truoc, lai_sau, xoa))
        say("    equity/cua window: " + ", ".join(
            "%s=%.0f" % (t.strftime("%m-%d"), v) for t, v in pe.items()))

        # --- % lai 2025 truoc/sau
        d25 = d[d["te"].dt.year == 2025]
        pre25 = d25[d25["te"] < W_START]["pnl"].sum()
        in25 = d25[(d25["te"] >= W_START) & (d25["te"] <= W_END)]["pnl"].sum()
        post25 = d25[d25["te"] > W_END]["pnl"].sum()
        tot25 = pre25 + in25 + post25
        say("    lai 2025 theo leg: truoc W=%.0f (%.1f%%) | trong W=%.0f (%.1f%%) | sau W=%.0f (%.1f%%) | tong=%.0f"
            % (pre25, pre25 / tot25 * 100, in25, in25 / tot25 * 100, post25,
               post25 / tot25 * 100, tot25))
        e2024 = e[e.index <= pd.Timestamp("2024-12-31")]
        p2025 = eq_end - float(e2024.iloc[-1])
        say("    lai 2025 theo EQUITY: %.0f (eq 2024-12-31=%.0f -> eq 2025-12-30=%.0f)"
            % (p2025, float(e2024.iloc[-1]), eq_end))
        # --- THAM KHAO (exploratory, NGOAI danh sach pre-reg; khong dung lam ket luan)
        tw, hw, _ = sweep(d)
        jw = int(np.argmin(np.abs(tw - PEAK_EXP.value // 60_000_000_000)))
        idf = intraday(base)
        iw = idf[(idf.index >= W_START) & (idf.index <= W_END)]
        anch_int = float(e[e.index < W_START].iloc[-1])
        loww = float(iw["low"].min())
        say("    [tham khao] open margin @ dinh exposure %s = %.0f USDT (max toan ky %.0f)"
            % (PEAK_EXP, hw[jw], hw.max()))
        say("    [tham khao] moc-to-market trong ngay (b+unPMin; KHONG phai pre-reg): W low=%.0f = %+.1f%% tu dinh %.0f"
            % (loww, (loww / anch_int - 1) * 100, anch_int))
        eo = d[(d["ts"] >= E_DAY) & (d["ts"] < E_DAY + pd.Timedelta(days=1))]
        neg = float(eo[eo["pnl"] < 0]["pnl"].sum())
        say("    [tham khao] leg MO trong ngay E (2025-10-10 UTC): n=%d Σpnl=%.0f | Σpnl(am)=%.0f | worst=%.0f"
            % (len(eo), float(eo["pnl"].sum()), neg, float(eo["pnl"].min())))
        R.setdefault(tag, {})["exploratory"] = dict(
            peak_open_margin=float(hw[jw]), peak_open_margin_all=float(hw.max()),
            w_intraday_low=loww, w_intraday_low_pct=float((loww / anch_int - 1) * 100),
            n_leg_E=int(len(eo)), pnl_E=float(eo["pnl"].sum()), pnl_E_neg=neg)

        R.setdefault(tag, {})["B"] = dict(
            n_open=len(win), n_closed_w=len(inw), pnl_w=float(inw["pnl"].sum()),
            conc_all=[ceall[1], ceall[0], ceall[2]], conc_w=[ce[1], ce[0], ce[2]],
            eq_anchor=anchor, eq_post=postv, drop_w=drop, lai_truoc=lai_truoc,
            lai_sau=lai_sau, xoa=xoa, pnl25_pre=float(pre25), pnl25_in=float(in25),
            pnl25_post=float(post25), profit25_eq=float(p2025), eq_end=eq_end)

        # ------------------------------------------------ VIEC C
        say("VIEC C. stress chi phi (cost = 0.008*margin tren MOI leg dong trong W)")
        msum = float(inw["margin"].sum())
        say("    Σmargin(W) = %.0f USDT ⇒ cost goc(W) = %.0f USDT" % (msum, COST * msum))
        cC = []
        for k in (1, 2, 5, 10):
            dP = -(k - 1) * COST * msum
            e2 = eq_end + dP
            cC.append(dict(k=k, dPnL=dP, eq=e2, cagr=cagr(e2, years),
                           dcagr=cagr(e2, years) - cagr(eq_end, years)))
            say("    x%-2d : ΔPnL=%+10.0f USDT | eq=%9.0f | CAGR=%.2f%% (Δ%+.2f pp) | ΔPnL/lai2025=%.1f%%"
                % (k, dP, e2, cagr(e2, years), cagr(e2, years) - cagr(eq_end, years),
                   abs(dP) / p2025 * 100))
        R[tag]["C_cost"] = cC

        # 1 coin ve -90 / -100
        cc_all, cc_nocap = ceall, ce
        say("    1 coin ve -90%/-100% khi dang giu (max_t margin_1coin/equity):")
        for lab, c in (("TOAN KY (max)", cc_all), ("TRONG W", cc_nocap)):
            say("      %-12s %s %.2f%% equity ⇒ mat -90%%: %.2f%% | -100%%: %.2f%% equity"
                % (lab, c[1], c[0], c[0] * 0.90, c[0] * 1.00))
        n1, s1, blk, sub = conc_replay(d, e, 0.15)
        ce_cap = coin_exposure(sub, e) if len(sub) else (0, None, None, 0)
        say("    REPLAY OFFLINE conc<=15%% (xap xi, khong phai sim): n=%d (tu %d), Σpnl=%.0f (tu %.0f), "
            "chan=%d ⇒ max 1 coin=%.2f%% equity (%s) ⇒ -90%%: %.2f%% equity"
            % (n1, len(d), s1, float(d["pnl"].sum()), blk, ce_cap[0], ce_cap[1], ce_cap[0] * 0.90))
        say("    BOUND ly thuyet: 0.15 x 0.90 = 13.50% equity / su kien (khong the hon)")
        R[tag]["C_coin0"] = dict(conc_all=cc_all[0], conc_all_sym=cc_all[1],
                                 conc_w=cc_nocap[0], replay=dict(n=n1, s=s1, blk=blk,
                                                                 conc=ce_cap[0]))
        # doi chieu artifact THAT
        if tag == "T170":
            dc_ = legs(CC_TIGHT)
            ec = equity(CC_TIGHT)
            ce_t = coin_exposure(dc_, ec)
            n2, s2, blk2, _ = conc_replay(dc_, ec, 0.05)
            say("    DOI CHIEU THAT CC_TIGHT_T170 (cap 0.05/5%%, md5 fad1b63e, n=%d): max 1 coin=%.2f%% equity (%s)"
                % (len(dc_), ce_t[0], ce_t[1]))
            R[tag]["C_cc_tight"] = dict(n=len(dc_), conc=ce_t[0], sym=ce_t[1])

        # ------------------------------------------------ VIEC D
        say("VIEC D. 1-2 leg margin lon nhat dang mo trong W — gia dinh exit FAIL, chiu -X% margin")
        big = win.sort_values("margin", ascending=False).head(2).reset_index(drop=True)
        base_dd = maxdd(e)
        r2024 = float(e2024.iloc[-1])
        say("    leg lon nhat: %s m=%.0f (%.2f%% equity) %s->%s pnl=%.0f"
            % (big.loc[0, "sym"], big.loc[0, "margin"], big.loc[0, "margin"] / eq_end * 100,
               big.loc[0, "ts"].strftime("%m-%d %H:%M"), big.loc[0, "te"].strftime("%m-%d %H:%M"),
               big.loc[0, "pnl"]))
        dD = []
        for nleg in (1, 2):
            msumD = float(big.loc[:nleg - 1, "margin"].sum())
            for X in (20, 50, 80, 90, 100):
                loss = X / 100.0 * msumD
                e2 = eq_end - loss
                # equity NGAY dieu chinh: tru loss tu ngay ket thuc leg lon nhat
                t0 = big.loc[nleg - 1, "te"]
                eadj = e.copy()
                eadj[eadj.index >= t0] -= loss
                dd2 = maxdd(eadj)
                dD.append(dict(n=-nleg, X=X, msum=msumD, loss=loss, eq=e2,
                               dpnl=-loss, cagr=cagr(e2, years),
                               dcagr=cagr(e2, years) - cagr(eq_end, years),
                               dmaxdd=dd2 - base_dd))
                say("    %d leg (Σm=%.0f): -%3d%% ⇒ ΔPnL=%+9.0f | ΔCAGR=%+6.2f pp | ΔmaxDD=%+6.2f pp "
                    "(%.2f->%.2f%%) | ΔPnL/lai2025=%.1f%%"
                    % (nleg, msumD, X, -loss, cagr(e2, years) - cagr(eq_end, years),
                       dd2 - base_dd, base_dd, dd2, loss / p2025 * 100))
        R[tag]["D_grid"] = dD
        # nguong xoa sach
        m1 = float(big.loc[0, "margin"])
        m12 = float(big.loc[:1, "margin"].sum())
        say("    NGUONG XOA SACH: lai 2025 = %.0f | (eq_end-35000) = %.0f" % (p2025, eq_end - CAP0))
        say("      1 leg (m=%.0f): X*_nam = %.1f%% | X*_ky = %.1f%%"
            % (m1, p2025 / m1 * 100, (eq_end - CAP0) / m1 * 100))
        say("      2 leg (Σm=%.0f): X*_nam = %.1f%% | X*_ky = %.1f%%"
            % (m12, p2025 / m12 * 100, (eq_end - CAP0) / m12 * 100))
        R[tag]["D_thresh"] = dict(m1=m1, m12=m12, profit25=p2025, profit_all=eq_end - CAP0,
                                  x_star_1y_single=p2025 / m1 * 100,
                                  x_star_all_single=(eq_end - CAP0) / m1 * 100,
                                  x_star_1y_two=p2025 / m12 * 100,
                                  x_star_all_two=(eq_end - CAP0) / m12 * 100,
                                  base_maxdd=base_dd)

    # --- kiem cheo: T170 printDone byte-identical CC_OFF/CC_ON
    return R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=os.path.join(OUTDIR, "blackswan.json"))
    a = ap.parse_args()
    say("BLACKSWAN_2510 — W(UTC) %s .. %s | ngay su kien %s" % (W_START, W_END, E_DAY))
    idx, syms, M = vc_a(say)
    vc_bcd(say, idx, syms, M)
    with open(a.json, "w") as f:
        json.dump(R, f, indent=2, ensure_ascii=False, default=str)
    with open(os.path.join(OUTDIR, "report_blackswan.txt"), "w") as f:
        f.write("\n".join(REPORT) + "\n")
    L.info("done -> %s", a.json)


if __name__ == "__main__":
    main()
