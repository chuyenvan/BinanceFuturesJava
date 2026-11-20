"""run_s2.py - gop ket qua fetch_reduce + KIEM W0-W6 (+ E1b) + thong ke + luat L2-A/B/C (PREREG_GRIDV2_S2 muc 7-9).
Thu tu: moi kiem W chay TRUOC; bat ky W nao FAIL -> result_s2.json chi co khoi W, rule = "W_FAIL", KHONG tinh M.

Dung (chay that):
  python3 run_s2.py --stage precheck --events EVDIR --expected-sha EXPECTED_SHA.txt --run2 RUN2 --s1code S1DIR --out RESDIR
  python3 run_s2.py --stage full --events EVDIR --fetch FETCH_OUT --sample sample.csv --sample-sha SHA --expected-sha EXPECTED_SHA.txt \
      --run2 ~/claude_master/w3/gridv2/run2 --s1code ~/claude_master/vz_e1_wt/research/gridv2_s1 --out RESDIR
Hang so prereg (khong CLI / env): san 4 bps, alpha nua B 0,04 (1 phia; MASTER D1), nua A M > 4 & p <= 0,10, B = 2000, khoi 20 ngay,
seed 2026112160 (+1 nua B, +10 TOUCH, +100 co trong so), MIN_UNITS 200, W2 >= 0,99, W3 dong y >= 0,97 & |dM| <= 1 bps,
W5 >= 200 don vi 0 lech, W6 thieu <= 3 % moi nua.
"""
import argparse
import glob
import hashlib
import json
import logging
import os
import sys
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tl_engine as E  # noqa: E402
import tl_ref as TR  # noqa: E402
import sample as SM  # noqa: E402

log = logging.getLogger("run_s2")
FLOOR = 4.0
ALPHA_B = 0.04                 # MASTER D1 (size do: 4,25 % null cum; toi 7,5 % neu phu thuoc che do 30 ngay)
ALPHA_A = 0.10
NBOOT = 2000
SEED_S2 = 2026112160
MIN_UNITS = 200
W2_MIN = 0.99
W3_AGREE_MIN = 0.97
W3_DM_MAX = 1.0
W5_MIN_UNITS = 200
W4_SEED = 2026112170
DS = E.DATA_START_MS
DAY = 86400000
MIN = 60000
HALF_B_DAY = SM.HALF_B_DAY
STUDY_DAY = SM.STUDY_DAY
NDAY = SM.NDAY
EVENTS = [("2022-05-09", "2022-05-13"), ("2022-11-08", "2022-11-10"), ("2025-10-10", "2025-10-13")]
S2_CODE = ("tl_engine.py", "tl_ref.py", "sample.py", "fetch_reduce.py", "run_s2.py", "events_kernel.py")
S1_PIN = {"klite.py": "196f458489c5a808754d4afc39c2ad03f9149d57936de7f84c810074b8652680",
          "stats.py": "975f3a427cd52750018d615b664ab13f899ee216764e5f80fca82192976df3e4"}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def import_s1(s1dir):
    for f, h in S1_PIN.items():
        if sha(os.path.join(s1dir, f)) != h:
            raise RuntimeError("sha S1 %s khong khop ghim - DUNG" % f)
    sys.path.insert(1, s1dir)
    import klite
    import stats
    return klite, stats


def read_expected(path):
    out = {}
    for line in open(path):
        p = line.split()
        if len(p) >= 2 and not line.startswith("#"):
            out[os.path.basename(p[1].lstrip("*"))] = p[0].lower()
    return out


# ------------------------------------------------------------------------------------------------------------ W checks
def w0_events(ev_dir, expected, allow_test):
    vals, mans = [], []
    for i in range(5):
        vf, mf = os.path.join(ev_dir, "validate_s%d.json" % i), os.path.join(ev_dir, "manifest_s%d.json" % i)
        if not (os.path.exists(vf) and os.path.exists(mf)):
            return dict(ok=False, why="thieu shard %d" % i)
        vals.append(json.load(open(vf)))
        mans.append(json.load(open(mf)))
    shards = sorted(m["shard"] for m in mans)
    ok = shards == ["%d/5" % i for i in range(5)]
    ok &= all(v.get("all_pass") is True for v in vals)
    ok &= all(m.get("prereg_constants") is True for m in mans) or allow_test
    ok &= len({json.dumps(m["inputs"], sort_keys=True) for m in mans}) == 1
    if expected is not None:
        want = {f: expected.get(f) for f in ("klite.py", "kref.py", "stats.py", "runner_kaggle.py", "events_kernel.py")}
        ok &= all(m["code"] == want for m in mans)
    return dict(ok=bool(ok), shards=shards, all_pass=[v.get("all_pass") for v in vals],
                prereg_constants=[m.get("prereg_constants") for m in mans])


def w0_fetch(fetch_dir, ev):
    bad = 0
    n = 0
    fl = os.path.join(fetch_dir, "files.jsonl")
    for line in (open(fl) if os.path.exists(fl) else []):
        r = json.loads(line)
        n += 1
        if r["date"] >= "2026-01-01" or (r.get("t_max", -1) >= E.SEAL_MS):
            bad += 1
    ok = bad == 0 and (ev.t0_ms.max() < E.SEAL_MS) and (ev.date.max() < "2026-01-01")
    return dict(ok=bool(ok), n_files=n, n_bad=bad)


def e1b_vs_run2(ev, run2_dir):
    """Tong theo (mo hinh, ngay) cua danh sach su kien == bang reduced/agg o 20 cua lan chay S1 (run2)."""
    ag = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(run2_dir, "d*", "reduced", "agg.parquet")))])
    ag = ag[ag.cell == 20].groupby(["model", "day"]).sum(numeric_only=True)
    mx = 0.0
    ok = True
    for model, pre in (("OPT", "o_"), ("PESS", "p_")):
        okm = ev[pre + "ok"] == 1
        mine = pd.DataFrame(dict(place=ev.groupby("day").size(),
                                 fill=okm.groupby(ev.day).sum(),
                                 net=ev[pre + "net"].where(okm, 0.0).groupby(ev.day).sum(),
                                 gross=ev[pre + "gross"].where(okm, 0.0).groupby(ev.day).sum())).fillna(0.0)
        ref = ag.loc[model][["place", "fill", "net", "gross"]]
        if set(ref.index) != set(mine.index):
            ok = False
        j = mine.join(ref, rsuffix="_r", how="outer").fillna(0.0)
        for c in ("place", "fill", "net", "gross"):
            d = np.abs(j[c] - j[c + "_r"]) - 1e-6 * np.abs(j[c + "_r"])
            mx = max(mx, float((j[c] - j[c + "_r"]).abs().max()))
            ok &= bool((d <= 1e-6).all())
    return dict(ok=bool(ok), max_abs_diff=mx)


def w1_sample(state, fr, sample_sha):
    sel = fr[fr.selected]
    keys = {"%s|%s" % (s, d) for s, d in zip(sel.sym, sel.date)}
    ok = state.get("sample_sha") == sample_sha and keys <= set(state["done"])
    rank = {"%s|%s" % (s, d): (st, r) for s, d, st, r in zip(fr.sym, fr.date, fr.stratum, fr["rank"])}
    last = {}
    for s in state["subs"]:
        if s["sub"] is None:
            continue
        st, r = rank[s["sub"]]
        ok &= st == s["stratum"] and s["sub"] not in keys and r > last.get(st, -1)
        last[st] = r
    return dict(ok=bool(ok), n_selected=len(keys), n_done=len(state["done"]), n_subs=len(state["subs"]))


def w2_bars(bars, kw):
    """Nen 1m dung lai tu aggTrades vs kline lake: phut lake hop le trong cua so cum mau, low VA high bang dung (dung sai 0)."""
    b = bars.drop_duplicates(["sym", "mi"])
    k = kw[kw.valid].merge(b[["sym", "mi", "o", "h", "l", "c", "n"]], on=["sym", "mi"], how="left", suffixes=("", "_t"))
    has = k.n.notna()
    hl = has & (k.l == k.l_t) & (k.h == k.h_t)
    oc = has & (k.o == k.o_t) & (k.c == k.c_t)
    n = len(k)
    trade_only = b.merge(kw[["sym", "mi", "valid"]], on=["sym", "mi"], how="inner")
    frac = float(hl.sum() / n) if n else float("nan")
    return dict(ok=bool(n > 0 and frac >= W2_MIN), n_minutes=int(n), frac_low_high_equal=frac,
                frac_open_close_equal=float(oc.sum() / n) if n else None, n_lake_valid_no_trades=int((~has).sum()),
                n_trades_lake_invalid=int((~trade_only.valid).sum()))


def w3_klite(klite, ev_s, bars, fmap):
    """klite S1 tren nen dung lai tu aggTrades (C[t0-1] := m0 lake) vs ket qua S1 tung don vi."""
    out = {}
    agree = {m: [0, 0, 0] for m in ("o", "p")}
    dm = {m: {} for m in ("o", "p")}
    bz = {k: g for k, g in bars.drop_duplicates(["sym", "mi"]).groupby("sym")}
    rows = {m: [] for m in ("o", "p")}
    for (sym, date), u in ev_s.groupby(["sym", "date"]):
        t0m = u.t0_min.to_numpy(np.int64)
        lo = int(t0m.min()) - 62
        hi = int((t0m + u.W.to_numpy() + u["T"].to_numpy()).max()) + 64
        n = hi - lo
        O = np.full(n, np.nan); H = O.copy(); L = O.copy(); C = O.copy()
        g = bz.get(sym)
        if g is not None:
            gg = g[(g.mi >= lo) & (g.mi < hi)]
            ii = gg.mi.to_numpy(np.int64) - lo
            O[ii], H[ii], L[ii], C[ii] = gg.o, gg.h, gg.l, gg.c
        valid = np.isfinite(C)
        C[t0m - 1 - lo] = u.m0.to_numpy()
        valid[t0m - 1 - lo] = True
        dle = int(u.dl_end_ms.iloc[0])
        dl = -1
        if dle >= 0:
            dl = (dle - DS) // MIN - 1 - lo
            if dl >= n:
                dl = -1
            elif dl < 0:
                dl = 0
        G = klite.prepare_grid(O, H, L, C, valid, dl)
        ft, fr = fmap.get(sym, (np.zeros(0, np.int64), np.zeros(0)))
        fs = (ft - DS) // MIN - lo
        kk = (fs >= 1) & (fs < n)
        for m, model in (("o", "OPT"), ("p", "PESS")):
            Rk = klite.run_units(G, t0m - lo, u.d.to_numpy(), u.W.to_numpy(), u["T"].to_numpy(), u.tick.to_numpy(),
                                 u.slip.to_numpy(), model, u.side.to_numpy(), fs[kk], fr[kk])
            f1 = Rk["filled"]
            f0 = u[m + "_filled"].to_numpy() == 1
            fm = np.where(f1, Rk["f"] + lo, -1)
            xm = np.where(f1, Rk["x"] + lo, -1)
            f0m = np.where(f0, (u[m + "_f_ms"].to_numpy() - DS) // MIN, -1)
            x0m = np.where(f0 & (u[m + "_x_ms"].to_numpy() >= 0), (u[m + "_x_ms"].to_numpy() - DS) // MIN, -1)
            same_fill = f1 == f0
            same_all = same_fill & (fm == f0m) & (np.where(f1, Rk["kind"], 0) == np.where(f0, u[m + "_kind"].to_numpy(), 0)) & (
                np.where(f1 & (Rk["excl"] == 0), xm, -1) == np.where(f0 & (u[m + "_excl"].to_numpy() == 0), x0m, -1))
            agree[m][0] += len(u)
            agree[m][1] += int(same_fill.sum())
            agree[m][2] += int(same_all.sum())
            ok1 = f1 & (Rk["excl"] == 0)
            ok0 = u[m + "_ok"].to_numpy() == 1
            half = "B" if int(u.day.iloc[0]) >= HALF_B_DAY else "A"
            a = dm[m].setdefault(half, [0.0, 0, 0.0, 0])
            a[0] += float(np.nansum(np.where(ok1, Rk["net"], 0.0)))
            a[1] += int(ok1.sum())
            a[2] += float(np.nansum(np.where(ok0, u[m + "_net"].to_numpy(), 0.0)))
            a[3] += int(ok0.sum())
    ok = True
    for m in ("o", "p"):
        n, sf, sa = agree[m]
        r = dict(n_units=n, agree_fill=sf / max(n, 1), agree_all=sa / max(n, 1))
        for h, a in dm[m].items():
            r["M_rebuilt_" + h] = a[0] / max(a[1], 1)
            r["M_s1_" + h] = a[2] / max(a[3], 1)
            r["dM_" + h] = r["M_rebuilt_" + h] - r["M_s1_" + h]
            ok &= abs(r["dM_" + h]) <= W3_DM_MAX
        ok &= n > 0 and r["agree_all"] >= W3_AGREE_MIN
        out[{"o": "K_OPT", "p": "K_PESS"}[m]] = r
    out["ok"] = bool(ok)
    return out


def window_kline(ev_s, res, kw):
    """Phut kline lake can kiem W2: thuoc cua so [t0 - 61, t0 + W + T + 61] cua don vi trong cum da mo phong VA nam trong du
    lieu giao dich da tai cua cum do."""
    rng_ = res[["sym", "date", "data_start", "data_end"]].drop_duplicates(["sym", "date"])
    e = ev_s[["sym", "date", "t0_min", "W", "T"]].merge(rng_, on=["sym", "date"])
    parts = []
    for r in e.drop_duplicates(["sym", "date", "t0_min"]).itertuples(index=False):
        m = np.arange(r.t0_min - 61, r.t0_min + r.W + r.T + 62, dtype=np.int64)
        m = m[(m >= (r.data_start - DS) // MIN) & (m < (r.data_end - DS) // MIN)]
        parts.append(pd.DataFrame(dict(sym=r.sym, mi=m)))
    if not parts:
        return kw.iloc[0:0]
    need = pd.concat(parts, ignore_index=True).drop_duplicates()
    return kw.merge(need, on=["sym", "mi"], how="inner")


def _unit_rows(u):
    return [dict(t0=int(r.t0_ms), side=int(r.side), L=float(r.L), X=float(r.X), tick=float(r.tick), W=int(r.W), T=int(r.T),
                 slip=float(r.slip), dl_end=int(r.dl_end_ms)) for r in u.itertuples()]


def w45_audit(fetch_dir, ev_s, res, fmap):
    """W4 (khong nhin tuong lai, rac sau moc tc) + W5 (tl_ref doc lap vs engine) + phat lai engine tren giao dich audit = ket
    qua luc fetch, tren cac cum audit."""
    rng = np.random.default_rng(W4_SEED)
    w4 = dict(n_full=0, d_full=0, n_out=0, d_out=0)
    w5 = dict(n_units=0, mismatch_ref=0, mismatch_replay=0)
    evg = {k: g for k, g in ev_s.groupby(["sym", "date"])}
    rz = {k: g for k, g in res.groupby(["sym", "date", "model"])}
    for fn in sorted(glob.glob(os.path.join(fetch_dir, "audit", "*.npz"))):
        sym, date = os.path.basename(fn)[:-4].rsplit("_", 1)
        z = np.load(fn)
        t, aid, p, ibm = z["t"], z["aid"], z["p"], z["ibm"]
        r0, r1 = int(z["r0"]), int(z["r1"])
        u = evg[(sym, date)].sort_values(["t0_ms", "side"], ascending=[True, False])
        U = dict(t0=u.t0_ms.to_numpy(np.int64), side=u.side.to_numpy(np.int64), L=u.L.to_numpy(), X=u.X.to_numpy(),
                 tick=u.tick.to_numpy(), W=u.W.to_numpy(np.int64), T=u["T"].to_numpy(np.int64), slip=u.slip.to_numpy(),
                 dl_end=u.dl_end_ms.to_numpy(np.int64))
        ft, fr = fmap.get(sym, (np.zeros(0, np.int64), np.zeros(0)))
        MS = E.collapse_ms(t, aid, p, ibm)
        P = TR.prepare(list(zip(t.tolist(), aid.tolist(), p.tolist(), ibm.tolist())))
        fund = list(zip(ft.tolist(), fr.tolist()))
        tc = int(rng.integers(int(U["t0"].min()), int(U["t0"].max()) + 230 * MIN + 1))
        t2p = p.copy()
        j = t >= tc
        t2p[j] = np.round(p[j] * rng.uniform(0.9, 1.1, j.sum()) / U["tick"][0]) * U["tick"][0]
        ib2 = ibm.copy()
        ib2[j] = rng.random(j.sum()) < 0.5
        MS2 = E.collapse_ms(t, aid, t2p, ib2)
        for m in E.MODELS:
            a = E.simulate(MS, U, m, r0, r1, ft, fr)
            stored = rz[(sym, date, m)].sort_values(["t0_ms", "side"], ascending=[True, False])
            for c in E.OUT_COLS:
                x, y = np.asarray(a[c], float), stored[c].to_numpy(float)
                if not np.array_equal(np.nan_to_num(x, nan=-9e99), np.nan_to_num(y, nan=-9e99)):
                    w5["mismatch_replay"] += 1
            refs = [TR.ref_unit(P, r, m, r0, r1, fund) for r in _unit_rows(u)]
            for i, rr in enumerate(refs):
                bad = any(int(a[c][i]) != int(rr[c]) for c in ("filled", "excl", "tf", "tx", "kind", "n_maker"))
                for c in ("xpx", "gross", "fee", "fee_stress", "slip", "fund", "net", "net_stress"):
                    x, y = float(a[c][i]), float(rr[c])
                    bad |= (np.isnan(x) != np.isnan(y)) or (not np.isnan(x) and abs(x - y) > 1e-9)
                w5["mismatch_ref"] += int(bad)
                w5["n_units"] += 1
            b = E.simulate(MS2, U, m, r0, r1, ft, fr)
            end = np.where(a["filled"] == 1, a["tx"], np.minimum(U["t0"] + U["W"] * MIN,
                                                                np.where(U["dl_end"] >= 0, U["dl_end"], 1 << 62)))
            for i in range(len(u)):
                same = [(a[c][i] == b[c][i]) or (np.isnan(a[c][i]) and np.isnan(b[c][i])) for c in E.OUT_COLS]
                if end[i] + E.GAP_MS < tc:
                    w4["n_full"] += 1
                    w4["d_full"] += int(not all(same))
                if end[i] < tc:
                    w4["n_out"] += 1
                    w4["d_out"] += int(not all(s for s, c in zip(same, E.OUT_COLS) if c != "excl"))
    w4["ok"] = bool(w4["d_full"] == 0 and w4["d_out"] == 0 and w4["n_full"] > 0)
    w5["n_units"] //= 2
    w5["ok"] = bool(w5["mismatch_ref"] == 0 and w5["mismatch_replay"] == 0 and w5["n_units"] >= W5_MIN_UNITS)
    return w4, w5


# ------------------------------------------------------------------------------------------------------------ thong ke
def _event_keep(lo, hi):
    """Bo ngay t0 trong [dau - 3 ngay, cuoi + 1 ngay) cua 3 su kien (nhu S1)."""
    keep = np.ones(hi - lo, bool)
    for a, b in EVENTS:
        elo = (int(pd.Timestamp(a, tz="UTC").value // 10**6) - 3 * DAY - DS) // DAY
        ehi = (int(pd.Timestamp(b, tz="UTC").value // 10**6) + DAY - DS) // DAY
        a_, b_ = max(elo, lo) - lo, min(ehi, hi) - lo
        if b_ > a_:
            keep[a_:b_] = False
    return keep


def analyze(stats, U, model, nboot=NBOOT, weighted=False):
    """U: bang don vi da mo phong (1 dong / don vi x mo hinh) co cot day, sym, tier, year, w, s_hat + OUT_COLS."""
    u = U[U.model == model]
    okm = (u.filled == 1) & (u.excl == 0)
    out = {}
    for h, (lo, hi) in (("A", (STUDY_DAY, HALF_B_DAY)), ("B", (HALF_B_DAY, NDAY))):
        inh = (u.day >= lo) & (u.day < hi)
        uh = u[okm & inh]
        w = uh.w.to_numpy() if weighted else np.ones(len(uh))
        D = hi - lo
        di = uh.day.to_numpy(np.int64) - lo
        S = np.bincount(di, weights=w * uh.net.to_numpy(), minlength=D)
        N = np.bincount(di, weights=w, minlength=D)
        seed = SEED_S2 + (1 if h == "B" else 0) + (10 if model == "TOUCH" else 0) + (100 if weighted else 0)
        st = stats.cell_stats(S[:, None], N[:, None], FLOOR, seed, B=nboot)
        nraw = len(uh)
        st_blocks = np.add.reduceat(np.bincount(di, minlength=D), np.arange(0, D, stats.BLOCK))
        nb = -(-D // stats.BLOCK)
        ins = bool(nraw < MIN_UNITS or int((st_blocks > 0).sum()) < -(-nb // 3) or not np.isfinite(st["M"][0])
                   or not np.isfinite(st["SE"][0]) or not st["SE"][0] > 0)
        M = float(st["M"][0])
        sw = max(w.sum(), 1e-12)
        cap = float((w * uh.s_hat.to_numpy() / 2.0 * uh.n_maker.to_numpy() * 1e4).sum() / sw)
        bys = pd.DataFrame(dict(sym=uh.sym.to_numpy(), s=w * uh.net.to_numpy(), n=w)).groupby("sym").sum().sort_values(
            "s", ascending=False)
        rest = bys.iloc[3:]
        keep = _event_keep(lo, hi)
        r = dict(n_placed=int(inh.sum()), n_excl=int((inh & (u.excl == 1)).sum()), n_fill=nraw, M=M, SE=float(st["SE"][0]),
                 p=float(st["p_marg"][0]), ci95=[float(st["ci95_lo"][0]), float(st["ci95_hi"][0])], insufficient=ins,
                 n_blocks_with_units=int((st_blocks > 0).sum()), M_adj_C4=M - cap, cap_mean=cap,
                 M_drop_top3=float(rest.s.sum() / max(rest.n.sum(), 1e-12)), top3=bys.index[:3].tolist(),
                 M_drop_events=float(S[keep].sum() / max(N[keep].sum(), 1e-12)),
                 M_maker_stress=float((w * uh.net_stress.to_numpy()).sum() / sw),
                 fill_rate=float(nraw / max(int((inh & (u.excl == 0)).sum()), 1)),
                 p_limit_exit=float((w * (uh.kind.to_numpy() == E.EX_LIMIT)).sum() / sw))
        for c in ("gross", "fee", "slip", "fund"):
            r[c + "_mean"] = float((w * uh[c].to_numpy()).sum() / sw)
        r["M_by_year"] = {int(y): float(g.net.sum() / len(g)) for y, g in uh.groupby("year")}
        r["M_by_tier"] = {int(t): float(g.net.sum() / len(g)) for t, g in uh.groupby("tier")}
        r["sd_unit"] = float(uh.net.std()) if nraw > 1 else None
        out[h] = r
    A, B = out["A"], out["B"]
    conds = dict(not_insufficient=not A["insufficient"] and not B["insufficient"], a_pB=B["p"] <= ALPHA_B and B["M"] > FLOOR,
                 b_A=A["M"] > FLOOR and A["p"] <= ALPHA_A, c_Madj_B=B["M_adj_C4"] > 0, d_top3_B=B["M_drop_top3"] > FLOOR,
                 e_events=A["M_drop_events"] > FLOOR and B["M_drop_events"] > FLOOR)
    out["conditions"] = {k: bool(v) for k, v in conds.items()}
    out["PASS"] = bool(all(conds.values()))
    return out


def decide(R):
    thr, tch = R["THROUGH"], R["TOUCH"]
    if thr["A"]["insufficient"] or thr["B"]["insufficient"]:
        return "L2-INS"
    if thr["PASS"]:
        return "L2-A"
    if tch["PASS"]:
        return "L2-B"
    return "L2-C"


def infra_label(rule, R, Rd):
    """MASTER D5 (chi nhan bo sung, luat khong doi): L2-A ma THROUGH_LAT5S khong PASS -> 'L2-A-INFRA' (ung vien chi kha thi
    voi ha tang dat lenh maker do tre thap; buoc ke gom xay ha tang truoc kiem ngoai mau)."""
    if rule == "L2-A" and not Rd["THROUGH_LAT5S"]["PASS"]:
        return "L2-A-INFRA"
    return rule


def build_units(res, ev, fr, state):
    e = ev[["sym", "t0_ms", "side", "day", "tier", "s_hat", "date"]]
    U = res.merge(e, on=["sym", "date", "t0_ms", "side"], how="left", validate="many_to_one")
    if U.day.isna().any():
        raise RuntimeError("ket qua khong ghep duoc voi danh sach su kien")
    U["year"] = U.date.str[:4].astype(int)
    done = {k for k, v in state["done"].items() if v.get("status") == "ok"}
    frk = fr.assign(k=fr.sym + "|" + fr.date)
    nproc = frk[frk.k.isin(done)].groupby("stratum").size()
    Nh = frk.groupby("stratum").n_stratum.first()
    U["w"] = U.stratum.map(Nh / nproc).astype(float)
    return U


def run(a, allow_test=False, nboot=NBOOT):
    klite, stats = import_s1(a.s1code)
    expected = None
    if not allow_test:
        expected = read_expected(a.expected_sha)
        for f in S2_CODE:
            if sha(os.path.join(HERE, f)) != expected.get(f):
                raise RuntimeError("sha code S2 %s khong khop EXPECTED_SHA - DUNG" % f)
    os.makedirs(a.out, exist_ok=True)
    fr, ssha = SM.read_csv(a.sample, a.sample_sha)
    ev, _ = SM.load_events(a.events)
    state = json.load(open(os.path.join(a.fetch, "state.json")))
    res = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(a.fetch, "res", "part_*.parquet")))],
                    ignore_index=True)
    bars = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(a.fetch, "bars", "part_*.parquet")))],
                     ignore_index=True)
    kw = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(a.events, "kline_win_s*.parquet")))],
                   ignore_index=True)
    fu = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(os.path.join(a.events, "funding_ev_s*.parquet")))],
                   ignore_index=True).drop_duplicates(["sym", "ts"]).sort_values(["sym", "ts"])
    fmap = {s: (g.ts.to_numpy(np.int64), g.rate.to_numpy(float)) for s, g in fu.groupby("sym")}
    done = [k for k, v in state["done"].items() if v.get("status") == "ok"]
    dk = pd.DataFrame([k.split("|") for k in done], columns=["sym", "date"])
    ev_s = ev.merge(dk, on=["sym", "date"])
    kw_s = window_kline(ev_s, res, kw)
    W = {}
    W["W0_events"] = w0_events(a.events, expected, allow_test)
    W["W0_fetch"] = w0_fetch(a.fetch, ev)
    W["E1b_vs_run2"] = e1b_vs_run2(ev, a.run2) if a.run2 else dict(ok=bool(allow_test), skipped=True)
    W["W1_sample"] = w1_sample(state, fr, ssha)
    W["W6_missing"] = state.get("W6", dict(ok=False))
    W["W2_bars_vs_kline"] = w2_bars(bars, kw_s)
    W["W3_klite_rebuilt"] = w3_klite(klite, ev_s, bars, fmap)
    W["W4_no_lookahead"], W["W5_ref"] = w45_audit(a.fetch, ev_s, res, fmap)
    allw = all(v.get("ok") for v in W.values())
    out = dict(TEST_ONLY=bool(allow_test), W=W, W_all_pass=bool(allw), sample_sha=ssha, floor=FLOOR, alpha_B=ALPHA_B,
               alpha_A=ALPHA_A, nboot=nboot, seed=SEED_S2)
    if not allw:
        out["rule"] = ("TEST_ONLY:" if allow_test else "") + "W_FAIL"
        json.dump(out, open(os.path.join(a.out, "result_s2.json"), "w"), indent=1, default=str)
        log.error("W FAIL: %s", {k: v.get("ok") for k, v in W.items()})
        return out
    U = build_units(res, ev, fr, state)
    R = {m: analyze(stats, U, m, nboot) for m in E.MODELS}
    Rw = {m: analyze(stats, U, m, nboot, weighted=True) for m in E.MODELS}
    Rd = {m: analyze(stats, U, m, nboot) for m in E.DIAG_MODELS}
    s1 = {}
    for m, pre in (("K_OPT", "o_"), ("K_PESS", "p_")):
        for h, (lo, hi) in (("A", (STUDY_DAY, HALF_B_DAY)), ("B", (HALF_B_DAY, NDAY))):
            e = ev_s[(ev_s[pre + "ok"] == 1) & (ev_s.day >= lo) & (ev_s.day < hi)]
            s1["%s_%s" % (m, h)] = dict(n=int(len(e)), M=float(e[pre + "net"].mean()) if len(e) else None)
    out.update(models=R, weighted=Rw, diag_models_report_only=Rd, s1_on_sample=s1, rule_core=decide(R),
               weighted_rule_core=decide(Rw))
    out["rule"] = ("TEST_ONLY:" if allow_test else "") + out["rule_core"]
    out["label"] = ("TEST_ONLY:" if allow_test else "") + infra_label(out["rule_core"], R, Rd)
    json.dump(out, open(os.path.join(a.out, "result_s2.json"), "w"), indent=1, default=str)
    log.info("rule %s", out["rule"])
    return out


def precheck(a):
    """Buoc 3 ke hoach chay (TRUOC khi lay mau): W0_events + E1b. Khong doc gi ngoai danh sach su kien va run2."""
    expected = read_expected(a.expected_sha)
    ev, shas = SM.load_events(a.events)
    out = dict(W0_events=w0_events(a.events, expected, False), E1b_vs_run2=e1b_vs_run2(ev, a.run2), events_sha256=shas,
               n_units=int(len(ev)), n_clusters=int(ev.groupby(["sym", "date"]).ngroups))
    out["ok"] = bool(out["W0_events"]["ok"] and out["E1b_vs_run2"]["ok"])
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(os.path.join(a.out, "precheck.json"), "w"), indent=1, default=str)
    log.info("precheck ok=%s", out["ok"])
    return out


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=("precheck", "full"), required=True)
    for k in ("events", "expected-sha", "run2", "s1code", "out"):
        ap.add_argument("--" + k, required=True)
    for k in ("fetch", "sample", "sample-sha"):
        ap.add_argument("--" + k, default=None)
    a = ap.parse_args()
    if a.stage == "precheck":
        precheck(a)
    else:
        run(a)


if __name__ == "__main__":
    main()
