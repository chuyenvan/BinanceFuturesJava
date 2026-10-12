#!/usr/bin/env python3
"""exec_legs.py -- EXEC E1a: tap chan DEV (nsel-nen-s*, K24+skipFull, stress 1,675% in-sim, 8 seed) -> bang chan + danh sach
(sym, ngay UTC) can aggTrades va (sym, thang) can kline 1m Vision. CHI DEV: start trong [2022-01-01, 2026-01-01) +07.
0 sim, 0 Java, 0 Binance REST. Output: ~/claude_master/1012/exec/legs.pkl, need.json
"""
import hashlib
import json
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("exec_legs")
HOME = "/home/ubuntu"
OUTK = HOME + "/kaggle_sim/out/"
W = HOME + "/claude_master/1012/exec"
SEEDS = (42, 7, 13, 21, 99, 123, 777, 2024)
H, D, MN = 3600000, 86400000, 60000
TZ = 7 * H
T22, T26 = 1640970000000, 1767200400000          # 2022-01-01 / 2026-01-01 00:00 GMT+7 (ms UTC)
CAP0 = 35000.0
DEC_OFF = 66000                                  # quyet dinh = giay 6 cua phut M+1 (nen M mo tai s_ms)
WIN_PRE, WIN_POST = 2 * MN, 30 * MN
PATH_H = 169 * H + 31 * MN                       # time-stop 168h + tre P4 toi da 30' + du


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def load(seed):
    tag = "nsel-nen-s%d" % seed
    assert not tag.startswith(("ho4", "ho26")), tag
    f = OUTK + tag + "/storage/printDone.csv"
    raw = pd.read_csv(f, on_bad_lines="skip")
    raw.columns = [c.strip() for c in raw.columns]
    for c in ("quantity", "entry", "margin", "pnl", "profit"):
        raw[c] = pd.to_numeric(raw[c], errors="coerce")
    ts = pd.to_datetime(raw["start"].astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    te = pd.to_datetime(raw["end"].astype(str).str.strip(), format="%Y%m%d %H:%M", errors="coerce")
    ok = (raw[["quantity", "entry", "margin", "pnl"]].notna().all(axis=1).to_numpy() & ts.notna().to_numpy()
          & te.notna().to_numpy())
    d = raw[ok].copy()
    d["row"] = np.arange(len(raw))[ok]
    d["s_ms"] = ts[ok].values.astype("datetime64[ms]").astype(np.int64) - TZ
    d["e_ms"] = te[ok].values.astype("datetime64[ms]").astype(np.int64) - TZ
    d["sym"] = d["sym"].astype(str).str.strip()
    d["level"] = d["level"].astype(str).str.strip()
    d["side"] = d["side"].astype(str).str.strip()
    d = d.sort_values(["s_ms", "row"], kind="mergesort").reset_index(drop=True)
    d["pid"] = d.groupby(["sym", "e_ms"], sort=False).ngroup()
    d["leg0"] = ~d.duplicated("pid", keep="first")
    d["nleg"] = d.groupby("pid")["pid"].transform("size")
    # von sim truoc luc vao = CAP0 + pnl da chot (e_ms <= s_ms) cung seed (xap xi, khong MTM)
    e_sorted = np.sort(d["e_ms"].to_numpy())
    cum = np.concatenate(([0.0], np.cumsum(d.sort_values("e_ms")["pnl"].to_numpy())))
    k = np.searchsorted(e_sorted, d["s_ms"].to_numpy(), side="right")
    d["eq_sim"] = CAP0 + cum[k]
    d["size_ratio"] = d["margin"] / d["eq_sim"]
    d["seed"] = seed
    meta = dict(tag=tag, md5=md5f(f), n_raw=int(len(raw)), n_ok=int(len(d)), sell=int((d["side"] != "BUY").sum()))
    d = d[(d["s_ms"] >= T22) & (d["s_ms"] < T26)].copy()
    meta["n_dev2225"] = int(len(d))
    return d, meta


def day_str(ms):
    return pd.Timestamp(int(ms), unit="ms").strftime("%Y-%m-%d")


def main():
    parts, metas = [], []
    for s in SEEDS:
        d, m = load(s)
        parts.append(d)
        metas.append(m)
        log.info("seed %d: %s", s, json.dumps(m))
    L = pd.concat(parts, ignore_index=True)
    L["t_dec"] = L["s_ms"] + DEC_OFF
    ev = L.groupby(["sym", "s_ms"], sort=True).size().rename("nseed").reset_index()
    ev["eid"] = np.arange(len(ev))
    L = L.merge(ev[["sym", "s_ms", "eid"]], on=["sym", "s_ms"], how="left")
    symday, symmon = set(), set()
    for sym, s in zip(ev["sym"], ev["s_ms"]):
        a, b = s + DEC_OFF - WIN_PRE, s + DEC_OFF + WIN_POST
        symday.add((sym, day_str(a)))
        symday.add((sym, day_str(b)))
        e = min(T26 - 1, s + PATH_H)
        for m in pd.period_range(pd.Timestamp(s - WIN_PRE, unit="ms"), pd.Timestamp(e, unit="ms"), freq="M"):
            symmon.add((sym, str(m)))
    need = dict(seeds=metas, n_legs=int(len(L)), n_events=int(len(ev)), n_symday=len(symday), n_symmon=len(symmon),
                n_sym=int(ev["sym"].nunique()), symday=sorted(symday), symmon=sorted(symmon),
                levels=L["level"].value_counts().to_dict(), leg0=int(L["leg0"].sum()),
                size_ratio=dict(zip(("p5", "p50", "p95"), np.percentile(L["size_ratio"], [5, 50, 95]).tolist())),
                per_year=L.groupby(pd.to_datetime(L["s_ms"] + TZ, unit="ms").dt.year).size().to_dict())
    pd.to_pickle(dict(L=L, ev=ev), W + "/legs.pkl")
    with open(W + "/need.json", "w") as f:
        json.dump(need, f, default=str)
    log.info("legs %d events %d symday %d symmon %d sym %d levels %s size_ratio %s per_year %s", len(L), len(ev),
             len(symday), len(symmon), need["n_sym"], need["levels"], need["size_ratio"], need["per_year"])


if __name__ == "__main__":
    main()
