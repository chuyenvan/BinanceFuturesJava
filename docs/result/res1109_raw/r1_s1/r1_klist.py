import logging
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(message)s")
a = KaggleApi(); a.authenticate()
for k in a.kernels_list(mine=True, sort_by="dateRun", page_size=8):
    ref = getattr(k, "ref", None) or getattr(k, "slug", "")
    try:
        st = a.kernels_status(ref)
        st = getattr(st, "status", st)
    except Exception as e:  # noqa
        st = "ERR %s" % type(e).__name__
    logging.info("%s %s %s", ref, getattr(k, "lastRunTime", getattr(k, "last_run_time", "")), st)
