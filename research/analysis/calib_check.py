"""NUT THAT KIEN TRUC: gate dung DO TU TIN TUYET DOI cua selector (dyn_thr = f(score)),
nen moi model moi phai bi quantile-map ve phan phoi cua G015 => KHONG the cai thien phan tuyet doi.
Ma ~48% PnL den tu cac lenh o tick p15 THAP, noi CHI coin G015 cuc tu tin lot qua.

CAU HOI RE VA QUYET DINH: do tu tin tuyet doi cua G015 co HIEU CHUAN TOT khong?
 - Neu TOT: khong con du dia, giu nguyen G015 lam 'dau tuyet doi'.
 - Neu XAU: co du dia thay G015 bang mot dau xac suat hieu chuan tot hon => gate tot hon
   VA van giu S1 lam dau xep hang. Day la H3.
Chay tren ledger v3 (moi tick), DEV only.

DINH CHINH 2026-09-03: ban truoc tinh nguong bang
    thr = 0.008 * clip(score/0.15*1.2876, 0.26787, 2.14135)      <-- CO TRAN: SAI
Code that (AIRejectFilter.checkSignalDynamic) chi co CAN DUOI. Nay lay cong thuc tu
gate_cfg.py (doc truc tiep profile + Configs.java + AIRejectFilter.java).
Hau qua: nguong o dai score (0.2494, 0.3212] tang tu 1.713% len tan 2.206% => admit GIAM.
"""
import logging
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "/home/ubuntu/featv2")
import gate_cfg

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("calib_check")
gate_cfg.describe()

C = pd.read_parquet("/home/ubuntu/ledger/cand_dev3.parquet",
                    columns=["ts", "sym", "p15", "p_g015", "g1lite", "maxFav_72h"])
C = C[C.g1lite.notna() & C.p_g015.notna()].copy()
C["score"] = 1 - C.p_g015          # score dung nhu sim: thap = tu tin
C["yr"] = pd.to_datetime(C.ts, unit="ms").dt.year
LOG.info("rows: %d | ticks: %d", len(C), C.ts.nunique())

C["dyn_thr"] = gate_cfg.dyn_thr(C.score)
C["admit"] = C.p15 >= C.dyn_thr
LOG.info("ti le hang duoc gate cho qua: %.4f%%", 100 * C.admit.mean())
LOG.info("phan phoi score: p1=%.3f p5=%.3f p25=%.3f p50=%.3f p75=%.3f p99=%.3f",
         *np.percentile(C.score, [1, 5, 25, 50, 75, 99]))
LOG.info("ti le hang co score <= tran ung vien %.4f (tang 1, chi ap khi SELECTOR_RANK_TOPK<=0): %.3f%%",
         gate_cfg.CANDIDATE_SCORE_MAX, 100 * (C.score <= gate_cfg.CANDIDATE_SCORE_MAX).mean())
LOG.info("ti le hang duoc admit MA score < 0.30: %.2f%% cua so hang admit",
         100 * (C[C.admit].score < 0.30).mean())

LOG.info("=== 1. HIEU CHUAN TUYET DOI cua G015: outcome that theo bucket p_g015 ===")
C["b"] = pd.qcut(C.p_g015, 20, labels=False, duplicates="drop")
g = C.groupby("b").agg(n=("g1lite", "size"), p_tb=("p_g015", "mean"),
                       g1_tb=("g1lite", "mean"), win5=("g1lite", lambda s: (s > 0.05).mean()))
g["chenh_vs_buoc_truoc"] = g.g1_tb.diff()
LOG.info("\n%s", g.round(4).to_string())
mono = (g.g1_tb.diff().dropna() > 0).mean()
LOG.info("ti le buoc TANG don dieu: %.2f  (1.00 = hieu chuan hoan hao ve THU TU)", mono)

LOG.info("=== 2. Do tu tin co du bao duoc MUC do khong (khong chi thu tu)? ===")
LOG.info("spearman(p_g015, g1lite) toan pool = %.4f", spearmanr(C.p_g015, C.g1lite).correlation)
for y, gy in C.groupby("yr"):
    LOG.info("   %d n=%8d spearman=%.4f", y, len(gy), spearmanr(gy.p_g015, gy.g1lite).correlation)

LOG.info("=== 3. Cac hang G015 CUC TU TIN (score < 0.30) - nguon 48%% PnL - chat luong that ===")
CM = gate_cfg.CANDIDATE_SCORE_MAX
for lab, sub in [("score<0.10", C[C.score < 0.10]),
                 ("0.10-0.20", C[(C.score >= 0.10) & (C.score < 0.20)]),
                 ("0.20-0.30", C[(C.score >= 0.20) & (C.score < 0.30)]),
                 ("score>=0.30", C[C.score >= 0.30]),
                 ("  0.20-0.2494", C[(C.score >= 0.20) & (C.score < 0.2494)]),
                 ("  0.2494-tranUV", C[(C.score >= 0.2494) & (C.score <= CM)]),
                 ("  >tranUV", C[C.score > CM])]:
    if len(sub) == 0:
        LOG.info("   %-14s n=0", lab)
        continue
    LOG.info("   %-14s n=%8d  g1lite_tb=%+.4f  ti_le>5%%=%.3f  admit=%.5f  p15_tv=%.4f  thr_tb=%.5f",
             lab, len(sub), sub.g1lite.mean(), (sub.g1lite > 0.05).mean(), sub.admit.mean(),
             sub.p15.median(), sub.dyn_thr.mean())

LOG.info("=== 4. TRAN LY THUYET: neu co dau tuyet doi HOAN HAO thi gate chon duoc gi ===")
# gia lap: thay score bang thu hang thuc te cua g1lite trong tick (oracle) roi ap cung cong thuc gate
C["orc"] = 1 - C.groupby("ts").g1lite.rank(pct=True)
C["admit_orc"] = C.p15 >= gate_cfg.dyn_thr(C.orc)
LOG.info("   gate voi score THAT  : admit %.4f%% | g1lite_tb cua hang admit = %+.4f",
         100 * C.admit.mean(), C[C.admit].g1lite.mean())
LOG.info("   gate voi score ORACLE: admit %.4f%% | g1lite_tb cua hang admit = %+.4f",
         100 * C.admit_orc.mean(), C[C.admit_orc].g1lite.mean())
LOG.info("   => khoang cach nay la DU DIA toi da cua viec cai thien dau tuyet doi")
