#!/usr/bin/env python3
"""GRID_RESEARCH — do kha thi grid trading tren kline 1m that (0-sim, thuan Python).

Pre-reg: docs/prereg/PREREG_GRID_RESEARCH.md (commit 3d97009d) — chot TRUOC khi chay.
Du lieu: /tmp/grid_research/<SYM>-<YYYY-MM>.npy (Binance public, 1m, DEV<=2025-12-31).
Khong cham production/242/ONNX/.java. Khong push du lieu.

Xuat: docs/result/GRID_RESEARCH.json
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = "/home/ubuntu/src/BinanceFuturesJava"
SRC = os.environ.get("GRID_DIR", "/tmp/grid_research")
OUT_JSON = os.path.join(REPO, "docs/result/GRID_RESEARCH.json")

COINS = "BTCUSDT ETHUSDT SOLUSDT BNBUSDT XRPUSDT DOGEUSDT".split()
MONTHS = ["2022-05", "2022-11", "2023-06", "2024-03", "2024-11", "2025-06"]
# 3 cau hinh luoi khoa truoc: (id, dai +-band, buoc g)
GRIDS = [("G1", 0.10, 0.010), ("G2", 0.10, 0.005), ("G3", 0.30, 0.015)]
# phi %/vong (round-trip) theo che do
FEES = {"maker": 0.0400, "taker_do": 0.0982, "taker_spread": 0.1120, "stress": 0.1500}
BLOCK_DAYS = 3          # 72h
NREP = 2000
SEED = 20260905
INFLATE = 1.177410      # sqrt(2 ln 2)


def run_grid(o, h, l, c, band, g):
    """Neutral bounded grid, 50% deployed at start. Sate may per MUC (lenh limit thuc su):
    b[k]=co lenh MUA cho o muc k ; s[k]=co lenh BAN cho o muc k. Mua tai k -> dat ban k+1;
    ban tai k -> dat mua k-1. Moi muc toi da 1 khop/nen (khong round-trip trong 1 nen).
    Tra ve: net_gross (chua tru phi), turnover (tong notional/B), q cuoi, eq path."""
    n = len(c)
    p0 = float(c[0])
    half = band / g
    Nlvl = int(round(2 * half))          # so buoc => Nlvl+1 muc
    pmin = p0 * (1.0 - half * g)
    step = p0 * g
    dq = 1.0 / (Nlvl * p0)               # B=1
    qmax = Nlvl * dq
    q = (Nlvl // 2) * dq                 # bat dau 50% deployed
    cash = 1.0 - q * p0
    b = np.zeros(Nlvl + 1, dtype=bool)
    s = np.zeros(Nlvl + 1, dtype=bool)
    b[: Nlvl // 2] = True
    s[Nlvl // 2 + 1:] = True
    turnover = 0.0
    nf = 0
    nbuy = 0
    nsell = 0
    units = [p0] * (Nlvl // 2)            # FIFO gia von cac don vi dang giu
    realized = 0.0
    eq = np.empty(n, dtype=np.float64)
    eq[0] = 1.0
    for t in range(1, n):
        lo, hi = l[t], h[t]
        klo = int(np.ceil((lo - pmin) / step))
        khi = int(np.floor((hi - pmin) / step))
        if klo < 0:
            klo = 0
        if khi > Nlvl:
            khi = Nlvl
        if klo > Nlvl or khi < 0:
            eq[t] = cash + q * c[t]
            continue
        down_first = (o[t] - lo) <= (hi - o[t])
        rng_up = range(klo, khi + 1)
        rng_dn = range(khi, klo - 1, -1)
        seq = [("B", rng_up), ("S", rng_dn)] if down_first else [("S", rng_dn), ("B", rng_up)]
        bb = set()
        ss = set()
        for side, rr in seq:
            if side == "B":
                for k in rr:
                    if b[k] and k not in bb and q + dq <= qmax + 1e-12:
                        q += dq
                        cash -= dq * (pmin + k * step)
                        b[k] = False
                        units.append(pmin + k * step)
                        if k + 1 <= Nlvl:
                            s[k + 1] = True
                            ss.add(k + 1)
                        turnover += dq * (pmin + k * step)
                        nf += 1
                        nbuy += 1
            else:
                for k in rr:
                    if s[k] and k not in ss and q - dq >= -1e-12:
                        q -= dq
                        pcost = units.pop(0) if units else p0
                        realized += dq * ((pmin + k * step) - pcost)
                        cash += dq * (pmin + k * step)
                        s[k] = False
                        if k - 1 >= 0:
                            b[k - 1] = True
                            bb.add(k - 1)
                        turnover += dq * (pmin + k * step)
                        nf += 1
                        nsell += 1
        eq[t] = cash + q * c[t]
    return {
        "net_gross": float(eq[-1] - 1.0),
        "realized": float(realized),
        "mtm_end": float(eq[-1] - 1.0 - realized),
        "turnover": float(turnover),
        "n_fills": int(nf),
        "n_buy": int(nbuy),
        "n_sell": int(nsell),
        "q_end_frac": float(q / qmax) if qmax > 0 else 0.0,
        "eq": eq,
        "p0": p0,
    }


def regime(o, h, l, c, band, g):
    ret = np.diff(np.log(c))
    vol_ann = float(np.std(ret) * np.sqrt(1440 * 365))
    ER = float(abs(np.log(c[-1] / c[0])) / max(np.sum(np.abs(ret)), 1e-12))
    # VR(60): overlapping
    r60 = np.convolve(ret, np.ones(60), "valid")
    vr = float(np.var(r60) / (60 * np.var(ret))) if np.var(ret) > 0 else np.nan
    ret_win = float(c[-1] / c[0] - 1.0)
    p0 = float(c[0])
    pmin = p0 * (1 - band); pmax = p0 * (1 + band)
    inband = float(np.mean((l >= pmin) & (h <= pmax)))
    # ADR ngay
    n = len(c)
    d = n // 1440
    adr = np.nan
    if d > 0:
        hh = h[: d * 1440].reshape(d, 1440).max(1)
        ll = l[: d * 1440].reshape(d, 1440).min(1)
        cc = c[: d * 1440].reshape(d, 1440)[:, 0]
        adr = float(np.mean((hh - ll) / cc))
    return {"vol_ann": vol_ann, "ER": ER, "VR60": vr, "ret_win": ret_win,
            "inband": inband, "ADR": adr}


def main():
    rows = []
    for sym in COINS:
        for mon in MONTHS:
            p = os.path.join(SRC, "%s-%s.npy" % (sym, mon))
            if not os.path.exists(p):
                print("MISS", p, flush=True)
                continue
            a = np.load(p)
            o, h, l, c = a[:, 1], a[:, 2], a[:, 3], a[:, 4]
            for gid, band, g in GRIDS:
                r = run_grid(o, h, l, c, band, g)
                rg = regime(o, h, l, c, band, g)
                eq = r.pop("eq")
                dd = float(np.min(eq / np.maximum.accumulate(eq) - 1.0))
                # daily net PnL (fraction) de bootstrap block-72h
                n = len(eq)
                d = n // 1440
                eqd = eq[: d * 1440].reshape(d, 1440)[:, -1]
                eqd = np.concatenate([[1.0], eqd])
                dret = np.diff(eqd) / eqd[:-1]
                row = {"sym": sym, "month": mon, "grid": gid, "fee_mode": None,
                       "net_gross": r["net_gross"], "dd_mtm": dd,
                       "realized": r["realized"], "mtm_end": r["mtm_end"],
                       "turnover": r["turnover"], "n_fills": r["n_fills"],
                       "n_buy": r["n_buy"], "n_sell": r["n_sell"],
                       "q_end_frac": r["q_end_frac"]}
                row.update(rg)
                for fm, fee in FEES.items():
                    net = r["net_gross"] - (fee / 100.0) / 2.0 * r["turnover"]
                    rows.append({**row, "fee_mode": fm, "net": net,
                                 "daily": dret.tolist()})
    # ---- tong hop ----
    base = [x for x in rows if x["fee_mode"] == "maker"]   # cung tap run cho moi fee
    # CI GROSS (block 72h tren chuoi daily PnL gop), don vi %/thang
    rng = np.random.default_rng(SEED)
    daily = np.concatenate([np.array(x["daily"]) for x in base])
    nb = len(daily) // BLOCK_DAYS
    blocks = daily[: nb * BLOCK_DAYS].reshape(nb, BLOCK_DAYS)
    means = np.empty(NREP)
    for i in range(NREP):
        pick = rng.integers(0, nb, nb)
        means[i] = blocks[pick].mean()
    lo_g, hi_g = np.percentile(means, [2.5, 97.5]) * INFLATE * 30  # -> %/thang
    print("GROSS: mean=%+.4f%%/thang  CI72h(x1.177,x30)=[%+.4f,%+.4f]"
          % (np.mean([x["net_gross"] for x in base]) * 100, lo_g * 100, hi_g * 100), flush=True)
    print("DECOMP gross: realized(cycle)=%+.4f%%  mtm_ton_kho_cuoi=%+.4f%%  |realized| TB=%.3f%%"
          % (np.mean([x["realized"] for x in base]) * 100, np.mean([x["mtm_end"] for x in base]) * 100,
             np.mean(np.abs([x["realized"] for x in base])) * 100), flush=True)
    print("turnover TB=%.2f xB  n_fills TB=%.1f  dd_mtm TB=%.2f%%  inband TB=%.2f"
          % (np.mean([x["turnover"] for x in base]), np.mean([x["n_fills"] for x in base]),
             np.mean([x["dd_mtm"] for x in base]) * 100, np.mean([x["inband"] for x in base])), flush=True)
    for fm, fee in FEES.items():
        sub = [x for x in rows if x["fee_mode"] == fm]
        allnet = np.array([x["net"] for x in sub])
        feem = float(np.mean([(fee / 100.0) / 2.0 * x["turnover"] for x in base]))  # %/thang
        print("[%s] n=%d mean(net/thang)=%+.4f%%  med=%+.4f  CI72h*1.177(x30)=[%+.4f,%+.4f]  duong=%d/%d  feeTB=%+.4f%%"
              % (fm, len(sub), allnet.mean() * 100, np.median(allnet) * 100,
                 (lo_g - feem) * 100, (hi_g - feem) * 100, int((allnet > 0).sum()), len(allnet), feem * 100), flush=True)
        for y in ("2022", "2023", "2024", "2025"):
            yy = [x["net"] for x in sub if x["month"].startswith(y)]
            if yy:
                print("    %s: mean=%+.4f%% n=%d duong=%d" % (y, np.mean(yy) * 100, len(yy), int(np.sum(np.array(yy) > 0))), flush=True)
    # theo luoi (maker)
    for gid, _, _ in GRIDS:
        yy = [x["net"] for x in rows if x["fee_mode"] == "maker" and x["grid"] == gid]
        print("    grid %s maker: mean=%+.4f%% duong=%d/%d turn=%.2f" % (gid, np.mean(yy) * 100, int(np.sum(np.array(yy) > 0)), len(yy), np.mean([x["turnover"] for x in base if x["grid"] == gid])), flush=True)
    # theo coin (maker)
    for sy in COINS:
        yy = [x["net"] for x in rows if x["fee_mode"] == "maker" and x["sym"] == sy]
        print("    coin %s maker: mean=%+.4f%%" % (sy, np.mean(yy) * 100), flush=True)
    # correlation ER / |ret| vs net (maker)
    sub = np.array([[x["net"], x["ER"], abs(x["ret_win"]), x["VR60"], x["ADR"], x["realized"], x["inband"]] for x in rows if x["fee_mode"] == "maker"])
    for j, nm in enumerate(["ER", "|ret|", "VR60", "ADR", "realized", "inband"]):
        cc = np.corrcoef(sub[:, 0], sub[:, j + 1])[0, 1]
        print("corr(net_maker, %s) = %+.3f" % (nm, cc), flush=True)
    # tercile theo ER: nhom "range-bound nhat" (ER thap) co net > 0 khong?
    for key, col in (("ER", 1), ("ADR", 4), ("VR60", 3)):
        o = np.argsort(sub[:, col])
        t = np.array_split(o, 3)
        print("tercile %s (maker): thap=%+.3f%%  giua=%+.3f%%  cao=%+.3f%%"
              % (key, sub[t[0], 0].mean() * 100, sub[t[1], 0].mean() * 100, sub[t[2], 0].mean() * 100), flush=True)
    # ER trung binh theo coin (co chon duoc coin 'di ngang' khong)
    for sy in COINS:
        e = [x["ER"] for x in rows if x["fee_mode"] == "maker" and x["sym"] == sy]
        print("    ER TB %s = %.5f" % (sy, np.mean(e)), flush=True)
    out = {"rows": [{k: v for k, v in r.items() if k != "daily"} for r in rows]}
    with open(OUT_JSON, "w") as f:
        json.dump(out, f)
    print("WROTE", OUT_JSON)


if __name__ == "__main__":
    main()
