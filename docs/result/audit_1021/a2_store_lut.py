"""AUDIT 1021 A2 — niên đại ghi store market_data_object (Oracle aerospike-wfo 127.0.0.1:3222, ns test). CHI DOC (scan).
- moi record: time (bin), generation (meta), LUT (last-update-time qua expression filter) -> dem theo (nam ts) x (moc LUT)
- ts trung (nhieu key cung time): liet ke moi phien ban (d,u,d15) de doi chieu dong NEW lech STORE.
"""
import json, logging, struct, sys, time
from collections import defaultdict
import numpy as np, pandas as pd
import aerospike
from aerospike_helpers import expressions as exp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a2")
NEW = sys.argv[1]; OUT = sys.argv[2]
NS, SET = "test", "market_data_object"
c = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 20000}}).connect()
GMT7 = 7 * 3600000


def yr(t):
    return time.gmtime((t + GMT7) / 1000).tm_year


# 1) scan day du: time, gen, gia tri
rows = []
def cb(rec):
    key, meta, bins = rec
    d = bins.get("data"); t = bins.get("time")
    if d is None or t is None: return
    a, b, x = struct.unpack(">fff", bytes(d[:12]))
    rows.append((int(t), int(meta.get("gen", -1)), a, b, x, 1 if isinstance(key[2], str) else 0))
s = c.scan(NS, SET); s.select("time", "data"); s.foreach(cb)
R = pd.DataFrame(rows, columns=["ts", "gen", "d", "u", "d15", "haskey"])
R["yr"] = [yr(t) for t in R.ts]
log.info("scan rows=%d unique_ts=%d", len(R), R.ts.nunique())
res = {"n_records": len(R), "n_unique_ts": int(R.ts.nunique()),
       "gen_by_year": {int(y): {int(k): int(v) for k, v in g.gen.value_counts().sort_index().items()} for y, g in R.groupby("yr")}}

# 2) LUT: dem record theo nam ts co LUT < moc (scan co bo loc expression), cong don
MOCS = ["2026-06-01", "2026-06-23", "2026-07-01", "2026-07-15", "2026-08-01", "2026-08-05", "2026-08-06", "2026-08-07",
        "2026-08-08", "2026-08-10", "2026-08-14", "2026-08-20", "2026-09-01", "2026-10-01", "2026-10-22"]
lut = {}
for m in MOCS:
    ns_t = int(pd.Timestamp(m + " 00:00", tz="Asia/Ho_Chi_Minh").value)  # LUT tinh bang ns
    cnt = defaultdict(int)
    def cb2(rec):
        t = rec[2].get("time")
        if t is not None: cnt[yr(int(t))] += 1
    sc = c.scan(NS, SET); sc.select("time")
    sc.foreach(cb2, policy={"expressions": exp.LT(exp.LastUpdateTime(), ns_t).compile()})
    lut[m] = dict(sorted(cnt.items()))
    log.info("LUT < %s : %s (tong %d)", m, lut[m], sum(cnt.values()))
res["records_LUT_before_GMT7"] = lut
res["records_by_year"] = {int(k): int(v) for k, v in R.yr.value_counts().sort_index().items()}

# 3) dong NEW lech store: co khop phien ban khac cua ts trung khong
N = pd.read_csv(NEW, usecols=["timestamp", "momentum1M", "momentum15M"])
dup = R[R.ts.duplicated(keep=False)]
vers = defaultdict(list)
for t, a, x in zip(dup.ts.values, dup.d.values, dup.d15.values):
    vers[int(t)].append((float(a), float(x)))
first = R.drop_duplicates("ts")  # tham chieu: so voi BAT KY phien ban
J = N.merge(R[["ts", "d", "d15"]], left_on="timestamp", right_on="ts", how="inner")
J["ok"] = (np.abs(J.momentum1M - J.d.astype(np.float64)) <= 5.1e-9) & (np.abs(J.momentum15M - J.d15.astype(np.float64)) <= 5.1e-9)
okany = J.groupby("timestamp").ok.any()
nver = J.groupby("timestamp").size()
tsN = okany.index.values
y = np.array([yr(int(t)) for t in tsN])
res["NEW_vs_anyversion_by_year"] = {}
for Y in sorted(set(y)):
    msk = y == Y
    res["NEW_vs_anyversion_by_year"][int(Y)] = {"n": int(msk.sum()), "match_any_version": round(float(okany.values[msk].mean()), 6),
        "n_ts_multi_version": int((nver.values[msk] > 1).sum()),
        "n_nomatch": int((~okany.values[msk]).sum())}
    log.info("NEW vs store(any version) %d: %s", Y, res["NEW_vs_anyversion_by_year"][int(Y)])
# 2026 chi tiet theo thang
m26 = y == 2026
mon = np.array([time.gmtime((int(t) + GMT7) / 1000).tm_mon for t in tsN[m26]])
res["NEW_vs_store_2026_by_month"] = {int(mm): round(float(okany.values[m26][mon == mm].mean()), 5) for mm in sorted(set(mon))}
log.info("2026 theo thang %s", res["NEW_vs_store_2026_by_month"])
json.dump(res, open(OUT, "w"), indent=1)
log.info("WROTE %s", OUT)
c.close()
