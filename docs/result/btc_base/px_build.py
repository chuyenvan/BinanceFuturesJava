#!/usr/bin/env python3
"""BTC_BASE buoc 0: dung chuoi close 1m BTCUSDT/ETHUSDT (USDT-M, Binance Vision kline1m) 2021-01..2026-09 tren luoi phut UTC
+ funding BTCUSDT/ETHUSDT (Vision fundingRate). Nguon: gvz_mtm.kp (2021-06..2025-12, da co tren Oracle) + Kaggle
chuyendinh/vz-kline1m-2026 (2026-01..09, tai tung thang, trich 2 symbol, xoa parquet). Khong Binance REST."""
import glob
import json
import logging
import os
import sys
import zipfile

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import pyarrow.compute as pc

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402  (nguon gia Vision; import truoc)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bbpx")
W = "/home/ubuntu/claude_master/btc_base"
KL = W + "/kl"
os.makedirs(KL, exist_ok=True)
MS = 60000
T0 = int(pd.Timestamp("2021-01-01").value // 10**6) // MS          # phut UTC
T1 = int(pd.Timestamp("2026-10-01").value // 10**6) // MS
SYMS = ["BTCUSDT", "ETHUSDT"]
A = None


def path_of(ym):
    if ym <= "2025-12":
        return MT.kp(ym)
    global A
    p = KL + "/kline1m-%s.parquet" % ym
    if not os.path.exists(p):
        if A is None:
            from kaggle.api.kaggle_api_extended import KaggleApi
            A = KaggleApi()
            A.authenticate()
        A.dataset_download_file("chuyendinh/vz-kline1m-%s" % ym[:4], "kline1m-%s.parquet" % ym, path=KL, quiet=True)
        for z in glob.glob(KL + "/*.zip"):
            with zipfile.ZipFile(z) as f:
                f.extractall(KL)
            os.remove(z)
    return p


def main():
    n = T1 - T0
    C = {s: np.full(n, np.nan) for s in SYMS}
    rep = {}
    for ym in pd.period_range("2021-01", "2026-09", freq="M").strftime("%Y-%m"):
        p = path_of(ym)
        try:
            t = pq.read_table(p, columns=["ts", "sym", "close"])
        except Exception as ex:  # noqa: BLE001  file tai do dang -> tai lai 1 lan
            log.info("doc loi %s (%s) -> tai lai", p, ex)
            os.remove(p)
            p = path_of(ym)
            t = pq.read_table(p, columns=["ts", "sym", "close"])
        t = t.filter(pc.is_in(t.column("sym").cast("string"), value_set=__import__("pyarrow").array(SYMS)))
        d = t.to_pandas()
        d["sym"] = d["sym"].astype(str)
        d = d.drop_duplicates(["sym", "ts"], keep="last")
        for s in SYMS:
            x = d[d.sym == s]
            i = x.ts.to_numpy(np.int64) // MS - T0
            k = (i >= 0) & (i < n)
            C[s][i[k]] = x.close.to_numpy(float)[k]
        m0 = int(pd.Timestamp(ym + "-01").value // 10**6) // MS - T0
        m1 = int((pd.Timestamp(ym + "-01") + pd.offsets.MonthBegin(1)).value // 10**6) // MS - T0
        rep[ym] = {s: int(np.isnan(C[s][m0:m1]).sum()) for s in SYMS}
        log.info("px %s src=%s missing_min=%s", ym, p, rep[ym])
        if ym >= "2026-01":
            os.remove(p)
    fr = []
    for f in sorted(glob.glob("/home/ubuntu/vz/out/funding/20*/20*.parquet")):
        x = pd.read_parquet(f)
        x["sym"] = x["sym"].astype(str)
        fr.append(x[x.sym.isin(SYMS)])
    fr = pd.concat(fr).drop_duplicates(["sym", "ts"]).sort_values(["sym", "ts"])
    fr = fr[(fr.ts >= T0 * MS) & (fr.ts < T1 * MS)]
    frep = {s: dict(n=int((fr.sym == s).sum()), first=str(pd.Timestamp(fr[fr.sym == s].ts.min(), unit="ms")),
                    last=str(pd.Timestamp(fr[fr.sym == s].ts.max(), unit="ms")),
                    mean_rate=float(fr[fr.sym == s].rate.mean())) for s in SYMS}
    np.savez_compressed(W + "/px_btceth.npz", t0=T0, btc=C["BTCUSDT"], eth=C["ETHUSDT"],
                        f_sym=fr.sym.to_numpy().astype("U8"), f_ts=fr.ts.to_numpy(np.int64), f_rate=fr.rate.to_numpy(float))
    tot = {s: int(np.isnan(C[s]).sum()) for s in SYMS}
    json.dump({"missing_by_month": rep, "missing_total": tot, "funding": frep}, open(W + "/px_report.json", "w"), indent=1)
    log.info("PX_DONE missing_total=%s funding=%s", tot, frep)


if __name__ == "__main__":
    main()
