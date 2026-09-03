"""NGUON SU THAT cho cong thuc gate tang 2, doc tu repo — KHONG hardcode.

Ly do ton tai: 2026-09-03 phat hien cong thuc bi ghi SAI ("clamp co tran => nguong hang so
1.713%") lan ra 9 file va vao ca ledger.py/ledger3.py. De khong tai pham, moi script phan tich
lay tham so + hinh dang cong thuc tu day, va day doc truc tiep tu:
  - profiles/<profile>.properties   (SIM_*)
  - Configs.java                    (default khi profile khong khai bao)
  - AIRejectFilter.java             (CO hay KHONG co can tren -> doc bang cach nhin code)

Cong thuc DUNG (2026-09-03):
  scaleFactor = max(AI_DYNAMIC_MIN, score / PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MULTIPLIER)
  dyn_thr     = MIN_MOMENTUM_15M * scaleFactor          <-- CHI CO CAN DUOI
AI_DYNAMIC_MAX KHONG phai tran clamp: no la TRAN UNG VIEN tang 1 selector
(maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD * AI_DYNAMIC_MAX), va tang 1 do BI BO QUA
khi SELECTOR_RANK_TOPK > 0.
"""
import io
import logging
import os
import re

import numpy as np

LOG = logging.getLogger("gate_cfg")
REPO = os.environ.get("BFJ_REPO", "/home/ubuntu/src/BinanceFuturesJava")
PROFILE = os.environ.get("GATE_PROFILE", REPO + "/profiles/c2b.properties")
_CFG_JAVA = REPO + "/src/main/java/com/binance/chuyennd/tradecore/Configs.java"
_ARF_JAVA = REPO + "/src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/AIRejectFilter.java"


def _read(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def _props(p):
    d = {}
    if not os.path.exists(p):
        return d
    for line in _read(p).split("\n"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        d[k.strip()] = v.strip()
    return d


_P = _props(PROFILE)
_CFG = _read(_CFG_JAVA)
_ARF = _read(_ARF_JAVA)


def _java_float(name):
    m = re.search(r"public static (?:final )?float " + name + r"\s*=\s*([0-9.eE+-]+)f", _CFG)
    if m is None:
        raise RuntimeError("khong doc duoc %s tu Configs.java" % name)
    return float(m.group(1))


def _resolve(profile_key, java_name):
    if profile_key in _P:
        return float(_P[profile_key]), "profile:" + profile_key
    return _java_float(java_name), "Configs.java:" + java_name


MIN_MOMENTUM_15M, SRC_MM = _resolve("SIM_MIN_MOMENTUM_15M", "MIN_MOMENTUM_15M")
AI_DYNAMIC_MIN, SRC_LO = _resolve("SIM_AI_DYNAMIC_MIN", "AI_DYNAMIC_MIN")
AI_DYNAMIC_MULTIPLIER, SRC_MULT = _resolve("SIM_AI_DYNAMIC_MULTIPLIER", "AI_DYNAMIC_MULTIPLIER")
AI_DYNAMIC_MAX, SRC_HI = _resolve("SIM_AI_DYNAMIC_MAX", "AI_DYNAMIC_MAX")
RATE_MAX, SRC_RM = _resolve("SIM_PREDICT_SYMBOL_RATE_MAX", "PREDICT_SYMBOL_RATE_MAX_THRESHOLD")
SELECTOR_RANK_TOPK = int(_P.get("SELECTOR_RANK_TOPK", "-1"))
CANDIDATE_SCORE_MAX = RATE_MAX * AI_DYNAMIC_MAX

# ---- doc HINH DANG cong thuc truc tiep tu AIRejectFilter.java, khong gia dinh ----
_blk = re.search(r"float scaleFactor\s*=.*?float dynamic_15M[^;]*;", _ARF, re.S)
if _blk is None:
    raise RuntimeError("khong tim thay khoi scaleFactor trong AIRejectFilter.java")
_BLK = _blk.group(0)
HAS_UPPER_CAP = "Math.min" in _BLK
HAS_LOWER_CAP = "Math.max" in _BLK
OFF_FLAT_HARD_GATES_CAP = "OFF_FLAT_HARD" in _BLK


def dyn_thr(score):
    """Nguong momentum 15M thuc te theo score selector (score THAP = TOT)."""
    raw = np.asarray(score, dtype="float64") / RATE_MAX * AI_DYNAMIC_MULTIPLIER
    sc = raw
    if HAS_LOWER_CAP:
        sc = np.maximum(AI_DYNAMIC_MIN, sc)
    if HAS_UPPER_CAP:
        sc = np.minimum(sc, AI_DYNAMIC_MAX)
    return MIN_MOMENTUM_15M * sc


def describe():
    LOG.info("gate_cfg: profile=%s", PROFILE)
    LOG.info("  MIN_MOMENTUM_15M=%.5f (%s) AI_DYNAMIC_MIN=%.5f (%s) MULT=%.5f (%s)",
             MIN_MOMENTUM_15M, SRC_MM, AI_DYNAMIC_MIN, SRC_LO, AI_DYNAMIC_MULTIPLIER, SRC_MULT)
    LOG.info("  AI_DYNAMIC_MAX=%.5f (%s) RATE_MAX=%.5f (%s) SELECTOR_RANK_TOPK=%d",
             AI_DYNAMIC_MAX, SRC_HI, RATE_MAX, SRC_RM, SELECTOR_RANK_TOPK)
    LOG.info("  AIRejectFilter: can_duoi=%s can_tren=%s (co OFF_FLAT_HARD con boc cap? %s)",
             HAS_LOWER_CAP, HAS_UPPER_CAP, OFF_FLAT_HARD_GATES_CAP)
    if not HAS_UPPER_CAP:
        LOG.info("  => KHONG CO TRAN. dyn_thr(san)=%.5f dyn_thr(score=%.4f)=%.5f",
                 dyn_thr(0.0), CANDIDATE_SCORE_MAX, dyn_thr(CANDIDATE_SCORE_MAX))
    else:
        LOG.warning("  => CO TRAN clamp o AI_DYNAMIC_MAX: dyn_thr toi da=%.5f",
                    MIN_MOMENTUM_15M * AI_DYNAMIC_MAX)
    LOG.info("  TANG 1 tran ung vien = RATE_MAX*AI_DYNAMIC_MAX = %.5f; TOPK=%d => tang 1 %s",
             CANDIDATE_SCORE_MAX, SELECTOR_RANK_TOPK,
             "BI BO QUA (rank top-K)" if SELECTOR_RANK_TOPK > 0 else "CO hieu luc (cutoff tuyet doi)")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    describe()
