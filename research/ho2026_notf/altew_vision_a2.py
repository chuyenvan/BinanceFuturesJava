#!/usr/bin/env python3
"""HO2026_TRADFI_AUDIT A2 (chi doc Vision, khong sim): theo thang 2025-12..2026-09, tai Vision monthly 1m cho MOI symbol USDT
(manifest ~/vz/manifest) -> tong hop theo phut:
 (1) ALT_EW (dung luat build_index/logret edge_attr_build: r=dlog close phut lien tiep, qv>0 ca 2 nen, bo BTC/ETH, clip 0.5)
     sum/n cho nhom CRYPTO / TF / IDX  -> ALL (validate vs ew_2026.npz), noTF, noTFIDX
 (2) proxy calMarketData (MarketBigChangeDetector: rc=close/open-1; bo rc>0.3; bo rc<-0.15 khi btc>-0.004; TreeMap khoa=rc
     (trung khoa gop 1); avg 100 khoa dau, period<=size*4/5) tren universe sim (in_uni: USDT, regex, !DIED, mapper 863)
     cho ALL / noTF / noTFIDX: down100, up100
 (3) thong ke TF theo ngay: so TF co dong, so TF co >=1 phut qv>0, ti le dong qv==0 (nen phang), ti trong TF trong ALT_EW.
Ghi ~/claude_master/ho_tradfi_wk/a2/<ym>.npz + day_<ym>.json. Khong luu zip."""
import io, json, logging, os, re, sys, time, urllib.parse, urllib.request, zipfile
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a2")
W = "/home/ubuntu/claude_master/ho_tradfi_wk"
OUT = W + "/a2"
os.makedirs(OUT, exist_ok=True)
C = json.load(open(W + "/classes.json"))
TF, IDX = set(C["TF"]), set(C["IDX"])
MAP = set(pd.read_csv("/home/ubuntu/claude_master/1011/ho4p1/stage/ho4p1-code/symbol_map_863.csv").symbol)
DIED = {"BTCDOMUSDT", "USDCUSDT"}
def in_uni(s):
    return s.endswith("USDT") and re.fullmatch(r"[A-Z0-9]+", s) is not None and s not in DIED and s in MAP
man = pd.read_csv("/home/ubuntu/vz/manifest/kline1m.csv.gz", usecols=["key", "sym"])
man["ym"] = man.key.str.extract(r"-1m-(\d{4}-\d{2})\.zip$")[0]
URL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"
def http(u):
    for a in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "ho2026tradfi"}), timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(2 + 3 * a)
        except Exception:  # noqa: BLE001
            time.sleep(2 + 3 * a)
    raise IOError(u)
def get(sm):
    s, m = sm
    b = http(URL.format(s=urllib.parse.quote(s), m=m))
    if b is None:
        return s, None
    z = zipfile.ZipFile(io.BytesIO(b))
    raw = z.read(z.namelist()[0])
    first = raw[:raw.find(b"\n")]
    hdr = 0 if not first[:1].isdigit() else None
    d = pd.read_csv(io.BytesIO(raw), header=hdr, usecols=[0, 1, 4, 7, 8], names=None if hdr is None else None)
    d.columns = ["t", "o", "c", "qv", "n"]
    d = d.drop_duplicates("t", keep="last").sort_values("t")
    return s, (d.t.to_numpy(np.int64), d.o.to_numpy(np.float64), d.c.to_numpy(np.float64), d.qv.to_numpy(np.float64), d.n.to_numpy(np.int64))
months = sys.argv[1:] or (["2025-12"] + ["2026-%02d" % k for k in range(1, 10)])
for ym in months:
    if os.path.exists(OUT + "/%s.npz" % ym):
        log.info("skip %s", ym); continue
    t0 = time.time()
    syms = sorted(s for s in set(man[man.ym == ym].sym) if s.endswith("USDT") and "_" not in s)
    with ThreadPoolExecutor(16) as ex:
        got = [g for g in ex.map(get, [(s, ym) for s in syms]) if g[1] is not None]
    m0 = int(pd.Timestamp(ym + "-01", tz="UTC").timestamp() * 1000)
    m1 = int((pd.Timestamp(ym + "-01", tz="UTC") + pd.offsets.MonthBegin(1)).timestamp() * 1000)
    NM = (m1 - m0) // 60000
    S = [g[0] for g in got]
    NS = len(S)
    LC = np.full((NS, NM), np.nan, np.float64); RC = np.full((NS, NM), np.nan, np.float32); QV = np.zeros((NS, NM), np.float32); PR = np.zeros((NS, NM), bool)
    for i, (s, (t, o, c, qv, n)) in enumerate(got):
        k = (t - m0) // 60000
        ok = (k >= 0) & (k < NM)
        k = k[ok]
        LC[i, k] = np.log(c[ok]); RC[i, k] = (c[ok] / o[ok] - 1).astype(np.float32); QV[i, k] = qv[ok]; PR[i, k] = True
    del got
    # (1) ALT_EW (cross-month boundary: phut dau thang khong co r -> giong build_index theo thang)
    r = np.full((NS, NM), np.nan); r[:, 1:] = LC[:, 1:] - LC[:, :-1]
    ok = np.zeros((NS, NM), bool); ok[:, 1:] = PR[:, 1:] & PR[:, :-1] & (QV[:, 1:] > 0) & (QV[:, :-1] > 0)
    alt = ok & np.isfinite(r) & ~np.isin(np.array(S), ["BTCUSDT", "ETHUSDT"])[:, None]
    rc_ = np.where(alt, np.clip(r, -0.5, 0.5), 0.0)
    isTF = np.array([s in TF for s in S]); isIDX = np.array([s in IDX for s in S])
    agg = {}
    for nm, msk in (("cr", ~isTF & ~isIDX), ("tf", isTF), ("idx", isIDX)):
        agg["n_" + nm] = alt[msk].sum(0).astype(np.int32); agg["s_" + nm] = rc_[msk].sum(0)
    # (2) calMarketData proxy tren in_uni
    U = np.array([in_uni(s) for s in S])
    bi = S.index("BTCUSDT")
    btc = RC[bi]
    out = {k: np.full(NM, np.nan, np.float32) for k in ("dn_all", "up_all", "dn_notf", "up_notf", "dn_notfidx", "up_notfidx", "n_all", "n_notf", "nzero_tf")}
    for j in range(NM):
        col = RC[:, j]
        have = PR[:, j] & U & np.isfinite(col)
        b = btc[j] if np.isfinite(btc[j]) else 0.0
        keep = have & ~(col > 0.3) & ~((b > -0.004) & (col < -0.15))
        for tag, m in (("all", keep), ("notf", keep & ~isTF), ("notfidx", keep & ~isTF & ~isIDX)):
            u = np.unique(col[m])
            if len(u) == 0:
                continue
            p = min(100, len(u) * 4 // 5)
            if p < 1:
                continue
            out["dn_" + tag][j] = u[:p].mean(); out["up_" + tag][j] = u[::-1][:p].mean()
            if tag == "all": out["n_all"][j] = len(u)
            if tag == "notf": out["n_notf"][j] = len(u)
        out["nzero_tf"][j] = int((keep & isTF & (col == 0)).sum())
    # (3) theo ngay
    days = {}
    for dd in range(NM // 1440):
        sl = slice(dd * 1440, (dd + 1) * 1440)
        tfp = PR[isTF & U, sl]; tfq = QV[isTF & U, sl] > 0
        tfp_all = PR[isTF, sl]; tfq_all = QV[isTF, sl] > 0
        n_alt = agg["n_cr"][sl] + agg["n_tf"][sl] + agg["n_idx"][sl]
        days[str((pd.Timestamp(ym + "-01") + pd.Timedelta(days=dd)).date())] = dict(
            tf_rows_uni=int((tfp.any(1)).sum()), tf_traded_uni=int((tfq.any(1)).sum()), tf_rows_all=int(tfp_all.any(1).sum()), tf_traded_all=int(tfq_all.any(1).sum()),
            tf_flat_row_frac_uni=float(1 - tfq.sum() / max(tfp.sum(), 1)), tf_active_min_median_uni=float(np.median(tfq.sum(1)[tfp.any(1)])) if tfp.any() else 0.0,
            tf_share_altew_mean=float(np.mean(agg["n_tf"][sl] / np.maximum(n_alt, 1))), tf_share_altew_max=float(np.max(agg["n_tf"][sl] / np.maximum(n_alt, 1))),
            n_uni_rows=int(PR[U, sl].any(1).sum()))
    np.savez_compressed(OUT + "/%s.npz" % ym, ts=(m0 + 60000 * np.arange(NM)).astype(np.int64), **agg, **out)
    json.dump(dict(ym=ym, n_sym=NS, n_tf=int(isTF.sum()), n_idx=int(isIDX.sum()), n_uni=int(U.sum()), n_uni_tf=int((U & isTF).sum()), days=days), open(OUT + "/day_%s.json" % ym, "w"))
    log.info("DONE %s nsym=%d tf=%d uni_tf=%d %.0fs", ym, NS, isTF.sum(), (U & isTF).sum(), time.time() - t0)
    del LC, RC, QV, PR, r, ok, alt, rc_
log.info("A2_ALL_DONE")
