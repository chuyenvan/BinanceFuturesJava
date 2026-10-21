import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("kg")
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi(); api.authenticate()
user = "chuyendinh"
log.info("== datasets mine")
for page in range(1, 6):
    ds = api.dataset_list(mine=True, page=page)
    if not ds: break
    for d in ds:
        log.info("DS %s | size=%s | upd=%s | title=%s", d.ref, getattr(d, "totalBytes", getattr(d, "total_bytes", None)),
                 getattr(d, "lastUpdated", getattr(d, "last_updated", None)), d.title)
log.info("== kernels mine")
for page in range(1, 8):
    ks = api.kernels_list(user=user, page=page, page_size=100)
    if not ks: break
    for k in ks:
        log.info("KN %s | upd=%s | title=%s", k.ref, getattr(k, "lastRunTime", getattr(k, "last_run_time", None)), k.title)
