#!/usr/bin/env python3
"""EXEC_MAKER_T170 — execution realism: maker (post-only) vs taker tren 1089 lenh T170.

Pre-reg: docs/PREREG_EXECUTION_MAKER.md (commit e2eb646, chot TRUOC khi chay).

Thuan Python. KHONG Java, KHONG claude-run, KHONG push, KHONG cham 2026, KHONG sua tham so.

Du lieu:
  * leg:  /home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv (md5 efb793e2..., n=1089)
  * nen:  /home/ubuntu/claudedata/rvb_1m/raw/<SYM>USDT.f32  [ts<i4,o,h,l,c,v f4], ts = phut epoch UTC
          start/end trong printDone.csv la GIO GMT+7 (naive).

Mo hinh chi phi (Configs.java:103,117): sim = RATE_FEE 0,002 x1 chan + SLIPPAGE_RATE 0,003 x2 = 0,80% RT.
Slip proxy per chan = 0,5*(high-low)/close tai DUNG phut khop (entry bar / exit bar) — do BIEN DONG,
KHONG phai tac dong thi truong.

Trung gian: /tmp/exec_maker/  (don sau khi commit).
"""
import os
import json
import hashlib
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
OUT = os.environ.get("EM_OUT", "/tmp/exec_maker")
PRINT_DONE = os.environ.get(
    "EM_PRINT_DONE", "/home/ubuntu/java/devrun/X1_GS_T170_2021/storage/printDone.csv")
RAW = os.environ.get("EM_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
MD5_EXPECT = "efb793e2468ca3a7318da0f0ad23d4fc"
N_EXPECT = 1089

# --- hang so chi phi (doc tu code/docs, khong bia) ---
SIM_RT = 0.800000        # % round-trip: RATE_FEE 0.002*1 + SLIPPAGE_RATE 0.003*2 (Configs.java:103,117)
FEE = {                  # % round-trip theo chan
    "A": 0.10,           # taker 0.05 x2
    "B": 0.07,           # entry maker 0.02 + exit taker 0.05
    "C": 0.04,           # maker 0.02 x2
}
SLIP_BASES = (("proxy", None), ("universe", 0.140), ("1bp", 0.010))   # %/chan
P_GRID = (0.2, 0.4, 0.6, 0.8, 1.0)
R_REP = 200
SEED = 20260923
BLOCK_MIN = 72 * 60
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

os.makedirs(OUT, exist_ok=True)
REPORT = []
def say(s=""):
    REPORT.append(s)
    print(s, flush=True)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


# ------------------------------------------------------------------ load + gates
def load():
    md = md5(PRINT_DONE)
    df = pd.read_csv(PRINT_DONE)
    say("[G1] md5 printDone = %s (cho %s) %s" % (md, MD5_EXPECT, "OK" if md == MD5_EXPECT else "**LECH**"))
    say("[G1] n_dong  = %d (cho %d) %s" % (len(df), N_EXPECT, "OK" if len(df) == N_EXPECT else "**LECH**"))
    assert md == MD5_EXPECT and len(df) == N_EXPECT

    t7 = pd.to_datetime(df["start"], format="%Y%m%d %H:%M")
    df["t_min"] = ((t7.astype("int64") // 10**9) - 7 * 3600) // 60
    df["day"] = ((t7.astype("int64") // 10**9 - 7 * 3600) // 86400)
    e = df["end"].astype(str).str.strip().str.lstrip("'").str.strip()
    tE = pd.to_datetime(e, format="%Y%m%d %H:%M")
    df["te_min"] = ((tE.astype("int64") // 10**9) - 7 * 3600) // 60
    df["symfull"] = df["sym"].astype(str) + "USDT"

    df["notional"] = df["quantity"] * df["entry"]
    rel = ((df["notional"] - df["margin"]).abs() / df["margin"]).max()
    say("[G2] |notional/margin - 1| max = %.2e (cho < 1e-6) %s" % (rel, "OK" if rel < 1e-6 else "**LECH**"))

    df["gross"] = df["profit"].astype(float)
    df["net_sim"] = 100.0 * df["pnl"] / df["notional"]
    df["cost_actual"] = df["gross"] - df["net_sim"]
    df["funding"] = df["cost_actual"] - SIM_RT
    resid = (df["gross"] - SIM_RT - df["funding"] - df["net_sim"]).abs().max()
    say("[G3] tai tao net_sim tu (gross - 0,80 - funding): |resid| max = %.2e %s"
        % (resid, "OK" if resid < 1e-9 else "**LECH**"))
    say("[G3] cost_actual: median = %.6f%% (min %.4f / max %.4f) | funding mean = %+.4f%%/lenh"
        % (df["cost_actual"].median(), df["cost_actual"].min(), df["cost_actual"].max(), df["funding"].mean()))
    g5 = int((t7 >= pd.Timestamp("2026-01-01")).sum())
    say("[G5] so dong start >= 2026-01-01: %d %s" % (g5, "OK" if g5 == 0 else "**LECH**"))

    # --- proxy slip tai DUNG phut khop (entry + exit), streaming, cache nho ---
    s_e = np.full(len(df), np.nan)
    s_x = np.full(len(df), np.nan)
    miss_file = miss_bar = 0
    cache = {}
    for i, r in df.iterrows():
        p = os.path.join(RAW, r["symfull"] + ".f32")
        if not os.path.exists(p):
            miss_file += 1
            continue
        if r["symfull"] not in cache:
            if len(cache) > 3:
                cache.clear()
            cache[r["symfull"]] = np.fromfile(p, dtype=DT)
        a = cache[r["symfull"]]
        ts = a["ts"].astype(np.int64)
        for mm, arr in ((int(r["t_min"]), s_e), (int(r["te_min"]), s_x)):
            j = np.searchsorted(ts, mm)
            if j < len(ts) and ts[j] == mm:
                arr[i] = 0.5 * (float(a["h"][j]) - float(a["l"][j])) / float(a["c"][j]) * 100.0
            else:
                miss_bar += 1
    ok = np.isfinite(s_e) & np.isfinite(s_x)
    say("[G4] proxy slip co du ca 2 chan: %d/1089 (thieu file %d, thieu nen %d) %s"
        % (ok.sum(), miss_file, miss_bar, "OK" if ok.sum() == N_EXPECT else "**LECH**"))
    df["s_e"], df["s_x"] = s_e, s_x
    df = df[ok].reset_index(drop=True)
    say("[G4] proxy: entry mean %.4f%% median %.4f%% | exit mean %.4f%% median %.4f%% | RT mean %.4f%% median %.4f%%"
        % (df["s_e"].mean(), df["s_e"].median(), df["s_x"].mean(), df["s_x"].median(),
           (df["s_e"] + df["s_x"]).mean(), (df["s_e"] + df["s_x"]).median()))
    return df, t7[ok].reset_index(drop=True)


# ------------------------------------------------- 5. do lai moc "universe 0,140%"
def universe_proxy(df):
    """median 0,5*(h-l)/c tren TOAN BO nen 1m cua cac coin xuat hien trong 1089 lenh."""
    syms = sorted(df["symfull"].unique())
    med, allv = [], []
    for s in syms:
        p = os.path.join(RAW, s + ".f32")
        if not os.path.exists(p):
            continue
        a = np.fromfile(p, dtype=DT)
        c = a["c"].astype(np.float64)
        v = 0.5 * (a["h"].astype(np.float64) - a["l"].astype(np.float64)) / c * 100.0
        v = v[np.isfinite(v) & (c > 0)]
        if len(v):
            med.append(float(np.median(v)))
            step = max(1, len(v) // 20000)
            allv.append(v[::step])
    med = np.array(med)
    allv = np.concatenate(allv)
    q = np.percentile(allv, [50, 75, 90, 95, 99])
    say("[UNIV] %d coin: median(tung coin) -> median %.4f%% mean %.4f%%" % (len(med), np.median(med), med.mean()))
    say("[UNIV] pool %d nen: p50 %.4f%% p75 %.4f%% p90 %.4f%% p95 %.4f%% p99 %.4f%%"
        % (len(allv), q[0], q[1], q[2], q[3], q[4]))
    return {"n_coin": len(med), "coin_median": float(np.median(med)),
            "pool_p50": float(q[0]), "pool_p75": float(q[1]), "pool_p90": float(q[2]),
            "pool_p95": float(q[3]), "pool_p99": float(q[4])}


# ------------------------------------------------------------------ scenarios
def slip_of(scn, df, base):
    if scn == "S":
        return np.full(len(df), 0.60)
    if scn == "C":
        return np.zeros(len(df))
    if base[0] == "proxy":
        return (df["s_e"] + df["s_x"]).values if scn == "A" else df["s_x"].values
    return np.full(len(df), base[1] * (2 if scn == "A" else 1))


def net_of(scn, df, slip):
    fee = 0.20 if scn == "S" else FEE[scn]
    return df["gross"].values - fee - slip - df["funding"].values


def metrics(df, net):
    n = len(df)
    notl = df["notional"].values
    sum_notl = notl.sum()
    sum_net = float((notl * net / 100.0).sum())
    return {
        "n": n,
        "sum_notional": sum_notl,
        "sum_net_usdt": sum_net,
        "meanP": float(np.mean(net)),
        "aggP": float(sum_notl and (notl * net).sum() / sum_notl),
        "win": float(np.mean(net > 0) * 100.0),
    }


def boot_ci(vals, days, rng, nrep=2000):
    """bootstrap block-72h tren mean (mo ta)."""
    order = np.argsort(days, kind="stable")
    v = vals[order]
    d = days[order]
    uniq, start = np.unique(d, return_index=True)
    # gom block 3 ngay ke tiep
    blocks, i0 = [], 0
    daylist = list(uniq)
    bstart = {}
    for k, dd in enumerate(daylist):
        bstart[dd] = k // 3
    bid = np.array([bstart[dd] for dd in d])
    nb = bid.max() + 1
    idx = [np.where(bid == b)[0] for b in range(nb)]
    out = np.empty(nrep)
    for r in range(nrep):
        pick = rng.integers(0, nb, nb)
        s = np.concatenate([idx[b] for b in pick])
        out[r] = v[s].mean()
    return float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))


def main():
    say("=== EXEC_MAKER_T170 — execution realism maker vs taker (1089 lenh T170) ===")
    say("Pre-reg docs/PREREG_EXECUTION_MAKER.md (commit e2eb646). Thuan Python.")
    df, t7 = load()
    univ = universe_proxy(df)
    days = df["day"].values
    rng = np.random.default_rng(SEED)

    # ---------------- bang 1: 3 kich ban x 3 moc slip (khong p; p=1,0 = day du) ----------------
    say("\n### BANG 1 — 3 kich ban x 3 moc slip (p = 1,0, KHONG bo lenh)")
    say("| Kich ban | slip base | n | SigmaNotional | SigmaNet (USDT) | meanP/notional (%) | agg (%/notional) | win% | chi phi/lenh (%) |")
    say("|---|---|---|---|---|---|---|---|---|")
    scen_net = {}
    rows1 = {}
    for scn in ("S", "A", "B", "C"):
        for base in SLIP_BASES:
            if scn in ("S", "C") and base[0] != "proxy":
                continue
            slip = slip_of(scn, df, base)
            net = net_of(scn, df, slip)
            m = metrics(df, net)
            fee = 0.20 if scn == "S" else FEE[scn]
            tot_cost = fee + float(slip.mean()) + float(df["funding"].mean())
            key = "%s/%s" % (scn, base[0])
            scen_net[key] = net
            rows1[key] = dict(m, cost_per_order=tot_cost, slip_mean=float(slip.mean()))
            say("| **%s** %s | %s | %d | %.0f | %+.1f | **%+.4f** | %+.4f | %.1f | %.4f |"
                % (scn, {"S": "(sim 0,80%)", "A": "(taker that)", "B": "(entry maker/exit taker)",
                         "C": "(ca hai maker)"}[scn], base[0], m["n"], m["sum_notional"],
                   m["sum_net_usdt"], m["meanP"], m["aggP"], m["win"], tot_cost))
        say("")

    # ---------------- bang 2: quet p (mo hinh i.i.d. + adverse selection) ----------------
    say("### BANG 2 — quet p khop maker (B, C): mo hinh (i) i.i.d. ngau nhien R=%d seed %d | (ii) adverse-selection xau-nhat-truoc" % (R_REP, SEED))
    say("| scn | slip base | p | n_con_lai | (i) SigmaNet | (i) meanP | (i) win% | (ii) SigmaNet | (ii) meanP | (ii) win% |")
    say("|---|---|---|---|---|---|---|---|---|---|")
    p_sweep = {}
    for scn in ("B", "C"):
        for base in SLIP_BASES:
            slip = slip_of(scn, df, base)
            net = net_of(scn, df, slip)
            notl = df["notional"].values
            for p in P_GRID:
                # (i) i.i.d.
                tot_i = np.empty(R_REP)
                for r in range(R_REP):
                    mask = rng.random(len(net)) < p
                    if mask.sum() == 0:
                        tot_i[r] = np.nan
                        continue
                    tot_i[r] = (notl[mask] * net[mask] / 100.0).sum()
                meanp_i = np.array([np.nan])
                # meanP/win on a representative iid draw (average over reps)
                mp_i, win_i = [], []
                for r in range(min(60, R_REP)):
                    mask = rng.random(len(net)) < p
                    if mask.sum() == 0:
                        continue
                    mp_i.append(net[mask].mean())
                    win_i.append(np.mean(net[mask] > 0) * 100)
                # (ii) worst-first
                order = np.argsort(net, kind="stable")
                k = int(round(p * len(net)))
                sel = order[:k]
                tot_ii = (notl[sel] * net[sel] / 100.0).sum()
                mp_ii = net[sel].mean()
                win_ii = (net[sel] > 0).mean() * 100
                key = "%s/%s" % (scn, base[0])
                p_sweep.setdefault(key, {})[p] = dict(
                    n_iid=float(np.nanmean([np.sum(rng.random(len(net)) < p) for _ in range(3)])),
                    sum_i=float(np.nanmean(tot_i)), meanp_i=float(np.mean(mp_i)), win_i=float(np.mean(win_i)),
                    sum_ii=float(tot_ii), meanp_ii=float(mp_ii), win_ii=float(win_ii), n_ii=k)
                say("| %s | %s | %.1f | ~%d / %d | %+.1f | %+.4f | %.1f | %+.1f | %+.4f | %.1f |"
                    % (scn, base[0], p, p_sweep[key][p]["n_iid"], k,
                       p_sweep[key][p]["sum_i"], p_sweep[key][p]["meanp_i"], p_sweep[key][p]["win_i"],
                       tot_ii, mp_ii, win_ii))
    say("")

    # ---------------- CI block-72h cho vai o chinh (mo ta) ----------------
    say("### CI95 block-72h (mo ta, 2000 rep) cho meanP/notional — p = 1,0")
    say("| Kich ban | meanP | CI95 |")
    say("|---|---|---|")
    for key in ("S/proxy", "A/proxy", "A/universe", "A/1bp", "B/proxy", "B/universe", "B/1bp", "C/proxy"):
        net = scen_net[key]
        lo, hi = boot_ci(net, days, rng, 2000)
        say("| %s | %+.4f | [%+.4f, %+.4f] |" % (key, net.mean(), lo, hi))
    say("")

    # ---------------- hoa von p ----------------
    say("### HOA VON p (theo TONG; per-order la tam thuong vi B/C re hon A moi lenh)")
    say("| moc slip | Sigma net A | Sigma net B | Sigma net C | p*_B (iid) | p*_C (iid) | p*_B (stress) | p*_C (stress) |")
    say("|---|---|---|---|---|---|---|---|")
    be = {}
    for base in SLIP_BASES:
        nA = scen_net["A/%s" % base[0]]
        nB = scen_net["B/%s" % base[0]]
        nC = scen_net["C/proxy"]
        notl = df["notional"].values
        SA = (notl * nA / 100).sum(); SB = (notl * nB / 100).sum(); SC = (notl * nC / 100).sum()
        ps = {}
        for tag, net, S in (("B", nB, SB), ("C", nC, SC)):
            p_iid = SA / S if S > 0 else float("nan")
            # stress: tim p nho nhat sao cho tong net (xau-nhat-truoc) >= SA
            kk = np.arange(1, len(net) + 1)
            cum = np.cumsum((notl * net / 100)[np.argsort(net, kind="stable")])
            idx = np.searchsorted(cum, SA)
            p_str = (idx + 1) / len(net) if idx < len(cum) else 1.0
            ps[tag] = (p_iid, p_str)
        be[base[0]] = {k: {"iid": v[0], "stress": v[1]} for k, v in ps.items()}
        say("| %s | %+.1f | %+.1f | %+.1f | **%.2f** | **%.2f** | %.2f | %.2f |"
            % (base[0], SA, SB, SC, ps["B"][0], ps["C"][0], ps["B"][1], ps["C"][1]))
    say("")

    # ---------------- doc ket qua ----------------
    say("### DOC")
    for base in SLIP_BASES:
        nS = scen_net["S/proxy"]; nA = scen_net["A/%s" % base[0]]
        nB = scen_net["B/%s" % base[0]]; nC = scen_net["C/proxy"]
        say("- slip=%s: net/lenh A %+.4f%% | B %+.4f%% | C %+.4f%% (sim %+.4f%%) | win%% A %.1f / B %.1f / C %.1f (sim %.1f)"
            % (base[0], nA.mean(), nB.mean(), nC.mean(), nS.mean(),
               (nA > 0).mean() * 100, (nB > 0).mean() * 100, (nC > 0).mean() * 100, (nS > 0).mean() * 100))

    json.dump({"universe": univ, "rows1": rows1, "p_sweep": p_sweep, "breakeven": be},
              open(os.path.join(OUT, "summary.json"), "w"), indent=1, default=float)
    open(os.path.join(OUT, "report_exec.txt"), "w").write("\n".join(REPORT) + "\n")
    say("\n[saved] %s/report_exec.txt + summary.json" % OUT)


if __name__ == "__main__":
    main()
