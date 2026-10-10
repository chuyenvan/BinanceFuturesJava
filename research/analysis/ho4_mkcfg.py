#!/usr/bin/env python3
"""HO4-P3: sinh cfg JSON cho kernel ho4-dev-x (ADDENDUM-5 §5.3). Usage: ho4_mkcfg.py <out.json>"""
import json, sys
import pandas as pd
mp = sorted(pd.read_csv("/home/ubuntu/claudedata/oi/symbol_map.csv")["symbol"].astype(str))
X = {"TICKER_SOURCE": "aerospike", "IS_KAGGLE_MODE": "false", "TIME_RUN": "20210101", "TIME_START": "1714150800000",
     "NUMBER_TICKER_CAL_RATE_CHANGE": "15", "NUMBER_HOUR_FUNDING_CAL": "30", "FUNDING_MAX_TRADE": "0.0006",
     "FUNDING_MIN_TRADE": "-0.0005", "RATE_FEE": "0.001", "RATE_PROFIT_STOP_MARKET": "0.1", "LEVERAGE_ORDER": "1",
     "NUMBER_ENTRY_EACH_SIGNAL": "4", "PROFIT_RATE": "0.01", "BTC_TREND_REVERSE_DURATION": "360",
     "BTC_TREND_REVERSE_RATE_MAX": "0.01", "BTC_TREND_REVERSE_RATE_MIN": "0.006", "BTC_TREND_REVERSE_RATE_MIN_TRADE": "0.0054",
     "STABLE_SYMBOLS": "SOL,ADA,DOGE,TRX,AVAX,LINK,XLM,VET,1000PEPE,SUI",
     "AEROSPIKE_SET_NAME_FUNDING_PRED": "funding_pred_1m_v5", "AEROSPIKE_SET_NAME_PRED_40": "pred_40_1m"}
T1 = "com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool"
LB = "com.binance.chuyennd.ai_ml.features.export.ExportFundingLabel"
cfg = {"tag": "ho4-dev-x", "jar_ds": "sim-jar-nsel",
       "jar_sha": "b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2",
       "cfg_ds": "sim-ho26a-bundle", "cfg_override": X, "as_ds": "ho3b-aerospike-ce", "as_mem_gb": 14, "xmx_gb": 11,
       "asdata_ds": "ho3b-asdata", "asdata_file": "asdata_local.pkl", "dev_market_ds": "sim-x1-2021-bundle",
       "S": [1751302800000, 1767200400000], "mapper": mp,
       "months": ["2025-06", "2025-07", "2025-08", "2025-09", "2025-10", "2025-11", "2025-12"],
       "fund_months": ["2025-%02d" % m for m in range(1, 13)], "ingest": ["20250601", "20251231"], "dl_threads": 24,
       "tasks": [
           {"name": "mkt", "cls": "com.binance.chuyennd.research.ExportMarketData2File", "args": [], "cfg": {"TIME_RUN": "20250601"},
            "post": "market", "out_glob": "market_rebuilt.bin", "timeout_s": 7200},
           {"name": "gate", "cls": "com.binance.chuyennd.ai_ml.features.export.gate.ExportGateDataset",
            "args": ["20250620", "20260101", "@OUT/gate/gate_dev.csv.gz"], "mkdirs": ["@OUT/gate"], "out_glob": "gate/*"},
           {"name": "t1a", "cls": T1, "args": ["20250701", "20251001", "@OUT/t1a/"], "env": {"FF_UNFILTERED": "1"},
            "mkdirs": ["@OUT/t1a"], "out_glob": "t1a/*"},
           {"name": "t1b", "cls": T1, "args": ["20251001", "20260101", "@OUT/t1b/"], "env": {"FF_UNFILTERED": "1"},
            "mkdirs": ["@OUT/t1b"], "out_glob": "t1b/*"},
           {"name": "laba", "cls": LB, "args": ["20250701", "20251001", "@OUT/laba/funding_label.csv"],
            "env": {"LABEL_THREADS": "4", "LABEL_STEP_MIN": "15"}, "mkdirs": ["@OUT/laba"], "out_glob": "laba/*"},
           {"name": "labb", "cls": LB, "args": ["20251001", "20260101", "@OUT/labb/funding_label.csv"],
            "env": {"LABEL_THREADS": "4", "LABEL_STEP_MIN": "15"}, "mkdirs": ["@OUT/labb"], "out_glob": "labb/*"}]}
json.dump(cfg, open(sys.argv[1], "w"), indent=1)
print(len(mp))
