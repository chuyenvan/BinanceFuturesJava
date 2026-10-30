#!/usr/bin/env python3
"""GATE_STAB M (PREREG_GATE_STAB.md §2) -- CHI DO, offline, khong PnL sim.
stage val  : tai lap gate G2 offline tren printDone nt-x14-s* (held) -> so pass/recall vs sim (cong V-tool).
stage meas : dem burst hour / dot sap kep / o bi chan do q tang sau burst (q_cf loai record gio burst 24h truoc).
"""
import sys, json, math, logging
import numpy as np, pandas as pd
sys.path.insert(0, '/home/ubuntu/claude_master/vz_e1_wt/research/analysis')
import gate_offline as GO
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("gst")
H, D = GO.H, GO.D
SEEDTAG = {"A1": "nt-x14-s42", "S7": "nt-x14-s7", "S13": "nt-x14-s13", "S21": "nt-x14-s21", "S99": "nt-x14-s99",
           "S123": "nt-x14-s123", "S777": "nt-x14-s777", "S2024": "nt-x14-s2024"}
BURST_N = 10          # §2.1: gio co >= 10 o PASS
CF_H = 24             # §2.2: loai record gio burst trong 24h truoc
EP_GAP = 3            # §2.3: gop gio burst cach <= 3h thanh 1 dot
OUT = '/home/ubuntu/claude_master/gst1030/'


def setup(arm):
    B = dict(np.load(GO.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(GO.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    C = GO.build(arm, B, s2id, SEEDTAG[arm])
    G = GO.run_g2(C, J=1024)
    return C, G, s2id


def val(arm):
    C, G, _ = setup(arm)
    x = GO.classify(C, G["P"])
    sl = GO.simlog(SEEDTAG[arm])
    dev = (x.yr >= 2022) & (x.yr <= 2025)
    cat = x[dev].cat.value_counts().to_dict()
    rec = cat.get("pass", 0) / max(1, sum(cat.values()))
    qsim = {k: v for k, v in sl["q"].items() if 20221 <= k <= 20254}
    yq = C["yq"]; P = G["P"]
    off = {int(k): int(P[yq == k].sum()) for k in qsim}
    so, ss = sum(off.values()), sum(p for p, s in qsim.values())
    o = dict(arm=arm, recall_entry_dev=round(rec, 4), cat_dev=cat, pass_off_dev=so, pass_sim_dev=ss,
             dev_pct=round(100.0 * (so - ss) / max(1, ss), 3))
    log.info("VAL %s", o)
    return o


if __name__ == "__main__":
    st = sys.argv[1]
    arms = sys.argv[2].split(",") if len(sys.argv) > 2 else list(SEEDTAG)
    if st == "val":
        R = [val(a) for a in arms]
        json.dump(R, open(OUT + "val_%s.json" % "_".join(arms), "w"), indent=1)


PCTD = float(np.float32(0.999950829))
DEV0, DEV1 = 1640970000000, 1767200400000   # 2022-01-01 / 2026-01-01 00:00 +07


def meas(arm):
    C, G, _ = setup(arm)
    ts, P, r, valid, qm = C["ts"], G["P"], G["r"], C["valid"], G["qm"]
    hm = ts // H
    h0 = int(hm.min()); nH = int(hm.max()) - h0 + 1
    hp = np.bincount(hm - h0, weights=P.sum(1), minlength=nH).astype(int)
    # buffer theo gio: top-256 r hop le + dem
    rows, cols = np.nonzero(valid)
    vh = hm[rows] - h0; vv = r[rows, cols].astype(np.float32)
    o = np.argsort(vh, kind="stable"); vh, vv = vh[o], vv[o]
    cnt = np.bincount(vh, minlength=nH); st = np.concatenate([[0], np.cumsum(cnt)])
    J = 256; TOP = np.full((nH, J), -np.inf, np.float32)
    for h in np.nonzero(cnt)[0].tolist():
        x = vv[st[h]:st[h + 1]]
        if len(x) > J: x = np.partition(x, len(x) - J)[len(x) - J:]
        TOP[h, :len(x)] = x
    del rows, cols, vh, vv
    BH = np.nonzero(hp >= BURST_N)[0]
    isB = np.zeros(nH, bool); isB[BH] = True
    W = 90 * 24
    def qwin(h, excl):
        lo = max(0, h - W)
        keep = np.ones(h - lo, bool)
        if excl: keep &= ~isB[lo:h] | (np.arange(lo, h) < h - CF_H)
        m = int(cnt[lo:h][keep].sum())
        k = min(m - 1, max(0, int(math.floor(PCTD * (m - 1))))); jj = m - 1 - k
        x = TOP[lo:h][keep].ravel()
        return float(x[np.argpartition(-x, jj)[jj]]), jj
    tgt = sorted(set(int(b + d) for b in BH.tolist() for d in range(1, CF_H + 1) if b + d < nH))
    qh_act = {}; 
    first_idx = np.searchsorted(hm - h0, np.arange(nH))
    chk = []
    QCF = {}
    for h in tgt:
        q_cf, jj = qwin(h, True)
        QCF[h] = q_cf
        if len(chk) < 200 and first_idx[h] < len(ts) and hm[first_idx[h]] - h0 == h:
            chk.append(abs(qwin(h, False)[0] - float(qm[first_idx[h]])))
    # o bi chan
    qcf_min = np.array([QCF.get(int(h - h0), np.inf) for h in hm], np.float32)
    blk = valid & (r >= qcf_min[:, None]) & ~P & (r < qm[:, None])
    # dot
    eps = []
    for b in BH.tolist():
        if eps and b - eps[-1][1] <= EP_GAP: eps[-1][1] = b
        else: eps.append([b, b])
    syms = C["SY"]
    rows, cols = np.nonzero(blk)
    bh_ = hm[rows] - h0
    out_eps = []
    for (a, L) in eps:
        sel = (bh_ >= L + 1) & (bh_ <= L + CF_H)
        ins = (bh_ > a) & (bh_ <= L)
        nb = int(sel.sum())
        newe = len(set(syms[rows[sel], cols[sel]].tolist()))
        nxt = bool(((BH > L) & (BH <= L + CF_H)).any())
        ia = first_idx[a]; il = first_idx[min(L + 1, nH - 1)]
        qr = float(qm[min(il, len(ts) - 1)] / qm[min(ia, len(ts) - 1)])
        tsa = int((a + h0) * H)
        out_eps.append(dict(t=tsa, yr=int(pd.Timestamp(tsa + 7 * H, unit="ms").year), nBH=int(((BH >= a) & (BH <= L)).sum()),
                            pass_=int(hp[a:L + 1].sum()), blk_cells_after=nb, blk_new_after=newe,
                            blk_cells_inside=int(ins.sum()), next_burst24=nxt, q_ratio=round(qr, 4)))
    E = pd.DataFrame(out_eps); E = E[(E.t >= DEV0) & (E.t < DEV1)]
    # 2.5 mo ta printDone
    d = C["d"]; x = d[(d.level == "PREDICT_SYMBOL_TRADE") & (d.s_ms >= DEV0) & (d.s_ms < DEV1)].copy()
    xh = (x.s_ms.to_numpy(np.int64) // H) - h0
    post = np.zeros(len(x), bool); inb = np.zeros(len(x), bool)
    for i, hh in enumerate(xh.tolist()):
        if 0 <= hh < nH:
            inb[i] = isB[hh]
            post[i] = (not isB[hh]) and isB[max(0, hh - CF_H):hh].any()
    def agg(m):
        v = x.pnl.to_numpy(float)[m]
        return dict(n=int(m.sum()), pnl_mean=round(float(np.nanmean(v)), 2) if m.any() else None,
                    pnl_med=round(float(np.nanmedian(v)), 2) if m.any() else None)
    res = dict(arm=arm, tag=SEEDTAG[arm], q_check_maxabs=float(max(chk) if chk else -1), n_check=len(chk),
               n_BH_dev=int(((BH + h0) * H >= DEV0).sum() - ((BH + h0) * H >= DEV1).sum()),
               n_ep=int(len(E)), n_ep_kep_blocked=int((E.blk_cells_after > 0).sum()),
               n_ep_kep_entered=int(E.next_burst24.sum()), blk_cells_after=int(E.blk_cells_after.sum()),
               blk_new_after=int(E.blk_new_after.sum()), blk_cells_inside=int(E.blk_cells_inside.sum()),
               q_ratio_med=round(float(E.q_ratio.median()), 4), q_ratio_p90=round(float(E.q_ratio.quantile(0.9)), 4),
               by_year=E.groupby("yr").agg(ep=("t", "size"), kep_blk=("blk_cells_after", lambda s: int((s > 0).sum())),
                                           new_blk=("blk_new_after", "sum")).to_dict("index"),
               pd_inBH=agg(inb), pd_post24=agg(post), pd_other=agg(~inb & ~post))
    E.to_csv(OUT + "eps_%s.csv" % arm, index=False)
    log.info("MEAS %s", json.dumps(res, default=int))
    return res


if __name__ == "__main__" and sys.argv[1] == "meas":
    arms = sys.argv[2].split(",") if len(sys.argv) > 2 else list(SEEDTAG)
    R = [meas(a) for a in arms]
    json.dump(R, open(OUT + "meas.json", "w"), indent=1, default=int)
