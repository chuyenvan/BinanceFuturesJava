import sys
from kaggle.api.kaggle_api_extended import KaggleApi
a = KaggleApi(); a.authenticate()
for n in sys.argv[1:]:
    try:
        r = a.dataset_list_files("chuyendinh/" + n, page_size=200)
    except TypeError:
        r = a.dataset_list_files("chuyendinh/" + n)
    fs = [f for f in r.files]
    gz = [f for f in fs if "ticker_" in str(f.name)]
    print(n, "files", len(fs), "ticker", len(gz), "bytes_ticker", sum(int(getattr(f, "totalBytes", 0) or 0) for f in gz))
