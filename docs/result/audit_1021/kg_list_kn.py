import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("kg")
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi(); api.authenticate()
seen = set()
for page in range(1, 60):
    try:
        ks = api.kernels_list(user="chuyendinh", page=page, page_size=100)
    except Exception as e:
        log.info("ERR page %d %s", page, e); break
    if not ks: break
    n_new = 0
    for k in ks:
        key = k.ref or ("priv%d_%d" % (page, n_new))
        if key in seen: continue
        seen.add(key); n_new += 1
        log.info("KN %s | upd=%s", k.ref, getattr(k, "lastRunTime", getattr(k, "last_run_time", None)))
    if n_new == 0: break
log.info("TOTAL_KN %d", len(seen))
