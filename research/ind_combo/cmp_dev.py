import logging
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s")
a = pd.read_parquet("/home/ubuntu/claude_master/ind1114/legs_x_dev.parquet")
b = pd.read_parquet("/home/ubuntu/claude_master/ind1114/legs_x.parquet")
cols = ["C%d" % i for i in range(1, 21)] + ["M%d" % i for i in range(1, 7)]
m = (a.per != "H").to_numpy()
assert (a.M.to_numpy() == b.M.to_numpy()).all()
bad = {c: int((~np.isclose(a[c].to_numpy()[m], b[c].to_numpy()[m], rtol=1e-9, atol=1e-12, equal_nan=True)).sum()) for c in cols}
logging.info("DEV lech sau rebuild HO: %s", bad)
assert (a.clu.to_numpy()[m] == b.clu.to_numpy()[m]).all()
h = b[b.per == "H"]
logging.info("HO leg %d cum %d nan %s", len(h), h.clu.nunique(), h[cols].isna().mean().round(3).to_dict())
