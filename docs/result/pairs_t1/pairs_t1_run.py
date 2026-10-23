#!/usr/bin/env python3
"""PAIRS_T1 runner. Stages: main | controls | valid | report   (python3 pairs_t1_run.py <stage>)
Pre-reg docs/prereg/PREREG_PAIRS_T1.md. Outputs ~/claude_master/pairs/out/ (pickles) + small JSON for docs.
"""
import json
import logging
import os
import pickle
import sys
import time
from multiprocessing import Pool

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pairs_t1_core as K  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("pairs_t1_run")
OUT = os.path.expanduser("~/claude_master/pairs/out")
os.makedirs(OUT, exist_ok=True)
SEED = 20261023
N_C1 = 50      # V3 control reps (random pairs + random direction)
N_C2 = 20      # diagnostic reps (random pairs, rule direction)
PAIR_METHODS = ("M1", "M2", "M3")
P = None


def _init():
    global P
    if P is None:
        P = K.Panel()


# ------------------------------------------------------------------ main
def _main_window(k):
    t = K.window_start(k)
    U = K.universe(P, t)
    p1, ntest, npass = K.form_m1(P, t, U)
    p2 = K.form_m2(P, t, U)
    out = dict(k=k, t=t, U=U, p1=p1, p2=p2, ntest=ntest, npass=npass, res={})
    for name, tr in (("M1", K.sim_m1(P, t, p1)), ("M2", K.sim_m2(P, t, p2)), ("M3", K.sim_m3(P, t, p1))):
        g, u, f = K.account(P, t, tr)
        out["res"][name] = dict(g=g, u=u, f=f, trades=tr)
    return out


def stage_main():
    _init()
    t0 = time.time()
    with Pool(3) as pool:
        wins = pool.map(_main_window, range(P.NW), chunksize=4)
    pickle.dump(wins, open(os.path.join(OUT, "pairs_main.pkl"), "wb"))
    pickle.dump([(w["k"], w["t"], w["U"]) for w in wins], open(os.path.join(OUT, "univ.pkl"), "wb"))
    log.info("pairs main done NW=%d %.0fs", len(wins), time.time() - t0)
    sig = K.m4_signals(P)
    pickle.dump(sig, open(os.path.join(OUT, "m4_sig.pkl"), "wb"))
    log.info("m4 signals done %.0fs", time.time() - t0)
    m4 = {}
    for cv, c in K.COSTS.items():
        m4[cv] = K.sim_m4(P, sig, c, want_detail=(cv == "base"))
        log.info("m4 %s final eq %.4f %.0fs", cv, m4[cv]["eq"][-1], time.time() - t0)
    pickle.dump(m4, open(os.path.join(OUT, "m4_main.pkl"), "wb"))


# ------------------------------------------------------------------ controls
def _ctrl_rep(args):
    rep, flip = args
    _init()
    univ = pickle.load(open(os.path.join(OUT, "univ.pkl"), "rb"))
    rng = np.random.default_rng(SEED + 1000 * flip + rep)
    tot = {m: np.zeros((P.NW, 3)) for m in PAIR_METHODS}
    for k, t, U in univ:
        rp1 = K.rand_pairs_m1(P, t, U, rng)
        rp2 = K.rand_pairs_m2(P, t, U, rng)
        fr = rng if flip else None
        for name, tr in (("M1", K.sim_m1(P, t, rp1, fr)), ("M2", K.sim_m2(P, t, rp2, fr)),
                         ("M3", K.sim_m3(P, t, rp1, fr))):
            g, u, f = K.account(P, t, tr)
            tot[name][k] = (g[-1], u[-1], f[-1])
    return rep, flip, tot


def _ctrl_m4(rep):
    _init()
    sig = pickle.load(open(os.path.join(OUT, "m4_sig.pkl"), "rb"))
    rng = np.random.default_rng(SEED + 5000 + rep)
    r = K.sim_m4(P, sig, K.COSTS["base"], flip_rng=rng)
    return rep, dict(gsum=r["gsum"], fsum=r["fsum"], csum=r["csum"], eq_final=r["eq"][-1])


def stage_controls():
    _init()
    t0 = time.time()
    jobs = [(r, 1) for r in range(N_C1)] + [(r, 0) for r in range(N_C2)]
    with Pool(3) as pool:
        res = pool.map(_ctrl_rep, jobs, chunksize=1)
    log.info("pair controls done %.0fs", time.time() - t0)
    with Pool(3) as pool:
        r4 = pool.map(_ctrl_m4, range(N_C1), chunksize=1)
    log.info("m4 controls done %.0fs", time.time() - t0)
    pickle.dump(dict(pairs=res, m4=r4), open(os.path.join(OUT, "controls.pkl"), "wb"))


# ------------------------------------------------------------------ validations V1 V2 V4
def _same(a, b):
    return json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def _strip(trs):
    return [dict(e=t["e"], x=t["x"], why=t["why"], legs=[(int(s), float(w)) for s, w in t["legs"]]) for t in trs]


def stage_valid():
    import pyarrow.parquet as pq
    import pandas as pd
    _init()
    wins = pickle.load(open(os.path.join(OUT, "pairs_main.pkl"), "rb"))
    sig = pickle.load(open(os.path.join(OUT, "m4_sig.pkl"), "rb"))
    V = {}
    # ---- V1 future poison
    v1 = []
    for k in (10, 60, 120, 180, 240):
        w = wins[k]
        t = w["t"]
        Pp = P.copy_poisoned(t, seed=k)
        U2 = K.universe(Pp, t)
        p1b = K.form_m1(Pp, t, U2)[0]
        p2b = K.form_m2(Pp, t, U2)
        okf = bool(np.array_equal(U2, w["U"]) and _same(p1b, w["p1"]) and _same(p2b, w["p2"]))
        del Pp
        Pp = P.copy_poisoned(t + K.TRAD + 1, seed=k + 1)
        okt = True
        for name, fn, pp in (("M1", K.sim_m1, w["p1"]), ("M2", K.sim_m2, w["p2"]), ("M3", K.sim_m3, w["p1"])):
            tr = fn(Pp, t, pp)
            g, u, f = K.account(Pp, t, tr)
            r0 = w["res"][name]
            gaps = any(l["xe"] > t + K.TRAD for x in tr for l in x["ledger"])
            same = _same(_strip(tr), _strip(r0["trades"])) and np.allclose(g, r0["g"], atol=0, rtol=0) \
                and np.array_equal(u, r0["u"]) and np.array_equal(f, r0["f"])
            okt &= bool(same or gaps)
        del Pp
        # M4: s-scores at a decision hour inside week k
        r4 = 100                                  # decision row r <-> h = t-1+r (fill at open t+r)
        h = t - 1 + r4
        Pp = P.copy_poisoned(h + 1, seed=k + 2)
        R2 = K.log_returns(Pp)
        U4 = K.universe(Pp, t)
        Qd, _ = K.m4_pca(R2, t + 24 * (r4 // 24), U4)
        s2, b2 = K.m4_scores(R2, h, U4, Qd)
        s0 = sig[k]["s"][r4]
        ok4 = bool(np.array_equal(U4, sig[k]["U"]) and np.array_equal(np.nan_to_num(s2, nan=99), np.nan_to_num(s0, nan=99)))
        del Pp, R2
        v1.append(dict(k=k, formation_identical=okf, trades_identical=okt, m4_identical=ok4))
        log.info("V1 k=%d %s %s %s", k, okf, okt, ok4)
    V["V1"] = dict(windows=v1, PASS=all(d["formation_identical"] and d["trades_identical"] and d["m4_identical"] for d in v1))
    # ---- V2 delisted symbols in universe / trades
    inU = set()
    for w in wins:
        inU |= set(int(u) for u in w["U"])
    dl = [int(j) for j in inU if P.last[j] < P.NH - 31 * 24]
    nleg = {m: 0 for m in PAIR_METHODS}
    flags = {m: {"delist": 0, "gap": 0} for m in PAIR_METHODS}
    for w in wins:
        for m in PAIR_METHODS:
            for tr in w["res"][m]["trades"]:
                for l in tr["ledger"]:
                    if l["sym"] in dl:
                        nleg[m] += 1
                    if l["flag"]:
                        flags[m][l["flag"]] += 1
    V["V2"] = dict(delisted_in_universe=sorted(str(P.syms[j]) for j in dl), n=len(dl), legs_on_delisted=nleg,
                   fill_flags=flags, PASS=len(dl) > 0)
    # ---- V4 per-leg reconciliation vs raw Vision 1m + raw funding; window identities
    rng = np.random.default_rng(SEED + 7)
    raw_k = os.path.expanduser("~/claude_master/pairs/data/kline1m")
    raw_e1 = os.path.expanduser("~/vz_e1/raw")
    fund = pd.concat([pd.read_parquet(os.path.expanduser("~/claude_master/pairs/data/funding/funding-%d.parquet" % y))
                      for y in range(2021, 2026)])
    fund["sym"] = fund["sym"].astype(str)

    cache = {}

    def minute(sym, h, first=True):
        ts0 = K.H0_MS + h * 3600000
        mm = pd.Timestamp(ts0, unit="ms").strftime("%Y-%m")
        if (sym, mm) not in cache:
            p = os.path.join(raw_k, "kline1m-%s.parquet" % mm)
            p = p if os.path.exists(p) else os.path.join(raw_e1, "kline1m-%s.parquet" % mm)
            tb = pq.read_table(p, columns=["ts", "sym", "open", "close", "active"],
                               filters=[("sym", "=", sym)]).to_pandas()
            cache[(sym, mm)] = tb[tb.active].sort_values("ts").set_index("ts")
        tb = cache[(sym, mm)]
        tb = tb[(tb.index >= ts0) & (tb.index < ts0 + 3600000)]
        return None if tb.empty else (float(tb.open.iloc[0]) if first else float(tb.close.iloc[-1]))

    v4 = dict(legs=0, px_mismatch=0, fund_mismatch=0, pnl_mismatch=0, max_fund_rel=0.0, details=[])
    for m in PAIR_METHODS:
        allt = [(w["t"], tr) for w in wins for tr in w["res"][m]["trades"]]
        for i in rng.choice(len(allt), min(40, len(allt)), replace=False):
            t, tr = allt[i]
            for l in tr["ledger"]:
                s = str(P.syms[l["sym"]])
                pe = minute(s, l["e"])
                px = minute(s, l["xe"]) if l["flag"] != "delist" else l["px"]
                v4["legs"] += 1
                if pe != l["pe"] or px != l["px"]:
                    v4["px_mismatch"] += 1
                    v4["details"].append(dict(m=m, sym=s, e=l["e"], pe=l["pe"], pe_raw=pe, px=l["px"], px_raw=px))
                ts_lo = K.H0_MS + (l["e"] + 0.5) * 3600000
                ts_hi = K.H0_MS + (l["xe"] + 0.5) * 3600000
                fr = fund[(fund.sym == s) & (fund.ts > ts_lo) & (fund.ts < ts_hi)]
                fs = 0.0
                for _, row in fr.iterrows():
                    hf = int(round((row.ts - K.H0_MS) / 3600000))
                    mk = minute(s, hf)
                    if mk is None:
                        mk = float(P.CF[hf - 1, l["sym"]])
                    fs += -l["qty"] * mk * row.rate
                rel = abs(fs - l["fund"]) / max(1e-12, abs(l["fund"])) if l["fund"] != 0 else abs(fs)
                v4["max_fund_rel"] = max(v4["max_fund_rel"], rel)
                if rel > 1e-9:
                    v4["fund_mismatch"] += 1
                if abs(l["qty"] * (px - pe) - l["gross"]) > 1e-12:
                    v4["pnl_mismatch"] += 1
    ident = 0
    for w in wins:
        for m in PAIR_METHODS:
            r = w["res"][m]
            sg = sum(tr["gross"] for tr in r["trades"])
            su = sum(tr["turn"] for tr in r["trades"])
            sf = sum(tr["fund"] for tr in r["trades"])
            if abs(sg - r["g"][-1]) > 1e-12 or abs(su - r["u"][-1]) > 1e-12 or abs(sf - r["f"][-1]) > 1e-12:
                ident += 1
    m4 = pickle.load(open(os.path.join(OUT, "m4_main.pkl"), "rb"))
    m4id = {cv: abs(float(m4[cv]["attr"].sum()) - (m4[cv]["eq"][-1] - 1.0)) for cv in m4}
    v4["window_identity_fail"] = ident
    v4["m4_attr_identity_absdiff"] = m4id
    v4["details"] = v4["details"][:20]
    v4["PASS"] = (v4["px_mismatch"] == 0 and v4["fund_mismatch"] == 0 and v4["pnl_mismatch"] == 0 and ident == 0
                  and max(m4id.values()) < 1e-8)
    V["V4"] = v4
    json.dump(V, open(os.path.join(OUT, "valid.json"), "w"), indent=1, default=str)
    log.info("VALID V1 %s V2 %s V4 %s", V["V1"]["PASS"], V["V2"]["PASS"], V["V4"]["PASS"])


if __name__ == "__main__":
    st = sys.argv[1]
    {"main": stage_main, "controls": stage_controls, "valid": stage_valid}[st]()
