#!/usr/bin/env python3
"""OB_SR 02: price-path outcomes from Vision 1m klines + tsx_v2 replay engine.

Entry outcomes: arm168, mfe24, mfe72.
Arm outcomes (per seed, replay engine): giveback_bps, pnl_trail_bps, exit_j.
168h outcomes: extra24_bps, extra72_bps (price-only counterfactual).
"""
import json
import os
import sys
import time
from decimal import Decimal

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/tsx_v2")
import engine as EN  # noqa: E402

OUT = os.path.dirname(os.path.abspath(__file__))
KRAW = "/home/ubuntu/vz_e1/raw"
FUND = "/home/ubuntu/vz/out/funding"
MARK = 168 * 60 + 1
HOR = 264 * 60
ARM = np.float32(0.07)


def kfile(ym):
    if ym < "2021-12":
        return "/home/ubuntu/claude_master/gvz/k2021/kline1m-%s.parquet" % ym
    return KRAW + "/kline1m-%s.parquet" % ym


def load_month(ym, syms):
    fn = kfile(ym)
    if not os.path.exists(fn) or not syms:
        return {}
    t = pd.read_parquet(fn, columns=["ts", "sym", "open", "high", "low", "close"])
    t = t[t["sym"].isin(syms)]
    out = {}
    for s, v in t.groupby("sym", sort=False):
        v = v.sort_values("ts")
        out[s] = (v["ts"].to_numpy(np.int64), v["open"].to_numpy(np.float32),
                  v["high"].to_numpy(np.float32), v["low"].to_numpy(np.float32),
                  v["close"].to_numpy(np.float32))
    return out


def load_fund(ym, syms):
    fn = "%s/%s/%s.parquet" % (FUND, ym[:4], ym)
    if not os.path.exists(fn):
        return {}
    x = pd.read_parquet(fn, columns=["ts", "sym", "rate"])
    x = x[x["sym"].isin(syms)]
    return {s: (v["ts"].to_numpy(np.int64), v["rate"].to_numpy(np.float64)) for s, v in x.groupby("sym")}


def ticks():
    ex = json.load(open("/home/ubuntu/java/exchange_info_pin.json"))
    out = {}
    for s in ex["symbols"]:
        for fl in s["filters"]:
            for f in fl:
                if f.get("tickSize") is not None:
                    out[s["symbol"]] = Decimal(EN.jstr(np.float32(float(f["tickSize"]))))
    return out


def nextym(ym):
    return str((pd.Timestamp(ym + "-01") + pd.offsets.MonthBegin(1)))[:7]


def main():
    A = pd.read_parquet(OUT + "/anchors.parquet")
    G = pd.read_parquet(OUT + "/anchor.parquet")
    A["t0"] = pd.to_datetime(A["t0"])
    G["t0"] = pd.to_datetime(G["t0"])
    G["ym"] = G["t0"].dt.strftime("%Y-%m")
    TK = ticks()
    months = sorted(G["ym"].unique())
    syms_month = {m: set(G.loc[G["ym"] == m, "sym"] + "USDT") for m in months}
    allsyms = set(G.sym + "USDT")
    sub_by = {(s, t): list(v.itertuples()) for (s, t), v in A.groupby(["sym", "t0"], sort=False)}
    frames, fc = {}, {}
    rows = []
    nreplay = 0
    t_start = time.time()
    for m in months:
        nxt = nextym(m)
        need_m = syms_month.get(m, set()) | syms_month.get(months[months.index(m) - 1], set()) if months.index(m) > 0 else syms_month.get(m, set())
        need_n = syms_month.get(nxt, set()) | syms_month.get(m, set())
        if m not in frames:
            frames[m] = load_month(m, need_m)
        if nxt not in frames:
            frames[nxt] = load_month(nxt, need_n)
        for ym in (m, nxt, nextym(nxt)):
            if ym not in fc:
                fc[ym] = load_fund(ym, allsyms)
        cur, nx = frames[m], frames[nxt]
        Gg = G[G["ym"] == m]
        for r in Gg.itertuples():
            s = r.sym + "USDT"
            a = cur.get(s)
            if a is None:
                rows.append(dict(sym=r.sym, t0=r.t0, nbars=0))
                continue
            b = nx.get(s)
            if b is not None:
                ts = np.concatenate([a[0], b[0]])
                O = np.concatenate([a[1], b[1]]); H = np.concatenate([a[2], b[2]])
                L = np.concatenate([a[3], b[3]]); C = np.concatenate([a[4], b[4]])
            else:
                ts, O, H, L, C = a
            i0 = int(np.searchsorted(ts, r.t0_ms, side="left"))
            if i0 >= len(ts) or ts[i0] != r.t0_ms:
                rows.append(dict(sym=r.sym, t0=r.t0, nbars=0))
                continue
            n = min(HOR + 1, len(ts) - i0)
            o, h, l, c = O[i0:i0 + n], H[i0:i0 + n], L[i0:i0 + n], C[i0:i0 + n]
            E = np.float32(r.E)
            hh = h[1:min(n, 10081)]
            hit = np.flatnonzero(hh >= E * np.float32(1.07))
            arm_j = int(hit[0]) + 1 if len(hit) else -1
            mfe24 = float(np.nanmax(h[1:min(n, 1441)]) / E - 1) * 1e4 if n > 1 else np.nan
            mfe72 = float(np.nanmax(h[1:min(n, 4321)]) / E - 1) * 1e4 if n > 1 else np.nan
            px0 = float(c[0]) if n > 0 else np.nan
            pxa = float(c[arm_j]) if arm_j > 0 and arm_j < n else np.nan
            def pre(gi, k=6):
                lo = max(0, gi - k)
                return list(L[lo:gi + 1]), list(H[lo:gi + 1])
            lo0, hi0 = pre(i0)
            loa, hia = pre(i0 + arm_j) if arm_j > 0 else ([], [])
            lo6, hi6 = pre(i0 + MARK)
            px168 = np.nan; j168 = -1
            if n > MARK:
                px168 = float(c[MARK]); j168 = MARK
            elif n > 0:
                px168 = float(c[n - 1]); j168 = n - 1
            ok168 = (j168 >= 0) and (MARK - j168 <= 5)
            extra24 = extra72 = np.nan
            if ok168:
                if MARK + 1440 < n:
                    extra24 = (float(c[MARK + 1440]) - px168) / float(r.E) * 1e4
                if MARK + 4320 < n:
                    extra72 = (float(c[MARK + 4320]) - px168) / float(r.E) * 1e4
            gb, pt, ej = [], [], []
            if arm_j > 0:
                fts = np.concatenate([fc[ym].get(s, (np.zeros(0, np.int64), np.zeros(0)))[0] for ym in (m, nxt, nextym(nxt))])
                frt = np.concatenate([fc[ym].get(s, (np.zeros(0, np.int64), np.zeros(0)))[1] for ym in (m, nxt, nextym(nxt))])
                k = (fts > r.t0_ms) & (fts <= r.t0_ms + n * 60000)
                fts, frt = fts[k], frt[k]
                arr = np.stack([o, h, l, c], axis=1)
                w = EN.Win(arr, r.t0_ms, (fts, frt), TK.get(s))
                for q in sub_by.get((r.sym, r.t0), []):
                    legs = [(int(j), float(e), float(qq)) for j, e, qq in q.legs]
                    res = EN.replay(w, legs)
                    nreplay += 1
                    if res["st"] != "OPEN" and np.isfinite(res["tp"]):
                        jex = int(res["j"])
                        a0 = max(0, min(arm_j, jex))
                        seg = h[a0:min(jex + 1, len(h))]
                        if not len(seg) or not np.isfinite(seg).any():
                            continue
                        peak = float(np.nanmax(seg))
                        gb.append((peak - float(res["tp"])) / peak * 1e4)
                        pt.append(float(res["pnl"]) / float(q.notional) * 1e4)
                        ej.append(jex)
            rows.append(dict(
                sym=r.sym, t0=r.t0, nbars=int(n), arm_j=arm_j, mfe24_bps=mfe24, mfe72_bps=mfe72,
                px0=px0, px_arm=pxa,
                pre_lo0=lo0, pre_hi0=hi0, pre_loa=loa, pre_hia=hia, pre_lo6=lo6, pre_hi6=hi6,
                px168=px168, ok168=bool(ok168), extra24_bps=extra24, extra72_bps=extra72,
                gb_med=float(np.median(gb)) if gb else np.nan,
                pt_med=float(np.median(pt)) if pt else np.nan,
                exit_j_med=float(np.median(ej)) if ej else np.nan,
                nseed_replay=len(gb)))
        for k in list(frames):
            if k not in (m, nxt):
                frames.pop(k, None)
        for k in list(fc):
            if k not in (m, nxt, nextym(nxt)):
                fc.pop(k, None)
        print("month %s anchors=%d elapsed=%.0fs replays=%d" % (m, len(Gg), time.time() - t_start, nreplay), flush=True)
    R = pd.DataFrame(rows)
    R.to_parquet(OUT + "/price_out.parquet", index=False)
    print("arm anchors", int((R.arm_j > 0).sum()), "ok168", int(R.ok168.sum()), "replays", nreplay)
    print(R[["mfe24_bps", "mfe72_bps", "gb_med", "pt_med", "extra24_bps", "extra72_bps"]].describe().to_string())


if __name__ == "__main__":
    main()
