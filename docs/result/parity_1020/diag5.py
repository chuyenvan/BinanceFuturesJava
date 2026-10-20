#!/usr/bin/env python3
"""S1 lech: thu moi diem OI (ref) kha di trong [now-2h, now] cho tung (phut, coin) lech; neu co ref cho score KHOP
dung float32 voi live => lech do THOI DIEM OI (kha dung luc nap cache), khong phai close/code."""
import numpy as np, pandas as pd, json
W = "/home/ubuntu/claude_master/parity_1020"
src = open(W + "/s1_off.py").read().split('res = {"modes": {}}')[0]
exec(src)
R = pd.read_csv(W + "/out_s1_E35.csv.gz")
R["ex"] = R.score_live.astype(np.float32) == R.score_off.astype(np.float32)
mins_s = sorted(R.ts.unique())[::8]
out = []
for ts in mins_s:
    uni = set(F45.symbol[F45.ts == ts])
    H0 = (ts // H) * H
    # tinh feature day du (E35) de co phan bo oid cua coin khac
    j1 = (H0 - hmin) // H
    cand = sorted(x for x in uni if x in SIDX)
    Cw = CL[[SIDX[x] for x in cand], j1 - (NH - 1):j1 + 1]
    keep = ~np.all(np.isnan(Cw), axis=1)
    syms = [x for x, k in zip(cand, keep) if k]
    base_sc, _, _ = s1_scores(uni, ts, "E35")
    # lay lai X bang cach goi noi bo: tinh oid/lsg E35
    oid = np.array([oi_feats2(x, ts, H0, "E35")[0] for x in syms])
    lsg = np.array([oi_feats2(x, ts, H0, "E35")[1] for x in syms])
    C = Cw[keep]; n = NH - 1; cn = C[:, n]; w = C[:, n - 167:n + 1]
    nn = np.sum(~np.isnan(w), axis=1)
    with np.errstate(all="ignore"):
        mx = np.nanmax(np.where(np.isnan(w), -np.inf, w), axis=1)
        dd = np.where((nn >= 84) & ~np.isnan(cn) & (mx != 0) & np.isfinite(mx), cn / mx - 1, np.nan)
        ww = np.where(np.isnan(w), -np.inf, w); k = np.argmax(ww, axis=1)
        hrs = np.where(((168 - nn) <= 84) & np.isfinite(ww[np.arange(len(k)), k]), (167 - k) / 168.0, np.nan)
        rr = C[:, n - 167:n + 1] / C[:, n - 168:n] - 1; nr = np.sum(~np.isnan(rr), axis=1)
        vol = np.where((nr >= 84) & (nr >= 2), np.nanstd(rr, axis=1, ddof=1), np.nan)
        r3 = cn / C[:, n - 72] - 1; r14 = cn / C[:, n - 336] - 1
    rkdd, rkr3 = rank_pct(dd), rank_pct(r3)
    L = R[(R.ts == ts) & (~R.ex)]
    for _, r in L.iterrows():
        s = r.symbol
        if s not in syms:
            out.append(dict(ts=ts, symbol=s, verdict="not_in_offline_universe")); continue
        i = syms.index(s)
        d_, l_ = oi.get(s, ((np.array([], dtype=np.int64), np.array([])),) * 2)
        refs = [None] + [int(x) for x in d_[0] if ts - 2 * H <= x <= ts]
        found = None
        for ref in refs:
            o = np.nan if ref is None else val_of(d_, ref)
            g = np.nan if ref is None else val_of(l_, ref)
            oo = oid.copy(); oo[i] = o
            rk = rank_pct(oo)[i]
            x = np.array([[vol[i], dd[i], rkdd[i], hrs[i], r3[i], rkr3[i], r14[i], g, rk]], dtype=np.float32)
            sc = np.float32(-np.asarray(S1.run(None, {s1in: x})[0]).reshape(-1)[0])
            if sc == np.float32(r.score_live):
                found = ref; break
        e35 = floor_tol(d_[0][d_[0] >= H0 - 24 * H], ts, H0 - 35 * MIN) if len(d_[0]) else None
        out.append(dict(ts=ts, symbol=s, verdict=("oi_ref_match" if found is not None else ("oi_none_match" if found is None and refs and False else "no_oi_ref_matches")),
                        ref_found=found, ref_e35=e35, lag_found_min=None if found is None else (H0 - found) / MIN,
                        lag_e35_min=None if e35 is None else (H0 - e35) / MIN))
O = pd.DataFrame(out)
print("rows tested", len(O))
print(O.verdict.value_counts())
print("lag (H0 - ref live) phut:", O.lag_found_min.describe().round(1).to_dict())
print(O.lag_found_min.value_counts().head(12).to_dict())
O.to_csv(W + "/out_diag5.csv", index=False)
json.dump(dict(n=len(O), verdict=O.verdict.value_counts().to_dict(), lag=O.lag_found_min.describe().to_dict(),
               lag_mode=O.lag_found_min.value_counts().head(12).to_dict()), open(W + "/diag5.json", "w"), indent=1, default=str)
