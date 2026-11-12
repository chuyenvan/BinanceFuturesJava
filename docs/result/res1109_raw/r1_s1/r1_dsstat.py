import logging, time
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
a = KaggleApi(); a.authenticate()
for i in range(40):
    s = a.dataset_status("chuyendinh/r1-a3-bins")
    logging.info("status=%s", s)
    if str(s).lower() == "ready":
        break
    time.sleep(30)
