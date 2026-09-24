#!/usr/bin/env python3
"""LIMIT_ENTRY — test entry LIMIT 15 phut (fill-or-fail) tren ung vien C1 = REVERSAL-BOUNCE.

Pre-reg: docs/prereg/PREREG_LIMIT_ENTRY.md (commit TRUOC khi chay).
Thuan Python, chi DOC 1m tu /home/ubuntu/claudedata/rvb_1m/raw/*.f32 + Aerospike funding_data (cache).
Khong Java tren Oracle, khong claude-run, khong push, khong cham 2026 (du lieu < 2026-01-01).

Trigger C1 = nguyen ban PREREG_REVERSAL_BOUNCE (a68dc88): DROP_THRESH=0.01, moc 15m-aligned,
max15/max30, priceReverse=open[j-14], fire tai nen dau t>j co close[t]>priceReverse, HOLD 24h.

Entry LIMIT: L = p0 (delta=0) hoac p0*(1-delta), delta=0,15%. Cua so khop = 15 nen 1m ke tiep.
Khop => fee MAKER, gia khop = L. Khong cham => BO lenh (khong vao).
Exit = MARKET tai cung moc exit cua baseline => fee taker + slip day du.

Hang chi phi: A0 template-baseline, A1 market/market doi xung, B limit/market, C nhu B slip=0.

Out (ngoai repo): /home/ubuntu/claudedata/limit_entry/{events_d0.npz, events_d15.npz, report.txt, summary.json}
"""
import os
import glob
import json
import time
from datetime import datetime, timezone
from math import sqrt

import numpy as np
import pandas as pd

RAW = os.environ.get("LE_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
OUT = os.environ.get("LE_OUT", "/home/ubuntu/claudedata/limit_entry")
FUND_CACHE = os.environ.get("LE_FUND", "/home/ubuntu/claudedata/funding_sign/fund_cache.npz")
os.makedirs(OUT, exist_ok=True)

# ---- LOCKED params (PREREG) ----
DROP_THRESH = 0.01
W15, W30 = 15, 30
HOLD = 1440
FEE_TAKER_RT = 0.0010      # 0,10% ca hai chan (baseline/A1)
FEE_MAKER = 0.0002         # 0,02%/chan
FEE_TAKER = 0.0005         # 0,05%/chan
SLIP = 0.5                 # nua range 1m
DELTAS = (0.0, 0.0015)
FILL_WIN = 15
SEED = 20260905
NREP = 2000
BLOCK_H = 72
CI_INFLATE_LEGACY = 1.21
DEV_Y0, DEV_Y1 = 2022, 2026
UTC = timezone.utc
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

REP = []


def say(s=""):
    REP.append(str(s))
    print(s, flush=True)


def min_of(y, mo, d):
    return int(datetime(y, mo, d, tzinfo=UTC).timestamp() // 60)


DEV_START = min_of(DEV_Y0, 1, 1)
DEV_END = min_of(DEV_Y1, 1, 1)
SAMPLE_END = min_of(2026, 1, 1)


def load_sym(path):
    a = np.fromfile(path, dtype=DT)
    n = len(a)
    if n == 0:
        return None
    ts = a["ts"].astype(np.int64)
    o = np.argsort(ts, kind="stable")
    ts = ts[o]
    a = a[o]
    uq, idx = np.unique(ts, return_index=True)
    return (uq, a["o"][idx].astype(np.float64), a["h"][idx].astype(np.float64),
            a["l"][idx].astype(np.float64), a["c"][idx].astype(np.float64))


def rolling_max(vals, w):
    return pd.Series(vals).rolling(w, min_periods=w).max().values


def gen_fires(ts, O, H, L, C):
    """NGUYEN BAN reversal_bounce.py gen_fires (khong doi thiet ke)."""
    base = ts[0]
    span = int(ts[-1] - base + 1)
    O_ = np.full(span, np.nan); H_ = np.full(span, np.nan)
    L_ = np.full(span, np.nan); C_ = np.full(span, np.nan)
    pos = (ts - base).astype(np.int64)
    O_[pos] = O; H_[pos] = H; L_[pos] = L; C_[pos] = C
    present = ~np.isnan(C_)
    m15 = rolling_max(H_, W15)
    m30 = rolling_max(H_, W30)
    with np.errstate(invalid="ignore", divide="ignore"):
        drop = np.minimum(C_ / m15 - 1.0, C_ / m30 - 1.0)
    gmin = (np.arange(span) + base) % 15
    p14 = np.zeros(span, dtype=bool); p14[14:] = present[:-14]
    p29 = np.zeros(span, dtype=bool); p29[29:] = present[:-29]
    anchors = np.where((gmin == 14) & (drop <= -DROP_THRESH) & present & p14 & p29)[0]
    fires = []
    i = 0; last_fire = -1; na = len(anchors)
    while i < na:
        j = anchors[i]
        if j <= last_fire:
            i += 1; continue
        pr = O_[j - 14]
        lo = j + 1
        hi = anchors[i + 1] if i + 1 < na else span
        if hi <= lo:
            i += 1; continue
        cross = np.where(present[lo:hi] & (C_[lo:hi] > pr))[0]
        if len(cross):
            fp = lo + int(cross[0])
            fires.append(fp); last_fire = fp
            while i < na and anchors[i] <= last_fire:
                i += 1
        else:
            i += 1
    return base, span, H_, L_, C_, present, np.array(fires, dtype=np.int64)


# ------------------------------- stats harness (repo standard) -------------------------------
def block_boot(net, blk, nrep=NREP, seed=SEED, inflate=1.0):
    df = pd.DataFrame({"b": blk, "x": net})
    g = df.groupby("b")["x"]
    s = g.sum().values; c = g.count().values
    nblk = len(s)
    rng = np.random.default_rng(seed)
    means = np.empty(nrep)
    for r in range(nrep):
        idx = rng.integers(0, nblk, nblk)
        means[r] = s[idx].sum() / c[idx].sum()
    lo, hi = np.percentile(means, [2.5, 97.5])
    obs = net.mean()
    half = (hi - lo) / 2.0 * inflate
    return dict(obs=obs, lo=lo, hi=hi, sd=means.std(), p_gt0=float((means > 0).mean()),
                ci_lo=obs - half, ci_hi=obs + half, n_blk=nblk)


def block_perm(net, blk, nrep=NREP, seed=SEED):
    blk = np.asarray(blk); net = np.asarray(net)
    bcode, binv = np.unique(blk, return_inverse=True)
    rng = np.random.default_rng(seed)
    obs = net.mean()
    signs = rng.choice([-1.0, 1.0], size=(nrep, len(bcode)))
    bsum = np.bincount(binv, weights=net)
    null = (signs @ bsum) / len(net)
    return obs, float(null.mean()), float(null.std()), float((null >= obs).mean())


def summ(name, net, blk, extra=""):
    if len(net) < 30:
        return "%s: N=%d (qua it)" % (name, len(net))
    r = block_boot(net, blk, inflate=1.0)
    rl = block_boot(net, blk, inflate=CI_INFLATE_LEGACY)
    obs, nm, ns, pv = block_perm(net, blk)
    mde = 2.8 * ns
    return ("%s: N=%d meanNet=meanP=%+.4f%% med=%+.4f%% win=%.1f%% | "
            "CI72h=[%+.4f%%,%+.4f%%] p(>0)=%.3f | CI72h_x1.21=[%+.4f%%,%+.4f%%] | "
            "null: mean %+.4f%% sd %.4f p=%.4f | MDE80: %.4f%% (2,8xSD) %.4f%% (CI) | N_blk=%d%s"
            % (name, len(net), obs * 100, np.median(net) * 100, 100 * (net > 0).mean(),
               r["lo"] * 100, r["hi"] * 100, r["p_gt0"], rl["ci_lo"] * 100, rl["ci_hi"] * 100,
               nm * 100, ns * 100, pv, mde * 100, (r["hi"] - r["lo"]) / 2 * 100, r["n_blk"], extra))


def main():
    files = sorted(glob.glob(RAW + "/*.f32"))
    if os.environ.get("LE_NUM"):
        files = files[:int(os.environ["LE_NUM"])]
    stats_only = os.environ.get("LE_STATS_ONLY") == "1"
    say("=" * 100)
    say("LIMIT_ENTRY — C1 = REVERSAL-BOUNCE | pre-reg docs/prereg/PREREG_LIMIT_ENTRY.md")
    say("symbols=%d  DEV=[%s..%s)  HOLD=%d  FILL_WIN=%d  deltas=%s"
        % (len(files), DEV_START, DEV_END, HOLD, FILL_WIN, DELTAS))
    say("=" * 100)

    # funding cache
    z = np.load(FUND_CACHE, allow_pickle=True)
    fsyms = list(z["syms"]); fts = z["ts"]; frt = z["rt"].astype(np.float64); fsid = z["sid"]
    o = np.argsort(fsid, kind="stable")
    fsid_s, fts_s, frt_s = fsid[o], fts[o], frt[o]
    uq_sid, st = np.unique(fsid_s, return_index=True)
    st = np.append(st, len(fsid_s))
    fund = {}
    for i, s in enumerate(fsyms):
        j = np.searchsorted(uq_sid, i)
        if j < len(uq_sid) and uq_sid[j] == i:
            arr = fts_s[st[j]:st[j + 1]]
            fund[s] = (arr, np.concatenate([[0.0], np.cumsum(frt_s[st[j]:st[j + 1]])]))
    say("[fund] %d symbol trong cache" % len(fund))

    acc = {d: dict(ts=[], rawA1=[], netA0=[], netA1=[], slipx=[], fundsig=[], p0=[],
                   filled=[], foff=[], rawBC=[], fundfill=[], netB=[], netC=[], sid=[], nsym=None)
           for d in DELTAS}
    symnames = []
    t0 = time.time()
    nfire = 0
    if stats_only:
        for d in DELTAS:
            zz = np.load(os.path.join(OUT, "events_d%s.npz" % str(d).replace(".", "")), allow_pickle=True)
            symnames = list(zz["syms"])
            for k in acc[d]:
                if k == "nsym":
                    continue
                acc[d][k] = [zz[k]]
            nfire = len(zz["ts"])
        say("[stats-only] nap lai events npz (%d fire)" % nfire)
    for fi, path in enumerate(files if not stats_only else []):
        sym = os.path.basename(path)[:-4]
        r = load_sym(path)
        if r is None or len(r[0]) < W30 + 1:
            continue
        ts, O, H, L, C = r
        base, span, H_, L_, C_, present, fpos = gen_fires(ts, O, H, L, C)
        if len(fpos) == 0:
            continue
        # --- exit giong baseline: nen co mat cuoi cung trong (f, f+HOLD]; loai bien (f+HOLD > span-1)
        pi = np.where(present)[0]
        hiidx = np.searchsorted(pi, fpos + HOLD, side="right") - 1
        okE = hiidx >= 0
        fpos2 = fpos[okE]; hiidx = hiidx[okE]
        Epos = pi[hiidx]
        valid = (Epos > fpos2) & ((fpos2 + HOLD) <= span - 1)
        fpos2 = fpos2[valid]; Epos = Epos[valid]
        if len(fpos2) == 0:
            continue
        sid = len(symnames); symnames.append(sym)
        p0 = C_[fpos2]
        ce = C_[Epos]
        he = H_[Epos]; le = L_[Epos]
        with np.errstate(invalid="ignore", divide="ignore"):
            rawA1 = ce / p0 - 1.0
            slipx = np.where(ce > 0, SLIP * (he - le) / ce, 0.0)
            slipe = np.where(p0 > 0, SLIP * (H_[fpos2] - L_[fpos2]) / p0, 0.0)
        netA1 = rawA1 - FEE_TAKER_RT - slipe - slipx
        tms = (base + fpos2) * 60000
        ems = (base + Epos) * 60000
        fa = fund.get(sym)
        if fa is not None:
            ats, acum = fa
            j1 = np.searchsorted(ats, tms, side="right")
            j2 = np.searchsorted(ats, ems, side="right")
            fundsig = acum[j2] - acum[j1]
        else:
            fundsig = np.zeros(len(fpos2))
        netA0 = rawA1 - FEE_TAKER_RT - slipe - fundsig
        # --- rolling min low de test khop trong 15' (window [f+1, f+15] <=> rolling(15) tai idx f+15)
        rmin = pd.Series(L_).rolling(FILL_WIN, min_periods=1).min().values
        wmin = rmin[fpos2 + FILL_WIN]
        for d in DELTAS:
            Llim = p0 * (1.0 - d)
            filled = wmin <= Llim
            foff = np.full(len(fpos2), -1, dtype=np.int16)
            rem = filled.copy()
            for j in range(1, FILL_WIN + 1):
                idx = fpos2 + j
                touch = np.zeros(len(fpos2), dtype=bool)
                tv = L_[idx] <= Llim
                touch[rem] = tv[rem]
                newly = rem & touch
                foff[newly] = j
                rem = rem & ~newly
            with np.errstate(invalid="ignore", divide="ignore"):
                rawBC = ce / Llim - 1.0
            fms = (base + fpos2 + np.maximum(foff, 0)) * 60000
            if fa is not None:
                k1 = np.searchsorted(ats, fms, side="right")
                fundfill = acum[j2] - acum[k1]
            else:
                fundfill = np.zeros(len(fpos2))
            a = acc[d]
            a["ts"].append((base + fpos2).astype(np.int64))
            a["p0"].append(p0.astype(np.float32))
            a["rawA1"].append(rawA1.astype(np.float32))
            a["netA0"].append(netA0.astype(np.float32))
            a["netA1"].append(netA1.astype(np.float32))
            a["slipx"].append(slipx.astype(np.float32))
            a["fundsig"].append(fundsig.astype(np.float32))
            a["filled"].append(filled.astype(np.int8))
            a["foff"].append(foff)
            a["rawBC"].append(rawBC.astype(np.float32))
            a["fundfill"].append(fundfill.astype(np.float32))
            a["netB"].append((rawBC - FEE_MAKER - FEE_TAKER - slipx - fundfill).astype(np.float32))
            a["netC"].append((rawBC - FEE_MAKER - FEE_TAKER - fundfill).astype(np.float32))
            a["sid"].append(np.full(len(fpos2), sid, dtype=np.int16))
        nfire += len(fpos2)
        if fi % 40 == 0:
            say("  sym %d/%d %s fires=%d el=%.0fs" % (fi, len(files), sym, nfire, time.time() - t0))

    say("[scan] xong: %d fire dung duoc, %d symbol, el=%.0fs" % (nfire, len(symnames), time.time() - t0))

    SUM = {}
    for d in DELTAS:
        a = acc[d]
        E = {k: (np.concatenate(v) if len(v) else np.array([])) for k, v in a.items() if k != "nsym"}
        if not stats_only:
            p = os.path.join(OUT, "events_d%s.npz" % str(d).replace(".", ""))
            np.savez_compressed(p, syms=np.array(symnames, dtype=object), **E)
            say("[save] %s (%d fire)" % (p, len(E["ts"])))

    # ---------------- bao cao ----------------
    for d in DELTAS:
        a = acc[d]
        ts = np.concatenate(a["ts"]); rawA1 = np.concatenate(a["rawA1"])
        netA0 = np.concatenate(a["netA0"]); netA1 = np.concatenate(a["netA1"])
        slipx = np.concatenate(a["slipx"]); fundsig = np.concatenate(a["fundsig"])
        filled = np.concatenate(a["filled"]).astype(bool); foff = np.concatenate(a["foff"])
        rawBC = np.concatenate(a["rawBC"]); fundfill = np.concatenate(a["fundfill"])
        netB = np.concatenate(a["netB"]); netC = np.concatenate(a["netC"])
        blk = ts // (BLOCK_H * 60)
        dev = (ts >= DEV_START) & (ts < DEV_END)
        yr = pd.to_datetime(ts, unit="m", utc=True).year.values
        tag = "delta=%.4g" % d
        say()
        say("=" * 100)
        say("### %s" % tag)
        say("=" * 100)
        say("[gate] N fire dung duoc: ALL=%d | DEV=%d" % (len(ts), int(dev.sum())))
        if d == 0.0:
            dev_old = (ts >= min_of(2022, 1, 1)) & (ts < min_of(2024, 7, 1))
            say("[GATE-A0] meanNet A0 tai lap so DA DANG cua RESULT_REVERSAL_BOUNCE:")
            say("          ALL 2021-2025 = %+.4f%% (dang ky +0,003%%) | DEV cu 2022-01..2024-06 = %+.4f%% (dang ky -0,080%%)"
                % (netA0.mean() * 100, netA0[dev_old].mean() * 100))
        say("[fill] ti le khop ALL %.2f%% (n=%d) | DEV %.2f%% (n=%d)"
            % (100 * filled.mean(), int(filled.sum()), 100 * filled[dev].mean(), int(filled[dev].sum())))
        fo = foff[filled]
        say("[fill] offset phut: med %d p90 %d | %% khop ngay nen 1: %.1f%% | nen <=5: %.1f%%"
            % (np.median(fo), np.percentile(fo, 90), 100 * (fo == 1).mean(), 100 * (fo <= 5).mean()))
        # A0-A1-A1(filled)-B-C
        say()
        say("-- BANG: (i) market ca 2 dau | (ii) limit entry + market exit | (iii) nhu (ii) slip=0 --")
        say(summ("A0 BASELINE-REPRO (toan bo fire)", netA0, blk))
        say(summ("A0 BASELINE-REPRO (tap khop)", netA0[filled], blk[filled]))
        say(summ("A1 market/market (toan bo fire)", netA1, blk))
        say(summ("A1 market/market (tap khop)", netA1[filled], blk[filled]))
        say(summ("B  LIMIT/market (tap khop)", netB[filled], blk[filled]))
        say(summ("C  LIMIT/market slip=0 (tap khop)", netC[filled], blk[filled]))
        say()
        say("-- DEV (CHINH) --")
        for nm, v in (("A0 BASELINE-REPRO", netA0), ("A1 market/market (all)", netA1),
                      ("B  LIMIT/market", netB), ("C  LIMIT slip=0", netC)):
            if nm.startswith(("B", "C")):
                sel = dev & filled
            else:
                sel = dev
            say(summ("DEV " + nm, v[sel], blk[sel]))
        say(summ("ALL B  LIMIT/market", netB[filled], blk[filled]))
        say(summ("ALL C  LIMIT slip=0", netC[filled], blk[filled]))
        say()
        say("-- DEV (CHINH) day du 4 hang (A1 lap lai tren TAP KHOP de so cung mau) --")
        for nm, v, sel in (("DEV A0 BASELINE-REPRO (all)", netA0, dev),
                           ("DEV A1 market/market (all)", netA1, dev),
                           ("DEV A1 market/market (tap khop)", netA1, dev & filled),
                           ("DEV B  LIMIT/market", netB, dev & filled),
                           ("DEV C  LIMIT slip=0", netC, dev & filled)):
            say(summ(nm, v[sel], blk[sel]))
        say()
        say("-- PHAN RA B - A1 tren CUNG TAP KHOP (nguon cua moi 'cai thien') --")
        dBB = netB[filled].mean() - netA1[filled].mean()
        as2 = float((rawBC[filled] - rawA1[filled]).mean())
        dff = float((fundsig[filled] - fundfill[filled]).mean())
        feed = FEE_TAKER_RT - (FEE_MAKER + FEE_TAKER)     # tiet kiem phi THAT (fraction)
        slipe_imp = dBB - as2 - feed - dff
        say("   B - A1 = %+.4f pp = [AS2 (gia khop tot hon) %+.4f] + [phi tiet kiem %+.4f] + [slip entry bo duoc %+.4f] + [funding %+.4f]"
            % (dBB * 100, as2 * 100, feed * 100, slipe_imp * 100, dff * 100))
        say("   B - A0 = %+.4f pp | C - B (dong gop cua slip exit) = %+.4f pp"
            % ((netB[filled].mean() - netA0.mean()) * 100,
               (netC[filled].mean() - netB[filled].mean()) * 100))
        say()
        say("-- ADVERSE SELECTION (do tu gia khop; raw_signal = C[E]/p0-1) --")
        rsf = rawA1[filled]; rsn = rawA1[~filled]
        say("   nhom KHOP   n=%d | mean raw_signal %+.4f%% | med %+.4f%% | win %5.1f%%"
            % (len(rsf), rsf.mean() * 100, np.median(rsf) * 100, 100 * (rsf > 0).mean()))
        say("   nhom FAIL   n=%d | mean raw_signal %+.4f%% | med %+.4f%% | win %5.1f%%"
            % (len(rsn), rsn.mean() * 100, np.median(rsn) * 100, 100 * (rsn > 0).mean()))
        say("   AS1 = E[raw_signal|khop] - E[raw_signal|fail] = %+.4f pp  (>0 = khop TOT hon; <0 = ADVERSE)"
            % ((rsf.mean() - rsn.mean()) * 100))
        say("   AS2 = E[raw_fill|khop] - E[raw_signal|khop] = %+.4f pp (thanh phan co hoc cua delta)"
            % ((rawBC[filled].mean() - rsf.mean()) * 100))
        say("   (raw_fill = C[E]/L-1; netB/netC deu tinh tu L, KHONG tu p0)")
        say()
        say("-- theo NAM (B limit/market, tap khop) --")
        for y in sorted(set(yr)):
            sel = (yr == y) & filled
            if sel.sum() >= 20:
                say("   %d: n=%5d | filled %5.1f%% | meanNetB %+.4f%% | win %5.1f%%"
                    % (y, int((yr == y).sum()), 100 * filled[yr == y].mean(),
                       netB[sel].mean() * 100, 100 * (netB[sel] > 0).mean()))
        SUM[tag] = dict(n_all=int(len(ts)), n_dev=int(dev.sum()),
                        fill_all=float(100 * filled.mean()), fill_dev=float(100 * filled[dev].mean()),
                        A0_all=float(netA0.mean() * 100), A1_all=float(netA1.mean() * 100),
                        A1_fill=float(netA1[filled].mean() * 100), B_fill=float(netB[filled].mean() * 100),
                        C_fill=float(netC[filled].mean() * 100),
                        AS1=float((rsf.mean() - rsn.mean()) * 100), AS2=float((rawBC[filled].mean() - rsf.mean()) * 100),
                        A0_dev=float(netA0[dev].mean() * 100), A1_dev_all=float(netA1[dev].mean() * 100),
                        A1_dev_fill=float(netA1[dev & filled].mean() * 100),
                        B_dev_all=float(netB[dev].mean() * 100), B_mean_all=float(netB.mean() * 100),
                        C_mean_all=float(netC.mean() * 100), A1_mean_all=float(netA1.mean() * 100),
                        rawBC_mean=float(rawBC[filled].mean() * 100))
        rep_b = block_boot(netB[dev & filled], blk[dev & filled], inflate=CI_INFLATE_LEGACY)
        SUM[tag]["B_dev"] = float(netB[dev & filled].mean() * 100)
        SUM[tag]["B_dev_ci_lo"] = float(rep_b["ci_lo"] * 100)
        SUM[tag]["B_dev_ci_hi"] = float(rep_b["ci_hi"] * 100)
        SUM[tag]["B_dev_pgt0"] = float(rep_b["p_gt0"])

    with open(os.path.join(OUT, "report.txt"), "w") as f:
        f.write("\n".join(REP) + "\n")
    json.dump(SUM, open(os.path.join(OUT, "summary.json"), "w"), indent=2, ensure_ascii=False, default=float)
    say()
    say("[xong] trung gian: %s" % OUT)


if __name__ == "__main__":
    main()
