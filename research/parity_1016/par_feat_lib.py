import glob
import gzip
import io
import zlib

import pandas as pd

FEATS = ["momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H", "momentumAcceleration",
         "trendStrengthETH", "trendConsistency", "volatility1M", "volatility15M", "volatility1H", "volatility24H",
         "volatilityTermStructure", "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown",
         "marketBreadthStrength", "btcDominance", "rsi14", "volumeSpike", "distMA20", "fundingRateRaw",
         "fundingRateAvg24H", "fundingRateTrend", "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
         "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike"]


def read_gz_tolerant(p):
    raw = b""
    try:
        with gzip.open(p, "rb") as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                raw += b
    except (EOFError, OSError, zlib.error):
        pass
    if not raw:
        return None
    txt = raw.decode(errors="ignore")
    lines = txt.splitlines()
    if not txt.endswith("\n"):
        lines = lines[:-1]
    if len(lines) < 2:
        return None
    try:
        return pd.read_csv(io.StringIO("\n".join(lines)))
    except Exception:  # noqa: BLE001
        return None


def read_live(shadow, since_ms, until_ms=None):
    parts = []
    for p in sorted(glob.glob(shadow + "/app/feat_dump/feat_dump_*.csv.gz")):
        d = read_gz_tolerant(p)
        if d is None or "ts" not in d:
            continue
        d = d[d.ts >= since_ms]
        if until_ms:
            d = d[d.ts < until_ms]
        parts.append(d)
    L = pd.concat(parts, ignore_index=True)
    L["min"] = (L.ts // 60000) * 60000
    return L.drop_duplicates("min", keep="last")
