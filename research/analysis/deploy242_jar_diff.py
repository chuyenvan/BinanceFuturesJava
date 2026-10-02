#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEPLOY242 — so jar theo CRC32 tung .class (javac deterministic: cung nguon => cung byte).
Jar: LIVE 242 (8f3ee52c, keo ve READ-ONLY) vs SIM Kaggle sim-jar-gdv2 (7368be46) vs bdjar (ea14071d = module target 10-01 13:14).
In: so class khac/them/bot, va danh sach class khac thuoc DUONG gate/exit/sizing/selector.
Usage: python3 deploy242_jar_diff.py <jarA> <jarB> [<jarC> ...]  (cap dau so voi tung jar con lai)
"""
import hashlib
import json
import logging
import os
import sys
import zipfile

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("jar_diff")
PREFIX = "com/binance/chuyennd/"
HOT = ["EntryGate", "AIRejectFilter", "GateRatioBuffer", "GateRollingRatio", "LiveGateRollingRatio",
       "GateRatioPersist", "GateRollingThreshold", "OnnxInferenceManager", "TradeUtils", "Configs", "Cfg",
       "BinanceOrderTradingManager", "DetectEntrySignal2TradeNormal", "ShadowBookC3", "LiveProfileC3",
       "LegacySymbols", "OrderTargetInfoTest", "SimulatorMarketLevelTicker1MStopLoss", "S1RankerLive",
       "Net015ValueLive", "LiveBuildMap", "SelectorTier1Source", "TrailHingeSource", "LiveOiFeatProvider",
       "BudgetManager", "ComprehensiveMarketFeatureExtractor", "LiveFeatureDump", "MarketBigChangeDetector"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def crcs(p):
    with zipfile.ZipFile(p) as z:
        return {i.filename: (i.CRC, i.file_size) for i in z.infolist()
                if i.filename.startswith(PREFIX) and i.filename.endswith(".class")}


def outer(name):
    base = name[len(PREFIX):-6]
    return base.split("$")[0]


def compare(a, b):
    ca, cb = crcs(a), crcs(b)
    diff = sorted(k for k in set(ca) & set(cb) if ca[k] != cb[k])
    only_a = sorted(set(ca) - set(cb))
    only_b = sorted(set(cb) - set(ca))
    diff_outer = sorted(set(outer(k) for k in diff))
    hot = sorted(set(o for o in diff_outer + [outer(k) for k in only_a + only_b]
                     if o.split("/")[-1] in HOT))
    r = {"a": os.path.basename(a), "b": os.path.basename(b), "classes_a": len(ca), "classes_b": len(cb),
         "n_diff": len(diff), "n_only_a": len(only_a), "n_only_b": len(only_b),
         "diff_outer": diff_outer, "only_a_outer": sorted(set(outer(k) for k in only_a)),
         "only_b_outer": sorted(set(outer(k) for k in only_b)), "hot_changed": hot}
    LOG.info("[%s vs %s] diff=%d only_a=%d only_b=%d hot=%s", r["a"], r["b"], len(diff), len(only_a), len(only_b), hot)
    return r


def main():
    jars = sys.argv[1:]
    out = {"jars": {j: sha(j) for j in jars}, "pairs": [compare(jars[0], j) for j in jars[1:]]}
    for j, s in out["jars"].items():
        LOG.info("sha256 %s %s", s[:12], j)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
