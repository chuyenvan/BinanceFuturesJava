"""T1 — RATE PRIMARY + CI block-bootstrap ghep cap THEO THOI GIAN cho cac chan T1.

Tuan `docs/prereg/PREREG_T1.md` §6/§8. Bon chan chon COIN KHAC NHAU nen khong ghep cap duoc theo
tung lenh; ghep cap theo KHOI THOI GIAN (cung danh sach khoi cho moi chan) la cach dung.
Usage: python3 t1_rates_ci.py TAG_BASE TAG ...   (TAG = thu muc trong /home/ubuntu/java/devrun)
"""
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LG = logging.getLogger("t1_rates_ci")

B = "/home/ubuntu/java/devrun"
SEED_B, NREP, F_COV = 20260905, 2000, 1.21
H = 3600_000
RATES = ("tsloss", "win", "mp_sm", "mp_sl")
BETTER = {"tsloss": -1, "win": +1, "mp_sm": +1, "mp_sl": +1}   # dau = "tot hon cho chan do"


def load(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    for c in ("profit", "margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["profit"]).copy()
    d["ts"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M").astype("int64") // 10**6
    return d


def rates(d):
    sm = d.loc[d.status == "STOP_MARKET_DONE", "profit"]
    sl = d.loc[d.status == "STOP_LOSS_DONE", "profit"]
    return {"n": float(len(d)),
            "tsloss": 100.0 * float((d.status == "STOP_LOSS_DONE").mean()),
            "win": 100.0 * float((d.profit > 0).mean()),
            "mp_sm": float(sm.mean()) if len(sm) else np.nan,
            "mp_sl": float(sl.mean()) if len(sl) else np.nan}


def boot(D, tags, blen_h):
    """Resample KHOI thoi gian; moi rep dung CUNG danh sach khoi cho moi chan."""
    rng = np.random.default_rng(SEED_B)
    span = blen_h * H
    lo = min(int(d.ts.min()) for d in D.values())
    hi = max(int(d.ts.max()) for d in D.values())
    nb = int((hi - lo) // span) + 1
    idx = {t: [np.where(((D[t].ts.values - lo) // span) == k)[0] for k in range(nb)]
           for t in tags}
    out = {t: np.full((NREP, len(RATES)), np.nan) for t in tags}
    for r in range(NREP):
        pick = rng.integers(0, nb, nb)
        for t in tags:
            rows = np.concatenate([idx[t][k] for k in pick]) if nb else np.array([], int)
            if not len(rows):
                continue
            v = rates(D[t].iloc[rows])
            out[t][r] = [v[k] for k in RATES]
    return out


def main(tags):
    D = {t: load(t) for t in tags}
    base = tags[0]
    R = {t: rates(D[t]) for t in tags}
    LG.info("%-10s %5s %7s %8s %9s %9s", "tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL")
    for t in tags:
        LG.info("%-10s %5.0f %7.2f %8.2f %9.3f %9.3f", t, R[t]["n"], R[t]["win"],
                R[t]["tsloss"], R[t]["mp_sm"], R[t]["mp_sl"])
    for blen in (72, 24, 168):
        BO = boot(D, tags, blen)
        LG.info("\n== block-bootstrap %dh, NREP=%d, seed=%d, f=%.2f ==", blen, NREP, SEED_B, F_COV)
        for t in tags:
            if t == base:
                continue
            sig = []
            for j, k in enumerate(RATES):
                d = R[t][k] - R[base][k]
                sd = float(np.nanstd(BO[t][:, j] - BO[base][:, j], ddof=1))
                lo, hi = d - 1.96 * F_COV * sd, d + 1.96 * F_COV * sd
                ex = lo * hi > 0
                if ex:
                    sig.append(BETTER[k] * np.sign(d))
                LG.info("  %-9s %-7s d=%+9.4f sd=%7.4f f-CI=[%+9.4f,%+9.4f] excl0=%s",
                        t, k, d, sd, lo, hi, "YES" if ex else "no")
            same = len(set(sig)) == 1 if sig else False
            LG.info("  %-9s => %d/4 rate ngoai CI, cung huong=%s -> %s", t, len(sig), same,
                    "KHAC C2b" if (len(sig) >= 2 and same) else "KHONG PHAN BIET DUOC")


if __name__ == "__main__":
    main(sys.argv[1:])
