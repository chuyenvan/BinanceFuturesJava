import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("kg")
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi(); api.authenticate()
seen = set()
for page in range(1, 40):
    ds = api.dataset_list(mine=True, page=page)
    if not ds: break
    n_new = 0
    for d in ds:
        if d.ref in seen: continue
        seen.add(d.ref); n_new += 1
        log.info("DS %s | size=%s | upd=%s", d.ref, getattr(d, "totalBytes", getattr(d, "total_bytes", None)),
                 getattr(d, "lastUpdated", getattr(d, "last_updated", None)))
    if n_new == 0: break
log.info("TOTAL_DS %d", len(seen))
