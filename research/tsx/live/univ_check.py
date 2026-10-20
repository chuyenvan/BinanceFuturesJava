#!/usr/bin/env python3
"""Universe Vision (sim) vs live 242: symbol Vision 2026-09 khong co trong record kline_1m_opt 242 (cache 10-13..10-17)
co dong gop vao ALT_EW khong (qv>0 ca 2 nen)? Va anh huong len S_j / dd neu bo chung."""
import glob, json, os, zipfile  # noqa: E401

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

D = "/home/ubuntu/claude_master/v11_tsx/off/univ"
os.makedirs(D, exist_ok=True)
from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402
A = KaggleApi()
A.authenticate()
p = D + "/kline1m-2026-09.parquet"
if not os.path.exists(p):
    A.dataset_download_file("chuyendinh/vz-kline1m-2026", "kline1m-2026-09.parquet", path=D, quiet=True)
    for z in glob.glob(D + "/*.zip"):
        with zipfile.ZipFile(z) as f:
            f.extractall(D)
        os.remove(z)
t = pq.read_table(p, columns=["ts", "sym", "close", "quote_volume"]).to_pandas()
t["sym"] = t["sym"].astype(str)
t = t.drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"], kind="mergesort").reset_index(drop=True)
live = set(open("/home/ubuntu/claude_master/v11_tsx/off/cache_out/cache_1791922800000_1792198740000_syms.txt").read().split())
ts = t["ts"].to_numpy(np.int64)
sy = t["sym"].to_numpy()
lc = np.log(t["close"].to_numpy(np.float64))
qv = t["quote_volume"].to_numpy(np.float64)
same = (sy[1:] == sy[:-1]) & (ts[1:] - ts[:-1] == 60000)
r = np.full(len(t), np.nan)
r[1:] = np.where(same, lc[1:] - lc[:-1], np.nan)
ok = np.zeros(len(t), bool)
ok[1:] = same & (qv[1:] > 0) & (qv[:-1] > 0)
alt = ok & ~np.isin(sy, ["BTCUSDT", "ETHUSDT"]) & np.isfinite(r)
inlive = np.isin(sy, list(live))
out = {}
out["rows"] = int(len(t))
out["contrib_pairs"] = int(alt.sum())
out["contrib_pairs_not_live"] = int((alt & ~inlive).sum())
nl = pd.Series(sy[alt & ~inlive]).value_counts()
out["not_live_contrib_syms"] = int(len(nl))
out["not_live_top"] = nl.head(30).to_dict()
day = pd.to_datetime(ts, unit="ms").floor("D")
last = day == pd.Timestamp("2026-09-30")
out["0930_contrib_syms_total"] = int(len(np.unique(sy[alt & last])))
out["0930_contrib_syms_not_live"] = sorted(np.unique(sy[alt & last & ~inlive]).tolist())
cr = np.clip(r, -0.5, 0.5)
f = pd.DataFrame({"ts": ts[alt], "r": cr[alt]}).groupby("ts")["r"].mean()
g = pd.DataFrame({"ts": ts[alt & inlive], "r": cr[alt & inlive]}).groupby("ts")["r"].mean()
Sf = f.groupby(pd.to_datetime(f.index, unit="ms").floor("D")).sum()
Sg = g.groupby(pd.to_datetime(g.index, unit="ms").floor("D")).sum()
dS = (Sf - Sg).abs()
out["S_day_absdiff_max"] = float(dS.max())
out["S_day_absdiff_mean"] = float(dS.mean())
out["S_month_sum_full"] = float(Sf.sum())
out["S_month_sum_liveuniv"] = float(Sg.sum())
json.dump(out, open(D + "/univ_check.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "not_live_top"}, default=str))
print("top", list(out["not_live_top"].items())[:15])
os.remove(p)
