import json, logging, sys, re, hashlib, os
sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r1_s1")
import r1_a3_driver as R  # noqa
log = logging.getLogger("f")
ks = R.GA.ks_mod()
tag = sys.argv[1]
out = R.GA.OUT % tag
log.info("OUT=%s", out)
r = ks.fetch(tag, out_dir=out)
res = r["result"] or {}
log.info("result: %s", json.dumps({k: res.get(k) for k in ("ok", "java_rc", "secs", "equity_final", "n_trades", "date_first", "date_last", "jar_sha256", "profile_hash", "r1_a3")}))
pd_ = r["print_done"]
log.info("printDone=%s md5=%s", pd_, hashlib.md5(open(pd_, "rb").read()).hexdigest() if pd_ else None)
ref = R.GA.OUT % ("tsx-x14-" + tag.split("-")[-1]) + "storage/printDone.csv"
log.info("ref md5 %s", hashlib.md5(open(ref, "rb").read()).hexdigest())
txt = open(r["log"]).read() if r["log"] else ""
for pat in ("A3 bins sha", "A3 s3_funding", "A3 dataset ok", "A3_FAIL", "PATCH", "pred md5", "\\[TSX\\] extHours", "SYMBOL_MAPPER"):
    m = re.findall(".*%s.*" % pat, txt)
    log.info("%s -> %s", pat, [x[:220] for x in m[-2:]])
