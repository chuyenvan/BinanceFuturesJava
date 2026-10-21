import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("as")
import aerospike
# CHI DOC: info sets tren Oracle aerospike-wfo (127.0.0.1:3222). Khong ghi.
c = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
r = c.info_all("sets")
for node, (err, txt) in r.items():
    for item in (txt or "").strip().split(";"):
        if not item: continue
        kv = dict(p.split("=", 1) for p in item.split(":") if "=" in p)
        log.info("SET ns=%s set=%s objects=%s mem/dev=%s", kv.get("ns"), kv.get("set"), kv.get("objects"),
                 kv.get("data_used_bytes", kv.get("device_data_bytes", kv.get("memory_data_bytes"))))
c.close()
