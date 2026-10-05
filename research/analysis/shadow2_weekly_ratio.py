"""SHADOW #2 prereg (ii): ti le so lenh/tuan K24+skipFull / K16 tu output Kaggle co san (0 sim, 0 tune).

Cap cung seed model: gqsf-<s> (K24 ON) vs gqsf16-<s> (K16 ON = byte-identical OFF), s in A1/S21/S7.
Ky 2022-01-03..2025-12-28 (tuan ISO day du). Dem theo ngay 'start' cua dong printDone.
Xuat JSON: phan vi p10/p50/p90 cua ti le tuan, ti le khoi 4 tuan, so lenh/tuan tuyet doi.
"""
import json
import logging
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("s2ratio")
OUT = "/home/ubuntu/kaggle_sim/out"
PAIRS = {"A1": ("gqsf-a1", "gqsf16-a1"), "S21": ("gqsf-s21", "gqsf16-s21"), "S7": ("gqsf-s7", "gqsf16-s7")}
D0, D1 = pd.Timestamp("2022-01-03"), pd.Timestamp("2025-12-29")


def weekly(tag, only_predict):
    df = pd.read_csv(f"{OUT}/{tag}/storage/printDone.csv", usecols=["start", "level"])
    if only_predict:
        df = df[df["level"] == "PREDICT_SYMBOL_TRADE"]
    t = pd.to_datetime(df["start"], format="%Y%m%d %H:%M")
    t = t[(t >= D0) & (t < D1)]
    wk = ((t - D0).dt.days // 7).value_counts()
    nweek = (D1 - D0).days // 7
    return wk.reindex(range(nweek), fill_value=0).sort_index().values.astype(float)


def pct(a):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return None
    return {k: round(float(np.percentile(a, q)), 3) for k, q in (("p10", 10), ("p50", 50), ("p90", 90))} | {
        "n": int(len(a)), "min": round(float(a.min()), 3), "max": round(float(a.max()), 3)}


def main():
    res = {"pairs": {}, "pooled": {}, "period": [str(D0.date()), str(D1.date())]}
    for mode, only_pred in (("all_legs", False), ("leg0_predict", True)):
        r1, r4, k24w, k16w, r4y = [], [], [], [], {}
        for s, (a, b) in PAIRS.items():
            x, y = weekly(a, only_pred), weekly(b, only_pred)
            LOG.info("%s %s: K24 tong=%d (%.0f/nam) K16 tong=%d (%.0f/nam)", mode, s, x.sum(), x.sum() / 4, y.sum(), y.sum() / 4)
            w = np.where(y > 0, x / np.where(y > 0, y, 1), np.nan)
            nb = len(x) // 4
            xb, yb = x[:nb * 4].reshape(nb, 4).sum(1), y[:nb * 4].reshape(nb, 4).sum(1)
            b4 = np.where(yb > 0, xb / np.where(yb > 0, yb, 1), np.nan)
            res["pairs"].setdefault(s, {})[mode] = {"total_k24": int(x.sum()), "total_k16": int(y.sum()),
                                                     "ratio_total": round(float(x.sum() / y.sum()), 3),
                                                     "week_ratio": pct(w), "block4w_ratio": pct(b4)}
            r1 += list(w); r4 += list(b4); k24w += list(x); k16w += list(y)
            for i in range(nb):
                yr = str((D0 + pd.Timedelta(days=28 * i)).year)
                r4y.setdefault(yr, []).append(b4[i])
        res["pooled"][mode] = {"week_ratio": pct(r1), "block4w_ratio": pct(r4), "k24_per_week": pct(k24w),
                               "k16_per_week": pct(k16w), "week_k16_zero": int(sum(1 for v in k16w if v == 0)),
                               "block4w_ratio_by_year": {k: pct(v) for k, v in sorted(r4y.items())}}
    json.dump(res, open(sys.argv[1], "w"), indent=1, ensure_ascii=False)
    LOG.info("ghi %s", sys.argv[1])
    print(json.dumps(res["pooled"], indent=1))


if __name__ == "__main__":
    main()
