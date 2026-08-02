#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RECOVERY-BY-DEPTH tren TOAN UNIVERSE tu label (khu survivorship) — do DO SAU PHAO cho spec DCA.

Cau hoi: mot entry roi toi do sau -d, xac suat no HOI (cham +p SAU khi cham day) la bao nhieu?
Dat phao F o cho xac suat hoi roi khoi vach.

Nguon: funding_label.csv (all alt x luoi 15m). Cot: maxAdv_H (day sau nhat), maxFav_H (dinh cao nhat),
tHitAdv_H / tHitFav_H (offset phut toi day/dinh), retEnd_H, nBars_H — H in {24h,72h}.

KHU SURVIVORSHIP: label phu MOI coin ke ca coin sau do chet (trong cua so H). Coin cham day roi
KHONG hoi trong H => dem la KHONG hoi (khong bi bo khoi mau).

CHONG OVERLAP: 1 crash cua 1 coin trai nhieu bar 15m lien tiep => dedup cooldown COOL_H gio/coin
(non-overlapping event), tranh thoi phong so lieu.

GIOI HAN: horizon toi da 72h. DCA "cho hoi" dai hon => day la CAN DUOI cua ti le hoi (hoi trong 72h).
Bu cho probe Oracle (horizon 180 ngay nhung mau mong). Hai cai bracket lay dap an that.
"""
import os, glob, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rec-depth")

HZ = ["24h", "72h"]                    # horizon do
HSTEP = {"24h": 96, "72h": 288}        # so bar 15m 1 window day du
DEPTHS = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
PS = [0.0, 0.03]                        # muc hoi: hoa von, va +3% (TP spec)
COOL_H = 72                             # cooldown dedup (gio)


def find1(pat):
    m = glob.glob(pat, recursive=True)
    if not m:
        raise FileNotFoundError(pat)
    return m[0]


def dedup_cooldown(df, cool_ms):
    # giu event non-overlapping: sort theo (symbol, ts), bo row cach event truoc < cool
    df = df.sort_values(["symbol", "ts"]).reset_index(drop=True)
    keep = np.ones(len(df), dtype=bool)
    last = {}
    sym = df["symbol"].values
    ts = df["ts"].values
    for i in range(len(df)):
        s = sym[i]
        if s in last and ts[i] - last[s] < cool_ms:
            keep[i] = False
        else:
            last[s] = ts[i]
    return df[keep].reset_index(drop=True)


def main():
    path = find1("/kaggle/input/**/funding_label.csv")
    log.info("LABEL: %s", path)
    want = ["tEpochMs", "symbol"]
    for h in HZ:
        want += [f"maxAdv_{h}", f"maxFav_{h}", f"tHitAdv_{h}", f"tHitFav_{h}", f"retEnd_{h}", f"nBars_{h}"]
    df = pd.read_csv(path, usecols=lambda c: c in want, on_bad_lines="skip")
    df = df.rename(columns={"tEpochMs": "ts"})
    log.info("Nap %d row, cot: %s", len(df), list(df.columns))

    for h in HZ:
        adv, fav = f"maxAdv_{h}", f"maxFav_{h}"
        tadv, tfav = f"tHitAdv_{h}", f"tHitFav_{h}"
        nb = f"nBars_{h}"
        sub = df[df[nb] >= HSTEP[h]].copy()
        sub = sub[sub[adv].notna() & sub[fav].notna()]
        # dedup cooldown de non-overlapping
        d = dedup_cooldown(sub[["ts", "symbol", adv, fav, tadv, tfav]], COOL_H * 3600_000)
        log.info("")
        log.info("================ HORIZON %s : %d event (sau dedup %dh) ================", h, len(d), COOL_H)
        # HOI = cham day truoc (tHitAdv < tHitFav) VA sau do cham muc +p (maxFav>=p).
        # ordering tHitFav>tHitAdv => dinh den SAU day => la hoi that, khong phai pump-roi-dump.
        recovered_after = (d[tfav].values > d[tadv].values)
        maxfav = d[fav].values
        adv_v = d[adv].values
        for p in PS:
            rec = recovered_after & (maxfav >= p)
            log.info("--- muc hoi +%.0f%% ---", p * 100)
            log.info("%8s %9s %10s", "do sau", "so event", "%hoi")
            for dp in DEPTHS:
                mask = adv_v <= -dp
                n = int(mask.sum())
                if n == 0:
                    log.info("%7.0f%% %9d %10s", -dp * 100, 0, "-")
                    continue
                rate = 100.0 * rec[mask].mean()
                log.info("%7.0f%% %9d %9.1f%%", -dp * 100, n, rate)
                log.info("CSVREC,%s,%.0f,%.0f,%d,%.1f", h, p * 100, -dp * 100, n, rate)
        # phan phoi do sau (percentile maxAdv)
        a = np.sort(adv_v)
        def pct(q):
            return round(100.0 * a[min(int(q * (len(a) - 1)), len(a) - 1)], 1)
        log.info("maxAdv percentile %s: p50=%s p75=%s p90=%s p95=%s p99=%s worst=%s",
                 h, pct(0.50), pct(0.25), pct(0.10), pct(0.05), pct(0.01), round(100.0 * a[0], 1))

    log.info("========== HET RECOVERY-BY-DEPTH ==========")


if __name__ == "__main__":
    main()
