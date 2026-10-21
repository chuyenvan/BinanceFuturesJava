"""AUDIT 1021 A2c — histogram LUT (ngay +07) cua cac set nguon gate tren Oracle aerospike-wfo. CHI DOC.
Voi moi set: dem record theo ngay LUT; neu co user_key dang chuoi -> (thang cua key) x (ngay LUT) cho LUT >= 2026-08-01."""
import json, logging, sys, time
from collections import defaultdict
import aerospike
from aerospike_helpers import expressions as exp
from aerospike_helpers.operations import expression_operations as eo

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a2c")
OUT = sys.argv[1]; SETS = sys.argv[2:]
c = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 60000}}).connect()
res = {}
for st in SETS:
    hist = defaultdict(int); late = defaultdict(int); keys = [0, 0]; samp = []
    def cb(rec):
        key, meta, bins = rec
        l = bins.get("lut")
        if l is None: return
        d = time.strftime("%Y-%m-%d", time.gmtime(l / 1e9 + 7 * 3600)); hist[d] += 1
        uk = key[2]
        if isinstance(uk, (str, int)):
            keys[0] += 1
            if len(samp) < 5: samp.append(str(uk))
            if d >= "2026-08-01": late[(str(uk)[:6], d)] += 1
        else:
            keys[1] += 1
    t0 = time.time()
    s = c.scan("test", st)
    s.add_ops([eo.expression_read("lut", exp.LastUpdateTime().compile())])
    s.foreach(cb, policy={"socket_timeout": 60000, "total_timeout": 0})
    res[st] = {"lut_day_hist": dict(sorted(hist.items())), "n_with_key": keys[0], "n_keyless": keys[1], "key_samples": samp,
               "late_keyprefix_x_lutday": {f"{a}|{b}": v for (a, b), v in sorted(late.items())}}
    log.info("%s %.0fs hist=%s keys=%s samp=%s late=%d nhom", st, time.time() - t0, res[st]["lut_day_hist"], keys, samp, len(late))
json.dump(res, open(OUT, "w"), indent=1)
c.close()
