import sys, logging
import numpy as np
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import reset_rule_score as R
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("natvol")
d = R.load_daily("g2flat3-val")
log.info("daily rows=%d first=%s last=%s", len(d), d.index[0], d.index[-1])
eq = d["equity"].astype(float)
lr = np.log(eq / eq.shift(1)).dropna()
sd = lr.std(ddof=1)
log.info("B0 daily sd=%.4f%% annualized(x sqrt365)=%.2f%%", sd * 100, sd * np.sqrt(365) * 100)
roll = lr.rolling(20).std(ddof=1).dropna()
ann = roll * np.sqrt(365)
log.info("rolling20 ann vol: p10=%.3f p25=%.3f p50=%.3f p75=%.3f p90=%.3f mean=%.3f", *[float(np.percentile(ann, q)) for q in (10, 25, 50, 75, 90)], float(ann.mean()))
for tgt in (0.25, 0.14, 0.10, 0.08, 0.06):
    m = np.clip(tgt / ann, 0.5, 2.0)
    log.info("target=%.2f  mult mean=%.3f median=%.3f  frac@2.0=%.1f%%  frac@0.5=%.1f%%", tgt, m.mean(), np.median(m), 100 * (m >= 1.999).mean(), 100 * (m <= 0.501).mean())
