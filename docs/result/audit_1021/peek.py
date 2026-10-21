import json, sys, logging
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
d = json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."):
    if k: d = d[k]
flt = sys.argv[3] if len(sys.argv) > 3 else ""
if isinstance(d, dict):
    for k, v in d.items():
        if str(k) >= flt:
            logging.info("%s %s", k, json.dumps(v)[:900])
else:
    logging.info("%s", json.dumps(d)[:3000])
