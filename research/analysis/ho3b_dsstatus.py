import sys
from kaggle.api.kaggle_api_extended import KaggleApi
a = KaggleApi(); a.authenticate()
for n in sys.argv[1:]:
    try:
        print(n, a.dataset_status("chuyendinh/" + n))
    except Exception as e:  # noqa: BLE001
        print(n, "ERR", str(e)[:120])
