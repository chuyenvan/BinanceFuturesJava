#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECOVERY-TO-AVG theo GRID LADDER, tren TOAN universe label (v2 — sua l 3 loi cua v1).

Sua so voi v1:
  * v1 do hoi ve firstEntry (SAI cho DCA). v2 do ve AVG da trung binh sau khi nhoi (dung TP that).
  * v1 dung bucket do sau deu. v2 mo phong GRID LADDER that (moc + ti trong) — leg fill theo maxAdv.
  * mau lon (dedup 24h tu toan label), so sanh nhieu cau hinh grid trong 1 lan.

HAN CHE (khong tranh duoc voi label): horizon toi da 72h. Hoi sau mat hang THANG (probe Oracle 180d
cho thay 100-267 ngay) => con so 72h la CAN DUOI cua ti le hoi. Doc kem probe Oracle de bracket.

Cach mo phong 1 entry voi grid (levels L=[0,l1,l2,l3], weights w):
  - leg i fill neu maxAdv_H <= L_i (gia da roi TOI moc do). leg0 luon fill.
  - k = so leg fill. avg_k = sum(w_i)/sum(w_i/(1+L_i)) cho i<k.
  - TP can: gia >= avg_k*(1+p). Tinh theo return-tu-entry: tp_ret_k = avg_k*(1+p) - 1.
  - HOI = maxFav_H >= tp_ret_k VA (k<2 hoac tHitFav_H > tHitAdv_H)  [dinh den SAU day => hoi that].
"""
import glob, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rec-grid-v2")

HZ = ["24h", "72h"]
HSTEP = {"24h": 96, "72h": 288}
COOL_MS = 24 * 3600_000
P_TP = 0.03
# cau hinh grid: ten -> (levels am [l1,l2,l3], weights [w0,w1,w2,w3])
GRIDS = {
    "g1_deep_backload": ([-0.50, -0.75, -0.90], [1, 1, 2, 6]),
    "g2_deep_flat":     ([-0.50, -0.75, -0.90], [1, 1, 1, 1]),
    "g3_shallow_flat":  ([-0.30, -0.50, -0.70], [1, 1, 1, 1]),
    "g4_shallow_front": ([-0.10, -0.20, -0.30], [3, 2, 1, 1]),
}


def find1(pat):
    m = glob.glob(pat, recursive=True)
    if not m:
        raise FileNotFoundError(pat)
    return m[0]


def dedup(df):
    df = df.sort_values(["symbol", "ts"]).reset_index(drop=True)
    keep = np.ones(len(df), dtype=bool)
    last = {}
    sym = df["symbol"].values; ts = df["ts"].values
    for i in range(len(df)):
        s = sym[i]
        if s in last and ts[i] - last[s] < COOL_MS:
            keep[i] = False
        else:
            last[s] = ts[i]
    return df[keep].reset_index(drop=True)


def grid_tables(levels, weights):
    # tra ve mang theo so-leg-fill k=1..4: avg_k, tp_ret_k
    L = [0.0] + list(levels)
    w = list(weights)
    avg = [np.nan] * (len(L) + 1)
    tpr = [np.nan] * (len(L) + 1)
    for k in range(1, len(L) + 1):
        money = sum(w[:k])
        qty = sum(w[i] / (1.0 + L[i]) for i in range(k))
        a = money / qty
        avg[k] = a
        tpr[k] = a * (1.0 + P_TP) - 1.0
    return L, avg, tpr


def main():
    path = find1("/kaggle/input/**/funding_label.csv")
    log.info("LABEL: %s", path)
    want = ["tEpochMs", "symbol"]
    for h in HZ:
        want += [f"maxAdv_{h}", f"maxFav_{h}", f"tHitAdv_{h}", f"tHitFav_{h}", f"nBars_{h}"]
    df = pd.read_csv(path, usecols=lambda c: c in want, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    log.info("Nap %d row", len(df))

    for h in HZ:
        adv, fav, tadv, tfav, nb = f"maxAdv_{h}", f"maxFav_{h}", f"tHitAdv_{h}", f"tHitFav_{h}", f"nBars_{h}"
        sub = df[(df[nb] >= HSTEP[h]) & df[adv].notna() & df[fav].notna()]
        d = dedup(sub[["ts", "symbol", adv, fav, tadv, tfav]])
        advv = d[adv].values; favv = d[fav].values
        after = d[tfav].values > d[tadv].values
        log.info("")
        log.info("############ HORIZON %s : %d event ############", h, len(d))
        for name, (levels, weights) in GRIDS.items():
            L, avg, tpr = grid_tables(levels, weights)
            # so leg fill: dem i sao cho advv <= L_i (L_0=0 luon dung)
            k = np.ones(len(d), dtype=int)
            for i in range(1, len(L)):
                k += (advv <= L[i]).astype(int)
            tp_ret = np.array([tpr[kk] for kk in k])
            recovered = (favv >= tp_ret) & ((k < 2) | after)
            # tong the
            log.info("--- %s  levels=%s w=%s  avg_full=%.1f%% (day->TP can +%.0f%%) ---",
                     name, levels, weights, (avg[len(L)] - 1) * 100,
                     (avg[len(L)] * (1 + P_TP) / (1.0 + levels[-1]) - 1) * 100)
            log.info("%6s %9s %9s %9s", "so leg", "so cum", "%tong", "%cham TP(avg)")
            for kk in range(1, len(L) + 1):
                m = k == kk
                n = int(m.sum())
                if n == 0:
                    log.info("%6d %9d %8s %10s", kk, 0, "-", "-"); continue
                rate = 100.0 * recovered[m].mean()
                log.info("%6d %9d %7.1f%% %10.1f%%", kk, n, 100.0 * n / len(d), rate)
                log.info("CSVGRID,%s,%s,%d,%d,%.1f", h, name, kk, n, rate)
            log.info("   => TONG %%cham TP: %.1f%%  (cum dung leg1 = %.1f%% tong)",
                     100.0 * recovered.mean(), 100.0 * (k == 1).mean())
    log.info("========== HET RECOVERY-GRID-V2 ==========")


if __name__ == "__main__":
    main()
