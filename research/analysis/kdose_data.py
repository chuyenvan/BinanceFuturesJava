#!/usr/bin/env python3
"""KDOSE — du lieu: ticker HO26 (=242) + Binance Vision -> kho loi that (D1) + funding cache. Pre-reg docs/prereg/PREREG_KDOSE.md.

CHI DOC: ~/kaggle_data_hpo/ticker_2026*.bin.gz, data.binance.vision (cong khai, trong RAM), Aerospike Oracle-LOCAL (ns test:
funding_data, symbol_mapper). 0 cham 242, 0 Binance REST. Stage: d1 | fund.   python3 kdose_data.py d1
"""
import gzip, io, json, logging, os, pickle, sys, time, urllib.error, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import jbin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("kdose")
WD = "/home/ubuntu/claude_master/1010/kdose"
TICK = "/home/ubuntu/kaggle_data_hpo"
VIS = "https://data.binance.vision/data/futures/um/monthly/klines/%s/1m/%s-1m-%s.zip"
MN, H, D = 60000, 3600000, 86400000
TZ = 7 * H
U0 = 1776816000000                      # 2026-04-22 00:00 UTC
NM = 70 * 1440                          # -> 2026-07-01 00:00 UTC
IW0 = (1777084260000 - U0) // MN        # 2026-04-25 09:31 +07 = 02:31 UTC (diem gay KDIV)
IW1 = (1782838800000 - U0) // MN        # 2026-07-01 00:00 +07 (= 06-30 17:00 UTC)
IG0 = (1777568400000 - U0) // MN        # 2026-05-01 00:00 +07 (W_g)
VB = np.array([0, 0.001, 0.002, 0.005, 0.01, 0.02, 0.05, np.inf])
NSMAX = 900


def parse_day(day):
    """ticker 1 ngay UTC -> (day, syms, A[nsym,5,1440] O/H/L/C/Q float32). jbin tuple = (start,max,min,close,open,vol)."""
    p = TICK + "/ticker_%s.bin.gz" % day
    if not os.path.exists(p):
        return day, None, None
    d0 = int(pd.Timestamp(day).value // 10 ** 6)
    with gzip.open(p, "rb") as f:
        b = f.read()
    syms, R, C, V = {}, [], [], []
    for k, v in jbin.iter_minutes(b):
        mi = (k - d0) // MN
        if 0 <= mi < 1440:
            for s, t in v.items():
                R.append(mi)
                C.append(syms.setdefault(s, len(syms)))
                V.append(t)
    A = np.full((max(1, len(syms)), 5, 1440), np.nan, np.float32)
    if R:
        R, C, X = np.array(R), np.array(C), np.array(V, np.float64)
        for j, src in enumerate((4, 1, 2, 3, 5)):
            A[C, j, R] = X[:, src].astype(np.float32)
    return day, list(syms), A


def load_ticker(workers=3):
    """-> (Dn[nsym,5,NM] float32 NaN=khong co, names list). Fork pool TRUOC khi cap phat mang lon."""
    days = [x.strftime("%Y%m%d") for x in pd.date_range(pd.Timestamp(U0, unit="ms"), periods=70, freq="D")]
    SI, miss, t0 = {}, [], time.time()
    with Pool(workers) as pool:
        P = np.full((NSMAX, 5, NM), np.nan, np.float32)
        for i, (day, syms, A) in enumerate(pool.imap_unordered(parse_day, days)):
            if syms is None:
                miss.append(day)
                continue
            g0 = (int(pd.Timestamp(day).value // 10 ** 6) - U0) // MN
            idx = np.array([SI.setdefault(s, len(SI)) for s in syms])
            assert len(SI) <= NSMAX, len(SI)
            P[idx, :, g0:g0 + 1440] = A
            if i % 10 == 0:
                log.info("ticker %d/%d %.0fs nsym %d", i, len(days), time.time() - t0, len(SI))
    assert not miss, miss
    names = [None] * len(SI)
    for s, i in SI.items():
        names[i] = s
    log.info("ticker xong %d ngay nsym %d %.0fs", len(days), len(SI), time.time() - t0)
    return P[:len(SI)], names


ERR = {"http": 0}


def http(url, tries=4, timeout=60):
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            log.warning("http %s %s", e.code, url)
            if e.code in (418, 429, 403):
                time.sleep(30)
            time.sleep(3 + 5 * i)
        except Exception as e:
            log.warning("http err %s %s", e, url)
            time.sleep(3 + 5 * i)
    ERR["http"] += 1
    log.error("http FAIL %s", url)
    return None


def vis_sym(sym):
    """Vision monthly 2026-04..06 -> V[5,NM] float32 O/H/L/C/Q (NaN thieu) hoac None."""
    V, got = np.full((5, NM), np.nan, np.float32), 0
    for ym in ("2026-04", "2026-05", "2026-06"):
        b = http(VIS % (sym, sym, ym))
        if b is None:
            continue
        z = zipfile.ZipFile(io.BytesIO(b))
        df = pd.read_csv(z.open(z.namelist()[0]), header=None, dtype=str)
        df = df[df[0].str.isdigit()]
        mi = (df[0].astype(np.int64).to_numpy() // MN * MN - U0) // MN
        v = df[[1, 2, 3, 4, 7]].astype(np.float64).to_numpy().astype(np.float32)
        ok = (mi >= 0) & (mi < NM)
        V[:, mi[ok]] = v[ok].T
        got += 1
    return V if got else None


def local_month():
    t = pd.to_datetime(U0 + TZ + np.arange(NM, dtype=np.int64) * MN, unit="ms")
    return t.month.to_numpy().astype(np.int8)   # thang +07


def stage_d1():
    P, names = load_ticker()
    mon = local_month()
    idx = np.arange(NM)
    inw = (idx >= IW0) & (idx < IW1)
    st = dict(N_b=np.zeros(7, np.int64), E_b=np.zeros(7, np.int64), keep242=0, nocell=0, novis_sym=[],
              by_month={}, field_diff=np.zeros(5, np.int64), pre_break_diff=0, pre_break_cells=0)
    for m in (4, 5, 6):
        st["by_month"][m] = [0, 0, np.zeros(5, np.int64)]
    CMI, CSI, CMS, CVAL, CBIN, CINW, CREL = [], [], [], [], [], [], []
    t0 = time.time()
    with ThreadPoolExecutor(6) as ex:
        for si, (sym, V) in enumerate(zip(names, ex.map(vis_sym, names))):
            A = P[si]
            have = np.isfinite(A[3])
            if V is None:
                st["novis_sym"].append(sym)
                st["keep242"] += int((have & inw).sum())
                continue
            both = have & np.isfinite(V[3])
            st["keep242"] += int((have & ~np.isfinite(V[3]) & inw).sum())
            neq = ~(np.abs(A - V) <= np.float32(1e-8) * np.abs(V)) & both[None, :]
            diff = neq.any(0)
            with np.errstate(divide="ignore", invalid="ignore"):
                amp = (V[1].astype(np.float64) - V[2]) / V[0]
            b = np.clip(np.searchsorted(VB, np.nan_to_num(amp, nan=0.0), "right") - 1, 0, 6)
            w = both & inw
            st["N_b"] += np.bincount(b[w], minlength=7)
            st["E_b"] += np.bincount(b[w & diff], minlength=7)
            st["field_diff"] += neq[:, w].sum(1)
            pb = both & (idx < IW0) & (idx >= IW0 - 4 * 1440)
            st["pre_break_cells"] += int(pb.sum())
            st["pre_break_diff"] += int((pb & diff).sum())
            for m in (4, 5, 6):
                mm = w & (mon == m)
                bm = st["by_month"][m]
                bm[0] += int(mm.sum())
                bm[1] += int((mm & diff).sum())
                bm[2] += neq[:, mm].sum(1)
            ci = np.flatnonzero(diff)
            if len(ci):
                ms = np.zeros(len(ci), np.uint8)
                for f in range(5):
                    ms |= (neq[f, ci].astype(np.uint8) << f)
                CMI.append(ci.astype(np.int32))
                CSI.append(np.full(len(ci), si, np.int16))
                CMS.append(ms)
                CVAL.append(V[:, ci].T[neq[:, ci].T])          # gia tri Vision cua cac truong khac, theo o roi truong
                CBIN.append(b[ci].astype(np.int8))
                CINW.append(inw[ci])
                cw = ci[inw[ci] & neq[3, ci]]
                CREL.append(((A[3, cw].astype(np.float64) - V[3, cw]) / V[3, cw]).astype(np.float32))
            if si % 50 == 0:
                log.info("d1 %d/%d %s %.0fs cells %d http_fail %d", si, len(names), sym, time.time() - t0,
                         sum(len(x) for x in CMI), ERR["http"])
    cat = lambda L, dt: np.concatenate(L).astype(dt) if L else np.zeros(0, dt)
    MI, SI_, MS, VAL = cat(CMI, np.int32), cat(CSI, np.int16), cat(CMS, np.uint8), cat(CVAL, np.float32)
    BIN, INW, REL = cat(CBIN, np.int8), cat(CINW, bool), cat(CREL, np.float32)
    np.savez(WD + "/kdose_err.npz", mi=MI, si=SI_, msk=MS, val=VAL, bin=BIN, inw=INW,
             names=np.array(names), N_b=st["N_b"], E_b=st["E_b"])
    np.save(WD + "/kdose_rel_close.npy", REL)
    report_d1(st, MS, INW, REL, names)


def report_d1(st, MS, INW, REL, names):
    N, E = st["N_b"], st["E_b"]
    fd = st["field_diff"]
    bm = {m: dict(cells=v[0], err=v[1], err_pct=100.0 * v[1] / max(v[0], 1),
                  field_pct=dict(zip("OHLCQ", (100.0 * v[2] / max(v[0], 1)).round(4).tolist())))
          for m, v in st["by_month"].items()}
    t56c = st["by_month"][5][0] + st["by_month"][6][0]
    t56e = st["by_month"][5][1] + st["by_month"][6][1]
    a = np.abs(REL.astype(np.float64)) * 1e4
    res = dict(cells_W=int(N.sum()), err_W=int(E.sum()), ebar_pct=100.0 * E.sum() / max(N.sum(), 1),
               bins_pct=["<0.1", "0.1-0.2", "0.2-0.5", "0.5-1", "1-2", "2-5", ">5"],
               N_b=N.tolist(), E_b=E.tolist(), rate_b_pct=(100.0 * E / np.maximum(N, 1)).round(3).tolist(),
               share_b_pct=(100.0 * E / max(E.sum(), 1)).round(3).tolist(),
               field_pct_W=dict(zip("OHLCQ", (100.0 * fd / max(N.sum(), 1)).round(4).tolist())),
               by_month=bm, t56_err_pct=100.0 * t56e / max(t56c, 1), kdiv_t56=21.05,
               check_t56=("PASS" if abs(100.0 * t56e / max(t56c, 1) - 21.05) <= 1.0 else "FAIL"),
               close_absdiff_bps=dict(n=int(len(a)), p50=float(np.percentile(a, 50)) if len(a) else None,
                                      p90=float(np.percentile(a, 90)) if len(a) else None,
                                      p99=float(np.percentile(a, 99)) if len(a) else None),
               close_signed_mean_bps=float(REL.astype(np.float64).mean() * 1e4) if len(REL) else None,
               keep242_cells_W=st["keep242"], novis_sym=st["novis_sym"], nsym=len(names),
               pre_break_4d=dict(cells=st["pre_break_cells"], diff=st["pre_break_diff"]),
               store_cells=int(len(MS)), store_inW=int(INW.sum()), http_fail=ERR["http"])
    json.dump(res, open(WD + "/kdose_d1.json", "w"), indent=1, default=int)
    log.info("D1 %s", json.dumps({k: v for k, v in res.items() if k not in ("by_month", "novis_sym")}, default=int))


def stage_fund():
    import devexport_202609 as dx
    names = list(np.load(WD + "/kdose_err.npz")["names"])
    st = dx.Store("local")
    mp = st.get_symbol_mapper()
    F = {s: st.get_funding_map(s) for s in names}
    st.close()
    pickle.dump(dict(mapper=mp, fund=F), open(WD + "/kdose_fund.pkl", "wb"))
    log.info("fund: mapper %d, sym %d, co funding %d", len(mp), len(F), sum(v is not None for v in F.values()))


if __name__ == "__main__":
    {"d1": stage_d1, "fund": stage_fund}[sys.argv[1]]()
