"""PREREG_GRAVEYARD (2e031f1): om bag sau time-stop + DCA 1:1 toi da K leg theo BIG_DOWN — loi tren von khoa? Offline, hourly close."""
import logging, numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s"); L = logging.getLogger("grave")
H = 3600000; D = 24 * H
d = pd.read_csv("/home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv", usecols=lambda c: c and not c.startswith("Unnamed"))
d["t0"] = (pd.to_datetime(d.end, format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)).astype("int64") // 10**6
d["ts"] = (pd.to_datetime(d.start, format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)).astype("int64") // 10**6
events = np.sort(d.loc[d.level == "BIG_DOWN", "ts"].unique()); L.info("BIG_DOWN events: %d", len(events))
sl = d[(d.status == "STOP_LOSS_DONE") & (d.level == "PREDICT_SYMBOL_TRADE")].copy(); L.info("time-stop PST: %d", len(sl))
m = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv"); mp = dict(zip(m.symbol.str.replace("USDT$", "", regex=True), m.symId))
sl["sid"] = sl.sym.map(mp); L.info("map ok %.3f", sl.sid.notna().mean()); sl = sl[sl.sid.notna()]
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")]); a = np.fromfile("/home/ubuntu/java/fsrun/CLOSES_1H.bin", dtype=DT)
P = pd.DataFrame({"ts": a["ts"].astype(np.int64), "sym": a["sym"].astype(np.int32), "c": a["c"].astype(np.float64)}); del a
TEND = int(P.ts.max()); series = {s: g.set_index("ts").c.sort_index() for s, g in P.groupby("sym")}
L.info("closes toi %s", pd.Timestamp(TEND, unit="ms"))

def simulate(r, K):
    s = series.get(int(r.sid))
    if s is None: return None
    fut = s[s.index > r.t0]
    if len(fut) == 0: return None
    last_ts = int(fut.index.max()); U = float(r.margin)
    legs = [(r.t0, float(r.tp))]  # (time, price) — leg 0 = giu tu gia cat
    last_leg = r.t0
    if K > 0:
        for ev in events[(events > r.t0 + H)]:
            if len(legs) - 1 >= K: break
            if ev - last_leg < D: continue
            px = fut[fut.index <= ev]
            if len(px) == 0: continue
            px = float(px.iloc[-1]); avg = np.mean([p for _, p in legs])  # 1:1 => avg cost = mean gia leg
            if px <= 0.80 * avg:
                legs.append((ev, px)); last_leg = ev
    out = {"sym": r.sym, "yr": pd.Timestamp(r.t0, unit="ms").year, "depth": r.profit, "U": U, "nleg": len(legs), "last_ts": last_ts,
           "delist_gap_d": (TEND - last_ts) / D, "capdays": U * len(legs) * (TEND - r.t0) / D}
    cap = U * len(legs)
    for hz, name in ((90, "90"), (180, "180"), (365, "365"), (None, "end")):
        t_h = TEND if hz is None else r.t0 + hz * D
        if t_h > TEND: out[f"v_{name}"] = np.nan; out[f"cap_{name}"] = np.nan; continue
        w = fut[fut.index <= t_h]
        if len(w) == 0: out[f"v_{name}"] = np.nan; out[f"cap_{name}"] = np.nan; continue
        delisted = (t_h - last_ts) > 7 * D
        p_h = 0.0 if delisted else float(w.iloc[-1])
        p_h_alt = float(w.iloc[-1])
        # von tinh theo leg da vao TRUOC t_h
        legs_h = [(t, p) for t, p in legs if t <= t_h]
        val = sum(U * p_h / p for _, p in legs_h); val_alt = sum(U * p_h_alt / p for _, p in legs_h); c = U * len(legs_h)
        out[f"v_{name}"] = val; out[f"valt_{name}"] = val_alt; out[f"cap_{name}"] = c; out[f"delist_{name}"] = float(delisted)
        out[f"ret_{name}"] = val / c - 1; out[f"be_{name}"] = float(val >= c); out[f"p50_{name}"] = float(val >= 1.5 * c)
        out[f"bad_{name}"] = float(delisted or val / c - 1 <= -0.80)
    return out

def summarize(X, tag):
    L.info("\n===== %s =====", tag)
    for name in ("90", "180", "365", "end"):
        ok = X[f"cap_{name}"].notna()
        if ok.sum() == 0: continue
        x = X[ok]; cw = x[f"v_{name}"].sum() / x[f"cap_{name}"].sum() - 1; cw_alt = x[f"valt_{name}"].sum() / x[f"cap_{name}"].sum() - 1
        L.info("%-4s n=%3d | loi/von khoa=%+.1f%% (delist=gia cuoi: %+.1f%%) | median vi the=%+.1f%% | veBE=%.1f%% | >=+50%%=%.1f%% | delist=%.1f%% | delist_or<=-80=%.1f%% | leg TB=%.2f",
               name, len(x), 100*cw, 100*cw_alt, 100*x[f"ret_{name}"].median(), 100*x[f"be_{name}"].mean(), 100*x[f"p50_{name}"].mean(),
               100*x[f"delist_{name}"].mean(), 100*x[f"bad_{name}"].mean(), x.nleg.mean())
    ok = X["cap_180"].notna(); x = X[ok]; rng = np.random.default_rng(20260911); bs = []
    for _ in range(2000):
        i = rng.integers(0, len(x), len(x)); bs.append(x.v_180.values[i].sum() / x.cap_180.values[i].sum() - 1)
    lo, hi = np.percentile(bs, [2.5, 97.5]); L.info("180d loi/von khoa CI95 = [%+.1f%%, %+.1f%%]  (n=%d)", 100*lo, 100*hi, len(x))
    g = x.groupby("yr").apply(lambda q: pd.Series({"n": len(q), "loi180%": 100*(q.v_180.sum()/q.cap_180.sum()-1), "veBE180%": 100*q.be_180.mean(), "bad180%": 100*q.bad_180.mean()}))
    L.info("theo nam cat:\n%s", g.round(1).to_string())
    x = x.assign(bin=pd.cut(x.depth, [-100, -50, -30, -20, -10, 0], labels=["<-50", "-50..-30", "-30..-20", "-20..-10", "-10..0"]))
    g = x.groupby("bin", observed=True).apply(lambda q: pd.Series({"n": len(q), "loi180%": 100*(q.v_180.sum()/q.cap_180.sum()-1), "veBE180%": 100*q.be_180.mean(), "bad180%": 100*q.bad_180.mean()}))
    L.info("theo do sau luc cat:\n%s", g.round(1).to_string())
    return lo, x

res = {}
for K, tag in ((0, "H0 hold"), (1, "D1 (<=1 leg DCA 1:1)"), (2, "D2 (<=2 leg DCA 1:1) PRIMARY")):
    rows = [simulate(r, K) for _, r in sl.iterrows()]; X = pd.DataFrame([r for r in rows if r]); res[K] = summarize(X, tag)
lo, x2 = res[2]; ok365 = x2["cap_365"].notna(); bad365 = 100 * x2.loc[ok365, "bad_365"].mean()
L.info("\n== QUYET DINH (PREREG muc 4): D2 CI95 duoi 180d = %+.1f%% (can > 0) ; delist_or<=-80 @365d = %.1f%% (can < 15, n=%d) => %s",
       100*lo, bad365, ok365.sum(), "DANG PRE-REG SIM" if (lo > 0 and bad365 < 15) else "DONG")
L.info("von-ngay khoa (D2, den cuoi): %.0f USDT-ngay tren %d vi the (TB %.0f ngay/vi the); engine PST quay vong 1 don vi ~13h", x2.capdays.sum(), len(x2), x2.capdays.sum()/x2.cap_end.fillna(0).sum() if x2.cap_end.fillna(0).sum() else 0)

# ===== MO TA NGOAI PRE-REG (khong quyet dinh): "VE BO" = gia von TRUNG BINH tinh tu GIA VAO GOC e0 (gom ca lo da chim).
# Leg 0 = U tai e0 (vi the goc, KHONG cat). DCA 1:1 toi da K leg khi gia <= 0.80*avg theo BIG_DOWN, cooldown 24h. Thoat khi gia >= avg*mult.
# So sanh voi "CAT tai time-stop": loi = p0/e0 - 1 (chinh la `profit` cua lenh).
def simulate_exit(r, K, mult):
    s = series.get(int(r.sid)); fut = s[s.index > r.t0] if s is not None else None
    if fut is None or len(fut) == 0: return None
    U = float(r.margin); e0 = float(r.entry); legs = [(r.ts, e0)]; avg = e0; last_leg = r.t0; t_cur = r.t0; exit_t = None
    idx = fut.index.values; vals = fut.values
    def first_hit(t_a, t_b):
        m = (idx > t_a) & (idx <= t_b) & (vals >= avg * mult); return int(idx[m][0]) if m.any() else None
    for ev in events[events > r.t0 + H]:
        h = first_hit(t_cur, ev)
        if h is not None: exit_t = h; break
        if len(legs) - 1 < K and ev - last_leg >= D:
            m = idx <= ev
            if m.any():
                px = float(vals[m][-1])
                if px <= 0.80 * avg: legs.append((ev, px)); avg = float(np.mean([p for _, p in legs])); last_leg = ev
        t_cur = ev
    if exit_t is None: exit_t = first_hit(t_cur, TEND)
    last_ts = int(idx.max()); out = {"yr": pd.Timestamp(r.t0, unit="ms").year, "depth": r.profit, "nleg": len(legs), "cut_val": U * float(r.tp) / e0, "U": U}
    for hz, name in ((90, "90"), (180, "180"), (365, "365"), (None, "end")):
        t_h = TEND if hz is None else r.t0 + hz * D
        if t_h > TEND: out[f"cap_{name}"] = np.nan; continue
        if exit_t is not None and exit_t <= t_h:
            cap = U * len([1 for t, _ in legs if t <= exit_t]); out[f"val_{name}"] = cap * mult; out[f"cap_{name}"] = cap; out[f"exit_{name}"] = 1.0; out[f"days_{name}"] = (exit_t - r.t0) / D
        else:
            legs_h = [(t, p) for t, p in legs if t <= t_h]; cap = U * len(legs_h); m = idx <= t_h
            if not m.any(): out[f"cap_{name}"] = np.nan; continue
            delisted = (t_h - last_ts) > 7 * D; p_h = 0.0 if delisted else float(vals[m][-1])
            out[f"val_{name}"] = sum(U * p_h / p for _, p in legs_h); out[f"cap_{name}"] = cap; out[f"exit_{name}"] = 0.0; out[f"days_{name}"] = (t_h - r.t0) / D
        out[f"extra_{name}"] = out[f"cap_{name}"] - U   # von DCA them
    return out
for K, mult, tag in ((0, 1.00, "H0 om, thoat khi VE BO e0"), (2, 1.00, "D2 (<=2 leg 1:1) thoat khi VE BO avg"), (2, 1.07, "D2 thoat khi +7% tren avg"), (2, 9.99, "D2 om toi cung (khong thoat)"), (3, 1.00, "NGOAI PRE-REG D3 (<=3 leg 1:1) thoat VE BO avg"), (4, 1.00, "NGOAI PRE-REG D4 (<=4 leg 1:1) thoat VE BO avg"), (3, 9.99, "NGOAI PRE-REG D3 om toi cung"), (4, 9.99, "NGOAI PRE-REG D4 om toi cung")):
    X = pd.DataFrame([r for r in (simulate_exit(r, K, mult) for _, r in sl.iterrows()) if r])
    L.info("\n===== MO TA: %s =====", tag)
    for name in ("90", "180", "365", "end"):
        ok = X[f"cap_{name}"].notna(); x = X[ok]
        if len(x) == 0: continue
        pnl_hold = x[f"val_{name}"].sum() - x[f"cap_{name}"].sum(); pnl_cut = x.cut_val.sum() - x.U.sum()
        L.info("%-4s n=%3d | ve bo/thoat=%.1f%% (ngay TB=%.0f) | PnL om+DCA=%+.0f vs PnL CAT=%+.0f (chenh %+.0f = %+.1f%% tren von goc) | von DCA them=%.0f (%.0f%% von goc) | chua thoat: n=%d, loi tren von median=%+.1f%%",
               name, len(x), 100*x[f"exit_{name}"].mean(), x.loc[x[f"exit_{name}"] == 1, f"days_{name}"].mean() if (x[f"exit_{name}"] == 1).any() else 0,
               pnl_hold, pnl_cut, pnl_hold - pnl_cut, 100*(pnl_hold - pnl_cut)/x.U.sum(), x[f"extra_{name}"].sum(), 100*x[f"extra_{name}"].sum()/x.U.sum(),
               (x[f"exit_{name}"] == 0).sum(), 100*((x[f"val_{name}"]/x[f"cap_{name}"]-1)[x[f"exit_{name}"] == 0]).median() if (x[f"exit_{name}"] == 0).any() else 0)
    ok = X["cap_180"].notna(); x = X[ok]; rng = np.random.default_rng(20260911); bs = []
    for _ in range(2000):
        i = rng.integers(0, len(x), len(x)); bs.append(((x.val_180.values[i] - x.cap_180.values[i]) - (x.cut_val.values[i] - x.U.values[i])).sum() / x.U.values[i].sum())
    L.info("180d chenh (om+DCA - CAT)/von goc CI95 = [%+.1f%%, %+.1f%%] | theo nam: %s", 100*np.percentile(bs, 2.5), 100*np.percentile(bs, 97.5),
           {y: round(100*((g.val_180 - g.cap_180).sum() - (g.cut_val - g.U).sum())/g.U.sum(), 1) for y, g in x.groupby("yr")})

# ===== MO TA NGOAI PRE-REG (y user 11/09 toi): om + DCA 1:1 <=K leg; khi gia >= avg*1.07 => ARM va TRAILING nhu C3
# (giveback = min(0.5*peak, cap), cap 0.08 STRONG / 0.03 WEAK (symbolPred<0.29); SL = avg*(1+peak-giveback)); chua arm => khong SL.
def simulate_trail(r, K):
    s = series.get(int(r.sid)); fut = s[s.index > r.t0] if s is not None else None
    if fut is None or len(fut) == 0: return None
    U = float(r.margin); e0 = float(r.entry); legs = [(r.ts, e0)]; avg = e0; last_leg = r.t0
    cap_gb = 0.03 if float(r.symbolPred) < 0.29 else 0.08
    idx = fut.index.values; vals = fut.values; last_ts = int(idx.max())
    evs = events[events > r.t0 + H]; ei = 0; armed = False; peak = 0.0; exit_t = None; exit_px = None
    for j in range(len(idx)):
        t = int(idx[j]); px = float(vals[j])
        # su kien BIG_DOWN roi vao gio nay (ev <= t va > gio truoc)
        while ei < len(evs) and evs[ei] <= t:
            if not armed and len(legs) - 1 < K and evs[ei] - last_leg >= D and px <= 0.80 * avg:
                legs.append((int(evs[ei]), px)); avg = float(np.mean([p for _, p in legs])); last_leg = int(evs[ei])
            ei += 1
        rate = px / avg - 1
        if not armed:
            if rate >= 0.07: armed = True; peak = rate
        else:
            if rate > peak: peak = rate
            sl_rate = peak - min(0.5 * peak, cap_gb)
            if rate <= sl_rate: exit_t = t; exit_px = avg * (1 + sl_rate); break
    cap = U * len(legs); out = {"yr": pd.Timestamp(r.t0, unit="ms").year, "depth": r.profit, "nleg": len(legs), "armed": float(armed),
                                "cut_pnl": U * (float(r.tp) / e0 - 1), "U": U, "cap": cap}
    for hz, name in ((180, "180"), (365, "365"), (None, "end")):
        t_h = TEND if hz is None else r.t0 + hz * D
        if t_h > TEND: out[f"pnl_{name}"] = np.nan; continue
        if exit_t is not None and exit_t <= t_h:
            legs_x = [(tt, p) for tt, p in legs if tt <= exit_t]; capx = U * len(legs_x)
            out[f"pnl_{name}"] = sum(U * exit_px / p for _, p in legs_x) - capx; out[f"cap_{name}"] = capx; out[f"ex_{name}"] = 1.0
        else:
            legs_h = [(tt, p) for tt, p in legs if tt <= t_h]; caph = U * len(legs_h); m = idx <= t_h
            if not m.any(): out[f"pnl_{name}"] = np.nan; continue
            delisted = (t_h - last_ts) > 7 * D; p_h = 0.0 if delisted else float(vals[m][-1])
            out[f"pnl_{name}"] = sum(U * p_h / p for _, p in legs_h) - caph; out[f"cap_{name}"] = caph; out[f"ex_{name}"] = 0.0
    return out
for K in (0, 2, 3, 4):
    X = pd.DataFrame([r for r in (simulate_trail(r, K) for _, r in sl.iterrows()) if r])
    L.info("\n===== MO TA: OM + DCA 1:1 <=%d leg + ARM 7%% + TRAILING C3 =====  armed=%.1f%%  leg TB=%.2f", K, 100*X.armed.mean(), X.nleg.mean())
    for name in ("180", "365", "end"):
        ok = X[f"pnl_{name}"].notna(); x = X[ok]
        if len(x) == 0: continue
        pnl = x[f"pnl_{name}"].sum(); cut = x.cut_pnl.sum(); U0 = x.U.sum(); ret = x[f"pnl_{name}"] / x[f"cap_{name}"]
        top = x[f"pnl_{name}"].sort_values(ascending=False); k5 = max(1, int(0.05 * len(top)))
        L.info("%-4s n=%3d | PnL om=%+.0f vs CAT=%+.0f | chenh %+.1f%% von goc | da thoat(trail)=%.1f%% | ret/von: med=%+.1f%% p90=%+.1f%% max=%+.0f%% | top5%% lenh gop %+.0f (=%.0f%% |PnL CAT|) | von them=%.0f%% | chua thoat: n=%d med=%+.1f%%",
               name, len(x), pnl, cut, 100*(pnl - cut)/U0, 100*x[f"ex_{name}"].mean(), 100*ret.median(), 100*ret.quantile(.9), 100*ret.max(),
               top.head(k5).sum(), 100*top.head(k5).sum()/abs(cut), 100*(x[f"cap_{name}"].sum()-U0)/U0, int((x[f"ex_{name}"]==0).sum()), 100*ret[x[f"ex_{name}"]==0].median() if (x[f"ex_{name}"]==0).any() else 0)
    ok = X["pnl_180"].notna(); x = X[ok]; rng = np.random.default_rng(20260911); bs = []
    for _ in range(2000):
        i = rng.integers(0, len(x), len(x)); bs.append((x.pnl_180.values[i] - x.cut_pnl.values[i]).sum() / x.U.values[i].sum())
    L.info("180d chenh CI95 = [%+.1f%%, %+.1f%%] | theo nam: %s", 100*np.percentile(bs, 2.5), 100*np.percentile(bs, 97.5),
           {y: round(100*(g.pnl_180 - g.cut_pnl).sum()/g.U.sum(), 1) for y, g in x.groupby("yr")})
