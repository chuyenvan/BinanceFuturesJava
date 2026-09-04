"""LAB3 — CI cua HIEU spearman(nhan, ROI that) giua cac nhan, block-bootstrap ghep cap khoi 72h.
Bo sung cai LAB2 thieu: LAB2 chi co diem uoc luong, khong co CI => khong tra loi duoc
"khac biet co phan biet duoc khong". Mo ta. CHI DEV.
"""
import glob
import logging
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

logging.basicConfig(level=logging.INFO, format="%(message)s",
                    handlers=[logging.FileHandler("/home/ubuntu/cov/LAB3.out", "w"),
                              logging.StreamHandler()])
LG = logging.getLogger("lab3")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label

VN = 7 * 3600 * 1000
Q = 900_000
H = 3600_000
SEED, NREP = 20260904, 2000

df = pd.read_csv("/home/ubuntu/java/devrun/C2b/storage/printDone.csv")
df = df[df.level == "PREDICT_SYMBOL_TRADE"].copy()
df["ts"] = (pd.to_datetime(df.start, format="%Y%m%d %H:%M").astype("int64") // 10**6 - VN)
df["ts"] = (df["ts"] // Q) * Q
df["symbol"] = df.sym + "USDT"
df["ret"] = df.pnl / df.margin
df["pnp"] = df["symbolPred"]

HS = ["4h", "24h", "72h"]
cols = ["tEpochMs", "symbol"] + [f"{k}_{h}" for h in HS for k in ("maxFav", "maxAdv", "retEnd")]
files = (sorted(glob.glob("/home/ubuntu/label_15m/funding_label_2022*.pb"))
         + sorted(glob.glob("/home/ubuntu/label_15m/funding_label_2023*.pb"))
         + sorted(glob.glob("/home/ubuntu/label_15m/funding_label_20240101*.pb"))
         + sorted(glob.glob("/home/ubuntu/label_15m/funding_label_20240401*.pb")))
want = df[["symbol", "ts"]].drop_duplicates()
parts = []
for f in files:
    L = read_label(f, usecols=cols)
    for h in HS:
        L[f"g1_{h}"] = np.where(L[f"maxFav_{h}"] >= 0.05,
                                L[f"maxFav_{h}"] - np.minimum(0.5 * L[f"maxFav_{h}"], 0.08),
                                L[f"retEnd_{h}"])
    L["hit6_4h"] = (L["maxFav_4h"] >= 0.06).astype(float)
    L["pathq_72h"] = L["maxFav_72h"] / (L["maxAdv_72h"].abs() + 0.01)
    parts.append(L.merge(want, left_on=["symbol", "tEpochMs"], right_on=["symbol", "ts"],
                         how="inner"))
Lb = pd.concat(parts)
m = df.merge(Lb.drop(columns=["ts"]), left_on=["symbol", "ts"],
             right_on=["symbol", "tEpochMs"], how="inner")
LG.info("n lenh = %d (join %.1f%%)", len(m), 100 * len(m) / len(df))

LAB = {
    "g1lite_72h(C2b)": m.g1_72h.values,
    "g1lite_24h": m.g1_24h.values,
    "g1lite_4h": m.g1_4h.values,
    "maxFav_72h": m.maxFav_72h.values,
    "pathq_72h": m.pathq_72h.values,
    "retEnd_72h": m.retEnd_72h.values,
    "hit6_4h(G015)": m.hit6_4h.values,
}
ret = m.ret.values
ts = m.ts.values.astype(np.int64)
TS_MIN = ts.min()
nb = int((ts.max() - TS_MIN) // (72 * H)) + 1
bid = ((ts - TS_MIN) // (72 * H)).astype(np.int64)
pop = int(len(np.unique(bid)))
LG.info("khoi 72h: %d tong, %d CO du lieu | n/khoi TB=%.1f", nb, pop, len(m) / pop)

idx_by_b = [np.where(bid == b)[0] for b in range(nb)]
rng = np.random.default_rng(SEED)
draw = rng.integers(0, nb, size=(NREP, nb))

LG.info("\n=== spearman(nhan, ROI that) + CI95 block-bootstrap khoi 72h ===")
boots = {}
for name, x in LAB.items():
    ok = np.isfinite(x) & np.isfinite(ret)
    pt = spearmanr(x[ok], ret[ok]).correlation
    bs = np.empty(NREP)
    for r in range(NREP):
        sel = np.concatenate([idx_by_b[b] for b in draw[r] if len(idx_by_b[b])])
        xx, rr = x[sel], ret[sel]
        o = np.isfinite(xx) & np.isfinite(rr)
        bs[r] = spearmanr(xx[o], rr[o]).correlation if o.sum() > 30 else np.nan
    boots[name] = bs
    lo, hi = np.nanpercentile(bs, [2.5, 97.5])
    LG.info("  %-18s rho=%+.3f  CI95=[%+.3f, %+.3f]  sd=%.4f", name, pt, lo, hi,
            np.nanstd(bs, ddof=1))

LG.info("\n=== CI cua HIEU (ghep cap: cung danh sach khoi moi rep) ===")
PAIRS = [
    ("g1lite_72h(C2b)", "g1lite_4h", "CHAN TROI 72h vs 4h"),
    ("g1lite_72h(C2b)", "g1lite_24h", "CHAN TROI 72h vs 24h"),
    ("g1lite_24h", "g1lite_4h", "CHAN TROI 24h vs 4h"),
    ("g1lite_72h(C2b)", "maxFav_72h", "CONG THUC (cung 72h)"),
    ("g1lite_72h(C2b)", "pathq_72h", "CONG THUC (cung 72h)"),
    ("g1lite_72h(C2b)", "retEnd_72h", "CONG THUC (cung 72h)"),
    ("g1lite_72h(C2b)", "hit6_4h(G015)", "C2b vs nhan G015"),
]
for a, b, tag in PAIRS:
    d = boots[a] - boots[b]
    dpt = np.nanmean(d)
    lo, hi = np.nanpercentile(d, [2.5, 97.5])
    verdict = "LOAI TRU 0" if lo * hi > 0 else "CHUA 0 => khong phan biet duoc"
    LG.info("  %-34s d=%+.3f CI95=[%+.3f, %+.3f]  %s", f"{a} - {b}", dpt, lo, hi, verdict)
    LG.info("      (%s)", tag)
LG.info("\nDONE_LAB3")
