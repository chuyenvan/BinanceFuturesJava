import logging, sys
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("kg")
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi(); api.authenticate()
refs = sys.argv[1:]
for r in refs:
    try:
        fl = api.dataset_list_files(r)
        files = getattr(fl, "files", fl)
        for f in files:
            log.info("FILE %s | %s | size=%s | created=%s", r, getattr(f, "name", f), getattr(f, "totalBytes", getattr(f, "total_bytes", getattr(f, "size", None))),
                     getattr(f, "creationDate", getattr(f, "creation_date", None)))
    except Exception as e:
        log.info("ERR files %s %s", r, e)
    try:
        own, slug = r.split("/")
        md = api.dataset_metadata(r, path="/tmp/audit1021_md")
        log.info("META %s -> %s", r, md)
    except Exception as e:
        log.info("ERR meta %s %s", r, e)
    try:
        vs = api.datasets_view(r) if hasattr(api, "datasets_view") else None
    except Exception as e:
        vs = None
