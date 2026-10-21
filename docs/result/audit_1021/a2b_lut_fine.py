"""AUDIT 1021 A2b — LUT min/max theo (nam, thang ts) cua market_data_object (CHI DOC, expression read LastUpdateTime)."""
import json, logging, sys, time
from collections import defaultdict
import aerospike
from aerospike_helpers import expressions as exp
from aerospike_helpers.operations import expression_operations as eo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a2b")
OUT = sys.argv[1]
c = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 20000}}).connect()
lut_expr = exp.LastUpdateTime().compile()
agg = defaultdict(lambda: [None, None, 0])
hist = defaultdict(int)
def cb(rec):
    key, meta, bins = rec
    t = bins.get("time"); l = bins.get("lut")
    if t is None or l is None: return
    g = time.gmtime((int(t) + 7 * 3600000) / 1000)
    k = "%d-%02d" % (g.tm_year, g.tm_mon)
    a = agg[k]
    a[0] = l if a[0] is None or l < a[0] else a[0]
    a[1] = l if a[1] is None or l > a[1] else a[1]
    a[2] += 1
    d = time.strftime("%Y-%m-%d", time.gmtime(l / 1e9 + 7 * 3600))
    hist[d] += 1
s = c.scan("test", "market_data_object")
s.add_ops([eo.expression_read("lut", lut_expr), eo.expression_read("time", exp.IntBin("time").compile())])
s.foreach(cb)
fmt = lambda ns: time.strftime("%Y-%m-%d %H:%M", time.gmtime(ns / 1e9 + 7 * 3600))
res = {"by_ts_month": {k: {"lut_min_gmt7": fmt(v[0]), "lut_max_gmt7": fmt(v[1]), "n": v[2]} for k, v in sorted(agg.items())},
       "n_records_by_lut_day_gmt7": dict(sorted(hist.items()))}
for k, v in res["by_ts_month"].items():
    log.info("%s %s", k, v)
log.info("LUT day hist %s", res["n_records_by_lut_day_gmt7"])
json.dump(res, open(OUT, "w"), indent=1)
c.close()
