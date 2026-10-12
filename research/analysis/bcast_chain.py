#!/usr/bin/env python3
"""BCAST (PREREG_BACKCAST_RESERVOIR 596c1ef8) chuoi ha nguon mode bc20 — chay TRONG kernel Kaggle, dung lai ham cua ho4p1_chain.py
(cung thu muc /tmp/code). Kho 2020: S_LO = 2020-01-01 00:00 +07, END = 2021-01-01 00:00 +07; khong ghep doan DEV; OI = ghim e3887f63.
KHONG tinh PnL/tin hieu: chi dem/khoang ts/NaN/md5. Usage (trong kernel): bcast_chain.py <cfg.json>"""
import json, logging, os, sys, time
import numpy as np
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ho4p1_chain as C  # noqa: E402  (module-level: kiem sha model, DUP_IDS, moi truong)
log = logging.getLogger("bcast_chain")
H = 3600000
S_LO, END = 1577811600000, 1609434000000
EDGES = [S_LO, 1585674000000, 1593536400000, 1601485200000, END]
CUTS = ["20200101", "20200401", "20200701", "20201001"]
SC_LO = 1588266000000                                  # 2020-05-01 00:00 +07 (dau cua so cham)


def ms7(d):
    return int(pd.Timestamp(d, tz="Asia/Ho_Chi_Minh").value // 10**6)


def month7(ts):
    return pd.to_datetime(np.asarray(ts, np.int64), unit="ms", utc=True).tz_convert("Asia/Ho_Chi_Minh").strftime("%Y-%m")


def build_oi_pin(lo, hi):
    pin = C.one("oi_percoin_full.bin", "funding-oi-percoin")
    assert C.sha256f(pin) == C.CFG["pin_sha"], "OI ghim sha"
    ODT = C.ODT
    n = os.path.getsize(pin) // ODT.itemsize
    parts, first = [], None
    for k in range(0, n, 10_000_000):
        c = np.fromfile(pin, dtype=ODT, count=min(10_000_000, n - k), offset=k * ODT.itemsize)
        if first is None:
            first = c[:1].copy()
        t = c["ts"].astype(np.int64)
        parts.append(c[(t >= lo) & (t < hi)].copy())
    a = np.concatenate(parts).astype(ODT)
    a = a[~np.isin(a["sym"].astype(np.int64), np.array(sorted(C.DUP_IDS), np.int64))]
    n_in = int(len(a))
    if n_in == 0:                                   # file rong lam vo np.concatenate([]) o doc theo khoi -> 1 dong NGOAI cua so
        a = first.astype(ODT)
        assert not (lo <= int(a["ts"][0]) < hi)
    a.tofile(C.G.OI_FILE)
    C.RES["steps"]["oi"] = dict(pin_rows_in_window=n_in, syms=sorted(int(x) for x in np.unique(a["sym"])) if n_in else [],
                                ts_min=int(a["ts"].min()), ts_max=int(a["ts"].max()), lo=lo, hi=hi, md5=C.md5f(C.G.OI_FILE))
    log.info("OI ghim %s", {k: v for k, v in C.RES["steps"]["oi"].items() if k != "syms"})


def run_bc20():
    CODE, OUT, RES = C.CODE, C.OUT, C.RES
    assert EDGES == [ms7(d) for d in ("2020-01-01", "2020-04-01", "2020-07-01", "2020-10-01", "2021-01-01")] and SC_LO == ms7("2020-05-01")
    src = C.CFG["x_src"]
    RES["prereg"] = "BCAST 596c1ef8"
    t0 = time.time()
    build_oi_pin(S_LO - 3 * 86400000, END + 4 * 86400000)
    C.save()
    st = C.load_gate(C.one("gate.csv*", src), S_LO, END)
    ts = st.timestamp.to_numpy(np.int64)
    assert (np.diff(ts) > 0).all()
    X = st[C.V3].to_numpy(np.float32)
    mo = month7(ts)
    nanr = np.isnan(X).sum(axis=1)
    RES["steps"]["gate"] = dict(rows=int(len(st)), ts_min=int(ts.min()), ts_max=int(ts.max()), nan_cells=int(nanr.sum()),
                                nan_cells_score_window=int(nanr[ts >= SC_LO].sum()),
                                rows_by_month=pd.Series(1, index=mo).groupby(level=0).sum().astype(int).to_dict(),
                                nan_cells_by_month=pd.Series(nanr, index=mo).groupby(level=0).sum().astype(int).to_dict(),
                                nan_by_col={c: int(v) for c, v in zip(C.V3, np.isnan(X).sum(axis=0)) if v})
    preds, p42 = {}, None
    for s in C.CFG["seeds"]:
        p = C.p15_of(CODE + "/gate_s%d_cut20260101p15.json" % s, X)
        md = C.write_pred(C.mkd(OUT + "/pred_s%d" % s) + "/pred.bin", b"", ts, p)
        preds[str(s)] = dict(md5=md, n=int(len(ts)), nan=int(np.isnan(p).sum()))
        if s == 42:
            p42 = p
    RES["steps"]["pred"] = preds
    del X
    C.save()
    m = C.read_market(C.one("market_rebuilt.bin", src))
    mt = m["ts"].astype(np.int64)
    mk = m[(mt >= S_LO) & (mt < END)]
    RES["steps"]["market"] = C.write_market(OUT + "/market.bin", [mk])
    RES["steps"]["market"]["minutes_by_month"] = pd.Series(1, index=month7(mk["ts"].astype(np.int64))).groupby(level=0).sum().astype(int).to_dict()
    C.save()
    srcs = [(p, 0, 1 << 62) for p in C.find("t1/*.t1c*", src)]
    os.makedirs(OUT + "/net015", exist_ok=True)
    RES["steps"]["net015"] = {c: C.net015_fold(srcs, EDGES[i], EDGES[i + 1], OUT + "/net015/predict_wf_%s.bin" % c) for i, c in enumerate(CUTS)}
    C.save()
    cl = C.closes_merge([(C.one("CLOSES_1H_vision1m.bin", src), 0, 1 << 62)])
    F, RES["steps"]["featv2"] = C.featv2(cl, False, C.ms_utc("2020-01-01"), C.ms_utc("2021-01-04"), S_LO - 24 * H, OUT + "/feat_v2_bc20.parquet")
    F = F[["ts", "sym"] + C.S1.KEEP].copy(); F["sym"] = F.sym.astype(np.int64)
    m781 = pd.read_csv(C.S1.MAP)
    i2s = dict(zip(C._m863.symId, C._m863.symbol))
    csyms = {i2s.get(int(x)) for x in np.unique(cl["sym"])}
    RES["steps"]["closes_syms_not_in_781"] = sorted(s for s in csyms if s not in set(m781.symbol))
    C.save()
    labs = C.find("lab/*.pb", src)
    RES["steps"]["s1"] = C.pool_s1(ts, p42, [(EDGES[i], EDGES[i + 1], labs) for i in range(4)], F, CODE + "/s1a2x1_cut20251231.json", "bcast20")
    C.save()
    RES["steps"]["bins_raw"] = C.bins("bcast20", CUTS, OUT + "/net015", OUT + "/bins")
    s2i = dict(zip(C._m863.symbol, C._m863.symId))
    ux = json.load(open(C.one("universe_excl.json", src)))
    nof = set(ux["no_funding_vision"])
    ids = {int(s2i[s]) for s in nof if s in s2i} | C.DUP_IDS
    RES["steps"]["excl_no_funding"] = dict(symbols=sorted(nof), ids=sorted(ids), settle_tail=sorted(ux.get("settle_tail", {})))
    RES["steps"]["bins"] = {c: C.drop_syms(OUT + "/bins/predict_wf_%s.bin" % c, ids) for c in CUTS}
    cov = {}
    for c in CUTS:
        a = np.fromfile(OUT + "/bins/predict_wf_%s.bin" % c, dtype=C.DT)
        df = pd.DataFrame({"m": month7(a["ts"].astype(np.int64)), "s": a["sym"].astype(np.int64)})
        cov.update(df.groupby("m").s.nunique().astype(int).to_dict())
        RES["steps"]["bins"][c].update(nan_p0=int(np.isnan(a["p0"].astype(np.float64)).sum()),
                                       ts_nondecr=bool((np.diff(a["ts"].astype(np.int64)) >= 0).all()))
    RES["steps"]["bins_syms_by_month"] = cov
    RES["secs"] = round(time.time() - t0)
    C.manifest()
    ok = (all(v["nan"] == 0 for v in preds.values()) and RES["steps"]["market"]["nan"] == 0
          and all(v["nan_p0"] == 0 and v["ts_nondecr"] for v in RES["steps"]["bins"].values())
          and all(v["nan"] == 0 for v in RES["steps"]["net015"].values()))
    RES["ok"] = bool(ok)
    C.save()
    log.info("CHAIN_BC20_DONE ok=%s secs=%s", ok, RES["secs"])


if __name__ == "__main__":
    assert C.CFG["mode"] == "bc20"
    run_bc20()
