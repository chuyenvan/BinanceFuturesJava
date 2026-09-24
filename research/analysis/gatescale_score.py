"""GATE-SCALE SWEEP scorer — cham diem 6 diem cua docs/PREREG_GATESCALE_SWEEP.md.

  [0] cong parity md5 (1.70 = efb793e2, 1.00 = dc16e4da)
  [1] co che + 5 rate (n, meanP/leg, win%, TSloss%) + maxDD/UW nam & toan ky
  [2] CI block-72h 2000 rep seed 20260905 x1.21 cua hieu 5 rate vs T170 (1.70)
  [3] rao cung (S1) maxDD<=30% va (S2) maxDD<=40% (UW<=200, quy>=-15%, ko nam am, conc<=15%)
      — kiem CA theo nam LAN toan ky
  [4] do venh theo nam: SD + range cua ret% nam
  [5] relSE = SE/mean (bootstrap block-72h 2000 rep cua meanP/leg) => kiem scaling 1/sqrt(n)
  [6] BANG PnL CHI TIET THEO NAM cho MOI diem
  [7] KET LUAN (a)(b)(c)

Usage: python3 gatescale_score.py [--k 5] [--json OUT.json]
"""
import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gd92xexit_score as G
import c3_rates as C

KOUT = "/home/ubuntu/kaggle_sim/out"
SEED = 20260905
NREP = 2000

# (tag = TEN THU MUC trong kaggle_sim/out, scale, md5 bat buoc hoac None)
#   tag la ten thu muc -> gd92xexit_score.base()/trades() resolve dung ngay.
ARMS = [
    ("t170-x1-2021", 1.70, "efb793e2468ca3a7318da0f0ad23d4fc"),   # moc/T170
    ("gs-t155", 1.55, None),
    ("gs-t140", 1.40, None),
    ("gs-t125", 1.25, None),
    ("gs-t110", 1.10, None),
    ("hn-t100", 1.00, "dc16e4da6ff6cb7b8d41c592bc3d9c45"),          # T100 base
]
T170 = "t170-x1-2021"
SCALES = [a[1] for a in ARMS]


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def rel_se(tag, nrep=NREP, seed=SEED):
    """Block-72h bootstrap cua meanP/leg => (mean, SE, relSE = SE/mean)."""
    d = G.trades(tag)
    blocks = np.sort(d.blk.unique())
    idx_of = {b: i for i, b in enumerate(blocks)}
    psum = np.zeros(len(blocks))
    pcnt = np.zeros(len(blocks))
    for b, v in d.groupby("blk"):
        i = idx_of[b]
        psum[i] = v.profit.sum()
        pcnt[i] = len(v)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(blocks), size=(nrep, len(blocks)))
    means = psum[idx].sum(axis=1) / pcnt[idx].sum(axis=1)
    m = d.profit.mean()
    se = float(np.std(means, ddof=1))
    return dict(mean=float(m), se=se, relse=float(se / abs(m)) if m else float("nan"),
                n_blk=int(len(blocks)))


def gates(S, Y, dd_max, uw_max=G.UW_MAX, q_min=G.Q_MIN, conc_max=G.CONC_MAX):
    """Qua het rao cung? Tra ve (ok_whole, ly_do, ok_theo_nam:dict)."""
    bad = []
    if S["maxDD"] < -dd_max:
        bad.append("maxDD toan ky %.2f" % S["maxDD"])
    if S["uw"] > uw_max:
        bad.append("UW toan ky %d" % S["uw"])
    if S["qmin"] < q_min:
        bad.append("qmin toan ky %.2f" % S["qmin"])
    if S["conc"] > conc_max:
        bad.append("conc %.2f" % S["conc"])
    yb = {}
    for y, r in sorted(Y.items()):
        b = []
        if r["maxDD"] < -dd_max:
            b.append("maxDD %.2f" % r["maxDD"])
        if r["uw"] > uw_max:
            b.append("UW %d" % r["uw"])
        if r["qmin"] < q_min:
            b.append("qmin %.2f" % r["qmin"])
        if r["ret"] < 0:
            b.append("nam am %.2f" % r["ret"])
        yb[y] = b
        if b:
            bad.append("%d(%s)" % (y, ",".join(b)))
    return (len(bad) == 0), bad, yb


def main():
    k, jout = 5, None
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--k":
            k = int(sys.argv[i + 1]); i += 2; continue
        if sys.argv[i] == "--json":
            jout = sys.argv[i + 1]; i += 2; continue
        i += 1
    W = C.inflate(k)

    print("=== GATE-SCALE SWEEP — %d diem | block-%dh %d rep seed %d anchor %s | CI quyet dinh x%.2f (phu inflate(%d)=%.4f) ===" % (
        len(ARMS), G.BLOCK_H, NREP, SEED, G.ANCHOR.date(), G.LEGACY, k, W))
    print("    rao cung: S1 maxDD<=30%% UW<=200 quy>=-15%% | S2 maxDD<=40%% (con lai nhu S1) | "
          "S3(HIEN HANH §7 sau 0c2a8a5) maxDD<=40%% UW<=250 quy>=-20%% | ko nam am | conc<=%.0f%%" % G.CONC_MAX)

    # ---- [0] parity ----
    print("\n[0] CONG PARITY (md5 printDone.csv)")
    par_ok = True
    res = {"parity": {}}
    for tag, sc, must in ARMS:
        if not must:
            continue
        p = os.path.join(KOUT, tag, "storage", "printDone.csv")
        got = md5(p)
        ok = (got == must)
        par_ok &= ok
        res["parity"][tag] = dict(md5=got, want=must, ok=bool(ok))
        print("    %-8s scale %.2f  md5=%s  want=%s  => %s" % (
            tag, sc, got, must, "PASS" if ok else "FAIL"))
    if not par_ok:
        print("\n*** CONG PARITY FAIL => DUNG, khong doc tiep. ***")
        return 3
    print("    => PARITY PASS ca 2 moc. Duoc phep doc ket qua.")

    # ---- load ----
    D = {t: G.trades(t) for t, _, _ in ARMS}
    S = {t: G.summary(t) for t, _, _ in ARMS}
    Y = {t: G.yearly_detail(t) for t, _, _ in ARMS}
    tags = [t for t, _, _ in ARMS]
    sc_of = {t: sc for t, sc, _ in ARMS}

    # ---- [1] co che + 5 rate ----
    print("\n[1] CO CHE + 5 RATE (toan bo leg) — chieu n phai DON DIEU theo scale")
    print("%-8s %6s %7s %8s %9s %8s %9s %9s %7s %7s" % (
        "tag", "scale", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "hold_h", "turn"))
    for t in tags:
        d = D[t]
        sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"]
        sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"]
        s = S[t]
        print("%-8s %6.2f %7d %8.2f %9.2f %8.3f %9.3f %9.3f %7.1f %7.3f" % (
            t, sc_of[t], len(d), 100.0 * (d.profit > 0).mean(),
            100.0 * (d.status == "STOP_LOSS_DONE").mean(),
            sm.mean() if len(sm) else float("nan"),
            sl.mean() if len(sl) else float("nan"), d.profit.mean(),
            s["hold_med"], s["turn"]))
    n_by_scale = [(sc_of[t], len(D[t])) for t in tags]
    n_sorted = [n for _, n in sorted(n_by_scale)]
    mono = all(n_sorted[i] < n_sorted[i + 1] for i in range(len(n_sorted) - 1))
    print("    co che: n theo scale %s => %s" % (
        ["%.2f:%d" % (s, n) for s, n in sorted(n_by_scale)],
        "DON DIEU (dung chieu)" if mono else "*** KHONG DON DIEU — co che bat thuong, ghi ro ***"))

    # ---- [2] CI vs T170 ----
    print("\n[2] CI block-72h x%.2f cua hieu 5 rate SO T170 (1.70) — 'NGOAI CI' = ngoai o x%.2f" % (
        G.LEGACY, G.LEGACY))
    ci_res = {}
    for t in tags:
        if t == T170:
            continue
        c1 = G.ci_pair(t, T170, G.LEGACY)
        c2 = G.ci_pair(t, T170, W)
        ng = nb = 0
        print("  -- %s (scale %.2f, n=%d) - T170 --" % (t, sc_of[t], len(D[t])))
        print("  %-9s %11s %26s %30s %5s" % ("rate", "hieu", "CI @1.21", "CI @%.4f (phu)" % W, "huong"))
        det = {}
        for name, dirc in G.RATES:
            obs = c1[name][0]
            lo1, hi1, o1 = c1[name][1], c1[name][2], c1[name][3]
            lo2, hi2, o2 = c2[name][1], c2[name][2], c2[name][3]
            out = o1 and o2
            good = out and ((dirc > 0 and obs > 0) or (dirc < 0 and obs < 0))
            bad = out and not good
            ng += int(good); nb += int(bad)
            det[name] = dict(obs=obs, lo21=lo1, hi21=hi1, out21=bool(o1), out_both=bool(out),
                             good=bool(good), bad=bool(bad))
            print("  %-9s %+11.3f [%9.3f,%9.3f] %5s [%9.3f,%9.3f] %5s %s" % (
                name, obs, lo1, hi1, "Y" if o1 else "-", lo2, hi2, "Y" if o2 else "-",
                "TOT" if good else ("XAU" if bad else "-")))
        print("  >>> %s vs T170: TOT ngoai CI @x1.21 = %d/5 | XAU = %d/5" % (t, ng, nb))
        ci_res[t] = dict(detail=det, good=ng, bad=nb, e_pass=bool(ng >= 2 and nb == 0))

    # ---- [3] rao cung ----
    print("\n[3] RAO CUNG S1 (maxDD<=30%) / S2 (maxDD<=40%) / S3 (HIEN HANH: 40%/UW250/quy-20%) — theo nam VA toan ky")
    print("%-8s %6s %10s %7s %8s %6s %8s %8s %7s %6s" % (
        "tag", "scale", "equity", "CAGR%", "maxDD%", "UW", "qmin%", "conc%", "n", "SumPnL"))
    for t in tags:
        s = S[t]
        print("%-8s %6.2f %10.0f %7.2f %8.2f %6d %8.2f %8.2f %7d %6.0f" % (
            t, sc_of[t], s["end"], s["cagr"], s["maxDD"], s["uw"], s["qmin"], s["conc"],
            s["n"], s["sumpnl"]))
    gres = {}
    for t in tags:
        row = {}
        for lab, kw in (("S1", dict(dd_max=30.0)),
                        ("S2", dict(dd_max=40.0)),
                        ("S3", dict(dd_max=40.0, uw_max=250, q_min=-20.0))):
            okw, bad, yb = gates(S[t], Y[t], **kw)
            row[lab] = dict(ok=bool(okw), bad=bad, year=yb)
        gres[t] = row
    print("\n  maxDD/UW/qmin THEO NAM:")
    yrs = sorted({y for t in tags for y in Y[t]})
    print("  %-8s %s" % ("tag", " ".join("%-30d" % y for y in yrs)))
    for t in tags:
        cells = []
        for y in yrs:
            r = Y[t].get(y)
            cells.append("%-30s" % ("-" if not r else "%.2f/%d/%+.2f/%.2f" % (
                r["maxDD"], r["uw"], r["ret"], r["qmin"])))
        print("  %-8s %s" % (t, " ".join(cells)))
    print("  (moi o = maxDD% / UW / ret% / qmin%)")
    for lab, nm in (("S1", "S1 maxDD<=30% UW<=200 quy>=-15%"),
                    ("S2", "S2 maxDD<=40% UW<=200 quy>=-15%"),
                    ("S3", "S3 HIEN HANH maxDD<=40% UW<=250 quy>=-20%")):
        print("\n  RAO CUNG (%s):" % nm)
        for t in tags:
            r = gres[t][lab]
            print("  %-8s scale %.2f n=%5d  %s" % (
                t, sc_of[t], len(D[t]), "PASS" if r["ok"] else "FAIL (" + ", ".join(r["bad"]) + ")"))

    # ---- [4] do venh nam ----
    print("\n[4] DO VENH THEO NAM (ret% nam): SD va range(max-min)")
    print("%-8s %6s %10s %10s %10s %10s" % ("tag", "scale", "SD_pp", "range_pp", "min_pp", "max_pp"))
    disp = {}
    for t in tags:
        rr = np.array([Y[t][y]["ret"] for y in sorted(Y[t])])
        sd = float(np.std(rr, ddof=1))
        disp[t] = dict(sd=sd, rng=float(rr.max() - rr.min()), mn=float(rr.min()), mx=float(rr.max()))
        print("%-8s %6.2f %10.2f %10.2f %10.2f %10.2f" % (
            t, sc_of[t], sd, disp[t]["rng"], disp[t]["mn"], disp[t]["mx"]))

    # ---- [5] relSE ----
    print("\n[5] relSE = SE/mean (bootstrap block-72h, %d rep) cua meanP/leg => kiem 1/sqrt(n)" % NREP)
    print("%-8s %6s %8s %10s %12s %12s %14s" % (
        "tag", "scale", "n", "meanP", "SE", "relSE", "relSE*sqrt(n)"))
    rse = {}
    base_rel, base_n = None, None
    for t in tags:
        r = rel_se(t)
        rse[t] = r
        if t == T170:
            base_rel, base_n = r["relse"], len(D[t])
        print("%-8s %6.2f %8d %10.3f %12.3f %12.4f %14.4f" % (
            t, sc_of[t], len(D[t]), r["mean"], r["se"], r["relse"], r["relse"] * len(D[t]) ** 0.5))
    print("    (neu relSE*sqrt(n) ~ HANG SO => dung luat 1/sqrt(n); giam => n moi it gia tri hon)")
    print("    du doan tu moc T170: relSE_du_doan(t) = relSE_T170 * sqrt(n_T170 / n_t)")
    print("  %-8s %6s %10s %12s %10s" % ("tag", "scale", "n", "relSE_do", "relSE/do"))
    for t in tags:
        pred = base_rel * (base_n / len(D[t])) ** 0.5
        print("  %-8s %6.2f %10d %12.4f %10.3f" % (
            t, sc_of[t], len(D[t]), pred, rse[t]["relse"] / pred))

    # ---- [6] bang PnL chi tiet theo nam ----
    print("\n[6] *** BANG PnL CHI TIET THEO NAM (moi diem) ***")
    for t in tags:
        s = S[t]
        print("\n  == %s (scale %.2f) == equity cuoi %.0f | toan ky: maxDD %.2f%% UW %d qmin %.2f conc %.2f SumPnL %.0f" % (
            t, sc_of[t], s["end"], s["maxDD"], s["uw"], s["qmin"], s["conc"], s["sumpnl"]))
        print("  %-5s %6s %8s %8s %9s %12s %9s %9s %5s %8s %11s" % (
            "nam", "n", "win%", "TSloss%", "meanP", "PnL(USDT)", "ret%", "maxDD%", "UW", "qmin%", "equity"))
        for y in sorted(Y[t]):
            r = Y[t][y]
            print("  %-5d %6d %8.2f %8.2f %9.3f %12.0f %+9.2f %9.2f %5d %8.2f %11.0f" % (
                y, r["n"], r["win"], r["tsloss"], r["meanP"], r["pnl_usdt"], r["ret"],
                r["maxDD"], r["uw"], r["qmin"], r["eq_end"]))

    # ---- [7] ket luan ----
    print("\n[7] KET LUAN (theo luat §7 pre-reg)")
    print("  %-8s %6s %7s %10s %10s %10s %12s %12s %12s %10s %10s" % (
        "tag", "scale", "n", "R-PASS S1", "R-PASS S2", "R-PASS S3", "E-PASS", "PASS day du", "PASS S3 full", "maxDD_ky", "UW_ky"))
    for t in tags:
        r1 = gres[t]["S1"]["ok"]
        r2 = gres[t]["S2"]["ok"]
        r3 = gres[t]["S3"]["ok"]
        ep = ci_res[t]["e_pass"] if t in ci_res else False
        print("  %-8s %6.2f %7d %10s %10s %10s %12s %12s %12s %10.2f %10d" % (
            t, sc_of[t], len(D[t]), "PASS" if r1 else "FAIL", "PASS" if r2 else "FAIL",
            "PASS" if r3 else "FAIL", "PASS" if ep else "FAIL",
            "PASS" if (r1 and ep) else "FAIL", "PASS" if (r3 and ep) else "FAIL",
            S[t]["maxDD"], S[t]["uw"]))

    res.update(dict(arms=[dict(tag=t, scale=sc_of[t], n=len(D[t]), equity=S[t]["end"],
                               cagr=S[t]["cagr"], maxDD=S[t]["maxDD"], uw=S[t]["uw"],
                               qmin=S[t]["qmin"], conc=S[t]["conc"], sumpnl=S[t]["sumpnl"])
                          for t in tags],
                    summary=S, yearly=Y, ci=ci_res, gates=gres, disp=disp, relse=rse,
                    monotone_n=bool(mono)))
    if jout:
        with open(jout, "w") as f:
            json.dump(res, f, indent=1, default=str)
        print("\n[json] %s" % jout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
